"""
Unit tests for style_ots and style_track modules.

Covers all public classes, methods, enums, and dataclasses.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from synth.style.style import CCEvent, NoteEvent, StyleTrackData, TrackType
from synth.style.style_ots import OTSPart, OTSPreset, OTSSection, OneTouchSettings
from synth.style.style_track import StyleTrack, TrackVariation


class TestOTSSection:
    """Test OTSSection enum values and members."""

    def test_enum_values(self):
        assert OTSSection.INTRO.value == "intro"
        assert OTSSection.MAIN_A.value == "main_a"
        assert OTSSection.MAIN_B.value == "main_b"
        assert OTSSection.MAIN_C.value == "main_c"
        assert OTSSection.MAIN_D.value == "main_d"
        assert OTSSection.ENDING.value == "ending"

    def test_enum_members(self):
        members = {OTSSection.INTRO, OTSSection.MAIN_A, OTSSection.MAIN_B,
                   OTSSection.MAIN_C, OTSSection.MAIN_D, OTSSection.ENDING}
        assert set(OTSSection) == members

    def test_enum_str(self):
        assert str(OTSSection.INTRO) == "OTSSection.INTRO"


class TestOTSPart:
    """Test OTSPart dataclass."""

    @pytest.fixture
    def default_part(self) -> OTSPart:
        return OTSPart()

    def test_default_init(self, default_part: OTSPart):
        assert default_part.part_id == 0
        assert default_part.enabled is True
        assert default_part.program_change == 0
        assert default_part.bank_msb == 0
        assert default_part.bank_lsb == 0
        assert default_part.volume == 100
        assert default_part.pan == 64
        assert default_part.reverb_send == 40
        assert default_part.chorus_send == 0
        assert default_part.variation_send == 0
        assert default_part.octave_shift == 0
        assert default_part.velocity_limit_low == 1
        assert default_part.velocity_limit_high == 127
        assert default_part.assign_type == "normal"

    def test_custom_init(self):
        part = OTSPart(
            part_id=2,
            enabled=False,
            program_change=24,
            bank_msb=121,
            bank_lsb=64,
            volume=80,
            pan=0,
            reverb_send=100,
            chorus_send=50,
            variation_send=30,
            octave_shift=-1,
            velocity_limit_low=10,
            velocity_limit_high=100,
            assign_type="fixed",
        )
        assert part.part_id == 2
        assert part.enabled is False
        assert part.program_change == 24
        assert part.bank_msb == 121
        assert part.bank_lsb == 64
        assert part.volume == 80
        assert part.pan == 0
        assert part.reverb_send == 100
        assert part.chorus_send == 50
        assert part.variation_send == 30
        assert part.octave_shift == -1
        assert part.velocity_limit_low == 10
        assert part.velocity_limit_high == 100
        assert part.assign_type == "fixed"

    def test_program_property(self):
        part = OTSPart(program_change=15, bank_msb=1, bank_lsb=32)
        expected = (1 << 16) | (32 << 8) | 15
        assert part.program == expected

    def test_midi_channel_property(self):
        assert OTSPart(part_id=0).midi_channel == 0
        assert OTSPart(part_id=3).midi_channel == 3

    def test_to_dict(self, default_part: OTSPart):
        d = default_part.to_dict()
        assert d["part_id"] == 0
        assert d["enabled"] is True
        assert d["program_change"] == 0
        assert d["volume"] == 100
        assert d["assign_type"] == "normal"
        assert len(d) == 14

    def test_from_dict_defaults(self):
        part = OTSPart.from_dict({})
        assert part.part_id == 0
        assert part.enabled is True
        assert part.volume == 100
        assert part.assign_type == "normal"
        assert part.velocity_limit_low == 1
        assert part.velocity_limit_high == 127

    def test_from_dict_custom(self):
        part = OTSPart.from_dict({
            "part_id": 1,
            "enabled": False,
            "program_change": 42,
            "bank_msb": 1,
            "bank_lsb": 0,
            "volume": 127,
            "pan": 0,
            "reverb_send": 20,
            "chorus_send": 0,
            "variation_send": 0,
            "octave_shift": 0,
            "velocity_limit_low": 1,
            "velocity_limit_high": 127,
            "assign_type": "normal",
        })
        assert part.part_id == 1
        assert part.enabled is False
        assert part.program_change == 42
        assert part.bank_msb == 1
        assert part.volume == 127

    def test_to_dict_from_dict_roundtrip(self):
        original = OTSPart(
            part_id=3,
            enabled=True,
            program_change=10,
            bank_msb=0,
            bank_lsb=0,
            volume=90,
            pan=10,
            reverb_send=50,
            chorus_send=10,
            variation_send=5,
            octave_shift=1,
            velocity_limit_low=20,
            velocity_limit_high=110,
            assign_type="normal",
        )
        restored = OTSPart.from_dict(original.to_dict())
        assert restored == original


class TestOTSPreset:
    """Test OTSPreset dataclass."""

    @pytest.fixture
    def default_preset(self) -> OTSPreset:
        return OTSPreset()

    def test_default_init(self, default_preset: OTSPreset):
        assert default_preset.preset_id == 0
        assert default_preset.name == "New OTS"
        assert len(default_preset.parts) == 4
        assert all(isinstance(p, OTSPart) for p in default_preset.parts)
        assert default_preset.parts[0].part_id == 0
        assert default_preset.parts[3].part_id == 3
        assert default_preset.master_volume == 100
        assert default_preset.master_tempo == 0
        assert default_preset.master_transpose == 0
        assert default_preset.master_tune == 0
        assert default_preset.reverb_type == 0
        assert default_preset.reverb_parameter == 64
        assert default_preset.chorus_type == 0
        assert default_preset.chorus_parameter == 64
        assert default_preset.variation_type == 0
        assert default_preset.variation_parameter == 64
        assert default_preset.linked_section is None
        assert default_preset.description == ""
        assert default_preset.color == "#FFFFFF"
        assert default_preset.icon == ""
        assert default_preset.category == "user"
        assert default_preset.dual_voice_enabled is False
        assert default_preset.dual_voice_part == -1
        assert default_preset.dual_voice_octave == 0
        assert default_preset.key_on_answer is True
        assert default_preset.key_off_answer is True

    def test_get_part_found(self, default_preset: OTSPreset):
        part = default_preset.get_part(2)
        assert part.part_id == 2

    def test_get_part_not_found(self, default_preset: OTSPreset):
        part = default_preset.get_part(9)
        assert part.part_id == 9
        assert part.enabled is True

    def test_to_dict(self, default_preset: OTSPreset):
        d = default_preset.to_dict()
        assert d["preset_id"] == 0
        assert d["name"] == "New OTS"
        assert len(d["parts"]) == 4
        assert d["linked_section"] is None
        assert d["category"] == "user"
        assert d["color"] == "#FFFFFF"

    def test_to_dict_with_linked_section(self):
        preset = OTSPreset(preset_id=1, linked_section=OTSSection.INTRO)
        d = preset.to_dict()
        assert d["linked_section"] == "intro"

    def test_from_dict_defaults(self):
        preset = OTSPreset.from_dict({})
        assert preset.preset_id == 0
        assert preset.name == "New OTS"
        assert len(preset.parts) == 4
        assert preset.linked_section is None

    def test_from_dict_with_parts(self):
        data = {
            "preset_id": 5,
            "name": "My Preset",
            "parts": [
                {"part_id": 0, "program_change": 10, "volume": 120},
                {"part_id": 1, "program_change": 20, "volume": 100},
                {"part_id": 2, "program_change": 30, "volume": 80},
                {"part_id": 3, "program_change": 40, "volume": 60},
            ],
            "linked_section": "main_c",
            "category": "favorite",
        }
        preset = OTSPreset.from_dict(data)
        assert preset.preset_id == 5
        assert preset.name == "My Preset"
        assert len(preset.parts) == 4
        assert preset.parts[0].program_change == 10
        assert preset.parts[1].program_change == 20
        assert preset.linked_section == OTSSection.MAIN_C
        assert preset.category == "favorite"

    def test_from_dict_fills_missing_parts(self):
        data = {
            "parts": [
                {"part_id": 0, "program_change": 5},
            ]
        }
        preset = OTSPreset.from_dict(data)
        assert len(preset.parts) == 4
        assert preset.parts[0].program_change == 5
        assert preset.parts[1].part_id == 1
        assert preset.parts[2].part_id == 2
        assert preset.parts[3].part_id == 3

    def test_to_dict_from_dict_roundtrip(self):
        original = OTSPreset(
            preset_id=3,
            name="Jazz Piano",
            parts=[
                OTSPart(part_id=0, program_change=1, volume=110),
                OTSPart(part_id=1, program_change=2, volume=100),
                OTSPart(part_id=2, program_change=3, volume=90),
                OTSPart(part_id=3, program_change=4, volume=80),
            ],
            master_volume=90,
            master_tempo=120,
            master_transpose=0,
            linked_section=OTSSection.MAIN_A,
            description="A warm jazz piano",
            category="jazz",
        )
        restored = OTSPreset.from_dict(original.to_dict())
        assert restored.preset_id == original.preset_id
        assert restored.name == original.name
        assert restored.master_volume == original.master_volume
        assert restored.master_tempo == original.master_tempo
        assert restored.linked_section == original.linked_section
        assert restored.description == original.description
        assert restored.category == original.category
        assert len(restored.parts) == len(original.parts)
        for rp, op in zip(restored.parts, original.parts):
            assert rp.program_change == op.program_change


class TestOneTouchSettings:
    """Test OneTouchSettings class."""

    @pytest.fixture
    def ots(self) -> OneTouchSettings:
        return OneTouchSettings()

    @pytest.fixture
    def ots_with_presets(self) -> OneTouchSettings:
        presets = [
            OTSPreset(preset_id=0, name="Piano"),
            OTSPreset(preset_id=1, name="Organ"),
            OTSPreset(preset_id=2, name="Strings"),
        ]
        return OneTouchSettings(presets=presets, active_preset_id=0)

    def test_default_init_creates_eight_presets(self, ots: OneTouchSettings):
        assert len(ots.presets) == 8
        assert ots.presets[0].name == "Piano"
        assert ots.presets[7].name == "Sax"
        assert ots.active_preset_id == 0
        assert ots.ots_link_enabled is True
        assert ots._synthesizer is None

    def test_provided_presets_not_overwritten(self):
        presets = [OTSPreset(preset_id=99, name="Custom")]
        ots = OneTouchSettings(presets=presets)
        assert len(ots.presets) == 1
        assert ots.presets[0].name == "Custom"

    def test_active_preset_property(self, ots_with_presets: OneTouchSettings):
        assert ots_with_presets.active_preset.name == "Piano"

    def test_active_preset_fallback(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.active_preset_id = 999
        assert ots_with_presets.active_preset is ots_with_presets.presets[0]

    def test_set_synthesizer(self, ots_with_presets: OneTouchSettings):
        synth = Mock()
        ots_with_presets.set_synthesizer(synth)
        assert ots_with_presets._synthesizer is synth

    def test_activate_preset_success(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.activate_preset(1)
        assert result is True
        assert ots_with_presets.active_preset_id == 1

    def test_activate_preset_not_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.activate_preset(999)
        assert result is False
        assert ots_with_presets.active_preset_id == 0

    def test_activate_preset_applies_to_synthesizer(self):
        synth = Mock()
        presets = [
            OTSPreset(
                preset_id=0, name="Test",
                parts=[
                    OTSPart(part_id=0, program_change=5, volume=100, pan=64,
                            reverb_send=40, chorus_send=10, enabled=True),
                    OTSPart(part_id=1, program_change=10, volume=90, pan=32,
                            reverb_send=20, chorus_send=5, enabled=False),
                    OTSPart(part_id=2, program_change=15, volume=80, pan=0,
                            reverb_send=30, chorus_send=15, enabled=True),
                    OTSPart(part_id=3, program_change=20, volume=70, pan=64,
                            reverb_send=10, chorus_send=0, enabled=True),
                ],
            ),
        ]
        ots = OneTouchSettings(presets=presets, _synthesizer=synth)
        ots.activate_preset(0)
        # Only enabled parts get program changes
        assert synth.program_change.call_count == 3
        calls = [c.args for c in synth.program_change.call_args_list]
        assert (0, 5, 0, 0) in calls
        assert (2, 15, 0, 0) in calls
        assert (3, 20, 0, 0) in calls
        # 3 enabled parts x 4 CCs (volume=7, pan=10, reverb=91, chorus=93)
        assert synth.control_change.call_count == 12

    def test_next_preset(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.next_preset()
        assert ots_with_presets.active_preset_id == 1

    def test_next_preset_wraps_around(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.active_preset_id = 2
        ots_with_presets.next_preset()
        assert ots_with_presets.active_preset_id == 0

    def test_previous_preset(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.active_preset_id = 1
        ots_with_presets.previous_preset()
        assert ots_with_presets.active_preset_id == 0

    def test_previous_preset_wraps_around(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.previous_preset()
        assert ots_with_presets.active_preset_id == 2

    def test_get_preset_found(self, ots_with_presets: OneTouchSettings):
        preset = ots_with_presets.get_preset(1)
        assert preset is not None
        assert preset.name == "Organ"

    def test_get_preset_not_found(self, ots_with_presets: OneTouchSettings):
        assert ots_with_presets.get_preset(999) is None

    def test_add_preset(self, ots_with_presets: OneTouchSettings):
        new_preset = OTSPreset(preset_id=5, name="New")
        ots_with_presets.add_preset(new_preset)
        assert len(ots_with_presets.presets) == 4
        assert ots_with_presets.presets[3].name == "New"

    def test_add_preset_max_sixteen(self, ots: OneTouchSettings):
        for i in range(8):
            ots.add_preset(OTSPreset(preset_id=i + 100, name=f"P{i}"))
        assert len(ots.presets) == 16
        ots.add_preset(OTSPreset(preset_id=999, name="Extra"))
        assert len(ots.presets) == 16

    def test_remove_preset_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.remove_preset(1)
        assert result is True
        assert len(ots_with_presets.presets) == 2

    def test_remove_preset_not_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.remove_preset(999)
        assert result is False
        assert len(ots_with_presets.presets) == 3

    def test_copy_preset_success(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.copy_preset(0, 1)
        assert result is True
        assert ots_with_presets.presets[1].master_volume == \
               ots_with_presets.presets[0].master_volume

    def test_copy_preset_source_not_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.copy_preset(999, 1)
        assert result is False

    def test_copy_preset_dest_not_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.copy_preset(0, 999)
        assert result is False

    def test_link_preset_to_section(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.link_preset_to_section(0, OTSSection.INTRO)
        assert result is True
        assert ots_with_presets.presets[0].linked_section == OTSSection.INTRO

    def test_link_preset_to_section_not_found(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.link_preset_to_section(999, OTSSection.INTRO)
        assert result is False

    def test_get_preset_for_section_found(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.link_preset_to_section(1, OTSSection.MAIN_A)
        preset = ots_with_presets.get_preset_for_section(OTSSection.MAIN_A)
        assert preset is not None
        assert preset.preset_id == 1

    def test_get_preset_for_section_not_found(self, ots_with_presets: OneTouchSettings):
        assert ots_with_presets.get_preset_for_section(OTSSection.ENDING) is None

    def test_auto_load_for_section_disabled(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.ots_link_enabled = False
        result = ots_with_presets.auto_load_for_section("main_a")
        assert result is False

    def test_auto_load_for_section_found(self):
        synth = Mock()
        presets = [
            OTSPreset(preset_id=0, name="Piano", linked_section=OTSSection.MAIN_A),
            OTSPreset(preset_id=1, name="Organ"),
        ]
        ots = OneTouchSettings(presets=presets, active_preset_id=0,
                               _synthesizer=synth)
        result = ots.auto_load_for_section("main_a")
        assert result is True
        assert ots.active_preset_id == 0

    def test_auto_load_for_section_not_linked(self, ots_with_presets: OneTouchSettings):
        ots_with_presets.link_preset_to_section(0, OTSSection.INTRO)
        result = ots_with_presets.auto_load_for_section("main_b")
        assert result is False

    def test_auto_load_for_section_unknown_section(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.auto_load_for_section("invalid_section")
        assert result is False

    def test_auto_load_section_name_mapping(self):
        synth = Mock()
        presets = [
            OTSPreset(preset_id=0, name="IntroPreset",
                      linked_section=OTSSection.INTRO),
        ]
        ots = OneTouchSettings(presets=presets, active_preset_id=0,
                               _synthesizer=synth)
        for name in ("intro", "intro_1", "intro_2", "intro_3"):
            ots.active_preset_id = 999
            result = ots.auto_load_for_section(name)
            assert result is True
            assert ots.active_preset_id == 0

    def test_store_current_to_preset_no_synth(self, ots_with_presets: OneTouchSettings):
        result = ots_with_presets.store_current_to_preset(0)
        assert result is False

    def test_store_current_to_preset_not_found(self):
        synth = Mock(spec=["get_parts_state"])
        presets = [OTSPreset(preset_id=0, name="Test")]
        ots = OneTouchSettings(presets=presets, _synthesizer=synth)
        result = ots.store_current_to_preset(999)
        assert result is False

    def test_store_current_to_preset_renames(self):
        synth = Mock(spec=["get_parts_state"])
        synth.get_parts_state.return_value = [
            {"program": 0, "volume": 100, "pan": 64, "enabled": True}
        ] * 16
        presets = [OTSPreset(preset_id=0, name="Old Name")]
        ots = OneTouchSettings(presets=presets, _synthesizer=synth)
        result = ots.store_current_to_preset(0, name="New Name")
        assert result is True
        assert presets[0].name == "New Name"

    def test_store_current_to_preset_updates_part_data(self):
        synth = Mock(spec=["get_parts_state"])
        synth.get_parts_state.return_value = [
            {
                "program": 0x000015,
                "volume": 110,
                "pan": 20,
                "reverb_send": 60,
                "chorus_send": 15,
                "variation_send": 5,
                "enabled": True,
                "octave_shift": 1,
                "velocity_limit_low": 10,
                "velocity_limit_high": 100,
            }
        ] * 16
        presets = [OTSPreset(preset_id=0, name="Test")]
        ots = OneTouchSettings(presets=presets, _synthesizer=synth)
        result = ots.store_current_to_preset(0)
        assert result is True
        part = presets[0].parts[0]
        assert part.program_change == 21
        assert part.bank_msb == 0
        assert part.bank_lsb == 0
        assert part.volume == 110
        assert part.pan == 20
        assert part.reverb_send == 60
        assert part.chorus_send == 15
        assert part.variation_send == 5
        assert part.enabled is True
        assert part.octave_shift == 1
        assert part.velocity_limit_low == 10
        assert part.velocity_limit_high == 100

    def test_get_preset_names(self, ots_with_presets: OneTouchSettings):
        names = ots_with_presets.get_preset_names()
        assert names == ["Piano", "Organ", "Strings"]

    def test_to_dict(self, ots: OneTouchSettings):
        d = ots.to_dict()
        assert len(d["presets"]) == 8
        assert d["active_preset_id"] == 0
        assert d["ots_link_enabled"] is True

    def test_from_dict(self):
        data = {
            "presets": [
                {"preset_id": 0, "name": "Custom1"},
                {"preset_id": 1, "name": "Custom2"},
            ],
            "active_preset_id": 1,
            "ots_link_enabled": False,
        }
        ots = OneTouchSettings.from_dict(data, synthesizer=None)
        assert len(ots.presets) == 2
        assert ots.presets[0].name == "Custom1"
        assert ots.active_preset_id == 1
        assert ots.ots_link_enabled is False
        assert ots._synthesizer is None

    def test_from_dict_with_synthesizer(self):
        synth = Mock()
        data = {
            "presets": [{"preset_id": 0, "name": "Test"}],
            "active_preset_id": 0,
        }
        ots = OneTouchSettings.from_dict(data, synthesizer=synth)
        assert ots._synthesizer is synth

    def test_get_status(self, ots_with_presets: OneTouchSettings):
        status = ots_with_presets.get_status()
        assert status["active_preset_id"] == 0
        assert status["active_preset_name"] == "Piano"
        assert status["total_presets"] == 3
        assert status["ots_link_enabled"] is True


class TestTrackType:
    """Test TrackType enum."""

    def test_enum_values(self):
        assert TrackType.RHYTHM_1.value == "rhythm_1"
        assert TrackType.RHYTHM_2.value == "rhythm_2"
        assert TrackType.BASS.value == "bass"
        assert TrackType.CHORD_1.value == "chord_1"
        assert TrackType.CHORD_2.value == "chord_2"
        assert TrackType.PAD.value == "pad"
        assert TrackType.PHRASE_1.value == "phrase_1"
        assert TrackType.PHRASE_2.value == "phrase_2"

    def test_default_midi_channel(self):
        assert TrackType.RHYTHM_1.default_midi_channel == 9
        assert TrackType.RHYTHM_2.default_midi_channel == 9
        assert TrackType.BASS.default_midi_channel == 0
        assert TrackType.CHORD_1.default_midi_channel == 1
        assert TrackType.CHORD_2.default_midi_channel == 2
        assert TrackType.PAD.default_midi_channel == 3
        assert TrackType.PHRASE_1.default_midi_channel == 4
        assert TrackType.PHRASE_2.default_midi_channel == 5

    def test_is_drum(self):
        assert TrackType.RHYTHM_1.is_drum is True
        assert TrackType.RHYTHM_2.is_drum is True
        assert TrackType.BASS.is_drum is False
        assert TrackType.CHORD_1.is_drum is False
        assert TrackType.PAD.is_drum is False

    def test_is_chordal(self):
        assert TrackType.CHORD_1.is_chordal is True
        assert TrackType.CHORD_2.is_chordal is True
        assert TrackType.PAD.is_chordal is True
        assert TrackType.RHYTHM_1.is_chordal is False
        assert TrackType.BASS.is_chordal is False
        assert TrackType.PHRASE_1.is_chordal is False


class TestNoteEvent:
    """Test NoteEvent dataclass."""

    @pytest.fixture
    def default_note(self) -> NoteEvent:
        return NoteEvent()

    def test_default_init(self, default_note: NoteEvent):
        assert default_note.tick == 0
        assert default_note.note == 60
        assert default_note.velocity == 100
        assert default_note.duration == 480
        assert default_note.gate_time == 0.8
        assert default_note.variation == 0

    def test_custom_init(self):
        note = NoteEvent(tick=240, note=72, velocity=80, duration=960,
                         gate_time=0.5, variation=2)
        assert note.tick == 240
        assert note.note == 72
        assert note.velocity == 80
        assert note.duration == 960
        assert note.gate_time == 0.5
        assert note.variation == 2

    def test_to_dict(self, default_note: NoteEvent):
        d = default_note.to_dict()
        assert d["tick"] == 0
        assert d["note"] == 60
        assert d["velocity"] == 100
        assert d["duration"] == 480
        assert d["gate_time"] == 0.8
        assert d["variation"] == 0

    def test_from_dict_defaults(self):
        note = NoteEvent.from_dict({})
        assert note.tick == 0
        assert note.note == 60
        assert note.velocity == 100
        assert note.duration == 480
        assert note.gate_time == 0.8
        assert note.variation == 0

    def test_from_dict_custom(self):
        note = NoteEvent.from_dict({
            "tick": 480,
            "note": 64,
            "velocity": 120,
            "duration": 240,
            "gate_time": 0.9,
            "variation": 1,
        })
        assert note.tick == 480
        assert note.note == 64
        assert note.variation == 1

    def test_to_dict_from_dict_roundtrip(self):
        original = NoteEvent(tick=120, note=67, velocity=110, duration=720,
                             gate_time=0.6, variation=3)
        restored = NoteEvent.from_dict(original.to_dict())
        assert restored == original


class TestCCEvent:
    """Test CCEvent dataclass."""

    @pytest.fixture
    def default_cc(self) -> CCEvent:
        return CCEvent()

    def test_default_init(self, default_cc: CCEvent):
        assert default_cc.tick == 0
        assert default_cc.controller == 7
        assert default_cc.value == 100

    def test_custom_init(self):
        cc = CCEvent(tick=120, controller=10, value=64)
        assert cc.tick == 120
        assert cc.controller == 10
        assert cc.value == 64

    def test_to_dict(self, default_cc: CCEvent):
        d = default_cc.to_dict()
        assert d["tick"] == 0
        assert d["controller"] == 7
        assert d["value"] == 100

    def test_from_dict_defaults(self):
        cc = CCEvent.from_dict({})
        assert cc.tick == 0
        assert cc.controller == 7
        assert cc.value == 100

    def test_from_dict_custom(self):
        cc = CCEvent.from_dict({
            "tick": 240,
            "controller": 91,
            "value": 50,
        })
        assert cc.tick == 240
        assert cc.controller == 91
        assert cc.value == 50

    def test_to_dict_from_dict_roundtrip(self):
        original = CCEvent(tick=360, controller=64, value=127)
        restored = CCEvent.from_dict(original.to_dict())
        assert restored == original


class TestStyleTrackData:
    """Test StyleTrackData dataclass."""

    @pytest.fixture
    def default_data(self) -> StyleTrackData:
        return StyleTrackData()

    def test_default_init(self, default_data: StyleTrackData):
        assert default_data.notes == []
        assert default_data.cc_events == []
        assert default_data.mute is False
        assert default_data.solo is False
        assert default_data.volume == 1.0
        assert default_data.pan == 64
        assert default_data.reverb_send == 0
        assert default_data.chorus_send == 0
        assert default_data.variation_send == 0
        assert default_data.quantize == 480
        assert default_data.swing == 0.0
        assert default_data.groove == ""
        assert default_data.velocity_offset == 0
        assert default_data.velocity_curve == "linear"
        assert default_data.humanize == 0.0

    def test_to_dict(self):
        data = StyleTrackData(
            notes=[NoteEvent(tick=0, note=60)],
            cc_events=[CCEvent(tick=0, controller=7, value=100)],
            volume=0.8,
        )
        d = data.to_dict()
        assert len(d["notes"]) == 1
        assert len(d["cc_events"]) == 1
        assert d["volume"] == 0.8
        assert d["mute"] is False

    def test_from_dict_defaults(self):
        data = StyleTrackData.from_dict({})
        assert data.notes == []
        assert data.cc_events == []
        assert data.volume == 1.0
        assert data.velocity_curve == "linear"

    def test_from_dict_with_content(self):
        data = StyleTrackData.from_dict({
            "notes": [
                {"tick": 0, "note": 60, "velocity": 100, "duration": 480,
                 "gate_time": 0.8, "variation": 0},
            ],
            "cc_events": [
                {"tick": 0, "controller": 7, "value": 100},
            ],
            "volume": 0.5,
            "mute": True,
            "pan": 0,
        })
        assert len(data.notes) == 1
        assert len(data.cc_events) == 1
        assert data.volume == 0.5
        assert data.mute is True
        assert data.pan == 0

    def test_to_dict_from_dict_roundtrip(self):
        original = StyleTrackData(
            notes=[
                NoteEvent(tick=0, note=60, velocity=100, duration=480),
                NoteEvent(tick=480, note=64, velocity=80, duration=240),
            ],
            cc_events=[
                CCEvent(tick=0, controller=7, value=80),
                CCEvent(tick=480, controller=10, value=32),
            ],
            volume=0.75,
            mute=False,
            pan=10,
            reverb_send=20,
            chorus_send=5,
            variation_send=3,
            quantize=240,
            swing=0.1,
            groove="shuffle",
            velocity_offset=5,
        )
        restored = StyleTrackData.from_dict(original.to_dict())
        assert len(restored.notes) == len(original.notes)
        assert len(restored.cc_events) == len(original.cc_events)
        assert restored.volume == original.volume
        assert restored.pan == original.pan
        assert restored.groove == original.groove


class TestStyleTrack:
    """Test StyleTrack class."""

    @pytest.fixture
    def default_track(self) -> StyleTrack:
        return StyleTrack()

    def test_default_init(self, default_track: StyleTrack):
        assert default_track.track_type == TrackType.RHYTHM_1
        assert default_track.name == "rhythm_1"
        assert isinstance(default_track.data, StyleTrackData)
        assert default_track.midi_channel == 0
        assert default_track.program_change == 0
        assert default_track.bank_msb == 0
        assert default_track.bank_lsb == 0
        assert default_track.mute is False
        assert default_track.solo is False
        assert default_track.volume == 1.0
        assert default_track.pan == 64
        assert default_track.reverb_send == 0
        assert default_track.chorus_send == 0
        assert default_track.variation_send == 0
        assert default_track.quantize == 480
        assert default_track.swing == 0.0
        assert default_track.groove == ""
        assert default_track.humanize == 0.0
        assert default_track.velocity_offset == 0
        assert default_track.velocity_curve == "linear"
        assert default_track.variations == []

    def test_init_with_name_does_not_override(self):
        track = StyleTrack(track_type=TrackType.BASS, name="My Bass")
        assert track.name == "My Bass"

    def test_is_drum_track(self):
        assert StyleTrack(track_type=TrackType.RHYTHM_1).is_drum_track is True
        assert StyleTrack(track_type=TrackType.BASS).is_drum_track is False

    def test_is_chordal_track(self):
        assert StyleTrack(track_type=TrackType.CHORD_1).is_chordal_track is True
        assert StyleTrack(track_type=TrackType.PAD).is_chordal_track is True
        assert StyleTrack(track_type=TrackType.RHYTHM_1).is_chordal_track is False

    def test_default_channel_returns_set_midi_channel(self):
        track = StyleTrack(track_type=TrackType.BASS, midi_channel=5)
        assert track.default_channel == 5

    def test_default_channel_falls_back_to_track_type(self):
        track = StyleTrack(track_type=TrackType.BASS, midi_channel=0)
        assert track.default_channel == TrackType.BASS.default_midi_channel

    def test_get_data_for_section_returns_own_data(self, default_track: StyleTrack):
        data = default_track.get_data_for_section("main_a")
        assert data is default_track.data

    def test_set_notes(self):
        track = StyleTrack()
        notes = [NoteEvent(tick=0, note=60), NoteEvent(tick=480, note=64)]
        track.set_notes(notes)
        assert track.data.notes == notes
        assert len(track.data.notes) == 2

    def test_add_note(self):
        track = StyleTrack()
        note = NoteEvent(tick=240, note=67, velocity=100)
        track.add_note(note)
        assert len(track.data.notes) == 1
        assert track.data.notes[0] is note

    def test_set_cc_events(self):
        track = StyleTrack()
        events = [CCEvent(tick=0, controller=7, value=100)]
        track.set_cc_events(events)
        assert track.data.cc_events == events

    def test_add_cc_event(self):
        track = StyleTrack()
        event = CCEvent(tick=120, controller=10, value=64)
        track.add_cc_event(event)
        assert len(track.data.cc_events) == 1
        assert track.data.cc_events[0] is event

    def test_to_dict(self, default_track: StyleTrack):
        d = default_track.to_dict()
        assert d["track_type"] == "rhythm_1"
        assert d["name"] == "rhythm_1"
        assert d["midi_channel"] == 0
        assert "data" in d
        assert isinstance(d["data"], dict)

    def test_from_dict_defaults(self):
        track = StyleTrack.from_dict({})
        assert track.track_type == TrackType.RHYTHM_1
        assert track.name == "rhythm_1"
        assert track.midi_channel == 0

    def test_to_dict_from_dict_roundtrip(self):
        original = StyleTrack(
            track_type=TrackType.CHORD_1,
            name="Chord 1",
            midi_channel=1,
            program_change=5,
            bank_msb=1,
            bank_lsb=0,
            volume=0.8,
            pan=32,
            data=StyleTrackData(
                notes=[NoteEvent(tick=0, note=60, velocity=100, duration=480)],
                cc_events=[CCEvent(tick=0, controller=7, value=90)],
            ),
            quantize=240,
            swing=0.2,
        )
        restored = StyleTrack.from_dict(original.to_dict())
        assert restored.track_type == original.track_type
        assert restored.name == original.name
        assert restored.midi_channel == original.midi_channel
        assert restored.volume == original.volume
        assert restored.pan == original.pan
        assert restored.quantize == original.quantize
        assert restored.swing == original.swing
        assert len(restored.data.notes) == 1
        assert len(restored.data.cc_events) == 1


class TestTrackVariation:
    """Test TrackVariation dataclass."""

    @pytest.fixture
    def default_variation(self) -> TrackVariation:
        return TrackVariation()

    def test_default_init(self, default_variation: TrackVariation):
        assert default_variation.variation_id == 0
        assert default_variation.name == ""
        assert isinstance(default_variation.data, StyleTrackData)
        assert default_variation.probability == 1.0
        assert default_variation.conditions == {}

    def test_custom_init(self):
        var = TrackVariation(
            variation_id=3,
            name="Variation 3",
            data=StyleTrackData(
                notes=[NoteEvent(tick=0, note=72, velocity=100, duration=240)],
            ),
            probability=0.5,
            conditions={"velocity_range": (60, 127)},
        )
        assert var.variation_id == 3
        assert var.name == "Variation 3"
        assert len(var.data.notes) == 1
        assert var.probability == 0.5
        assert var.conditions == {"velocity_range": (60, 127)}

    def test_to_dict(self, default_variation: TrackVariation):
        d = default_variation.to_dict()
        assert d["variation_id"] == 0
        assert d["name"] == ""
        assert d["probability"] == 1.0
        assert d["conditions"] == {}
        assert "data" in d

    def test_from_dict_defaults(self):
        var = TrackVariation.from_dict({})
        assert var.variation_id == 0
        assert var.name == ""
        assert var.probability == 1.0
        assert var.conditions == {}

    def test_from_dict_custom(self):
        var = TrackVariation.from_dict({
            "variation_id": 2,
            "name": "Soft",
            "data": {
                "notes": [
                    {"tick": 0, "note": 60, "velocity": 50, "duration": 480,
                     "gate_time": 0.8, "variation": 0},
                ],
            },
            "probability": 0.3,
            "conditions": {"velocity_threshold": 80},
        })
        assert var.variation_id == 2
        assert var.name == "Soft"
        assert len(var.data.notes) == 1
        assert var.probability == 0.3
        assert var.conditions == {"velocity_threshold": 80}

    def test_to_dict_from_dict_roundtrip(self):
        original = TrackVariation(
            variation_id=1,
            name="Loud",
            data=StyleTrackData(
                notes=[NoteEvent(tick=0, note=60, velocity=127, duration=960)],
                cc_events=[CCEvent(tick=0, controller=7, value=127)],
            ),
            probability=0.8,
            conditions={"min_velocity": 100},
        )
        restored = TrackVariation.from_dict(original.to_dict())
        assert restored.variation_id == original.variation_id
        assert restored.name == original.name
        assert restored.probability == original.probability
        assert restored.conditions == original.conditions
        assert len(restored.data.notes) == len(original.data.notes)


class TestEdgeCases:
    """Edge cases for style_ots and style_track modules."""

    @pytest.fixture
    def ots_with_presets(self) -> OneTouchSettings:
        presets = [
            OTSPreset(preset_id=0, name="Piano"),
            OTSPreset(preset_id=1, name="Organ"),
            OTSPreset(preset_id=2, name="Strings"),
        ]
        return OneTouchSettings(presets=presets, active_preset_id=0)

    def test_ots_part_negative_octave_shift(self):
        part = OTSPart(octave_shift=-3)
        assert part.octave_shift == -3
        d = part.to_dict()
        assert d["octave_shift"] == -3
        restored = OTSPart.from_dict(d)
        assert restored.octave_shift == -3

    def test_ots_part_extreme_values(self):
        part = OTSPart(
            volume=0,
            pan=0,
            reverb_send=127,
            chorus_send=127,
            velocity_limit_low=127,
            velocity_limit_high=1,
            assign_type="",
        )
        assert part.volume == 0
        assert part.velocity_limit_low == 127
        assert part.velocity_limit_high == 1
        restored = OTSPart.from_dict(part.to_dict())
        assert restored.volume == 0

    def test_ots_preset_empty_parts_list(self):
        preset = OTSPreset.from_dict({"parts": []})
        assert len(preset.parts) == 4

    def test_ots_activate_preset_no_synth(self, ots_with_presets):
        result = ots_with_presets.activate_preset(2)
        assert result is True
        assert ots_with_presets.active_preset_id == 2

    def test_ots_copy_preset_preserves_source(self, ots_with_presets):
        ots_with_presets.presets[0].master_volume = 50
        ots_with_presets.presets[1].master_volume = 100
        ots_with_presets.copy_preset(0, 1)
        assert ots_with_presets.presets[0].master_volume == 50

    def test_ots_store_current_exception_returns_false(self):
        synth = Mock(spec=["get_parts_state"])
        synth.get_parts_state.side_effect = RuntimeError("Synth error")
        presets = [OTSPreset(preset_id=0, name="Test")]
        ots = OneTouchSettings(presets=presets, _synthesizer=synth)
        result = ots.store_current_to_preset(0)
        assert result is False

    def test_note_event_zero_velocity(self):
        note = NoteEvent(velocity=0)
        assert note.velocity == 0
        restored = NoteEvent.from_dict(note.to_dict())
        assert restored.velocity == 0

    def test_note_event_max_values(self):
        note = NoteEvent(tick=99999, note=127, velocity=127, duration=99999,
                         gate_time=1.0, variation=255)
        restored = NoteEvent.from_dict(note.to_dict())
        assert restored == note

    def test_cc_event_extreme_values(self):
        cc = CCEvent(controller=127, value=127)
        restored = CCEvent.from_dict(cc.to_dict())
        assert restored == cc

    def test_style_track_empty_name_uses_track_type(self):
        track = StyleTrack(track_type=TrackType.PHRASE_1)
        assert track.name == "phrase_1"

    def test_style_track_no_variations_serialized(self):
        track = StyleTrack()
        d = track.to_dict()
        assert "variations" not in d

    def test_track_variation_zero_probability(self):
        var = TrackVariation(probability=0.0)
        assert var.probability == 0.0
        restored = TrackVariation.from_dict(var.to_dict())
        assert restored.probability == 0.0

    def test_track_variation_no_data(self):
        var = TrackVariation()
        d = var.to_dict()
        assert d["data"]["notes"] == []
        assert d["data"]["cc_events"] == []

    def test_style_track_data_empty_lists(self):
        data = StyleTrackData()
        d = data.to_dict()
        assert d["notes"] == []
        assert d["cc_events"] == []

    def test_remove_preset_active_not_updated(self):
        presets = [
            OTSPreset(preset_id=0, name="A"),
            OTSPreset(preset_id=1, name="B"),
        ]
        ots = OneTouchSettings(presets=presets, active_preset_id=0)
        ots.remove_preset(0)
        assert ots.active_preset_id == 0
        assert len(ots.presets) == 1
        assert ots.presets[0].preset_id == 1

    def test_auto_load_with_synth_activate_called(self):
        synth = Mock()
        presets = [
            OTSPreset(preset_id=0, name="Piano",
                      linked_section=OTSSection.MAIN_A),
        ]
        ots = OneTouchSettings(presets=presets, active_preset_id=999,
                               _synthesizer=synth)
        result = ots.auto_load_for_section("main_a")
        assert result is True
        assert ots.active_preset_id == 0
        # Verify the preset was applied via activate_preset -> _apply_preset
        assert synth.program_change.call_count == 4  # 4 parts

    def test_octave_shift_in_to_dict_roundtrip(self):
        part = OTSPart(octave_shift=-2)
        restored = OTSPart.from_dict(part.to_dict())
        assert restored.octave_shift == -2
