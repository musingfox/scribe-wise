# Scrible Wise

An audio transcription tool based on Whisper models that converts long audio files into Chinese transcripts, with support for WebM video to MP3 conversion.

## Features

### Audio Transcription
- Supports various audio formats including MP3
- Uses MediaTek Breeze-ASR-25 model for Chinese speech recognition
- Automatic chunking for long audio files (30-second segments)
- Supports Apple Silicon (MPS) and CPU computation
- Complete transcription results saved as text files

### WebM to MP3 Conversion (New)
- Convert WebM video files to MP3 audio format
- Multiple quality levels (Low: 128k, Medium: 160k, High: 256k bitrate)
- Async processing with timeout handling
- FFmpeg integration with cross-platform support
- Audio file validation with detailed reporting

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

## Usage

### Audio Transcription
1. Name your audio file `meeting.mp3` and place it in the project root directory
2. Run the transcription program:

```bash
uv run python main.py
```

### WebM to MP3 Conversion
The tool supports converting WebM video files to MP3 audio format before transcription:

```python
from converters.media_converter import MediaConverter, QualityLevel
from validators.audio_validator import AudioValidator
from utils.ffmpeg_checker import FFmpegChecker
from utils.file_detector import FileTypeDetector

# Check FFmpeg installation
ffmpeg_checker = FFmpegChecker()
if not ffmpeg_checker.check_ffmpeg_installation():
    raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")

# Detect file type
detector = FileTypeDetector()
file_type = detector.detect_file_type("input.webm")

# Convert WebM to MP3
converter = MediaConverter(quality=QualityLevel.MEDIUM)
result = await converter.convert_webm_to_mp3("input.webm", "output.mp3")

# Validate converted audio
validator = AudioValidator()
validation_result = validator.validate_audio_file("output.mp3")
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
- **Speech Recognition**: Hugging Face Transformers Whisper
- **Hardware Acceleration**: Apple MPS (Metal Performance Shaders)
- **Package Management**: `uv`
- **Testing**: pytest with asyncio support
- **Code Quality**: ruff, black, isort, mypy

### Module Structure

```
scrible-wise/
├── main.py                    # Main transcription program
├── converters/                # Media conversion modules
│   └── media_converter.py     # WebM to MP3 converter
├── validators/                # Audio validation modules
│   └── audio_validator.py     # Audio file validator
├── utils/                     # Utility modules
│   ├── ffmpeg_checker.py      # FFmpeg dependency checker
│   └── file_detector.py       # File type detection
└── tests/                     # Test suites
    ├── test_media_converter.py
    ├── test_audio_validator.py
    ├── test_ffmpeg_checker.py
    └── test_file_detector.py
```

## Output Example

```
Starting long audio transcription...
Using device: mps
Audio duration: 7.0 minutes
Processing in 15 segments, 30 seconds each
Processing segment 1/15 (0.0s - 30.0s)
Segment 1 result: That's start our meeting today
...
Transcription saved to transcription.txt
```

## Notes

- First run will download Whisper model, internet connection required
- Processing time depends on audio length and hardware performance
- Recommended to run on Apple Silicon Mac for optimal performance
- Supports Chinese speech recognition, limited effectiveness for other languages

## Troubleshooting

If you encounter audio loading issues, ensure `soundfile` and `librosa` packages are installed:

```bash
uv add soundfile librosa
```

If you encounter CUDA-related errors, the program will automatically switch to MPS or CPU mode.
