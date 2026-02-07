#!/usr/bin/env python3
"""
Merge palestine_geodata with existing palestinians_towns.geojson
Extracts all locations from the detailed palestinian GeoJSON and enhances the database
"""
import json
import os

# Load the detailed palestine.geo.json from the cloned repo
detailed_geojson_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestine_geodata', 'palestine.geo.json')
current_geojson_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns.geojson')
output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'palestinians_towns_enhanced.geojson')

print("Loading detailed palestine.geo.json...")
try:
    with open(detailed_geojson_path, 'r', encoding='utf-8') as f:
        detailed_data = json.load(f)
    print(f"✓ Loaded {len(detailed_data.get('features', []))} features from detailed GeoJSON")
except Exception as e:
    print(f"✗ Error loading detailed GeoJSON: {e}")
    exit(1)

print(f"\nLoading current palestinians_towns.geojson...")
try:
    with open(current_geojson_path, 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    print(f"✓ Loaded {len(current_data.get('features', []))} features from current GeoJSON")
except Exception as e:
    print(f"✗ Error loading current GeoJSON: {e}")
    exit(1)

# Build a set of location names from current data for deduplication
current_locations = set()
for feature in current_data.get('features', []):
    props = feature.get('properties', {})
    name = props.get('town_name', '').lower()
    if name:
        current_locations.add(name)

print(f"\nCurrent unique locations: {len(current_locations)}")

# Extract all point features from detailed data (skip polygon/multipolygon for now)
new_features = []
skipped = 0
added = 0

for feature in detailed_data.get('features', []):
    geometry = feature.get('geometry', {})
    geom_type = geometry.get('type', '')
    props = feature.get('properties', {})
    
    # Extract location name - try multiple property names
    name = props.get('name') or props.get('en_name') or props.get('NAME') or props.get('EN_NAME')
    if not name:
        skipped += 1
        continue
    
    name_lower = name.lower().strip()
    
    # Skip if already in current database
    if name_lower in current_locations:
        skipped += 1
        continue
    
    # Only process point features for now (detailed data may have complex geometries)
    if geom_type == 'Point':
        coords = geometry.get('coordinates', [])
        if len(coords) == 2:
            lon, lat = coords
            new_feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "place_id": f"pal_enhanced_{name_lower.replace(' ', '_')}",
                    "town_name": name,
                    "arabic_name": props.get('ar_name', props.get('ARABIC_NAME', '')),
                    "english_name": name,
                    "district": props.get('governorate', props.get('GOVERNORATE', 'Unknown')),
                    "type": props.get('place_type', props.get('PLACE_TYPE', 'town')),
                    "status": props.get('status', 'existing'),
                    "source": "palestine_geodata"
                }
            }
            new_features.append(new_feature)
            added += 1
            current_locations.add(name_lower)

print(f"Added: {added} new locations")
print(f"Skipped: {skipped} (duplicates or non-point features)")

# Merge with current data
merged_data = {
    "type": "FeatureCollection",
    "features": current_data.get('features', []) + new_features
}

# Save enhanced GeoJSON
try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved enhanced GeoJSON to: {output_path}")
    print(f"✓ Total features: {len(merged_data['features'])}")
except Exception as e:
    print(f"✗ Error saving enhanced GeoJSON: {e}")
    exit(1)

# Also backup and replace the original
import shutil
backup_path = current_geojson_path + '.bak'
try:
    shutil.copy(current_geojson_path, backup_path)
    shutil.copy(output_path, current_geojson_path)
    print(f"✓ Backed up original to: {backup_path}")
    print(f"✓ Replaced palestinians_towns.geojson with enhanced version")
except Exception as e:
    print(f"⚠️  Could not replace original: {e}")

print("\n" + "="*60)
print("Merge complete! Restart consumer/producer to load new data.")
print("="*60)
