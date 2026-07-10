"""Tests for the XGML redesign: types, parser, NRPN definitions, and bridges."""

from __future__ import annotations

import pytest
import yaml

from synth.xgml.types import (
    AmpEnvelope,
    BasicMessages,
    ChannelConfig,
    ChannelSetup,
    ChorusConfig,
    ControlEvent,
    DrumConfig,
    DrumNoteParams,
    EffectSends,
    EffectsConfig,
    EQBand,
    EQConfig,
    FilterParams,
    GSChorusConfig,
    GSConfig,
    GSDrumPartConfig,
    GSEffectsConfig,
    GSPartConfig,
    GSReverbConfig,
    GSSystemConfig,
    InsertionSlot,
    JupiterXArpConfig,
    JupiterXConfig,
    JupiterXEngineConfig,
    JupiterXPartConfig,
    JupiterXPartLFO,
    JupiterXPartEnvelope,
    JupiterXPartModulation,
    JupiterXSystemConfig,
    JupiterXVCMConfig,
    LFOParams,
    Meta,
    NoteEvent,
    NRPNEvent,
    PitchParams,
    ReverbConfig,
    Sequence,
    SequenceEvent,
    SynthesizerCore,
    SystemExclusive,
    Track,
    VariationConfig,
    XGMLConfig,
)
from synth.xgml.errors import ParseError, SchemaValidationError, UnsupportedVersionError
from synth.xgml.defaults import default_xgml_config


# =============================================================================
# Types
# =============================================================================


class TestTypes:
    def test_default_construction(self):
        """All fields optional — dataclasses construct with None defaults."""
        mc = Meta()
        assert mc.description is None

        cs = ChannelSetup()
        assert cs.volume is None
        assert cs.program is None

        fc = FilterParams()
        assert fc.cutoff is None

        lp = LFOParams()
        assert lp.waveform is None
        assert lp.speed is None

        bm = BasicMessages()
        assert bm.channels == {}

        cc = ChannelConfig()
        assert cc.filter is None

        ec = EffectsConfig()
        assert ec.reverb is None
        assert ec.chorus is None
        assert ec.variation is None

    def test_channel_setup_with_values(self):
        cs = ChannelSetup(
            program="acoustic_grand_piano",
            volume=100,
            pan="center",
            expression=127,
            reverb_send=40,
        )
        assert cs.program == "acoustic_grand_piano"
        assert cs.volume == 100
        assert cs.pan == "center"
        assert cs.expression == 127
        assert cs.reverb_send == 40
        assert cs.chorus_send is None  # not set

    def test_channel_config_full(self):
        cc = ChannelConfig(
            filter=FilterParams(cutoff=100, resonance=30, type="lowpass"),
            lfo={"lfo1": LFOParams(waveform="sine", speed=64, delay=32)},
            amp_envelope=AmpEnvelope(attack=0, decay=40, sustain=100, release=64),
            pitch=PitchParams(coarse=0, fine=0),
            effects_sends=EffectSends(reverb=40, chorus=0),
            mono_poly="poly",
        )
        assert cc.filter.cutoff == 100
        assert cc.lfo["lfo1"].speed == 64
        assert cc.amp_envelope.sustain == 100
        assert cc.effects_sends.chorus == 0
        assert cc.mono_poly == "poly"

    def test_effects_config(self):
        ec = EffectsConfig(
            reverb=ReverbConfig(type=1, time=2.0, level=0.5),
            chorus=ChorusConfig(type=1, rate=0.5, depth=0.3, feedback=-0.2, level=0.4),
        )
        assert ec.reverb.type == 1
        assert ec.chorus.feedback == -0.2

    def test_drum_note_params(self):
        dp = DrumNoteParams(level=100, pan=64, filter_cutoff=80)
        assert dp.level == 100
        assert dp.pan == 64
        assert dp.alternate_group is None

    def test_sequences(self):
        track = Track(
            name="Piano",
            channel=0,
            program="acoustic_grand_piano",
            events=[
                SequenceEvent(
                    at=0.0,
                    note_on=NoteEvent(note="C4", velocity=100, duration=1.0),
                ),
                SequenceEvent(
                    at=1.0,
                    note_on=NoteEvent(note="E4", velocity=80, duration=0.5),
                ),
            ],
        )
        seq = Sequence(name="test", tempo=120, tracks=[track])
        assert len(seq.tracks) == 1
        assert seq.tracks[0].events[0].note_on.note == "C4"
        assert seq.tracks[0].events[0].note_on.duration == 1.0

    def test_xgml_config_roundtrip(self):
        """Construct XGMLConfig from scratch, verify all sections."""
        cfg = XGMLConfig(
            version="3.0",
            description="Test config",
            meta=Meta(author="test", tags=["test"]),
            basic_messages=BasicMessages(channels={0: ChannelSetup(volume=100)}),
            channel_parameters={0: ChannelConfig(mono_poly="poly")},
            drum_parameters=DrumConfig(kit_number=0, channel=10),
            effects=EffectsConfig(reverb=ReverbConfig(type=1)),
            sequences={
                "perf": Sequence(
                    name="perf",
                    tempo=120,
                    tracks=[Track(name="t1", channel=0)],
                )
            },
        )
        assert cfg.version == "3.0"
        assert cfg.meta.tags == ["test"]
        assert cfg.basic_messages.channels[0].volume == 100
        assert cfg.effects.reverb.type == 1
        assert cfg.sequences["perf"].tempo == 120


# =============================================================================
# Parser
# =============================================================================


