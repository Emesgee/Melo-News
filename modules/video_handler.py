import os
import requests
from urllib.parse import urlparse, unquote
from config import DOWNLOADS_FOLDER
from modules.azure_handler import upload_file_to_blob

def download_and_upload_videos(video_links):
    """Download videos and upload to Azure"""
    uploaded_urls = []
    
    if not video_links or not video_links.strip():
        return uploaded_urls
    
    for url in video_links.split('|'):
        url = url.strip()
        if not url:
            continue
        
        try:
            local_path = os.path.join(DOWNLOADS_FOLDER, unquote(os.path.basename(urlparse(url).path)))
            
            print(f"[VIDEO] Downloading: {url}")
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"[VIDEO] Downloaded to: {local_path}")
            
            blob_url = upload_file_to_blob(local_path)
            if blob_url:
                uploaded_urls.append(blob_url)
            
            # Clean up local file
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"[VIDEO] Cleaned up: {local_path}")
                
        except Exception as e:
            print(f"[VIDEO ERROR] {url}: {e}")
    
    return uploaded_urls

def process_image_links(image_links):
    """Extract and validate image links"""
    if not image_links or not image_links.strip():
        return []
    
    urls = [url.strip() for url in image_links.split('|') if url.strip()]
    return urls
