import psycopg2
import os
from dotenv import load_dotenv
import json

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, matched_city, image_links, video_links 
        FROM telegram 
        WHERE video_links IS NOT NULL OR image_links IS NOT NULL
        LIMIT 10
    """)

    print("=" * 60)
    print("VIDEO/IMAGE URLS IN DATABASE:")
    print("=" * 60)

    for row in cursor.fetchall():
        print(f"\nID: {row[0]}")
        print(f"City: {row[1]}")
        print(f"Image Links: {row[2]}")
        print(f"Video Links: {row[3]}")

    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")
