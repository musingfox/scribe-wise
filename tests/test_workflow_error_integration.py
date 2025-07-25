from unittest.mock import AsyncMock, Mock, patch

import pytest

from exceptions import ConversionError, TranscriptionError, ValidationError
from transcription.workflow import TranscriptionWorkflow
from utils.error_recovery import ErrorRecoveryManager, RetryConfig
from utils.file_detector import FileType
from validators.audio_validator import ValidationStatus


class TestWorkflowErrorIntegration:
    @pytest.mark.asyncio
    async def test_workflow_with_error_recovery_success_after_retry(self):
        """Test workflow succeeds after retry with error recovery"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager(
            retry_config=RetryConfig(max_retries=2)
        )

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock FFmpeg checker to succeed
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()

            # Mock file detector
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.WEBM)

            # Mock converter to fail first time, then succeed
            success_result = Mock(success=True, output_path="/tmp/converted.mp3")
            conversion_side_effects = [
                ConversionError("Temporary failure", can_retry=True),
                success_result,
            ]
            workflow.media_converter.convert_webm_to_mp3 = AsyncMock(
                side_effect=conversion_side_effects
            )

            # Mock validator
            workflow.audio_validator.validate_audio_file = Mock(
                return_value=Mock(status=ValidationStatus.VALID)
            )

            # Mock transcription
            workflow._transcribe_audio = AsyncMock(return_value="Test transcription")

            result = await workflow.process_file("/test/input.webm", "/test/output.txt")

            assert result.success is True
            assert result.transcription == "Test transcription"
            assert workflow.media_converter.convert_webm_to_mp3.call_count == 2

    @pytest.mark.asyncio
    async def test_workflow_with_error_recovery_max_retries_exceeded(self):
        """Test workflow fails after exceeding max retries"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager(
            retry_config=RetryConfig(max_retries=1)
        )

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock FFmpeg checker to succeed
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()

            # Mock file detector
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.WEBM)

            # Mock converter to always fail with retryable error
            workflow.media_converter.convert_webm_to_mp3 = AsyncMock(
                side_effect=ConversionError("Persistent failure", can_retry=True)
            )

            result = await workflow.process_file("/test/input.webm", "/test/output.txt")

            assert result.success is False
            assert "Persistent failure" in result.error_message
            assert (
                workflow.media_converter.convert_webm_to_mp3.call_count == 2
            )  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_workflow_with_non_retryable_error(self):
        """Test workflow handles non-retryable errors correctly"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager()

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock FFmpeg checker to succeed
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()

            # Mock file detector
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.WEBM)

            # Mock converter to fail with non-retryable error
            workflow.media_converter.convert_webm_to_mp3 = AsyncMock(
                side_effect=ConversionError("File not found", can_retry=False)
            )

            result = await workflow.process_file("/test/input.webm", "/test/output.txt")

            assert result.success is False
            assert "File not found" in result.error_message
            # Should not retry non-retryable errors
            workflow.media_converter.convert_webm_to_mp3.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_temp_file_cleanup_on_error(self):
        """Test workflow cleans up temporary files on error"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager()

        # Add temp files to recovery manager
        temp_files = ["/tmp/temp1.mp3", "/tmp/temp2.mp3"]
        for temp_file in temp_files:
            workflow.error_recovery.temp_file_tracker.add(temp_file)

        # Mock Path.exists
        with (
            patch("pathlib.Path.exists") as mock_exists_input,
            patch("pathlib.Path.exists") as mock_exists_temp,
            patch("pathlib.Path.unlink"),
        ):
            mock_exists_input.return_value = True  # Input file exists
            mock_exists_temp.return_value = True  # Temp files exist

            # Mock FFmpeg checker to succeed
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()

            # Mock file detector
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.WEBM)

            # Mock converter to fail
            workflow.media_converter.convert_webm_to_mp3 = AsyncMock(
                side_effect=ConversionError("Conversion failed")
            )

            result = await workflow.process_file("/test/input.webm", "/test/output.txt")

            assert result.success is False
            # Verify temp files were cleaned up
            assert len(workflow.error_recovery.temp_file_tracker) == 0

    @pytest.mark.asyncio
    async def test_workflow_recovery_suggestions_in_result(self):
        """Test workflow includes recovery suggestions in error results"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager()

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock FFmpeg checker to fail
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock(
                side_effect=ConversionError(
                    "FFmpeg not found", error_code="CV001", can_retry=False
                )
            )

            result = await workflow.process_file("/test/input.webm", "/test/output.txt")

            assert result.success is False
            assert "FFmpeg not found" in result.error_message
            # Should include recovery suggestion
            assert "install" in result.error_message.lower()

    def test_workflow_uses_custom_retry_config(self):
        """Test workflow can use custom retry configuration"""
        custom_config = RetryConfig(
            max_retries=5, base_delay=2.0, exponential_backoff=False
        )

        workflow = TranscriptionWorkflow(error_recovery_config=custom_config)

        assert workflow.error_recovery.retry_config.max_retries == 5
        assert workflow.error_recovery.retry_config.base_delay == 2.0
        assert workflow.error_recovery.retry_config.exponential_backoff is False

    @pytest.mark.asyncio
    async def test_workflow_transcription_error_with_context(self):
        """Test workflow handles transcription errors with proper context"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager()

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock successful conversion and validation
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.MP3)
            workflow.audio_validator.validate_audio_file = Mock(
                return_value=Mock(status=ValidationStatus.VALID)
            )

            # Mock transcription to fail with context
            workflow._transcribe_audio = AsyncMock(
                side_effect=TranscriptionError(
                    "Whisper model failed",
                    audio_path="/test/input.mp3",
                    chunk_index=2,
                    duration_seconds=30.0,
                    can_retry=False,
                )
            )

            result = await workflow.process_file("/test/input.mp3", "/test/output.txt")

            assert result.success is False
            assert "Whisper model failed" in result.error_message

    @pytest.mark.asyncio
    async def test_workflow_validation_error_with_issues(self):
        """Test workflow handles validation errors with detailed issues"""
        workflow = TranscriptionWorkflow()
        workflow.error_recovery = ErrorRecoveryManager()

        # Mock Path.exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock successful setup
            workflow.ffmpeg_checker.ensure_ffmpeg_available = Mock()
            workflow.file_detector.detect_file_type = Mock(return_value=FileType.MP3)

            # Mock validation to fail with detailed issues
            workflow.audio_validator.validate_audio_file = Mock(
                side_effect=ValidationError(
                    "Audio validation failed",
                    file_path="/test/input.mp3",
                    validation_issues=["Invalid sample rate", "Corrupted header"],
                    can_retry=False,
                )
            )

            result = await workflow.process_file("/test/input.mp3", "/test/output.txt")

            assert result.success is False
            assert "Audio validation failed" in result.error_message
