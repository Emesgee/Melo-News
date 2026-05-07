# app/analytics/engine.py
"""
Analytics engine implementing:
  P0-4: Escalation / De-escalation indicators
  P1-5: Keyword trending
  P1-6: Global Tension Index

Each feature has a legacy Telegram-only function (kept for backward compat)
and a source-agnostic *_multi variant that queries both Telegram and FileUpload.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter
from sqlalchemy import and_

logger = logging.getLogger(__name__)

# Stopwords for keyword extraction
STOPWORDS = {
    'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
    'shall', 'can', 'not', 'no', 'with', 'from', 'by', 'about', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off',
    'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
    'other', 'some', 'such', 'than', 'too', 'very', 'just', 'because', 'as',
    'until', 'while', 'its', 'it', 'this', 'that', 'these', 'those', 'he', 'she',
    'him', 'her', 'his', 'himself', 'they', 'them', 'their', 'we', 'us', 'our',
    'who', 'which', 'what', 'whom', 'up', 'down', 'also', 'so', 'if',
}


# --- P0-4: Escalation / De-escalation ---

def calculate_escalation(db, Telegram, city, hours=24):
    """
    Determine if a city is experiencing escalation or de-escalation
    by comparing story volume in the recent window vs. the previous window.
    
    Returns: 'escalation', 'de-escalation', or 'stable'
    """
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(hours=hours)
    previous_start = recent_start - timedelta(hours=hours)
    
    try:
        recent_count = Telegram.query.filter(
            and_(
                Telegram.matched_city == city,
                Telegram.time >= recent_start,
                Telegram.time < now,
            )
        ).count()
        
        previous_count = Telegram.query.filter(
            and_(
                Telegram.matched_city == city,
                Telegram.time >= previous_start,
                Telegram.time < recent_start,
            )
        ).count()
        
        if previous_count == 0 and recent_count > 0:
            return 'escalation'
        if previous_count == 0 and recent_count == 0:
            return 'stable'
        
        ratio = recent_count / max(previous_count, 1)
        
        if ratio >= 1.5:
            return 'escalation'
        elif ratio <= 0.5:
            return 'de-escalation'
        else:
            return 'stable'
    except Exception as e:
        logger.error("Escalation calculation error for %s: %s", city, e)
        return 'stable'


def calculate_all_escalations(db, Telegram, hours=24):
    """
    Calculate escalation status for all active cities.
    Returns dict: {city_name: 'escalation'|'de-escalation'|'stable'}
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours * 2)
    
    try:
        active_cities = db.session.query(
            Telegram.matched_city
        ).filter(
            Telegram.time >= cutoff,
            Telegram.matched_city.isnot(None),
        ).distinct().all()
        
        results = {}
        for (city,) in active_cities:
            if city:
                results[city] = calculate_escalation(db, Telegram, city, hours)
        return results
    except Exception as e:
        logger.error("Error calculating all escalations: %s", e)
        return {}


# --- P1-5: Keyword Trending ---

def extract_keywords(text, max_keywords=10):
    """
    Extract meaningful keywords from text using simple NLP.
    Returns list of (keyword, count) tuples.
    """
    if not text:
        return []
    
    # Clean text
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'[^\w\s#@]', ' ', text)  # Keep # and @ for hashtags/mentions
    
    words = text.lower().split()
    
    # Filter stopwords and short words
    keywords = [w for w in words if w not in STOPWORDS and len(w) > 2]
    
    # Count and return top keywords
    counter = Counter(keywords)
    return counter.most_common(max_keywords)


