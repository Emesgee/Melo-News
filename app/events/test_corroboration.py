"""
Corroboration engine smoke tests (Stage D).

Exercises the rules locked during the design grill: geo+time clustering,
corroboration = COUNT(DISTINCT non-anonymous identity) over VERIFIED members,
the Sybil backstop (fresh rung-1 keys raise the count but cannot auto-promote),
anonymous members count 0, and geo/time separation starts new Events.

Runs against in-memory SQLite with a minimal Flask app (no blueprints), so it
needs only the Flask + SQLAlchemy stack, not the full media/AI dependencies.
"""

from datetime import datetime, timedelta

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event
from app.events.service import assign_event, recompute_event


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


def _report(ft, user, lat, lon, when, city=None, severity='LOW', media_sha256=None):
    up = FileUpload(
        filename='x', file_path='x', file_type_id=ft.filetypeid,
        user_id=(user.userid if user else None),
        lat=lat, lon=lon, city=city, severity=severity,
        upload_date=when, verification_status='PENDING',
        media_sha256=media_sha256,
    )
    db.session.add(up)
    db.session.flush()
    assign_event(up)
    return up


def _verify(up):
    up.verification_status = 'VERIFIED'
    db.session.flush()
    recompute_event(db.session.get(Event, up.event_id))


def test_distinct_established_identities_corroborate(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2), _user(2)
    r1 = _report(ft, u1, 31.5000, 34.4600, now)
    r2 = _report(ft, u2, 31.5005, 34.4605, now)  # ~70 m away, same time
    assert r1.event_id == r2.event_id, "nearby same-time reports should cluster"

    ev = db.session.get(Event, r1.event_id)
    assert ev.status == 'DEVELOPING' and ev.corroboration_count == 0  # nothing verified yet

    _verify(r1)
    _verify(r2)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 2
    assert ev.status == 'CORROBORATED'  # 2 distinct rung-2 identities


def test_reshared_media_collapses_to_one_origin(ctx):
    """Two established keys posting BYTE-IDENTICAL media is a reshare/astroturf,
    not independent corroboration (UC3/UC8). The raw count is honest (2 distinct
    keys), but independent_source_count collapses to 1 and the Event stays
    DEVELOPING even though a rung-2 member is present (ADR-0020 Phase 1)."""
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2), _user(2)
    same = 'a' * 64
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256=same)
    r2 = _report(ft, u2, 31.5005, 34.4605, now, media_sha256=same)  # same clip
    assert r1.event_id == r2.event_id
    _verify(r1)
    _verify(r2)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 2         # two distinct keys, honestly
    assert ev.independent_source_count == 1     # ...but one piece of evidence
    assert ev.status == 'DEVELOPING'            # reshare cannot promote


def test_distinct_media_stays_independent(ctx):
    """Two established keys with DIFFERENT media hashes (two people filming the
    same event) are genuinely independent -> two origins -> CORROBORATED."""
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2), _user(2)
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    r2 = _report(ft, u2, 31.5005, 34.4605, now, media_sha256='b' * 64)
    _verify(r1)
    _verify(r2)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 2
    assert ev.independent_source_count == 2
    assert ev.status == 'CORROBORATED'


def test_same_reporter_multiple_media_counts_once(ctx):
    """One reporter posting several DIFFERENT files is still ONE independent
    source — identities are the unit, so extra media never adds sources. Guards
    against a single rung-2 reporter self-corroborating by uploading two clips
    (the real-usage bug: a video + a photo from one phone)."""
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2)
    r1 = _report(ft, u1, 31.5000, 34.4600, now, media_sha256='a' * 64)
    r2 = _report(ft, u1, 31.5005, 34.4605, now, media_sha256='b' * 64)  # same user, diff clip
    assert r1.event_id == r2.event_id
    _verify(r1)
    _verify(r2)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 1          # one identity
    assert ev.independent_source_count == 1     # ...one source, despite two files
    assert ev.status == 'DEVELOPING'            # a reporter cannot corroborate themselves


def test_sybil_fresh_keys_count_but_stay_gated(ctx):
    """One actor's two fresh keys = two distinct user_ids: the count climbs to
    2, but with no established (rung-2+) member the Event stays DEVELOPING."""
    ft, now = _ft(), datetime.utcnow()
    a, b = _user(1), _user(1)
    r1 = _report(ft, a, 32.0000, 35.0000, now)
    r2 = _report(ft, b, 32.0003, 35.0003, now)
    assert r1.event_id == r2.event_id
    _verify(r1)
    _verify(r2)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 2      # count is honest...
    assert ev.status == 'DEVELOPING'        # ...status is gated (Sybil backstop)


def test_anonymous_member_counts_zero(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2)
    r1 = _report(ft, u1, 31.5000, 34.4600, now)
    anon = _report(ft, None, 31.5001, 34.4601, now)  # anonymous, no user_id
    assert r1.event_id == anon.event_id
    _verify(r1)
    _verify(anon)
    ev = db.session.get(Event, r1.event_id)
    assert ev.corroboration_count == 1      # anon does not count toward the total
    assert ev.status == 'DEVELOPING'        # threshold of 2 not met


def test_geo_separation_starts_new_event(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2)
    r1 = _report(ft, u1, 31.50, 34.46, now)
    r2 = _report(ft, u1, 31.60, 34.56, now)  # ~14 km away
    assert r1.event_id != r2.event_id


def test_time_separation_starts_new_event(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1 = _user(2)
    r1 = _report(ft, u1, 31.50, 34.46, now)
    r2 = _report(ft, u1, 31.50, 34.46, now + timedelta(hours=48))  # outside 24 h window
    assert r1.event_id != r2.event_id


def test_city_degrade_when_pin_withheld(ctx):
    ft, now = _ft(), datetime.utcnow()
    u1, u2 = _user(2), _user(2)
    r1 = _report(ft, u1, None, None, now, city='Gaza')
    r2 = _report(ft, u2, None, None, now, city='gaza')  # case-insensitive, no pins
    assert r1.event_id == r2.event_id
