# app/ai_analyzer/routes.py
"""
AI-powered citizen journalism content analysis using GPT-4o multimodal.

Pipeline:
  Image  → EXIF extraction → GPT-4o Vision     → structured metadata
  Video  → Keyframes + Whisper transcription → GPT-4o → structured metadata
  Audio  → Whisper transcription → GPT-4o       → structured metadata

Single /analyze endpoint replaces the old separate Azure Vision + Speech + GPT calls.
"""

import base64
import json
import logging
import mimetypes
import os
import tempfile

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from .exif_extractor import extract_exif
from .transcriber import transcribe
from .keyframes import extract_keyframes

logger = logging.getLogger(__name__)

ai_analyzer_bp = Blueprint('ai_analyzer', __name__)

# ── Configuration ───────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_ANALYSIS_MODEL', 'gpt-4o')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY', '')

# System prompt for structured citizen journalism analysis
ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant for a citizen journalism platform focused on Palestine.
Analyze the provided media content and return a JSON object with these fields:

{
  "title": "A concise, factual news headline (max 100 chars)",
  "tags": "comma-separated relevant tags (max 8 tags, e.g. 'airstrike, gaza, humanitarian')",
  "subject": "A 1-2 sentence factual summary of what the media shows",
  "city": "The city/town where this appears to take place (empty if unknown)",
  "country": "The country (empty if unknown)",
  "event_type": "One of: military_action, humanitarian, protest, infrastructure, daily_life, political, other",
  "language_detected": "Primary language in any text/speech (e.g. 'ar', 'he', 'en')",
  "content_warnings": "Comma-separated warnings if applicable (e.g. 'graphic, violence') or empty"
}

