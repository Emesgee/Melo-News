"""
app/events/service.py

Event (Incident) clustering + status derivation -- the corroboration engine.

A freshly-created report is clustered into an existing open Event by geo+time
proximity (reporter-entered lat/lon -- NOT media EXIF, which is stripped for
safety), or it starts a singleton Event of one. Clustering only *proposes*
membership; a report never auto-promotes an Event's status on its own.

corroboration_count counts DISTINCT non-anonymous identities among VERIFIED
members. An Event auto-reaches CORROBORATED only when that count meets the
threshold AND at least one verified member is an established (rung-2+) identity.
A flood of fresh rung-1 keys raises the *count* but the status stays gated at
DEVELOPING -- this is the Sybil backstop (status, not count). A moderator can
pin status via status_override (sticky).

Semantic clustering is deferred; geo+time only.
"""

import logging
import math
from datetime import timedelta, timezone

import config
from app.models import db, FileUpload, Event, User

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}


def _cfg(name, default):
    return getattr(config, name, default)


def _naive_utc(dt):
    """Normalize to naive UTC so aware datetimes (fresh ORM objects) and naive
    ones (read back from non-tz DB columns) compare without raising."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0  # Earth radius, km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def assign_event(upload):
    """Cluster `upload` into an open Event (geo+time) or start a singleton, set
    upload.event_id, recompute the Event, and return it.

    Call AFTER the upload has been flushed (so it has an id and an upload_date).
    Does not commit -- the caller owns the transaction.
    """
    radius_km = _cfg('EVENT_CLUSTER_RADIUS_KM', 1.0)
    window_h = _cfg('EVENT_CLUSTER_WINDOW_HOURS', 24)
    when = _naive_utc(upload.upload_date)

    event = _find_candidate_event(upload, when, radius_km, window_h)
    if event is None:
        event = Event(
            status='DEVELOPING',
            title=upload.title,
            city=upload.city,
            country=upload.country,
            lat=upload.lat,
            lon=upload.lon,
            severity=upload.severity,
        )
        db.session.add(event)
        db.session.flush()
    upload.event_id = event.id
    db.session.flush()
    recompute_event(event)
    return event


def process_new_report(upload):
    """Full post-creation pipeline for a fresh report:
      1. cluster it into an Event (or start a singleton),
      2. apply the rung gate (initial publication status + safety override),
      3. recompute the Event so an auto-published rung-2+ report immediately
         counts toward corroboration.
    Does not commit -- the caller owns the transaction."""
    from app.moderation.gate import apply_rung_gate
    event = assign_event(upload)
    apply_rung_gate(upload)
    db.session.flush()
    recompute_event(event)
    return event


def _find_candidate_event(upload, when, radius_km, window_h):
    """Return the nearest open Event within radius_km AND window_h of `upload`,
    or None. Logs a near-miss when the closest event is just outside the radius
    (a tuning aid -- see the pilot calibration plan)."""
    if when is None:
        return None
    window = timedelta(hours=window_h)
    candidates = (
        Event.query
        .filter(Event.status != 'CLOSED')
        .filter(Event.created_at >= when - window, Event.created_at <= when + window)
        .all()
    )

    # Geo match when a pin is present.
    if upload.lat is not None and upload.lon is not None:
        best, best_d = None, math.inf
        near, near_d = None, math.inf
        for ev in candidates:
            if ev.lat is None or ev.lon is None:
                continue
            d = _haversine_km(upload.lat, upload.lon, ev.lat, ev.lon)
            if d <= radius_km:
                if d < best_d:
                    best, best_d = ev, d
            elif d <= radius_km * 2:
                if d < near_d:
                    near, near_d = ev, d
        if best is None and near is not None:
            logger.info(
                "event near-miss: report %s is ~%.2fkm from event %s "
                "(radius %.2fkm) -- not clustered",
                upload.id, near_d, near.id, radius_km,
            )
        return best

    # Pin withheld (safety) -> degrade to city + time.
    if upload.city:
        city = upload.city.strip().lower()
        for ev in candidates:
            if ev.city and ev.city.strip().lower() == city:
                return ev
    return None


def recompute_event(event):
    """Recompute corroboration_count, aggregates, and derived status from the
    Event's current members. Reads members; writes the Event. Call after any
    membership or verification change."""
    members = FileUpload.query.filter_by(event_id=event.id).all()
    verified = [m for m in members if m.verification_status == 'VERIFIED']

    # Distinct, non-anonymous identities among VERIFIED members. Anonymous
    # (user_id NULL) members count 0 toward the threshold (supporting context).
    identities = {m.user_id for m in verified if m.user_id is not None}
    event.corroboration_count = len(identities)

    _update_aggregates(event, members)
    event.status = _derive_status(event, _has_established_member(identities))
    db.session.flush()
    return event


def _update_aggregates(event, members):
    """Centroid + rolled-up severity/confidence + display fallbacks."""
    geo = [(m.lat, m.lon) for m in members if m.lat is not None and m.lon is not None]
    if geo:
        event.lat = sum(p[0] for p in geo) / len(geo)
        event.lon = sum(p[1] for p in geo) / len(geo)
    sevs = [m.severity for m in members if m.severity]
    if sevs:
        event.severity = max(sevs, key=lambda s: _SEVERITY_RANK.get(s, 0))
    confs = [m.confidence_score for m in members if m.confidence_score is not None]
    if confs:
        event.confidence_score = sum(confs) / len(confs)
    if not event.title:
        titles = [m.title for m in members if m.title]
        if titles:
            event.title = titles[0]
    if not event.city:
        cities = [m.city for m in members if m.city]
        if cities:
            event.city = cities[0]


def _has_established_member(identity_ids):
    """True if any of these user ids is a rung-2+ identity. This is the gate
    that lets an Event auto-reach CORROBORATED; without it the Event stays
    DEVELOPING (moderator-gated), which is what neutralizes a fresh-key flood."""
    if not identity_ids:
        return False
    return db.session.query(User.userid).filter(
        User.userid.in_(identity_ids), User.trust_rung >= 2
    ).first() is not None


def _derive_status(event, has_established_member):
    """Pure status function. Moderator override is sticky; otherwise status is
    derived from corroboration + the Sybil gate."""
    if event.status_override:
        return event.status_override
    if event.closed_at:
        return 'CLOSED'
    if (event.dispute_count or 0) > 0:
        return 'DISPUTED'
    threshold = _cfg('EVENT_CORROBORATION_THRESHOLD', 2)
    if event.corroboration_count >= threshold and has_established_member:
        return 'CORROBORATED'
    return 'DEVELOPING'
