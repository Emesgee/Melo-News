# app/auth/routes.py
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.models import db, User
from datetime import datetime
from flask_cors import CORS
from flask_cors import cross_origin


auth_bp = Blueprint('auth', __name__ ,url_prefix='/auth')
CORS(auth_bp, origins="http://localhost:3000", supports_credentials=True)


# auth/routes.py

@auth_bp.route('/register', methods=['POST'])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
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
              name:
                type: string
                example: "Mo Doe"
              email:
                type: string
                example: "mo.doe@example.com"
              password:
                type: string
                example: "securePassword123"
    responses:
      201:
        description: User registered successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "User registered successfully!"
      400:
        description: Missing or invalid parameters
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Missing required fields"
    """
    # Rest of your registration code remains the same
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201


# User Login (POST)

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



@auth_bp.route('/login', methods=['POST'])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def login_user():
    data = request.json
    is_valid, error_message = validate_user_data(data, ['email', 'password'])
    if not is_valid:
        return jsonify({"message": error_message}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"message": "Incorrect email or password"}), 401

    access_token = create_access_token(identity=user.userid)
    return jsonify(access_token=access_token), 200


