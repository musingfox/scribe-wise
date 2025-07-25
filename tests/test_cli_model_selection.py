"""Tests for CLI model selection functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.integration import CLIIntegration
from cli.main import parse_args


class TestCLIModelSelection:
    """Test CLI model selection functionality."""

    def test_parse_args_model_parameter(self):
        """Test parsing --model parameter."""
        args = parse_args(["input.mp3", "--model", "local_whisper_base"])
        assert args.model == "local_whisper_base"

    def test_parse_args_list_models_flag(self):
        """Test parsing --list-models flag."""
        args = parse_args(["--list-models"])
        assert args.list_models is True

    def test_parse_args_model_info_parameter(self):
        """Test parsing --model-info parameter."""
        args = parse_args(["--model-info", "local_breeze"])
        assert args.model_info == "local_breeze"

    def test_parse_args_default_model_none(self):
        """Test default model parameter is None."""
        args = parse_args(["input.mp3"])
        assert not hasattr(args, "model") or args.model is None

    @pytest.mark.asyncio
    async def test_cli_integration_get_available_models(self):
        """Test getting available models from CLI integration."""
        cli = CLIIntegration()
        models = cli.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(model, dict) for model in models)

        # Check first model has required fields
        first_model = models[0]
        assert "id" in first_model
        assert "name" in first_model
        assert "type" in first_model

    @pytest.mark.asyncio
    async def test_cli_integration_get_model_info(self):
        """Test getting specific model information."""
        cli = CLIIntegration()

        # Test valid model
        info = cli.get_model_info("local_breeze")
        assert info is not None
        assert "id" in info
        assert "name" in info
        assert "description" in info

        # Test invalid model
        info = cli.get_model_info("invalid_model")
        assert info is None

    @pytest.mark.asyncio
    async def test_cli_integration_process_file_with_model(self):
        """Test processing file with specific model."""
        with patch("pathlib.Path.exists", return_value=True):
            cli = CLIIntegration()

            # Mock workflow.process_file instead
            cli.workflow.process_file = AsyncMock()
            cli.workflow.process_file.return_value = MagicMock(
                success=True, error_message=None
            )

            result = await cli.process_file_with_model(
                "test.mp3", model_id="local_whisper_base"
            )

            assert result.success is True
            cli.workflow.process_file.assert_called_once()

    def test_cli_integration_validate_model_id(self):
        """Test model ID validation."""
        cli = CLIIntegration()

        # Valid model IDs
        assert cli.validate_model_id("local_breeze") is True
        assert cli.validate_model_id("local_whisper_base") is True
        assert cli.validate_model_id("openai_api") is True

        # Invalid model ID
        assert cli.validate_model_id("invalid_model") is False
        assert cli.validate_model_id("") is False
        assert cli.validate_model_id(None) is False
