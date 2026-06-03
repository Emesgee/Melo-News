import logging
import os
import json
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from .models import db, InputTemplate, OutputTemplate, FileType

logger = logging.getLogger(__name__)

# Initialize SocketIO globally
socketio = SocketIO(
    cors_allowed_origins=["https://app.melonews.tech", "http://localhost:3000", "http://localhost:3001"],
    async_mode="threading",
)

def create_app(config_name=None):
    """
    Create and configure Flask application
    
    Args:
        config_name: 'development', 'production', or 'testing' (auto-detected if not provided)
    """
    app = Flask(__name__)
    
    # Auto-detect environment from ENVIRONMENT variable if not provided
    if config_name is None:
        env = os.getenv('ENVIRONMENT', 'development').lower()
        config_name = 'production' if env == 'production' else 'development'
    
    # Use the Config class from config.py
    from config import Config
    app.config.from_object(Config)
    
    # Override for testing
    if config_name == 'testing':
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['JWT_SECRET_KEY'] = 'test-secret-key-at-least-32-bytes-long!'
        # In tests we hit endpoints with Bearer tokens; the CSRF check that
        # guards cookie-based auth blocks those POSTs even when a header
        # token is present, because login also sets the cookie. Off in
        # testing only — production keeps full CSRF protection.
        app.config['JWT_COOKIE_CSRF_PROTECT'] = False

    # CORS Configuration restricted to known frontends (wildcard is invalid with credentials)
    CORS(
        app,
        resources={r"/*": {"origins": ["https://app.melonews.tech", "http://localhost:3000", "http://localhost:3001"]}},
        supports_credentials=True,
        methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Log database URI for debugging (masked)
    logger.info("Environment: %s", config_name)
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
        masked_uri = db_uri.split('://')[0] + '://***:***@' + db_uri.split('@')[-1]
        logger.info("Connected to database: %s", masked_uri)
    else:
        logger.error("SQLALCHEMY_DATABASE_URI is not set in config!")
    # SQLAlchemy engine options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 280
    }

    # Set max upload size to 100MB
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

    # Allow routes to work with or without trailing slashes
    app.url_map.strict_slashes = False

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)
    socketio.init_app(app)

    # Directories for uploads and exports
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['EXPORT_DIR'] = EXPORT_DIR

    # Register Blueprints
    try:
        from .auth.routes import auth_bp
        from .profile.routes import profile_bp
        from .file_upload.routes import file_upload_bp
        from .file_types.routes import file_types_bp
        from .templates.routes import templates_bp
        from .search.routes import search_bp
        from .output.routes import output_bp
        from .ai_analyzer.routes import ai_analyzer_bp
        from .story.routes import story_bp
        from .moderation.routes import moderation_bp

        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(profile_bp, url_prefix='/api/profile')
        app.register_blueprint(file_upload_bp)
        app.register_blueprint(file_types_bp)
        app.register_blueprint(templates_bp, url_prefix='/api')
        app.register_blueprint(search_bp, url_prefix='/api')
        app.register_blueprint(output_bp)
        app.register_blueprint(ai_analyzer_bp, url_prefix='/api/ai')
        app.register_blueprint(story_bp)
        app.register_blueprint(moderation_bp)

        # Flask-Limiter decorators only enforce limits across requests
        # when the limiter is bound to the app. Each route module exposes
        # its limiter at module scope; bind them all here so rate limits
        # actually take effect at request time.
        from .auth.routes import limiter as auth_limiter
        from .file_upload.routes import limiter as file_upload_limiter
        from .story.routes import limiter as story_limiter, anon_limiter
        for _lim in (auth_limiter, file_upload_limiter, story_limiter, anon_limiter):
            try:
                _lim.init_app(app)
            except Exception as _le:
                logger.warning("limiter init_app failed: %s", _le)

        logger.info("All blueprints registered successfully")
    except ImportError as e:
        logger.warning("Could not import blueprints: %s", e)
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'environment': config_name
        })

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Server error"}), 500

    # Initialize Database and Populate Data (skip for testing)
    # NOTE: In production, use `flask db upgrade` (Alembic migrations) instead of db.create_all().
    # db.create_all() is kept here as a fallback for dev environments without migrations.
    if config_name != 'testing':
        with app.app_context():
            try:
                logger.info("Initializing database tables...")
                db.create_all()
                logger.info("Populating initial data...")
                populate_initial_data()
                logger.info("Initial data populated successfully.")
            except SQLAlchemyError as e:
                logger.error("Database error during initialization: %s", e)
                db.session.rollback()
            except Exception as e:
                logger.error("Unexpected error during initialization: %s", e)
            finally:
                db.session.close()

    # Ensure proper session cleanup at the end of each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            logger.error("Exception during request: %s", exception)
            db.session.rollback()
        db.session.remove()

    return app

