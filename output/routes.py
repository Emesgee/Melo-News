# app/output/routes.py
from flask import Blueprint, jsonify, request, send_file, current_app
from datetime import datetime
from sqlalchemy import or_ 
from app.models import db, Search, OutputTemplate, FileUpload, Output, Input
import csv
import os

output_bp = Blueprint('output', __name__, url_prefix='/output')

# Date parsing function to format dates for PostgreSQL
def parse_datetime(date_str):
    try:
        # Parses date in format "YYYY HH:MM:SS" and reformats to "YYYY-MM-DD HH:MM:SS"
        parsed_date = datetime.strptime(date_str, "%Y %H:%M:%S")
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

@output_bp.route('/generate_output', methods=['POST'])
def generate_output():
    data = request.get_json()
    search_id = data.get('search_id')
    template_id = data.get('template_id')
    filetype_id = data.get('filetype_id', None)

    current_app.logger.info(f"Received search_id: {search_id}, template_id: {template_id}")

    # Validate search and template IDs
    search = Search.query.get(search_id)
    if not search:
        current_app.logger.error("Invalid search ID")
        return jsonify({"error": "Invalid search ID"}), 400

    template = OutputTemplate.query.get(template_id)
    if not template:
        current_app.logger.error("Invalid output template ID")
        return jsonify({"error": "Invalid output template ID"}), 400

    # Retrieve search criteria from the Input associated with this search
    input_record = Input.query.filter_by(searchid=search_id).first()
    if not input_record:
        current_app.logger.info("No input record found for the specified search.")
        return jsonify({"message": "No input record found for the specified search"}), 200

    # Use the keyword and filters from the Input record to query FileUpload
    keyword = input_record.keyword
    filters = input_record.filters

    # Construct query based on search criteria
    query = FileUpload.query
    if keyword:
        query = query.filter(or_(
            FileUpload.filename.ilike(f'%{keyword}%'),
            FileUpload.title.ilike(f'%{keyword}%'),
            FileUpload.tags.ilike(f'%{keyword}%'),
            FileUpload.subject.ilike(f'%{keyword}%')
        ))

    # Parse and apply date filters
    upload_date_start = parse_datetime(filters.get("from_date", ""))
    upload_date_end = parse_datetime(filters.get("to_date", ""))
    if upload_date_start and upload_date_end:
        query = query.filter(
            FileUpload.upload_date >= upload_date_start,
            FileUpload.upload_date <= upload_date_end
        )
    elif upload_date_start or upload_date_end:
        current_app.logger.error("Invalid datetime format")
        return jsonify({"error": "Invalid datetime format"}), 400

    # Apply other filters
    if filters.get("city"):
        query = query.filter(FileUpload.city.ilike(f'%{filters["city"]}%'))
    if filters.get("country"):
        query = query.filter(FileUpload.country.ilike(f'%{filters["country"]}%'))

    results = query.all()
    current_app.logger.info(f"Number of results found: {len(results)}")

    if not results:
        current_app.logger.info("No data available to generate output.")
        return jsonify({"message": "No data found for the given search criteria"}), 200

    # Prepare data based on output template
    output_data = []
    if template.template_type == "Summary View":
        output_data = [{"filename": file.filename, "upload_date": file.upload_date} for file in results]
    elif template.template_type == "Detailed View":
        output_data = [{
            "filename": file.filename, "tags": file.tags, "subject": file.subject, 
            "city": file.city, "country": file.country, "upload_date": file.upload_date, 
            "lat": file.lat, "lon": file.lon
        } for file in results]
    elif template.template_type == "Location Map View":
        output_data = [{"city": file.city, "country": file.country, "lat": file.lat, "lon": file.lon} for file in results]
    elif template.template_type == "CSV Export":
        output_data = [{
            "filename": file.filename, "tags": file.tags, "subject": file.subject, 
            "city": file.city, "country": file.country, "upload_date": file.upload_date, 
            "lat": file.lat, "lon": file.lon
        } for file in results]

        # Generate CSV file
        filename = f"output_{search_id}_{template.template_type}.csv".replace(" ", "_")
        file_path = os.path.join(current_app.config['EXPORT_DIR'], filename)
        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=output_data[0].keys())
                writer.writeheader()
                writer.writerows(output_data)
            return send_file(file_path, as_attachment=True, download_name=filename)
        except Exception as e:
            current_app.logger.error(f"Error creating CSV: {e}")
            return jsonify({"error": "Failed to generate CSV output"}), 500

    # Save output to Outputs table if data is not empty
    new_output = Output(
        searchid=search_id,
        filetypeid=filetype_id,
        templateid=template_id,
        date_generated=datetime.utcnow()
    )
    db.session.add(new_output)
    db.session.commit()

    return jsonify({
        "message": "Output generated successfully",
        "output_id": new_output.outputid,
        "data": output_data  # Return for non-CSV views
    }), 200
