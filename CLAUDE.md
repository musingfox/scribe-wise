# Claude Code Project Configuration

## Project Information

- **Project Name**: Scrible Wise
- **Project Type**: Audio transcription tool with WebM video conversion
- **Primary Language**: Python
- **Package Manager**: uv

## Development Environment

### Python Environment
- **Version**: Python 3.13+
- **Package Management Tool**: `uv` (preferred)
- **Virtual Environment**: Managed by `uv`

### Main Dependencies
- `torch>=2.7.1`
- `torchaudio>=2.7.1`
- `transformers>=4.53.3`
- `soundfile>=0.12.1`
- `librosa>=0.10.0`
- `ffmpeg-python>=0.2.0` - FFmpeg integration for video conversion
- `numpy`

### Development Dependencies
- `ruff>=0.8.0` - Fast Python linter
- `black>=24.0.0` - Code formatter
- `isort>=5.13.0` - Import sorter
- `mypy>=1.13.0` - Type checker
- `pytest>=8.0.0` - Testing framework
- `pytest-mock>=3.12.0` - Mock support for pytest
- `pytest-asyncio>=0.25.0` - Async test support
- `pre-commit>=4.0.0` - Pre-commit hooks

### Hardware Support
- **Recommended**: Apple Silicon (MPS)
- **Fallback**: CPU
- **Not Supported**: CUDA (auto-switching configured)

### External Dependencies
- **FFmpeg**: Required for WebM to MP3 conversion
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: Download from [https://ffmpeg.org](https://ffmpeg.org)

## Task Management System

### Current Setup
- **System**: Local TodoWrite tool
- **Status Tracking**: Using Claude Code built-in todo functionality
- **Task Sync**: No external integration needed

## Development Workflow

### Common Commands
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev

# Run main program
uv run python main.py

# Check Python version
uv run python --version

# Add new dependencies
uv add <package_name>
```

### Code Quality Commands
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

### Pre-commit Setup
```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files

# Run hooks on specific files
uv run pre-commit run --files main.py
```

### Testing Process
- **Testing Framework**: pytest with asyncio and mocking support
- **Test Coverage**: 39 test cases covering all modules
- **Test Execution**: `uv run pytest -v`
- **Manual Testing**: Use `meeting.mp3` for transcription testing
- **Output Validation**: Check `transcription.txt` completeness

### Code Quality
- **Style**: Clean, self-documenting code
- **Comments**: English comments, minimal but meaningful
- **Naming**: Consistent formatting and naming conventions
- **Linting**: Ruff for fast Python linting
- **Formatting**: Black for consistent code formatting
- **Import Sorting**: isort with Black profile
- **Type Checking**: MyPy for static type analysis (optional)
- **Pre-commit Hooks**: Automatic code quality checks before commits

## Project Structure

```
scrible-wise/
├── main.py                    # Main transcription program
├── meeting.mp3               # Test audio file
├── transcription.txt         # Output results
├── converters/               # Media conversion modules
│   ├── __init__.py
│   └── media_converter.py    # WebM to MP3 converter
├── validators/               # Audio validation modules
│   ├── __init__.py
│   └── audio_validator.py    # Audio file validator
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── ffmpeg_checker.py     # FFmpeg dependency checker
│   └── file_detector.py      # File type detection
├── tests/                    # Test suites
│   ├── __init__.py
│   ├── test_media_converter.py
│   ├── test_audio_validator.py
│   ├── test_ffmpeg_checker.py
│   └── test_file_detector.py
├── PRD/                      # Product Requirements Documents
│   └── webm-to-mp3-transcription.md
├── pyproject.toml            # Project configuration
├── uv.lock                  # Dependency lock
├── .pre-commit-config.yaml  # Pre-commit configuration
├── README.md                # Project documentation
└── CLAUDE.md               # This configuration file
```

## Functional Modules

### Core Transcription Features
- **Audio Loading**: `torchaudio.load()` supports MP3
- **Audio Preprocessing**: Mono conversion, resampling to 16kHz
- **Speech Recognition**: MediaTek Breeze-ASR-25 Whisper model
- **Chunked Processing**: 30-second segment processing for long audio
- **Result Merging**: Concatenates all segment transcription results

### WebM Conversion Features (New)
- **FFmpeg Integration**: Cross-platform video conversion support
- **File Type Detection**: Automatic format recognition (WebM, MP4, MP3, etc.)
- **Media Conversion**: Async WebM to MP3 conversion with quality control
- **Audio Validation**: Comprehensive audio file validation and reporting
- **Quality Levels**: Configurable bitrate (128k/160k/256k)
- **Timeout Handling**: Configurable conversion timeouts

### Device Support
- Auto-detects MPS availability
- Graceful fallback to CPU
- Model loading to corresponding device

### Module Architecture
- **`utils/`**: Core utility functions (FFmpeg, file detection)
- **`converters/`**: Media conversion logic
- **`validators/`**: Audio file validation
- **`tests/`**: Comprehensive test coverage with TDD methodology

## Known Issues & Solutions

### Audio Backend Issues
- **Issue**: `torchaudio` cannot load MP3
- **Solution**: Install `soundfile` and `librosa`

### CUDA Support Issues
- **Issue**: macOS doesn't support CUDA
- **Solution**: Auto-switch to MPS or CPU

### Long Audio Processing Issues
- **Issue**: Whisper defaults to processing only first 30 seconds
- **Solution**: Implemented chunked processing functionality

## Performance Optimization

### Current Settings
- **Chunk Length**: 30 seconds
- **Model Parameters**: `max_length=448`, `num_beams=1`
- **Memory Management**: Using `torch.no_grad()`

### Performance Metrics
- **Processing Speed**: Approximately 1:1 real-time ratio (Apple Silicon)
- **Memory Usage**: ~2-3GB after model loading
- **Accuracy**: Good Chinese speech recognition performance

## Maintenance Notes

1. **Dependency Updates**: Regularly check `transformers` and `torch` versions
2. **Model Cache**: First run downloads model, requires internet connection
3. **Disk Space**: Whisper model ~1-2GB
4. **Compatibility**: Primarily optimized for macOS Apple Silicon

## Git Commit Convention

Using conventional commits format:
- `feat: new feature`
- `fix: bug fix`
- `docs: documentation update`
- `refactor: code refactoring`
- `perf: performance optimization`

Example: `feat: implement long audio chunking for complete transcription`
