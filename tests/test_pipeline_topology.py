"""Tests for PipelineTopology — configurable effects pipeline with named presets.

Tests cover:
- EffectStageType enum values (including SYSTEM_DELAY)
- All 3 named presets (XG_STANDARD, GS_STANDARD, SC8850)
- Stage management (add, remove, reorder)
- Stage enable/bypass toggling
- Stage lookup
"""

from __future__ import annotations

import pytest

from synth.processing.effects.pipeline_topology import PipelineTopology
from synth.processing.effects.effect_slot import EffectSlot, EffectStageType


# ---------------------------------------------------------------------------
# EffectStageType tests
# ---------------------------------------------------------------------------

class TestEffectStageType:
    """EffectStageType enum correctness."""

    def test_all_types_present(self):
        types = {e.value for e in EffectStageType}
        expected = {
            "insertion", "mix", "vcm", "variation",
            "system_reverb", "system_chorus", "system_delay", "master",
        }
        assert types == expected

    def test_system_delay_included(self):
        """SYSTEM_DELAY is the new stage added for SC-8850."""
        assert EffectStageType.SYSTEM_DELAY.value == "system_delay"

    def test_stage_type_distinct(self):
        stages = list(EffectStageType)
        assert len(stages) == len({s.value for s in stages})

    def test_insertion(self):
        assert EffectStageType.INSERTION.value == "insertion"

    def test_mix(self):
        assert EffectStageType.MIX.value == "mix"

    def test_vcm(self):
        assert EffectStageType.VCM.value == "vcm"

    def test_variation(self):
        assert EffectStageType.VARIATION.value == "variation"

    def test_system_reverb(self):
        assert EffectStageType.SYSTEM_REVERB.value == "system_reverb"

    def test_system_chorus(self):
        assert EffectStageType.SYSTEM_CHORUS.value == "system_chorus"

    def test_master(self):
        assert EffectStageType.MASTER.value == "master"


# ---------------------------------------------------------------------------
# EffectSlot tests (lightweight — used by PipelineTopology)
# ---------------------------------------------------------------------------

class TestEffectSlot:
    """EffectSlot dataclass fields."""

    def test_default_construction(self):
        slot = EffectSlot(EffectStageType.SYSTEM_DELAY)
        assert slot.stage_type == EffectStageType.SYSTEM_DELAY
        assert slot.enabled is True
        assert slot.bypass is False
        assert slot.wet_dry == 1.0
        assert slot.params == {}

    def test_custom_params(self):
        slot = EffectSlot(EffectStageType.INSERTION, enabled=False, wet_dry=0.5)
        assert slot.stage_type == EffectStageType.INSERTION
        assert slot.enabled is False
        assert slot.wet_dry == 0.5

    def test_slots_enabled(self):
        """EffectSlot uses @dataclass(slots=True)."""
        slot = EffectSlot(EffectStageType.MASTER)
        with pytest.raises(AttributeError):
            slot.nonexistent_attr = "should_fail"


# ---------------------------------------------------------------------------
# Preset tests
# ---------------------------------------------------------------------------

class TestPipelineTopologyXGStandard:
    """XG_STANDARD preset."""

    def test_preset_name(self):
        topo = PipelineTopology.xg_standard()
        assert topo.name == "XG_STANDARD"

    def test_stage_count(self):
        topo = PipelineTopology.xg_standard()
        assert len(topo.stages) == 7

    def test_stage_order(self):
        topo = PipelineTopology.xg_standard()
        expected = [
            EffectStageType.INSERTION,
            EffectStageType.MIX,
            EffectStageType.VCM,
            EffectStageType.VARIATION,
            EffectStageType.SYSTEM_REVERB,
            EffectStageType.SYSTEM_CHORUS,
            EffectStageType.MASTER,
        ]
        actual = [s.stage_type for s in topo.stages]
        assert actual == expected

    def test_all_stages_enabled_by_default(self):
        topo = PipelineTopology.xg_standard()
        assert all(s.enabled for s in topo.stages)

    def test_no_stage_bypassed(self):
        topo = PipelineTopology.xg_standard()
        assert all(not s.bypass for s in topo.stages)


