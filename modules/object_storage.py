"""
modules/object_storage.py

Backend-agnostic entry point for media object storage (ADR-0017).

Dispatches to S3-compatible storage (Hetzner Object Storage / MinIO) or Azure
Blob Storage based on config.STORAGE_BACKEND. The direct-upload model (server
never sees the bytes, ADR-0009) is identical either way.

The concrete backend functions are imported INSIDE each call so that:
  * an unconfigured/absent backend SDK only errors when actually used, and
  * existing tests that patch `modules.azure_handler.generate_sas_upload_url`
    keep working when STORAGE_BACKEND is 'azure'.
"""

import config


def presigned_upload_url(object_name: str, expiry_minutes: int = 15) -> dict:
    """Return a short-lived presigned upload dict
    {upload_url, blob_url, blob_name, expires_at} from the configured backend.
    Raises RuntimeError if that backend is not configured."""
    if config.STORAGE_BACKEND == "s3":
        from modules.s3_handler import generate_presigned_upload_url
        return generate_presigned_upload_url(object_name, expiry_minutes=expiry_minutes)
    from modules.azure_handler import generate_sas_upload_url
    return generate_sas_upload_url(object_name, expiry_minutes=expiry_minutes)


def upload_local_file(local_file_path: str):
    """Server-side upload (web/anonymous lane). Returns the object URL or None."""
    if config.STORAGE_BACKEND == "s3":
        from modules.s3_handler import upload_file_to_bucket
        return upload_file_to_bucket(local_file_path)
    from modules.azure_handler import upload_file_to_blob
    return upload_file_to_blob(local_file_path)
