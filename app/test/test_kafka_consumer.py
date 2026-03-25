# app/test/test_kafka_consumer.py
"""
Unit tests for the consumer-side pipeline_task.build_db_row() function.

Covers:
- Fallback location enrichment when lat/lon are missing
- Metadata passthrough (tags, subject, source)
- DB row field correctness
- Message truncation to 250 chars
- Media link JSON serialisation
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GEO_KHAN_YOUNIS = {"lat": 31.3452, "lon": 34.3043, "city": "khan younis", "district": "Khan Younis"}
GEO_GAZA        = {"lat": 31.5000, "lon": 34.5000, "city": "Gaza",        "district": "Gaza"}


def _build_db_row_mocked(message_data, uploaded_videos=None, image_urls=None,
                          geocode_result=None, detect_result=None):
    """Call build_db_row with mocked location modules."""
    from modules.pipeline_task import build_db_row
    with patch("modules.pipeline_task._get_geocoder",
               return_value=lambda c: geocode_result), \
         patch("modules.pipeline_task._get_detector",
               return_value=lambda t: detect_result):
        return build_db_row(message_data, uploaded_videos=uploaded_videos, image_urls=image_urls)


# ---------------------------------------------------------------------------
# Location enrichment
# ---------------------------------------------------------------------------

class TestConsumerLocationEnrichment:

    def test_uses_existing_coords_when_present(self):
        """When lat/lon are already in the payload they pass through unchanged."""
        data = {
            "message":      "Breaking news from Khan Younis",
            "matched_city": "Khan Younis",
            "lat":          31.34,
            "lon":          34.30,
        }
        row = _build_db_row_mocked(data)
        assert row["matched_city"] == "Khan Younis"
        assert row["lat"]          == pytest.approx(31.34)
        assert row["lon"]          == pytest.approx(34.30)

    def test_geocodes_city_when_coords_missing(self):
        """When city is known but lat/lon are absent, geocoding is performed."""
        data = {
            "message":      "Reports from Gaza",
            "matched_city": "Gaza",
        }
        row = _build_db_row_mocked(data, geocode_result=GEO_GAZA)
        assert row["lat"] == pytest.approx(31.5)
        assert row["lon"] == pytest.approx(34.5)

    def test_detects_location_from_text_when_no_city(self):
        """When no city or coords are present, location detection runs on message text."""
        data = {
            "message": "Clashes erupted near Khan Younis today",
        }
        detect_result = {"village": "khan younis"}
        row = _build_db_row_mocked(data, geocode_result=GEO_KHAN_YOUNIS, detect_result=detect_result)
        assert row["matched_city"] == "khan younis"
        assert row["lat"] is not None

    def test_no_location_leaves_none(self):
        """When no location can be found, lat/lon/city remain None."""
        data = {"message": "Some generic unrelated text"}
        row = _build_db_row_mocked(data, geocode_result=None, detect_result=None)
        assert row["lat"]          is None
        assert row["lon"]          is None
        assert row["matched_city"] is None


# ---------------------------------------------------------------------------
# Metadata passthrough
# ---------------------------------------------------------------------------

class TestConsumerMetadataPassthrough:

    def test_tags_preserved(self):
        data = {
            "message":      "News item",
            "matched_city": "Gaza",
            "lat":          31.5, "lon": 34.5,
            "tags":         "rss, Al Jazeera Middle East",
        }
        row = _build_db_row_mocked(data)
        assert row["tags"] == "rss, Al Jazeera Middle East"

    def test_subject_preserved(self):
        data = {
            "message":      "News item",
            "matched_city": "Gaza",
            "lat":          31.5, "lon": 34.5,
            "subject":      "Breaking: Israeli airstrike",
        }
        row = _build_db_row_mocked(data)
        assert row["subject"] == "Breaking: Israeli airstrike"

    def test_source_preserved(self):
        data = {
            "message":      "News item",
            "matched_city": "Gaza",
            "lat":          31.5, "lon": 34.5,
            "source":       "telegram",
        }
        row = _build_db_row_mocked(data)
        assert row["source"] == "telegram"

    def test_null_metadata_defaults(self):
        """When metadata fields are absent, subject defaults to 'settler_violence'."""
        data = {"message": "News", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(data)
        assert row["tags"]    is None
        assert row["subject"] == "settler_violence"
        assert row["source"]  is None


# ---------------------------------------------------------------------------
# DB row structure and field rules
# ---------------------------------------------------------------------------

class TestConsumerDatabaseRow:

    def test_all_expected_columns_present(self):
        """build_db_row returns all columns needed by INSERT_ROW."""
        data = {"message": "News", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(data)
        expected = {
            "time", "total_views", "message", "video_links", "video_durations",
            "image_links", "tags", "subject", "source", "relevance_score",
            "matched_city", "city_result", "lat", "lon",
        }
        assert expected.issubset(set(row.keys()))

    def test_message_truncated_to_250(self):
        """Messages are capped at 250 characters for the DB column."""
        long_msg = "x" * 400
        data = {"message": long_msg, "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(data)
        assert len(row["message"]) == 250

    def test_video_links_json_serialised(self):
        """uploaded_videos list is stored as a JSON array string."""
        data = {"message": "News", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(
            data,
            uploaded_videos=["https://blob.example/video.mp4"]
        )
        parsed = json.loads(row["video_links"])
        assert parsed == ["https://blob.example/video.mp4"]

    def test_image_links_json_serialised(self):
        """image_urls list is stored as a JSON array string."""
        data = {"message": "News", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(
            data,
            image_urls=["https://cdn.example/img.jpg"]
        )
        parsed = json.loads(row["image_links"])
        assert parsed == ["https://cdn.example/img.jpg"]

    def test_no_videos_produces_none(self):
        """When uploaded_videos is empty/None, video_links column is None."""
        data = {"message": "News", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(data, uploaded_videos=None)
        assert row["video_links"] is None

    def test_city_result_populated(self):
        """city_result is filled from matched_city if not explicitly given."""
        data = {"message": "News", "matched_city": "Ramallah", "lat": 31.9, "lon": 35.2}
        row = _build_db_row_mocked(data)
        assert row["city_result"] == "Ramallah"

    def test_time_passthrough(self):
        """time field passes through as-is."""
        data = {
            "message":      "News",
            "time":         "2024-06-15T08:00:00",
            "matched_city": "Gaza",
            "lat":          31.5, "lon": 34.5,
        }
        row = _build_db_row_mocked(data)
        assert row["time"] == "2024-06-15T08:00:00"

    def test_total_views_passthrough(self):
        """total_views is preserved."""
        data = {"message": "News", "total_views": 12345, "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = _build_db_row_mocked(data)
        assert row["total_views"] == 12345
