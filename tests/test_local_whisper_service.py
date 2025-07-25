"""Tests for LocalWhisperService."""

from unittest.mock import Mock, patch

import pytest

from config.model_config import ModelType
from services.base import ModelMetadata, ServiceStatus
from services.local_whisper import LocalWhisperService, WhisperModelSize


class TestWhisperModelSize:
    """Test WhisperModelSize enum."""

    def test_model_size_enum_values(self):
        """Test WhisperModelSize enum contains all expected values."""
        expected_sizes = ["base", "small", "medium", "large", "large-v2", "large-v3"]
        actual_sizes = [size.value for size in WhisperModelSize]
        assert set(actual_sizes) == set(expected_sizes)

    def test_model_size_to_model_type(self):
        """Test conversion from WhisperModelSize to ModelType."""
        mapping = {
            WhisperModelSize.BASE: ModelType.LOCAL_WHISPER_BASE,
            WhisperModelSize.SMALL: ModelType.LOCAL_WHISPER_SMALL,
            WhisperModelSize.MEDIUM: ModelType.LOCAL_WHISPER_MEDIUM,
            WhisperModelSize.LARGE: ModelType.LOCAL_WHISPER_LARGE,
        }

        for whisper_size, model_type in mapping.items():
            assert whisper_size.to_model_type() == model_type


