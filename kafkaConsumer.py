import sys
import io
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import time
from confluent_kafka import Consumer, KafkaError

# Import modules
from config import KAFKA_CONF
from modules.pipeline_task import build_db_row
from modules.video_handler import download_and_upload_videos, process_image_links
from modules.database import connect_db, insert_message, validate_row
from modules.azure_handler import setup_cors
from modules.geocoder import load_geojson_coordinates

# Initialize
setup_cors()

# Load GeoJSON coordinates
geojson_coords = load_geojson_coordinates()

# ✅ FIX: Use unique consumer group + reset to earliest
import time as time_module
consumer_config = KAFKA_CONF.copy()
consumer_config['group.id'] = f'eyesonpalestine-consumer-{int(time_module.time())}'
consumer_config['auto.offset.reset'] = 'earliest'
consumer_config['enable.auto.commit'] = True

print("[KAFKA] Starting consumer...")
print(f"[KAFKA] Bootstrap servers: {consumer_config['bootstrap.servers']}")
print(f"[KAFKA] Topic: eyesonpalestine")
print(f"[KAFKA] Consumer group: {consumer_config['group.id']}")
print(f"[KAFKA] Reading from: earliest")

consumer = Consumer(consumer_config)
consumer.subscribe(['eyesonpalestine'])

conn = connect_db()
if not conn:
    print("[ERROR] Failed to connect to database")
    exit(1)

print("[POSTGRES] Connected successfully")
print("[CONSUMER] Waiting for messages...\n")
message_counter = 0

try:
    while True:
        msg = consumer.poll(timeout=1.0)
        
        if msg is None:
            continue
        
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                print("[KAFKA ERROR]", msg.error())
            continue

        try:
            message_data = json.loads(msg.value().decode("utf-8", errors='replace'))
            message_counter += 1
            print(f"\n{'='*60}")
            print(f"[MESSAGE #{message_counter}]")
            print(f"{'='*60}")
        except Exception as e:
            print("[JSON DECODE ERROR]", e)
            continue

        # Extract message fields
        text = message_data.get("message", "")
        matched_city = message_data.get("matched_city")
        lat = message_data.get("lat")
        lon = message_data.get("lon")

        print(f"[INFO] City: {matched_city}")
        print(f"[INFO] Text: {text[:100]}...")

        # Process videos
        video_links = message_data.get("video_links", "")
        uploaded_videos = download_and_upload_videos(video_links) if video_links else []

        # Process images
        image_links = message_data.get("image_links", "")
        image_urls = process_image_links(image_links) if image_links else []

        # Build DB row (pipeline_task handles fallback location + metadata passthrough)
        row = build_db_row(message_data, uploaded_videos=uploaded_videos, image_urls=image_urls)
        if row.get("matched_city") and row.get("lat") is not None:
            print(f"[LOCATION] {row['matched_city']} -> ({row['lat']}, {row['lon']})")
        elif not row.get("lat"):
            print(f"[LOCATION] No location resolved for this message")

        # Validate before insert
        valid, reason = validate_row(row)
        if not valid:
            print(f"[VALIDATION] ⚠️  Skipping message: {reason}")
            continue

        # Insert into database
        success, msg = insert_message(conn, row)
        if success:
            print(f"[POSTGRES] ✅ {msg}")
        else:
            print(f"[POSTGRES] ⚠️  {msg}")

except KeyboardInterrupt:
    print(f"\n[CONSUMER] Processed {message_counter} messages")

finally:
    consumer.close()
    if conn:
        conn.close()
    print("[SHUTDOWN] Complete")