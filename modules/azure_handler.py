import os
import json
import logging
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, CorsRule
from azure.core.exceptions import ResourceExistsError
from urllib.parse import unquote
from config import AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME, DOWNLOADS_FOLDER

logger = logging.getLogger(__name__)

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

try:
    container_client.create_container()
except ResourceExistsError:
    pass

def upload_file_to_blob(local_file_path):
    """Uploads a local file to Azure Blob Storage and returns its URL."""
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

def setup_cors():
    """Configure CORS rules for Azure Blob Storage"""
    try:
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