class TestLocalWhisperService:
    """Test LocalWhisperService implementation."""

    def test_whisper_service_initialization(self):
        """Test LocalWhisperService initialization."""
        service = LocalWhisperService()

        assert service.status == ServiceStatus.UNLOADED
        assert not service.is_ready()
        assert service.model_size == WhisperModelSize.SMALL
        assert service.device == "auto"
        assert service.language == "auto"

    def test_whisper_service_initialization_with_params(self):
        """Test LocalWhisperService initialization with custom parameters."""
        service = LocalWhisperService(
            model_size=WhisperModelSize.MEDIUM,
            device="cpu",
            language="zh",
            temperature=0.2,
            beam_size=5,
        )

        assert service.model_size == WhisperModelSize.MEDIUM
        assert service.device == "cpu"
        assert service.language == "zh"
        assert service.temperature == 0.2
        assert service.beam_size == 5

    def test_get_metadata_small(self):
        """Test get_metadata returns correct model information for small model."""
        service = LocalWhisperService(model_size=WhisperModelSize.SMALL)
        metadata = service.get_metadata()

        assert isinstance(metadata, ModelMetadata)
        assert metadata.name == "OpenAI Whisper Small"
        assert metadata.model_type == ModelType.LOCAL_WHISPER_SMALL
        assert metadata.additional_info["model_size"] == "small"
        assert metadata.memory_requirements_mb == 2048
        assert "multilingual" in metadata.additional_info

    def test_get_metadata_large(self):
        """Test get_metadata returns correct model information for large model."""
        service = LocalWhisperService(model_size=WhisperModelSize.LARGE)
        metadata = service.get_metadata()

        assert metadata.name == "OpenAI Whisper Large"
        assert metadata.model_type == ModelType.LOCAL_WHISPER_LARGE
        assert metadata.memory_requirements_mb == 8192

    @pytest.mark.asyncio
    async def test_load_model_success(self):
        """Test successful model loading."""
        service = LocalWhisperService()

        with (
            patch("services.local_whisper.whisper") as mock_whisper,
            patch.object(service, "_get_optimal_device", return_value="cpu"),
        ):
            # Mock whisper.load_model
            mock_model = Mock()
            mock_whisper.load_model.return_value = mock_model

            # Load model
            result = await service.load_model()

            assert result is True
            assert service.status == ServiceStatus.READY
            assert service.is_ready()
            assert service._model is mock_model
            mock_whisper.load_model.assert_called_once_with(name="small", device="cpu")

    @pytest.mark.asyncio
    async def test_load_model_with_download_root(self):
        """Test model loading with custom download root."""
        service = LocalWhisperService(download_root="/custom/path")

        with (
            patch("services.local_whisper.whisper") as mock_whisper,
            patch.object(service, "_get_optimal_device", return_value="cpu"),
        ):
            mock_model = Mock()
            mock_whisper.load_model.return_value = mock_model

            result = await service.load_model()

            assert result is True
            mock_whisper.load_model.assert_called_once_with(
                name="small", device="cpu", download_root="/custom/path"
            )

    @pytest.mark.asyncio
    async def test_load_model_failure(self):
        """Test model loading failure."""
        service = LocalWhisperService()

        with patch("services.local_whisper.whisper") as mock_whisper:
            mock_whisper.load_model.side_effect = Exception("Model loading failed")

            result = await service.load_model()

            assert result is False
            assert service.status == ServiceStatus.ERROR

    @pytest.mark.asyncio
    async def test_unload_model(self):
        """Test model unloading."""
        service = LocalWhisperService()
        service._model = Mock()
        service._status = ServiceStatus.READY

        result = await service.unload_model()

        assert result is True
        assert service.status == ServiceStatus.UNLOADED
        assert service._model is None

    @pytest.mark.asyncio
    async def test_transcribe_async_not_ready(self):
        """Test transcription when service not ready."""
        service = LocalWhisperService()

        result = await service.transcribe_async("test.mp3")

        assert result.success is False
        assert "Service not ready" in result.error_message
        assert result.model_used == "whisper-small"

    @pytest.mark.asyncio
    async def test_transcribe_async_success(self):
        """Test successful transcription."""
        service = LocalWhisperService()
        service._status = ServiceStatus.READY
        service._model = Mock()

        # Mock whisper transcribe result
        mock_result = {
            "text": "Hello world",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello"},
                {"start": 2.0, "end": 4.0, "text": "world"},
            ],
        }
        service._model.transcribe.return_value = mock_result

        with patch("os.path.exists", return_value=True):
            result = await service.transcribe_async("test.mp3")

        assert result.success is True
        assert result.transcription == "Hello world"
        assert result.model_used == "whisper-small"
        assert result.input_path == "test.mp3"
        assert result.metadata["num_segments"] == 2

    @pytest.mark.asyncio
    async def test_transcribe_async_with_language(self):
        """Test transcription with specific language."""
        service = LocalWhisperService(language="zh")
        service._status = ServiceStatus.READY
        service._model = Mock()

        mock_result = {"text": "你好世界", "segments": []}
        service._model.transcribe.return_value = mock_result

        with patch("os.path.exists", return_value=True):
            result = await service.transcribe_async("test.mp3")

        assert result.success is True
        assert result.transcription == "你好世界"
        # Verify language was passed to transcribe
        service._model.transcribe.assert_called_once_with(
            "test.mp3",
            language="zh",
            temperature=0.0,
            beam_size=1,
            best_of=1,
            patience=1.0,
        )

    @pytest.mark.asyncio
    async def test_transcribe_async_file_not_found(self):
        """Test transcription with non-existent file."""
        service = LocalWhisperService()
        service._status = ServiceStatus.READY

        with patch("os.path.exists", return_value=False):
            result = await service.transcribe_async("nonexistent.mp3")

        assert result.success is False
        assert "File not found" in result.error_message

    @pytest.mark.asyncio
    async def test_transcribe_async_exception(self):
        """Test transcription with exception."""
        service = LocalWhisperService()
        service._status = ServiceStatus.READY
        service._model = Mock()

        service._model.transcribe.side_effect = Exception("Transcription failed")

        with patch("os.path.exists", return_value=True):
            result = await service.transcribe_async("test.mp3")

        assert result.success is False
        assert "Transcription failed" in result.error_message

    def test_get_model_identifier(self):
        """Test model identifier generation."""
        service_small = LocalWhisperService(model_size=WhisperModelSize.SMALL)
        assert service_small._get_model_identifier() == "whisper-small"

        service_large = LocalWhisperService(model_size=WhisperModelSize.LARGE_V3)
        assert service_large._get_model_identifier() == "whisper-large-v3"

    def test_calculate_memory_requirements(self):
        """Test memory requirement calculation."""
        service_base = LocalWhisperService(model_size=WhisperModelSize.BASE)
        assert service_base._calculate_memory_requirements() == 1024

        service_small = LocalWhisperService(model_size=WhisperModelSize.SMALL)
        assert service_small._calculate_memory_requirements() == 2048

        service_medium = LocalWhisperService(model_size=WhisperModelSize.MEDIUM)
        assert service_medium._calculate_memory_requirements() == 4096

        service_large = LocalWhisperService(model_size=WhisperModelSize.LARGE)
        assert service_large._calculate_memory_requirements() == 8192
