import os
import shutil
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import db, FileUpload, FileType
from app.utils.azure_blob import upload_file_to_azure_storage, delete_file_from_azure_storage
from app.utils.rate_limit import per_user_or_ip_key
from .analysis_service import start_analysis_thread
from .media_sanitizer import sanitize_for_upload, safe_remove

file_upload_bp = Blueprint('file_upload', __name__, url_prefix='/api/file_upload')

# Per-user (or IP for unauth) rate limit on submission endpoints.
# Limits target abuse from a compromised account or a spam bot while
# leaving plenty of headroom for a reporter actively documenting an
# unfolding event.
limiter = Limiter(key_func=per_user_or_ip_key, storage_uri='memory://')


def _serialize_upload(f):
    """Serialize a FileUpload record to a dict."""
    return {
        'id': f.id,
        'filename': f.filename,
        'file_path': f.file_path,
        'title': f.title,
        'tags': f.tags,
        'subject': f.subject,
        'city': f.city,
        'country': f.country,
        'lat': f.lat,
        'lon': f.lon,
        'upload_date': f.upload_date.isoformat() if f.upload_date else None,
        'confidence_score': f.confidence_score,
        'severity': f.severity,
        'analysis_status': f.analysis_status,
        'transcription': f.transcription,
        'witness_statement': f.witness_statement,
        'source_type': f.source_type,
        'is_sensitive': f.is_sensitive,
        'verification_status': f.verification_status,
        'verification_note': f.verification_note,
        'verified_at': f.verified_at.isoformat() if f.verified_at else None,
    }


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
@limiter.limit('30 per hour; 100 per day')
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
    witness_statement = request.form.get('witness_statement')
    source_type = request.form.get('source_type', 'eyewitness')
    is_sensitive = request.form.get('is_sensitive', 'false').lower() == 'true'
    
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

    # Keep a raw copy for the background analyzer so it can still extract
    # EXIF GPS/timestamp/device for confidence scoring and map placement.
    # The public-served file (file_path) gets sanitized in place below.
    analysis_source_path = file_path + '.raw-for-analysis'
    try:
        shutil.copy2(file_path, analysis_source_path)
    except OSError as exc:
        current_app.logger.warning("Could not stage raw analysis copy: %s", exc)
        analysis_source_path = file_path

    # Strip EXIF (GPS + device tags) from the file we will hand to Azure
    # or serve via /api/uploads. Failures fall back to the raw file but are
    # logged loudly — reporter location can leak via embedded GPS otherwise.
    sanitized_path = sanitize_for_upload(file_path)
    if sanitized_path != file_path:
        try:
            os.replace(sanitized_path, file_path)
        except OSError as exc:
            current_app.logger.error(
                "Sanitized file replace failed for %s: %s — uploading raw file",
                file_path, exc,
            )
            safe_remove(sanitized_path)

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
            # The sanitized local copy is no longer needed once it's in Azure.
            safe_remove(file_path)
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
            lon=lon,
            witness_statement=witness_statement,
            source_type=source_type,
            is_sensitive=is_sensitive,
        )
        db.session.add(new_upload)
        db.session.flush()
        from app.events.service import process_new_report
        process_new_report(new_upload)
        db.session.commit()

        start_analysis_thread(new_upload.id, analysis_source_path)

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


@file_upload_bp.route('/my-uploads', methods=['GET'])
@jwt_required()
def my_uploads():
    """Return all uploads belonging to the authenticated user."""
    user_id = get_jwt_identity()
    uploads = (
        FileUpload.query
        .filter_by(user_id=user_id)
        .order_by(FileUpload.upload_date.desc())
        .all()
    )
    return jsonify([_serialize_upload(f) for f in uploads]), 200


