import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    import os
    os.environ['ENVIRONMENT'] = 'testing'
    
    from app import create_app, db
    
    app = create_app(config_name='testing')
    return app

@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope="function")
def runner(app):
    """Create CLI runner"""
    return app.test_cli_runner()

@pytest.fixture(scope="function")
def database(app):
    """Set up and tear down test database"""
    from app import db
    
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()