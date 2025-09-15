"""
AI Services Module for TalkToText Pro-v1.0 Engine
Handles all AI-powered operations including transcription, translation, and summarization.
"""

import os
from openai import OpenAI, APIError
from typing import List, Dict, Any
from langdetect import detect, LangDetectException

from utils.custom_exceptions import TranscriptionError, ApiServiceError, LanguageDetectionError, IrrelevantContentError
from core.message_system import MessageSystem, MessageCode
from core.text_processor import TextProcessor
import config

class AIServices:
    """
    Handles all AI-powered operations using OpenAI services and language detection.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize AI Services with OpenAI client and text processor.
        
        Args:
            api_key (str): OpenAI API key for authentication
            
        Raises:
            ApiServiceError: If OpenAI client initialization fails
        """
        try:
            self.client = OpenAI(api_key=api_key)
            self.internal_text_processor = TextProcessor()
        except Exception as e:
            raise ApiServiceError(f"Failed to initialize OpenAI client. Is the API key valid? Error: {e}")
        
    def classify_url_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Use GPT-5 nano to classify URL content suitability based on metadata analysis.
        
        Args:
            metadata (Dict[str, Any]): URL metadata including title, description, tags
            
        Returns:
            str: Classification result ('proceed', 'reject', or 'uncertain')
        """
        MessageSystem.log_progress(MessageCode.AI_METADATA_ANALYSIS)
        
        title = metadata.get("title", "N/A")
        description = metadata.get("description", "N/A")
        
        # Limit description length to prevent API token issues
        if len(description) > 1500:
            description = description[:1500] + "..."
            
        tags = metadata.get("tags", [])
        
        try:
            prompt = config.URL_METADATA_CLASSIFICATION_PROMPT.format(
                title=title,
                description=description,
                tags=", ".join(tags) if tags else "N/A"
            )
            
            response = self.client.chat.completions.create(
                model=config.CLASSIFICATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                # temperature=0.0
            )
            
            decision = response.choices[0].message.content.strip().lower()

            # Validate AI response
            if decision in ["proceed", "reject", "uncertain"]:
                MessageSystem.log_success(MessageCode.AI_METADATA_ANALYSIS_COMPLETE, decision=decision.upper())
                return decision
            else:
                MessageSystem.log_warning(MessageCode.AI_METADATA_ANALYSIS_COMPLETE, 
                                        decision="UNCERTAIN (invalid AI response)")
                return "uncertain"

        except APIError as e:
            MessageSystem.log_warning(MessageCode.AI_METADATA_ANALYSIS_COMPLETE, 
                                    decision="UNCERTAIN (API error)", details=str(e))
            return "uncertain"
        
    def check_content_relevance(self, audio_clip_path: str):
        """
        Transcribe short audio clip and classify content relevance using GPT-5 nano.
        
        Args:
            audio_clip_path (str): Path to audio clip for analysis
            
        Raises:
            IrrelevantContentError: If content is classified as irrelevant
        """
        MessageSystem.log_progress(MessageCode.AI_CONTENT_SCREENING)
        
        try:
            # Transcribe the screening clip
            with open(audio_clip_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=config.WHISPER_MODEL,
                    file=audio_file
                ).text.strip()

            # Handle empty transcription (likely music or silence)
            if not transcription:
                raise IrrelevantContentError("The beginning of the audio contains no discernible speech.")

            # Classify transcript content using GPT-4o-mini
            prompt = config.CONTENT_CLASSIFICATION_PROMPT.format(text=transcription)
            response = self.client.chat.completions.create(
                model=config.CLASSIFICATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                # temperature=0.0
            )
            
            decision = response.choices[0].message.content.strip().lower()

            if 'irrelevant' in decision:
                raise IrrelevantContentError(
                    "Content identified as irrelevant (e.g., movie, music, anime). Processing halted."
                )
            
            MessageSystem.log_success(MessageCode.AI_CONTENT_SCREENING_PASSED)

        except APIError as e:
            MessageSystem.log_warning(MessageCode.AI_CONTENT_SCREENING, 
                                    details=f"API error during screening: {e}. Proceeding with caution.")
        except TranscriptionError as e:
            MessageSystem.log_warning(MessageCode.AI_CONTENT_SCREENING, 
                                    details=f"Transcription failed: {e}. Proceeding with caution.")

    def translate_summary(self, text_to_translate: str, target_language: str) -> str:
        """
        Translate final summary to specified target language using GPT-5 mini.
        
        Args:
            text_to_translate (str): Summary text to translate
            target_language (str): Target language name (e.g., "Arabic", "Spanish")
            
        Returns:
            str: Translated summary text
            
        Raises:
            ApiServiceError: If translation API call fails
        """
        MessageSystem.log_progress(MessageCode.AI_TRANSLATION_START, language=target_language)
        
        try:
            prompt = config.SUMMARY_TRANSLATION_PROMPT.format(target_language=target_language)
            response = self.client.chat.completions.create(
                model=config.TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text_to_translate}
                ],
                # temperature=0.2
            )
            
            translated_text = response.choices[0].message.content.strip()
            MessageSystem.log_success(MessageCode.AI_TRANSLATION_SUCCESS)
            return translated_text
            
        except APIError as e:
            raise ApiServiceError(f"API error during summary translation: {e}")

    def transcribe_audio_files(self, audio_files: List[str]) -> str:
        """
        Transcribe list of audio files using OpenAI Whisper and merge results.
        
        Args:
            audio_files (List[str]): List of audio file paths to transcribe
            
        Returns:
            str: Complete merged transcript
            
        Raises:
            TranscriptionError: If any transcription fails
        """
        MessageSystem.log_progress(MessageCode.TRANSCRIPTION_START)
        
        full_transcript = []
        total_files = len(audio_files)
        
        for i, file_path in enumerate(audio_files, 1):
            MessageSystem.log_progress(MessageCode.TRANSCRIPTION_CHUNK_PROGRESS,
                                     current=i, total=total_files, filename=os.path.basename(file_path))
            try:
                with open(file_path, "rb") as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        model=config.WHISPER_MODEL,
                        file=audio_file
                    )
                full_transcript.append(transcription.text.strip())
                
            except APIError as e:
                raise TranscriptionError(f"OpenAI API error during transcription of {file_path}: {e}")
            except Exception as e:
                raise TranscriptionError(f"Unexpected error during transcription of {file_path}: {e}")

        MessageSystem.log_success(MessageCode.TRANSCRIPTION_SUCCESS)
        return "\n".join(full_transcript)

    def detect_language(self, text: str) -> str:
        """
        Detect text language using local langdetect library.
        
        Args:
            text (str): Text to analyze for language detection
            
        Returns:
            str: Detected language code (e.g., 'en', 'ar', 'es')
            
        Raises:
            LanguageDetectionError: If language cannot be determined
        """
        MessageSystem.log_progress(MessageCode.TEXT_LANGUAGE_DETECTED, language="analyzing...")
        
        try:
            # Use first 500 characters for faster and more accurate detection
            sample = text[:500]
            detected_lang = detect(sample)
            
            MessageSystem.log_success(MessageCode.TEXT_LANGUAGE_DETECTED, language=detected_lang)
            return detected_lang
            
        except LangDetectException:
            raise LanguageDetectionError("Could not determine the language of the provided text.")

    def translate_text(self, text_to_translate: str) -> str:
        """
        Translate large text to English using GPT-5 mini with intelligent chunking.
        
        Args:
            text_to_translate (str): Text to translate to English
            
        Returns:
            str: English translation of the input text
            
        Raises:
            ApiServiceError: If any translation API call fails
        """
        MessageSystem.log_progress(MessageCode.TEXT_TRANSLATION_START)
        
        chunks = self.internal_text_processor.split_into_chunks(text_to_translate)
        if not chunks:
            return ""

        translated_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks, 1):
            if total_chunks > 1:
                MessageSystem.log_progress(MessageCode.TRANSCRIPTION_CHUNK_PROGRESS,
                                         current=i, total=total_chunks, filename="translation chunk")
            try:
                response = self.client.chat.completions.create(
                    model=config.TRANSLATION_MODEL,
                    messages=[
                        {"role": "system", "content": config.TRANSLATION_PROMPT},
                        {"role": "user", "content": chunk}
                    ],
                    # temperature=0.1
                )
                translated_chunks.append(response.choices[0].message.content.strip())
                
            except APIError as e:
                raise ApiServiceError(f"API error during translation of chunk {i}: {e}")
        
        MessageSystem.log_success(MessageCode.TEXT_TRANSLATION_SUCCESS)
        return " ".join(translated_chunks)

    def summarize_text(self, text: str) -> str:
        """
        Generate comprehensive summary using hierarchical summarization with SRS compliance.
        
        Args:
            text (str): Text to summarize
            
        Returns:
            str: Structured summary following SRS format
            
        Raises:
            ApiServiceError: If summarization API calls fail
        """
        MessageSystem.log_progress(MessageCode.AI_SUMMARIZATION_START)
        
        chunks = self.internal_text_processor.split_into_chunks(text)
        if not chunks:
            return "Could not generate a summary because the input text was empty after cleaning."

        summaries = []
        total_chunks = len(chunks)
        
        # Summarize each chunk individually
        for i, chunk in enumerate(chunks, 1):
            MessageSystem.log_progress(MessageCode.AI_SUMMARIZATION_CHUNK, current=i, total=total_chunks)
            
            try:
                response = self.client.chat.completions.create(
                    model=config.SUMMARIZATION_MODEL,
                    messages=[
                        {"role": "system", "content": config.SRS_COMPLIANT_PROMPT},
                        {"role": "user", "content": f"Please summarize this chunk of the meeting transcript:\n\n---\n{chunk}\n---"}
                    ]
                )
                summaries.append(response.choices[0].message.content.strip())
                
            except APIError as e:
                raise ApiServiceError(f"API error while summarizing chunk {i}: {e}")

        # Return single summary if only one chunk
        if len(summaries) == 1:
            MessageSystem.log_success(MessageCode.AI_SUMMARIZATION_SUCCESS)
            return summaries[0]

        # Merge multiple summaries into final coherent report
        MessageSystem.log_progress(MessageCode.AI_SUMMARIZATION_MERGE)
        
        merged_summaries = "\n\n---\n[End of Part]\n---\n\n".join(summaries)

        try:
            final_response = self.client.chat.completions.create(
                model=config.CHAT_MODEL,
                messages=[
                    {"role": "system", "content": config.SRS_COMPLIANT_PROMPT},
                    {"role": "user", "content": (
                        "You have been provided with summaries from different parts of a single meeting. "
                        "Synthesize them into one final, cohesive summary that follows all required output sections "
                        "(Abstract Summary, Key Points, etc.). Ensure the final output is a single, unified document.\n\n"
                        f"---\n{merged_summaries}\n---"
                    )}
                ]
            )
            
            MessageSystem.log_success(MessageCode.AI_SUMMARIZATION_SUCCESS)
            return final_response.choices[0].message.content.strip()
            
        except APIError as e:
            raise ApiServiceError(f"API error during final merge-summarization step: {e}")
