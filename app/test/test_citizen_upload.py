# app/test/test_citizen_upload.py
"""
Tests for the citizen journalism AI-assisted upload pipeline.

Covers:
- EXIF metadata extraction
- Whisper transcription (mocked API)
- Video keyframe extraction
- AI analyzer /analyze endpoint (mocked GPT-4o)
- Geocode proxy endpoint
- Confidence scoring for citizen uploads
"""

import importlib.util
import io
import json
import os
import struct
import tempfile
from unittest.mock import patch, MagicMock

import pytest

# `openai` is an optional dependency (the app has pivoted away from AI features,
# ADR-0019). Detect it without importing so the guard is cheap, and use skipif —
# not an in-body importorskip — because the @patch('openai.OpenAI') decorator
# resolves openai at call time, before any test body runs.
_HAS_OPENAI = importlib.util.find_spec("openai") is not None


# ── EXIF Extractor Tests ────────────────────────────────────────────────

class TestExifExtractor:
    """Test EXIF metadata extraction from images."""

    def test_extract_exif_no_exif(self, tmp_path):
        """A plain image with no EXIF returns empty results."""
        from app.ai_analyzer.exif_extractor import extract_exif

        # Create a minimal valid JPEG (no EXIF)
        img_path = str(tmp_path / "no_exif.jpg")
        try:
            from PIL import Image
            img = Image.new('RGB', (10, 10), color='red')
            img.save(img_path, 'JPEG')
        except ImportError:
            pytest.skip("Pillow not installed")

        result = extract_exif(img_path)

        assert result['lat'] is None
        assert result['lon'] is None
        assert result['has_gps'] is False
        assert result['has_timestamp'] is False

    def test_extract_exif_with_gps(self, tmp_path):
        """Image with GPS EXIF data extracts coordinates correctly."""
        from app.ai_analyzer.exif_extractor import extract_exif

        try:
            from PIL import Image
            import piexif
        except ImportError:
            # Test with mock if piexif not available
            pytest.skip("piexif not installed — testing with mock instead")

        img_path = str(tmp_path / "gps_photo.jpg")
        img = Image.new('RGB', (10, 10), color='blue')

        # Create EXIF with GPS data (Gaza: 31.5, 34.47)
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b'N',
            piexif.GPSIFD.GPSLatitude: ((31, 1), (30, 1), (0, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b'E',
            piexif.GPSIFD.GPSLongitude: ((34, 1), (28, 1), (12, 1)),
        }
        exif_dict = {'GPS': gps_ifd}
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, 'JPEG', exif=exif_bytes)

        result = extract_exif(img_path)
        assert result['has_gps'] is True
        assert result['lat'] is not None
        assert result['lon'] is not None
        assert 31.0 < result['lat'] < 32.0
        assert 34.0 < result['lon'] < 35.0

    def test_extract_exif_nonexistent_file(self):
        """Non-existent file returns empty result without crashing."""
        from app.ai_analyzer.exif_extractor import extract_exif

        result = extract_exif("/nonexistent/photo.jpg")
        assert result['lat'] is None
        assert result['has_gps'] is False

    def test_parse_exif_datetime(self):
        """EXIF datetime strings parse correctly to ISO format."""
        from app.ai_analyzer.exif_extractor import _parse_exif_datetime

        assert _parse_exif_datetime("2024:03:15 14:30:00") is not None
        assert "2024-03-15" in _parse_exif_datetime("2024:03:15 14:30:00")
        assert _parse_exif_datetime("") is None
        assert _parse_exif_datetime(None) is None

    def test_dms_to_decimal(self):
        """DMS GPS coordinates convert to decimal correctly."""
        from app.ai_analyzer.exif_extractor import _dms_to_decimal

        # 31°30'0" N = 31.5
        assert abs(_dms_to_decimal((31, 30, 0), 'N') - 31.5) < 0.001
        # 34°28'12" E = 34.47
        assert abs(_dms_to_decimal((34, 28, 12), 'E') - 34.47) < 0.001
        # Southern hemisphere
        assert _dms_to_decimal((31, 30, 0), 'S') < 0
        # Invalid input
        assert _dms_to_decimal(None, 'N') is None


# ── Transcriber Tests ───────────────────────────────────────────────────

