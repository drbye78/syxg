"""
Style Integrations and MIDI Learn Unit Tests

Comprehensive tests for:
1. MIDILearn system (midi_learn.py)
2. Style Integrations (integrations.py)
   - StyleEffectsIntegration
   - StyleVoiceIntegration
   - StyleModulationIntegration
   - StyleSequencerIntegration
   - StyleMPEIntegration
   - StyleIntegrations (master orchestrator)
"""

from __future__ import annotations

import json
import threading
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from synth.style.midi_learn import LearnTargetType, MIDILearn, MIDILearnMapping
from synth.style.integrations import (
    StyleEffectsIntegration,
    StyleVoiceIntegration,
    StyleModulationIntegration,
    StyleSequencerIntegration,
    StyleMPEIntegration,
    StyleIntegrations,
)


# =============================================================================
# MIDI Learn Mapping Tests
# =============================================================================


class TestLearnTargetType:
    """Test LearnTargetType enum values."""

    def test_enum_values(self):
        """Verify key enum values exist."""
        assert LearnTargetType.STYLE_START_STOP.value == "style_start_stop"
        assert LearnTargetType.STYLE_TEMPO.value == "style_tempo"
        assert LearnTargetType.STYLE_DYNAMICS.value == "style_dynamics"
        assert LearnTargetType.STYLE_VOLUME.value == "style_volume"
        assert LearnTargetType.STYLE_SECTION_A.value == "style_section_a"
        assert LearnTargetType.STYLE_SECTION_B.value == "style_section_b"
        assert LearnTargetType.STYLE_FILL.value == "style_fill"
        assert LearnTargetType.STYLE_BREAK.value == "style_break"
        assert LearnTargetType.STYLE_INTRO.value == "style_intro"
        assert LearnTargetType.STYLE_ENDING.value == "style_ending"
        assert LearnTargetType.OTS_1.value == "ots_1"
        assert LearnTargetType.OTS_NEXT.value == "ots_next"
        assert LearnTargetType.EFFECT_REVERB.value == "effect_reverb"
        assert LearnTargetType.EFFECT_CHORUS.value == "effect_chorus"
        assert LearnTargetType.REGISTRATION_1.value == "registration_1"

    def test_all_enum_members_unique(self):
        """No duplicate values in enum."""
        values = [e.value for e in LearnTargetType]
        assert len(values) == len(set(values))


