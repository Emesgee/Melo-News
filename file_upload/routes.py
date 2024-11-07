import os
from flask import Blueprint, jsonify, request, current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import db, FileUpload, FileType

file_upload_bp = Blueprint('file_upload', __name__, url_prefix='/api/file_upload')

@file_upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """
    Endpoint for file upload.
    Expects a file along with metadata such as title, tags, subject, city, country, and file_type_id.
    """
    user_id = get_jwt_identity()

    # Check for 'file' in request
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    # Validate and parse file_type_id from the form data
    try:
        file_type_id = int(request.form.get('file_type_id'))
    except (ValueError, TypeError):
        return jsonify({'message': 'Invalid file type ID'}), 400

    file_type = FileType.query.get(file_type_id)
    if not file_type:
        return jsonify({'message': 'Invalid file type'}), 400

    # Collect additional metadata fields
    title = request.form.get('title')
    tags = request.form.get('tags')
    subject = request.form.get('subject')
    city = request.form.get('city')
    country = request.form.get('country')

    # Validate the file extension
    file_extension = file.filename.split('.')[-1].lower()
    allowed_extensions_list = file_type.allowed_extensions.split(',')
    if file_extension not in allowed_extensions_list:
        return jsonify({'message': f'Invalid file extension for {file_type.type_name}'}), 400

    # Use a secure filename and set the path for saving the file
    secure_name = secure_filename(file.filename)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, secure_name)

    try:
        # Ensure the upload directory exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save the file to the upload directory
        file.save(file_path)

        # Dummy values for latitude and longitude (if needed, replace with actual EXIF data extraction)
        latitude, longitude = None, None

        # Save file information to the database
        new_upload = FileUpload(
            filename=secure_name,
            file_path=file_path,
            title=title,
            tags=tags,
            subject=subject,
            city=city,
            country=country,
            upload_date=datetime.utcnow(),
            user_id=user_id,
            file_type_id=file_type_id,
            lat=latitude,
            lon=longitude
        )
        db.session.add(new_upload)
        db.session.commit()

        # Generate a public URL for the uploaded file
        file_url = url_for('static', filename=f'uploads/{secure_name}', _external=True)

        return jsonify({
            'message': f'File {secure_name} uploaded successfully!',
            'file_url': file_url,
            'file_id': new_upload.id
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading file: {e}")
        return jsonify({'message': f"Error uploading file: {str(e)}"}), 500
