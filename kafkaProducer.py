import os
import time
import json
import tempfile
import hashlib
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from confluent_kafka import Producer
import psycopg2
from psycopg2.extras import execute_values
import spacy
import requests
import pandas as pd

# -------------------------
# Logging
# -------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("kafkaProducer")

# -------------------------
# Load spaCy model (optional; not critical)
# -------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# -------------------------
# Telegram URLs (can be configured via env var TELEGRAM_URLS as comma-separated list)
# -------------------------
telegram_urls = [u.strip() for u in os.getenv("TELEGRAM_URLS", "https://t.me/s/QudsNen?q=settlers+village").split(",") if u.strip()]

# Keywords
SCRAPER_KEYWORDS = [k.strip().lower() for k in os.getenv("SCRAPER_KEYWORDS", "settlers, village").split(',') if k.strip()]

# -------------------------
# Load Palestinian towns CSV (config via PALESTINIAN_TOWNS_CSV)
# -------------------------
TOWNS_CSV = os.getenv("PALESTINIAN_TOWNS_CSV", os.path.join(os.getcwd(), "palestinian_towns.csv"))
try:
    df = pd.read_csv(TOWNS_CSV)
    df.columns = df.columns.str.strip()
except Exception as e:
    logger.warning(f"Failed to load towns CSV at {TOWNS_CSV}: {e}")
    df = pd.DataFrame({"town_name": []})

# Build lookups: map lowercased town -> canonical town
all_villages = {str(v).strip().lower(): str(v).strip() for v in df.get('town_name', []) if pd.notna(v)}
all_cities = set()  # can be extended if you have a cities list

# -------------------------
# Location filter
# -------------------------
def filter_location(text):
    if not text:
        return None, None
    text_lower = text.lower()
    # Exact token match
    for word in set(text_lower.replace('\n', ' ').replace('\t', ' ').split()):
        if word in all_villages:
            canon = all_villages[word]
            return canon, canon
    # Substring fallbacks (for multi-word towns)
    for village_lc, canon in all_villages.items():
        if village_lc and village_lc in text_lower:
            return canon, canon
    # Cities placeholder
    for city in all_cities:
        if city in text_lower:
            return city, city
    return None, None

# -------------------------
# Parsing helpers
# -------------------------
def parse_time(element):
    try:
        time_element = element.find_element(By.XPATH, './/span[@class="tgme_widget_message_meta"]/a/time')
        time_text = time_element.get_attribute('datetime')
        if time_text:
            return datetime.fromisoformat(time_text.replace('Z', '+00:00'))
    except:
        return None

def parse_views(element):
    try:
        views_element = element.find_element(By.XPATH, './/span[@class="tgme_widget_message_views"]')
        views_text = views_element.text
        return parse_views_text(views_text) if views_text else None
    except:
        return None

def parse_views_text(views_text):
    try:
        if 'K' in views_text:
            return int(float(views_text.replace('K','').replace(' views','').replace(',','')) * 1000) 
        elif 'M' in views_text:
            return int(float(views_text.replace('M','').replace(' views','').replace(',','')) * 1000000)
        else:
            return int(views_text.replace(' views','').replace(',',''))
    except:
        return None

def extract_video_links(element):
    links = []
    try:
        for video in element.find_elements(By.XPATH, './/video'):
            src = video.get_attribute('src')
            if src:
                links.append(src)
    except:
        pass
    return links

def extract_video_durations(element, class_name='message_video_duration'):
    durations = []
    try:
        for d in element.find_elements(By.CLASS_NAME, class_name):
            txt = d.text.strip()
            if txt:
                durations.append(txt)
    except:
        pass
    return durations

def extract_image_links(element):
    links = []
    try:
        # Video thumbnails
        for i in element.find_elements(By.XPATH, './/i[contains(@class,"tgme_widget_message_video_thumb")]'):
            style = i.get_attribute("style")
            if style and "url(" in style:
                url = style.split("url(")[-1].split(")")[0].strip("'\"")
                links.append(url)

        # Any other images (<img>) for completeness
        for img in element.find_elements(By.XPATH, './/img'):
            src = img.get_attribute('src')
            if src:
                links.append(src)

    except Exception as e:
        logger.debug("Image extraction error: %s", e)

    return list(set(links))

def extract_message_text(element):
    try:
        return element.find_element(By.CLASS_NAME, 'tgme_widget_message_text').text
    except:
        return ""

