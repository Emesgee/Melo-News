# app/file_types/routes.py
from flask import Blueprint, jsonify
from app.models import FileType  # Make sure FileType is imported correctly

file_types_bp = Blueprint('file_types', __name__, url_prefix='/api/file-types')

@file_types_bp.route('/', methods=['GET'])
def get_file_types():
    try:
        # Retrieve all file types from the database
        file_types = FileType.query.all()
        # Convert each file type to a dictionary format
        file_types_data = [{'id': ft.filetypeid, 'type_name': ft.type_name} for ft in file_types]
        return jsonify(file_types_data), 200
    except Exception as e:
        print("Error fetching file types:", e)
        return jsonify({"message": "Error retrieving file types"}), 500
