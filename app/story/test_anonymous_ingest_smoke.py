"""Smoke test for the anonymous-ingest endpoint.

Boots the app in-memory, posts an anonymous text-only submission,
verifies it lands as PENDING with user_id=NULL, doesn't appear on the
public feed, and DOES appear in the moderation queue. Also exercises
the rate limiter and an attached-media path with a tiny dummy file.
"""

import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PIL import Image  # noqa: E402

from app import create_app, populate_initial_data  # noqa: E402
from app.models import db, FileUpload, User  # noqa: E402


def _tiny_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), 'green').save(buf, format='JPEG')
    return buf.getvalue()


def _register(client, username, email, password):
    resp = client.post('/api/auth/register', json={
        'username': username, 'email': email, 'password': password,
    })
    assert resp.status_code in (200, 201), f'register failed: {resp.status_code} {resp.data}'


def _token_for(client, email, password):
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, f'login failed: {resp.status_code} {resp.data}'
    return resp.get_json()['access_token']


def main():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        populate_initial_data()
    with app.app_context(), app.test_client() as client:
        # Bootstrap a moderator so we can confirm pending anon submissions
        # are visible in the queue.
        _register(client, 'modr', 'modr@test.local', 'Passw0rd!')
        moderator = User.query.filter_by(email='modr@test.local').first()
        moderator.is_moderator = True
        db.session.commit()

        # 1. Text-only anonymous submission
        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={
                'title': 'Witness report — Quarter 9',
                'body': 'Saw smoke rising over the eastern ridge around dawn.',
                'city': 'Testville',
                'severity': 'MEDIUM',
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 201, f'anon ingest failed: {resp.status_code} {resp.data}'
        ack = resp.get_json()
        # Crucial — no id leaked back to the anonymous submitter
        assert 'id' not in ack and 'source_record_id' not in ack
        assert ack.get('pending_review') is True

        # 2. The row exists, has no user_id, and is PENDING
        rows = FileUpload.query.filter_by(source_type='anonymous').all()
        assert len(rows) == 1
        row = rows[0]
        assert row.user_id is None, f'anonymous row leaked user_id: {row.user_id}'
        assert row.verification_status == 'PENDING'
        assert row.title.startswith('Witness report')

        # 3. Does NOT appear on the public feed
        resp = client.get('/api/stories?source=upload')
        ids = [s['source_record_id'] for s in resp.get_json()['items']]
        assert row.id not in ids, f'pending anon leaked publicly: {ids}'

        # 4. Public detail 404s
        resp = client.get(f'/api/stories/upload/{row.id}')
        assert resp.status_code == 404

        # 5. Moderator sees it in the queue
        mod_token = _token_for(client, 'modr@test.local', 'Passw0rd!')
        resp = client.get(
            '/api/moderation/queue',
            headers={'Authorization': f'Bearer {mod_token}'},
        )
        assert resp.status_code == 200
        q_ids = [item['source_record_id'] for item in resp.get_json()['items']]
        assert row.id in q_ids

        # 6. Missing title is rejected
        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={'body': 'no title'},
            content_type='multipart/form-data',
        )
        assert resp.status_code == 400

        # 7. Anonymous submission with a tiny media file works
        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={
                'title': 'Photo evidence',
                'body': 'Attached image',
                'media': (io.BytesIO(_tiny_jpeg_bytes()), 'evidence.jpg'),
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 201, f'anon media ingest failed: {resp.status_code} {resp.data}'
        media_rows = FileUpload.query.filter_by(source_type='anonymous').all()
        assert len(media_rows) == 2
        with_media = next(r for r in media_rows if r.title == 'Photo evidence')
        assert with_media.user_id is None
        assert with_media.file_path  # blob path set
        assert with_media.file_path != 'anonymous:no-media'

        # 8. Idempotency: the same submission_id replays without creating
        # a duplicate row. This is what Android's offline-draft sync
        # depends on — a network blip retrying mid-stream must not create
        # five copies in the moderation queue.
        sub_id = 'test-sub-abcdef0123456789'
        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={'title': 'Offline draft sync', 'submission_id': sub_id},
            content_type='multipart/form-data',
        )
        assert resp.status_code == 201, f'first submission_id post failed: {resp.status_code}'

        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={'title': 'Different title same id', 'submission_id': sub_id},
            content_type='multipart/form-data',
        )
        assert resp.status_code == 200, f'idempotent replay should return 200, got {resp.status_code}'

        same_id_rows = FileUpload.query.filter_by(anon_submission_id=sub_id).all()
        assert len(same_id_rows) == 1, f'idempotency failed — found {len(same_id_rows)} rows for {sub_id}'

        # 9. Rate limit still kicks in. Anon limiter is 5/hour; we've now
        # consumed 5 slots (witness, 400, media, idempotent-1, idempotent-2),
        # so the next call should be blocked.
        resp = client.post(
            '/api/stories/anonymous-ingest',
            data={'title': 'Over the cap'},
            content_type='multipart/form-data',
        )
        assert resp.status_code == 429, f'rate limit not enforced: {resp.status_code}'

    print('OK — anonymous-ingest smoke test passed')


if __name__ == '__main__':
    main()
