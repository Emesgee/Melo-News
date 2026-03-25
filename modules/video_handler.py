import os
import logging
from typing import Optional

import requests
from urllib.parse import urlparse, unquote
from config import DOWNLOADS_FOLDER
from modules.azure_handler import upload_file_to_blob

logger = logging.getLogger(__name__)


def download_and_upload_videos(video_links: Optional[str]) -> list[str]:
    """Download videos and upload to Azure."""
    uploaded_urls: list[str] = []

    if not video_links or not video_links.strip():
        return uploaded_urls

    for url in video_links.split('|'):
        url = url.strip()
        if not url:
            continue

        try:
            local_path = os.path.join(DOWNLOADS_FOLDER, unquote(os.path.basename(urlparse(url).path)))

            logger.info("Downloading video: %s", url)
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info("Downloaded to: %s", local_path)

            blob_url = upload_file_to_blob(local_path)
            if blob_url:
                uploaded_urls.append(blob_url)

            # Clean up local file
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.debug("Cleaned up: %s", local_path)

        except Exception as e:
            logger.error("Video download error for %s: %s", url, e)

    return uploaded_urls


def process_image_links(image_links: Optional[str]) -> list[str]:
    """Extract and validate image links."""
    if not image_links or not image_links.strip():
        return []

    return [url.strip() for url in image_links.split('|') if url.strip()]
