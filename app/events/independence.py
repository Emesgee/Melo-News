"""
app/events/independence.py

Advisory coordination signals over an Event's members (ADR-0020 Phase 1,
richer independence detection; strengthens the debunk shape, UC8).

IMPORTANT design boundary. Byte-identical media is an UNAMBIGUOUS reshare, so it
collapses the hard independent_source_count (events.service). Text similarity and
submission timing are NOT: independent people witnessing the same event naturally
submit around the same time and describe it similarly -- that is the signature of
genuine corroboration as much as of astroturf. So these signals are ADVISORY
ONLY. They never reduce the corroboration count; they are surfaced transparently
for a moderator/reader to weigh (ADR-0006 non-binary; UC8 "signals, never an
automated FAKE stamp"). Auto-collapsing on them would destroy real corroboration
(the scripted drill would trip every flag).

True perceptual (near-duplicate) MEDIA hashing WOULD be a strong, count-affecting
signal, but it cannot run here: the server never sees media bytes (ADR-0009). It
needs an on-device perceptual hash added to the signed envelope (ADR-0008/0014) --
deferred to a client-contract change, not half-built server-side.

Pure functions; deterministic output (sorted) so it is safe inside the hashed
corroboration graph.
"""

import re
from datetime import timezone
from itertools import combinations

import config


def _cfg(name, default):
    return getattr(config, name, default)


def _naive_utc(dt):
    """Coerce to naive UTC so tz-aware (fresh ORM / ingested) and tz-naive (read
    from a non-tz DB column) datetimes can be compared without raising."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _norm_text(s):
    """Lowercase, strip punctuation, collapse whitespace -- so trivial edits
    (case, spacing, punctuation) don't hide a copy-paste."""
    if not s:
        return ''
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s.lower())).strip()


def _shingles(text, k=3):
    """Set of k-word shingles; falls back to the bare token set for short text."""
    toks = text.split()
    if len(toks) < k:
        return set(toks)
    return {' '.join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _member_text(m):
    return _norm_text(getattr(m, 'witness_statement', None) or getattr(m, 'title', None) or '')


def analyze_independence(members):
    """Return a deterministic list of advisory coordination flags over VERIFIED,
    non-anonymous members. Empty list == no coordination detected. Each flag:
    {type, source_ids (sorted), detail}. Never mutates the corroboration count.

    - duplicate_text: two distinct identities whose reports share >= the Jaccard
      threshold of their wording (copy-paste / scripted campaign).
    - synchronized_submission: >= N distinct identities submitting inside a very
      tight window (more machine-like than organic arrival)."""
    named = [m for m in members if getattr(m, 'user_id', None) is not None]
    flags = []

    # --- text near-duplication (pairwise over distinct identities) ---
    threshold = _cfg('TEXT_DUP_JACCARD', 0.85)
    shingled = [(m, _shingles(_member_text(m))) for m in named]
    for (m1, s1), (m2, s2) in combinations(shingled, 2):
        if m1.user_id == m2.user_id or not s1 or not s2:
            continue
        sim = _jaccard(s1, s2)
        if sim >= threshold:
            flags.append({
                'type': 'duplicate_text',
                'source_ids': sorted([m1.id, m2.id]),
                'detail': f'reports share {round(sim * 100)}% of their wording',
            })

    # --- synchronized submission (tight-window burst across identities) ---
    window = _cfg('COORDINATION_WINDOW_SECONDS', 30)
    min_ids = _cfg('COORDINATION_MIN_SOURCES', 3)
    timed = sorted(
        ((m, _naive_utc(m.upload_date)) for m in named if m.upload_date is not None),
        key=lambda t: t[1],
    )
    for i, (anchor, t0) in enumerate(timed):
        burst = {anchor.user_id: anchor.id}
        for m, t in timed[i + 1:]:
            if (t - t0).total_seconds() > window:
                break
            burst.setdefault(m.user_id, m.id)
        if len(burst) >= min_ids:
            flags.append({
                'type': 'synchronized_submission',
                'source_ids': sorted(burst.values()),
                'detail': f'{len(burst)} reports within {window}s',
            })
            break  # one representative burst flag is enough

    flags.sort(key=lambda f: (f['type'], f['source_ids']))
    return flags
