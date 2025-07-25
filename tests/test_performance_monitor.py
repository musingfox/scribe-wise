"""Tests for performance monitoring utilities."""

from unittest.mock import Mock, patch

from utils.performance_monitor import (
    MemorySnapshot,
    ModelLoadOptimizer,
    PerformanceMonitor,
    PerformanceReport,
)


class TestMemorySnapshot:
    def test_memory_snapshot_creation(self):
        """Test memory snapshot creation with required fields."""
        snapshot = MemorySnapshot(
            timestamp=1234567890.0,
            process_memory_mb=1024.0,
            system_memory_percent=75.0,
            torch_allocated_mb=512.0,
            torch_cached_mb=256.0,
        )

        assert snapshot.timestamp == 1234567890.0
        assert snapshot.process_memory_mb == 1024.0
        assert snapshot.system_memory_percent == 75.0
        assert snapshot.torch_allocated_mb == 512.0
        assert snapshot.torch_cached_mb == 256.0

    def test_memory_snapshot_without_torch(self):
        """Test memory snapshot creation without torch metrics."""
        snapshot = MemorySnapshot(
            timestamp=1234567890.0,
            process_memory_mb=1024.0,
            system_memory_percent=75.0,
        )

        assert snapshot.torch_allocated_mb is None
        assert snapshot.torch_cached_mb is None


class TestPerformanceReport:
    def test_performance_report_creation(self):
        """Test performance report creation."""
        snapshots = [
            MemorySnapshot(
                timestamp=1234567890.0,
                process_memory_mb=1024.0,
                system_memory_percent=75.0,
            )
        ]

        report = PerformanceReport(
            operation_name="test_operation",
            duration_seconds=5.5,
            peak_memory_mb=1200.0,
            initial_memory_mb=1000.0,
            memory_delta_mb=200.0,
            snapshots=snapshots,
            torch_device="mps",
        )

        assert report.operation_name == "test_operation"
        assert report.duration_seconds == 5.5
        assert report.peak_memory_mb == 1200.0
        assert report.initial_memory_mb == 1000.0
        assert report.memory_delta_mb == 200.0
        assert len(report.snapshots) == 1
        assert report.torch_device == "mps"


class TestPerformanceMonitor:
    def test_init_default(self):
        """Test performance monitor initialization with defaults."""
        monitor = PerformanceMonitor()
        assert monitor.enable_torch_monitoring is False  # CUDA not available in test

    @patch("psutil.Process")
    @patch("psutil.virtual_memory")
    def test_take_memory_snapshot(self, mock_virtual_memory, mock_process):
        """Test taking memory snapshot."""
        # Mock process memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB in bytes
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance

        # Mock virtual memory
        mock_vm = Mock()
        mock_vm.percent = 75.0
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor(enable_torch_monitoring=False)
        snapshot = monitor.take_memory_snapshot()

        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.process_memory_mb == 1024.0  # 1GB -> 1024MB
        assert snapshot.system_memory_percent == 75.0
        assert snapshot.torch_allocated_mb is None
        assert snapshot.torch_cached_mb is None

    @patch("psutil.Process")
    def test_get_memory_usage_mb(self, mock_process):
        """Test getting current memory usage."""
        mock_memory_info = Mock()
        mock_memory_info.rss = 512 * 1024 * 1024  # 512MB in bytes
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance

        monitor = PerformanceMonitor()
        memory_mb = monitor.get_memory_usage_mb()

        assert memory_mb == 512.0

    @patch("psutil.Process")
    def test_check_memory_threshold(self, mock_process):
        """Test memory threshold checking."""
        mock_memory_info = Mock()
        mock_memory_info.rss = 9 * 1024 * 1024 * 1024  # 9GB in bytes
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance

        monitor = PerformanceMonitor()

        # Above threshold
        assert monitor.check_memory_threshold(8192) is True  # 8GB threshold

        # Below threshold
        assert monitor.check_memory_threshold(10240) is False  # 10GB threshold

    @patch("utils.performance_monitor.time.time")
    @patch("psutil.Process")
    @patch("psutil.virtual_memory")
    def test_monitor_operation_context_manager(
        self, mock_virtual_memory, mock_process, mock_time
    ):
        """Test operation monitoring context manager."""
        # Mock time progression - need more calls for initial + final snapshots
        mock_time.side_effect = [1000.0, 1000.0, 1005.5, 1005.5]  # 5.5 second operation

        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance

        # Mock virtual memory
        mock_vm = Mock()
        mock_vm.percent = 75.0
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor(enable_torch_monitoring=False)

        with monitor.monitor_operation("test_operation"):
            # Simulate some work
            pass

        # Verify snapshots were taken
        assert len(monitor._snapshots) == 2  # Initial and final
        assert monitor._operation_start_time == 1000.0
        assert monitor._initial_memory == 1024.0

    def test_cleanup_torch_cache_no_cuda(self):
        """Test torch cache cleanup when CUDA not available."""
        monitor = PerformanceMonitor()
        freed_mb = monitor.cleanup_torch_cache()
        assert freed_mb == 0.0