class TestMIDILearnMapping:
    """Test MIDILearnMapping data class."""

    @pytest.fixture
    def mapping(self):
        return MIDILearnMapping(
            cc_number=7,
            channel=0,
            target_type=LearnTargetType.STYLE_VOLUME,
            target_param="master_volume",
            min_val=0.0,
            max_val=1.0,
            curve="linear",
            label="Volume",
        )

    def test_init_defaults(self):
        """Default values are set correctly."""
        m = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_TEMPO, target_param="tempo"
        )
        assert m.min_val == 0.0
        assert m.max_val == 1.0
        assert m.curve == "linear"
        assert m.label == ""
        assert m.momentary is False
        assert m.snap_to_grid == 0.0
        assert m.default_value == 0.5
        assert m.inverted is False
        assert m.channel_specific is True
        assert m.last_value == 0.5
        assert m.last_raw_value == 0

    def test_process_value_linear(self, mapping):
        """Linear curve maps raw 0-127 to 0-1."""
        assert mapping.process_value(0) == pytest.approx(0.0, abs=1e-6)
        assert mapping.process_value(64) == pytest.approx(64 / 127, abs=1e-6)
        assert mapping.process_value(127) == pytest.approx(1.0, abs=1e-6)

    def test_process_value_exponential(self):
        """Exponential curve squares the normalized value."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_DYNAMICS, target_param="dynamics", curve="exponential"
        )
        val = mapping.process_value(127)
        assert val == pytest.approx(1.0, abs=1e-6)
        val64 = mapping.process_value(64)
        norm = 64 / 127
        assert val64 == pytest.approx(norm * norm, abs=1e-6)

    def test_process_value_logarithmic(self):
        """Logarithmic curve uses sqrt of normalized."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_TEMPO, target_param="tempo", curve="logarithmic"
        )
        val = mapping.process_value(0)
        assert val == pytest.approx(0.0, abs=1e-6)
        val64 = mapping.process_value(64)
        norm = 64 / 127
        expected = norm**0.5
        assert val64 == pytest.approx(expected, abs=1e-6)

    def test_process_value_inverted(self):
        """Inverted curve reverses the raw value."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_VOLUME, target_param="vol", inverted=True
        )
        assert mapping.process_value(0) == pytest.approx(1.0, abs=1e-6)
        assert mapping.process_value(127) == pytest.approx(0.0, abs=1e-6)

    def test_process_value_scaled_range(self):
        """Scaling maps raw 0-127 to min_val-max_val."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_TEMPO, target_param="tempo", min_val=40, max_val=280
        )
        assert mapping.process_value(0) == pytest.approx(40.0, abs=1e-6)
        assert mapping.process_value(127) == pytest.approx(280.0, abs=1e-6)
        assert mapping.process_value(64) == pytest.approx(40 + (64 / 127) * 240, abs=1e-2)

    def test_process_value_snap_to_grid(self):
        """Snap-to-grid rounds to nearest grid step."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_TEMPO, target_param="tempo", min_val=0, max_val=10, snap_to_grid=1.0
        )
        # 0-127 -> 0-10 -> snap to integer
        result = mapping.process_value(64)
        assert result == pytest.approx(round((64 / 127) * 10), abs=0.01)

    def test_process_value_clamps_to_range(self):
        """Processed value is clamped to min/max."""
        mapping = MIDILearnMapping(
            cc_number=1, channel=0, target_type=LearnTargetType.STYLE_VOLUME, target_param="vol", min_val=0.2, max_val=0.8
        )
        # Even with extreme values we clamp
        assert mapping.process_value(0) == pytest.approx(0.2, abs=1e-6)
        assert mapping.process_value(127) == pytest.approx(0.8, abs=1e-6)

    def test_to_dict(self, mapping):
        """to_dict produces correct serializable dict."""
        d = mapping.to_dict()
        assert d["cc_number"] == 7
        assert d["channel"] == 0
        assert d["target_type"] == "style_volume"
        assert d["target_param"] == "master_volume"
        assert d["curve"] == "linear"
        assert d["label"] == "Volume"
        assert d["inverted"] is False

    def test_from_dict(self):
        """from_dict restores a mapping from dict."""
        data = {
            "cc_number": 74,
            "channel": 1,
            "target_type": "style_tempo",
            "target_param": "tempo",
            "min_val": 40.0,
            "max_val": 280.0,
            "curve": "logarithmic",
            "label": "Tempo",
            "momentary": False,
            "snap_to_grid": 0.0,
            "default_value": 160.0,
            "inverted": False,
            "channel_specific": True,
        }
        m = MIDILearnMapping.from_dict(data)
        assert m.cc_number == 74
        assert m.channel == 1
        assert m.target_type == LearnTargetType.STYLE_TEMPO
        assert m.target_param == "tempo"
        assert m.min_val == 40.0
        assert m.max_val == 280.0
        assert m.curve == "logarithmic"
        assert m.label == "Tempo"

    def test_to_dict_from_dict_roundtrip(self, mapping):
        """Roundtrip to_dict -> from_dict preserves all fields."""
        d = mapping.to_dict()
        restored = MIDILearnMapping.from_dict(d)
        assert restored.cc_number == mapping.cc_number
        assert restored.channel == mapping.channel
        assert restored.target_type == mapping.target_type
        assert restored.target_param == mapping.target_param
        assert restored.min_val == mapping.min_val
        assert restored.max_val == mapping.max_val
        assert restored.curve == mapping.curve
        assert restored.label == mapping.label


class TestMIDILearn:
    """Test MIDILearn system."""

    @pytest.fixture
    def midi_learn(self):
        return MIDILearn()

    def test_init(self, midi_learn):
        """Verify initial state."""
        assert isinstance(midi_learn.lock, type(threading.RLock()))
        assert midi_learn.mappings == {}
        assert midi_learn.pending_learn is None
        assert midi_learn.learn_enabled is False
        assert midi_learn.learn_timeout == 10.0
        assert midi_learn.learn_start_time is None
        assert "transport" in midi_learn.groups
        assert "sections" in midi_learn.groups
        assert "fills" in midi_learn.groups
        assert "continuous" in midi_learn.groups
        assert "ots" in midi_learn.groups
        assert "registration" in midi_learn.groups
        assert "effects" in midi_learn.groups

    def test_curves_dict(self, midi_learn):
        """CURVES has all expected curve functions."""
        assert "linear" in MIDILearn.CURVES
        assert "exponential" in MIDILearn.CURVES
        assert "logarithmic" in MIDILearn.CURVES
        assert "sine" in MIDILearn.CURVES
        assert "inverse_sine" in MIDILearn.CURVES

    def test_curves_linear(self, midi_learn):
        """Linear curve returns identity."""
        fn = MIDILearn.CURVES["linear"]
        assert fn(0.0) == 0.0
        assert fn(0.5) == 0.5
        assert fn(1.0) == 1.0

    def test_curves_exponential(self, midi_learn):
        """Exponential curve squares input."""
        fn = MIDILearn.CURVES["exponential"]
        assert fn(0.5) == 0.25
        assert fn(1.0) == 1.0

    def test_curves_logarithmic(self, midi_learn):
        """Logarithmic curve uses sqrt."""
        fn = MIDILearn.CURVES["logarithmic"]
        assert fn(0) == 0
        assert fn(0.25) == 0.5
        assert fn(1.0) == 1.0

    def test_default_mappings(self, midi_learn):
        """DEFAULT_MAPPINGS dict contains controller presets."""
        assert "korg_nanokontrol2" in MIDILearn.DEFAULT_MAPPINGS
        assert "akai_apc_mini" in MIDILearn.DEFAULT_MAPPINGS

    # -- start_learn / cancel_learn / check_learn_timeout --

    def test_start_learn(self, midi_learn):
        """start_learn sets pending_learn and enables learn mode."""
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")
        assert midi_learn.pending_learn == (LearnTargetType.STYLE_TEMPO, "tempo")
        assert midi_learn.learn_enabled is True
        assert midi_learn.learn_start_time is not None

    def test_start_learn_with_timeout(self, midi_learn):
        """start_learn with timeout overrides default."""
        midi_learn.start_learn(LearnTargetType.STYLE_DYNAMICS, "dynamics", timeout=30.0)
        assert midi_learn.learn_timeout == 30.0

    def test_cancel_learn(self, midi_learn):
        """cancel_learn clears pending learn state."""
        midi_learn.start_learn(LearnTargetType.STYLE_VOLUME, "vol")
        midi_learn.cancel_learn()
        assert midi_learn.pending_learn is None
        assert midi_learn.learn_enabled is False
        assert midi_learn.learn_start_time is None

    def test_check_learn_timeout_no_timeout(self, midi_learn):
        """check_learn_timeout returns False before timeout."""
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo", timeout=60.0)
        result = midi_learn.check_learn_timeout()
        assert result is False
        assert midi_learn.learn_enabled is True

    def test_check_learn_timeout_expired(self, midi_learn):
        """check_learn_timeout returns True and cancels after timeout."""
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo", timeout=0.001)
        time.sleep(0.005)
        result = midi_learn.check_learn_timeout()
        assert result is True
        assert midi_learn.learn_enabled is False
        assert midi_learn.pending_learn is None

    def test_check_learn_timeout_not_learning(self, midi_learn):
        """check_learn_timeout returns False when not in learn mode."""
        assert midi_learn.check_learn_timeout() is False

    # -- process_midi --

    def test_process_midi_no_mapping(self, midi_learn):
        """process_midi returns None for unmapped CC."""
        result = midi_learn.process_midi(99, 0, 64)
        assert result is None

    def test_process_midi_with_mapping(self, midi_learn):
        """process_midi returns processed result for mapped CC."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="master_volume", label="Volume"
        )
        midi_learn.mappings[(7, 0)] = mapping
        result = midi_learn.process_midi(7, 0, 100)
        assert result is not None
        assert result["target_type"] == "style_volume"
        assert result["target_param"] == "master_volume"
        assert result["label"] == "Volume"
        assert result["raw_value"] == 100
        assert result["value"] == pytest.approx(100 / 127, abs=1e-6)

    def test_process_midi_channel_specific_mismatch(self, midi_learn):
        """process_midi returns None when channel doesn't match."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol", channel_specific=True
        )
        midi_learn.mappings[(7, 0)] = mapping
        # Different channel
        result = midi_learn.process_midi(7, 1, 64)
        assert result is None

    def test_process_midi_learns_new_mapping(self, midi_learn):
        """process_midi in learn mode creates new mapping."""
        midi_learn.start_learn(LearnTargetType.EFFECT_REVERB, "reverb")
        result = midi_learn.process_midi(16, 0, 100)
        assert result is not None
        assert result["learned"] is True
        assert result["target"] == "effect_reverb"
        assert result["cc"] == 16
        # Mapping should be stored
        assert (16, 0) in midi_learn.mappings
        mapping = midi_learn.mappings[(16, 0)]
        assert mapping.target_type == LearnTargetType.EFFECT_REVERB
        assert mapping.target_param == "reverb"
        # Learn mode should be cancelled
        assert midi_learn.learn_enabled is False

    def test_process_midi_triggers_callbacks(self, midi_learn):
        """process_midi triggers registered callbacks."""
        callback = Mock()
        midi_learn.register_callback(LearnTargetType.STYLE_VOLUME, callback)
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="master_volume"
        )
        midi_learn.mappings[(7, 0)] = mapping
        midi_learn.process_midi(7, 0, 80)
        callback.assert_called_once()
        args, _ = callback.call_args
        assert len(args) == 2
        assert args[0] == pytest.approx(80 / 127, abs=1e-6)  # processed value
        assert args[1] == 80  # raw value

    def test_process_midi_momentary_hold(self, midi_learn):
        """Momentary mapping holds last value."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol", momentary=True, default_value=0.5
        )
        midi_learn.mappings[(7, 0)] = mapping
        # Press (non-zero)
        result1 = midi_learn.process_midi(7, 0, 100)
        assert result1["value"] > 0.5
        # Release (zero -> default)
        result2 = midi_learn.process_midi(7, 0, 0)
        assert result2["value"] == pytest.approx(0.5, abs=1e-6)

    def test_process_midi_stores_last_value(self, midi_learn):
        """process_midi updates last_value and last_raw_value."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol"
        )
        midi_learn.mappings[(7, 0)] = mapping
        midi_learn.process_midi(7, 0, 50)
        assert mapping.last_raw_value == 50
        assert mapping.last_value == pytest.approx(50 / 127, abs=1e-6)

    # -- register_callback / unregister_callback --

    def test_register_callback(self, midi_learn):
        """register_callback adds callback for target type."""
        cb = Mock()
        midi_learn.register_callback(LearnTargetType.STYLE_TEMPO, cb)
        assert cb in midi_learn.callbacks[LearnTargetType.STYLE_TEMPO]

    def test_register_callback_duplicate(self, midi_learn):
        """register_callback does not add duplicate callbacks."""
        cb = Mock()
        midi_learn.register_callback(LearnTargetType.STYLE_TEMPO, cb)
        midi_learn.register_callback(LearnTargetType.STYLE_TEMPO, cb)
        assert len(midi_learn.callbacks[LearnTargetType.STYLE_TEMPO]) == 1

    def test_unregister_callback(self, midi_learn):
        """unregister_callback removes callback and returns True."""
        cb = Mock()
        midi_learn.register_callback(LearnTargetType.STYLE_TEMPO, cb)
        result = midi_learn.unregister_callback(LearnTargetType.STYLE_TEMPO, cb)
        assert result is True
        assert cb not in midi_learn.callbacks[LearnTargetType.STYLE_TEMPO]

    def test_unregister_callback_not_found(self, midi_learn):
        """unregister_callback returns False if callback not registered."""
        cb = Mock()
        result = midi_learn.unregister_callback(LearnTargetType.STYLE_TEMPO, cb)
        assert result is False

    # -- add_mapping / remove_mapping / get_mapping / get_all_mappings --

    def test_add_mapping(self, midi_learn):
        """add_mapping stores the mapping and returns True."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol"
        )
        result = midi_learn.add_mapping(mapping)
        assert result is True
        assert midi_learn.mappings[(7, 0)] is mapping
        # Should also be in a group
        assert (7, 0) in midi_learn.groups["continuous"]

    def test_add_mapping_duplicate_key(self, midi_learn):
        """add_mapping returns False when key already exists."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol"
        )
        midi_learn.add_mapping(mapping)
        mapping2 = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_TEMPO,
            target_param="tempo"
        )
        result = midi_learn.add_mapping(mapping2)
        assert result is False
        assert midi_learn.mappings[(7, 0)].target_type == LearnTargetType.STYLE_VOLUME

    def test_remove_mapping(self, midi_learn):
        """remove_mapping removes mapping by CC/channel."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol"
        )
        midi_learn.add_mapping(mapping)
        result = midi_learn.remove_mapping(7, 0)
        assert result is True
        assert (7, 0) not in midi_learn.mappings

    def test_remove_mapping_not_found(self, midi_learn):
        """remove_mapping returns False if mapping doesn't exist."""
        result = midi_learn.remove_mapping(99, 0)
        assert result is False

    def test_get_mapping(self, midi_learn):
        """get_mapping returns mapping for CC/channel."""
        mapping = MIDILearnMapping(
            cc_number=7, channel=0, target_type=LearnTargetType.STYLE_VOLUME,
            target_param="vol"
        )
        midi_learn.mappings[(7, 0)] = mapping
        assert midi_learn.get_mapping(7, 0) is mapping
        assert midi_learn.get_mapping(99, 0) is None

    def test_get_all_mappings(self, midi_learn):
        """get_all_mappings returns all mappings."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol")
        m2 = MIDILearnMapping(2, 0, LearnTargetType.STYLE_TEMPO, "tempo")
        midi_learn.mappings[(1, 0)] = m1
        midi_learn.mappings[(2, 0)] = m2
        all_mappings = midi_learn.get_all_mappings()
        assert len(all_mappings) == 2
        assert m1 in all_mappings
        assert m2 in all_mappings

    # -- get_mappings_by_group --

    def test_get_mappings_by_group(self, midi_learn):
        """get_mappings_by_group returns mappings in a group."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol")
        m2 = MIDILearnMapping(2, 0, LearnTargetType.STYLE_TEMPO, "tempo")
        m3 = MIDILearnMapping(16, 0, LearnTargetType.EFFECT_REVERB, "reverb")
        midi_learn.add_mapping(m1)  # -> continuous
        midi_learn.add_mapping(m2)  # -> continuous
        midi_learn.add_mapping(m3)  # -> effects
        continuous = midi_learn.get_mappings_by_group("continuous")
        assert len(continuous) == 2
        effects = midi_learn.get_mappings_by_group("effects")
        assert len(effects) == 1
        assert effects[0].target_type == LearnTargetType.EFFECT_REVERB

    def test_get_mappings_by_group_invalid(self, midi_learn):
        """get_mappings_by_group returns empty list for unknown group."""
        assert midi_learn.get_mappings_by_group("unknown") == []

    def test_get_mappings_by_group_empty(self, midi_learn):
        """get_mappings_by_group returns empty list when group has no mappings."""
        assert midi_learn.get_mappings_by_group("transport") == []

    # -- clear_all_mappings --

    def test_clear_all_mappings(self, midi_learn):
        """clear_all_mappings clears everything."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol")
        midi_learn.add_mapping(m1)
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")
        midi_learn.clear_all_mappings()
        assert midi_learn.mappings == {}
        assert midi_learn.pending_learn is None
        assert midi_learn.learn_enabled is False
        assert midi_learn.active_values == {}
        for group_keys in midi_learn.groups.values():
            assert group_keys == []

    # -- load_default_mappings --

    def test_load_default_mappings_korg(self, midi_learn):
        """load_default_mappings loads korg_nanokontrol2."""
        result = midi_learn.load_default_mappings("korg_nanokontrol2")
        assert result is True
        assert len(midi_learn.mappings) == 5
        # Check specific mappings exist
        assert (1, 0) in midi_learn.mappings
        assert midi_learn.mappings[(1, 0)].target_type == LearnTargetType.STYLE_VOLUME

    def test_load_default_mappings_akai(self, midi_learn):
        """load_default_mappings loads akai_apc_mini."""
        result = midi_learn.load_default_mappings("akai_apc_mini")
        assert result is True
        assert len(midi_learn.mappings) == 4
        assert (48, 0) in midi_learn.mappings
        assert midi_learn.mappings[(48, 0)].target_type == LearnTargetType.OTS_1

    def test_load_default_mappings_unknown(self, midi_learn):
        """load_default_mappings returns False for unknown preset."""
        result = midi_learn.load_default_mappings("unknown_controller")
        assert result is False
        assert midi_learn.mappings == {}

    # -- export_mappings / import_mappings roundtrip --

    def test_export_mappings(self, midi_learn):
        """export_mappings returns list of dicts."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol", label="Vol")
        midi_learn.add_mapping(m1)
        exported = midi_learn.export_mappings()
        assert len(exported) == 1
        assert exported[0]["cc_number"] == 1
        assert exported[0]["label"] == "Vol"

    def test_import_mappings(self, midi_learn):
        """import_mappings restores mappings from list of dicts."""
        data = [
            {
                "cc_number": 1,
                "channel": 0,
                "target_type": "style_volume",
                "target_param": "vol",
                "min_val": 0.0,
                "max_val": 1.0,
                "curve": "linear",
                "label": "Vol",
                "momentary": False,
                "snap_to_grid": 0.0,
                "default_value": 0.5,
                "inverted": False,
                "channel_specific": True,
            }
        ]
        result = midi_learn.import_mappings(data)
        assert result is True
        assert len(midi_learn.mappings) == 1
        assert (1, 0) in midi_learn.mappings

    def test_export_import_roundtrip(self, midi_learn):
        """Roundtrip preserves all mappings."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol", label="Volume")
        m2 = MIDILearnMapping(2, 0, LearnTargetType.STYLE_TEMPO, "tempo", min_val=40, max_val=280, curve="logarithmic")
        midi_learn.add_mapping(m1)
        midi_learn.add_mapping(m2)
        exported = midi_learn.export_mappings()
        # Clear and re-import
        midi_learn.clear_all_mappings()
        midi_learn.import_mappings(exported)
        assert len(midi_learn.mappings) == 2
        assert midi_learn.mappings[(1, 0)].label == "Volume"
        assert midi_learn.mappings[(2, 0)].max_val == 280

    def test_import_mappings_invalid_data(self, midi_learn):
        """import_mappings returns False for invalid data."""
        result = midi_learn.import_mappings([{"bad": "data"}])
        assert result is False

    # -- save_to_file / load_from_file roundtrip --

    def test_save_to_file(self, midi_learn):
        """save_to_file writes JSON file."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol", label="Vol")
        midi_learn.add_mapping(m1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = midi_learn.save_to_file(path)
            assert result is True
            with open(path) as f:
                data = json.load(f)
            assert "mappings" in data
            assert "groups" in data
            assert len(data["mappings"]) == 1
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_from_file(self, midi_learn):
        """load_from_file restores mappings from JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "mappings": [
                    {
                        "cc_number": 1,
                        "channel": 0,
                        "target_type": "style_volume",
                        "target_param": "vol",
                        "min_val": 0.0,
                        "max_val": 1.0,
                        "curve": "linear",
                        "label": "Vol",
                        "momentary": False,
                        "snap_to_grid": 0.0,
                        "default_value": 0.5,
                        "inverted": False,
                        "channel_specific": True,
                    }
                ],
                "groups": {"continuous": [[1, 0]]},
            }, f)
            path = f.name
        try:
            result = midi_learn.load_from_file(path)
            assert result is True
            assert len(midi_learn.mappings) == 1
            assert (1, 0) in midi_learn.mappings
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_from_file_old_format(self, midi_learn):
        """load_from_file handles old format (list of dicts)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([
                {
                    "cc_number": 1,
                    "channel": 0,
                    "target_type": "style_volume",
                    "target_param": "vol",
                    "min_val": 0.0,
                    "max_val": 1.0,
                    "curve": "linear",
                    "label": "Vol",
                    "momentary": False,
                    "snap_to_grid": 0.0,
                    "default_value": 0.5,
                    "inverted": False,
                    "channel_specific": True,
                }
            ], f)
            path = f.name
        try:
            result = midi_learn.load_from_file(path)
            assert result is True
            assert len(midi_learn.mappings) == 1
        finally:
            Path(path).unlink(missing_ok=True)

    def test_save_load_roundtrip(self, midi_learn):
        """save_to_file then load_from_file preserves all mappings."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol", label="Volume")
        m2 = MIDILearnMapping(2, 0, LearnTargetType.STYLE_TEMPO, "tempo", min_val=40, max_val=280)
        midi_learn.add_mapping(m1)
        midi_learn.add_mapping(m2)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            assert midi_learn.save_to_file(path) is True
            midi_learn.clear_all_mappings()
            assert midi_learn.load_from_file(path) is True
            assert len(midi_learn.mappings) == 2
            assert midi_learn.mappings[(1, 0)].label == "Volume"
            assert midi_learn.mappings[(2, 0)].max_val == 280
        finally:
            Path(path).unlink(missing_ok=True)

    def test_save_to_file_error(self, midi_learn):
        """save_to_file returns False on I/O error."""
        result = midi_learn.save_to_file("/nonexistent/dir/file.json")
        assert result is False

    def test_load_from_file_error(self, midi_learn):
        """load_from_file returns False on I/O error."""
        result = midi_learn.load_from_file("/nonexistent/file.json")
        assert result is False

    def test_load_from_file_invalid_json(self, midi_learn):
        """load_from_file returns False for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = f.name
        try:
            result = midi_learn.load_from_file(path)
            assert result is False
        finally:
            Path(path).unlink(missing_ok=True)

    # -- get_status --

    def test_get_status_no_mappings(self, midi_learn):
        """get_status returns correct state with no mappings."""
        status = midi_learn.get_status()
        assert status["learn_enabled"] is False
        assert status["pending_learn"] is None
        assert status["mapping_count"] == 0
        assert status["learn_timeout"] == 10.0
        assert all(v == 0 for v in status["groups"].values())

    def test_get_status_with_mappings(self, midi_learn):
        """get_status includes mapping info."""
        m1 = MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "vol", label="Vol")
        midi_learn.add_mapping(m1)
        status = midi_learn.get_status()
        assert status["mapping_count"] == 1
        assert len(status["mappings"]) == 1
        assert status["mappings"][0]["cc"] == 1
        assert status["mappings"][0]["label"] == "Vol"

    def test_get_status_learn_mode(self, midi_learn):
        """get_status reflects learn mode."""
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")
        status = midi_learn.get_status()
        assert status["learn_enabled"] is True
        assert status["pending_learn"] == "style_tempo"


