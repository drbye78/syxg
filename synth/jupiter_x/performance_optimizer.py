"""
Jupiter-X Performance Optimization Suite

Comprehensive real-time performance optimization system providing
monitoring, profiling, and optimization tools for maximum synthesis
performance and stability.
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import time
import psutil
import numpy as np
from collections import deque
import gc
import sys
import os


class PerformanceMetrics:
    """Real-time performance metrics collection and analysis."""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size

        # CPU metrics
        self.cpu_usage = deque(maxlen=window_size)
        self.cpu_per_core = deque(maxlen=window_size)

        # Memory metrics
        self.memory_usage = deque(maxlen=window_size)
        self.memory_peak = 0
        self.allocation_count = deque(maxlen=window_size)

        # Audio processing metrics
        self.processing_time = deque(maxlen=window_size)
        self.processing_time_peak = 0
        self.xruns = 0
        self.buffer_underruns = 0

        # Synthesis metrics
        self.active_voices = deque(maxlen=window_size)
        self.polyphony_peak = 0
        self.engine_load = {}  # engine -> load percentage

        # System metrics
        self.system_load = deque(maxlen=window_size)
        self.disk_io = deque(maxlen=window_size)

        # Timing
        self.last_update = time.time()
        self.update_interval = 0.1  # 100ms updates

    def update(self):
        """Update all performance metrics."""
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return

        self.last_update = current_time

        # CPU metrics
        self.cpu_usage.append(psutil.cpu_percent(interval=None))
        self.cpu_per_core.append(psutil.cpu_percent(percpu=True))

        # Memory metrics
        memory = psutil.virtual_memory()
        self.memory_usage.append(memory.percent)
        self.memory_peak = max(self.memory_peak, memory.used)

        # Get allocation count (approximate)
        self.allocation_count.append(len(gc.get_objects()))

    def record_processing_time(self, processing_time_ms: float):
        """Record audio processing time."""
        self.processing_time.append(processing_time_ms)
        self.processing_time_peak = max(self.processing_time_peak, processing_time_ms)

        # Check for xruns (processing time > buffer time)
        # Assuming 5ms buffer time for 200Hz update rate
        if processing_time_ms > 5.0:
            self.xruns += 1

    def record_voice_count(self, voice_count: int):
        """Record active voice count."""
        self.active_voices.append(voice_count)
        self.polyphony_peak = max(self.polyphony_peak, voice_count)

    def record_engine_load(self, engine_name: str, load_percentage: float):
        """Record engine processing load."""
        self.engine_load[engine_name] = load_percentage

    def get_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            'cpu': {
                'current': self.cpu_usage[-1] if self.cpu_usage else 0,
                'average': np.mean(self.cpu_usage) if self.cpu_usage else 0,
                'peak': max(self.cpu_usage) if self.cpu_usage else 0,
            },
            'memory': {
                'current': self.memory_usage[-1] if self.memory_usage else 0,
                'average': np.mean(self.memory_usage) if self.memory_usage else 0,
                'peak': self.memory_peak,
            },
            'audio': {
                'processing_time_avg': np.mean(self.processing_time) if self.processing_time else 0,
                'processing_time_peak': self.processing_time_peak,
                'xruns': self.xruns,
                'buffer_underruns': self.buffer_underruns,
            },
            'synthesis': {
                'voices_current': self.active_voices[-1] if self.active_voices else 0,
                'voices_average': np.mean(self.active_voices) if self.active_voices else 0,
                'voices_peak': self.polyphony_peak,
                'engine_load': self.engine_load.copy(),
            },
            'system': {
                'load_average': np.mean(self.system_load) if self.system_load else 0,
                'disk_io': np.mean(self.disk_io) if self.disk_io else 0,
            }
        }


class MemoryOptimizer:
    """Memory usage optimization and monitoring."""

    def __init__(self):
        self.object_counts = {}
        self.memory_thresholds = {
            'warning': 0.8,  # 80% memory usage
            'critical': 0.95,  # 95% memory usage
        }
        self.allocation_tracking = {}
        self.garbage_collection_stats = {
            'collections': 0,
            'collected_objects': 0,
            'uncollectable_objects': 0,
        }

    def analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze current memory usage patterns."""
        memory = psutil.virtual_memory()

        # Get object counts by type
        objects = gc.get_objects()
        type_counts = {}
        for obj in objects[:1000]:  # Sample first 1000 objects
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

        # Sort by count
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'memory_info': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percentage': memory.percent,
            },
            'object_types': dict(sorted_types[:20]),  # Top 20 object types
            'gc_stats': self.garbage_collection_stats.copy(),
            'threshold_status': self._check_thresholds(memory.percent),
        }

    def _check_thresholds(self, memory_percent: float) -> str:
        """Check memory usage against thresholds."""
        if memory_percent >= self.memory_thresholds['critical']:
            return 'critical'
        elif memory_percent >= self.memory_thresholds['warning']:
            return 'warning'
        else:
            return 'normal'

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Perform memory optimization operations."""
        results = {
            'gc_collections': 0,
            'freed_memory': 0,
            'before_gc': len(gc.get_objects()),
        }

        # Force garbage collection
        collected = gc.collect()
        results['gc_collections'] = collected
        results['after_gc'] = len(gc.get_objects())

        # Update stats
        self.garbage_collection_stats['collections'] += 1
        self.garbage_collection_stats['collected_objects'] += collected

        return results

    def monitor_allocations(self, enable: bool = True):
        """Enable/disable allocation monitoring."""
        if enable:
            # Enable garbage collection debugging
            gc.set_debug(gc.DEBUG_STATS)
        else:
            gc.set_debug(0)


class CPUOptimizer:
    """CPU usage optimization and threading management."""

    def __init__(self):
        self.thread_pool = []
        self.cpu_affinity = []
        self.realtime_priority = False
        self.thread_priorities = {}

        # Performance targets
        self.target_cpu_usage = 70.0  # Target 70% CPU usage
        self.max_cpu_usage = 90.0     # Maximum allowed CPU usage

    def analyze_cpu_usage(self) -> Dict[str, Any]:
        """Analyze CPU usage patterns."""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_freq = psutil.cpu_freq(percpu=True) if hasattr(psutil, 'cpu_freq') else None

        return {
            'overall_usage': psutil.cpu_percent(),
            'per_core_usage': cpu_percent,
            'cpu_frequency': cpu_freq,
            'core_count': psutil.cpu_count(),
            'logical_cores': psutil.cpu_count(logical=True),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
        }

    def optimize_threading(self) -> Dict[str, Any]:
        """Optimize threading configuration for performance."""
        results = {
            'thread_count': threading.active_count(),
            'active_threads': [t.name for t in threading.enumerate()],
            'optimizations_applied': [],
        }

        # Set thread priorities if possible
        try:
            import os
            if hasattr(os, 'nice'):
                # Lower process priority for better real-time performance
                current_nice = os.nice(0)
                if current_nice > -10:
                    os.nice(-10)
                    results['optimizations_applied'].append('process_priority_adjusted')
        except:
            pass

        # Analyze thread pool
        main_thread = threading.main_thread()
        results['main_thread_priority'] = getattr(main_thread, 'priority', 'unknown')

        return results

    def set_cpu_affinity(self, cpu_cores: List[int]) -> bool:
        """Set CPU affinity for the process."""
        try:
            import os
            if hasattr(os, 'sched_setaffinity'):
                os.sched_setaffinity(0, cpu_cores)
                self.cpu_affinity = cpu_cores
                return True
        except:
            pass
        return False

    def enable_realtime_priority(self, enable: bool = True) -> bool:
        """Enable/disable real-time process priority."""
        try:
            import os
            if hasattr(os, 'sched_setscheduler'):
                if enable:
                    # Set SCHED_RR (round-robin) scheduling
                    os.sched_setscheduler(0, os.SCHED_RR, os.sched_param(50))
                    self.realtime_priority = True
                    return True
                else:
                    # Set SCHED_OTHER (normal scheduling)
                    os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
                    self.realtime_priority = False
                    return True
        except:
            pass
        return False


class BufferOptimizer:
    """Audio buffer management and optimization."""

    def __init__(self):
        self.buffer_pool_stats = {
            'total_buffers': 0,
            'active_buffers': 0,
            'buffer_hits': 0,
            'buffer_misses': 0,
            'memory_usage': 0,
        }

        self.buffer_sizes = {}
        self.latency_measurements = deque(maxlen=1000)

    def analyze_buffer_usage(self) -> Dict[str, Any]:
        """Analyze buffer usage patterns."""
        return {
            'pool_stats': self.buffer_pool_stats.copy(),
            'buffer_sizes': self.buffer_sizes.copy(),
            'latency_stats': {
                'average': np.mean(self.latency_measurements) if self.latency_measurements else 0,
                'peak': max(self.latency_measurements) if self.latency_measurements else 0,
                'jitter': np.std(self.latency_measurements) if self.latency_measurements else 0,
            },
        }

    def optimize_buffer_sizes(self, target_latency: float = 5.0) -> Dict[str, Any]:
        """Optimize buffer sizes for target latency."""
        # Calculate optimal buffer size based on sample rate and target latency
        sample_rate = 44100  # Assume 44.1kHz
        optimal_buffer_size = int((target_latency / 1000.0) * sample_rate)

        # Round to nearest power of 2 for efficiency
        optimal_buffer_size = 2 ** int(np.log2(optimal_buffer_size))

        results = {
            'target_latency_ms': target_latency,
            'optimal_buffer_size': optimal_buffer_size,
            'sample_rate': sample_rate,
            'recommended_block_size': optimal_buffer_size,
        }

        return results

    def monitor_latency(self, latency_ms: float):
        """Monitor audio latency."""
        self.latency_measurements.append(latency_ms)

    def update_buffer_stats(self, total_buffers: int, active_buffers: int,
                           buffer_hits: int, buffer_misses: int, memory_usage: int):
        """Update buffer pool statistics."""
        self.buffer_pool_stats.update({
            'total_buffers': total_buffers,
            'active_buffers': active_buffers,
            'buffer_hits': buffer_hits,
            'buffer_misses': buffer_misses,
            'memory_usage': memory_usage,
        })


class ProfilingTools:
    """Performance profiling and benchmarking tools."""

    def __init__(self):
        self.profiles = {}
        self.benchmarks = {}
        self.active_profiles = set()

    def start_profile(self, profile_name: str):
        """Start profiling a specific operation."""
        if profile_name not in self.active_profiles:
            self.profiles[profile_name] = {
                'start_time': time.time(),
                'samples': [],
                'call_count': 0,
            }
            self.active_profiles.add(profile_name)

    def end_profile(self, profile_name: str) -> Dict[str, Any]:
        """End profiling and return results."""
        if profile_name in self.active_profiles:
            profile = self.profiles[profile_name]
            end_time = time.time()
            duration = end_time - profile['start_time']

            results = {
                'duration': duration,
                'call_count': profile['call_count'],
                'average_time': duration / max(profile['call_count'], 1),
                'samples': len(profile['samples']),
            }

            self.active_profiles.remove(profile_name)
            return results

        return {}

    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile function execution."""
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            self.start_profile(func_name)

            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            # Record sample
            if func_name in self.profiles:
                self.profiles[func_name]['samples'].append(end_time - start_time)
                self.profiles[func_name]['call_count'] += 1

            self.end_profile(func_name)
            return result

        return wrapper

    def benchmark_operation(self, operation_name: str, operation: Callable,
                           iterations: int = 100) -> Dict[str, Any]:
        """Benchmark an operation over multiple iterations."""
        times = []

        for i in range(iterations):
            start_time = time.time()
            operation()
            end_time = time.time()
            times.append(end_time - start_time)

        times_array = np.array(times)

        results = {
            'operation': operation_name,
            'iterations': iterations,
            'total_time': sum(times),
            'average_time': np.mean(times_array),
            'median_time': np.median(times_array),
            'min_time': np.min(times_array),
            'max_time': np.max(times_array),
            'std_dev': np.std(times_array),
            'throughput': iterations / sum(times),
        }

        self.benchmarks[operation_name] = results
        return results


