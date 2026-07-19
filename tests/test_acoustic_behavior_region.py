"""Tests for the AcousticBehaviorRegion wrapper (single-note + cross-note)."""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.acoustic.acoustic_behavior_region import AcousticBehaviorRegion
from synth.engines.acoustic.behavior_config import BehaviorConfig, InstrumentGroup
from synth.engines.acoustic.channel_context import ChannelAcousticContext
from synth.processing.partial.region import IRegion, RegionState


class _MockRegion(IRegion):
    """Minimal base region returning a constant stereo buffer."""

    def _load_sample_data(self):
        return None

    def _create_partial(self):
        return None

    def _init_envelopes(self):
        pass

    def _init_filters(self):
        pass

    def generate_samples(self, block_size, modulation):
        return np.full((block_size, 2), 0.5, np.float32)

    def is_active(self):
        return True


@pytest.fixture
def ctx():
    return ChannelAcousticContext(44100, 0, BehaviorConfig())


def _make_region(ctx, group=InstrumentGroup.ACOUSTIC_PIANO):
    base = _MockRegion(
        __import__(
            "synth.engines.region_descriptor", fromlist=["RegionDescriptor"]
        ).RegionDescriptor(engine_type="mock", region_id="r1"),
        44100,
    )
    return AcousticBehaviorRegion(base, ctx, group=group, sample_rate=44100)


class TestPipelineShape:
    """Output must always be a valid stereo float32 buffer."""

    @pytest.mark.unit
    def test_output_shape_and_dtype(self, ctx):
        region = _make_region(ctx)
        region.note_on(100, 60)
        buf = region.generate_samples(512, {"articulation": "normal"})
        assert buf.shape == (512, 2)
        assert buf.dtype == np.float32

    @pytest.mark.unit
    def test_silence_on_empty_base(self, ctx):
        class _Empty(_MockRegion):
            def generate_samples(self, block_size, modulation):
                return np.zeros((block_size, 2), np.float32)

        base = _Empty(
            __import__(
                "synth.engines.region_descriptor", fromlist=["RegionDescriptor"]
            ).RegionDescriptor(engine_type="mock", region_id="r1"),
            44100,
        )
        region = AcousticBehaviorRegion(base, ctx, sample_rate=44100)
        region.note_on(100, 60)
        buf = region.generate_samples(512, {})
        assert buf.shape == (512, 2)


class TestSingleNoteBehavior:
    """Velocity-driven timbre is applied per note."""

    @pytest.mark.unit
    def test_soft_vs_hard_velocity_differ(self, ctx):
        # Use a harmonic-rich base signal so the velocity lowpass produces a
        # measurable brightness difference (hard = brighter = more HF energy).
        class _Harmonic(_MockRegion):
            def generate_samples(self, block_size, modulation):
                t = np.arange(block_size) / 44100.0
                sig = np.zeros(block_size, np.float32)
                for h in range(1, 9):
                    sig += np.sin(2 * np.pi * 220 * h * t) / h
                return np.stack([sig, sig], axis=1).astype(np.float32)

        def brightness(b):
            # High-frequency energy proxy: std of first difference.
            return float(np.std(np.diff(b[:, 0])))

        soft = AcousticBehaviorRegion(
            _Harmonic(
                __import__(
                    "synth.engines.region_descriptor", fromlist=["RegionDescriptor"]
                ).RegionDescriptor(engine_type="mock", region_id="r1"),
                44100,
            ),
            ctx,
            sample_rate=44100,
        )
        soft.note_on(40, 60)
        buf_soft = soft.generate_samples(4096, {"articulation": "normal"})

        hard = AcousticBehaviorRegion(
            _Harmonic(
                __import__(
                    "synth.engines.region_descriptor", fromlist=["RegionDescriptor"]
                ).RegionDescriptor(engine_type="mock", region_id="r1"),
                44100,
            ),
            ctx,
            sample_rate=44100,
        )
        hard.note_on(127, 60)
        buf_hard = hard.generate_samples(4096, {"articulation": "normal"})

        assert brightness(buf_hard) > brightness(buf_soft)


class TestCrossNoteBehavior:
    """Shared resonance bus is fed by all voices on the channel."""

    @pytest.mark.unit
    def test_resonance_fed_by_multiple_voices(self, ctx):
        # Three voices on the same context feed the shared bank.
        regions = []
        for i, note in enumerate((60, 64, 67)):
            r = _make_region(ctx)
            r.note_on(90, note)
            regions.append(r)
            ctx.note_on(note, 90, i + 1, 0.0)

        # Render one block from each; the bank accumulates energy.
        for r in regions:
            _ = r.generate_samples(1024, {"articulation": "normal"})

        bank = ctx.get_resonance_bank()
        mixed = bank.mix(np.zeros((1024, 2), np.float32), amount=1.0)
        assert float(np.sqrt(np.mean(mixed**2))) > 0.0

    @pytest.mark.unit
    def test_held_chord_flag_propagates(self, ctx):
        for i, note in enumerate((60, 64, 67)):
            ctx.note_on(note, 90, i + 1, 0.0)
        assert ctx.phrase.is_held_chord is True


class TestLifecycle:
    """Note-on/off and dispose must not leak state."""

    @pytest.mark.unit
    def test_note_off_releases_state(self, ctx):
        region = _make_region(ctx)
        region.note_on(100, 60)
        assert region._state is not None
        region.note_off()
        assert region._state.phase.value == "release"

    @pytest.mark.unit
    def test_dispose_clears_dsp(self, ctx):
        region = _make_region(ctx)
        region.note_on(100, 60)
        region.generate_samples(256, {"articulation": "normal"})
        region.dispose()
        assert region._dsp == {}
        assert region.state == RegionState.RELEASED
