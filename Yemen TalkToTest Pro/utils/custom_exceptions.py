"""
Custom exception classes for TalkToText Pro-v1.0 Engine
Provides specialized exception handling for different system components.
"""

class ProjectBaseException(Exception):
    """Base exception class for all custom exceptions in this project."""
    pass

class FileSystemError(ProjectBaseException):
    """Raised for file-related operations such as file not found or access denied."""
    pass

class FFmpegError(ProjectBaseException):
    """Raised when FFmpeg operations fail (conversion, trimming, chunking)."""
    pass

class IrrelevantContentError(ProjectBaseException):
    """Raised when content pre-screening determines content is unsuitable for processing."""
    pass

class TranscriptionError(ProjectBaseException):
    """Raised during audio-to-text transcription process failures."""
    pass

class ApiServiceError(ProjectBaseException):
    """Raised for errors when communicating with external API services."""
    pass

class LanguageDetectionError(ProjectBaseException):
    """Raised when automatic language detection process fails."""
    pass
