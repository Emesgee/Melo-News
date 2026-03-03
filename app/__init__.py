from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from .models import db, InputTemplate, OutputTemplate, FileType, Telegram

# Initialize SocketIO globally
socketio = SocketIO(cors_allowed_origins="*")

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
        app.config['JWT_SECRET_KEY'] = 'test-secret-key'

    # CORS Configuration
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True,
         methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
         allow_headers=["Content-Type", "Authorization"])

    # Log database URI for debugging (masked)
    print(f"[APP] Environment: {config_name}")
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
        masked_uri = db_uri.split('://')[0] + '://***:***@' + db_uri.split('@')[-1]
        print(f"[APP] Connected to database: {masked_uri}")
    else:
        print("[APP] ERROR: SQLALCHEMY_DATABASE_URI is not set in config!")
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
        from .telegram.routes import telegram_bp
        from .city_history.routes import city_history_bp
        from .city_history.chat_routes import news_chat_bp
        from .summary.summary import summary_bp
        from .ai_analyzer.routes import ai_analyzer_bp

        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(profile_bp, url_prefix='/api/profile')
        app.register_blueprint(file_upload_bp)
        app.register_blueprint(file_types_bp)
        app.register_blueprint(templates_bp, url_prefix='/api')
        app.register_blueprint(search_bp, url_prefix='/api')
        app.register_blueprint(output_bp)
        app.register_blueprint(telegram_bp, url_prefix='/api/telegram')
        app.register_blueprint(city_history_bp)
        app.register_blueprint(news_chat_bp)
        app.register_blueprint(summary_bp)
        app.register_blueprint(ai_analyzer_bp, url_prefix='/api/ai')
        
        print("[APP] All blueprints registered successfully")
    except ImportError as e:
        print(f"[WARNING] Could not import blueprints: {e}")
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
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
    if config_name != 'testing':
        with app.app_context():
            try:
                # Create tables
                print("[APP] Creating database tables...")
                db.create_all()

                # Populate initial data
                print("[APP] Populating initial data...")
                populate_initial_data()
                print("[APP] Initial data populated successfully.")
            except SQLAlchemyError as e:
                print(f"[ERROR] Database error during initialization: {e}")
                db.session.rollback()
            except Exception as e:
                print(f"[ERROR] Unexpected error during initialization: {e}")
            finally:
                db.session.close()

    # Ensure proper session cleanup at the end of each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            print(f"[ERROR] Exception during request: {exception}")
            db.session.rollback()
        db.session.remove()

    return app

# Populate Initial Data
def populate_initial_data():
    """Populate database with initial data"""
    try:
        populate_file_types()
        populate_input_templates()
        populate_output_templates()
    except Exception as e:
        print(f"[ERROR] Failed to populate initial data: {e}")

def populate_file_types():
    """Populate FileType table"""
    if not FileType.query.first():
        templates = [
            FileType(type_name="Audio", allowed_extensions="m4a, mp3, wav"),
            FileType(type_name="Image", allowed_extensions="jpg, png, jpeg, gif"),
            FileType(type_name="Video", allowed_extensions="mp4, avi, mpeg, mov"),
            FileType(type_name="Documents", allowed_extensions="docx, pdf, ppt"),
            FileType(type_name="Data Files", allowed_extensions="csv")
        ]
        try:
            db.session.bulk_save_objects(templates)
            db.session.commit()
            print("[APP] FileTypes populated successfully.")
        except SQLAlchemyError as e:
            print(f"[ERROR] Error populating FileType: {e}")
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
            print("[APP] InputTemplates populated successfully.")
        except SQLAlchemyError as e:
            print(f"[ERROR] Error populating InputTemplate: {e}")
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
            print("[APP] OutputTemplates populated successfully.")
        except SQLAlchemyError as e:
            print(f"[ERROR] Error populating OutputTemplate: {e}")
            db.session.rollback()

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    print('[SOCKET] Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('[SOCKET] Client disconnected')

@socketio.on('message')
def handle_message(message):
    print(f'[SOCKET] Received message: {message}')
    socketio.send(f'Echo: {message}')