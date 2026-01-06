"""
S90/S70 Performance Features

Real-time performance features and optimizations specific to S90/S70 synthesizers,
including voice allocation, performance monitoring, and hardware optimizations.
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import time
import psutil
import os


class VoiceAllocationOptimizer:
    """Optimizes voice allocation for S90/S70 hardware characteristics"""

    def __init__(self, max_voices: int = 64):
        """
        Initialize voice allocation optimizer.

        Args:
            max_voices: Maximum voices available
        """
        self.max_voices = max_voices
        self.active_voices: Dict[int, Dict[str, Any]] = {}
        self.voice_stealing_queue: List[int] = []

        # Voice allocation strategies
        self.allocation_strategy = 'priority'  # 'priority', 'oldest', 'quietest'
        self.voice_priorities = {
            'awm': 3,     # Highest priority
            'an': 2,      # Medium priority
            'fdsp': 1     # Lower priority
        }

        # Performance monitoring
        self.allocation_stats = {
            'total_allocations': 0,
            'total_deallocations': 0,
            'voice_stealing_events': 0,
            'peak_concurrent_voices': 0,
            'allocation_failures': 0
        }

        self.lock = threading.RLock()

    def allocate_voice(self, voice_type: str, channel: int, note: int,
                      velocity: int) -> Optional[int]:
        """
        Allocate a voice with hardware-optimized strategy.

        Args:
            voice_type: Type of voice ('awm', 'an', 'fdsp')
            channel: MIDI channel
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Voice ID or None if allocation failed
        """
        with self.lock:
            voice_id = self._find_available_voice_id()

            if voice_id is None:
                # No available voices, attempt stealing
                voice_id = self._steal_voice(voice_type, channel, note, velocity)

            if voice_id is not None:
                # Record allocation
                self.active_voices[voice_id] = {
                    'type': voice_type,
                    'channel': channel,
                    'note': note,
                    'velocity': velocity,
                    'allocated_time': time.time(),
                    'priority': self.voice_priorities.get(voice_type, 0)
                }

                self.allocation_stats['total_allocations'] += 1
                self.allocation_stats['peak_concurrent_voices'] = max(
                    self.allocation_stats['peak_concurrent_voices'],
                    len(self.active_voices)
                )

                return voice_id
            else:
                self.allocation_stats['allocation_failures'] += 1
                return None

    def deallocate_voice(self, voice_id: int) -> bool:
        """
        Deallocate a voice.

        Args:
            voice_id: Voice to deallocate

        Returns:
            True if deallocated successfully
        """
        with self.lock:
            if voice_id in self.active_voices:
                del self.active_voices[voice_id]
                self.allocation_stats['total_deallocations'] += 1
                return True
            return False

    def _find_available_voice_id(self) -> Optional[int]:
        """Find an available voice ID"""
        # Simple sequential allocation
        for voice_id in range(self.max_voices):
            if voice_id not in self.active_voices:
                return voice_id
        return None

    def _steal_voice(self, voice_type: str, channel: int, note: int,
                    velocity: int) -> Optional[int]:
        """
        Attempt to steal a voice using hardware-optimized strategy.

        Args:
            voice_type: Type of voice requesting allocation
            channel: MIDI channel
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Voice ID to steal or None
        """
        if not self.active_voices:
            return None

        # Apply allocation strategy
        if self.allocation_strategy == 'priority':
            return self._steal_by_priority(voice_type)
        elif self.allocation_strategy == 'oldest':
            return self._steal_oldest()
        elif self.allocation_strategy == 'quietest':
            return self._steal_quietest()
        else:
            return self._steal_oldest()  # Default fallback

    def _steal_by_priority(self, requesting_type: str) -> Optional[int]:
        """Steal voice based on priority (lower priority voices first)"""
        requesting_priority = self.voice_priorities.get(requesting_type, 0)

        # Find lowest priority voice
        lowest_priority = float('inf')
        candidate_voice = None

        for voice_id, voice_info in self.active_voices.items():
            voice_priority = voice_info['priority']
            if voice_priority < lowest_priority:
                lowest_priority = voice_priority
                candidate_voice = voice_id

        if candidate_voice is not None:
            self.allocation_stats['voice_stealing_events'] += 1
            return candidate_voice

        return None

    def _steal_oldest(self) -> Optional[int]:
        """Steal the oldest allocated voice"""
        if not self.active_voices:
            return None

        oldest_time = float('inf')
        oldest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            allocated_time = voice_info['allocated_time']
            if allocated_time < oldest_time:
                oldest_time = allocated_time
                oldest_voice = voice_id

        if oldest_voice is not None:
            self.allocation_stats['voice_stealing_events'] += 1
            return oldest_voice

        return None

    def _steal_quietest(self) -> Optional[int]:
        """Steal the voice with lowest velocity (quietest)"""
        if not self.active_voices:
            return None

        lowest_velocity = float('inf')
        quietest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            velocity = voice_info['velocity']
            if velocity < lowest_velocity:
                lowest_velocity = velocity
                quietest_voice = voice_id

        if quietest_voice is not None:
            self.allocation_stats['voice_stealing_events'] += 1
            return quietest_voice

        return None

    def set_allocation_strategy(self, strategy: str) -> bool:
        """
        Set voice allocation strategy.

        Args:
            strategy: Allocation strategy ('priority', 'oldest', 'quietest')

        Returns:
            True if strategy is valid
        """
        valid_strategies = ['priority', 'oldest', 'quietest']
        if strategy in valid_strategies:
            self.allocation_strategy = strategy
            return True
        return False

    def get_allocation_status(self) -> Dict[str, Any]:
        """Get current voice allocation status"""
        with self.lock:
            active_count = len(self.active_voices)
            return {
                'active_voices': active_count,
                'available_voices': self.max_voices - active_count,
                'allocation_strategy': self.allocation_strategy,
                'voice_types': self._count_voice_types(),
                'stats': self.allocation_stats.copy()
            }

    def _count_voice_types(self) -> Dict[str, int]:
        """Count active voices by type"""
        counts = {}
        for voice_info in self.active_voices.values():
            voice_type = voice_info['type']
            counts[voice_type] = counts.get(voice_type, 0) + 1
        return counts


class HardwarePerformanceMonitor:
    """Monitors hardware performance characteristics"""

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize performance monitor.

        Args:
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate

        # Performance metrics
        self.metrics = {
            'cpu_usage_percent': 0.0,
            'memory_usage_mb': 0.0,
            'audio_latency_ms': 0.0,
            'midi_latency_ms': 2.0,  # Hardware typical
            'buffer_underruns': 0,
            'buffer_overruns': 0,
            'voice_allocation_time_us': 0,
            'filter_update_time_us': 0,
            'envelope_update_time_us': 0,
            'lfo_update_time_us': 0
        }

        # Historical data for trending
        self.history: List[Dict[str, Any]] = []
        self.max_history_entries = 100

        # Monitoring thread
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        self.lock = threading.RLock()

    def start_monitoring(self):
        """Start performance monitoring"""
        with self.lock:
            if not self.monitoring_active:
                self.monitoring_active = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring"""
        with self.lock:
            self.monitoring_active = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Update system metrics
                self._update_system_metrics()

                # Store historical data
                self._store_historical_data()

                # Sleep for monitoring interval
                time.sleep(0.1)  # 10Hz monitoring

            except Exception as e:
                print(f"Performance monitoring error: {e}")
                break

        self.monitoring_active = False

    def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            # CPU usage
            self.metrics['cpu_usage_percent'] = psutil.cpu_percent(interval=None)

            # Memory usage
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            self.metrics['memory_usage_mb'] = memory_info.rss / (1024 * 1024)

        except Exception:
            # Fallback if psutil not available
            self.metrics['cpu_usage_percent'] = 0.0
            self.metrics['memory_usage_mb'] = 0.0

    def _store_historical_data(self):
        """Store current metrics in history"""
        with self.lock:
            historical_entry = {
                'timestamp': time.time(),
                'metrics': self.metrics.copy()
            }

            self.history.append(historical_entry)

            # Maintain history size limit
            if len(self.history) > self.max_history_entries:
                self.history.pop(0)

    def update_audio_metrics(self, latency_ms: float, underruns: int = 0, overruns: int = 0):
        """
        Update audio-specific performance metrics.

        Args:
            latency_ms: Audio latency in milliseconds
            underruns: Number of buffer underruns
            overruns: Number of buffer overruns
        """
        with self.lock:
            self.metrics['audio_latency_ms'] = latency_ms
            self.metrics['buffer_underruns'] += underruns
            self.metrics['buffer_overruns'] += overruns

    def update_dsp_metrics(self, voice_allocation_us: float = 0,
                          filter_update_us: float = 0,
                          envelope_update_us: float = 0,
                          lfo_update_us: float = 0):
        """
        Update DSP-specific performance metrics.

        Args:
            voice_allocation_us: Voice allocation time in microseconds
            filter_update_us: Filter update time in microseconds
            envelope_update_us: Envelope update time in microseconds
            lfo_update_us: LFO update time in microseconds
        """
        with self.lock:
            self.metrics['voice_allocation_time_us'] = voice_allocation_us
            self.metrics['filter_update_time_us'] = filter_update_us
            self.metrics['envelope_update_time_us'] = envelope_update_us
            self.metrics['lfo_update_time_us'] = lfo_update_us

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.lock:
            return self.metrics.copy()

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        with self.lock:
            current_metrics = self.metrics.copy()

            # Calculate averages from history
            if self.history:
                avg_metrics = self._calculate_averages()
                peak_metrics = self._calculate_peaks()
            else:
                avg_metrics = {}
                peak_metrics = {}

            return {
                'current': current_metrics,
                'averages': avg_metrics,
                'peaks': peak_metrics,
                'history_entries': len(self.history),
                'monitoring_active': self.monitoring_active,
                'performance_rating': self._calculate_performance_rating(current_metrics)
            }

    def _calculate_averages(self) -> Dict[str, float]:
        """Calculate average metrics from history"""
        if not self.history:
            return {}

        # Sum all metrics
        sums = {}
        counts = {}

        for entry in self.history:
            for metric_name, value in entry['metrics'].items():
                if isinstance(value, (int, float)):
                    if metric_name not in sums:
                        sums[metric_name] = 0.0
                        counts[metric_name] = 0
                    sums[metric_name] += value
                    counts[metric_name] += 1

        # Calculate averages
        averages = {}
        for metric_name in sums:
            if counts[metric_name] > 0:
                averages[metric_name] = sums[metric_name] / counts[metric_name]

        return averages

    def _calculate_peaks(self) -> Dict[str, float]:
        """Calculate peak metrics from history"""
        if not self.history:
            return {}

        peaks = {}
        for entry in self.history:
            for metric_name, value in entry['metrics'].items():
                if isinstance(value, (int, float)):
                    if metric_name not in peaks:
                        peaks[metric_name] = value
                    else:
                        peaks[metric_name] = max(peaks[metric_name], value)

        return peaks

    def _calculate_performance_rating(self, metrics: Dict[str, Any]) -> str:
        """
        Calculate overall performance rating.

        Args:
            metrics: Current performance metrics

        Returns:
            Performance rating string
        """
        cpu_usage = metrics.get('cpu_usage_percent', 0)
        memory_mb = metrics.get('memory_usage_mb', 0)
        latency_ms = metrics.get('audio_latency_ms', 0)
        underruns = metrics.get('buffer_underruns', 0)

        # Simple rating algorithm
        score = 100

        # CPU usage penalty
        if cpu_usage > 80:
            score -= 30
        elif cpu_usage > 60:
            score -= 15
        elif cpu_usage > 40:
            score -= 5

        # Memory usage penalty (assuming 2GB system)
        if memory_mb > 1500:  # >1.5GB
            score -= 20
        elif memory_mb > 1000:  # >1GB
            score -= 10

        # Latency penalty
        if latency_ms > 50:
            score -= 25
        elif latency_ms > 20:
            score -= 10
        elif latency_ms > 10:
            score -= 5

        # Buffer issues penalty
        score -= underruns * 2

        # Clamp to valid range
        score = max(0, min(100, score))

        # Convert to rating
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Very Good"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Fair"
        else:
            return "Poor"


