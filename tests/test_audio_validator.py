import pytest
import torch

from validators.audio_validator import (
    AudioValidationError,
    AudioValidationResult,
    AudioValidator,
    ValidationStatus,
)


class TestAudioValidator:
    def test_init_creates_validator_with_defaults(self):
        """Test that AudioValidator initializes with default settings"""
        validator = AudioValidator()
        assert validator.min_duration == 0.1
        assert validator.max_duration == 3600.0
        assert validator.target_sample_rate == 16000

    def test_init_creates_validator_with_custom_settings(self):
        """Test that AudioValidator initializes with custom settings"""
        validator = AudioValidator(
            min_duration=1.0, max_duration=1800.0, target_sample_rate=22050
        )
        assert validator.min_duration == 1.0
        assert validator.max_duration == 1800.0
        assert validator.target_sample_rate == 22050

    def test_validate_audio_file_success(self, mocker):
        """Test successful audio file validation"""
        validator = AudioValidator()

        # Mock torchaudio.load to return valid audio data
        mock_load = mocker.patch("torchaudio.load")
        mock_load.return_value = (
            torch.randn(2, 16000),  # 2 channels, 1 second at 16kHz
            16000,  # sample rate
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = validator.validate_audio_file("/test/audio.mp3")

        assert isinstance(result, AudioValidationResult)
        assert result.status == ValidationStatus.VALID
        assert result.file_path == "/test/audio.mp3"
        assert result.duration == 1.0
        assert result.sample_rate == 16000
        assert result.channels == 2
        assert result.error_message is None

    def test_validate_audio_file_not_found(self):
        """Test validation with non-existent audio file"""
        validator = AudioValidator()

        with pytest.raises(AudioValidationError, match="Audio file not found"):
            validator.validate_audio_file("/nonexistent/audio.mp3")

    def test_validate_audio_file_too_short(self, mocker):
        """Test validation with audio file that is too short"""
        validator = AudioValidator(min_duration=2.0)

        # Mock torchaudio.load to return short audio
        mock_load = mocker.patch("torchaudio.load")
        mock_load.return_value = (
            torch.randn(1, 8000),  # 0.5 seconds at 16kHz
            16000,
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = validator.validate_audio_file("/test/short_audio.mp3")

        assert result.status == ValidationStatus.WARNING
        assert "too short" in result.error_message
        assert result.duration == 0.5

    def test_validate_audio_file_too_long(self, mocker):
        """Test validation with audio file that is too long"""
        validator = AudioValidator(max_duration=10.0)

        # Mock torchaudio.load to return long audio
        mock_load = mocker.patch("torchaudio.load")
        mock_load.return_value = (
            torch.randn(1, 320000),  # 20 seconds at 16kHz
            16000,
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = validator.validate_audio_file("/test/long_audio.mp3")

        assert result.status == ValidationStatus.WARNING
        assert "too long" in result.error_message
        assert result.duration == 20.0

    def test_validate_audio_file_wrong_sample_rate(self, mocker):
        """Test validation with wrong sample rate"""
        validator = AudioValidator(target_sample_rate=16000)

        # Mock torchaudio.load to return audio with wrong sample rate
        mock_load = mocker.patch("torchaudio.load")
        mock_load.return_value = (
            torch.randn(1, 44100),  # 1 second at 44.1kHz
            44100,
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = validator.validate_audio_file("/test/wrong_rate.mp3")

        assert result.status == ValidationStatus.WARNING
        assert "sample rate mismatch" in result.error_message
        assert result.sample_rate == 44100

    def test_validate_audio_file_load_error(self, mocker):
        """Test validation when torchaudio.load fails"""
        validator = AudioValidator()

        # Mock torchaudio.load to raise exception
        mock_load = mocker.patch("torchaudio.load")
        mock_load.side_effect = RuntimeError("Unsupported audio format")

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        result = validator.validate_audio_file("/test/corrupt.mp3")

        assert result.status == ValidationStatus.ERROR
        assert "Failed to load audio" in result.error_message

    def test_validate_multiple_files_success(self, mocker):
        """Test validation of multiple audio files"""
        validator = AudioValidator()

        # Mock torchaudio.load to return valid audio data
        mock_load = mocker.patch("torchaudio.load")
        mock_load.return_value = (
            torch.randn(2, 16000),  # 2 channels, 1 second at 16kHz
            16000,
        )

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        files = ["/test/audio1.mp3", "/test/audio2.mp3"]
        results = validator.validate_multiple_files(files)

        assert len(results) == 2
        assert all(result.status == ValidationStatus.VALID for result in results)
        assert results[0].file_path == "/test/audio1.mp3"
        assert results[1].file_path == "/test/audio2.mp3"

    def test_validate_multiple_files_mixed_results(self, mocker):
        """Test validation of multiple files with mixed results"""
        validator = AudioValidator()

        # Mock different results for different files
        def mock_load_side_effect(file_path):
            if "good" in file_path:
                return (torch.randn(2, 16000), 16000)
            else:
                raise RuntimeError("Bad audio")

        mock_load = mocker.patch("torchaudio.load")
        mock_load.side_effect = mock_load_side_effect

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        files = ["/test/good_audio.mp3", "/test/bad_audio.mp3"]
        results = validator.validate_multiple_files(files)

        assert len(results) == 2
        assert results[0].status == ValidationStatus.VALID
        assert results[1].status == ValidationStatus.ERROR

    def test_get_validation_summary(self, mocker):
        """Test validation summary generation"""
        validator = AudioValidator()

        # Create mock results
        results = [
            AudioValidationResult(
                status=ValidationStatus.VALID,
                file_path="/test/good1.mp3",
                duration=10.0,
                sample_rate=16000,
                channels=2,
            ),
            AudioValidationResult(
                status=ValidationStatus.VALID,
                file_path="/test/good2.mp3",
                duration=15.0,
                sample_rate=16000,
                channels=1,
            ),
            AudioValidationResult(
                status=ValidationStatus.WARNING,
                file_path="/test/warning.mp3",
                duration=5.0,
                sample_rate=44100,
                channels=2,
                error_message="Sample rate mismatch",
            ),
            AudioValidationResult(
                status=ValidationStatus.ERROR,
                file_path="/test/error.mp3",
                duration=0.0,
                sample_rate=0,
                channels=0,
                error_message="Failed to load",
            ),
        ]

        summary = validator.get_validation_summary(results)

        assert summary["total_files"] == 4
        assert summary["valid_files"] == 2
        assert summary["warning_files"] == 1
        assert summary["error_files"] == 1
        assert summary["total_duration"] == 30.0
        assert len(summary["warnings"]) == 1
        assert len(summary["errors"]) == 1
