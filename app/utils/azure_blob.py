import logging
import os
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


def upload_file_to_azure_storage(file_path, blob_name, container_name):
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        raise Exception("AZURE_STORAGE_CONNECTION_STRING not set in environment variables.")

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container_name)

    # Create container if it doesn't exist
    try:
        container_client.create_container()
    except Exception:
        pass  # Container may already exist

    # Upload the file
    with open(file_path, "rb") as data:
        container_client.upload_blob(name=blob_name, data=data, overwrite=True)


def delete_file_from_azure_storage(blob_name: str, container_name: str) -> bool:
    """
    Remove a blob from Azure storage.

    Returns True on success or when the blob was already absent. Returns
    False (and logs) when the connection string is missing or the
    request fails for any other reason. Never raises — callers should
    proceed with database deletion even if blob cleanup fails, to avoid
    leaving the user unable to delete their own record.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logger.warning("Azure connection string missing — skipping blob delete for %s", blob_name)
        return False

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        container_client.delete_blob(blob_name)
        return True
    except ResourceNotFoundError:
        # Blob already gone — treat as success so we don't keep retrying.
        logger.info("Blob %s/%s already absent on delete", container_name, blob_name)
        return True
    except Exception as exc:
        logger.error("Azure delete failed for %s/%s: %s", container_name, blob_name, exc)
        return False