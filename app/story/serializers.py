"""
app/story/serializers.py

Normalize citizen FileUpload records into a common Story dict.
The Story shape is the single contract that all read paths (map, search,
summary, analytics) should consume going forward.
"""

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
            'verification_status': upload.verification_status or 'PENDING',
            'verification_note': upload.verification_note,
            'verified_at': upload.verified_at.isoformat() if upload.verified_at else None,
            'is_sensitive': upload.is_sensitive,
        },
        'provenance': {
            'source_name': 'upload',
            'source_label': 'Citizen Upload',
            'source_type_detail': upload.source_type,
            'witness_statement': upload.witness_statement,
            # Never expose the raw user_id (deanonymization vector). Public read
            # paths only need to know whether a report is unattributed.
            # Full reporter object (handle, rung, is_signed) arrives with Stage B/E.
            'is_anonymous': upload.user_id is None,
        },
        'timestamps': {
            'published_at': published,
            'ingested_at': published,
        },
    }
