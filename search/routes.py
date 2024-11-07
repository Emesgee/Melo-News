# app/search/routes.py
from flask import Blueprint, jsonify, request
from datetime import datetime
from sqlalchemy import or_
from app.models import db, Search, Input, FileUpload, InputTemplate

# Define blueprint with /api prefix
search_bp = Blueprint('search', __name__, url_prefix='/api')

@search_bp.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    user_id = data.get('user_id')
    term = data.get('term')
    template_ids = data.get('template_ids')
    filters = data.get('filters', {})

    # Validate required fields
    if not user_id or not isinstance(user_id, int):
        return jsonify({"error": "Invalid or missing user_id"}), 400
    if not term or not isinstance(term, str):
        return jsonify({"error": "Invalid or missing term"}), 400
    if not template_ids or not isinstance(template_ids, list):
        return jsonify({"error": "Invalid or missing template_ids"}), 400

    # Check required fields
    if not user_id or not term or not template_ids:
        return jsonify({"error": "User ID, term, and at least one template ID are required."}), 400

    # Create and save a new Search record
    primary_template_id = template_ids[0] if template_ids else None
    new_search = Search(userid=user_id)
    db.session.add(new_search)
    db.session.flush()  # Retrieve search ID

    # Create and save a new Input record
    new_input = Input(
        searchid=new_search.searchid,
        keyword=term,
        filters=filters,
        date_input=datetime.utcnow(),
        templateid=primary_template_id
    )
    db.session.add(new_input)
    db.session.commit()  # Commit both search and input records

    # Build search query based on input templates
    query = FileUpload.query
    for template_id in template_ids:
        template = InputTemplate.query.get(template_id)
        if template:
            if template.template_type == "Keyword Search":
                query = query.filter(or_(
                    FileUpload.filename.ilike(f'%{term}%'),
                    FileUpload.title.ilike(f'%{term}%'),
                    FileUpload.tags.ilike(f'%{term}%'),
                    FileUpload.subject.ilike(f'%{term}%')
                ))
            elif template.template_type == "Date Range Search":
                if filters.get("from_date"):
                    query = query.filter(FileUpload.upload_date >= filters["from_date"])
                if filters.get("to_date"):
                    query = query.filter(FileUpload.upload_date <= filters["to_date"])
            elif template.template_type == "Location-Based Search":
                if filters.get("city"):
                    query = query.filter(FileUpload.city.ilike(f'%{filters["city"]}%'))
                if filters.get("country"):
                    query = query.filter(FileUpload.country.ilike(f'%{filters["country"]}%'))

    # Execute search and return results
    results = query.all()
    file_list = [
        {
            "id": file.id,
            "filename": file.filename,
            "file_path": file.file_path,
            "tags": file.tags,
            "subject": file.subject,
            "city": file.city,
            "country": file.country,
            "upload_date": file.upload_date,
            "lat": file.lat,
            "lon": file.lon
        }
        for file in results
    ]

    return jsonify({
        "message": "Search and input recorded successfully.",
        "search_id": new_search.searchid,
        "results": file_list
    }), 200
