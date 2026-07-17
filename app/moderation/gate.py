"""
app/moderation/gate.py

Rung-based moderation routing (Stage F).

GATE (publication): rung 0-1 reports are pre-moderation mandatory (PENDING,
hidden until a moderator approves); rung 2-3 reports post-moderate (auto-publish
VERIFIED, audited later). This is what lets a vouched cohort flow without a
moderator touching every report.

SAFETY OVERRIDE: HIGH severity, sensitive content, or the first media on a
brand-new event forces pre-moderation regardless of rung -- the irreversible
cases get human eyes first.

ORDER (attention, not publication): the PENDING queue is sorted by a priority
score, not FIFO, so dangerous / breaking / about-to-corroborate reports surface
first and nothing starves.
"""

import logging
from datetime import datetime, timezone

import config
from app.models import db, User

logger = logging.getLogger(__name__)

_NO_MEDIA = {'', 'ingest:no-media', 'anonymous:no-media'}
_SEVERITY_PRIORITY = {'HIGH': 100, 'MEDIUM': 40, 'LOW': 10}


def _utcnow():
    return datetime.now(timezone.utc)


def _has_media(upload):
    return (upload.file_path or '') not in _NO_MEDIA


def reporter_rung(upload):
    """Trust rung behind a report: 0 for anonymous, else the user's rung."""
    if upload.user_id is None:
        return 0
    user = getattr(upload, 'user', None) or db.session.get(User, upload.user_id)
    return getattr(user, 'trust_rung', 1) if user else 1


def _is_first_media_on_new_event(upload):
    """First media on a brand-new (singleton) event -- the riskiest moment for
    an unvetted graphic or location-revealing image to go straight public."""
    if not _has_media(upload):
        return False
    ev = getattr(upload, 'event', None)
    if ev is None:
        return False
    return len(list(getattr(ev, 'members', []) or [])) <= 1


def safety_override(upload):
    """True when this report must be pre-moderated regardless of rung."""
    if (upload.severity or 'LOW').upper() == 'HIGH':
        return True
    if getattr(upload, 'is_sensitive', False):
        return True
    if _is_first_media_on_new_event(upload):
        return True
    return False


def apply_rung_gate(upload):
    """Set the initial verification_status for a freshly-created report from the
    reporter's rung + the safety override. Call after the upload is flushed and
    its event is assigned (the media/event checks need that). Returns status."""
    rung = reporter_rung(upload)
    if rung >= 2 and not safety_override(upload):
        upload.verification_status = 'VERIFIED'
        upload.verified_at = _utcnow()
        upload.verified_by = None  # system auto-publish: audited, not approved
        upload.verification_note = None
    else:
        upload.verification_status = 'PENDING'
    return upload.verification_status


def compute_priority(upload):
    """Attention score for the PENDING queue (higher = reviewed sooner). Not
    FIFO: severity + sensitivity + media + low-rung + would-tip-to-CORROBORATED,
    with an anti-starvation aging nudge."""
    score = float(_SEVERITY_PRIORITY.get((upload.severity or 'LOW').upper(), 10))
    if getattr(upload, 'is_sensitive', False):
        score += 50
    if _has_media(upload):
        score += 20
    if reporter_rung(upload) <= 1:
        score += 30
    # Approving this report could push its event over the distinct-identity
    # threshold -- corroboration is the high-value outcome, so surface it.
    ev = getattr(upload, 'event', None)
    if ev is not None:
        threshold = getattr(config, 'EVENT_CORROBORATION_THRESHOLD', 2)
        if (ev.corroboration_count or 0) >= threshold - 1:
            score += 40
    # Anti-starvation: older items drift up (capped so age can't dominate).
    if upload.upload_date is not None:
        when = upload.upload_date
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        age_min = max(0.0, (_utcnow() - when).total_seconds() / 60.0)
        score += min(age_min * 0.5, 120)
    return score
