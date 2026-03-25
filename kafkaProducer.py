import os
import time
import json
import tempfile
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from confluent_kafka import Producer
from modules.pipeline_task import detect_and_geocode, build_kafka_row
from modules.sources.rss_adapter import RSSAdapter
from modules.sources.reddit_adapter import RedditAdapter
from modules.sources.twitter_adapter import TwitterAdapter
from modules.sources.upscrolled_adapter import UpScrolledAdapter
from modules.sources.settler_violence_sources import (
    SETTLER_VIOLENCE_TOPICS,
    TELEGRAM_CHANNELS,
    SETTLER_VIOLENCE_RSS_FEEDS,
    SETTLER_VIOLENCE_TWITTER_ACCOUNTS,
    SETTLER_VIOLENCE_TWITTER_SEARCH_TERMS,
    SETTLER_VIOLENCE_SUBREDDITS,
    SETTLER_VIOLENCE_REDDIT_SEARCH_TERMS,
    SETTLER_VIOLENCE_UPSCROLLED_TAGS,
    SETTLER_VIOLENCE_UPSCROLLED_CHANNELS,
)
# -------------------------
# Logging
# -------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("kafkaProducer")
print(f"[LOGGING] Level set to: {LOG_LEVEL}")




# -------------------------
# Telegram URLs — verified channels × settler violence topics
# -------------------------
topics = SETTLER_VIOLENCE_TOPICS  # ['settler', 'settler violence', ...]
telegram_channels = [handle for handle, _desc in TELEGRAM_CHANNELS]

# Build URLs: each channel searched for the primary topic
primary_topic = topics[0]  # 'settler'
telegram_urls = [
    f'https://t.me/s/{ch}?q={primary_topic.replace(" ", "+")}'
    for ch in telegram_channels
]
print(f"[CONFIG] Telegram channels to scrape: {len(telegram_urls)} (topic: {primary_topic})")
print(f"[CONFIG] Sample channels: {telegram_channels[:5]}")

SCRAPER_KEYWORDS = [t.strip().lower() for t in topics if t.strip()]
print(f"[CONFIG] Scraper keywords: {SCRAPER_KEYWORDS}")



# -------------------------
# Load Palestinian towns from GeoJSON (has all locations)
# -------------------------
try:
    from modules.geocoder import geojson_coords
    all_villages = geojson_coords
    all_cities = set()
    logger.info(f"[CONFIG] Loaded {len(all_villages)} Palestinian towns from GeoJSON")
    if len(all_villages) > 0:
        sample = list(all_villages.keys())[:5]
        logger.info(f"[CONFIG] Sample towns: {sample}")
except ImportError as import_err:
    logger.warning(f"Could not load GeoJSON locations: {import_err}, using CSV fallback")
    all_villages = {}
    all_cities = set()

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
            # all_villages now contains dicts, extract the town name
            town_name = word if isinstance(all_villages[word], dict) else all_villages[word]
            return town_name, town_name
    # Substring fallbacks (for multi-word towns)
    for village_lc in all_villages.keys():
        if village_lc and village_lc in text_lower:
            return village_lc, village_lc
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
            print(f"[DEBUG] Parsed time text: {time_text}")
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

# ──────────────────────────────────────────────────────────
# Benchmark helpers
# ──────────────────────────────────────────────────────────
_bench_sources = []   # list of dicts recorded per source

def _record(name, found, filtered, sent, duration):
    _bench_sources.append({
        'name':     name,
        'found':    found,
        'filtered': filtered,
        'sent':     sent,
        'duration': duration,
    })

