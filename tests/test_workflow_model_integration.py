"""Tests for workflow model integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.model_config import ModelConfig, ModelType
from transcription.workflow import TranscriptionWorkflow


class TestWorkflowModelIntegration:
    """Test workflow integration with model configuration."""

    def test_workflow_has_model_config(self):
        """Test workflow has model configuration."""
        workflow = TranscriptionWorkflow()
        assert hasattr(workflow, "model_config")
        assert isinstance(workflow.model_config, ModelConfig)

    @pytest.mark.asyncio
    async def test_workflow_uses_configured_model(self):
        """Test workflow uses configured model for transcription."""
        workflow = TranscriptionWorkflow()

        # Set model to Whisper Base
        workflow.model_config.set_model(ModelType.LOCAL_WHISPER_BASE)

        # Mock the service loading and transcription
        mock_service = AsyncMock()
        mock_service.transcribe_async.return_value = MagicMock(
            success=True, transcription="Test transcription", error_message=None
        )

        with (
            patch.object(
                workflow, "_load_transcription_service", return_value=mock_service
            ) as mock_load,
            patch.object(workflow, "_unload_transcription_service") as mock_unload,
        ):
            result = await workflow._transcribe_audio("test.mp3")

            # Should load service, transcribe, and unload
            mock_load.assert_called_once()
            mock_service.transcribe_async.assert_called_once_with("test.mp3")
            mock_unload.assert_called_once()
            assert result == "Test transcription"

    @pytest.mark.asyncio
    async def test_workflow_service_lifecycle_management(self):
        """Test workflow manages service lifecycle properly."""
        workflow = TranscriptionWorkflow()

        # Mock the service loading and transcription
        mock_service = AsyncMock()
        mock_service.transcribe_async.return_value = MagicMock(
            success=True, transcription="Test transcription", error_message=None
        )

        # Directly test the lifecycle methods
        workflow._load_transcription_service = AsyncMock(return_value=mock_service)
        workflow._unload_transcription_service = AsyncMock()

        result = await workflow._transcribe_audio("test.mp3")

        # Should load and unload service
        workflow._load_transcription_service.assert_called_once()
        workflow._unload_transcription_service.assert_called_once()
        assert result == "Test transcription"

    def test_workflow_get_current_model_info(self):
        """Test workflow can provide current model information."""
        workflow = TranscriptionWorkflow()

        # Set specific model
        workflow.model_config.set_model(ModelType.LOCAL_WHISPER_SMALL)

        model_info = workflow.get_current_model_info()
        assert model_info is not None
        assert model_info["type"] == ModelType.LOCAL_WHISPER_SMALL
        assert "settings" in model_info

    @pytest.mark.asyncio
    async def test_workflow_with_openai_model_requires_api_key(self):
        """Test workflow fails gracefully when OpenAI model lacks API key."""
        workflow = TranscriptionWorkflow()

        # Mock no API key
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key required"):
                workflow.model_config.set_model(ModelType.OPENAI_API)
