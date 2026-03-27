# modules/sources/rss_adapter.py
"""
RSS feed source adapter.
Uses feedparser for robust RSS 2.0 / Atom parsing.
Ingests news from configured RSS feeds and normalizes them into
story dicts for the Kafka pipeline.
"""

import re
import logging
import time
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .base_adapter import BaseSourceAdapter
from .settler_violence_sources import SETTLER_VIOLENCE_RSS_FEEDS

logger = logging.getLogger(__name__)

# ── Defaults: settler-violence-focused feeds from central config ──────
DEFAULT_RSS_FEEDS = SETTLER_VIOLENCE_RSS_FEEDS

# HTML tag stripper
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')


def _strip_html(text):
    """Remove HTML tags and collapse whitespace."""
    if not text:
        return ''
    text = _HTML_TAG_RE.sub(' ', text)
    text = _WHITESPACE_RE.sub(' ', text).strip()
    return text


class RSSAdapter(BaseSourceAdapter):
    """Fetches stories from RSS/Atom feeds using feedparser."""

    source_name = 'rss'

    # Retry settings
    MAX_RETRIES = 2
    RETRY_DELAY = 3          # seconds between retries

    def __init__(self, feeds=None, **kwargs):
        super().__init__(**kwargs)
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    # ── Parse a single feed ───────────────────────────────────────────

    def _parse_feed(self, url, feed_name):
        """
        Download and parse one RSS/Atom feed.
        Retries on transient failures.  Yields story dicts.
        """
        parsed = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                parsed = feedparser.parse(
                    url,
                    request_headers={
                        'User-Agent': 'Melo-News/2.0 (RSS Adapter; feedparser)',
                    },
                )
                # feedparser doesn't raise on HTTP errors — check bozo flag
                if parsed.bozo and not parsed.entries:
                    exc = getattr(parsed, 'bozo_exception', None)
                    logger.warning(
                        "[RSS] %s attempt %d/%d bozo: %s",
                        feed_name, attempt, self.MAX_RETRIES, exc,
                    )
                    if attempt < self.MAX_RETRIES:
                        time.sleep(self.RETRY_DELAY)
                        continue
                break  # success (or last attempt)
            except Exception as e:
                logger.warning(
                    "[RSS] %s attempt %d/%d exception: %s",
                    feed_name, attempt, self.MAX_RETRIES, e,
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)

        if not parsed or not parsed.entries:
            logger.error("[RSS] %s — no entries returned after %d attempts", feed_name, self.MAX_RETRIES)
            return

        logger.info("[RSS] %s — %d entries fetched", feed_name, len(parsed.entries))

        for entry in parsed.entries:
            story = self._entry_to_story(entry, feed_name)
            if story:
                yield story

    # ── Convert a feedparser entry → story dict ───────────────────────

    def _entry_to_story(self, entry, feed_name):
        """Normalize a feedparser entry into a Melo-News story dict."""
        title = _strip_html(getattr(entry, 'title', '') or '')
        # 'summary' in RSS 2.0 / 'content' in Atom
        description = ''
        if hasattr(entry, 'summary'):
            description = _strip_html(entry.summary)
        elif hasattr(entry, 'content') and entry.content:
            description = _strip_html(entry.content[0].get('value', ''))

        message = f"{title}\n\n{description}" if description else title
        if not message.strip():
            return None

        # ── Time ──────────────────────────────────────────────────────
        parsed_time = None
        # feedparser provides a struct_time in 'published_parsed' or 'updated_parsed'
        for attr in ('published_parsed', 'updated_parsed'):
            st = getattr(entry, attr, None)
            if st:
                try:
                    parsed_time = datetime(*st[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
                break
        # Fallback: raw string
        if not parsed_time:
            for attr in ('published', 'updated'):
                raw = getattr(entry, attr, None)
                if raw:
                    try:
                        parsed_time = parsedate_to_datetime(raw)
                    except Exception:
                        try:
                            parsed_time = datetime.fromisoformat(
                                raw.replace('Z', '+00:00')
                            )
                        except Exception:
                            pass
                    if parsed_time:
                        break

        # ── Location filter ───────────────────────────────────────────
        matched_city, city_result = None, None
        if self.filter_fn:
            matched_city, city_result = self.filter_fn(message)
            if not matched_city:
                return None  # filtered out

        # ── Media links ───────────────────────────────────────────────
        image_links = ''
        images = []
        for enc in getattr(entry, 'enclosures', []):
            href = enc.get('href', '')
            etype = enc.get('type', '')
            if 'image' in etype or href.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                images.append(href)
        for mc in getattr(entry, 'media_content', []):
            url = mc.get('url', '')
            if url:
                images.append(url)
        for mt in getattr(entry, 'media_thumbnail', []):
            url = mt.get('url', '')
            if url:
                images.append(url)
        if images:
            image_links = '|'.join(images[:3])

        link = getattr(entry, 'link', '') or ''

        return {
            'message': message,
            'time': parsed_time,
            'matched_city': matched_city,
            'city_result': city_result,
            'subject': title[:255] if title else None,
            'tags': f'rss, {feed_name}',
            'image_links': image_links,
            'source_url': link,
        }

    # ── Main entry point ──────────────────────────────────────────────

    def fetch_stories(self):
        """Fetch stories from all configured RSS feeds."""
        total = 0
        for feed in self.feeds:
            name = feed['name']
            url = feed['url']
            logger.info("[RSS] Fetching feed: %s", name)
            count = 0
            for story in self._parse_feed(url, name):
                count += 1
                total += 1
                yield story
            logger.info("[RSS] %s — %d stories passed location filter", name, count)

        logger.info("[RSS] Total stories from all feeds: %d", total)
