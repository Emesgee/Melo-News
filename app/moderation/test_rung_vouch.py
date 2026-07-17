"""Steward rung-vouch tests, incl. the ADR-0016 vouch-by-handle bootstrap.

A tester registers a device (self-registering a pseudonym at rung 1) and reads
their `k-xxxx` handle off the phone; the steward vouches that handle to rung 2
without first resolving a numeric id.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, populate_initial_data  # noqa: E402
from app.models import db, User  # noqa: E402


def _register(client, username, email, password):
    r = client.post('/api/auth/register', json={
        'username': username, 'email': email, 'password': password,
    })
    assert r.status_code in (200, 201), f'register failed: {r.status_code} {r.data}'


def _token(client, email, password):
    r = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert r.status_code == 200, f'login failed: {r.status_code} {r.data}'
    return r.get_json()['access_token']


def _steward_client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        populate_initial_data()
    ctx = app.app_context()
    ctx.push()
    client = app.test_client()
    _register(client, 'stew', 'stew@test.local', 'Passw0rd!')
    User.query.filter_by(email='stew@test.local').first().role = 'steward'
    db.session.commit()
    token = _token(client, 'stew@test.local', 'Passw0rd!')
    return client, token


def _mk_pseudonym(handle='k-abc123def'):
    u = User(display_handle=handle, identity_type='pseudonymous', role='reporter',
             trust_rung=1, public_key=f'PK-{handle}')
    db.session.add(u)
    db.session.commit()
    return u


def test_vouch_by_handle_sets_rung():
    client, token = _steward_client()
    _mk_pseudonym('k-abc123def')
    hdr = {'Authorization': f'Bearer {token}'}

    r = client.post('/api/moderation/pseudonyms/k-abc123def/rung', headers=hdr, json={'rung': 2})
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body['handle'] == 'k-abc123def' and body['trust_rung'] == 2
    assert User.query.filter_by(display_handle='k-abc123def').first().trust_rung == 2


def test_vouch_by_handle_unknown_is_404():
    client, token = _steward_client()
    r = client.post('/api/moderation/pseudonyms/k-nope/rung',
                    headers={'Authorization': f'Bearer {token}'}, json={'rung': 2})
    assert r.status_code == 404


def test_vouch_by_handle_bad_rung_is_422():
    client, token = _steward_client()
    _mk_pseudonym('k-badrung99')
    r = client.post('/api/moderation/pseudonyms/k-badrung99/rung',
                    headers={'Authorization': f'Bearer {token}'}, json={'rung': 9})
    assert r.status_code == 422


def test_vouch_by_handle_requires_steward():
    client, _ = _steward_client()
    _register(client, 'plainreporter', 'rep@test.local', 'Passw0rd!')
    _mk_pseudonym('k-guarded01')
    rep_token = _token(client, 'rep@test.local', 'Passw0rd!')
    r = client.post('/api/moderation/pseudonyms/k-guarded01/rung',
                    headers={'Authorization': f'Bearer {rep_token}'}, json={'rung': 2})
    assert r.status_code == 403
