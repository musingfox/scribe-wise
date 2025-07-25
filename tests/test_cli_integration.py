import pytest

from cli.integration import (
    CLIIntegration,
    CLIResult,
)


class TestCLIIntegration:
    def test_init_creates_cli_with_defaults(self):
        """Test that CLIIntegration initializes with default settings"""
        cli = CLIIntegration()
        assert cli is not None
        assert hasattr(cli, "workflow")

    @pytest.mark.asyncio
    async def test_process_webm_to_transcription_success(self, mocker):
        """Test successful WebM to transcription via CLI"""
        cli = CLIIntegration()

        # Mock Path.exists for input file
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        # Mock workflow process_file
        mock_process = mocker.patch.object(cli.workflow, "process_file")

        from transcription.workflow import TranscriptionResult

        mock_process.return_value = TranscriptionResult(
            success=True,
            input_path="/test/input.webm",
            output_path="/test/output.txt",
            transcription="Test transcription result",
            duration_seconds=60.0,
        )

        result = await cli.process_file("/test/input.webm", "/test/output.txt")

        assert isinstance(result, CLIResult)
        assert result.success is True
        assert result.message == "Transcription completed successfully"
        assert result.input_path == "/test/input.webm"
        assert result.output_path == "/test/output.txt"

        # Verify workflow was called
        mock_process.assert_called_once_with("/test/input.webm", "/test/output.txt")

    @pytest.mark.asyncio
    async def test_process_file_workflow_failure(self, mocker):
        """Test handling of workflow failure"""
        cli = CLIIntegration()

        # Mock Path.exists for input file
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        # Mock workflow process_file to return failure
        mock_process = mocker.patch.object(cli.workflow, "process_file")

        from transcription.workflow import TranscriptionResult

        mock_process.return_value = TranscriptionResult(
            success=False,
            input_path="/test/input.webm",
            output_path="/test/output.txt",
            error_message="FFmpeg not found",
        )

        result = await cli.process_file("/test/input.webm", "/test/output.txt")

        assert result.success is False
        assert "FFmpeg not found" in result.message

    def test_get_version(self):
        """Test version information retrieval"""
        cli = CLIIntegration()
        version = cli.get_version()

        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_supported_formats(self):
        """Test supported formats retrieval"""
        cli = CLIIntegration()
        formats = cli.get_supported_formats()

        assert isinstance(formats, list)
        assert "webm" in formats
        assert "mp3" in formats

    @pytest.mark.asyncio
    async def test_validate_input_file_exists(self, mocker):
        """Test input file validation when file exists"""
        cli = CLIIntegration()

        # Mock Path.exists
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        # Mock workflow process_file
        mock_process = mocker.patch.object(cli.workflow, "process_file")
        from transcription.workflow import TranscriptionResult

        mock_process.return_value = TranscriptionResult(
            success=True,
            input_path="/test/input.webm",
            output_path="/test/output.txt",
            transcription="Test result",
        )

        result = await cli.process_file("/test/input.webm", "/test/output.txt")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_validate_input_file_not_exists(self):
        """Test input file validation when file doesn't exist"""
        cli = CLIIntegration()

        result = await cli.process_file("/nonexistent/file.webm", "/test/output.txt")

        assert result.success is False
        assert "Input file not found" in result.message

    def test_generate_output_path_auto(self):
        """Test automatic output path generation"""
        cli = CLIIntegration()

        output_path = cli.generate_output_path("/test/input.webm")

        assert output_path == "/test/input_transcription.txt"

    def test_generate_output_path_custom(self):
        """Test custom output path handling"""
        cli = CLIIntegration()

        output_path = cli.generate_output_path(
            "/test/input.webm", custom_output="/custom/output.txt"
        )

        assert output_path == "/custom/output.txt"

    @pytest.mark.asyncio
    async def test_process_with_auto_output_path(self, mocker):
        """Test processing with automatically generated output path"""
        cli = CLIIntegration()

        # Mock Path.exists for input file
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = True

        # Mock workflow process_file
        mock_process = mocker.patch.object(cli.workflow, "process_file")
        from transcription.workflow import TranscriptionResult

        mock_process.return_value = TranscriptionResult(
            success=True,
            input_path="/test/input.webm",
            output_path="/test/input_transcription.txt",
            transcription="Test result",
        )

        result = await cli.process_file("/test/input.webm")

        assert result.success is True
        assert result.output_path == "/test/input_transcription.txt"

        # Verify workflow was called with auto-generated path
        mock_process.assert_called_once_with(
            "/test/input.webm", "/test/input_transcription.txt"
        )
