"""
app/story/routes.py

Source-agnostic story read endpoints:

  GET /api/stories                         — paged list, all sources
  GET /api/stories/map                     — slim geolocated markers for map
  GET /api/stories/<source_type>/<id>      — single story detail
"""

from datetime import datetime, timezone
import logging
import os
import shutil
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dateutil import parser as dateutil_parser
from werkzeug.utils import secure_filename

from app.utils.rate_limit import per_user_or_ip_key
from app.models import db, FileUpload, FileType
from app.utils.azure_blob import upload_file_to_azure_storage
from app.file_upload.media_sanitizer import sanitize_for_upload, safe_remove
from app.file_upload.analysis_service import start_analysis_thread
from .service import list_stories, list_story_markers, get_story, get_facets, ingest_story

logger = logging.getLogger(__name__)

story_bp = Blueprint('story', __name__, url_prefix='/api/stories')

# Per-user/IP throttle on submission and SAS-token endpoints. Read paths
# (list, markers, facets, detail) are not rate-limited at the app layer —
# fronting infrastructure handles that.
limiter = Limiter(key_func=per_user_or_ip_key, storage_uri='memory://')

# Anonymous submission needs a stricter, IP-only limiter — there is no
# JWT identity to scope by, and a single hostile IP could otherwise
# flood the moderation queue.
anon_limiter = Limiter(key_func=get_remote_address, storage_uri='memory://')

# Max accepted size for an anonymous media attachment. Keeps individual
# abuse cheap; multi-file flooding is bounded by the per-IP rate limit.
_ANON_MAX_MEDIA_BYTES = 50 * 1024 * 1024


def _should_use_azure() -> bool:
    """Mirror of file_upload.routes _should_use_azure — keeps anon ingest
    consistent with the authed pipeline without coupling the modules."""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env != 'production':
        return False
    conn = os.getenv('AZURE_STORAGE_CONNECTION_STRING') or ''
    account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME') or ''
    if not conn or not account or conn.startswith('your_') or '...' in conn:
        return False
    conn_l = conn.lower()
    return 'accountname=' in conn_l and 'defaultendpointsprotocol=' in conn_l

_VALID_SOURCES = {'all', 'upload'}
_VALID_SORTS = {'published_at', 'confidence', 'severity'}
_VALID_ORDERS = {'desc', 'asc'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value):
    if not value:
        return None
    try:
        dt = dateutil_parser.isoparse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, OverflowError):
        return None


def _parse_bool(value):
    if value is None:
        return None
    return str(value).lower() in ('1', 'true', 'yes')


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@story_bp.route('', methods=['GET'])
def stories_list():
    """
    Paged list of stories from one or more sources.

    Query params:
      source=all|upload
      q=<text>
      city=<city>
      country=<country>
      severity=HIGH|MEDIUM|LOW
      has_location=true|false
      has_media=true|false
      from=<ISO8601>
      to=<ISO8601>
      sort=published_at|confidence|severity
      order=desc|asc
      limit=<int>   (max 500)
      offset=<int>
    """
    source = request.args.get('source', 'all')
    if source not in _VALID_SOURCES:
        return jsonify({'error': f'source must be one of {sorted(_VALID_SOURCES)}'}), 400

    sort = request.args.get('sort', 'published_at')
    if sort not in _VALID_SORTS:
        sort = 'published_at'

    order = request.args.get('order', 'desc')
    if order not in _VALID_ORDERS:
        order = 'desc'

    result = list_stories(
        source=source,
        q=request.args.get('q'),
        city=request.args.get('city'),
        country=request.args.get('country'),
        severity=request.args.get('severity'),
        has_location=_parse_bool(request.args.get('has_location')),
        has_media=_parse_bool(request.args.get('has_media')),
        from_date=_parse_date(request.args.get('from')),
        to_date=_parse_date(request.args.get('to')),
        sort=sort,
        order=order,
        limit=min(request.args.get('limit', default=50, type=int), 500),
        offset=max(request.args.get('offset', default=0, type=int), 0),
    )

    result['filters'] = {
        'source': source,
        'q': request.args.get('q'),
        'city': request.args.get('city'),
        'country': request.args.get('country'),
        'severity': request.args.get('severity'),
    }

    return jsonify(result), 200


# Allowed extensions for field-reporter media uploads
_ALLOWED_MEDIA_EXTS = {
    'jpg', 'jpeg', 'png', 'webp',           # images
    'mp4', 'mov', 'avi', 'webm', 'mpeg',    # video
    'mp3', 'aac', 'ogg', 'm4a',             # audio
}