def _print_benchmark(chrome_secs, total_secs):
    """Print a formatted benchmark summary table."""
    col = [24, 7, 9, 7, 9, 8]
    div = '╠' + '╬'.join('═' * c for c in col) + '╣'
    top = '╔' + '╦'.join('═' * c for c in col) + '╗'
    bot = '╚' + '╩'.join('═' * c for c in col) + '╝'
    hdr = '╠' + '╬'.join('═' * c for c in col) + '╣'

    def row(cells):
        parts = [str(c).center(col[i]) for i, c in enumerate(cells)]
        return '║' + '║'.join(parts) + '║'

    print('\n' + top)
    print(row(['Source', 'Found', 'Filtered', 'Sent', 'Time(s)', 'msg/s']))
    print(hdr)
    print(row(['Chrome startup', '-', '-', '-', f'{chrome_secs:.1f}', '-']))
    print(div)
    t_found = t_filt = t_sent = 0
    for s in _bench_sources:
        spd = f"{s['sent']/s['duration']:.2f}" if s['duration'] > 0 else '-'
        f_str = str(s['found']) if s['found'] is not None else '-'
        fl_str = str(s['filtered']) if s['filtered'] is not None else '-'
        print(row([s['name'][:24], f_str, fl_str, s['sent'], f"{s['duration']:.1f}", spd]))
        if s['found'] is not None:  t_found += s['found']
        if s['filtered'] is not None: t_filt  += s['filtered']
        t_sent += s['sent']
    print(div)
    tot_spd = f"{t_sent/total_secs:.2f}" if total_secs > 0 else '-'
    print(row(['TOTAL', t_found, t_filt, t_sent, f'{total_secs:.1f}', tot_spd]))
    print(bot + '\n')

