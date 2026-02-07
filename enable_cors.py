from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

try:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Set CORS rules
    from azure.storage.blob import CorsRule
    
    cors_rule = CorsRule(
        allowed_origins=['*'],  # Allow all origins (or specify 'http://localhost:3000')
        allowed_methods=['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST'],
        allowed_headers=['*'],
        exposed_headers=['*'],
        max_age_in_seconds=3600
    )
    
    # Apply CORS settings
    blob_service_client.set_service_properties(cors=[cors_rule])
    print("=" * 60)
    print("✅ CORS ENABLED SUCCESSFULLY!")
    print("=" * 60)
    print("\nCORS Settings Applied:")
    print("- Allowed Origins: * (all origins)")
    print("- Allowed Methods: GET, HEAD, OPTIONS, PUT, POST")
    print("- Allowed Headers: *")
    print("- Max Age: 3600 seconds")
    print("\n🎉 Your videos should now load in the browser!")
    print("\nRefresh your browser at http://localhost:3000")
    
except Exception as e:
    print(f"❌ Error enabling CORS: {e}")
    print("\nMake sure AZURE_STORAGE_CONNECTION_STRING is set in .env file")
