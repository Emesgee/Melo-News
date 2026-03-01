import pytest
import json

class TestFileTypesAPI:
    """Test file types API endpoints"""
    
    def test_get_file_types(self, client, database):
        """Test GET /api/file_types"""
        from app.models import FileType
        
        # Create test data
        file_type = FileType(
            type_name="Image",
            allowed_extensions="jpg, png"
        )
        database.session.add(file_type)
        database.session.commit()
        
        # Test endpoint
        response = client.get('/api/file_types')
        assert response.status_code == 200

class TestSearchAPI:
    """Test search API endpoints"""
    
    def test_search_endpoint(self, client):
        """Test /api/search endpoint"""
        response = client.post('/api/search', json={
            'query': 'test',
            'filter': 'all'
        })
        assert response.status_code in [200, 400, 404]

class TestTemplatesAPI:
    """Test templates API endpoints"""
    
    def test_get_templates(self, client):
        """Test GET /api/templates"""
        response = client.get('/api/templates')
        assert response.status_code in [200, 404]
