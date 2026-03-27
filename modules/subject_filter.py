# modules/subject_filter.py
"""
Two-stage settler violence relevance filter.

Stage 1 (fast):  Keyword matching — O(n) scan against curated terms.
Stage 2 (AI):    Thaura AI classification — only called when Stage 1
                 finds no keywords but the text *might* still be relevant.

Public API
----------
    classify_settler_violence(text) -> dict
        Returns {'is_relevant': bool,
                 'relevance_score': float,   # 0.0–1.0
                 'matched_keywords': list,
                 'method': str}              # 'keyword' | 'ai' | 'none'
"""

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

# ── Stage 1: Keyword Lists ───────────────────────────────────────────────

# High-confidence keywords — a single match is enough to classify as relevant.
SETTLER_VIOLENCE_KEYWORDS_HIGH = [
    # Direct settler violence terms
    'settler violence', 'settler attack', 'settler attacks',
    'settler assault', 'settler shooting', 'settler stabbing',
    'settler rampage', 'settler pogrom', 'settler lynch',
    'settler mob', 'settlers opened fire', 'settler car ramming',
    'settler arson', 'settler torched', 'homes torched by settlers',
    'village burned by settlers', 'shot by settlers',
    'settlers beat', 'settlers attacked', 'settlers raided',
    'settlers stormed', 'settlers vandalized',
    # Price-tag / hilltop youth
    'price tag attack', 'price tag', 'hilltop youth',
    # Olive tree / agricultural attacks
    'olive trees destroyed', 'olive trees uprooted',
    'olive trees burned', 'olive grove attack',
    'crop destruction by settlers', 'agricultural land seized by settlers',
    'livestock killed by settlers', 'shepherd attacked by settlers',
    # Property destruction
    'settler graffiti', 'mosque vandalized by settlers',
    'church vandalized by settlers', 'car vandalized by settlers',
    'property damage settlers',
    # Settlement expansion (often accompanies violence)
    'illegal outpost', 'settler outpost', 'outpost established',
    'settlement expansion', 'land confiscation',
]

# Medium-confidence keywords — need ≥2 matches or 1 match + contextual signal.
SETTLER_VIOLENCE_KEYWORDS_MEDIUM = [
    'settlers', 'settler', 'settlement',
    'west bank violence', 'west bank attack',
    'home demolition', 'demolition order',
    'water supply cut', 'road blocked settlers',
    'stone throwing settlers', 'intimidation settlers',
    'harassment settlers', 'settler escort',
    'army settler', 'idf settler', 'soldier settler',
    'protected by soldiers',
]

# Contextual terms — these alone aren't settler-violence-specific
# but strengthen a medium match.
_CONTEXT_SIGNALS = [
    'west bank', 'nablus', 'hebron', 'jenin', 'ramallah',
    'tulkarem', 'salfit', 'qalqilya', 'tubas', 'jericho',
    'bethlehem', 'palestinian', 'occupied',
]

# Pre-compile a combined regex for fast scanning
_HIGH_RE = re.compile(
    '|'.join(re.escape(kw) for kw in SETTLER_VIOLENCE_KEYWORDS_HIGH),
    re.IGNORECASE,
)
_MEDIUM_RE = re.compile(
    '|'.join(re.escape(kw) for kw in SETTLER_VIOLENCE_KEYWORDS_MEDIUM),
    re.IGNORECASE,
)
_CONTEXT_RE = re.compile(
    '|'.join(re.escape(kw) for kw in _CONTEXT_SIGNALS),
    re.IGNORECASE,
)


def _stage1_keyword(text: str) -> dict | None:
    """
    Fast keyword scan.  Returns a result dict if relevant, else None.
    """
    if not text:
        return None

    # High-confidence matches
    high_matches = _HIGH_RE.findall(text)
    if high_matches:
        unique = list(dict.fromkeys(m.lower() for m in high_matches))
        score = min(0.7 + 0.1 * len(unique), 1.0)
        return {
            'is_relevant': True,
            'relevance_score': round(score, 2),
            'matched_keywords': unique,
            'method': 'keyword',
        }

    # Medium-confidence matches
    medium_matches = _MEDIUM_RE.findall(text)
    if medium_matches:
        unique = list(dict.fromkeys(m.lower() for m in medium_matches))
        context_hits = len(_CONTEXT_RE.findall(text))

        if len(unique) >= 2 or (len(unique) >= 1 and context_hits >= 1):
            score = min(0.5 + 0.1 * len(unique) + 0.05 * context_hits, 0.9)
            return {
                'is_relevant': True,
                'relevance_score': round(score, 2),
                'matched_keywords': unique,
                'method': 'keyword',
            }

    return None  # No keyword match — fall through to Stage 2