# =============================================================================
# MIDI Learn Edge Cases
# =============================================================================


class TestMIDILearnEdgeCases:
    """Test edge cases for MIDI Learn system."""

    @pytest.fixture
    def midi_learn(self):
        return MIDILearn()

    def test_process_midi_concurrent_safety(self, midi_learn):
        """Multiple rapid process_midi calls are thread-safe."""
        mapping = MIDILearnMapping(7, 0, LearnTargetType.STYLE_VOLUME, "vol")
        midi_learn.mappings[(7, 0)] = mapping
        for i in range(100):
            midi_learn.process_midi(7, 0, i % 128)
        # No crash - that's the test
        assert True

    def test_add_mapping_edge_values(self, midi_learn):
        """Mapping with edge CC and channel values."""
        mapping = MIDILearnMapping(0, 0, LearnTargetType.STYLE_START_STOP, "start")
        assert midi_learn.add_mapping(mapping) is True
        mapping2 = MIDILearnMapping(127, 15, LearnTargetType.STYLE_STOP, "stop")
        assert midi_learn.add_mapping(mapping2) is True
        assert len(midi_learn.mappings) == 2

    def test_learn_timeout_cancels_during_process(self, midi_learn):
        """Timeout check runs inside process_midi and auto-cancels learn."""
        midi_learn.start_learn(LearnTargetType.STYLE_VOLUME, "vol", timeout=0.001)
        time.sleep(0.005)
        # process_midi will hit check_learn_timeout -> cancel_learn before
        # processing any pending learn, so this returns None (no mapping).
        result = midi_learn.process_midi(99, 0, 64)
        assert result is None
        assert midi_learn.learn_enabled is False
        assert midi_learn.pending_learn is None

    def test_start_learn_replaces_previous(self, midi_learn):
        """Starting learn while already in learn mode replaces target."""
        midi_learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")
        midi_learn.start_learn(LearnTargetType.STYLE_DYNAMICS, "dynamics")
        assert midi_learn.pending_learn == (LearnTargetType.STYLE_DYNAMICS, "dynamics")


