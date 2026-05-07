"""
Melo Summary Module - Generate professional news summaries from map data
Uses AI to create journalist-style reports from story snapshots
"""
import requests
import os
import json
from flask import Blueprint, jsonify, request
from datetime import datetime
from app.models import db, Telegram, FileUpload
from app.story.service import list_stories, get_story

summary_bp = Blueprint('summary', __name__, url_prefix='/api')

def safe_json_parse(value):
    """Safely parse JSON field, return empty list on error"""
    if not value or value == 'null' or value == '':
        return []
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []

def generate_summary_with_thaura(stories_data):
    """
    Generate a professional news summary using Thaura AI
    stories_data: list of story objects with title, description, city, etc.
    """
    try:
        # Use Thaura AI instead of OpenAI
        api_key = os.getenv('THAURA_API_KEY')
        api_base = os.getenv('THAURA_API_BASE', 'https://backend.thaura.ai/v1')
        model = os.getenv('THAURA_DEFAULT_MODEL', 'thaura')
        
        if not api_key:
            print("DEBUG: THAURA_API_KEY not found, using mock summary for testing")
            return {
                'summary': 'Mock summary: Recent developments in Gaza include heavy fighting in the city center, humanitarian aid arriving in Rafah, and peace talks resuming in Cairo. These events highlight the ongoing conflict and diplomatic efforts in the region.',
                'service': 'Mock Thaura AI',
                'generated_at': datetime.now().isoformat(),
            }
        # Format stories for the prompt with media links
        stories_text = ""
        for story in stories_data:
            story_text = f"- {story.get('title', 'Untitled')} ({story.get('matched_city', 'Unknown Location')}): {story.get('description', story.get('message', ''))}"
            
            # Add video links - labeled as "Video" instead of full URL
            videos = story.get('video_links', [])
            if videos:
                video_list = ", ".join([f"[Video]({v})" for v in videos])
                story_text += f"\n  Videos: {video_list}"
            
            # Add image links - labeled as "Image" instead of full URL
            images = story.get('image_links', [])
            if images:
                image_list = ", ".join([f"[Image]({img})" for img in images])
                story_text += f"\n  Images: {image_list}"
            
            stories_text += story_text + "\n"
        
        prompt = f"""You are a professional news editor. Create a neutral, fact-based news summary (maximum 500 words) 
from the following news snapshots from the Israel-Palestine region. Format it as a professional one-page news brief 
with a headline, date, and organized paragraphs covering key locations and events. Be balanced and objective.

IMPORTANT: Include hyperlinks to videos and images using ONLY the word "Video" or "Image" as the link text in markdown format.
Example: "footage shows [Video](url)" NOT "footage shows [Video 1](url)"

STORIES:
{stories_text}

FORMAT:
- Start with a compelling headline
- Include date: {datetime.now().strftime('%B %d, %Y')}
- Organize by location/theme
- Keep tone professional and neutral
- Include media links inline using only "Video" or "Image" as link text
- End with a brief outlook

SUMMARY:"""
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': float(os.getenv('THAURA_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('THAURA_MAX_TOKENS', '4096'))
        }
        
        response = requests.post(
            f'{api_base}/chat/completions',
            json=payload,
            headers=headers,
            timeout=int(os.getenv('THAURA_REQUEST_TIMEOUT', '30'))
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                msg = data['choices'][0].get('message', {})
                summary_text = msg.get('content', '')
                # Thaura reasoning models may put output in 'reasoning' with empty 'content'
                if not summary_text:
                    summary_text = msg.get('reasoning', '')
                if summary_text:
                    return {
                        "status": "success",
                        "summary": summary_text,
                        "service": "thaura",
                        "generated_at": datetime.now().isoformat()
                    }
        
        print(f"DEBUG: Thaura AI summary returned status {response.status_code}")
        return None
            
    except Exception as e:
        print(f"DEBUG: Error generating summary with Thaura AI: {e}")
        return None

def generate_summary_with_claude(stories_data):
    """Fallback to Claude for summary generation"""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None
        
        # Format stories for the prompt with media links
        stories_text = ""
        for story in stories_data:
            story_text = f"- {story.get('title', 'Untitled')} ({story.get('matched_city', 'Unknown Location')}): {story.get('description', story.get('message', ''))}"
            
            # Add video links - labeled as "Video" instead of full URL
            videos = story.get('video_links', [])
            if videos:
                video_list = ", ".join([f"[Video]({v})" for v in videos])
                story_text += f"\n  Videos: {video_list}"
            
            # Add image links - labeled as "Image" instead of full URL
            images = story.get('image_links', [])
            if images:
                image_list = ", ".join([f"[Image]({img})" for img in images])
                story_text += f"\n  Images: {image_list}"
            
            stories_text += story_text + "\n"
        
        prompt = f"""You are a professional news editor. Create a neutral, fact-based news summary (maximum 500 words) 
from the following news snapshots from the Israel-Palestine region. Format it as a professional one-page news brief 
with a headline, date, and organized paragraphs covering key locations and events. Be balanced and objective.

IMPORTANT: Include hyperlinks to videos and images using ONLY the word "Video" or "Image" as the link text in markdown format.
Example: "footage shows [Video](url)" NOT "footage shows [Video 1](url)"

STORIES:
{stories_text}

FORMAT:
- Start with a compelling headline
- Include date: {datetime.now().strftime('%B %d, %Y')}
- Organize by location/theme
- Keep tone professional and neutral
- Include media links inline using only "Video" or "Image" as link text
- End with a brief outlook

SUMMARY:"""
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 1000,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            json=payload,
            headers=headers,
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "summary": data['content'][0]['text'],
                "service": "claude",
                "generated_at": datetime.now().isoformat()
            }
        
        return None
            
    except Exception as e:
        print(f"DEBUG: Error generating summary with Claude: {e}")
        return None

