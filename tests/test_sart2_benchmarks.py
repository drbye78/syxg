"""
S.Art2 Performance Benchmarks

Benchmarks for S.Art2 articulation system performance.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from synth.engines.region_descriptor import RegionDescriptor
from synth.processing.partial.region import IRegion
from synth.protocols.xg.sart.articulation_controller import ArticulationController
from synth.protocols.xg.sart.articulation_preset import ArticulationPreset, ArticulationPresetManager
from synth.protocols.xg.sart.sart2_region import SArt2Region

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def controller():
    """Create ArticulationController for benchmarking."""
    return ArticulationController()


@pytest.fixture
def preset_manager():
    """Create ArticulationPresetManager for benchmarking."""
    return ArticulationPresetManager()


@pytest.fixture
def mock_region():
    """Create mock base region for benchmarking."""

    class MockRegion(IRegion):
        def __init__(self):
            descriptor = RegionDescriptor(
                region_id=0, engine_type="mock", key_range=(0, 127), velocity_range=(0, 127)
            )
            super().__init__(descriptor, 44100)
            self._active = False

        def _load_sample_data(self):
            return None

        def _create_partial(self):
            return None

        def _init_envelopes(self):
            pass

        def _init_filters(self):
            pass

        def note_on(self, velocity, note):
            self._active = True
            return True

        def note_off(self):
            self._active = False

        def is_active(self):
            return self._active

        def generate_samples(self, block_size, modulation):
            return np.zeros(block_size * 2, dtype=np.float32)

        def initialize(self):
            return True

        def reset(self):
            pass

        def dispose(self):
            pass

        def get_region_info(self):
            return {}

    return MockRegion()


# ============================================================================
# NRPN PROCESSING BENCHMARKS
# ============================================================================


class TestNRPNBenchmarks:
    """Benchmarks for NRPN processing."""

    def test_nrpn_processing_speed(self, controller):
        """Benchmark NRPN processing speed."""
        iterations = 10000

        start = time.perf_counter()
        for i in range(iterations):
            controller.process_nrpn(1, i % 50)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should process NRPN in < 0.01ms on average
        assert avg_time_ms < 0.01, f"NRPN processing too slow: {avg_time_ms:.4f}ms"
        print(f"\nNRPN Processing: {avg_time_ms:.4f}ms per call ({iterations} iterations)")

    def test_nrpn_mode_switching_speed(self, controller):
        """Benchmark mode switching speed."""
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            controller.set_compatibility_mode("sart2")
            controller.set_compatibility_mode("xg")
            controller.set_compatibility_mode("gs")
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should switch modes in < 0.001ms on average
        assert avg_time_ms < 0.001, f"Mode switching too slow: {avg_time_ms:.4f}ms"
        print(f"\nMode Switching: {avg_time_ms:.4f}ms per switch ({iterations} iterations)")


# ============================================================================
# ARTICULATION PRESET BENCHMARKS
# ============================================================================


class TestPresetBenchmarks:
    """Benchmarks for articulation preset operations."""

    def test_preset_creation_speed(self):
        """Benchmark preset creation speed."""
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            preset = ArticulationPreset(
                name=f"Test {i}", program=i % 128, bank=0, default_articulation="normal"
            )
            preset.add_velocity_split(0, 64, "staccato")
            preset.add_velocity_split(65, 127, "legato")
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should create preset in < 0.1ms on average
        assert avg_time_ms < 0.1, f"Preset creation too slow: {avg_time_ms:.4f}ms"
        print(f"\nPreset Creation: {avg_time_ms:.4f}ms per preset ({iterations} iterations)")

    def test_preset_lookup_speed(self, preset_manager):
        """Benchmark preset lookup speed."""
        # Add presets
        for i in range(100):
            preset = ArticulationPreset(name=f"Preset {i}", program=i, bank=0)
            preset_manager.add_preset(preset)

        iterations = 10000

        start = time.perf_counter()
        for i in range(iterations):
            preset_manager.get_preset(i % 100, 0)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should lookup preset in < 0.001ms on average
        assert avg_time_ms < 0.001, f"Preset lookup too slow: {avg_time_ms:.4f}ms"
        print(f"\nPreset Lookup: {avg_time_ms:.4f}ms per lookup ({iterations} iterations)")

    def test_preset_serialization_speed(self):
        """Benchmark preset serialization speed."""
        preset = ArticulationPreset(
            name="Test Piano", program=0, bank=0, default_articulation="normal"
        )
        preset.add_velocity_split(0, 64, "staccato", note_length=0.5)
        preset.add_velocity_split(65, 100, "normal")
        preset.add_velocity_split(101, 127, "marcato", accent=1.2)

        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            json_str = preset.to_json()
            preset2 = ArticulationPreset.from_json(json_str)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should serialize/deserialize in < 0.5ms on average
        assert avg_time_ms < 0.5, f"Serialization too slow: {avg_time_ms:.4f}ms"
        print(
            f"\nPreset Serialization: {avg_time_ms:.4f}ms per round-trip ({iterations} iterations)"
        )


# ============================================================================
# SART2REGION BENCHMARKS
# ============================================================================


class TestSArt2RegionBenchmarks:
    """Benchmarks for SArt2Region operations."""

    def test_sart2_region_creation_speed(self, mock_region):
        """Benchmark SArt2Region creation speed."""
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            region = SArt2Region(mock_region)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should create region in < 5ms on average (includes object initialization)
        assert avg_time_ms < 5, f"Region creation too slow: {avg_time_ms:.4f}ms"
        print(f"\nSArt2Region Creation: {avg_time_ms:.4f}ms per region ({iterations} iterations)")

    def test_sart2_region_note_on_speed(self, mock_region):
        """Benchmark SArt2Region note_on speed."""
        region = SArt2Region(mock_region)
        region.set_velocity_articulation(0, 64, "staccato")
        region.set_velocity_articulation(65, 127, "legato")

        iterations = 10000

        start = time.perf_counter()
        for i in range(iterations):
            region.note_on(velocity=(i % 128), note=60)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should process note_on in < 0.01ms on average
        assert avg_time_ms < 0.01, f"note_on too slow: {avg_time_ms:.4f}ms"
        print(f"\nSArt2Region note_on: {avg_time_ms:.4f}ms per call ({iterations} iterations)")

    def test_sart2_region_articulation_switching_speed(self, mock_region):
        """Benchmark articulation switching speed."""
        region = SArt2Region(mock_region)

        iterations = 10000

        start = time.perf_counter()
        for i in range(iterations):
            region.set_articulation("legato" if i % 2 == 0 else "staccato")
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000

        # Should switch articulation in < 0.01ms on average
        assert avg_time_ms < 0.01, f"Articulation switching too slow: {avg_time_ms:.4f}ms"
        print(f"\nArticulation Switching: {avg_time_ms:.4f}ms per switch ({iterations} iterations)")


# ============================================================================
# MEMORY USAGE BENCHMARKS
# ============================================================================


class TestMemoryBenchmarks:
    """Benchmarks for memory usage."""

    def test_controller_memory_usage(self):
        """Benchmark ArticulationController memory usage."""
        import sys

        controller = ArticulationController()

        # Get approximate memory usage
        memory_bytes = sys.getsizeof(controller)
        memory_kb = memory_bytes / 1024

        # Should use < 100KB
        assert memory_kb < 100, f"Controller uses too much memory: {memory_kb:.2f}KB"
        print(f"\nArticulationController Memory: {memory_kb:.2f}KB")

    def test_preset_memory_usage(self):
        """Benchmark ArticulationPreset memory usage."""
        import sys

        preset = ArticulationPreset(
            name="Test Piano", program=0, bank=0, default_articulation="normal"
        )
        preset.add_velocity_split(0, 64, "staccato")
        preset.add_velocity_split(65, 127, "legato")
        preset.add_velocity_split(101, 127, "marcato")

        # Get approximate memory usage
        memory_bytes = sys.getsizeof(preset)
        memory_kb = memory_bytes / 1024

        # Should use < 10KB
        assert memory_kb < 10, f"Preset uses too much memory: {memory_kb:.2f}KB"
        print(f"\nArticulationPreset Memory: {memory_kb:.2f}KB")

    def test_preset_manager_memory_usage(self, preset_manager):
        """Benchmark ArticulationPresetManager memory usage with many presets."""
        import sys

        # Add 100 presets
        for i in range(100):
            preset = ArticulationPreset(name=f"Preset {i}", program=i, bank=0)
            preset_manager.add_preset(preset)

        # Get approximate memory usage
        memory_bytes = sys.getsizeof(preset_manager)
        memory_kb = memory_bytes / 1024

        # Should use < 1MB for 100 presets
        assert memory_kb < 1024, f"Preset manager uses too much memory: {memory_kb:.2f}KB"
        print(f"\nArticulationPresetManager Memory (100 presets): {memory_kb:.2f}KB")


# ============================================================================
# THROUGHPUT BENCHMARKS
# ============================================================================


class TestThroughputBenchmarks:
    """Benchmarks for throughput."""

    def test_nrpn_throughput(self, controller):
        """Benchmark NRPN throughput."""
        iterations = 100000

        start = time.perf_counter()
        for i in range(iterations):
            controller.process_nrpn(1, i % 50)
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed

        # Should process > 100,000 NRPN messages per second
        assert throughput > 100000, f"NRPN throughput too low: {throughput:.0f}/s"
        print(f"\nNRPN Throughput: {throughput:.0f} messages/second")

    def test_preset_lookup_throughput(self, preset_manager):
        """Benchmark preset lookup throughput."""
        # Add presets
        for i in range(100):
            preset = ArticulationPreset(name=f"Preset {i}", program=i, bank=0)
            preset_manager.add_preset(preset)

        iterations = 100000

        start = time.perf_counter()
        for i in range(iterations):
            preset_manager.get_preset(i % 100, 0)
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed

        # Should lookup > 1,000,000 presets per second
        assert throughput > 1000000, f"Preset lookup throughput too low: {throughput:.0f}/s"
        print(f"\nPreset Lookup Throughput: {throughput:.0f} lookups/second")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
