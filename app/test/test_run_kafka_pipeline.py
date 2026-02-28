import pytest
import subprocess
import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import from root directory
try:
    from run_kafka_pipeline import KafkaPipeline
except ImportError:
    # Fallback: try adding root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")
    from run_kafka_pipeline import KafkaPipeline

# Get root directory
ROOT_DIR = os.path.join(os.path.dirname(__file__), "../..")


class TestKafkaPipelineInitialization:
    """Test pipeline initialization"""
    
    def test_pipeline_init(self):
        """Test pipeline initializes correctly"""
        pipeline = KafkaPipeline()
        assert pipeline.producer_process is None
        assert pipeline.consumer_process is None
    
    def test_pipeline_attributes(self):
        """Test pipeline has required attributes"""
        pipeline = KafkaPipeline()
        assert hasattr(pipeline, 'producer_process')
        assert hasattr(pipeline, 'consumer_process')
        assert hasattr(pipeline, 'run_producer')
        assert hasattr(pipeline, 'run_consumer')
        assert hasattr(pipeline, 'start_pipeline')
        assert hasattr(pipeline, 'stop_pipeline')


class TestKafkaPipelineShutdown:
    """Test graceful shutdown"""
    
    def test_stop_pipeline_terminates_producer(self):
        """Test stop_pipeline terminates producer"""
        pipeline = KafkaPipeline()
        mock_producer = MagicMock()
        pipeline.producer_process = mock_producer
        pipeline.stop_pipeline()
        mock_producer.terminate.assert_called_once()
    
    def test_stop_pipeline_terminates_consumer(self):
        """Test stop_pipeline terminates consumer"""
        pipeline = KafkaPipeline()
        mock_consumer = MagicMock()
        pipeline.consumer_process = mock_consumer
        pipeline.stop_pipeline()
        mock_consumer.terminate.assert_called_once()


class TestKafkaPipelineFiles:
    """Test required files exist"""
    
    def test_kafka_producer_exists(self):
        """Test kafkaProducer.py exists"""
        kafka_producer_path = os.path.join(ROOT_DIR, 'kafkaProducer.py')
        assert os.path.exists(kafka_producer_path), f"kafkaProducer.py not found at {kafka_producer_path}"
    
    def test_kafka_consumer_exists(self):
        """Test kafkaConsumer.py exists"""
        kafka_consumer_path = os.path.join(ROOT_DIR, 'kafkaConsumer.py')
        assert os.path.exists(kafka_consumer_path), f"kafkaConsumer.py not found at {kafka_consumer_path}"
    
    def test_run_kafka_pipeline_exists(self):
        """Test run_kafka_pipeline.py exists"""
        run_pipeline_path = os.path.join(ROOT_DIR, 'run_kafka_pipeline.py')
        assert os.path.exists(run_pipeline_path), f"run_kafka_pipeline.py not found at {run_pipeline_path}"