# app/profile/routes.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

profile_bp = Blueprint('profile', __name__, url_prefix='/api')

@profile_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    try:
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        return jsonify({
            "id": str(user.userid),
            "name": str(user.username),
            "email": str(user.email),
            "created_date": str(user.created_date)
        }), 200
    except Exception as e:
        return jsonify({"message": "An error occurred", "error": str(e)}), 500
