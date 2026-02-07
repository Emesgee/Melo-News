import json
import spacy
from modules.geocoder import load_geojson_coordinates, geocode_with_fuzzy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[WARNING] spacy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

# Load Palestinian locations from GeoJSON on startup
geojson_coords = load_geojson_coordinates()

# Generic locations fallback (for broad area references) - with high precision (5+ decimals)
GENERIC_LOCATIONS = {
    'gaza': {'lat': 31.50000, 'lon': 34.50000, 'name': 'Gaza'},
    'gaza strip': {'lat': 31.50000, 'lon': 34.50000, 'name': 'Gaza'},
    'west bank': {'lat': 31.95000, 'lon': 35.20000, 'name': 'West Bank'},
    'occupied territories': {'lat': 31.95000, 'lon': 35.00000, 'name': 'Occupied Territories'},
}

def detect_location_with_thaura(text: str):
    """Use Thaura AI to extract location from text"""
    if not THAURA_API_KEY:
        return None
    
    for attempt in range(2):
        try:
            headers = {
                'Authorization': f'Bearer {THAURA_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            prompt = f"""Extract location from this news text.

Examples:
Text: "In Berlin, protesters marched for Gaza"
Answer: Gaza

Text: "Israeli settlers attack village of Deir Sharaf near Nablus"  
Answer: Deir Sharaf

Text: "Violence in the occupied West Bank continues"
Answer: West Bank

Text: {text}
Answer:"""
            
            payload = {
                'model': THAURA_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Extract the Palestinian location mentioned. Reply with location name only, no explanation.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.0,
                'max_tokens': 30
            }
            
            response = requests.post(
                f'{THAURA_API_BASE}/chat/completions',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    message = data['choices'][0]['message']
                    location = message.get('content', '').strip()
                    
                    if not location and 'reasoning' in message:
                        location = message['reasoning'].strip()
                    
                    # Clean location
                    location = location.strip().strip('"').strip("'")
                    if '\n' in location:
                        location = location.split('\n')[0].strip()
                    
                    if location and location.upper() != "NONE" and len(location) < 100:
                        return location
                
                return None
            
        except requests.exceptions.Timeout:
            if attempt < 1:
                continue
        except Exception as e:
            print(f"[THAURA ERROR] {e}")
            return None
    
def detect_palestine_location(text: str):
    """Detect Palestinian location - exact, spaCy, fuzzy, generic locations"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Level 1: Try exact word-by-word match in GeoJSON
    for location in geojson_coords.keys():
        if location in text_lower:
            print(f"[LOCATION EXACT MATCH] {location}")
            return {"village": location, "city": location}
    
    # Level 2: Try generic locations (Gaza, West Bank, etc.)
    for generic_name, generic_data in GENERIC_LOCATIONS.items():
        if generic_name in text_lower:
            print(f"[LOCATION GENERIC] {generic_data['name']}")
            return {"village": generic_data['name'], "city": generic_data['name']}
    
    # Level 3: Try spaCy NER to extract location words
    if nlp:
        try:
            doc = nlp(text)
            location_entities = [ent.text.lower() for ent in doc.ents if ent.label_ == 'GPE']
            
            # Check each entity against GeoJSON
            for entity in location_entities:
                if entity in geojson_coords:
                    print(f"[LOCATION spaCy] {entity}")
                    return {"village": entity, "city": entity}
        except Exception as e:
            print(f"[spaCy ERROR] {e}")
    
    # Level 4: Try Fuzzy Matching
    location_name, lat, lon = geocode_with_fuzzy(text)
    if location_name:
        print(f"[LOCATION FUZZY MATCH] {location_name}")
        return {"village": location_name, "city": location_name}
    
    print("[LOCATION] Not detected")
    return None
