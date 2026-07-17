"""
app/drill/scenario.py

T4P drill scenario -- a fictional, sandboxed corroboration exercise that forces
every rule the trust model claims, so a synchronous live drill (or a dry-run
simulation) exercises the machinery end to end. See the pilot test plan.

THROWAWAY tooling: all data lives in a fictional locale (Testoria / Sandboxia)
and every identity's display_handle is prefixed `drill:`, so reset() can wipe it
without touching real data. Never point this at a database holding real reports.

Seven scripted elements, each mapped to an exit criterion:
  ALPHA    auto path        -- 2 rung-2 reporters -> auto-CORROBORATED, no mod
  BRAVO    moderator-gated  -- 3 rung-1 reporters -> mod-confirmed, then a
                               steward vouch promotes it to CORROBORATED
  SYBIL    on BRAVO         -- one human's 2 extra accounts; the mod rejects them
                               via dedup signals (status, not count)
  CHARLIE  DISPUTED         -- two contradicting reporters; moderator pins DISPUTED
  DELTA    lone unverified  -- a single witness -> verified-but-uncorroborated
  NEARMISS clustering edge  -- ~1.5 km from ALPHA, must NOT merge
  ECHO     reshare probe    -- 2 rung-2 reporters post BYTE-IDENTICAL media; the
                               engine collapses it to ONE independent source, so
                               a reshared clip cannot corroborate (ADR-0020/UC8)

provision()/simulate()/reset() take a live `db` and run inside an app context;
the CLI (scripts/seed_drill.py) supplies that via create_app(). role_cards() is
pure data for printing the live-drill briefs.
"""

import logging
from datetime import datetime, timezone

from app.models import db, User, FileUpload, FileType, Event
from app.events.service import process_new_report, recompute_event

logger = logging.getLogger(__name__)

HANDLE_PREFIX = 'drill:'
SANDBOX_CITY = 'Testoria'
SANDBOX_COUNTRY = 'Sandboxia'

# Distinct event centroids, ~15+ km apart so events never cross-cluster.
_ALPHA = (10.000, 20.000)
_BRAVO = (10.150, 20.150)
_CHARLIE = (10.300, 20.300)
_DELTA = (10.450, 20.450)
_ECHO = (10.600, 20.600)

# A single fictional clip's fingerprint. Both ECHO reporters post THIS exact
# hash -> the independence detector treats them as one origin (a reshare),
# not two independent witnesses.
_ECHO_SHA = 'e' * 64


def _off(base, dlat, dlon):
    return (round(base[0] + dlat, 6), round(base[1] + dlon, 6))


# Each report is a role card. `handle` (without the drill: prefix) identifies the
# tester/account; `sybil_of` marks an extra account driven by another handle's
# human. Offsets within an event are <100 m (cluster); NEARMISS is ~1.5 km off
# ALPHA (must not merge).
REPORTS = [
    # ALPHA -- auto path (two rung-2, text-only -> auto-publish -> CORROBORATED)
    dict(key='A1', handle='alpha-1', rung=2, event='ALPHA', pos=_off(_ALPHA, 0, 0),
         severity='MEDIUM', text='Loud explosion near the central market; smoke rising over the square.'),
    dict(key='A2', handle='alpha-2', rung=2, event='ALPHA', pos=_off(_ALPHA, 0.0005, 0.0005),
         severity='MEDIUM', text='Blast at the market; people running east down the main street.'),
    # BRAVO -- moderator-gated (three fresh rung-1)
    dict(key='B1', handle='bravo-1', rung=1, event='BRAVO', pos=_off(_BRAVO, 0, 0),
         severity='MEDIUM', text='Gunfire along the riverside road, near the old bridge.'),
    dict(key='B2', handle='bravo-2', rung=1, event='BRAVO', pos=_off(_BRAVO, 0.0004, 0.0003),
         severity='MEDIUM', text='Shots heard by the river bridge; residents going indoors.'),
    dict(key='B3', handle='bravo-3', rung=1, event='BRAVO', pos=_off(_BRAVO, 0.0006, 0.0006),
         severity='MEDIUM', text='Armed men by the river; sustained gunfire for several minutes.'),
    # SYBIL -- bravo-1's human spins up two extra fresh accounts on BRAVO
    dict(key='S1', handle='bravo-1-alt1', rung=1, event='BRAVO', pos=_off(_BRAVO, 0.0002, 0.0002),
         severity='MEDIUM', text='More gunfire by the river!!', sybil_of='bravo-1'),
    dict(key='S2', handle='bravo-1-alt2', rung=1, event='BRAVO', pos=_off(_BRAVO, 0.0003, 0.0001),
         severity='MEDIUM', text='Still shooting near the bridge!!', sybil_of='bravo-1'),
    # CHARLIE -- DISPUTED (two rung-1 contradict each other)
    dict(key='C1', handle='charlie-1', rung=1, event='CHARLIE', pos=_off(_CHARLIE, 0, 0),
         severity='HIGH', text='Clash at the checkpoint; several people injured.'),
    dict(key='C2', handle='charlie-2', rung=1, event='CHARLIE', pos=_off(_CHARLIE, 0.0004, 0.0004),
         severity='LOW', text='No clash here -- the checkpoint is calm; this looks like a rumor.'),
    # DELTA -- lone witness (singleton; verified-but-uncorroborated)
    dict(key='D1', handle='delta-1', rung=1, event='DELTA', pos=_off(_DELTA, 0, 0),
         severity='LOW', text='Single witness: a drone circling over the north field.'),
    # NEARMISS -- ~1.5 km from ALPHA; must start its own event, not merge
    dict(key='NM', handle='nearmiss-1', rung=1, event='NEARMISS', pos=_off(_ALPHA, 0.014, 0.0),
         severity='LOW', text='Unrelated: a minor traffic accident on the ring road.'),
    # ECHO -- reshare probe: two rung-2 reporters post the SAME clip (identical
    # media_sha256). Distinct keys (counted=2) but ONE independent origin
    # (independent=1), so it must NOT auto-corroborate.
    dict(key='E1', handle='echo-1', rung=2, event='ECHO', pos=_off(_ECHO, 0, 0),
         severity='MEDIUM', text='Footage of the burning warehouse by the port.', media_sha256=_ECHO_SHA),
    dict(key='E2', handle='echo-2', rung=2, event='ECHO', pos=_off(_ECHO, 0.0004, 0.0004),
         severity='MEDIUM', text='Same warehouse fire clip, forwarded on.', media_sha256=_ECHO_SHA),
]

