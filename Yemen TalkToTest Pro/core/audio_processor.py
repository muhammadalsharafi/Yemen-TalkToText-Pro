"""
Audio Processing Module for TalkToText Pro-v1.0 Engine
Handles audio downloading, conversion, cleaning, and chunking operations.
"""

import os
import re
import subprocess
import uuid
import json
from math import ceil
from pathlib import Path
from typing import List, Dict, Any

from utils.custom_exceptions import FileSystemError, FFmpegError
from core.message_system import MessageSystem, MessageCode
import config

class AudioProcessor:
    """
    Handles all audio-related operations including download, conversion, cleaning, and chunking.
    """
    
    def __init__(self, bitrate: str, ffmpeg_path: str, ffprobe_path: str):
        """
        Initialize AudioProcessor with required tools and settings.
        """
        if not os.path.exists(ffmpeg_path):
            raise FileSystemError(f"FFmpeg executable not found at: {ffmpeg_path}")
        if not os.path.exists(ffprobe_path):
            raise FileSystemError(f"FFprobe executable not found at: {ffprobe_path}")
            
        self.bitrate = bitrate
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.max_size_bytes = config.MAX_AUDIO_CHUNK_SIZE_MB * 1024 * 1024

    def get_url_metadata(self, url: str) -> Dict[str, Any]:
        """
        Fetch metadata from URL without downloading full content using yt-dlp.
        """
        MessageSystem.log_progress(MessageCode.AUDIO_METADATA_FETCH_START, url=url)
        command = ['python', '-m', 'yt_dlp', '--skip-download', '--dump-json', '--no-playlist', url]
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            MessageSystem.log_warning(MessageCode.AUDIO_METADATA_FETCH_FAILED, details=str(e))
            return {}

    def download_audio_from_url(self, url: str, output_dir: str) -> str:
        """
        Download audio from URL using a robust method, ensuring temp files are in the correct directory.
        """
        MessageSystem.log_progress(MessageCode.AUDIO_DOWNLOAD_START, url=url)
        unique_id = uuid.uuid4()
        output_template = os.path.join(output_dir, f"downloaded_{unique_id}.%(ext)s")
        
        # CRITICAL: Force all yt-dlp files (temp, cache, output) into the job's temp directory
        command = [
            'python', '-m', 'yt_dlp',
            '--ffmpeg-location', self.ffmpeg_path,
            '--paths', output_dir, 
            '-f', 'bestaudio/best',
            '-x', '--audio-format', 'mp3',
            '--no-playlist',
            '-o', output_template,
            url
        ]
        
        try:
            self._run_command(command, "Audio download failed")
        except FFmpegError as e:
            raise FFmpegError(f"Download failed for URL. Error: {e}")
        
        # Find the downloaded file, as the extension might not be '.mp3'
        for f in os.listdir(output_dir):
            if f.startswith(f"downloaded_{unique_id}"):
                downloaded_path = os.path.join(output_dir, f)
                MessageSystem.log_success(MessageCode.AUDIO_DOWNLOAD_SUCCESS, path=downloaded_path)
                return downloaded_path
                
        raise FileSystemError("Audio file was not found after download process")

    def _run_command(self, command: List[str], error_message: str):
        """
        Execute system command with proper error handling.
        """
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise FFmpegError(f"{error_message}: {stderr}")
        except FileNotFoundError:
            raise FFmpegError(f"Command '{command[0]}' was not found. Please check installation.")
        
    def _get_duration_seconds(self, file_path: str) -> float:
        """
        Get audio file duration using ffprobe.
        """
        command = [self.ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            raise FFmpegError(f"Failed to get duration for '{file_path}': {e}")

    def extract_initial_segment(self, input_path: str, output_path: str, duration: int) -> str:
        # ... (this function remains the same) ...
        MessageSystem.log_progress(MessageCode.AUDIO_SCREENING_EXTRACT, duration=duration)
        
        command = [
            self.ffmpeg_path, "-y", "-i", input_path,
            "-t", str(duration),
            "-vn",
            "-acodec", "libmp3lame",
            "-ac", str(config.AUDIO_CHANNELS),
            "-ar", str(config.AUDIO_SAMPLE_RATE),
            "-b:a", self.bitrate,
            output_path
        ]
        
        self._run_command(command, "Failed to extract initial audio segment")
        return output_path

    def convert_to_standard_mp3(self, input_path: str, output_path: str) -> str:
        # ... (this function remains the same) ...
        if not os.path.exists(input_path):
            raise FileSystemError(f"Input file not found: {input_path}")
        MessageSystem.log_progress(MessageCode.AUDIO_CONVERSION_START, method="standardization")
        command = [
            self.ffmpeg_path, "-y", "-i", input_path,
            "-vn", "-acodec", "libmp3lame",
            "-ac", str(config.AUDIO_CHANNELS), 
            "-ar", str(config.AUDIO_SAMPLE_RATE),
            "-b:a", self.bitrate,
        ]
        if config.AUDIO_ENHANCE_FILTERS:
            command.extend(["-af", ",".join(config.AUDIO_ENHANCE_FILTERS)])
        command.append(output_path)
        self._run_command(command, "Audio conversion failed")
        MessageSystem.log_success(MessageCode.AUDIO_STANDARDIZATION_SUCCESS, path=output_path)
        return output_path
    
    def clean_audio(self, input_path: str, output_path: str) -> str:
        # ... (this function remains the same) ...
        MessageSystem.log_progress(MessageCode.AUDIO_CONVERSION_START, method="cleaning")
        command = [
            self.ffmpeg_path, "-y", "-i", input_path,
            "-af", ",".join(config.AUDIO_CLEANING_FILTERS),
            output_path
        ]
        self._run_command(command, "Audio cleaning failed")
        MessageSystem.log_success(MessageCode.AUDIO_CLEANING_SUCCESS, path=output_path)
        return output_path

    def chunk_audio(self, input_path: str, output_dir: str = "chunks") -> List[str]:
        # ... (this function remains the same) ...
        file_size = os.path.getsize(input_path)
        if file_size <= self.max_size_bytes:
            return [input_path]
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        num_parts = ceil(file_size / self.max_size_bytes)
        duration = self._get_duration_seconds(input_path)
        segment_time = duration / num_parts
        
        output_pattern = os.path.join(output_dir, "part_%03d.mp3")
        command = [
            self.ffmpeg_path, "-y", "-i", input_path,
            "-f", "segment", "-segment_time", str(segment_time),
            "-c", "copy", output_pattern
        ]
        self._run_command(command, "Audio chunking failed")
        
        output_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("part_")])
        if not output_files:
            raise FFmpegError("No audio chunks were created during splitting process")
            
        return output_files