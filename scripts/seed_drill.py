#!/usr/bin/env python
"""
Seed / simulate / reset the T4P drill scenario (see app/drill/scenario.py).

Run from the repo root, in the environment where the app's DATABASE_URL points
at a NON-production, drill-only database:

    python scripts/seed_drill.py --provision    # create the cohort (live drill)
    python scripts/seed_drill.py --role-cards    # print the briefs to hand out
    python scripts/seed_drill.py --simulate      # dry-run the whole scenario
    python scripts/seed_drill.py --reset         # wipe all drill data

--role-cards is pure data and needs no database. The others run inside an app
context via create_app(). All drill data is namespaced by the `drill:` handle
prefix, so --reset only ever removes drill rows.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.drill import scenario  # noqa: E402


def _print_role_cards():
    for c in scenario.role_cards():
        tag = (f"   [SYBIL: same human as {scenario.HANDLE_PREFIX}{c['sybil_of']}]"
               if c['sybil_of'] else '')
        print(f"[{c['key']}] {c['account']} (rung {c['rung']}) -> {c['event']}{tag}")
        print(f"     pin: {c['lat']}, {c['lon']}  ({c['city']})  severity: {c['severity']}")
        print(f"     text: {c['text']}\n")


def main():
    p = argparse.ArgumentParser(description='T4P drill seeding / simulation tool')
    p.add_argument('--reset', action='store_true', help='wipe all drill data')
    p.add_argument('--provision', action='store_true', help='create the cohort identities')
    p.add_argument('--simulate', action='store_true', help='dry-run the full scenario end to end')
    p.add_argument('--role-cards', action='store_true', help='print the live-drill briefs')
    args = p.parse_args()

    # Role cards are pure data — no app or database needed.
    if args.role_cards and not (args.reset or args.provision or args.simulate):
        _print_role_cards()
        return

    if not any([args.reset, args.provision, args.simulate, args.role_cards]):
        p.print_help()
        return

    from app import create_app
    from app.models import db

    app = create_app()
    with app.app_context():
        if args.reset:
            print('reset:', scenario.reset(db))
        if args.simulate:
            print(json.dumps(scenario.simulate(db), indent=2, default=str))
        elif args.provision:
            users = scenario.provision(db)
            print(f'provisioned {len(users)} identities (incl. the steward)')
        if args.role_cards:
            _print_role_cards()


if __name__ == '__main__':
    main()