STEWARD_HANDLE = 'steward'  # also the sole moderator for round one


# ── identity helpers ────────────────────────────────────────────────

def _identity_specs():
    """Unique (handle, rung) pairs across all role cards."""
    seen = {}
    for r in REPORTS:
        seen.setdefault(r['handle'], r['rung'])
    return seen


def _drill_users():
    return User.query.filter(User.display_handle.like(f'{HANDLE_PREFIX}%')).all()


def _get_or_create_filetype():
    ft = FileType.query.filter_by(type_name='Other').first()
    if ft is None:
        ft = FileType(type_name='Other', allowed_extensions='*')
        db.session.add(ft)
        db.session.flush()
    return ft


# ── lifecycle ───────────────────────────────────────────────────────

def reset(db):
    """Delete all drill data (identities, their reports, and the events those
    reports created). Scoped strictly to the `drill:` handle prefix."""
    users = _drill_users()
    uids = [u.userid for u in users]
    uploads = FileUpload.query.filter(FileUpload.user_id.in_(uids)).all() if uids else []
    event_ids = {u.event_id for u in uploads if u.event_id}
    for up in uploads:
        db.session.delete(up)
    db.session.flush()
    for eid in event_ids:
        ev = db.session.get(Event, eid)
        if ev is not None:
            db.session.delete(ev)
    for u in users:
        db.session.delete(u)
    db.session.commit()
    logger.info("drill reset: removed %d identities, %d reports, %d events",
                len(users), len(uploads), len(event_ids))
    return {'identities': len(users), 'reports': len(uploads), 'events': len(event_ids)}


def provision(db):
    """Create a clean drill cohort: a sole steward+moderator plus one identity
    per role card, with the assigned trust rungs. Idempotent (resets first)."""
    reset(db)
    steward = User(username='drill-steward', display_handle=f'{HANDLE_PREFIX}{STEWARD_HANDLE}',
                   identity_type='pseudonymous', role='steward', trust_rung=3)
    db.session.add(steward)
    users = {STEWARD_HANDLE: steward}
    for handle, rung in _identity_specs().items():
        u = User(display_handle=f'{HANDLE_PREFIX}{handle}', identity_type='pseudonymous',
                 role='reporter', trust_rung=rung)
        db.session.add(u)
        users[handle] = u
    db.session.flush()
    db.session.commit()
    logger.info("drill provisioned: steward + %d reporter identities", len(users) - 1)
    return users


# ── moderator / steward actions (the sole steward drives all of these) ──

def _verify(upload, steward):
    upload.verification_status = 'VERIFIED'
    upload.verified_at = datetime.now(timezone.utc)
    upload.verified_by = steward.userid
    db.session.flush()
    if upload.event_id:
        recompute_event(db.session.get(Event, upload.event_id))


def _reject(upload, steward, note):
    upload.verification_status = 'REJECTED'
    upload.verified_at = datetime.now(timezone.utc)
    upload.verified_by = steward.userid
    upload.verification_note = note
    db.session.flush()
    if upload.event_id:
        recompute_event(db.session.get(Event, upload.event_id))


def _vouch(user, rung):
    user.trust_rung = rung
    db.session.flush()
    event_ids = {fu.event_id for fu in FileUpload.query.filter_by(user_id=user.userid).all() if fu.event_id}
    for eid in event_ids:
        recompute_event(db.session.get(Event, eid))


