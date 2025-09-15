"""
Text Processing Module for TalkToText Pro-v1.0 Engine
Handles cleaning and preprocessing of raw text transcripts.
"""

import re
from typing import List
import config
from core.message_system import MessageSystem, MessageCode

class TextProcessor:
    """
    Handles cleaning and chunking of raw text transcripts before AI processing.
    """
    
    def __init__(self, chunk_size: int = config.TEXT_CHUNK_SIZE_CHARS):
        """
        Initialize TextProcessor with configurable chunk size.
        
        Args:
            chunk_size (int): Maximum character count per text chunk
        """
        self.chunk_size = chunk_size

    def clean_transcript(self, text: str) -> str:
        """
        Apply advanced cleaning to raw text transcript to remove noise and improve quality.
        
        Args:
            text (str): Raw transcript text to be cleaned
            
        Returns:
            str: Cleaned and normalized text
        """
        # Normalize whitespace to single spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common filler words, vocalizations, and disfluencies
        filler_pattern = r'\b(um|uh|hmm|er|ah|eh|like|you know|I mean|so|well|right|okay|actually|basically|literally)\b'
        text = re.sub(filler_pattern, '', text, flags=re.IGNORECASE)

        # Handle word repetitions (e.g., "Yes. Yes," or "word word")
        # Pattern finds a word followed by punctuation/spaces and the same word again
        repetition_pattern = re.compile(r"(\b\w+\b)([\s,.!?\"'`\-–—]{1,15})\1\b", flags=re.IGNORECASE)
        while True:
            new_text = repetition_pattern.sub(r'\1\2', text)
            if new_text == text:
                break
            text = new_text

        # Clean up formatting artifacts
        text = re.sub(r'\s+([,.!?])', r'\1', text)  # Remove spaces before punctuation
        text = re.sub(r' +', ' ', text).strip()      # Normalize multiple spaces

        MessageSystem.log_success(MessageCode.TEXT_CLEANING_SUCCESS)
        return text

    def split_into_chunks(self, text: str) -> List[str]:
        """
        Split large text into manageable chunks while respecting sentence boundaries.
        
        Args:
            text (str): Text to be split into chunks
            
        Returns:
            List[str]: List of text chunks
        """
        if not isinstance(text, str) or not text.strip():
            return []
        
        if len(text) <= self.chunk_size:
            return [text]

        MessageSystem.log_progress(MessageCode.TEXT_CHUNKING_START, size=self.chunk_size)

        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + self.chunk_size, len(text))

            # Try to find natural sentence break points near the end position
            if end_pos < len(text):
                last_break = max(
                    text.rfind('. ', current_pos, end_pos),
                    text.rfind('? ', current_pos, end_pos),
                    text.rfind('! ', current_pos, end_pos)
                )
                if last_break != -1:
                    end_pos = last_break + 1

            chunk = text[current_pos:end_pos].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            current_pos = end_pos

        return chunks
