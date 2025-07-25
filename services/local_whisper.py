"""LocalWhisperService for OpenAI Whisper models."""

import os
from enum import Enum
from typing import Any

import torch
import whisper

from config.model_config import ModelType
from services.base import (
    BaseTranscriptionService,
    ModelMetadata,
    ServiceStatus,
    TranscriptionResult,
)
from utils.platform_compatibility import PlatformCompatibility

# Default configuration constants
DEFAULT_TEMPERATURE = 0.0
DEFAULT_BEAM_SIZE = 1
DEFAULT_BEST_OF = 1
DEFAULT_PATIENCE = 1.0


class WhisperModelSize(Enum):
    """Available Whisper model sizes."""

    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"

    def to_model_type(self) -> ModelType:
        """Convert WhisperModelSize to ModelType."""
        mapping = {
            WhisperModelSize.BASE: ModelType.LOCAL_WHISPER_BASE,
            WhisperModelSize.SMALL: ModelType.LOCAL_WHISPER_SMALL,
            WhisperModelSize.MEDIUM: ModelType.LOCAL_WHISPER_MEDIUM,
            WhisperModelSize.LARGE: ModelType.LOCAL_WHISPER_LARGE,
            WhisperModelSize.LARGE_V2: ModelType.LOCAL_WHISPER_LARGE,
            WhisperModelSize.LARGE_V3: ModelType.LOCAL_WHISPER_LARGE,
        }
        return mapping[self]


class LocalWhisperService(BaseTranscriptionService):
    """Local transcription service using OpenAI Whisper models."""

    def __init__(
        self,
        model_size: WhisperModelSize = WhisperModelSize.SMALL,
        device: str = "auto",
        language: str = "auto",
        temperature: float = DEFAULT_TEMPERATURE,
        beam_size: int = DEFAULT_BEAM_SIZE,
        best_of: int = DEFAULT_BEST_OF,
        patience: float = DEFAULT_PATIENCE,
        download_root: str | None = None,
        enable_performance_monitoring: bool = True,
    ):
        """Initialize LocalWhisperService."""
        super().__init__()

        self.model_size = model_size
        self.device = device
        self.language = language
        self.temperature = temperature
        self.beam_size = beam_size
        self.best_of = best_of
        self.patience = patience
        self.download_root = download_root

        # Initialize platform compatibility
        self.platform_compat = PlatformCompatibility()

        # Model components
        self._model: Any | None = None  # whisper.Whisper model
        self._device_resolved: str | None = None

    def get_metadata(self) -> ModelMetadata:
        """Get model metadata."""
        model_names = {
            WhisperModelSize.BASE: "OpenAI Whisper Base",
            WhisperModelSize.SMALL: "OpenAI Whisper Small",
            WhisperModelSize.MEDIUM: "OpenAI Whisper Medium",
            WhisperModelSize.LARGE: "OpenAI Whisper Large",
            WhisperModelSize.LARGE_V2: "OpenAI Whisper Large V2",
            WhisperModelSize.LARGE_V3: "OpenAI Whisper Large V3",
        }

        return ModelMetadata(
            name=model_names[self.model_size],
            version="1.0",
            model_type=self.model_size.to_model_type(),
            languages_supported=self._get_supported_languages(),
            memory_requirements_mb=self._calculate_memory_requirements(),
            performance_benchmark={
                "wer_en": 0.05,  # Word Error Rate for English (estimated)
                "wer_zh": 0.10,  # Word Error Rate for Chinese (estimated)
                "rtf": 0.8,  # Real-time factor (estimated)
            },
            additional_info={
                "model_size": self.model_size.value,
                "multilingual": True,
                "supports_language_detection": True,
                "supports_timestamps": True,
                "model_identifier": self._get_model_identifier(),
            },
        )

    async def load_model(self) -> bool:
        """Load the Whisper model."""
        try:
            self._status = ServiceStatus.LOADING

            # Get optimal device
            self._device_resolved = self._get_optimal_device()

            # Load model with optional download root
            load_kwargs = {
                "name": self.model_size.value,
                "device": self._device_resolved,
            }
            if self.download_root:
                load_kwargs["download_root"] = self.download_root

            self._model = whisper.load_model(**load_kwargs)

            self._status = ServiceStatus.READY
            return True

        except Exception:
            self._status = ServiceStatus.ERROR
            return False

    async def unload_model(self) -> bool:
        """Unload the model from memory."""
        try:
            self._model = None
            self._device_resolved = None

            # Clean up GPU memory if applicable
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._status = ServiceStatus.UNLOADED
            return True

        except Exception:
            return False

    async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file asynchronously."""
        if not self.is_ready():
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self._get_model_identifier(),
                error_message="Service not ready. Call load_model() first.",
            )

        # Check if file exists
        if not os.path.exists(audio_path):
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self._get_model_identifier(),
                error_message=f"File not found: {audio_path}",
            )

        try:
            # Prepare transcription options
            transcribe_options = {
                "temperature": self.temperature,
                "beam_size": self.beam_size,
                "best_of": self.best_of,
                "patience": self.patience,
            }

            # Add language if not auto-detect
            if self.language != "auto":
                transcribe_options["language"] = self.language

            # Transcribe audio
            result = self._model.transcribe(audio_path, **transcribe_options)

            return TranscriptionResult(
                success=True,
                transcription=result["text"],
                input_path=audio_path,
                model_used=self._get_model_identifier(),
                metadata={
                    "num_segments": len(result.get("segments", [])),
                    "language": result.get("language", "unknown"),
                    "segments": result.get("segments", []),
                    "device": self._device_resolved,
                    "model_size": self.model_size.value,
                },
            )

        except Exception as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=self._get_model_identifier(),
                error_message=str(e),
            )

    def _get_optimal_device(self) -> str:
        """Get optimal device for this platform."""
        if self.device == "auto":
            return self.platform_compat.get_optimal_torch_device()
        return self.device

    def _get_model_identifier(self) -> str:
        """Get model identifier string."""
        return f"whisper-{self.model_size.value}"

    def _calculate_memory_requirements(self) -> int:
        """Calculate memory requirements in MB based on model size."""
        memory_map = {
            WhisperModelSize.BASE: 1024,  # ~39MB model, ~1GB total
            WhisperModelSize.SMALL: 2048,  # ~244MB model, ~2GB total
            WhisperModelSize.MEDIUM: 4096,  # ~769MB model, ~4GB total
            WhisperModelSize.LARGE: 8192,  # ~1550MB model, ~8GB total
            WhisperModelSize.LARGE_V2: 8192,  # Same as large
            WhisperModelSize.LARGE_V3: 8192,  # Same as large
        }
        return memory_map[self.model_size]

    def _get_supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        # Whisper supports 99 languages, return most common ones
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
        ]