class TestTranscriber:
    """Test Whisper and Azure Speech transcription."""

    @pytest.mark.skipif(not _HAS_OPENAI, reason="openai not installed (optional AI dep)")
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_whisper_transcription(self, mock_openai_cls, tmp_path):
        """Whisper API returns structured transcription."""
        from app.ai_analyzer.transcriber import transcribe_with_whisper

        # Mock the Whisper response
        mock_response = MagicMock()
        mock_response.text = "Bombing in northern Gaza reported near hospital"
        mock_response.language = "en"
        mock_response.duration = 12.5
        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 5.0
        mock_seg.text = "Bombing in northern Gaza"
        mock_response.segments = [mock_seg]

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        # Create a small temp wav file
        audio_path = str(tmp_path / "test.wav")
        with open(audio_path, 'wb') as f:
            f.write(b'\x00' * 1000)

        result = transcribe_with_whisper(audio_path)

        assert result['text'] == "Bombing in northern Gaza reported near hospital"
        assert result['language'] == 'en'
        assert result['method'] == 'whisper'
        assert result['duration'] == 12.5
        assert len(result['segments']) == 1

    def test_whisper_no_api_key(self, tmp_path):
        """Without API key, returns empty result."""
        from app.ai_analyzer.transcriber import transcribe_with_whisper

        audio_path = str(tmp_path / "test.wav")
        with open(audio_path, 'wb') as f:
            f.write(b'\x00' * 100)

        with patch.dict(os.environ, {}, clear=True):
            # Ensure no key is set
            os.environ.pop('OPENAI_API_KEY', None)
            os.environ.pop('AZURE_OPENAI_KEY', None)
            result = transcribe_with_whisper(audio_path)

        assert result['text'] == ''
        assert result['method'] == 'none'

    def test_transcribe_entry_point_with_audio(self, tmp_path):
        """The transcribe() entry point works for audio files."""
        from app.ai_analyzer.transcriber import transcribe

        audio_path = str(tmp_path / "test.wav")
        with open(audio_path, 'wb') as f:
            f.write(b'\x00' * 100)

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('OPENAI_API_KEY', None)
            os.environ.pop('AZURE_OPENAI_KEY', None)
            os.environ.pop('AZURE_SPEECH_KEY', None)
            result = transcribe(audio_path, is_video=False)

        assert 'text' in result
        assert 'method' in result


# ── Keyframe Tests ──────────────────────────────────────────────────────