# ──────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────
driver   = None
producer = None
_t_total = time.perf_counter()

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

    _t_chrome_start = time.perf_counter()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    _chrome_secs = time.perf_counter() - _t_chrome_start
    logger.info(f"[BENCH] Chrome ready in {_chrome_secs:.1f}s")

    # Kafka
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC', 'eyesonpalestine')
    producer = Producer({'bootstrap.servers': bootstrap_servers})
    logger.info(f"Kafka producer connected to {bootstrap_servers}, topic: {topic}")

    for url in telegram_urls:
        _t_url = time.perf_counter()
        _channel = url.split('/')[4].split('?')[0]   # e.g. QudsNen
        try:
            driver.get(url)
            elements = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'tgme_widget_message_bubble'))
            )
            _t_loaded = time.perf_counter()
            logger.info(f"[BENCH] {_channel}: page loaded in {_t_loaded - _t_url:.1f}s")

            # Chunked scrolling
            for _ in range(10):
                driver.execute_script("window.scrollBy(0, 1000)")
                time.sleep(0.5)
            _t_scrolled = time.perf_counter()
            logger.info(f"[BENCH] {_channel}: scrolled in {_t_scrolled - _t_loaded:.1f}s")

            elements = driver.find_elements(By.CLASS_NAME, 'tgme_widget_message_bubble')
            messages_sent = 0
            messages_found = len(elements)
            messages_filtered = 0
            _msg_times = []   # per-message processing durations

            logger.info(f"Found {messages_found} total messages on page")

            for element in elements:
                _t_msg = time.perf_counter()
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)
                except:
                    pass

                text = extract_message_text(element)

                # Debug: log first few messages to see what content we're getting
                if messages_sent + messages_filtered < 3:
                    logger.info(f"Message sample: {text[:200]}...")
                
                # Extract location - must have Palestinian location to proceed
                village_or_city, city_result = filter_location(text)
                if not village_or_city:
                    messages_filtered += 1
                    logger.debug(f"Filtered out (no Palestinian location): {text[:80]}...")
                    continue

                msg_time = parse_time(element)
                views = parse_views(element)
                videos = extract_video_links(element)
                durations = extract_video_durations(element)
                images = extract_image_links(element)
                
                # Build and enrich row via pipeline_task (accurate location)
                row = build_kafka_row({
                    'time':            msg_time,
                    'total_views':     views,
                    'message':         text,
                    'video_links':     '|'.join(videos),
                    'video_durations': '|'.join(durations),
                    'image_links':     '|'.join(images),
                    'subject':         None,
                    'tags':            f'telegram, settler_violence, {url.split("/")[4].split("?")[0]}',
                    'source':          'telegram',
                    'matched_city':    village_or_city,
                    'city_result':     city_result,
                    'lat':             None,
                    'lon':             None,
                })

                try:
                    producer.produce(topic, value=json.dumps(row).encode('utf-8'))
                    producer.poll(0)
                    messages_sent += 1
                    logger.info(f"Sent to Kafka: {village_or_city} | {text[:50]}...")
                except Exception as e:
                    logger.error("Kafka error: %s", e)

                with open('output.json', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(row) + '\n')

                _msg_times.append(time.perf_counter() - _t_msg)

            _url_dur = time.perf_counter() - _t_url
            _avg_msg = (sum(_msg_times) / len(_msg_times)) if _msg_times else 0
            logger.info(f"Scraped {_channel}:")
            logger.info(f"  Total messages found:   {messages_found}")
            logger.info(f"  Filtered out:           {messages_filtered}")
            logger.info(f"  Sent to Kafka:          {messages_sent}")
            logger.info(f"[BENCH] {_channel}: total={_url_dur:.1f}s  avg/msg={_avg_msg:.2f}s")
            _record(f'Telegram/{_channel}', messages_found, messages_filtered, messages_sent, _url_dur)

        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)

    producer.flush()
    logger.info("[TELEGRAM] All Telegram messages flushed to Kafka")

    # ── RSS Sources (14 settler-violence feeds) ────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("[RSS] Starting RSS feed ingestion (14 settler violence feeds)...")
    logger.info("=" * 60)
    _t_rss = time.perf_counter()
    try:
        rss = RSSAdapter(
            feeds=SETTLER_VIOLENCE_RSS_FEEDS,
            producer=producer, topic=topic, filter_fn=filter_location,
        )
        rss_sent = rss.run()
        _rss_dur = time.perf_counter() - _t_rss
        logger.info(f"[RSS] Done: {rss_sent} stories sent in {_rss_dur:.1f}s")
        _record('RSS (14 feeds)', None, None, rss_sent, _rss_dur)
    except Exception as e:
        logger.error("[RSS] Failed: %s", e)
        _record('RSS (14 feeds)', None, None, 0, time.perf_counter() - _t_rss)

    # ── Reddit Sources (5 subs × 7 settler terms) ─────────────────
    logger.info("\n" + "=" * 60)
    logger.info("[REDDIT] Starting Reddit ingestion (settler violence)...")
    logger.info("=" * 60)
    _t_reddit = time.perf_counter()
    try:
        reddit = RedditAdapter(
            subreddits=SETTLER_VIOLENCE_SUBREDDITS,
            search_terms=SETTLER_VIOLENCE_REDDIT_SEARCH_TERMS,
            producer=producer, topic=topic, filter_fn=filter_location,
        )
        reddit_sent = reddit.run()
        _reddit_dur = time.perf_counter() - _t_reddit
        logger.info(f"[REDDIT] Done: {reddit_sent} stories sent in {_reddit_dur:.1f}s")
        _record('Reddit (5 subs)', None, None, reddit_sent, _reddit_dur)
    except Exception as e:
        logger.error("[REDDIT] Failed: %s", e)
        _record('Reddit (5 subs)', None, None, 0, time.perf_counter() - _t_reddit)

    # ── Twitter/X Sources (20 accts + 9 settler terms) ────────────
    logger.info("\n" + "=" * 60)
    logger.info("[TWITTER] Starting Twitter/X ingestion (settler violence)...")
    logger.info("=" * 60)
    _t_twitter = time.perf_counter()
    try:
        twitter = TwitterAdapter(
            accounts=SETTLER_VIOLENCE_TWITTER_ACCOUNTS,
            search_terms=SETTLER_VIOLENCE_TWITTER_SEARCH_TERMS,
            producer=producer, topic=topic, filter_fn=filter_location,
        )
        twitter_sent = twitter.run()
        _twitter_dur = time.perf_counter() - _t_twitter
        logger.info(f"[TWITTER] Done: {twitter_sent} stories sent in {_twitter_dur:.1f}s")
        _record('Twitter/X (20 accts)', None, None, twitter_sent, _twitter_dur)
    except Exception as e:
        logger.error("[TWITTER] Failed: %s", e)
        _record('Twitter/X (20 accts)', None, None, 0, time.perf_counter() - _t_twitter)

    # ── Final benchmark table
    _print_benchmark(_chrome_secs, time.perf_counter() - _t_total)

finally:
    if driver:
        driver.quit()
