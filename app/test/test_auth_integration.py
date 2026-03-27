"""Integration tests for auth API endpoints."""
import pytest
from app import create_app
from app.models import db, User


@pytest.fixture
def app():
    """Create test application."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestRegistration:
    """Test POST /api/auth/register."""

    def test_register_success(self, client):
        resp = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPass1!'
        })
        assert resp.status_code == 201
        assert resp.json['message'] == 'User registered successfully!'

    def test_register_missing_fields(self, client):
        resp = client.post('/api/auth/register', json={'email': 'a@b.com'})
        assert resp.status_code == 400

    def test_register_weak_password(self, client):
        resp = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'short'
        })
        assert resp.status_code == 400
        assert 'Password' in resp.json['error']

    def test_register_duplicate_email(self, client):
        data = {
            'username': 'user1',
            'email': 'dup@example.com',
            'password': 'StrongPass1!'
        }
        client.post('/api/auth/register', json=data)
        resp = client.post('/api/auth/register', json=data)
        assert resp.status_code == 409


class TestLogin:
    """Test POST /api/auth/login."""

    def _register(self, client):
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'login@example.com',
            'password': 'StrongPass1!'
        })

    def test_login_success(self, client):
        self._register(client)
        resp = client.post('/api/auth/login', json={
            'email': 'login@example.com',
            'password': 'StrongPass1!'
        })
        assert resp.status_code == 200
        assert 'access_token' in resp.json

    def test_login_wrong_password(self, client):
        self._register(client)
        resp = client.post('/api/auth/login', json={
            'email': 'login@example.com',
            'password': 'WrongPass1!'
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post('/api/auth/login', json={
            'email': 'nobody@example.com',
            'password': 'StrongPass1!'
        })
        assert resp.status_code == 401


class TestLogout:
    """Test POST /api/auth/logout."""

    def test_logout(self, client):
        resp = client.post('/api/auth/logout')
        assert resp.status_code == 200


class TestHealthCheck:
    """Test GET /api/health."""

    def test_health(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        assert resp.json['status'] == 'healthy'
