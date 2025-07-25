import os
import tempfile
from unittest.mock import AsyncMock, Mock

import pytest

from converters.media_converter import (
    ConversionError,
    ConversionResult,
    MediaConverter,
    QualityLevel,
)


class TestMediaConverter:
    def test_init_creates_converter_with_default_quality(self):
        """Test that MediaConverter initializes with default medium quality"""
        converter = MediaConverter()
        assert converter.quality == QualityLevel.MEDIUM

    def test_init_creates_converter_with_custom_quality(self):
        """Test that MediaConverter initializes with custom quality"""
        converter = MediaConverter(quality=QualityLevel.HIGH)
        assert converter.quality == QualityLevel.HIGH

    @pytest.mark.asyncio
    async def test_convert_webm_to_mp3_success(self, mocker):
        """Test successful WebM to MP3 conversion"""
        converter = MediaConverter()

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(b"dummy webm content")
            input_path = input_file.name

        output_path = input_path.replace(".webm", ".mp3")

        try:
            # Mock FFmpeg process
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"", b"")

            mock_create_subprocess = mocker.patch("asyncio.create_subprocess_exec")
            mock_create_subprocess.return_value = mock_process

            # Mock Path.exists to simulate output file creation
            mock_exists = mocker.patch("pathlib.Path.exists")
            mock_exists.return_value = True

            result = await converter.convert_webm_to_mp3(input_path, output_path)

            assert isinstance(result, ConversionResult)
            assert result.success is True
            assert result.input_path == input_path
            assert result.output_path == output_path
            assert result.error_message is None

            # Verify FFmpeg command was called correctly
            mock_create_subprocess.assert_called_once()
            args = mock_create_subprocess.call_args[0]
            assert args[0] == "ffmpeg"
            assert "-i" in args
            assert input_path in args
            assert output_path in args

        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_convert_webm_to_mp3_ffmpeg_failure(self, mocker):
        """Test WebM to MP3 conversion when FFmpeg fails"""
        converter = MediaConverter()

        # Create temp input file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(b"dummy webm content")
            input_path = input_file.name

        output_path = input_path.replace(".webm", ".mp3")

        try:
            # Mock FFmpeg process failure
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"conversion failed")

            mock_create_subprocess = mocker.patch("asyncio.create_subprocess_exec")
            mock_create_subprocess.return_value = mock_process

            result = await converter.convert_webm_to_mp3(input_path, output_path)

            assert isinstance(result, ConversionResult)
            assert result.success is False
            assert "conversion failed" in result.error_message

        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_convert_webm_to_mp3_input_not_found(self):
        """Test conversion with non-existent input file"""
        converter = MediaConverter()

        with pytest.raises(ConversionError, match="Input file not found"):
            await converter.convert_webm_to_mp3(
                "/nonexistent/input.webm", "/tmp/output.mp3"
            )

    def test_get_ffmpeg_command_medium_quality(self):
        """Test FFmpeg command generation for medium quality"""
        converter = MediaConverter(quality=QualityLevel.MEDIUM)

        command = converter._get_ffmpeg_command("/input.webm", "/output.mp3")

        expected_command = [
            "ffmpeg",
            "-i",
            "/input.webm",
            "-vn",  # No video
            "-acodec",
            "libmp3lame",
            "-ac",
            "2",  # Stereo
            "-ab",
            "160k",  # Medium quality bitrate
            "-ar",
            "16000",  # 16kHz sample rate
            "/output.mp3",
        ]

        assert command == expected_command

    def test_get_ffmpeg_command_high_quality(self):
        """Test FFmpeg command generation for high quality"""
        converter = MediaConverter(quality=QualityLevel.HIGH)

        command = converter._get_ffmpeg_command("/input.webm", "/output.mp3")

        expected_command = [
            "ffmpeg",
            "-i",
            "/input.webm",
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ac",
            "2",
            "-ab",
            "256k",  # High quality bitrate
            "-ar",
            "16000",
            "/output.mp3",
        ]

        assert command == expected_command

    def test_get_ffmpeg_command_low_quality(self):
        """Test FFmpeg command generation for low quality"""
        converter = MediaConverter(quality=QualityLevel.LOW)

        command = converter._get_ffmpeg_command("/input.webm", "/output.mp3")

        expected_command = [
            "ffmpeg",
            "-i",
            "/input.webm",
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ac",
            "2",
            "-ab",
            "128k",  # Low quality bitrate
            "-ar",
            "16000",
            "/output.mp3",
        ]

        assert command == expected_command

    @pytest.mark.asyncio
    async def test_convert_with_timeout(self, mocker):
        """Test conversion with timeout handling"""
        converter = MediaConverter(timeout_minutes=1)

        # Create temp input file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(b"dummy webm content")
            input_path = input_file.name

        output_path = input_path.replace(".webm", ".mp3")

        try:
            # Mock asyncio.wait_for to raise TimeoutError
            mock_wait_for = mocker.patch("asyncio.wait_for")
            mock_wait_for.side_effect = TimeoutError()

            result = await converter.convert_webm_to_mp3(input_path, output_path)

            assert result.success is False
            assert "timeout" in result.error_message.lower()

        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cleanup_temp_files(self, mocker):
        """Test temporary file cleanup functionality"""
        converter = MediaConverter()

        # Mock Path constructor and instances
        mock_path_class = mocker.patch("converters.media_converter.Path")
        mock_instance1 = Mock()
        mock_instance2 = Mock()
        mock_instance1.exists.return_value = True
        mock_instance2.exists.return_value = True

        # Configure side_effect to return different instances for each call
        mock_path_class.side_effect = [mock_instance1, mock_instance2]

        converter._cleanup_temp_files(["/temp/file1.tmp", "/temp/file2.tmp"])

        # Verify unlink was called for each temp file
        mock_instance1.unlink.assert_called_once()
        mock_instance2.unlink.assert_called_once()