class TestKeyframes:
    """Test video keyframe extraction."""

    def _create_test_video(self, path, frames=30, fps=10):
        """Create a minimal test video with OpenCV."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            pytest.skip("opencv-python or numpy not installed")

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(str(path), fourcc, fps, (64, 64))

        for i in range(frames):
            # Vary color to create some scene changes
            color = (i * 8 % 256, 100, 50)
            frame = np.full((64, 64, 3), color, dtype=np.uint8)
            out.write(frame)

        out.release()

    def test_interval_extraction(self, tmp_path):
        """Interval-based extraction returns expected number of frames."""
        from app.ai_analyzer.keyframes import extract_keyframes_interval

        video_path = tmp_path / "test.avi"
        self._create_test_video(video_path, frames=50, fps=10)

        frames = extract_keyframes_interval(str(video_path), interval_sec=2, max_frames=5)

        assert len(frames) > 0
        assert len(frames) <= 5
        assert all('base64' in f for f in frames)
        assert all('time_sec' in f for f in frames)

    def test_scene_change_extraction(self, tmp_path):
        """Scene-change extraction returns frames at visual transitions."""
        from app.ai_analyzer.keyframes import extract_keyframes_scene_change

        video_path = tmp_path / "test.avi"
        self._create_test_video(video_path, frames=50, fps=10)

        frames = extract_keyframes_scene_change(str(video_path), max_frames=8)

        assert len(frames) > 0
        assert len(frames) <= 8
        # First frame should always be at time 0
        assert frames[0]['time_sec'] == 0.0

    def test_hybrid_extraction(self, tmp_path):
        """Hybrid strategy returns frames from both methods."""
        from app.ai_analyzer.keyframes import extract_keyframes

        video_path = tmp_path / "test.avi"
        self._create_test_video(video_path, frames=50, fps=10)

        frames = extract_keyframes(str(video_path), strategy='hybrid', max_frames=6)

        assert len(frames) > 0
        assert len(frames) <= 6

    def test_invalid_video(self):
        """Invalid video path returns empty list."""
        from app.ai_analyzer.keyframes import extract_keyframes

        frames = extract_keyframes("/nonexistent/video.mp4")
        assert frames == []


# ── Confidence Scoring Tests ────────────────────────────────────────────

class TestConfidenceScoring:
    """Test confidence scoring with citizen upload source and EXIF boosts."""

    def test_citizen_upload_base_score(self):
        """Citizen upload gets a reasonable base score."""
        from app.ai_analyzer.confidence import calculate_confidence

        result = calculate_confidence({
            'source': 'citizen_upload',
            'message': 'Airstrike aftermath in northern Gaza',
            'image_links': 'present',
            'lat': 31.5,
            'lon': 34.47,
            'matched_city': 'Gaza',
        })

        assert 0.3 < result < 1.0

    def test_exif_gps_boost(self):
        """EXIF GPS match gives a confidence boost."""
        from app.ai_analyzer.confidence import calculate_confidence

        base = calculate_confidence({
            'source': 'citizen_upload',
            'message': 'Report from Gaza',
            'image_links': 'present',
        })

        boosted = calculate_confidence({
            'source': 'citizen_upload',
            'message': 'Report from Gaza',
            'image_links': 'present',
            'exif_gps_match': True,
            'exif_has_timestamp': True,
            'has_device_info': True,
        })

        assert boosted > base

    def test_citizen_vs_rss_source(self):
        """RSS source starts with higher base than citizen upload."""
        from app.ai_analyzer.confidence import calculate_confidence

        citizen = calculate_confidence({
            'source': 'citizen_upload',
            'message': 'Report from Gaza',
        })

        rss = calculate_confidence({
            'source': 'rss',
            'message': 'Report from Gaza',
        })

        assert rss > citizen  # RSS is a known outlet

    def test_confidence_clamped(self):
        """Confidence is always between 0 and 1."""
        from app.ai_analyzer.confidence import calculate_confidence

        result = calculate_confidence({
            'source': 'citizen_upload',
            'message': 'x' * 1000,
            'image_links': 'yes',
            'video_links': 'yes',
            'lat': 31.5, 'lon': 34.47,
            'matched_city': 'Gaza',
            'source_count': 5,
            'total_views': 50000,
            'exif_gps_match': True,
            'exif_has_timestamp': True,
            'has_device_info': True,
        })

        assert 0.0 <= result <= 1.0


# ── API Route Tests (mocked) ───────────────────────────────────────────

class TestAnalyzeEndpoint:
    """Test the /api/ai/analyze endpoint with mocked AI services."""

    def test_analyze_no_file(self, client):
        """Returns 200 with fallback payload and error field when no file is provided."""
        response = client.post('/api/ai/analyze')
        assert response.status_code == 200
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'No file provided'

    def test_analyze_image_fallback(self, client, tmp_path):
        """Image analysis works with fallback when no API key is set."""
        # Create a minimal JPEG
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img_path = str(tmp_path / "test.jpg")
        img = Image.new('RGB', (10, 10), color='red')
        img.save(img_path, 'JPEG')

        with open(img_path, 'rb') as f:
            data = {'file': (f, 'test.jpg', 'image/jpeg')}

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('OPENAI_API_KEY', None)
                os.environ.pop('AZURE_OPENAI_KEY', None)
                response = client.post(
                    '/api/ai/analyze',
                    data=data,
                    content_type='multipart/form-data',
                )

        assert response.status_code == 200
        result = response.get_json()
        assert 'title' in result
        assert 'tags' in result
        assert 'analysis_steps' in result

    @patch('app.ai_analyzer.routes._call_gpt4o_vision')
    def test_analyze_image_with_gpt(self, mock_gpt, client, tmp_path):
        """Image analysis returns GPT-4o structured result."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        mock_gpt.return_value = {
            'title': 'Destruction in northern Gaza',
            'tags': 'airstrike, destruction, gaza',
            'subject': 'Aftermath of airstrike showing damaged buildings',
            'city': 'Gaza',
            'country': 'Palestine',
            'event_type': 'military_action',
            'language_detected': '',
            'content_warnings': 'destruction',
        }

        img_path = str(tmp_path / "test.jpg")
        Image.new('RGB', (10, 10)).save(img_path, 'JPEG')

        with open(img_path, 'rb') as f:
            response = client.post(
                '/api/ai/analyze',
                data={'file': (f, 'test.jpg', 'image/jpeg')},
                content_type='multipart/form-data',
            )

        assert response.status_code == 200
        result = response.get_json()
        assert result['title'] == 'Destruction in northern Gaza'
        assert result['city'] == 'Gaza'
        assert result['event_type'] == 'military_action'
        assert 'confidence' in result
        assert 'exif' in result

    def test_geocode_proxy_no_query(self, client):
        """Geocode proxy returns 400 without query param."""
        response = client.get('/api/ai/geocode')
        assert response.status_code == 400

    def test_geocode_proxy_no_key(self, client):
        """Geocode proxy returns 200 with configured=False when API key not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OPENCAGE_API_KEY', None)
            response = client.get('/api/ai/geocode?q=Gaza')

        assert response.status_code == 200
        data = response.get_json()
        assert data['configured'] is False
        assert data['lat'] is None
