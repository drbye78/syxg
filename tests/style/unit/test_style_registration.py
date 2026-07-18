"""
Registration Memory Unit Tests

Tests for the registration memory system including:
- RegistrationParameter enum values
- Registration dataclass (init, to_dict, from_dict, freeze)
- RegistrationBank management (init, get/set, serialization)
- RegistrationMemory (bank/slot navigation, recall/store, copy/swap/clear, freeze, callbacks, I/O)
- Edge cases and error handling
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, Mock

import pytest

from synth.style.registration import (
    Registration,
    RegistrationBank,
    RegistrationMemory,
    RegistrationParameter,
)


class TestRegistrationParameter:
    """Test RegistrationParameter enum values and properties."""

    def test_all_enum_values_present(self):
        """Verify all 17 registration parameters exist."""
        assert len(RegistrationParameter) == 17

    def test_voice(self):
        assert RegistrationParameter.VOICE.value == "voice"

    def test_style(self):
        assert RegistrationParameter.STYLE.value == "style"

    def test_ots(self):
        assert RegistrationParameter.OTS.value == "ots"

    def test_tempo(self):
        assert RegistrationParameter.TEMPO.value == "tempo"

    def test_transpose(self):
        assert RegistrationParameter.TRANSPOSE.value == "transpose"

    def test_tune(self):
        assert RegistrationParameter.TUNE.value == "tune"

    def test_volume_master(self):
        assert RegistrationParameter.VOLUME_MASTER.value == "volume_master"

    def test_volume_style(self):
        assert RegistrationParameter.VOLUME_STYLE.value == "volume_style"

    def test_volume_voice(self):
        assert RegistrationParameter.VOLUME_VOICE.value == "volume_voice"

    def test_reverb(self):
        assert RegistrationParameter.REVERB.value == "reverb"

    def test_chorus(self):
        assert RegistrationParameter.CHORUS.value == "chorus"

    def test_variation(self):
        assert RegistrationParameter.VARIATION.value == "variation"

    def test_master_effect(self):
        assert RegistrationParameter.MASTER_EFFECT.value == "master_effect"

    def test_scale(self):
        assert RegistrationParameter.SCALE.value == "scale"

    def test_tuning(self):
        assert RegistrationParameter.TUNING.value == "tuning"

    def test_footswitch(self):
        assert RegistrationParameter.FOOTSWITCH.value == "footswitch"

    def test_knob_assignment(self):
        assert RegistrationParameter.KNOB_ASSIGNMENT.value == "knob_assignment"


class TestRegistration:
    """Test Registration dataclass."""

    @pytest.fixture
    def default_reg(self):
        return Registration()

    @pytest.fixture
    def custom_reg(self):
        return Registration(
            slot_id=3,
            name="My Setup",
            voice_parts={0: {"program": 5, "volume": 80}},
            style_name="CoolGroove",
            style_tempo=140,
            ots_preset=2,
            transpose=3,
            tune=1,
            master_volume=90,
            style_volume=80,
            voice_volume=70,
            reverb_type=3,
            reverb_parameter=96,
            chorus_type=2,
            chorus_parameter=48,
            variation_type=1,
            variation_parameter=32,
            scale_type="pythagorean",
            micro_tuning={"root_note": 60},
            custom_parameters={"custom1": 42},
            color="#FF0000",
            icon="star",
        )

    def test_init_defaults(self, default_reg):
        """Test default values."""
        assert default_reg.slot_id == 0
        assert default_reg.name == "New Registration"
        assert default_reg.voice_parts == {}
        assert default_reg.style_name == ""
        assert default_reg.style_tempo == 120
        assert default_reg.ots_preset == 0
        assert default_reg.transpose == 0
        assert default_reg.tune == 0
        assert default_reg.master_volume == 100
        assert default_reg.style_volume == 100
        assert default_reg.voice_volume == 100
        assert default_reg.reverb_type == 0
        assert default_reg.reverb_parameter == 64
        assert default_reg.chorus_type == 0
        assert default_reg.chorus_parameter == 64
        assert default_reg.variation_type == 0
        assert default_reg.variation_parameter == 64
        assert default_reg.scale_type == "equal"
        assert default_reg.micro_tuning == {}
        assert default_reg.custom_parameters == {}
        assert default_reg.color == "#FFFFFF"
        assert default_reg.icon == ""
        assert default_reg.freeze_mask == set()

    def test_init_custom_values(self, custom_reg):
        """Test initialization with custom values."""
        assert custom_reg.slot_id == 3
        assert custom_reg.name == "My Setup"
        assert custom_reg.voice_parts == {0: {"program": 5, "volume": 80}}
        assert custom_reg.style_name == "CoolGroove"
        assert custom_reg.style_tempo == 140
        assert custom_reg.ots_preset == 2
        assert custom_reg.transpose == 3
        assert custom_reg.tune == 1
        assert custom_reg.master_volume == 90
        assert custom_reg.style_volume == 80
        assert custom_reg.voice_volume == 70
        assert custom_reg.reverb_type == 3
        assert custom_reg.reverb_parameter == 96
        assert custom_reg.chorus_type == 2
        assert custom_reg.chorus_parameter == 48
        assert custom_reg.variation_type == 1
        assert custom_reg.variation_parameter == 32
        assert custom_reg.scale_type == "pythagorean"
        assert custom_reg.micro_tuning == {"root_note": 60}
        assert custom_reg.custom_parameters == {"custom1": 42}
        assert custom_reg.color == "#FF0000"
        assert custom_reg.icon == "star"

    def test_timestamps_set_on_init(self, default_reg):
        """Test created_at and modified_at are set."""
        assert default_reg.created_at > 0
        assert default_reg.modified_at > 0
        # They should be close to current time
        now = time.time()
        assert abs(default_reg.created_at - now) < 5
        assert abs(default_reg.modified_at - now) < 5

    def test_created_at_fixed_on_init(self):
        """Test created_at stays the same while modified_at updates."""
        reg = Registration()
        created = reg.created_at
        modified_before = reg.modified_at
        time.sleep(0.01)
        reg.set_freeze(RegistrationParameter.VOICE, True)
        assert reg.created_at == created
        assert reg.modified_at > modified_before

    def test_to_dict_basic(self, default_reg):
        """Test to_dict with default values."""
        d = default_reg.to_dict()
        assert d["slot_id"] == 0
        assert d["name"] == "New Registration"
        assert d["freeze_mask"] == []
        assert d["voice_parts"] == {}

    def test_to_dict_full(self, custom_reg):
        """Test to_dict with populated fields."""
        d = custom_reg.to_dict()
        assert d["slot_id"] == 3
        assert d["name"] == "My Setup"
        assert d["style_name"] == "CoolGroove"
        assert d["style_tempo"] == 140
        assert d["ots_preset"] == 2
        assert d["transpose"] == 3
        assert d["tune"] == 1
        assert d["master_volume"] == 90
        assert d["style_volume"] == 80
        assert d["voice_volume"] == 70
        assert d["reverb_type"] == 3
        assert d["reverb_parameter"] == 96
        assert d["chorus_type"] == 2
        assert d["chorus_parameter"] == 48
        assert d["variation_type"] == 1
        assert d["variation_parameter"] == 32
        assert d["scale_type"] == "pythagorean"
        assert d["micro_tuning"] == {"root_note": 60}
        assert d["custom_parameters"] == {"custom1": 42}
        assert d["color"] == "#FF0000"
        assert d["icon"] == "star"
        assert d["freeze_mask"] == []
        assert "created_at" in d
        assert "modified_at" in d

    def test_from_dict_defaults(self):
        """Test from_dict with minimal data."""
        reg = Registration.from_dict({})
        assert reg.slot_id == 0
        assert reg.name == "New Registration"
        assert reg.style_tempo == 120
        assert reg.master_volume == 100
        assert reg.reverb_parameter == 64
        assert reg.scale_type == "equal"
        assert reg.color == "#FFFFFF"
        assert reg.freeze_mask == set()

    def test_from_dict_full(self, custom_reg):
        """Test from_dict roundtrip with full data."""
        d = custom_reg.to_dict()
        reg = Registration.from_dict(d)
        assert reg.slot_id == custom_reg.slot_id
        assert reg.name == custom_reg.name
        assert reg.voice_parts == custom_reg.voice_parts
        assert reg.style_name == custom_reg.style_name
        assert reg.style_tempo == custom_reg.style_tempo
        assert reg.ots_preset == custom_reg.ots_preset
        assert reg.transpose == custom_reg.transpose
        assert reg.tune == custom_reg.tune
        assert reg.master_volume == custom_reg.master_volume
        assert reg.style_volume == custom_reg.style_volume
        assert reg.voice_volume == custom_reg.voice_volume
        assert reg.reverb_type == custom_reg.reverb_type
        assert reg.reverb_parameter == custom_reg.reverb_parameter
        assert reg.chorus_type == custom_reg.chorus_type
        assert reg.chorus_parameter == custom_reg.chorus_parameter
        assert reg.variation_type == custom_reg.variation_type
        assert reg.variation_parameter == custom_reg.variation_parameter
        assert reg.scale_type == custom_reg.scale_type
        assert reg.micro_tuning == custom_reg.micro_tuning
        assert reg.custom_parameters == custom_reg.custom_parameters
        assert reg.color == custom_reg.color
        assert reg.icon == custom_reg.icon
        assert reg.freeze_mask == custom_reg.freeze_mask

    def test_to_dict_from_dict_roundtrip(self, custom_reg):
        """Test full roundtrip serialization."""
        d = custom_reg.to_dict()
        reg = Registration.from_dict(d)
        d2 = reg.to_dict()
        assert d == d2

    def test_from_dict_freeze_mask_strings(self):
        """Test freeze_mask is deserialized from string list."""
        data = {
            "slot_id": 0,
            "freeze_mask": ["voice", "style", "volume_master"],
        }
        reg = Registration.from_dict(data)
        assert RegistrationParameter.VOICE in reg.freeze_mask
        assert RegistrationParameter.STYLE in reg.freeze_mask
        assert RegistrationParameter.VOLUME_MASTER in reg.freeze_mask
        assert len(reg.freeze_mask) == 3

    def test_from_dict_skip_invalid_freeze_value(self):
        """Test invalid freeze_mask values are silently skipped."""
        data = {
            "freeze_mask": ["voice", "INVALID_PARAM", "style"],
        }
        reg = Registration.from_dict(data)
        assert RegistrationParameter.VOICE in reg.freeze_mask
        assert RegistrationParameter.STYLE in reg.freeze_mask
        assert len(reg.freeze_mask) == 2

    def test_set_freeze_add_parameter(self, default_reg):
        """Test set_freeze adds parameter to freeze_mask."""
        default_reg.set_freeze(RegistrationParameter.VOICE, True)
        assert RegistrationParameter.VOICE in default_reg.freeze_mask

    def test_set_freeze_remove_parameter(self, default_reg):
        """Test set_freeze removes parameter from freeze_mask."""
        default_reg.set_freeze(RegistrationParameter.VOICE, True)
        assert RegistrationParameter.VOICE in default_reg.freeze_mask
        default_reg.set_freeze(RegistrationParameter.VOICE, False)
        assert RegistrationParameter.VOICE not in default_reg.freeze_mask

    def test_set_freeze_multiple_parameters(self, default_reg):
        """Test freezing multiple parameters."""
        default_reg.set_freeze(RegistrationParameter.VOICE, True)
        default_reg.set_freeze(RegistrationParameter.STYLE, True)
        default_reg.set_freeze(RegistrationParameter.OTS, True)
        assert len(default_reg.freeze_mask) == 3

    def test_is_frozen_true(self, default_reg):
        """Test is_frozen returns True for frozen param."""
        default_reg.set_freeze(RegistrationParameter.TEMPO, True)
        assert default_reg.is_frozen(RegistrationParameter.TEMPO) is True

    def test_is_frozen_false(self, default_reg):
        """Test is_frozen returns False for unfrozen param."""
        assert default_reg.is_frozen(RegistrationParameter.VOICE) is False

    def test_is_frozen_after_remove(self, default_reg):
        """Test is_frozen after unfreezing."""
        default_reg.set_freeze(RegistrationParameter.VOICE, True)
        default_reg.set_freeze(RegistrationParameter.VOICE, False)
        assert default_reg.is_frozen(RegistrationParameter.VOICE) is False

    def test_set_freeze_updates_modified_at(self, default_reg):
        """Test set_freeze updates modified_at."""
        old = default_reg.modified_at
        time.sleep(0.01)
        default_reg.set_freeze(RegistrationParameter.STYLE, True)
        assert default_reg.modified_at > old

    def test_freeze_mask_in_to_dict(self, custom_reg):
        """Test freeze_mask is serialized as list of enum objects."""
        custom_reg.set_freeze(RegistrationParameter.VOLUME_MASTER, True)
        custom_reg.set_freeze(RegistrationParameter.REVERB, True)
        d = custom_reg.to_dict()
        assert RegistrationParameter.VOLUME_MASTER in d["freeze_mask"]
        assert RegistrationParameter.REVERB in d["freeze_mask"]
        assert len(d["freeze_mask"]) == 2


class TestRegistrationBank:
    """Test RegistrationBank dataclass."""

    @pytest.fixture
    def bank(self):
        return RegistrationBank(bank_id=0, name="Test Bank")

    @pytest.fixture
    def bank_with_custom_id(self):
        return RegistrationBank(bank_id=5, name="Custom Bank")

    def test_init_defaults(self):
        """Test bank initializes with 16 slots."""
        bank = RegistrationBank()
        assert bank.bank_id == 0
        assert bank.name == "Bank 1"
        assert len(bank.registrations) == 16

    def test_init_with_custom_id(self, bank_with_custom_id):
        """Test bank with custom id and name."""
        bank = bank_with_custom_id
        assert bank.bank_id == 5
        assert bank.name == "Custom Bank"
        assert len(bank.registrations) == 16

    def test_init_slots_have_sequential_ids(self, bank):
        """Test default registrations have slot_id 0..15."""
        for i, reg in enumerate(bank.registrations):
            assert reg.slot_id == i
            assert reg.name == "New Registration"

    def test_get_registration_valid(self, bank):
        """Test get_registration returns correct slot."""
        reg = bank.get_registration(5)
        assert reg is not None
        assert reg.slot_id == 5

    def test_get_registration_invalid(self, bank):
        """Test get_registration returns None for invalid slot."""
        assert bank.get_registration(-1) is None
        assert bank.get_registration(16) is None
        assert bank.get_registration(99) is None

    def test_set_registration_valid(self, bank):
        """Test set_registration replaces slot."""
        new_reg = Registration(slot_id=5, name="Replaced")
        result = bank.set_registration(5, new_reg)
        assert result is True
        fetched = bank.get_registration(5)
        assert fetched is not None
        assert fetched.name == "Replaced"

    def test_set_registration_invalid_slot(self, bank):
        """Test set_registration returns False for invalid slot."""
        new_reg = Registration(slot_id=99, name="Ghost")
        result = bank.set_registration(99, new_reg)
        assert result is False

        new_reg_neg = Registration(slot_id=-1)
        result = bank.set_registration(-1, new_reg_neg)
        assert result is False

    def test_set_registration_changes_only_target_slot(self, bank):
        """Test set_registration doesn't affect other slots."""
        new_reg = Registration(slot_id=3, name="Only Me")
        bank.set_registration(3, new_reg)
        assert bank.get_registration(0).name == "New Registration"
        assert bank.get_registration(3).name == "Only Me"
        assert bank.get_registration(15).name == "New Registration"

    def test_to_dict(self, bank):
        """Test to_dict serialization."""
        d = bank.to_dict()
        assert d["bank_id"] == 0
        assert d["name"] == "Test Bank"
        assert len(d["registrations"]) == 16
        for r in d["registrations"]:
            assert "slot_id" in r
            assert "name" in r

    def test_from_dict(self, bank):
        """Test from_dict roundtrip."""
        d = bank.to_dict()
        restored = RegistrationBank.from_dict(d)
        assert restored.bank_id == bank.bank_id
        assert restored.name == bank.name
        assert len(restored.registrations) == len(bank.registrations)
        for i, reg in enumerate(restored.registrations):
            assert reg.slot_id == bank.registrations[i].slot_id

    def test_from_dict_with_custom_bank_id(self):
        """Test from_dict with custom data."""
        data = {
            "bank_id": 3,
            "name": "Custom",
            "registrations": [
                Registration(slot_id=0, name="Slot 0").to_dict(),
                Registration(slot_id=1, name="Slot 1").to_dict(),
            ],
        }
        bank = RegistrationBank.from_dict(data)
        assert bank.bank_id == 3
        assert bank.name == "Custom"
        assert len(bank.registrations) == 2
        assert bank.get_registration(0).name == "Slot 0"
        assert bank.get_registration(1).name == "Slot 1"

    def test_to_dict_from_dict_roundtrip_full(self):
        """Test full serialization roundtrip with custom bank."""
        bank = RegistrationBank(bank_id=7, name="Roundtrip Bank")
        bank.set_registration(0, Registration(slot_id=0, name="Alpha", style_tempo=130))
        bank.set_registration(1, Registration(slot_id=1, name="Beta", ots_preset=3))
        d = bank.to_dict()
        restored = RegistrationBank.from_dict(d)
        assert restored.name == "Roundtrip Bank"
        assert restored.get_registration(0).name == "Alpha"
        assert restored.get_registration(0).style_tempo == 130
        assert restored.get_registration(1).name == "Beta"
        assert restored.get_registration(1).ots_preset == 3


