import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class QualityLevel(Enum):
    """Audio quality levels for conversion"""

    LOW = "128k"
    MEDIUM = "160k"
    HIGH = "256k"


class ConversionError(Exception):
    """Raised when media conversion fails"""

    pass


@dataclass
class ConversionResult:
    """Result of media conversion operation"""

    success: bool
    input_path: str
    output_path: str
    error_message: str | None = None
    duration_seconds: float | None = None


class MediaConverter:
    """Converter for media files using FFmpeg"""

    def __init__(
        self,
        quality: QualityLevel = QualityLevel.MEDIUM,
        timeout_minutes: int = 10,
    ):
        """Initialize media converter with quality and timeout settings"""
        self.quality = quality
        self.timeout_seconds = timeout_minutes * 60

    async def convert_webm_to_mp3(
        self, input_path: str, output_path: str
    ) -> ConversionResult:
        """Convert WebM file to MP3 format"""
        # Check if input file exists
        if not Path(input_path).exists():
            raise ConversionError(f"Input file not found: {input_path}")

        try:
            # Generate FFmpeg command
            command = self._get_ffmpeg_command(input_path, output_path)

            # Execute FFmpeg command with timeout
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for process completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    output_path=output_path,
                    error_message=f"Conversion timeout after {self.timeout_seconds} seconds",
                )

            # Check if conversion was successful
            if process.returncode == 0 and Path(output_path).exists():
                return ConversionResult(
                    success=True, input_path=input_path, output_path=output_path
                )
            else:
                error_msg = stderr.decode() if stderr else "Unknown conversion error"
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    output_path=output_path,
                    error_message=error_msg,
                )

        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                error_message=str(e),
            )

    def _get_ffmpeg_command(self, input_path: str, output_path: str) -> list[str]:
        """Generate FFmpeg command for WebM to MP3 conversion"""
        return [
            "ffmpeg",
            "-i",
            input_path,
            "-vn",  # No video
            "-acodec",
            "libmp3lame",
            "-ac",
            "2",  # Stereo
            "-ab",
            self.quality.value,  # Bitrate based on quality
            "-ar",
            "16000",  # 16kHz sample rate
            output_path,
        ]

    def _cleanup_temp_files(self, temp_files: list[str]) -> None:
        """Clean up temporary files"""
        for temp_file in temp_files:
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()
