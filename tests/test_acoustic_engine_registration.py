"""Tests for acoustic behavior layer enable/registration hook."""

from __future__ import annotations

from synth.engines.acoustic.acoustic_behavior_region import AcousticBehaviorRegion
from synth.engines.acoustic.engine import (
    ACOUSTIC_BEHAVIOR_FEATURE,
    AcousticBehaviorFeature,
    is_acoustic_behavior_registered,
)
from synth.engines.synthesis_engine import SynthesisEngineRegistry
from synth.processing.channel import Channel
from synth.processing.voice.voice_factory import VoiceFactory
from synth.synthesizers.rendering import ModernXGSynthesizer


def _make_channel() -> Channel:
    registry = SynthesisEngineRegistry()
    factory = VoiceFactory(registry)
    return Channel(0, factory, 44100, None)


def test_channel_flag_disables_wrap():
    ch = _make_channel()
    ch.set_acoustic_behavior_enabled(False)
    assert ch.get_acoustic_context() is None
    ch.set_acoustic_behavior_enabled(True)
    assert ch.get_acoustic_context() is not None


def test_modernxg_flag_disables_layer():
    synth = ModernXGSynthesizer(sample_rate=44100, max_channels=2, acoustic_behavior=False)
    synth.load_soundfont("tests/ref.sf2")
    synth.set_channel_program(0, 0, 0)
    synth.process_midi_message(bytes([0x90, 60, 100]))

    ch = synth.channels[0]
    assert ch.get_acoustic_context() is None
    active = list(ch.active_voices.values())
    assert active, "expected an active voice after note-on"
    region = active[0].regions[0]
    assert not isinstance(region, AcousticBehaviorRegion)

    # Re-enable and trigger a fresh note (note-off then new note number).
    synth.set_acoustic_behavior_enabled(True)
    synth.process_midi_message(bytes([0x80, 60, 0]))
    synth.process_midi_message(bytes([0x90, 64, 100]))

    assert ch.get_acoustic_context() is not None
    active2 = [vi for vi in ch.active_voices.values() if vi.note == 64]
    assert active2, "expected an active voice for note 64 after second note-on"
    region2 = active2[0].regions[0]
    assert isinstance(region2, AcousticBehaviorRegion)


def test_feature_registered():
    # SynthesisEngineRegistry has no register_feature; the feature lives in the
    # module-level registry exposed by the engine module.
    if hasattr(SynthesisEngineRegistry, "register_feature"):
        synth = ModernXGSynthesizer(sample_rate=44100, max_channels=1)
        feature = synth.engine_registry.get_feature(ACOUSTIC_BEHAVIOR_FEATURE)
        assert feature is not None
    else:
        # Constructing the feature descriptor must succeed and register it.
        feat = AcousticBehaviorFeature()
        feat.register()
        assert is_acoustic_behavior_registered()
        assert feat.name == ACOUSTIC_BEHAVIOR_FEATURE