@story_bp.route('/ingest/media-token', methods=['GET'])
@limiter.limit('100 per hour; 500 per day')
@jwt_required()
def stories_ingest_media_token():
    """
    Issue a short-lived Azure SAS token so a mobile client can upload a
    media file directly to Blob Storage without proxying through the server.

    Query params
    ------------
    ext : str  — file extension WITHOUT the dot (e.g. 'mp4', 'jpg'). Required.

    Response 200
    ------------
    {
      "upload_url"  : "<SAS URL — HTTP PUT the file here>",
      "blob_url"    : "<permanent public URL of the blob>",
      "blob_name"   : "<blob path>",
      "expires_at"  : "<ISO-8601>"
    }

    The Android app should:
      1. GET this endpoint → receive upload_url + blob_url
      2. PUT the file bytes to upload_url (no auth headers — SAS handles it)
      3. POST /api/stories/ingest with blob_url as media_url
    """
    import uuid
    from modules.azure_handler import generate_sas_upload_url

    ext = (request.args.get('ext') or '').lstrip('.').lower()
    if not ext:
        return jsonify({'error': 'ext query parameter is required'}), 400
    if ext not in _ALLOWED_MEDIA_EXTS:
        return jsonify({'error': f'unsupported extension: {ext}'}), 422

    user_id = get_jwt_identity()
    blob_name = f"field-reports/{user_id}/{uuid.uuid4().hex}.{ext}"

    try:
        token_info = generate_sas_upload_url(blob_name, expiry_minutes=15)
    except RuntimeError as exc:
        logger.error("SAS token generation failed: %s", exc)
        return jsonify({'error': 'Media upload not available', 'detail': str(exc)}), 503

    return jsonify(token_info), 200