class TestParser:
    _SAMPLE_YAML = """\
xg_dsl_version: '3.0'
description: Test config
basic_messages:
  channels:
    0:
      program: acoustic_grand_piano
      volume: 100
      pan: center
      expression: 127
      reverb_send: 40
channel_parameters:
  0:
    filter:
      cutoff: 100
      resonance: 30
      type: lowpass
    lfo:
      lfo1:
        waveform: sine
        speed: 64
effects:
  reverb:
    type: 1
    time: 2.0
    level: 0.5
  chorus:
    type: 1
    rate: 0.5
    depth: 0.3
    feedback: -0.2
    level: 0.4
sequences:
  perf:
    tempo: 120
    tracks:
      - name: Piano
        channel: 0
        program: acoustic_grand_piano
        events:
          - at: 0.0
            note_on:
              note: C4
              velocity: 100
              duration: 1.0
          - at: 1.0
            note_on:
              note: E4
              velocity: 80
              duration: 0.5
"""

    def test_parse_string(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        config = parser.parse_string(self._SAMPLE_YAML)
        assert config is not None, f"Errors: {parser.get_errors()}"
        assert config.version == "3.0"
        assert config.description == "Test config"

        # Basic messages
        bm = config.basic_messages
        assert bm is not None
        assert 0 in bm.channels
        assert bm.channels[0].program == "acoustic_grand_piano"
        assert bm.channels[0].volume == 100
        assert bm.channels[0].pan == "center"

        # Channel parameters
        assert config.channel_parameters is not None
        cp = config.channel_parameters[0]
        assert cp.filter.cutoff == 100
        assert cp.filter.resonance == 30
        assert cp.filter.type == "lowpass"
        assert cp.lfo["lfo1"].waveform == "sine"
        assert cp.lfo["lfo1"].speed == 64

        # Effects
        fx = config.effects
        assert fx is not None
        assert fx.reverb.type == 1
        assert fx.reverb.time == 2.0
        assert fx.reverb.level == 0.5
        assert fx.chorus.type == 1
        assert fx.chorus.feedback == -0.2

        # Sequences
        assert config.sequences is not None
        seq = config.sequences["perf"]
        assert seq.tempo == 120
        assert len(seq.tracks) == 1
        assert seq.tracks[0].name == "Piano"
        assert seq.tracks[0].events[0].note_on.note == "C4"

    def test_parse_file(self, tmp_path):
        from synth.xgml.parser import XGMLConfigParser

        f = tmp_path / "test.xgml"
        f.write_text(self._SAMPLE_YAML)
        parser = XGMLConfigParser()
        config = parser.parse_file(f)
        assert config is not None
        assert config.version == "3.0"

    def test_parse_file_not_found(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        result = parser.parse_file("/nonexistent/file.xgml")
        assert result is None
        assert parser.has_errors()

    def test_parse_invalid_yaml(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        result = parser.parse_string("{invalid: yaml: broken")
        assert result is None
        assert parser.has_errors()

    def test_parse_non_dict(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        result = parser.parse_string("hello")
        assert result is None
        assert parser.has_errors()

    def test_parse_minimal(self):
        """Minimal valid config — only version, no sections."""
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        result = parser.parse_string("xg_dsl_version: '3.0'")
        assert result is not None
        assert result.version == "3.0"
        assert result.basic_messages is None

    def test_parse_v2_backward_compat(self):
        """Old v2 format still parses into the new type system."""
        from synth.xgml.parser import XGMLConfigParser

        v2_yaml = """\
xg_dsl_version: '2.0'
description: Legacy config
basic_messages:
  channels:
    0:
      program: acoustic_grand_piano
      volume: 100
"""
        parser = XGMLConfigParser()
        config = parser.parse_string(v2_yaml)
        assert config is not None
        assert config.version == "2.0"
        assert config.basic_messages.channels[0].program == "acoustic_grand_piano"


class TestLegacyParser:
    def test_legacy_parser_backward_compat(self):
        """Old XGMLParser still works (backward compat)."""
        from synth.xgml.parser import XGMLParser as OldParser, XGMLDocument

        yaml_text = """\
xg_dsl_version: '2.0'
basic_messages:
  channels:
    0:
      program_change: 0
"""
        parser = OldParser()
        doc = parser.parse_string(yaml_text)
        assert doc is not None
        assert isinstance(doc, XGMLDocument)
        assert doc.version == "2.0"
        assert doc.has_section("basic_messages")


# =============================================================================
# Schema validation
# =============================================================================


class TestSchemaValidation:
    def test_schema_accepts_valid(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser(validate_schema=True)
        config = parser.parse_string("xg_dsl_version: '3.0'")
        assert config is not None

        valid = """\
xg_dsl_version: '3.0'
description: Valid
basic_messages:
  channels:
    0:
      volume: 100
      pan: center
"""
        config = parser.parse_string(valid)
        assert config is not None

    def test_schema_rejects_unknown_field(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser(validate_schema=True)
        bad = """\
xg_dsl_version: '3.0'
unknown_field: true
"""
        config = parser.parse_string(bad)
        # additionalProperties: false blocks it
        assert config is None
        assert parser.has_errors()

    def test_schema_can_be_disabled(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser(validate_schema=False)
        result = parser.parse_string("xg_dsl_version: '3.0'\nunknown_field: true")
        assert result is not None


# =============================================================================
# Defaults
# =============================================================================


class TestDefaults:
    def test_default_xgml_config(self):
        cfg = default_xgml_config()
        assert cfg.version == "3.0"
        assert cfg.basic_messages is not None
        assert len(cfg.basic_messages.channels) == 16
        assert all(
            cfg.basic_messages.channels[ch].volume == 100
            for ch in range(16)
        )
        assert cfg.effects is not None
        assert cfg.effects.reverb.type == 1

    def test_default_channel_setup(self):
        from synth.xgml.defaults import default_channel_setup

        cs = default_channel_setup()
        assert cs.volume == 100
        assert cs.pan == "center"
        assert cs.expression == 127


# =============================================================================
# NRPN Definitions
# =============================================================================


class TestNRPNDefinitions:
    def test_parameter_address(self):
        from synth.protocols.xg.xg_nrpn_definitions import (
            ParameterAddress,
            REVERB_TYPE,
            CHANNEL_VOLUME_COARSE,
            FILTER_CUTOFF,
            AMP_ENV_ATTACK,
            LFO1_WAVEFORM,
            DRUM_COARSE_TUNE,
        )
        assert REVERB_TYPE == (1, 0)
        assert CHANNEL_VOLUME_COARSE == (3, 0)
        assert FILTER_CUTOFF == (5, 0)
        assert AMP_ENV_ATTACK == (7, 0)
        assert LFO1_WAVEFORM == (9, 0)
        assert DRUM_COARSE_TUNE == (41, 32)

    def test_part_address_functions(self):
        from synth.protocols.xg.xg_nrpn_definitions import (
            part_reverb_send,
            part_chorus_send,
            part_voice_reserve,
        )
        assert part_reverb_send(0) == (32, 0)
        assert part_reverb_send(5) == (32, 5)
        assert part_chorus_send(3) == (33, 3)
        assert part_voice_reserve(0) == (42, 0)

    def test_drum_note_address(self):
        from synth.protocols.xg.xg_nrpn_definitions import (
            drum_note_address,
            DrumNoteParam,
        )
        # LEVEL has index 2 -> MSB = 48+2 = 50
        addr = drum_note_address(DrumNoteParam.LEVEL, 36)
        assert addr == (50, 36)

        addr = drum_note_address(DrumNoteParam.PITCH_COARSE, 42)
        assert addr == (48, 42)

        addr = drum_note_address(DrumNoteParam.FILTER_CUTOFF, 60)
        assert addr == (57, 60)

    def test_note_name_conversion(self):
        from synth.protocols.xg.xg_nrpn_definitions import (
            note_name_to_midi,
            midi_note_to_name,
        )
        assert note_name_to_midi("C4") == 60
        assert note_name_to_midi("A4") == 69
        assert note_name_to_midi("C0") == 12
        assert note_name_to_midi("G8") == 115
        assert note_name_to_midi("C#4") == 61
        assert note_name_to_midi("Db4") == 61
        assert midi_note_to_name(60) == "C4"

    def test_nrpn_value_conversion(self):
        from synth.protocols.xg.xg_nrpn_definitions import (
            float_to_nrpn_value,
            nrpn_value_to_float,
        )
        assert float_to_nrpn_value(0.0, 0.0, 1.0) == 0
        assert float_to_nrpn_value(0.5, 0.0, 1.0) == 64
        assert float_to_nrpn_value(1.0, 0.0, 1.0) == 127
        # Test with wider range: 50.0 / 127.0 * 127 = 50.0
        assert float_to_nrpn_value(50.0, 0.0, 127.0) == 50

        # Reverse
        val = nrpn_value_to_float(64)
        assert 0.5 <= val <= 0.51  # 64/127 ≈ 0.504

        val = nrpn_value_to_float(0)
        assert val == 0.0

        val = nrpn_value_to_float(127)
        assert val == 1.0

    def test_reverb_types_map(self):
        from synth.protocols.xg.xg_nrpn_definitions import XG_REVERB_TYPES_MAP
        assert XG_REVERB_TYPES_MAP[1] == "hall1"
        assert XG_REVERB_TYPES_MAP[8] == "plate"

    def test_variation_types_map(self):
        from synth.protocols.xg.xg_nrpn_definitions import XG_VARIATION_TYPES_MAP
        assert XG_VARIATION_TYPES_MAP[0] == "delay_lcr"
        assert XG_VARIATION_TYPES_MAP[16] == "chorus1"
        assert XG_VARIATION_TYPES_MAP[48] == "distortion1"
        assert XG_VARIATION_TYPES_MAP[64] == "rotary_speaker"

    def test_lfo_waveforms(self):
        from synth.protocols.xg.xg_nrpn_definitions import XG_LFO_WAVEFORMS
        assert XG_LFO_WAVEFORMS[0] == "sine"
        assert XG_LFO_WAVEFORMS[5] == "sample_and_hold"


# =============================================================================
# MIDI Bridge
# =============================================================================


class TestMIDIBridge:
    def test_empty_config(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(version="3.0")
        msgs = bridge.translate(cfg)
        assert msgs == []
        assert not bridge.has_errors()

    def test_basic_messages(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            basic_messages=BasicMessages(channels={
                0: ChannelSetup(
                    program="acoustic_grand_piano",
                    volume=100,
                    pan="center",
                    expression=127,
                    reverb_send=40,
                    chorus_send=0,
                ),
            }),
        )
        msgs = bridge.translate(cfg)
        assert len(msgs) == 6
        # Order: program_change, volume(CC7), pan(CC10), expression(CC11), reverb(CC91), chorus(CC93)
        assert msgs[0].type == "program_change"
        assert msgs[0].channel == 0
        assert msgs[1].type == "control_change"
        assert msgs[1].data["controller"] == 7  # volume

        pan_cc = [m for m in msgs if m.data.get("controller") == 10]
        assert len(pan_cc) == 1
        assert pan_cc[0].data["value"] == 64  # center

    def test_channel_config_filter(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            channel_parameters={
                0: ChannelConfig(
                    filter=FilterParams(cutoff=100, resonance=30, type="lowpass"),
                ),
            },
        )
        msgs = bridge.translate(cfg)
        assert len(msgs) == 9  # 3 CCs per NRPN × 3 params

        # Find NRPN MSB/Data Entry pairs
        nrpn_msgs = [m for m in msgs if m.data.get("controller") == 99]
        assert len(nrpn_msgs) == 3  # 3 NRPN messages

        data_msgs = [m for m in msgs if m.data.get("controller") == 6]
        assert len(data_msgs) == 3
        assert data_msgs[0].data["value"] == 100  # cutoff

    def test_effects_reverb(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            effects=EffectsConfig(
                reverb=ReverbConfig(type=1, time=2.0, level=0.5, hf_damping=0.3),
            ),
        )
        msgs = bridge.translate(cfg)
        assert len(msgs) == 12  # 4 NRPN params × 3 CCs each

        # Types should be on channel 0 for system effects
        nrpn_msb = [m for m in msgs if m.data.get("controller") == 99]
        assert len(nrpn_msb) == 4

        data_msgs = [m for m in msgs if m.data.get("controller") == 6]
        assert len(data_msgs) == 4

    def test_sequences(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            sequences={
                "test": Sequence(
                    name="test",
                    tempo=120,
                    tracks=[
                        Track(
                            name="Piano",
                            channel=0,
                            program="acoustic_grand_piano",
                            volume=100,
                            events=[
                                SequenceEvent(
                                    at=0.0,
                                    note_on=NoteEvent(note="C4", velocity=100, duration=1.0),
                                ),
                                SequenceEvent(
                                    at=1.0,
                                    note_on=NoteEvent(note="E4", velocity=80),
                                ),
                            ],
                        ),
                    ],
                ),
            },
        )
        msgs = bridge.translate(cfg)
        assert len(msgs) >= 4

        # First messages should be program change + volume at t=0
        assert msgs[0].type == "program_change"
        assert msgs[0].timestamp == 0.0

        # Find note ons
        note_ons = [m for m in msgs if m.type == "note_on"]
        assert len(note_ons) == 2
        assert note_ons[0].data["note"] == 60  # C4
        assert note_ons[0].velocity == 100
        assert note_ons[0].timestamp == 0.0

        # Second note at 1.0 beat = 0.5 sec at 120 BPM
        assert note_ons[1].data["note"] == 64  # E4
        assert note_ons[1].timestamp == 0.5

        # First note has duration, so there should be a note-off
        note_offs = [m for m in msgs if m.type == "note_off"]
        assert len(note_offs) == 1
        assert note_offs[0].data["note"] == 60
        assert note_offs[0].timestamp == 0.5  # 1.0 beats at 120 BPM

    def test_drum_config(self):
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            drum_parameters=DrumConfig(
                kit_number=1,
                channel=10,
                notes={
                    36: DrumNoteParams(level=100, pan=64, reverb_send=30),
                    42: DrumNoteParams(pitch_coarse=0, pitch_fine=0),
                },
            ),
        )
        msgs = bridge.translate(cfg)
        assert len(msgs) >= 3  # kit_nrpn + 3 per-note params × 3 + 2 per-note params × 3
        assert not bridge.has_errors()

    def test_drum_note_routing(self):
        """Drum config goes on the default channel (10 = MIDI ch10)."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge

        bridge = XGMLMIDIBridge()
        cfg = XGMLConfig(
            version="3.0",
            drum_parameters=DrumConfig(kit_number=5),
        )
        msgs = bridge.translate(cfg)
        # Kit number NRPN on default drum channel (10)
        kit_msgs = [m for m in msgs if m.channel == 10]
        assert len(kit_msgs) == 3  # NRPN MSB, LSB, Data Entry


# =============================================================================
# Errors
# =============================================================================


class TestErrors:
    def test_error_hierarchy(self):
        from synth.xgml.errors import (
            XGMLError,
            ParseError,
            ValidationError,
            SchemaValidationError,
            UnsupportedVersionError,
        )
        assert issubclass(ParseError, XGMLError)
        assert issubclass(ValidationError, XGMLError)
        assert issubclass(SchemaValidationError, ValidationError)
        assert issubclass(UnsupportedVersionError, ParseError)

    def test_parse_warning_for_unknown_version(self):
        from synth.xgml.parser import XGMLConfigParser

        parser = XGMLConfigParser()
        config = parser.parse_string("xg_dsl_version: '999.0'")
        assert config is not None  # unknown version logs warning, doesn't fail
        assert parser.has_warnings()
        assert any("999.0" in w for w in parser.get_warnings())


# =============================================================================
# Schemas
# =============================================================================


class TestSchema:
    def test_schema_is_valid_json_schema(self):
        from synth.xgml.schema import XGML_SCHEMA
        assert XGML_SCHEMA["title"] == "XGML Document"
        assert XGML_SCHEMA["type"] == "object"
        assert "basic_messages" in XGML_SCHEMA["properties"]
        assert "channel_parameters" in XGML_SCHEMA["properties"]
        assert "effects" in XGML_SCHEMA["properties"]
        assert "sequences" in XGML_SCHEMA["properties"]
        assert "meta" in XGML_SCHEMA["properties"]


# =============================================================================
# Roland GS
# =============================================================================


class TestGSConfig:
    def test_gs_types_defaults(self):
        """GS types construct with None defaults."""
        sys = GSSystemConfig()
        assert sys.master_tune is None
        assert sys.master_volume is None
        assert sys.master_transpose is None

        part = GSPartConfig()
        assert part.program is None
        assert part.volume is None
        assert part.reverb_send is None
        assert part.rx_note is None

        rv = GSReverbConfig()
        assert rv.type is None

        ch = GSChorusConfig()
        assert ch.type is None

        drum = GSDrumPartConfig()
        assert drum.map_low_note is None

        fx = GSEffectsConfig()
        assert fx.reverb is None
        assert fx.chorus is None

        gs = GSConfig()
        assert gs.system is None
        assert gs.parts is None
        assert gs.effects is None
        assert gs.drum_parts is None

    def test_gs_config_roundtrip(self):
        """Parse a YAML GS config, then verify the typed fields."""
        yaml_str = """
xg_dsl_version: "3.0"
gs:
  system:
    master_volume: 100
    master_tune: 0
  parts:
    "0":
      program: 0
      volume: 100
      pan: 64
      reverb_send: 40
      chorus_send: 0
    "9":
      program: 1
      volume: 80
      pan: 10
      bank_msb: 127
  effects:
    reverb:
      type: "hall1"
      level: 64
      time: 64
    chorus:
      type: "chorus1"
      level: 80
"""
        from synth.xgml.parser import XGMLConfigParser
        parser = XGMLConfigParser()
        config = parser.parse_string(yaml_str)
        assert config is not None
        assert not parser.has_errors()

        gs = config.gs
        assert gs is not None
        assert gs.system is not None
        assert gs.system.master_volume == 100
        assert gs.system.master_tune == 0

        assert gs.parts is not None
        assert 0 in gs.parts
        assert gs.parts[0].program == 0
        assert gs.parts[0].volume == 100
        assert gs.parts[0].pan == 64
        assert gs.parts[0].reverb_send == 40

        assert 9 in gs.parts
        assert gs.parts[9].program == 1
        assert gs.parts[9].bank_msb == 127

        assert gs.effects is not None
        assert gs.effects.reverb is not None
        assert gs.effects.reverb.type == "hall1"
        assert gs.effects.reverb.level == 64
        assert gs.effects.chorus is not None
        assert gs.effects.chorus.type == "chorus1"

    def test_gs_midi_bridge_system(self):
        """Translating GS system params produces GS SysEx messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(gs=GSConfig(
            system=GSSystemConfig(master_volume=100, master_tune=0),
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        assert len(msgs) == 2
        # First SysEx: master_tune (0x00 00 00) with value = 0 + 64
        assert msgs[0].type == "system_exclusive"
        data0 = msgs[0].data["data"]
        # Address bytes are at indices 4,5,6: 0x00 0x00 0x00 = master_tune
        assert data0[4] == 0x00 and data0[5] == 0x00 and data0[6] == 0x00
        # Second: master_volume (0x00 00 01) with value = 100
        assert msgs[1].type == "system_exclusive"
        data1 = msgs[1].data["data"]
        assert data1[4] == 0x00 and data1[5] == 0x00 and data1[6] == 0x01

    def test_gs_midi_bridge_part(self):
        """Translating GS part config produces SysEx + CC messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(gs=GSConfig(
            parts={0: GSPartConfig(program=5, volume=100, pan=64, reverb_send=40)},
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Expect: program_change, CC volume, CC pan, SysEx reverb_send
        assert len(msgs) >= 3
        assert msgs[0].type == "program_change"  # program change first
        assert msgs[1].type == "control_change"   # volume CC
        assert msgs[2].type == "control_change"   # pan CC

    def test_gs_midi_bridge_effects(self):
        """Translating GS effects produces reverb + chorus SysEx."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        rv = GSReverbConfig(type="hall1", level=64)
        ch = GSChorusConfig(type="chorus1", level=80)
        cfg = XGMLConfig(gs=GSConfig(effects=GSEffectsConfig(reverb=rv, chorus=ch)))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # 1 reverb type + 1 reverb level + 1 chorus type + 1 chorus level = 4 SysEx
        assert len(msgs) == 4
        for m in msgs:
            assert m.type == "system_exclusive"


# =============================================================================
# Jupiter-X Config Tests
# =============================================================================


class TestJupiterXConfig:
    """Tests for Jupiter-X XGML types, parser roundtrip, and MIDI bridge."""

    def test_jx_types_defaults(self):
        """Jupiter-X dataclasses construct with None defaults."""
        sys = JupiterXSystemConfig()
        assert sys.master_volume is None
        assert sys.master_tune is None

        eng = JupiterXEngineConfig()
        assert eng.enable is None
        assert eng.level is None
        assert eng.pan is None

        lfo = JupiterXPartLFO()
        assert lfo.waveform is None
        assert lfo.rate is None

        env = JupiterXPartEnvelope()
        assert env.attack is None
        assert env.decay is None

        mod = JupiterXPartModulation()
        assert mod.mod_wheel_depth is None
        assert mod.aftertouch_depth is None

        part = JupiterXPartConfig()
        assert part.level is None
        assert part.engines is None
        assert part.lfo is None
        assert part.envelope is None

        vcm = JupiterXVCMConfig()
        assert vcm.distortion_type is None
        assert vcm.chorus_type is None

        arp = JupiterXArpConfig()
        assert arp.enable is None
        assert arp.style is None

        jx = JupiterXConfig()
        assert jx.system is None
        assert jx.parts is None
        assert jx.effects is None
        assert jx.arpeggiator is None

    def test_jx_config_roundtrip(self):
        """Parse a YAML Jupiter-X config and verify typed fields."""
        yaml_str = """
xg_dsl_version: "3.0"
jupiter_x:
  system:
    master_volume: 110
    master_tune: 0
    master_transpose: 0
  parts:
    "0":
      level: 127
      volume: 100
      pan: 0
      reverb_send: 40
      delay_send: 20
      engines:
        analog:
          enable: true
          level: 120
          pan: 0
        digital:
          enable: false
          level: 0
      lfo:
        waveform: 0
        rate: 64
        depth: 32
      envelope:
        attack: 10
        decay: 50
        sustain: 100
        release: 40
      modulation:
        mod_wheel_depth: 80
        aftertouch_depth: 30
    "4":
      level: 100
      active_engine: 1
      coarse_tune: -5
      engines:
        analog:
          enable: true
          level: 100
        fm:
          enable: true
          level: 80
          coarse_tune: 12
  effects:
    distortion_type: "overdrive"
    distortion_drive: 75
    chorus_type: 1
    chorus_rate: 50
    delay_time: 60
    reverb_type: "hall1"
    reverb_time: 80
  arpeggiator:
    enable: true
    style: 0
    range: 2
    rate: 64
    swing: 0
"""
        from synth.xgml.parser import XGMLConfigParser
        parser = XGMLConfigParser()
        config = parser.parse_string(yaml_str)
        assert config is not None
        assert not parser.has_errors()

        jx = config.jupiter_x
        assert jx is not None

        # System
        assert jx.system is not None
        assert jx.system.master_volume == 110
        assert jx.system.master_tune == 0

        # Parts
        assert jx.parts is not None
        assert 0 in jx.parts
        p0 = jx.parts[0]
        assert p0.level == 127
        assert p0.volume == 100
        assert p0.pan == 0
        assert p0.reverb_send == 40
        assert p0.delay_send == 20

        # Engines on part 0
        assert p0.engines is not None
        assert "analog" in p0.engines
        ae = p0.engines["analog"]
        assert ae.enable is True
        assert ae.level == 120
        assert ae.pan == 0

        assert "digital" in p0.engines
        de = p0.engines["digital"]
        assert de.enable is False
        assert de.level == 0

        # LFO
        assert p0.lfo is not None
        assert p0.lfo.waveform == 0
        assert p0.lfo.rate == 64
        assert p0.lfo.depth == 32

        # Envelope
        assert p0.envelope is not None
        assert p0.envelope.attack == 10
        assert p0.envelope.sustain == 100

        # Modulation
        assert p0.modulation is not None
        assert p0.modulation.mod_wheel_depth == 80
        assert p0.modulation.aftertouch_depth == 30

        # Part 4 check
        assert 4 in jx.parts
        p4 = jx.parts[4]
        assert p4.active_engine == 1
        assert p4.coarse_tune == -5
        assert p4.engines is not None
        assert "analog" in p4.engines
        assert p4.engines["analog"].enable is True
        assert "fm" in p4.engines
        assert p4.engines["fm"].enable is True
        assert p4.engines["fm"].level == 80
        assert p4.engines["fm"].coarse_tune == 12

        # Effects
        assert jx.effects is not None
        assert jx.effects.distortion_type == "overdrive"
        assert jx.effects.distortion_drive == 75
        assert jx.effects.chorus_type == 1
        assert jx.effects.chorus_rate == 50
        assert jx.effects.delay_time == 60
        assert jx.effects.reverb_type == "hall1"
        assert jx.effects.reverb_time == 80

        # Arpeggiator
        assert jx.arpeggiator is not None
        assert jx.arpeggiator.enable is True
        assert jx.arpeggiator.style == 0
        assert jx.arpeggiator.range == 2
        assert jx.arpeggiator.rate == 64

    def test_jx_midi_bridge_system(self):
        """Translating Jupiter-X system params produces NRPN messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(jupiter_x=JupiterXConfig(
            system=JupiterXSystemConfig(master_volume=100, master_tune=5),
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Bridge order: master_volume (LSB 0x03) then master_tune (LSB 0x01)
        # Each = 3 CC messages (NRPN MSB, NRPN LSB, Data Entry)
        assert len(msgs) == 6
        # First trio: MSB 0x00, LSB 0x03 (master_volume)
        assert msgs[0].type == "control_change"
        assert msgs[0].controller == 99  # NRPN MSB
        assert msgs[0].value == 0x00
        assert msgs[1].type == "control_change"
        assert msgs[1].controller == 98  # NRPN LSB
        assert msgs[1].value == 0x03  # master_volume
        assert msgs[2].type == "control_change"
        assert msgs[2].controller == 6  # Data Entry
        assert msgs[2].value == 100  # volume value

        # Second trio: MSB 0x00, LSB 0x01 (master_tune), value = 5 + 64 = 69
        assert msgs[3].value == 0x00
        assert msgs[4].value == 0x01  # master_tune
        assert msgs[5].value == 69  # tune value (5 + 64 offset)

    def test_jx_midi_bridge_part(self):
        """Translating Jupiter-X part config produces NRPN messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(jupiter_x=JupiterXConfig(
            parts={
                0: JupiterXPartConfig(level=127, volume=100, pan=0, reverb_send=40),
                1: JupiterXPartConfig(level=100, coarse_tune=-5, delay_send=20),
            },
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Part 0: level (0x10, 0x00), volume (0x10, 0x06), pan (0x10, 0x01), reverb_send (0x10, 0x0B)
        # Part 1: level (0x11, 0x00), coarse_tune (0x11, 0x07), delay_send (0x11, 0x0A)
        # = 7 NRPN trios = 21 messages
        assert len(msgs) == 21

        # Check Part 0 level: MSB = 0x10, LSB = 0x00
        assert msgs[0].value == 0x10
        assert msgs[1].value == 0x00
        assert msgs[2].value == 127

        # Check Part 1 coarse_tune: MSB = 0x11, LSB = 0x07, value = -5 + 64 = 59
        # offset by 2 params before (part 0 level, pan...) wait let's count
        # Part 0: level, volume, pan, reverb_send = 4 trios
        # Part 1 starts at index 12
        p1_level_idx = 12
        assert msgs[p1_level_idx].value == 0x11  # MSB for part 1
        assert msgs[p1_level_idx + 1].value == 0x00  # level LSB
        # coarse_tune at idx 15 (level + 1 trio offset for C.T.)
        # Actually: level(0x00), coarse_tune(0x07), delay_send(0x0A) = 3 params = 9 msgs
        # So part 1 trio 2 = coarse_tune
        assert msgs[15].value == 0x11  # same MSB
        assert msgs[16].value == 0x07  # coarse_tune LSB
        assert msgs[17].value == 59  # -5 + 64

    def test_jx_midi_bridge_engine(self):
        """Translating Jupiter-X engine config produces NRPN with MSB 0x30+."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(jupiter_x=JupiterXConfig(
            parts={
                0: JupiterXPartConfig(
                    engines={
                        "analog": JupiterXEngineConfig(enable=True, level=120, pan=0),
                        "digital": JupiterXEngineConfig(enable=False, level=0),
                    },
                ),
            },
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Part 0 analog (engine_offset=0): MSB = 0x30 + 0*4 + 0 = 0x30
        #   enable(LSB=0x00), level(LSB=0x01), pan(LSB=0x02) = 3 trios
        # Part 0 digital (engine_offset=1): MSB = 0x30 + 0*4 + 1 = 0x31
        #   enable(LSB=0x00), level(LSB=0x01) = 2 trios
        # Total = 5 trios = 15 msgs
        assert len(msgs) == 15

        # Analog: MSB=0x30, LSB=0x00 (enable), value=1
        assert msgs[0].value == 0x30
        assert msgs[1].value == 0x00
        assert msgs[2].value == 1  # True

        # Analog level: LSB=0x01, value=120
        assert msgs[4].value == 0x01
        assert msgs[5].value == 120

        # Digital: MSB=0x31, LSB=0x00 (enable), value=0
        assert msgs[9].value == 0x31
        assert msgs[10].value == 0x00
        assert msgs[11].value == 0  # False

    def test_jx_midi_bridge_vcm(self):
        """Translating Jupiter-X VCM effects produces SysEx messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(jupiter_x=JupiterXConfig(
            effects=JupiterXVCMConfig(
                distortion_type="overdrive",
                distortion_drive=75,
                reverb_type="hall1",
                reverb_time=80,
                reverb_level=64,
            ),
        ))
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Distortion: type + drive = 2 SysEx
        # Reverb: type + time + level = 3 SysEx
        # Total = 5 SysEx messages
        assert len(msgs) == 5
        for m in msgs:
            assert m.type == "system_exclusive"

    def test_jx_config_in_xgml_document(self):
        """Jupiter-X config in a full XGML document alongside XG and GS."""
        yaml_str = """
xg_dsl_version: "3.0"
description: "Hybrid XG + GS + Jupiter-X test"
basic_messages:
  channels:
    "0":
      volume: 100
gs:
  system:
    master_volume: 90
jupiter_x:
  system:
    master_volume: 110
  parts:
    "0":
      level: 127
      volume: 100
      engines:
        analog:
          enable: true
          level: 120
"""
        from synth.xgml.parser import XGMLConfigParser
        parser = XGMLConfigParser()
        config = parser.parse_string(yaml_str)
        assert config is not None
        assert not parser.has_errors()

        assert config.description == "Hybrid XG + GS + Jupiter-X test"
        assert config.basic_messages is not None
        assert config.basic_messages.channels[0].volume == 100
        assert config.gs is not None
        assert config.gs.system is not None
        assert config.gs.system.master_volume == 90
        assert config.jupiter_x is not None
        assert config.jupiter_x.system is not None
        assert config.jupiter_x.system.master_volume == 110
        assert config.jupiter_x.parts is not None
        assert config.jupiter_x.parts[0].volume == 100
        assert config.jupiter_x.parts[0].engines["analog"].level == 120


# =============================================================================
# Sequence Event Tests (all MIDI message types)
# =============================================================================


class TestSequenceEventTypes:
    """Tests for all MIDI event types in sequences: note, CC, NRPN, pitch bend,
    aftertouch, SysEx — via types, parser roundtrip, and MIDI bridge."""

    # ------------------------------------------------------------------
    # Type-level tests
    # ------------------------------------------------------------------

    def test_sequence_event_defaults(self):
        """SequenceEvent fields all default to None."""
        se = SequenceEvent(at=0.0)
        assert se.note_on is None
        assert se.note_off is None
        assert se.control is None
        assert se.nrpn is None
        assert se.program is None
        assert se.tempo is None
        assert se.text is None
        assert se.pitch_bend is None
        assert se.channel_pressure is None
        assert se.poly_pressure is None
        assert se.sysex is None

    def test_sequence_event_all_fields(self):
        """Construct SequenceEvent with every field populated."""
        se = SequenceEvent(
            at=1.0,
            note_on=NoteEvent(note="C4", velocity=100, duration=0.5),
            note_off=NoteEvent(note="C4", velocity=64),
            control=ControlEvent(controller="volume", value=100),
            nrpn=NRPNEvent(msb=5, lsb=0, value=64),
            program="acoustic_grand_piano",
            tempo=140.0,
            text="verse",
            pitch_bend=0,
            channel_pressure=80,
            poly_pressure=[(60, 64), (64, 32)],
            sysex=[0x41, 0x10, 0x42, 0x12, 0x00, 0x00, 0x00, 0x40, 0x37],
        )
        assert se.at == 1.0
        assert se.note_on.note == "C4"
        assert se.note_off.note == "C4"
        assert se.control.controller == "volume"
        assert se.nrpn.msb == 5
        assert se.nrpn.value == 64
        assert se.program == "acoustic_grand_piano"
        assert se.tempo == 140.0
        assert se.channel_pressure == 80
        assert len(se.poly_pressure) == 2
        assert se.poly_pressure[0] == (60, 64)
        assert len(se.sysex) == 9

    # ------------------------------------------------------------------
    # Parser roundtrip tests
    # ------------------------------------------------------------------

    def test_parse_sequence_events_yaml(self):
        """Parse a sequence with every event type from YAML."""
        yaml_str = """
xg_dsl_version: "3.0"
sequences:
  demo:
    tempo: 120
    tracks:
      - channel: 0
        events:
          - at: 0.0
            note_on:
              note: C4
              velocity: 100
              duration: 1.0
          - at: 0.5
            note_off:
              note: C4
          - at: 1.0
            control:
              controller: volume
              value: 80
          - at: 1.5
            nrpn:
              msb: 5
              lsb: 0
              value: 64
          - at: 2.0
            program: 0
          - at: 2.5
            pitch_bend: 0
          - at: 3.0
            channel_pressure: 64
          - at: 3.5
            poly_pressure:
              - {note: 60, pressure: 80}
              - {note: 64, pressure: 40}
          - at: 4.0
            sysex: [0x41, 0x10, 0x42, 0x12, 0x00, 0x00, 0x00, 0x40, 0x37]
          - at: 4.5
            text: "marker"
          - at: 5.0
            tempo: 140
"""
        from synth.xgml.parser import XGMLConfigParser
        parser = XGMLConfigParser()
        config = parser.parse_string(yaml_str)
        assert config is not None, f"Parse errors: {parser.errors}"
        assert not parser.has_errors()

        seq = config.sequences["demo"]
        assert seq.tempo == 120
        assert len(seq.tracks) == 1
        t = seq.tracks[0]
        assert t.channel == 0
        assert len(t.events) == 11

        ev = t.events[0]
        assert ev.at == 0.0
        assert ev.note_on is not None
        assert ev.note_on.note == "C4"
        assert ev.note_on.velocity == 100
        assert ev.note_on.duration == 1.0

        ev = t.events[1]
        assert ev.at == 0.5
        assert ev.note_off is not None
        assert ev.note_off.note == "C4"

        ev = t.events[2]
        assert ev.at == 1.0
        assert ev.control is not None
        assert ev.control.controller == "volume"
        assert ev.control.value == 80
        # Verify it's a real ControlEvent instance
        from synth.xgml.types import ControlEvent as CE
        assert isinstance(ev.control, CE)

        ev = t.events[3]
        assert ev.at == 1.5
        assert ev.nrpn is not None
        assert ev.nrpn.msb == 5
        assert ev.nrpn.lsb == 0
        assert ev.nrpn.value == 64

        ev = t.events[4]
        assert ev.program == 0

        ev = t.events[5]
        assert ev.pitch_bend == 0

        ev = t.events[6]
        assert ev.channel_pressure == 64

        ev = t.events[7]
        assert ev.poly_pressure is not None
        assert (60, 80) in ev.poly_pressure
        assert (64, 40) in ev.poly_pressure

        ev = t.events[8]
        assert ev.sysex is not None
        assert len(ev.sysex) == 9
        assert ev.sysex[0] == 0x41

        ev = t.events[9]
        assert ev.text == "marker"

        ev = t.events[10]
        assert ev.tempo == 140

    # ------------------------------------------------------------------
    # MIDI bridge tests
    # ------------------------------------------------------------------

    def test_midi_bridge_tempo(self):
        """Tempo event in sequence produces set-tempo meta event."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, volume=None, events=[
                    SequenceEvent(at=1.0, tempo=140.0),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        tempo_msgs = [m for m in msgs if m.type == "meta_event" and m.data.get("meta_type") == 0x51]
        assert len(tempo_msgs) == 1
        # 140 BPM = 60000000/140 ≈ 428571 us/qnote
        data = tempo_msgs[0].data["data"]
        us = (data[0] << 16) | (data[1] << 8) | data[2]
        assert abs(us - 428571) < 100
        # Timestamp: 1.0 beat at 120 BPM = 0.5 sec
        assert abs(tempo_msgs[0].timestamp - 0.5) < 0.001

    def test_midi_bridge_text(self):
        """Text event in sequence produces text meta event."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, volume=None, events=[
                    SequenceEvent(at=0.5, text="verse"),
                    SequenceEvent(at=1.0, text="chorus"),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        text_msgs = [m for m in msgs if m.type == "meta_event" and m.data.get("meta_type") == 0x01]
        assert len(text_msgs) == 2
        assert text_msgs[0].data["data"] == [ord(c) for c in "verse"]
        assert text_msgs[1].data["data"] == [ord(c) for c in "chorus"]
        # Timestamp: 0.5 beat at 120 BPM = 0.25 sec
        assert abs(text_msgs[0].timestamp - 0.25) < 0.001

    def test_midi_bridge_port(self):
        """Track port is stamped onto all emitted messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, port=1, volume=None, events=[
                    SequenceEvent(at=0.0, note_on=NoteEvent(note=60, velocity=100)),
                    SequenceEvent(at=0.5, control=ControlEvent(controller=7, value=80)),
                ]),
                Track(channel=5, port=2, volume=None, events=[
                    SequenceEvent(at=0.0, note_on=NoteEvent(note=64, velocity=100)),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # Messages from track 1 (port=1) should have port=1
        track1_msgs = [m for m in msgs if abs(m.timestamp - 0.0) < 0.001 and m.type in ("note_on",)]
        # Messages from track 2 (port=2) should have port=2
        track2_msgs = [m for m in msgs if m.type == "note_on" and m.note == 64]

        # Both messages at t=0 should be from track 1 (port=1)
        for m in msgs:
            if m.type == "note_on" and m.note == 60:
                assert m.data.get("port") == 1
            elif m.type == "note_on" and m.note == 64:
                assert m.data.get("port") == 2
            elif m.type == "control_change":
                assert m.data.get("port") == 1

    def test_midi_bridge_note_off(self):
        """Explicit note_off in sequence produces note_off MIDI message."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, events=[
                    SequenceEvent(at=1.0, note_off=NoteEvent(note="C4", velocity=64)),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        note_offs = [m for m in msgs if m.type == "note_off"]
        assert len(note_offs) == 1
        assert note_offs[0].note == 60  # C4
        assert note_offs[0].velocity == 64
        # 1.0 beats at 120 BPM = 0.5 seconds
        assert abs(note_offs[0].timestamp - 0.5) < 0.001

    def test_midi_bridge_nrpn(self):
        """NRPN event in sequence produces 3 CC messages per value."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, volume=None, events=[
                    SequenceEvent(at=0.0, nrpn=NRPNEvent(msb=5, lsb=0, value=64)),
                    SequenceEvent(at=1.0, nrpn=NRPNEvent(msb=31, lsb=0, value=8)),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        # 2 NRPN events × 3 CC messages each = 6 (no track setup CCs)
        nrpn_ccs = [m for m in msgs if m.type == "control_change"]
        assert len(nrpn_ccs) == 6

        # First NRPN: MSB=5, LSB=0, value=64
        assert nrpn_ccs[0].controller == 99  # NRPN MSB
        assert nrpn_ccs[0].value == 5
        assert nrpn_ccs[1].controller == 98  # NRPN LSB
        assert nrpn_ccs[1].value == 0
        assert nrpn_ccs[2].controller == 6   # Data Entry
        assert nrpn_ccs[2].value == 64

        # Second NRPN: MSB=31, LSB=0, value=8
        assert nrpn_ccs[3].value == 31
        assert nrpn_ccs[4].value == 0
        assert nrpn_ccs[5].value == 8

    def test_midi_bridge_channel_pressure(self):
        """Channel pressure event produces channel_pressure MIDI message."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=5, events=[
                    SequenceEvent(at=0.0, channel_pressure=100),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        pressure_msgs = [m for m in msgs if m.type == "channel_pressure"]
        assert len(pressure_msgs) == 1
        assert pressure_msgs[0].channel == 5
        assert pressure_msgs[0].pressure == 100

    def test_midi_bridge_poly_pressure(self):
        """Poly pressure events produce poly_pressure MIDI messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, events=[
                    SequenceEvent(at=0.0, poly_pressure=[(60, 80), (64, 40)]),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        poly_msgs = [m for m in msgs if m.type == "poly_pressure"]
        assert len(poly_msgs) == 2
        assert poly_msgs[0].note == 60
        assert poly_msgs[0].pressure == 80
        assert poly_msgs[1].note == 64
        assert poly_msgs[1].pressure == 40

    def test_midi_bridge_sysex(self):
        """SysEx event in sequence produces system_exclusive MIDI message."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        raw = [0x41, 0x10, 0x42, 0x12, 0x00, 0x00, 0x00, 0x40, 0x37]
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, events=[
                    SequenceEvent(at=0.0, sysex=raw),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)
        sx_msgs = [m for m in msgs if m.type == "system_exclusive"]
        assert len(sx_msgs) == 1
        # MIDIMessage stores SysEx data in data["data"]
        assert sx_msgs[0].data["data"] == [b & 0x7F for b in raw]

    def test_midi_bridge_mixed_events(self):
        """Multiple event types in the same sequence produce correct messages."""
        from synth.xgml.bridges.midi import XGMLMIDIBridge
        cfg = XGMLConfig(sequences={
            "test": Sequence(tempo=120, tracks=[
                Track(channel=0, events=[
                    SequenceEvent(at=0.0, note_on=NoteEvent(note="C4", velocity=100)),
                    SequenceEvent(at=0.5, control=ControlEvent(controller=7, value=80)),
                    SequenceEvent(at=1.0, nrpn=NRPNEvent(msb=5, lsb=0, value=64)),
                    SequenceEvent(at=1.5, pitch_bend=0),
                    SequenceEvent(at=2.0, channel_pressure=64),
                    SequenceEvent(at=2.5, poly_pressure=[(60, 80)]),
                    SequenceEvent(at=3.0, sysex=[0x41, 0x00, 0x42, 0x12, 0x00, 0x00, 0x00, 0x40, 0x37]),
                ]),
            ]),
        })
        bridge = XGMLMIDIBridge()
        msgs = bridge.translate(cfg)

        types = [m.type for m in msgs]
        assert "note_on" in types
        assert "control_change" in types
        assert "pitch_bend" in types
        assert "channel_pressure" in types
        assert "poly_pressure" in types
        assert "system_exclusive" in types

        # Verify timestamps are correct (1 beat = 0.5 sec at 120 BPM)
        # Track also emits initial program+volume, so don't index by position
        for m in msgs:
            if m.type == "note_on":
                assert abs(m.timestamp - 0.0) < 0.001
            elif m.type == "channel_pressure":
                assert abs(m.timestamp - 1.0) < 0.001  # 2.0 beats * 0.5
            elif m.type == "system_exclusive":
                assert abs(m.timestamp - 1.5) < 0.001  # 3.0 beats * 0.5
