"""End-to-end smoke test for the moderation queue.

Boots the app in testing mode (in-memory SQLite), creates a reporter,
seeds an unverified citizen upload, and walks it through the moderation
flow:
    - public list/detail must NOT return the pending story
    - non-moderator users hit 403 on the queue
    - a moderator can see + verify it
    - after verify, public list/detail return it
    - reject also works and requires a note
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, populate_initial_data  # noqa: E402
from app.models import db, FileUpload, FileType, User  # noqa: E402


def _seed_upload(user_id, file_type_id, status='PENDING'):
    upload = FileUpload(
        filename='test.jpg',
        file_path='https://example.com/test.jpg',
        title='Smoke test story',
        user_id=user_id,
        file_type_id=file_type_id,
        verification_status=status,
        severity='LOW',
    )
    db.session.add(upload)
    db.session.commit()
    db.session.refresh(upload)
    return upload


def _token_for(client, email, password):
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, f'login failed: {resp.status_code} {resp.data}'
    return resp.get_json()['access_token']


def _register(client, username, email, password):
    resp = client.post('/api/auth/register', json={
        'username': username, 'email': email, 'password': password,
    })
    assert resp.status_code in (200, 201), f'register failed: {resp.status_code} {resp.data}'


def main():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        populate_initial_data()
    with app.app_context(), app.test_client() as client:
        # Bootstrap: register reporter + moderator users
        _register(client, 'reporter', 'reporter@test.local', 'Passw0rd!')
        _register(client, 'modr', 'modr@test.local', 'Passw0rd!')
        moderator = User.query.filter_by(email='modr@test.local').first()
        reporter = User.query.filter_by(email='reporter@test.local').first()
        assert moderator and reporter
        moderator.role = 'moderator'
        db.session.commit()

        ft = FileType.query.filter_by(type_name='Image').first()
        assert ft is not None, 'Image FileType should be seeded by populate_initial_data'

        upload = _seed_upload(reporter.userid, ft.filetypeid, status='PENDING')

        # 1. Public list should NOT include pending upload
        resp = client.get('/api/stories?source=upload')
        body = resp.get_json()
        ids = [s['source_record_id'] for s in body['items']]
        assert upload.id not in ids, f'pending upload leaked to public list: {ids}'

        # 2. Public detail should 404 the pending upload
        resp = client.get(f'/api/stories/upload/{upload.id}')
        assert resp.status_code == 404, f'pending upload visible publicly: {resp.status_code}'

        # 3. Non-moderator hits 403 on the queue
        reporter_token = _token_for(client, 'reporter@test.local', 'Passw0rd!')
        resp = client.get(
            '/api/moderation/queue',
            headers={'Authorization': f'Bearer {reporter_token}'},
        )
        assert resp.status_code == 403, f'non-moderator got access: {resp.status_code} {resp.data}'

        # 4. Moderator sees the upload in the queue
        mod_token = _token_for(client, 'modr@test.local', 'Passw0rd!')
        resp = client.get(
            '/api/moderation/queue',
            headers={'Authorization': f'Bearer {mod_token}'},
        )
        assert resp.status_code == 200, f'queue failed: {resp.status_code} {resp.data}'
        q_ids = [item['source_record_id'] for item in resp.get_json()['items']]
        assert upload.id in q_ids, f'pending upload not in queue: {q_ids}'

        # 5. Reject requires a note
        resp = client.post(
            f'/api/moderation/{upload.id}/reject',
            headers={'Authorization': f'Bearer {mod_token}'},
            json={},
        )
        assert resp.status_code == 422, f'reject without note should 422, got {resp.status_code}'

        # 6. Verify the upload and check it now appears publicly
        resp = client.post(
            f'/api/moderation/{upload.id}/verify',
            headers={'Authorization': f'Bearer {mod_token}'},
            json={'note': 'Looks legit'},
        )
        assert resp.status_code == 200, f'verify failed: {resp.status_code} {resp.data}'
        verified = resp.get_json()
        assert verified['workflow']['verification_status'] == 'VERIFIED'

        resp = client.get('/api/stories?source=upload')
        ids = [s['source_record_id'] for s in resp.get_json()['items']]
        assert upload.id in ids, f'verified upload missing from public list: {ids}'

        resp = client.get(f'/api/stories/upload/{upload.id}')
        assert resp.status_code == 200, f'verified upload still 404 publicly: {resp.status_code}'

        # 7. Reject a separate upload (with a note this time) flows through
        upload2 = _seed_upload(reporter.userid, ft.filetypeid, status='PENDING')
        resp = client.post(
            f'/api/moderation/{upload2.id}/reject',
            headers={'Authorization': f'Bearer {mod_token}'},
            json={'note': 'Could not verify location'},
        )
        assert resp.status_code == 200
        rejected = resp.get_json()
        assert rejected['workflow']['verification_status'] == 'REJECTED'
        assert rejected['workflow']['verification_note'] == 'Could not verify location'

        # 8. Rejected stays out of the public feed too
        resp = client.get(f'/api/stories/upload/{upload2.id}')
        assert resp.status_code == 404

    print('OK — moderation queue smoke test passed')


if __name__ == '__main__':
    main()