class TestRegistrationMemoryBasic:
    """Test RegistrationMemory initialization and bank/slot navigation."""

    @pytest.fixture
    def mem(self):
        return RegistrationMemory()

    @pytest.fixture
    def custom_mem(self):
        return RegistrationMemory(num_banks=4, slots_per_bank=8)

    def test_init_defaults(self, mem):
        """Test default initialization (8 banks × 16 slots)."""
        assert mem.num_banks == 8
        assert mem.slots_per_bank == 16

    def test_init_custom(self, custom_mem):
        """Test custom num_banks and slots_per_bank."""
        assert custom_mem.num_banks == 4
        assert custom_mem.slots_per_bank == 8

    def test_init_all_banks_populated(self, mem):
        """Test all banks have 16 slots each on init."""
        for i in range(8):
            bank = mem._banks[i]
            assert len(bank.registrations) == 16
            assert bank.bank_id == i

    def test_get_current_bank_initial(self, mem):
        """Test get_current_bank returns bank 0 initially."""
        bank = mem.get_current_bank()
        assert bank.bank_id == 0

    def test_set_bank_valid(self, mem):
        """Test set_bank with valid index."""
        assert mem.set_bank(3) is True
        assert mem.get_current_bank().bank_id == 3

    def test_set_bank_invalid(self, mem):
        """Test set_bank with out-of-range index."""
        assert mem.set_bank(-1) is False
        assert mem.set_bank(8) is False
        assert mem.set_bank(100) is False
        # Current bank should not have changed
        assert mem.get_current_bank().bank_id == 0

    def test_next_bank(self, mem):
        """Test next_bank wraps around."""
        mem.set_bank(0)
        mem.next_bank()
        assert mem.get_current_bank().bank_id == 1
        mem.next_bank()
        assert mem.get_current_bank().bank_id == 2
        # Wrap around
        mem.set_bank(7)
        mem.next_bank()
        assert mem.get_current_bank().bank_id == 0

    def test_previous_bank(self, mem):
        """Test previous_bank wraps around."""
        mem.set_bank(0)
        mem.previous_bank()
        assert mem.get_current_bank().bank_id == 7
        mem.previous_bank()
        assert mem.get_current_bank().bank_id == 6

    def test_set_slot_valid(self, mem):
        """Test set_slot with valid index."""
        assert mem.set_slot(10) is True
        # slot value is internal, we check via recall target

    def test_set_slot_invalid(self, mem):
        """Test set_slot with out-of-range index."""
        assert mem.set_slot(-1) is False
        assert mem.set_slot(16) is False
        assert mem.set_slot(100) is False

    def test_next_slot(self, mem):
        """Test next_slot wraps around."""
        mem.set_slot(0)
        mem.next_slot()
        mem.next_slot()
        # After next_slot twice, should be slot 2
        bank = mem.get_current_bank()
        reg = bank.get_registration(2)
        assert reg is not None
        # Wrap around
        mem.set_slot(15)
        mem.next_slot()
        bank = mem.get_current_bank()
        reg = bank.get_registration(0)
        assert reg is not None

    def test_previous_slot(self, mem):
        """Test previous_slot wraps around."""
        mem.set_slot(0)
        mem.previous_slot()
        bank = mem.get_current_bank()
        reg = bank.get_registration(15)
        assert reg is not None
        mem.previous_slot()
        reg = bank.get_registration(14)
        assert reg is not None

    def test_get_current_registration(self, mem):
        """Test get_current_registration returns slot 0 of bank 0."""
        reg = mem.get_current_registration()
        assert reg is not None
        assert reg.slot_id == 0

    def test_get_current_registration_after_navigation(self, mem):
        """Test get_current_registration updates with navigation."""
        mem.set_bank(2)
        mem.set_slot(5)
        reg = mem.get_current_registration()
        assert reg is not None
        assert reg.slot_id == 5
        assert reg.name == "New Registration"


