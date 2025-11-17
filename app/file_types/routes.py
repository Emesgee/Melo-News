# app/file_types/routes.py
from flask import Blueprint, jsonify
from app.models import FileType

file_types_bp = Blueprint('file_types', __name__, url_prefix='/api/file-types')

@file_types_bp.route('/', methods=['GET'])
def get_file_types():
    file_types = FileType.query.all()
    return jsonify([
        {
            "id": ft.filetypeid,  # <-- use filetypeid here
            "type_name": ft.type_name,
            "allowed_extensions": ft.allowed_extensions
        }
        for ft in file_types
    ])
  