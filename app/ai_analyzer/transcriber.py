# app/ai_analyzer/transcriber.py
"""
Continuous multilingual transcription for citizen journalism uploads.

Uses OpenAI Whisper API for full audio transcription with:
- Arabic, Hebrew, English (and 90+ other languages) support
- Timestamped segments for timeline alignment
- Language auto-detection
- Audio extraction from video via ffmpeg

Falls back to Azure Speech SDK if OpenAI key is unavailable.
"""

import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Max file size for Whisper API (25MB)
WHISPER_MAX_BYTES = 25 * 1024 * 1024


def _extract_audio(video_path: str) -> Optional[str]:
    """
    Extract audio track from a video file as WAV (16kHz mono).

    Returns path to temp WAV file, or None on failure.
    Caller is responsible for deleting the temp file.
    """
    try:
        import ffmpeg
    except ImportError:
        logger.warning("ffmpeg-python not installed — cannot extract audio")
        return None

    audio_path = os.path.join(tempfile.gettempdir(), f"melo_audio_{os.getpid()}.wav")

    try:
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ac=1, ar='16000')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)

        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            logger.info("Audio extracted: %s (%.1f KB)",
                        audio_path, os.path.getsize(audio_path) / 1024)
            return audio_path
        else:
            logger.warning("Audio extraction produced empty file")
            return None
    except Exception as e:
        logger.error("Audio extraction failed: %s", e)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return None


def transcribe_with_whisper(audio_path: str) -> dict:
    """
    Transcribe audio using OpenAI Whisper API.

    Parameters
    ----------
    audio_path : str — path to audio file (WAV, MP3, M4A, etc.)

    Returns
    -------
    dict:
        text      : str          — full transcription
        language  : str          — detected language code (e.g. 'ar', 'he', 'en')
        segments  : list[dict]   — [{start: float, end: float, text: str}, ...]
        duration  : float        — total audio duration in seconds
        method    : str          — 'whisper'
    """
    empty = {'text': '', 'language': '', 'segments': [], 'duration': 0, 'method': 'none'}

    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_KEY')
    if not api_key:
        logger.warning("No OpenAI API key — Whisper transcription unavailable")
        return empty

    # Check file size
    file_size = os.path.getsize(audio_path)
    if file_size > WHISPER_MAX_BYTES:
        logger.warning("Audio file too large for Whisper API (%.1f MB > 25 MB)",
                        file_size / (1024 * 1024))
        return empty

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        with open(audio_path, 'rb') as audio_file:
            response = client.audio.transcriptions.create(
                model='whisper-1',
                file=audio_file,
                response_format='verbose_json',
                timestamp_granularities=['segment'],
            )

        # Extract segments
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                segments.append({
                    'start': round(getattr(seg, 'start', 0), 2),
                    'end': round(getattr(seg, 'end', 0), 2),
                    'text': getattr(seg, 'text', '').strip(),
                })

        result = {
            'text': getattr(response, 'text', '').strip(),
            'language': getattr(response, 'language', ''),
            'segments': segments,
            'duration': round(getattr(response, 'duration', 0), 2),
            'method': 'whisper',
        }

        logger.info("Whisper transcription: %d chars, language=%s, %d segments, %.1fs",
                     len(result['text']), result['language'],
                     len(result['segments']), result['duration'])
        return result

    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        return empty


def transcribe_with_azure(audio_path: str) -> dict:
    """
    Fallback: transcribe using Azure Speech SDK (continuous recognition).

    Improves on the old recognize_once() by using continuous recognition
    to capture the full audio, not just the first utterance.
    """
    empty = {'text': '', 'language': '', 'segments': [], 'duration': 0, 'method': 'none'}

    speech_key = os.getenv('AZURE_SPEECH_KEY', '')
    speech_region = os.getenv('AZURE_SPEECH_REGION', 'eastus')

    if not speech_key:
        logger.warning("No Azure Speech key — fallback transcription unavailable")
        return empty

    try:
        import azure.cognitiveservices.speech as speechsdk
        import threading

        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=speech_region
        )
        # Enable multi-language detection for Arabic/Hebrew/English
        speech_config.speech_recognition_language = "ar-SA"
        auto_detect = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=["ar-SA", "he-IL", "en-US"]
        )

        audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            auto_detect_source_language_config=auto_detect,
            audio_config=audio_config,
        )

        all_text = []
        done = threading.Event()

        def on_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                all_text.append(evt.result.text)

        def on_stopped(evt):
            done.set()

        def on_canceled(evt):
            done.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_stopped)
        recognizer.canceled.connect(on_canceled)

        recognizer.start_continuous_recognition()
        done.wait(timeout=300)  # 5 min max
        recognizer.stop_continuous_recognition()

        full_text = ' '.join(all_text).strip()

        result = {
            'text': full_text,
            'language': 'auto',
            'segments': [],
            'duration': 0,
            'method': 'azure_speech',
        }

        logger.info("Azure Speech transcription: %d chars", len(full_text))
        return result

    except ImportError:
        logger.warning("Azure Speech SDK not installed")
        return empty
    except Exception as e:
        logger.error("Azure Speech transcription failed: %s", e)
        return empty


def transcribe(video_or_audio_path: str, is_video: bool = True) -> dict:
    """
    High-level transcription entry point.

    1. If video, extract audio first
    2. Try Whisper API (best quality, multilingual)
    3. Fall back to Azure Speech if Whisper unavailable
    4. Return structured result

    Parameters
    ----------
    video_or_audio_path : str  — path to video or audio file
    is_video            : bool — True if input is video (needs audio extraction)

    Returns
    -------
    dict with keys: text, language, segments, duration, method
    """
    audio_path = None
    temp_audio = False

    try:
        if is_video:
            audio_path = _extract_audio(video_or_audio_path)
            temp_audio = True
            if not audio_path:
                return {'text': '', 'language': '', 'segments': [],
                        'duration': 0, 'method': 'none'}
        else:
            audio_path = video_or_audio_path

        # Try Whisper first (state-of-the-art)
        result = transcribe_with_whisper(audio_path)
        if result['text']:
            return result

        # Fallback to Azure Speech (continuous recognition)
        result = transcribe_with_azure(audio_path)
        if result['text']:
            return result

        logger.warning("All transcription methods failed")
        return {'text': '', 'language': '', 'segments': [],
                'duration': 0, 'method': 'none'}

    finally:
        # Clean up temp audio file
        if temp_audio and audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass
