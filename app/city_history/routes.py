import requests
import os
from flask import Blueprint, jsonify, request
from functools import lru_cache
import json

city_history_bp = Blueprint('city_history', __name__, url_prefix='/api')

# In-memory cache for city histories (max 100 entries)
HISTORY_CACHE = {}

# Israel/Palestine region bounds (roughly)
REGION_BOUNDS = {
    'min_lat': 31.2,
    'max_lat': 33.3,
    'min_lon': 34.2,
    'max_lon': 35.9
}

def is_in_region(lat, lon):
    """Check if coordinates are in Israel/Palestine region"""
    return (REGION_BOUNDS['min_lat'] <= lat <= REGION_BOUNDS['max_lat'] and
            REGION_BOUNDS['min_lon'] <= lon <= REGION_BOUNDS['max_lon'])

def get_city_name_from_coords(lat, lon):
    """Use reverse geocoding to get city name from coordinates"""
    try:
        # Using OpenCage API which you already have configured
        geocoder_api_key = '0bc1962b58b7482ebe0507debae9a885'
        url = f'https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={geocoder_api_key}'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                return data['results'][0].get('formatted', 'Unknown Location')
        return None
    except Exception as e:
        print(f"Error reverse geocoding: {e}")
        return None

def generate_history_with_openai(city_name, lat, lon):
    """
    Generate city history using Thaura AI (PRIMARY)
    Requires THAURA_API_KEY environment variable
    """
    try:
        api_key = os.getenv('THAURA_API_KEY')
        api_base = os.getenv('THAURA_API_BASE', 'https://backend.thaura.ai/v1')
        model = os.getenv('THAURA_DEFAULT_MODEL', 'thaura')
        
        if not api_key:
            print("DEBUG: THAURA_API_KEY not found")
            return None
        
        print(f"DEBUG: Using Thaura AI for history (key found: {len(api_key)} chars)")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Provide a brief historical overview (2-3 sentences) of {city_name} in the Israel-Palestine region at coordinates {lat}, {lon}. 
        Focus on key historical events, cultural significance, and current status. Be factual and balanced."""
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': float(os.getenv('THAURA_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('THAURA_MAX_TOKENS', '2048'))
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
                history_text = data['choices'][0]['message']['content']
                if history_text:
                    return {
                        "status": "success",
                        "history": history_text,
                        "city": city_name,
                        "service": "thaura"
                    }
        
        print(f"DEBUG: Thaura AI returned status {response.status_code}: {response.text[:200]}")
        return None
            
    except Exception as e:
        print(f"DEBUG: Error with Thaura AI: {e}")
        return None

def generate_history_with_thaurae(city_name, lat, lon):
    """
    Generate city history using Thaura.ai API (SECONDARY)
    Requires THAURA_AI_API_KEY environment variable
    """
    try:
        api_key = os.getenv('THAURA_AI_API_KEY')
        if not api_key:
            return {
                "error": "Thaura.ai not configured",
                "fallback": f"History not available for {city_name}. Coordinates: {lat}, {lon}"
            }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Provide a brief historical overview (2-3 sentences) of {city_name} in the Israel-Palestine region at coordinates {lat}, {lon}. 
        Focus on key historical events, cultural significance, and current status. Be factual and balanced."""
        
        payload = {
            'model': 'default',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 300
        }
        
        response = requests.post(
            'https://thaura.ai/api/v1/chat/completions',
            json=payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                history_text = data['choices'][0].get('message', {}).get('content', '')
                if history_text:
                    return {
                        "status": "success",
                        "history": history_text,
                        "city": city_name,
                        "service": "thaurae"
                    }
        
        return None
            
    except Exception as e:
        print(f"Error generating history with Thaura.ai: {e}")
        return None

def generate_history_with_claude(city_name, lat, lon):
    """
    Generate city history using Claude AI (via Anthropic API)
    Fallback if Thaura.ai is not available
    """
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        prompt = f"""Provide a brief historical overview (2-3 sentences) of {city_name} in the Israel-Palestine region at coordinates {lat}, {lon}. 
        Focus on key historical events, cultural significance, and current status. Be factual and balanced."""
        
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 300,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            history_text = data['content'][0]['text']
            return {
                "status": "success",
                "history": history_text,
                "city": city_name,
                "service": "claude"
            }
        
        return None
            
    except Exception as e:
        print(f"Error generating history with Claude: {e}")
        return None

@city_history_bp.route('/city-history', methods=['POST'])
def get_city_history():
    """
    Get history of a city based on lat/lon coordinates
    Uses Thaura AI only - requires THAURA_API_KEY environment variable
    
    Expected JSON: { "lat": 31.9, "lon": 35.2, "city": "Jerusalem" (optional) }
    """
    try:
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        city_name = data.get('city', 'Unknown')
        
        # Validate region
        if not is_in_region(lat, lon):
            return jsonify({
                "error": "Location is outside Israel-Palestine region",
                "message": f"Coordinates {lat}, {lon} are outside the configured region"
            }), 400
        
        # Check cache first
        cache_key = f"{lat:.4f},{lon:.4f}"
        if cache_key in HISTORY_CACHE:
            print(f"Cache hit for {cache_key}")
            return jsonify(HISTORY_CACHE[cache_key]), 200
        
        # If city name not provided, reverse geocode
        if city_name == 'Unknown':
            city_name = get_city_name_from_coords(lat, lon)
            if not city_name:
                city_name = f"Location ({lat:.4f}, {lon:.4f})"
        
        # Use Thaura AI only
        history_data = generate_history_with_openai(city_name, lat, lon)
        
        if not history_data:
            print("Thaura AI history generation failed")
            history_data = {
                "error": "AI service unavailable",
                "message": "Unable to generate history. Check that THAURA_API_KEY is configured."
            }
        
        # Cache the result
        HISTORY_CACHE[cache_key] = history_data
        
        # Limit cache size
        if len(HISTORY_CACHE) > 100:
            # Remove oldest entry (simple approach)
            HISTORY_CACHE.pop(next(iter(HISTORY_CACHE)))
        
        return jsonify(history_data), 200
        
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400
    except Exception as e:
        print(f"Error in city_history endpoint: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

