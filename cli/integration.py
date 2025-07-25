from dataclasses import dataclass
from pathlib import Path

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
