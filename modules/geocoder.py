import json
import os
import requests
from fuzzywuzzy import fuzz

geocode_cache = {}
geojson_coords = {}
CACHE_FILE = "geocode_cache.json"

# Generic locations fallback (for broad area references) - with high precision (5+ decimals)
GENERIC_LOCATIONS = {
    'gaza': {'lat': 31.50000, 'lon': 34.50000, 'name': 'Gaza'},
    'gaza strip': {'lat': 31.50000, 'lon': 34.50000, 'name': 'Gaza'},
    'west bank': {'lat': 31.95000, 'lon': 35.20000, 'name': 'West Bank'},
    'occupied territories': {'lat': 31.95000, 'lon': 35.00000, 'name': 'Occupied Territories'},
}

def load_cache():
    """Load geocode cache from file"""
    global geocode_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                geocode_cache = json.load(f)
                print(f"[CACHE] Loaded {len(geocode_cache)} cached coordinates")
        except Exception as e:
            print(f"[CACHE ERROR] {e}")

def save_cache():
    """Save geocode cache to file"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(geocode_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CACHE SAVE ERROR] {e}")

def load_geojson_coordinates():
    """Load coordinates from palestinians_towns.geojson"""
    global geojson_coords
    coords = {}
    
    try:
        geojson_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns.geojson')
        
        if os.path.exists(geojson_path):
            with open(geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    coords_geom = geometry.get('coordinates', [])
                    if len(coords_geom) != 2:
                        continue
                    
                    lon, lat = coords_geom
                    town_name = props.get('town_name', '').strip().lower()
                    
                    if town_name:
                        coords[town_name] = {
                            'lat': lat,
                            'lon': lon,
                            'district': props.get('district', ''),
                            'type': props.get('type', ''),
                            'arabic_name': props.get('arabic_name', '')
                        }
                
                geojson_coords = coords
                print(f"[GEOCODER] Loaded {len(coords)} locations from GeoJSON")
        else:
            print(f"[GEOCODER WARNING] GeoJSON not found: {geojson_path}")
    except Exception as e:
        print(f"[GEOCODER ERROR] {e}")
    
    return coords

def geocode_with_fuzzy(text):
    """Use fuzzy matching to find location in text"""
    if not text or len(text) < 5:
        return None, None, None
    
    text_lower = text.lower()
    best_match = None
    best_score = 0
    
    # Try to match against all known locations
    for location, data in geojson_coords.items():
        score = fuzz.token_sort_ratio(text_lower, location)
        
        if score > best_score:
            best_score = score
            best_match = (location, data)
    
    # Only return if score is high enough
    if best_score >= 85 and best_match:
        location, data = best_match
        print(f"[FUZZY MATCH] Score {best_score}% -> '{location}'")
        return location, data['lat'], data['lon']
    
    return None, None, None

def geocode_city(city_name):
    """Geocode a city using GeoJSON, cache, fuzzy matching, and generic locations"""
    if not city_name:
        return None
    
    city_name_lower = city_name.lower().strip()
    
    # Strategy 1: Direct GeoJSON lookup
    if city_name_lower in geojson_coords:
        data = geojson_coords[city_name_lower]
        result = {
            "lat": data['lat'],
            "lon": data['lon'],
            "city": city_name_lower,
            "district": data['district']
        }
        print(f"[GEOCODE GEOJSON] {city_name} -> ({data['lat']}, {data['lon']})")
        return result
    
    # Strategy 2: Check generic locations (Gaza, West Bank, etc.)
    if city_name_lower in GENERIC_LOCATIONS:
        generic_data = GENERIC_LOCATIONS[city_name_lower]
        result = {
            "lat": generic_data['lat'],
            "lon": generic_data['lon'],
            "city": generic_data['name'],
            "district": generic_data['name']
        }
        print(f"[GEOCODE GENERIC] {city_name} -> ({generic_data['lat']}, {generic_data['lon']})")
        return result
    
    # Strategy 3: Check cache
    if city_name_lower in geocode_cache:
        cached = geocode_cache[city_name_lower]
        # Cache might have list format, convert if needed
        if isinstance(cached, list):
            return {"lat": cached[0], "lon": cached[1], "city": city_name_lower, "district": "Unknown"}
        return cached
    
    # Strategy 4: Try fuzzy matching
    location_name, lat, lon = geocode_with_fuzzy(city_name)
    if location_name:
        result = {
            "lat": lat,
            "lon": lon,
            "city": location_name,
            "district": geojson_coords[location_name]['district']
        }
        geocode_cache[city_name_lower] = result
        save_cache()
        return result
    
    # Strategy 5: Try Nominatim
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': f'{city_name}, Palestine', 'format': 'json'},
            timeout=5,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200 and response.json():
            data = response.json()[0]
            result = {
                "lat": float(data['lat']),
                "lon": float(data['lon']),
                "city": city_name,
                "district": "Unknown"
            }
            geocode_cache[city_name_lower] = result
            save_cache()
            print(f"[GEOCODE NOMINATIM] {city_name} -> ({result['lat']}, {result['lon']})")
            return result
    except Exception as e:
        print(f"[NOMINATIM ERROR] {city_name}: {e}")
    
    print(f"[GEOCODE FAILED] {city_name}")
    return None

# Load on module import
load_cache()
load_geojson_coordinates()
