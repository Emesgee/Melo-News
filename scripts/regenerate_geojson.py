#!/usr/bin/env python3
"""
Regenerate GeoJSON from palestinians_towns.json
Removes JSON comments and creates valid GeoJSON file
"""
import json
import re
import os

def remove_json_comments(text):
    """Remove C-style comments from JSON text"""
    # Remove /* */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove // comments
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    # Remove trailing commas before ] or }
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text

# Read the JSON file with comments
json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns.json')
with open(json_path, 'r', encoding='utf-8') as f:
    json_text = f.read()

# Remove comments
clean_json = remove_json_comments(json_text)

# Parse JSON
try:
    data = json.loads(clean_json)
    print(f"✓ Loaded {len(data['features'])} features")
except json.JSONDecodeError as e:
    print(f"✗ JSON Parse Error: {e}")
    exit(1)

# Save clean GeoJSON
geojson_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns.geojson')
with open(geojson_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ Generated {geojson_path}")
print(f"✓ Total features: {len(data['features'])}")

# Count by region/district
districts = {}
for feature in data['features']:
    district = feature['properties'].get('district', 'Unknown')
    districts[district] = districts.get(district, 0) + 1

print("\nFeatures by district:")
for district, count in sorted(districts.items()):
    print(f"  {district}: {count}")
