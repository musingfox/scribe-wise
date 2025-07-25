"""LocalBreezeService for MediaTek Breeze-ASR-25 model."""

import numpy as np
import torch
import torchaudio
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from config.model_config import BREEZE_MODEL_NAME, ModelType
from services.base import (
    BaseTranscriptionService,
    ModelMetadata,
    ServiceStatus,
    TranscriptionResult,
)
from utils.performance_monitor import ModelLoadOptimizer, PerformanceMonitor
from utils.platform_compatibility import PlatformCompatibility

# Model configuration constants
TARGET_SAMPLE_RATE = 16_000
DEFAULT_CHUNK_LENGTH_SEC = 30
DEFAULT_MAX_LENGTH = 448
DEFAULT_NUM_BEAMS = 1


class LocalBreezeService(BaseTranscriptionService):
    """Local transcription service using MediaTek Breeze-ASR-25 model."""

    def __init__(
        self,
        chunk_length_sec: int = DEFAULT_CHUNK_LENGTH_SEC,
        device: str = "auto",
        enable_performance_monitoring: bool = True,
    ):
        """Initialize LocalBreezeService."""
        super().__init__()

        self.chunk_length_sec = chunk_length_sec
        self.device = device

        # Initialize platform compatibility and performance monitoring
        self.platform_compat = PlatformCompatibility()
        self.performance_monitor = PerformanceMonitor(
            enable_torch_monitoring=enable_performance_monitoring
        )
        self.model_optimizer = ModelLoadOptimizer(self.performance_monitor)

        # Model components
        self._model: WhisperForConditionalGeneration | None = None
        self._processor: WhisperProcessor | None = None
        self._device_resolved: str | None = None

    def get_metadata(self) -> ModelMetadata:
        """Get model metadata."""
        return ModelMetadata(
            name="MediaTek Breeze-ASR-25",
            version="1.0",
            model_type=ModelType.LOCAL_BREEZE,
            languages_supported=["zh", "en", "ja", "ko"],
            memory_requirements_mb=2048,
            performance_benchmark={
                "wer_zh": 0.08,  # Word Error Rate for Chinese
                "wer_en": 0.12,  # Word Error Rate for English
                "rtf": 1.0,  # Real-time factor
            },
            additional_info={
                "model_name": BREEZE_MODEL_NAME,
                "chunk_length_sec": self.chunk_length_sec,
                "supports_streaming": False,
            },
        )

    async def load_model(self) -> bool:
        """Load the Breeze-ASR-25 model."""
        try:
            self._status = ServiceStatus.LOADING

            # Get optimal device
            self._device_resolved = self._get_optimal_device()

            # Load model and processor
            self._model = WhisperForConditionalGeneration.from_pretrained(
                BREEZE_MODEL_NAME
            )
            self._processor = WhisperProcessor.from_pretrained(BREEZE_MODEL_NAME)

            # Move model to device and set to eval mode
            self._model = self._model.to(self._device_resolved)
            self._model = self._model.eval()

            self._status = ServiceStatus.READY
            return True

        except Exception:
            self._status = ServiceStatus.ERROR
            return False

    async def unload_model(self) -> bool:
        """Unload the model from memory."""
        try:
            self._model = None
            self._processor = None
            self._device_resolved = None

            # Clean up GPU memory if applicable
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._status = ServiceStatus.UNLOADED
            return True

        except Exception:
            return False

    async def transcribe_async(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file asynchronously."""
        if not self.is_ready():
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=BREEZE_MODEL_NAME,
                error_message="Service not ready. Call load_model() first.",
            )

        try:
            # Load and preprocess audio
            waveform, sample_rate = torchaudio.load(audio_path)
            waveform, sample_rate = self._preprocess_audio(waveform, sample_rate)

            # Split into chunks and transcribe
            chunks = self._split_into_chunks(waveform, sample_rate)
            transcription = await self._transcribe_chunks(chunks, sample_rate)

            # Calculate duration
            duration_seconds = len(waveform) / sample_rate

            return TranscriptionResult(
                success=True,
                transcription=transcription,
                input_path=audio_path,
                model_used=BREEZE_MODEL_NAME,
                duration_seconds=duration_seconds,
                metadata={
                    "num_chunks": len(chunks),
                    "chunk_length_sec": self.chunk_length_sec,
                    "device": self._device_resolved,
                },
            )

        except Exception as e:
            return TranscriptionResult(
                success=False,
                transcription=None,
                input_path=audio_path,
                model_used=BREEZE_MODEL_NAME,
                error_message=str(e),
            )

    def _get_optimal_device(self) -> str:
        """Get optimal device for this platform."""
        if self.device == "auto":
            return self.platform_compat.get_optimal_torch_device()
        return self.device

    def _preprocess_audio(
        self, waveform: torch.Tensor, sample_rate: int
    ) -> tuple[torch.Tensor, int]:
        """Preprocess audio: convert to mono and resample to 16kHz."""
        # Convert stereo to mono if needed
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0)
        waveform = waveform.squeeze()

        # Resample to target sample rate if needed
        if sample_rate != TARGET_SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sample_rate, TARGET_SAMPLE_RATE)
            waveform = resampler(waveform)
            sample_rate = TARGET_SAMPLE_RATE

        return waveform, sample_rate

    def _split_into_chunks(
        self, waveform: torch.Tensor, sample_rate: int
    ) -> list[torch.Tensor]:
        """Split audio into chunks for processing."""
        total_length = waveform.shape[0]
        chunk_samples = self.chunk_length_sec * sample_rate
        num_chunks = int(np.ceil(total_length / chunk_samples))

        chunks = []
        for i in range(num_chunks):
            start_idx = i * chunk_samples
            end_idx = min((i + 1) * chunk_samples, total_length)
            chunk = waveform[start_idx:end_idx]
            chunks.append(chunk)

        return chunks

    async def _transcribe_chunks(
        self, chunks: list[torch.Tensor], sample_rate: int
    ) -> str:
        """Transcribe audio chunks and combine results."""
        transcriptions = []

        for chunk in chunks:
            # Process chunk through processor
            input_features = self._processor(
                chunk, sampling_rate=sample_rate, return_tensors="pt"
            ).input_features.to(self._device_resolved)

            # Generate transcription
            with torch.no_grad():
                predicted_ids = self._model.generate(
                    input_features,
                    max_length=DEFAULT_MAX_LENGTH,
                    num_beams=DEFAULT_NUM_BEAMS,
                    do_sample=False,
                )
                chunk_transcription = self._processor.batch_decode(
                    predicted_ids, skip_special_tokens=True
                )[0]

            if chunk_transcription.strip():
                transcriptions.append(chunk_transcription.strip())

        return " ".join(transcriptions)
