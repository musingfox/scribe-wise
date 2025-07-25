"""Tests for base transcription service."""

from abc import ABC

import pytest

from config.model_config import ModelType
from services.base import (
    BaseTranscriptionService,
    ModelMetadata,
    ServiceStatus,
    TranscriptionResult,
)


class TestTranscriptionResult:
    """Test TranscriptionResult dataclass."""

    def test_transcription_result_success(self):
        """Test successful transcription result."""
        result = TranscriptionResult(
            success=True,
            transcription="Hello world",
            input_path="/path/to/audio.mp3",
            model_used="whisper-small",
            duration_seconds=10.5,
        )

        assert result.success is True
        assert result.transcription == "Hello world"
        assert result.input_path == "/path/to/audio.mp3"
        assert result.model_used == "whisper-small"
        assert result.duration_seconds == 10.5
        assert result.error_message is None

    def test_transcription_result_failure(self):
        """Test failed transcription result."""
        result = TranscriptionResult(
            success=False,
            transcription=None,
            input_path="/path/to/audio.mp3",
            model_used="whisper-small",
            error_message="Model loading failed",
        )

        assert result.success is False
        assert result.transcription is None
        assert result.error_message == "Model loading failed"


class TestModelMetadata:
    """Test ModelMetadata dataclass."""

    def test_model_metadata_creation(self):
        """Test ModelMetadata creation with all fields."""
        metadata = ModelMetadata(
            name="Whisper Small",
            version="1.0",
            model_type=ModelType.LOCAL_WHISPER_SMALL,
            languages_supported=["en", "zh", "ja"],
            memory_requirements_mb=2048,
            performance_benchmark={"wer": 0.05, "rtf": 1.2},
        )

        assert metadata.name == "Whisper Small"
        assert metadata.version == "1.0"
        assert metadata.model_type == ModelType.LOCAL_WHISPER_SMALL
        assert "zh" in metadata.languages_supported
        assert metadata.memory_requirements_mb == 2048
        assert metadata.performance_benchmark["wer"] == 0.05


class TestServiceStatus:
    """Test ServiceStatus enum."""

    def test_service_status_values(self):
        """Test ServiceStatus enum values."""
        expected_statuses = ["UNLOADED", "LOADING", "READY", "ERROR"]
        actual_statuses = [status.value for status in ServiceStatus]
        assert set(actual_statuses) == set(expected_statuses)


class TestBaseTranscriptionService:
    """Test BaseTranscriptionService abstract class."""

    def test_base_service_is_abstract(self):
        """Test BaseTranscriptionService is abstract class."""
        assert issubclass(BaseTranscriptionService, ABC)

        with pytest.raises(TypeError):
            BaseTranscriptionService()

    def test_concrete_implementation_required_methods(self):
        """Test concrete implementation must implement all abstract methods."""

        class ConcreteService(BaseTranscriptionService):
            def __init__(self):
                super().__init__()

            async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
                return TranscriptionResult(
                    success=True,
                    transcription="test",
                    input_path=audio_path,
                    model_used="test-model",
                )

            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Test Model",
                    version="1.0",
                    model_type=ModelType.LOCAL_BREEZE,
                    languages_supported=["en"],
                    memory_requirements_mb=1024,
                )

            async def load_model(self) -> bool:
                self._status = ServiceStatus.READY
                return True

            async def unload_model(self) -> bool:
                self._status = ServiceStatus.UNLOADED
                return True

        # Should be able to instantiate concrete implementation
        service = ConcreteService()
        assert service.status == ServiceStatus.UNLOADED

    def test_base_service_context_manager(self):
        """Test BaseTranscriptionService context manager protocol."""

        class MockService(BaseTranscriptionService):
            def __init__(self):
                super().__init__()
                self.load_called = False
                self.unload_called = False

            async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
                return TranscriptionResult(True, "test", audio_path, "test-model")

            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    "Test", "1.0", ModelType.LOCAL_BREEZE, ["en"], 1024
                )

            async def load_model(self) -> bool:
                self.load_called = True
                self._status = ServiceStatus.READY
                return True

            async def unload_model(self) -> bool:
                self.unload_called = True
                self._status = ServiceStatus.UNLOADED
                return True

        service = MockService()

        # Test context manager usage (sync version for testing)
        assert hasattr(service, "__aenter__")
        assert hasattr(service, "__aexit__")

    @pytest.mark.asyncio
    async def test_base_service_lifecycle(self):
        """Test service lifecycle management."""

        class TestService(BaseTranscriptionService):
            def __init__(self):
                super().__init__()

            async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
                if self._status != ServiceStatus.READY:
                    return TranscriptionResult(
                        False,
                        None,
                        audio_path,
                        "test-model",
                        error_message="Service not ready",
                    )
                return TranscriptionResult(True, "success", audio_path, "test-model")

            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    "Test", "1.0", ModelType.LOCAL_BREEZE, ["en"], 1024
                )

            async def load_model(self) -> bool:
                self._status = ServiceStatus.LOADING
                # Simulate model loading
                self._status = ServiceStatus.READY
                return True

            async def unload_model(self) -> bool:
                self._status = ServiceStatus.UNLOADED
                return True

        service = TestService()

        # Initial state
        assert service.status == ServiceStatus.UNLOADED
        assert not service.is_ready()

        # Load model
        result = await service.load_model()
        assert result is True
        assert service.status == ServiceStatus.READY
        assert service.is_ready()

        # Transcribe
        transcription_result = await service.transcribe_async("test.mp3")
        assert transcription_result.success is True

        # Unload model
        result = await service.unload_model()
        assert result is True
        assert service.status == ServiceStatus.UNLOADED
        assert not service.is_ready()
