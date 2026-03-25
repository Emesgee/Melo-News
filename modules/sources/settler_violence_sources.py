# modules/sources/settler_violence_sources.py
"""
Centralized source configuration for settler violence monitoring.

Telegram, RSS, Twitter, and Reddit sources
all focused on documenting Israeli settler violence against Palestinians.
"""

# ─── Search topics appended to Telegram channel URLs ──────────────────
SETTLER_VIOLENCE_TOPICS = [
    'settler',
    'settler violence',
    'settler attack',
    'settlers',
]

# ─── Telegram channels covering settler violence ─────────────────────
# All channels verified reachable with 1000+ subscribers as of 2026-03-24.
# Format: (channel_handle, description)

TELEGRAM_CHANNELS = [
    # ── Palestinian news agencies (verified, 1 000+ subs) ─────────────
    ('QudsN',            'Quds News Network — Arabic (731K subs)'),
    ('QudsNen',          'Quds News Network — English (122K subs)'),
    ('alresalahpress',   'Al Resalah Press — Palestinian media (30K subs)'),
    ('PalInfo',          'Palestinian Information Center (17K subs)'),
    ('EyesOnPal',        'Eyes on Palestine — ground-level reporting (13K subs)'),
    ('palestineonline',  'Palestine Online — news aggregator (1.6K subs)'),
    ('eye_on_palestine', 'Eye on Palestine — settler violence coverage (1.5K subs)'),

    # ── International news covering the region ────────────────────────
    ('AlMayadeen',       'Al Mayadeen News — Lebanon/Palestine (508K subs)'),
    ('PressTV',          'Press TV — Middle East coverage (86K subs)'),
    ('BBCArabic',        'BBC Arabic — Middle East desk (31K subs)'),
    ('TRTWorld',         'TRT World — international news (20K subs)'),
]


# ─── RSS feeds covering settler violence ─────────────────────────────
# All feeds verified reachable as of 2026-03-24.
SETTLER_VIOLENCE_RSS_FEEDS = [
    # Major international outlets — Middle East desks
    {'name': 'Al Jazeera Middle East',  'url': 'https://www.aljazeera.com/xml/rss/all.xml'},
    {'name': 'Middle East Eye',         'url': 'https://www.middleeasteye.net/rss'},
    {'name': 'BBC Middle East',         'url': 'https://feeds.bbci.co.uk/news/world/middle_east/rss.xml'},
    {'name': 'Guardian Middle East',    'url': 'https://www.theguardian.com/world/middleeast/rss'},
    {'name': 'Al Monitor',              'url': 'https://www.al-monitor.com/rss'},
    {'name': 'Times of Israel',         'url': 'https://www.timesofisrael.com/feed/'},

    # Independent journalism & analysis
    {'name': 'Mondoweiss',              'url': 'https://mondoweiss.net/feed/'},
    {'name': 'Electronic Intifada',     'url': 'https://electronicintifada.net/rss.xml'},

    # UN / humanitarian
    {'name': 'UN News Middle East',     'url': 'https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml'},
    {'name': 'ReliefWeb Settler Violence', 'url': 'https://reliefweb.int/updates/rss.xml?search=settler%20violence'},
]


# ─── Reddit config for settler violence ──────────────────────────────
SETTLER_VIOLENCE_SUBREDDITS = [
    'Palestine',
    'IsraelPalestine',
    'worldnews',
    'internationalnews',
    'HumanRights',
]

SETTLER_VIOLENCE_REDDIT_SEARCH_TERMS = [
    'settler violence',
    'settler attack',
    'settlers West Bank',
    'settler arson',
    'price tag attack',
    'olive trees destroyed',
    'settler pogrom',
]
