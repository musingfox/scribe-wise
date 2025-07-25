"""Error recovery and retry mechanisms"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exceptions import (
    ConversionError,
    ScribbleWiseError,
    TranscriptionError,
    ValidationError,
)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    jitter: bool = True


class ErrorRecoveryManager:
    """Manages error recovery strategies and retry mechanisms"""

    def __init__(self, retry_config: RetryConfig | None = None):
        self.retry_config = retry_config or RetryConfig()
        self.temp_file_tracker: set[str] = set()

        # Define retryable error codes
        self._retryable_error_codes = {
            "CV_TIMEOUT",
            "CV_NETWORK",
            "CV_TEMP_FAILURE",
            "TR_MODEL_LOADING",
            "TR_MEMORY_ERROR",
            "VL_TEMP_UNAVAILABLE",
        }

    async def retry_operation(
        self, operation: Callable[[], Awaitable[Any]], operation_name: str
    ) -> Any:
        """Retry an async operation with configured retry strategy"""
        last_error = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return await operation()
            except ScribbleWiseError as error:
                last_error = error

                # Don't retry if error is not retryable
                if not self._is_retryable_error(error):
                    raise error

                # Don't retry on last attempt
                if attempt == self.retry_config.max_retries:
                    break

                # Wait before retry
                delay = self._calculate_delay(attempt + 1)
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        if last_error:
            raise last_error

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay before retry attempt"""
        if self.retry_config.exponential_backoff:
            delay = self.retry_config.base_delay * (2**attempt)
        else:
            delay = self.retry_config.base_delay

        # Apply maximum delay cap
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            delay += random.uniform(0, delay * 0.1)

        return delay

    def _is_retryable_error(self, error: ScribbleWiseError) -> bool:
        """Determine if an error is retryable"""
        # Check explicit can_retry flag
        if hasattr(error, "can_retry"):
            return error.can_retry

        # Check error code against retryable codes
        if error.error_code in self._retryable_error_codes:
            return True

        return False

    async def cleanup_temp_files(self):
        """Clean up tracked temporary files"""
        for temp_file_path in list(self.temp_file_tracker):
            try:
                temp_file = Path(temp_file_path)
                if temp_file.exists():
                    temp_file.unlink()
                self.temp_file_tracker.discard(temp_file_path)
            except Exception:
                # Ignore cleanup errors to avoid masking original errors
                pass

    def get_recovery_suggestion(self, error: ScribbleWiseError) -> str:
        """Get recovery suggestion for specific error"""
        if isinstance(error, ConversionError):
            return self._get_conversion_recovery_suggestion(error)
        elif isinstance(error, ValidationError):
            return self._get_validation_recovery_suggestion(error)
        elif isinstance(error, TranscriptionError):
            return self._get_transcription_recovery_suggestion(error)
        else:
            return "Please check the error message and try again."

    def _get_conversion_recovery_suggestion(self, error: ConversionError) -> str:
        """Get recovery suggestion for conversion errors"""
        if error.error_code == "CV001" or "ffmpeg" in error.message.lower():
            return (
                "FFmpeg is required for media conversion. "
                "Install it using: brew install ffmpeg (macOS) or "
                "sudo apt install ffmpeg (Ubuntu/Debian)"
            )
        elif "timeout" in error.message.lower():
            return (
                "Conversion timed out. Try with a smaller file or "
                "increase the timeout limit in configuration."
            )
        else:
            return (
                "Check that the input file is valid and not corrupted. "
                "Ensure sufficient disk space for output file."
            )

    def _get_validation_recovery_suggestion(self, error: ValidationError) -> str:
        """Get recovery suggestion for validation errors"""
        if "format" in error.message.lower():
            return (
                "Check that the audio file is in a supported format "
                "(MP3, WAV, FLAC, OGG, AAC, M4A)."
            )
        elif "corrupted" in error.message.lower():
            return (
                "The audio file appears to be corrupted. "
                "Try with a different file or re-download the original."
            )
        else:
            return "Check the audio file properties and ensure it's a valid audio file."

    def _get_transcription_recovery_suggestion(self, error: TranscriptionError) -> str:
        """Get recovery suggestion for transcription errors"""
        if "model" in error.message.lower():
            return (
                "Check internet connection for model download. "
                "Ensure sufficient disk space for model files (~2GB)."
            )
        elif "memory" in error.message.lower():
            return (
                "Insufficient memory for transcription. "
                "Try with shorter audio segments or reduce concurrent processing."
            )
        else:
            return (
                "Check audio quality and ensure the file is not silent or corrupted. "
                "Try with a different audio file."
            )
