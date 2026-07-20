"""
Editorial moderation queue for citizen-submitted stories.

Citizen uploads (web + Android) land in FileUpload with
``verification_status='PENDING'`` and are excluded from the public feed
until a moderator decides. These endpoints let an authorized moderator
walk the queue and approve or reject each submission.

Endpoints
---------
GET  /api/moderation/queue                    list pending submissions
POST /api/moderation/<id>/verify              approve (becomes public)
POST /api/moderation/<id>/reject              reject (with reason)

All endpoints require a logged-in user whose ``role`` is ``moderator`` or
``steward``. The first moderator is bootstrapped manually (set the role
directly in the database) until a promotion UI exists.
"""

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import db, FileUpload, User, Event
from app.story.serializers import serialize_upload

moderation_bp = Blueprint('moderation', __name__, url_prefix='/api/moderation')

_VALID_STATUSES = {'PENDING', 'VERIFIED', 'REJECTED'}


# Roles allowed through the moderation gate. Stewards are governance-level
# and therefore also moderator-capable.
_MODERATOR_ROLES = {'moderator', 'steward'}


_VALID_ROLES = {'reporter', 'moderator', 'steward'}


def moderator_required(fn):
    """Require an authenticated user whose role can moderate."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or getattr(user, 'role', 'reporter') not in _MODERATOR_ROLES:
            return jsonify({'error': 'Moderator role required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def steward_required(fn):
    """Require a steward — the governance role for role/rung changes."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or getattr(user, 'role', 'reporter') != 'steward':
            return jsonify({'error': 'Steward role required'}), 403
        return fn(*args, **kwargs)
    return wrapper


@moderation_bp.route('/queue', methods=['GET'])
@moderator_required
def queue():
    """List submissions awaiting (or already routed through) review.

    Query params
    ------------
    status : PENDING (default) | VERIFIED | REJECTED
    limit  : int (default 50, max 200)
    offset : int (default 0)
    """
    status = (request.args.get('status') or 'PENDING').upper()
    if status not in _VALID_STATUSES:
        return jsonify({'error': f'status must be one of {sorted(_VALID_STATUSES)}'}), 400

    limit = min(max(request.args.get('limit', default=50, type=int), 1), 200)
    offset = max(request.args.get('offset', default=0, type=int), 0)

    q = FileUpload.query.filter(FileUpload.verification_status == status)

    if status == 'PENDING':
        # Attention-ordered, not FIFO: priority depends on event state + age, so
        # sort in Python. Pilot scale is small; revisit with a SQL score if it grows.
        from app.moderation.gate import compute_priority
        all_rows = q.all()
        all_rows.sort(key=compute_priority, reverse=True)
        total = len(all_rows)
        rows = all_rows[offset:offset + limit]
    else:
        # Audit views (VERIFIED / REJECTED) stay newest-first.
        q = q.order_by(FileUpload.upload_date.desc())
        total = q.count()
        rows = q.limit(limit).offset(offset).all()

    return jsonify({
        'items': [serialize_upload(r) for r in rows],
        'paging': {
            'limit': limit,
            'offset': offset,
            'returned': len(rows),
            'total': total,
            'has_more': (offset + limit) < total,
        },
        'filters': {'status': status},
    }), 200


@moderation_bp.route('/<int:upload_id>/verify', methods=['POST'])
@moderator_required
def verify(upload_id):
    """Approve a submission so it appears on the public feed."""
    upload = FileUpload.query.get_or_404(upload_id)
    data = request.get_json(silent=True) or {}

    moderator_id = get_jwt_identity()
    upload.verification_status = 'VERIFIED'
    upload.verified_at = datetime.now(timezone.utc)
    upload.verified_by = moderator_id
    note = (data.get('note') or '').strip()
    upload.verification_note = note or None

    # A verification changes the Event's corroboration — recompute its status.
    _recompute_owning_event(upload)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('verify upload %s failed: %s', upload_id, exc)
        return jsonify({'error': 'Database error'}), 500

    return jsonify(serialize_upload(upload)), 200


@moderation_bp.route('/<int:upload_id>/reject', methods=['POST'])
@moderator_required
def reject(upload_id):
    """Reject a submission. A reason is required so reporters know why."""
    upload = FileUpload.query.get_or_404(upload_id)
    data = request.get_json(silent=True) or {}

    note = (data.get('note') or '').strip()
    if not note:
        return jsonify({'error': 'note is required when rejecting'}), 422

    moderator_id = get_jwt_identity()
    upload.verification_status = 'REJECTED'
    upload.verified_at = datetime.now(timezone.utc)
    upload.verified_by = moderator_id
    upload.verification_note = note

    # A rejected member no longer counts toward corroboration — recompute.
    _recompute_owning_event(upload)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('reject upload %s failed: %s', upload_id, exc)
        return jsonify({'error': 'Database error'}), 500

    return jsonify(serialize_upload(upload)), 200