class JupiterXPerformanceOptimizer:
    """
    Jupiter-X Performance Optimization Suite

    Comprehensive real-time performance monitoring, optimization,
    and profiling system for maximum synthesis performance.
    """

    def __init__(self):
        self.lock = threading.RLock()

        # Core optimization components
        self.metrics = PerformanceMetrics()
        self.memory_optimizer = MemoryOptimizer()
        self.cpu_optimizer = CPUOptimizer()
        self.buffer_optimizer = BufferOptimizer()
        self.profiling_tools = ProfilingTools()

        # Optimization settings
        self.auto_optimize = True
        self.optimization_interval = 30.0  # 30 seconds
        self.last_optimization = time.time()

        # Performance targets
        self.targets = {
            'max_cpu_usage': 80.0,
            'max_memory_usage': 90.0,
            'max_latency_ms': 10.0,
            'target_buffer_size': 1024,
        }

        # Optimization history
        self.optimization_history = deque(maxlen=100)

        print("⚡ Jupiter-X Performance Optimizer: Initialized with real-time monitoring")

    def update_metrics(self):
        """Update all performance metrics."""
        with self.lock:
            self.metrics.update()

            # Auto-optimization
            if self.auto_optimize:
                current_time = time.time()
                if current_time - self.last_optimization >= self.optimization_interval:
                    self.perform_auto_optimization()
                    self.last_optimization = current_time

    def record_audio_processing(self, processing_time_ms: float, active_voices: int):
        """Record audio processing metrics."""
        with self.lock:
            self.metrics.record_processing_time(processing_time_ms)
            self.metrics.record_voice_count(active_voices)

    def record_engine_load(self, engine_name: str, load_percentage: float):
        """Record engine processing load."""
        with self.lock:
            self.metrics.record_engine_load(engine_name, load_percentage)

    def perform_auto_optimization(self) -> Dict[str, Any]:
        """Perform automatic optimization based on current metrics."""
        with self.lock:
            optimizations_applied = []
            results = {}

            # Check CPU usage
            cpu_summary = self.metrics.get_summary()['cpu']
            if cpu_summary['current'] > self.targets['max_cpu_usage']:
                cpu_results = self.cpu_optimizer.optimize_threading()
                optimizations_applied.append('cpu_threading')
                results['cpu_optimization'] = cpu_results

            # Check memory usage
            memory_summary = self.metrics.get_summary()['memory']
            if memory_summary['current'] > self.targets['max_memory_usage']:
                memory_results = self.memory_optimizer.optimize_memory_usage()
                optimizations_applied.append('memory_gc')
                results['memory_optimization'] = memory_results

            # Check audio latency
            audio_summary = self.metrics.get_summary()['audio']
            if audio_summary['processing_time_avg'] > self.targets['max_latency_ms']:
                buffer_results = self.buffer_optimizer.optimize_buffer_sizes()
                optimizations_applied.append('buffer_optimization')
                results['buffer_optimization'] = buffer_results

            # Record optimization
            optimization_record = {
                'timestamp': time.time(),
                'optimizations_applied': optimizations_applied,
                'results': results,
                'pre_optimization_metrics': self.metrics.get_summary(),
            }

            self.optimization_history.append(optimization_record)

            return {
                'optimizations_applied': optimizations_applied,
                'results': results,
                'success': len(optimizations_applied) > 0,
            }

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        with self.lock:
            return {
                'current_metrics': self.metrics.get_summary(),
                'memory_analysis': self.memory_optimizer.analyze_memory_usage(),
                'cpu_analysis': self.cpu_optimizer.analyze_cpu_usage(),
                'buffer_analysis': self.buffer_optimizer.analyze_buffer_usage(),
                'optimization_history': list(self.optimization_history)[-5:],  # Last 5 optimizations
                'targets': self.targets.copy(),
                'system_info': {
                    'python_version': sys.version,
                    'platform': sys.platform,
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                },
            }

    def benchmark_synthesis_engine(self, engine_name: str, engine_instance,
                                 note: int = 60, velocity: int = 100,
                                 duration_blocks: int = 100) -> Dict[str, Any]:
        """Benchmark synthesis engine performance."""
        def benchmark_operation():
            # Generate audio for one block
            modulation = {}
            block_size = 1024
            engine_instance.generate_samples(note, velocity, modulation, block_size)

        return self.profiling_tools.benchmark_operation(
            f"{engine_name}_synthesis", benchmark_operation, duration_blocks
        )

    def optimize_for_realtime(self) -> Dict[str, Any]:
        """Apply all optimizations for real-time performance."""
        with self.lock:
            results = {
                'optimizations_applied': [],
                'results': {},
            }

            # CPU optimizations
            cpu_results = self.cpu_optimizer.optimize_threading()
            if cpu_results['thread_count'] > 1:
                results['optimizations_applied'].append('cpu_optimization')
                results['results']['cpu'] = cpu_results

            # Memory optimizations
            memory_results = self.memory_optimizer.optimize_memory_usage()
            results['optimizations_applied'].append('memory_optimization')
            results['results']['memory'] = memory_results

            # Buffer optimizations
            buffer_results = self.buffer_optimizer.optimize_buffer_sizes()
            results['optimizations_applied'].append('buffer_optimization')
            results['results']['buffer'] = buffer_results

            # Enable real-time priority if possible
            if self.cpu_optimizer.enable_realtime_priority():
                results['optimizations_applied'].append('realtime_priority')

            return results

    def set_performance_targets(self, max_cpu: float = None, max_memory: float = None,
                              max_latency: float = None, buffer_size: int = None):
        """Set performance optimization targets."""
        with self.lock:
            if max_cpu is not None:
                self.targets['max_cpu_usage'] = max_cpu
            if max_memory is not None:
                self.targets['max_memory_usage'] = max_memory
            if max_latency is not None:
                self.targets['max_latency_ms'] = max_latency
            if buffer_size is not None:
                self.targets['target_buffer_size'] = buffer_size

    def export_performance_data(self, filename: str) -> bool:
        """Export performance data for analysis."""
        try:
            data = {
                'performance_report': self.get_performance_report(),
                'optimization_history': list(self.optimization_history),
                'benchmarks': self.profiling_tools.benchmarks,
                'profiles': self.profiling_tools.profiles,
                'targets': self.targets,
            }

            import json
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True
        except Exception as e:
            print(f"Performance data export error: {e}")
            return False

    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current metrics."""
        recommendations = []
        metrics = self.metrics.get_summary()

        # CPU recommendations
        if metrics['cpu']['current'] > 85:
            recommendations.append("High CPU usage detected. Consider reducing polyphony or using CPU optimization.")
        elif metrics['cpu']['current'] > 70:
            recommendations.append("Moderate CPU usage. Monitor for xruns during complex passages.")

        # Memory recommendations
        if metrics['memory']['current'] > 85:
            recommendations.append("High memory usage. Consider reducing sample library size or enabling memory optimization.")
        elif metrics['memory']['current'] > 70:
            recommendations.append("Moderate memory usage. Monitor garbage collection frequency.")

        # Audio recommendations
        if metrics['audio']['xruns'] > 0:
            recommendations.append(f"Audio xruns detected ({metrics['audio']['xruns']}). Reduce buffer size or system load.")
        if metrics['audio']['processing_time_avg'] > 5.0:
            recommendations.append("High audio processing latency. Consider buffer optimization or system tuning.")

        # Synthesis recommendations
        if metrics['synthesis']['voices_peak'] > 32:
            recommendations.append("High polyphony detected. Consider voice management optimization.")

        if not recommendations:
            recommendations.append("System performance is optimal. No optimizations needed.")

        return recommendations


# Export the performance optimizer
__all__ = ['JupiterXPerformanceOptimizer', 'PerformanceMetrics', 'MemoryOptimizer',
           'CPUOptimizer', 'BufferOptimizer', 'ProfilingTools']