class TestRegistrationMemoryRecall:
    """Test RegistrationMemory recall operations."""

    @pytest.fixture
    def mem(self):
        return RegistrationMemory()

    def test_recall_with_defaults_changes_current_position(self, mem):
        """Test recall moves current bank/slot position."""
        # Put something in bank 3, slot 7
        reg = Registration(slot_id=7, name="Recalled")
        mem._banks[3].set_registration(7, reg)
        assert mem.recall(bank=3, slot=7) is True
        assert mem._current_bank == 3
        assert mem._current_slot == 7

    def test_recall_applies_to_synthesizer(self, mem):
        """Test recall applies registration to synthesizer."""
        synth = Mock()
        mem.set_synthesizer(synth)
        reg = Registration(
            slot_id=0,
            voice_parts={0: {"program": 10, "bank_msb": 0, "bank_lsb": 0, "volume": 100, "pan": 64}},
        )
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        synth.program_change.assert_called_once_with(0, 10, 0, 0)
        synth.control_change.assert_any_call(0, 7, 100)
        synth.control_change.assert_any_call(0, 10, 64)

    def test_recall_applies_style_tempo(self, mem):
        """Test recall applies style tempo to style_player."""
        synth = Mock()
        mem.set_synthesizer(synth)
        style_player = Mock()
        mem.set_style_player(style_player)
        reg = Registration(slot_id=0, style_tempo=150)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        assert style_player.tempo == 150

    def test_recall_applies_ots(self, mem):
        """Test recall activates OTS preset."""
        synth = Mock()
        mem.set_synthesizer(synth)
        ots = Mock()
        mem.set_ots(ots)
        reg = Registration(slot_id=0, ots_preset=3)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        ots.activate_preset.assert_called_once_with(3)

    def test_recall_applies_transpose(self, mem):
        """Test recall applies transpose via synthesizer."""
        synth = Mock()
        mem.set_synthesizer(synth)
        reg = Registration(slot_id=0, transpose=5)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        synth.set_transpose.assert_called_once_with(5)

    def test_recall_applies_master_volume(self, mem):
        """Test recall applies master volume via synthesizer."""
        synth = Mock()
        mem.set_synthesizer(synth)
        reg = Registration(slot_id=0, master_volume=80)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        synth.set_master_volume.assert_called_once_with(80)

    def test_recall_returns_false_for_invalid_bank(self, mem):
        """Test recall returns False for out-of-range bank."""
        assert mem.recall(bank=99, slot=0) is False

    def test_recall_returns_false_for_invalid_slot(self, mem):
        """Test recall returns False for slot not in bank."""
        assert mem.recall(bank=0, slot=99) is False

    def test_recall_empty_bank(self, mem):
        """Test recall returns False for empty bank."""
        mem._banks.pop(0, None)
        # Now bank 0 doesn't exist
        result = mem.recall(bank=0, slot=0)
        assert result is False

    def test_recall_with_current_position(self, mem):
        """Test recall with no bank/slot uses current position."""
        mem.set_bank(2)
        mem.set_slot(1)
        reg = Registration(slot_id=1, name="Current Recall")
        mem._banks[2].set_registration(1, reg)
        assert mem.recall() is True

    def test_recall_triggers_callback(self, mem):
        """Test recall triggers on_recall callback."""
        callback = Mock()
        mem.set_recall_callback(callback)
        reg = Registration(slot_id=0, name="Callback Test")
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        callback.assert_called_once()
        args, _ = callback.call_args
        assert args[0].name == "Callback Test"

    def test_recall_triggers_change_callback(self, mem):
        """Test recall triggers change callback."""
        change_cb = Mock()
        mem.set_change_callback(change_cb)
        reg = Registration(slot_id=0)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        change_cb.assert_called_once()


