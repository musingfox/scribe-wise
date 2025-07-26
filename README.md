# Scrible Wise

A comprehensive audio transcription tool powered by Whisper models that converts audio/video files into Chinese transcripts. Features include WebM video conversion, robust error handling, and an intuitive CLI interface.

## Features

### Core Features
- 🎵 **Multi-format Support**: WebM, MP4, MKV, AVI, MP3, WAV, FLAC, OGG, AAC, M4A
- 🧠 **Multi-Model AI**: Support for 6 different transcription models (local & cloud)
  - MediaTek Breeze-ASR-25 (默認中文模型)
  - OpenAI Whisper (Base/Small/Medium/Large 本地模型)
  - OpenAI Whisper API (雲端服務)
- ⚡ **Smart Processing**: Automatic chunking for long audio files (30-second segments)
- 🔧 **Error Recovery**: Comprehensive error handling with retry mechanisms and recovery suggestions
- 💻 **Cross-platform**: Apple Silicon (MPS), CPU support with automatic fallback
- 📝 **Complete Workflow**: Video → Audio → Transcription with validation at each step
- 💰 **Cost Control**: API usage tracking and cost estimation for cloud services

### Advanced CLI Interface
- 🚀 **Easy to Use**: Simple command-line interface with automatic output path generation
- ✅ **User-friendly**: Clear success/error messages with recovery suggestions
- 🔍 **Format Detection**: Automatic file type detection and processing
- 📊 **Progress Tracking**: Real-time processing feedback and status reporting
- 🎯 **Model Selection**: Choose from 6 different AI models with `--model` parameter
- 📋 **Model Management**: List models (`--list-models`) and view details (`--model-info`)

## System Requirements

- Python 3.13+
- FFmpeg (for video to audio conversion)
- macOS (Apple Silicon recommended for better performance)
- Sufficient memory to load Whisper models

## Installation

### Install FFmpeg
First, install FFmpeg for video conversion:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

### Install Python Dependencies
Install dependencies using `uv`:

```bash
uv sync
```

For development with linting tools:

```bash
uv sync --extra dev
```

## Quick Start

### 🚀 Simple Usage (Recommended)
The advanced CLI interface makes transcription incredibly easy:

```bash
# Basic transcription - automatic output file generation
uv run python -m cli.main input.webm

# Custom output file
uv run python -m cli.main input.webm my_transcription.txt

# Works with any supported format
uv run python -m cli.main meeting.mp3
uv run python -m cli.main video.mp4
uv run python -m cli.main audio.wav
```

### 🎯 Model Selection
Choose from 6 different AI models for optimal results:

```bash
# Use specific model
uv run python -m cli.main audio.mp3 --model local_whisper_base

# List all available models
uv run python -m cli.main --list-models

# Get detailed model information
uv run python -m cli.main --model-info local_breeze

# Use OpenAI API (requires OPENAI_API_KEY environment variable)
export OPENAI_API_KEY="your-api-key"
uv run python -m cli.main audio.mp3 --model openai_api
```

### 📋 Available Models

| Model ID | Type | Description | Best For |
|----------|------|-------------|----------|
| `local_breeze` | 本地 | MediaTek Breeze-ASR-25 | 中文語音識別 (默認) |
| `local_whisper_base` | 本地 | OpenAI Whisper Base | 輕量級多語言轉錄 |
| `local_whisper_small` | 本地 | OpenAI Whisper Small | 平衡性能與準確度 |
| `local_whisper_medium` | 本地 | OpenAI Whisper Medium | 高品質轉錄 |
| `local_whisper_large` | 本地 | OpenAI Whisper Large | 最高準確度 |
| `openai_api` | 雲端 | OpenAI Whisper API | 免安裝，按使用付費 |

### 📋 CLI Options
```bash
# Show help and all available options
uv run python -m cli.main --help

# Show version information
uv run python -m cli.main --version

# Show supported input formats
uv run python -m cli.main --formats

# Show system diagnostics
uv run python -m cli.main --diagnostics

# Model management commands
uv run python -m cli.main --list-models              # List all models
uv run python -m cli.main --model-info <model_id>    # Model details
```

### 🔄 Legacy Usage (Still Supported)
For backward compatibility, the original interface works with MP3 files:

```bash
# Place your audio file as 'meeting.mp3' in the project root
uv run python main.py
```

### 💡 Example Output
```bash
$ uv run python -m cli.main presentation.webm --model local_whisper_base

✅ Transcription completed successfully
Input: presentation.webm
Output: presentation_transcription.txt
Model: OpenAI Whisper Base (local)
```

## Development

### Code Quality Tools

The project includes several linting and formatting tools:

```bash
# Run linter
uv run ruff check main.py

# Auto-fix linting issues
uv run ruff check --fix main.py

# Format code
uv run black main.py

# Sort imports
uv run isort main.py

# Type checking
uv run mypy main.py
```

### Pre-commit Hooks

Pre-commit hooks automatically run linting and formatting before each commit:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files

