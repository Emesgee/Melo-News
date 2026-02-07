import json
import time
from confluent_kafka import Consumer, KafkaError

# Import modules
from config import KAFKA_CONF
from modules.location_detector import detect_palestine_location
from modules.geocoder import geocode_city, load_geojson_coordinates
from modules.video_handler import download_and_upload_videos, process_image_links
from modules.database import connect_db, insert_message
from modules.azure_handler import setup_cors

# Initialize
setup_cors()

# Load GeoJSON coordinates
geojson_coords = load_geojson_coordinates()

print("[KAFKA] Starting consumer...")
print(f"[KAFKA] Bootstrap servers: {KAFKA_CONF['bootstrap.servers']}")
print(f"[KAFKA] Topic: eyesonpalestine")

consumer = Consumer(KAFKA_CONF)
consumer.subscribe(['eyesonpalestine'])

conn = connect_db()
if not conn:
    print("[ERROR] Failed to connect to database")
    exit(1)

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
            message_data = json.loads(msg.value().decode("utf-8"))
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

        # Detect location if missing
        if not matched_city or lat is None or lon is None:
            print("[LOCATION] Detecting from message...")
            location_result = detect_palestine_location(text)
            
            if location_result:
                matched_city = location_result.get("village") or location_result.get("city") or matched_city
                if matched_city:
                    geocode_result = geocode_city(matched_city)
                    if geocode_result:
                        lat = geocode_result.get("lat")
                        lon = geocode_result.get("lon")
                        print(f"[LOCATION] {matched_city} -> ({lat}, {lon})")
                    else:
                        print(f"[LOCATION] Could not geocode: {matched_city}")

        # Process videos
        video_links = message_data.get("video_links", "")
        uploaded_videos = download_and_upload_videos(video_links)
        
        # Process images
        image_links = message_data.get("image_links", "")
        image_urls = process_image_links(image_links)

        # Prepare database row
        row = {
            "time": message_data.get("time"),
            "total_views": message_data.get("total_views"),
            "message": text[:250] if text else None,
            "video_links": json.dumps(uploaded_videos) if uploaded_videos else None,
            "video_durations": (message_data.get("video_durations") or "")[:250],
            "image_links": json.dumps(image_urls) if image_urls else None,
            "tags": None,
            "subject": None,
            "matched_city": matched_city[:250] if matched_city else None,
            "city_result": (message_data.get("city_result") or "")[:250],
            "lat": lat,
            "lon": lon,
        }

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
