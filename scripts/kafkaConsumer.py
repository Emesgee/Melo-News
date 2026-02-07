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
DOWNLOADS_FOLDER = os.getenv("DOWNLOAD_FOLDER", "./downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
print(f"[CONFIG] Downloads folder set to: {DOWNLOADS_FOLDER}")

# -------------------------
# Kafka configuration
# -------------------------
import time
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': f'melo_consumer_{int(time.time())}',  # Unique group ID to reprocess messages
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
# SQL queries
# -------------------------
# Check if message already exists (prevent duplicates)
check_duplicate_query = """
SELECT COUNT(*) FROM telegram 
WHERE message = %(message)s 
  AND time = %(time)s
  AND matched_city = %(matched_city)s;
"""

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
CSV_PATH = r"C:\Users\ghadb\Desktop\testmelo\Melo-News\data\palestinians_towns.csv"  # Fixed path
df = None
try:
    df = pd.read_csv(CSV_PATH, on_bad_lines='warn') # Warn enables us to see if issues persist
    df.columns = df.columns.str.strip()
    
    # Initialize dictionaries
    all_villages = {}
    town_coordinates = {}
    
    for _, row in df.iterrows():
        try:
            # Get values
            full_name = str(row.get('town_name', '')).strip()
            lat = float(row.get('latitude', 0))
            lon = float(row.get('longitude', 0))
            eng = str(row.get('english_name', '')).strip()
            ara = str(row.get('arabic_name', '')).strip()
            
            # Skip if invalid coords
            if lat == 0 and lon == 0:
                continue
                
            coords = (lat, lon)
            
            # Index by Full Name
            if full_name and full_name.lower() != 'nan':
                all_villages[full_name.lower()] = "Palestine"
                town_coordinates[full_name.lower()] = coords
                
            # Index by English Name
            if eng and eng.lower() != 'nan':
                all_villages[eng.lower()] = "Palestine"
                town_coordinates[eng.lower()] = coords

            # Index by Arabic Name (kept as is for dictionary key, lower() doesn't affect Arabic much but consistency)
            if ara and ara.lower() != 'nan':
                all_villages[ara.lower()] = "Palestine"
                town_coordinates[ara.lower()] = coords
                
        except Exception as row_err:
            continue
            
    all_cities = set()  # Not used explicitly since everything is in all_villages
    print(f"[CSV] Loaded {len(town_coordinates)} location keys from CSV")
    
except Exception as e:
    print(f"[CSV WARNING] Could not load towns CSV: {e}")
    print("[CSV WARNING] Continuing without town data...")
    all_villages = {}
    all_cities = set()
    town_coordinates = {}

# Legacy block removed as it is now integrated above
# town_coordinates = {}
# if df is not None ...

# Thaura AI configuration
THAURA_API_KEY = os.getenv('THAURA_API_KEY')
THAURA_API_BASE = os.getenv('THAURA_API_BASE', 'https://backend.thaura.ai/v1')
THAURA_MODEL = os.getenv('THAURA_DEFAULT_MODEL', 'thaura')

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
# Location detection with Thaura AI
# -------------------------
def detect_location_with_thaura(text: str):
    """Use Thaura AI to extract location from text"""
    if not THAURA_API_KEY:
        return None
    
    for attempt in range(2):  # Retry once on timeout
        try:
            headers = {
                'Authorization': f'Bearer {THAURA_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            # Super simple prompt with examples
            prompt = f"""Extract location from this news text.

Examples:
Text: "In Berlin, protesters marched for Gaza"
Answer: Berlin, Germany

Text: "Israeli settlers attack village of Deir Sharaf near Nablus"  
Answer: Deir Sharaf, Palestine

Text: "Violence in the occupied West Bank continues"
Answer: West Bank, Palestine

Text: {text}
Answer:"""
            
            print(f"[THAURA AI DEBUG] Attempt {attempt+1}, message length: {len(text)} chars")
            
            payload = {
                'model': THAURA_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'You are a location extraction assistant. Only reply with the location name in "City, Country" format. Never explain.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.0,
                'max_tokens': 20  # Further reduced to force brevity
            }
            
            response = requests.post(
                f'{THAURA_API_BASE}/chat/completions',
                json=payload,
                headers=headers,
                timeout=30  # Increased from 10 to 30 seconds
            )
            
            print(f"[THAURA AI DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    message = data['choices'][0]['message']
                    
                    # Get response content
                    location = message.get('content', '').strip()
                    if not location and 'reasoning' in message:
                        location = message['reasoning'].strip()
                    # If response still has explanation, try to extract location with regex
                    if location and any(skip in location.lower() for skip in ['i need', 'let me', 'analyze', 'extract', 'the text']):
                        print("[THAURA AI DEBUG] Response contains explanation, trying regex extraction")
                        import re
                        
                        # Look for specific location patterns in the text
                        # Pattern 1: "in [Location]" or "at [Location]"
                        in_pattern = re.search(r'\bin\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:,|\.|$)', location)
                        if in_pattern:
                            location = in_pattern.group(1).strip()
                        # Pattern 2: Quoted location
                        elif '"' in location:
                            quoted = re.findall(r'"([^"]+)"', location)
                            if quoted:
                                location = quoted[0]
                        # Pattern 3: After "Answer:" or "Location:"
                        elif 'answer:' in location.lower() or 'location:' in location.lower():
                            parts = re.split(r'(?:answer|location):\s*', location, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                location = parts[1].split('\n')[0].strip()
                    
                    # Clean up the location
                    location = location.strip().strip('"').strip("'").strip()
                    
                    # Remove any trailing explanation after first line
                    if '\n' in location:
                        location = location.split('\n')[0].strip()
                    
                    # Validate: should be short and have a comma or be a known location
                    if location and len(location) < 100:
                        # If no comma, try to add country based on context
                        if ',' not in location:
                            location_lower = location.lower()
                            if any(pl in location_lower for pl in ['gaza', 'ramallah', 'jenin', 'nablus', 'hebron', 'jericho', 'bethlehem', 'khan younis', 'rafah', 'west bank', 'deir', 'al-']):
                                location = f"{location}, Palestine"
                            elif len(location.split()) <= 3:  # Short location name, likely just city
                                pass  # Keep as is for now
                        
                        print(f"[THAURA AI DEBUG] Final cleaned location: '{location}'")
                    else:
                        location = ''
                        location = location.split('\n')[0].strip()
                        
                        print(f"[THAURA AI DEBUG] Cleaned location: '{location}'")
                    
                    if location and location.upper() != "NONE" and len(location) > 0 and len(location) < 100:
                        # Parse "City, Country" format
                        if ',' in location:
                            parts = location.split(',', 1)
                            city = parts[0].strip()
                            country = parts[1].strip() if len(parts) > 1 else "Unknown"
                        else:
                            # No comma, assume it's just a city name
                            city = location
                            # Try to infer country from known locations
                            location_lower = location.lower()
                            if any(pl in location_lower for pl in ['gaza', 'ramallah', 'jenin', 'nablus', 'hebron', 'jericho', 'bethlehem', 'khan younis', 'rafah', 'west bank']):
                                country = "Palestine"
                            else:
                                country = "Unknown"
                        
                        return {"place": city, "country": country}
                else:
                    print(f"[THAURA AI DEBUG] No choices in response")
            else:
                print(f"[THAURA AI DEBUG] Error response: {response.text}")
            
            return None  # Success but no location found
            
        except requests.exceptions.Timeout:
            print(f"[THAURA AI TIMEOUT] Attempt {attempt+1} timed out after 30s")
            if attempt == 0:
                print("[THAURA AI] Retrying...")
                continue
            else:
                print("[THAURA AI] Max retries reached, skipping")
                return None
        except Exception as e:
            print(f"[THAURA AI ERROR] Location detection failed: {e}")
            return None
    
    return None

def detect_palestine_location(text: str):
    """Detect Palestinian location - try CSV first, then Thaura AI"""
    doc = nlp(text)
    words = [token.text.lower() for token in doc]

    # Check villages from CSV
    for word in words:
        if word in all_villages:
            return {"village": word, "country": "Palestine"}

    # Check cities from CSV
    for word in words:
        if word in all_cities:
            return {"city": word, "country": "Palestine"}

    # Try spaCy named entities
    for ent in doc.ents:
        if ent.label_ == "GPE":
            ent_lower = ent.text.lower()
            if ent_lower in all_villages or ent_lower in all_cities:
                return {"place": ent.text}
    
    # If not found in CSV, use Thaura AI
    print("[LOCATION] Not found in CSV, trying Thaura AI...")
    return detect_location_with_thaura(text)

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

def geocode_with_thaura(location_name: str):
    """Use Thaura AI to get lat/lon for a location"""
    if not THAURA_API_KEY:
        return None, None
    
    try:
        headers = {
            'Authorization': f'Bearer {THAURA_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""What are the precise latitude and longitude coordinates for this Palestinian location?
If it's a neighborhood or area within a city, provide the specific coordinates for that neighborhood.
Return ONLY in this exact format: latitude,longitude
For example: 31.5167,34.4667

Location: {location_name}
Coordinates:"""
        
        payload = {
            'model': THAURA_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.1,
            'max_tokens': 50
        }
        
        response = requests.post(
            f'{THAURA_API_BASE}/chat/completions',
            json=payload,
            headers=headers,
            timeout=30  # Increased from 10 to 30 seconds
        )
        
        print(f"[THAURA GEOCODE DEBUG] Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                message = data['choices'][0]['message']
                coords = message.get('content', '').strip()
                
                # If content is empty, try parsing from reasoning
                if not coords and 'reasoning' in message:
                    reasoning = message['reasoning']
                    # Look for coordinate patterns in reasoning
                    import re
                    coord_match = re.search(r'(\d+\.?\d*)\s*,\s*(\d+\.?\d*)', reasoning)
                    if coord_match:
                        coords = f"{coord_match.group(1)},{coord_match.group(2)}"
                
                print(f"[THAURA GEOCODE DEBUG] Response: '{coords}'")
                try:
                    if ',' in coords:
                        lat_str, lon_str = coords.split(',')
                        lat, lon = float(lat_str.strip()), float(lon_str.strip())
                        
                        # Validate coordinates are within Palestine/Israel bounds
                        lat_min, lat_max, lon_min, lon_max = ISRAEL_PALESTINE_BOUNDS
                        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                            print(f"[THAURA GEOCODE] {location_name} -> ({lat}, {lon})")
                            return lat, lon
                        else:
                            print(f"[THAURA GEOCODE DEBUG] Coords out of bounds: ({lat}, {lon})")
                    else:
                        print(f"[THAURA GEOCODE DEBUG] No comma in response")
                except ValueError as ve:
                    print(f"[THAURA GEOCODE DEBUG] Failed to parse coords: {ve}")
            else:
                print(f"[THAURA GEOCODE DEBUG] No choices in response")
        else:
            print(f"[THAURA GEOCODE DEBUG] Error response: {response.text}")
        
    except Exception as e:
        print(f"[THAURA GEOCODE ERROR] Failed for {location_name}: {e}")
        import traceback
        traceback.print_exc()
    
    return None, None

def append_to_csv(town_name: str, lat: float, lon: float):
    """Append new location to CSV file"""
    try:
        csv_path = 'data/palestinians_towns.csv'
        
        # Read existing CSV
        if os.path.exists(csv_path):
            df_csv = pd.read_csv(csv_path)
        else:
            df_csv = pd.DataFrame(columns=['town_name', 'latitude', 'longitude'])
        
        # Check if already exists
        if town_name.lower() in df_csv['town_name'].str.lower().values:
            print(f"[CSV] {town_name} already exists, skipping")
            return
        
        # Append new row
        new_row = pd.DataFrame([{
            'town_name': town_name,
            'latitude': lat,
            'longitude': lon
        }])
        df_csv = pd.concat([df_csv, new_row], ignore_index=True)
        df_csv.to_csv(csv_path, index=False)
        
        # Update in-memory dictionary
        town_coordinates[town_name.lower()] = (lat, lon)
        
        print(f"[CSV] Added {town_name} ({lat}, {lon}) to CSV")
        
    except Exception as e:
        print(f"[CSV ERROR] Failed to append {town_name}: {e}")

def geocode_city(city_name):
    if not city_name:
        return None, None

    city_name_lower = city_name.lower()
    
    # Level 1: Check CSV coordinates
    if city_name_lower in town_coordinates:
        lat, lon = town_coordinates[city_name_lower]
        print(f"[GEOCODE CSV] {city_name} -> ({lat}, {lon})")
        return lat, lon
    
    # Level 2: Check geocode cache
    if city_name_lower in geocode_cache:
        lat, lon = geocode_cache[city_name_lower]
        print(f"[GEOCODE CACHE] {city_name} -> ({lat}, {lon})")
        return lat, lon

    # Level 3: Try Nominatim
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
                print(f"[NOMINATIM] {city_name} -> ({lat}, {lon})")
                return lat, lon
    except Exception as e:
        print(f"[NOMINATIM ERROR] {city_name}: {e}")

    # Level 4: Try Thaura AI
    print(f"[GEOCODE] Trying Thaura AI for {city_name}...")
    lat, lon = geocode_with_thaura(city_name)
    if lat and lon:
        # Save to cache
        geocode_cache[city_name_lower] = (lat, lon)
        save_geocode_cache()
        
        # Append to CSV
        append_to_csv(city_name, lat, lon)
        
        return lat, lon

    print(f"[GEOCODE FAILED] Could not geocode {city_name}")
    return None, None

    geocode_cache[city_name_lower] = (None, None)
    save_geocode_cache()
    return None, None

# -------------------------
# Kafka consumer
# -------------------------
print("[KAFKA] Starting consumer...")
print(f"[KAFKA] Bootstrap servers: {kafka_conf['bootstrap.servers']}")
print(f"[KAFKA] Consumer group: {kafka_conf['group.id']}")
print(f"[KAFKA] Topic: eyesonpalestine")

consumer = Consumer(kafka_conf)
consumer.subscribe(['eyesonpalestine'])

print("[POSTGRES] Connecting to database...")
conn = psycopg2.connect(**pg_conf)
cur = conn.cursor()
print("[POSTGRES] Connected successfully")
print("\n[CONSUMER] Waiting for messages...\n")

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
            print(f"[MESSAGE #{message_counter}] Received from Kafka")
            print(f"{'='*60}")
        except Exception as e:
            print("[JSON ERROR]", e)
            continue

        text = message_data.get("message", "")  # Full message text for location detection

        # Get location data from message or detect it
        matched_city = message_data.get("matched_city")
        city_result = message_data.get("city_result")
        lat = message_data.get("lat")
        lon = message_data.get("lon")
        
        # If location data is missing, try to detect it from the message text
        if not matched_city or lat is None or lon is None:
            print("[LOCATION] No location data from producer, detecting from message...")
            location_result = detect_palestine_location(text)
            
            if location_result:
                # Try village first
                if "village" in location_result:
                    matched_city = location_result["village"]
                    city_result = location_result["country"]
                # Then city
                elif "city" in location_result:
                    matched_city = location_result["city"]
                    city_result = location_result["country"]
                # Then any place
                elif "place" in location_result:
                    matched_city = location_result["place"]
                    city_result = "Unknown"
                
                # Geocode the detected location
                if matched_city:
                    geocoded = geocode_city(matched_city)
                    if geocoded:
                        lat = geocoded['lat']
                        lon = geocoded['lon']
                        matched_city = geocoded.get('city', matched_city)
                        print(f"[LOCATION DETECTED] {matched_city} -> ({lat}, {lon})")
                    else:
                        lat, lon = None, None
            else:
                print("[LOCATION] No location detected in message")
        else:
            print(f"[LOCATION] From producer: {matched_city} -> ({lat}, {lon})")


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
        video_urls = uploaded_video_urls if uploaded_video_urls else (message_data.get("video_links", "").split('|') if message_data.get("video_links") else [])
        video_urls = [url for url in video_urls if url]  # Filter empty strings
        
        # Process image links
        image_links = message_data.get("image_links", "")
        image_urls = image_links.split('|') if image_links else []
        image_urls = [url.strip() for url in image_urls if url.strip()]  # Filter empty strings
        
        # Truncate long text fields to match VARCHAR(255) limit
        message_text = text[:250] if text else None
        # Ensure matched_city is string before slicing
        matched_city_str = str(matched_city) if matched_city else None
        matched_city_text = matched_city_str[:250] if matched_city_str else None
        # Ensure city_result is string before slicing
        city_result_str = str(city_result) if city_result else None
        city_result_text = city_result_str[:250] if city_result_str else None
        
        row = {
            "time": message_data.get("time"),
            "total_views": message_data.get("total_views"),
            "message": message_text,
            "video_links": json.dumps(video_urls) if video_urls else None,  # JSON array
            "video_durations": message_data.get("video_durations", "")[:250],
            "image_links": json.dumps(image_urls) if image_urls else None,  # JSON array
            "tags": None,
            "subject": None,
            "matched_city": matched_city_text,
            "city_result": city_result_text,  # String column
            "lat": lat,
            "lon": lon,
        }

        try:
            # Check for duplicates first
            cur.execute(check_duplicate_query, row)
            duplicate_count = cur.fetchone()[0]
            
            if duplicate_count > 0:
                print(f"[POSTGRES] ⚠️  Duplicate found - Skipping message #{message_counter}")
                print(f"  City: {matched_city} | Message: {text[:80]}...")
                continue
            
            # Insert only if not duplicate
            cur.execute(insert_query, row)
            conn.commit()
            print(f"[POSTGRES] ✅ Inserted row #{message_counter}")
            print(f"  City: {matched_city} | Coords: ({lat}, {lon})")
            print(f"  Message: {text[:100]}...")
        except Exception as e:
            conn.rollback()
            print(f"[POSTGRES] ❌ FAILED to insert: {e}")

except KeyboardInterrupt:
    print(f"\n[CONSUMER] Stopping... Processed {message_counter} messages total")

finally:
    consumer.close()
    cur.close()
    conn.close()
    save_geocode_cache()
    print(f"[CACHE] Saved to {CACHE_FILE}")
    print(f"[SUMMARY] Total messages processed: {message_counter}")

# Add this to your kafkaConsumer.py or run separately
from azure.storage.blob import BlobServiceClient

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Set CORS rules
cors_rules = {
    'allowed_origins': ['http://localhost:3000', 'http://localhost:8000'],
    'allowed_methods': ['GET', 'HEAD', 'OPTIONS'],
    'allowed_headers': ['*'],
    'exposed_headers': ['*'],
    'max_age_in_seconds': 3600
}

blob_service_client.set_service_properties(cors=[cors_rules])
print("CORS enabled for Azure Blob Storage")
