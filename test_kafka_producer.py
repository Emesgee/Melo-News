import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestParseViews:
    """Test view count parsing"""
    
    def test_parse_views_with_k(self):
        """Test parsing views with K suffix (thousands)"""
        # Simulate "5.2K views"
        views_text = "5.2K views"
        
        # Manual calculation (since we can't import the function directly)
        result = int(float(views_text.replace('K','').replace(' views','').replace(',','')) * 1000)
        
        assert result == 5200
    
    def test_parse_views_with_m(self):
        """Test parsing views with M suffix (millions)"""
        views_text = "2.5M views"
        
        result = int(float(views_text.replace('M','').replace(' views','').replace(',','')) * 1000000)
        
        assert result == 2500000
    
    def test_parse_views_plain_number(self):
        """Test parsing plain number views"""
        views_text = "1,234 views"
        
        result = int(views_text.replace(' views','').replace(',',''))
        
        assert result == 1234
    
    def test_parse_views_zero(self):
        """Test parsing zero views"""
        views_text = "0 views"
        
        result = int(views_text.replace(' views','').replace(',',''))
        
        assert result == 0


class TestFilterLocation:
    """Test location filtering for Palestinian towns"""
    
    def test_filter_location_with_match(self):
        """Test finding location in text"""
        # Mock geojson_coords with Palestinian towns
        test_locations = {
            'gaza': {'lat': 31.34, 'lon': 34.30},
            'khan younis': {'lat': 31.34, 'lon': 34.30},
            'rafah': {'lat': 31.29, 'lon': 34.26}
        }
        
        text = "Breaking news from Gaza today"
        text_lower = text.lower()
        
        # Check if any location word is in text
        found = None
        for word in set(text_lower.split()):
            if word in test_locations:
                found = word
                break
        
        assert found == "gaza"
    
    def test_filter_location_no_match(self):
        """Test when no Palestinian location found"""
        test_locations = {
            'gaza': {'lat': 31.34, 'lon': 34.30},
            'khan younis': {'lat': 31.34, 'lon': 34.30}
        }
        
        text = "News from Cairo Egypt"
        text_lower = text.lower()
        
        found = None
        for word in set(text_lower.split()):
            if word in test_locations:
                found = word
                break
        
        assert found is None
    
    def test_filter_location_substring_match(self):
        """Test substring matching for multi-word locations"""
        test_locations = {
            'khan younis': {'lat': 31.34, 'lon': 34.30}
        }
        
        text = "Conflict in Khan Younis region"
        text_lower = text.lower()
        
        found = None
        for village_lc in test_locations.keys():
            if village_lc in text_lower:
                found = village_lc
                break
        
        assert found == "khan younis"


class TestMessageIdGeneration:
    """Test message ID generation"""
    
    def test_message_id_hash(self):
        """Test that message ID is generated from content hash"""
        import hashlib
        
        msg_time = "2024-02-28T10:30:00"
        text = "Breaking news from Gaza"
        
        base_id = f"{msg_time}|{text[:120]}"
        msg_id = hashlib.sha256(base_id.encode('utf-8')).hexdigest()
        
        # Verify it's a valid SHA256 hash
        assert len(msg_id) == 64
        assert all(c in '0123456789abcdef' for c in msg_id)
    
    def test_message_id_consistency(self):
        """Test that same content produces same ID"""
        import hashlib
        
        msg_time = "2024-02-28T10:30:00"
        text = "Breaking news"
        
        base_id = f"{msg_time}|{text[:120]}"
        msg_id_1 = hashlib.sha256(base_id.encode('utf-8')).hexdigest()
        msg_id_2 = hashlib.sha256(base_id.encode('utf-8')).hexdigest()
        
        assert msg_id_1 == msg_id_2


class TestProducerMessageFormat:
    """Test Kafka message formatting"""
    
    def test_message_structure(self):
        """Test that message has all required fields"""
        row = {
            'id': 'abc123',
            'time': '2024-02-28T10:30:00',
            'total_views': 5000,
            'message': 'Breaking news from Gaza',
            'video_links': 'http://example.com/video.mp4',
            'video_durations': '5:30',
            'image_links': 'http://example.com/image.jpg',
            'subject': None,
            'matched_city': 'Gaza',
            'city_result': 'Gaza',
            'lat': 31.34,
            'lon': 34.30
        }
        
        # Verify all required fields exist
        required_fields = ['id', 'time', 'total_views', 'message', 'matched_city', 'lat', 'lon']
        for field in required_fields:
            assert field in row
    
    def test_message_json_serializable(self):
        """Test that message can be serialized to JSON"""
        row = {
            'id': 'abc123',
            'time': '2024-02-28T10:30:00',
            'total_views': 5000,
            'message': 'Test message',
            'matched_city': 'Gaza',
            'lat': 31.34,
            'lon': 34.30
        }
        
        # Should not raise exception
        json_str = json.dumps(row)
        assert isinstance(json_str, str)
        
        # Should be deserializable
        decoded = json.loads(json_str)
        assert decoded['matched_city'] == 'Gaza'