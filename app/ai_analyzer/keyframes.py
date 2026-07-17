# app/ai_analyzer/keyframes.py
"""
Video keyframe extraction for citizen journalism content analysis.

Instead of analyzing only the first frame, this module samples representative
frames throughout the video using two strategies:
1. Interval-based: every N seconds (simple, predictable)
2. Scene-change detection: histogram diff to find visual transitions

Returns frames as base64-encoded JPEG for GPT-4o multimodal analysis.
"""

import base64
import io
import logging
import os
import tempfile
from typing import List, Optional

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_INTERVAL_SEC = 5    # Sample every 5 seconds
MAX_FRAMES = 8              # Cap to limit API cost
SCENE_CHANGE_THRESHOLD = 0.4  # Histogram diff threshold (0-1)
FRAME_JPEG_QUALITY = 75     # JPEG quality for base64 encoding
MAX_FRAME_DIMENSION = 768   # Resize frames to limit token cost


def _frame_to_base64(frame, max_dim: int = MAX_FRAME_DIMENSION) -> str:
    """Convert an OpenCV frame (numpy array) to base64 JPEG string."""
    import cv2

    h, w = frame.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, FRAME_JPEG_QUALITY])
    return base64.b64encode(buffer.tobytes()).decode('utf-8')


def _histogram_diff(frame_a, frame_b) -> float:
    """
    Compute normalized histogram difference between two frames.
    Returns 0.0 (identical) to 1.0 (completely different).
    """
    import cv2

    # Convert to HSV for better color comparison
    hsv_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2HSV)
    hsv_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2HSV)

    hist_a = cv2.calcHist([hsv_a], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist_b = cv2.calcHist([hsv_b], [0, 1], None, [50, 60], [0, 180, 0, 256])

    cv2.normalize(hist_a, hist_a, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist_b, hist_b, 0, 1, cv2.NORM_MINMAX)

    # Correlation: 1.0 = identical, -1.0 = opposite
    correlation = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return max(0.0, 1.0 - correlation)


def extract_keyframes_interval(
    video_path: str,
    interval_sec: float = DEFAULT_INTERVAL_SEC,
    max_frames: int = MAX_FRAMES,
) -> List[dict]:
    """
    Extract frames at fixed intervals throughout the video.

    Returns list of:
        {
            'base64': str  — base64-encoded JPEG
            'time_sec': float — timestamp in seconds
            'index': int — frame index
        }
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python not installed — keyframe extraction unavailable")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    if duration_sec <= 0:
        cap.release()
        return []

    # Calculate frame positions
    interval_frames = int(fps * interval_sec)
    positions = list(range(0, total_frames, max(1, interval_frames)))

    # Always include first and last frame
    if 0 not in positions:
        positions.insert(0, 0)
    last_frame = max(0, total_frames - 1)
    if last_frame not in positions:
        positions.append(last_frame)

    # Cap the number of frames
    if len(positions) > max_frames:
        step = len(positions) / max_frames
        positions = [positions[int(i * step)] for i in range(max_frames)]

    frames = []
    for idx, frame_pos in enumerate(positions):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = cap.read()
        if ret and frame is not None:
            frames.append({
                'base64': _frame_to_base64(frame),
                'time_sec': round(frame_pos / fps, 2),
                'index': idx,
            })

    cap.release()
    logger.info("Extracted %d keyframes from %.1fs video (interval=%ds)",
                len(frames), duration_sec, interval_sec)
    return frames


def extract_keyframes_scene_change(
    video_path: str,
    threshold: float = SCENE_CHANGE_THRESHOLD,
    max_frames: int = MAX_FRAMES,
    sample_fps: float = 2.0,
) -> List[dict]:
    """
    Extract frames at scene changes detected by histogram difference.

    Samples the video at `sample_fps` rate and compares consecutive frames.
    When the difference exceeds `threshold`, the frame is captured.

    Returns same format as extract_keyframes_interval.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python not installed — keyframe extraction unavailable")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    if duration_sec <= 0:
        cap.release()
        return []

    sample_interval = max(1, int(fps / sample_fps))
    prev_frame = None
    frames = []

    # Always capture first frame
    ret, first_frame = cap.read()
    if ret and first_frame is not None:
        frames.append({
            'base64': _frame_to_base64(first_frame),
            'time_sec': 0.0,
            'index': 0,
        })
        prev_frame = first_frame

    frame_idx = 0
    while len(frames) < max_frames:
        frame_idx += sample_interval
        if frame_idx >= total_frames:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        if prev_frame is not None:
            diff = _histogram_diff(prev_frame, frame)
            if diff >= threshold:
                frames.append({
                    'base64': _frame_to_base64(frame),
                    'time_sec': round(frame_idx / fps, 2),
                    'index': len(frames),
                })
                prev_frame = frame

    cap.release()
    logger.info("Extracted %d scene-change keyframes from %.1fs video (threshold=%.2f)",
                len(frames), duration_sec, threshold)
    return frames


def extract_keyframes(
    video_path: str,
    strategy: str = 'hybrid',
    max_frames: int = MAX_FRAMES,
) -> List[dict]:
    """
    High-level keyframe extraction entry point.

    Parameters
    ----------
    video_path : str      — path to video file
    strategy   : str      — 'interval', 'scene_change', or 'hybrid' (default)
    max_frames : int      — maximum frames to return

    Returns
    -------
    list of {base64: str, time_sec: float, index: int}
    """
    if strategy == 'scene_change':
        frames = extract_keyframes_scene_change(video_path, max_frames=max_frames)
    elif strategy == 'interval':
        frames = extract_keyframes_interval(video_path, max_frames=max_frames)
    else:
        # Hybrid: try scene change first, fall back to interval if too few
        frames = extract_keyframes_scene_change(video_path, max_frames=max_frames)
        if len(frames) < 3:
            logger.info("Scene change found few frames (%d), supplementing with interval",
                        len(frames))
            interval_frames = extract_keyframes_interval(
                video_path, max_frames=max_frames
            )
            # Merge, deduplicate by similar timestamp
            existing_times = {f['time_sec'] for f in frames}
            for f in interval_frames:
                if len(frames) >= max_frames:
                    break
                # Skip if within 2 seconds of an existing frame
                if not any(abs(f['time_sec'] - t) < 2.0 for t in existing_times):
                    frames.append(f)
                    existing_times.add(f['time_sec'])

            # Re-sort by time and re-index
            frames.sort(key=lambda f: f['time_sec'])
            for i, f in enumerate(frames):
                f['index'] = i

    return frames[:max_frames]
