"""
TalkToText Pro-v1.0 Engine - Main Pipeline
Professional audio processing and transcription system with AI-powered summarization.
"""

import os
import shutil
import datetime
from dotenv import load_dotenv
from bson.objectid import ObjectId

import config
from core.audio_processor import AudioProcessor
from core.text_processor import TextProcessor
from core.ai_services import AIServices
from core.database_manager import DatabaseManager
from core.message_system import MessageSystem, MessageCode
from utils.custom_exceptions import ProjectBaseException, FileSystemError, IrrelevantContentError

class MainPipeline:
    """
    Main processing pipeline that orchestrates audio processing, transcription, and summarization.
    """
    
    def __init__(self, api_key: str, audio_quality: str, ffmpeg_path: str, ffprobe_path: str, db_manager: DatabaseManager):
        """
        Initialize pipeline with all required components and services.
        """
        bitrate = config.QUALITY_PRESETS.get(audio_quality, config.QUALITY_PRESETS["medium"])
        
        self.audio_processor = AudioProcessor(
            bitrate=bitrate, 
            ffmpeg_path=ffmpeg_path, 
            ffprobe_path=ffprobe_path
        )
        self.text_processor = TextProcessor()
        self.ai_services = AIServices(api_key=api_key)
        self.db_manager = db_manager

    def _execute_step(self, job_id: ObjectId, stage: str, step_name: str, func, *args, **kwargs):
        """
        Execute and log pipeline step with timing and error handling.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc)
        message = ""
        
        try:
            result = func(*args, **kwargs)
            status = "completed"
            
            if isinstance(result, tuple) and len(result) == 2:
                message = result[1]
                result = result[0]
                
        except Exception as e:
            end_time = datetime.datetime.now(datetime.timezone.utc)
            self.db_manager.add_log_entry(job_id, stage, step_name, "failed", start_time, end_time, str(e))
            raise
        
        end_time = datetime.datetime.now(datetime.timezone.utc)
        self.db_manager.add_log_entry(job_id, stage, step_name, status, start_time, end_time, message)
        return result

    def _handle_url_input(self, url: str, temp_dir: str, job_id: ObjectId) -> tuple[str, bool]:
        """
        Handle URL input with metadata analysis and smart screening.
        """
        metadata = self._execute_step(job_id, "setup", "get_metadata", self.audio_processor.get_url_metadata, url)
        
        if not metadata:
            downloaded_file = self._execute_step(job_id, "audio_processing", "download", 
                                                self.audio_processor.download_audio_from_url, url, temp_dir)
            return downloaded_file, True
        
        decision = self._execute_step(job_id, "setup", "classify_metadata", 
                                    self.ai_services.classify_url_metadata, metadata)
        
        if decision == "reject":
            raise IrrelevantContentError("URL rejected by AI metadata analysis.")
        
        downloaded_file = self._execute_step(job_id, "audio_processing", "download", 
                                           self.audio_processor.download_audio_from_url, url, temp_dir)
        
        return downloaded_file, (decision != "proceed")

    def run(self, input_path_or_url: str, user_id: ObjectId, audio_quality: str = "medium", target_language_name: str = None, job_id_for_temp_dir: str = None):
        """
        Execute complete processing pipeline for given input.
        The temporary directory is now managed by the calling function to ensure cleanup.
        """
        job_id = None
        
        try:
            # Dynamically set audio quality for this specific job
            self.audio_processor.bitrate = config.QUALITY_PRESETS.get(audio_quality, config.QUALITY_PRESETS["medium"])

            is_url = input_path_or_url.strip().startswith(('http://', 'https://'))
            source_type = "url" if is_url else "file"
            
            # Use the provided job_id from app.py to create a job record in the DB
            job_id_obj = self.db_manager.create_job(user_id, source_type, input_path_or_url)
            job_id = job_id_obj # Keep ObjectId for DB operations

            MessageSystem.log_progress(MessageCode.PIPELINE_START, job_id=job_id)
            
            # The temp directory path is now determined by the job_id from the calling function
            temp_dir = f"temp_{job_id_for_temp_dir}"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            self.db_manager.update_job_status(job_id, "processing_audio")
            
            if is_url:
                initial_audio_file, needs_audio_screening = self._handle_url_input(input_path_or_url, temp_dir, job_id)
            else:
                if not os.path.exists(input_path_or_url):
                    raise FileSystemError("Input file not found")
                initial_audio_file = input_path_or_url
                needs_audio_screening = True
            
            if needs_audio_screening:
                screening_clip = self._execute_step(
                    job_id, "audio_processing", "extract_screening_clip",
                    self.audio_processor.extract_initial_segment, 
                    initial_audio_file, 
                    os.path.join(temp_dir, "screening.mp3"), 
                    config.PRE_SCREEN_DURATION_SECONDS
                )
                self._execute_step(
                    job_id, "audio_processing", "check_relevance",
                    self.ai_services.check_content_relevance, 
                    screening_clip
                )
            
            converted_audio = self._execute_step(
                job_id, "audio_processing", "standardize_audio",
                self.audio_processor.convert_to_standard_mp3,
                initial_audio_file,
                os.path.join(temp_dir, "converted.mp3")
            )
            
            cleaned_audio = self._execute_step(
                job_id, "audio_processing", "clean_audio",
                self.audio_processor.clean_audio,
                converted_audio,
                os.path.join(temp_dir, "cleaned.mp3")
            )
            
            audio_chunks = self._execute_step(
                job_id, "audio_processing", "chunk_audio",
                self.audio_processor.chunk_audio,
                cleaned_audio,
                os.path.join(temp_dir, "chunks")
            )
            
            self.db_manager.update_job_status(job_id, "transcribing")
            raw_transcript = self._execute_step(
                job_id, "transcription", "transcribe",
                self.ai_services.transcribe_audio_files,
                audio_chunks
            )
            self.db_manager.update_job_processing_data(job_id, {"transcription.rawTranscript": raw_transcript})
            
            self.db_manager.update_job_status(job_id, "processing_text")
            cleaned_transcript = self._execute_step(
                job_id, "text_processing", "clean_transcript",
                self.text_processor.clean_transcript,
                raw_transcript
            )
            self.db_manager.update_job_processing_data(job_id, {"transcription.cleanedTranscript": cleaned_transcript})
            
            detected_lang = self._execute_step(
                job_id, "text_processing", "detect_language",
                self.ai_services.detect_language,
                cleaned_transcript
            )
            self.db_manager.update_job_processing_data(job_id, {"language.detectedLanguage": detected_lang})
            
            if detected_lang != 'en':
                english_transcript = self._execute_step(
                    job_id, "text_processing", "translate_to_english",
                    self.ai_services.translate_text,
                    cleaned_transcript
                )
            else:
                english_transcript = cleaned_transcript
            self.db_manager.update_job_processing_data(job_id, {
                "language.wasTranslated": detected_lang != 'en',
                "language.finalTranscript": english_transcript
            })
            
            self.db_manager.update_job_status(job_id, "summarizing")
            final_summary = self._execute_step(
                job_id, "summarization", "generate_summary",
                self.ai_services.summarize_text,
                english_transcript
            )
            self.db_manager.update_job_processing_data(job_id, {"summary.fullReport": final_summary})
            
            translated_summary = None
            if target_language_name and target_language_name.lower() != 'auto':
                translated_summary = self._execute_step(
                    job_id, "final_translation", f"translate_summary_to_{target_language_name}",
                    self.ai_services.translate_summary,
                    final_summary,
                    target_language_name
                )
                if translated_summary:
                    self.db_manager.update_job_processing_data(job_id, {
                        "summary.translatedReport": {"language": target_language_name, "text": translated_summary}
                    })

            final_results = {
                "audio": {"qualityPreset": audio_quality, "wasChunked": len(audio_chunks) > 1},
                "transcription": {"rawTranscript": raw_transcript, "cleanedTranscript": cleaned_transcript},
                "language": {"detectedLanguage": detected_lang, "wasTranslated": detected_lang != 'en', "finalTranscript": english_transcript},
                "summary": {"fullReport": final_summary}
            }
            
            if translated_summary and target_language_name:
                final_results["summary"]["translatedReport"] = {"language": target_language_name, "text": translated_summary}

            self.db_manager.save_job_results(job_id, final_results)
            self.db_manager.update_job_status(job_id, "completed")
            MessageSystem.log_success(MessageCode.PIPELINE_SUCCESS)
            return final_results

        except (ProjectBaseException, IrrelevantContentError) as e:
            MessageSystem.log_error(MessageCode.OPERATION_FAILED, error=str(e))
            if job_id:
                self.db_manager.update_job_status(job_id, "failed", "pipeline_error", str(e))
            raise
                
        except Exception as e:
            MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=str(e))
            if job_id:
                self.db_manager.update_job_status(job_id, "failed", "critical_error", str(e))
            raise