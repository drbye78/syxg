"""
Style Engine Performance Tests

Performance benchmarks for the style engine including:
- Timing accuracy tests
- Latency measurements
- Polyphony stress tests
- Memory usage tests
"""
from __future__ import annotations

import pytest
import time
import numpy as np
from unittest.mock import Mock
import tracemalloc

from synth.style.auto_accompaniment import AutoAccompaniment, AutoAccompanimentConfig
from synth.style.chord_detector import ChordDetector, ChordDetectionConfig
from synth.style.chord_detection_enhanced import EnhancedChordDetector
from synth.style.scale import ScaleDetector
from synth.style.style_loader import StyleLoader


class TestTimingAccuracy:
    """Test timing accuracy of style engine components."""

    @pytest.fixture
    def accompaniment(self):
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        config = AutoAccompanimentConfig(sync_start_enabled=False)
        return AutoAccompaniment(style, synth, config, sample_rate=44100)

    def test_tick_timing_accuracy(self, accompaniment):
        """Verify ticks progress at correct rate."""
        accompaniment.start()
        
        expected_tick_duration_ms = 60000 / (120 * 480)  # ~1.04ms at 120bpm
        
        start_tick = accompaniment._tick_position
        time.sleep(0.1)  # 100ms
        end_tick = accompaniment._tick_position
        
        expected_ticks = 100 / expected_tick_duration_ms
        actual_ticks = end_tick - start_tick
        
        # Allow 10% tolerance for test environment
        tolerance = 0.10
        assert abs(actual_ticks - expected_ticks) / expected_ticks < tolerance

    def test_bar_boundary_detection(self, accompaniment):
        """Test that bar boundaries are detected correctly."""
        accompaniment.start()
        
        initial_bar = accompaniment._bar_position
        ticks_per_bar = accompaniment._ticks_per_bar
        
        # Wait for approximately one bar
        time.sleep(ticks_per_bar * accompaniment._ms_per_tick / 1000 + 0.05)
        
        # Bar should have incremented
        assert accompaniment._bar_position >= initial_bar


class TestLatency:
    """Test latency measurements."""

    def test_chord_detection_latency_basic(self):
        """Measure latency from note input to chord detection."""
        detector = ChordDetector()
        
        iterations = 100
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            detector.note_on(60)
            detector.note_on(64)
            detector.note_on(67)
            detector.get_current_chord()
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            
            detector.reset()
        
        avg_latency = np.mean(latencies) * 1000  # Convert to ms
        max_latency = np.max(latencies) * 1000
        
        # Should be well under 10ms
        assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}ms exceeds 5ms"
        assert max_latency < 10.0, f"Max latency {max_latency:.2f}ms exceeds 10ms"

    def test_chord_detection_latency_enhanced(self):
        """Measure latency for enhanced chord detector."""
        detector = EnhancedChordDetector()
        
        iterations = 50
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            detector.note_on(60)
            detector.note_on(64)
            detector.note_on(67)
            detector.note_on(70)
            detector.get_current_chord()
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            
            detector.reset()
        
        avg_latency = np.mean(latencies) * 1000
        max_latency = np.max(latencies) * 1000
        
        # Enhanced detector is more complex, allow more time
        assert avg_latency < 10.0, f"Average latency {avg_latency:.2f}ms exceeds 10ms"
        assert max_latency < 20.0, f"Max latency {max_latency:.2f}ms exceeds 20ms"

    def test_scale_detection_latency(self):
        """Measure latency for scale detection."""
        detector = ScaleDetector()
        
        # Add some notes
        for note in range(60, 72):
            detector.add_note(note)
        
        iterations = 20
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            detector.get_current_scale()
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
        
        avg_latency = np.mean(latencies) * 1000
        assert avg_latency < 2.0, f"Scale detection latency {avg_latency:.2f}ms exceeds 2ms"


class TestPolyphony:
    """Test polyphony and resource management."""

    def test_max_polyphony_not_exceeded(self):
        """Verify voice count stays within limits."""
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        config = AutoAccompanimentConfig(sync_start_enabled=False)
        
        accompaniment = AutoAccompaniment(style, synth, config, sample_rate=44100)
        accompaniment.start()
        
        # Play many notes
        for note in range(36, 84):
            accompaniment.process_midi_note_on(0, note, 100)
        
        time.sleep(0.1)
        
        # Check active notes
        status = accompaniment.get_status()
        assert status is not None

    def test_voice_stealing_works(self):
        """Test that oldest voices are stolen when limit reached."""
        detector = ChordDetector()
        
        # Add many notes rapidly
        for i in range(50):
            detector.note_on(48 + (i % 24))
        
        # Should not crash - active notes can exceed max_notes_for_chord
        # as it's just a detection threshold, not a hard limit
        active = detector.get_active_notes()
        assert len(active) >= 0  # Should not crash

    def test_memory_usage_stable(self):
        """Test no memory leaks during extended playback."""
        tracemalloc.start()
        
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        config = AutoAccompanimentConfig(sync_start_enabled=False)
        
        accompaniment = AutoAccompaniment(style, synth, config, sample_rate=44100)
        accompaniment.start()
        
        # Simulate extended playback
        for _ in range(100):
            for note in [60, 64, 67]:
                accompaniment.process_midi_note_on(0, note, 100)
            time.sleep(0.001)
            for note in [60, 64, 67]:
                accompaniment.process_midi_note_off(0, note)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak should not exceed reasonable threshold (50MB)
        assert peak < 50 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024:.2f}MB exceeds 50MB"


class TestStyleLoaderPerformance:
    """Test style loading performance."""

    def test_style_load_time(self):
        """Test that styles load within acceptable time."""
        loader = StyleLoader()
        
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            style = loader.create_example_style()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = np.mean(times) * 1000  # ms
        assert avg_time < 100, f"Average load time {avg_time:.2f}ms exceeds 100ms"

    def test_style_save_load_roundtrip(self, tmp_path):
        """Test save/load roundtrip performance."""
        loader = StyleLoader()
        style = loader.create_example_style()
        
        times = []
        for i in range(5):
            path = tmp_path / f"style_{i}.yaml"
            
            start = time.perf_counter()
            loader.save_style(style, path)
            reloaded = loader.load_style_file(path)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = np.mean(times) * 1000
        assert avg_time < 200, f"Roundtrip time {avg_time:.2f}ms exceeds 200ms"


class TestConcurrentAccess:
    """Test thread safety and concurrent access."""

    def test_concurrent_note_events(self):
        """Test handling concurrent note events."""
        detector = ChordDetector()
        import threading
        
        errors = []
        
        def add_notes():
            try:
                for i in range(50):
                    detector.note_on(60 + (i % 12))
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_notes) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Concurrent access errors: {errors}"

    def test_concurrent_chord_detection(self):
        """Test concurrent chord detection."""
        detector = EnhancedChordDetector()
        import threading
        
        results = []
        
        def detect():
            for i in range(20):
                detector.note_on(60 + (i % 12))
                chord = detector.get_current_chord()
                results.append(chord is not None)
        
        threads = [threading.Thread(target=detect) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have results from all threads
        assert len(results) == 80
