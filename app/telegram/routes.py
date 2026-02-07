#app/telegra/routes.py

from flask import Blueprint, jsonify, request
from app.models import Telegram, db

# Define the blueprint
telegram_bp = Blueprint('telegram', __name__)

# GET route to fetch all TestJson records
@telegram_bp.route('/', methods=['GET'])
def get_testjson():
    # Query all records from the TestJson table
    results = Telegram.query.all()
    return jsonify([{
        "id": record.id,
        "time": record.time,
        "total_views": record.total_views,
        "message": record.message,
        "video_links": record.video_links,
        "image_links": record.image_links,
        "tags": record.tags,
        "subject": record.subject,
        "matched_city": record.matched_city,
        "city_result": record.city_result,
        "lat": record.lat,
        "lon": record.lon
    } for record in results])

# POST route to create a new TestJson record
@telegram_bp.route('/', methods=['POST'])
def create_testjson():
    # Parse JSON request data
    data = request.json
    new_record = Telegram(
        time=data.get('time'),
        total_views=data.get('total_views'),
        message=data.get('message'),
        video_links=data.get('video_links'),
        image_links=data.get('image_links'),
        tags=data.get('tags'),
        subject=data.get('subject'),
        matched_city=data.get('matched_city'),
        city_result=data.get('city_result'),
        lat=data.get('lat'),
        lon=data.get('lon')
    )
    # Add and commit the new record to the database
    db.session.add(new_record)
    db.session.commit()
    return jsonify({'message': 'TestJson record created'}), 201

# GET route for map visualization - returns news data with coordinates
@telegram_bp.route('/news', methods=['GET'])
def get_news_for_map():
    """Fetch news data with locations for map visualization"""
    try:
        # Get limit from query params (default 500)
        limit = request.args.get('limit', default=500, type=int)
        
        # Query records with coordinates, ordered by newest first
        results = Telegram.query.filter(
            Telegram.lat.isnot(None),
            Telegram.lon.isnot(None)
        ).order_by(Telegram.time.desc()).limit(limit).all()
        
        news_data = [{
            "id": record.id,
            "matched_city": record.matched_city,
            "message": record.message,
            "lat": record.lat,
            "lon": record.lon,
            "time": record.time.isoformat() if record.time else None,
            "total_views": record.total_views,
            "video_links": record.video_links,
            "image_links": record.image_links,
            "tags": record.tags,
            "subject": record.subject
        } for record in results]
        
        return jsonify(news_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