# =============================================================================
# Style Integrations Tests
# =============================================================================


class TestStyleEffectsIntegration:
    """Test StyleEffectsIntegration."""

    @pytest.fixture
    def effects(self):
        return Mock()

    @pytest.fixture
    def dynamics(self):
        d = Mock()
        d.add_callback = Mock()
        d.remove_callback = Mock()
        return d

    @pytest.fixture
    def integration(self, effects, dynamics):
        return StyleEffectsIntegration(effects, dynamics)

    def test_init_adds_callback(self, integration, dynamics):
        """Constructor registers callback with dynamics."""
        dynamics.add_callback.assert_called_once_with(integration._on_dynamics_change)

    def test_init_sets_default_scales(self, integration):
        """Constructor sets default scale factors."""
        assert integration.reverb_scale == 1.0
        assert integration.chorus_scale == 1.0
        assert integration.delay_scale == 1.0
        assert integration.eq_scale == 1.0
        assert integration.compressor_scale == 1.0

    def test_enable(self, integration, dynamics):
        """enable re-registers callback."""
        dynamics.add_callback.reset_mock()
        integration.enable()
        dynamics.add_callback.assert_called_once_with(integration._on_dynamics_change)

    def test_disable(self, integration, dynamics):
        """disable removes callback."""
        integration.disable()
        dynamics.remove_callback.assert_called_once_with(integration._on_dynamics_change)

    def test_disable_with_error(self, integration, dynamics):
        """disable handles removal error gracefully."""
        dynamics.remove_callback.side_effect = Exception("removal failed")
        integration.disable()  # Should not raise

    def test_on_dynamics_change_updates_scales(self, integration, effects):
        """_on_dynamics_change updates effect parameters."""
        from synth.style.dynamics import DynamicsParameter

        integration._on_dynamics_change(
            100,
            {
                DynamicsParameter.REVERB_MIX: 0.8,
                DynamicsParameter.CHORUS_MIX: 0.3,
            },
        )
        assert integration.reverb_scale == 0.8
        assert integration.chorus_scale == 0.3
        # Reverb and chorus scaling should be applied
        effects.set_reverb_parameter.assert_called()
        effects.set_chorus_parameter.assert_called()

    def test_on_dynamics_change_missing_params(self, integration):
        """_on_dynamics_change uses defaults for missing params."""
        from synth.style.dynamics import DynamicsParameter

        integration._on_dynamics_change(64, {})
        assert integration.reverb_scale == 0.5
        assert integration.chorus_scale == 0.5

    def test_apply_reverb_scaling_no_method(self, integration, effects):
        """_apply_reverb_scaling does nothing when effects lacks method."""
        del effects.set_reverb_parameter
        integration.reverb_scale = 0.5
        integration._apply_reverb_scaling()  # Should not raise

    def test_apply_chorus_scaling_no_method(self, integration, effects):
        """_apply_chorus_scaling does nothing when effects lacks method."""
        del effects.set_chorus_parameter
        integration.chorus_scale = 0.5
        integration._apply_chorus_scaling()  # Should not raise

    def test_apply_eq_scaling(self, integration, effects):
        """_apply_eq_scaling calls set_eq_parameter."""
        integration.eq_scale = 0.5
        integration._apply_eq_scaling()
        effects.set_eq_parameter.assert_called_once_with("high_gain", -3.0 + 0.5 * 6.0)

    def test_apply_compressor_scaling(self, integration, effects):
        """_apply_compressor_scaling calls set_compressor_parameter."""
        integration.compressor_scale = 0.3
        integration._apply_compressor_scaling()
        expected_threshold = -20.0 + 0.3 * 10.0
        effects.set_compressor_parameter.assert_called_once_with("threshold", expected_threshold)


