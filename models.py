# app/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# User model
class User(db.Model):
    __tablename__ = 'users'
    
    userid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploads = db.relationship('FileUpload', backref='user', lazy=True)
    searches = db.relationship('Search', backref='user', lazy=True)


# FileUpload model
class FileUpload(db.Model):
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(100))
    tags = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    file_type_id = db.Column(db.Integer, db.ForeignKey('file_types.filetypeid'), nullable=False)


# FileType model
class FileType(db.Model):
    __tablename__ = 'file_types'
    
    filetypeid = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), nullable=False)
    allowed_extensions = db.Column(db.String(100), nullable=False)
    
    # Relationships
    files = db.relationship('FileUpload', backref='file_type', lazy=True)


# Input model
class Input(db.Model):
    __tablename__ = 'inputs'
    
    inputid = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(255), nullable=False)
    filters = db.Column(db.JSON, nullable=True)
    date_input = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    searchid = db.Column(db.Integer, db.ForeignKey('searches.searchid'), nullable=False)
    templateid = db.Column(db.Integer, db.ForeignKey('input_templates.templateid'), nullable=False)


# Search model
class Search(db.Model):
    __tablename__ = 'searches'
    
    searchid = db.Column(db.Integer, primary_key=True)
    date_searched = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    templateid = db.Column(db.Integer, db.ForeignKey('input_templates.templateid'), nullable=True)
    
    # Relationships
    inputs = db.relationship('Input', backref='search', lazy=True)


# InputTemplate model
class InputTemplate(db.Model):
    __tablename__ = 'input_templates'
    
    templateid = db.Column(db.Integer, primary_key=True)
    template_type = db.Column(db.String(50), nullable=False)
    template_description = db.Column(db.String(255))


# OutputTemplate model
class OutputTemplate(db.Model):
    __tablename__ = 'output_templates'
    
    templateid = db.Column(db.Integer, primary_key=True)
    template_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))


# Output model
class Output(db.Model):
    __tablename__ = 'outputs'
    
    outputid = db.Column(db.Integer, primary_key=True)
    date_generated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    searchid = db.Column(db.Integer, db.ForeignKey('searches.searchid'), nullable=False)
    filetypeid = db.Column(db.Integer, db.ForeignKey('file_types.filetypeid'), nullable=True)
    templateid = db.Column(db.Integer, db.ForeignKey('output_templates.templateid'), nullable=False)

class TestJson(db.Model):
    __bind_key__ = 'secondary'  # Bind to the secondary database
    __tablename__ = 'testjson'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime)
    total_views = db.Column(db.Integer)
    message = db.Column(db.String(255))  # Specify a max length for the string
    video_links = db.Column(db.String(255))
    video_durations = db.Column(db.String(255))
    image_links = db.Column(db.String(255))
    tags = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    matched_city = db.Column(db.String(255))
    city_result = db.Column(db.String(255))
    latitude = db.Column(db.Float)



