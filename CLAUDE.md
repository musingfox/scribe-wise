# Claude Code Project Configuration

## Project Information

- **Project Name**: Scrible Wise
- **Project Type**: Audio transcription tool
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
- `numpy`

### Development Dependencies
- `ruff>=0.8.0` - Fast Python linter
- `black>=24.0.0` - Code formatter
- `isort>=5.13.0` - Import sorter
- `mypy>=1.13.0` - Type checker

### Hardware Support
- **Recommended**: Apple Silicon (MPS)
- **Fallback**: CPU
- **Not Supported**: CUDA (auto-switching configured)

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
- Currently no automated testing framework
- Manual testing: Use `meeting.mp3` for transcription testing
- Output validation: Check `transcription.txt` completeness

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
├── main.py              # Main program
├── meeting.mp3          # Test audio file
├── transcription.txt    # Output results
├── pyproject.toml       # Project configuration
├── uv.lock             # Dependency lock
├── README.md           # Project documentation
└── CLAUDE.md           # This configuration file
```

## Functional Modules

### Core Features
- **Audio Loading**: `torchaudio.load()` supports MP3
- **Audio Preprocessing**: Mono conversion, resampling to 16kHz
- **Speech Recognition**: MediaTek Breeze-ASR-25 Whisper model
- **Chunked Processing**: 30-second segment processing for long audio
- **Result Merging**: Concatenates all segment transcription results

### Device Support
- Auto-detects MPS availability
- Graceful fallback to CPU
- Model loading to corresponding device

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
