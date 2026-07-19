"""Tests for acoustic behavior configuration and program mapping."""

from __future__ import annotations

import pytest

from synth.engines.acoustic.behavior_config import (
    BehaviorConfig,
    EnsembleConfig,
    InstrumentGroup,
    program_to_group,
)


class TestInstrumentGroup:
    """The 18 supported acoustic groups."""

    @pytest.mark.unit
    def test_eighteen_groups(self):
        assert len(list(InstrumentGroup)) == 18

    @pytest.mark.unit
    def test_group_is_str_enum(self):
        assert InstrumentGroup.ACOUSTIC_PIANO == "acoustic_piano"
        assert InstrumentGroup.ACOUSTIC_PIANO.value == "acoustic_piano"


class TestProgramToGroup:
    """GM/XG program number -> InstrumentGroup mapping."""

    @pytest.mark.unit
    def test_piano_family(self):
        assert program_to_group(0) == InstrumentGroup.ACOUSTIC_PIANO
        assert program_to_group(4) == InstrumentGroup.ELECTRIC_PIANO

    @pytest.mark.unit
    def test_strings_and_choir(self):
        assert program_to_group(40) == InstrumentGroup.BOWED_STRINGS
        assert program_to_group(42) == InstrumentGroup.CHOIR

    @pytest.mark.unit
    def test_brass_and_woodwinds(self):
        # GM 48-55 = brass, 56-63 = reeds/woodwinds (per map)
        assert program_to_group(48) == InstrumentGroup.BRASS
        assert program_to_group(55) == InstrumentGroup.BRASS
        assert program_to_group(56) == InstrumentGroup.REEDS_WOODWINDS
        assert program_to_group(60) == InstrumentGroup.REEDS_WOODWINDS

    @pytest.mark.unit
    def test_out_of_range_wraps(self):
        # program % 128
        assert program_to_group(128) == program_to_group(0)
        assert program_to_group(-1) == program_to_group(127)


class TestBehaviorConfig:
    """Per-group config factories and JSON serialization."""

    @pytest.mark.unit
    def test_for_group_piano_defaults(self):
        cfg = BehaviorConfig.for_group(InstrumentGroup.ACOUSTIC_PIANO)
        assert cfg.group == InstrumentGroup.ACOUSTIC_PIANO
        assert cfg.key_off_noise is True
        assert cfg.velocity_to_decay is False

    @pytest.mark.unit
    def test_for_group_mallets_decay(self):
        cfg = BehaviorConfig.for_group(InstrumentGroup.MALLETS)
        assert cfg.velocity_to_decay is True
        assert cfg.sympathetic_resonance is True

    @pytest.mark.unit
    def test_for_group_section_ensembles(self):
        cfg = BehaviorConfig.for_group(InstrumentGroup.BOWED_STRINGS)
        assert cfg.ensemble.voicing_mode == "section"
        assert cfg.ensemble.shared_vibrato is True
        assert cfg.ensemble_detune is True

    @pytest.mark.unit
    def test_json_round_trip(self):
        cfg = BehaviorConfig.for_group(InstrumentGroup.ACOUSTIC_PIANO)
        data = cfg.to_dict()
        restored = BehaviorConfig.from_dict(data)
        assert restored.group == cfg.group
        assert restored.ensemble.section_size == cfg.ensemble.section_size
        assert restored.sympathetic_resonance == cfg.sympathetic_resonance

    @pytest.mark.unit
    def test_ensemble_has_vibrato_rate(self):
        assert isinstance(EnsembleConfig().vibrato_rate_hz, float)
        assert EnsembleConfig().vibrato_rate_hz > 0.0
