from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from app.models import db, User
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import logging
import re

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Rate limiter for auth endpoints
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Apply CORS to the auth blueprint (allow dev + tunnel origins, with credentials)
CORS(
    auth_bp,
    resources={r"/*": {
        "origins": [
            "https://app.melonews.tech",
            "http://localhost:3000",
        ],
    }},
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type", "Authorization"],
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Password validation constants
MIN_PASSWORD_LENGTH = 8
PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]'
)

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password meets minimum security requirements."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[@$!%*?&]', password):
        return False, "Password must contain at least one special character (@$!%*?&)"
    return True, ""

# Utility Function to Validate User Data
def validate_user_data(data, required_fields):
    """
    Validates that the required fields are present in the request data.
    :param data: The JSON data to validate
    :param required_fields: List of required field names
    :return: Tuple (is_valid, error_message)
    """
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    return True, ""


# User Registration Route
@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register_user():
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Validate required fields using the utility function
    is_valid, error_message = validate_user_data(data, ['username', 'email', 'password'])
    if not is_valid:
        return jsonify({"error": error_message}), 400

    username = data['username']
    email = data['email']
    password = data['password']

    # Validate password strength
    pw_valid, pw_error = validate_password(password)
    if not pw_valid:
        return jsonify({"error": pw_error}), 400

    # Check if email already exists
    logger.info("Registration attempt for a new user")
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email is already registered"}), 409

    # Generate hashed password and save user
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201


# User Login Route
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_user():
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    is_valid, error_message = validate_user_data(data, ['email', 'password'])
    if not is_valid:
        return jsonify({"error": error_message}), 400

    # Verify user credentials
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"error": "Incorrect email or password"}), 401

    # Generate JWT Token (with expiration time)
    access_token = create_access_token(identity=str(user.userid), expires_delta=timedelta(hours=1))

    response = jsonify({
        "message": "Login successful",
        "username": user.username,
        "access_token": access_token  # Kept for backward compat; prefer cookie
    })
    set_access_cookies(response, access_token)
    return response, 200


# User Logout Route (clears httpOnly cookie)
@auth_bp.route('/logout', methods=['POST'])
def logout_user():
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)
    return response, 200


# Check authentication status (cookie-based)
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "userid": user.userid,
        "username": user.username,
        "email": user.email,
        "is_moderator": bool(getattr(user, 'is_moderator', False)),
    }), 200
