from flask import Blueprint, jsonify, request, send_from_directory, current_app
from datetime import datetime, timezone
from dateutil import parser
from app.models import db, Search, Input, InputTemplate
from app.story.service import list_stories
import traceback
import json
import os

search_bp = Blueprint('search', __name__, url_prefix='/api')


@search_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve files from the uploads directory."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'
    ))
    return send_from_directory(upload_folder, filename)


@search_bp.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()

        user_id = 1  # Hardcoded for now
        term = data.get('term')
        template_ids = data.get('template_ids')
        filters = data.get('filters', {})

        # Validate required fields
        if not term or not isinstance(term, str):
            return jsonify({"error": "Invalid or missing term"}), 400
        if not template_ids or not isinstance(template_ids, list) or len(template_ids) == 0:
            return jsonify({"error": "Invalid or missing template_ids"}), 400

        try:
            filters = json.loads(json.dumps(filters))
        except Exception as e:
            return jsonify({"error": "Invalid filters format", "details": str(e)}), 400

        # --- Audit trail (unchanged) ---
        primary_template_id = template_ids[0]
        new_search = Search(userid=user_id)
        db.session.add(new_search)
        db.session.flush()

        new_input = Input(
            searchid=new_search.searchid,
            keyword=term,
            filters=filters,
            date_input=datetime.now(timezone.utc),
            templateid=primary_template_id,
        )
        db.session.add(new_input)
        db.session.commit()

        # --- Translate template types into story service params ---
        q = None
        from_date = None
        to_date = None
        city = None
        country = None

        for template_id in template_ids:
            template = db.session.get(InputTemplate, template_id)
            if not template:
                continue

            if template.template_type == "Keyword Search":
                # Wildcard '*' means no text filter
                if term and term != '*':
                    q = term

            elif template.template_type == "Date Range Search":
                raw_from = filters.get("from_date")
                raw_to = filters.get("to_date")
                if raw_from:
                    from_date = parser.isoparse(raw_from)
                if raw_to:
                    to_date = parser.isoparse(raw_to)

            elif template.template_type == "Location-Based Search":
                city = filters.get("city") or city
                country = filters.get("country") or country

        # --- Query via story service ---
        result = list_stories(
            source='all',
            q=q,
            city=city,
            country=country,
            has_location=True,
            from_date=from_date,
            to_date=to_date,
            sort='published_at',
            order='desc',
            limit=500,
            offset=0,
        )

        return jsonify({
            "message": "Search completed successfully.",
            "results": result['items'],
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500