Rules:
- Be factual, not sensationalist. Use neutral journalistic language.
- If you cannot determine a field, return an empty string rather than guessing.
- For location: look at visible text, signs, landmarks, architecture, and any EXIF data provided.
- Tags should be specific and useful for search (not generic like 'news' or 'important').
- Respond ONLY with valid JSON, no markdown or explanation."""


@ai_analyzer_bp.route('/analyze', methods=['POST'])
def analyze_media():
    """
    Analyze uploaded media (image/video/audio) and return structured metadata.

    The endpoint orchestrates:
    1. EXIF extraction (images) — GPS, timestamp, device
    2. Whisper transcription (video/audio) — full multilingual text
    3. Keyframe extraction (video) — representative frames
    4. GPT-4o multimodal analysis — structured JSON output

    Returns JSON with: title, tags, subject, city, country, event_type,
    confidence, transcription, exif, analysis_steps
    """
    if 'file' not in request.files:
        fallback = _fallback_analysis()
        fallback['error'] = 'No file provided'
        return jsonify(fallback), 200

    file = request.files['file']
    if file.filename == '':
        fallback = _fallback_analysis()
        fallback['error'] = 'Empty filename'
        return jsonify(fallback), 200

    filename = secure_filename(file.filename)
    temp_path = os.path.join(tempfile.gettempdir(), f"melo_analyze_{filename}")
    file.save(temp_path)

    try:
        mime_type, _ = mimetypes.guess_type(filename)
        analysis_steps = []  # Track progress for frontend

        if mime_type and mime_type.startswith('image'):
            result = _analyze_image(temp_path, analysis_steps)
        elif mime_type and mime_type.startswith('video'):
            result = _analyze_video(temp_path, analysis_steps)
        elif mime_type and mime_type.startswith('audio'):
            result = _analyze_audio(temp_path, analysis_steps)
        else:
            fallback = _fallback_analysis()
            fallback['title'] = 'Uploaded File'
            fallback['subject'] = 'AI analysis unavailable for this file type. Fill in the details manually.'
            fallback['note'] = f'Unsupported file type for AI analysis: {mime_type or "unknown"}'
            fallback['analysis_steps'] = analysis_steps
            return jsonify(fallback), 200

        result['analysis_steps'] = analysis_steps
        return jsonify(result), 200

    except Exception as e:
        logger.error("Analysis failed for %s: %s", filename, e, exc_info=True)
        return jsonify({'error': str(e)}), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _analyze_image(image_path: str, steps: list) -> dict:
    """Analyze a single image: EXIF → GPT-4o Vision."""

    # Step 1: EXIF extraction
    steps.append('Extracting photo metadata (EXIF)...')
    exif = extract_exif(image_path)

    # Step 2: GPT-4o Vision analysis
    steps.append('Analyzing image with AI...')
    with open(image_path, 'rb') as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Build context from EXIF
    exif_context = ""
    if exif['has_gps']:
        exif_context += f"\nEXIF GPS coordinates: {exif['lat']}, {exif['lon']}"
    if exif['has_timestamp']:
        exif_context += f"\nEXIF timestamp: {exif['timestamp']}"
    if exif['device']:
        exif_context += f"\nDevice: {exif['device']}"

    gpt_result = _call_gpt4o_vision(
        images_b64=[image_b64],
        text_context=f"Analyze this citizen journalism photo.{exif_context}",
    )

    # Merge EXIF location as ground truth (overrides GPT guess if available)
    result = _build_result(gpt_result, exif=exif)
    result['exif'] = exif
    return result


def _analyze_video(video_path: str, steps: list) -> dict:
    """Analyze video: Keyframes + Whisper → GPT-4o multimodal."""

    # Step 1: Extract keyframes
    steps.append('Extracting video keyframes...')
    keyframes = extract_keyframes(video_path, strategy='hybrid', max_frames=6)

    # Step 2: Transcribe audio
    steps.append('Transcribing audio (multilingual)...')
    transcript = transcribe(video_path, is_video=True)

    # Step 3: GPT-4o multimodal analysis
    steps.append('Analyzing content with AI...')
    images_b64 = [kf['base64'] for kf in keyframes] if keyframes else []

    text_context = "Analyze this citizen journalism video.\n"
    if transcript['text']:
        text_context += f"\nAudio transcription ({transcript['language'] or 'auto'}):\n"
        text_context += transcript['text'][:2000]  # Cap to avoid token overflow
    if not images_b64:
        text_context += "\n(No visual frames could be extracted)"

    gpt_result = _call_gpt4o_vision(
        images_b64=images_b64[:4],  # Limit frames sent to GPT-4o
        text_context=text_context,
    )

    result = _build_result(gpt_result)
    result['transcription'] = transcript['text']
    result['transcript_language'] = transcript['language']
    result['transcript_segments'] = transcript['segments'][:50]  # Cap segments
    result['transcript_duration'] = transcript['duration']
    result['transcript_method'] = transcript['method']
    result['keyframe_count'] = len(keyframes)
    return result


def _analyze_audio(audio_path: str, steps: list) -> dict:
    """Analyze audio-only: Whisper → GPT-4o text analysis."""

    # Step 1: Transcribe
    steps.append('Transcribing audio (multilingual)...')
    transcript = transcribe(audio_path, is_video=False)

    if not transcript['text']:
        return {
            'title': 'Audio Report',
            'tags': 'audio, citizen report',
            'subject': 'Audio uploaded — transcription unavailable',
            'city': '', 'country': '',
            'confidence': 0.3,
            'transcription': '',
            'note': 'Could not transcribe audio'
        }

    # Step 2: GPT-4o text analysis (no vision needed)
    steps.append('Analyzing transcript with AI...')
    gpt_result = _call_gpt4o_text(
        f"Analyze this citizen journalism audio transcription:\n\n{transcript['text'][:3000]}"
    )

    result = _build_result(gpt_result)
    result['transcription'] = transcript['text']
    result['transcript_language'] = transcript['language']
    result['transcript_segments'] = transcript['segments'][:50]
    result['transcript_duration'] = transcript['duration']
    result['transcript_method'] = transcript['method']
    return result


# ── GPT-4o API Calls ───────────────────────────────────────────────────

def _call_gpt4o_vision(images_b64: list, text_context: str) -> dict:
    """Send images + text to GPT-4o and get structured JSON."""
    if not OPENAI_API_KEY:
        logger.warning("No OpenAI API key — using fallback analysis")
        return _fallback_analysis()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Build message content with images
        content = [{"type": "text", "text": text_context}]
        for img_b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}",
                    "detail": "low",  # Use low detail to save tokens
                },
            })

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        result['ai_used'] = True
        return result

    except json.JSONDecodeError as e:
        logger.error("GPT-4o returned invalid JSON: %s", e)
        return _fallback_analysis()
    except Exception as e:
        logger.error("GPT-4o Vision call failed: %s", e)
        return _fallback_analysis()


def _call_gpt4o_text(text_context: str) -> dict:
    """Send text-only to GPT-4o and get structured JSON (for audio)."""
    if not OPENAI_API_KEY:
        return _fallback_analysis()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": text_context},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        result['ai_used'] = True
        return result

    except Exception as e:
        logger.error("GPT-4o text call failed: %s", e)
        return _fallback_analysis()


def _fallback_analysis() -> dict:
    """Minimal fallback when no AI service is available."""
    return {
        'title': '',
        'tags': '',
        'subject': '',
        'city': '',
        'country': '',
        'event_type': 'other',
        'language_detected': '',
        'content_warnings': '',
        'ai_used': False,
    }


def _build_result(gpt_result: dict, exif: dict = None) -> dict:
    """
    Merge GPT-4o analysis with EXIF data and compute confidence.

    EXIF GPS is treated as ground truth — if available, it overrides
    any location GPT-4o inferred from visual content.
    """
    from .confidence import calculate_confidence

    result = {
        'title': gpt_result.get('title', 'Citizen Report'),
        'tags': gpt_result.get('tags', ''),
        'subject': gpt_result.get('subject', ''),
        'city': gpt_result.get('city', ''),
        'country': gpt_result.get('country', ''),
        'event_type': gpt_result.get('event_type', 'other'),
        'language_detected': gpt_result.get('language_detected', ''),
        'content_warnings': gpt_result.get('content_warnings', ''),
    }

    # EXIF overrides — GPS from the device is more trustworthy than AI vision
    exif_lat = None
    exif_lon = None
    if exif and exif.get('has_gps'):
        exif_lat = exif['lat']
        exif_lon = exif['lon']

    # Calculate confidence for citizen upload
    confidence_data = {
        'message': result['subject'],
        'source': 'citizen_upload',
        'image_links': 'present',  # Media was uploaded
        'lat': exif_lat,
        'lon': exif_lon,
        'matched_city': result['city'],
        'exif_gps_match': exif is not None and exif.get('has_gps', False),
        'exif_has_timestamp': exif is not None and exif.get('has_timestamp', False),
        'has_device_info': exif is not None and bool(exif.get('device')),
    }
    result['confidence'] = calculate_confidence(confidence_data)

    return result


# ── Geocoding Proxy ────────────────────────────────────────────────────

@ai_analyzer_bp.route('/geocode', methods=['GET'])
def geocode_proxy():
    """
    Proxy geocoding requests to OpenCage so the API key stays server-side.

    Query params:
        q : str — search query (e.g. "Gaza, Palestine" or "31.5,34.4")
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400

    api_key = OPENCAGE_API_KEY
    if not api_key:
        return jsonify({
            'lat': None,
            'lon': None,
            'city': '',
            'country': '',
            'formatted': '',
            'configured': False,
            'note': 'Geocoding not configured'
        }), 200

    try:
        import requests as http_requests
        resp = http_requests.get(
            'https://api.opencagedata.com/geocode/v1/json',
            params={'q': query, 'key': api_key, 'limit': 1},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get('results'):
            r = data['results'][0]
            geo = r.get('geometry', {})
            comp = r.get('components', {})
            return jsonify({
                'lat': geo.get('lat'),
                'lon': geo.get('lng'),
                'city': comp.get('city') or comp.get('town') or comp.get('village', ''),
                'country': comp.get('country', ''),
                'formatted': r.get('formatted', ''),
            })
        else:
            return jsonify({'error': 'No results found'}), 404

    except Exception as e:
        logger.error("Geocode proxy error: %s", e)
        return jsonify({
            'lat': None,
            'lon': None,
            'city': '',
            'country': '',
            'formatted': '',
            'configured': True,
            'note': 'Geocoding service unavailable'
        }), 200
