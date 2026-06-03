import os
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
    LOG_LEVEL = 'INFO'
else:
    _DB_HOST_DEFAULT = 'localhost'
    _DB_NAME_DEFAULT = 'melo_news'
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
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'uploads')

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

# ── Azure AI Services ──────────────────────────────────────────────
AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")
AZURE_VISION_KEY = os.getenv("AZURE_VISION_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# ── Event clustering / corroboration (Stage D) ────────────────────────
# Geo+time clustering of citizen reports into Events. Deliberately tunable
# (env-overridable) so the thresholds can be calibrated against real
# corroboration density during the pilot. Semantic clustering is deferred.
EVENT_CLUSTER_RADIUS_KM = float(os.getenv('EVENT_CLUSTER_RADIUS_KM', '1.0'))
EVENT_CLUSTER_WINDOW_HOURS = float(os.getenv('EVENT_CLUSTER_WINDOW_HOURS', '24'))
# Distinct non-anonymous identities among VERIFIED members required before an
# Event can reach CORROBORATED. Still gated: auto-promotion also needs a
# rung-2+ member present, so a flood of fresh rung-1 keys cannot self-promote.
EVENT_CORROBORATION_THRESHOLD = int(os.getenv('EVENT_CORROBORATION_THRESHOLD', '2'))

# ── Startup log ───────────────────────────────────────────────────────
logger.info(f"Environment: {ENVIRONMENT}")
logger.info(f"Log level: {LOG_LEVEL}")
logger.info(f"Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
