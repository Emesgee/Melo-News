# app/ai_analyzer/confidence.py
"""
AI-powered confidence scoring and severity classification for news stories.
Implements P0-1 (Confidence Scoring) and P0-3 (Severity Classification).
"""

import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Severity Classification ---

# Keywords that indicate HIGH severity events
HIGH_SEVERITY_KEYWORDS = [
    'killed', 'martyred', 'massacre', 'bombing', 'airstrike', 'air strike',
    'shelling', 'explosion', 'destroyed', 'casualties', 'death toll',
    'invasion', 'ground operation', 'war crime', 'genocide', 'ethnic cleansing',
    'hospital attacked', 'school attacked', 'refugee camp', 'mass displacement',
    'chemical', 'missile strike', 'ballistic', 'siege', 'blockade',
    'execution', 'assassination', 'hostage', 'prisoner', 'torture',
    'ceasefire violation', 'escalation', 'declared war', 'state of emergency',
    'humanitarian crisis', 'famine', 'starvation', 'infrastructure destroyed',
    # Settler violence — HIGH severity
    'settler pogrom', 'settler rampage', 'settler shooting', 'settler lynch',
    'settler mob', 'homes torched', 'village burned', 'family attacked',
    'settler killed', 'shot by settlers', 'settler arson homes',
    'settler stabbing', 'settlers opened fire', 'settler car ramming',
]

# Keywords that indicate MEDIUM severity events  
MEDIUM_SEVERITY_KEYWORDS = [
    'protest', 'demonstration', 'clash', 'confrontation', 'tear gas',
    'rubber bullets', 'arrest', 'detained', 'raid', 'incursion',
    'settler violence', 'checkpoint', 'roadblock', 'curfew',
    'displacement', 'evacuation', 'warning', 'threat', 'tension',
    'sanction', 'resolution', 'negotiation', 'ceasefire talks',
    'humanitarian aid', 'relief', 'reconstruction', 'injured', 'wounded',
    # Settler violence — MEDIUM severity
    'settler attack', 'settler harassment', 'settler intimidation',
    'olive trees destroyed', 'olive trees uprooted', 'crop destruction',
    'price tag', 'price tag attack', 'hilltop youth',
    'settler outpost', 'illegal outpost', 'settlement expansion',
    'land confiscation', 'demolition order', 'home demolition',
    'settler road blocked', 'settler stone throwing', 'water supply cut',
    'shepherd attacked', 'livestock killed', 'agricultural land seized',
    'settler graffiti', 'mosque vandalized', 'church vandalized',
    'school vandalized', 'car vandalized', 'property damage settlers',
]

# LOW severity: everything else (general updates, statements, etc.)


def classify_severity(text):
    """
    Classify story severity as HIGH, MEDIUM, or LOW based on content analysis.
    
    Args:
        text: The story message/description text
        
    Returns:
        str: 'HIGH', 'MEDIUM', or 'LOW'
    """
    if not text:
        return 'LOW'
    
    text_lower = text.lower()
    
    # Check HIGH keywords first
    high_matches = sum(1 for kw in HIGH_SEVERITY_KEYWORDS if kw in text_lower)
    if high_matches >= 2:
        return 'HIGH'
    if high_matches >= 1:
        # Single high keyword + length check (longer = more detail = likely serious)
        if len(text) > 100:
            return 'HIGH'
        return 'MEDIUM'
    
    # Check MEDIUM keywords
    medium_matches = sum(1 for kw in MEDIUM_SEVERITY_KEYWORDS if kw in text_lower)
    if medium_matches >= 2:
        return 'MEDIUM'
    if medium_matches >= 1:
        return 'MEDIUM'
    
    return 'LOW'


# --- Confidence Scoring ---