@file_upload_bp.route('/<int:upload_id>', methods=['PUT'])
@jwt_required()
def edit_upload(upload_id):
    """Update metadata of an upload owned by the authenticated user."""
    user_id = get_jwt_identity()
    upload = FileUpload.query.get_or_404(upload_id)

    if str(upload.user_id) != str(user_id):
        return jsonify({'message': 'Forbidden'}), 403

    data = request.get_json(silent=True) or {}

    editable = ['title', 'tags', 'subject', 'city', 'country', 'witness_statement', 'source_type']
    for field in editable:
        if field in data:
            setattr(upload, field, data[field])

    if 'is_sensitive' in data:
        upload.is_sensitive = bool(data['is_sensitive'])

    for coord in ('lat', 'lon'):
        if coord in data:
            try:
                setattr(upload, coord, float(data[coord]) if data[coord] is not None else None)
            except (ValueError, TypeError):
                pass

    try:
        db.session.commit()
        return jsonify(_serialize_upload(upload)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('Edit upload error: %s', e)
        return jsonify({'message': str(e)}), 500


@file_upload_bp.route('/<int:upload_id>', methods=['DELETE'])
@jwt_required()
def delete_upload(upload_id):
    """Delete an upload owned by the authenticated user.

    Also removes the underlying blob from Azure (or the local file in
    dev-mode fallback) so reporter media is actually gone, not just
    delisted. Storage cleanup failures are logged but don't block the DB
    deletion — a stranded blob is preferable to leaving a record the
    reporter can never remove.
    """
    user_id = get_jwt_identity()
    upload = FileUpload.query.get_or_404(upload_id)

    if str(upload.user_id) != str(user_id):
        return jsonify({'message': 'Forbidden'}), 403

    file_path_value = upload.file_path or ''
    blob_name = upload.filename
    is_remote = file_path_value.startswith('http://') or file_path_value.startswith('https://')

    if is_remote and blob_name:
        container_name = current_app.config.get('AZURE_BLOB_CONTAINER', 'uploads')
        ok = delete_file_from_azure_storage(blob_name, container_name)
        if not ok:
            current_app.logger.warning(
                "Proceeding with DB delete for upload %s despite Azure cleanup failure", upload_id
            )
    elif file_path_value.startswith('/api/uploads/') and blob_name:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        local_path = os.path.join(upload_folder, blob_name)
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except OSError as exc:
            current_app.logger.warning("Local file cleanup failed for upload %s: %s", upload_id, exc)

    try:
        db.session.delete(upload)
        db.session.commit()
        return jsonify({'message': 'Deleted'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('Delete upload error: %s', e)
        return jsonify({'message': str(e)}), 500


# ── Chunked upload support ────────────────────────────────────────────────────

import uuid
import tempfile

# In-memory chunk registry: { upload_id: { 'dir': str, 'chunks': set, 'total': int, 'filename': str, 'file_type': str } }
_CHUNK_REGISTRY = {}


@file_upload_bp.route('/chunk', methods=['POST'])
@limiter.limit('1000 per hour')
@jwt_required()
def receive_chunk():
    """Accept a single chunk of a multi-part upload."""
    chunk = request.files.get('chunk')
    if not chunk:
        return jsonify({'message': 'No chunk provided'}), 400

    chunk_index = int(request.form.get('chunk_index', 0))
    total_chunks = int(request.form.get('total_chunks', 1))
    filename = secure_filename(request.form.get('filename', 'upload'))
    file_type = request.form.get('file_type', 'application/octet-stream')
    upload_id = request.form.get('upload_id') or str(uuid.uuid4())

    if upload_id not in _CHUNK_REGISTRY:
        tmp_dir = tempfile.mkdtemp(prefix='melo_chunk_')
        _CHUNK_REGISTRY[upload_id] = {
            'dir': tmp_dir,
            'chunks': set(),
            'total': total_chunks,
            'filename': filename,
            'file_type': file_type,
        }

    reg = _CHUNK_REGISTRY[upload_id]
    chunk_path = os.path.join(reg['dir'], f'chunk_{chunk_index:05d}')
    chunk.save(chunk_path)
    reg['chunks'].add(chunk_index)

    return jsonify({'upload_id': upload_id, 'received': chunk_index}), 200


@file_upload_bp.route('/chunk-complete', methods=['POST'])
@limiter.limit('30 per hour; 100 per day')
@jwt_required()
def complete_chunk_upload():
    """Assemble chunks and create the FileUpload record."""
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    upload_id = data.get('upload_id')
    if not upload_id or upload_id not in _CHUNK_REGISTRY:
        return jsonify({'message': 'Unknown upload_id'}), 400

    reg = _CHUNK_REGISTRY.pop(upload_id)

    if len(reg['chunks']) != reg['total']:
        return jsonify({'message': f"Missing chunks: expected {reg['total']}, got {len(reg['chunks'])}"}), 400

    filename = reg['filename']
    file_extension = filename.split('.')[-1].lower()

    # Resolve file_type_id from extension if not provided
    file_type_id_raw = data.get('file_type_id')
    file_type_id = None
    if file_type_id_raw:
        try:
            file_type_id = int(file_type_id_raw)
        except (ValueError, TypeError):
            pass

    if not file_type_id:
        ft = FileType.query.filter(FileType.allowed_extensions.ilike(f'%{file_extension}%')).first()
        file_type_id = ft.filetypeid if ft else None

    if not file_type_id:
        return jsonify({'message': 'Could not determine file type'}), 400

    # Assemble chunks into final file
    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
    os.makedirs(upload_folder, exist_ok=True)
    final_path = os.path.join(upload_folder, unique_filename)

    with open(final_path, 'wb') as out:
        for i in range(reg['total']):
            chunk_path = os.path.join(reg['dir'], f'chunk_{i:05d}')
            with open(chunk_path, 'rb') as cf:
                out.write(cf.read())
            os.remove(chunk_path)

    shutil.rmtree(reg['dir'], ignore_errors=True)

    # Stage a raw copy for the analyzer so EXIF-derived lat/lon survives.
    analysis_source_path = final_path + '.raw-for-analysis'
    try:
        shutil.copy2(final_path, analysis_source_path)
    except OSError as exc:
        current_app.logger.warning("Could not stage raw analysis copy: %s", exc)
        analysis_source_path = final_path

    # Strip EXIF before the file leaves the server.
    sanitized_path = sanitize_for_upload(final_path)
    if sanitized_path != final_path:
        try:
            os.replace(sanitized_path, final_path)
        except OSError as exc:
            current_app.logger.error(
                "Sanitized file replace failed for %s: %s — uploading raw file",
                final_path, exc,
            )
            safe_remove(sanitized_path)

    blob_url = f"/api/uploads/{unique_filename}"
    if _should_use_azure():
        try:
            container_name = current_app.config.get('AZURE_BLOB_CONTAINER', 'uploads')
            storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
            upload_file_to_azure_storage(final_path, unique_filename, container_name)
            blob_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{unique_filename}"
            safe_remove(final_path)
        except Exception as e:
            current_app.logger.warning("Azure upload failed for chunk assembly: %s", e)

    try:
        lat = float(data['lat']) if data.get('lat') is not None else None
        lon = float(data['lon']) if data.get('lon') is not None else None
    except (ValueError, TypeError):
        lat = lon = None

    try:
        new_upload = FileUpload(
            filename=unique_filename,
            file_path=blob_url,
            title=data.get('title'),
            tags=data.get('tags'),
            subject=data.get('subject'),
            city=data.get('city'),
            country=data.get('country'),
            upload_date=datetime.utcnow(),
            user_id=user_id,
            file_type_id=file_type_id,
            lat=lat,
            lon=lon,
        )
        db.session.add(new_upload)
        db.session.flush()
        from app.events.service import process_new_report
        process_new_report(new_upload)
        db.session.commit()
        start_analysis_thread(new_upload.id, analysis_source_path)
        return jsonify({
            'message': 'Upload complete.',
            'file_id': new_upload.id,
            'file_url': blob_url,
            'analysis_status': 'PENDING',
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error('Chunk complete error: %s', e)
        return jsonify({'message': str(e)}), 500
