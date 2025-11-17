import os
import json
import requests
import spacy
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from datetime import datetime
from urllib.parse import urlparse, unquote

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "uploads")

DOWNLOADS_FOLDER = "E:/ProjectPortfolio/DataPipelines/kafkaProjects/Melo-News/app/uploads"
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# -------------------------
# Kafka configuration
# -------------------------
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my_consumer_group',
    'auto.offset.reset': 'earliest'
}

# PostgreSQL configuration
pg_conf = {
    'dbname': 'mydb',
    'user': 'admin',
    'password': 'admin',
    'host': 'localhost',
    'port': 5432
}

# -------------------------
# SQL insert query
# -------------------------
insert_query = """
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

# -------------------------
# Load spaCy NLP model
# -------------------------
nlp = spacy.load("en_core_web_sm")

# -------------------------
# Load towns from CSV
# -------------------------
CSV_PATH = r"e:\ProjectPortfolio\DataPipelines\kafkaProjects\Melo-News\palestinian_towns.csv"
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip()
all_villages = {v.lower(): "Palestine" for v in df['town_name']}
all_cities = set()  # fill if needed

# -------------------------
# Azure Blob client
# -------------------------
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

try:
    container_client.create_container()
except ResourceExistsError:
    pass

def upload_file_to_blob(local_file_path):
    """Uploads a local file to Azure Blob Storage and returns its URL."""
    filename = unquote(os.path.basename(local_file_path))
    blob_client = container_client.get_blob_client(filename)
    try:
        with open(local_file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"
        print(f"[AZURE UPLOAD SUCCESS] {blob_url}")
        return blob_url
    except Exception as e:
        print(f"[AZURE UPLOAD FAILED] {local_file_path}: {e}")
        return None

# -------------------------
# Location detection
# -------------------------
def detect_palestine_location(text: str):
    doc = nlp(text)
    words = [token.text.lower() for token in doc]

    for word in words:
        if word in all_villages:
            return {"village": word, "country": "Palestine"}

    for word in words:
        if word in all_cities:
            return {"city": word, "country": "Palestine"}

    for ent in doc.ents:
        if ent.label_ == "GPE":
            return {"place": ent.text}

    return None

# -------------------------
# Geocode caching
# -------------------------
ISRAEL_PALESTINE_BOUNDS = [29.5, 33.5, 34.0, 35.9]
CACHE_FILE = "geocode_cache.json"

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        geocode_cache = json.load(f)
else:
    geocode_cache = {}

def save_geocode_cache():
    tmp_file = CACHE_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(geocode_cache, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, CACHE_FILE)

def geocode_city(city_name):
    if not city_name:
        return None, None

    city_name_lower = city_name.lower()
    if city_name_lower in geocode_cache:
        return geocode_cache[city_name_lower]

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': f"{city_name}, Palestine", 'format': 'json', 'limit': 1}
        response = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            lat_min, lat_max, lon_min, lon_max = ISRAEL_PALESTINE_BOUNDS
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                geocode_cache[city_name_lower] = (lat, lon)
                save_geocode_cache()
                return lat, lon
    except Exception as e:
        print(f"[GEOCODE FAILED] {city_name}: {e}")

    geocode_cache[city_name_lower] = (None, None)
    save_geocode_cache()
    return None, None

# -------------------------
# Kafka consumer
# -------------------------
consumer = Consumer(kafka_conf)
consumer.subscribe(['eyesonpalestine'])

conn = psycopg2.connect(**pg_conf)
cur = conn.cursor()

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
        except Exception as e:
            print("[JSON ERROR]", e)
            continue

        text = message_data.get("message", "")

        # Detect location
        location_result = detect_palestine_location(text)
        matched_city = None
        lat, lon = None, None
        if location_result:
            matched_city = location_result.get("village") or location_result.get("city") or location_result.get("place")
            lat, lon = geocode_city(matched_city)
            print(f"[LOCATION DETECTED] {matched_city} -> {lat}, {lon}")

        # Process video links and upload to Azure
        video_links = message_data.get("video_links", "")
        uploaded_video_urls = []

        for url in video_links.split('|'):
            url = url.strip()
            if not url:
                continue
            local_path = os.path.join(DOWNLOADS_FOLDER, unquote(os.path.basename(urlparse(url).path)))
            try:
                r = requests.get(url, stream=True, timeout=30)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                blob_url = upload_file_to_blob(local_path)
                if blob_url:
                    uploaded_video_urls.append(blob_url)
                os.remove(local_path)
            except Exception as e:
                print("[VIDEO DOWNLOAD/UPLOAD FAILED]", url, e)

        # Insert into Postgres
        row = {
            "time": message_data.get("time"),
            "total_views": message_data.get("total_views"),
            "message": text,
            "video_links": '|'.join(uploaded_video_urls),
            "video_durations": message_data.get("video_durations"),
            "image_links": message_data.get("image_links"),
            "tags": None,
            "subject": None,
            "matched_city": matched_city,
            "city_result": json.dumps(location_result) if location_result else None,
            "lat": lat,
            "lon": lon,
        }

        try:
            cur.execute(insert_query, row)
            conn.commit()
            print("[POSTGRES] Inserted row:", row)
        except Exception as e:
            conn.rollback()
            print("[POSTGRES FAILED]", e)

except KeyboardInterrupt:
    print("Stopping consumer...")

finally:
    consumer.close()
    cur.close()
    conn.close()
    save_geocode_cache()
    print("Cache saved to", CACHE_FILE)
