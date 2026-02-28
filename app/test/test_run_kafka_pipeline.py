import pytest
import subprocess
import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from run_kafka_pipeline import KafkaPipeline


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
        assert os.path.exists('kafkaProducer.py')
    
    def test_kafka_consumer_exists(self):
        """Test kafkaConsumer.py exists"""
        assert os.path.exists('kafkaConsumer.py')
    
    def test_run_kafka_pipeline_exists(self):
        """Test run_kafka_pipeline.py exists"""
        assert os.path.exists('run_kafka_pipeline.py')