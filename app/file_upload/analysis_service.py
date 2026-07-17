import os
import logging
import threading
from flask import current_app
from app.models import db, FileUpload
from app.ai_analyzer.exif_extractor import extract_exif
from app.ai_analyzer.transcriber import transcribe
from app.ai_analyzer.confidence import score_and_classify

logger = logging.getLogger(__name__)

def _run_analysis(app, file_upload_id, local_file_path):
    """
    Internal function to run analysis within the app context.
    """
    with app.app_context():
        try:
            logger.info(f"Starting background analysis for FileUpload ID {file_upload_id}")
            
            # 1. Fetch the record
            upload_record = FileUpload.query.get(file_upload_id)
            if not upload_record:
                logger.error(f"FileUpload {file_upload_id} not found")
                return

            upload_record.analysis_status = 'PROCESSING'
            db.session.commit()

            # 2. Determine File Type
            ext = os.path.splitext(local_file_path)[1].lower()
            is_image = ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp']
            is_video = ext in ['.mp4', '.mov', '.avi', '.mkv']
            is_audio = ext in ['.mp3', '.wav', '.m4a', '.aac']

            exif_result = {}
            
            # 3. Extract EXIF (Images)
            if is_image:
                logger.info(f"Extracting EXIF for {local_file_path}")
                exif_result = extract_exif(local_file_path)
                
                # Store EXIF data
                # We need to ensure it's JSON serializable (extract_exif returns dict with basic types)
                upload_record.exif_data = exif_result
                
                # Update location if found
                if exif_result.get('lat') and exif_result.get('lon'):
                    upload_record.lat = exif_result['lat']
                    upload_record.lon = exif_result['lon']
                    logger.info(f"Updated location from EXIF: {upload_record.lat}, {upload_record.lon}")

            # 4. Transcribe (Video/Audio)
            transcription_result = {}
            if is_video or is_audio:
                logger.info("Starting transcription...")
                # is_video=True if video file (needs audio extraction)
                transcription_result = transcribe(local_file_path, is_video=is_video)
                
                text = transcription_result.get('text', '')
                if text:
                    upload_record.transcription = text
                    logger.info(f"Transcription complete: {len(text)} chars")
                else:
                    logger.info("Transcription returned empty text")

            # 5. Calculate Confidence Score & Severity
            # Map data to what the confidence module expects
            story_data = {
                'message': upload_record.transcription or upload_record.title or '',
                'image_links': [upload_record.file_path] if is_image else [],
                'video_links': [upload_record.file_path] if is_video else [],
                'lat': upload_record.lat,
                'lon': upload_record.lon,
                'source': 'citizen_upload',
                'source_count': 1,
                'time': upload_record.upload_date.isoformat() if upload_record.upload_date else None,
                # Citizen journalism specific boosts
                'exif_gps_match': exif_result.get('has_gps', False),
                'exif_has_timestamp': exif_result.get('has_timestamp', False),
                'has_device_info': bool(exif_result.get('device')),
            }
            
            logger.info("Calculating confidence score...")
            classification = score_and_classify(story_data)
            
            upload_record.confidence_score = classification['confidence_score']
            upload_record.severity = classification['severity']
            
            upload_record.analysis_status = 'COMPLETED'
            db.session.commit()
            logger.info(f"Analysis completed for FileUpload {file_upload_id}. Score: {upload_record.confidence_score}")

        except Exception as e:
            logger.error(f"Error analyzing FileUpload {file_upload_id}: {e}", exc_info=True)
            try:
                # Re-fetch in case session was rolled back
                upload_record = FileUpload.query.get(file_upload_id)
                if upload_record:
                    upload_record.analysis_status = 'FAILED'
                    db.session.commit()
            except Exception as db_e:
                logger.error(f"Failed to update status to FAILED: {db_e}")
        finally:
            # Cleanup local file
            if os.path.exists(local_file_path):
                try:
                    os.remove(local_file_path)
                    logger.info(f"Deleted temp file: {local_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {local_file_path}: {e}")

def start_analysis_thread(file_upload_id, local_file_path):
    """
    Start the analysis in a background thread.
    """
    # Capture the real app object (not the proxy) to pass to the thread
    app = current_app._get_current_object()
    
    thread = threading.Thread(
        target=_run_analysis,
        args=(app, file_upload_id, local_file_path)
    )
    thread.daemon = True
    thread.start()
