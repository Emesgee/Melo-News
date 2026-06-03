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
    # email/password/username are nullable: a pseudonymous reporter
    # self-registers via an on-device keypair (Stage C) with only a
    # display_handle and public_key — no email or password exists.
    username = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=True)
    created_date = db.Column(db.DateTime, default=_utcnow)

    # Editorial role — replaces the old is_moderator boolean.
    # reporter   = ordinary identity (default)
    # moderator  = reviews the verification queue / event status
    # steward    = governance role (M-of-N actions); also moderator-capable
    role = db.Column(db.String(20), default='reporter', nullable=False)

    # Pseudonymous identity anchor. The Ed25519 public key IS the pseudonym;
    # it self-registers on the first signed report (Stage C). Null for
    # web email/password accounts.
    public_key = db.Column(db.String(128), unique=True, nullable=True)
    display_handle = db.Column(db.String(50), nullable=True)
    # 'registered' (web email/password) | 'pseudonymous' (device keypair)
    identity_type = db.Column(db.String(20), default='registered', nullable=False)

    # Reputation / trust ladder. trust_rung 1..3 (0 = anonymous, which has
    # no User row). A fresh key earns nothing → starts at rung 1. Only
    # corroborated history + time (or a steward vouch) climbs the ladder.
    trust_rung = db.Column(db.Integer, default=1, nullable=False)
    reports_count = db.Column(db.Integer, default=0, nullable=False)
    corroborated_count = db.Column(db.Integer, default=0, nullable=False)
    first_seen_at = db.Column(db.DateTime, default=_utcnow)
    last_active_at = db.Column(db.DateTime, default=_utcnow)

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

    # Foreign keys — user_id is nullable so reporters in hostile regions
    # can submit without creating an account. Anonymous submissions land
    # as PENDING and are always reviewed by a moderator before going
    # public; the public endpoint is rate-limited per IP.
    user_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)
    file_type_id = db.Column(db.Integer, db.ForeignKey('file_types.filetypeid'), nullable=False)

    # Idempotency key from Android local queue — prevents relay duplicates
    local_id = db.Column(db.String(64), nullable=True, unique=True, index=True)

    # Idempotency key for anonymous offline drafts. Separate column from
    # local_id so the authenticated-flow uniqueness is not muddied by
    # values generated outside an account context. A re-sync of the same
    # anonymous draft after a network blip returns the existing row
    # instead of creating a duplicate in the moderation queue.
    anon_submission_id = db.Column(db.String(64), nullable=True, unique=True, index=True)

    # Event membership — every report belongs to exactly one Event; a new
    # report auto-creates a singleton Event of one (Stage D). Nullable here
    # so existing rows can be backfilled lazily.
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True, index=True)

    # Ed25519 signature over the report payload, produced on-device (Stage C).
    # Null for web submissions and anonymous reports (the unsigned lane).
    report_signature = db.Column(db.String(256), nullable=True)


# Event (Incident) model — the primary reader-facing unit. Reports cluster
# into Events (geo+time, Stage D); corroboration = an Event accumulating
# members from DISTINCT identities. Status is a derived function of its
# members + verifications + sticky moderator overrides (Stage D/E).
class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)

    # Reader-facing display + map placement (centroid of members,
    # populated by aggregation in Stage D/E).
    title = db.Column(db.String(200))
    summary = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)

    # Derived status: DEVELOPING | CORROBORATED | DISPUTED | CLOSED.
    status = db.Column(db.String(20), default='DEVELOPING', nullable=False, index=True)
    # Sticky moderator override that pins status against the derived value.
    status_override = db.Column(db.String(20), nullable=True)

    # corroboration_count = COUNT(DISTINCT user_id) over VERIFIED members
    # with user_id NOT NULL (anonymous members count 0 toward the threshold).
    corroboration_count = db.Column(db.Integer, default=0, nullable=False)
    dispute_count = db.Column(db.Integer, default=0, nullable=False)

    # Aggregated metrics (confidence is shown to readers as a band, not raw).
    severity = db.Column(db.String(20), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)

    # Moderation / audit
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    members = db.relationship(
        'FileUpload',
        backref='event',
        lazy=True,
        foreign_keys='FileUpload.event_id',
    )


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



