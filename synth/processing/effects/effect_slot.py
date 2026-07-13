"""EffectSlot — configurable processing stage for the effects pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EffectStageType(Enum):
    """Types of effect stages in the processing pipeline."""

    INSERTION = "insertion"  # Per-channel insertion effects
    MIX = "mix"  # Channel mixing with effect sends
    VCM = "vcm"  # Jupiter-X VCM effects chain
    VARIATION = "variation"  # Variation (MFX) effects
    SYSTEM_REVERB = "system_reverb"  # System reverb effect
    SYSTEM_CHORUS = "system_chorus"  # System chorus effect
    SYSTEM_DELAY = "system_delay"  # System delay effect (SC-8850)
    MASTER = "master"  # Master processing (EQ + level)


@dataclass(slots=True)
class EffectSlot:
    """A single processing stage in the effects pipeline.

    Attributes:
        stage_type: The type of effect stage
        enabled: Whether this stage is active in the pipeline
        bypass: Whether audio passes through without processing
        wet_dry: Wet/dry mix ratio (0.0 = dry, 1.0 = wet)
        params: Additional parameters for this stage
    """

    stage_type: EffectStageType
    enabled: bool = True
    bypass: bool = False
    wet_dry: float = 1.0
    params: dict[str, Any] = field(default_factory=dict)
