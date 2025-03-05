import logging
from flask import Blueprint, jsonify, request
from app.models import Telegram, db
import json
from datetime import datetime
import os
from sqlalchemy.exc import SQLAlchemyError

telegram_bp = Blueprint('telegram', __name__)

def load_telegram_data(file_path):
    """Reusable function to load and insert Telegram data from JSON"""
    print(f"\n🔹 Checking for Telegram JSON file at: {file_path}")

    if not os.path.exists(file_path):
        print(f"\n❌ Telegram JSON file not found at: {file_path}")
        return {"error": f"File not found at: {file_path}"}, 400

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        print(f"\n✅ JSON Data Loaded Successfully. Number of records: {len(data)}")

        if not isinstance(data, list):
            print("\n❌ Invalid JSON format: Expected a list of objects")
            return {"error": "Invalid JSON format"}, 400

        records_to_add = []
        for index, item in enumerate(data):
            print(f"\n🔹 Processing Record #{index + 1}: {item}")

            try:
                # Handle missing values
                date_str = item.get('date', '2024-01-01')  # Default if missing
                time_str = item.get('time', '00:00:00')  # Default if missing
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

                # Convert lat/lon safely
                lat = float(item.get('latitude', 0.0) or 0.0)
                lon = float(item.get('longitude', 0.0) or 0.0)

                # Create Telegram record
                record = Telegram(
                    time=dt,
                    total_views=0,
                    message=item.get('message', 'No message'),
                    video_links=item.get('video'),
                    video_durations=item.get('video_durations'),
                    image_links=item.get('image_links'),
                    tags=item.get('tags'),
                    subject=item.get('title', 'No title'),
                    matched_city=item.get('city'),
                    city_result=None,
                    lat=lat,
                    lon=lon,
                    summary=item.get('summary')
                )

                records_to_add.append(record)

            except Exception as e:
                print(f"\n⚠️ Error processing record #{index + 1}: {str(e)}")
                continue  # Skip faulty records

        # Debugging: Confirm if records are being added
        print(f"\n🔹 Total Records Ready to Insert: {len(records_to_add)}")

        if records_to_add:
            try:
                db.session.add_all(records_to_add)
                print("\n🔹 Attempting to commit data...")
                db.session.commit()
                print("\n✅ Data committed successfully!")
                return {"message": "Data uploaded successfully"}, 201
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Database commit error: {e}")
                return {"error": f"Database commit error: {str(e)}"}, 500

    except SQLAlchemyError as e:
        print(f"\n❌ Database error: {e}")
        db.session.rollback()
        return {"error": f"Database error: {str(e)}"}, 500

    except json.JSONDecodeError as e:
        print(f"\n❌ JSON decoding error: {e}")
        return {"error": f"JSON decoding error: {str(e)}"}, 400

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        db.session.rollback()
        return {"error": f"Unexpected error: {str(e)}"}, 500


@telegram_bp.route('/upload_json', methods=['POST'])
def upload_json():
    """Manually trigger Telegram JSON upload via API"""
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../test_with_lat_lon.json'))
    response, status_code = load_telegram_data(file_path)
    return jsonify(response), status_code
