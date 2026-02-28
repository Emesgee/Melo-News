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
        
        consumer_thread = Thread(target=self.run_consumer, daemon=False)
        consumer_thread.start()
        
        logger.info("⏳ Waiting for consumer to connect to Kafka broker...\n")
        time.sleep(5)
        
        producer_thread = Thread(target=self.run_producer, daemon=False)
        producer_thread.start()
        
        logger.info("\n✅ Pipeline is running!")
        
        try:
            consumer_thread.join()
            producer_thread.join()
        except KeyboardInterrupt:
            self.stop_pipeline()
    
    def stop_pipeline(self):
        """Stop both processes gracefully"""
        logger.info("\n🛑 SHUTTING DOWN PIPELINE")
        
        if self.producer_process:
            self.producer_process.terminate()
            try:
                self.producer_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.producer_process.kill()
        
        if self.consumer_process:
            self.consumer_process.terminate()
            try:
                self.consumer_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.consumer_process.kill()
        
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
