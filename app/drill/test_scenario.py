"""
T4P drill scenario self-test.

Runs the full scripted scenario through the real submission + moderation
pipeline and asserts it reaches the state the live drill is meant to demonstrate
-- so the scenario stays faithful to the engine as the engine evolves.
"""

import pytest
from flask import Flask

from app.models import db, User, FileUpload, Event
from app.drill import scenario


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


def test_full_scenario_reaches_expected_endstate(ctx):
    s = scenario.simulate(db)
    # ALPHA: two rung-2 reporters auto-corroborate with no moderator action.
    assert s['ALPHA']['status'] == 'CORROBORATED' and s['ALPHA']['counted'] == 2
    # BRAVO: moderator-confirmed (Sybil accounts rejected) + steward vouch -> CORROBORATED.
    assert s['BRAVO']['status'] == 'CORROBORATED' and s['BRAVO']['counted'] == 3
    # CHARLIE: moderator-pinned DISPUTED.
    assert s['CHARLIE']['status'] == 'DISPUTED'
    # DELTA: lone witness, verified but uncorroborated.
    assert s['DELTA']['status'] == 'DEVELOPING' and s['DELTA']['counted'] == 1
    # NEARMISS: ~1.5 km off ALPHA -> its own event.
    assert s['NEARMISS']['separate_from_alpha'] is True


def test_sybil_accounts_are_rejected_not_counted(ctx):
    scenario.simulate(db)
    # The two Sybil accounts (bravo-1's extra keys) must end REJECTED.
    for handle in ('bravo-1-alt1', 'bravo-1-alt2'):
        u = User.query.filter_by(display_handle=f'drill:{handle}').one()
        ups = FileUpload.query.filter_by(user_id=u.userid).all()
        assert ups and all(x.verification_status == 'REJECTED' for x in ups)


def test_role_cards_cover_every_report(ctx):
    cards = scenario.role_cards()
    assert len(cards) == len(scenario.REPORTS)
    assert sum(1 for c in cards if c['sybil_of']) == 2     # the two Sybil briefs
    assert {c['event'] for c in cards} == {'ALPHA', 'BRAVO', 'CHARLIE', 'DELTA', 'NEARMISS'}


def test_reset_removes_only_drill_data(ctx):
    scenario.simulate(db)
    assert User.query.filter(User.display_handle.like('drill:%')).count() > 0
    res = scenario.reset(db)
    assert res['identities'] > 0 and res['reports'] > 0
    assert User.query.filter(User.display_handle.like('drill:%')).count() == 0
    # every event created by the drill is gone too
    assert Event.query.count() == 0
