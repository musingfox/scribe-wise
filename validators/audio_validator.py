from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import torchaudio


class ValidationStatus(Enum):
    """Status of audio validation"""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"


class AudioValidationError(Exception):
    """Raised when audio validation fails"""

    pass


@dataclass
class AudioValidationResult:
    """Result of audio validation operation"""

    status: ValidationStatus
    file_path: str
    duration: float
    sample_rate: int
    channels: int
    error_message: str | None = None


class AudioValidator:
    """Validator for audio files using torchaudio"""

    def __init__(
        self,
        min_duration: float = 0.1,
        max_duration: float = 3600.0,
        target_sample_rate: int = 16000,
    ):
        """Initialize audio validator with validation criteria"""
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.target_sample_rate = target_sample_rate

    def validate_audio_file(self, file_path: str) -> AudioValidationResult:
        """Validate a single audio file"""
        # Check if file exists
        if not Path(file_path).exists():
            raise AudioValidationError(f"Audio file not found: {file_path}")

        try:
            # Load audio file using torchaudio
            waveform, sample_rate = torchaudio.load(file_path)

            # Extract audio properties
            channels = waveform.shape[0]
            total_samples = waveform.shape[1]
            duration = total_samples / sample_rate

            # Validate duration
            if duration < self.min_duration:
                return AudioValidationResult(
                    status=ValidationStatus.WARNING,
                    file_path=file_path,
                    duration=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    error_message=f"Audio duration ({duration:.2f}s) is too short (minimum: {self.min_duration}s)",
                )

            if duration > self.max_duration:
                return AudioValidationResult(
                    status=ValidationStatus.WARNING,
                    file_path=file_path,
                    duration=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    error_message=f"Audio duration ({duration:.2f}s) is too long (maximum: {self.max_duration}s)",
                )

            # Validate sample rate
            if sample_rate != self.target_sample_rate:
                return AudioValidationResult(
                    status=ValidationStatus.WARNING,
                    file_path=file_path,
                    duration=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    error_message=f"Audio sample rate mismatch: {sample_rate}Hz (expected: {self.target_sample_rate}Hz)",
                )

            # All validations passed
            return AudioValidationResult(
                status=ValidationStatus.VALID,
                file_path=file_path,
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
            )

        except Exception as e:
            return AudioValidationResult(
                status=ValidationStatus.ERROR,
                file_path=file_path,
                duration=0.0,
                sample_rate=0,
                channels=0,
                error_message=f"Failed to load audio file: {str(e)}",
            )

    def validate_multiple_files(
        self, file_paths: list[str]
    ) -> list[AudioValidationResult]:
        """Validate multiple audio files"""
        results = []
        for file_path in file_paths:
            try:
                result = self.validate_audio_file(file_path)
                results.append(result)
            except AudioValidationError as e:
                # Convert exception to error result
                results.append(
                    AudioValidationResult(
                        status=ValidationStatus.ERROR,
                        file_path=file_path,
                        duration=0.0,
                        sample_rate=0,
                        channels=0,
                        error_message=str(e),
                    )
                )
        return results

    def get_validation_summary(self, results: list[AudioValidationResult]) -> dict:
        """Generate validation summary from results"""
        summary = {
            "total_files": len(results),
            "valid_files": 0,
            "warning_files": 0,
            "error_files": 0,
            "total_duration": 0.0,
            "warnings": [],
            "errors": [],
        }

        for result in results:
            if result.status == ValidationStatus.VALID:
                summary["valid_files"] += 1
                summary["total_duration"] += result.duration
            elif result.status == ValidationStatus.WARNING:
                summary["warning_files"] += 1
                summary["total_duration"] += result.duration
                summary["warnings"].append(
                    {"file": result.file_path, "message": result.error_message}
                )
            elif result.status == ValidationStatus.ERROR:
                summary["error_files"] += 1
                summary["errors"].append(
                    {"file": result.file_path, "message": result.error_message}
                )

        return summary
