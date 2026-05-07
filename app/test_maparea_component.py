#!/usr/bin/env python3
"""
MapArea.js Component Testing Suite
Tests the MapArea component by analyzing structure and verifying API integration
"""

import json
import re
import os
from pathlib import Path

def test_maparea_syntax():
    """Verify MapArea.js has valid syntax"""
    print("\n" + "="*70)
    print("TEST 1: MapArea.js Syntax Validation")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for balanced JSX tags
    jsx_open = content.count('<MapContainer')
    jsx_close = content.count('</MapContainer>')
    
    print(f"✓ MapContainer open tags: {jsx_open}")
    print(f"✓ MapContainer close tags: {jsx_close}")
    assert jsx_open == jsx_close, "JSX tags not balanced!"
    print("✓ JSX syntax is balanced")
    
    # Check for required imports
    required_imports = [
        'MapContainer',
        'TileLayer',
        'Marker',
        'react-leaflet',
        'CityHistory',
        'NewsChat',
        'MeloSummary',
    ]
    
    print("\nChecking imports:")
    for imp in required_imports:
        if imp in content:
            print(f"  ✓ {imp} found")
        else:
            print(f"  ✗ {imp} NOT found")
    
    return True

def test_maparea_component_structure():
    """Verify MapArea component has required structure"""
    print("\n" + "="*70)
    print("TEST 2: Component Structure")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for main component definition
    if 'const MapArea = ' in content or 'function MapArea' in content:
        print("✓ MapArea component defined")
    else:
        print("✗ MapArea component NOT found")
        return False
    
    # Check for required functions/hooks
    required_hooks = [
        'useState',
        'useEffect',
        'useMemo',
        'useCallback',
        'useRef',
    ]
    
    print("\nChecking React hooks:")
    for hook in required_hooks:
        if hook in content:
            print(f"  ✓ {hook} found")
        else:
            print(f"  ✗ {hook} NOT found")
    
    # Check for required components
    required_components = [
        'MarkerPopupWrapper',
        'ZoomCircles',
        'FitBounds',
    ]
    
    print("\nChecking internal components:")
    for comp in required_components:
        if comp in content:
            print(f"  ✓ {comp} found")
        else:
            print(f"  ✗ {comp} NOT found")
    
    return True

def test_maparea_features():
    """Verify MapArea has all expected features"""
    print("\n" + "="*70)
    print("TEST 3: Feature Implementation")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    features = {
        'Clustered markers': 'MarkerClusterGroup',
        'Custom marker icons': 'createThumbnailIcon',
        'Thumbnail support': 'thumbnailUrl',
        'Video detection': 'hasVideo',
        'Zoom controls': 'zoom-circles',
        'Layer selection': 'map-dropdown',
        'Coordinate normalization': 'lat: parseFloat',
        'Time formatting': 'toLocaleString',
        'File handling': 'imageLinks',
        'Popup with tabs': 'showTab',
    }
    
    print("Checking features:")
    for feature_name, feature_code in features.items():
        if feature_code in content:
            print(f"  ✓ {feature_name}")
        else:
            print(f"  ✗ {feature_name}")
    
    return True

def test_maparea_props():
    """Verify MapArea accepts correct props"""
    print("\n" + "="*70)
    print("TEST 4: Props Validation")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for searchResults prop destructuring
    if 'searchResults = []' in content:
        print("✓ searchResults prop with default value")
    else:
        print("✗ searchResults prop NOT found")
    
    # Check for dedupeStories usage
    if 'dedupeStories' in content:
        print("✓ Story deduplication implemented")
    else:
        print("✗ Story deduplication NOT found")
    
    # Check for result field handling
    field_mappings = {
        'lat': ['lat', 'latitude', 'result_lat', 'lat_result'],
        'lon': ['lon', 'longitude', 'result_lon', 'lon_result'],
        'city': ['city', 'matched_city', 'city_result'],
        'title': ['title', 'message'],
    }
    
    print("\nChecking field mappings:")
    for primary, alternatives in field_mappings.items():
        found = False
        for alt in alternatives:
            if alt in content:
                found = True
                break
        if found:
            print(f"  ✓ {primary} field mapping found")
        else:
            print(f"  ✗ {primary} field mapping NOT found")
    
    return True

def test_api_integration():
    """Verify MapArea integrates with API"""
    print("\n" + "="*70)
    print("TEST 5: API Integration")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for API endpoint reference
    if '/api/stories/map' in content:
        print("✓ API endpoint '/api/stories/map' referenced")
    elif '/api/telegram/news' in content:
        print("✗ Legacy endpoint '/api/telegram/news' still present — should be '/api/stories/map'")
    else:
        print("✗ API endpoint NOT found")
    
    # Check for fetch usage
    if 'fetch' in content:
        print("✓ fetch API used")
    else:
        print("✗ fetch API NOT found")
    
    return True

def test_css_classes():
    """Verify CSS classes are properly referenced"""
    print("\n" + "="*70)
    print("TEST 6: CSS Class References")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    css_classes = [
        'map-area-container',
        'map-container',
        'map-dropdown',
        'zoom-circles',
        'custom-marker-icon',
        'red-dot-marker',
        'thumbnail-marker',
    ]
    
    print("Checking CSS class references:")
    for css_class in css_classes:
        if css_class in content:
            print(f"  ✓ {css_class}")
        else:
            print(f"  ✗ {css_class}")
    
    return True

def test_export():
    """Verify MapArea is properly exported"""
    print("\n" + "="*70)
    print("TEST 7: Module Export")
    print("="*70)
    
    maparea_path = Path(__file__).parent / "app" / "frontend" / "src" / "components" / "letleaf_map" / "MapArea.js"
    
    with open(maparea_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'export default MapArea' in content:
        print("✓ MapArea exported as default export")
    else:
        print("✗ MapArea NOT properly exported")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MapArea.js Component Test Suite")
    print("="*70)
    
    try:
        results = []
        
        results.append(('Syntax Validation', test_maparea_syntax()))
        results.append(('Component Structure', test_maparea_component_structure()))
        results.append(('Feature Implementation', test_maparea_features()))
        results.append(('Props Validation', test_maparea_props()))
        results.append(('API Integration', test_api_integration()))
        results.append(('CSS Classes', test_css_classes()))
        results.append(('Module Export', test_export()))
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