# Populate Initial Data
def populate_initial_data():
    """Populate database with initial data"""
    try:
        ensure_schema_compatibility()
        populate_file_types()
        populate_input_templates()
        populate_output_templates()
    except Exception as e:
        logger.error("Failed to populate initial data: %s", e)


def ensure_schema_compatibility():
    """Backfill columns that exist in models but may be missing in legacy databases."""
    try:
        dialect = db.engine.dialect.name
        if dialect == 'postgresql':
            file_uploads_q = text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'file_uploads'"
            )
            users_q = text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
            )
        elif dialect == 'sqlite':
            file_uploads_q = text("PRAGMA table_info(file_uploads)")
            users_q = text("PRAGMA table_info(users)")
        else:
            logger.warning("Unsupported database dialect: %s", dialect)
            return

        def _cols(rows):
            return {row[0] if dialect == 'postgresql' else row[1] for row in rows}

        file_upload_cols = _cols(db.session.execute(file_uploads_q).fetchall())
        user_cols = _cols(db.session.execute(users_q).fetchall())

        # Keep this list minimal and explicit for safe startup compatibility.
        # `verification_status` uses DEFAULT 'VERIFIED' for the ALTER so
        # existing rows are grandfathered — the public feed shouldn't go
        # dark on deploy. New rows go through the ORM and get the model's
        # 'PENDING' default instead.
        required_file_upload_columns = {
            'transcription': 'TEXT',
            'confidence_score': 'DOUBLE PRECISION DEFAULT 0.0' if dialect == 'postgresql' else 'REAL DEFAULT 0.0',
            'severity': "VARCHAR(20) DEFAULT 'LOW'",
            'exif_data': 'JSONB' if dialect == 'postgresql' else 'TEXT',
            'analysis_status': "VARCHAR(20) DEFAULT 'PENDING'",
            'verification_status': "VARCHAR(20) DEFAULT 'VERIFIED' NOT NULL",
            'verification_note': 'TEXT',
            'verified_at': 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME',
            'verified_by': 'INTEGER',
            # Idempotency key from Android local queue. UNIQUE inline so a
            # duplicate relay can be caught at insert time even before a
            # supporting index exists.
            'local_id': 'VARCHAR(64) UNIQUE',
            # Idempotency key for anonymous offline drafts — separate from
            # local_id so the authed-flow uniqueness is not muddied. Lets
            # the same offline draft be safely re-submitted across retries.
            'anon_submission_id': 'VARCHAR(64) UNIQUE',
            # Stage B: Event membership + on-device signature. event_id is a
            # plain INTEGER here (the ORM defines the FK to events.id); the
            # physical FK constraint is omitted on the backfill ALTER, matching
            # verified_by. report_signature is the unsigned/web lane when null.
            'event_id': 'INTEGER',
            'report_signature': 'VARCHAR(256)',
        }
        # Stage B: extend User into the identity + reputation table. `role`
        # replaces the legacy is_moderator boolean (migrated below).
        required_user_columns = {
            'role': "VARCHAR(20) DEFAULT 'reporter' NOT NULL",
            'public_key': 'VARCHAR(128) UNIQUE',
            'display_handle': 'VARCHAR(50)',
            'identity_type': "VARCHAR(20) DEFAULT 'registered' NOT NULL",
            'trust_rung': 'INTEGER DEFAULT 1 NOT NULL',
            'reports_count': 'INTEGER DEFAULT 0 NOT NULL',
            'corroborated_count': 'INTEGER DEFAULT 0 NOT NULL',
            'first_seen_at': 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME',
            'last_active_at': 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME',
        }

        altered = False
        for col_name, col_ddl in required_file_upload_columns.items():
            if col_name not in file_upload_cols:
                db.session.execute(text(f"ALTER TABLE file_uploads ADD COLUMN {col_name} {col_ddl}"))
                altered = True
                logger.info("Added missing column file_uploads.%s", col_name)

        for col_name, col_ddl in required_user_columns.items():
            if col_name not in user_cols:
                db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_ddl}"))
                altered = True
                logger.info("Added missing column users.%s", col_name)

        # Migrate legacy is_moderator → role, only on the run that first adds
        # `role` (so a later manual steward/moderator assignment isn't clobbered
        # on every startup). 'role' not in user_cols == it was just added above.
        if 'role' not in user_cols and 'is_moderator' in user_cols:
            db.session.execute(text(
                "UPDATE users SET role = 'moderator' WHERE is_moderator = "
                + ("TRUE" if dialect == 'postgresql' else "1")
            ))
            altered = True
            logger.info("Backfilled users.role from legacy is_moderator")

        # Drop NOT NULL on email/password/username so a pseudonymous reporter
        # can self-register with only a device keypair + handle (Stage C).
        # PostgreSQL alters in place; SQLite needs a table rebuild (dev only).
        if dialect == 'postgresql':
            for _col in ('email', 'password', 'username'):
                row = db.session.execute(text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'users' AND column_name = :c"
                ), {'c': _col}).fetchone()
                if row and row[0] == 'NO':
                    db.session.execute(text(f"ALTER TABLE users ALTER COLUMN {_col} DROP NOT NULL"))
                    altered = True
                    logger.info("Dropped NOT NULL on users.%s", _col)
        elif dialect == 'sqlite':
            urows = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
            if any(r[1] in ('email', 'password', 'username') and r[3] == 1 for r in urows):
                logger.warning(
                    "users.email/password/username are NOT NULL on this SQLite "
                    "database. Pseudonymous registration requires a manual table "
                    "rebuild — recreate the dev DB or run a custom migration."
                )

        # Drop NOT NULL on file_uploads.user_id so anonymous submissions
        # are allowed. PostgreSQL supports this in place; SQLite needs a
        # table rebuild (only matters in dev — dev DBs are usually wiped).
        if dialect == 'postgresql':
            nullable_row = db.session.execute(text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'file_uploads' AND column_name = 'user_id'"
            )).fetchone()
            if nullable_row and nullable_row[0] == 'NO':
                db.session.execute(text(
                    "ALTER TABLE file_uploads ALTER COLUMN user_id DROP NOT NULL"
                ))
                altered = True
                logger.info("Dropped NOT NULL on file_uploads.user_id (anonymous submissions)")
        elif dialect == 'sqlite':
            # PRAGMA table_info row format: (cid, name, type, notnull, dflt_value, pk)
            rows = db.session.execute(text("PRAGMA table_info(file_uploads)")).fetchall()
            user_id_row = next((r for r in rows if r[1] == 'user_id'), None)
            if user_id_row and user_id_row[3] == 1:
                logger.warning(
                    "file_uploads.user_id is NOT NULL on this SQLite database. "
                    "Anonymous submissions require a manual table rebuild — "
                    "recreate the dev DB or run a custom migration."
                )

        if altered:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("Schema compatibility check failed: %s", e)

