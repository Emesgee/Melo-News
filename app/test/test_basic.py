import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Core application package imports cleanly."""
    from app import create_app
    from app.models import db, FileUpload
    assert create_app is not None
    assert db is not None and FileUpload is not None

def test_config_exists():
    """Test config loading"""
    from pathlib import Path
    
    # Check if config.py exists
    config_path = Path(__file__).parent.parent.parent / 'config.py'
    assert config_path.exists(), f"config.py not found at {config_path}"

def test_environment_detection():
    """Test environment variable detection"""
    import os
    
    env = os.getenv('ENVIRONMENT', 'development')
    assert env in ['development', 'production', 'testing']

def test_app_creation(app):
    """Test Flask app creation"""
    assert app is not None
    assert app.config['TESTING'] == True

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
