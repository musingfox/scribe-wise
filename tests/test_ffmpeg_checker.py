from unittest.mock import Mock

import pytest

from utils.ffmpeg_checker import FFmpegChecker, FFmpegNotFoundError


class TestFFmpegChecker:
    def test_check_ffmpeg_installation_returns_true_when_ffmpeg_available(self, mocker):
        """Test that FFmpeg checker returns True when FFmpeg is available"""
        # Mock successful subprocess call
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            returncode=0, stdout="ffmpeg version 4.4.2", stderr=""
        )

        checker = FFmpegChecker()
        result = checker.check_ffmpeg_installation()

        assert result is True
        mock_run.assert_called_once_with(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_ffmpeg_installation_returns_false_when_ffmpeg_not_found(
        self, mocker
    ):
        """Test that FFmpeg checker returns False when FFmpeg is not found"""
        # Mock FileNotFoundError (command not found)
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        checker = FFmpegChecker()
        result = checker.check_ffmpeg_installation()

        assert result is False

    def test_check_ffmpeg_installation_returns_false_when_ffmpeg_fails(self, mocker):
        """Test that FFmpeg checker returns False when FFmpeg command fails"""
        # Mock failed subprocess call
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="command failed")

        checker = FFmpegChecker()
        result = checker.check_ffmpeg_installation()

        assert result is False

    def test_get_ffmpeg_version_returns_version_string(self, mocker):
        """Test that get_ffmpeg_version returns version string when available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            returncode=0,
            stdout="ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021",
            stderr="",
        )

        checker = FFmpegChecker()
        version = checker.get_ffmpeg_version()

        assert version == "4.4.2"

    def test_get_ffmpeg_version_raises_error_when_not_available(self, mocker):
        """Test that get_ffmpeg_version raises error when FFmpeg not available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        checker = FFmpegChecker()

        with pytest.raises(FFmpegNotFoundError):
            checker.get_ffmpeg_version()

    def test_ensure_ffmpeg_available_passes_when_ffmpeg_available(self, mocker):
        """Test that ensure_ffmpeg_available passes when FFmpeg is available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(
            returncode=0, stdout="ffmpeg version 4.4.2", stderr=""
        )

        checker = FFmpegChecker()
        # Should not raise exception
        checker.ensure_ffmpeg_available()

    def test_ensure_ffmpeg_available_raises_error_when_not_available(self, mocker):
        """Test that ensure_ffmpeg_available raises error when FFmpeg not available"""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        checker = FFmpegChecker()

        with pytest.raises(FFmpegNotFoundError):
            checker.ensure_ffmpeg_available()
