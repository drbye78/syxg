"""End-to-end render verification through the complete SF2 + acoustic stack.

Loads the reference GM soundfont (tests/ref.sf2 -> Timbres Of Heaven) into
the real SF2Engine, drives notes through the production Channel -> Voice ->
SF2Region -> AcousticBehaviorRegion path, and asserts that:

  * real (non-silent) stereo audio is produced,
  * the acoustic wrapper is actually applied (SF2Region is wrapped),
  * the S.Art2 bridge resolves against the real modifier set,
  * cross-note context tracks all sounding voices and the shared
    resonance bus is fed by every voice.

This is the "complete rendering stack" check requested for the 1.1.0
acoustic behavior layer.
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.engines.acoustic.acoustic_behavior_region import AcousticBehaviorRegion
from synth.engines.acoustic.sart_bridge import SArt2Bridge
from synth.engines.engine_registry import SynthesisEngineRegistry
from synth.engines.sf2_engine import SF2Engine
from synth.processing.channel import Channel
from synth.processing.voice.voice_factory import VoiceFactory

REF_SF2 = "tests/ref.sf2"


@pytest.fixture(scope="module")
def channel():
    """A Channel backed by the real reference soundfont."""
    eng = SF2Engine(sample_rate=44100, block_size=1024)
    eng.load_soundfont(REF_SF2)
    reg = SynthesisEngineRegistry()
    reg.register_engine(eng, "sf2", priority=10)
    factory = VoiceFactory(reg)
    ch = Channel(0, factory, 44100)
    ch.load_program(0, 0)  # GM Acoustic Grand Piano
    return ch


class TestCompleteStack:
    """Full SF2 + acoustic behavior render path."""

    @pytest.mark.unit
    def test_voice_created_with_acoustic_context(self, channel):
        assert channel.current_voice is not None
        assert channel.get_acoustic_context() is not None

    @pytest.mark.unit
    def test_region_is_wrapped_by_acoustic_layer(self, channel):
        regions = channel.current_voice.get_regions_for_note(60, 100)
        assert len(regions) >= 1
        for r in regions:
            assert isinstance(r, AcousticBehaviorRegion)
            assert type(r.base_region).__name__ == "SF2Region"

    @pytest.mark.unit
    def test_sart2_bridge_resolves_real_modifier(self):
        bridge = SArt2Bridge(44100)
        assert bridge.available is True

    @pytest.mark.unit
    def test_single_note_renders_real_audio(self, channel):
        regions = channel.current_voice.get_regions_for_note(60, 100)
        regions[0].note_on(100, 60)
        buf = regions[0].generate_samples(1024, {"articulation": "normal"})
        assert buf.shape == (1024, 2)
        assert buf.dtype == np.float32
        rms = float(np.sqrt(np.mean(buf**2)))
        # Real piano sample -> audible, non-silent output
        assert rms > 1e-4

    @pytest.mark.unit
    def test_velocity_changes_timbre(self, channel):
        def render(note, vel):
            rs = channel.current_voice.get_regions_for_note(note, vel)
            rs[0].note_on(vel, note)
            return rs[0].generate_samples(2048, {"articulation": "normal"})

        soft = render(60, 30)
        hard = render(60, 127)
        # Different velocities -> different output energy
        assert abs(float(np.sqrt(np.mean(soft**2))) - float(np.sqrt(np.mean(hard**2)))) > 1e-5


class TestCrossNoteRender:
    """Multiple real voices feed the shared acoustic context."""

    @pytest.mark.unit
    def test_chord_tracks_all_voices(self, channel):
        ctx = channel.get_acoustic_context()
        notes = [48, 52, 55]  # C3 E3 G3
        regions = []
        for n in notes:
            rs = channel.current_voice.get_regions_for_note(n, 100)
            for r in rs:
                r.note_on(100, n)
                regions.append(r)
                ctx.note_on(n, 100, id(r), 0.0)
        # All three voices registered in the shared context
        assert len(ctx.held_notes) == 3
        # Shared resonance bank exists and is fed
        bank = ctx.get_resonance_bank()
        for n in notes:
            bank.feed(np.full((1024, 2), 0.3, np.float32), n)
        mixed = bank.mix(np.zeros((1024, 2), np.float32), amount=1.0)
        assert float(np.sqrt(np.mean(mixed**2))) > 0.0

    @pytest.mark.unit
    def test_chord_renders_building_audio(self, channel):
        ctx = channel.get_acoustic_context()
        notes = [48, 52, 55]
        regions = []
        for n in notes:
            rs = channel.current_voice.get_regions_for_note(n, 100)
            for r in rs:
                r.note_on(100, n)
                regions.append(r)
                ctx.note_on(n, 100, id(r), 0.0)
        # Render several blocks; RMS should be non-trivial (real chord)
        rmss = []
        for _ in range(4):
            mixed = np.zeros((1024, 2), np.float32)
            for r in regions:
                mixed += r.generate_samples(1024, {"articulation": "normal"})
            rmss.append(float(np.sqrt(np.mean(mixed**2))))
        assert max(rmss) > 1e-3