def _recompute_owning_event(upload):
    """Recompute the Event a report belongs to after its verification changes.
    No-op for reports that aren't clustered (shouldn't happen post-Stage-D, but
    older rows may predate event assignment)."""
    if not upload.event_id:
        return
    from app.events.service import recompute_event
    event = db.session.get(Event, upload.event_id)
    if event:
        recompute_event(event)


@moderation_bp.route('/users', methods=['GET'])
@steward_required
def list_users():
    """Identities a steward can act on (ADR-0016 rung bootstrap).

    Steward-gated, not moderator-gated: this is the roster behind role/rung
    changes, and it exposes the pseudonym<->rung mapping for every reporter.
    Never returns email or password — a moderation roster has no need for
    contact details, and pseudonymous reporters have none anyway (ADR-0003).
    """
    users = User.query.order_by(User.userid).all()
    return jsonify({
        'users': [{
            'userid': u.userid,
            'username': u.username,
            'handle': u.display_handle,
            'identity_type': getattr(u, 'identity_type', 'registered'),
            'role': getattr(u, 'role', 'reporter'),
            'trust_rung': getattr(u, 'trust_rung', 1),
            'reports_count': getattr(u, 'reports_count', 0),
            'corroborated_count': getattr(u, 'corroborated_count', 0),
        } for u in users],
        'count': len(users),
    }), 200


@moderation_bp.route('/users/<int:user_id>/role', methods=['POST'])
@steward_required
def set_role(user_id):
    """Steward sets a user's role (reporter | moderator | steward).

    High-impact promotions/revocations are M-of-N in the full governance design;
    that's deferred. For the pilot the bootstrap steward acts directly.
    """
    data = request.get_json(silent=True) or {}
    role = (data.get('role') or '').strip().lower()
    if role not in _VALID_ROLES:
        return jsonify({'error': f'role must be one of {sorted(_VALID_ROLES)}'}), 422

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    user.role = role
    db.session.commit()
    return jsonify({'userid': user.userid, 'role': user.role}), 200


def _parse_rung(data):
    """Return an int rung in 1..3 from the request body, or None if invalid."""
    try:
        rung = int(data.get('rung'))
    except (TypeError, ValueError):
        return None
    return rung if 1 <= rung <= 3 else None


def _vouch_user_to_rung(user, rung):
    """Set the user's rung and re-derive their events. A bump to rung 2+ can
    immediately let the reporter's existing corroborated events auto-reach
    CORROBORATED, so re-evaluate those events here. Commits."""
    user.trust_rung = rung
    from app.events.service import recompute_event
    event_ids = {
        fu.event_id for fu in FileUpload.query.filter_by(user_id=user.userid).all()
        if fu.event_id
    }
    for eid in event_ids:
        ev = db.session.get(Event, eid)
        if ev:
            recompute_event(ev)
    db.session.commit()


@moderation_bp.route('/users/<int:user_id>/rung', methods=['POST'])
@steward_required
def set_rung(user_id):
    """Steward vouches a user to a trust rung (1..3) by numeric id."""
    rung = _parse_rung(request.get_json(silent=True) or {})
    if rung is None:
        return jsonify({'error': 'rung must be an integer 1..3'}), 422
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    _vouch_user_to_rung(user, rung)
    return jsonify({'userid': user.userid, 'trust_rung': user.trust_rung}), 200


@moderation_bp.route('/pseudonyms/<handle>/rung', methods=['POST'])
@steward_required
def set_rung_by_handle(handle):
    """Vouch a pseudonym to a rung by its ``k-xxxx`` handle (ADR-0016 bootstrap).

    The tester reads the handle off their device after registering; the steward
    vouches it directly, without first resolving a numeric id.
    """
    rung = _parse_rung(request.get_json(silent=True) or {})
    if rung is None:
        return jsonify({'error': 'rung must be an integer 1..3'}), 422
    user = User.query.filter_by(display_handle=handle).first()
    if not user:
        return jsonify({'error': 'pseudonym not found'}), 404
    _vouch_user_to_rung(user, rung)
    return jsonify({'userid': user.userid, 'handle': user.display_handle,
                    'trust_rung': user.trust_rung}), 200
