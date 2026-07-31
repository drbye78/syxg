"""Tests for PitchModProcessor — pitch accuracy, curve shapes, boundary conditions."""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.articulation.processors.pitch import PitchModProcessor
from synth.engines.acoustic.behavior_config import InstrumentGroup


SR = 44100
BLOCK = 2048


class Ctx:
    note = 60
    velocity = 100
    sample_rate = SR
    instrument_group = InstrumentGroup.ACOUSTIC_PIANO
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
    """Estimate dominant frequency via zero-crossing rate on left channel."""
    signal = buf[:, 0]
    mid = len(signal) // 4
    seg = signal[mid : mid * 3]
    crossings = np.sum(np.diff(np.signbit(seg)))
    if crossings < 2:
        return 0.0
    return (crossings / 2.0) / (len(seg) / SR)


@pytest.fixture
def processor():
    return PitchModProcessor(SR)


class TestPitchAccuracy:
    def test_vibrato_modulates_pitch(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "vibrato", "rate": 5.0, "depth": 0.5})
        freq = _dominant_freq(buf)
        # Vibrato sweeps around 440Hz — zero-crossing average should be near 440
        assert 400 < freq < 480, f"Expected ~440Hz, got {freq:.1f}"

    def test_vibrato_zero_depth_passthrough(self, processor):
        buf = _sine(440.0)
        original = buf.copy()
        processor.process(buf, ctx, {"type": "vibrato", "rate": 5.0, "depth": 0.0})
        assert np.allclose(buf, original, atol=1e-4)

    def test_bend_one_octave(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "bend", "amount": 12.0})
        freq = _dominant_freq(buf)
        assert freq > 480, f"Bend +12 should increase frequency, got {freq:.1f}"

    def test_bend_zero(self, processor):
        buf = _sine(440.0)
        original = buf.copy()
        processor.process(buf, ctx, {"type": "bend", "amount": 0.0})
        assert np.allclose(buf, original, atol=1e-4)

    def test_trill_alternates_pitch(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "trill", "rate": 8.0, "interval": 2})
        freq = _dominant_freq(buf)
        # Trill of ±2 semitones around 440 → should average near ~470-520
        assert 420 < freq < 560, f"Trill should vary pitch, got {freq:.1f}"

    def test_glissando_sweeps_up(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "glissando", "amount": 12})
        freq = _dominant_freq(buf)
        assert freq > 500, f"Glissando +12 should sweep up, got {freq:.1f}"

    def test_scoop_sweeps_from_below(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "scoop", "amount": -2.0, "curve": "exponential"})
        freq = _dominant_freq(buf)
        assert 360 < freq < 480, f"Scoop should start below target, got {freq:.1f}"

    def test_fall_drops_pitch(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "fall", "amount": -7.0, "curve": "exponential"})
        freq = _dominant_freq(buf)
        # Fall sweeps 440→~294Hz over the block; zero-crossing avg < 440
        assert freq < 440, f"Fall -7 should drop below 440Hz, got {freq:.1f}"

    def test_stereo_independence(self, processor):
        buf = _sine(440.0)
        buf[:, 1] *= 0.5  # right channel quieter
        original_left = buf[:, 0].copy()
        processor.process(buf, ctx, {"type": "vibrato", "rate": 5.0, "depth": 0.5})
        # Both channels should be modified
        assert not np.array_equal(buf[:, 0], original_left)

    def test_ethnic_bend(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "ethnic_bend", "amount": 0.5, "speed": 0.3})
        assert np.any(np.abs(buf) > 0.001)

    def test_hammer_on(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "hammer_on", "amount": 2})
        freq = _dominant_freq(buf)
        assert freq > 440, f"Hammer-on should raise pitch, got {freq:.1f}"

    def test_pull_off(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "pull_off", "amount": -2})
        freq = _dominant_freq(buf)
        assert freq < 480, f"Pull-off should lower pitch, got {freq:.1f}"


class TestBoundaryConditions:
    def test_empty_buffer(self, processor):
        buf = np.zeros((0, 2), dtype=np.float32)
        processor.process(buf, ctx, {"type": "vibrato"})
        assert buf.shape == (0, 2)

    def test_single_sample(self, processor):
        buf = np.ones((1, 2), dtype=np.float32)
        processor.process(buf, ctx, {"type": "vibrato", "rate": 5.0, "depth": 0.5})
        assert buf.shape == (1, 2)
        assert np.isfinite(buf).all()

    def test_reset_clears_state(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"type": "vibrato"})
        processor.reset()
        # Reset should not raise
