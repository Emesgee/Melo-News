from flask import Blueprint, jsonify, request
from app.models import TestJson, db

# Define the blueprint
testjson_bp = Blueprint('testjson', __name__)

# GET route to fetch all TestJson records
@testjson_bp.route('/', methods=['GET'])
def get_testjson():
    # Query all records from the TestJson table
    results = TestJson.query.all()
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
        "latitude": record.latitude,
        "longitude": record.longitude
    } for record in results])

# POST route to create a new TestJson record
@testjson_bp.route('/', methods=['POST'])
def create_testjson():
    # Parse JSON request data
    data = request.json
    new_record = TestJson(
        time=data.get('time'),
        total_views=data.get('total_views'),
        message=data.get('message'),
        video_links=data.get('video_links'),
        video_durations=data.get('video_durations'),
        image_links=data.get('image_links'),
        tags=data.get('tags'),
        subject=data.get('subject'),
        matched_city=data.get('matched_city'),
        city_result=data.get('city_result'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    # Add and commit the new record to the database
    db.session.add(new_record)
    db.session.commit()
    return jsonify({'message': 'TestJson record created'}), 201
