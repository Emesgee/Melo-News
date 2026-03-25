import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

env_file = Path(__file__).parent / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

# ── Environment-specific defaults ──────────────────────────────────────
if ENVIRONMENT == 'production':
    _DB_HOST_DEFAULT = 'db-prod'
    _DB_NAME_DEFAULT = 'melonews_prod'
    _KAFKA_BOOTSTRAP_DEFAULT = 'kafka-prod:9092'
    _KAFKA_GROUP_ID = 'eyesonpalestine-consumer-prod'
    SCHEDULER_ENABLED = True
    LOG_LEVEL = 'INFO'
else:
    _DB_HOST_DEFAULT = 'localhost'
    _DB_NAME_DEFAULT = 'melo_news'
    _KAFKA_BOOTSTRAP_DEFAULT = 'localhost:9092'
    _KAFKA_GROUP_ID = f'melo_consumer_dev_{int(time.time())}'
    SCHEDULER_ENABLED = False
    LOG_LEVEL = 'DEBUG'

# ── Database configuration (single source of truth) ────────────────────
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')
DB_HOST = os.getenv('DB_HOST', _DB_HOST_DEFAULT)
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', _DB_NAME_DEFAULT)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# PostgreSQL configuration for raw psycopg2 connections (Kafka pipeline)
PG_CONF = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

# ── Flask application config ──────────────────────────────────────────
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

    # Enforce real secrets in production
    if ENVIRONMENT == 'production':
        if not SECRET_KEY or SECRET_KEY == 'default_secret_key':
            raise ValueError("SECRET_KEY must be set in production")
        if not JWT_SECRET_KEY or JWT_SECRET_KEY == 'default_jwt_secret_key':
            raise ValueError("JWT_SECRET_KEY must be set in production")
    else:
        SECRET_KEY = SECRET_KEY or 'dev-only-secret-key'
        JWT_SECRET_KEY = JWT_SECRET_KEY or 'dev-only-jwt-secret-key'

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 10,
        "max_overflow": 20,
    }
    PORT = 5000

    # JWT cookie configuration (httpOnly for XSS protection)
    JWT_TOKEN_LOCATION = ["cookies", "headers"]  # Accept both during migration
    JWT_COOKIE_SECURE = ENVIRONMENT == 'production'  # HTTPS only in prod
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_ACCESS_COOKIE_PATH = '/'

# ── Azure / Blob Storage ──────────────────────────────────────────────
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "uploads")
DOWNLOADS_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# ── Kafka ─────────────────────────────────────────────────────────────
KAFKA_CONF = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', _KAFKA_BOOTSTRAP_DEFAULT),
    'group.id': _KAFKA_GROUP_ID,
    'auto.offset.reset': 'earliest'
}

# ── Geocoding ─────────────────────────────────────────────────────────
ISRAEL_PALESTINE_BOUNDS = [29.5, 33.5, 34.0, 35.9]
CACHE_FILE = "geocode_cache.json"
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "palestinians_towns.geojson")

# ── Startup log ───────────────────────────────────────────────────────
logger.info(f"Environment: {ENVIRONMENT}")
logger.info(f"Kafka servers: {KAFKA_CONF['bootstrap.servers']}")
logger.info(f"Scheduler enabled: {SCHEDULER_ENABLED}")
logger.info(f"Log level: {LOG_LEVEL}")
logger.info(f"Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
