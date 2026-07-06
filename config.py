import os
import logging
from datetime import timedelta
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

    # Access-token lifetime. flask-jwt-extended defaults to 15 minutes, far too
    # short for a field reporter who is often offline and can't re-login mid-
    # report. The JWT is only a turnstile here (ADR-0016) — the signature is the
    # real identity — and token-at-rest hardening is ADR-0011's job, so a long
    # default is acceptable for the drill. Override via JWT_ACCESS_TOKEN_EXPIRES_DAYS.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_DAYS', '30'))
    )

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

    # Anonymous /anonymous-ingest is DISABLED for the pilot (ADR-0007: an
    # unauthenticated public ingest is the easiest Sybil/spam vector and adds no
    # value to the scripted drill, which uses signed pseudonyms; anonymous
    # reports also count 0 toward corroboration). Re-enable post-pilot ONLY with
    # real anti-abuse (device attestation / proof-of-work) via env override.
    ANONYMOUS_INGEST_ENABLED = os.getenv(
        'ANONYMOUS_INGEST_ENABLED', 'false'
    ).lower() in ('1', 'true', 'yes')

    # JWT cookie configuration (httpOnly for XSS protection)
    JWT_TOKEN_LOCATION = ["cookies", "headers"]  # Accept both during migration
    JWT_COOKIE_SECURE = ENVIRONMENT == 'production'  # HTTPS only in prod
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_ACCESS_COOKIE_PATH = '/'

# ── Object storage backend (ADR-0017) ─────────────────────────────────
# Which store issues the media direct-upload presigned URL: 's3' (Hetzner /
# any S3-compatible, incl. MinIO) or 'azure'. Default 'azure' for backward
# compat; the Hetzner deploy sets STORAGE_BACKEND=s3.
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "azure").lower()

# ── Azure / Blob Storage ──────────────────────────────────────────────
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "uploads")
DOWNLOADS_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# ── S3-compatible object storage (Hetzner Object Storage / MinIO, ADR-0017) ──
# Endpoint e.g. https://fsn1.your-objectstorage.com (Hetzner) or your MinIO URL.
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_REGION = os.getenv("S3_REGION", "auto")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
# Optional override for the permanent object URL (e.g. a CDN); when unset the
# object URL is the presigned URL minus its query string.
S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL")
# 'virtual' (bucket.host) or 'path' (host/bucket) addressing.
S3_ADDRESSING_STYLE = os.getenv("S3_ADDRESSING_STYLE", "virtual").lower()
# TTL (minutes) for the short-lived presigned GET URLs handed to readers so a
# private bucket's media can still be displayed (ADR-0017).
MEDIA_READ_URL_TTL_MINUTES = int(os.getenv("MEDIA_READ_URL_TTL_MINUTES", "60"))

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
