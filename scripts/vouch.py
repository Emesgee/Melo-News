#!/usr/bin/env python
"""
Steward operations from the server: list identities, set trust rungs, set roles.

This is the out-of-band equivalent of the steward endpoints in
app/moderation/routes.py, for use before the steward UI exists (or when no
steward account is reachable). It deliberately calls the SAME
``_vouch_user_to_rung`` helper the API uses, so a rung set here behaves
identically to one set through the UI -- in particular it re-derives the user's
Events, because a bump to rung 2+ can immediately let an existing Event reach
CORROBORATED (ADR-0005 gate: an Event needs an established member).

Run inside the API container, e.g.:

    docker compose -f docker-compose.prod.yml exec -T melo-api \
        python scripts/vouch.py --list

    # ADR-0016 bootstrap: vouch a device pseudonym read off the tester's phone
    docker compose -f docker-compose.prod.yml exec -T melo-api \
        python scripts/vouch.py --handle k-0d241c76ea --rung 2

    docker compose -f docker-compose.prod.yml exec -T melo-api \
        python scripts/vouch.py --user-id 17 --role moderator

Rungs are 1..3 (0 means anonymous and has no User row). Roles are
reporter | moderator | steward.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VALID_ROLES = ('reporter', 'moderator', 'steward')


def _fmt(u):
    handle = u.display_handle or '-'
    username = u.username or '-'
    return (f"  #{u.userid:<4} rung={u.trust_rung}  role={u.role:<9} "
            f"handle={handle:<28} user={username:<14} "
            f"reports={u.reports_count} corroborated={u.corroborated_count}")


def main():
    p = argparse.ArgumentParser(description='Steward ops: list / set rung / set role')
    p.add_argument('--list', action='store_true', help='list all identities')
    p.add_argument('--handle', help='target by display_handle (e.g. k-0d241c76ea)')
    p.add_argument('--user-id', type=int, help='target by numeric user id')
    p.add_argument('--rung', type=int, choices=[1, 2, 3], help='set trust rung')
    p.add_argument('--role', choices=VALID_ROLES, help='set editorial role')
    args = p.parse_args()

    if not any([args.list, args.rung, args.role]):
        p.print_help()
        return

    from app import create_app
    from app.models import db, User
    from app.moderation.routes import _vouch_user_to_rung

    app = create_app()
    with app.app_context():
        if args.list:
            users = User.query.order_by(User.userid).all()
            print(f"=== {len(users)} identities ===")
            for u in users:
                print(_fmt(u))
            if not (args.rung or args.role):
                return

        if not (args.handle or args.user_id):
            print('ERROR: --handle or --user-id is required to change anything')
            sys.exit(1)

        if args.user_id:
            user = db.session.get(User, args.user_id)
        else:
            user = User.query.filter_by(display_handle=args.handle).first()

        if user is None:
            print(f"ERROR: no such identity ({args.handle or args.user_id})")
            sys.exit(1)

        print('before:')
        print(_fmt(user))

        if args.role:
            user.role = args.role
            db.session.commit()

        if args.rung:
            # Same helper the API uses: also re-derives this user's Events.
            _vouch_user_to_rung(user, args.rung)

        db.session.refresh(user)
        print('after:')
        print(_fmt(user))

        if args.rung:
            from app.models import FileUpload, Event
            event_ids = {fu.event_id for fu in
                         FileUpload.query.filter_by(user_id=user.userid).all() if fu.event_id}
            if event_ids:
                print('affected events (re-derived):')
                for eid in sorted(event_ids):
                    ev = db.session.get(Event, eid)
                    if ev:
                        print(f"  Event #{ev.id} status={ev.status} "
                              f"corroborated={ev.corroboration_count} "
                              f"independent={ev.independent_source_count}")


if __name__ == '__main__':
    main()
