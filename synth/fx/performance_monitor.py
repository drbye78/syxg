"""
XG Effects Performance Monitor and Profiler

This module provides comprehensive performance monitoring and profiling
for the XG effects system. Tracks CPU usage, memory consumption, latency,
and processing efficiency across all effect chains.

Key Features:
- Real-time CPU usage monitoring per effect
- Memory allocation tracking (zero-allocation compliance)
- Processing latency measurements
- Effect chain performance analysis
- Statistical reporting and alerting
- Thread-safe profiling with minimal overhead
- XG-specific performance metrics

Performance Categories:
- System Effects: Reverb/Chorus CPU and latency
- Variation Effects: Per-type processing statistics
- Insertion Effects: Channel processing overhead
- EQ/Mixer: Signal chain efficiency
- Buffer Management: Pool usage and allocation monitoring
- MIDI Control: Parameter update response times
"""

import time
import numpy as np
import threading
import psutil
import os
from typing import Dict, List, Tuple, Optional, Any, Callable
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

# Import our core components for monitoring
try:
    from .effects_coordinator import XGEffectsCoordinator
    from .buffer_pool import XGBufferPool
except ImportError:
    # Fallback for development
    pass


class XGPerformanceMetric(IntEnum):
    """XG Performance Metrics"""
    CPU_PERCENT = 0
    MEMORY_MB = 1
    LATENCY_MS = 2
    ALLOCATION_COUNT = 3
    PROCESSING_BLOCKS = 4
    MISSED_DEADLINES = 5
    PARAMETER_UPDATES = 6


class XGProfilingEvent(IntEnum):
    """Profiling Events for Timeline Tracking"""
    PROCESS_START = 0
    PROCESS_END = 1
    PARAMETER_UPDATE = 2
    BUFFER_ALLOCATE = 3
    BUFFER_RELEASE = 4
    EFFECT_ENABLE = 5
    EFFECT_DISABLE = 6


@dataclass
class XGProcessStats:
    """XG Processing Statistics Structure"""
    total_blocks: int = 0
    total_time_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    cpu_percent_avg: float = 0.0
    memory_mb_avg: float = 0.0
    buffer_allocations: int = 0
    missed_deadlines: int = 0
    parameter_updates: int = 0


@dataclass
class XGEffectProfile:
    """XG Effect Profile Data"""
    effect_type: str
    active_channels: int = 0
    processing_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    allocations: int = 0
    parameter_changes: int = 0
    quality_score: float = 1.0  # 1.0 = perfect, lower = degraded