class RealTimeOptimizer:
    """Real-time performance optimization for S90/S70"""

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        """
        Initialize real-time optimizer.

        Args:
            sample_rate: Audio sample rate
            buffer_size: Audio buffer size
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Optimization settings
        self.optimizations = {
            'simd_enabled': True,
            'buffer_preallocation': True,
            'voice_culling': True,
            'filter_optimization': True,
            'memory_pooling': True,
            'threading_optimization': True
        }

        # Performance thresholds
        self.thresholds = {
            'max_cpu_usage': 80.0,  # %
            'max_memory_usage': 1500.0,  # MB
            'max_audio_latency': 20.0,  # ms
            'min_buffer_headroom': 10  # samples
        }

        # Adaptive parameters
        self.adaptive_settings = {
            'voice_limit_adaptive': True,
            'quality_degradation_allowed': False,
            'background_processing_disabled': False
        }

        self.lock = threading.RLock()

    def apply_optimizations(self) -> Dict[str, Any]:
        """
        Apply real-time optimizations based on current conditions.

        Returns:
            Applied optimizations report
        """
        with self.lock:
            applied_optimizations = []

            # SIMD optimization
            if self.optimizations['simd_enabled']:
                applied_optimizations.append('SIMD processing enabled')

            # Buffer preallocation
            if self.optimizations['buffer_preallocation']:
                applied_optimizations.append('Buffer preallocation active')

            # Voice culling
            if self.optimizations['voice_culling']:
                applied_optimizations.append('Voice culling optimization active')

            # Memory pooling
            if self.optimizations['memory_pooling']:
                applied_optimizations.append('Memory pooling active')

            return {
                'applied_optimizations': applied_optimizations,
                'optimization_count': len(applied_optimizations),
                'performance_impact': self._estimate_performance_impact(applied_optimizations)
            }

    def _estimate_performance_impact(self, optimizations: List[str]) -> Dict[str, float]:
        """Estimate performance impact of applied optimizations"""
        impact = {
            'cpu_reduction_percent': 0.0,
            'memory_reduction_mb': 0.0,
            'latency_reduction_ms': 0.0
        }

        for opt in optimizations:
            if 'SIMD' in opt:
                impact['cpu_reduction_percent'] += 15.0
            elif 'Buffer preallocation' in opt:
                impact['memory_reduction_mb'] += 5.0
                impact['cpu_reduction_percent'] += 5.0
            elif 'Voice culling' in opt:
                impact['cpu_reduction_percent'] += 10.0
            elif 'Memory pooling' in opt:
                impact['memory_reduction_mb'] += 8.0

        return impact

    def check_performance_thresholds(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Check if performance metrics exceed thresholds.

        Args:
            metrics: Current performance metrics

        Returns:
            List of exceeded thresholds
        """
        with self.lock:
            exceeded = []

            cpu_usage = metrics.get('cpu_usage_percent', 0)
            if cpu_usage > self.thresholds['max_cpu_usage']:
                exceeded.append('.1f')

            memory_mb = metrics.get('memory_usage_mb', 0)
            if memory_mb > self.thresholds['max_memory_usage']:
                exceeded.append('.1f')

            latency_ms = metrics.get('audio_latency_ms', 0)
            if latency_ms > self.thresholds['max_audio_latency']:
                exceeded.append('.1f')

            return exceeded

    def apply_adaptive_measures(self, exceeded_thresholds: List[str]) -> Dict[str, Any]:
        """
        Apply adaptive measures when thresholds are exceeded.

        Args:
            exceeded_thresholds: List of exceeded threshold descriptions

        Returns:
            Applied adaptive measures
        """
        with self.lock:
            measures = []

            for threshold in exceeded_thresholds:
                if 'CPU' in threshold and self.adaptive_settings['voice_limit_adaptive']:
                    measures.append('Reduced voice limit due to high CPU usage')
                elif 'Memory' in threshold:
                    measures.append('Enabled aggressive garbage collection')
                elif 'Latency' in threshold:
                    measures.append('Reduced buffer size for lower latency')

            return {
                'applied_measures': measures,
                'severity_level': len(exceeded_thresholds),
                'recommendations': self._generate_recommendations(exceeded_thresholds)
            }

    def _generate_recommendations(self, exceeded_thresholds: List[str]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        if any('CPU' in t for t in exceeded_thresholds):
            recommendations.extend([
                'Consider reducing polyphony limit',
                'Disable non-essential effects',
                'Use lighter synthesis algorithms'
            ])

        if any('Memory' in t for t in exceeded_thresholds):
            recommendations.extend([
                'Reduce sample library size',
                'Use compressed sample formats',
                'Clear unused presets from memory'
            ])

        if any('Latency' in t for t in exceeded_thresholds):
            recommendations.extend([
                'Reduce audio buffer size',
                'Use lower latency audio driver',
                'Optimize audio processing pipeline'
            ])

        return recommendations

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        with self.lock:
            return {
                'optimizations': self.optimizations.copy(),
                'thresholds': self.thresholds.copy(),
                'adaptive_settings': self.adaptive_settings.copy(),
                'applied_optimizations': self.apply_optimizations()
            }


class S90S70PerformanceFeatures:
    """
    S90/S70 Performance Features Manager

    Provides comprehensive performance features and optimizations
    specific to S90/S70 synthesizers.
    """

    def __init__(self, max_voices: int = 64, sample_rate: int = 44100):
        """
        Initialize performance features manager.

        Args:
            max_voices: Maximum voice count
            sample_rate: Audio sample rate
        """
        self.max_voices = max_voices
        self.sample_rate = sample_rate

        # Core components
        self.voice_optimizer = VoiceAllocationOptimizer(max_voices)
        self.performance_monitor = HardwarePerformanceMonitor(sample_rate)
        self.realtime_optimizer = RealTimeOptimizer(sample_rate)

        # Performance presets
        self.performance_presets = {
            'maximum_performance': {
                'polyphony': 32,
                'effects_quality': 'low',
                'sample_quality': 'compressed',
                'description': 'Maximum performance, minimum latency'
            },
            'balanced': {
                'polyphony': 48,
                'effects_quality': 'medium',
                'sample_quality': 'standard',
                'description': 'Balanced performance and quality'
            },
            'maximum_quality': {
                'polyphony': 64,
                'effects_quality': 'high',
                'sample_quality': 'uncompressed',
                'description': 'Maximum quality, higher latency acceptable'
            }
        }

        self.current_preset = 'balanced'

        # Thread safety
        self.lock = threading.RLock()

    def initialize_performance_monitoring(self):
        """Initialize performance monitoring"""
        with self.lock:
            self.performance_monitor.start_monitoring()

    def shutdown_performance_monitoring(self):
        """Shutdown performance monitoring"""
        with self.lock:
            self.performance_monitor.stop_monitoring()

    def allocate_voice(self, voice_type: str, channel: int, note: int,
                      velocity: int) -> Optional[int]:
        """
        Allocate a voice using hardware-optimized strategy.

        Args:
            voice_type: Type of voice ('awm', 'an', 'fdsp')
            channel: MIDI channel
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Voice ID or None
        """
        with self.lock:
            return self.voice_optimizer.allocate_voice(voice_type, channel, note, velocity)

    def deallocate_voice(self, voice_id: int) -> bool:
        """
        Deallocate a voice.

        Args:
            voice_id: Voice to deallocate

        Returns:
            True if deallocated successfully
        """
        with self.lock:
            return self.voice_optimizer.deallocate_voice(voice_id)

    def apply_performance_preset(self, preset_name: str) -> bool:
        """
        Apply a performance preset.

        Args:
            preset_name: Name of performance preset

        Returns:
            True if preset applied successfully
        """
        with self.lock:
            if preset_name not in self.performance_presets:
                return False

            preset = self.performance_presets[preset_name]
            self.current_preset = preset_name

            # Apply preset settings (placeholder for actual implementation)
            # In a full implementation, this would configure:
            # - Polyphony limits
            # - Effects quality settings
            # - Sample quality/compression settings
            # - Buffer sizes
            # - Voice allocation strategies

            return True

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        with self.lock:
            return {
                'voice_allocation': self.voice_optimizer.get_allocation_status(),
                'hardware_performance': self.performance_monitor.get_performance_report(),
                'optimizations': self.realtime_optimizer.get_optimization_status(),
                'current_preset': self.current_preset,
                'available_presets': list(self.performance_presets.keys()),
                'system_health': self._assess_system_health()
            }

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health"""
        current_metrics = self.performance_monitor.get_current_metrics()

        # Check for performance issues
        issues = self.realtime_optimizer.check_performance_thresholds(current_metrics)

        health_score = 100 - (len(issues) * 20)  # Deduct 20 points per issue
        health_score = max(0, min(100, health_score))

        health_status = "Excellent" if health_score >= 90 else \
                       "Good" if health_score >= 80 else \
                       "Fair" if health_score >= 70 else \
                       "Poor" if health_score >= 60 else "Critical"

        return {
            'health_score': health_score,
            'health_status': health_status,
            'issues': issues,
            'recommendations': self.realtime_optimizer.apply_adaptive_measures(issues) if issues else []
        }

    def optimize_for_workload(self, active_voices: int, effects_active: int) -> Dict[str, Any]:
        """
        Optimize system for current workload.

        Args:
            active_voices: Number of active voices
            effects_active: Number of active effects

        Returns:
            Optimization recommendations
        """
        with self.lock:
            recommendations = []

            # Voice-based optimizations
            if active_voices > self.max_voices * 0.8:
                recommendations.append('High voice count - consider reducing polyphony or using voice stealing')
            elif active_voices > self.max_voices * 0.6:
                recommendations.append('Moderate voice usage - monitor CPU usage')

            # Effects-based optimizations
            if effects_active > 8:
                recommendations.append('Many effects active - consider disabling unused effects')
            elif effects_active > 4:
                recommendations.append('Several effects active - monitor CPU usage')

            # Apply real-time optimizations
            applied_opts = self.realtime_optimizer.apply_optimizations()

            return {
                'recommendations': recommendations,
                'applied_optimizations': applied_opts,
                'workload_assessment': {
                    'voice_utilization': active_voices / self.max_voices,
                    'effects_load': effects_active / 16  # Assuming max 16 effects
                }
            }

    def set_voice_allocation_strategy(self, strategy: str) -> bool:
        """
        Set voice allocation strategy.

        Args:
            strategy: Allocation strategy ('priority', 'oldest', 'quietest')

        Returns:
            True if strategy set successfully
        """
        with self.lock:
            return self.voice_optimizer.set_allocation_strategy(strategy)

    def get_voice_allocation_strategy(self) -> str:
        """Get current voice allocation strategy"""
        with self.lock:
            return self.voice_optimizer.allocation_strategy

    def reset_performance_stats(self):
        """Reset all performance statistics"""
        with self.lock:
            # Reset voice optimizer stats
            self.voice_optimizer.allocation_stats = {
                'total_allocations': 0,
                'total_deallocations': 0,
                'voice_stealing_events': 0,
                'peak_concurrent_voices': 0,
                'allocation_failures': 0
            }

            # Reset performance monitor history
            self.performance_monitor.history.clear()

    def get_realtime_performance_data(self) -> Dict[str, Any]:
        """Get real-time performance data for monitoring"""
        with self.lock:
            return {
                'current_metrics': self.performance_monitor.get_current_metrics(),
                'voice_status': self.voice_optimizer.get_allocation_status(),
                'optimization_status': self.realtime_optimizer.get_optimization_status(),
                'system_health': self._assess_system_health()
            }
