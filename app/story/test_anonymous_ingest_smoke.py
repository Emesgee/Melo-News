"""Pytest tests for the anonymous-ingest endpoint.

Boots the full app in-memory (blueprints + rate limiter) and exercises the
anonymous submission path: a report lands as PENDING with user_id=NULL, never
leaks an id back, stays off the public feed, shows up in the moderation queue,
validates its input, stores attached media, is idempotent on a submission_id
replay, and is rate-limited.

The anonymous endpoint is DISABLED by default for the pilot (ADR-0007); each
test enables it on its own app instance.

Isolation note: every test gets a FRESH app via the function-scoped `client`
fixture. That is deliberate — the anonymous rate limiter (5/hour) keeps per-app
counters, so a shared app would let one test's POSTs bleed into another's limit
accounting and make `test_rate_limit_enforced` flaky.
"""

import io

import pytest
from PIL import Image

from app import create_app, populate_initial_data
from app.models import db, FileUpload, User

ANON_INGEST = '/api/stories/anonymous-ingest'


@pytest.fixture
def client():
    """Fresh full app (anon-ingest enabled) + in-memory DB + test client, one
    per test so the rate limiter and DB never bleed across tests."""
    app = create_app('testing')
    app.config['ANONYMOUS_INGEST_ENABLED'] = True
    with app.app_context():
        db.create_all()
        populate_initial_data()
        with app.test_client() as c:
            yield c
        db.session.remove()
        db.drop_all()


def _tiny_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), 'green').save(buf, format='JPEG')
    return buf.getvalue()


def _post_anon(client, **data):
    return client.post(ANON_INGEST, data=data, content_type='multipart/form-data')


def _moderator_token(client):
    """Register a user, promote them to moderator, and return a bearer token."""
    resp = client.post('/api/auth/register', json={
        'username': 'modr', 'email': 'modr@test.local', 'password': 'Passw0rd!',
    })
    assert resp.status_code in (200, 201), f'register failed: {resp.status_code} {resp.data}'
    moderator = User.query.filter_by(email='modr@test.local').first()
    moderator.role = 'moderator'
    db.session.commit()
    resp = client.post('/api/auth/login', json={'email': 'modr@test.local', 'password': 'Passw0rd!'})
    assert resp.status_code == 200, f'login failed: {resp.status_code} {resp.data}'
    return resp.get_json()['access_token']


def test_anonymous_text_submission_lands_pending_and_hidden(client):
    resp = _post_anon(
        client,
        title='Witness report — Quarter 9',
        body='Saw smoke rising over the eastern ridge around dawn.',
        city='Testville', severity='MEDIUM',
    )
    assert resp.status_code == 201, f'anon ingest failed: {resp.status_code} {resp.data}'
    ack = resp.get_json()
    # Crucial — no id leaked back to the anonymous submitter.
    assert 'id' not in ack and 'source_record_id' not in ack
    assert ack.get('pending_review') is True

    # The row exists, has no user_id, and is PENDING.
    rows = FileUpload.query.filter_by(source_type='anonymous').all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id is None, f'anonymous row leaked user_id: {row.user_id}'
    assert row.verification_status == 'PENDING'
    assert row.title.startswith('Witness report')

    # Does NOT appear on the public feed.
    resp = client.get('/api/stories?source=upload')
    ids = [s['source_record_id'] for s in resp.get_json()['items']]
    assert row.id not in ids, f'pending anon leaked publicly: {ids}'

    # Public detail 404s.
    resp = client.get(f'/api/stories/upload/{row.id}')
    assert resp.status_code == 404


def test_moderator_sees_pending_anonymous_in_queue(client):
    resp = _post_anon(client, title='Witness report — Quarter 9', body='smoke', city='Testville')
    assert resp.status_code == 201
    row = FileUpload.query.filter_by(source_type='anonymous').one()

    mod_token = _moderator_token(client)
    resp = client.get('/api/moderation/queue', headers={'Authorization': f'Bearer {mod_token}'})
    assert resp.status_code == 200
    q_ids = [item['source_record_id'] for item in resp.get_json()['items']]
    assert row.id in q_ids


def test_missing_title_rejected(client):
    resp = _post_anon(client, body='no title')
    assert resp.status_code == 400


def test_anonymous_media_submission_stores_blob(client):
    resp = client.post(
        ANON_INGEST,
        data={
            'title': 'Photo evidence', 'body': 'Attached image',
            'media': (io.BytesIO(_tiny_jpeg_bytes()), 'evidence.jpg'),
        },
        content_type='multipart/form-data',
    )
    assert resp.status_code == 201, f'anon media ingest failed: {resp.status_code} {resp.data}'
    with_media = FileUpload.query.filter_by(source_type='anonymous', title='Photo evidence').one()
    assert with_media.user_id is None
    assert with_media.file_path and with_media.file_path != 'anonymous:no-media'


def test_idempotent_submission_id_replays(client):
    # Android's offline-draft sync depends on this — a network blip retrying
    # mid-stream must not create five copies in the moderation queue.
    sub_id = 'test-sub-abcdef0123456789'
    resp = _post_anon(client, title='Offline draft sync', submission_id=sub_id)
    assert resp.status_code == 201, f'first submission_id post failed: {resp.status_code}'

    resp = _post_anon(client, title='Different title same id', submission_id=sub_id)
    assert resp.status_code == 200, f'idempotent replay should return 200, got {resp.status_code}'

    same_id_rows = FileUpload.query.filter_by(anon_submission_id=sub_id).all()
    assert len(same_id_rows) == 1, f'idempotency failed — found {len(same_id_rows)} rows for {sub_id}'


def test_rate_limit_enforced(client):
    # Anon limiter is 5/hour. The limiter counts every request that reaches the
    # decorator, including validation 400s, so five POSTs consume the window and
    # the sixth is blocked regardless of its payload.
    for i in range(5):
        resp = _post_anon(client, title=f'submission {i}')
        assert resp.status_code != 429, f'unexpected early rate limit at post {i}: {resp.data}'

    resp = _post_anon(client, title='Over the cap')
    assert resp.status_code == 429, f'rate limit not enforced: {resp.status_code}'
