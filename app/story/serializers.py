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


def confidence_band(score):
    """Collapse a 0..1 confidence_score into a LOW/MEDIUM/HIGH band.

    Readers never see the raw decimal: it's an automated estimate and the
    precision is false. The band is labelled as automated and stays secondary
    to human corroboration in the UI. Returns None when there's no score.
    """
    if score is None:
        return None
    if score < 0.34:
        return 'LOW'
    if score < 0.67:
        return 'MEDIUM'
    return 'HIGH'


def serialize_reporter(upload):
    """Reader-facing reporter chip. Never leaks user_id (deanonymization).

    Shows the *basis* of trust: a pseudonymous handle + trust rung + track
    record, or an explicit anonymous/unverifiable marker. is_signed reflects an
    on-device cryptographic signature (tamper-evidence); web/anon reports are
    the unsigned lane.
    """
    is_signed = bool(getattr(upload, 'report_signature', None))
    user = getattr(upload, 'user', None)
    if upload.user_id is None or user is None:
        return {
            'handle': None,
            'rung': 0,
            'reports_count': 0,
            'corroborated_count': 0,
            'is_anonymous': True,
            'is_signed': is_signed,
        }
    return {
        'handle': user.display_handle or user.username,
        'rung': getattr(user, 'trust_rung', 1),
        'reports_count': getattr(user, 'reports_count', 0),
        'corroborated_count': getattr(user, 'corroborated_count', 0),
        'is_anonymous': False,
        'is_signed': is_signed,
    }


def _slim_event(upload):
    """Minimal Event context attached to a report (full Event via serialize_event)."""
    ev = getattr(upload, 'event', None)
    if ev is None:
        return None
    return {
        'id': ev.id,
        'status': ev.status_override or ev.status,
        'corroboration_count': ev.corroboration_count or 0,
    }


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
            # Band, never the raw decimal (false precision). Secondary to
            # human corroboration in the UI.
            'confidence_band': confidence_band(upload.confidence_score),
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
            # Reporter chip: handle/rung/track-record or anonymous — never user_id.
            'reporter': serialize_reporter(upload),
        },
        # The Event this report belongs to (corroboration context).
        'event': _slim_event(upload),
        'timestamps': {
            'published_at': published,
            'ingested_at': published,
        },
    }


def serialize_event(event, include_members=False):
    """Convert an Event ORM record to a reader-facing dict.

    The Event is the primary reader-facing unit. corroboration is shown as
    two SEPARATE numbers — `counted` (distinct non-anonymous VERIFIED
    identities, the falsifiable signal) and `supporting` (anonymous VERIFIED
    members, context only). status reflects a sticky moderator override when
    present. Confidence is a band, never a raw decimal.
    """
    # Public view: only VERIFIED members count and are listed — unverified
    # reports never reach the public feed.
    verified = [m for m in (getattr(event, 'members', []) or [])
                if m.verification_status == 'VERIFIED']
    supporting = sum(1 for m in verified if m.user_id is None)
    data = {
        'id': event.id,
        'status': event.status_override or event.status,
        'is_overridden': event.status_override is not None,
        'title': event.title,
        'summary': event.summary,
        'location': {
            'city': event.city,
            'country': event.country,
            'lat': event.lat,
            'lon': event.lon,
        },
        'severity': event.severity,
        'confidence_band': confidence_band(event.confidence_score),
        'corroboration': {
            'counted': event.corroboration_count or 0,
            'supporting': supporting,
        },
        'dispute_count': event.dispute_count or 0,
        'member_count': len(verified),
        'timestamps': {
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'updated_at': event.updated_at.isoformat() if event.updated_at else None,
            'closed_at': event.closed_at.isoformat() if event.closed_at else None,
        },
    }
    if include_members:
        data['members'] = [serialize_upload(m) for m in verified]
    return data
