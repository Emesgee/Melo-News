import os
import time
from pathlib import Path

env_file = Path(__file__).parent / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

# Database configuration built from env vars (defaults match docker-compose)
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')
DB_HOST = os.getenv('DB_HOST', 'melo-database')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'melonews_prod' if ENVIRONMENT == 'production' else 'melonews_dev')

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_jwt_secret_key')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 10,
        "max_overflow": 20,
    }
    PORT = 5000

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "uploads")
DOWNLOADS_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# ✅ ENVIRONMENT-SPECIFIC KAFKA CONFIGURATION
if ENVIRONMENT == 'production':
    KAFKA_CONF = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka-prod:9092'),
        'group.id': 'eyesonpalestine-consumer-prod',
        'auto.offset.reset': 'earliest'  # Read from beginning in production
    }
    SCHEDULER_ENABLED = True
    LOG_LEVEL = 'INFO'
    DB_HOST = os.getenv('DB_HOST', 'db-prod')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'mydb')
    DB_USER = os.getenv('DB_USER', 'admin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')
else:  # development (default)
    KAFKA_CONF = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': f'melo_consumer_dev_{int(time.time())}',
        'auto.offset.reset': 'earliest'  # Read all messages in development
    }
    SCHEDULER_ENABLED = False
    LOG_LEVEL = 'DEBUG'
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'mydb')
    DB_USER = os.getenv('DB_USER', 'admin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')

# PostgreSQL configuration (uses environment variables above)
PG_CONF = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

# Geocoding
ISRAEL_PALESTINE_BOUNDS = [29.5, 33.5, 34.0, 35.9]
CACHE_FILE = "geocode_cache.json"
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "palestinians_towns.geojson")

# ✅ Print configuration on startup
print(f"[CONFIG] Environment: {ENVIRONMENT}")
print(f"[CONFIG] Kafka servers: {KAFKA_CONF['bootstrap.servers']}")
print(f"[CONFIG] Scheduler enabled: {SCHEDULER_ENABLED}")
print(f"[CONFIG] Log level: {LOG_LEVEL}")
print(f"[CONFIG] Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")