class TestRegistrationMemoryFreeze:
    """Test RegistrationMemory freeze functionality."""

    @pytest.fixture
    def mem(self):
        m = RegistrationMemory()
        synth = Mock()
        m.set_synthesizer(synth)
        return m

    def test_recall_with_frozen_voice_skips_apply(self, mem):
        """Test frozen voice parameter is not applied."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        reg = Registration(slot_id=0, voice_parts={0: {"program": 10, "volume": 100, "pan": 64}})
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        mem._synthesizer.program_change.assert_not_called()

    def test_recall_with_frozen_style_skips_tempo(self, mem):
        """Test frozen style parameter skips tempo apply."""
        style_player = Mock()
        mem.set_style_player(style_player)
        mem.set_global_freeze(RegistrationParameter.STYLE, True)
        reg = Registration(slot_id=0, style_tempo=200)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        # Tempo should not have been changed from default
        assert style_player.tempo != 200

    def test_recall_with_frozen_ots_skips_activate(self, mem):
        """Test frozen OTS parameter skips activation."""
        ots = Mock()
        mem.set_ots(ots)
        mem.set_global_freeze(RegistrationParameter.OTS, True)
        reg = Registration(slot_id=0, ots_preset=5)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        ots.activate_preset.assert_not_called()

    def test_recall_with_frozen_transpose_skips(self, mem):
        """Test frozen transpose is not applied."""
        mem.set_global_freeze(RegistrationParameter.TRANSPOSE, True)
        reg = Registration(slot_id=0, transpose=7)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        mem._synthesizer.set_transpose.assert_not_called()

    def test_recall_with_frozen_master_volume_skips(self, mem):
        """Test frozen master volume is not applied."""
        mem.set_global_freeze(RegistrationParameter.VOLUME_MASTER, True)
        reg = Registration(slot_id=0, master_volume=50)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        mem._synthesizer.set_master_volume.assert_not_called()

    def test_recall_ignore_freeze_applies_anyway(self, mem):
        """Test recall with ignore_freeze=True applies frozen params."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.TRANSPOSE, True)
        reg = Registration(
            slot_id=0,
            voice_parts={0: {"program": 1, "volume": 100, "pan": 64}},
            transpose=3,
        )
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0, ignore_freeze=True)
        mem._synthesizer.program_change.assert_called_once()
        mem._synthesizer.set_transpose.assert_called_once_with(3)

    def test_registration_local_freeze(self, mem):
        """Test local freeze_mask on a Registration is respected."""
        reg = Registration(slot_id=0, voice_parts={0: {"program": 10, "volume": 100, "pan": 64}})
        reg.set_freeze(RegistrationParameter.VOICE, True)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        mem._synthesizer.program_change.assert_not_called()

    def test_global_freeze_set_and_get(self, mem):
        """Test set_global_freeze and get_global_freeze."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.STYLE, True)
        freeze = mem.get_global_freeze()
        assert RegistrationParameter.VOICE in freeze
        assert RegistrationParameter.STYLE in freeze
        assert RegistrationParameter.OTS not in freeze

    def test_global_freeze_remove(self, mem):
        """Test removing from global freeze."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.VOICE, False)
        freeze = mem.get_global_freeze()
        assert RegistrationParameter.VOICE not in freeze

    def test_clear_global_freeze(self, mem):
        """Test clear_global_freeze removes all."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.STYLE, True)
        mem.clear_global_freeze()
        assert mem.get_global_freeze() == set()

    def test_global_freeze_returns_copy(self, mem):
        """Test get_global_freeze returns a copy, not the internal set."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        returned = mem.get_global_freeze()
        returned.add(RegistrationParameter.STYLE)
        # Internal should not have changed
        internal = mem.get_global_freeze()
        assert RegistrationParameter.STYLE not in internal

    def test_freeze_thread_safety(self, mem):
        """Test freeze operations are thread-safe."""
        import threading

        errors = []

        def setter():
            for _ in range(50):
                mem.set_global_freeze(RegistrationParameter.VOICE, True)
                mem.set_global_freeze(RegistrationParameter.VOICE, False)

        threads = [threading.Thread(target=setter) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


class TestRegistrationMemoryStoreCopyClear:
    """Test RegistrationMemory store, copy, swap, clear operations."""

    @pytest.fixture
    def mem_with_synth(self):
        mem = RegistrationMemory()
        synth = Mock()
        synth.channels = [
            Mock(program=5, bank_msb=0, bank_lsb=0, volume=80, pan=64) for _ in range(16)
        ]
        mem.set_synthesizer(synth)
        return mem

    def test_store_creates_registration(self, mem_with_synth):
        """Test store creates a registration at current position."""
        result = mem_with_synth.store(name="Stored Reg")
        assert result is True
        reg = mem_with_synth.get_current_registration()
        assert reg is not None
        assert reg.name == "Stored Reg"
        assert reg.slot_id == 0

    def test_store_at_specific_position(self, mem_with_synth):
        """Test store at specific bank/slot."""
        result = mem_with_synth.store(name="Positioned", bank=5, slot=10)
        assert result is True
        reg = mem_with_synth._banks[5].get_registration(10)
        assert reg is not None
        assert reg.name == "Positioned"
        assert reg.slot_id == 10

    def test_store_invalid_bank(self, mem_with_synth):
        """Test store returns False for invalid bank."""
        result = mem_with_synth.store(bank=99, slot=0)
        assert result is False

    def test_store_triggers_store_callback(self, mem_with_synth):
        """Test store calls on_store callback."""
        callback = Mock()
        mem_with_synth.set_store_callback(callback)
        mem_with_synth.store(name="Callback Reg", bank=2, slot=3)
        callback.assert_called_once()
        args, _ = callback.call_args
        assert args[0] == 2  # bank
        assert args[1] == 3  # slot
        assert args[2].name == "Callback Reg"

    def test_store_triggers_change_callback(self, mem_with_synth):
        """Test store triggers change callback."""
        change_cb = Mock()
        mem_with_synth.set_change_callback(change_cb)
        mem_with_synth.store(name="Change Test")
        change_cb.assert_called_once()

    def test_store_captures_voice_data(self, mem_with_synth):
        """Test store captures voice data from synthesizer channels."""
        mem_with_synth.store(name="Capture Test")
        reg = mem_with_synth.get_current_registration()
        assert len(reg.voice_parts) == 16
        for i in range(16):
            assert reg.voice_parts[i]["program"] == 5

    def test_copy_slot_valid(self, mem_with_synth):
        """Test copy_slot copies registration between slots."""
        # First store something
        mem_with_synth.store(name="Source", bank=0, slot=0)
        mem_with_synth._banks[0].registrations[0].voice_parts = {0: {"test": True}}
        result = mem_with_synth.copy_slot(from_bank=0, from_slot=0, to_bank=1, to_slot=7)
        assert result is True
        dest = mem_with_synth._banks[1].get_registration(7)
        assert dest is not None
        assert dest.name == "Source"
        assert dest.slot_id == 7

    def test_copy_slot_invalid_source_bank(self, mem_with_synth):
        """Test copy_slot returns False with invalid source bank."""
        result = mem_with_synth.copy_slot(from_bank=99, from_slot=0, to_bank=0, to_slot=1)
        assert result is False

    def test_copy_slot_invalid_dest_bank(self, mem_with_synth):
        """Test copy_slot returns False with invalid destination bank."""
        result = mem_with_synth.copy_slot(from_bank=0, from_slot=0, to_bank=99, to_slot=1)
        assert result is False

    def test_copy_slot_invalid_source_slot(self, mem_with_synth):
        """Test copy_slot returns False when source slot doesn't exist."""
        result = mem_with_synth.copy_slot(from_bank=0, from_slot=99, to_bank=0, to_slot=1)
        assert result is False

    def test_swap_slots_valid(self, mem_with_synth):
        """Test swap_slots exchanges registration data."""
        mem_with_synth.store(name="Alpha", bank=0, slot=0)
        mem_with_synth.store(name="Beta", bank=1, slot=1)
        result = mem_with_synth.swap_slots(0, 0, 1, 1)
        assert result is True
        assert mem_with_synth._banks[0].get_registration(0).name == "Beta"
        assert mem_with_synth._banks[1].get_registration(1).name == "Alpha"

    def test_swap_slots_invalid_bank(self, mem_with_synth):
        """Test swap_slots returns False with invalid bank."""
        result = mem_with_synth.swap_slots(0, 0, 99, 0)
        assert result is False

    def test_swap_slots_invalid_slot(self, mem_with_synth):
        """Test swap_slots returns False with invalid slot."""
        result = mem_with_synth.swap_slots(0, 0, 1, 99)
        assert result is False

    def test_swap_slots_triggers_change_callback(self, mem_with_synth):
        """Test swap_slots triggers change callback."""
        change_cb = Mock()
        mem_with_synth.set_change_callback(change_cb)
        mem_with_synth.store(name="A", bank=0, slot=0)
        mem_with_synth.store(name="B", bank=0, slot=1)
        change_cb.reset_mock()
        mem_with_synth.swap_slots(0, 0, 0, 1)
        change_cb.assert_called_once()

    def test_clear_slot_default(self, mem_with_synth):
        """Test clear_slot with current position."""
        mem_with_synth.store(name="To Be Cleared")
        result = mem_with_synth.clear_slot()
        assert result is True
        reg = mem_with_synth.get_current_registration()
        assert reg is not None
        assert reg.name == "Empty"
        assert reg.slot_id == 0

    def test_clear_slot_specific(self, mem_with_synth):
        """Test clear_slot at specific position."""
        mem_with_synth.store(name="Clear Me", bank=3, slot=5)
        result = mem_with_synth.clear_slot(bank=3, slot=5)
        assert result is True
        reg = mem_with_synth._banks[3].get_registration(5)
        assert reg is not None
        assert reg.name == "Empty"

    def test_clear_slot_invalid_bank(self, mem_with_synth):
        """Test clear_slot returns False for invalid bank."""
        result = mem_with_synth.clear_slot(bank=99, slot=0)
        assert result is False

    def test_clear_slot_triggers_change_callback(self, mem_with_synth):
        """Test clear_slot triggers change callback."""
        change_cb = Mock()
        mem_with_synth.set_change_callback(change_cb)
        mem_with_synth.clear_slot()
        change_cb.assert_called_once()


class TestRegistrationMemorySerialization:
    """Test RegistrationMemory serialization (to_dict, from_dict, file I/O)."""

    @pytest.fixture
    def mem(self):
        m = RegistrationMemory()
        return m

    def test_to_dict_contains_structure(self, mem):
        """Test to_dict has all expected keys."""
        d = mem.to_dict()
        assert d["num_banks"] == 8
        assert d["slots_per_bank"] == 16
        assert d["current_bank"] == 0
        assert d["current_slot"] == 0
        assert d["global_freeze"] == []
        assert "banks" in d
        assert len(d["banks"]) == 8

    def test_to_dict_with_global_freeze(self, mem):
        """Test to_dict includes global freeze state."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.STYLE, True)
        d = mem.to_dict()
        assert "voice" in d["global_freeze"]
        assert "style" in d["global_freeze"]
        assert len(d["global_freeze"]) == 2

    def test_to_dict_with_custom_data(self):
        """Test to_dict reflects custom bank/slot state."""
        mem = RegistrationMemory(num_banks=3, slots_per_bank=4)
        mem.set_bank(1)
        mem.set_slot(2)
        d = mem.to_dict()
        assert d["num_banks"] == 3
        assert d["slots_per_bank"] == 4
        assert d["current_bank"] == 1
        assert d["current_slot"] == 2

    def test_load_from_file_roundtrip(self, mem, tmp_path):
        """Test save_to_file / load_from_file roundtrip."""
        # Modify some data
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.TRANSPOSE, True)
        mem.store(name="Saved", bank=0, slot=3)
        mem.set_bank(2)
        mem.set_slot(5)

        filepath = tmp_path / "registrations.json"
        assert mem.save_to_file(str(filepath)) is True

        loaded = RegistrationMemory.load_from_file(str(filepath))
        assert loaded is not None
        assert loaded.num_banks == mem.num_banks
        assert loaded.slots_per_bank == mem.slots_per_bank
        assert loaded._current_bank == 2
        assert loaded._current_slot == 5

        # Check global freeze restored
        gf = loaded.get_global_freeze()
        assert RegistrationParameter.VOICE in gf
        assert RegistrationParameter.TRANSPOSE in gf
        assert len(gf) == 2

        # Check stored registration restored
        restored_reg = loaded._banks[0].get_registration(3)
        assert restored_reg is not None
        assert restored_reg.name == "Saved"

    def test_save_to_file_returns_false_on_error(self, mem):
        """Test save_to_file returns False on invalid path."""
        result = mem.save_to_file("/nonexistent/path/reg.json")
        assert result is False

    def test_load_from_file_returns_none_on_error(self):
        """Test load_from_file returns None on invalid file."""
        result = RegistrationMemory.load_from_file("/nonexistent/file.json")
        assert result is None

    def test_load_from_file_bad_json(self, tmp_path):
        """Test load_from_file returns None on corrupt JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json}")
        result = RegistrationMemory.load_from_file(str(bad_file))
        assert result is None

    def test_load_from_file_with_freeze_values(self, tmp_path):
        """Test load_from_file restores global freeze from saved data."""
        mem = RegistrationMemory()
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.REVERB, True)
        filepath = tmp_path / "freeze_test.json"
        mem.save_to_file(str(filepath))

        loaded = RegistrationMemory.load_from_file(str(filepath))
        freeze = loaded.get_global_freeze()
        assert RegistrationParameter.VOICE in freeze
        assert RegistrationParameter.REVERB in freeze

    def test_load_from_file_skips_invalid_freeze(self, tmp_path):
        """Test load_from_file skips invalid freeze enum values."""
        # Manually craft JSON with bad freeze value
        data = {
            "num_banks": 8,
            "slots_per_bank": 16,
            "current_bank": 0,
            "current_slot": 0,
            "global_freeze": ["voice", "INVALID_ENUM", "style"],
            "banks": {},
        }
        filepath = tmp_path / "bad_freeze.json"
        with open(filepath, "w") as f:
            json.dump(data, f)
        loaded = RegistrationMemory.load_from_file(str(filepath))
        assert loaded is not None
        freeze = loaded.get_global_freeze()
        assert RegistrationParameter.VOICE in freeze
        assert RegistrationParameter.STYLE in freeze
        assert len(freeze) == 2

    def test_save_and_load_preserves_all_banks(self, mem, tmp_path):
        """Test all 8 banks preserved after save/load."""
        # Put unique data in each bank
        for i in range(8):
            mem.store(name=f"Bank{i}_Slot0", bank=i, slot=0)
        filepath = tmp_path / "full_save.json"
        mem.save_to_file(str(filepath))
        loaded = RegistrationMemory.load_from_file(str(filepath))
        for i in range(8):
            reg = loaded._banks[i].get_registration(0)
            assert reg is not None
            assert reg.name == f"Bank{i}_Slot0"


