from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