@story_bp.route('/ingest', methods=['POST'])
@limiter.limit('30 per hour; 100 per day')
@jwt_required()
def stories_ingest():
    """
    Submit a story from a mobile/API client without a file upload.

    Accepts JSON. Required: title.
    Optional: body, tags (str|list), subject, city, country, lat, lon,
              severity (LOW|MEDIUM|HIGH), media_url, source_name, published_at.

    Returns the created Story (normalized shape) with status 201.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'JSON body required'}), 400

    user_id = get_jwt_identity()
    try:
        story = ingest_story(user_id, payload)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        logger.exception("ingest error")
        return jsonify({'error': 'Ingest failed', 'detail': str(exc)}), 500

    return jsonify(story), 201


@story_bp.route('/anonymous-ingest', methods=['POST'])
@anon_limiter.limit('5 per hour; 20 per day')
def stories_anonymous_ingest():
    """Accept a citizen submission without requiring an account.

    For reporters in regions where account creation is itself a risk.
    Anonymous submissions:
      • Are accepted without JWT (rate-limited by IP — 5/h, 20/day).
      • Always land as PENDING and must pass moderation before publication.
      • Cannot be edited or deleted later — anonymity is irrevocable.
      • Accept a single optional media file (≤ 50 MB) which is sanitized
        through the same EXIF/GPS-strip pipeline as authed uploads.

    Accepts multipart/form-data:
      title        required, string ≤ 100
      body         optional, free text
      city/country optional, ≤ 100
      lat/lon      optional, floats
      severity     optional, LOW|MEDIUM|HIGH (default LOW)
      tags         optional, comma-separated
      subject      optional, ≤ 255
      media        optional, file
    Returns 201 with an opaque ack — no IDs that could later be used to
    correlate or enumerate.
    """
    title = (request.form.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title is required'}), 400
    title = title[:100]

    # Idempotency: if the client sends the same submission_id again
    # (network retry, offline-then-online drain) we return the same
    # opaque ack without creating a second row. Keeps the moderation
    # queue free of duplicates without ever exposing an id to the caller.
    submission_id = (request.form.get('submission_id') or '').strip()[:64] or None
    if submission_id:
        existing = FileUpload.query.filter_by(anon_submission_id=submission_id).first()
        if existing:
            return jsonify({'status': 'received', 'pending_review': True}), 200

    body = (request.form.get('body') or '').strip() or None
    city = (request.form.get('city') or '').strip()[:100] or None
    country = (request.form.get('country') or '').strip()[:100] or None
    subject = (request.form.get('subject') or '').strip()[:255] or None
    tags = (request.form.get('tags') or '').strip()[:255] or None

    severity = (request.form.get('severity') or 'LOW').upper()
    if severity not in ('LOW', 'MEDIUM', 'HIGH'):
        severity = 'LOW'

    try:
        lat = float(request.form['lat']) if request.form.get('lat') else None
        lon = float(request.form['lon']) if request.form.get('lon') else None
    except (TypeError, ValueError):
        lat = lon = None

    media_file = request.files.get('media')
    blob_url = None
    analysis_source_path = None
    file_type = None

    if media_file and media_file.filename:
        original_name = media_file.filename
        ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
        if not ext or len(ext) > 6:
            return jsonify({'error': 'media file must have a recognizable extension'}), 400

        # Size cap — enforce up front, the Flask MAX_CONTENT_LENGTH is a
        # backstop but this surfaces a clear 413 to the client.
        media_file.stream.seek(0, os.SEEK_END)
        size = media_file.stream.tell()
        media_file.stream.seek(0)
        if size > _ANON_MAX_MEDIA_BYTES:
            return jsonify({'error': 'media file exceeds 50 MB limit'}), 413

        # Lookup or fall back to 'Other' file type so the row is valid.
        ft = (
            FileType.query
            .filter(FileType.allowed_extensions.ilike(f'%{ext}%'))
            .first()
        )
        if not ft:
            ft = FileType.query.filter_by(type_name='Other').first()
            if not ft:
                ft = FileType(type_name='Other', allowed_extensions='*')
                db.session.add(ft)
                db.session.flush()
        file_type = ft

        # Anonymous blob naming: no user_id in the path, just a uuid.
        # Path prefix segregates anonymous content for audit.
        unique_filename = f"anonymous/{uuid.uuid4().hex}.{ext}"
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        anon_dir = os.path.join(upload_folder, 'anonymous')
        os.makedirs(anon_dir, exist_ok=True)
        local_path = os.path.join(anon_dir, os.path.basename(unique_filename))
        media_file.save(local_path)

        # Same sanitize → upload pipeline as the authed endpoints.
        analysis_source_path = local_path + '.raw-for-analysis'
        try:
            shutil.copy2(local_path, analysis_source_path)
        except OSError as exc:
            current_app.logger.warning("anon raw analysis copy: %s", exc)
            analysis_source_path = local_path

        sanitized_path = sanitize_for_upload(local_path)
        if sanitized_path != local_path:
            try:
                os.replace(sanitized_path, local_path)
            except OSError as exc:
                current_app.logger.error("anon sanitized replace failed: %s", exc)
                safe_remove(sanitized_path)

        blob_url = f"/api/uploads/{unique_filename}"
        if _should_use_azure():
            try:
                container_name = current_app.config.get('AZURE_BLOB_CONTAINER', 'uploads')
                storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
                upload_file_to_azure_storage(local_path, unique_filename, container_name)
                blob_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{unique_filename}"
                safe_remove(local_path)
            except Exception as exc:
                current_app.logger.warning("anon Azure upload failed; using local fallback: %s", exc)
    else:
        # Text-only anonymous submission — still needs a FileType FK.
        file_type = FileType.query.filter_by(type_name='Other').first()
        if not file_type:
            file_type = FileType(type_name='Other', allowed_extensions='*')
            db.session.add(file_type)
            db.session.flush()

    record = FileUpload(
        filename=(media_file.filename[:255] if media_file and media_file.filename else f'anon-{uuid.uuid4().hex[:12]}'),
        file_path=blob_url or 'anonymous:no-media',
        anon_submission_id=submission_id,
        title=title,
        tags=tags,
        subject=subject,
        city=city,
        country=country,
        lat=lat,
        lon=lon,
        upload_date=datetime.now(timezone.utc),
        user_id=None,
        file_type_id=file_type.filetypeid,
        witness_statement=body,
        source_type='anonymous',
        severity=severity,
        verification_status='PENDING',
        analysis_status='PENDING' if analysis_source_path else 'SKIPPED',
    )
    try:
        db.session.add(record)
        db.session.flush()
        # Anonymous reports still cluster into Events (they corroborate as
        # supporting context, but count 0 toward the distinct-identity total).
        # The rung gate keeps anonymous (rung 0) reports pre-moderated.
        from app.events.service import process_new_report
        process_new_report(record)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("anonymous ingest commit failed")
        return jsonify({'error': 'Submission failed'}), 500

    if analysis_source_path:
        start_analysis_thread(record.id, analysis_source_path)

    # Opaque acknowledgement — no IDs returned. Anonymous means the
    # submitter has no handle to come back with.
    return jsonify({'status': 'received', 'pending_review': True}), 201


@story_bp.route('/facets', methods=['GET'])
def stories_facets():
    """
    Return distinct filter values for the frontend filter panel.

    Response:
    {
      "cities": [...],
      "countries": [...],
      "severities": [...],
      "sources": [...]
    }
    """
    return jsonify(get_facets()), 200


@story_bp.route('/map', methods=['GET'])
def stories_map():
    """
    Slim geolocated story markers for map rendering.

    Query params: source, q, city, country, severity, from, to, limit
    """
    source = request.args.get('source', 'all')
    if source not in _VALID_SOURCES:
        source = 'all'

    markers = list_story_markers(
        source=source,
        q=request.args.get('q'),
        city=request.args.get('city'),
        country=request.args.get('country'),
        severity=request.args.get('severity'),
        from_date=_parse_date(request.args.get('from')),
        to_date=_parse_date(request.args.get('to')),
        limit=min(request.args.get('limit', default=500, type=int), 2000),
    )
    return jsonify(markers), 200


@story_bp.route('/<string:source_type>/<int:source_record_id>', methods=['GET'])
def story_detail(source_type, source_record_id):
    """
    Single story detail by source type and record ID.

    Examples:
      GET /api/stories/upload/42
    """
    if source_type != 'upload':
        return jsonify({'error': 'source_type must be "upload"'}), 400

    story = get_story(source_type, source_record_id)
    if not story:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(story), 200
