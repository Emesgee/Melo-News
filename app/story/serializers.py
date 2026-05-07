"""
app/story/serializers.py

Normalize FileUpload and Telegram records into a common Story dict.
The Story shape is the single contract that all read paths (map, search,
summary, analytics) should consume going forward.
"""

import json
import re

_IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
_VIDEO_EXTS = {'mp4', 'avi', 'mpeg', 'mov', 'webm', 'ogv'}


def normalize_tags(value):
    """Return a clean list of tags regardless of storage format."""
    if not value:
        return []
    if isinstance(value, list):
        return [t.strip() for t in value if str(t).strip()]
    return [t.strip() for t in re.split(r'[,|;]', str(value)) if t.strip()]


def normalize_links(value):
    """Parse image_links / video_links which may be JSON, pipe-delimited, or a list."""
    if not value:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith('['):
            try:
                parsed = json.loads(stripped)
                return [v for v in parsed if v]
            except (json.JSONDecodeError, ValueError):
                pass
        return [v.strip() for v in stripped.split('|') if v.strip()]
    return []


def serialize_upload(upload):
    """Convert a FileUpload ORM record to a normalized Story dict."""
    ext = (upload.filename or '').rsplit('.', 1)[-1].lower()
    images = [upload.file_path] if ext in _IMAGE_EXTS and upload.file_path else []
    videos = [upload.file_path] if ext in _VIDEO_EXTS and upload.file_path else []
    primary_url = upload.file_path

    city = upload.city
    country = upload.country
    label_parts = [p for p in (city, country) if p]

    published = upload.upload_date.isoformat() if upload.upload_date else None

    return {
        'id': f'upload:{upload.id}',
        'source_type': 'upload',
        'source_record_id': upload.id,
        'title': upload.title or upload.filename,
        'body': upload.transcription or upload.subject or upload.title or '',
        'summary': None,
        'tags': normalize_tags(upload.tags),
        'subject': upload.subject,
        'location': {
            'city': city,
            'country': country,
            'lat': upload.lat,
            'lon': upload.lon,
            'label': ', '.join(label_parts) or None,
        },
        'media': {
            'images': images,
            'videos': videos,
            'primary_url': primary_url,
        },
        'metrics': {
            'confidence_score': upload.confidence_score,
            'severity': upload.severity,
            'source_count': 1,
            'total_views': None,
            'escalation': None,
        },
        'workflow': {
            'analysis_status': upload.analysis_status,
            'verification_status': 'unverified',
            'is_sensitive': upload.is_sensitive,
        },
        'provenance': {
            'source_name': 'upload',
            'source_label': 'Citizen Upload',
            'source_type_detail': upload.source_type,
            'witness_statement': upload.witness_statement,
            'author_user_id': upload.user_id,
        },
        'timestamps': {
            'published_at': published,
            'ingested_at': published,
        },
    }


def serialize_telegram(record):
    """Convert a Telegram ORM record to a normalized Story dict."""
    images = normalize_links(record.image_links)
    videos = normalize_links(record.video_links)
    primary_url = (images[0] if images else None) or (videos[0] if videos else None)

    city = record.matched_city
    country = record.city_result
    label_parts = [p for p in (city, country) if p]

    published = record.time.isoformat() if record.time else None

    return {
        'id': f'telegram:{record.id}',
        'source_type': 'telegram',
        'source_record_id': record.id,
        'title': record.subject or record.matched_city or 'Untitled',
        'body': record.message or '',
        'summary': None,
        'tags': normalize_tags(record.tags),
        'subject': record.subject,
        'location': {
            'city': city,
            'country': country,
            'lat': record.lat,
            'lon': record.lon,
            'label': ', '.join(label_parts) or None,
        },
        'media': {
            'images': images,
            'videos': videos,
            'primary_url': primary_url,
        },
        'metrics': {
            'confidence_score': record.confidence_score,
            'severity': record.severity,
            'source_count': record.source_count,
            'total_views': record.total_views,
            'escalation': record.escalation,
        },
        'workflow': {
            'analysis_status': None,
            'verification_status': 'unverified',
            'is_sensitive': False,
        },
        'provenance': {
            'source_name': record.source or 'telegram',
            'source_label': 'Telegram',
            'source_type_detail': record.source or 'telegram',
            'witness_statement': None,
            'author_user_id': None,
        },
        'timestamps': {
            'published_at': published,
            'ingested_at': published,
        },
    }
