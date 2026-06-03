"""
app/story/service.py

Citizen story retrieval. Queries FileUpload, normalizes each record via
serializers, sorts, and pages the result.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import or_, distinct

from app.models import db, FileUpload
from .serializers import serialize_upload

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_stories(
    source='all',
    q=None,
    city=None,
    country=None,
    severity=None,
    has_location=None,
    has_media=None,
    from_date=None,
    to_date=None,
    sort='published_at',
    order='desc',
    limit=50,
    offset=0,
    include_unverified=False,
):
    """
    Return a paged list of normalized Story dicts from one or more sources.

    Parameters
    ----------
    source : 'all' | 'upload'
    q : free-text search string
    city, country, severity : exact/ilike filters
    has_location : True = only geolocated stories; False = only non-geolocated
    has_media : True = only stories with a primary_url
    from_date, to_date : datetime bounds (timezone-aware preferred)
    sort : 'published_at' | 'confidence' | 'severity'
    order : 'desc' | 'asc'
    limit, offset : pagination
    include_unverified : when False (default), citizen uploads that are
        still PENDING or REJECTED are excluded — only moderator-approved
        stories reach the public feed. Set True for moderator views.
    """
    stories = []

    if source in ('all', 'upload'):
        stories.extend(_query_uploads(
            q, city, country, severity, has_location, from_date, to_date,
            include_unverified=include_unverified,
        ))

    if has_media is True:
        stories = [s for s in stories if s['media']['primary_url']]
    elif has_media is False:
        stories = [s for s in stories if not s['media']['primary_url']]

    _sort_stories(stories, sort, order)

    total = len(stories)
    page = stories[offset: offset + limit]

    return {
        'items': page,
        'paging': {
            'limit': limit,
            'offset': offset,
            'returned': len(page),
            'has_more': (offset + limit) < total,
        },
    }


def list_story_markers(
    source='all',
    q=None,
    city=None,
    country=None,
    severity=None,
    from_date=None,
    to_date=None,
    limit=500,
):
    """
    Return a slim list of map-marker Story dicts (geolocated only).
    """
    result = list_stories(
        source=source,
        q=q,
        city=city,
        country=country,
        severity=severity,
        has_location=True,
        from_date=from_date,
        to_date=to_date,
        sort='published_at',
        order='desc',
        limit=limit,
        offset=0,
    )

    markers = [
        {
            'id': s['id'],
            'source_type': s['source_type'],
            'title': s['title'],
            'body': s['body'],
            'location': s['location'],
            'media': {'primary_url': s['media']['primary_url']},
            'metrics': {
                'severity': s['metrics']['severity'],
                'confidence_score': s['metrics']['confidence_score'],
            },
            'timestamps': {'published_at': s['timestamps']['published_at']},
        }
        for s in result['items']
    ]
    return {'items': markers}


def get_facets():
    """
    Return distinct filter values present in the data so the frontend
    filter panel can populate itself from real data.

    Returns
    -------
    dict with keys:
        cities     : sorted list of non-null city strings
        countries  : sorted list of non-null country strings
        severities : sorted list of distinct severity values
        sources    : list of enabled source_type strings
    """
    cities = set()
    countries = set()
    severities = set()

    # FileUpload facets
    try:
        for (v,) in db.session.query(distinct(FileUpload.city)).filter(
            FileUpload.city.isnot(None), FileUpload.city != ''
        ).all():
            cities.add(v)
        for (v,) in db.session.query(distinct(FileUpload.country)).filter(
            FileUpload.country.isnot(None), FileUpload.country != ''
        ).all():
            countries.add(v)
        for (v,) in db.session.query(distinct(FileUpload.severity)).filter(
            FileUpload.severity.isnot(None)
        ).all():
            severities.add(v)
    except Exception as exc:
        logger.error("facets: upload query failed: %s", exc)

    return {
        'cities': sorted(cities),
        'countries': sorted(countries),
        'severities': sorted(severities),
        'sources': ['upload'],
    }


def ingest_story(user_id, payload):
    """
    Create a FileUpload row from a JSON field-packet (Android / API client).

    Required: title
    Optional: body, tags (str|list), subject, city, country, lat, lon,
              severity (LOW|MEDIUM|HIGH), media_url, source_name, published_at

    Returns the new normalized Story dict, or raises ValueError on bad input.
    """
    from app.models import FileUpload  # avoid circular at module load

    title = (payload.get('title') or '').strip()
    if not title:
        raise ValueError('title is required')

    # Idempotency: if the Android local_id was already ingested, return the existing record
    local_id = (payload.get('local_id') or '').strip() or None
    if local_id:
        existing = FileUpload.query.filter_by(local_id=local_id).first()
        if existing:
            return serialize_upload(existing)

    tags_raw = payload.get('tags', '')
    if isinstance(tags_raw, list):
        tags_str = ', '.join(str(t).strip() for t in tags_raw if t)
    else:
        tags_str = str(tags_raw).strip()

    severity = (payload.get('severity') or 'LOW').upper()
    if severity not in ('LOW', 'MEDIUM', 'HIGH'):
        severity = 'LOW'

    media_url = (payload.get('media_url') or '').strip()
    file_type = _resolve_file_type(media_url)

    upload_date = None
    if payload.get('published_at'):
        try:
            from dateutil import parser as _dp
            upload_date = _dp.parse(payload['published_at'])
            if upload_date.tzinfo is None:
                upload_date = upload_date.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    record = FileUpload(
        filename=title[:255],
        file_path=media_url or 'ingest:no-media',
        title=title[:100],
        tags=tags_str[:255] if tags_str else None,
        subject=(payload.get('subject') or '')[:255] or None,
        city=(payload.get('city') or '')[:100] or None,
        country=(payload.get('country') or '')[:100] or None,
        lat=_float_or_none(payload.get('lat')),
        lon=_float_or_none(payload.get('lon')),
        severity=severity,
        witness_statement=payload.get('body') or None,
        source_type=payload.get('source_name') or 'mobile',
        analysis_status='PENDING',
        user_id=user_id,
        file_type_id=file_type.filetypeid,
        local_id=local_id,
    )
    if upload_date:
        record.upload_date = upload_date

    db.session.add(record)
    db.session.flush()
    # Cluster into an Event (geo+time) or start a singleton — proposes only.
    from app.events.service import assign_event
    assign_event(record)
    db.session.commit()
    db.session.refresh(record)
    return serialize_upload(record)


def _resolve_file_type(media_url):
    """Match FileType by URL extension; fall back to get-or-create 'Other'."""
    from app.models import FileType
    import os

    if media_url:
        ext = os.path.splitext(media_url.split('?')[0])[1].lstrip('.').lower()
        if ext:
            for ft in FileType.query.all():
                if ext in [e.strip().lower() for e in ft.allowed_extensions.split(',')]:
                    return ft

    other = FileType.query.filter_by(type_name='Other').first()
    if not other:
        other = FileType(type_name='Other', allowed_extensions='*')
        db.session.add(other)
        db.session.flush()
    return other


def _float_or_none(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_story(source_type, source_record_id, include_unverified=False):
    """
    Return a single normalized Story by source type and record id,
    or None if not found.

    When ``include_unverified`` is False (default), citizen uploads in
    PENDING or REJECTED state are hidden — a public link to a pending
    story 404s until the moderator approves it. Reporters viewing their
    own work use /api/file_upload/my-uploads instead, which always shows
    every state.
    """
    if source_type == 'upload':
        record = db.session.get(FileUpload, source_record_id)
        if not record:
            return None
        if not include_unverified and record.verification_status != 'VERIFIED':
            return None
        return serialize_upload(record)

    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _published_at_key(story):
    ts = story['timestamps']['published_at']
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, OverflowError):
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def _sort_stories(stories, sort, order):
    reverse = order != 'asc'
    if sort == 'confidence':
        stories.sort(key=lambda s: s['metrics']['confidence_score'] or 0.0, reverse=reverse)
    elif sort == 'severity':
        stories.sort(
            key=lambda s: _SEVERITY_ORDER.get(s['metrics']['severity'] or 'LOW', 1),
            reverse=reverse,
        )
    else:
        stories.sort(key=_published_at_key, reverse=reverse)


def _query_uploads(q, city, country, severity, has_location, from_date, to_date, include_unverified=False):
    fq = FileUpload.query

    if not include_unverified:
        fq = fq.filter(FileUpload.verification_status == 'VERIFIED')

    if q:
        fq = fq.filter(or_(
            FileUpload.filename.ilike(f'%{q}%'),
            FileUpload.title.ilike(f'%{q}%'),
            FileUpload.tags.ilike(f'%{q}%'),
            FileUpload.subject.ilike(f'%{q}%'),
            FileUpload.transcription.ilike(f'%{q}%'),
        ))
    if city:
        fq = fq.filter(FileUpload.city.ilike(f'%{city}%'))
    if country:
        fq = fq.filter(FileUpload.country.ilike(f'%{country}%'))
    if severity:
        fq = fq.filter(FileUpload.severity == severity.upper())
    if has_location is True:
        fq = fq.filter(FileUpload.lat.isnot(None), FileUpload.lon.isnot(None))
    if from_date:
        fq = fq.filter(FileUpload.upload_date >= from_date)
    if to_date:
        fq = fq.filter(FileUpload.upload_date <= to_date)

    try:
        return [serialize_upload(r) for r in fq.all()]
    except Exception as exc:
        logger.error("story service: upload query failed: %s", exc)
        return []
