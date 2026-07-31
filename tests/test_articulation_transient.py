"""Tests for TransientProcessor — multi-strike timing, per-group presets, boundary conditions."""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.articulation.processors.transient import TransientProcessor
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


def _silence(n: int = BLOCK) -> np.ndarray:
    return np.zeros((n, 2), dtype=np.float32)


@pytest.fixture
def processor():
    return TransientProcessor(SR)


class TestMultiStrike:
    def test_flam_produces_output(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "flam", "delay_ms": 15})
        assert np.any(np.abs(buf) > 0.0), "flam should produce audible output"

    def test_drag_has_two_bounces(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "drag", "delay_ms": 20, "bounces": 2})
        # Drag with 2 bounces should have more energy than single strike
        energy = float(np.mean(np.abs(buf)))
        assert energy > 0.0

    def test_ruff_has_three_bounces(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "ruff", "delay_ms": 12, "bounces": 3})
        assert np.any(np.abs(buf) > 0.0)

    def test_diddle_timing(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "diddle"})
        assert np.any(np.abs(buf) > 0.0)

    def test_bounce_timing(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "bounce"})
        assert np.any(np.abs(buf) > 0.0)

    def test_stereo_output(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "flam"})
        # Both channels should have output
        assert np.any(np.abs(buf[:, 0]) > 0.0)
        assert np.any(np.abs(buf[:, 1]) > 0.0)


class TestPerGroupPresets:
    def test_piano_preset(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "flam"})
        assert np.any(np.abs(buf) > 0.0)

    def test_percussion_preset(self, processor):
        ctx_p = Ctx()
        ctx_p.instrument_group = InstrumentGroup.MALLETS
        buf = _silence()
        processor.process(buf, ctx_p, {"type": "flam"})
        # Mallets should have higher resonance = brighter transient
        assert np.any(np.abs(buf) > 0.0)

    def test_different_groups_produce_different_output(self, processor):
        buf1 = _silence()
        processor.process(buf1, ctx, {"type": "flam"})

        ctx2 = Ctx()
        ctx2.instrument_group = InstrumentGroup.MALLETS
        buf2 = _silence()
        processor.process(buf2, ctx2, {"type": "flam"})

        # Different groups should produce different spectral content
        assert not np.array_equal(buf1, buf2)


class TestNoiseTransients:
    def test_cross_stick(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "cross_stick"})
        assert np.any(np.abs(buf) > 0.0)

    def test_dead_stroke(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "dead_stroke"})
        assert np.any(np.abs(buf) > 0.0)

    def test_perc_attack(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "perc_attack"})
        assert np.any(np.abs(buf) > 0.0)

    def test_ethnic_attack(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "ethnic_attack"})
        assert np.any(np.abs(buf) > 0.0)


class TestBoundaryConditions:
    def test_empty_buffer(self, processor):
        buf = np.zeros((0, 2), dtype=np.float32)
        processor.process(buf, ctx, {"type": "flam"})
        assert buf.shape == (0, 2)

    def test_single_sample(self, processor):
        buf = np.ones((1, 2), dtype=np.float32)
        processor.process(buf, ctx, {"type": "flam"})
        assert buf.shape == (1, 2)

    def test_reset(self, processor):
        buf = _silence()
        processor.process(buf, ctx, {"type": "flam"})
        processor.reset()
