"""
Melo Summary Module - Generate professional news summaries from map data
Uses AI to create journalist-style reports from story snapshots
"""
import requests
import os
from flask import Blueprint, jsonify, request
from datetime import datetime
from app.models import Telegram

summary_bp = Blueprint('summary', __name__, url_prefix='/api')

def generate_summary_with_openai(stories_data):
    """
    Generate a professional news summary using OpenAI
    stories_data: list of story objects with title, description, city, etc.
    """
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("DEBUG: OPENAI_API_KEY not found for summary")
            return None
        
        # Format stories for the prompt
        stories_text = "\n".join([
            f"- {story.get('title', 'Untitled')} ({story.get('matched_city', 'Unknown Location')}): {story.get('description', story.get('message', ''))}"
            for story in stories_data
        ])
        
        prompt = f"""You are a professional news editor. Create a neutral, fact-based news summary (maximum 500 words) 
from the following news snapshots from the Israel-Palestine region. Format it as a professional one-page news brief 
with a headline, date, and organized paragraphs covering key locations and events. Be balanced and objective.

STORIES:
{stories_text}

FORMAT:
- Start with a compelling headline
- Include date: {datetime.now().strftime('%B %d, %Y')}
- Organize by location/theme
- Keep tone professional and neutral
- End with a brief outlook

SUMMARY:"""
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            json=payload,
            headers=headers,
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                summary_text = data['choices'][0]['message']['content']
                if summary_text:
                    return {
                        "status": "success",
                        "summary": summary_text,
                        "service": "openai",
                        "generated_at": datetime.now().isoformat()
                    }
        
        print(f"DEBUG: OpenAI summary returned status {response.status_code}")
        return None
            
    except Exception as e:
        print(f"DEBUG: Error generating summary with OpenAI: {e}")
        return None

