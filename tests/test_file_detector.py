import os
import tempfile

import pytest

from utils.file_detector import FileType, FileTypeDetector, UnsupportedFileError


class TestFileTypeDetector:
    def test_detect_file_type_returns_webm_for_webm_file(self):
        """Test that detector returns WEBM for .webm files"""
        detector = FileTypeDetector()

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file.write(b"dummy webm content")
            temp_path = temp_file.name

        try:
            result = detector.detect_file_type(temp_path)
            assert result == FileType.WEBM
        finally:
            os.unlink(temp_path)

    def test_detect_file_type_returns_mp3_for_mp3_file(self):
        """Test that detector returns MP3 for .mp3 files"""
        detector = FileTypeDetector()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"dummy mp3 content")
            temp_path = temp_file.name

        try:
            result = detector.detect_file_type(temp_path)
            assert result == FileType.MP3
        finally:
            os.unlink(temp_path)

    def test_detect_file_type_returns_mp4_for_mp4_file(self):
        """Test that detector returns MP4 for .mp4 files"""
        detector = FileTypeDetector()

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"dummy mp4 content")
            temp_path = temp_file.name

        try:
            result = detector.detect_file_type(temp_path)
            assert result == FileType.MP4
        finally:
            os.unlink(temp_path)

    def test_detect_file_type_raises_error_for_unsupported_file(self):
        """Test that detector raises error for unsupported file types"""
        detector = FileTypeDetector()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"dummy text content")
            temp_path = temp_file.name

        try:
            with pytest.raises(UnsupportedFileError):
                detector.detect_file_type(temp_path)
        finally:
            os.unlink(temp_path)

    def test_detect_file_type_raises_error_for_nonexistent_file(self):
        """Test that detector raises error for non-existent files"""
        detector = FileTypeDetector()

        with pytest.raises(FileNotFoundError):
            detector.detect_file_type("/nonexistent/file.webm")

    def test_detect_file_type_case_insensitive(self):
        """Test that detector handles case-insensitive file extensions"""
        detector = FileTypeDetector()

        with tempfile.NamedTemporaryFile(suffix=".WEBM", delete=False) as temp_file:
            temp_file.write(b"dummy webm content")
            temp_path = temp_file.name

        try:
            result = detector.detect_file_type(temp_path)
            assert result == FileType.WEBM
        finally:
            os.unlink(temp_path)

    def test_check_file_size_returns_true_for_small_file(self):
        """Test that file size check returns True for files under limit"""
        detector = FileTypeDetector(max_file_size_gb=1)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"small content")
            temp_path = temp_file.name

        try:
            result = detector.check_file_size(temp_path)
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_check_file_size_returns_false_for_large_file(self, mocker):
        """Test that file size check returns False for files over limit"""
        detector = FileTypeDetector(max_file_size_gb=1)

        # Mock os.path.getsize to return large size
        mock_getsize = mocker.patch("os.path.getsize")
        mock_getsize.return_value = 2 * 1024 * 1024 * 1024  # 2GB

        result = detector.check_file_size("/dummy/path")
        assert result is False

    def test_get_supported_extensions_returns_all_extensions(self):
        """Test that get_supported_extensions returns all supported extensions"""
        detector = FileTypeDetector()

        extensions = detector.get_supported_extensions()

        expected = {".webm", ".mp4", ".mkv", ".avi", ".mp3", ".wav", ".flac"}
        assert extensions == expected

    def test_is_video_format_returns_true_for_video_files(self):
        """Test that is_video_format returns True for video file types"""
        detector = FileTypeDetector()

        assert detector.is_video_format(FileType.WEBM) is True
        assert detector.is_video_format(FileType.MP4) is True
        assert detector.is_video_format(FileType.MKV) is True
        assert detector.is_video_format(FileType.AVI) is True

    def test_is_video_format_returns_false_for_audio_files(self):
        """Test that is_video_format returns False for audio file types"""
        detector = FileTypeDetector()

        assert detector.is_video_format(FileType.MP3) is False
        assert detector.is_video_format(FileType.WAV) is False
        assert detector.is_video_format(FileType.FLAC) is False
