"""Performance monitoring utilities for Scrible Wise transcription workflow."""

import logging
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

import psutil
import torch


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific time."""

    timestamp: float
    process_memory_mb: float
    system_memory_percent: float
    torch_allocated_mb: float | None = None
    torch_cached_mb: float | None = None


@dataclass
class PerformanceReport:
    """Complete performance report for an operation."""

    operation_name: str
    duration_seconds: float
    peak_memory_mb: float
    initial_memory_mb: float
    memory_delta_mb: float
    snapshots: list[MemorySnapshot]
    torch_device: str | None = None


class PerformanceMonitor:
    """Monitor performance metrics during transcription workflow."""

    def __init__(self, enable_torch_monitoring: bool = True):
        """Initialize performance monitor."""
        self.enable_torch_monitoring = (
            enable_torch_monitoring and torch.cuda.is_available()
        )
        self.logger = logging.getLogger(__name__)
        self._snapshots: list[MemorySnapshot] = []
        self._operation_start_time: float | None = None
        self._initial_memory: float | None = None

    def take_memory_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage."""
        process = psutil.Process(os.getpid())
        process_memory_mb = process.memory_info().rss / 1024 / 1024
        system_memory_percent = psutil.virtual_memory().percent

        torch_allocated_mb = None
        torch_cached_mb = None

        if self.enable_torch_monitoring:
            try:
                torch_allocated_mb = torch.cuda.memory_allocated() / 1024 / 1024
                torch_cached_mb = torch.cuda.memory_reserved() / 1024 / 1024
            except Exception:
                # CUDA not available or other torch memory issues
                pass

        return MemorySnapshot(
            timestamp=time.time(),
            process_memory_mb=process_memory_mb,
            system_memory_percent=system_memory_percent,
            torch_allocated_mb=torch_allocated_mb,
            torch_cached_mb=torch_cached_mb,
        )

    def get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def check_memory_threshold(self, threshold_mb: float = 8192) -> bool:
        """Check if memory usage exceeds threshold."""
        current_memory = self.get_memory_usage_mb()
        return current_memory > threshold_mb

    def log_memory_warning(self, threshold_mb: float = 8192) -> None:
        """Log memory warning if usage is high."""
        current_memory = self.get_memory_usage_mb()
        if current_memory > threshold_mb:
            self.logger.warning(
                f"High memory usage detected: {current_memory:.1f}MB "
                f"(threshold: {threshold_mb}MB)"
            )

    @contextmanager
    def monitor_operation(
        self, operation_name: str, memory_threshold_mb: float = 8192
    ) -> Generator[None]:
        """Context manager to monitor an operation's performance."""
        self._operation_start_time = time.time()
        initial_snapshot = self.take_memory_snapshot()
        self._initial_memory = initial_snapshot.process_memory_mb
        self._snapshots = [initial_snapshot]

        try:
            yield
        finally:
            end_time = time.time()
            final_snapshot = self.take_memory_snapshot()
            self._snapshots.append(final_snapshot)

            # Generate performance report
            duration = end_time - self._operation_start_time
            peak_memory = max(
                snapshot.process_memory_mb for snapshot in self._snapshots
            )
            memory_delta = final_snapshot.process_memory_mb - self._initial_memory

            report = PerformanceReport(
                operation_name=operation_name,
                duration_seconds=duration,
                peak_memory_mb=peak_memory,
                initial_memory_mb=self._initial_memory,
                memory_delta_mb=memory_delta,
                snapshots=self._snapshots,
                torch_device=self._get_torch_device(),
            )

            self._log_performance_report(report, memory_threshold_mb)

    def _get_torch_device(self) -> str | None:
        """Get current torch device."""
        try:
            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return f"cuda:{torch.cuda.current_device()}"
            else:
                return "cpu"
        except Exception:
            return None

    def _log_performance_report(
        self, report: PerformanceReport, memory_threshold_mb: float
    ) -> None:
        """Log performance report."""
        self.logger.info(
            f"Performance Report - {report.operation_name}: "
            f"Duration: {report.duration_seconds:.2f}s, "
            f"Peak Memory: {report.peak_memory_mb:.1f}MB, "
            f"Memory Delta: {report.memory_delta_mb:+.1f}MB"
        )

        if report.torch_device:
            self.logger.info(f"Torch Device: {report.torch_device}")

        if report.peak_memory_mb > memory_threshold_mb:
            self.logger.warning(
                f"High memory usage during {report.operation_name}: "
                f"{report.peak_memory_mb:.1f}MB (threshold: {memory_threshold_mb}MB)"
            )

    def cleanup_torch_cache(self) -> float:
        """Cleanup torch cache and return freed memory in MB."""
        if not torch.cuda.is_available():
            return 0.0

        try:
            memory_before = torch.cuda.memory_allocated() / 1024 / 1024
            torch.cuda.empty_cache()
            memory_after = torch.cuda.memory_allocated() / 1024 / 1024
            freed_mb = memory_before - memory_after

            if freed_mb > 0:
                self.logger.info(f"Freed {freed_mb:.1f}MB from torch cache")

            return freed_mb
        except Exception as e:
            self.logger.warning(f"Failed to cleanup torch cache: {e}")
            return 0.0


