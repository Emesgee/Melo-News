# modules/pipeline_task.py
"""
Central location-enrichment and row-building task for the Kafka pipeline.

Both kafkaProducer.py and kafkaConsumer.py import from here so that
location detection and geocoding are handled in exactly one place.

Location strategy (in priority order):
  1. Lat/lon already present — use them directly, just confirm city name.
  2. matched_city already present — geocode it with geocode_city().
  3. Neither present — run detect_palestine_location() on the full text,
     then geocode the detected city.
  4. Nothing found — lat/lon remain None.
"""

import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy-import the heavy modules so the file can be imported even when
# optional dependencies (spaCy, psycopg2, etc.) are not available in
# a test environment that patches them.
def _get_detector():
    from modules.location_detector import detect_palestine_location
    return detect_palestine_location


def _get_geocoder():
    from modules.geocoder import geocode_city
    return geocode_city


def _get_subject_filter():
    from modules.subject_filter import classify_settler_violence
    return classify_settler_violence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_and_geocode(text, matched_city=None, lat=None, lon=None):
    """
    Return (matched_city, lat, lon) using the best available strategy.

    Parameters
    ----------
    text         : str   — raw message body
    matched_city : str   — city name already known (may be None)
    lat, lon     : float — coordinates already known (may be None)

    Returns
    -------
    (matched_city, lat, lon) — any or all may still be None if detection fails
    """
    # Strategy 1: coordinates already present — fast path (no geocoding needed)
    if lat is not None and lon is not None and matched_city:
        logger.debug("[pipeline_task] Using existing location: %s (%s, %s)", matched_city, lat, lon)
        return matched_city, float(lat), float(lon)

    geocode_city = _get_geocoder()

    # Strategy 2: city name known but coordinates missing — geocode it
    if matched_city and (lat is None or lon is None):
        result = geocode_city(matched_city)
        if result:
            logger.info("[pipeline_task] Geocoded known city '%s' -> (%s, %s)",
                        matched_city, result["lat"], result["lon"])
            return matched_city, result["lat"], result["lon"]

    # Strategy 3: no city — detect from text, then geocode
    if text:
        detect_palestine_location = _get_detector()
        location = detect_palestine_location(text)
        if location:
            detected_city = location.get("village") or location.get("city")
            if detected_city:
                result = geocode_city(detected_city)
                if result:
                    logger.info("[pipeline_task] Detected+geocoded '%s' -> (%s, %s)",
                                detected_city, result["lat"], result["lon"])
                    return detected_city, result["lat"], result["lon"]
                # Detection succeeded but geocode failed — still return the city name
                logger.debug("[pipeline_task] Detected '%s' but geocode failed", detected_city)
                return detected_city, None, None

    logger.debug("[pipeline_task] No location found for text: %s", (text or "")[:60])
    return matched_city, lat, lon


def classify_and_filter(text):
    """
    Run the two-stage settler-violence relevance filter.

    Returns
    -------
    dict | None
        Classification result if relevant (or AI unavailable),
        None if the story is definitively off-topic.
    """
    classify = _get_subject_filter()
    result = classify(text)

    if not result['is_relevant']:
        logger.debug("[pipeline_task] Filtered off-topic: %s", (text or "")[:60])
        return None

    return result


def build_kafka_row(raw_data):
    """
    Normalise a scraped/parsed story dict into the canonical Kafka row format.

    Handles:
    - Subject relevance filtering via classify_and_filter()
    - Accurate location via detect_and_geocode()
    - Stable deduplication ID
    - Field truncation matching DB column limits
    - Passthrough of optional metadata fields (tags, subject, source)

    Parameters
    ----------
    raw_data : dict with keys:
        message, time, total_views, video_links, video_durations,
        image_links, matched_city, city_result, lat, lon,
        subject, tags, source  (all optional except message)

    Returns
    -------
    dict ready to JSON-serialize and produce to Kafka, or None if off-topic.
    """
    text         = raw_data.get("message") or ""
    matched_city = raw_data.get("matched_city")
    lat          = raw_data.get("lat")
    lon          = raw_data.get("lon")

    # Subject relevance filter — reject off-topic stories
    classification = classify_and_filter(text)
    if classification is None:
        return None

    # Accurate location enrichment
    matched_city, lat, lon = detect_and_geocode(text, matched_city, lat, lon)

    # Stable dedup ID
    time_val = raw_data.get("time")
    if isinstance(time_val, datetime):
        time_str = time_val.isoformat()
    else:
        time_str = str(time_val) if time_val else ""
    msg_id = raw_data.get("id") or hashlib.sha256(
        f"{time_str}|{text[:120]}".encode("utf-8")
    ).hexdigest()

    # Normalise time to ISO string
    if isinstance(time_val, datetime):
        time_val = time_val.isoformat()

    # Video/image links: accept pipe-str, list, or None → pipe-str
    def _to_pipe_str(val):
        if isinstance(val, list):
            return "|".join(str(v) for v in val if v)
        return val or ""

    # Merge subject/tags from classification
    tags = raw_data.get("tags") or ""
    kw_tags = ",".join(classification.get("matched_keywords", [])[:5])
    if kw_tags:
        tags = f"{tags},{kw_tags}" if tags else kw_tags

    return {
        "id":               msg_id,
        "time":             time_val,
        "total_views":      raw_data.get("total_views"),
        "message":          text[:500] if text else None,
        "video_links":      _to_pipe_str(raw_data.get("video_links")),
        "video_durations":  _to_pipe_str(raw_data.get("video_durations"))[:250],
        "image_links":      _to_pipe_str(raw_data.get("image_links")),
        "subject":          "settler_violence",
        "tags":             tags or None,
        "source":           raw_data.get("source"),
        "relevance_score":  classification.get("relevance_score", 0.0),
        "matched_city":     matched_city[:250] if matched_city else None,
        "city_result":      (raw_data.get("city_result") or matched_city or "")[:250],
        "lat":              lat,
        "lon":              lon,
    }


def build_db_row(message_data, uploaded_videos=None, image_urls=None):
    """
    Build the dict that database.insert_message() expects, from a
    fully-enriched Kafka message payload (i.e. after consumer enrichment).

    Parameters
    ----------
    message_data    : dict — parsed Kafka message
    uploaded_videos : list — video URLs after upload/processing
    image_urls      : list — image URLs after processing

    Returns
    -------
    dict matching INSERT_ROW columns in modules/database.py
    """
    import json as _json

    text         = (message_data.get("message") or "")[:250] or None
    matched_city = message_data.get("matched_city")
    lat          = message_data.get("lat")
    lon          = message_data.get("lon")

    # Consumer-side fallback enrichment
    matched_city, lat, lon = detect_and_geocode(text or "", matched_city, lat, lon)

    return {
        "time":            message_data.get("time"),
        "total_views":     message_data.get("total_views"),
        "message":         text,
        "video_links":     _json.dumps(uploaded_videos) if uploaded_videos else None,
        "video_durations": (message_data.get("video_durations") or "")[:250],
        "image_links":     _json.dumps(image_urls) if image_urls else None,
        "tags":            message_data.get("tags"),
        "subject":         message_data.get("subject") or "settler_violence",
        "source":          message_data.get("source"),
        "relevance_score": message_data.get("relevance_score", 0.0),
        "matched_city":    matched_city[:250] if matched_city else None,
        "city_result":     (message_data.get("city_result") or matched_city or "")[:250],
        "lat":             lat,
        "lon":             lon,
    }
