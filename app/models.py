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

    # Pseudonymous identity anchor. The device public key IS the pseudonym
    # (ECDSA P-256, AndroidKeyStore — ADR-0013); stored as base64 SPKI DER
    # (~124 chars, fits 128). Self-registers on the first signed report
    # (Stage C). Null for web email/password accounts.
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

    # ECDSA-P256 signature (base64 DER) over the report payload, produced
    # on-device (Stage C, ADR-0013). Null for web/anonymous reports (unsigned
    # lane).
    report_signature = db.Column(db.String(256), nullable=True)

    # The exact canonical signed message (compact sorted-key JSON, ADR-0014)
    # persisted verbatim, so reader-side verification (ADR-0009) can rebuild
    # byte-identical input without re-formatting. Null on the unsigned lane.
    signed_message = db.Column(db.Text, nullable=True)

    # Media fingerprint (lowercase hex SHA-256 of the sanitized bytes) lifted
    # out of the signed_message blob into a first-class, queryable column
    # (ADR-0020 Phase 1: archive-grade + exportable). It is the primitive the
    # fake-independence detector keys on — byte-identical media across many
    # pseudonyms is a reshare/astroturf, not independent corroboration
    # (UC3/UC8). Null when text-only or on the unsigned lane.
    media_sha256 = db.Column(db.String(64), nullable=True, index=True)


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

    # independent_source_count = distinct identities AFTER collapsing
    # byte-identical media (reshares/astroturf) to a single origin (ADR-0020
    # Phase 1, the fake-independence detector). Two people filming the same
    # event produce DIFFERENT hashes -> counted separately; one clip reposted
    # under many keys collapses to one origin. Always <= corroboration_count,
    # so gating promotion on it is strictly more conservative. This is the
    # number the CORROBORATED gate and the reader display should trust.
    independent_source_count = db.Column(db.Integer, default=0, nullable=False)

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


# Durable corroboration-graph snapshot (ADR-0020 Phase 1). An append-only,
# content-addressed capture of an Event's corroboration state at an archival
# moment (e.g. the instant it reached CORROBORATED). The point is
# capture-before-deletion (UC9): the live Event can later mutate or its media be
# taken down, but the snapshot preserves what was corroborated, by whom
# (pseudonymously), and its integrity hash. New table -> created by
# db.create_all(); no ensure_schema_compatibility entry needed.
class EventGraphSnapshot(db.Model):
    __tablename__ = 'event_graph_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    # Emitted-shape version, so an old stored graph can always be interpreted.
    schema_version = db.Column(db.Integer, nullable=False)
    # Content address of the graph (lowercase-hex SHA-256), also the dedup key.
    graph_sha256 = db.Column(db.String(64), nullable=False, index=True)
    # The full canonical graph JSON, verbatim and exportable.
    graph_json = db.Column(db.Text, nullable=False)
    # Effective status + what triggered the capture, for cheap querying.
    status = db.Column(db.String(20), nullable=True)
    reason = db.Column(db.String(40), nullable=True)  # corroborated|disputed|closed|manual
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)


# Append-only audit log of moderator + steward actions. Every verify/reject
# (incl. reversals) and every rung/role change writes one row here, so a decision
# is never silently overwritten -- the FileUpload/User carries the *current*
# state, this table carries the *history* (who did what, when, from what to what,
# and why). Two purposes: a reversal is recorded rather than erased (keeps faith
# with the tamper-evident promise), and stewards get oversight of governance
# actions ("who vouched this pseudonym to rung 2?"). New table -> created by
# db.create_all(); no ensure_schema_compatibility entry needed.
class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    # Who performed the action (a moderator or steward user id). Nullable so a
    # system/script action can be recorded without a human actor.
    actor_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True, index=True)
    # What happened: verify | reject | reverify | set_rung | set_role.
    action = db.Column(db.String(30), nullable=False, index=True)
    # What it was done to: 'upload' (a report) or 'user' (an identity).
    target_type = db.Column(db.String(20), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False, index=True)
    # Prior and new value of the thing that changed (status, rung, role), as
    # short strings -- enough to reconstruct the transition without a join.
    before = db.Column(db.String(40), nullable=True)
    after = db.Column(db.String(40), nullable=True)
    # Free-text reason (required on a reject; optional elsewhere).
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)


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