def get_trending_keywords(db, Telegram, hours=24, limit=10):
    """
    Get trending keywords from stories in the last N hours.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    
    try:
        recent_stories = Telegram.query.filter(
            Telegram.time >= cutoff
        ).all()
        
        all_keywords = Counter()
        for story in recent_stories:
            message = story.message or ''
            for keyword, count in extract_keywords(message, max_keywords=20):
                all_keywords[keyword] += count
        
        return all_keywords.most_common(limit)
    except Exception as e:
        logger.error("Error getting trending keywords: %s", e)
        return []


def store_keyword_trends(db, KeywordTrend, keywords_with_counts):
    """
    Store keyword counts in the keyword_trends table for time-series trending.
    """
    now = datetime.now(timezone.utc)
    # Round to the hour for bucketing
    bucket = now.replace(minute=0, second=0, microsecond=0)
    
    try:
        for keyword, count in keywords_with_counts:
            existing = KeywordTrend.query.filter_by(
                keyword=keyword, bucket_time=bucket
            ).first()
            
            if existing:
                existing.count += count
            else:
                trend = KeywordTrend(keyword=keyword, count=count, bucket_time=bucket)
                db.session.add(trend)
        
        db.session.commit()
    except Exception as e:
        logger.error("Error storing keyword trends: %s", e)
        db.session.rollback()


# --- P1-6: Global Tension Index ---

SEVERITY_WEIGHTS = {'HIGH': 3.0, 'MEDIUM': 1.5, 'LOW': 0.5}


def calculate_tension_index(db, Telegram, hours=24):
    """
    Calculate a global tension index (0-100) based on:
    - Story volume in the last N hours
    - Average severity weight
    - Percentage of areas escalating
    - Keyword intensity (high-severity keyword frequency)
    
    Returns dict with score and component values.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    previous_cutoff = cutoff - timedelta(hours=hours)
    
    try:
        # Current period stories
        recent_stories = Telegram.query.filter(Telegram.time >= cutoff).all()
        previous_count = Telegram.query.filter(
            and_(Telegram.time >= previous_cutoff, Telegram.time < cutoff)
        ).count()
        
        story_count = len(recent_stories)
        
        if story_count == 0:
            return {
                'score': 0.0,
                'story_count': 0,
                'avg_severity': 0.0,
                'escalation_pct': 0.0,
                'change_vs_previous': 0.0,
            }
        
        # Average severity weight
        severity_sum = sum(
            SEVERITY_WEIGHTS.get(s.severity or 'LOW', 0.5)
            for s in recent_stories
        )
        avg_severity = severity_sum / story_count
        
        # Escalation percentage
        escalations = calculate_all_escalations(db, Telegram, hours)
        escalating = sum(1 for v in escalations.values() if v == 'escalation')
        total_areas = max(len(escalations), 1)
        escalation_pct = escalating / total_areas
        
        # Volume component (normalized: 50 stories/day = baseline)
        volume_score = min(story_count / 50.0, 1.0) * 30  # max 30 points
        
        # Severity component (max 3.0 = all HIGH)
        severity_score = (avg_severity / 3.0) * 40  # max 40 points
        
        # Escalation component
        escalation_score = escalation_pct * 20  # max 20 points
        
        # Change component (growth vs previous period)
        if previous_count > 0:
            growth = (story_count - previous_count) / previous_count
            change_score = min(max(growth, 0), 1.0) * 10  # max 10 points
        else:
            change_score = 5.0 if story_count > 0 else 0.0
        
        total_score = round(min(volume_score + severity_score + escalation_score + change_score, 100.0), 1)
        
        # Change vs previous period
        if previous_count > 0:
            change_pct = round(((story_count - previous_count) / previous_count) * 100, 1)
        else:
            change_pct = 100.0 if story_count > 0 else 0.0
        
        return {
            'score': total_score,
            'story_count': story_count,
            'avg_severity': round(avg_severity, 2),
            'escalation_pct': round(escalation_pct * 100, 1),
            'change_vs_previous': change_pct,
        }
    except Exception as e:
        logger.error("Error calculating tension index: %s", e)
        return {
            'score': 0.0,
            'story_count': 0,
            'avg_severity': 0.0,
            'escalation_pct': 0.0,
            'change_vs_previous': 0.0,
        }


# ---------------------------------------------------------------------------
# Source-agnostic variants — query both Telegram and FileUpload
# ---------------------------------------------------------------------------

def _story_rows_in_window(db, from_dt, to_dt):
    """
    Return lightweight (city, severity) tuples from both sources within [from_dt, to_dt).
    Used by escalation and tension index calculations.
    """
    import config
    from app.models import Telegram, FileUpload

    telegram_rows = []
    if config.TELEGRAM_ENABLED:
        telegram_rows = db.session.query(
            Telegram.matched_city.label('city'),
            Telegram.severity.label('severity'),
        ).filter(
            Telegram.time >= from_dt,
            Telegram.time < to_dt,
        ).all()

    upload_rows = db.session.query(
        FileUpload.city.label('city'),
        FileUpload.severity.label('severity'),
    ).filter(
        FileUpload.upload_date >= from_dt,
        FileUpload.upload_date < to_dt,
        FileUpload.lat.isnot(None),   # only geolocated, matching existing Telegram behaviour
    ).all()

    return telegram_rows + upload_rows


