"""Tests for model configuration management."""

import pytest

from config.model_config import ModelConfig, ModelSettings, ModelType


class TestModelType:
    """Test ModelType enum."""

    def test_model_type_enum_values(self):
        """Test ModelType enum contains all expected values."""
        expected_types = [
            "LOCAL_BREEZE",
            "LOCAL_WHISPER_BASE",
            "LOCAL_WHISPER_SMALL",
            "LOCAL_WHISPER_MEDIUM",
            "LOCAL_WHISPER_LARGE",
            "OPENAI_API",
        ]

        actual_types = [model_type.value for model_type in ModelType]
        assert set(actual_types) == set(expected_types)

    def test_model_type_local_variants(self):
        """Test local model type identification."""
        local_types = [
            ModelType.LOCAL_BREEZE,
            ModelType.LOCAL_WHISPER_BASE,
            ModelType.LOCAL_WHISPER_SMALL,
            ModelType.LOCAL_WHISPER_MEDIUM,
            ModelType.LOCAL_WHISPER_LARGE,
        ]

        for model_type in local_types:
            assert model_type.value.startswith("LOCAL_")

    def test_model_type_api_variant(self):
        """Test API model type identification."""
        assert ModelType.OPENAI_API.value == "OPENAI_API"


class TestModelSettings:
    """Test ModelSettings dataclass."""

    def test_model_settings_creation(self):
        """Test ModelSettings creation with required fields."""
        settings = ModelSettings(
            model_type=ModelType.LOCAL_BREEZE,
            model_name="MediaTek-Research/Breeze-ASR-25",
            device="auto",
        )

        assert settings.model_type == ModelType.LOCAL_BREEZE
        assert settings.model_name == "MediaTek-Research/Breeze-ASR-25"
        assert settings.device == "auto"
        assert settings.chunk_length == 30  # default value
        assert settings.language == "auto"  # default value

    def test_model_settings_with_all_params(self):
        """Test ModelSettings with all parameters."""
        settings = ModelSettings(
            model_type=ModelType.LOCAL_WHISPER_SMALL,
            model_name="openai/whisper-small",
            device="mps",
            chunk_length=15,
            language="zh",
            temperature=0.2,
            beam_size=5,
        )

        assert settings.model_type == ModelType.LOCAL_WHISPER_SMALL
        assert settings.device == "mps"
        assert settings.chunk_length == 15
        assert settings.language == "zh"
        assert settings.temperature == 0.2
        assert settings.beam_size == 5


class TestModelConfig:
    """Test ModelConfig manager."""

    def test_model_config_creation(self):
        """Test ModelConfig creation with default settings."""
        config = ModelConfig()

        assert config.current_model == ModelType.LOCAL_BREEZE
        assert config.get_current_settings().model_type == ModelType.LOCAL_BREEZE

    def test_model_config_set_model(self):
        """Test setting model type in config."""
        config = ModelConfig()

        config.set_model(ModelType.LOCAL_WHISPER_SMALL)
        assert config.current_model == ModelType.LOCAL_WHISPER_SMALL
        assert config.get_current_settings().model_type == ModelType.LOCAL_WHISPER_SMALL

    def test_model_config_get_model_settings(self):
        """Test getting model settings for specific model type."""
        config = ModelConfig()

        breeze_settings = config.get_model_settings(ModelType.LOCAL_BREEZE)
        assert breeze_settings.model_name == "MediaTek-Research/Breeze-ASR-25"

        whisper_settings = config.get_model_settings(ModelType.LOCAL_WHISPER_SMALL)
        assert whisper_settings.model_name == "openai/whisper-small"

    def test_model_config_validate_openai_requires_api_key(self):
        """Test OpenAI model validation requires API key."""
        config = ModelConfig()

        with pytest.raises(ValueError, match="OpenAI API key required"):
            config.set_model(ModelType.OPENAI_API)
