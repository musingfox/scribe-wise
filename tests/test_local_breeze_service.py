"""Tests for LocalBreezeService."""

from unittest.mock import Mock, patch

import pytest
import torch

from config.model_config import ModelType
from services.base import ModelMetadata, ServiceStatus
from services.local_breeze import LocalBreezeService


class TestLocalBreezeService:
    """Test LocalBreezeService implementation."""

    def test_breeze_service_initialization(self):
        """Test LocalBreezeService initialization."""
        service = LocalBreezeService()

        assert service.status == ServiceStatus.UNLOADED
        assert not service.is_ready()
        assert service.chunk_length_sec == 30
        assert service.device == "auto"

    def test_breeze_service_initialization_with_params(self):
        """Test LocalBreezeService initialization with custom parameters."""
        service = LocalBreezeService(
            chunk_length_sec=15, device="cpu", enable_performance_monitoring=False
        )

        assert service.chunk_length_sec == 15
        assert service.device == "cpu"

    def test_get_metadata(self):
        """Test get_metadata returns correct model information."""
        service = LocalBreezeService()
        metadata = service.get_metadata()

        assert isinstance(metadata, ModelMetadata)
        assert metadata.name == "MediaTek Breeze-ASR-25"
        assert metadata.model_type == ModelType.LOCAL_BREEZE
        assert (
            metadata.additional_info["model_name"] == "MediaTek-Research/Breeze-ASR-25"
        )
        assert "zh" in metadata.languages_supported
        assert "en" in metadata.languages_supported
        assert metadata.memory_requirements_mb >= 1024

    @pytest.mark.asyncio
    async def test_load_model_success(self):
        """Test successful model loading."""
        service = LocalBreezeService()

        with (
            patch(
                "services.local_breeze.WhisperForConditionalGeneration"
            ) as mock_model_class,
            patch("services.local_breeze.WhisperProcessor") as mock_processor_class,
            patch.object(service, "_get_optimal_device", return_value="cpu"),
        ):
            # Mock model and processor
            mock_model = Mock()
            mock_model.to.return_value = mock_model
            mock_model.eval.return_value = mock_model
            mock_model_class.from_pretrained.return_value = mock_model

            mock_processor = Mock()
            mock_processor_class.from_pretrained.return_value = mock_processor

            # Load model
            result = await service.load_model()

            assert result is True
            assert service.status == ServiceStatus.READY
            assert service.is_ready()
            assert service._model is mock_model
            assert service._processor is mock_processor

    @pytest.mark.asyncio
    async def test_load_model_failure(self):
        """Test model loading failure."""
        service = LocalBreezeService()

        with patch(
            "services.local_breeze.WhisperForConditionalGeneration"
        ) as mock_model_class:
            mock_model_class.from_pretrained.side_effect = Exception(
                "Model loading failed"
            )

            result = await service.load_model()

            assert result is False
            assert service.status == ServiceStatus.ERROR

    @pytest.mark.asyncio
    async def test_unload_model(self):
        """Test model unloading."""
        service = LocalBreezeService()
        service._model = Mock()
        service._processor = Mock()
        service._status = ServiceStatus.READY

        result = await service.unload_model()

        assert result is True
        assert service.status == ServiceStatus.UNLOADED
        assert service._model is None
        assert service._processor is None

    @pytest.mark.asyncio
    async def test_transcribe_async_not_ready(self):
        """Test transcription when service not ready."""
        service = LocalBreezeService()

        result = await service.transcribe_async("test.mp3")

        assert result.success is False
        assert "Service not ready" in result.error_message
        assert result.model_used == "MediaTek-Research/Breeze-ASR-25"

    @pytest.mark.asyncio
    async def test_transcribe_async_success(self):
        """Test successful transcription."""
        service = LocalBreezeService()
        service._status = ServiceStatus.READY
        service._model = Mock()
        service._processor = Mock()

        with (
            patch("torchaudio.load") as mock_load,
            patch.object(service, "_preprocess_audio") as mock_preprocess,
            patch.object(service, "_transcribe_chunks") as mock_transcribe,
        ):
            # Mock audio loading
            mock_waveform = torch.randn(1, 16000)  # 1 second audio
            mock_load.return_value = (mock_waveform, 16000)

            # Mock preprocessing
            mock_preprocess.return_value = (mock_waveform.squeeze(), 16000)

            # Mock transcription
            mock_transcribe.return_value = "Hello world"

            result = await service.transcribe_async("test.mp3")

            assert result.success is True
            assert result.transcription == "Hello world"
            assert result.model_used == "MediaTek-Research/Breeze-ASR-25"
            assert result.input_path == "test.mp3"

    @pytest.mark.asyncio
    async def test_transcribe_async_file_not_found(self):
        """Test transcription with non-existent file."""
        service = LocalBreezeService()
        service._status = ServiceStatus.READY

        with patch("torchaudio.load") as mock_load:
            mock_load.side_effect = FileNotFoundError("File not found")

            result = await service.transcribe_async("nonexistent.mp3")

            assert result.success is False
            assert "File not found" in result.error_message

    def test_preprocess_audio_mono_conversion(self):
        """Test audio preprocessing with stereo to mono conversion."""
        service = LocalBreezeService()

        # Create stereo audio (2 channels)
        stereo_waveform = torch.randn(2, 16000)

        mono_waveform, sample_rate = service._preprocess_audio(stereo_waveform, 16000)

        assert mono_waveform.shape == (16000,)  # Should be 1D
        assert sample_rate == 16000

    def test_preprocess_audio_resampling(self):
        """Test audio preprocessing with resampling."""
        service = LocalBreezeService()

        # Create audio with different sample rate
        waveform = torch.randn(1, 44100)  # 44.1kHz

        with patch("torchaudio.transforms.Resample") as mock_resample_class:
            mock_resampler = Mock()
            mock_resampled = torch.randn(22050)  # Resampled to 16kHz
            mock_resampler.return_value = mock_resampled
            mock_resample_class.return_value = mock_resampler

            processed_waveform, sample_rate = service._preprocess_audio(waveform, 44100)

            assert sample_rate == 16000
            mock_resample_class.assert_called_once_with(44100, 16000)

    def test_split_into_chunks(self):
        """Test audio chunking functionality."""
        service = LocalBreezeService(chunk_length_sec=2)  # 2 second chunks

        # Create 5 second audio at 16kHz
        waveform = torch.randn(5 * 16000)

        chunks = service._split_into_chunks(waveform, 16000)

        # Should create 3 chunks: [0-2s], [2-4s], [4-5s]
        assert len(chunks) == 3
        assert chunks[0].shape[0] == 2 * 16000  # 2 seconds
        assert chunks[1].shape[0] == 2 * 16000  # 2 seconds
        assert chunks[2].shape[0] == 1 * 16000  # 1 second (remainder)

    @pytest.mark.asyncio
    async def test_transcribe_chunks(self):
        """Test chunk transcription with mocked model."""
        service = LocalBreezeService()
        service._model = Mock()
        service._processor = Mock()
        service._device_resolved = "cpu"

        # Mock processor and model behavior
        mock_input_features = Mock()
        service._processor.return_value.input_features = mock_input_features
        mock_input_features.to.return_value = mock_input_features

        mock_predicted_ids = torch.tensor([[1, 2, 3]])
        service._model.generate.return_value = mock_predicted_ids
        service._processor.batch_decode.side_effect = [["Hello"], ["world"]]

        # Create test chunks
        chunks = [torch.randn(16000), torch.randn(16000)]

        with patch("torch.no_grad"):
            result = await service._transcribe_chunks(chunks, 16000)

        assert result == "Hello world"
        assert service._processor.call_count == 2  # Called for each chunk
        assert service._model.generate.call_count == 2