def calculate_all_escalations_multi(db, hours=24):
    """
    Source-agnostic escalation calculation across Telegram and FileUpload.
    Returns dict: {city_name: 'escalation'|'de-escalation'|'stable'}
    """
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(hours=hours)
    previous_start = recent_start - timedelta(hours=hours)

    try:
        recent_rows = _story_rows_in_window(db, recent_start, now)
        previous_rows = _story_rows_in_window(db, previous_start, recent_start)

        recent_counts = Counter(r.city for r in recent_rows if r.city)
        previous_counts = Counter(r.city for r in previous_rows if r.city)

        all_cities = set(recent_counts) | set(previous_counts)
        results = {}

        for city in all_cities:
            recent = recent_counts.get(city, 0)
            previous = previous_counts.get(city, 0)

            if previous == 0 and recent > 0:
                results[city] = 'escalation'
            elif previous == 0:
                results[city] = 'stable'
            else:
                ratio = recent / previous
                if ratio >= 1.5:
                    results[city] = 'escalation'
                elif ratio <= 0.5:
                    results[city] = 'de-escalation'
                else:
                    results[city] = 'stable'

        return results
    except Exception as e:
        logger.error("Multi-source escalation error: %s", e)
        return {}


def get_trending_keywords_multi(db, hours=24, limit=10):
    """
    Source-agnostic keyword trending from Telegram messages and
    FileUpload title/subject/transcription fields.
    """
    import config
    from app.models import Telegram, FileUpload

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    try:
        telegram_texts = []
        if config.TELEGRAM_ENABLED:
            telegram_texts = [
                r[0] for r in
                db.session.query(Telegram.message).filter(Telegram.time >= cutoff).all()
                if r[0]
            ]
        upload_texts = []
        for row in db.session.query(
            FileUpload.title, FileUpload.subject, FileUpload.transcription
        ).filter(FileUpload.upload_date >= cutoff).all():
            upload_texts.append(' '.join(p for p in row if p))

        all_keywords: Counter = Counter()
        for text in telegram_texts + upload_texts:
            for keyword, count in extract_keywords(text, max_keywords=20):
                all_keywords[keyword] += count

        return all_keywords.most_common(limit)
    except Exception as e:
        logger.error("Multi-source keyword trending error: %s", e)
        return []


def calculate_tension_index_multi(db, hours=24):
    """
    Source-agnostic global tension index across Telegram and FileUpload.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    previous_cutoff = cutoff - timedelta(hours=hours)

    try:
        recent_rows = _story_rows_in_window(db, cutoff, now)
        previous_count = len(_story_rows_in_window(db, previous_cutoff, cutoff))
        story_count = len(recent_rows)

        if story_count == 0:
            return {
                'score': 0.0,
                'story_count': 0,
                'avg_severity': 0.0,
                'escalation_pct': 0.0,
                'change_vs_previous': 0.0,
            }

        severity_sum = sum(
            SEVERITY_WEIGHTS.get(r.severity or 'LOW', 0.5) for r in recent_rows
        )
        avg_severity = severity_sum / story_count

        escalations = calculate_all_escalations_multi(db, hours)
        escalating = sum(1 for v in escalations.values() if v == 'escalation')
        escalation_pct = escalating / max(len(escalations), 1)

        volume_score = min(story_count / 50.0, 1.0) * 30
        severity_score = (avg_severity / 3.0) * 40
        escalation_score = escalation_pct * 20

        if previous_count > 0:
            growth = (story_count - previous_count) / previous_count
            change_score = min(max(growth, 0), 1.0) * 10
            change_pct = round(((story_count - previous_count) / previous_count) * 100, 1)
        else:
            change_score = 5.0 if story_count > 0 else 0.0
            change_pct = 100.0 if story_count > 0 else 0.0

        total_score = round(
            min(volume_score + severity_score + escalation_score + change_score, 100.0), 1
        )

        return {
            'score': total_score,
            'story_count': story_count,
            'avg_severity': round(avg_severity, 2),
            'escalation_pct': round(escalation_pct * 100, 1),
            'change_vs_previous': change_pct,
        }
    except Exception as e:
        logger.error("Multi-source tension index error: %s", e)
        return {
            'score': 0.0,
            'story_count': 0,
            'avg_severity': 0.0,
            'escalation_pct': 0.0,
            'change_vs_previous': 0.0,
        }
