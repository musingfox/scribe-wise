import asyncio
import sys
from argparse import ArgumentParser, Namespace

from cli.integration import CLIIntegration


def parse_args(args: list[str] | None = None) -> Namespace:
    """Parse command line arguments"""
    parser = ArgumentParser(
        prog="scrible-wise",
        description="Convert WebM videos and audio files to transcription",
        add_help=False,  # Disable default help to add custom help
    )

    parser.add_argument("input", nargs="?", help="Input file path")
    parser.add_argument("output", nargs="?", help="Output transcription file path")
    parser.add_argument("--help", action="store_true", help="Show help message")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--formats", action="store_true", help="Show supported formats")
    parser.add_argument(
        "--diagnostics", action="store_true", help="Show system diagnostics"
    )

    return parser.parse_args(args)


def print_help():
    """Print help message"""
    help_text = """
Scrible Wise - WebM Video to Audio Transcription Tool

Usage:
    python main.py <input_file> [output_file]
    python main.py [options]

Arguments:
    input_file      Input video or audio file (.webm, .mp4, .mp3, etc.)
    output_file     Output transcription file (optional, auto-generated if not provided)

Options:
    --help          Show this help message
    --version       Show version information
    --formats       Show supported input formats
    --diagnostics   Show system diagnostics and requirements

Examples:
    python main.py meeting.webm
    python main.py video.webm transcription.txt
    python main.py audio.mp3 output.txt

Features:
    - Convert WebM videos to MP3 audio
    - Direct transcription of audio files
    - Chinese speech recognition using Whisper models
    - Automatic chunking for long audio files
    - Cross-platform FFmpeg integration
"""
    print(help_text)


async def main() -> int:
    """Main CLI entry point"""
    try:
        args = parse_args()

        # Handle help flag
        if args.help or (not args.input and len(sys.argv) == 1):
            print_help()
            return 0 if args.help else 1

        # Initialize CLI integration
        cli = CLIIntegration()

        # Handle version flag
        if args.version:
            version = cli.get_version()
            print(f"Scrible Wise v{version}")
            return 0

        # Handle formats flag
        if args.formats:
            formats = cli.get_supported_formats()
            print("Supported input formats:")
            for fmt in sorted(formats):
                print(f"  .{fmt}")
            return 0

        # Handle diagnostics flag
        if args.diagnostics:
            diagnostics = cli.get_system_diagnostics()
            cli.print_system_diagnostics(diagnostics)
            return 0

        # Validate input file is provided
        if not args.input:
            print("Error: Input file is required", file=sys.stderr)
            print_help()
            return 1

        # Process file
        result = await cli.process_file(args.input, args.output)

        if result.success:
            print(f"✅ {result.message}")
            print(f"Input: {result.input_path}")
            print(f"Output: {result.output_path}")
            return 0
        else:
            print(f"❌ Error: {result.message}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
