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
            self.consumer_process = subprocess.Popen(
                [sys.executable, 'kafkaConsumer.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.consumer_process.stdout:
                if line:
                    print(f"[CONSUMER] {line.rstrip()}")
                    logger.info(f"[CONSUMER] {line.rstrip()}")
        
        except Exception as e:
            logger.error(f"❌ Consumer failed: {e}")
            print(f"❌ CONSUMER ERROR: {e}")
            sys.exit(1)
    
    def run_producer(self):
        """Run Kafka Producer (scrapes Telegram → produces to Kafka)"""
        logger.info("=" * 80)
        logger.info("📱 PRODUCER: Starting Telegram Scraper")
        logger.info("   Channels: QudsNen, eye_on_palestine")
        logger.info("   Topic: eyesonpalestine")
        logger.info("   Action: Scrape Telegram → Filter by Palestinian location → Produce to Kafka")
        logger.info("=" * 80)
        
        try:
            self.producer_process = subprocess.Popen(
                [sys.executable, 'kafkaProducer.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.producer_process.stdout:
                if line:
                    logger.info(f"[PRODUCER] {line.rstrip()}")
        
        except Exception as e:
            logger.error(f"❌ Producer failed: {e}")
            sys.exit(1)
    
    def start_pipeline(self):
        """Start both producer and consumer"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 MELO-NEWS KAFKA DATA PIPELINE STARTING")
        logger.info("=" * 80)
        logger.info("\n📊 Pipeline Architecture:")
        logger.info("   ┌─────────────────────────────────────────────────────────┐")
        logger.info("   │  Telegram Channels (QudsNen, eye_on_palestine)          │")
        logger.info("   │              ↓ (kafkaProducer.py scrapes)               │")
        logger.info("   │  Filter by Palestinian Location (Gaza, Khan Younis...) │")
        logger.info("   │              ↓ (produces messages)                      │")
        logger.info("   │  Kafka Topic: eyesonpalestine                          │")
        logger.info("   │              ↓ (kafkaConsumer.py consumes)             │")
        logger.info("   │  Detect Location + Download Media                      │")
        logger.info("   │              ↓ (processes data)                         │")
        logger.info("   │  PostgreSQL Database (stored data)                     │")
        logger.info("   └─────────────────────────────────────────────────────────┘")
        logger.info("\n" + "=" * 80 + "\n")
        
        # Start producer FIRST (begins scraping Telegram)
        producer_thread = Thread(target=self.run_producer, daemon=False)
        producer_thread.start()
        
        # Give producer time to start producing messages
        logger.info("⏳ Waiting for producer to start scraping Telegram...\n")
        time.sleep(5)
        
        # Start consumer (it waits for messages on Kafka)
        consumer_thread = Thread(target=self.run_consumer, daemon=False)
        consumer_thread.start()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Pipeline is running!")
        logger.info("=" * 80)
        logger.info("\n📝 What's happening:")
        logger.info("   1. Producer scrapes Telegram channels for Palestinian news")
        logger.info("   2. Filters messages by Palestinian locations (GeoJSON)")
        logger.info("   3. Produces valid messages to Kafka topic")
        logger.info("   4. Consumer reads from Kafka topic")
        logger.info("   5. Detects location if missing")
        logger.info("   6. Downloads/uploads videos and images")
        logger.info("   7. Stores in PostgreSQL database")
        logger.info("\n📌 Press Ctrl+C to stop the pipeline gracefully\n")
        
        try:
            producer_thread.join()
            consumer_thread.join()
        except KeyboardInterrupt:
            self.stop_pipeline()
    
    def stop_pipeline(self):
        """Stop both processes gracefully"""
        logger.info("\n" + "=" * 80)
        logger.info("🛑 SHUTTING DOWN PIPELINE")
        logger.info("=" * 80)
        
        # Stop producer first
        if self.producer_process:
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
        if self.consumer_process:
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