"""
app/events/routes.py

Reader-facing Event feed. The Event is the primary reader-facing unit, so the
public map/feed are feeds of Events (not raw reports). Only Events with at least
one VERIFIED member are surfaced — unverified content never reaches the public.
The feed leads with CORROBORATED and keeps DISPUTED prominent.
"""

from flask import Blueprint, jsonify, request

from app.models import db, Event
from app.story.serializers import serialize_event

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
