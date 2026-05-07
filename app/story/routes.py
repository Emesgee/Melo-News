"""
app/story/routes.py

Source-agnostic story read endpoints:

  GET /api/stories                         — paged list, all sources
  GET /api/stories/map                     — slim geolocated markers for map
  GET /api/stories/<source_type>/<id>      — single story detail
"""

from datetime import timezone
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from dateutil import parser as dateutil_parser

from .service import list_stories, list_story_markers, get_story, get_facets, ingest_story

logger = logging.getLogger(__name__)

story_bp = Blueprint('story', __name__, url_prefix='/api/stories')

_VALID_SOURCES = {'all', 'upload', 'telegram'}
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
      source=all|upload|telegram
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
    Replaces GET /api/telegram/news.

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
      GET /api/stories/telegram/123
      GET /api/stories/upload/42
    """
    if source_type not in ('telegram', 'upload'):
        return jsonify({'error': 'source_type must be "telegram" or "upload"'}), 400

    story = get_story(source_type, source_record_id)
    if not story:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(story), 200
