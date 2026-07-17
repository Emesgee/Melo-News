"""
Rung-gate + priority + vouch tests (Stage F).

Validates publication routing (rung 0-1 pre-moderation; rung 2-3 auto-publish),
the safety override (HIGH / sensitive / first-media-on-new-event force
pre-moderation regardless of rung), attention-priority ordering, and that a
steward vouch to rung 2 immediately promotes the reporter's corroborated event.
"""

from datetime import datetime

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event
from app.events.service import process_new_report, recompute_event
from app.moderation.gate import compute_priority


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


def _user(rung):
    u = User(display_handle=f'r{rung}', identity_type='pseudonymous', trust_rung=rung)
    db.session.add(u)
    db.session.flush()
    return u


def _submit(ft, user, lat, lon, severity='LOW', sensitive=False, media=False):
    up = FileUpload(
        filename='x.jpg',
        file_path=('blob://x.jpg' if media else 'ingest:no-media'),
        file_type_id=ft.filetypeid,
        user_id=(user.userid if user else None),
        lat=lat, lon=lon, severity=severity, is_sensitive=sensitive,
        upload_date=datetime.utcnow(),
    )
    db.session.add(up)
    db.session.flush()
    process_new_report(up)   # cluster + gate + recompute
    return up


def _moderator_verify(up):
    up.verification_status = 'VERIFIED'
    db.session.flush()
    recompute_event(db.session.get(Event, up.event_id))


def test_anonymous_and_fresh_are_pre_moderated(ctx):
    ft = _ft()
    anon = _submit(ft, None, 31.5, 34.4)          # rung 0
    fresh = _submit(ft, _user(1), 32.5, 35.4)      # rung 1
    assert anon.verification_status == 'PENDING'
    assert fresh.verification_status == 'PENDING'


def test_established_text_report_autopublishes(ctx):
    ft = _ft()
    up = _submit(ft, _user(2), 31.5, 34.4)         # rung 2, text-only
    assert up.verification_status == 'VERIFIED'
    assert up.verified_by is None                  # system auto-publish, not approved


def test_safety_override_forces_pre_moderation(ctx):
    ft = _ft()
    high = _submit(ft, _user(2), 31.50, 34.40, severity='HIGH')
    sens = _submit(ft, _user(2), 32.50, 35.40, sensitive=True)
    first_media = _submit(ft, _user(2), 33.50, 36.40, media=True)  # first media on new event
    assert high.verification_status == 'PENDING'
    assert sens.verification_status == 'PENDING'
    assert first_media.verification_status == 'PENDING'


def test_two_established_reports_autocorroborate(ctx):
    ft = _ft()
    a = _submit(ft, _user(2), 31.5000, 34.4600)
    b = _submit(ft, _user(2), 31.5004, 34.4604)
    assert a.event_id == b.event_id
    assert a.verification_status == 'VERIFIED' and b.verification_status == 'VERIFIED'
    ev = db.session.get(Event, a.event_id)
    assert ev.corroboration_count == 2
    assert ev.status == 'CORROBORATED'             # no moderator touched it


def test_priority_orders_high_above_low(ctx):
    ft = _ft()
    high = _submit(ft, _user(1), 31.5, 34.4, severity='HIGH')
    low = _submit(ft, _user(1), 32.5, 35.4, severity='LOW')
    assert compute_priority(high) > compute_priority(low)


def test_steward_vouch_promotes_event(ctx):
    """Bravo scenario: two fresh rung-1 reporters corroborate but stay gated;
    vouching one to rung 2 immediately promotes the event to CORROBORATED."""
    ft = _ft()
    a_user, b_user = _user(1), _user(1)
    a = _submit(ft, a_user, 32.0000, 35.0000)
    b = _submit(ft, b_user, 32.0003, 35.0003)
    assert a.event_id == b.event_id
    # rung-1 reports are pre-moderated → a moderator approves them
    _moderator_verify(a)
    _moderator_verify(b)
    ev = db.session.get(Event, a.event_id)
    assert ev.corroboration_count == 2 and ev.status == 'DEVELOPING'  # gated

    # Steward vouches one reporter to rung 2 (what set_rung does) → re-evaluate.
    a_user.trust_rung = 2
    db.session.flush()
    recompute_event(ev)
    assert ev.status == 'CORROBORATED'
