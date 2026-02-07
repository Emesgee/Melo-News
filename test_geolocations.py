#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test and analyze geolocation coverage"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from modules.geocoder import GENERIC_LOCATIONS, load_geojson_coordinates, geocode_city
from modules.location_detector import detect_palestine_location

def analyze_geojson():
    """Analyze GeoJSON data"""
    print("="*60)
    print("GeoJSON ANALYSIS")
    print("="*60)
    
    geojson_path = "data/palestinians_towns.geojson"
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    
    features = geojson.get('features', [])
    print(f"✓ Total towns/villages: {len(features)}")
    
    # Group by district
    districts = {}
    for feat in features:
        props = feat['properties']
        district = props.get('district', 'Unknown')
        if district not in districts:
            districts[district] = []
        districts[district].append(props.get('town_name', 'Unknown'))
    
    print(f"\n✓ Districts: {len(districts)}")
    for district, towns in sorted(districts.items()):
        print(f"  • {district}: {len(towns)} towns")
    
    # Sample towns
    print(f"\n✓ Sample towns:")
    for feat in features[:10]:
        props = feat['properties']
        print(f"  • {props.get('town_name', '?')} ({props.get('district', '?')})")
    
    return districts

def check_generic_locations():
    """Check generic locations"""
    print("\n" + "="*60)
    print("GENERIC LOCATIONS")
    print("="*60)
    
    for name, data in GENERIC_LOCATIONS.items():
        print(f"✓ {name}: ({data['lat']}, {data['lon']})")

def check_cache():
    """Check geocode cache"""
    print("\n" + "="*60)
    print("GEOCODE CACHE")
    print("="*60)
    
    if not os.path.exists('geocode_cache.json'):
        print("✗ Cache file not found")
        return {}
    
    with open('geocode_cache.json', 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    print(f"✓ Cached locations: {len(cache)}")
    print("\nSample cached entries:")
    for i, (key, val) in enumerate(list(cache.items())[:5]):
        print(f"  • {key}: {val}")
    
    return cache

def test_location_detection():
    """Test location detection with sample messages"""
    print("\n" + "="*60)
    print("LOCATION DETECTION TEST")
    print("="*60)
    
    test_messages = [
        "Breaking news from Gaza today",
        "In Ramallah, Israeli forces...",
        "Sheikh Jarrah neighborhood affected",
        "Khan Younis under bombardment",
        "West Bank settlers attack village",
        "Jenin refugee camp incident",
        "East Jerusalem protests",
        "Bethlehem residents demand justice",
        "Nablus market reopens",
        "Hebron school damaged",
        "Gaza Strip humanitarian crisis",
        "Occupied territories report",
    ]
    
    print(f"Testing {len(test_messages)} sample messages:\n")
    
    for msg in test_messages:
        result = detect_palestine_location(msg)
        if result:
            location = result.get('village') or result.get('city') or result.get('place') or 'Unknown'
            print(f"✓ '{msg[:40]}...' → {location}")
        else:
            print(f"✗ '{msg[:40]}...' → NOT DETECTED")

def test_geocoding():
    """Test geocoding of detected locations"""
    print("\n" + "="*60)
    print("GEOCODING TEST")
    print("="*60)
    
    # Load locations
    load_geojson_coordinates()
    
    test_locations = [
        "Gaza",
        "West Bank",
        "Ramallah",
        "Khan Younis",
        "Jenin",
        "Bethlehem",
        "Sheikh Jarrah",
        "Nablus",
        "Hebron",
        "Jericho",
    ]
    
    print(f"Testing {len(test_locations)} locations:\n")
    
    for loc in test_locations:
        result = geocode_city(loc)
        if result:
            print(f"✓ {loc:20} → ({result['lat']}, {result['lon']}) [{result.get('district', 'N/A')}]")
        else:
            print(f"✗ {loc:20} → GEOCODING FAILED")

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "GEOLOCATION ANALYSIS & TESTING" + " "*18 + "║")
    print("╚" + "="*58 + "╝")
    
    analyze_geojson()
    check_generic_locations()
    check_cache()
    test_location_detection()
    test_geocoding()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