def calculate_confidence(story_data):
    """
    Calculate a confidence/credibility score (0.0 - 1.0) for a news story.
    
    Factors:
    - Source reliability (known channels score higher)
    - Media attachment presence (images/video = more credible)
    - Text length and detail (longer, more detailed = higher confidence)
    - Location specificity (has coordinates = more credible)
    - Corroboration (source_count > 1 = higher confidence)
    - Recency (newer stories get a slight boost)
    
    Args:
        story_data: dict with keys like message, image_links, video_links,
                    lat, lon, source, source_count, time, total_views
                    
    Returns:
        float: confidence score between 0.0 and 1.0
    """
    score = 0.0
    weights = {
        'source': 0.20,
        'media': 0.20,
        'detail': 0.15,
        'location': 0.15,
        'corroboration': 0.15,
        'recency': 0.10,
        'views': 0.05,
    }
    
    # 1. Source reliability
    source = (story_data.get('source') or 'unknown').lower()
    source_scores = {
        'telegram': 0.7,       # Known channels, semi-reliable
        'rss': 0.85,           # Established news outlets
        'citizen_upload': 0.6, # Citizen journalism — starts moderate, boosted by EXIF
        'twitter': 0.5,        # Social media, less reliable
        'reddit': 0.4,         # Aggregated, least reliable
        'unknown': 0.3,
    }
    score += weights['source'] * source_scores.get(source, 0.3)
    
    # 2. Media presence
    has_images = bool(story_data.get('image_links'))
    has_video = bool(story_data.get('video_links'))
    if has_video:
        score += weights['media'] * 1.0
    elif has_images:
        score += weights['media'] * 0.7
    else:
        score += weights['media'] * 0.2
    
    # 3. Text detail/length
    message = story_data.get('message') or ''
    text_len = len(message)
    if text_len > 500:
        score += weights['detail'] * 1.0
    elif text_len > 200:
        score += weights['detail'] * 0.7
    elif text_len > 50:
        score += weights['detail'] * 0.4
    else:
        score += weights['detail'] * 0.1
    
    # 4. Location specificity
    has_coords = story_data.get('lat') is not None and story_data.get('lon') is not None
    has_city = bool(story_data.get('matched_city'))
    if has_coords and has_city:
        score += weights['location'] * 1.0
    elif has_coords or has_city:
        score += weights['location'] * 0.6
    else:
        score += weights['location'] * 0.1
    
    # 5. Corroboration (multi-source confirmation)
    source_count = story_data.get('source_count', 1)
    if source_count >= 3:
        score += weights['corroboration'] * 1.0
    elif source_count >= 2:
        score += weights['corroboration'] * 0.7
    else:
        score += weights['corroboration'] * 0.3
    
    # 6. Recency (stories < 6 hours old get a boost)
    try:
        story_time = story_data.get('time')
        if story_time:
            if isinstance(story_time, str):
                story_time = datetime.fromisoformat(story_time.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - story_time).total_seconds() / 3600
            if age_hours < 1:
                score += weights['recency'] * 1.0
            elif age_hours < 6:
                score += weights['recency'] * 0.7
            elif age_hours < 24:
                score += weights['recency'] * 0.4
            else:
                score += weights['recency'] * 0.2
    except Exception:
        score += weights['recency'] * 0.3
    
    # 7. View count (social proof)
    views = story_data.get('total_views', 0) or 0
    if views > 10000:
        score += weights['views'] * 1.0
    elif views > 1000:
        score += weights['views'] * 0.7
    elif views > 100:
        score += weights['views'] * 0.4
    else:
        score += weights['views'] * 0.1
    
    # 8. EXIF verification boosts (citizen uploads only)
    #    These reward uploads with verifiable device metadata.
    if story_data.get('exif_gps_match'):
        score += 0.08  # GPS from device = strong location proof
    if story_data.get('exif_has_timestamp'):
        score += 0.05  # Original capture time present
    if story_data.get('has_device_info'):
        score += 0.02  # Device fingerprint present

    # Clamp to [0.0, 1.0]
    return round(min(max(score, 0.0), 1.0), 2)


def score_and_classify(story_data):
    """
    Convenience function to compute both confidence and severity.
    
    Returns:
        dict: {'confidence_score': float, 'severity': str}
    """
    message = story_data.get('message') or story_data.get('description') or ''
    return {
        'confidence_score': calculate_confidence(story_data),
        'severity': classify_severity(message),
    }
