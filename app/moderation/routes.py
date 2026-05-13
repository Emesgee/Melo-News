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

All endpoints require a logged-in user whose ``is_moderator`` flag is
True. Moderators are bootstrapped manually (set the flag directly in
the database for the first reviewer) until a promotion UI exists.
"""

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import db, FileUpload, User
from app.story.serializers import serialize_upload

moderation_bp = Blueprint('moderation', __name__, url_prefix='/api/moderation')

_VALID_STATUSES = {'PENDING', 'VERIFIED', 'REJECTED'}


def moderator_required(fn):
    """Require an authenticated user whose is_moderator flag is True."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or not getattr(user, 'is_moderator', False):
            return jsonify({'error': 'Moderator role required'}), 403
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

    q = (
        FileUpload.query
        .filter(FileUpload.verification_status == status)
        .order_by(FileUpload.upload_date.desc())
    )
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

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('reject upload %s failed: %s', upload_id, exc)
        return jsonify({'error': 'Database error'}), 500

    return jsonify(serialize_upload(upload)), 200
