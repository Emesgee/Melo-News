# app/test/test_kafka_producer.py
"""
Unit tests for the producer-side pipeline_task module.

All external I/O (location detection, geocoding, Kafka, filesystem) is
mocked so these tests run without spaCy, psycopg2, or a live Kafka broker.
"""

import sys
import os
import json
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Ensure the project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GEOCODE_RESULT_KHAN_YOUNIS = {"lat": 31.3452, "lon": 34.3043, "city": "khan younis", "district": "Khan Younis"}
GEOCODE_RESULT_GAZA        = {"lat": 31.5000, "lon": 34.5000, "city": "Gaza",        "district": "Gaza"}
GEOCODE_RESULT_NABLUS      = {"lat": 32.2211, "lon": 35.2544, "city": "nablus",      "district": "Nablus"}


# ---------------------------------------------------------------------------
# detect_and_geocode tests
# ---------------------------------------------------------------------------

class TestDetectAndGeocode:

    def test_fast_path_all_data_present(self):
        """When city + lat/lon are all provided they are returned as-is."""
        from modules.pipeline_task import detect_and_geocode
        with patch("modules.pipeline_task._get_geocoder") as mock_gc:
            city, lat, lon = detect_and_geocode(
                "some text", matched_city="Gaza", lat=31.5, lon=34.5
            )
        assert city == "Gaza"
        assert lat  == 31.5
        assert lon  == 34.5
        # geocode should NOT be called — we already have everything
        mock_gc.assert_not_called()

    def test_geocodes_when_city_known_but_no_coords(self):
        """When city is known but lat/lon are None, geocode_city is called."""
        from modules.pipeline_task import detect_and_geocode
        with patch("modules.pipeline_task._get_geocoder", return_value=lambda c: GEOCODE_RESULT_KHAN_YOUNIS):
            city, lat, lon = detect_and_geocode("some text", matched_city="Khan Younis")
        assert city == "Khan Younis"
        assert lat  == pytest.approx(31.3452)
        assert lon  == pytest.approx(34.3043)

    def test_detects_from_text_when_no_city(self):
        """When no city is provided, detect_palestine_location is called on the text."""
        from modules.pipeline_task import detect_and_geocode
        fake_detection = {"village": "nablus", "city": "nablus"}
        with patch("modules.pipeline_task._get_detector", return_value=lambda t: fake_detection), \
             patch("modules.pipeline_task._get_geocoder", return_value=lambda c: GEOCODE_RESULT_NABLUS):
            city, lat, lon = detect_and_geocode("Clashes near nablus this morning")
        assert city == "nablus"
        assert lat  == pytest.approx(32.2211)
        assert lon  == pytest.approx(35.2544)

    def test_returns_city_even_if_geocode_fails(self):
        """When location is detected but geocoding fails, city is returned with None coords."""
        from modules.pipeline_task import detect_and_geocode
        fake_detection = {"village": "unknownplace"}
        with patch("modules.pipeline_task._get_detector", return_value=lambda t: fake_detection), \
             patch("modules.pipeline_task._get_geocoder", return_value=lambda c: None):
            city, lat, lon = detect_and_geocode("Incident near unknownplace")
        assert city == "unknownplace"
        assert lat  is None
        assert lon  is None

    def test_returns_none_when_nothing_found(self):
        """When text has no detectable location, all three returned values reflect input."""
        from modules.pipeline_task import detect_and_geocode
        with patch("modules.pipeline_task._get_detector", return_value=lambda t: None), \
             patch("modules.pipeline_task._get_geocoder", return_value=lambda c: None):
            city, lat, lon = detect_and_geocode("No location here at all")
        assert city is None
        assert lat  is None
        assert lon  is None


# ---------------------------------------------------------------------------
# build_kafka_row tests
# ---------------------------------------------------------------------------

# Fake subject filter that always classifies as relevant (for testing)
_ALWAYS_RELEVANT = {
    'is_relevant': True,
    'relevance_score': 0.8,
    'matched_keywords': ['settler violence'],
    'method': 'keyword',
}


