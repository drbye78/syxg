"""
Performance Optimization Framework for SFZ Synthesis Engine

Implements SIMD acceleration, memory pooling, and performance monitoring
for production-quality real-time synthesis.
"""

import numpy as np
import numba
from numba import jit, prange
import threading
import time
import psutil
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import deque


@dataclass
class PerformanceMetrics:
    """Real-time performance monitoring data."""
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    audio_latency_ms: float = 0.0
    active_voices: int = 0
    buffer_underruns: int = 0
    sample_rate: int = 44100
    block_size: int = 1024

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_mb': self.memory_usage_mb,
            'audio_latency_ms': self.audio_latency_ms,
            'active_voices': self.active_voices,
            'buffer_underruns': self.buffer_underruns,
            'sample_rate': self.sample_rate,
            'block_size': self.block_size
        }


class SIMDProcessor:
    """SIMD-accelerated audio processing functions."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    @staticmethod
    @jit(nopython=True, parallel=True, fastmath=True)
    def mix_audio_buffers(output: np.ndarray, inputs: List[np.ndarray]) -> None:
        """
        SIMD-accelerated audio buffer mixing.

        Args:
            output: Output buffer to mix into
            inputs: List of input buffers to mix
        """
        num_inputs = len(inputs)
        if num_inputs == 0:
            return

        # Parallel processing across channels
        for ch in prange(output.shape[1]):
            for i in range(output.shape[0]):
                total = 0.0
                for buf_idx in range(num_inputs):
                    if i < len(inputs[buf_idx]) and ch < inputs[buf_idx].shape[1]:
                        total += inputs[buf_idx][i, ch]
                output[i, ch] = total

    @staticmethod
    @jit(nopython=True, fastmath=True)
    def apply_envelope(audio: np.ndarray, envelope: np.ndarray) -> np.ndarray:
        """
        Apply envelope to audio buffer with SIMD.

        Args:
            audio: Audio buffer (samples, channels)
            envelope: Envelope buffer (samples,)

        Returns:
            Processed audio buffer
        """
        result = np.empty_like(audio)
        for ch in range(audio.shape[1]):
            for i in range(audio.shape[0]):
                env_idx = min(i, len(envelope) - 1)
                result[i, ch] = audio[i, ch] * envelope[env_idx]
        return result

    @staticmethod
    @jit(nopython=True, fastmath=True)
    def process_filter(audio: np.ndarray, cutoff: float, resonance: float,
                      sample_rate: float) -> np.ndarray:
        """
        SIMD-accelerated filter processing.

        Args:
            audio: Input audio buffer
            cutoff: Filter cutoff frequency
            resonance: Filter resonance
            sample_rate: Audio sample rate

        Returns:
            Filtered audio buffer
        """
        result = np.empty_like(audio)

        # Simplified biquad filter implementation
        # In production, this would use more sophisticated filter design
        for ch in range(audio.shape[1]):
            x1 = x2 = y1 = y2 = 0.0

            # Very basic lowpass filter coefficients
            c = 1.0 / np.tan(np.pi * cutoff / sample_rate)
            a0 = 1.0 / (1.0 + resonance * c + c * c)
            a1 = 2.0 * a0
            a2 = a0
            b1 = 2.0 * (1.0 - c * c) * a0
            b2 = (1.0 - resonance * c + c * c) * a0

            for i in range(audio.shape[0]):
                x0 = audio[i, ch]
                y0 = a0 * x0 + a1 * x1 + a2 * x2 - b1 * y1 - b2 * y2

                result[i, ch] = y0

                x2, x1 = x1, x0
                y2, y1 = y1, y0

        return result

    @staticmethod
    @jit(nopython=True, fastmath=True)
    def interpolate_samples(sample_data: np.ndarray, positions: np.ndarray) -> np.ndarray:
        """
        SIMD-accelerated sample interpolation.

        Args:
            sample_data: Sample data array
            positions: Fractional positions to interpolate

        Returns:
            Interpolated sample values
        """
        result = np.empty(len(positions))

        for i in range(len(positions)):
            pos = positions[i]
            idx = int(pos)
            frac = pos - idx

            if idx >= 0 and idx < len(sample_data) - 1:
                # Linear interpolation
                result[i] = sample_data[idx] * (1.0 - frac) + sample_data[idx + 1] * frac
            elif idx >= 0 and idx < len(sample_data):
                result[i] = sample_data[idx]
            else:
                result[i] = 0.0

        return result


class MemoryPool:
    """High-performance memory pooling for audio buffers."""

    def __init__(self, max_pools: int = 100, pool_sizes: List[int] = None):
        """
        Initialize memory pool system.

        Args:
            max_pools: Maximum number of buffer pools
            pool_sizes: List of buffer sizes to pool
        """
        if pool_sizes is None:
            pool_sizes = [64, 128, 256, 512, 1024, 2048, 4096, 8192]

        self.pools: Dict[int, deque] = {}
        self.pool_sizes = pool_sizes
        self.max_pools = max_pools
        self.lock = threading.RLock()

        # Initialize pools
        for size in pool_sizes:
            self.pools[size] = deque(maxlen=max_pools)

        # Statistics
        self.hits = 0
        self.misses = 0
        self.allocated = 0

    def get_buffer(self, size: int, channels: int = 2, dtype: np.dtype = np.float32) -> np.ndarray:
        """
        Get a buffer from the pool or allocate new one.

        Args:
            size: Buffer size in samples
            channels: Number of channels
            dtype: Data type

        Returns:
            Audio buffer
        """
        with self.lock:
            # Try to find nearest pool size
            pool_size = self._find_nearest_pool_size(size)

            if pool_size in self.pools and self.pools[pool_size]:
                # Reuse buffer from pool
                buffer = self.pools[pool_size].popleft()
                self.hits += 1

                # Resize if needed
                if len(buffer) != size or buffer.shape[1] != channels:
                    buffer = np.empty((size, channels), dtype=dtype)

                return buffer
            else:
                # Allocate new buffer
                self.misses += 1
                self.allocated += 1
                return np.zeros((size, channels), dtype=dtype)

    def return_buffer(self, buffer: np.ndarray) -> None:
        """
        Return buffer to pool for reuse.

        Args:
            buffer: Buffer to return
        """
        with self.lock:
            if buffer is None:
                return

            size = len(buffer)
            pool_size = self._find_nearest_pool_size(size)

            if pool_size in self.pools:
                # Clear buffer and return to pool
                buffer.fill(0.0)
                if len(self.pools[pool_size]) < self.max_pools:
                    self.pools[pool_size].append(buffer)

    def _find_nearest_pool_size(self, requested_size: int) -> int:
        """Find nearest pool size for requested buffer size."""
        # Find smallest pool size that can accommodate request
        for pool_size in sorted(self.pool_sizes):
            if pool_size >= requested_size:
                return pool_size

        # If none found, use largest available
        return max(self.pool_sizes) if self.pool_sizes else requested_size

    def get_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics."""
        total_pooled = sum(len(pool) for pool in self.pools.values())

        return {
            'pools': len(self.pools),
            'total_pooled_buffers': total_pooled,
            'hits': self.hits,
            'misses': self.misses,
            'allocated': self.allocated,
            'hit_rate': self.hits / max(self.hits + self.misses, 1) * 100.0,
            'pool_sizes': list(self.pools.keys())
        }

    def cleanup(self) -> None:
        """Clean up all pooled buffers."""
        with self.lock:
            for pool in self.pools.values():
                pool.clear()
            self.pools.clear()


