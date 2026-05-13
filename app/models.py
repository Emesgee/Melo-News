# app/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

def _utcnow():
    """Timezone-aware UTC now (replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)

# User model
class User(db.Model):
    __tablename__ = 'users'

    userid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_date = db.Column(db.DateTime, default=_utcnow)

    # Editorial role — moderators see and decide on the verification queue
    # for citizen-submitted stories before they go to the public feed.
    is_moderator = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    uploads = db.relationship(
        'FileUpload',
        foreign_keys='FileUpload.user_id',
        backref='user',
        lazy=True,
    )
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
    upload_date = db.Column(db.DateTime, default=_utcnow, index=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    
    # Analysis Fields (Citizen Journalism)
    transcription = db.Column(db.Text)
    confidence_score = db.Column(db.Float, default=0.0)
    severity = db.Column(db.String(20), default='LOW')
    exif_data = db.Column(JSON)
    analysis_status = db.Column(db.String(20), default='PENDING')

    # Citizen journalism provenance
    witness_statement = db.Column(db.Text)
    source_type = db.Column(db.String(30), default='eyewitness')  # eyewitness|secondhand|official|unknown
    is_sensitive = db.Column(db.Boolean, default=False)  # flagged for editorial review

    # Editorial moderation — citizen submissions stay PENDING until a
    # moderator reviews them, so unverified content never reaches the
    # public feed. Existing rows are grandfathered to VERIFIED by
    # ensure_schema_compatibility so live deployments don't go dark.
    verification_status = db.Column(
        db.String(20), default='PENDING', nullable=False, index=True,
    )
    verification_note = db.Column(db.Text)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    file_type_id = db.Column(db.Integer, db.ForeignKey('file_types.filetypeid'), nullable=False)

    # Idempotency key from Android local queue — prevents relay duplicates
    local_id = db.Column(db.String(64), nullable=True, unique=True, index=True)


# FileType model
class FileType(db.Model):
    __tablename__ = 'file_types'
    
    filetypeid = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), nullable=False)
    allowed_extensions = db.Column(db.String(100), nullable=False)
    
    # Relationships
    files = db.relationship('FileUpload', backref='file_type', lazy=True)


# Input model
class Input(db.Model):
    __tablename__ = 'inputs'
    
    inputid = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(255), nullable=False)
    filters = db.Column(db.JSON, nullable=True)
    date_input = db.Column(db.DateTime, default=_utcnow)
    
    # Foreign keys
    searchid = db.Column(db.Integer, db.ForeignKey('searches.searchid'), nullable=False)
    templateid = db.Column(db.Integer, db.ForeignKey('input_templates.templateid'), nullable=False)


# Search model
class Search(db.Model):
    __tablename__ = 'searches'
    
    searchid = db.Column(db.Integer, primary_key=True)
    date_searched = db.Column(db.DateTime, default=_utcnow)
    
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
    date_generated = db.Column(db.DateTime, default=_utcnow)
    
    # Foreign keys
    searchid = db.Column(db.Integer, db.ForeignKey('searches.searchid'), nullable=False)
    filetypeid = db.Column(db.Integer, db.ForeignKey('file_types.filetypeid'), nullable=True)
    templateid = db.Column(db.Integer, db.ForeignKey('output_templates.templateid'), nullable=False)


class Telegram(db.Model):
    __tablename__ = 'telegram'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, index=True)
    total_views = db.Column(db.Integer)
    message = db.Column(db.Text)
    video_links = db.Column(JSON)  # store as list of URLs
    image_links = db.Column(db.Text)
    tags = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    matched_city = db.Column(db.String(255), index=True)
    city_result = db.Column(db.String(255))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    
    # New fields from Conflictly benchmark
    confidence_score = db.Column(db.Float, default=0.0)       # 0.0-1.0 AI credibility score
    severity = db.Column(db.String(10), default='MEDIUM', index=True)  # HIGH / MEDIUM / LOW
    source = db.Column(db.String(50), default='telegram')     # telegram / rss / twitter / reddit
    source_count = db.Column(db.Integer, default=1)           # cross-reference count
    escalation = db.Column(db.String(15), nullable=True)      # escalation / de-escalation / stable


class Prediction(db.Model):
    """Community prediction polls (P2-9)"""
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), default='general')  # military, political, humanitarian
    created_at = db.Column(db.DateTime, default=_utcnow)
    closes_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)

    votes = db.relationship('PredictionVote', backref='prediction', lazy=True)


class PredictionVote(db.Model):
    """Votes on prediction polls (P2-9)"""
    __tablename__ = 'prediction_votes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    vote = db.Column(db.String(10), nullable=False)  # 'yes' or 'no'
    voted_at = db.Column(db.DateTime, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint('prediction_id', 'user_id', name='unique_user_prediction_vote'),
    )


class KeywordTrend(db.Model):
    """Time-bucketed keyword counts for trending (P1-5)"""
    __tablename__ = 'keyword_trends'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    keyword = db.Column(db.String(100), nullable=False, index=True)
    count = db.Column(db.Integer, default=1)
    bucket_time = db.Column(db.DateTime, nullable=False, index=True)  # hourly bucket
    
    __table_args__ = (
        db.UniqueConstraint('keyword', 'bucket_time', name='unique_keyword_bucket'),
    )


class TensionIndex(db.Model):
    """Global tension index snapshots (P1-6)"""
    __tablename__ = 'tension_index'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    score = db.Column(db.Float, nullable=False)  # 0-100
    story_count = db.Column(db.Integer, default=0)
    avg_severity = db.Column(db.Float, default=0.0)
    escalation_pct = db.Column(db.Float, default=0.0)  # % of areas escalating
    calculated_at = db.Column(db.DateTime, default=_utcnow, index=True)
    



