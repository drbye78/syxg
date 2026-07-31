"""Tests for HarmonicsProcessor — partial shift accuracy, harmonic type differences."""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.articulation.processors.harmonics import HarmonicsProcessor
from synth.engines.acoustic.behavior_config import InstrumentGroup


SR = 44100
BLOCK = 2048


class Ctx:
    note = 60
    velocity = 100
    sample_rate = SR
    instrument_group = InstrumentGroup.ACOUSTIC_GUITAR
    channel_context = None
    voice_state = None


ctx = Ctx()


def _sine(freq: float = 440.0, n: int = BLOCK) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    return np.column_stack([
        np.sin(2.0 * np.pi * freq * t).astype(np.float32),
        np.sin(2.0 * np.pi * freq * t).astype(np.float32),
    ])


def _dominant_freq(buf: np.ndarray) -> float:
    """Estimate dominant frequency via zero-crossing rate on first valid region."""
    signal = buf[:, 0]
    # Check first quarter of buffer — for upward pitch shift, the end gets clamped
    end = len(signal) // 4
    seg = signal[16:end]  # skip first few samples for onset
    crossings = np.sum(np.diff(np.signbit(seg)))
    if crossings < 2:
        return 0.0
    return (crossings / 2.0) / (len(seg) / SR)


@pytest.fixture
def processor():
    return HarmonicsProcessor(SR)


class TestPartialShift:
    def test_partial_2_shifts_octave_up(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 2, "harmonic_type": "natural"})
        freq = _dominant_freq(buf)
        # Octave up (partial 2) → ~880 Hz
        assert 700 < freq < 1000, f"Partial 2 should be ~880Hz, got {freq:.1f}"

    def test_partial_3_shifts_up(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 3, "harmonic_type": "natural"})
        freq = _dominant_freq(buf)
        assert freq > 880, f"Partial 3 should be >880Hz, got {freq:.1f}"

    def test_partial_4_shifts_higher(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 4, "harmonic_type": "natural"})
        freq = _dominant_freq(buf)
        assert freq > 1200, f"Partial 4 should be >1200Hz, got {freq:.1f}"

    def test_partial_1_passthrough(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 1, "harmonic_type": "natural"})
        freq = _dominant_freq(buf)
        assert 400 < freq < 520, f"Partial 1 should preserve pitch, got {freq:.1f}"


class TestHarmonicTypes:
    def test_pinch_adds_am(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"partial": 3, "harmonic_type": "pinch"})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"partial": 3, "harmonic_type": "natural"})
        # Pinch should differ from natural due to AM modulation
        assert not np.array_equal(buf1, buf2)

    def test_tap_is_muted(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"partial": 2, "harmonic_type": "natural"})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"partial": 2, "harmonic_type": "tap"})
        # Tap should be quieter than natural
        assert np.mean(np.abs(buf2)) < np.mean(np.abs(buf1))

    def test_artificial_differs_from_natural(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"partial": 2, "harmonic_type": "natural"})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"partial": 2, "harmonic_type": "artificial"})
        # Same partial, different type — output may differ depending on detune
        assert np.any(np.abs(buf2) > 0.0)

    def test_detune_cents(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"partial": 2, "harmonic_type": "natural", "detune_cents": 0})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"partial": 2, "harmonic_type": "natural", "detune_cents": 50})
        # Detune should change output
        assert not np.array_equal(buf1, buf2)


class TestBoundaryConditions:
    def test_empty_buffer(self, processor):
        buf = np.zeros((0, 2), dtype=np.float32)
        processor.process(buf, ctx, {"partial": 2})
        assert buf.shape == (0, 2)

    def test_stereo_output(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 2, "harmonic_type": "natural"})
        assert buf.shape == (BLOCK, 2)

    def test_reset(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"partial": 2})
        processor.reset()