def generate_summary_with_claude(stories_data):
    """Fallback to Claude for summary generation"""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None
        
        stories_text = "\n".join([
            f"- {story.get('title', 'Untitled')} ({story.get('matched_city', 'Unknown Location')}): {story.get('description', story.get('message', ''))}"
            for story in stories_data
        ])
        
        prompt = f"""You are a professional news editor. Create a neutral, fact-based news summary (maximum 500 words) 
from the following news snapshots from the Israel-Palestine region. Format it as a professional one-page news brief 
with a headline, date, and organized paragraphs covering key locations and events. Be balanced and objective.

STORIES:
{stories_text}

FORMAT:
- Start with a compelling headline
- Include date: {datetime.now().strftime('%B %d, %Y')}
- Organize by location/theme
- Keep tone professional and neutral
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

@summary_bp.route('/generate-melo-summary', methods=['POST'])
def generate_melo_summary():
    """
    Generate a professional news summary from selected stories
    Expected JSON options:
    1. { "stories": [list of story objects] }          - Custom stories list
    2. { "story_ids": [1, 2, 3...] }                   - By story IDs
    3. { "search": "keyword", "limit": 50 }            - By search query
    4. {}                                               - All stories (50 latest)
    """
    try:
        print("DEBUG: generate_melo_summary called")
        data = request.get_json() or {}
        print(f"DEBUG: Received data: {data}")
        stories = data.get('stories', [])
        
        # Option 1: Custom stories provided
        if stories:
            print(f"DEBUG: Using {len(stories)} custom stories from request")
        
        # Option 2: Story IDs provided (visible on map)
        elif data.get('story_ids'):
            print(f"DEBUG: Fetching stories by IDs: {data.get('story_ids')}")
            try:
                story_ids = data.get('story_ids', [])
                telegram_stories = Telegram.query.filter(Telegram.id.in_(story_ids)).all()
                print(f"DEBUG: Found {len(telegram_stories)} stories by ID")
                stories = [
                    {
                        'title': s.subject or 'Untitled',
                        'description': s.message or '',
                        'matched_city': s.matched_city or s.city_result or 'Unknown',
                        'lat': s.lat,
                        'lon': s.lon,
                        'time': s.time.isoformat() if s.time else None,
                        'views': s.total_views or 0
                    }
                    for s in telegram_stories
                ]
            except Exception as db_error:
                print(f"DEBUG: Error fetching by IDs: {db_error}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to fetch stories: {str(db_error)}"
                }), 500
        
        # Option 3: Search query provided
        elif data.get('search'):
            print(f"DEBUG: Searching for: {data.get('search')}")
            try:
                search_term = f"%{data.get('search')}%"
                limit = data.get('limit', 50)
                telegram_stories = Telegram.query.filter(
                    (Telegram.message.ilike(search_term)) |
                    (Telegram.subject.ilike(search_term)) |
                    (Telegram.matched_city.ilike(search_term))
                ).order_by(Telegram.time.desc()).limit(limit).all()
                print(f"DEBUG: Search found {len(telegram_stories)} stories")
                stories = [
                    {
                        'title': s.subject or 'Untitled',
                        'description': s.message or '',
                        'matched_city': s.matched_city or s.city_result or 'Unknown',
                        'lat': s.lat,
                        'lon': s.lon,
                        'time': s.time.isoformat() if s.time else None,
                        'views': s.total_views or 0
                    }
                    for s in telegram_stories
                ]
            except Exception as db_error:
                print(f"DEBUG: Search error: {db_error}")
                return jsonify({
                    "error": "Search error",
                    "message": f"Failed to search stories: {str(db_error)}"
                }), 500
        
        # Option 4: No filter, fetch all latest
        else:
            print("DEBUG: No filter, fetching latest 50 stories")
            try:
                telegram_stories = Telegram.query.order_by(Telegram.time.desc()).limit(50).all()
                print(f"DEBUG: Found {len(telegram_stories)} stories in database")
                stories = [
                    {
                        'title': s.subject or 'Untitled',
                        'description': s.message or '',
                        'matched_city': s.matched_city or s.city_result or 'Unknown',
                        'lat': s.lat,
                        'lon': s.lon,
                        'time': s.time.isoformat() if s.time else None,
                        'views': s.total_views or 0
                    }
                    for s in telegram_stories
                ]
            except Exception as db_error:
                print(f"DEBUG: Database error: {db_error}")
                return jsonify({
                    "error": "Database error",
                    "message": f"Failed to fetch stories: {str(db_error)}"
                }), 500
        
        if not stories:
            print("DEBUG: No stories available")
            return jsonify({
                "error": "No stories available",
                "message": "Please add some news stories first or check your filters"
            }), 400
        
        print(f"DEBUG: Generating summary for {len(stories)} stories")
        
        # Try OpenAI first, fallback to Claude
        summary_result = generate_summary_with_openai(stories)
        
        if not summary_result:
            print("DEBUG: OpenAI failed, trying Claude...")
            summary_result = generate_summary_with_claude(stories)
        
        if not summary_result:
            print("DEBUG: All AI services failed")
            return jsonify({
                "error": "Summary generation failed",
                "message": "Unable to generate summary. Check API keys are configured."
            }), 500
        
        return jsonify({
            "status": "success",
            "summary": summary_result.get('summary'),
            "service": summary_result.get('service'),
            "generated_at": summary_result.get('generated_at'),
            "stories_count": len(stories)
        }), 200
        
    except Exception as e:
        print(f"ERROR in generate_melo_summary: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@summary_bp.route('/summary-metadata', methods=['GET'])
def get_summary_metadata():
    """Get metadata about available stories for summary generation"""
    try:
        story_count = Telegram.query.count()
        latest_story = Telegram.query.order_by(Telegram.time.desc()).first()
        
        cities = Telegram.query.with_entities(Telegram.matched_city).distinct().count()
        
        return jsonify({
            "total_stories": story_count,
            "unique_cities": cities,
            "latest_story_date": latest_story.time.isoformat() if latest_story and latest_story.time else None,
            "ready_for_summary": story_count > 0
        }), 200
        
    except Exception as e:
        print(f"ERROR in get_summary_metadata: {e}")
        return jsonify({
            "error": "Failed to get metadata",
            "details": str(e)
        }), 500
