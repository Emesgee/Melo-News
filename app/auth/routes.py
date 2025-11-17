from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.models import db, User
from flask_cors import CORS
from datetime import timedelta
import logging

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Apply CORS to the entire auth blueprint
CORS(auth_bp, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
def register_user():
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 415

    data = request.get_json()

    # Validate required fields using the utility function
    is_valid, error_message = validate_user_data(data, ['username', 'email', 'password'])
    if not is_valid:
        return jsonify({"error": error_message}), 400

    username = data['username']
    email = data['email']
    password = data['password']

    # Check if email already exists
    logging.debug(f"Checking email: {email}")
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
def login_user():
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 415

    data = request.json
    is_valid, error_message = validate_user_data(data, ['email', 'password'])
    if not is_valid:
        return jsonify({"error": error_message}), 400

    # Verify user credentials
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"error": "Incorrect email or password"}), 401

    # Generate JWT Token (with expiration time)
    access_token = create_access_token(identity=str(user.userid), expires_delta=timedelta(hours=1))

    return jsonify({
        "message": "Login successful",
        "username": user.username,
        "access_token": access_token
    }), 200
