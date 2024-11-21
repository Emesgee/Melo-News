from flask import Blueprint, jsonify, request
from datetime import datetime
from sqlalchemy import or_
from app.models import db, Search, Input, FileUpload, InputTemplate, TestJson

search_bp = Blueprint('search', __name__, url_prefix='/api')

@search_bp.route('/search', methods=['GET', 'POST'])
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

    # Build queries for FileUpload and TestJson tables
    file_query = FileUpload.query
    testjson_query = TestJson.query

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
                testjson_query = testjson_query.filter(or_(
                    TestJson.message.ilike(f'%{term}%'),
                    TestJson.tags.ilike(f'%{term}%'),
                    TestJson.subject.ilike(f'%{term}%')
                ))
            elif template.template_type == "Date Range Search":
                if filters.get("from_date"):
                    file_query = file_query.filter(FileUpload.upload_date >= filters["from_date"])
                    testjson_query = testjson_query.filter(TestJson.time >= filters["from_date"])
                if filters.get("to_date"):
                    file_query = file_query.filter(FileUpload.upload_date <= filters["to_date"])
                    testjson_query = testjson_query.filter(TestJson.time <= filters["to_date"])
            elif template.template_type == "Location-Based Search":
                if filters.get("city"):
                    file_query = file_query.filter(FileUpload.city.ilike(f'%{filters["city"]}%'))
                    testjson_query = testjson_query.filter(TestJson.matched_city.ilike(f'%{filters["city"]}%'))
                if filters.get("country"):
                    file_query = file_query.filter(FileUpload.country.ilike(f'%{filters["country"]}%'))
                    testjson_query = testjson_query.filter(TestJson.city_result.ilike(f'%{filters["country"]}%'))

    # Execute queries and combine results
    file_results = file_query.all()
    testjson_results = testjson_query.all()

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

    for record in testjson_results:
        combined_results.append({
            "source": "TestJson",
            "id": record.id,
            "title": record.subject,
            "lat": record.latitude,
            "lon": record.longitude,
            "country": record.city_result,
            "city": record.matched_city,
            "message": record.message,
            "tags": record.tags,
        })

    return jsonify({
        "message": "Search completed successfully.",
        "results": combined_results
    }), 200
