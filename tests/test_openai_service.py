"""Tests for OpenAITranscriptionService."""

import os
from unittest.mock import Mock, mock_open, patch

import pytest

from config.model_config import ModelType
from services.base import ModelMetadata, ServiceStatus
from services.openai_service import CostTracker, OpenAIError, OpenAITranscriptionService


class TestCostTracker:
    """Test CostTracker functionality."""

    def test_cost_tracker_initialization(self):
        """Test CostTracker initialization."""
        tracker = CostTracker()

        assert tracker.total_cost == 0.0
        assert tracker.total_minutes == 0.0
        assert tracker.request_count == 0

    def test_cost_tracker_add_usage(self):
        """Test adding usage to cost tracker."""
        tracker = CostTracker()

        # Add usage: 2.5 minutes at $0.006/minute
        tracker.add_usage(duration_minutes=2.5, cost_per_minute=0.006)

        assert tracker.total_cost == 0.015  # 2.5 * 0.006
        assert tracker.total_minutes == 2.5
        assert tracker.request_count == 1

    def test_cost_tracker_multiple_usage(self):
        """Test multiple usage additions."""
        tracker = CostTracker()

        tracker.add_usage(1.0, 0.006)
        tracker.add_usage(3.0, 0.006)

        assert tracker.total_cost == 0.024  # (1.0 + 3.0) * 0.006
        assert tracker.total_minutes == 4.0
        assert tracker.request_count == 2

    def test_cost_tracker_get_summary(self):
        """Test cost tracker summary."""
        tracker = CostTracker()
        tracker.add_usage(5.0, 0.006)

        summary = tracker.get_summary()

        assert summary["total_cost"] == 0.030
        assert summary["total_minutes"] == 5.0
        assert summary["request_count"] == 1
        assert summary["average_cost_per_request"] == 0.030


class TestOpenAIError:
    """Test OpenAIError exception."""

    def test_openai_error_creation(self):
        """Test OpenAIError creation."""
        error = OpenAIError(
            message="API key invalid", error_code="invalid_api_key", retry_after=60
        )

        assert str(error) == "API key invalid"
        assert error.error_code == "invalid_api_key"
        assert error.retry_after == 60
        assert error.can_retry is False  # Default

    def test_openai_error_with_retry(self):
        """Test OpenAIError with retry capability."""
        error = OpenAIError(
            message="Rate limit exceeded",
            error_code="rate_limit",
            can_retry=True,
            retry_after=30,
        )

        assert error.can_retry is True
        assert error.retry_after == 30