class XGPerformanceProfiler:
    """
    XG Performance Profiler

    Advanced profiling system for tracking XG effects performance at multiple levels.
    Provides real-time monitoring with minimal overhead.
    """

    def __init__(self, target_latency_ms: float = 10.0, history_size: int = 1000):
        """
        Initialize performance profiler.

        Args:
            target_latency_ms: Target processing latency in milliseconds
            history_size: Number of historical samples to keep
        """
        self.target_latency_ms = target_latency_ms
        self.history_size = history_size

        # Core statistics
        self.global_stats = XGProcessStats()

        # Effect-specific profiling
        self.effect_profiles: Dict[str, XGEffectProfile] = {}
        self.system_profile = XGEffectProfile("system", 2)  # Stereo
        self.variation_profile = XGEffectProfile("variation", 1)  # Mono input
        self.insertion_profile = XGEffectProfile("insertion", 16)  # 16 channels
        self.mixer_profile = XGEffectProfile("mixer", 16)  # 16 channels to stereo

        # Historical data (rolling buffers)
        self.latency_history = deque(maxlen=history_size)
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)

        # Process monitoring
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.baseline_cpu = self.process.cpu_percent()

        # Timing and state
        self.session_start_time = time.time()
        self.last_sample_time = time.time()
        self.reset_interval = 60.0  # Reset stats every minute

        # Thread safety
        self.lock = threading.RLock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring_active = False

        # Alerting thresholds
        self.cpu_threshold_percent = 80.0
        self.latency_threshold_ms = target_latency_ms * 2.0
        self.memory_threshold_mb = 1000.0  # 1GB

        # Callbacks for alerts
        self.alert_callbacks: List[Callable] = []

    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        with self.lock:
            if self.monitoring_active:
                return

            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        with self.lock:
            self.monitoring_active = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)

    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback for performance alerts."""
        with self.lock:
            self.alert_callbacks.append(callback)

    def begin_frame(self) -> float:
        """
        Mark the beginning of a processing frame.

        Returns:
            Start time for profiling
        """
        return time.perf_counter()

    def end_frame(self, start_time: float, num_samples: int, num_channels: int) -> float:
        """
        Mark the end of a processing frame and record timing.

        Args:
            start_time: Start time from begin_frame()
            num_samples: Number of samples processed
            num_channels: Number of channels processed

        Returns:
            Processing latency in milliseconds
        """
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0

        with self.lock:
            # Update global statistics
            self.global_stats.total_blocks += 1
            self.global_stats.total_time_ms += latency_ms

            if latency_ms < self.global_stats.min_latency_ms:
                self.global_stats.min_latency_ms = latency_ms
            if latency_ms > self.global_stats.max_latency_ms:
                self.global_stats.max_latency_ms = latency_ms

            # Rolling average latency
            self.latency_history.append(latency_ms)
            self.global_stats.avg_latency_ms = np.mean(list(self.latency_history))

            # Check for missed deadlines
            if latency_ms > self.target_latency_ms:
                self.global_stats.missed_deadlines += 1

                # Trigger alert if threshold exceeded
                if latency_ms > self.latency_threshold_ms:
                    self._trigger_alert("HIGH_LATENCY", f"Latency {latency_ms:.1f}ms > threshold {self.latency_threshold_ms:.1f}ms")

            return latency_ms

    def record_effect_processing(self, effect_name: str, processing_time_ms: float,
                               cpu_percent: float = 0.0, allocations: int = 0) -> None:
        """
        Record processing statistics for a specific effect.

        Args:
            effect_name: Name of the effect
            processing_time_ms: Time spent processing this effect
            cpu_percent: CPU usage for this effect
            allocations: Number of memory allocations made
        """
        with self.lock:
            if effect_name not in self.effect_profiles:
                self.effect_profiles[effect_name] = XGEffectProfile(effect_name)

            profile = self.effect_profiles[effect_name]
            profile.processing_time_ms += processing_time_ms
            profile.cpu_percent = cpu_percent
            profile.allocations += allocations

            # Update global allocation count
            self.global_stats.buffer_allocations += allocations

    def record_parameter_update(self, effect_name: str = "unknown") -> None:
        """Record a parameter update event."""
        with self.lock:
            self.global_stats.parameter_updates += 1

            if effect_name in self.effect_profiles:
                self.effect_profiles[effect_name].parameter_changes += 1

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.

        Returns:
            Dictionary containing all performance metrics
        """
        with self.lock:
            # Calculate final averages
            total_blocks = max(self.global_stats.total_blocks, 1)
            session_time_seconds = time.time() - self.session_start_time

            # Get current resource usage
            current_cpu = self.process.cpu_percent()
            current_memory = self.process.memory_info().rss / 1024 / 1024 - self.baseline_memory

            # Update historical data
            self.cpu_history.append(current_cpu)
            self.memory_history.append(current_memory)

            # Calculate quality score (1.0 = perfect performance)
            quality_score = self._calculate_quality_score()

            return {
                'session_time_seconds': session_time_seconds,
                'global_stats': {
                    'blocks_processed': self.global_stats.total_blocks,
                    'blocks_per_second': self.global_stats.total_blocks / session_time_seconds if session_time_seconds > 0 else 0,
                    'latency_ms': {
                        'current': self.latency_history[-1] if self.latency_history else 0,
                        'average': self.global_stats.avg_latency_ms,
                        'min': self.global_stats.min_latency_ms if self.global_stats.min_latency_ms != float('inf') else 0,
                        'max': self.global_stats.max_latency_ms,
                        'target': self.target_latency_ms,
                    },
                    'cpu_percent': {
                        'current': current_cpu,
                        'average': np.mean(list(self.cpu_history)) if self.cpu_history else 0,
                        'peak': max(self.cpu_history) if self.cpu_history else 0,
                    },
                    'memory_mb': {
                        'current': current_memory,
                        'average': np.mean(list(self.memory_history)) if self.memory_history else 0,
                        'peak': max(self.memory_history) if self.memory_history else 0,
                    },
                    'allocations': self.global_stats.buffer_allocations,
                    'parameter_updates': self.global_stats.parameter_updates,
                    'missed_deadlines': self.global_stats.missed_deadlines,
                    'deadline_miss_rate': self.global_stats.missed_deadlines / total_blocks,
                },
                'quality_score': quality_score,
                'effect_profiles': {
                    name: {
                        'processing_time_ms': profile.processing_time_ms,
                        'cpu_percent': profile.cpu_percent,
                        'memory_usage_mb': profile.memory_usage_mb,
                        'allocations': profile.allocations,
                        'parameter_changes': profile.parameter_changes,
                        'quality_score': profile.quality_score,
                    }
                    for name, profile in self.effect_profiles.items()
                },
                'system_effects': {
                    'reverb': {
                        'active': True,  # Would get from actual system
                        'processing_time_ms': self.system_profile.processing_time_ms,
                        'quality_score': self.system_profile.quality_score,
                    },
                    'chorus': {
                        'active': True,
                        'processing_time_ms': self.system_profile.processing_time_ms,
                        'quality_score': self.system_profile.quality_score,
                    }
                },
                'alerts': {
                    'cpu_high': current_cpu > self.cpu_threshold_percent,
                    'latency_high': self.latency_history[-1] > self.latency_threshold_ms if self.latency_history else False,
                    'memory_high': current_memory > self.memory_threshold_mb,
                }
            }

    def _calculate_quality_score(self) -> float:
        """
        Calculate overall system quality score.

        Quality factors:
        - Latency compliance (40%)
        - CPU usage efficiency (30%)
        - Memory usage efficiency (20%)
        - Allocation compliance (10%)

        Returns:
            Quality score from 0.0 to 1.0
        """
        # Latency quality (inverted - lower latency = higher quality)
        latency_ratio = min(self.target_latency_ms / self.global_stats.avg_latency_ms, 1.0) if self.global_stats.avg_latency_ms > 0 else 1.0
        quality_latency = latency_ratio

        # CPU quality (inverted - lower CPU for same work = higher quality)
        cpu_usage = np.mean(list(self.cpu_history)) if self.cpu_history else 0
        quality_cpu = max(0, 1.0 - cpu_usage / self.cpu_threshold_percent)

        # Memory quality (lower memory usage = higher quality)
        memory_usage = np.mean(list(self.memory_history)) if self.memory_history else 0
        quality_memory = max(0, 1.0 - memory_usage / self.memory_threshold_mb)

        # Allocation quality (fewer allocations = higher quality)
        alloc_penalty = min(self.global_stats.buffer_allocations / max(self.global_stats.total_blocks * 10, 1), 1.0)
        quality_alloc = 1.0 - alloc_penalty

        # Weighted final score
        final_score = (
            quality_latency * 0.4 +
            quality_cpu * 0.3 +
            quality_memory * 0.2 +
            quality_alloc * 0.1
        )

        return max(0.0, min(1.0, final_score))

    def _trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger performance alert to all registered callbacks."""
        alert_data = {
            'type': alert_type,
            'message': message,
            'timestamp': time.time(),
            'performance_data': self.get_performance_report()
        }

        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception:
                pass  # Don't let callback errors affect performance

    def _monitor_loop(self) -> None:
        """Main monitoring loop for continuous performance tracking."""
        while self.monitoring_active:
            try:
                # Periodic performance checks
                time.sleep(1.0)  # Check every second

                # Check for performance degradation
                if self.latency_history:
                    current_latency = self.latency_history[-1]
                    if current_latency > self.latency_threshold_ms * 1.5:  # 150% of threshold
                        self._trigger_alert("CRITICAL_LATENCY", f"Critical latency: {current_latency:.1f}ms")

                # Periodic reset of statistics
                current_time = time.time()
                if current_time - self.last_sample_time > self.reset_interval:
                    self._reset_periodic_stats()
                    self.last_sample_time = current_time

            except Exception as e:
                print(f"Performance monitoring error: {e}")
                break

    def _reset_periodic_stats(self) -> None:
        """Reset periodic statistics while keeping session totals."""
        # Keep total blocks and time, but reset derived stats for fresh calculations
        self.latency_history.clear()
        self.cpu_history.clear()
        self.memory_history.clear()

        # Reset min/max (they will be recalculated from new data)
        self.global_stats.min_latency_ms = float('inf')
        self.global_stats.max_latency_ms = 0.0


class XGMemoryProfiler:
    """
    XG Memory Profiler

    Specialized memory profiling for XG effects with zero-allocation compliance checking.
    Tracks buffer usage, allocation patterns, and memory efficiency.
    """

    def __init__(self, buffer_pool: Optional[Any] = None):
        """
        Initialize memory profiler.

        Args:
            buffer_pool: XGBufferPool instance to monitor
        """
        self.buffer_pool = buffer_pool
        self.memory_samples: Dict[str, List[float]] = {}
        self.allocation_events: List[Tuple[float, str, bool]] = []  # (time, type, allocated)

        # Memory statistics
        self.peak_memory_mb = 0.0
        self.current_memory_mb = 0.0
        self.total_allocations = 0
        self.zero_alloc_violations = 0

        # Thread safety
        self.lock = threading.RLock()

    def record_allocation(self, allocation_type: str, size_bytes: int, allocated: bool = True) -> None:
        """
        Record a memory allocation/deallocation event.

        Args:
            allocation_type: Type of allocation (buffer, effect, etc.)
            size_bytes: Size of allocation in bytes
            allocated: True for allocation, False for deallocation
        """
        with self.lock:
            timestamp = time.time()
            self.allocation_events.append((timestamp, allocation_type, allocated))

            size_mb = size_bytes / 1024 / 1024

            if allocation_type not in self.memory_samples:
                self.memory_samples[allocation_type] = []

            if allocated:
                self.memory_samples[allocation_type].append(size_mb)
                self.current_memory_mb += size_mb
                self.total_allocations += 1

                if self.current_memory_mb > self.peak_memory_mb:
                    self.peak_memory_mb = self.current_memory_mb
            else:
                # Deallocation
                self.current_memory_mb -= size_mb

                # Remove from samples (simplified)
                if self.memory_samples[allocation_type]:
                    self.memory_samples[allocation_type].pop()

    def record_zero_alloc_violation(self, violation_type: str) -> None:
        """
        Record a zero-allocation policy violation.

        Args:
            violation_type: Type of violation (realtime_alloc, etc.)
        """
        with self.lock:
            self.zero_alloc_violations += 1
            print(f"ZERO-ALLOCATION VIOLATION: {violation_type}")

    def get_memory_report(self) -> Dict[str, Any]:
        """Generate detailed memory usage report."""
        with self.lock:
            total_allocated = sum(
                sum(samples) for samples in self.memory_samples.values()
            )

            return {
                'current_memory_mb': self.current_memory_mb,
                'peak_memory_mb': self.peak_memory_mb,
                'total_allocations': self.total_allocations,
                'zero_alloc_violations': self.zero_alloc_violations,
                'allocation_types': {
                    alloc_type: {
                        'count': len(samples),
                        'total_mb': sum(samples),
                        'average_mb': np.mean(samples) if samples else 0,
                        'peak_mb': max(samples) if samples else 0,
                    }
                    for alloc_type, samples in self.memory_samples.items()
                },
                'compliance_score': max(0, 1.0 - (self.zero_alloc_violations / max(self.total_allocations, 1))),
            }


class XGPerformanceMonitor:
    """
    XG Performance Monitor - Main Interface

    Unified interface for all XG performance monitoring and profiling.
    Provides high-level API for effect performance management.
    """

    def __init__(self, target_latency_ms: float = 10.0):
        """
        Initialize XG performance monitor.

        Args:
            target_latency_ms: Target processing latency in milliseconds
        """
        self.profiler = XGPerformanceProfiler(target_latency_ms)
        self.memory_profiler = XGMemoryProfiler()

        # Quick-access timing
        self._current_frame_start = 0.0

        # Thread safety
        self.lock = threading.RLock()

    def begin_processing_frame(self) -> None:
        """Mark the start of an audio processing frame."""
        with self.lock:
            self._current_frame_start = self.profiler.begin_frame()

    def end_processing_frame(self, num_samples: int, num_channels: int) -> float:
        """
        Mark the end of an audio processing frame.

        Args:
            num_samples: Number of samples processed
            num_channels: Number of channels processed

        Returns:
            Processing latency in milliseconds
        """
        with self.lock:
            return self.profiler.end_frame(self._current_frame_start, num_samples, num_channels)

    def monitor_effect(self, effect_name: str, start_time: Optional[float] = None) -> Callable:
        """
        Create a context manager for monitoring effect processing.

        Args:
            effect_name: Name of the effect to monitor
            start_time: Optional explicit start time

        Returns:
            Context manager for timing the effect
        """
        actual_start = start_time if start_time is not None else time.perf_counter()

        class EffectMonitor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                end_time = time.perf_counter()
                processing_time_ms = (end_time - actual_start) * 1000.0
                self.profiler.record_effect_processing(effect_name, processing_time_ms)

        # Create bound instance
        monitor = EffectMonitor()
        monitor.profiler = self.profiler
        return monitor

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance and memory report.

        Returns:
            Combined performance and memory statistics
        """
        with self.lock:
            report = self.profiler.get_performance_report()
            report['memory'] = self.memory_profiler.get_memory_report()
            return report

    def add_performance_alert_callback(self, callback: Callable) -> None:
        """Add a callback for performance alerts."""
        self.profiler.register_alert_callback(callback)

    def start_continuous_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        self.profiler.start_monitoring()

    def stop_continuous_monitoring(self) -> None:
        """Stop continuous performance monitoring."""
        self.profiler.stop_monitoring()

    @staticmethod
    def create_default_monitor() -> 'XGPerformanceMonitor':
        """Create a default XG performance monitor with standard settings."""
        return XGPerformanceMonitor(target_latency_ms=10.0)  # <10ms for realtime

# Global monitor instance for easy access
_default_monitor = XGPerformanceMonitor.create_default_monitor()

def get_global_monitor() -> XGPerformanceMonitor:
    """Get the global XG performance monitor instance."""
    return _default_monitor

def enable_performance_monitoring() -> None:
    """Enable global performance monitoring."""
    _default_monitor.start_continuous_monitoring()

def disable_performance_monitoring() -> None:
    """Disable global performance monitoring."""
    _default_monitor.stop_continuous_monitoring()
