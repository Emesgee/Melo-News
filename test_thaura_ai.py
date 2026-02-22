import pytest
import tempfile
import os
from io import BytesIO
from app.ai_analyzer.routes import (
    analyze_image,
    analyze_video,
    extract_keywords_from_text,
    analyze_media
)

class TestThauraAIAnalyzer:
    
    def test_extract_keywords_from_text(self):
        """Test keyword extraction from text"""
        text = "Breaking news from New York about major earthquake damage"
        keywords = extract_keywords_from_text(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert any(keyword in keywords for keyword in ['breaking', 'news', 'earthquake', 'damage'])
    
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction with empty text"""
        keywords = extract_keywords_from_text("")
        assert keywords == []
    
    def test_extract_keywords_only_stopwords(self):
        """Test keyword extraction with only stopwords"""
        text = "the a an in on at to for of and or but"
        keywords = extract_keywords_from_text(text)
        assert keywords == []
    
    def test_analyze_image_fallback(self):
        """Test image analysis fallback when Azure not configured"""
        # When Azure credentials are not set, should return fallback
        result = analyze_image("dummy_image.jpg")
        
        assert result is not None
        assert 'title' in result
        assert 'tags' in result
        assert 'subject' in result
        assert 'city' in result
        assert 'country' in result
        assert 'confidence' in result
    
    def test_analyze_video_fallback(self):
        """Test video analysis fallback when Azure not configured"""
        result = analyze_video("dummy_video.mp4")
        
        assert result is not None
        assert 'title' in result
        assert 'tags' in result
        assert 'subject' in result
        assert 'confidence' in result
    
    def test_analyze_image_returns_required_fields(self):
        """Test that image analysis returns all required fields"""
        result = analyze_image("test.jpg")
        
        required_fields = ['title', 'tags', 'subject', 'city', 'country', 'confidence']
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_analyze_video_returns_required_fields(self):
        """Test that video analysis returns all required fields"""
        result = analyze_video("test.mp4")
        
        required_fields = ['title', 'tags', 'subject', 'city', 'country', 'confidence']
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_confidence_score_range(self):
        """Test that confidence scores are between 0 and 1"""
        image_result = analyze_image("test.jpg")
        video_result = analyze_video("test.mp4")
        
        assert 0 <= image_result['confidence'] <= 1
        assert 0 <= video_result['confidence'] <= 1