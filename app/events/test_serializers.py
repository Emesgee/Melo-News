"""
Reader-facing trust serializer tests (Stage E).

Covers the honest-trust-display rules: confidence as a LOW/MED/HIGH band (never
a raw decimal), the reporter chip (handle/rung/track-record or anonymous, plus
the signed/unsigned lane), and the Event serializer showing counted (distinct
identities) vs supporting (anonymous) SEPARATELY, verified-only, with sticky
status override.
"""

import pytest
from flask import Flask

from app.models import db, User, FileUpload, FileType, Event
from app.story.serializers import (
    confidence_band, serialize_reporter, serialize_upload, serialize_event,
)


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


def _user(rung=1, handle='r', reports=0, corr=0):
    u = User(display_handle=handle, identity_type='pseudonymous',
             trust_rung=rung, reports_count=reports, corroborated_count=corr)
    db.session.add(u)
    db.session.flush()
    return u


def _mk(ft, user=None, event=None, status='PENDING', signed=False, conf=None):
    up = FileUpload(
        filename='x.jpg', file_path='/x.jpg', file_type_id=ft.filetypeid,
        user_id=(user.userid if user else None),
        event_id=(event.id if event else None),
        verification_status=status,
        report_signature=('sig' if signed else None),
        confidence_score=conf,
    )
    db.session.add(up)
    db.session.flush()
    return up


def test_confidence_band_thresholds():
    assert confidence_band(None) is None
    assert confidence_band(0.0) == 'LOW'
    assert confidence_band(0.33) == 'LOW'
    assert confidence_band(0.34) == 'MEDIUM'
    assert confidence_band(0.66) == 'MEDIUM'
    assert confidence_band(0.67) == 'HIGH'
    assert confidence_band(1.0) == 'HIGH'


def test_reporter_anonymous(ctx):
    r = serialize_reporter(_mk(_ft(), user=None, signed=False))
    assert r['is_anonymous'] is True
    assert r['rung'] == 0 and r['handle'] is None and r['is_signed'] is False


def test_reporter_pseudonymous_signed(ctx):
    u = _user(rung=2, handle='abu-karim')
    r = serialize_reporter(_mk(_ft(), user=u, signed=True))
    assert r['is_anonymous'] is False
    assert r['handle'] == 'abu-karim' and r['rung'] == 2
    assert r['is_signed'] is True


def test_reporter_track_record_computed_on_read(ctx):
    """Track record is derived from current rows (ADR-0012), not stored counters:
    only VERIFIED reports count, and corroborated_count counts DISTINCT events
    whose live status is CORROBORATED."""
    ft = _ft()
    u = _user(rung=2, handle='abu-karim')

    corro = Event(status='CORROBORATED')
    developing = Event(status='DEVELOPING')
    db.session.add_all([corro, developing])
    db.session.flush()

    # 3 VERIFIED reports: two in the CORROBORATED event (one distinct event),
    # one in a DEVELOPING event (published but not corroborated).
    _mk(ft, user=u, event=corro, status='VERIFIED')
    _mk(ft, user=u, event=corro, status='VERIFIED')
    _mk(ft, user=u, event=developing, status='VERIFIED')
    # PENDING report: not published, must not count toward reports_count.
    _mk(ft, user=u, event=corro, status='PENDING')
    db.session.flush()

    r = serialize_reporter(_mk(ft, user=u, signed=True))  # chip's own report is PENDING
    assert r['reports_count'] == 3          # only the 3 VERIFIED reports; PENDING excluded
    assert r['corroborated_count'] == 1     # distinct CORROBORATED events, not report count


def test_reporter_corroborated_count_reflects_status_override(ctx):
    """A sticky override that pulls an event OUT of CORROBORATED immediately drops
    the count — the drift a stored counter would have to chase (ADR-0012)."""
    ft = _ft()
    u = _user(rung=2)
    ev = Event(status='CORROBORATED')
    db.session.add(ev)
    db.session.flush()
    _mk(ft, user=u, event=ev, status='VERIFIED')
    db.session.flush()

    assert serialize_reporter(_mk(ft, user=u))['corroborated_count'] == 1
    ev.status_override = 'DISPUTED'         # moderator pins it out of CORROBORATED
    db.session.flush()
    assert serialize_reporter(_mk(ft, user=u))['corroborated_count'] == 0


def test_serialize_upload_uses_band_and_reporter(ctx):
    ev = Event(status='DEVELOPING')
    db.session.add(ev)
    db.session.flush()
    up = _mk(_ft(), user=_user(rung=2), event=ev, status='VERIFIED', conf=0.9)
    s = serialize_upload(up)
    # confidence is a band, raw decimal never exposed
    assert s['metrics']['confidence_band'] == 'HIGH'
    assert 'confidence_score' not in s['metrics']
    # reporter chip replaces the bare is_anonymous; user_id never leaks
    assert 'is_anonymous' not in s['provenance']
    assert s['provenance']['reporter']['rung'] == 2
    assert 'user_id' not in str(s)
    # slim event context attached
    assert s['event']['id'] == ev.id and s['event']['status'] == 'DEVELOPING'


def test_serialize_event_counted_vs_supporting(ctx):
    ft = _ft()
    ev = Event(status='CORROBORATED', confidence_score=0.8)
    db.session.add(ev)
    db.session.flush()
    _mk(ft, user=_user(rung=2), event=ev, status='VERIFIED')   # counted identity
    _mk(ft, user=None, event=ev, status='VERIFIED')            # anonymous → supporting
    _mk(ft, user=_user(rung=2), event=ev, status='PENDING')    # not public
    ev.corroboration_count = 1  # set by recompute in real flow
    db.session.flush()

    d = serialize_event(ev, include_members=True)
    assert d['status'] == 'CORROBORATED'
    assert d['corroboration'] == {'counted': 1, 'supporting': 1}
    assert d['member_count'] == 2          # verified only (the PENDING one excluded)
    assert d['confidence_band'] == 'HIGH'
    assert len(d['members']) == 2


def test_serialize_event_status_override_is_sticky(ctx):
    ev = Event(status='DEVELOPING', status_override='DISPUTED')
    db.session.add(ev)
    db.session.flush()
    d = serialize_event(ev)
    assert d['status'] == 'DISPUTED' and d['is_overridden'] is True