class TestBuildKafkaRow:

    def _patched_row(self, raw_data, geocode_result=None, detect_result=None):
        """Helper: call build_kafka_row with mocked location + subject filter modules."""
        from modules.pipeline_task import build_kafka_row
        with patch("modules.pipeline_task._get_geocoder",
                   return_value=lambda c: geocode_result), \
             patch("modules.pipeline_task._get_detector",
                   return_value=lambda t: detect_result), \
             patch("modules.pipeline_task._get_subject_filter",
                   return_value=lambda t: _ALWAYS_RELEVANT):
            return build_kafka_row(raw_data)

    def test_all_required_fields_present(self):
        """build_kafka_row returns all expected keys."""
        row = self._patched_row(
            {"message": "Attack in Gaza", "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        )
        required = {"id", "time", "total_views", "message", "video_links",
                    "video_durations", "image_links", "subject", "tags",
                    "source", "relevance_score", "matched_city", "city_result", "lat", "lon"}
        assert required.issubset(set(row.keys()))

    def test_location_populated_from_geocoding(self):
        """Location fields are filled when city is given but coords are absent."""
        row = self._patched_row(
            {"message": "Clashes in Khan Younis", "matched_city": "Khan Younis"},
            geocode_result=GEOCODE_RESULT_KHAN_YOUNIS,
        )
        assert row["matched_city"] == "Khan Younis"
        assert row["lat"]          == pytest.approx(31.3452)
        assert row["lon"]          == pytest.approx(34.3043)

    def test_metadata_passthrough(self):
        """tags, source from raw_data survive into the row; subject is always 'settler_violence'."""
        raw = {
            "message":      "Report from Al Jazeera",
            "matched_city": "Gaza",
            "lat":          31.5,
            "lon":          34.5,
            "tags":         "rss, Al Jazeera Middle East",
            "subject":      "Breaking: airstrike reported",
            "source":       "rss",
        }
        row = self._patched_row(raw)
        # tags get appended with matched keywords from subject filter
        assert "rss, Al Jazeera Middle East" in row["tags"]
        assert row["subject"] == "settler_violence"
        assert row["source"]  == "rss"

    def test_dedup_id_is_stable(self):
        """Same message+time input always produces the same id."""
        raw = {"message": "Incident in Ramallah", "time": "2024-03-01T10:00:00"}
        row1 = self._patched_row(raw)
        row2 = self._patched_row(raw)
        assert row1["id"] == row2["id"]

    def test_explicit_id_not_overwritten(self):
        """If raw_data already contains an id, it is kept."""
        raw = {"message": "Test", "id": "my-custom-id", "lat": 31.5, "lon": 34.5, "matched_city": "Gaza"}
        row = self._patched_row(raw)
        assert row["id"] == "my-custom-id"

    def test_message_truncated_to_500_chars(self):
        """Messages longer than 500 chars are truncated."""
        long_msg = "x" * 600
        row = self._patched_row({"message": long_msg, "matched_city": "Gaza", "lat": 31.5, "lon": 34.5})
        assert len(row["message"]) == 500

    def test_pipe_str_video_links(self):
        """video_links list is joined with pipes."""
        raw = {
            "message":      "Video footage",
            "matched_city": "Gaza",
            "lat":          31.5,
            "lon":          34.5,
            "video_links":  ["http://cdn.example/a.mp4", "http://cdn.example/b.mp4"],
        }
        row = self._patched_row(raw)
        assert row["video_links"] == "http://cdn.example/a.mp4|http://cdn.example/b.mp4"

    def test_city_result_falls_back_to_matched_city(self):
        """city_result uses matched_city when not explicitly provided."""
        raw = {"message": "News", "matched_city": "Hebron", "lat": 31.5, "lon": 34.5}
        row = self._patched_row(raw)
        assert row["city_result"] == "Hebron"

    def test_datetime_time_serialised_to_iso(self):
        """datetime objects in 'time' field are converted to ISO strings."""
        dt = datetime(2024, 3, 15, 12, 30, 0)
        raw = {"message": "News", "time": dt, "matched_city": "Gaza", "lat": 31.5, "lon": 34.5}
        row = self._patched_row(raw)
        assert row["time"] == "2024-03-15T12:30:00"

    def test_detect_and_geocode_called_for_missing_city(self):
        """When no city is in raw_data, text detection is attempted."""
        detect_result  = {"village": "ramallah"}
        geocode_result = {"lat": 31.9, "lon": 35.2, "city": "ramallah", "district": "Ramallah"}
        raw = {"message": "Protests erupted in Ramallah today"}
        row = self._patched_row(raw, geocode_result=geocode_result, detect_result=detect_result)
        assert row["matched_city"] == "ramallah"
        assert row["lat"] is not None


# ---------------------------------------------------------------------------
# filter_location helper (mirrors producer logic)
# ---------------------------------------------------------------------------

class TestFilterLocation:
    """Test the exact/substring location matching logic used in kafkaProducer."""

    def _make_filter(self, geojson_coords):
        def filter_location(text):
            if not text:
                return None, None
            text_lower = text.lower()
            for word in set(text_lower.replace('\n', ' ').replace('\t', ' ').split()):
                if word in geojson_coords:
                    return word, word
            for village_lc in geojson_coords:
                if village_lc and village_lc in text_lower:
                    return village_lc, village_lc
            return None, None
        return filter_location

    def test_exact_token_match(self):
        coords = {"gaza": {}, "nablus": {}, "hebron": {}}
        fl = self._make_filter(coords)
        city, result = fl("Heavy fire reported in Gaza today")
        assert city == "gaza"

    def test_multiword_substring_match(self):
        coords = {"khan younis": {}, "west bank": {}}
        fl = self._make_filter(coords)
        city, result = fl("Strikes hit Khan Younis")
        assert city == "khan younis"

    def test_no_match_returns_none(self):
        coords = {"gaza": {}, "nablus": {}}
        fl = self._make_filter(coords)
        city, result = fl("Nothing relevant here")
        assert city is None
        assert result is None

    def test_empty_text_returns_none(self):
        coords = {"gaza": {}}
        fl = self._make_filter(coords)
        city, result = fl("")
        assert city is None
