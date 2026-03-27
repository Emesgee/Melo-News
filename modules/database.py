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