# ── Stage 2: Thaura AI Classification ────────────────────────────────────

_THAURA_API_KEY = None  # Lazy-loaded
_THAURA_API_BASE = None
_THAURA_MODEL = None


def _load_thaura_config():
    global _THAURA_API_KEY, _THAURA_API_BASE, _THAURA_MODEL
    if _THAURA_API_KEY is None:
        _THAURA_API_KEY = os.getenv('THAURA_API_KEY', '')
        _THAURA_API_BASE = os.getenv('THAURA_API_BASE', 'https://backend.thaura.ai/v1')
        _THAURA_MODEL = os.getenv('THAURA_DEFAULT_MODEL', 'thaura')


_CLASSIFICATION_PROMPT = """Classify this news text.  Is it about **Israeli settler violence against Palestinians**?

Settler violence includes: physical attacks, arson, property destruction, olive tree uprooting, 
price-tag attacks, hilltop youth actions, settler mob violence, land seizure accompanied by force, 
harassment or intimidation by settlers, and similar incidents.

General war/military news, airstrikes, or political statements are NOT settler violence.

Text: {text}

Reply with ONLY one word: YES or NO"""


def _stage2_ai(text: str) -> dict | None:
    """
    Thaura AI classification fallback.
    Returns a result dict, or None if the AI is unavailable.
    """
    _load_thaura_config()
    if not _THAURA_API_KEY:
        return None

    try:
        headers = {
            'Authorization': f'Bearer {_THAURA_API_KEY}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': _THAURA_MODEL,
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are a news classifier. Reply with ONLY '
                        '"YES" or "NO". No explanation.'
                    ),
                },
                {
                    'role': 'user',
                    'content': _CLASSIFICATION_PROMPT.format(text=text[:500]),
                },
            ],
            'temperature': 0.0,
            'max_tokens': 5,
        }

        resp = requests.post(
            f'{_THAURA_API_BASE}/chat/completions',
            json=payload,
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            answer = (
                data.get('choices', [{}])[0]
                .get('message', {})
                .get('content', '')
                .strip()
                .upper()
            )
            is_yes = answer.startswith('YES')
            return {
                'is_relevant': is_yes,
                'relevance_score': 0.65 if is_yes else 0.15,
                'matched_keywords': [],
                'method': 'ai',
            }

    except requests.exceptions.Timeout:
        logger.warning('[subject_filter] Thaura AI timed out')
    except Exception as e:
        logger.error('[subject_filter] Thaura AI error: %s', e)

    return None


# ── Public API ────────────────────────────────────────────────────────────

def classify_settler_violence(text: str) -> dict:
    """
    Classify whether *text* is about Israeli settler violence.

    Returns
    -------
    dict with keys:
        is_relevant      : bool
        relevance_score  : float  (0.0–1.0)
        matched_keywords : list[str]
        method           : str    ('keyword' | 'ai' | 'none')
    """
    if not text or len(text.strip()) < 10:
        return {
            'is_relevant': False,
            'relevance_score': 0.0,
            'matched_keywords': [],
            'method': 'none',
        }

    # Stage 1: keyword matching (fast, no network)
    result = _stage1_keyword(text)
    if result is not None:
        logger.info(
            '[subject_filter] Stage 1 HIT — score=%.2f keywords=%s',
            result['relevance_score'],
            result['matched_keywords'][:3],
        )
        return result

    # Stage 2: AI classification (slower, network call)
    result = _stage2_ai(text)
    if result is not None:
        logger.info(
            '[subject_filter] Stage 2 AI — relevant=%s score=%.2f',
            result['is_relevant'],
            result['relevance_score'],
        )
        return result

    # Neither stage produced a result (AI unavailable, no keywords)
    return {
        'is_relevant': False,
        'relevance_score': 0.0,
        'matched_keywords': [],
        'method': 'none',
    }
