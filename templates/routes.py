# app/templates/routes.py
from flask import Blueprint, jsonify, request
from ..models import  InputTemplate, OutputTemplate


templates_bp = Blueprint('templates', __name__)

# app/templates/routes.py
@templates_bp.route('/templates', methods=['GET'])
def get_templates():
    templates = InputTemplate.query.all()
    return jsonify([
        {
            "templateid": template.templateid,
            "template_type": template.template_type,
            "template_description": template.template_description
        }
        for template in templates
    ])

@templates_bp.route('/output_templates', methods=['GET'])
def get_output_templates():
    templates = OutputTemplate.query.all()
    return jsonify([
        {
            "templateid": template.templateid,
            "template_type": template.template_type,
            "description": template.description
        }
        for template in templates
    ])

@templates_bp.route('/generate_output', methods=['POST'])
def generate_output():
    data = request.get_json()
    search_id = data.get("search_id")
    template_id = data.get("template_id")
    filetype_id = data.get("filetype_id")

    # Placeholder response
    output_data = {
        "message": "Output generated successfully",
        "download_link": "http://example.com/download/output_file.zip"
    }
    return jsonify(output_data)

from flask import Blueprint, jsonify, request
from app.models import Telegram, db
import json

# Define the blueprint
telegram_bp = Blueprint('telegram', __name__)

# GET route to fetch all Telegram records
@telegram_bp.route('/', methods=['GET'])
def get_testjson():
    # Query all records from the Telegram table
    results = Telegram.query.all()
    return jsonify([{
        "id": record.id,
        "time": record.time,
        "total_views": record.total_views,
        "message": record.message,
        "video_links": record.video_links,
        "video_durations": record.video_durations,
        "image_links": record.image_links,
        "tags": record.tags,
        "subject": record.subject,
        "matched_city": record.matched_city,
        "city_result": record.city_result,
        "lat": record.lat,
        "lon": record.lon
    } for record in results])

# POST route to upload data from test.json into the Telegram table
from flask import Blueprint, jsonify, request
from app.models import Telegram, db
import json
import traceback

telegram_bp = Blueprint('telegram', __name__)

# POST route to upload data from test.json into the Telegram table
@telegram_bp.route('/upload_json', methods=['POST'])
def upload_json():
    try:
        file_path = '../test.json'  # Adjust to your specific file location if needed
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        records = []
        num_records = len(data['date'])  # Ensure this key exists or adjust as necessary
        for i in range(num_records):
            try:
                record = {
                    'time': data['time'].get(str(i)),  # Change 'time' based on JSON structure
                    'total_views': int(data['total_views'].get(str(i))),
                    'message': data['message'].get(str(i)),
                    'video_links': data['video_links'].get(str(i)),
                    'video_durations': data['video_durations'].get(str(i)),
                    'image_links': data['image_links'].get(str(i)),
                    'tags': data['tags'].get(str(i)),
                    'subject': data['subject'].get(str(i)),
                    'matched_city': data['matched_city'].get(str(i)),
                    'city_result': data['city_result'].get(str(i)),
                    'lat': float(data['latitude'].get(str(i))),
                    'lon': float(data['longitude'].get(str(i)))
                }
                records.append(record)
            except (ValueError, TypeError) as e:
                print(f"Error parsing record at index {i}: {e}")
        
        # Verify the number of parsed records
        print(f"Number of records parsed: {len(records)}")

        # Insert records into the database
        for record in records:
            try:
                new_record = Telegram(
                    time=record['time'],
                    total_views=record['total_views'],
                    message=record['message'],
                    video_links=record['video_links'],
                    video_durations=record['video_durations'],
                    image_links=record['image_links'],
                    tags=record['tags'],
                    subject=record['subject'],
                    matched_city=record['matched_city'],
                    city_result=record['city_result'],
                    lat=record['lat'],
                    lon=record['lon']
                )
                db.session.add(new_record)
                print(f"Added record to session: {new_record}")
            except Exception as e:
                print(f"Error adding record to session: {e}")
                traceback.print_exc()

        try:
            db.session.commit()
            print(f"{len(records)} records committed to the Telegram table")
        except Exception as error:
            db.session.rollback()
            print(f"Error during commit: {error}")
            traceback.print_exc()
    
    except FileNotFoundError:
        print("JSON file not found")
    except json.JSONDecodeError:
        print("Error decoding JSON")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    
    return jsonify({'message': 'Data from test.json uploaded to the Telegram table'}), 201