class TestRegistrationMemoryCallbacks:
    """Test RegistrationMemory callback system."""

    @pytest.fixture
    def mem(self):
        m = RegistrationMemory()
        return m

    def test_recall_callback_fires(self, mem):
        """Test recall callback is invoked with the registration."""
        cb = Mock()
        mem.set_recall_callback(cb)
        reg = Registration(slot_id=0, name="CB Test")
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)
        cb.assert_called_once_with(reg)

    def test_store_callback_fires(self, mem):
        """Test store callback is invoked with bank, slot, registration."""
        synth = Mock()
        synth.channels = []
        mem.set_synthesizer(synth)
        cb = Mock()
        mem.set_store_callback(cb)
        mem.store(name="Store CB", bank=1, slot=4)
        cb.assert_called_once()
        args, _ = cb.call_args
        assert args[0] == 1
        assert args[1] == 4
        assert args[2].name == "Store CB"

    def test_change_callback_fires_on_set_bank(self, mem):
        """Test change callback fires on set_bank."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.set_bank(2)
        cb.assert_called_once()

    def test_change_callback_fires_on_set_slot(self, mem):
        """Test change callback fires on set_slot."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.set_slot(3)
        cb.assert_called_once()

    def test_change_callback_fires_on_next_bank(self, mem):
        """Test change callback fires on next_bank."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.next_bank()
        cb.assert_called_once()

    def test_change_callback_fires_on_previous_bank(self, mem):
        """Test change callback fires on previous_bank."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.previous_bank()
        cb.assert_called_once()

    def test_change_callback_fires_on_next_slot(self, mem):
        """Test change callback fires on next_slot."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.next_slot()
        cb.assert_called_once()

    def test_change_callback_fires_on_previous_slot(self, mem):
        """Test change callback fires on previous_slot."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.previous_slot()
        cb.assert_called_once()

    def test_change_callback_fires_on_store(self, mem):
        """Test change callback fires on store."""
        synth = Mock()
        synth.channels = []
        mem.set_synthesizer(synth)
        cb = Mock()
        mem.set_change_callback(cb)
        mem.store()
        cb.assert_called_once()

    def test_change_callback_fires_on_clear(self, mem):
        """Test change callback fires on clear_slot."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.clear_slot()
        cb.assert_called_once()

    def test_change_callback_fires_on_swap(self, mem):
        """Test change callback fires on swap_slots."""
        mem.store(name="A", bank=0, slot=0)
        mem.store(name="B", bank=0, slot=1)
        cb = Mock()
        mem.set_change_callback(cb)
        mem.swap_slots(0, 0, 0, 1)
        cb.assert_called_once()

    def test_change_callback_not_fired_on_noop(self, mem):
        """Test change callback not fired on failed operations."""
        cb = Mock()
        mem.set_change_callback(cb)
        mem.set_bank(99)  # Invalid - should not trigger callback
        cb.assert_not_called()

        cb.reset_mock()
        mem.set_slot(99)  # Invalid
        cb.assert_not_called()

        cb.reset_mock()
        mem.recall(bank=99, slot=0)  # Invalid
        cb.assert_not_called()

    def test_callback_error_does_not_crash(self, mem):
        """Test callback raising exception is caught."""
        def failing_cb(*args):
            raise RuntimeError("Callback failure")

        mem.set_recall_callback(failing_cb)
        mem.set_store_callback(failing_cb)
        mem.set_change_callback(failing_cb)

        # These should not raise
        reg = Registration(slot_id=0)
        mem._banks[0].set_registration(0, reg)
        mem.recall(bank=0, slot=0)

        mem.store(name="Fail", bank=0, slot=0)

        mem.set_bank(1)  # Triggers change callback


class TestRegistrationMemoryStatus:
    """Test RegistrationMemory.get_status."""

    @pytest.fixture
    def mem(self):
        return RegistrationMemory()

    def test_get_status_initial(self, mem):
        """Test status on fresh memory."""
        status = mem.get_status()
        assert status["current_bank"] == 0
        assert status["current_slot"] == 0
        assert status["current_registration"] == "New Registration"
        assert status["total_banks"] == 8
        assert status["slots_per_bank"] == 16
        assert status["global_freeze"] == []

    def test_get_status_after_navigation(self, mem):
        """Test status reflects navigation changes."""
        mem.set_bank(3)
        mem.set_slot(7)
        status = mem.get_status()
        assert status["current_bank"] == 3
        assert status["current_slot"] == 7
        assert status["current_registration"] == "New Registration"

    def test_get_status_with_named_registration(self, mem):
        """Test status shows custom registration name."""
        mem.store(name="My Saved", bank=1, slot=4)
        mem.set_bank(1)
        mem.set_slot(4)
        status = mem.get_status()
        assert status["current_registration"] == "My Saved"

    def test_get_status_with_global_freeze(self, mem):
        """Test status shows global freeze params."""
        mem.set_global_freeze(RegistrationParameter.VOICE, True)
        mem.set_global_freeze(RegistrationParameter.STYLE, True)
        status = mem.get_status()
        assert "voice" in status["global_freeze"]
        assert "style" in status["global_freeze"]
        assert len(status["global_freeze"]) == 2

    def test_get_status_empty_registration(self, mem):
        """Test status with cleared registration."""
        mem.store(name="Temp")
        mem.clear_slot()
        status = mem.get_status()
        assert status["current_registration"] == "Empty"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_registration_init_negative_slot_id(self):
        """Test Registration can handle negative slot_id."""
        reg = Registration(slot_id=-1)
        assert reg.slot_id == -1

    def test_registration_from_dict_empty_freeze_mask(self):
        """Test from_dict handles empty freeze_mask gracefully."""
        reg = Registration.from_dict({"freeze_mask": []})
        assert reg.freeze_mask == set()

    def test_registration_from_dict_none_freeze_mask(self):
        """Test from_dict handles None freeze_mask gracefully."""
        reg = Registration.from_dict({"freeze_mask": None})
        assert reg.freeze_mask == set()

    def test_registration_bank_with_inject_empty_list(self):
        """Test RegistrationBank with empty registrations list still creates 16 slots."""
        bank = RegistrationBank(registrations=[])
        assert len(bank.registrations) == 16

    def test_registration_bank_with_provided_registrations(self):
        """Test RegistrationBank with provided list skips default init."""
        custom_regs = [Registration(slot_id=i, name=f"Custom {i}") for i in range(5)]
        bank = RegistrationBank(bank_id=0, registrations=custom_regs)
        assert len(bank.registrations) == 5
        assert bank.get_registration(0).name == "Custom 0"
        assert bank.get_registration(4).name == "Custom 4"

    def test_registration_memory_with_zero_banks(self):
        """Test RegistrationMemory with 0 banks (unusual but not crashing)."""
        # Division by zero would happen with mod on next/prev
        mem = RegistrationMemory(num_banks=1, slots_per_bank=1)
        assert mem.num_banks == 1
        assert mem.slots_per_bank == 1

    def test_no_synthesizer_recall_does_not_crash(self):
        """Test recall without synthesizer set doesn't crash."""
        mem = RegistrationMemory()
        reg = Registration(slot_id=0)
        mem._banks[0].set_registration(0, reg)
        result = mem.recall(bank=0, slot=0)
        assert result is True

    def test_synth_without_set_transpose_method(self):
        """Test recall with synth missing optional methods doesn't crash."""
        mem = RegistrationMemory()
        synth = MagicMock(spec=[])  # No methods at all
        mem.set_synthesizer(synth)
        reg = Registration(slot_id=0, transpose=3, master_volume=80)
        mem._banks[0].set_registration(0, reg)
        result = mem.recall(bank=0, slot=0)
        assert result is True

    def test_style_player_without_tempo(self):
        """Test recall with style_player missing tempo attribute doesn't crash."""
        mem = RegistrationMemory()
        style_player = Mock()
        del style_player.tempo  # Remove tempo attribute
        mem.set_style_player(style_player)
        reg = Registration(slot_id=0, style_tempo=140)
        mem._banks[0].set_registration(0, reg)
        # Should not raise
        result = mem.recall(bank=0, slot=0)
        assert result is True

    def test_store_without_synthesizer(self):
        """Test store without synthesizer doesn't crash."""
        mem = RegistrationMemory()
        reg = mem.store(name="No Synth")
        assert reg is True
        stored = mem.get_current_registration()
        assert stored is not None
        assert stored.name == "No Synth"

    def test_swap_slots_same_bank(self):
        """Test swap_slots within the same bank."""
        mem = RegistrationMemory()
        mem.store(name="First", bank=0, slot=0)
        mem.store(name="Second", bank=0, slot=1)

        result = mem.swap_slots(0, 0, 0, 1)
        assert result is True
        assert mem._banks[0].get_registration(0).name == "Second"
        assert mem._banks[0].get_registration(1).name == "First"

    def test_swap_slots_same_slot_noop(self):
        """Test swap_slots with same slot returns True (self-swap)."""
        mem = RegistrationMemory()
        mem.store(name="Self", bank=0, slot=0)
        result = mem.swap_slots(0, 0, 0, 0)
        assert result is True
        assert mem._banks[0].get_registration(0).name == "Self"

    def test_copy_slot_same_position_noop(self):
        """Test copy_slot to same position works."""
        mem = RegistrationMemory()
        mem.store(name="Same", bank=0, slot=0)
        result = mem.copy_slot(0, 0, 0, 0)
        assert result is True
        assert mem._banks[0].get_registration(0).name == "Same"

    def test_set_synthesizer_accepts_any_object(self):
        """Test set_synthesizer accepts any object (duck typing)."""
        mem = RegistrationMemory()
        mem.set_synthesizer(object())
        assert mem._synthesizer is not None

    def test_set_style_player_accepts_any_object(self):
        """Test set_style_player accepts any object."""
        mem = RegistrationMemory()
        mem.set_style_player(object())
        assert mem._style_player is not None

    def test_set_ots_accepts_any_object(self):
        """Test set_ots accepts any object."""
        mem = RegistrationMemory()
        mem.set_ots(object())
        assert mem._ots is not None

    def test_get_current_registration_after_clear(self):
        """Test get_current_registration returns empty registration after clear."""
        mem = RegistrationMemory()
        mem.store(name="Will Be Cleared")
        mem.clear_slot()
        reg = mem.get_current_registration()
        assert reg is not None
        assert reg.name == "Empty"

    def test_recall_multiple_times_stable(self):
        """Test recall can be called multiple times on same slot."""
        mem = RegistrationMemory()
        synth = Mock()
        mem.set_synthesizer(synth)
        reg = Registration(slot_id=0, voice_parts={0: {"program": 1, "volume": 100, "pan": 64}})
        mem._banks[0].set_registration(0, reg)

        for _ in range(5):
            assert mem.recall(bank=0, slot=0) is True

        assert synth.program_change.call_count == 5
