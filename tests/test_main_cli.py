import sys
from io import StringIO
from unittest.mock import AsyncMock, Mock, patch

import pytest

from cli.main import main


class TestMainCLI:
    @pytest.mark.asyncio
    async def test_main_webm_to_transcription_success(self, mocker):
        """Test main function with WebM file"""
        # Mock CLI integration
        mock_cli = Mock()
        mock_process = AsyncMock()
        mock_cli.process_file = mock_process

        from cli.integration import CLIResult

        mock_process.return_value = CLIResult(
            success=True,
            message="Transcription completed successfully",
            input_path="test.webm",
            output_path="test_transcription.txt",
        )

        mock_cli_class = mocker.patch("cli.main.CLIIntegration")
        mock_cli_class.return_value = mock_cli

        # Mock sys.argv
        test_argv = ["main.py", "test.webm"]
        with patch.object(sys, "argv", test_argv):
            result = await main()

        assert result == 0
        mock_process.assert_called_once_with("test.webm", None)

    @pytest.mark.asyncio
    async def test_main_with_output_path(self, mocker):
        """Test main function with custom output path"""
        # Mock CLI integration
        mock_cli = Mock()
        mock_process = AsyncMock()
        mock_cli.process_file = mock_process

        from cli.integration import CLIResult

        mock_process.return_value = CLIResult(
            success=True,
            message="Transcription completed successfully",
            input_path="test.webm",
            output_path="custom_output.txt",
        )

        mock_cli_class = mocker.patch("cli.main.CLIIntegration")
        mock_cli_class.return_value = mock_cli

        # Mock sys.argv
        test_argv = ["main.py", "test.webm", "custom_output.txt"]
        with patch.object(sys, "argv", test_argv):
            result = await main()

        assert result == 0
        mock_process.assert_called_once_with("test.webm", "custom_output.txt")

    @pytest.mark.asyncio
    async def test_main_processing_failure(self, mocker):
        """Test main function with processing failure"""
        # Mock CLI integration
        mock_cli = Mock()
        mock_process = AsyncMock()
        mock_cli.process_file = mock_process

        from cli.integration import CLIResult

        mock_process.return_value = CLIResult(
            success=False,
            message="FFmpeg not found",
            input_path="test.webm",
        )

        mock_cli_class = mocker.patch("cli.main.CLIIntegration")
        mock_cli_class.return_value = mock_cli

        # Mock sys.argv and capture stderr
        test_argv = ["main.py", "test.webm"]
        captured_stderr = StringIO()

        with (
            patch.object(sys, "argv", test_argv),
            patch.object(sys, "stderr", captured_stderr),
        ):
            result = await main()

        assert result == 1
        assert "FFmpeg not found" in captured_stderr.getvalue()

    @pytest.mark.asyncio
    async def test_main_no_arguments(self):
        """Test main function with no arguments"""
        # Mock sys.argv with only script name
        test_argv = ["main.py"]
        captured_stdout = StringIO()

        with (
            patch.object(sys, "argv", test_argv),
            patch.object(sys, "stdout", captured_stdout),
        ):
            result = await main()

        assert result == 1
        assert "Usage:" in captured_stdout.getvalue()

    @pytest.mark.asyncio
    async def test_main_help_flag(self):
        """Test main function with help flag"""
        # Mock sys.argv with help flag
        test_argv = ["main.py", "--help"]
        captured_stdout = StringIO()

        with (
            patch.object(sys, "argv", test_argv),
            patch.object(sys, "stdout", captured_stdout),
        ):
            result = await main()

        assert result == 0
        assert "Usage:" in captured_stdout.getvalue()
        assert "Scrible Wise" in captured_stdout.getvalue()

    @pytest.mark.asyncio
    async def test_main_version_flag(self, mocker):
        """Test main function with version flag"""
        # Mock CLI integration for version
        mock_cli = Mock()
        mock_cli.get_version.return_value = "0.2.0"

        mock_cli_class = mocker.patch("cli.main.CLIIntegration")
        mock_cli_class.return_value = mock_cli

        # Mock sys.argv with version flag
        test_argv = ["main.py", "--version"]
        captured_stdout = StringIO()

        with (
            patch.object(sys, "argv", test_argv),
            patch.object(sys, "stdout", captured_stdout),
        ):
            result = await main()

        assert result == 0
        assert "0.2.0" in captured_stdout.getvalue()

    @pytest.mark.asyncio
    async def test_main_formats_flag(self, mocker):
        """Test main function with supported formats flag"""
        # Mock CLI integration for formats
        mock_cli = Mock()
        mock_cli.get_supported_formats.return_value = ["webm", "mp4", "mp3"]

        mock_cli_class = mocker.patch("cli.main.CLIIntegration")
        mock_cli_class.return_value = mock_cli

        # Mock sys.argv with formats flag
        test_argv = ["main.py", "--formats"]
        captured_stdout = StringIO()

        with (
            patch.object(sys, "argv", test_argv),
            patch.object(sys, "stdout", captured_stdout),
        ):
            result = await main()

        assert result == 0
        output = captured_stdout.getvalue()
        assert "webm" in output
        assert "mp4" in output
        assert "mp3" in output

    def test_parse_args_basic(self):
        """Test argument parsing with basic input"""
        from cli.main import parse_args

        args = parse_args(["test.webm"])

        assert args.input == "test.webm"
        assert args.output is None
        assert args.help is False
        assert args.version is False

    def test_parse_args_with_output(self):
        """Test argument parsing with output path"""
        from cli.main import parse_args

        args = parse_args(["test.webm", "output.txt"])

        assert args.input == "test.webm"
        assert args.output == "output.txt"

    def test_parse_args_flags(self):
        """Test argument parsing with flags"""
        from cli.main import parse_args

        args = parse_args(["--help"])
        assert args.help is True

        args = parse_args(["--version"])
        assert args.version is True

        args = parse_args(["--formats"])
        assert args.formats is True
