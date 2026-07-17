import os
import json
import logging
import uuid as _uuid_mod
from datetime import datetime, timedelta, timezone
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    CorsRule,
    generate_blob_sas,
)
from azure.core.exceptions import ResourceExistsError
from urllib.parse import unquote
from config import AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME, DOWNLOADS_FOLDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy client — avoids network calls (and timeouts) at import time
# ---------------------------------------------------------------------------
_blob_service_client = None
_container_client = None


def _get_clients():
    """Return (blob_service_client, container_client), creating them once."""
    global _blob_service_client, _container_client
    if _blob_service_client is None:
        if not AZURE_CONNECTION_STRING:
            raise RuntimeError(
                "Azure Storage is not configured (AZURE_STORAGE_CONNECTION_STRING missing)"
            )
        _blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        _container_client = _blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        try:
            _container_client.create_container()
        except ResourceExistsError:
            pass
    return _blob_service_client, _container_client

def upload_file_to_blob(local_file_path):
    """Uploads a local file to Azure Blob Storage and returns its URL."""
    blob_service_client, container_client = _get_clients()
    filename = unquote(os.path.basename(local_file_path))
    blob_client = container_client.get_blob_client(filename)
    try:
        with open(local_file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"
        logger.info("Azure upload success: %s", blob_url)
        return blob_url
    except Exception as e:
        logger.error("Azure upload failed for %s: %s", local_file_path, e)
        return None

def _parse_connection_string(conn_str):
    """Extract AccountName and AccountKey from an Azure storage connection string."""
    parts = {}
    for segment in (conn_str or '').split(';'):
        if '=' in segment:
            key, _, value = segment.partition('=')
            parts[key.strip()] = value.strip()
    return parts.get('AccountName'), parts.get('AccountKey')


def generate_sas_upload_url(blob_name: str, expiry_minutes: int = 15) -> dict:
    """
    Generate a short-lived SAS URL that allows a mobile client to upload
    a single blob directly to Azure Blob Storage (no server proxying).

    Parameters
    ----------
    blob_name      : str  — target blob path, e.g. 'field-reports/42/uuid.mp4'
    expiry_minutes : int  — how long the SAS token is valid (default 15 min)

    Returns
    -------
    dict with keys:
        upload_url  : SAS URL — HTTP PUT this URL to upload the file
        blob_url    : Public/permanent URL of the blob after upload
        blob_name   : blob_name (echo back for the ingest payload)
        expires_at  : ISO-8601 expiry timestamp

    Raises
    ------
    RuntimeError if Azure is not configured or SAS generation fails.
    """
    if not AZURE_CONNECTION_STRING:
        raise RuntimeError("Azure Storage is not configured (AZURE_STORAGE_CONNECTION_STRING missing)")

    account_name, account_key = _parse_connection_string(AZURE_CONNECTION_STRING)
    if not account_name or not account_key:
        raise RuntimeError("Could not parse AccountName/AccountKey from connection string")

    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=AZURE_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expiry,
    )

    blob_url = (
        f"https://{account_name}.blob.core.windows.net"
        f"/{AZURE_CONTAINER_NAME}/{blob_name}"
    )
    upload_url = f"{blob_url}?{sas_token}"

    logger.debug("SAS token generated for blob '%s', expires %s", blob_name, expiry.isoformat())

    return {
        'upload_url': upload_url,
        'blob_url': blob_url,
        'blob_name': blob_name,
        'expires_at': expiry.isoformat(),
    }


def setup_cors():
    """Configure CORS rules for Azure Blob Storage"""
    try:
        blob_service_client, _ = _get_clients()
        cors_rule = CorsRule(
            allowed_origins=['http://localhost:3000', 'http://localhost:8000', '*'],
            allowed_methods=['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'DELETE'],
            allowed_headers=['*'],
            exposed_headers=['*'],
            max_age_in_seconds=3600
        )
        
        # Get current service properties and update CORS
        properties = blob_service_client.get_service_properties()
        properties['cors'] = [cors_rule]
        blob_service_client.set_service_properties(properties)
        logger.info("Azure CORS enabled for Blob Storage")
    except Exception as e:
        logger.warning("Could not set Azure CORS: %s. Manual configuration may be needed.", e)
