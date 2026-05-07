"""Database access layer for the Kafka pipeline.

Uses raw psycopg2 because this module runs outside the Flask application
context. The SQL statements are kept in sync with the Telegram model
defined in app/models.py.
"""
import logging
from typing import Any, Optional

import psycopg2
from config import PG_CONF

logger = logging.getLogger(__name__)

# SQL queries  (columns must match app/models.py Telegram model)
CHECK_DUPLICATE = """
SELECT COUNT(*) FROM telegram 
WHERE message = %(message)s 
  AND time = %(time)s
  AND matched_city = %(matched_city)s;
"""

INSERT_ROW = """
INSERT INTO telegram (
    time, total_views, message, video_links, video_durations, image_links,
    tags, subject, matched_city, city_result, lat, lon
)
VALUES (
    %(time)s, %(total_views)s, %(message)s, %(video_links)s, %(video_durations)s,
    %(image_links)s, %(tags)s, %(subject)s, %(matched_city)s, %(city_result)s,
    %(lat)s, %(lon)s
);
"""


def connect_db() -> Optional[psycopg2.extensions.connection]:
    """Create database connection."""
    try:
        conn = psycopg2.connect(**PG_CONF)
        logger.info("PostgreSQL connected successfully")
        return conn
    except Exception as e:
        logger.error("PostgreSQL connection failed: %s", e)
        return None


def validate_row(row: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a pipeline row before insertion.

    Returns (True, '') when valid, or (False, reason) when not.
    Coerces safe defaults for optional truncatable fields in-place.
    """
    if not row.get('message'):
        return False, "Missing required field: message"
    if not row.get('time'):
        return False, "Missing required field: time"

    # Enforce column-length limits (mirrors Telegram model VARCHAR lengths)
    _TRUNCATE = {
        'message':         250,
        'matched_city':    250,
        'city_result':     250,
        'video_durations': 250,
        'subject':         255,
        'tags':            500,
    }
    for field, limit in _TRUNCATE.items():
        val = row.get(field)
        if isinstance(val, str) and len(val) > limit:
            row[field] = val[:limit]
            logger.warning("validate_row: truncated '%s' to %d chars", field, limit)

    # Coerce numeric fields — reject clearly bad values
    for field in ('lat', 'lon'):
        val = row.get(field)
        if val is not None:
            try:
                row[field] = float(val)
            except (TypeError, ValueError):
                logger.warning("validate_row: invalid %s=%r — setting to None", field, val)
                row[field] = None

    return True, ''


def insert_message(conn: psycopg2.extensions.connection, row: dict[str, Any]) -> tuple[bool, str]:
    """Insert message into database with duplicate detection."""
    cur = conn.cursor()
    try:
        cur.execute(CHECK_DUPLICATE, row)
        if cur.fetchone()[0] > 0:
            cur.close()
            return False, "Duplicate"

        cur.execute(INSERT_ROW, row)
        conn.commit()
        cur.close()
        return True, "Inserted"
    except Exception as e:
        conn.rollback()
        cur.close()
        return False, str(e)
