"""
app/moderation/audit.py

Append-only audit trail for moderator + steward actions.

`record` writes one AuditLog row per action; it does NOT commit -- the calling
endpoint owns the transaction, so the audit row and the state change land (or
roll back) together. `serialize` renders a row for the API, resolving the actor
to a display name without ever leaking an email/password.
"""

from app.models import db, AuditLog, User


def record(action, target_type, target_id, actor_id=None,
           before=None, after=None, note=None):
    """Append an audit entry. Does not commit (the caller's transaction owns it).

    action      verify | reject | reverify | set_rung | set_role
    target_type 'upload' (a report) | 'user' (an identity)
    before/after coerced to str so ints (rungs) and enums (status/role) store
                 uniformly and the transition reads back without type guessing.
    """
    entry = AuditLog(
        actor_id=int(actor_id) if actor_id is not None else None,
        action=action,
        target_type=target_type,
        target_id=int(target_id),
        before=None if before is None else str(before),
        after=None if after is None else str(after),
        note=(note or None),
    )
    db.session.add(entry)
    return entry


def _actor_label(actor_id):
    if actor_id is None:
        return 'system'
    u = db.session.get(User, actor_id)
    if u is None:
        return f'#{actor_id}'
    # Prefer a human-readable handle; never expose email.
    return u.username or u.display_handle or f'#{actor_id}'


def serialize(entry):
    return {
        'id': entry.id,
        'action': entry.action,
        'target_type': entry.target_type,
        'target_id': entry.target_id,
        'before': entry.before,
        'after': entry.after,
        'note': entry.note,
        'actor_id': entry.actor_id,
        'actor': _actor_label(entry.actor_id),
        'created_at': entry.created_at.isoformat() if entry.created_at else None,
    }
