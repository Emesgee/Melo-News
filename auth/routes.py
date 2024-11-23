# app/auth/routes.py
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.models import db, User
from flask_cors import CORS

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Apply CORS to the entire auth blueprint
CORS(auth_bp, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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
    """
    User Registration
    ---
    tags:
      - Authentication
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              username:
                type: string
                example: testuser
              email:
                type: string
                example: testuser@example.com
              password:
                type: string
                example: securepassword
    responses:
      201:
        description: Registration successful
      415:
        description: Request body must be JSON
      400:
        description: Bad request
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 415

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "All fields are required"}), 400

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email is already registered"}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(username=name, email=email, password=hashed_password)
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

    # Generate JWT Token
    access_token = create_access_token(identity=str(user.userid))  # Ensure 'userid' is a string
    return jsonify(access_token=access_token), 200