def _story_for_prompt(story):
    """Adapt a normalized Story dict to the shape expected by the AI prompt builders."""
    return {
        'title': story['title'],
        'description': story['body'],
        'matched_city': (
            story['location']['city']
            or story['location']['country']
            or 'Unknown'
        ),
        'lat': story['location']['lat'],
        'lon': story['location']['lon'],
        'time': story['timestamps']['published_at'],
        'views': story['metrics']['total_views'] or 0,
        'video_links': story['media']['videos'],
        'image_links': story['media']['images'],
    }


@summary_bp.route('/generate-melo-summary', methods=['POST'])
def generate_melo_summary():
    """
    Generate a professional news summary from selected stories.

    Accepted JSON options:
    1. { "stories": [...] }                     — custom story objects (passed through)
    2. { "story_ids": ["telegram:1", ...] }     — by prefixed story IDs
    3. { "story_ids": [1, 2, ...] }             — legacy: bare ints treated as telegram IDs
    4. { "search": "keyword", "limit": 50 }     — by search query
    5. {}                                        — 50 latest stories from all sources
    """
    try:
        data = request.get_json() or {}
        stories = data.get('stories', [])

        # Option 1: custom story objects provided directly
        if stories:
            print(f"DEBUG: Using {len(stories)} custom stories from request")

        # Option 2 / 3: story IDs
        elif data.get('story_ids'):
            raw_ids = data['story_ids']
            print(f"DEBUG: Fetching stories by IDs: {raw_ids}")
            fetched = []
            for raw_id in raw_ids:
                if isinstance(raw_id, str) and ':' in raw_id:
                    source_type, _, record_id = raw_id.partition(':')
                    story = get_story(source_type, int(record_id))
                else:
                    # Legacy: bare integer → assume telegram
                    story = get_story('telegram', int(raw_id))
                if story:
                    fetched.append(_story_for_prompt(story))
            stories = fetched
            print(f"DEBUG: Found {len(stories)} stories by ID")

        # Option 4: keyword search
        elif data.get('search'):
            q = data['search']
            limit = data.get('limit', 50)
            print(f"DEBUG: Searching for: {q}")
            result = list_stories(source='all', q=q, sort='published_at', order='desc', limit=limit)
            stories = [_story_for_prompt(s) for s in result['items']]
            print(f"DEBUG: Search found {len(stories)} stories")

        # Option 5: latest from all sources
        else:
            print("DEBUG: No filter, fetching latest 50 stories")
            result = list_stories(source='all', sort='published_at', order='desc', limit=50)
            stories = [_story_for_prompt(s) for s in result['items']]
            print(f"DEBUG: Found {len(stories)} stories")

        if not stories:
            return jsonify({
                "error": "No stories available",
                "message": "Please add some news stories first or check your filters",
            }), 400

        print(f"DEBUG: Generating summary for {len(stories)} stories")

        summary_result = generate_summary_with_thaura(stories)

        if not summary_result:
            return jsonify({
                "error": "Summary generation failed",
                "message": "Unable to generate summary. Check that THAURA_API_KEY is configured.",
            }), 500

        return jsonify({
            "status": "success",
            "summary": summary_result.get('summary'),
            "service": summary_result.get('service'),
            "generated_at": summary_result.get('generated_at'),
            "stories_count": len(stories),
        }), 200

    except Exception as e:
        print(f"ERROR in generate_melo_summary: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@summary_bp.route('/summary-metadata', methods=['GET'])
def get_summary_metadata():
    """Get metadata about available stories for summary generation."""
    try:
        telegram_count = db.session.query(Telegram.id).count()
        upload_count = db.session.query(FileUpload.id).count()
        total = telegram_count + upload_count

        latest_telegram = Telegram.query.order_by(Telegram.time.desc()).first()
        latest_upload = FileUpload.query.order_by(FileUpload.upload_date.desc()).first()

        # Pick the most recent across both sources
        candidates = [
            latest_telegram.time if latest_telegram and latest_telegram.time else None,
            latest_upload.upload_date if latest_upload and latest_upload.upload_date else None,
        ]
        latest_date = max((d for d in candidates if d), default=None)

        unique_cities = (
            db.session.query(Telegram.matched_city).distinct().count()
            + db.session.query(FileUpload.city).filter(FileUpload.city.isnot(None)).distinct().count()
        )

        return jsonify({
            "total_stories": total,
            "telegram_count": telegram_count,
            "upload_count": upload_count,
            "unique_cities": unique_cities,
            "latest_story_date": latest_date.isoformat() if latest_date else None,
            "ready_for_summary": total > 0,
        }), 200

    except Exception as e:
        print(f"ERROR in get_summary_metadata: {e}")
        return jsonify({"error": "Failed to get metadata", "details": str(e)}), 500
