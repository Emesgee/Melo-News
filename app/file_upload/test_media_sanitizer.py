"""Smoke tests for media_sanitizer."""

import os
import tempfile

from PIL import Image
from PIL.ExifTags import IFD

from .media_sanitizer import sanitize_for_upload, safe_remove


def _build_geotagged_jpeg(path: str) -> None:
    """Write a small JPEG carrying Make/Model + GPS lat/lon EXIF tags."""
    img = Image.new('RGB', (32, 32), 'red')
    exif = img.getexif()
    exif[271] = 'TestMake'       # Make
    exif[272] = 'TestModel'      # Model
    exif[305] = 'TestSoftware'   # Software

    # GPSInfo lives in its own IFD; PIL exposes it via get_ifd(IFD.GPSInfo)
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[1] = 'N'                    # GPSLatitudeRef
    gps_ifd[2] = (31.0, 47.0, 0.0)      # GPSLatitude  (Jerusalem-ish)
    gps_ifd[3] = 'E'                    # GPSLongitudeRef
    gps_ifd[4] = (35.0, 13.0, 0.0)      # GPSLongitude

    img.save(path, format='JPEG', exif=exif)


def _has_any_exif(path: str) -> dict:
    with Image.open(path) as img:
        exif = img.getexif()
        out = dict(exif)
        try:
            gps = exif.get_ifd(IFD.GPSInfo)
            if gps:
                out['__gps__'] = dict(gps)
        except Exception:
            pass
        return out


def test_sanitize_strips_gps_and_device():
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'reporter.jpg')
        _build_geotagged_jpeg(raw)

        before = _has_any_exif(raw)
        assert before, "fixture should carry EXIF"
        assert '__gps__' in before, f"fixture should carry GPS, got {before}"

        clean_path = sanitize_for_upload(raw)
        assert clean_path != raw, "sanitizer should return a new path for images"
        assert os.path.exists(clean_path)

        after = _has_any_exif(clean_path)
        assert not after, f"EXIF should be empty after strip, got {after}"

        safe_remove(clean_path)


def test_sanitize_passes_through_video():
    with tempfile.TemporaryDirectory() as tmp:
        fake_video = os.path.join(tmp, 'clip.mp4')
        with open(fake_video, 'wb') as f:
            f.write(b'fake video bytes')

        out = sanitize_for_upload(fake_video)
        assert out == fake_video, "video should pass through unchanged"


if __name__ == '__main__':
    test_sanitize_strips_gps_and_device()
    test_sanitize_passes_through_video()
    print("OK — EXIF strip verified, video pass-through verified")