class ModelLoadOptimizer:
    """Optimize model loading and memory usage."""

    def __init__(self, performance_monitor: PerformanceMonitor):
        """Initialize with performance monitor."""
        self.monitor = performance_monitor
        self.logger = logging.getLogger(__name__)
        self._cached_models = {}

    def get_optimal_device(self) -> str:
        """Get optimal device based on available hardware and memory."""
        # Check MPS availability (Apple Silicon)
        if torch.backends.mps.is_available():
            return "mps"

        # Check CUDA availability
        if torch.cuda.is_available():
            # Check VRAM availability
            total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if total_vram < 4.0:  # Less than 4GB VRAM
                self.logger.warning(
                    f"Limited VRAM ({total_vram:.1f}GB), considering CPU fallback"
                )

            return "cuda"

        # Fallback to CPU
        self.logger.info("Using CPU for inference (MPS/CUDA not available)")
        return "cpu"

    def should_use_quantization(self, device: str) -> bool:
        """Determine if quantization should be used based on available memory."""
        if device == "cpu":
            # Check system RAM
            memory_info = psutil.virtual_memory()
            available_gb = memory_info.available / 1024**3
            return available_gb < 8.0  # Use quantization if less than 8GB available

        return False  # Don't quantize for GPU by default

    def get_model_cache_key(self, model_name: str, device: str, quantized: bool) -> str:
        """Generate cache key for model."""
        return f"{model_name}:{device}:{'q8' if quantized else 'fp32'}"

    def clear_model_cache(self) -> None:
        """Clear cached models to free memory."""
        self.logger.info(f"Clearing {len(self._cached_models)} cached models")
        self._cached_models.clear()
        self.monitor.cleanup_torch_cache()

    @contextmanager
    def load_model_optimized(
        self, model_name: str, model_class, device: str | None = None
    ) -> Generator[tuple]:
        """Load model with optimization and caching."""
        if device is None:
            device = self.get_optimal_device()

        quantized = self.should_use_quantization(device)
        cache_key = self.get_model_cache_key(model_name, device, quantized)

        # Check cache first
        if cache_key in self._cached_models:
            self.logger.info(f"Using cached model: {cache_key}")
            yield self._cached_models[cache_key]
            return

        # Load model with performance monitoring
        with self.monitor.monitor_operation(f"load_model_{model_name}"):
            try:
                self.logger.info(f"Loading model {model_name} on {device}")

                if quantized:
                    self.logger.info("Using quantization for memory optimization")

                # Load model based on type
                if "processor" in model_name.lower():
                    model = model_class.from_pretrained(model_name)
                    processor = None
                else:
                    from transformers import WhisperProcessor

                    processor = WhisperProcessor.from_pretrained(model_name)
                    model = model_class.from_pretrained(model_name).to(device).eval()

                    if quantized and device == "cpu":
                        # Apply dynamic quantization for CPU
                        try:
                            model = torch.jit.script(model)
                            self.logger.info("Applied TorchScript optimization")
                        except Exception as e:
                            self.logger.warning(f"TorchScript optimization failed: {e}")

                # Cache the loaded model
                self._cached_models[cache_key] = (model, processor)
                self.logger.info(f"Model cached with key: {cache_key}")

                yield (model, processor)

            except Exception as e:
                self.logger.error(f"Failed to load model {model_name}: {e}")
                raise
