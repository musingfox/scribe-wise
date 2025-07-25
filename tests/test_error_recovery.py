from unittest.mock import AsyncMock, patch

import pytest

from exceptions import ConversionError, TranscriptionError, ValidationError
from utils.error_recovery import ErrorRecoveryManager, RetryConfig


class TestErrorRecoveryManager:
    def test_init_creates_manager_with_defaults(self):
        """Test that ErrorRecoveryManager initializes with default settings"""
        manager = ErrorRecoveryManager()

        assert manager is not None
        assert hasattr(manager, "retry_config")
        assert hasattr(manager, "temp_file_tracker")

    def test_retry_config_defaults(self):
        """Test default retry configuration"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_backoff is True
        assert config.jitter is True

    def test_retry_config_custom_values(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_backoff=False,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_backoff is False
        assert config.jitter is False

    @pytest.mark.asyncio
    async def test_retry_operation_success_on_first_try(self):
        """Test retry operation succeeds on first attempt"""
        manager = ErrorRecoveryManager()

        mock_operation = AsyncMock(return_value="success")

        result = await manager.retry_operation(
            operation=mock_operation, operation_name="test_operation"
        )

        assert result == "success"
        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_operation_success_after_failures(self):
        """Test retry operation succeeds after initial failures"""
        manager = ErrorRecoveryManager()

        # Mock operation that fails twice then succeeds
        mock_operation = AsyncMock(
            side_effect=[
                ConversionError("First failure", can_retry=True),
                ConversionError("Second failure", can_retry=True),
                "success",
            ]
        )

        result = await manager.retry_operation(
            operation=mock_operation, operation_name="test_operation"
        )

        assert result == "success"
        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_operation_fails_after_max_retries(self):
        """Test retry operation fails after exceeding max retries"""
        manager = ErrorRecoveryManager(retry_config=RetryConfig(max_retries=2))

        # Mock operation that always fails
        mock_operation = AsyncMock(
            side_effect=ConversionError("Persistent failure", can_retry=True)
        )

        with pytest.raises(ConversionError) as exc_info:
            await manager.retry_operation(
                operation=mock_operation, operation_name="test_operation"
            )

        assert "Persistent failure" in str(exc_info.value)
        assert mock_operation.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_operation_non_retryable_error(self):
        """Test retry operation with non-retryable error"""
        manager = ErrorRecoveryManager()

        # Mock operation that fails with non-retryable error
        mock_operation = AsyncMock(
            side_effect=ConversionError("Non-retryable failure", can_retry=False)
        )

        with pytest.raises(ConversionError) as exc_info:
            await manager.retry_operation(
                operation=mock_operation, operation_name="test_operation"
            )

        assert "Non-retryable failure" in str(exc_info.value)
        mock_operation.assert_called_once()  # No retries for non-retryable errors

    def test_calculate_delay_exponential_backoff(self):
        """Test delay calculation with exponential backoff"""
        manager = ErrorRecoveryManager(
            retry_config=RetryConfig(
                base_delay=1.0, exponential_backoff=True, jitter=False
            )
        )

        delay_1 = manager._calculate_delay(1)
        delay_2 = manager._calculate_delay(2)
        delay_3 = manager._calculate_delay(3)

        assert delay_1 == 2.0  # base_delay * 2^1
        assert delay_2 == 4.0  # base_delay * 2^2
        assert delay_3 == 8.0  # base_delay * 2^3

    def test_calculate_delay_linear_backoff(self):
        """Test delay calculation with linear backoff"""
        manager = ErrorRecoveryManager(
            retry_config=RetryConfig(
                base_delay=1.0, exponential_backoff=False, jitter=False
            )
        )

        delay_1 = manager._calculate_delay(1)
        delay_2 = manager._calculate_delay(2)
        delay_3 = manager._calculate_delay(3)

        assert delay_1 == 1.0  # base_delay
        assert delay_2 == 1.0  # base_delay
        assert delay_3 == 1.0  # base_delay

    def test_calculate_delay_max_delay_cap(self):
        """Test delay calculation respects max_delay"""
        manager = ErrorRecoveryManager(
            retry_config=RetryConfig(
                base_delay=1.0, max_delay=5.0, exponential_backoff=True, jitter=False
            )
        )

        delay_10 = manager._calculate_delay(10)  # Would be 1024.0 without cap

        assert delay_10 == 5.0  # Capped at max_delay

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_on_error(self):
        """Test temporary file cleanup on error"""
        manager = ErrorRecoveryManager()

        # Add temp files to tracker
        temp_files = ["/tmp/test1.mp3", "/tmp/test2.mp3"]
        for temp_file in temp_files:
            manager.temp_file_tracker.add(temp_file)

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            mock_exists.return_value = True

            await manager.cleanup_temp_files()

            assert mock_unlink.call_count == 2
            assert len(manager.temp_file_tracker) == 0

    def test_get_recovery_suggestion_conversion_error(self):
        """Test recovery suggestion for conversion errors"""
        manager = ErrorRecoveryManager()

        error = ConversionError("FFmpeg not found", error_code="CV001")

        suggestion = manager.get_recovery_suggestion(error)

        assert "install" in suggestion.lower()
        assert "ffmpeg" in suggestion.lower()
        assert (
            "brew install ffmpeg" in suggestion.lower()
            or "apt install ffmpeg" in suggestion.lower()
        )

    def test_get_recovery_suggestion_validation_error(self):
        """Test recovery suggestion for validation errors"""
        manager = ErrorRecoveryManager()

        error = ValidationError("Invalid audio format", error_code="VL001")

        suggestion = manager.get_recovery_suggestion(error)

        assert "check" in suggestion.lower()
        assert "audio file" in suggestion.lower()
        assert "supported format" in suggestion.lower()

    def test_get_recovery_suggestion_transcription_error(self):
        """Test recovery suggestion for transcription errors"""
        manager = ErrorRecoveryManager()

        error = TranscriptionError("Whisper model failed", error_code="TR001")

        suggestion = manager.get_recovery_suggestion(error)

        assert "check" in suggestion.lower()
        assert "model" in suggestion.lower()
        assert "download" in suggestion.lower()

    def test_is_retryable_error_with_retry_flag(self):
        """Test error retryability check with can_retry flag"""
        manager = ErrorRecoveryManager()

        retryable_error = ConversionError("Temporary failure", can_retry=True)
        non_retryable_error = ConversionError("Permanent failure", can_retry=False)

        assert manager._is_retryable_error(retryable_error) is True
        assert manager._is_retryable_error(non_retryable_error) is False

    def test_is_retryable_error_by_error_code(self):
        """Test error retryability check by error code"""
        manager = ErrorRecoveryManager()

        # Test with specific error codes
        timeout_error = ConversionError(
            "Timeout", error_code="CV_TIMEOUT", can_retry=True
        )
        network_error = ConversionError(
            "Network issue", error_code="CV_NETWORK", can_retry=True
        )
        file_not_found = ConversionError(
            "File not found", error_code="CV_FILE_NOT_FOUND", can_retry=False
        )

        # These should be retryable based on their error codes or can_retry flag
        assert manager._is_retryable_error(timeout_error) is True
        assert manager._is_retryable_error(network_error) is True
        assert manager._is_retryable_error(file_not_found) is False
