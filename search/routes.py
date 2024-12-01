#app/search/routes.py

from flask import Blueprint, jsonify, request
from datetime import datetime
from sqlalchemy import or_
from app.models import db, Search, Input, FileUpload, InputTemplate, Telegram

search_bp = Blueprint('search', __name__, url_prefix='/api')

@search_bp.route('/search', methods=['GET', 'POST'])
def search():
    data = request.get_json()
    user_id = 56 #data.get('user_id')
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

    # Build queries for FileUpload and Telegram tables
    file_query = FileUpload.query
    telegram_query = Telegram.query

    for template_id in template_ids:
        template = InputTemplate.query.get(template_id)
        if template:
            if template.template_type == "Keyword Search":
                file_query = file_query.filter(or_(
                    FileUpload.filename.ilike(f'%{term}%'),
                    FileUpload.title.ilike(f'%{term}%'),
                    FileUpload.tags.ilike(f'%{term}%'),
                    FileUpload.subject.ilike(f'%{term}%')
                ))
                telegram_query = telegram_query.filter(or_(
                    Telegram.message.ilike(f'%{term}%'),
                    Telegram.tags.ilike(f'%{term}%'),
                    Telegram.subject.ilike(f'%{term}%')
                ))
            elif template.template_type == "Date Range Search":
                if filters.get("from_date"):
                    file_query = file_query.filter(FileUpload.upload_date >= filters["from_date"])
                    telegram_query = telegram_query.filter(Telegram.time >= filters["from_date"])
                if filters.get("to_date"):
                    file_query = file_query.filter(FileUpload.upload_date <= filters["to_date"])
                    telegram_query = telegram_query.filter(Telegram.time <= filters["to_date"])
            elif template.template_type == "Location-Based Search":
                if filters.get("city"):
                    file_query = file_query.filter(FileUpload.city.ilike(f'%{filters["city"]}%'))
                    telegram_query = telegram_query.filter(Telegram.matched_city.ilike(f'%{filters["city"]}%'))
                if filters.get("country"):
                    file_query = file_query.filter(FileUpload.country.ilike(f'%{filters["country"]}%'))
                    telegram_query = telegram_query.filter(Telegram.city_result.ilike(f'%{filters["country"]}%'))

    # Execute queries and combine results
    file_results = file_query.all()
    telegram_results = telegram_query.all()

    combined_results = []

    for file in file_results:
        combined_results.append({
            "source": "FileUpload",
            "id": file.id,
            "title": file.title,
            "lat": file.lat,
            "lon": file.lon,
            "country": file.country,
            "city": file.city,
        })

    for record in telegram_results:
        combined_results.append({
            "source": "Telegram",
            "id": record.id,
            "title": record.subject,
            "lat": record.lat,
            "lon": record.lon,
            "country": record.city_result,
            "city": record.matched_city,
            "message": record.message,
            "tags": record.tags,
        })

    return jsonify({
        "message": "Search completed successfully.",
        "results": combined_results
    }), 200
