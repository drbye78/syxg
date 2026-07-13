"""PipelineTopology — configurable effects pipeline with named presets."""

from __future__ import annotations

from dataclasses import dataclass, field

from .effect_slot import EffectSlot, EffectStageType


@dataclass
class PipelineTopology:
    """Ordered list of effect stages forming a processing pipeline.

    Provides named presets matching common effect configurations.
    Stages can be added, removed, reordered, enabled, or bypassed at runtime.

    Presets:
        XG_STANDARD: Default XG pipeline (current hardcoded order)
        GS_STANDARD: GS-typical pipeline
        SC8850: SC-8850 pipeline (adds system delay)
    """

    name: str
    stages: list[EffectSlot] = field(default_factory=list)

    @staticmethod
    def xg_standard() -> PipelineTopology:
        """Default XG processing pipeline — matches current hardcoded order."""
        return PipelineTopology(
            name="XG_STANDARD",
            stages=[
                EffectSlot(EffectStageType.INSERTION),
                EffectSlot(EffectStageType.MIX),
                EffectSlot(EffectStageType.VCM),
                EffectSlot(EffectStageType.VARIATION),
                EffectSlot(EffectStageType.SYSTEM_REVERB),
                EffectSlot(EffectStageType.SYSTEM_CHORUS),
                EffectSlot(EffectStageType.MASTER),
            ],
        )

    @staticmethod
    def gs_standard() -> PipelineTopology:
        """GS-typical processing pipeline (reverb + chorus only, no variation insert)."""
        return PipelineTopology(
            name="GS_STANDARD",
            stages=[
                EffectSlot(EffectStageType.MIX),
                EffectSlot(EffectStageType.VCM),
                EffectSlot(EffectStageType.SYSTEM_REVERB),
                EffectSlot(EffectStageType.SYSTEM_CHORUS),
                EffectSlot(EffectStageType.MASTER),
            ],
        )

    @staticmethod
    def sc8850() -> PipelineTopology:
        """SC-8850 pipeline — adds System Delay alongside reverb/chorus."""
        return PipelineTopology(
            name="SC8850",
            stages=[
                EffectSlot(EffectStageType.INSERTION),
                EffectSlot(EffectStageType.MIX),
                EffectSlot(EffectStageType.VCM),
                EffectSlot(EffectStageType.VARIATION),
                EffectSlot(EffectStageType.SYSTEM_DELAY),
                EffectSlot(EffectStageType.SYSTEM_REVERB),
                EffectSlot(EffectStageType.SYSTEM_CHORUS),
                EffectSlot(EffectStageType.MASTER),
            ],
        )

    def add_stage(self, stage: EffectSlot, index: int | None = None) -> None:
        """Add a stage at the given index (default: end)."""
        if index is None:
            self.stages.append(stage)
        else:
            self.stages.insert(index, stage)

    def remove_stage(self, stage_type: EffectStageType) -> bool:
        """Remove the first occurrence of a stage type. Returns True if found."""
        for i, stage in enumerate(self.stages):
            if stage.stage_type == stage_type:
                del self.stages[i]
                return True
        return False

    def set_stage_enabled(self, stage_type: EffectStageType, enabled: bool) -> bool:
        """Enable or disable a stage by type. Returns True if found."""
        for stage in self.stages:
            if stage.stage_type == stage_type:
                stage.enabled = enabled
                return True
        return False

    def set_stage_bypass(self, stage_type: EffectStageType, bypass: bool) -> bool:
        """Bypass or un-bypass a stage by type. Returns True if found."""
        for stage in self.stages:
            if stage.stage_type == stage_type:
                stage.bypass = bypass
                return True
        return False

    def get_stage(self, stage_type: EffectStageType) -> EffectSlot | None:
        """Get the first stage matching the given type."""
        for stage in self.stages:
            if stage.stage_type == stage_type:
                return stage
        return None
