"""
Corroboration-graph tests (ADR-0020 Phase 1, the archive-grade export).

Verifies the graph is deterministic + hashable, classifies independence
(reshares vs independent origins) consistently with the corroboration engine,
never leaks a raw user_id, and that its integrity hash tracks its content.

In-memory SQLite with a minimal Flask app, matching test_corroboration.
"""

from datetime import datetime

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event
from app.events.service import assign_event, recompute_event
from app.events.archive import build_event_graph, graph_content_hash


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


def _report(ft, user, lat, lon, when, media_sha256=None, signature=None):
    up = FileUpload(
        filename='x', file_path='x', file_type_id=ft.filetypeid,
        user_id=(user.userid if user else None),
        lat=lat, lon=lon, severity='LOW',
        upload_date=when, verification_status='PENDING',
        media_sha256=media_sha256, report_signature=signature,
    )
    db.session.add(up)
    db.session.flush()
    assign_event(up)
    up.verification_status = 'VERIFIED'
    db.session.flush()
    recompute_event(db.session.get(Event, up.event_id))
    return up


def test_graph_is_deterministic_and_hashed(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2, 'k-aaa'), _user(2, 'k-bbb')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64, signature='sig1')
    _report(ft, u2, 31.5005, 34.4605, now, media_sha256='b' * 64, signature='sig2')
    ev = db.session.get(Event, r1.event_id)

    g1 = build_event_graph(ev)
    g2 = build_event_graph(ev)
    assert g1 == g2                                   # deterministic
    assert g1['integrity']['graph_sha256'] == graph_content_hash(g1)
    assert g1['schema_version'] == 1
    assert g1['corroboration'] == {
        'counted': 2, 'independent': 2, 'supporting': 0, 'reshare_clusters': [],
    }
    assert [n['independence'] for n in g1['nodes']] == ['independent', 'independent']
    assert [n['provenance_tier'] for n in g1['nodes']] == ['verified', 'verified']


def test_graph_flags_reshare_cluster(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2, 'k-aaa'), _user(2, 'k-bbb')
    same = 'c' * 64
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256=same)
    _report(ft, u2, 31.5005, 34.4605, now, media_sha256=same)  # reshare
    ev = db.session.get(Event, r1.event_id)

    g = build_event_graph(ev)
    assert g['corroboration']['counted'] == 2
    assert g['corroboration']['independent'] == 1
    assert g['corroboration']['reshare_clusters'] == [{'fingerprint': same, 'size': 2}]
    assert {n['independence'] for n in g['nodes']} == {'reshare'}


def test_graph_never_leaks_user_id(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2, 'k-aaa')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    ev = db.session.get(Event, r1.event_id)

    g = build_event_graph(ev)
    assert 'user_id' not in str(g)                       # no raw FK anywhere
    assert all('user_id' not in n['reporter'] for n in g['nodes'])
    assert g['nodes'][0]['reporter']['handle'] == 'k-aaa'  # pseudonym, not identity


def test_integrity_hash_tracks_content(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2, 'k-aaa')
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    ev = db.session.get(Event, r1.event_id)
    before = build_event_graph(ev)['integrity']['graph_sha256']

    # A new corroborating source changes the graph -> changes the hash.
    u2 = _user(2, 'k-bbb')
    _report(ft, u2, 31.5005, 34.4605, now, media_sha256='b' * 64)
    after = build_event_graph(db.session.get(Event, r1.event_id))['integrity']['graph_sha256']
    assert before != after


def test_unsigned_source_is_unverified_tier(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2, 'k-aaa')
    r1 = _report(ft, u1, 31.5000, 34.4600, now)  # no signature
    ev = db.session.get(Event, r1.event_id)

    g = build_event_graph(ev)
    assert g['nodes'][0]['provenance_tier'] == 'unverified'
