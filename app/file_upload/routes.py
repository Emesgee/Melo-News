import os
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import db, FileUpload, FileType
from app.utils.azure_blob import upload_file_to_azure_storage

file_upload_bp = Blueprint('file_upload', __name__, url_prefix='/api/file_upload')

@file_upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

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
    
    # Convert lat/lon to floats - CRITICAL for search/map to work
    try:
        lat = float(request.form.get('lat')) if request.form.get('lat') else None
        lon = float(request.form.get('lon')) if request.form.get('lon') else None
    except (ValueError, TypeError):
        lat = None
        lon = None

    # Validate the file extension
    file_extension = file.filename.split('.')[-1].lower()
    allowed_extensions_list = [ext.strip() for ext in file_type.allowed_extensions.split(',')]
    if file_extension not in allowed_extensions_list:
        return jsonify({'message': f'Invalid file extension for {file_type.type_name}'}), 400

    secure_name = secure_filename(file.filename)
    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_name}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    try:
        # Upload to Azure Blob Storage
        container_name = current_app.config.get('AZURE_BLOB_CONTAINER', 'uploads')
        storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        if not storage_account:
            raise Exception("AZURE_STORAGE_ACCOUNT_NAME not set in environment variables.")
        upload_file_to_azure_storage(file_path, unique_filename, container_name)
        os.remove(file_path)  # Optionally delete local file after upload

        # Construct Azure Blob URL
        blob_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{unique_filename}"

        # Save file information to the database
        new_upload = FileUpload(
            filename=unique_filename,
            file_path=blob_url,  # Store Azure Blob file URL
            title=title,
            tags=tags,
            subject=subject,
            city=city,
            country=country,
            upload_date=datetime.utcnow(),
            user_id=user_id,
            file_type_id=file_type_id,
            lat=lat,
            lon=lon
        )
        db.session.add(new_upload)
        db.session.commit()

        return jsonify({
            'message': f'File {secure_name} uploaded successfully to Azure Blob Storage!',
            'file_url': blob_url,
            'fileUrl': blob_url,  # for frontend JS convention
            'file_id': new_upload.id,
            'title': title,
            'tags': tags,
            'subject': subject,
            'city': city,
            'country': country,
            'lat': lat,
            'lon': lon
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading file: {e}")
        return jsonify({'message': f"Error uploading file: {str(e)}"}), 500