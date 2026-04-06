import os
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import db, FileUpload, FileType
from app.utils.azure_blob import upload_file_to_azure_storage
from .analysis_service import start_analysis_thread

file_upload_bp = Blueprint('file_upload', __name__, url_prefix='/api/file_upload')


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip().lower()
    return (
        v.startswith('your_')
        or '...' in v
        or v in {'changeme', 'change_me', 'none', 'null'}
    )


def _should_use_azure() -> bool:
    """Use Azure only when explicitly configured and not placeholder values."""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env != 'production':
        return False

    conn = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')

    if _is_placeholder(conn) or _is_placeholder(account):
        return False

    # Basic sanity check for connection string format.
    conn_l = str(conn).lower()
    return 'accountname=' in conn_l and 'defaultendpointsprotocol=' in conn_l

@file_upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    file_type_raw = request.form.get('file_type_id')
    try:
        file_type_id = int(file_type_raw) if file_type_raw is not None else None
    except (ValueError, TypeError):
        return jsonify({'message': 'Invalid file type ID'}), 400

    if file_type_id is None:
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
    lat_raw = request.form.get('lat')
    lon_raw = request.form.get('lon')
    try:
        lat = float(lat_raw) if lat_raw else None
        lon = float(lon_raw) if lon_raw else None
    except (ValueError, TypeError):
        lat = None
        lon = None

    # Validate the file extension
    file_name = file.filename or ''
    file_extension = file_name.split('.')[-1].lower()
    allowed_extensions_list = [ext.strip() for ext in file_type.allowed_extensions.split(',')]
    if file_extension not in allowed_extensions_list:
        return jsonify({'message': f'Invalid file extension for {file_type.type_name}'}), 400

    secure_name = secure_filename(file_name)
    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_name}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Default to local URL; upgrade to Azure URL only when upload succeeds.
    blob_url = f"/api/uploads/{unique_filename}"
    used_azure = False

    if _should_use_azure():
        try:
            container_name = current_app.config.get('AZURE_BLOB_CONTAINER', 'uploads')
            storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
            upload_file_to_azure_storage(file_path, unique_filename, container_name)
            blob_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{unique_filename}"
            used_azure = True
        except Exception as e:
            current_app.logger.warning("Azure upload failed; using local file URL fallback: %s", e)

    try:
        new_upload = FileUpload(
            filename=unique_filename,
            file_path=blob_url,
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

        start_analysis_thread(new_upload.id, file_path)

        msg_suffix = '' if used_azure else ' (local storage fallback)'
        return jsonify({
            'message': f'File {secure_name} uploaded successfully! Analysis started{msg_suffix}.',
            'file_url': blob_url,
            'fileUrl': blob_url,
            'file_id': new_upload.id,
            'title': title,
            'tags': tags,
            'subject': subject,
            'city': city,
            'country': country,
            'lat': lat,
            'lon': lon,
            'analysis_status': 'PENDING'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading file: {e}")
        return jsonify({'message': f"Error uploading file: {str(e)}"}), 500