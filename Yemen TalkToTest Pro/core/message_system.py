"""
Professional Message System for TalkToText Pro-v1.0 Engine
Provides centralized message management with standardized status codes and responses.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import datetime

class MessageType(Enum):
    """Enumeration for different types of messages."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"

class MessageCode(Enum):
    """Standardized message codes for different operations."""
    # Database Operations (1000-1099)
    DB_CONNECTION_SUCCESS = 1000
    DB_CONNECTION_FAILED = 1001
    DB_USER_CREATED = 1002
    DB_USER_EXISTS = 1003
    DB_JOB_CREATED = 1004
    DB_JOB_UPDATED = 1005
    DB_RESULTS_SAVED = 1006
    
    # Audio Processing (2000-2099)
    AUDIO_DOWNLOAD_START = 2001
    AUDIO_DOWNLOAD_SUCCESS = 2002
    AUDIO_DOWNLOAD_FAILED = 2003
    AUDIO_DOWNLOAD_PROGRESS = 2004
    AUDIO_CONVERSION_START = 2005
    AUDIO_CONVERSION_SUCCESS = 2006
    AUDIO_STANDARDIZATION_SUCCESS = 2007
    AUDIO_CLEANING_SUCCESS = 2008
    AUDIO_CHUNKING_SUCCESS = 2009
    AUDIO_NO_CHUNKING_NEEDED = 20010
    AUDIO_METADATA_FETCH_START = 2011
    AUDIO_METADATA_FETCH_FAILED = 2012
    AUDIO_SCREENING_EXTRACT = 2013

    # Transcription (3000-3099)
    TRANSCRIPTION_START = 3000
    TRANSCRIPTION_CHUNK_PROGRESS = 3001
    TRANSCRIPTION_SUCCESS = 3002
    TRANSCRIPTION_FAILED = 3003
    
    # Text Processing (4000-4099)
    TEXT_CLEANING_SUCCESS = 4001
    TEXT_LANGUAGE_DETECTED = 4002
    TEXT_TRANSLATION_START = 4003
    TEXT_TRANSLATION_SUCCESS = 4004
    TEXT_CHUNKING_START = 4005
    
    # AI Services (5000-5099)
    AI_METADATA_ANALYSIS = 5000
    AI_METADATA_ANALYSIS_COMPLETE = 5001
    AI_CONTENT_SCREENING = 5002
    AI_CONTENT_SCREENING_PASSED = 5003
    AI_SUMMARIZATION_START = 5004
    AI_SUMMARIZATION_CHUNK = 5005
    AI_SUMMARIZATION_MERGE = 5006
    AI_SUMMARIZATION_SUCCESS = 5007
    AI_TRANSLATION_START = 5008
    AI_TRANSLATION_SUCCESS = 5009
    
    # Pipeline Operations (6000-6099)
    PIPELINE_START = 6000
    PIPELINE_CLEANUP = 6001
    PIPELINE_SUCCESS = 6002
    PIPELINE_USER_INPUT = 6003
    
    # General Operations (9000-9099)
    OPERATION_FAILED = 9000
    FILE_NOT_FOUND = 9001
    UNEXPECTED_ERROR = 9002

@dataclass
class Message:
    """Data class representing a standardized message."""
    type: MessageType
    code: MessageCode
    message: str
    details: Optional[str] = None
    timestamp: datetime.datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "type": self.type.value,
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def format_console_output(self) -> str:
        """Format message for console output with appropriate emoji and styling."""
        emoji_map = {
            MessageType.SUCCESS: "✅",
            MessageType.ERROR: "❌",
            MessageType.WARNING: "⚠️",
            MessageType.INFO: "ℹ️",
            MessageType.PROGRESS: "🔄"
        }
        
        emoji = emoji_map.get(self.type, "📝")
        return f"{emoji} {self.message}"

