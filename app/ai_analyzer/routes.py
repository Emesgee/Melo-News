# app/ai_analyzer/routes.py
"""
AI-powered content analysis routes using Azure AI services
Analyzes images/videos and auto-fills upload form fields
"""

from flask import Blueprint, request, jsonify
import os
import tempfile
import mimetypes
from werkzeug.utils import secure_filename

# Azure AI imports
try:
    from azure.ai.vision.imageanalysis import ImageAnalysisClient
    from azure.ai.vision.imageanalysis.models import VisualFeatures
    from azure.core.credentials import AzureKeyCredential
    import azure.cognitiveservices.speech as speechsdk
    from openai import AzureOpenAI
except ImportError:
    print("Warning: Azure AI SDKs not installed. Install with: pip install azure-ai-vision-imageanalysis azure-cognitiveservices-speech openai")

ai_analyzer_bp = Blueprint('ai_analyzer', __name__)

# Azure Configuration (from environment variables)
VISION_ENDPOINT = os.getenv('AZURE_VISION_ENDPOINT', '')
VISION_KEY = os.getenv('AZURE_VISION_KEY', '')
SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY', '')
SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION', 'eastus')
OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY', '')
OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')


@ai_analyzer_bp.route('/analyze', methods=['POST'])
def analyze_media():
    """
    Analyze uploaded media (image/video) and return structured metadata
    Returns: {
        "title": "Auto-generated title",
        "tags": "tag1, tag2, tag3",
        "subject": "Description/summary",
        "city": "Detected city",
        "country": "Detected country",
        "confidence": 0.85
    }
    """
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Save to temp location
    filename = secure_filename(file.filename)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    file.save(temp_path)
    
    try:
        # Detect file type
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type and mime_type.startswith('image'):
            result = analyze_image(temp_path)
        elif mime_type and mime_type.startswith('video'):
            result = analyze_video(temp_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def analyze_image(image_path):
    """Analyze image using Azure Computer Vision"""
    
    if not VISION_ENDPOINT or not VISION_KEY:
        # Fallback: basic analysis without Azure
        return {
            'title': 'News Image',
            'tags': 'news, breaking',
            'subject': 'Image uploaded for news story',
            'city': '',
            'country': '',
            'confidence': 0.5,
            'note': 'Azure Vision not configured - using fallback'
        }
    
    try:
        # Initialize Azure Computer Vision client
        client = ImageAnalysisClient(
            endpoint=VISION_ENDPOINT,
            credential=AzureKeyCredential(VISION_KEY)
        )
        
        # Analyze image
        with open(image_path, 'rb') as img:
            result = client.analyze(
                image_data=img.read(),
                visual_features=[
                    VisualFeatures.CAPTION,
                    VisualFeatures.TAGS,
                    VisualFeatures.OBJECTS,
                    VisualFeatures.READ,  # OCR for text
                    VisualFeatures.SMART_CROPS
                ],
                language='en'
            )
        
        # Extract information
        caption = result.caption.text if result.caption else ''
        
        # Extract tags safely
        tags = []
        if result.tags:
            for tag in list(result.tags)[:10]:
                if isinstance(tag, str):
                    tags.append(tag)
                elif hasattr(tag, 'name'):
                    tags.append(tag.name)
        
        # Extract objects safely
        objects = []
        if result.objects:
            for obj in result.objects:
                if isinstance(obj, str):
                    objects.append(obj)
                elif hasattr(obj, 'tags') and obj.tags and len(obj.tags) > 0:
                    first_tag = obj.tags[0]
                    if isinstance(first_tag, str):
                        objects.append(first_tag)
                    elif hasattr(first_tag, 'name'):
                        objects.append(first_tag.name)
        
        # Extract text from image (for location detection)
        detected_text = []
        if result.read and result.read.blocks:
            for block in result.read.blocks:
                for line in block.lines:
                    detected_text.append(line.text)
        
        # Generate title from caption
        title = caption.capitalize() if caption else 'Breaking News'
        
        # Combine tags and objects
        all_tags = list(set(tags + objects))
        tags_str = ', '.join(all_tags[:8])
        
        # Use GPT-4 Vision to extract location if available
        city, country = extract_location_from_context(caption, detected_text, all_tags)
        
        return {
            'title': title,
            'tags': tags_str,
            'subject': caption,
            'city': city,
            'country': country,
            'confidence': result.caption.confidence if result.caption else 0.7,
            'detected_text': ' '.join(detected_text) if detected_text else None
        }
    
    except Exception as e:
        return {
            'title': 'News Image',
            'tags': 'news',
            'subject': f'Image analysis error: {str(e)}',
            'city': '',
            'country': '',
            'confidence': 0.3,
            'error': str(e)
        }


def analyze_video(video_path):
    """Analyze video using frame extraction + speech recognition"""
    
    if not SPEECH_KEY or not SPEECH_REGION:
        return {
            'title': 'News Video',
            'tags': 'video, news',
            'subject': 'Video uploaded for news story',
            'city': '',
            'country': '',
            'confidence': 0.5,
            'note': 'Azure Speech not configured - using fallback'
        }
    
    try:
        # Extract audio and transcribe
        transcription = transcribe_video_audio(video_path)
        
        # Extract first frame for visual analysis
        # (You'll need opencv-python: pip install opencv-python)
        try:
            import cv2
            video = cv2.VideoCapture(video_path)
            success, frame = video.read()
            if success:
                frame_path = video_path + '_frame.jpg'
                cv2.imwrite(frame_path, frame)
                video.release()
                
                # Analyze the frame
                visual_data = analyze_image(frame_path)
                os.remove(frame_path)
            else:
                visual_data = {}
        except ImportError:
            visual_data = {}
        
        # Combine transcription and visual analysis
        title = visual_data.get('title', 'Breaking News Video')
        
        # Extract keywords from transcription
        keywords = extract_keywords_from_text(transcription)
        existing_tags = visual_data.get('tags', '').split(', ')
        combined_tags = list(set(existing_tags + keywords))[:8]
        
        # Extract location from transcription
        city, country = extract_location_from_text(transcription)
        
        return {
            'title': title,
            'tags': ', '.join(combined_tags),
            'subject': transcription[:500] if transcription else visual_data.get('subject', ''),
            'city': city or visual_data.get('city', ''),
            'country': country or visual_data.get('country', ''),
            'confidence': 0.75,
            'transcription': transcription
        }
    
    except Exception as e:
        return {
            'title': 'News Video',
            'tags': 'video, breaking news',
            'subject': f'Video analysis error: {str(e)}',
            'city': '',
            'country': '',
            'confidence': 0.3,
            'error': str(e)
        }


def transcribe_video_audio(video_path):
    """Extract audio from video and transcribe using Azure Speech-to-Text"""
    
    try:
        # Extract audio to WAV format
        # (Requires ffmpeg: pip install ffmpeg-python)
        import ffmpeg
        audio_path = video_path + '_audio.wav'
        
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ac=1, ar='16000')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        
        # Transcribe using Azure Speech SDK
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
        
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        result = speech_recognizer.recognize_once()
        
        # Clean up
        os.remove(audio_path)
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        else:
            return ''
    
    except Exception as e:
        print(f"Transcription error: {e}")
        return ''


def extract_location_from_context(caption, text_list, tags):
    """Use GPT-4 to extract location from context"""
    
    if not OPENAI_ENDPOINT or not OPENAI_KEY:
        return '', ''
    
    try:
        client = AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=OPENAI_ENDPOINT
        )
        
        context = f"Caption: {caption}\nDetected text: {' '.join(text_list)}\nTags: {', '.join(tags)}"
        
        response = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a location extraction assistant. Extract city and country from the given context. Respond ONLY in JSON format: {\"city\": \"CityName\", \"country\": \"CountryName\"}. If no location found, return empty strings."},
                {"role": "user", "content": context}
            ],
            temperature=0.3
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result.get('city', ''), result.get('country', '')
    
    except Exception as e:
        print(f"Location extraction error: {e}")
        return '', ''


def extract_location_from_text(text):
    """Extract location from transcribed text using NLP"""
    # Placeholder - can use spaCy or Azure Text Analytics
    return '', ''


def extract_keywords_from_text(text):
    """Extract keywords from text"""
    # Simple keyword extraction (you can enhance with Azure Text Analytics)
    if not text:
        return []
    
    # Basic stopwords removal
    stopwords = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
    words = text.lower().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    
    # Return top 5 unique keywords
    return list(set(keywords))[:5]