# Run hooks on specific files
uv run pre-commit run --files main.py
```

The hooks will automatically:
- Remove trailing whitespace
- Fix end-of-file issues
- Check YAML syntax
- Run Ruff linter with auto-fix
- Format code with Ruff formatter
- Format code with Black
- Sort imports with isort

3. The program will:
   - Automatically detect audio file duration
   - Process long audio files in segments
   - Display processing progress
   - Save complete transcription results to `transcription.txt`

## Program Flow

1. **Load Audio**: Supports MP3 format, automatically converts sample rate to 16kHz
2. **Audio Preprocessing**: Mono conversion and normalization
3. **Model Loading**: Uses MediaTek Breeze-ASR-25 Whisper model
4. **Segmented Processing**: Splits long audio into 30-second chunks for processing
5. **Transcription Merging**: Combines all segment results into complete transcript
6. **Result Output**: Saves to text file

## Technical Architecture

- **Audio Processing**: `torchaudio` + `soundfile`
- **Video Conversion**: FFmpeg via `ffmpeg-python`
- **Speech Recognition**: Multi-model support (Hugging Face Transformers + OpenAI API)
- **Hardware Acceleration**: Apple MPS (Metal Performance Shaders)
- **Package Management**: `uv`
- **Testing**: pytest with asyncio support (115+ test cases)
- **Code Quality**: ruff, black, isort, mypy
- **Model Management**: Dynamic model loading/unloading with service abstraction

### Module Structure

```
scrible-wise/
├── main.py                         # Legacy transcription program
├── cli/                            # New CLI interface
│   ├── main.py                     # Main CLI entry point
│   └── integration.py              # CLI integration layer
├── transcription/                  # Core transcription workflow
│   └── workflow.py                 # Complete processing workflow
├── converters/                     # Media conversion modules
│   └── media_converter.py          # WebM to MP3 converter
├── validators/                     # Audio validation modules
│   └── audio_validator.py          # Audio file validator
├── utils/                          # Utility modules
│   ├── ffmpeg_checker.py           # FFmpeg dependency checker
│   ├── file_detector.py            # File type detection
│   └── error_recovery.py           # Error handling and retry logic
├── config/                         # Configuration management
│   └── model_config.py             # Model configuration and management
├── services/                       # Transcription service abstraction
│   ├── base.py                     # Base transcription service interface
│   ├── local_breeze.py             # MediaTek Breeze service
│   ├── local_whisper.py            # Local Whisper service
│   └── openai_service.py           # OpenAI API service
├── exceptions/                     # Custom exception hierarchy
│   ├── base.py                     # Base exception classes
│   ├── conversion.py               # Conversion-related exceptions
│   ├── validation.py               # Validation-related exceptions
│   └── transcription.py            # Transcription-related exceptions
└── tests/                          # Comprehensive test suites (115+ tests)
    ├── test_*.py                   # Unit tests for all modules
    └── test_workflow_error_integration.py  # Integration tests
```

## Error Handling & Recovery

Scrible Wise includes comprehensive error handling with automatic recovery suggestions:

```bash
$ uv run python -m cli.main broken_video.webm

❌ Error: FFmpeg not found. FFmpeg is required for media conversion.
Install it using: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Ubuntu/Debian)
```

The system automatically:
- ✅ **Detects Issues**: Identifies missing dependencies, corrupted files, and format problems
- 🔄 **Retries Operations**: Automatic retry with exponential backoff for temporary failures
- 💡 **Provides Solutions**: Clear recovery suggestions for common problems
- 🧹 **Cleans Up**: Automatic cleanup of temporary files on errors

## Notes

- First run will download Whisper model, internet connection required
- Processing time depends on audio length and hardware performance
- Recommended to run on Apple Silicon Mac for optimal performance
- Supports Chinese speech recognition, limited effectiveness for other languages

## Testing

The project includes comprehensive test coverage with 115+ test cases covering all modules:

```bash
# Run all tests
uv run pytest -v

# Run specific test module
uv run pytest tests/test_workflow_error_integration.py -v

# Test specific model integration
uv run pytest tests/test_workflow_model_integration.py -v

# Test CLI model selection
uv run pytest tests/test_cli_model_selection.py -v

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `FFmpeg not found` | Install FFmpeg: `brew install ffmpeg` (macOS) |
| `Audio loading failed` | Install audio libraries: `uv add soundfile librosa` |
| `CUDA errors` | Program auto-switches to MPS/CPU - no action needed |
| `Model download fails` | Check internet connection, model downloads on first run |
| `Memory errors` | Try shorter audio files or use lighter models (base/small) |
| `OpenAI API errors` | Set `OPENAI_API_KEY` environment variable |
| `Unknown model` | Use `--list-models` to see available models |

### Getting Help

1. Check the error message for recovery suggestions
2. Verify FFmpeg installation: `ffmpeg -version`
3. Test with a smaller audio file
4. Check available disk space (models need ~2GB)
