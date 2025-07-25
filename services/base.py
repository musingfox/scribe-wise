"""Base transcription service interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from config.model_config import ModelType


class ServiceStatus(Enum):
    """Status of transcription service."""

    UNLOADED = "UNLOADED"
    LOADING = "LOADING"
    READY = "READY"
    ERROR = "ERROR"


@dataclass
class TranscriptionResult:
    """Result of transcription operation."""

    success: bool
    transcription: str | None
    input_path: str
    model_used: str
    duration_seconds: float | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelMetadata:
    """Metadata about a transcription model."""

    name: str
    version: str
    model_type: ModelType
    languages_supported: list[str]
    memory_requirements_mb: int
    performance_benchmark: dict[str, float] = field(default_factory=dict)
    additional_info: dict[str, Any] = field(default_factory=dict)


class BaseTranscriptionService(ABC):
    """Abstract base class for transcription services."""

    def __init__(self):
        """Initialize transcription service."""
        self._status = ServiceStatus.UNLOADED

    @property
    def status(self) -> ServiceStatus:
        """Get current service status."""
        return self._status

    def is_ready(self) -> bool:
        """Check if service is ready for transcription."""
        return self._status == ServiceStatus.READY

    @abstractmethod
    async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file asynchronously."""
        pass

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Get model metadata."""
        pass

    @abstractmethod
    async def load_model(self) -> bool:
        """Load the transcription model."""
        pass

    @abstractmethod
    async def unload_model(self) -> bool:
        """Unload the transcription model."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.load_model()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.unload_model()
        return False
