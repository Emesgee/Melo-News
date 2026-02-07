import os
import time
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_jwt_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        "postgresql://admin:admin@localhost:5432/mydb"  # Replace with your PostgreSQL credentials
        #'postgresql://admin:lelecafe@192.168.77.62:5432/mydb'  # Replace with your PostgreSQL credentials
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = 8000  # Changed from 5000

# Azure configuration
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "uploads")
DOWNLOADS_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# Kafka configuration
KAFKA_CONF = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': f'melo_consumer_{int(time.time())}',
    'auto.offset.reset': 'latest'  # Only get NEW messages, not old ones
}

# PostgreSQL configuration
PG_CONF = {
    'dbname': 'mydb',
    'user': 'admin',
    'password': 'admin',
    'host': 'localhost',
    'port': 5432
}

# Geocoding
ISRAEL_PALESTINE_BOUNDS = [29.5, 33.5, 34.0, 35.9]
CACHE_FILE = "geocode_cache.json"
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "palestinians_towns.geojson")
