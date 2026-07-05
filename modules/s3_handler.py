"""
modules/s3_handler.py

S3-compatible object storage (Hetzner Object Storage / MinIO / any S3), ADR-0017.

Mirrors the interface of modules/azure_handler so the media-token endpoint can
dispatch to either backend (see modules/object_storage). The direct-upload model
is preserved: `generate_presigned_upload_url` returns a short-lived presigned PUT
URL that the phone uploads to directly — the API server never sees the bytes
(ADR-0009).

The presigned URL is signed WITHOUT a fixed Content-Type, so the client does a
plain PUT of the bytes (no Azure-specific headers).
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import config

logger = logging.getLogger(__name__)

# Lazy client — avoid constructing boto3/botocore at import time.
_client = None


def _require(*names):
    missing = [n for n in names if not getattr(config, n, None)]
    if missing:
        raise RuntimeError(
            "S3 object storage is not configured (missing: " + ", ".join(missing) + ")"
        )


def _get_client():
    global _client
    if _client is None:
        _require("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
        import boto3
        from botocore.config import Config as BotoConfig
        _client = boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT_URL,
            region_name=config.S3_REGION,
            aws_access_key_id=config.S3_ACCESS_KEY_ID,
            aws_secret_access_key=config.S3_SECRET_ACCESS_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": config.S3_ADDRESSING_STYLE},
            ),
        )
    return _client


def _object_url(presigned_url, object_name):
    """Permanent object URL: the S3_PUBLIC_BASE_URL override, else the presigned
    URL minus its query string (the most reliable host/path match)."""
    base = getattr(config, "S3_PUBLIC_BASE_URL", None)
    if base:
        return f"{base.rstrip('/')}/{object_name}"
    return presigned_url.split("?", 1)[0]


def generate_presigned_upload_url(object_name: str, expiry_minutes: int = 15) -> dict:
    """Short-lived presigned PUT URL for a direct phone→storage upload.

    Returns the same shape as the Azure handler:
        upload_url, blob_url, blob_name, expires_at

    Raises RuntimeError if S3 is not configured.
    """
    client = _get_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": config.S3_BUCKET, "Key": object_name},
        ExpiresIn=expiry_minutes * 60,
    )
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)).isoformat()
    logger.debug("S3 presigned PUT for '%s', expires %s", object_name, expires_at)
    return {
        "upload_url": upload_url,
        "blob_url": _object_url(upload_url, object_name),
        "blob_name": object_name,
        "expires_at": expires_at,
    }


def upload_file_to_bucket(local_file_path: str) -> str | None:
    """Server-side upload of a local file (web/anonymous lane). Returns the
    object URL, or None on failure."""
    try:
        client = _get_client()
        key = os.path.basename(local_file_path)
        client.upload_file(local_file_path, config.S3_BUCKET, key)
        base = getattr(config, "S3_PUBLIC_BASE_URL", None)
        url = (f"{base.rstrip('/')}/{key}" if base
               else f"{config.S3_ENDPOINT_URL.rstrip('/')}/{config.S3_BUCKET}/{key}")
        logger.info("S3 upload success: %s", url)
        return url
    except Exception as exc:  # noqa: BLE001 — log and degrade
        logger.error("S3 upload failed for %s: %s", local_file_path, exc)
        return None