def populate_file_types():
    """Populate FileType table"""
    desired_types = {
        "Audio": "m4a, mp3, wav, ogg",
        "Image": "jpg, png, jpeg, gif, webp",
        "Video": "mp4, avi, mpeg, mov, webm, ogv",
        "Documents": "doc, docx, pdf, ppt, pptx, xls, xlsx",
        "Data Files": "csv",
    }

    try:
        existing_types = {ft.type_name: ft for ft in FileType.query.all()}

        for type_name, allowed_extensions in desired_types.items():
            existing = existing_types.get(type_name)
            if existing is None:
                db.session.add(FileType(type_name=type_name, allowed_extensions=allowed_extensions))
            elif existing.allowed_extensions != allowed_extensions:
                existing.allowed_extensions = allowed_extensions

        db.session.commit()
        logger.info("FileTypes synchronized successfully.")
    except SQLAlchemyError as e:
        logger.error("Error populating FileType: %s", e)
        db.session.rollback()

def populate_input_templates():
    """Populate InputTemplate table"""
    if not InputTemplate.query.first():
        templates = [
            InputTemplate(template_type="Keyword Search", template_description="Searches by title, tags, or subject keywords"),
            InputTemplate(template_type="Date Range Search", template_description="Filters files by a specific date range"),
            InputTemplate(template_type="Location-Based Search", template_description="Filters files by city, country, latitude, and longitude"),
            InputTemplate(template_type="Tag and Date Search", template_description="Searches by image tags within a specific date range"),
            InputTemplate(template_type="Advanced Search", template_description="Comprehensive search using keywords, tags, date, and location filters")
        ]
        try:
            db.session.bulk_save_objects(templates)
            db.session.commit()
            logger.info("InputTemplates populated successfully.")
        except SQLAlchemyError as e:
            logger.error("Error populating InputTemplate: %s", e)
            db.session.rollback()

def populate_output_templates():
    """Populate OutputTemplate table"""
    if not OutputTemplate.query.first():
        templates = [
            OutputTemplate(template_type="Summary View", description="Shows key details only"),
            OutputTemplate(template_type="Detailed View", description="Shows all metadata"),
            OutputTemplate(template_type="Location Map View", description="Shows location data for mapping"),
            OutputTemplate(template_type="CSV Export", description="Exports data in CSV format")
        ]
        try:
            db.session.bulk_save_objects(templates)
            db.session.commit()
            logger.info("OutputTemplates populated successfully.")
        except SQLAlchemyError as e:
            logger.error("Error populating OutputTemplate: %s", e)
            db.session.rollback()

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    logger.debug('WebSocket client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.debug('WebSocket client disconnected')

@socketio.on('message')
def handle_message(message):
    logger.debug('WebSocket message received: %s', message)
    socketio.send(f'Echo: {message}')
