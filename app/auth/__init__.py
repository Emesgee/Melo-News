# app/__init__.py
from flask import Flask
from flask_jwt_extended import JWTManager
from ..models import db
from app.auth.routes import auth_bp
from app.profile.routes import profile_bp
from app.file_upload.routes import file_upload_bp
from app.file_types.routes import file_types_bp
from app.templates.routes import templates_bp
from app.search.routes import search_bp
from app.output.routes import output_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    JWTManager(app)

    # Blueprint registrations in create_app()
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(file_upload_bp)
    app.register_blueprint(file_types_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(output_bp)
   


    return app
