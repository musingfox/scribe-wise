from exceptions.base import ScribbleWiseError
from exceptions.conversion import ConversionError
from exceptions.transcription import TranscriptionError
from exceptions.validation import ValidationError


class TestScribbleWiseExceptions:
    def test_scribble_wise_error_base_exception(self):
        """Test ScribbleWiseError base exception"""
        error = ScribbleWiseError("Base error message")

        assert isinstance(error, Exception)
        assert str(error) == "Base error message"
        assert error.message == "Base error message"
        assert error.error_code is None
        assert error.recovery_suggestion is None

    def test_scribble_wise_error_with_code_and_suggestion(self):
        """Test ScribbleWiseError with error code and recovery suggestion"""
        error = ScribbleWiseError(
            "Error with details",
            error_code="SW001",
            recovery_suggestion="Try this solution",
        )

        assert error.message == "Error with details"
        assert error.error_code == "SW001"
        assert error.recovery_suggestion == "Try this solution"

    def test_conversion_error_inheritance(self):
        """Test ConversionError inherits from ScribbleWiseError"""
        error = ConversionError("Conversion failed")

        assert isinstance(error, ScribbleWiseError)
        assert isinstance(error, Exception)
        assert str(error) == "Conversion failed"

    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from ScribbleWiseError"""
        error = ValidationError("Validation failed")

        assert isinstance(error, ScribbleWiseError)
        assert isinstance(error, Exception)
        assert str(error) == "Validation failed"

    def test_transcription_error_inheritance(self):
        """Test TranscriptionError inherits from ScribbleWiseError"""
        error = TranscriptionError("Transcription failed")

        assert isinstance(error, ScribbleWiseError)
        assert isinstance(error, Exception)
        assert str(error) == "Transcription failed"

    def test_conversion_error_with_file_paths(self):
        """Test ConversionError with input/output file paths"""
        error = ConversionError(
            "FFmpeg conversion failed",
            input_path="/test/input.webm",
            output_path="/test/output.mp3",
        )

        assert error.message == "FFmpeg conversion failed"
        assert error.input_path == "/test/input.webm"
        assert error.output_path == "/test/output.mp3"

    def test_validation_error_with_validation_details(self):
        """Test ValidationError with validation details"""
        error = ValidationError(
            "Audio file validation failed",
            file_path="/test/audio.mp3",
            validation_issues=["Invalid sample rate", "Corrupted file"],
        )

        assert error.message == "Audio file validation failed"
        assert error.file_path == "/test/audio.mp3"
        assert error.validation_issues == ["Invalid sample rate", "Corrupted file"]

    def test_transcription_error_with_context(self):
        """Test TranscriptionError with transcription context"""
        error = TranscriptionError(
            "Whisper model failed",
            audio_path="/test/audio.mp3",
            chunk_index=5,
            duration_seconds=30.0,
        )

        assert error.message == "Whisper model failed"
        assert error.audio_path == "/test/audio.mp3"
        assert error.chunk_index == 5
        assert error.duration_seconds == 30.0

    def test_error_serialization(self):
        """Test error serialization to dict"""
        error = ConversionError(
            "FFmpeg not found",
            error_code="CV001",
            recovery_suggestion="Install FFmpeg",
            input_path="/test/input.webm",
        )

        error_dict = error.to_dict()

        expected_dict = {
            "error_type": "ConversionError",
            "message": "FFmpeg not found",
            "error_code": "CV001",
            "recovery_suggestion": "Install FFmpeg",
            "input_path": "/test/input.webm",
            "output_path": None,
        }

        assert error_dict == expected_dict

    def test_error_with_retry_capability(self):
        """Test error with retry capability flag"""
        error = ConversionError(
            "Temporary conversion failure", can_retry=True, max_retries=3
        )

        assert error.can_retry is True
        assert error.max_retries == 3
