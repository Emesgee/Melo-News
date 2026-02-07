from azure.storage.blob import BlobServiceClient, PublicAccess
import os
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

try:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client("uploads")
    
    # Set container to allow public access to blobs
    container_client.set_container_access_policy(signed_identifiers={}, public_access=PublicAccess.Blob)
    
    print("=" * 60)
    print("✅ PUBLIC ACCESS ENABLED!")
    print("=" * 60)
    print("\nContainer 'uploads' is now publicly accessible")
    print("All blobs can be accessed without authentication")
    print("\nTest a video URL in your browser:")
    print("https://melonewsapp.blob.core.windows.net/uploads/917a91ba9b.mp4")
    print("\n🎉 Videos should now play in your app!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure AZURE_STORAGE_CONNECTION_STRING is correct")