class TestOpenAITranscriptionService:
    """Test OpenAITranscriptionService implementation."""

    def test_openai_service_initialization(self):
        """Test OpenAITranscriptionService initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            assert service.status == ServiceStatus.UNLOADED
            assert not service.is_ready()
            assert service.model == "whisper-1"
            assert service.response_format == "text"
            assert service.max_file_size_mb == 25
            assert isinstance(service.cost_tracker, CostTracker)

    def test_openai_service_initialization_with_params(self):
        """Test OpenAITranscriptionService initialization with custom parameters."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService(
                model="whisper-1",
                language="zh",
                temperature=0.2,
                response_format="json",
            )

            assert service.model == "whisper-1"
            assert service.language == "zh"
            assert service.temperature == 0.2
            assert service.response_format == "json"

    def test_openai_service_no_api_key(self):
        """Test OpenAITranscriptionService without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key required"):
                OpenAITranscriptionService()

    def test_get_metadata(self):
        """Test get_metadata returns correct model information."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            metadata = service.get_metadata()

            assert isinstance(metadata, ModelMetadata)
            assert metadata.name == "OpenAI Whisper API"
            assert metadata.model_type == ModelType.OPENAI_API
            assert metadata.additional_info["model"] == "whisper-1"
            assert "multilingual" in metadata.additional_info
            assert metadata.memory_requirements_mb == 0  # API service

    @pytest.mark.asyncio
    async def test_load_model_success(self):
        """Test successful API client initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            with patch("services.openai_service.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                # Mock a test API call
                mock_client.audio.transcriptions.create.return_value = Mock(text="test")

                result = await service.load_model()

                assert result is True
                assert service.status == ServiceStatus.READY
                assert service.is_ready()
                assert service._client is mock_client

    @pytest.mark.asyncio
    async def test_load_model_failure(self):
        """Test API client initialization failure."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "invalid-key"}):
            service = OpenAITranscriptionService()

            with patch("services.openai_service.OpenAI") as mock_openai_class:
                # Mock OpenAI constructor to raise exception
                mock_openai_class.side_effect = Exception("Invalid API key")

                result = await service.load_model()

                assert result is False
                assert service.status == ServiceStatus.ERROR

    @pytest.mark.asyncio
    async def test_unload_model(self):
        """Test API client cleanup."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            service._client = Mock()
            service._status = ServiceStatus.READY

            result = await service.unload_model()

            assert result is True
            assert service.status == ServiceStatus.UNLOADED
            assert service._client is None

    @pytest.mark.asyncio
    async def test_transcribe_async_not_ready(self):
        """Test transcription when service not ready."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            result = await service.transcribe_async("test.mp3")

            assert result.success is False
            assert "Service not ready" in result.error_message
            assert result.model_used == "whisper-1"

    @pytest.mark.asyncio
    async def test_transcribe_async_file_not_found(self):
        """Test transcription with non-existent file."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            service._status = ServiceStatus.READY
            service._client = Mock()

            with patch("os.path.exists", return_value=False):
                result = await service.transcribe_async("nonexistent.mp3")

            assert result.success is False
            assert "File not found" in result.error_message

    @pytest.mark.asyncio
    async def test_transcribe_async_file_too_large(self):
        """Test transcription with file exceeding size limit."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            service._status = ServiceStatus.READY
            service._client = Mock()

            # Mock file that exceeds 25MB limit
            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=30 * 1024 * 1024),
            ):  # 30MB
                result = await service.transcribe_async("large_file.mp3")

            assert result.success is False
            assert "exceeds maximum file size" in result.error_message

    @pytest.mark.asyncio
    async def test_transcribe_async_success(self):
        """Test successful transcription."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            service._status = ServiceStatus.READY
            service._client = Mock()

            # Mock successful API response
            mock_response = Mock()
            mock_response.text = "Hello world"
            service._client.audio.transcriptions.create.return_value = mock_response

            # Mock file operations
            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=10 * 1024 * 1024),
                patch("builtins.open", mock_open(read_data=b"audio data")),
            ):
                result = await service.transcribe_async("test.mp3")

            assert result.success is True
            assert result.transcription == "Hello world"
            assert result.model_used == "whisper-1"
            assert result.input_path == "test.mp3"

            # Verify API call
            service._client.audio.transcriptions.create.assert_called_once()
            call_kwargs = service._client.audio.transcriptions.create.call_args.kwargs
            assert call_kwargs["model"] == "whisper-1"
            assert call_kwargs["response_format"] == "text"

    @pytest.mark.asyncio
    async def test_transcribe_async_with_language(self):
        """Test transcription with specific language."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService(language="zh")
            service._status = ServiceStatus.READY
            service._client = Mock()

            mock_response = Mock()
            mock_response.text = "你好世界"
            service._client.audio.transcriptions.create.return_value = mock_response

            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=5 * 1024 * 1024),
                patch("builtins.open", mock_open(read_data=b"audio data")),
            ):
                result = await service.transcribe_async("test.mp3")

            assert result.success is True
            assert result.transcription == "你好世界"

            # Verify language was passed
            call_kwargs = service._client.audio.transcriptions.create.call_args.kwargs
            assert call_kwargs["language"] == "zh"

    @pytest.mark.asyncio
    async def test_transcribe_async_api_error(self):
        """Test transcription with API error."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()
            service._status = ServiceStatus.READY
            service._client = Mock()

            # Mock API error
            from openai import RateLimitError

            service._client.audio.transcriptions.create.side_effect = RateLimitError(
                "Rate limit exceeded", response=Mock(), body=None
            )

            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=5 * 1024 * 1024),
                patch("builtins.open", mock_open(read_data=b"audio data")),
            ):
                result = await service.transcribe_async("test.mp3")

            assert result.success is False
            assert "Rate limit exceeded" in result.error_message

    def test_validate_file_size_valid(self):
        """Test file size validation for valid file."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            with patch("os.path.getsize", return_value=20 * 1024 * 1024):  # 20MB
                is_valid, error = service._validate_file_size("test.mp3")

                assert is_valid is True
                assert error is None

    def test_validate_file_size_too_large(self):
        """Test file size validation for oversized file."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            with patch("os.path.getsize", return_value=30 * 1024 * 1024):  # 30MB
                is_valid, error = service._validate_file_size("large.mp3")

                assert is_valid is False
                assert "exceeds maximum file size" in error

    def test_calculate_cost(self):
        """Test cost calculation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            # Test 150 seconds = 2.5 minutes
            cost = service._calculate_cost(150)

            expected_cost = 2.5 * 0.006  # 2.5 minutes * $0.006/minute
            assert cost == expected_cost

    def test_get_cost_summary(self):
        """Test cost summary retrieval."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = OpenAITranscriptionService()

            # Add some usage
            service.cost_tracker.add_usage(2.0, 0.006)
            service.cost_tracker.add_usage(3.0, 0.006)

            summary = service.get_cost_summary()

            assert (
                abs(summary["total_cost"] - 0.030) < 0.001
            )  # Handle floating point precision
            assert summary["total_minutes"] == 5.0
            assert summary["request_count"] == 2
