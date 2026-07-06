"""
Advisory coordination-signal tests (ADR-0020 Phase 1, richer independence).

Two layers:
  * pure-function tests of analyze_independence (text near-duplication + tight
    synchronized submission), using lightweight stand-ins;
  * an integration HONESTY GUARD proving the signals are advisory only: genuine
    corroboration with similar text at the same time STILL reaches CORROBORATED
    (the count is untouched) while the coordination flag is surfaced.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event
from app.events.service import assign_event, recompute_event
from app.events.independence import analyze_independence
from app.events.archive import build_event_graph


def _m(id, user_id, text='', when=None):
    return SimpleNamespace(id=id, user_id=user_id, witness_statement=text,
                           title=None, upload_date=when)


def _types(flags):
    return {f['type'] for f in flags}


# --- pure-function: text near-duplication ---

def test_duplicate_text_flagged():
    t = 'Airstrike hit the market near the central hospital this evening'
    flags = analyze_independence([_m(1, 10, t), _m(2, 20, t + ' .')])
    dup = [f for f in flags if f['type'] == 'duplicate_text']
    assert len(dup) == 1
    assert dup[0]['source_ids'] == [1, 2]


def test_distinct_text_not_flagged():
    flags = analyze_independence([
        _m(1, 10, 'Airstrike hit the market near the central hospital'),
        _m(2, 20, 'Flooding downtown blocked the coastal road for hours'),
    ])
    assert 'duplicate_text' not in _types(flags)


def test_same_identity_pair_not_flagged():
    """Two reports from the SAME identity are not a coordination signal."""
    t = 'Airstrike hit the market near the central hospital this evening'
    flags = analyze_independence([_m(1, 10, t), _m(2, 10, t)])
    assert 'duplicate_text' not in _types(flags)


# --- pure-function: synchronized submission ---

def test_synchronized_submission_flagged():
    now = datetime.utcnow()
    flags = analyze_independence([
        _m(1, 10, 'a', now),
        _m(2, 20, 'b', now + timedelta(seconds=5)),
        _m(3, 30, 'c', now + timedelta(seconds=12)),
    ])
    sync = [f for f in flags if f['type'] == 'synchronized_submission']
    assert len(sync) == 1
    assert sync[0]['source_ids'] == [1, 2, 3]


def test_spread_out_submission_not_flagged():
    now = datetime.utcnow()
    flags = analyze_independence([
        _m(1, 10, 'a', now),
        _m(2, 20, 'b', now + timedelta(minutes=10)),
        _m(3, 30, 'c', now + timedelta(minutes=20)),
    ])
    assert 'synchronized_submission' not in _types(flags)


# --- integration: the honesty guard ---

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


def test_similar_text_still_corroborates(ctx):
    """The decisive guard: two genuine, independent reporters (DIFFERENT media)
    who describe the same event similarly at the same time STILL corroborate --
    the advisory flag is surfaced but the count is untouched."""
    ft = FileType(type_name='Other', allowed_extensions='*')
    db.session.add(ft)
    db.session.flush()
    now = datetime.utcnow()
    text = 'Airstrike hit the market near the central hospital this evening'
    ev_id = None
    for i, (handle, fp) in enumerate([('k-aaa', 'a' * 64), ('k-bbb', 'b' * 64)]):
        u = User(display_handle=handle, identity_type='pseudonymous', trust_rung=2)
        db.session.add(u)
        db.session.flush()
        up = FileUpload(
            filename='x', file_path='x', file_type_id=ft.filetypeid,
            user_id=u.userid, lat=31.500 + i * 0.0005, lon=34.460 + i * 0.0005,
            severity='LOW', upload_date=now, verification_status='PENDING',
            witness_statement=text, media_sha256=fp,
        )
        db.session.add(up)
        db.session.flush()
        assign_event(up)
        up.verification_status = 'VERIFIED'
        db.session.flush()
        recompute_event(db.session.get(Event, up.event_id))
        ev_id = up.event_id

    ev = db.session.get(Event, ev_id)
    # Corroboration is intact: different media = two independent origins.
    assert ev.status == 'CORROBORATED'
    assert ev.independent_source_count == 2
    # ...and the coordination flag is surfaced advisorily, not applied.
    g = build_event_graph(ev)
    assert 'duplicate_text' in _types(g['coordination_flags'])
    assert g['corroboration']['independent'] == 2
