import json
import logging
import spacy
from modules.geocoder import load_geojson_coordinates, geocode_with_fuzzy
from modules.constants import GENERIC_LOCATIONS

logger = logging.getLogger(__name__)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spacy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

# Load Palestinian locations from GeoJSON on startup
geojson_coords = load_geojson_coordinates()

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
            logger.error("Thaura error: %s", e)
            return None
    
def detect_palestine_location(text: str):
    """Detect Palestinian location - exact, spaCy, fuzzy, generic locations"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Level 1: Try exact word-by-word match in GeoJSON
    for location in geojson_coords.keys():
        if location in text_lower:
            logger.info("Exact location match: %s", location)
            return {"village": location, "city": location}
    
    # Level 2: Try generic locations (Gaza, West Bank, etc.)
    for generic_name, generic_data in GENERIC_LOCATIONS.items():
        if generic_name in text_lower:
            logger.info("Generic location match: %s", generic_data['name'])
            return {"village": generic_data['name'], "city": generic_data['name']}
    
    # Level 3: Try spaCy NER to extract location words
    if nlp:
        try:
            doc = nlp(text)
            location_entities = [ent.text.lower() for ent in doc.ents if ent.label_ == 'GPE']
            
            # Check each entity against GeoJSON
            for entity in location_entities:
                if entity in geojson_coords:
                    logger.info("spaCy location match: %s", entity)
                    return {"village": entity, "city": entity}
        except Exception as e:
            logger.error("spaCy error: %s", e)
    
    # Level 4: Try Fuzzy Matching
    location_name, lat, lon = geocode_with_fuzzy(text)
    if location_name:
        logger.info("Fuzzy location match: %s", location_name)
        return {"village": location_name, "city": location_name}
    
    logger.debug("No location detected in text")
    return None
