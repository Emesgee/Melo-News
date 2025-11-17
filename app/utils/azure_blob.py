import os
from azure.storage.blob import BlobServiceClient

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