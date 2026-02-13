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

def create_app():

    app = Flask(__name__)
    # Use the Config class from config.py
    from config import Config
    app.config.from_object(Config)

    # CORS Configuration
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True,
         methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
         allow_headers=["Content-Type", "Authorization"])

    # Log database URI for debugging
    print(f"Connected to database: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # SQLAlchemy engine options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 280
    }

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

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(profile_bp, url_prefix='/api')
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
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })

    

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Server error"}), 500

    # Initialize Database and Populate Data
    with app.app_context():
        try:
            # Create tables
            print("Creating database tables...")
            db.create_all()

            # Populate initial data
            print("Populating initial data...")
            populate_initial_data()
            print("Initial data populated successfully.")
        except SQLAlchemyError as e:
            print(f"Database error during initialization: {e}")
            db.session.rollback()
        finally:
            db.session.close()

    # Ensure proper session cleanup at the end of each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    return app

# Populate Initial Data
def populate_initial_data():
    populate_file_types()
    populate_input_templates()
    populate_output_templates()

def populate_file_types():
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
            print("FileTypes populated successfully.")
        except SQLAlchemyError as e:
            print(f"Error populating FileType: {e}")
            db.session.rollback()

def populate_input_templates():
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
            print("InputTemplates populated successfully.")
        except SQLAlchemyError as e:
            print(f"Error populating InputTemplate: {e}")
            db.session.rollback()

def populate_output_templates():
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
            print("OutputTemplates populated successfully.")
        except SQLAlchemyError as e:
            print(f"Error populating OutputTemplate: {e}")
            db.session.rollback()

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(message):
    print(f'Received message: {message}')
    socketio.send(f'Echo: {message}')

