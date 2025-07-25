import os
from enum import Enum
from pathlib import Path


class FileType(Enum):
    """Enumeration of supported file types"""

    WEBM = "webm"
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"


class UnsupportedFileError(Exception):
    """Raised when file type is not supported"""

    pass


class FileTypeDetector:
    """Utility class for detecting file types and validating files"""

    # Mapping of file extensions to FileType enum
    EXTENSION_MAP = {
        ".webm": FileType.WEBM,
        ".mp4": FileType.MP4,
        ".mkv": FileType.MKV,
        ".avi": FileType.AVI,
        ".mp3": FileType.MP3,
        ".wav": FileType.WAV,
        ".flac": FileType.FLAC,
    }

    # Video file types
    VIDEO_FORMATS = {FileType.WEBM, FileType.MP4, FileType.MKV, FileType.AVI}

    # Audio file types
    AUDIO_FORMATS = {FileType.MP3, FileType.WAV, FileType.FLAC}

    def __init__(self, max_file_size_gb: float = 1.0):
        """Initialize file detector with maximum file size limit"""
        self.max_file_size_bytes = max_file_size_gb * 1024 * 1024 * 1024

    def detect_file_type(self, file_path: str) -> FileType:
        """Detect file type based on file extension"""
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file extension (case insensitive)
        extension = path.suffix.lower()

        # Check if extension is supported
        if extension not in self.EXTENSION_MAP:
            supported_extensions = ", ".join(self.EXTENSION_MAP.keys())
            raise UnsupportedFileError(
                f"Unsupported file type: {extension}. "
                f"Supported extensions: {supported_extensions}"
            )

        return self.EXTENSION_MAP[extension]

    def check_file_size(self, file_path: str) -> bool:
        """Check if file size is within allowed limits"""
        try:
            file_size = os.path.getsize(file_path)
            return file_size <= self.max_file_size_bytes
        except OSError:
            return False

    def get_supported_extensions(self) -> set[str]:
        """Get set of all supported file extensions"""
        return set(self.EXTENSION_MAP.keys())

    def is_video_format(self, file_type: FileType) -> bool:
        """Check if the given file type is a video format"""
        return file_type in self.VIDEO_FORMATS

    def is_audio_format(self, file_type: FileType) -> bool:
        """Check if the given file type is an audio format"""
        return file_type in self.AUDIO_FORMATS
