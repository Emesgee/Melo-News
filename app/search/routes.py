from flask import Blueprint, jsonify, request, send_from_directory
from datetime import datetime
from dateutil import parser
from sqlalchemy import or_
from app.models import db, Search, Input, FileUpload, InputTemplate, Telegram
import traceback
import json
import os

# Define the uploads folder path
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'
)

search_bp = Blueprint('search', __name__, url_prefix='/api')

# Route to serve uploaded files
@search_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    Serve files from the uploads directory.
    """
    return send_from_directory(UPLOAD_FOLDER, filename)

@search_bp.route('/search', methods=['POST'])
def search():
    try:
        # Parse and log the incoming request data
        data = request.get_json()
        print("Request data:", data)

        user_id = 1  # Hardcoded for now
        term = data.get('term')
        template_ids = data.get('template_ids')
        filters = data.get('filters', {})

        # Validate required fields
        if not term or not isinstance(term, str):
            return jsonify({"error": "Invalid or missing term"}), 400
        if not template_ids or not isinstance(template_ids, list):
            return jsonify({"error": "Invalid or missing template_ids"}), 400

        # Parse filters
        try:
            filters = json.loads(json.dumps(filters))  # Clean problematic types
        except Exception as e:
            return jsonify({"error": "Invalid filters format", "details": str(e)}), 400

        # Parse ISO date strings
        from_date = parser.isoparse(filters.get("from_date")) if filters.get("from_date") else None
        to_date = parser.isoparse(filters.get("to_date")) if filters.get("to_date") else None

        # Create and save new Search record
        primary_template_id = template_ids[0] if template_ids else None
        new_search = Search(userid=user_id)
        db.session.add(new_search)
        db.session.flush()  # Get searchid

        # Save Input
        new_input = Input(
            searchid=new_search.searchid,
            keyword=term,
            filters=filters,
            date_input=datetime.utcnow(),
            templateid=primary_template_id
        )
        db.session.add(new_input)
        db.session.commit()

        # Start queries
        file_query = FileUpload.query
        telegram_query = Telegram.query

        for template_id in template_ids:
            template = InputTemplate.query.get(template_id)
            if not template:
                print(f"Template ID {template_id} not found.")
                continue

            if template.template_type == "Keyword Search":
                # Skip wildcard-only searches to avoid returning everything
                if term and term != '*':
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
                else:
                    # For wildcard, get all recent uploads (ordered by date)
                    file_query = file_query.order_by(FileUpload.upload_date.desc())
                    telegram_query = telegram_query.order_by(Telegram.time.desc())
            elif template.template_type == "Date Range Search":
                if from_date:
                    file_query = file_query.filter(FileUpload.upload_date >= from_date)
                    telegram_query = telegram_query.filter(Telegram.time >= from_date)
                if to_date:
                    file_query = file_query.filter(FileUpload.upload_date <= to_date)
                    telegram_query = telegram_query.filter(Telegram.time <= to_date)
            elif template.template_type == "Location-Based Search":
                if filters.get("city"):
                    file_query = file_query.filter(FileUpload.city.ilike(f'%{filters["city"]}%'))
                    telegram_query = telegram_query.filter(Telegram.matched_city.ilike(f'%{filters["city"]}%'))
                if filters.get("country"):
                    file_query = file_query.filter(FileUpload.country.ilike(f'%{filters["country"]}%'))
                    telegram_query = telegram_query.filter(Telegram.city_result.ilike(f'%{filters["country"]}%'))

        # Execute queries
        file_results = file_query.all()
        telegram_results = telegram_query.all()

        print("File query results:", file_results)
        print("Telegram query results:", telegram_results)

        # Combine results - ONLY include results with valid lat/lon
        combined_results = [
            {
                "source": "FileUpload",
                "id": file.id,
                "title": file.title,
                "lat": float(file.lat) if file.lat is not None else None,
                "lon": float(file.lon) if file.lon is not None else None,
                "country": file.country,
                "city": file.city,
                "file": file.file_path,
                "fileUrl": file.file_path,
                "description": file.subject,
                "tags": file.tags,
            } for file in file_results if file.lat is not None and file.lon is not None
        ] + [
            {
                "source": "Telegram",
                "id": record.id,
                "title": record.subject,
                "lat": float(record.lat) if record.lat is not None else None,
                "lon": float(record.lon) if record.lon is not None else None,
                "country": record.city_result,
                "city": record.matched_city,
                "message": record.message,
                "tags": record.tags,
                "fileUrl": record.image_links,
                "videoUrl": record.video_links,
                "description": record.message,
            } for record in telegram_results if record.lat is not None and record.lon is not None
        ]

        return jsonify({
            "message": "Search completed successfully.",
            "results": combined_results
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500