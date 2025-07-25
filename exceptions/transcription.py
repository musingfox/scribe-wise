"""Transcription-related exceptions"""

from typing import Any

from .base import ScribbleWiseError


class TranscriptionError(ScribbleWiseError):
    """Exception raised during transcription"""

    def __init__(
        self,
        message: str,
        audio_path: str | None = None,
        chunk_index: int | None = None,
        duration_seconds: float | None = None,
        error_code: str | None = None,
        recovery_suggestion: str | None = None,
        can_retry: bool = False,
        max_retries: int = 0,
    ):
        super().__init__(
            message, error_code, recovery_suggestion, can_retry, max_retries
        )
        self.audio_path = audio_path
        self.chunk_index = chunk_index
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "audio_path": self.audio_path,
                "chunk_index": self.chunk_index,
                "duration_seconds": self.duration_seconds,
            }
        )
        return base_dict