class TestModelLoadOptimizer:
    def test_init(self):
        """Test model load optimizer initialization."""
        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)
        assert optimizer.monitor is monitor
        assert optimizer._cached_models == {}

    @patch("torch.backends.mps.is_available")
    @patch("torch.cuda.is_available")
    def test_get_optimal_device_mps(self, mock_cuda_available, mock_mps_available):
        """Test optimal device selection - MPS preferred."""
        mock_mps_available.return_value = True
        mock_cuda_available.return_value = False

        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)
        device = optimizer.get_optimal_device()

        assert device == "mps"

    @patch("torch.backends.mps.is_available")
    @patch("torch.cuda.is_available")
    @patch("torch.cuda.get_device_properties")
    def test_get_optimal_device_cuda(
        self, mock_get_device_props, mock_cuda_available, mock_mps_available
    ):
        """Test optimal device selection - CUDA."""
        mock_mps_available.return_value = False
        mock_cuda_available.return_value = True

        # Mock device properties with sufficient VRAM
        mock_props = Mock()
        mock_props.total_memory = 8 * 1024**3  # 8GB
        mock_get_device_props.return_value = mock_props

        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)
        device = optimizer.get_optimal_device()

        assert device == "cuda"

    @patch("torch.backends.mps.is_available")
    @patch("torch.cuda.is_available")
    def test_get_optimal_device_cpu_fallback(
        self, mock_cuda_available, mock_mps_available
    ):
        """Test optimal device selection - CPU fallback."""
        mock_mps_available.return_value = False
        mock_cuda_available.return_value = False

        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)
        device = optimizer.get_optimal_device()

        assert device == "cpu"

    @patch("psutil.virtual_memory")
    def test_should_use_quantization_cpu_low_memory(self, mock_virtual_memory):
        """Test quantization decision for CPU with low memory."""
        # Mock low available memory (6GB)
        mock_vm = Mock()
        mock_vm.available = 6 * 1024**3  # 6GB in bytes
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)

        assert optimizer.should_use_quantization("cpu") is True

    @patch("psutil.virtual_memory")
    def test_should_use_quantization_cpu_high_memory(self, mock_virtual_memory):
        """Test quantization decision for CPU with high memory."""
        # Mock high available memory (16GB)
        mock_vm = Mock()
        mock_vm.available = 16 * 1024**3  # 16GB in bytes
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)

        assert optimizer.should_use_quantization("cpu") is False

    def test_should_use_quantization_gpu(self):
        """Test quantization decision for GPU (should be False by default)."""
        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)

        assert optimizer.should_use_quantization("cuda") is False
        assert optimizer.should_use_quantization("mps") is False

    def test_get_model_cache_key(self):
        """Test model cache key generation."""
        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)

        # Without quantization
        key1 = optimizer.get_model_cache_key("test-model", "mps", False)
        assert key1 == "test-model:mps:fp32"

        # With quantization
        key2 = optimizer.get_model_cache_key("test-model", "cpu", True)
        assert key2 == "test-model:cpu:q8"

    def test_clear_model_cache(self):
        """Test clearing model cache."""
        monitor = PerformanceMonitor()
        optimizer = ModelLoadOptimizer(monitor)

        # Add some cached models
        optimizer._cached_models["test1"] = ("model1", "processor1")
        optimizer._cached_models["test2"] = ("model2", "processor2")
        assert len(optimizer._cached_models) == 2

        optimizer.clear_model_cache()
        assert len(optimizer._cached_models) == 0

    @patch("utils.performance_monitor.time.time")
    @patch("psutil.Process")
    @patch("psutil.virtual_memory")
    def test_load_model_optimized_caching(
        self, mock_virtual_memory, mock_process, mock_time
    ):
        """Test model loading with caching."""
        # Mock time and memory for performance monitoring
        mock_time.side_effect = [1000.0, 1000.0, 1002.0, 1002.0]  # Need enough calls
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance
        mock_vm = Mock()
        mock_vm.percent = 75.0
        mock_vm.available = 8 * 1024**3  # 8GB available memory
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor(enable_torch_monitoring=False)
        optimizer = ModelLoadOptimizer(monitor)

        # Mock model class
        mock_model_class = Mock()
        mock_model_instance = Mock()
        mock_model_instance.to.return_value = mock_model_instance
        mock_model_instance.eval.return_value = mock_model_instance
        mock_model_class.from_pretrained.return_value = mock_model_instance

        # First load - should call from_pretrained
        with optimizer.load_model_optimized("test-model", mock_model_class, "cpu") as (
            model,
            processor,
        ):
            assert model is mock_model_instance
            assert processor is None

        # Verify model was cached
        cache_key = "test-model:cpu:fp32"
        assert cache_key in optimizer._cached_models

        # Second load - should use cache
        mock_model_class.from_pretrained.reset_mock()
        with optimizer.load_model_optimized("test-model", mock_model_class, "cpu") as (
            model,
            processor,
        ):
            assert model is mock_model_instance

        # Verify from_pretrained was not called again
        mock_model_class.from_pretrained.assert_not_called()


