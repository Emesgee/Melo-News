"""
Durable corroboration-graph snapshot tests (ADR-0020 Phase 1 / UC9).

Verifies that reaching an archival status captures an append-only,
content-addressed snapshot; that snapshots dedup by hash; that the stored graph
is verbatim + integrity-consistent; and that a merely-DEVELOPING event captures
nothing.

In-memory SQLite with a minimal Flask app, matching test_corroboration.
"""

import json
from datetime import datetime

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event, EventGraphSnapshot
from app.events.service import assign_event, recompute_event
from app.events.archive import snapshot_event, graph_content_hash


@pytest.fixture
def ctx():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()


def _ft():
    ft = FileType(type_name='Other', allowed_extensions='*')
    db.session.add(ft)
    db.session.flush()
    return ft


def _user(rung, handle):
    u = User(display_handle=handle, identity_type='pseudonymous', trust_rung=rung)
    db.session.add(u)
    db.session.flush()
    return u


def _report(ft, user, lat, lon, when, media_sha256=None):
    up = FileUpload(
        filename='x', file_path='x', file_type_id=ft.filetypeid,
        user_id=(user.userid if user else None),
        lat=lat, lon=lon, severity='LOW',
        upload_date=when, verification_status='PENDING',
        media_sha256=media_sha256,
    )
    db.session.add(up)
    db.session.flush()
    assign_event(up)
    up.verification_status = 'VERIFIED'
    db.session.flush()
    recompute_event(db.session.get(Event, up.event_id))
    return up


def _snaps(event_id):
    return EventGraphSnapshot.query.filter_by(event_id=event_id).all()


def test_snapshot_captured_on_corroboration(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2, 'k-aaa'), _user(2, 'k-bbb')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    _report(ft, u2, 31.5005, 34.4605, now, media_sha256='b' * 64)  # -> CORROBORATED
    ev = db.session.get(Event, r1.event_id)
    assert ev.status == 'CORROBORATED'

    snaps = _snaps(ev.id)
    assert len(snaps) == 1
    s = snaps[0]
    assert s.reason == 'corroborated' and s.status == 'CORROBORATED'
    # Stored graph is verbatim + integrity-consistent.
    stored = json.loads(s.graph_json)
    assert stored['integrity']['graph_sha256'] == s.graph_sha256
    assert graph_content_hash(stored) == s.graph_sha256


def test_developing_event_captures_nothing(ctx):
    """A lone (or unpromoted) report never reaches an archival status, so no
    snapshot is taken."""
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2, 'k-aaa')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    ev = db.session.get(Event, r1.event_id)
    assert ev.status == 'DEVELOPING'
    assert _snaps(ev.id) == []


def test_snapshot_dedups_by_hash(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2, 'k-aaa'), _user(2, 'k-bbb')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    _report(ft, u2, 31.5005, 34.4605, now, media_sha256='b' * 64)
    ev = db.session.get(Event, r1.event_id)
    assert len(_snaps(ev.id)) == 1

    # An explicit re-snapshot with no material change is a no-op (same hash).
    first = _snaps(ev.id)[0]
    again = snapshot_event(ev, reason='manual')
    assert again.id == first.id
    assert len(_snaps(ev.id)) == 1

    # A recompute that leaves status unchanged also adds nothing.
    recompute_event(ev)
    assert len(_snaps(ev.id)) == 1
