import json

def convert_to_geojson(input_file, output_file):
    """Convert palestinians_towns.json to GeoJSON format"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = []
    
    for locality in data['palestinian_localities']:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [locality['longitude'], locality['latitude']]
            },
            "properties": {
                "town_name": locality['town_name'],
                "english_name": locality['english_name'],
                "arabic_name": locality['arabic_name'],
                "governorate": locality['governorate'],
                "district": locality['district'],
                "type": locality['type'],
                "status": locality['status'],
                "notes": locality['notes']
            }
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Converted {len(features)} localities to GeoJSON")
    print(f"✓ Saved to: {output_file}")

# Run conversion
convert_to_geojson(
    '../data/palestinians_towns.json',
    '../data/palestinians_towns.geojson'
)