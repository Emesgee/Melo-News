from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

try:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client("uploads")
    
    print("=" * 60)
    print("FILES IN AZURE BLOB STORAGE (uploads container):")
    print("=" * 60)
    
    count = 0
    for blob in container_client.list_blobs():
        count += 1
        print(f"\n{count}. {blob.name}")
        print(f"   URL: https://melonewsapp.blob.core.windows.net/uploads/{blob.name}")
        print(f"   Size: {blob.size} bytes")
        print(f"   Created: {blob.creation_time}")
    
    if count == 0:
        print("\n⚠️  NO FILES FOUND IN AZURE BLOB STORAGE!")
        print("You need to run Kafka consumer to upload files.")
    else:
        print(f"\n✅ Total files found: {count}")
        
except Exception as e:
    print(f"❌ Error connecting to Azure: {e}")
    print("\nCheck your AZURE_STORAGE_CONNECTION_STRING in .env file")
