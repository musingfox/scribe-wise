"""Tests for cross-platform compatibility utilities."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from utils.platform_compatibility import PlatformCompatibility, PlatformInfo


class TestPlatformInfo:
    def test_platform_info_creation(self):
        """Test platform info dataclass creation."""
        info = PlatformInfo(
            system="Darwin",
            architecture="arm64",
            python_version="3.13.0",
            is_windows=False,
            is_macos=True,
            is_linux=False,
            supports_mps=True,
            supports_cuda=False,
            ffmpeg_available=True,
        )

        assert info.system == "Darwin"
        assert info.architecture == "arm64"
        assert info.python_version == "3.13.0"
        assert info.is_macos is True
        assert info.supports_mps is True
        assert info.ffmpeg_available is True


class TestPlatformCompatibility:
    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.python_version")
    @patch("shutil.which")
    def test_detect_platform_macos(
        self, mock_which, mock_python_version, mock_machine, mock_system
    ):
        """Test platform detection for macOS."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        mock_python_version.return_value = "3.13.0"
        mock_which.return_value = "/opt/homebrew/bin/ffmpeg"

        with patch("torch.backends.mps.is_available", return_value=True):
            compat = PlatformCompatibility()
            info = compat.get_platform_info()

            assert info.system == "Darwin"
            assert info.architecture == "arm64"
            assert info.is_macos is True
            assert info.is_windows is False
            assert info.is_linux is False
            assert info.supports_mps is True
            assert info.ffmpeg_available is True

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.python_version")
    @patch("shutil.which")
    def test_detect_platform_windows(
        self, mock_which, mock_python_version, mock_machine, mock_system
    ):
        """Test platform detection for Windows."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"
        mock_python_version.return_value = "3.13.0"
        mock_which.return_value = "C:\\ffmpeg\\bin\\ffmpeg.exe"

        with patch("torch.cuda.is_available", return_value=True):
            compat = PlatformCompatibility()
            info = compat.get_platform_info()

            assert info.system == "Windows"
            assert info.architecture == "AMD64"
            assert info.is_windows is True
            assert info.is_macos is False
            assert info.is_linux is False
            assert info.supports_cuda is True
            assert info.ffmpeg_available is True

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.python_version")
    @patch("shutil.which")
    def test_detect_platform_linux(
        self, mock_which, mock_python_version, mock_machine, mock_system
    ):
        """Test platform detection for Linux."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        mock_python_version.return_value = "3.13.0"
        mock_which.return_value = "/usr/bin/ffmpeg"

        compat = PlatformCompatibility()
        info = compat.get_platform_info()

        assert info.system == "Linux"
        assert info.architecture == "x86_64"
        assert info.is_linux is True
        assert info.is_windows is False
        assert info.is_macos is False
        assert info.ffmpeg_available is True

    def test_get_optimal_torch_device_mps(self):
        """Test optimal torch device selection for MPS."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = True
        compat._platform_info.supports_cuda = False

        device = compat.get_optimal_torch_device()
        assert device == "mps"

    def test_get_optimal_torch_device_cuda(self):
        """Test optimal torch device selection for CUDA."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = False
        compat._platform_info.supports_cuda = True

        device = compat.get_optimal_torch_device()
        assert device == "cuda"

    def test_get_optimal_torch_device_cpu(self):
        """Test optimal torch device selection fallback to CPU."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = False
        compat._platform_info.supports_cuda = False

        device = compat.get_optimal_torch_device()
        assert device == "cpu"

    def test_get_path_separator(self):
        """Test path separator retrieval."""
        compat = PlatformCompatibility()
        separator = compat.get_path_separator()
        assert separator == os.sep

    def test_normalize_path(self):
        """Test path normalization."""
        compat = PlatformCompatibility()

        test_path = "some/relative/path"
        normalized = compat.normalize_path(test_path)

        # Should be absolute and normalized
        assert Path(normalized).is_absolute()
        assert str(Path(test_path).resolve()) == normalized

    def test_get_temp_directory_windows(self):
        """Test temp directory for Windows."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = True

        with patch.dict(os.environ, {"TEMP": "C:\\Windows\\Temp"}):
            temp_dir = compat.get_temp_directory()
            assert temp_dir == "C:\\Windows\\Temp"

    def test_get_temp_directory_unix(self):
        """Test temp directory for Unix-like systems."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False

        temp_dir = compat.get_temp_directory()
        assert temp_dir == "/tmp"

    def test_get_config_directory_windows(self):
        """Test config directory for Windows."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = True
        compat._platform_info.is_macos = False

        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            config_dir = compat.get_config_directory()
            # Path normalization may convert separators on different OS
            expected = str(Path("C:\\Users\\Test\\AppData\\Roaming") / "ScribbleWise")
            assert config_dir == expected

    def test_get_config_directory_macos(self):
        """Test config directory for macOS."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = True

        with patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = (
                "/Users/test/Library/Application Support/ScribbleWise"
            )
            config_dir = compat.get_config_directory()
            assert config_dir == "/Users/test/Library/Application Support/ScribbleWise"

    def test_get_config_directory_linux(self):
        """Test config directory for Linux."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = False

        with patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/test/.config/scribble-wise"
            config_dir = compat.get_config_directory()
            assert config_dir == "/home/test/.config/scribble-wise"

    def test_get_cache_directory_windows(self):
        """Test cache directory for Windows."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = True
        compat._platform_info.is_macos = False

        with patch.dict(
            os.environ, {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}
        ):
            cache_dir = compat.get_cache_directory()
            # Path normalization may convert separators on different OS
            expected = str(
                Path("C:\\Users\\Test\\AppData\\Local") / "ScribbleWise" / "Cache"
            )
            assert cache_dir == expected

    def test_get_cache_directory_macos(self):
        """Test cache directory for macOS."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = True

        with patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/Users/test/Library/Caches/ScribbleWise"
            cache_dir = compat.get_cache_directory()
            assert cache_dir == "/Users/test/Library/Caches/ScribbleWise"

    def test_get_cache_directory_linux(self):
        """Test cache directory for Linux."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = False

        with patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/test/.cache/scribble-wise"
            cache_dir = compat.get_cache_directory()
            assert cache_dir == "/home/test/.cache/scribble-wise"

    @patch("pathlib.Path.mkdir")
    def test_ensure_directory_exists_success(self, mock_mkdir):
        """Test successful directory creation."""
        compat = PlatformCompatibility()

        result = compat.ensure_directory_exists("/test/directory")

        assert result is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_ensure_directory_exists_failure(self, mock_mkdir):
        """Test directory creation failure."""
        mock_mkdir.side_effect = OSError("Permission denied")

        compat = PlatformCompatibility()
        result = compat.ensure_directory_exists("/test/directory")

        assert result is False

    def test_get_ffmpeg_install_instructions_windows(self):
        """Test FFmpeg installation instructions for Windows."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = True
        compat._platform_info.is_macos = False

        instructions = compat.get_ffmpeg_install_instructions()
        assert "ffmpeg.org" in instructions
        assert "Windows" in instructions
        assert "PATH" in instructions

    def test_get_ffmpeg_install_instructions_macos(self):
        """Test FFmpeg installation instructions for macOS."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = True

        instructions = compat.get_ffmpeg_install_instructions()
        assert "brew install ffmpeg" in instructions
        assert "macOS" in instructions

    def test_get_ffmpeg_install_instructions_linux(self):
        """Test FFmpeg installation instructions for Linux."""
        compat = PlatformCompatibility()
        compat._platform_info.is_windows = False
        compat._platform_info.is_macos = False

        instructions = compat.get_ffmpeg_install_instructions()
        assert "sudo apt install ffmpeg" in instructions
        assert "Linux" in instructions

    def test_get_memory_recommendations_mps(self):
        """Test memory recommendations for MPS systems."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = True
        compat._platform_info.supports_cuda = False

        recommendations = compat.get_memory_recommendations()

        assert recommendations["recommended_ram_gb"] == 16
        assert recommendations["model_cache_mb"] == 4096

    def test_get_memory_recommendations_cuda(self):
        """Test memory recommendations for CUDA systems."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = False
        compat._platform_info.supports_cuda = True

        recommendations = compat.get_memory_recommendations()

        assert "gpu_vram_gb" in recommendations
        assert recommendations["model_cache_mb"] == 1024

    def test_get_memory_recommendations_cpu(self):
        """Test memory recommendations for CPU-only systems."""
        compat = PlatformCompatibility()
        compat._platform_info.supports_mps = False
        compat._platform_info.supports_cuda = False

        recommendations = compat.get_memory_recommendations()

        assert recommendations["recommended_ram_gb"] == 16
        assert recommendations["model_cache_mb"] == 3072

    def test_validate_system_requirements_old_python(self):
        """Test system validation with old Python version."""
        compat = PlatformCompatibility()
        compat._platform_info.python_version = "3.11.0"
        compat._platform_info.ffmpeg_available = True

        with patch("importlib.import_module") as mock_import:
            # Mock successful imports
            mock_import.return_value = Mock()

            issues = compat.validate_system_requirements()

            # Should have Python version issue
            assert any("Python 3.13+" in issue for issue in issues)

    def test_validate_system_requirements_no_ffmpeg(self):
        """Test system validation without FFmpeg."""
        compat = PlatformCompatibility()
        compat._platform_info.python_version = "3.13.0"
        compat._platform_info.ffmpeg_available = False

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = Mock()

            issues = compat.validate_system_requirements()

            # Should have FFmpeg issue
            assert any("FFmpeg not found" in issue for issue in issues)

    def test_validate_system_requirements_missing_torch(self):
        """Test system validation without PyTorch."""
        compat = PlatformCompatibility()
        compat._platform_info.python_version = "3.13.0"
        compat._platform_info.ffmpeg_available = True

        # Mock import to raise ImportError for torch
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No module named 'torch'")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            issues = compat.validate_system_requirements()

            # Should have PyTorch issue
            assert any("PyTorch not installed" in issue for issue in issues)

    def test_get_temp_file_path(self):
        """Test temporary file path generation."""
        compat = PlatformCompatibility()

        with patch.object(compat, "get_temp_directory", return_value="/tmp"):
            temp_path = compat.get_temp_file_path("test_file.mp3")

            assert temp_path.startswith("/tmp/scribble_wise_")
            assert "test_file.mp3" in temp_path

    def test_get_temp_file_path_unsafe_chars(self):
        """Test temporary file path with unsafe characters."""
        compat = PlatformCompatibility()

        with patch.object(compat, "get_temp_directory", return_value="/tmp"):
            temp_path = compat.get_temp_file_path("file with spaces & symbols!.mp3")

            # Should sanitize unsafe characters (but "spaces" might be from original filename)
            # Check that dangerous chars are removed
            assert "&" not in temp_path
            assert "!" not in temp_path
            assert " " not in temp_path  # spaces should be removed

    @patch("pathlib.Path.mkdir")
    def test_setup_environment_success(self, mock_mkdir):
        """Test successful environment setup."""
        compat = PlatformCompatibility()

        with patch.object(compat, "ensure_directory_exists", return_value=True):
            result = compat.setup_environment()

            assert result is True

    @patch("pathlib.Path.mkdir")
    def test_setup_environment_failure(self, mock_mkdir):
        """Test environment setup failure."""
        compat = PlatformCompatibility()

        with patch.object(compat, "ensure_directory_exists", return_value=False):
            result = compat.setup_environment()

            assert result is False