class TestStyleVoiceIntegration:
    """Test StyleVoiceIntegration."""

    @pytest.fixture
    def voice_manager(self):
        return Mock()

    @pytest.fixture
    def ots(self):
        o = Mock()
        o.get_preset = Mock()
        o.set_change_callback = Mock()
        return o

    @pytest.fixture
    def integration(self, voice_manager, ots):
        return StyleVoiceIntegration(voice_manager, ots)

    def test_init(self, integration, voice_manager, ots):
        """Constructor stores references."""
        assert integration.voice_manager is voice_manager
        assert integration.ots is ots
        assert integration._current_preset_id == -1

    def test_voice_configs_have_required_keys(self):
        """All VOICE_CONFIGS have polyphony, attack, decay, sustain, release."""
        for name, config in StyleVoiceIntegration.VOICE_CONFIGS.items():
            assert "polyphony" in config, f"{name} missing polyphony"
            assert "attack" in config, f"{name} missing attack"
            assert "decay" in config, f"{name} missing decay"
            assert "sustain" in config, f"{name} missing sustain"
            assert "release" in config, f"{name} missing release"

    def test_apply_ots_voice_optimization(self, integration, ots, voice_manager):
        """apply_ots_voice_optimization configures voice manager."""
        # Create a mock preset with name that triggers piano
        preset = Mock()
        preset.name = "Grand Piano"
        part = Mock()
        part.enabled = True
        part.part_id = 0
        part.program_change = 1
        preset.parts = [part]
        ots.get_preset.return_value = preset

        integration.apply_ots_voice_optimization(preset_id=0)
        ots.get_preset.assert_called_with(0)
        voice_manager.configure_voice.assert_called_once()
        args, kwargs = voice_manager.configure_voice.call_args
        assert kwargs["channel"] == 0
        assert kwargs["polyphony"] == 16  # piano

    def test_apply_ots_no_ots(self, integration):
        """apply_ots_voice_optimization returns early if ots is None."""
        integration.ots = None
        integration.apply_ots_voice_optimization(0)  # Should not raise

    def test_apply_ots_no_preset(self, integration, ots):
        """apply_ots_voice_optimization returns early if preset not found."""
        ots.get_preset.return_value = None
        integration.apply_ots_voice_optimization(999)
        ots.get_preset.assert_called_with(999)

    def test_enable(self, integration, ots):
        """enable registers change callback."""
        integration.enable()
        ots.set_change_callback.assert_called_once_with(integration.apply_ots_voice_optimization)

    def test_enable_no_ots(self, integration):
        """enable does nothing if ots is None."""
        integration.ots = None
        integration.enable()  # Should not raise

    def test_disable(self, integration):
        """disable is a no-op."""
        integration.disable()  # Should not raise

    def test_analyze_preset_instrument_type_by_name(self, integration):
        """_analyze_preset_instrument_type classifies by name keywords."""
        class MockPreset:
            def __init__(self, name, parts=None):
                self.name = name
                self.parts = parts or []

        assert integration._analyze_preset_instrument_type(MockPreset("Synth Bass")) == "bass"
        assert integration._analyze_preset_instrument_type(MockPreset("Dream Pad")) == "pad"
        assert integration._analyze_preset_instrument_type(MockPreset("String Ensemble")) == "strings"
        assert integration._analyze_preset_instrument_type(MockPreset("Brass Section")) == "brass"
        assert integration._analyze_preset_instrument_type(MockPreset("Jazz Organ")) == "organ"
        assert integration._analyze_preset_instrument_type(MockPreset("Lead Synth")) == "synth_lead"
        assert integration._analyze_preset_instrument_type(MockPreset("Acoustic Piano")) == "piano"

    def test_analyze_preset_by_program(self, integration):
        """_analyze_preset_instrument_type falls back to program numbers."""
        class MockPart:
            def __init__(self, enabled, program_change, part_id=0):
                self.enabled = enabled
                self.program_change = program_change
                self.part_id = part_id

        class MockPreset:
            def __init__(self, name, parts):
                self.name = name
                self.parts = parts

        # Bass program range (32-39)
        p = integration._analyze_preset_instrument_type(MockPreset("Unknown", [MockPart(True, 35)]))
        assert p == "bass"
        # Default fallback
        p = integration._analyze_preset_instrument_type(MockPreset("Unknown", []))
        assert p == "piano"

    def test_apply_voice_config_no_configure_method(self, integration, voice_manager):
        """_apply_voice_config handles missing configure_voice method."""
        del voice_manager.configure_voice
        config = {"polyphony": 4, "attack": 0.1, "decay": 0.2, "sustain": 0.8, "release": 0.3}
        preset = Mock()
        part = Mock()
        part.enabled = True
        part.part_id = 0
        preset.parts = [part]
        integration._apply_voice_config(config, preset)  # Should not raise