class MessageSystem:
    """Centralized message management system."""
    
    # Pre-defined message templates
    MESSAGES = {
        # Database Messages
        MessageCode.DB_CONNECTION_SUCCESS: "Database connection established successfully.",
        MessageCode.DB_CONNECTION_FAILED: "Failed to connect to MongoDB database.",
        MessageCode.DB_USER_CREATED: "New user created with ID: {user_id}",
        MessageCode.DB_USER_EXISTS: "User already exists, retrieved existing ID: {user_id}",
        MessageCode.DB_JOB_CREATED: "New job created with ID: {job_id}",
        MessageCode.DB_JOB_UPDATED: "Job {job_id} status updated to: {status}",
        MessageCode.DB_RESULTS_SAVED: "Job {job_id} results saved successfully to database.",
        
        # Audio Processing Messages
        MessageCode.AUDIO_DOWNLOAD_START: "Starting audio download from URL: {url}",
        MessageCode.AUDIO_DOWNLOAD_SUCCESS: "Audio downloaded and saved to: {path}",
        MessageCode.AUDIO_DOWNLOAD_FAILED: "All download attempts failed for the provided URL.",
        MessageCode.AUDIO_DOWNLOAD_PROGRESS: "Download progress: {progress}%",
        MessageCode.AUDIO_CONVERSION_START: "Starting audio conversion with {method} method...",
        MessageCode.AUDIO_CONVERSION_SUCCESS: "Audio conversion completed successfully.",
        MessageCode.AUDIO_STANDARDIZATION_SUCCESS: "Audio standardized and saved to: {path}",
        MessageCode.AUDIO_CLEANING_SUCCESS: "Advanced audio cleaning complete, saved to: {path}",
        MessageCode.AUDIO_CHUNKING_SUCCESS: "File successfully split into {count} chunks.",
        MessageCode.AUDIO_NO_CHUNKING_NEEDED: "File size is within limit, no chunking needed.",
        MessageCode.AUDIO_METADATA_FETCH_START: "Fetching metadata for URL: {url}...",
        MessageCode.AUDIO_METADATA_FETCH_FAILED: "Could not fetch metadata for URL. It might be private or invalid.",
        MessageCode.AUDIO_SCREENING_EXTRACT: "Extracting first {duration} seconds for content pre-screening...",
        
        # Transcription Messages
        MessageCode.TRANSCRIPTION_START: "Starting transcription process...",
        MessageCode.TRANSCRIPTION_CHUNK_PROGRESS: "[Whisper] Transcribing chunk {current}/{total}: {filename}",
        MessageCode.TRANSCRIPTION_SUCCESS: "Transcription process completed successfully.",
        MessageCode.TRANSCRIPTION_FAILED: "Transcription failed for file: {filename}",
        
        # Text Processing Messages
        MessageCode.TEXT_CLEANING_SUCCESS: "Text cleaning and normalization completed.",
        MessageCode.TEXT_LANGUAGE_DETECTED: "Language detected: {language}",
        MessageCode.TEXT_TRANSLATION_START: "[GPT-4o] Translating text to English...",
        MessageCode.TEXT_TRANSLATION_SUCCESS: "Translation to English completed successfully.",
        MessageCode.TEXT_CHUNKING_START: "Text is too long, splitting into chunks (~{size} chars each)...",
        
        # AI Services Messages
        MessageCode.AI_METADATA_ANALYSIS: "[GPT-4o] Performing smart analysis of URL metadata...",
        MessageCode.AI_METADATA_ANALYSIS_COMPLETE: "AI metadata analysis complete. Decision: {decision}",
        MessageCode.AI_CONTENT_SCREENING: "[GPT-4o] Performing content pre-screening...",
        MessageCode.AI_CONTENT_SCREENING_PASSED: "Content pre-screening passed. Content appears relevant.",
        MessageCode.AI_SUMMARIZATION_START: "[GPT-4o] Starting text summarization process...",
        MessageCode.AI_SUMMARIZATION_CHUNK: "[GPT-4o] Summarizing chunk {current}/{total}...",
        MessageCode.AI_SUMMARIZATION_MERGE: "Merging multiple summaries into final coherent report...",
        MessageCode.AI_SUMMARIZATION_SUCCESS: "Summary generation completed successfully.",
        MessageCode.AI_TRANSLATION_START: "[GPT-4o] Translating summary to {language}...",
        MessageCode.AI_TRANSLATION_SUCCESS: "Summary translation completed successfully.",
        
        # Pipeline Messages
        MessageCode.PIPELINE_START: "Starting processing for Job ID: {job_id}",
        MessageCode.PIPELINE_CLEANUP: "Cleaned up temporary directory: {temp_dir}",
        MessageCode.PIPELINE_SUCCESS: "Pipeline completed successfully! All results saved to database.",
        MessageCode.PIPELINE_USER_INPUT: "Summary generated. Translation options available.",
        
        # General Messages
        MessageCode.OPERATION_FAILED: "Operation failed: {error}",
        MessageCode.FILE_NOT_FOUND: "Required file not found: {filepath}",
        MessageCode.UNEXPECTED_ERROR: "An unexpected error occurred: {error}"
    }
    
    @classmethod
    def create_message(cls, 
                        code: MessageCode, 
                        message_type: MessageType = None, 
                      **kwargs) -> Message:
        """Create a standardized message with the given code and parameters."""
        
        # Auto-determine message type based on code if not provided
        if message_type is None:
            if code.value < 2000:  # Database operations
                message_type = MessageType.SUCCESS if "SUCCESS" in code.name else MessageType.ERROR
            elif "FAILED" in code.name or "ERROR" in code.name:
                message_type = MessageType.ERROR
            elif "WARNING" in code.name:
                message_type = MessageType.WARNING
            elif "START" in code.name or "PROGRESS" in code.name:
                message_type = MessageType.PROGRESS
            else:
                message_type = MessageType.SUCCESS
        
        # Get message template and format it
        message_template = cls.MESSAGES.get(code, f"Message code {code.value}: No template defined")
        formatted_message = message_template.format(**kwargs) if kwargs else message_template
        
        return Message(
            type=message_type,
            code=code,
            message=formatted_message,
            details=kwargs.get('details')
        )
    
    @classmethod
    def log_message(cls, code: MessageCode, print_output: bool = True, inline: bool = False, **kwargs) -> Message:
        """Create and optionally print a message to console."""
        message = cls.create_message(code, **kwargs)
        
        if print_output:
            formatted_output = message.format_console_output()
            if inline:
                print(f"\r{formatted_output}", end="", flush=True)
            else:
                print(formatted_output)

        return message
    
    @classmethod
    def log_success(cls, code: MessageCode, **kwargs) -> Message:
        """Log a success message."""
        return cls.log_message(code, message_type=MessageType.SUCCESS, **kwargs)
    
    @classmethod
    def log_error(cls, code: MessageCode, **kwargs) -> Message:
        """Log an error message."""
        return cls.log_message(code, message_type=MessageType.ERROR, **kwargs)
    
    @classmethod
    def log_warning(cls, code: MessageCode, **kwargs) -> Message:
        """Log a warning message."""
        return cls.log_message(code, message_type=MessageType.WARNING, **kwargs)
    
    @classmethod
    def log_info(cls, code: MessageCode, **kwargs) -> Message:
        """Log an info message."""
        return cls.log_message(code, message_type=MessageType.INFO, **kwargs)
    
    @classmethod
    def log_progress(cls, code: MessageCode, inline: bool = False, **kwargs) -> Message:
        """Log a progress message, with an option for inline updating if needed."""
        return cls.log_message(code, message_type=MessageType.PROGRESS, inline=inline, **kwargs)