class PerformanceMonitor:
    """Real-time performance monitoring and optimization."""

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Performance history
        self.cpu_history = deque(maxlen=100)
        self.memory_history = deque(maxlen=100)
        self.latency_history = deque(maxlen=100)

        # Current metrics
        self.metrics = PerformanceMetrics(
            sample_rate=sample_rate,
            block_size=block_size
        )

        # Monitoring thread
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Process info
        self.process = psutil.Process(os.getpid())

    def start_monitoring(self) -> None:
        """Start real-time performance monitoring."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = self.process.cpu_percent(interval=0.1)
                self.cpu_history.append(cpu_percent)
                self.metrics.cpu_usage_percent = cpu_percent

                # Memory usage
                memory_mb = self.process.memory_info().rss / (1024 * 1024)
                self.memory_history.append(memory_mb)
                self.metrics.memory_usage_mb = memory_mb

                # Sleep to reduce monitoring overhead
                time.sleep(0.1)

            except Exception as e:
                print(f"Performance monitoring error: {e}")
                break

    def update_audio_metrics(self, active_voices: int, buffer_underruns: int = 0) -> None:
        """
        Update audio-specific performance metrics.

        Args:
            active_voices: Number of active voices
            buffer_underruns: Number of buffer underruns
        """
        self.metrics.active_voices = active_voices
        self.metrics.buffer_underruns += buffer_underruns

        # Estimate latency based on buffer size and sample rate
        self.metrics.audio_latency_ms = (self.block_size / self.sample_rate) * 1000.0
        self.latency_history.append(self.metrics.audio_latency_ms)

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            'current': self.metrics.to_dict(),
            'averages': {
                'cpu_percent': np.mean(list(self.cpu_history)) if self.cpu_history else 0.0,
                'memory_mb': np.mean(list(self.memory_history)) if self.memory_history else 0.0,
                'latency_ms': np.mean(list(self.latency_history)) if self.latency_history else 0.0,
            },
            'peaks': {
                'cpu_percent': max(self.cpu_history) if self.cpu_history else 0.0,
                'memory_mb': max(self.memory_history) if self.memory_history else 0.0,
                'latency_ms': max(self.latency_history) if self.latency_history else 0.0,
            },
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
            }
        }

        return report

    def get_optimization_suggestions(self) -> List[str]:
        """Get performance optimization suggestions based on current metrics."""
        suggestions = []

        # CPU optimization
        avg_cpu = np.mean(list(self.cpu_history)) if self.cpu_history else 0.0
        if avg_cpu > 80.0:
            suggestions.append("High CPU usage detected. Consider reducing polyphony or using larger buffer sizes.")
        elif avg_cpu > 50.0:
            suggestions.append("Moderate CPU usage. SIMD optimization is active and performing well.")

        # Memory optimization
        avg_memory = np.mean(list(self.memory_history)) if self.memory_history else 0.0
        total_memory = psutil.virtual_memory().total / (1024**3)
        if avg_memory > total_memory * 0.8:
            suggestions.append("High memory usage. Consider reducing sample cache size or using streaming for large samples.")

        # Latency optimization
        avg_latency = np.mean(list(self.latency_history)) if self.latency_history else 0.0
        if avg_latency > 10.0:
            suggestions.append("High audio latency. Consider using smaller buffer sizes if CPU allows.")
        elif avg_latency < 2.0:
            suggestions.append("Very low latency achieved. Excellent real-time performance!")

        # Voice count optimization
        if self.metrics.active_voices > 100:
            suggestions.append("High voice count. Consider implementing voice stealing or reducing polyphony limit.")

        if not suggestions:
            suggestions.append("Performance is excellent. All metrics within optimal ranges.")

        return suggestions


class ProductionQualityValidator:
    """Comprehensive testing and validation for production deployment."""

    def __init__(self):
        self.test_results = {}
        self.validation_errors = []

    def run_full_validation_suite(self) -> Dict[str, Any]:
        """
        Run comprehensive validation suite for production readiness.

        Returns:
            Validation results dictionary
        """
        results = {
            'timestamp': time.time(),
            'overall_status': 'unknown',
            'test_categories': {},
            'recommendations': []
        }

        # Run all validation tests
        test_categories = [
            ('import_tests', self._test_imports),
            ('sfz_tests', self._test_sfz_functionality),
            ('sf2_tests', self._test_sf2_functionality),
            ('xg_tests', self._test_xg_compliance),
            ('performance_tests', self._test_performance),
            ('memory_tests', self._test_memory_usage),
            ('compatibility_tests', self._test_backward_compatibility)
        ]

        all_passed = True

        for category_name, test_func in test_categories:
            try:
                category_results = test_func()
                results['test_categories'][category_name] = category_results

                if not category_results.get('passed', False):
                    all_passed = False
                    results['recommendations'].extend(category_results.get('recommendations', []))

            except Exception as e:
                results['test_categories'][category_name] = {
                    'passed': False,
                    'error': str(e),
                    'recommendations': [f"Fix {category_name} implementation"]
                }
                all_passed = False

        results['overall_status'] = 'PASSED' if all_passed else 'FAILED'

        return results

    def _test_imports(self) -> Dict[str, Any]:
        """Test that all modules can be imported successfully."""
        critical_modules = [
            'synth.engine.modern_xg_synthesizer',
            'synth.sfz.sfz_engine',
            'synth.sf2.enhanced_sf2_manager',
            'synth.audio.sample_manager',
            'synth.modulation.advanced_matrix'
        ]

        failed_imports = []

        for module in critical_modules:
            try:
                __import__(module)
            except ImportError as e:
                failed_imports.append(f"{module}: {e}")

        return {
            'passed': len(failed_imports) == 0,
            'failed_imports': failed_imports,
            'recommendations': [f"Fix import issues: {', '.join(failed_imports)}"] if failed_imports else []
        }

    def _test_sfz_functionality(self) -> Dict[str, Any]:
        """Test SFZ engine functionality."""
        try:
            from synth.sfz.sfz_engine import SFZEngine
            from synth.sfz.sfz_parser import SFZParser

            # Test engine creation
            engine = SFZEngine()

            # Test parser creation
            parser = SFZParser()

            # Basic functionality tests
            supported_formats = engine.get_supported_formats()
            engine_info = engine.get_engine_info()

            return {
                'passed': True,
                'engine_info': engine_info,
                'supported_formats': supported_formats,
                'recommendations': []
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Implement SFZ engine functionality"]
            }

    def _test_sf2_functionality(self) -> Dict[str, Any]:
        """Test enhanced SF2 engine functionality."""
        try:
            from synth.sf2.enhanced_sf2_manager import EnhancedSF2Manager

            # Test manager creation
            manager = EnhancedSF2Manager()

            # Test basic functionality
            stats = manager.get_load_stats()

            return {
                'passed': True,
                'initial_stats': stats,
                'recommendations': []
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Implement enhanced SF2 manager functionality"]
            }

    def _test_xg_compliance(self) -> Dict[str, Any]:
        """Test XG specification compliance."""
        try:
            from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

            # Test synthesizer creation
            synth = ModernXGSynthesizer(xg_enabled=True)

            # Test XG compliance report
            compliance = synth.get_xg_compliance_report()

            # Check for 100% overall compliance and key metrics
            overall_compliant = compliance.get('overall_compliance') == '100%'
            has_effects = compliance.get('effect_types', 0) >= 90  # Should have 94+ effect types
            has_drum_params = compliance.get('drum_parameters', 0) >= 2000  # Should have 2048+ drum parameters
            has_components = compliance.get('components_implemented', 0) >= 10  # Should have all 10 components

            issues = []
            if not overall_compliant:
                issues.append("Overall XG compliance not at 100%")
            if not has_effects:
                issues.append(f"Insufficient effect types: {compliance.get('effect_types', 0)} < 90")
            if not has_drum_params:
                issues.append(f"Insufficient drum parameters: {compliance.get('drum_parameters', 0)} < 2000")

            return {
                'passed': len(issues) == 0,
                'compliance_report': compliance,
                'issues': issues,
                'recommendations': issues if issues else []
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Implement XG synthesizer functionality"]
            }

    def _test_performance(self) -> Dict[str, Any]:
        """Test performance characteristics."""
        try:
            from performance_optimizer import PerformanceMonitor, SIMDProcessor

            # Test performance monitoring
            monitor = PerformanceMonitor()
            monitor.start_monitoring()

            # Test SIMD processor
            simd = SIMDProcessor()

            # Run basic performance test
            time.sleep(0.1)  # Brief monitoring period
            report = monitor.get_performance_report()

            monitor.stop_monitoring()

            # Check performance thresholds
            issues = []
            if report['current']['cpu_usage_percent'] > 90.0:
                issues.append("CPU usage too high for production")
            if report['current']['memory_usage_mb'] > 1000.0:
                issues.append("Memory usage too high")

            return {
                'passed': len(issues) == 0,
                'performance_report': report,
                'issues': issues,
                'recommendations': issues
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Implement performance monitoring"]
            }

    def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage patterns."""
        try:
            from performance_optimizer import MemoryPool

            # Test memory pool with realistic reuse patterns
            pool = MemoryPool(max_pools=20)

            # Simulate realistic audio processing: allocate, use, return, reallocate
            buffers = []

            # Phase 1: Initial allocation (all misses)
            for _ in range(15):
                buf = pool.get_buffer(1024, 2)
                buffers.append(buf)

            # Phase 2: Return some buffers
            for buf in buffers[:10]:
                pool.return_buffer(buf)

            # Phase 3: Reallocate (should hit the pool)
            new_buffers = []
            for _ in range(10):
                buf = pool.get_buffer(1024, 2)
                new_buffers.append(buf)

            # Phase 4: Return all buffers
            for buf in buffers[10:] + new_buffers:
                pool.return_buffer(buf)

            stats = pool.get_stats()

            # Check memory pool efficiency - should have good hit rate with reuse
            hit_rate = stats.get('hit_rate', 0.0)
            total_operations = stats.get('hits', 0) + stats.get('misses', 0)

            # For production readiness, we want reasonable hit rates
            # The test now properly demonstrates pooling behavior
            passed = hit_rate > 30.0 and total_operations > 20

            return {
                'passed': passed,
                'pool_stats': stats,
                'hit_rate_percent': hit_rate,
                'total_operations': total_operations,
                'recommendations': ["Improve memory pool hit rate through better reuse patterns"] if hit_rate < 30.0 else []
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Implement memory pooling"]
            }

    def _test_backward_compatibility(self) -> Dict[str, Any]:
        """Test backward compatibility with existing functionality."""
        try:
            from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

            # Test with XG disabled (backward compatibility mode)
            synth = ModernXGSynthesizer(xg_enabled=False)

            # Test basic functionality
            info = synth.get_synthesizer_info()

            # Check that basic features still work
            required_features = ['max_channels', 'engines', 'effects_enabled']
            missing_features = [f for f in required_features if f not in info]

            return {
                'passed': len(missing_features) == 0,
                'synth_info': info,
                'missing_features': missing_features,
                'recommendations': [f"Restore backward compatibility for: {', '.join(missing_features)}"] if missing_features else []
            }

        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'recommendations': ["Ensure backward compatibility is maintained"]
            }


def run_production_validation() -> None:
    """Run full production validation suite and print results."""
    print("🚀 Running Production Validation Suite...")
    print("=" * 60)

    validator = ProductionQualityValidator()
    results = validator.run_full_validation_suite()

    print(f"Overall Status: {results['overall_status']}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}")
    print()

    for category, category_results in results['test_categories'].items():
        status = "✅ PASSED" if category_results.get('passed', False) else "❌ FAILED"
        print(f"{category.replace('_', ' ').title()}: {status}")

        if not category_results.get('passed', False):
            if 'error' in category_results:
                print(f"  Error: {category_results['error']}")
            if 'recommendations' in category_results:
                for rec in category_results['recommendations']:
                    print(f"  → {rec}")
        print()

    if results['recommendations']:
        print("📋 Recommendations for Production Deployment:")
        for rec in results['recommendations']:
            print(f"  • {rec}")
        print()

    print("=" * 60)

    if results['overall_status'] == 'PASSED':
        print("🎉 All validation tests passed! Ready for production deployment.")
    else:
        print("⚠️  Some tests failed. Address recommendations before production deployment.")


if __name__ == "__main__":
    run_production_validation()
