"""OpenAITranscriptionService for OpenAI Whisper API."""

import os
from typing import Any

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from config.model_config import OPENAI_API_MODEL_NAME, ModelType
from exceptions.transcription import TranscriptionError
from services.base import (
    BaseTranscriptionService,
    ModelMetadata,
    ServiceStatus,
    TranscriptionResult,
)

# Default configuration constants
DEFAULT_MAX_FILE_SIZE_MB = 25
DEFAULT_COST_PER_MINUTE = 0.006
DEFAULT_RESPONSE_FORMAT = "text"
DEFAULT_TEMPERATURE = 0.0


class OpenAIError(TranscriptionError):
    """OpenAI API specific error."""

    def __init__(
        self,
        message: str,
        error_code: str = "unknown",
        can_retry: bool = False,
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(message, can_retry=can_retry, **kwargs)
        self.error_code = error_code
        self.retry_after = retry_after


class CostTracker:
    """Track OpenAI API usage costs."""

    def __init__(self):
        """Initialize cost tracker."""
        self.total_cost = 0.0
        self.total_minutes = 0.0
        self.request_count = 0

    def add_usage(self, duration_minutes: float, cost_per_minute: float) -> None:
        """Add usage to cost tracker."""
        cost = duration_minutes * cost_per_minute
        self.total_cost += cost
        self.total_minutes += duration_minutes
        self.request_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary."""
        return {
            "total_cost": self.total_cost,
            "total_minutes": self.total_minutes,
            "request_count": self.request_count,
            "average_cost_per_request": (
                self.total_cost / self.request_count if self.request_count > 0 else 0.0
            ),
        }


class OpenAITranscriptionService(BaseTranscriptionService):
    """Transcription service using OpenAI Whisper API."""

    def __init__(
        self,
        model: str = OPENAI_API_MODEL_NAME,
        language: str | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: str = DEFAULT_RESPONSE_FORMAT,
        max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
        cost_per_minute: float = DEFAULT_COST_PER_MINUTE,
    ):
        """Initialize OpenAITranscriptionService."""
        super().__init__()

        # Validate API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable."
            )

        self.model = model
        self.language = language
        self.temperature = temperature
        self.response_format = response_format
        self.max_file_size_mb = max_file_size_mb
        self.cost_per_minute = cost_per_minute

        # Initialize cost tracking
        self.cost_tracker = CostTracker()

        # API client
        self._client: OpenAI | None = None

    def get_metadata(self) -> ModelMetadata:
        """Get model metadata."""
        return ModelMetadata(
            name="OpenAI Whisper API",
            version="1.0",
            model_type=ModelType.OPENAI_API,
            languages_supported=self._get_supported_languages(),
            memory_requirements_mb=0,  # API service, no local memory required
            performance_benchmark={
                "wer_en": 0.03,  # Word Error Rate for English (estimated)
                "wer_zh": 0.08,  # Word Error Rate for Chinese (estimated)
                "rtf": 0.1,  # Real-time factor (estimated, network dependent)
            },
            additional_info={
                "model": self.model,
                "multilingual": True,
                "supports_language_detection": True,
                "supports_timestamps": True,
                "max_file_size_mb": self.max_file_size_mb,
                "cost_per_minute": self.cost_per_minute,
                "api_based": True,
            },
        )

    async def load_model(self) -> bool:
        """Initialize OpenAI API client."""
        try:
            self._status = ServiceStatus.LOADING

            # Initialize OpenAI client
            self._client = OpenAI()

            # Test API connection with a minimal call
            # Note: This doesn't actually transcribe, just validates the API key
            try:
                # We can't easily test without uploading a file, so we'll defer validation
                # to the first actual transcription call
                pass
            except Exception as e:
                raise OpenAIError(
                    "Failed to initialize OpenAI client",
                    error_code="client_init_failed",
                    can_retry=False,
                ) from e

            self._status = ServiceStatus.READY
            return True

        except Exception:
            self._status = ServiceStatus.ERROR
            return False

    async def unload_model(self) -> bool:
        """Clean up API client."""
        try:
            self._client = None
            self._status = ServiceStatus.UNLOADED
            return True
        except Exception:
            return False

    async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using OpenAI API."""
        if not self.is_ready():
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message="Service not ready. Call load_model() first.",
            )

        # Check if file exists
        if not os.path.exists(audio_path):
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=f"File not found: {audio_path}",
            )

        # Validate file size
        is_valid, size_error = self._validate_file_size(audio_path)
        if not is_valid:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=size_error,
            )

        try:
            # Prepare API call parameters
            transcribe_params = {
                "model": self.model,
                "response_format": self.response_format,
                "temperature": self.temperature,
            }

            # Add language if specified
            if self.language:
                transcribe_params["language"] = self.language

            # Open and transcribe audio file
            with open(audio_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    file=audio_file, **transcribe_params
                )

            # Extract transcription text
            if self.response_format == "text":
                transcription = (
                    response.text if hasattr(response, "text") else str(response)
                )
            else:
                # For JSON format, extract text field
                transcription = response.text if hasattr(response, "text") else ""

            # Calculate duration and cost (estimate based on file size)
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            estimated_duration_seconds = file_size_mb * 10  # Rough estimate
            duration_minutes = estimated_duration_seconds / 60
            cost = self._calculate_cost(estimated_duration_seconds)

            # Track cost
            self.cost_tracker.add_usage(duration_minutes, self.cost_per_minute)

            return TranscriptionResult(
                success=True,
                transcription=transcription,
                input_path=audio_path,
                model_used=self.model,
                duration_seconds=estimated_duration_seconds,
                metadata={
                    "file_size_mb": file_size_mb,
                    "estimated_duration_seconds": estimated_duration_seconds,
                    "cost": cost,
                    "cost_per_minute": self.cost_per_minute,
                    "api_model": self.model,
                    "response_format": self.response_format,
                },
            )

        except RateLimitError as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=f"Rate limit exceeded: {str(e)}",
            )

        except AuthenticationError as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=f"Authentication failed: {str(e)}",
            )

        except APIError as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=f"API error: {str(e)}",
            )

        except Exception as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self.model,
                error_message=str(e),
            )

    def _validate_file_size(self, file_path: str) -> tuple[bool, str | None]:
        """Validate audio file size against API limits."""
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            if file_size_mb > self.max_file_size_mb:
                return False, (
                    f"File size {file_size_mb:.1f}MB exceeds maximum file size "
                    f"{self.max_file_size_mb}MB for OpenAI API"
                )

            return True, None

        except Exception as e:
            return False, f"Error checking file size: {str(e)}"

    def _calculate_cost(self, duration_seconds: float) -> float:
        """Calculate transcription cost based on duration."""
        duration_minutes = duration_seconds / 60
        return duration_minutes * self.cost_per_minute

    def get_cost_summary(self) -> dict[str, Any]:
        """Get cost usage summary."""
        return self.cost_tracker.get_summary()

    def _get_supported_languages(self) -> list[str]:
        """Get list of supported languages for OpenAI Whisper API."""
        # OpenAI Whisper API supports the same languages as the model
        return [
            "en",
            "zh",
            "ja",
            "ko",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ar",
            "hi",
            "th",
            "vi",
            "id",
            "ms",
            "tl",
            "tr",
            "pl",
            "nl",
            "sv",
            "da",
            "no",
            "fi",
            "cs",
            "sk",
            "hu",
            "ro",
            "bg",
            "hr",
            "ca",
            "eu",
            "gl",
            "is",
            "lv",
            "lt",
            "mk",
            "mt",
            "sl",
            "cy",
            "et",
            "fa",
            "he",
            "ur",
            "bn",
            "gu",
            "kn",
            "ml",
            "mr",
            "ne",
            "pa",
            "si",
            "ta",
            "te",
            "my",
            "km",
            "lo",
            "ka",
            "am",
            "sw",
            "zu",
            "af",
            "sq",
            "hy",
            "az",
            "be",
            "bs",
            "bg",
            "ca",
            "hr",
            "cs",
            "da",
            "nl",
            "et",
            "fi",
            "fr",
            "gl",
            "de",
            "el",
            "gu",
            "ht",
            "he",
            "hi",
            "hu",
            "is",
            "id",
            "ga",
            "it",
            "ja",
            "kn",
            "kk",
            "ko",
            "lv",
            "lt",
            "lb",
            "mk",
            "ms",
            "ml",
            "mt",
            "mi",
            "mr",
            "ne",
            "no",
            "ps",
            "fa",
            "pl",
            "pt",
            "pa",
            "ro",
            "ru",
            "sr",
            "si",
            "sk",
            "sl",
            "so",
            "es",
            "sw",
            "sv",
            "tl",
            "ta",
            "te",
            "th",
            "tr",
            "uk",
            "ur",
            "vi",
            "cy",
            "yi",
        ]
