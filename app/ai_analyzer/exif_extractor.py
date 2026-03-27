# app/ai_analyzer/exif_extractor.py
"""
Extract EXIF metadata from uploaded photos for citizen journalism verification.

Extracts:
- GPS coordinates (lat/lon) — most trustworthy geolocation signal
- Original timestamp — when the photo was actually taken
- Device info — camera model for credibility scoring
- Orientation — for proper display
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _dms_to_decimal(dms_tuple, ref: str) -> Optional[float]:
    """Convert EXIF GPS DMS (degrees, minutes, seconds) to decimal degrees."""
    try:
        degrees = float(dms_tuple[0])
        minutes = float(dms_tuple[1])
        seconds = float(dms_tuple[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 7)
    except (TypeError, IndexError, ValueError, ZeroDivisionError):
        return None


def _parse_exif_datetime(dt_str: str) -> Optional[str]:
    """Parse EXIF datetime string (e.g. '2024:03:15 14:30:00') to ISO format."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    # EXIF uses colon separators in date portion
    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y:%m:%d'):
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def extract_exif(file_path: str) -> dict:
    """
    Extract EXIF metadata from an image file.

    Parameters
    ----------
    file_path : str — path to the image file on disk

    Returns
    -------
    dict with keys:
        lat          : float or None — GPS latitude
        lon          : float or None — GPS longitude
        timestamp    : str or None   — ISO datetime when photo was taken
        device       : str or None   — camera make/model
        orientation  : int or None   — EXIF orientation tag (1-8)
        has_gps      : bool          — whether GPS data was found
        has_timestamp: bool          — whether original datetime was found
    """
    result = {
        'lat': None,
        'lon': None,
        'timestamp': None,
        'device': None,
        'orientation': None,
        'has_gps': False,
        'has_timestamp': False,
    }

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
    except ImportError:
        logger.warning("Pillow not installed — EXIF extraction unavailable")
        return result

    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if not exif_data:
            logger.debug("No EXIF data found in %s", file_path)
            return result
    except Exception as e:
        logger.warning("Failed to read EXIF from %s: %s", file_path, e)
        return result

    # Build a readable tag dict
    decoded = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, tag_id)
        decoded[tag_name] = value

    # --- GPS extraction ---
    gps_info = decoded.get('GPSInfo')
    if gps_info and isinstance(gps_info, dict):
        gps_decoded = {}
        for key, val in gps_info.items():
            gps_tag = GPSTAGS.get(key, key)
            gps_decoded[gps_tag] = val

        lat_dms = gps_decoded.get('GPSLatitude')
        lat_ref = gps_decoded.get('GPSLatitudeRef', 'N')
        lon_dms = gps_decoded.get('GPSLongitude')
        lon_ref = gps_decoded.get('GPSLongitudeRef', 'E')

        if lat_dms and lon_dms:
            lat = _dms_to_decimal(lat_dms, lat_ref)
            lon = _dms_to_decimal(lon_dms, lon_ref)
            if lat is not None and lon is not None:
                result['lat'] = lat
                result['lon'] = lon
                result['has_gps'] = True
                logger.info("EXIF GPS: %s, %s", lat, lon)

    # --- Timestamp extraction ---
    # Prefer DateTimeOriginal > DateTimeDigitized > DateTime
    for tag in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
        raw_dt = decoded.get(tag)
        if raw_dt:
            parsed = _parse_exif_datetime(str(raw_dt))
            if parsed:
                result['timestamp'] = parsed
                result['has_timestamp'] = True
                break

    # --- Device info ---
    make = decoded.get('Make', '')
    model = decoded.get('Model', '')
    device_parts = [str(make).strip(), str(model).strip()]
    device_str = ' '.join(p for p in device_parts if p)
    if device_str:
        result['device'] = device_str

    # --- Orientation ---
    orientation = decoded.get('Orientation')
    if orientation and isinstance(orientation, int):
        result['orientation'] = orientation

    logger.info("EXIF extraction complete: gps=%s, timestamp=%s, device=%s",
                result['has_gps'], result['has_timestamp'], result['device'])
    return result
