# app/test/test_story_ingest.py
"""
Tests for POST /api/stories/ingest — field-reporter (Android) ingestion endpoint.
"""

import json
import pytest

from app import create_app, db
from app.models import User, FileType, FileUpload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    application = create_app(config_name='testing')
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="module")
def _seed(app):
    """Create a user + default FileType once for the whole module."""
    with app.app_context():
        user = User(username='reporter', email='reporter@test.local', password='hashed')
        db.session.add(user)
        file_type = FileType(type_name='Image', allowed_extensions='jpg,jpeg,png')
        db.session.add(file_type)
        db.session.commit()
        yield {'user_id': user.userid, 'file_type_id': file_type.filetypeid}


@pytest.fixture(scope="module")
def auth_token(app, _seed):
    """JWT for the seeded user (identity must be a string, matching auth routes)."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        return create_access_token(identity=str(_seed['user_id']))


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _pin_azure_backend(monkeypatch):
    """These media-token tests mock the Azure handler, so pin the backend to
    'azure'. Otherwise a local .env STORAGE_BACKEND=s3 routes the endpoint to
    the S3 handler and the Azure mocks never fire (ADR-0017)."""
    import config
    monkeypatch.setattr(config, 'STORAGE_BACKEND', 'azure', raising=False)


def _post(client, token, payload):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    return client.post(
        '/api/stories/ingest',
        data=json.dumps(payload),
        content_type='application/json',
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStoryIngestAuth:
    """Authentication guards."""

    def test_missing_jwt_returns_401(self, client, _seed):
        resp = _post(client, token=None, payload={'title': 'Test'})
        assert resp.status_code == 401

    def test_invalid_jwt_returns_4xx(self, client, _seed):
        # Flask-JWT-Extended returns 422 for a malformed token, 401 for missing
        resp = _post(client, token='not.a.real.token', payload={'title': 'Test'})
        assert resp.status_code in (401, 422)


class TestStoryIngestValidation:
    """Input validation."""

    def test_no_body_returns_400(self, client, auth_token, _seed):
        resp = client.post(
            '/api/stories/ingest',
            data='not json',
            content_type='text/plain',
            headers={'Authorization': f'Bearer {auth_token}'},
        )
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_missing_title_returns_422(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {'city': 'Rafah'})
        assert resp.status_code == 422
        data = resp.get_json()
        assert 'title' in data['error'].lower()

    def test_empty_title_returns_422(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {'title': '   '})
        assert resp.status_code == 422


class TestStoryIngestSuccess:
    """Happy-path and field mapping."""

    def test_minimal_payload_returns_201(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {'title': 'Breaking: minimal test'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['id'].startswith('upload:')
        assert data['title'] == 'Breaking: minimal test'

    def test_full_payload_fields_mapped(self, client, auth_token, _seed):
        payload = {
            'title': 'Airstrike near Rafah border',
            'body': 'Three explosions at 14:30 local time.',
            'tags': ['airstrike', 'rafah'],
            'city': 'Rafah',
            'country': 'Palestine',
            'lat': 31.28,
            'lon': 34.25,
            'severity': 'HIGH',
            'media_url': 'https://example.com/clip.mp4',
            'source_name': 'Field Reporter',
        }
        resp = _post(client, auth_token, payload)
        assert resp.status_code == 201
        data = resp.get_json()

        assert data['title'] == payload['title']
        assert data['location']['city'] == 'Rafah'
        assert data['location']['country'] == 'Palestine'
        assert data['location']['lat'] == pytest.approx(31.28)
        assert data['location']['lon'] == pytest.approx(34.25)
        assert data['metrics']['severity'] == 'HIGH'
        assert data['media']['primary_url'] == payload['media_url']
        assert data['provenance']['source_type_detail'] == 'Field Reporter'

    def test_tags_as_list_stored(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {
            'title': 'Tag list test',
            'tags': ['alpha', 'beta', 'gamma'],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        # tags stored as comma-separated string, normalized to list in story shape
        assert 'alpha' in data.get('tags', [])

    def test_invalid_severity_coerces_to_low(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {
            'title': 'Bad severity test',
            'severity': 'EXTREME',
        })
        assert resp.status_code == 201
        assert resp.get_json()['metrics']['severity'] == 'LOW'

    def test_published_at_override(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {
            'title': 'Backdated story',
            'published_at': '2025-01-15T10:30:00Z',
        })
        assert resp.status_code == 201
        ts = resp.get_json()['timestamps']['published_at']
        assert '2025' in ts

    def test_response_shape_has_required_keys(self, client, auth_token, _seed):
        resp = _post(client, auth_token, {'title': 'Shape check'})
        assert resp.status_code == 201
        data = resp.get_json()
        for key in ('id', 'title', 'location', 'media', 'metrics', 'timestamps', 'provenance'):
            assert key in data, f"missing key: {key}"


# ---------------------------------------------------------------------------
# GET /api/stories/ingest/media-token
# ---------------------------------------------------------------------------

def _get_token(client, auth_token, ext=None):
    url = '/api/stories/ingest/media-token'
    if ext is not None:
        url += f'?ext={ext}'
    headers = {'Authorization': f'Bearer {auth_token}'} if auth_token else {}
    return client.get(url, headers=headers)


class TestMediaTokenAuth:
    def test_missing_jwt_returns_401(self, client, _seed):
        resp = _get_token(client, auth_token=None, ext='mp4')
        assert resp.status_code == 401


class TestMediaTokenValidation:
    def test_missing_ext_returns_400(self, client, auth_token, _seed):
        resp = _get_token(client, auth_token, ext=None)
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_unsupported_ext_returns_422(self, client, auth_token, _seed):
        resp = _get_token(client, auth_token, ext='exe')
        assert resp.status_code == 422
        assert 'unsupported' in resp.get_json()['error']

    def test_ext_with_leading_dot_accepted(self, client, auth_token, _seed):
        """Leading dot should be stripped — '.mp4' == 'mp4'."""
        from unittest.mock import patch
        fake_result = {
            'upload_url': 'https://blob.example.com/up?sas=x',
            'blob_url': 'https://blob.example.com/up',
            'blob_name': 'field-reports/1/abc.mp4',
            'expires_at': '2026-01-01T00:00:00+00:00',
        }
        with patch('modules.azure_handler.generate_sas_upload_url', return_value=fake_result):
            resp = _get_token(client, auth_token, ext='.mp4')
        assert resp.status_code == 200


class TestMediaTokenSuccess:
    """Happy-path tests use a mock so no real Azure credentials are needed."""

    FAKE_RESULT = {
        'upload_url': 'https://mystorage.blob.core.windows.net/uploads/field-reports/1/abc123.mp4?sv=2023&sig=x',
        'blob_url':   'https://mystorage.blob.core.windows.net/uploads/field-reports/1/abc123.mp4',
        'blob_name':  'field-reports/1/abc123.mp4',
        'expires_at': '2026-01-01T00:15:00+00:00',
    }

    def _call(self, client, auth_token, ext='mp4'):
        from unittest.mock import patch
        with patch('modules.azure_handler.generate_sas_upload_url', return_value=self.FAKE_RESULT):
            return _get_token(client, auth_token, ext=ext)

    def test_returns_200(self, client, auth_token, _seed):
        resp = self._call(client, auth_token)
        assert resp.status_code == 200

    def test_response_has_required_keys(self, client, auth_token, _seed):
        resp = self._call(client, auth_token)
        data = resp.get_json()
        for key in ('upload_url', 'blob_url', 'blob_name', 'expires_at'):
            assert key in data, f"missing key: {key}"

    def test_blob_name_scoped_to_user(self, client, auth_token, _seed):
        """blob_name must contain the user's ID so blobs are namespaced."""
        from unittest.mock import patch, call
        captured = {}

        def _capture(blob_name, **kwargs):
            captured['blob_name'] = blob_name
            return self.FAKE_RESULT

        with patch('modules.azure_handler.generate_sas_upload_url', side_effect=_capture):
            _get_token(client, auth_token, ext='jpg')

        assert str(_seed['user_id']) in captured['blob_name']
        assert captured['blob_name'].endswith('.jpg')

    def test_video_ext_accepted(self, client, auth_token, _seed):
        resp = self._call(client, auth_token, ext='mov')
        assert resp.status_code == 200

    def test_image_ext_accepted(self, client, auth_token, _seed):
        resp = self._call(client, auth_token, ext='png')
        assert resp.status_code == 200

    def test_audio_ext_accepted(self, client, auth_token, _seed):
        resp = self._call(client, auth_token, ext='aac')
        assert resp.status_code == 200

    def test_azure_not_configured_returns_503(self, client, auth_token, _seed):
        from unittest.mock import patch
        with patch(
            'modules.azure_handler.generate_sas_upload_url',
            side_effect=RuntimeError('Azure Storage is not configured'),
        ):
            resp = _get_token(client, auth_token, ext='mp4')
        assert resp.status_code == 503
        assert 'error' in resp.get_json()

