#!/usr/bin/env python3
"""
Simple HTTP server to test the map visibility
Run with: python serve_test_map.py
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def log_message(self, format, *args):
        print(f"[MAP SERVER] {format % args}")

if __name__ == '__main__':
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"\n{'='*70}")
            print(f"MapArea Test Server Started")
            print(f"{'='*70}")
            print(f"✓ Server running at: http://localhost:{PORT}/test_map_visibility.html")
            print(f"✓ Open this URL in your browser to test the map visibility")
            print(f"\nFeatures to verify:")
            print(f"  ✓ Map displays with Palestine/Israel centered")
            print(f"  ✓ 9 Palestinian cities marked with red dots")
            print(f"  ✓ Marker clustering visible")
            print(f"  ✓ Zoom controls (+/-) functional")
            print(f"  ✓ Layer selector (OSM, Topo, Stadia)")
            print(f"  ✓ Click markers to see city details")
            print(f"  ✓ Pan and zoom with mouse")
            print(f"\nPress Ctrl+C to stop the server")
            print(f"{'='*70}\n")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Error: {e}")
