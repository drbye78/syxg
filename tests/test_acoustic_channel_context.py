"""Tests for the shared per-channel acoustic context (cross-note state)."""

from __future__ import annotations

import pytest

from synth.engines.acoustic.behavior_config import BehaviorConfig, InstrumentGroup
from synth.engines.acoustic.channel_context import ChannelAcousticContext


class TestHeldNoteTracking:
    """The context must track all sounding notes across voices."""

    @pytest.mark.unit
    def test_note_on_registers(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        assert 1 in ctx.held_notes
        assert ctx.held_notes[1].velocity == 100
        assert ctx.held_notes[1].note == 60

    @pytest.mark.unit
    def test_note_off_clears(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        ctx.note_off(60, 1, 0.0)
        assert 1 not in ctx.held_notes

    @pytest.mark.unit
    def test_multiple_voices_same_note(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        ctx.note_on(60, 90, 2, 0.0)
        # Both voices tracked under their own ids
        assert 1 in ctx.held_notes and 2 in ctx.held_notes
        # note_off by voice_id, not note, so the note stays until both release
        ctx.note_off(60, 1, 0.0)
        assert 1 not in ctx.held_notes
        assert 2 in ctx.held_notes
        ctx.note_off(60, 2, 0.0)
        assert 2 not in ctx.held_notes


class TestPhraseDetection:
    """Held-chord / register detection drives cross-note behavior."""

    @pytest.mark.unit
    def test_single_note_not_held_chord(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        assert ctx.phrase.held_count == 1
        assert ctx.phrase.is_held_chord is False

    @pytest.mark.unit
    def test_three_notes_is_held_chord(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        ctx.note_on(64, 90, 2, 0.0)
        ctx.note_on(67, 80, 3, 0.0)
        assert ctx.phrase.held_count == 3
        assert ctx.phrase.is_held_chord is True
        # Register centroid near the mean of 60/64/67
        assert 60.0 <= ctx.phrase.register_centroid <= 67.0


class TestDetunePool:
    """Section voices claim deterministic, non-overlapping detune offsets."""

    @pytest.mark.unit
    def test_claim_and_release(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        off1 = ctx.claim_detune_offset(1)
        # Same voice returns same offset
        assert ctx.claim_detune_offset(1) == off1
        ctx.release_detune_offset(1)
        # After release the slot is free again
        assert 1 not in ctx._claimed_offsets

    @pytest.mark.unit
    def test_solo_mode_no_detune(self):
        cfg = BehaviorConfig.for_group(InstrumentGroup.ACOUSTIC_PIANO)
        ctx = ChannelAcousticContext(44100, 0, cfg)
        # Piano is solo mode -> no detune spread
        assert ctx.claim_detune_offset(1) == 0.0


class TestSerialization:
    """Context state must survive JSON round-trip (no pickle)."""

    @pytest.mark.unit
    def test_to_from_dict(self):
        ctx = ChannelAcousticContext(44100, 3, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        ctx.update_controller("sustain", 1.0)
        data = ctx.to_dict()
        restored = ChannelAcousticContext.from_dict(data, 44100)
        assert restored.channel_number == 3
        assert restored.sustain_pedal is True
        # held_notes keyed by voice_id
        assert 1 in restored.held_notes
        assert restored.held_notes[1].note == 60


class TestResonanceBus:
    """The shared resonance bank is created lazily and fed by all voices."""

    @pytest.mark.unit
    def test_lazy_bank_created_once(self):
        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        bank1 = ctx.get_resonance_bank()
        bank2 = ctx.get_resonance_bank()
        assert bank1 is bank2

    @pytest.mark.unit
    def test_feed_produces_audible_mix(self):
        import numpy as np

        ctx = ChannelAcousticContext(44100, 0, BehaviorConfig())
        ctx.note_on(60, 100, 1, 0.0)
        ctx.note_on(64, 90, 2, 0.0)
        bank = ctx.get_resonance_bank()
        for n in (60, 64):
            bank.feed(np.full((1024, 2), 0.3, np.float32), n)
        mixed = bank.mix(np.zeros((1024, 2), np.float32), amount=1.0)
        assert mixed.shape == (1024, 2)
        assert float(np.sqrt(np.mean(mixed**2))) > 0.0