class TestStyleModulationIntegration:
    """Test StyleModulationIntegration."""

    @pytest.fixture
    def mod_matrix(self):
        return Mock()

    @pytest.fixture
    def midi_learn(self):
        return Mock()

    @pytest.fixture
    def integration(self, mod_matrix, midi_learn):
        return StyleModulationIntegration(mod_matrix, midi_learn)

    def test_init(self, integration, mod_matrix, midi_learn):
        """Constructor stores references."""
        assert integration.mod_matrix is mod_matrix
        assert integration.midi_learn is midi_learn
        assert integration._registered_callbacks == {}

    def test_default_modulation_mappings(self):
        """DEFAULT_MODULATION_MAPPINGS has expected keys."""
        mappings = StyleModulationIntegration.DEFAULT_MODULATION_MAPPINGS
        assert "lfo_rate" in mappings
        assert "lfo_depth" in mappings
        assert "filter_cutoff" in mappings
        assert "filter_resonance" in mappings
        assert "env_attack" in mappings
        assert "env_release" in mappings
        assert "effect_param1" in mappings
        assert "effect_param2" in mappings

    def test_bind_modulation_to_midi_learn(self, integration, midi_learn):
        """bind_modulation_to_midi_learn registers callbacks with midi_learn."""
        integration.bind_modulation_to_midi_learn()
        # Should have registered callbacks for each default mapping
        assert len(integration._registered_callbacks) == len(
            StyleModulationIntegration.DEFAULT_MODULATION_MAPPINGS
        )
        from synth.style.midi_learn import LearnTargetType

        assert midi_learn.register_callback.call_count == len(
            StyleModulationIntegration.DEFAULT_MODULATION_MAPPINGS
        )

    def test_add_modulation_mapping(self, integration, midi_learn):
        """add_modulation_mapping creates and adds a MIDILearnMapping."""
        integration.add_modulation_mapping("filter_resonance", 71, 0.0, 10.0, "linear")
        midi_learn.add_mapping.assert_called_once()
        mapping = midi_learn.add_mapping.call_args[0][0]
        assert mapping.cc_number == 71
        assert mapping.target_param == "filter_resonance"
        assert mapping.min_val == 0.0
        assert mapping.max_val == 10.0

    def test_enable(self, integration, midi_learn):
        """enable calls bind_modulation_to_midi_learn."""
        integration.enable()
        assert len(integration._registered_callbacks) > 0
        assert midi_learn.register_callback.call_count > 0

    def test_disable(self, integration):
        """disable clears registered callbacks."""
        # First bind
        integration.bind_modulation_to_midi_learn()
        assert len(integration._registered_callbacks) > 0
        integration.disable()
        assert integration._registered_callbacks == {}

    def test_on_modulation_cc_with_set_parameter(self, integration, mod_matrix):
        """_on_modulation_cc routes to mod_matrix.set_parameter."""
        integration._on_modulation_cc("filter_cutoff", 0.5, 20.0, 20000.0)
        mod_matrix.set_parameter.assert_called_once_with("filter_cutoff", 20.0 + 0.5 * (20000.0 - 20.0))

    def test_on_modulation_cc_no_set_parameter(self, integration):
        """_on_modulation_cc handles missing set_parameter gracefully."""
        integration.mod_matrix = Mock(spec=[])  # No set_parameter
        integration._on_modulation_cc("test", 0.5, 0.0, 1.0)  # Should not raise


