# app/analytics/routes.py
"""
API routes for analytics features:
  - /api/analytics/escalation — city escalation status
  - /api/analytics/trending — keyword trends
  - /api/analytics/tension — global tension index
  - /api/analytics/predictions — community predictions
"""

from flask import Blueprint, jsonify, request
from app.models import db, Prediction, PredictionVote
from app.analytics.engine import (
    calculate_all_escalations_multi,
    get_trending_keywords_multi,
    calculate_tension_index_multi,
)
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)


# --- P0-4: Escalation Indicators ---

@analytics_bp.route('/escalation', methods=['GET'])
def get_escalation():
    """Get escalation/de-escalation status for all active cities."""
    hours = request.args.get('hours', default=24, type=int)
    escalations = calculate_all_escalations_multi(db, hours)
    return jsonify({
        'escalations': escalations,
        'summary': {
            'escalating': sum(1 for v in escalations.values() if v == 'escalation'),
            'de_escalating': sum(1 for v in escalations.values() if v == 'de-escalation'),
            'stable': sum(1 for v in escalations.values() if v == 'stable'),
        }
    }), 200


# --- P1-5: Keyword Trending ---

@analytics_bp.route('/trending', methods=['GET'])
def get_trending():
    """Get trending keywords over the last N hours."""
    hours = request.args.get('hours', default=24, type=int)
    limit = request.args.get('limit', default=10, type=int)
    keywords = get_trending_keywords_multi(db, hours, limit)
    return jsonify({
        'keywords': [{'keyword': kw, 'count': cnt} for kw, cnt in keywords],
        'period_hours': hours,
    }), 200


# --- P1-6: Global Tension Index ---

@analytics_bp.route('/tension', methods=['GET'])
def get_tension():
    """Get the current global tension index."""
    hours = request.args.get('hours', default=24, type=int)
    tension = calculate_tension_index_multi(db, hours)
    return jsonify(tension), 200


# --- P2-9: Community Predictions ---

@analytics_bp.route('/predictions', methods=['GET'])
def get_predictions():
    """Get all active predictions with vote tallies."""
    predictions = Prediction.query.filter_by(is_active=True).order_by(
        Prediction.created_at.desc()
    ).all()
    
    results = []
    for p in predictions:
        yes_votes = PredictionVote.query.filter_by(prediction_id=p.id, vote='yes').count()
        no_votes = PredictionVote.query.filter_by(prediction_id=p.id, vote='no').count()
        total = yes_votes + no_votes
        
        results.append({
            'id': p.id,
            'question': p.question,
            'category': p.category,
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'closes_at': p.closes_at.isoformat() if p.closes_at else None,
            'yes_votes': yes_votes,
            'no_votes': no_votes,
            'total_votes': total,
            'yes_pct': round((yes_votes / total) * 100, 1) if total > 0 else 50.0,
        })
    
    return jsonify({'predictions': results}), 200


@analytics_bp.route('/predictions', methods=['POST'])
@jwt_required()
def create_prediction():
    """Create a new prediction poll (admin only)."""
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    user_id = get_jwt_identity()
    prediction = Prediction(
        question=question,
        category=data.get('category', 'general'),
        created_by=user_id,
    )
    db.session.add(prediction)
    db.session.commit()
    return jsonify({'id': prediction.id, 'question': prediction.question}), 201


@analytics_bp.route('/predictions/<int:prediction_id>/vote', methods=['POST'])
@jwt_required()
def vote_prediction(prediction_id):
    """Vote on a prediction poll."""
    data = request.get_json()
    vote = data.get('vote')  # 'yes' or 'no'
    if vote not in ('yes', 'no'):
        return jsonify({'error': 'Vote must be "yes" or "no"'}), 400
    
    user_id = get_jwt_identity()
    
    # Check if already voted
    existing = PredictionVote.query.filter_by(
        prediction_id=prediction_id, user_id=user_id
    ).first()
    
    if existing:
        existing.vote = vote  # Allow changing vote
    else:
        new_vote = PredictionVote(
            prediction_id=prediction_id,
            user_id=user_id,
            vote=vote,
        )
        db.session.add(new_vote)
    
    db.session.commit()
    return jsonify({'message': 'Vote recorded'}), 200
