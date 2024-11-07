# tests/test_auth.py

import pytest
from app import create_app, db
from flask import url_for

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database for testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Setup the database
        yield client
        with app.app_context():
            db.drop_all()  # Clean up after each test

def test_register_user(client):
    # Test the user registration endpoint
    response = client.post('/auth/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert response.get_json()['message'] == "User registered successfully!"

def test_login_user(client):
    # First register a user
    client.post('/auth/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })

    # Then test the login endpoint
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.get_json()
