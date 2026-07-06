"""
app/events/routes.py

Reader-facing Event feed. The Event is the primary reader-facing unit, so the
public map/feed are feeds of Events (not raw reports). Only Events with at least
one VERIFIED member are surfaced — unverified content never reaches the public.
The feed leads with CORROBORATED and keeps DISPUTED prominent.
"""

import json

from flask import Blueprint, jsonify, request

from app.models import db, Event, EventGraphSnapshot
from app.story.serializers import serialize_event
from app.events.archive import build_event_graph

events_bp = Blueprint('events', __name__, url_prefix='/api/events')

# Feed ordering: lead with CORROBORATED, then DISPUTED (needs attention, kept
# prominent), then DEVELOPING; CLOSED sinks to the bottom.
_STATUS_RANK = {'CORROBORATED': 0, 'DISPUTED': 1, 'DEVELOPING': 2, 'CLOSED': 3}


def _effective_status(ev):
    return ev.status_override or ev.status


def _has_public_member(ev):
    return any(m.verification_status == 'VERIFIED' for m in ev.members)


@events_bp.route('', methods=['GET'])
def list_events():
    """Event feed. Query: status=<STATUS>, limit=<int>."""
    limit = request.args.get('limit', default=100, type=int)
    status_filter = (request.args.get('status') or '').strip().upper() or None
    q = (request.args.get('q') or '').strip().lower()

    # Pilot scale is small; filter/sort in Python for clarity. Replace with a
    # join + window function if volume grows.
    visible = []
    for ev in Event.query.all():
        if not _has_public_member(ev):
            continue
        if status_filter and _effective_status(ev) != status_filter:
            continue
        if q and q not in (ev.title or '').lower() and q not in (ev.city or '').lower():
            continue
        visible.append(ev)

    visible.sort(key=lambda e: (
        _STATUS_RANK.get(_effective_status(e), 9),
        -(e.updated_at.timestamp() if e.updated_at else 0.0),
    ))
    visible = visible[:max(1, limit)]
    return jsonify({'events': [serialize_event(e) for e in visible]}), 200


@events_bp.route('/<int:event_id>', methods=['GET'])
def event_detail(event_id):
    """Single Event with its VERIFIED members (each a reporter-chip story)."""
    ev = db.session.get(Event, event_id)
    if ev is None or not _has_public_member(ev):
        return jsonify({'error': 'Event not found'}), 404
    return jsonify(serialize_event(ev, include_members=True)), 200


@events_bp.route('/<int:event_id>/graph', methods=['GET'])
def event_graph(event_id):
    """The corroboration graph: an explicit, deterministic, privacy-preserving
    provenance record of the Event and its sources, with an integrity hash
    (ADR-0020 Phase 1). The archive-grade export -- same visibility as the
    detail view (VERIFIED members only, never a raw user_id)."""
    ev = db.session.get(Event, event_id)
    if ev is None or not _has_public_member(ev):
        return jsonify({'error': 'Event not found'}), 404
    return jsonify(build_event_graph(ev)), 200


@events_bp.route('/<int:event_id>/snapshots', methods=['GET'])
def event_snapshots(event_id):
    """Durable snapshot history for an Event (ADR-0020 Phase 1 / UC9): the
    append-only, content-addressed record of its corroboration graph at each
    archival moment. Metadata only (hash + status + reason + time); fetch a
    single snapshot's full graph via the detail route below."""
    ev = db.session.get(Event, event_id)
    if ev is None or not _has_public_member(ev):
        return jsonify({'error': 'Event not found'}), 404
    snaps = (
        EventGraphSnapshot.query
        .filter_by(event_id=event_id)
        .order_by(EventGraphSnapshot.created_at.asc(), EventGraphSnapshot.id.asc())
        .all()
    )
    return jsonify({'snapshots': [{
        'id': s.id,
        'schema_version': s.schema_version,
        'graph_sha256': s.graph_sha256,
        'status': s.status,
        'reason': s.reason,
        'created_at': s.created_at.isoformat() if s.created_at else None,
    } for s in snaps]}), 200


@events_bp.route('/<int:event_id>/snapshots/<int:snapshot_id>', methods=['GET'])
def event_snapshot_detail(event_id, snapshot_id):
    """The full, verbatim corroboration graph captured in one snapshot -- the
    preserved archive record, exactly as it was hashed."""
    ev = db.session.get(Event, event_id)
    if ev is None or not _has_public_member(ev):
        return jsonify({'error': 'Event not found'}), 404
    s = db.session.get(EventGraphSnapshot, snapshot_id)
    if s is None or s.event_id != event_id:
        return jsonify({'error': 'Snapshot not found'}), 404
    return jsonify(json.loads(s.graph_json)), 200
