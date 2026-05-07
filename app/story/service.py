"""
app/story/service.py

Source-agnostic story retrieval.  Queries FileUpload and/or Telegram,
normalizes each record via serializers, merges, sorts, and pages the result.

Sources are controlled by the `source` parameter ('all' | 'upload' | 'telegram').
Adding a new source later requires only a new _query_* helper and a branch here.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import or_, distinct

import config
from app.models import db, FileUpload, Telegram
from .serializers import serialize_upload, serialize_telegram

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
):
    """
    Return a paged list of normalized Story dicts from one or more sources.

    Parameters
    ----------
    source : 'all' | 'upload' | 'telegram'
    q : free-text search string
    city, country, severity : exact/ilike filters
    has_location : True = only geolocated stories; False = only non-geolocated
    has_media : True = only stories with a primary_url
    from_date, to_date : datetime bounds (timezone-aware preferred)
    sort : 'published_at' | 'confidence' | 'severity'
    order : 'desc' | 'asc'
    limit, offset : pagination
    """
    stories = []

    if source in ('all', 'upload'):
        stories.extend(_query_uploads(q, city, country, severity, has_location, from_date, to_date))

    if config.TELEGRAM_ENABLED and source in ('all', 'telegram'):
        stories.extend(_query_telegram(q, city, country, severity, has_location, from_date, to_date))

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
    Replaces GET /api/telegram/news for the map feed.
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

    # Telegram facets (when enabled)
    if config.TELEGRAM_ENABLED:
        try:
            for (v,) in db.session.query(distinct(Telegram.matched_city)).filter(
                Telegram.matched_city.isnot(None), Telegram.matched_city != ''
            ).all():
                cities.add(v)
            for (v,) in db.session.query(distinct(Telegram.severity)).filter(
                Telegram.severity.isnot(None)
            ).all():
                severities.add(v)
        except Exception as exc:
            logger.error("facets: telegram query failed: %s", exc)

    sources = ['upload']
    if config.TELEGRAM_ENABLED:
        sources.append('telegram')

    return {
        'cities': sorted(cities),
        'countries': sorted(countries),
        'severities': sorted(severities),
        'sources': sources,
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
    )
    if upload_date:
        record.upload_date = upload_date

    db.session.add(record)
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


def get_story(source_type, source_record_id):
    """
    Return a single normalized Story by source type and record id,
    or None if not found.
    """
    if source_type == 'upload':
        record = db.session.get(FileUpload, source_record_id)
        return serialize_upload(record) if record else None

    if source_type == 'telegram':
        if not config.TELEGRAM_ENABLED:
            return None
        record = db.session.get(Telegram, source_record_id)
        return serialize_telegram(record) if record else None

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


def _query_uploads(q, city, country, severity, has_location, from_date, to_date):
    fq = FileUpload.query

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


def _query_telegram(q, city, country, severity, has_location, from_date, to_date):
    tq = Telegram.query

    if q:
        tq = tq.filter(or_(
            Telegram.message.ilike(f'%{q}%'),
            Telegram.tags.ilike(f'%{q}%'),
            Telegram.subject.ilike(f'%{q}%'),
        ))
    if city:
        tq = tq.filter(Telegram.matched_city.ilike(f'%{city}%'))
    if country:
        tq = tq.filter(Telegram.city_result.ilike(f'%{country}%'))
    if severity:
        tq = tq.filter(Telegram.severity == severity.upper())
    if has_location is True:
        tq = tq.filter(Telegram.lat.isnot(None), Telegram.lon.isnot(None))
    if from_date:
        tq = tq.filter(Telegram.time >= from_date)
    if to_date:
        tq = tq.filter(Telegram.time <= to_date)

    try:
        return [serialize_telegram(r) for r in tq.all()]
    except Exception as exc:
        logger.error("story service: telegram query failed: %s", exc)
        return []
