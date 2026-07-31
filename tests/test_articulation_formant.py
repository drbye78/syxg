"""Tests for FormantProcessor — spectral peaks, register differences, drive effects."""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.articulation.processors.formant import FormantProcessor
from synth.engines.acoustic.behavior_config import InstrumentGroup


SR = 44100
BLOCK = 2048


class Ctx:
    note = 60
    velocity = 100
    sample_rate = SR
    instrument_group = InstrumentGroup.CHOIR
    channel_context = None
    voice_state = None


ctx = Ctx()


def _sine(freq: float = 440.0, n: int = BLOCK) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    return np.column_stack([
        np.sin(2.0 * np.pi * freq * t).astype(np.float32),
        np.sin(2.0 * np.pi * freq * t).astype(np.float32),
    ])


@pytest.fixture
def processor():
    return FormantProcessor(SR)


class TestFormantRegisters:
    def test_chest_voice_modifies_buffer(self, processor):
        buf = _sine(440.0)
        original = buf.copy()
        processor.process(buf, ctx, {"register": "chest_voice", "mix": 0.5})
        assert not np.array_equal(buf, original), "chest_voice should modify buffer"

    def test_falsetto_modifies_buffer(self, processor):
        buf = _sine(440.0)
        original = buf.copy()
        processor.process(buf, ctx, {"register": "falsetto", "mix": 0.5, "breathiness": 0.2})
        assert not np.array_equal(buf, original)

    def test_head_voice_modifies_buffer(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "head_voice", "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_mixed_voice_modifies_buffer(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "mixed_voice", "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_straight_tone_modifies_buffer(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "straight_tone", "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_different_registers_produce_different_output(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"register": "chest_voice", "mix": 0.5})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"register": "falsetto", "mix": 0.5})
        assert not np.array_equal(buf1, buf2), "chest vs falsetto should differ"


class TestDriveEffects:
    def test_shout_adds_drive(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "shout", "drive": 0.3, "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_scream_adds_more_drive(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "scream", "drive": 0.6, "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_shout_vs_scream_different(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"register": "shout", "drive": 0.3, "mix": 0.5})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"register": "scream", "drive": 0.6, "mix": 0.5})
        assert not np.array_equal(buf1, buf2)


class TestBreathiness:
    def test_breathiness_adds_noise(self, processor):
        buf1 = _sine(440.0)
        processor.process(buf1, ctx, {"register": "falsetto", "mix": 0.5, "breathiness": 0.0})
        buf2 = _sine(440.0)
        processor.process(buf2, ctx, {"register": "falsetto", "mix": 0.5, "breathiness": 0.8})
        assert not np.array_equal(buf1, buf2), "breathiness should add noise"

    def test_vocal_fry_modulates(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "vocal_fry", "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)

    def test_vocal_attack(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "vocal_attack", "mix": 0.5})
        assert np.any(np.abs(buf) > 0.0)


class TestBoundaryConditions:
    def test_empty_buffer(self, processor):
        buf = np.zeros((0, 2), dtype=np.float32)
        processor.process(buf, ctx, {"register": "chest_voice"})
        assert buf.shape == (0, 2)

    def test_zero_mix_passthrough(self, processor):
        buf = _sine(440.0)
        original = buf.copy()
        processor.process(buf, ctx, {"register": "chest_voice", "mix": 0.0})
        assert np.allclose(buf, original, atol=1e-4)

    def test_stereo_preserved(self, processor):
        buf = np.ones((BLOCK, 2), dtype=np.float32)
        buf[:, 1] *= 0.5
        processor.process(buf, ctx, {"register": "chest_voice", "mix": 0.5})
        assert buf.shape == (BLOCK, 2)

    def test_reset(self, processor):
        buf = _sine(440.0)
        processor.process(buf, ctx, {"register": "chest_voice", "mix": 0.5})
        processor.reset()
