# modules/sources/reddit_adapter.py
"""
Reddit source adapter.
Primary: Reddit public JSON API (richer data — scores, timestamps).
Fallback: Reddit RSS via feedparser (when JSON is blocked / rate-limited).
Includes retry logic and rate-limiting to stay within Reddit's limits.
"""

import re
import logging
import time
import requests
import feedparser
from datetime import datetime, timezone

from .base_adapter import BaseSourceAdapter
from .settler_violence_sources import (
    SETTLER_VIOLENCE_SUBREDDITS,
    SETTLER_VIOLENCE_REDDIT_SEARCH_TERMS,
)

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = SETTLER_VIOLENCE_SUBREDDITS
DEFAULT_SEARCH_TERMS = SETTLER_VIOLENCE_REDDIT_SEARCH_TERMS

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')

USER_AGENT = 'Melo-News/2.0 (Reddit Adapter; educational project)'

# Reddit asks for ≥1 s between requests on unauthenticated endpoints
RATE_LIMIT_DELAY = 1.5  # seconds between API calls


def _strip_html(text):
    if not text:
        return ''
    text = _HTML_TAG_RE.sub(' ', text)
    text = _WHITESPACE_RE.sub(' ', text).strip()
    return text


class RedditAdapter(BaseSourceAdapter):
    """Fetches stories from Reddit subreddits (JSON primary, RSS fallback)."""

    source_name = 'reddit'
    MAX_RETRIES = 2
    RETRY_DELAY = 3

    def __init__(self, subreddits=None, search_terms=None, **kwargs):
        super().__init__(**kwargs)
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self.search_terms = search_terms or DEFAULT_SEARCH_TERMS
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': USER_AGENT})
        self._seen_ids = set()  # dedup across search terms

    # ── JSON API (primary) ────────────────────────────────────────────

    def _fetch_json(self, subreddit, search_term):
        """
        Fetch posts via Reddit JSON API with retries.
        Returns list of raw post dicts, or None on failure.
        """
        url = f'https://www.reddit.com/r/{subreddit}/search.json'
        params = {
            'q': search_term,
            'sort': 'new',
            'limit': 25,
            'restrict_sr': 'true',
            't': 'week',
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = self._session.get(url, params=params, timeout=15)

                if resp.status_code == 429:
                    wait = int(resp.headers.get('Retry-After', 10))
                    logger.warning(
                        "[Reddit] Rate-limited on r/%s, waiting %ds",
                        subreddit, wait,
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                children = data.get('data', {}).get('children', [])
                return [c.get('data', {}) for c in children]

            except requests.RequestException as e:
                logger.warning(
                    "[Reddit] JSON r/%s attempt %d/%d: %s",
                    subreddit, attempt, self.MAX_RETRIES, e,
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)

        return None  # all attempts failed

    # ── RSS fallback ──────────────────────────────────────────────────

    def _fetch_rss(self, subreddit, search_term):
        """
        Fetch posts via Reddit RSS (Atom) feed using feedparser.
        Used as fallback when the JSON API is unreachable.
        """
        url = (
            f'https://www.reddit.com/r/{subreddit}'
            f'/search.rss?q={requests.utils.quote(search_term)}'
            f'&sort=new&restrict_sr=true&t=week'
        )
        try:
            # Fetch with requests (more reliable headers), parse content
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                return []
            parsed = feedparser.parse(resp.content)
            return parsed.entries
        except Exception as e:
            logger.warning("[Reddit] RSS fallback r/%s failed: %s", subreddit, e)
            return []

    # ── Post normalizers ──────────────────────────────────────────────

    def _json_post_to_story(self, post, subreddit):
        """Convert a Reddit JSON post dict to a story dict."""
        post_id = post.get('id', '')
        if post_id in self._seen_ids:
            return None
        self._seen_ids.add(post_id)

        title = post.get('title', '')
        selftext = post.get('selftext', '')
        message = f"{title}\n\n{selftext}" if selftext else title
        if not message.strip():
            return None

        # Time
        created_utc = post.get('created_utc')
        parsed_time = (
            datetime.fromtimestamp(created_utc, tz=timezone.utc)
            if created_utc else None
        )

        # Location filter
        matched_city, city_result = None, None
        if self.filter_fn:
            matched_city, city_result = self.filter_fn(message)
            if not matched_city:
                return None

        # Images
        image_links = ''
        images = []
        post_url = post.get('url', '')
        if post_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            images.append(post_url)
        # Reddit image previews
        preview = post.get('preview', {})
        for img in preview.get('images', []):
            src = img.get('source', {}).get('url', '')
            if src:
                images.append(src.replace('&amp;', '&'))
        if post.get('thumbnail', '').startswith('http'):
            images.append(post['thumbnail'])
        if images:
            image_links = '|'.join(dict.fromkeys(images))[:3]  # dedup, max 3

        return {
            'message': message,
            'time': parsed_time,
            'matched_city': matched_city,
            'city_result': city_result,
            'total_views': post.get('score', 0),
            'image_links': image_links,
            'subject': title[:255],
            'tags': f'reddit, r/{subreddit}',
            'source_url': f"https://www.reddit.com{post.get('permalink', '')}",
        }

    def _rss_entry_to_story(self, entry, subreddit):
        """Convert a feedparser entry (Reddit Atom) to a story dict."""
        link = getattr(entry, 'link', '') or ''
        # Dedup by link
        if link in self._seen_ids:
            return None
        self._seen_ids.add(link)

        title = _strip_html(getattr(entry, 'title', '') or '')
        content = ''
        if hasattr(entry, 'content') and entry.content:
            content = _strip_html(entry.content[0].get('value', ''))
        elif hasattr(entry, 'summary'):
            content = _strip_html(entry.summary)

        message = f"{title}\n\n{content}" if content else title
        if not message.strip():
            return None

        # Time
        parsed_time = None
        for attr in ('published_parsed', 'updated_parsed'):
            st = getattr(entry, attr, None)
            if st:
                try:
                    parsed_time = datetime(*st[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
                break

        # Location filter
        matched_city, city_result = None, None
        if self.filter_fn:
            matched_city, city_result = self.filter_fn(message)
            if not matched_city:
                return None

        return {
            'message': message,
            'time': parsed_time,
            'matched_city': matched_city,
            'city_result': city_result,
            'total_views': 0,
            'image_links': '',
            'subject': title[:255],
            'tags': f'reddit, r/{subreddit}',
            'source_url': link,
        }

    # ── Main entry point ──────────────────────────────────────────────

    def fetch_stories(self):
        """Fetch stories from all configured subreddits × search terms."""
        total = 0

        for subreddit in self.subreddits:
            for term in self.search_terms:
                logger.info("[Reddit] Fetching r/%s search: %s", subreddit, term)
                count = 0

                # Try JSON API first
                posts = self._fetch_json(subreddit, term)

                if posts is not None:
                    for post in posts:
                        story = self._json_post_to_story(post, subreddit)
                        if story:
                            count += 1
                            yield story
                else:
                    # Fallback to RSS
                    logger.info(
                        "[Reddit] JSON failed for r/%s, falling back to RSS",
                        subreddit,
                    )
                    entries = self._fetch_rss(subreddit, term)
                    for entry in entries:
                        story = self._rss_entry_to_story(entry, subreddit)
                        if story:
                            count += 1
                            yield story

                total += count
                logger.info(
                    "[Reddit] r/%s '%s' — %d stories passed filter",
                    subreddit, term, count,
                )

                # Rate-limit between requests
                time.sleep(RATE_LIMIT_DELAY)

        logger.info("[Reddit] Total stories from all subreddits: %d", total)
