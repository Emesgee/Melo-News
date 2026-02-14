#!/usr/bin/env python3
"""
Script to add default file types to PostgreSQL database
Run this once to populate file_types table
"""

from app import create_app
from app.models import db, FileType

def add_file_types():
    """Add default file types to the database"""
    
    app = create_app()
    
    with app.app_context():
        # Check if file types already exist
        existing_count = FileType.query.count()
        if existing_count > 0:
            print(f"⚠️  File types already exist ({existing_count} records). Skipping...")
            return
        
        # Define file types
        file_types = [
            {
                'type_name': 'Document',
                'allowed_extensions': 'pdf,doc,docx,txt,xlsx,csv'
            },
            {
                'type_name': 'Image',
                'allowed_extensions': 'jpg,jpeg,png,gif,webp,bmp'
            },
            {
                'type_name': 'Video',
                'allowed_extensions': 'mp4,avi,mov,mkv,flv,webm,m4v'
            },
            {
                'type_name': 'Audio',
                'allowed_extensions': 'mp3,wav,flac,aac,ogg,m4a'
            },
            {
                'type_name': 'Compressed',
                'allowed_extensions': 'zip,rar,7z,tar,gz,bz2'
            },
            {
                'type_name': 'Data',
                'allowed_extensions': 'json,xml,geojson,kml,shp'
            }
        ]
        
        # Add file types to database
        for ft in file_types:
            new_type = FileType(
                type_name=ft['type_name'],
                allowed_extensions=ft['allowed_extensions']
            )
            db.session.add(new_type)
            print(f"✅ Added: {ft['type_name']} ({ft['allowed_extensions']})")
        
        try:
            db.session.commit()
            print("\n✅ All file types added successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error adding file types: {e}")

if __name__ == '__main__':
    add_file_types()
