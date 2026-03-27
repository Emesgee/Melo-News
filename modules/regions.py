# modules/regions.py
"""
Multi-region support (P2-11).
Configurable GeoJSON sources for different conflict zones.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Default regions with GeoJSON paths and Kafka topic configuration
REGIONS = {
    'palestine': {
        'name': 'Palestine',
        'geojson_path': os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns.geojson'),
        'kafka_topic': 'eyesonpalestine',
        'center': [31.9, 35.2],
        'zoom': 10,
        'telegram_channels': ['QudsNen', 'eye_on_palestine'],
        'active': True,
    },
    # Future regions — add GeoJSON files and set active=True to enable
    'yemen': {
        'name': 'Yemen',
        'geojson_path': os.path.join(os.path.dirname(__file__), '..', 'data', 'yemen_towns.geojson'),
        'kafka_topic': 'eyesonyemen',
        'center': [15.5, 48.5],
        'zoom': 6,
        'telegram_channels': [],
        'active': False,
    },
    'sudan': {
        'name': 'Sudan',
        'geojson_path': os.path.join(os.path.dirname(__file__), '..', 'data', 'sudan_towns.geojson'),
        'kafka_topic': 'eyesonsudan',
        'center': [12.8, 30.2],
        'zoom': 6,
        'telegram_channels': [],
        'active': False,
    },
    'ukraine': {
        'name': 'Ukraine',
        'geojson_path': os.path.join(os.path.dirname(__file__), '..', 'data', 'ukraine_towns.geojson'),
        'kafka_topic': 'eyesonukraine',
        'center': [48.3, 31.2],
        'zoom': 6,
        'telegram_channels': [],
        'active': False,
    },
}


def get_active_regions():
    """Return only active regions."""
    return {k: v for k, v in REGIONS.items() if v.get('active')}


def get_region(region_id):
    """Get a specific region config."""
    return REGIONS.get(region_id)


def load_region_geojson(region_id):
    """Load GeoJSON data for a region."""
    region = REGIONS.get(region_id)
    if not region:
        return None
    
    path = region['geojson_path']
    if not os.path.exists(path):
        logger.warning("GeoJSON not found for region %s: %s", region_id, path)
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error loading GeoJSON for %s: %s", region_id, e)
        return None