class TestPipelineTopologyGSStandard:
    """GS_STANDARD preset."""

    def test_preset_name(self):
        topo = PipelineTopology.gs_standard()
        assert topo.name == "GS_STANDARD"

    def test_stage_count(self):
        topo = PipelineTopology.gs_standard()
        assert len(topo.stages) == 5

    def test_stage_order(self):
        topo = PipelineTopology.gs_standard()
        expected = [
            EffectStageType.MIX,
            EffectStageType.VCM,
            EffectStageType.SYSTEM_REVERB,
            EffectStageType.SYSTEM_CHORUS,
            EffectStageType.MASTER,
        ]
        actual = [s.stage_type for s in topo.stages]
        assert actual == expected

    def test_no_insertion_or_variation(self):
        """GS standard omits insertion and variation stages."""
        topo = PipelineTopology.gs_standard()
        types = {s.stage_type for s in topo.stages}
        assert EffectStageType.INSERTION not in types
        assert EffectStageType.VARIATION not in types
        assert EffectStageType.SYSTEM_DELAY not in types


class TestPipelineTopologySC8850:
    """SC8850 preset — adds SYSTEM_DELAY."""

    def test_preset_name(self):
        topo = PipelineTopology.sc8850()
        assert topo.name == "SC8850"

    def test_stage_count(self):
        """SC8850 has 8 stages (7 from XG + SYSTEM_DELAY)."""
        topo = PipelineTopology.sc8850()
        assert len(topo.stages) == 8

    def test_stage_order(self):
        """SYSTEM_DELAY sits between VARIATION and SYSTEM_REVERB."""
        topo = PipelineTopology.sc8850()
        expected = [
            EffectStageType.INSERTION,
            EffectStageType.MIX,
            EffectStageType.VCM,
            EffectStageType.VARIATION,
            EffectStageType.SYSTEM_DELAY,
            EffectStageType.SYSTEM_REVERB,
            EffectStageType.SYSTEM_CHORUS,
            EffectStageType.MASTER,
        ]
        actual = [s.stage_type for s in topo.stages]
        assert actual == expected

    def test_system_delay_present(self):
        topo = PipelineTopology.sc8850()
        assert any(s.stage_type == EffectStageType.SYSTEM_DELAY for s in topo.stages)


# ---------------------------------------------------------------------------
# Stage management tests
# ---------------------------------------------------------------------------

class TestPipelineTopologyAddStage:
    """add_stage method."""

    def test_append_default(self):
        topo = PipelineTopology(name="test")
        slot = EffectSlot(EffectStageType.SYSTEM_DELAY)
        topo.add_stage(slot)
        assert topo.stages[-1] is slot
        assert len(topo.stages) == 1

    def test_insert_at_index(self):
        topo = PipelineTopology.xg_standard()
        delay = EffectSlot(EffectStageType.SYSTEM_DELAY)
        topo.add_stage(delay, index=3)  # After VCM, before VARIATION
        assert topo.stages[3].stage_type == EffectStageType.SYSTEM_DELAY
        assert topo.stages[4].stage_type == EffectStageType.VARIATION
        assert len(topo.stages) == 8

    def test_insert_at_zero(self):
        topo = PipelineTopology(name="test")
        topo.add_stage(EffectSlot(EffectStageType.MASTER))
        topo.add_stage(EffectSlot(EffectStageType.MIX), index=0)
        assert topo.stages[0].stage_type == EffectStageType.MIX
        assert topo.stages[1].stage_type == EffectStageType.MASTER

    def test_insert_at_end_with_index(self):
        topo = PipelineTopology.gs_standard()
        count = len(topo.stages)
        topo.add_stage(EffectSlot(EffectStageType.SYSTEM_DELAY), index=count)
        assert topo.stages[-1].stage_type == EffectStageType.SYSTEM_DELAY


class TestPipelineTopologyRemoveStage:
    """remove_stage method."""

    def test_remove_existing(self):
        topo = PipelineTopology.xg_standard()
        result = topo.remove_stage(EffectStageType.VCM)
        assert result is True
        assert EffectStageType.VCM not in [s.stage_type for s in topo.stages]
        assert len(topo.stages) == 6

    def test_remove_nonexistent(self):
        topo = PipelineTopology.xg_standard()
        result = topo.remove_stage(EffectStageType.SYSTEM_DELAY)
        assert result is False
        assert len(topo.stages) == 7

    def test_remove_first_only(self):
        topo = PipelineTopology(name="test")
        topo.add_stage(EffectSlot(EffectStageType.MIX))
        topo.add_stage(EffectSlot(EffectStageType.MIX))
        topo.remove_stage(EffectStageType.MIX)
        assert len(topo.stages) == 1

    def test_remove_from_empty(self):
        topo = PipelineTopology(name="empty")
        result = topo.remove_stage(EffectStageType.MASTER)
        assert result is False