# -------------------------
# Postgres batch insert
# -------------------------
def insert_into_postgres_batch(conn, rows):
    try:
        with conn.cursor() as cur:
            query = """
                INSERT INTO telegram (
                    message_id, time, total_views, message, video_links, video_durations, image_links,
                    subject, matched_city, city_result, lat, lon
                )
                VALUES %s
                ON CONFLICT (message_id) DO NOTHING
            """
            values = [
                (
                    r['id'], r['time'], r['total_views'], r['message'], r['video_links'],
                    r['video_durations'], r['image_links'],
                    r['subject'], r['matched_city'], r['city_result'], r['lat'], r['lon']
                ) for r in rows
            ]
            execute_values(cur, query, values)
        conn.commit()
        logger.info("Inserted %d rows into PostgreSQL", len(rows))
    except Exception as e:
        logger.error("Error inserting into PostgreSQL: %s", e)
        conn.rollback()

# -------------------------
# Main scraper
# -------------------------
driver = None
conn = None
producer = None

try:
    # Chrome setup
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    options.add_argument("--disable-gcm")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    # Kafka
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC', 'eyesonpalestine')
    producer = Producer({'bootstrap.servers': bootstrap_servers})

    # Postgres
    pg_dsn = os.getenv('DATABASE_URL', 'postgresql://admin:admin@localhost:5432/mydb')
    conn = psycopg2.connect(pg_dsn)

    for url in telegram_urls:
        try:
            driver.get(url)
            elements = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'tgme_widget_message_bubble'))
            )

            # Chunked scrolling - increased to find more messages
            for _ in range(500):
                driver.execute_script("window.scrollBy(0, 1000)")
                time.sleep(0.5)

            elements = driver.find_elements(By.CLASS_NAME, 'tgme_widget_message_bubble')
            rows_to_insert = []

            for element in elements:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)
                except:
                    pass

                text = extract_message_text(element)
                tl = text.lower() if text else ""
                if not any(k in tl for k in SCRAPER_KEYWORDS):
                    continue

                msg_time = parse_time(element)
                views = parse_views(element)
                videos = extract_video_links(element)
                durations = extract_video_durations(element)
                images = extract_image_links(element)

                village_or_city, city_result = filter_location(text)
                lat, lon = None, None
                if village_or_city:
                    try:
                        key = f"{village_or_city}, Palestine".lower()
                        if not hasattr(insert_into_postgres_batch, "_geo_cache"):
                            insert_into_postgres_batch._geo_cache = {}
                        cache = insert_into_postgres_batch._geo_cache
                        if not cache:
                            # Load disk cache on first use
                            try:
                                with open('geocode_cache.json', 'r', encoding='utf-8') as cf:
                                    cache.update(json.load(cf))
                            except Exception:
                                pass

                        if key in cache:
                            lat, lon = cache[key]
                        else:
                            resp = requests.get(
                                "https://nominatim.openstreetmap.org/search",
                                params={"q": key, "format": "json", "limit": 1},
                                headers={"User-Agent": "Mozilla/5.0 (Melo-News scraper)"},
                                timeout=15,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                if data:
                                    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                                    cache[key] = [lat, lon]
                                    try:
                                        with open('geocode_cache.json', 'w', encoding='utf-8') as cf:
                                            json.dump(cache, cf)
                                    except Exception as werr:
                                        logger.debug("Failed writing geocode cache: %s", werr)
                            time.sleep(1)  # be polite to Nominatim
                    except Exception as gerr:
                        logger.debug("Geocoding error: %s", gerr)
                        lat, lon = None, None

                # Build a stable id to reduce duplicates
                base_id = f"{msg_time.isoformat() if msg_time else ''}|{text[:120] if text else ''}"
                msg_id = hashlib.sha256(base_id.encode('utf-8')).hexdigest()

                row = {
                    'id': msg_id,
                    'time': msg_time.isoformat() if msg_time else None,
                    'total_views': views,
                    'message': text,
                    'video_links': '|'.join(videos),
                    'video_durations': '|'.join(durations),
                    'image_links': '|'.join(images),
                    'subject': None,
                    'matched_city': village_or_city,
                    'city_result': city_result,
                    'lat': lat,
                    'lon': lon
                }

                try:
                    producer.produce(topic, value=json.dumps(row).encode('utf-8'))
                    producer.poll(0)
                except Exception as e:
                    logger.error("Kafka error: %s", e)

                rows_to_insert.append(row)

                with open('output.json', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(row) + '\n')

            if rows_to_insert:
                insert_into_postgres_batch(conn, rows_to_insert)

        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)

    producer.flush()

finally:
    if driver:
        driver.quit()
    if conn:
        conn.close()
