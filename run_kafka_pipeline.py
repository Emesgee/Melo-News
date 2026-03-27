import subprocess
import time
import logging
import os
import sys
from threading import Thread

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s'
)
logger = logging.getLogger("KafkaPipeline")

class KafkaPipeline:
    def __init__(self):
        self.producer_process = None
        self.consumer_process = None

    def run_consumer(self):
        """Run Kafka Consumer (processes messages → PostgreSQL)"""
        logger.info("=" * 80)
        logger.info("🔄 CONSUMER: Starting Kafka Consumer")
        logger.info("=" * 80)
        
        try:
            # ✅ Set UTF-8 encoding for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.consumer_process = subprocess.Popen(
                [sys.executable, 'kafkaConsumer.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )
            
            for line in self.consumer_process.stdout:
                if line:
                    print(line.rstrip())
                    logger.info(f"[CONSUMER] {line.rstrip()}")
        
        except Exception as e:
            logger.error(f"❌ Consumer failed: {e}")
            print(f"❌ CONSUMER ERROR: {e}")
    
    def run_producer(self):
        """Run Kafka Producer (all sources → Kafka)"""
        logger.info("=" * 80)
        logger.info("🌐 PRODUCER: Starting multi-source ingestion")
        logger.info("   [1] Telegram    — 11 verified channels (Selenium scraper)")
        logger.info("   [2] RSS         — 10 feeds (feedparser)")
        logger.info("   [3] Reddit      — 5 subreddits × 7 search terms (JSON + RSS fallback)")
        logger.info("   [4] Twitter/X   — 20 accounts via nitter RSS + X API v2")
        logger.info("   Topic: eyesonpalestine")
        logger.info("=" * 80)
        
        try:
            # ✅ Set UTF-8 encoding for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.producer_process = subprocess.Popen(
                [sys.executable, 'kafkaProducer.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )
            
            # Read producer output until it exits
            for line in self.producer_process.stdout:
                if line:
                    logger.info(f"[PRODUCER] {line.rstrip()}")
            
            # Wait for process to actually finish
            self.producer_process.wait(timeout=300)
            logger.info("[PRODUCER] Producer process finished successfully")
        
        except subprocess.TimeoutExpired:
            logger.error("Producer timeout - killing process")
            self.producer_process.kill()
        except Exception as e:
            logger.error(f"❌ Producer failed: {e}")
    
    def start_pipeline(self):
        """Start both producer and consumer"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 MELO-NEWS KAFKA DATA PIPELINE STARTING")
        logger.info("=" * 80)
        logger.info("\n📊 Pipeline Architecture:")
        logger.info("   ┌──────────────────────────────────────────────────────────────┐")
        logger.info("   │  [1] Telegram    11 verified channels (Selenium)              │")
        logger.info("   │  [2] RSS         10 feeds (feedparser)                        │")
        logger.info("   │  [3] Reddit      5 subs × 7 terms (JSON + RSS fallback)       │")
        logger.info("   │  [4] Twitter/X   20 accounts (nitter + X API)                 │")
        logger.info("   │              ↓ filter by Palestinian location               │")
        logger.info("   │              ↓ geocode via GeoJSON/Nominatim               │")
        logger.info("   │    Kafka Topic: eyesonpalestine                             │")
        logger.info("   │              ↓ kafkaConsumer.py                            │")
        logger.info("   │    Enrich location · download media · deduplicate          │")
        logger.info("   │              ↓                                              │")
        logger.info("   │    PostgreSQL (telegram table)                              │")
        logger.info("   └──────────────────────────────────────────────────────────────┘")
        logger.info("\n" + "=" * 80 + "\n")
        
        # Start producer FIRST (begins scraping Telegram)
        producer_thread = Thread(target=self.run_producer, daemon=False)
        producer_thread.start()
        
        # Wait for producer to finish (it will exit after sending messages)
        logger.info("⏳ Waiting for producer to finish scraping and sending to Kafka...\n")
        producer_thread.join(timeout=600)  # Wait up to 10 minutes
        
        if producer_thread.is_alive():
            logger.error("Producer thread still running after timeout!")
            return
        
        logger.info("\n✅ Producer finished! Starting consumer...\n")
        time.sleep(2)  # Small delay
        
        # Start consumer (it waits for messages on Kafka)
        consumer_thread = Thread(target=self.run_consumer, daemon=False)
        consumer_thread.start()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Pipeline is running!")
        logger.info("=" * 80)
        logger.info("\n📝 What's happening:")
        logger.info("   1. Producer scraped 11 Telegram channels (Selenium headless Chrome)")
        logger.info("   2. Producer fetched 10 RSS feeds (feedparser)")
        logger.info("   3. Producer fetched Reddit posts (5 subs × 7 terms)")
        logger.info("   4. Producer fetched Twitter/X (20 accounts)")
        logger.info("   5. All sources filtered by Palestinian locations (GeoJSON)")
        logger.info("   6. All messages geocoded and produced to Kafka topic")
        logger.info("   7. Consumer reading + enriching location if missing")
        logger.info("   8. Downloading/uploading videos and images")
        logger.info("   9. Storing in PostgreSQL database")
        logger.info("\n📌 Press Ctrl+C to stop the pipeline gracefully\n")
        
        try:
            consumer_thread.join()
        except KeyboardInterrupt:
            self.stop_pipeline()
    
    def stop_pipeline(self):
        """Stop both processes gracefully"""
        logger.info("\n" + "=" * 80)
        logger.info("🛑 SHUTTING DOWN PIPELINE")
        logger.info("=" * 80)
        
        # Stop producer first
        if self.producer_process and self.producer_process.poll() is None:
            logger.info("Stopping Producer (Telegram scraper)...")
            self.producer_process.terminate()
            try:
                self.producer_process.wait(timeout=10)
                logger.info("✅ Producer stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  Producer did not stop, forcing kill...")
                self.producer_process.kill()
                logger.info("✅ Producer killed")
        
        # Stop consumer
        if self.consumer_process and self.consumer_process.poll() is None:
            logger.info("Stopping Consumer (database processor)...")
            self.consumer_process.terminate()
            try:
                self.consumer_process.wait(timeout=10)
                logger.info("✅ Consumer stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  Consumer did not stop, forcing kill...")
                self.consumer_process.kill()
                logger.info("✅ Consumer killed")
        
        logger.info("=" * 80)
        logger.info("Pipeline shutdown complete ✅\n")

if __name__ == '__main__':
    pipeline = KafkaPipeline()
    
    try:
        pipeline.start_pipeline()
    except KeyboardInterrupt:
        pipeline.stop_pipeline()
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        pipeline.stop_pipeline()
        sys.exit(1)