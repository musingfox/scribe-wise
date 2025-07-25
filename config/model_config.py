"""Model configuration management for Scrible Wise."""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Model name constants
BREEZE_MODEL_NAME = "MediaTek-Research/Breeze-ASR-25"
WHISPER_BASE_MODEL_NAME = "openai/whisper-base"
WHISPER_SMALL_MODEL_NAME = "openai/whisper-small"
WHISPER_MEDIUM_MODEL_NAME = "openai/whisper-medium"
WHISPER_LARGE_MODEL_NAME = "openai/whisper-large"
OPENAI_API_MODEL_NAME = "whisper-1"

# Default configuration values
DEFAULT_CHUNK_LENGTH = 30
DEFAULT_DEVICE = "auto"
DEFAULT_LANGUAGE = "auto"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_BEAM_SIZE = 1


class ModelType(Enum):
    """Supported model types for transcription."""

    LOCAL_BREEZE = "LOCAL_BREEZE"
    LOCAL_WHISPER_BASE = "LOCAL_WHISPER_BASE"
    LOCAL_WHISPER_SMALL = "LOCAL_WHISPER_SMALL"
    LOCAL_WHISPER_MEDIUM = "LOCAL_WHISPER_MEDIUM"
    LOCAL_WHISPER_LARGE = "LOCAL_WHISPER_LARGE"
    OPENAI_API = "OPENAI_API"

    def is_local_model(self) -> bool:
        """Check if this is a local model type."""
        return self.value.startswith("LOCAL_")

    def is_api_model(self) -> bool:
        """Check if this is an API-based model type."""
        return self.value.endswith("_API")


@dataclass
class ModelSettings:
    """Configuration settings for a specific model."""

    model_type: ModelType
    model_name: str
    device: str = DEFAULT_DEVICE
    chunk_length: int = DEFAULT_CHUNK_LENGTH
    language: str = DEFAULT_LANGUAGE
    temperature: float = DEFAULT_TEMPERATURE
    beam_size: int = DEFAULT_BEAM_SIZE
    api_key_env: str = ""
    additional_params: dict[str, Any] = field(default_factory=dict)


class ModelConfig:
    """Model configuration manager."""

    def __init__(self):
        """Initialize model configuration with defaults."""
        self.current_model = ModelType.LOCAL_BREEZE
        self._model_settings = self._get_default_model_settings()

    def _get_default_model_settings(self) -> dict[ModelType, ModelSettings]:
        """Get default settings for all supported models."""
        return {
            ModelType.LOCAL_BREEZE: ModelSettings(
                model_type=ModelType.LOCAL_BREEZE, model_name=BREEZE_MODEL_NAME
            ),
            ModelType.LOCAL_WHISPER_BASE: ModelSettings(
                model_type=ModelType.LOCAL_WHISPER_BASE,
                model_name=WHISPER_BASE_MODEL_NAME,
            ),
            ModelType.LOCAL_WHISPER_SMALL: ModelSettings(
                model_type=ModelType.LOCAL_WHISPER_SMALL,
                model_name=WHISPER_SMALL_MODEL_NAME,
            ),
            ModelType.LOCAL_WHISPER_MEDIUM: ModelSettings(
                model_type=ModelType.LOCAL_WHISPER_MEDIUM,
                model_name=WHISPER_MEDIUM_MODEL_NAME,
            ),
            ModelType.LOCAL_WHISPER_LARGE: ModelSettings(
                model_type=ModelType.LOCAL_WHISPER_LARGE,
                model_name=WHISPER_LARGE_MODEL_NAME,
            ),
            ModelType.OPENAI_API: ModelSettings(
                model_type=ModelType.OPENAI_API,
                model_name=OPENAI_API_MODEL_NAME,
                device="api",
                api_key_env="OPENAI_API_KEY",
            ),
        }

    def set_model(self, model_type: ModelType) -> None:
        """Set current model type with validation."""
        if model_type == ModelType.OPENAI_API:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable."
                )

        self.current_model = model_type

    def get_current_settings(self) -> ModelSettings:
        """Get settings for currently selected model."""
        return self._model_settings[self.current_model]

    def get_model_settings(self, model_type: ModelType) -> ModelSettings:
        """Get settings for specific model type."""
        return self._model_settings[model_type]
