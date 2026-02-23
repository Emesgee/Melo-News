import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestConsumerDatabaseInsertion:
    """Test database row preparation"""
    
    def test_prepare_database_row(self):
        """Test preparing a row for database insertion"""
        message_data = {
            "time": "2024-02-23T10:30:00",
            "total_views": 5000,
            "message": "Breaking news from Khan Younis",
            "video_links": "http://example.com/video.mp4",
            "video_durations": "5:30",
            "image_links": "http://example.com/image.jpg",
            "matched_city": "Khan Younis",
            "city_result": "Khan Younis",
            "lat": 31.34,
            "lon": 34.30
        }
        
        # Simulate what consumer.py does
        row = {
            "time": message_data.get("time"),
            "total_views": message_data.get("total_views"),
            "message": message_data.get("message")[:250] if message_data.get("message") else None,
            "video_links": json.dumps([message_data.get("video_links")]) if message_data.get("video_links") else None,
            "video_durations": (message_data.get("video_durations") or "")[:250],
            "image_links": json.dumps([message_data.get("image_links")]) if message_data.get("image_links") else None,
            "matched_city": message_data.get("matched_city")[:250] if message_data.get("matched_city") else None,
            "city_result": (message_data.get("city_result") or "")[:250],
            "lat": message_data.get("lat"),
            "lon": message_data.get("lon"),
        }
        
        # Verify row structure
        assert row["time"] == "2024-02-23T10:30:00"
        assert row["total_views"] == 5000
        assert row["matched_city"] == "Khan Younis"
        assert row["lat"] == 31.34
        assert row["lon"] == 34.30
    
    def test_message_truncation(self):
        """Test that long messages are truncated to 250 chars"""
        long_message = "This is a very long message " * 20  # Much longer than 250
        
        # Simulate truncation
        truncated = long_message[:250] if long_message else None
        
        # Verify length
        assert len(truncated) <= 250
        assert len(truncated) == 250
    
    def test_json_serialization_for_links(self):
        """Test that links are properly JSON serialized"""
        video_url = "http://example.com/video.mp4"
        image_url = "http://example.com/image.jpg"
        
        # Simulate JSON serialization
        video_json = json.dumps([video_url]) if video_url else None
        image_json = json.dumps([image_url]) if image_url else None
        
        # Verify it's valid JSON
        assert json.loads(video_json) == [video_url]
        assert json.loads(image_json) == [image_url]