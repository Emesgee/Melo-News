# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flasgger import Swagger
import os
from datetime import timedelta
from .models import db, InputTemplate, OutputTemplate, FileType
from .auth.routes import auth_bp
from .profile.routes import profile_bp
from .file_upload.routes import file_upload_bp
from .file_types.routes import file_types_bp
from .templates.routes import templates_bp
from .search.routes import search_bp
from .output.routes import output_bp

def create_app():
    app = Flask(__name__)
    app.config['DEBUG'] = True

    # CORS Configuration
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True,
    methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"])
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'supersecretkey')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']

    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost:5432/postgres'
     #Defining multiple databases with SQLALCHEMY_BINDS configuration
    app.config['SQLALCHEMY_BINDS'] = {
    'default': 'postgresql://postgres:admin@localhost:5432/postgres',
    'secondary': 'postgresql://postgres:admin@localhost:5432/telegramdb'
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
   


    # JWT Manager
    jwt = JWTManager(app)

    # Set up directories for file uploads and exports
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['EXPORT_DIR'] = EXPORT_DIR

    # Initialize the database and migration
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register Blueprints for various modules with /api prefix where needed
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(file_upload_bp)
    app.register_blueprint(file_types_bp)
    app.register_blueprint(templates_bp, url_prefix='/api')
    # Register the blueprint with the /api prefix
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(output_bp)

    # Swagger Configuration
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
        "swagger_ui_config": {
            "defaultModelsExpandDepth": -1
        },
        "consumes": ["application/json"],
        "produces": ["application/json"]
    }
    swagger = Swagger(app, config=swagger_config)

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Server error"}), 500

    # Populate initial data for templates and file types if needed
    with app.app_context():
        db.create_all()
        populate_input_templates()
        populate_output_templates()
        populate_file_types()

    # Print registered routes for debugging
    for rule in app.url_map.iter_rules():
        print(f"Endpoint: {rule.endpoint}, Route: {rule}")

    return app

# Functions to populate initial data for InputTemplate, OutputTemplate, and FileType tables
def populate_file_types():
    if not FileType.query.first():
        templates = [
            FileType(type_name="Audio", allowed_extensions="m4a, mp3, wav"),
            FileType(type_name="Image", allowed_extensions="jpg, png, jpeg"),
            FileType(type_name="Video", allowed_extensions="mp4, avi, mpeg"),
            FileType(type_name="Documents", allowed_extensions="docx, pdf, ppt"),
            FileType(type_name="Data Files", allowed_extensions="csv")
        ]
        db.session.bulk_save_objects(templates)
        db.session.commit()

def populate_input_templates():
    if not InputTemplate.query.first():
        templates = [
            InputTemplate(template_type="Keyword Search", template_description="Searches by title, tags, or subject keywords"),
            InputTemplate(template_type="Date Range Search", template_description="Filters files by a specific date range"),
            InputTemplate(template_type="Location-Based Search", template_description="Filters files by city, country, latitude, and longitude"),
            InputTemplate(template_type="Tag and Date Search", template_description="Searches by image tags within a specific date range"),
            InputTemplate(template_type="Advanced Search", template_description="Comprehensive search using keywords, tags, date, and location filters")
        ]
        db.session.bulk_save_objects(templates)
        db.session.commit()

def populate_output_templates():
    if not OutputTemplate.query.first():
        templates = [
            OutputTemplate(template_type="Summary View", description="Shows key details only"),
            OutputTemplate(template_type="Detailed View", description="Shows all metadata"),
            OutputTemplate(template_type="Location Map View", description="Shows location data for mapping"),
            OutputTemplate(template_type="CSV Export", description="Exports data in CSV format")
        ]
        db.session.bulk_save_objects(templates)
        db.session.commit()
