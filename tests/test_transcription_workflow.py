from unittest.mock import Mock

import pytest

from transcription.workflow import (
    TranscriptionResult,
    TranscriptionWorkflow,
)


class TestTranscriptionWorkflow:
    def test_init_creates_workflow_with_defaults(self):
        """Test that TranscriptionWorkflow initializes with default settings"""
        workflow = TranscriptionWorkflow()
        assert workflow is not None
        assert hasattr(workflow, "ffmpeg_checker")
        assert hasattr(workflow, "file_detector")
        assert hasattr(workflow, "media_converter")
        assert hasattr(workflow, "audio_validator")

    @pytest.mark.asyncio
    async def test_process_webm_to_transcription_success(self, mocker):
        """Test successful WebM to transcription conversion"""
        workflow = TranscriptionWorkflow()

        # Mock all dependencies
        mock_ffmpeg_check = mocker.patch.object(
            workflow.ffmpeg_checker, "ensure_ffmpeg_available"
        )
        mock_detect_type = mocker.patch.object(
            workflow.file_detector, "detect_file_type"
        )
        mock_convert = mocker.patch.object(
            workflow.media_converter, "convert_webm_to_mp3"
        )
        mock_validate = mocker.patch.object(
            workflow.audio_validator, "validate_audio_file"
        )
        mock_transcribe = mocker.patch.object(workflow, "_transcribe_audio")

        # Setup mock returns
        from converters.media_converter import ConversionResult
        from utils.file_detector import FileType
        from validators.audio_validator import AudioValidationResult, ValidationStatus

        mock_detect_type.return_value = FileType.WEBM
        mock_convert.return_value = ConversionResult(
            success=True,
            input_path="/test/input.webm",
            output_path="/test/output.mp3",
        )
        mock_validate.return_value = AudioValidationResult(
            status=ValidationStatus.VALID,
            file_path="/test/output.mp3",
            duration=60.0,
            sample_rate=16000,
            channels=2,
        )
        mock_transcribe.return_value = "Test transcription result"

        # Mock Path.exists for input file
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = await workflow.process_file("/test/input.webm", "/test/output.txt")

        assert isinstance(result, TranscriptionResult)
        assert result.success is True
        assert result.input_path == "/test/input.webm"
        assert result.output_path == "/test/output.txt"
        assert result.transcription == "Test transcription result"
        assert result.error_message is None

        # Verify all steps were called
        mock_ffmpeg_check.assert_called_once()
        mock_detect_type.assert_called_once_with("/test/input.webm")
        mock_convert.assert_called_once()
        mock_validate.assert_called_once_with("/test/input.mp3")
        mock_transcribe.assert_called_once_with("/test/input.mp3")

    @pytest.mark.asyncio
    async def test_process_mp3_direct_transcription(self, mocker):
        """Test direct MP3 transcription without conversion"""
        workflow = TranscriptionWorkflow()

        # Mock dependencies (skip conversion for MP3)
        mock_detect_type = mocker.patch.object(
            workflow.file_detector, "detect_file_type"
        )
        mock_validate = mocker.patch.object(
            workflow.audio_validator, "validate_audio_file"
        )
        mock_transcribe = mocker.patch.object(workflow, "_transcribe_audio")

        from utils.file_detector import FileType
        from validators.audio_validator import AudioValidationResult, ValidationStatus

        mock_detect_type.return_value = FileType.MP3
        mock_validate.return_value = AudioValidationResult(
            status=ValidationStatus.VALID,
            file_path="/test/input.mp3",
            duration=60.0,
            sample_rate=16000,
            channels=2,
        )
        mock_transcribe.return_value = "Direct MP3 transcription"

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = await workflow.process_file("/test/input.mp3", "/test/output.txt")

        assert result.success is True
        assert result.transcription == "Direct MP3 transcription"

        # Verify conversion was skipped
        mock_detect_type.assert_called_once_with("/test/input.mp3")
        mock_validate.assert_called_once_with("/test/input.mp3")
        mock_transcribe.assert_called_once_with("/test/input.mp3")

    @pytest.mark.asyncio
    async def test_process_file_not_found(self):
        """Test processing with non-existent input file"""
        workflow = TranscriptionWorkflow()

        result = await workflow.process_file(
            "/nonexistent/file.webm", "/test/output.txt"
        )

        assert result.success is False
        assert "Input file not found" in result.error_message

    @pytest.mark.asyncio
    async def test_process_unsupported_file_type(self, mocker):
        """Test processing with unsupported file type"""
        workflow = TranscriptionWorkflow()

        mock_detect_type = mocker.patch.object(
            workflow.file_detector, "detect_file_type"
        )

        from utils.file_detector import UnsupportedFileError

        mock_detect_type.side_effect = UnsupportedFileError("Unsupported file type")

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = await workflow.process_file(
            "/test/unsupported.xyz", "/test/output.txt"
        )

        assert result.success is False
        assert "Unsupported file type" in result.error_message

    @pytest.mark.asyncio
    async def test_process_conversion_failure(self, mocker):
        """Test handling of conversion failure"""
        workflow = TranscriptionWorkflow()

        # Mock dependencies
        mocker.patch.object(workflow.ffmpeg_checker, "ensure_ffmpeg_available")
        mock_detect_type = mocker.patch.object(
            workflow.file_detector, "detect_file_type"
        )
        mock_convert = mocker.patch.object(
            workflow.media_converter, "convert_webm_to_mp3"
        )

        from converters.media_converter import ConversionResult
        from utils.file_detector import FileType

        mock_detect_type.return_value = FileType.WEBM
        mock_convert.return_value = ConversionResult(
            success=False,
            input_path="/test/input.webm",
            output_path="/test/output.mp3",
            error_message="FFmpeg conversion failed",
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = await workflow.process_file("/test/input.webm", "/test/output.txt")

        assert result.success is False
        assert "FFmpeg conversion failed" in result.error_message

    @pytest.mark.asyncio
    async def test_process_audio_validation_error(self, mocker):
        """Test handling of audio validation error"""
        workflow = TranscriptionWorkflow()

        # Mock successful conversion but validation error
        mocker.patch.object(workflow.ffmpeg_checker, "ensure_ffmpeg_available")
        mock_detect_type = mocker.patch.object(
            workflow.file_detector, "detect_file_type"
        )
        mock_convert = mocker.patch.object(
            workflow.media_converter, "convert_webm_to_mp3"
        )
        mock_validate = mocker.patch.object(
            workflow.audio_validator, "validate_audio_file"
        )

        from converters.media_converter import ConversionResult
        from utils.file_detector import FileType
        from validators.audio_validator import AudioValidationResult, ValidationStatus

        mock_detect_type.return_value = FileType.WEBM
        mock_convert.return_value = ConversionResult(
            success=True,
            input_path="/test/input.webm",
            output_path="/test/output.mp3",
        )
        mock_validate.return_value = AudioValidationResult(
            status=ValidationStatus.ERROR,
            file_path="/test/output.mp3",
            duration=0.0,
            sample_rate=0,
            channels=0,
            error_message="Invalid audio format",
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = await workflow.process_file("/test/input.webm", "/test/output.txt")

        assert result.success is False
        assert "Invalid audio format" in result.error_message

    def test_get_supported_input_formats(self):
        """Test getting supported input formats"""
        workflow = TranscriptionWorkflow()
        formats = workflow.get_supported_input_formats()

        assert isinstance(formats, list)
        assert "webm" in formats
        assert "mp3" in formats
        assert "mp4" in formats

    def test_cleanup_temp_files(self, mocker):
        """Test temporary file cleanup functionality"""
        workflow = TranscriptionWorkflow()

        # Mock Path operations
        mock_path_class = mocker.patch("transcription.workflow.Path")
        mock_instance = Mock()
        mock_instance.exists.return_value = True
        mock_path_class.return_value = mock_instance

        workflow._cleanup_temp_files(["/temp/file1.mp3", "/temp/file2.mp3"])

        # Verify cleanup was attempted for both files
        assert mock_path_class.call_count == 2
        assert mock_instance.unlink.call_count == 2