class TestPipelineTopologySetEnabled:
    """set_stage_enabled method."""

    def test_disable_stage(self):
        topo = PipelineTopology.xg_standard()
        result = topo.set_stage_enabled(EffectStageType.VARIATION, False)
        assert result is True
        stage = topo.get_stage(EffectStageType.VARIATION)
        assert stage is not None
        assert stage.enabled is False

    def test_reenable_stage(self):
        topo = PipelineTopology.xg_standard()
        topo.set_stage_enabled(EffectStageType.VARIATION, False)
        topo.set_stage_enabled(EffectStageType.VARIATION, True)
        stage = topo.get_stage(EffectStageType.VARIATION)
        assert stage is not None
        assert stage.enabled is True

    def test_enable_nonexistent(self):
        topo = PipelineTopology(name="test")
        result = topo.set_stage_enabled(EffectStageType.SYSTEM_DELAY, False)
        assert result is False

    def test_disable_master(self):
        topo = PipelineTopology.xg_standard()
        result = topo.set_stage_enabled(EffectStageType.MASTER, False)
        assert result is True
        assert topo.get_stage(EffectStageType.MASTER).enabled is False


class TestPipelineTopologySetBypass:
    """set_stage_bypass method."""

    def test_bypass_stage(self):
        topo = PipelineTopology.xg_standard()
        result = topo.set_stage_bypass(EffectStageType.SYSTEM_REVERB, True)
        assert result is True
        stage = topo.get_stage(EffectStageType.SYSTEM_REVERB)
        assert stage.bypass is True

    def test_unbypass_stage(self):
        topo = PipelineTopology.xg_standard()
        topo.set_stage_bypass(EffectStageType.SYSTEM_REVERB, True)
        topo.set_stage_bypass(EffectStageType.SYSTEM_REVERB, False)
        stage = topo.get_stage(EffectStageType.SYSTEM_REVERB)
        assert stage.bypass is False

    def test_bypass_nonexistent(self):
        topo = PipelineTopology.gs_standard()
        result = topo.set_stage_bypass(EffectStageType.INSERTION, True)
        assert result is False


class TestPipelineTopologyGetStage:
    """get_stage method."""

    def test_get_existing(self):
        topo = PipelineTopology.sc8850()
        stage = topo.get_stage(EffectStageType.SYSTEM_DELAY)
        assert stage is not None
        assert stage.stage_type == EffectStageType.SYSTEM_DELAY

    def test_get_nonexistent(self):
        topo = PipelineTopology.gs_standard()
        stage = topo.get_stage(EffectStageType.INSERTION)
        assert stage is None

    def test_get_first_match(self):
        topo = PipelineTopology(name="test")
        a = EffectSlot(EffectStageType.MIX)
        b = EffectSlot(EffectStageType.MIX)
        topo.add_stage(a)
        topo.add_stage(b)
        assert topo.get_stage(EffectStageType.MIX) is a


class TestPipelineTopologyPresetsIndependent:
    """Each preset call returns a fresh independent topology."""

    def test_xg_independent_copies(self):
        a = PipelineTopology.xg_standard()
        b = PipelineTopology.xg_standard()
        assert a is not b
        assert a.stages is not b.stages
        a.remove_stage(EffectStageType.MASTER)
        assert len(b.stages) == 7  # b unaffected

    def test_sc8850_independent_copies(self):
        a = PipelineTopology.sc8850()
        b = PipelineTopology.sc8850()
        a.add_stage(EffectSlot(EffectStageType.MIX))
        assert len(b.stages) == 8

    def test_presets_not_aliased(self):
        xg = PipelineTopology.xg_standard()
        gs = PipelineTopology.gs_standard()
        sc = PipelineTopology.sc8850()
        assert xg is not gs is not sc


class TestPipelineTopologyMutations:
    """Combined mutation scenarios."""

    def test_remove_then_add(self):
        topo = PipelineTopology.sc8850()
        topo.remove_stage(EffectStageType.VARIATION)
        assert len(topo.stages) == 7
        topo.add_stage(EffectSlot(EffectStageType.VARIATION), index=3)
        assert topo.stages[3].stage_type == EffectStageType.VARIATION

    def test_disable_and_bypass_different_stages(self):
        topo = PipelineTopology.xg_standard()
        topo.set_stage_enabled(EffectStageType.VARIATION, False)
        topo.set_stage_bypass(EffectStageType.SYSTEM_REVERB, True)
        assert topo.get_stage(EffectStageType.VARIATION).enabled is False
        assert topo.get_stage(EffectStageType.SYSTEM_REVERB).bypass is True

    def test_custom_name(self):
        topo = PipelineTopology(name="Custom")
        assert topo.name == "Custom"

    def test_construct_with_stages(self):
        stages = [EffectSlot(EffectStageType.MASTER)]
        topo = PipelineTopology(name="Minimal", stages=stages)
        assert len(topo.stages) == 1
        assert topo.stages[0].stage_type == EffectStageType.MASTER