class TestPerformanceIntegration:
    """Integration tests for performance monitoring components."""

    @patch("utils.performance_monitor.time.time")
    @patch("psutil.Process")
    @patch("psutil.virtual_memory")
    def test_full_monitoring_workflow(
        self, mock_virtual_memory, mock_process, mock_time
    ):
        """Test complete performance monitoring workflow."""
        # Mock time progression - need enough calls for all snapshots
        mock_time.side_effect = [1000.0, 1000.0, 1001.0, 1002.0, 1003.0, 1003.0]

        # Mock memory progression
        memory_values = [1024, 1536, 1280, 1024]  # MB progression
        mock_memory_info_instances = []
        for mb in memory_values:
            mock_info = Mock()
            mock_info.rss = mb * 1024 * 1024
            mock_memory_info_instances.append(mock_info)

        mock_process_instance = Mock()
        mock_process_instance.memory_info.side_effect = mock_memory_info_instances
        mock_process.return_value = mock_process_instance

        # Mock virtual memory
        mock_vm = Mock()
        mock_vm.percent = 75.0
        mock_virtual_memory.return_value = mock_vm

        monitor = PerformanceMonitor(enable_torch_monitoring=False)

        with monitor.monitor_operation("integration_test"):
            # Take additional snapshots during operation
            snapshot1 = monitor.take_memory_snapshot()
            snapshot2 = monitor.take_memory_snapshot()

        # Verify snapshots show memory progression
        assert len(monitor._snapshots) == 2  # Initial and final from context manager
        assert snapshot1.process_memory_mb == 1536.0
        assert snapshot2.process_memory_mb == 1280.0
