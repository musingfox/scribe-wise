from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.model_config import ModelConfig, ModelType
from transcription.workflow import TranscriptionWorkflow


@dataclass
class CLIResult:
    """Result of CLI operation"""

    success: bool
    message: str
    input_path: str | None = None
    output_path: str | None = None


class CLIIntegration:
    """CLI integration layer for transcription workflow"""

    def __init__(self):
        """Initialize CLI integration with workflow"""
        self.workflow = TranscriptionWorkflow()
        self.model_config = ModelConfig()

    async def process_file(
        self, input_path: str, output_path: str | None = None
    ) -> CLIResult:
        """Process file through CLI interface"""
        # Validate input file exists
        if not Path(input_path).exists():
            return CLIResult(
                success=False,
                message=f"Input file not found: {input_path}",
                input_path=input_path,
            )

        # Generate output path if not provided
        if output_path is None:
            output_path = self.generate_output_path(input_path)

        # Process through workflow
        result = await self.workflow.process_file(input_path, output_path)

        if result.success:
            return CLIResult(
                success=True,
                message="Transcription completed successfully",
                input_path=input_path,
                output_path=output_path,
            )
        else:
            return CLIResult(
                success=False,
                message=result.error_message or "Transcription failed",
                input_path=input_path,
                output_path=output_path,
            )

    def generate_output_path(
        self, input_path: str, custom_output: str | None = None
    ) -> str:
        """Generate output path for transcription"""
        if custom_output:
            return custom_output

        # Auto-generate based on input path
        input_path_obj = Path(input_path)
        return str(input_path_obj.parent / f"{input_path_obj.stem}_transcription.txt")

    def get_version(self) -> str:
        """Get version information"""
        return "0.2.0"

    def get_supported_formats(self) -> list[str]:
        """Get supported input formats"""
        return self.workflow.get_supported_input_formats()

    def get_system_diagnostics(self) -> dict[str, Any]:
        """Get comprehensive system diagnostics"""
        return self.workflow.get_system_diagnostics()

    def print_system_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        """Print formatted system diagnostics"""
        print("🔍 Scrible Wise System Diagnostics")
        print("=" * 50)

        # Platform information
        platform = diagnostics["platform"]
        print("\n📊 Platform Information:")
        print(f"  System: {platform['system']} ({platform['architecture']})")
        print(f"  Python: {platform['python_version']}")

        # Hardware acceleration
        hw = diagnostics["hardware_acceleration"]
        print("\n⚡ Hardware Acceleration:")
        print(f"  Optimal Device: {hw['optimal_device']}")
        print(f"  MPS Support: {'✅' if hw['supports_mps'] else '❌'}")
        print(f"  CUDA Support: {'✅' if hw['supports_cuda'] else '❌'}")

        # Dependencies
        deps = diagnostics["dependencies"]
        print("\n📦 Dependencies:")
        print(
            f"  FFmpeg: {'✅ Available' if deps['ffmpeg_available'] else '❌ Not found'}"
        )
        if not deps["ffmpeg_available"] and deps["ffmpeg_install_instructions"]:
            print("\n📝 FFmpeg Installation:")
            for line in deps["ffmpeg_install_instructions"].split("\n"):
                if line.strip():
                    print(f"    {line}")

        # Memory recommendations
        memory = diagnostics["memory_recommendations"]
        print("\n💾 Memory Recommendations:")
        print(f"  Minimum RAM: {memory['min_ram_gb']}GB")
        print(f"  Recommended RAM: {memory['recommended_ram_gb']}GB")
        print(f"  Model Cache: {memory['model_cache_mb']}MB")
        if "gpu_vram_gb" in memory:
            print(f"  GPU VRAM: {memory['gpu_vram_gb']}GB")

        # Supported formats
        formats = diagnostics["supported_formats"]
        print(f"\n📁 Supported Formats ({len(formats)} total):")
        formatted_formats = ", ".join(f".{fmt}" for fmt in sorted(formats))
        print(f"  {formatted_formats}")

        # Directories
        dirs = diagnostics["directories"]
        print("\n📂 System Directories:")
        print(f"  Config: {dirs['config']}")
        print(f"  Cache: {dirs['cache']}")
        print(f"  Models: {dirs['models']}")

        # Validation issues
        issues = diagnostics["validation_issues"]
        if issues:
            print("\n⚠️  System Issues Found:")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print("\n✅ System Validation: All requirements met")

        print("\n" + "=" * 50)

    def get_available_models(self) -> list[dict[str, str]]:
        """Get list of available transcription models."""
        models = []
        for model_type in ModelType:
            settings = self.model_config.get_model_settings(model_type)
            model_info = {
                "id": model_type.value.lower(),
                "name": settings.model_name,
                "type": "local" if model_type.is_local_model() else "api",
                "description": self._get_model_description(model_type),
            }
            models.append(model_info)
        return models

    def get_model_info(self, model_id: str) -> dict[str, Any] | None:
        """Get detailed information about specific model."""
        model_type = self._model_id_to_type(model_id)
        if model_type is None:
            return None

        settings = self.model_config.get_model_settings(model_type)
        return {
            "id": model_id,
            "name": settings.model_name,
            "type": "local" if model_type.is_local_model() else "api",
            "description": self._get_model_description(model_type),
            "device": settings.device,
            "language": settings.language,
            "chunk_length": settings.chunk_length,
            "temperature": settings.temperature,
            "beam_size": settings.beam_size,
        }

    async def process_file_with_model(
        self,
        input_path: str,
        output_path: str | None = None,
        model_id: str | None = None,
    ) -> CLIResult:
        """Process file with specific model."""
        # Set model if specified
        if model_id:
            model_type = self._model_id_to_type(model_id)
            if model_type is None:
                return CLIResult(
                    success=False,
                    message=f"Unknown model: {model_id}",
                    input_path=input_path,
                )
            self.model_config.set_model(model_type)

        # Use existing process_file method
        return await self.process_file(input_path, output_path)

    def validate_model_id(self, model_id: str | None) -> bool:
        """Validate model ID."""
        if not model_id:
            return False
        return self._model_id_to_type(model_id) is not None

    def _model_id_to_type(self, model_id: str) -> ModelType | None:
        """Convert model ID string to ModelType enum."""
        model_id_upper = model_id.upper()
        for model_type in ModelType:
            if model_type.value == model_id_upper:
                return model_type
        return None

    def _get_model_description(self, model_type: ModelType) -> str:
        """Get human-readable description for model."""
        descriptions = {
            ModelType.LOCAL_BREEZE: "MediaTek Breeze ASR model for Chinese speech recognition",
            ModelType.LOCAL_WHISPER_BASE: "OpenAI Whisper Base model (local)",
            ModelType.LOCAL_WHISPER_SMALL: "OpenAI Whisper Small model (local)",
            ModelType.LOCAL_WHISPER_MEDIUM: "OpenAI Whisper Medium model (local)",
            ModelType.LOCAL_WHISPER_LARGE: "OpenAI Whisper Large model (local)",
            ModelType.OPENAI_API: "OpenAI Whisper API service (cloud)",
        }
        return descriptions.get(model_type, "Unknown model")