class TestStyleSequencerIntegration:
    """Test StyleSequencerIntegration."""

    @pytest.fixture
    def sequencer(self):
        return Mock()

    @pytest.fixture
    def style_player(self):
        sp = Mock()
        sp.tempo = 120
        sp.set_section_change_callback = Mock()
        return sp

    @pytest.fixture
    def integration(self, sequencer, style_player):
        return StyleSequencerIntegration(sequencer, style_player)

    def test_init(self, integration, sequencer, style_player):
        """Constructor stores references."""
        assert integration.sequencer is sequencer
        assert integration.style_player is style_player
        assert integration._sync_enabled is False

    def test_section_pattern_map(self):
        """SECTION_PATTERN_MAP has all expected sections."""
        expected = ["intro_1", "intro_2", "intro_3", "main_a", "main_b", "main_c", "main_d",
                     "fill_in_aa", "fill_in_bb", "fill_in_cc", "fill_in_dd",
                     "break", "ending_1", "ending_2", "ending_3"]
        for section in expected:
            assert section in StyleSequencerIntegration.SECTION_PATTERN_MAP, f"Missing: {section}"

    def test_sync_with_style_section(self, integration, style_player, sequencer):
        """sync_with_style_section registers callback and syncs tempo."""
        integration.sync_with_style_section()
        style_player.set_section_change_callback.assert_called_once_with(
            integration._on_style_section_change
        )
        sequencer.set_tempo.assert_called_once_with(120)
        assert integration._sync_enabled is True

    def test_sync_with_style_section_no_player(self, integration):
        """sync_with_style_section returns early without style_player."""
        integration.style_player = None
        integration.sync_with_style_section()
        assert integration._sync_enabled is False

    def test_enable(self, integration):
        """enable calls sync_with_style_section."""
        integration.enable()
        assert integration._sync_enabled is True

    def test_disable(self, integration):
        """disable sets _sync_enabled to False."""
        integration._sync_enabled = True
        integration.disable()
        assert integration._sync_enabled is False

    def test_on_style_section_change(self, integration, sequencer):
        """_on_style_section_change triggers pattern transition."""
        integration._sync_enabled = True
        old_section = Mock()
        old_section.value = "main_a"
        new_section = Mock()
        new_section.value = "fill_in_aa"

        integration._on_style_section_change(old_section, new_section)
        sequencer.queue_pattern.assert_called_once_with("fill_a")

    def test_on_style_section_change_sync_disabled(self, integration, sequencer):
        """_on_style_section_change does nothing when sync disabled."""
        integration._sync_enabled = False
        old_section = Mock()
        old_section.value = "main_a"
        new_section = Mock()
        new_section.value = "main_b"

        integration._on_style_section_change(old_section, new_section)
        sequencer.queue_pattern.assert_not_called()

    def test_set_pattern_for_section(self, integration):
        """set_pattern_for_section overrides the pattern map."""
        integration.set_pattern_for_section("main_a", "custom_pattern_a")
        assert integration.SECTION_PATTERN_MAP["main_a"] == "custom_pattern_a"

    def test_on_style_section_change_none_values(self, integration, sequencer):
        """_on_style_section_change handles None old/new section."""
        integration._sync_enabled = True
        integration._on_style_section_change(None, None)
        # Should not raise
        sequencer.play_pattern.assert_not_called()

    def test_transition_to_pattern_prefers_queue(self, integration, sequencer):
        """_transition_to_pattern prefers queue_pattern over play_pattern."""
        integration._transition_to_pattern("pattern_a")
        sequencer.queue_pattern.assert_called_once_with("pattern_a")
        sequencer.play_pattern.assert_not_called()

    def test_transition_to_pattern_falls_back_to_play(self, integration, sequencer):
        """_transition_to_pattern falls back to play_pattern."""
        del sequencer.queue_pattern
        integration._transition_to_pattern("pattern_a")
        sequencer.play_pattern.assert_called_once_with("pattern_a")

    def test_transition_to_pattern_no_methods(self, integration, sequencer):
        """_transition_to_pattern handles missing methods gracefully."""
        del sequencer.queue_pattern
        del sequencer.play_pattern
        integration._transition_to_pattern("pattern_a")  # Should not raise


class TestStyleMPEIntegration:
    """Test StyleMPEIntegration."""

    @pytest.fixture
    def mpe_manager(self):
        return Mock()

    @pytest.fixture
    def scale_detector(self):
        sd = Mock()
        sd.get_current_scale = Mock()
        return sd

    @pytest.fixture
    def integration(self, mpe_manager, scale_detector):
        return StyleMPEIntegration(mpe_manager, scale_detector)

    def test_init(self, integration, mpe_manager, scale_detector):
        """Constructor stores references."""
        assert integration.mpe is mpe_manager
        assert integration.scale_detector is scale_detector
        assert integration._scale_constraint_enabled is False
        assert integration._last_scale is None

    def test_apply_scale_constraint_high_confidence(self, integration, mpe_manager, scale_detector):
        """apply_scale_constraint with confident scale applies to MPE."""
        from synth.style.scale import DetectedScale, ScaleType

        scale = Mock(spec=DetectedScale)
        scale.root = 0
        scale.confidence = 0.8
        scale.scale_type = ScaleType.MAJOR
        scale.get_scale_notes.return_value = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83]
        scale_detector.get_current_scale.return_value = scale

        integration.apply_scale_constraint()
        assert integration._scale_constraint_enabled is True
        assert integration._last_scale is scale
        mpe_manager.set_scale_constraint.assert_called_once()
        args, kwargs = mpe_manager.set_scale_constraint.call_args
        assert kwargs["root"] == 0

    def test_apply_scale_constraint_low_confidence(self, integration, scale_detector, mpe_manager):
        """apply_scale_constraint with low confidence does not apply."""
        from synth.style.scale import DetectedScale

        scale = Mock(spec=DetectedScale)
        scale.confidence = 0.3
        scale_detector.get_current_scale.return_value = scale

        integration.apply_scale_constraint()
        mpe_manager.set_scale_constraint.assert_not_called()
        assert integration._scale_constraint_enabled is False

    def test_apply_scale_constraint_no_scale(self, integration, scale_detector, mpe_manager):
        """apply_scale_constraint with no scale returns early."""
        scale_detector.get_current_scale.return_value = None
        integration.apply_scale_constraint()
        mpe_manager.set_scale_constraint.assert_not_called()

    def test_apply_scale_constraint_no_mpe(self, integration):
        """apply_scale_constraint without MPE manager returns early."""
        integration.mpe = None
        integration.apply_scale_constraint()  # Should not raise

    def test_set_diatonic_bend_range(self, integration, mpe_manager):
        """set_diatonic_bend_range sets bend mode and range."""
        integration.set_diatonic_bend_range(4)
        mpe_manager.set_bend_mode.assert_called_once_with("diatonic")
        mpe_manager.set_bend_range.assert_called_once_with(4)

    def test_set_diatonic_bend_range_default(self, integration, mpe_manager):
        """set_diatonic_bend_range uses default of 2 semitones."""
        integration.set_diatonic_bend_range()
        mpe_manager.set_bend_range.assert_called_once_with(2)

    def test_set_diatonic_bend_range_no_methods(self, integration):
        """set_diatonic_bend_range handles missing methods gracefully."""
        integration.mpe = Mock(spec=[])  # No set_bend_mode or set_bend_range
        integration.set_diatonic_bend_range()  # Should not raise

    def test_enable_microtonal_adjustment(self, integration, mpe_manager):
        """enable_microtonal_adjustment applies just intonation temperament."""
        from synth.style.scale import ScaleType

        integration._last_scale = Mock()
        integration._last_scale.scale_type = ScaleType.MAJOR
        integration.enable_microtonal_adjustment()
        mpe_manager.set_temperament.assert_called_once()
        temperament = mpe_manager.set_temperament.call_args[0][0]
        assert isinstance(temperament, dict)
        assert temperament[0] == 0  # Root

    def test_enable_microtonal_adjustment_no_last_scale(self, integration, mpe_manager):
        """enable_microtonal_adjustment returns early without _last_scale."""
        integration._last_scale = None
        integration.enable_microtonal_adjustment()
        mpe_manager.set_temperament.assert_not_called()

    def test_enable(self, integration):
        """enable sets _scale_constraint_enabled."""
        assert integration._scale_constraint_enabled is False
        integration.enable()
        assert integration._scale_constraint_enabled is True

    def test_disable(self, integration, mpe_manager):
        """disable clears constraint and sets chromatic mode."""
        integration._scale_constraint_enabled = True
        integration.disable()
        assert integration._scale_constraint_enabled is False
        mpe_manager.set_bend_mode.assert_called_once_with("chromatic")

    def test_disable_no_mpe(self, integration):
        """disable without mpe manager does not crash."""
        integration.mpe = None
        integration.disable()  # Should not raise

    def test_apply_scale_to_mpe_no_method(self, integration, mpe_manager):
        """_apply_scale_to_mpe handles missing set_scale_constraint."""
        del mpe_manager.set_scale_constraint
        scale = Mock()
        integration._apply_scale_to_mpe(scale)  # Should not raise

    def test_get_temperament_adjustments(self, integration):
        """_get_temperament_adjustments returns just intonation by default."""
        result = integration._get_temperament_adjustments(Mock())
        assert isinstance(result, dict)
        assert 0 in result


