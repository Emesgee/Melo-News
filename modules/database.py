import psycopg2
from config import PG_CONF

# SQL queries
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

def connect_db():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**PG_CONF)
        print("[POSTGRES] Connected successfully")
        return conn
    except Exception as e:
        print(f"[POSTGRES ERROR] Connection failed: {e}")
        return None

def insert_message(conn, row):
    """Insert message into database"""
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
