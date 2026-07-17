"""
Media sanitizer for reporter safety.

Strips metadata that could de-anonymize a reporter (GPS coordinates,
device serials, recording device info) BEFORE the file leaves the server
for cloud storage. Without this, a downloaded photo or video would reveal
the reporter's location via embedded tags.

Images are re-encoded into a fresh PIL Image so no EXIF survives.
Orientation is baked into pixel data via ImageOps.exif_transpose so the
visual rotation is preserved even after the orientation tag is dropped.

Videos are stream-copied through ffmpeg with ``-map_metadata -1`` so the
container is rewritten without metadata atoms (location, device, encoder
software) but the audio/video tracks are not transcoded — fast and
lossless. If ffmpeg is unavailable, the file passes through with a loud
warning; deployments that handle sensitive reporter media should install
ffmpeg.

Callers should treat the returned path as the safe-to-upload artifact;
on any failure the original path is returned so uploads are never
blocked.
"""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

# How long to give ffmpeg before we give up and ship the raw file.
# Stream-copy is fast, but very large files (hours of video) need headroom.
_FFMPEG_TIMEOUT_SECONDS = 120

_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.tiff', '.tif'}
_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpeg', '.m4v'}


def sanitize_for_upload(input_path: str) -> str:
    """
    Produce a metadata-stripped copy of the file safe to send to cloud storage.

    Returns the path to a sanitized sibling file (caller owns cleanup).
    On any failure, falls back to returning ``input_path`` so the upload
    pipeline never breaks because of sanitization. Failures are logged.
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext in _IMAGE_EXTS:
        sanitized = _sanitize_image(input_path)
        return sanitized or input_path

    if ext in _VIDEO_EXTS:
        sanitized = _sanitize_video(input_path, ext)
        return sanitized or input_path

    return input_path


def _sanitize_image(input_path: str) -> str | None:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        logger.error("Pillow not installed — cannot strip EXIF; uploading raw file")
        return None

    output_path = _sibling_path(input_path, '.sanitized')

    try:
        with Image.open(input_path) as img:
            img.load()
            original_format = img.format or _format_from_ext(input_path)
            oriented = ImageOps.exif_transpose(img)

            clean = Image.new(oriented.mode, oriented.size)
            clean.paste(oriented)

            save_kwargs = {'format': original_format}
            if original_format == 'JPEG':
                save_kwargs['quality'] = 92
                save_kwargs['optimize'] = True
            clean.save(output_path, **save_kwargs)
    except Exception as exc:
        logger.exception("EXIF strip failed for %s: %s — falling back to raw file", input_path, exc)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None

    return output_path


def _sanitize_video(input_path: str, ext: str) -> str | None:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        logger.warning(
            "ffmpeg not installed — cannot strip metadata from %s. "
            "Container GPS/device tags will leak. Install ffmpeg on this host.",
            input_path,
        )
        return None

    output_path = _sibling_path(input_path, '.sanitized')
    # -map_metadata -1   drop global metadata atoms
    # -map_chapters -1   drop chapter list (can carry markers / location notes)
    # -c copy            stream-copy: no re-encode, fast and lossless
    # -y                 overwrite if a stale temp exists from a previous attempt
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
        '-i', input_path,
        '-map_metadata', '-1',
        '-map_chapters', '-1',
        '-c', 'copy',
        output_path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out stripping %s — uploading raw file", input_path)
        safe_remove(output_path)
        return None
    except OSError as exc:
        logger.error("ffmpeg invocation failed for %s: %s — uploading raw file", input_path, exc)
        safe_remove(output_path)
        return None

    if proc.returncode != 0 or not os.path.exists(output_path):
        logger.error(
            "ffmpeg returned %s stripping %s: %s — uploading raw file",
            proc.returncode, input_path, proc.stderr.decode('utf-8', errors='replace')[:500],
        )
        safe_remove(output_path)
        return None

    return output_path


def _sibling_path(path: str, suffix: str) -> str:
    base, ext = os.path.splitext(path)
    return f"{base}{suffix}{ext}"


def _format_from_ext(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    return {
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'png': 'PNG',
        'webp': 'WEBP',
        'tiff': 'TIFF',
        'tif': 'TIFF',
    }.get(ext)


def safe_remove(path: str) -> None:
    """Best-effort cleanup helper for sanitized temp files."""
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Failed to remove sanitized temp %s: %s", path, exc)


__all__ = ['sanitize_for_upload', 'safe_remove']