def _dispute(event):
    event.status_override = 'DISPUTED'
    db.session.flush()
    recompute_event(event)


# ── simulation (dry-run / demo / self-test) ─────────────────────────

def simulate(db):
    """Provision the cohort and play the whole scripted scenario through the
    real submission + moderation pipeline, ending in the state the live drill is
    meant to reach. Returns a summary keyed by event. Useful as a dry run, a
    demo, and a self-test."""
    users = provision(db)
    steward = users[STEWARD_HANDLE]
    ft = _get_or_create_filetype()
    now = datetime.now(timezone.utc)

    uploads = {}
    for spec in REPORTS:
        u = users[spec['handle']]
        sha = spec.get('media_sha256')
        up = FileUpload(
            filename=f"drill-{spec['key']}." + ('jpg' if sha else 'txt'),
            # Media-bearing reports carry a sandbox path + the fingerprint the
            # independence detector keys on; text-only reports use the no-media
            # sentinel (also avoids the first-media safety gate).
            file_path=(f"drill-media/{spec['key']}.jpg" if sha else 'ingest:no-media'),
            media_sha256=sha,
            title=spec['text'][:100],
            witness_statement=spec['text'],
            city=SANDBOX_CITY, country=SANDBOX_COUNTRY,
            lat=spec['pos'][0], lon=spec['pos'][1],
            severity=spec['severity'],
            source_type='drill',
            user_id=u.userid,
            file_type_id=ft.filetypeid,
            upload_date=now,
        )
        db.session.add(up)
        db.session.flush()
        process_new_report(up)                     # cluster -> gate -> recompute
        uploads[spec['key']] = up

    # BRAVO: moderator approves the three genuine reporters; rejects the two
    # Sybil accounts on dedup signals (same human, near-identical text/location).
    for k in ('B1', 'B2', 'B3'):
        _verify(uploads[k], steward)
    for k in ('S1', 'S2'):
        _reject(uploads[k], steward, 'Duplicate of bravo-1: same author, near-identical text and pin.')
    # Steward vouches a DIFFERENT genuine reporter to rung 2 -> BRAVO promotes.
    _vouch(users['bravo-2'], 2)

    # CHARLIE: approve both contradicting reports, then moderator pins DISPUTED.
    for k in ('C1', 'C2'):
        _verify(uploads[k], steward)
    _dispute(db.session.get(Event, uploads['C1'].event_id))

    # DELTA: approve the lone witness -> verified-but-uncorroborated.
    _verify(uploads['D1'], steward)

    # ECHO: approve both reshare reports; the engine collapses the identical clip
    # to one independent origin, so the event stays DEVELOPING (not corroborated).
    for k in ('E1', 'E2'):
        _verify(uploads[k], steward)

    db.session.commit()

    def ev_of(key):
        return db.session.get(Event, uploads[key].event_id)

    alpha, bravo, charlie, delta, nm, echo = (ev_of('A1'), ev_of('B1'), ev_of('C1'),
                                              ev_of('D1'), ev_of('NM'), ev_of('E1'))
    summary = {
        'ALPHA':   {'status': alpha.status, 'counted': alpha.corroboration_count, 'note': 'auto-CORROBORATED (no moderator)'},
        'BRAVO':   {'status': bravo.status, 'counted': bravo.corroboration_count, 'note': 'mod-confirmed + steward vouch; 2 Sybil accounts rejected'},
        'CHARLIE': {'status': charlie.status, 'counted': charlie.corroboration_count, 'note': 'moderator-pinned DISPUTED (contradiction)'},
        'DELTA':   {'status': delta.status, 'counted': delta.corroboration_count, 'note': 'lone, verified-but-uncorroborated'},
        'NEARMISS': {'separate_from_alpha': nm.id != alpha.id, 'note': '~1.5 km off ALPHA -> own event'},
        'ECHO':    {'status': echo.status, 'counted': echo.corroboration_count,
                    'independent': echo.independent_source_count,
                    'note': 'same clip reshared under 2 accounts -> 1 independent source, NOT corroborated'},
    }
    return summary


# ── role cards (pure data for the live drill briefs) ────────────────

def role_cards():
    """One brief per report for the synchronous live drill: which account to use,
    its rung, the pin to enter, and the exact text to submit."""
    cards = []
    for r in REPORTS:
        cards.append({
            'key': r['key'],
            'account': f"{HANDLE_PREFIX}{r['handle']}",
            'rung': r['rung'],
            'event': r['event'],
            'lat': r['pos'][0],
            'lon': r['pos'][1],
            'city': SANDBOX_CITY,
            'severity': r['severity'],
            'text': r['text'],
            'sybil_of': r.get('sybil_of'),
            # Present -> this brief attaches media; ECHO's two briefs share the
            # SAME clip (identical fingerprint) to exercise the reshare probe.
            'media_sha256': r.get('media_sha256'),
        })
    return cards
