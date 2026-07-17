#!/usr/bin/env python
"""
Seed a small Rafah demo so you can exercise the moderation queue from the website.

It creates a handful of rung-1 citizen reports in Rafah that land PENDING (rung
0-1 is pre-moderation mandatory), clustered into Events through the real
submission pipeline — so they show up in /api/moderation/queue for a moderator
to verify or reject. It also gives you a way to LOG IN as a moderator.

Run from the repo root, in the same environment your backend uses (so
DATABASE_URL points at the same database the website reads):

    python scripts/seed_rafah_demo.py                      # create demo + a moderator login
    python scripts/seed_rafah_demo.py --promote you@x.com  # ...but make an EXISTING account the moderator
    python scripts/seed_rafah_demo.py --reset              # remove the demo data

All demo identities use the `rafah-demo:` display_handle prefix, so --reset only
removes demo rows (it never touches a --promote'd real account).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone  # noqa: E402

from werkzeug.security import generate_password_hash  # noqa: E402

HANDLE_PREFIX = 'rafah-demo:'
CITY = 'Rafah'
COUNTRY = 'Palestine'

# Approx. Rafah (southern Gaza Strip). Same-incident reports sit within ~60 m so
# they cluster; separate incidents are >1.5 km apart so they form their own Events.
_BASE = (31.2890, 34.2500)

# Default moderator login (used unless --promote points at an existing account).
MOD_EMAIL = 'moderator@rafah.test'
MOD_PASSWORD = 'Rafah2026!'


def _off(dlat, dlon):
    return (round(_BASE[0] + dlat, 6), round(_BASE[1] + dlon, 6))


# Each is a rung-1 citizen report -> all land PENDING. Three incidents:
# MARKET (3 reports, corroborating), SHELTER (2 reports), DRONE (1 lone witness).
REPORTS = [
    dict(handle='reporter-1', incident='MARKET', pos=_off(0, 0), severity='MEDIUM',
         title='Explosion near al-Awda market', is_sensitive=False,
         text='Loud explosion near the al-Awda market in Rafah; thick smoke rising over the rooftops.'),
    dict(handle='reporter-2', incident='MARKET', pos=_off(0.0005, 0.0004), severity='MEDIUM',
         title='Blast in the Rafah market area', is_sensitive=False,
         text='Blast in the market area; people running west away from the square.'),
    dict(handle='reporter-3', incident='MARKET', pos=_off(0.0006, 0.0005), severity='HIGH',
         title='Strike near the central market — casualties', is_sensitive=True,
         text='Strike near the central market; ambulances arriving and injured being carried out.'),
    dict(handle='reporter-4', incident='SHELTER', pos=_off(0.018, 0.0), severity='MEDIUM',
         title='Crowding at an eastern Rafah school shelter', is_sensitive=False,
         text='Panic and crowding at a school-turned-shelter in eastern Rafah after nearby shelling.'),
    dict(handle='reporter-5', incident='SHELTER', pos=_off(0.0184, 0.0003), severity='MEDIUM',
         title='School shelter overwhelmed', is_sensitive=False,
         text='The school shelter is overwhelmed; families arriving on foot with belongings.'),
    dict(handle='reporter-6', incident='DRONE', pos=_off(0.035, 0.010), severity='LOW',
         title='Drone heard over Tel al-Sultan overnight', is_sensitive=False,
         text='Single witness: a drone circling over the Tel al-Sultan area through the night.'),
]


def _demo_users(User):
    return User.query.filter(User.display_handle.like(f'{HANDLE_PREFIX}%')).all()


def _get_or_create_filetype(db, FileType):
    ft = FileType.query.filter_by(type_name='Other').first()
    if ft is None:
        ft = FileType(type_name='Other', allowed_extensions='*')
        db.session.add(ft)
        db.session.flush()
    return ft


def reset(db, User, FileUpload, Event):
    """Delete demo identities, their reports, and the events those reports made.
    Scoped strictly to the `rafah-demo:` handle prefix."""
    users = _demo_users(User)
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
    return {'identities': len(users), 'reports': len(uploads), 'events': len(event_ids)}


def provision(db, models, promote_email=None):
    User, FileUpload, FileType, Event = (
        models['User'], models['FileUpload'], models['FileType'], models['Event'],
    )
    from app.events.service import process_new_report

    removed = reset(db, User, FileUpload, Event)

    # ── The moderator login ────────────────────────────────────────────
    if promote_email:
        mod = User.query.filter_by(email=promote_email).first()
        if not mod:
            raise SystemExit(
                f"No account found with email {promote_email!r}. Register it on the "
                f"website first, then re-run with --promote {promote_email}."
            )
        mod.role = 'moderator'
        login_hint = f"your existing account {promote_email} (use your own password)"
    else:
        mod = User.query.filter_by(email=MOD_EMAIL).first()
        if not mod:
            mod = User(username='rafahmod', email=MOD_EMAIL,
                       display_handle=f'{HANDLE_PREFIX}moderator', identity_type='registered')
            db.session.add(mod)
        mod.password = generate_password_hash(MOD_PASSWORD)
        mod.role = 'moderator'
        mod.trust_rung = 3
        login_hint = f"{MOD_EMAIL} / {MOD_PASSWORD}"
    db.session.flush()

    # ── The rung-1 reporters (distinct identities so corroboration is real) ──
    reporters = {}
    for spec in REPORTS:
        h = spec['handle']
        if h not in reporters:
            u = User(display_handle=f'{HANDLE_PREFIX}{h}', identity_type='registered',
                     role='reporter', trust_rung=1)
            db.session.add(u)
            reporters[h] = u
    db.session.flush()

    # ── The reports — each runs through the real cluster -> gate -> recompute ──
    ft = _get_or_create_filetype(db, FileType)
    now = datetime.now(timezone.utc)
    made = []
    for spec in REPORTS:
        up = FileUpload(
            filename=f"rafah-demo-{spec['handle']}.txt",
            file_path='ingest:no-media',          # text-only
            title=spec['title'][:100],
            witness_statement=spec['text'],
            city=CITY, country=COUNTRY,
            lat=spec['pos'][0], lon=spec['pos'][1],
            severity=spec['severity'],
            is_sensitive=spec['is_sensitive'],
            source_type='eyewitness',
            user_id=reporters[spec['handle']].userid,
            file_type_id=ft.filetypeid,
            upload_date=now,
            analysis_status='SKIPPED',
        )
        db.session.add(up)
        db.session.flush()
        process_new_report(up)                     # cluster -> apply_rung_gate (PENDING) -> recompute
        made.append((spec, up))
    db.session.commit()

    pending = sum(1 for _, up in made if up.verification_status == 'PENDING')
    events = {up.event_id for _, up in made if up.event_id}
    return {
        'removed_prior': removed,
        'reporters': len(reporters),
        'reports': len(made),
        'pending': pending,
        'events': len(events),
        'login_hint': login_hint,
    }


def main():
    p = argparse.ArgumentParser(description='Seed a Rafah moderation-queue demo.')
    p.add_argument('--reset', action='store_true', help='remove the demo data and exit')
    p.add_argument('--promote', metavar='EMAIL',
                   help='make an existing (already-registered) account the moderator instead of creating one')
    args = p.parse_args()

    from app import create_app
    from app.models import db, User, FileUpload, FileType, Event

    app = create_app()
    with app.app_context():
        if args.reset:
            print('reset:', reset(db, User, FileUpload, Event))
            return
        models = {'User': User, 'FileUpload': FileUpload, 'FileType': FileType, 'Event': Event}
        result = provision(db, models, promote_email=args.promote)

    print('\n  Rafah demo seeded.')
    print(f"   reporters: {result['reporters']}  reports: {result['reports']} "
          f"(PENDING: {result['pending']})  events: {result['events']}")
    print(f"   (cleared prior demo: {result['removed_prior']})")
    print('\n  Log in as moderator with:')
    print(f"   {result['login_hint']}")
    print('\n  Then on the website: open the Account menu (top-right) -> Moderation')
    print('   to see the PENDING Rafah reports and Verify / Reject them.\n')


if __name__ == '__main__':
    main()