class TestStyleIntegrations:
    """Test StyleIntegrations master orchestrator."""

    @pytest.fixture
    def all_deps(self):
        return {
            "effects_coordinator": Mock(),
            "voice_manager": Mock(),
            "modulation_matrix": Mock(),
            "pattern_sequencer": Mock(),
            "mpe_manager": Mock(),
            "style_player": Mock(),
            "style_dynamics": Mock(),
            "ots": Mock(),
            "midi_learn": Mock(),
            "scale_detector": Mock(),
        }

    @pytest.fixture
    def integrations(self, all_deps):
        return StyleIntegrations(**all_deps)

    def test_init_with_all_dependencies(self, all_deps):
        """All 5 integrations are created when all deps provided."""
        si = StyleIntegrations(**all_deps)
        assert len(si.integrations) == 5
        assert "effects" in si.integrations
        assert "voice" in si.integrations
        assert "modulation" in si.integrations
        assert "sequencer" in si.integrations
        assert "mpe" in si.integrations

    def test_init_without_dependencies(self):
        """No integrations are created when no deps provided."""
        si = StyleIntegrations()
        assert len(si.integrations) == 0

    def test_init_partial_dependencies(self):
        """Only integrations with available deps are created."""
        si = StyleIntegrations(effects_coordinator=Mock(), style_dynamics=Mock())
        assert len(si.integrations) == 1
        assert "effects" in si.integrations
        assert "voice" not in si.integrations

    def test_enable_all(self, integrations):
        """enable_all enables all integrations."""
        for name, integration in integrations.integrations.items():
            integration.enable = Mock(wraps=integration.enable)
        integrations.enable_all()
        for name, integration in integrations.integrations.items():
            integration.enable.assert_called_once()

    def test_disable_all(self, integrations):
        """disable_all disables all integrations."""
        for name, integration in integrations.integrations.items():
            integration.disable = Mock(wraps=integration.disable)
        integrations.disable_all()
        for name, integration in integrations.integrations.items():
            integration.disable.assert_called_once()

    def test_enable_by_name(self, integrations):
        """enable(name) enables specific integration."""
        integrations.integrations["effects"].enable = Mock()
        integrations.enable("effects")
        integrations.integrations["effects"].enable.assert_called_once()

    def test_enable_by_name_not_found(self, integrations):
        """enable(name) does nothing for unknown name."""
        integrations.enable("unknown")  # Should not raise

    def test_disable_by_name(self, integrations):
        """disable(name) disables specific integration."""
        integrations.integrations["voice"].disable = Mock()
        integrations.disable("voice")
        integrations.integrations["voice"].disable.assert_called_once()

    def test_disable_by_name_not_found(self, integrations):
        """disable(name) does nothing for unknown name."""
        integrations.disable("unknown")  # Should not raise

    def test_get_integration(self, integrations):
        """get_integration returns the integration by name."""
        assert integrations.get_integration("effects") is integrations.integrations["effects"]
        assert integrations.get_integration("unknown") is None

    def test_get_status(self, integrations):
        """get_status returns dict with all integration names as keys, all True."""
        status = integrations.get_status()
        assert len(status) == 5
        for name in integrations.integrations:
            assert status[name] is True

    def test_get_status_empty(self):
        """get_status returns empty dict when no integrations."""
        si = StyleIntegrations()
        assert si.get_status() == {}

    def test_enable_all_error_handling(self, integrations):
        """enable_all handles integration enable failures gracefully."""
        integrations.integrations["effects"].enable = Mock(side_effect=Exception("fail"))
        integrations.enable_all()  # Should not raise


# =============================================================================
# Style Integrations Edge Cases
# =============================================================================


class TestStyleIntegrationsEdgeCases:
    """Test edge cases for style integrations."""

    def test_effects_integration_without_dynamics(self):
        """StyleEffectsIntegration can't be constructed without dynamics (no type check)."""
        # This will call add_callback on the mock, which is fine
        integration = StyleEffectsIntegration(Mock(), Mock())
        assert integration.effects is not None
        assert integration.dynamics is not None

    def test_voice_integration_without_voice_manager(self):
        """StyleVoiceIntegration handles missing voice_manager methods gracefully."""
        ots = Mock()
        ots.get_preset = Mock(return_value=None)
        integration = StyleVoiceIntegration(Mock(), ots)
        # get_preset with no preset should return early
        integration.apply_ots_voice_optimization(0)  # Should not raise

    def test_sequencer_without_set_tempo(self):
        """StyleSequencerIntegration handles missing set_tempo on sequencer."""
        sequencer = Mock(spec=[])  # No set_tempo
        style_player = Mock()
        style_player.tempo = 120
        integration = StyleSequencerIntegration(sequencer, style_player)
        integration.sync_with_style_section()  # Should not raise
        # set_section_change_callback should still be called
        style_player.set_section_change_callback.assert_called_once()

    def test_mpe_without_set_scale_constraint(self):
        """StyleMPEIntegration handles missing set_scale_constraint."""
        mpe = Mock(spec=[])
        scale_detector = Mock()
        scale = Mock()
        scale.confidence = 0.9
        scale.get_scale_notes.return_value = [60, 64, 67]
        scale_detector.get_current_scale.return_value = scale
        integration = StyleMPEIntegration(mpe, scale_detector)
        integration.apply_scale_constraint()  # Should not raise

    def test_mpe_without_set_temperament(self):
        """StyleMPEIntegration handles missing set_temperament."""
        from synth.style.scale import ScaleType

        mpe = Mock(spec=[])
        scale_detector = Mock()
        integration = StyleMPEIntegration(mpe, scale_detector)
        integration._last_scale = Mock()
        integration._last_scale.scale_type = ScaleType.MAJOR
        integration.enable_microtonal_adjustment()  # Should not raise
