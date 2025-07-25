import os
import re
import subprocess


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg is not found or not available"""

    pass


class FFmpegChecker:
    """Utility class for checking FFmpeg installation and version"""

    # Minimum required FFmpeg version
    MIN_VERSION = "4.0.0"

    # Installation instructions for different platforms
    INSTALL_INSTRUCTIONS = {
        "darwin": "brew install ffmpeg",
        "linux": "sudo apt install ffmpeg  # Ubuntu/Debian\nsudo yum install ffmpeg  # CentOS/RHEL",
        "win32": "Download from https://ffmpeg.org/download.html",
    }

    def __init__(self, ffmpeg_path: str | None = None):
        """Initialize FFmpeg checker with optional custom path"""
        self.ffmpeg_path = ffmpeg_path or os.environ.get("FFMPEG_PATH", "ffmpeg")

    def check_ffmpeg_installation(self) -> bool:
        """Check if FFmpeg is installed and available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_ffmpeg_version(self) -> str:
        """Get FFmpeg version string"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise FFmpegNotFoundError("FFmpeg command failed")

            # Extract version from output like "ffmpeg version 4.4.2-0ubuntu0.22.04.1"
            version_match = re.search(r"ffmpeg version (\d+\.\d+\.\d+)", result.stdout)
            if version_match:
                return version_match.group(1)
            else:
                raise FFmpegNotFoundError("Could not parse FFmpeg version")

        except FileNotFoundError as e:
            raise FFmpegNotFoundError("FFmpeg not found in system PATH") from e

    def ensure_ffmpeg_available(self) -> None:
        """Ensure FFmpeg is available, raise error if not"""
        if not self.check_ffmpeg_installation():
            import sys

            platform_key = sys.platform
            install_cmd = self.INSTALL_INSTRUCTIONS.get(
                platform_key, "Please install FFmpeg from https://ffmpeg.org/"
            )

            raise FFmpegNotFoundError(
                f"FFmpeg not found. Please install FFmpeg or set FFMPEG_PATH environment variable.\n"
                f"Installation instructions for {platform_key}:\n{install_cmd}"
            )
