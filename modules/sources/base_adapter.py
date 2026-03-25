# modules/sources/base_adapter.py
"""
Base class for all source adapters.
New sources (RSS, Twitter, Reddit) extend this class.
"""

import json
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    """
    Abstract base class for news source adapters.
    Every adapter must implement `fetch_stories()` which yields story dicts.
    """

    source_name = 'unknown'  # Override in subclass

    def __init__(self, producer=None, topic='eyesonpalestine', filter_fn=None):
        """
        Args:
            producer: Kafka Producer instance (or None for dry-run)
            topic: Kafka topic to produce to
            filter_fn: function(text) -> (matched_city, city_result) or (None, None)
        """
        self.producer = producer
        self.topic = topic
        self.filter_fn = filter_fn

    @abstractmethod
    def fetch_stories(self):
        """
        Yield story dicts with at minimum these fields:
          - message: str
          - time: datetime or ISO string or None
          - matched_city: str or None
          - city_result: str or None
          - lat: float or None
          - lon: float or None
          
        Optional fields:
          - total_views: int
          - video_links: str (pipe-separated)
          - image_links: str (pipe-separated)
          - subject: str
          - tags: str
        """
        pass

    def generate_id(self, story):
        """Generate a stable dedup ID from story content."""
        time_str = ''
        if story.get('time'):
            t = story['time']
            time_str = t.isoformat() if isinstance(t, datetime) else str(t)
        base = f"{time_str}|{(story.get('message') or '')[:120]}"
        return hashlib.sha256(base.encode('utf-8')).hexdigest()

    def normalize_story(self, story):
        """Ensure all required fields exist and add source metadata."""
        story.setdefault('source', self.source_name)
        story.setdefault('total_views', None)
        story.setdefault('video_links', '')
        story.setdefault('image_links', '')
        story.setdefault('subject', None)
        story.setdefault('tags', None)
        story.setdefault('matched_city', None)
        story.setdefault('city_result', None)
        story.setdefault('lat', None)
        story.setdefault('lon', None)
        
        # Generate ID if missing
        if 'id' not in story:
            story['id'] = self.generate_id(story)
        
        # Serialize time
        if isinstance(story.get('time'), datetime):
            story['time'] = story['time'].isoformat()
        
        return story

    def produce(self, story):
        """Send a normalized story to Kafka."""
        story = self.normalize_story(story)
        
        if self.producer:
            try:
                self.producer.produce(
                    self.topic,
                    value=json.dumps(story).encode('utf-8')
                )
                self.producer.poll(0)
                logger.info("[%s] Sent: %s | %s",
                           self.source_name,
                           story.get('matched_city', '?'),
                           (story.get('message') or '')[:50])
            except Exception as e:
                logger.error("[%s] Kafka error: %s", self.source_name, e)
        
        return story

    def run(self):
        """Fetch all stories and produce them to Kafka. Returns count of stories sent."""
        count = 0
        for story in self.fetch_stories():
            self.produce(story)
            count += 1
        
        if self.producer:
            self.producer.flush()
        
        logger.info("[%s] Total stories produced: %d", self.source_name, count)
        return count
