"""Cross-platform compatibility utilities for Scrible Wise."""

import logging
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PlatformInfo:
    """Information about the current platform."""

    system: str  # Windows, Darwin, Linux
    architecture: str  # x86_64, arm64, etc.
    python_version: str
    is_windows: bool
    is_macos: bool
    is_linux: bool
    supports_mps: bool
    supports_cuda: bool
    ffmpeg_available: bool


class PlatformCompatibility:
    """Handle cross-platform compatibility concerns."""

    def __init__(self):
        """Initialize platform compatibility checker."""
        self.logger = logging.getLogger(__name__)
        self._platform_info = self._detect_platform()

    def _detect_platform(self) -> PlatformInfo:
        """Detect current platform and capabilities."""
        system = platform.system()
        architecture = platform.machine()
        python_version = platform.python_version()

        is_windows = system == "Windows"
        is_macos = system == "Darwin"
        is_linux = system == "Linux"

        # Check for MPS support (Apple Silicon)
        supports_mps = False
        if is_macos:
            try:
                import torch

                supports_mps = torch.backends.mps.is_available()
            except Exception:
                supports_mps = False

        # Check for CUDA support
        supports_cuda = False
        try:
            import torch

            supports_cuda = torch.cuda.is_available()
        except Exception:
            supports_cuda = False

        # Check FFmpeg availability
        ffmpeg_available = shutil.which("ffmpeg") is not None

        return PlatformInfo(
            system=system,
            architecture=architecture,
            python_version=python_version,
            is_windows=is_windows,
            is_macos=is_macos,
            is_linux=is_linux,
            supports_mps=supports_mps,
            supports_cuda=supports_cuda,
            ffmpeg_available=ffmpeg_available,
        )

    def get_platform_info(self) -> PlatformInfo:
        """Get platform information."""
        return self._platform_info

    def get_optimal_torch_device(self) -> str:
        """Get optimal torch device for current platform."""
        if self._platform_info.supports_mps:
            return "mps"
        elif self._platform_info.supports_cuda:
            return "cuda"
        else:
            return "cpu"

    def get_path_separator(self) -> str:
        """Get appropriate path separator for platform."""
        return os.sep

    def normalize_path(self, path: str) -> str:
        """Normalize path for current platform."""
        return str(Path(path).resolve())

    def get_temp_directory(self) -> str:
        """Get appropriate temporary directory for platform."""
        if self._platform_info.is_windows:
            return os.environ.get("TEMP", "C:\\Windows\\Temp")
        else:
            return "/tmp"

    def get_config_directory(self) -> str:
        """Get appropriate configuration directory for platform."""
        if self._platform_info.is_windows:
            appdata = os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming")
            return str(Path(appdata) / "ScribbleWise")
        elif self._platform_info.is_macos:
            return os.path.expanduser("~/Library/Application Support/ScribbleWise")
        else:  # Linux
            return os.path.expanduser("~/.config/scribble-wise")

    def get_cache_directory(self) -> str:
        """Get appropriate cache directory for platform."""
        if self._platform_info.is_windows:
            localappdata = os.environ.get(
                "LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"
            )
            return str(Path(localappdata) / "ScribbleWise" / "Cache")
        elif self._platform_info.is_macos:
            return os.path.expanduser("~/Library/Caches/ScribbleWise")
        else:  # Linux
            return os.path.expanduser("~/.cache/scribble-wise")

    def ensure_directory_exists(self, directory: str) -> bool:
        """Ensure directory exists, create if necessary."""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            self.logger.error(f"Failed to create directory {directory}: {e}")
            return False

    def get_ffmpeg_install_instructions(self) -> str:
        """Get platform-specific FFmpeg installation instructions."""
        if self._platform_info.is_windows:
            return (
                "Install FFmpeg for Windows:\n"
                "1. Download from https://ffmpeg.org/download.html#build-windows\n"
                "2. Extract to a folder (e.g., C:\\ffmpeg)\n"
                "3. Add C:\\ffmpeg\\bin to your system PATH\n"
                "4. Restart your command prompt"
            )
        elif self._platform_info.is_macos:
            return (
                "Install FFmpeg for macOS:\n"
                "Using Homebrew: brew install ffmpeg\n"
                "Using MacPorts: sudo port install ffmpeg"
            )
        else:  # Linux
            return (
                "Install FFmpeg for Linux:\n"
                "Ubuntu/Debian: sudo apt install ffmpeg\n"
                "RHEL/CentOS: sudo yum install ffmpeg\n"
                "Fedora: sudo dnf install ffmpeg\n"
                "Arch: sudo pacman -S ffmpeg"
            )

    def get_memory_recommendations(self) -> dict[str, Any]:
        """Get memory recommendations based on platform."""
        recommendations = {
            "min_ram_gb": 4,
            "recommended_ram_gb": 8,
            "model_cache_mb": 2048,
            "chunk_processing_mb": 1024,
        }

        # Adjust for platform-specific considerations
        if self._platform_info.supports_mps:
            # Apple Silicon typically has unified memory
            recommendations["recommended_ram_gb"] = 16
            recommendations["model_cache_mb"] = 4096
        elif self._platform_info.supports_cuda:
            # CUDA systems often have dedicated VRAM
            recommendations["gpu_vram_gb"] = 4
            recommendations["model_cache_mb"] = 1024  # Smaller CPU cache
        else:
            # CPU-only systems need more RAM for models
            recommendations["recommended_ram_gb"] = 16
            recommendations["model_cache_mb"] = 3072

        return recommendations

    def validate_system_requirements(self) -> list[str]:
        """Validate system meets minimum requirements."""
        issues = []

        # Check Python version
        python_major, python_minor = map(
            int, self._platform_info.python_version.split(".")[:2]
        )
        if python_major < 3 or (python_major == 3 and python_minor < 13):
            issues.append(
                f"Python 3.13+ required, found {self._platform_info.python_version}"
            )

        # Check FFmpeg
        if not self._platform_info.ffmpeg_available:
            issues.append("FFmpeg not found. Video conversion will not work.")

        # Check PyTorch
        try:
            import torch  # noqa: F401
        except ImportError:
            issues.append("PyTorch not installed")

        # Check for audio libraries
        try:
            import librosa  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError:
            issues.append("Audio libraries (soundfile, librosa) not installed")

        # Platform-specific checks
        if self._platform_info.is_windows:
            # Check for long path support
            try:
                test_path = "\\\\?\\" + "a" * 260  # Very long path
                Path(test_path)  # Just test path creation
            except OSError:
                issues.append(
                    "Windows long path support may be required for model caching"
                )

        return issues

    def get_model_download_path(self) -> str:
        """Get appropriate path for downloading models."""
        cache_dir = self.get_cache_directory()
        model_dir = os.path.join(cache_dir, "models")
        self.ensure_directory_exists(model_dir)
        return model_dir

    def get_temp_file_path(self, filename: str) -> str:
        """Get temporary file path with platform-appropriate naming."""
        temp_dir = self.get_temp_directory()

        # Ensure filename is safe for all platforms
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")

        return os.path.join(temp_dir, f"scribble_wise_{safe_filename}")

    def log_platform_info(self) -> None:
        """Log detailed platform information."""
        info = self._platform_info

        self.logger.info(f"Platform: {info.system} {info.architecture}")
        self.logger.info(f"Python: {info.python_version}")

        # Hardware acceleration
        acceleration = []
        if info.supports_mps:
            acceleration.append("MPS")
        if info.supports_cuda:
            acceleration.append("CUDA")
        if not acceleration:
            acceleration.append("CPU-only")

        self.logger.info(f"Acceleration: {', '.join(acceleration)}")
        self.logger.info(
            f"FFmpeg: {'Available' if info.ffmpeg_available else 'Not found'}"
        )

        # Memory recommendations
        memory_rec = self.get_memory_recommendations()
        self.logger.info(
            f"Memory recommendations: {memory_rec['recommended_ram_gb']}GB RAM, "
            f"{memory_rec['model_cache_mb']}MB model cache"
        )

    def setup_environment(self) -> bool:
        """Setup environment for optimal performance on current platform."""
        try:
            # Create necessary directories
            directories = [
                self.get_config_directory(),
                self.get_cache_directory(),
                self.get_model_download_path(),
            ]

            for directory in directories:
                if not self.ensure_directory_exists(directory):
                    return False

            # Platform-specific optimizations
            if self._platform_info.is_windows:
                # Set console encoding for Windows
                try:
                    import sys

                    if hasattr(sys.stdout, "reconfigure"):
                        sys.stdout.reconfigure(encoding="utf-8")
                        sys.stderr.reconfigure(encoding="utf-8")
                except Exception:
                    pass

            # Set torch thread configuration
            try:
                import torch

                if self._platform_info.system == "Darwin":
                    # macOS optimization
                    torch.set_num_threads(min(4, os.cpu_count() or 1))
                else:
                    # Linux/Windows optimization
                    torch.set_num_threads(min(8, os.cpu_count() or 1))
            except Exception:
                pass

            self.logger.info("Environment setup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Environment setup failed: {e}")
            return False
