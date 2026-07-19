"""Behavior configuration for the SuperNATURAL-Acoustic alike engine.

Defines per-instrument-group behavior parameters and the higher-level
ensemble/scene configuration (solo vs section) that drives cross-note
dynamics. Config is JSON-serializable (no pickle) per project rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class InstrumentGroup(StrEnum):
    """The 18 supported acoustic instrument groups (match + surpass SN-A)."""

    ACOUSTIC_PIANO = "acoustic_piano"
    ELECTRIC_PIANO = "electric_piano"
    ORGAN = "organ"
    ACOUSTIC_GUITAR = "acoustic_guitar"
    ELECTRIC_GUITAR = "electric_guitar"
    ACOUSTIC_BASS = "acoustic_bass"
    ELECTRIC_BASS = "electric_bass"
    BOWED_STRINGS = "bowed_strings"
    MALLETS = "mallets"
    TIMPANI = "timpani"
    BRASS = "brass"
    REEDS_WOODWINDS = "reeds_woodwinds"
    ETHNIC = "ethnic"
    PLUCKED_WORLD = "plucked_world"
    ACCORDION = "accordion"
    CHOIR = "choir"
    HARP = "harp"
    FREE_REED = "free_reed"


@dataclass(slots=True)
class EnsembleConfig:
    """Scene-level configuration above a single instrument group.

    Drives cross-note ensemble behavior (section vs solo, shared vibrato,
    detune spread). Serializable to JSON.
    """

    voicing_mode: str = "solo"  # 'solo' | 'section'
    section_size: int = 8
    blend_amount: float = 0.5  # 0..1 how much section blending applies
    shared_vibrato: bool = False  # section voices share vibrato phase
    detune_spread_cents: float = 6.0  # max detune spread across a section
    vibrato_rate_hz: float = 5.0  # shared vibrato rate for section coherence

    def to_dict(self) -> dict[str, Any]:
        return {
            "voicing_mode": self.voicing_mode,
            "section_size": self.section_size,
            "blend_amount": self.blend_amount,
            "shared_vibrato": self.shared_vibrato,
            "detune_spread_cents": self.detune_spread_cents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnsembleConfig:
        return cls(
            voicing_mode=data.get("voicing_mode", "solo"),
            section_size=data.get("section_size", 8),
            blend_amount=data.get("blend_amount", 0.5),
            shared_vibrato=data.get("shared_vibrato", False),
            detune_spread_cents=data.get("detune_spread_cents", 6.0),
        )


@dataclass(slots=True)
class BehaviorConfig:
    """Per-instrument-group behavior configuration.

    Combines SFZ-native coverage (handled by the sampler) with the
    custom-DSP flags the behavior layer implements. Serializable to JSON.
    """

    group: InstrumentGroup = InstrumentGroup.ACOUSTIC_PIANO
    ensemble: EnsembleConfig = field(default_factory=EnsembleConfig)

    # --- Single-note (Layer A) flags ---
    velocity_to_brightness: bool = True
    velocity_to_decay: bool = False  # mallets: harder = shorter
    key_off_noise: bool = True
    legato_enabled: bool = True
    portamento_ms: float = 40.0
    articulation_keyswitch: bool = False  # uses SFZ sw_last

    # --- Cross-note (Layer B) flags ---
    sympathetic_resonance: bool = True  # shared bus
    damper_resonance: bool = True
    ensemble_detune: bool = False  # enabled when section mode
    phrase_detection: bool = True  # roll/trill/held-chord detection
    register_context: bool = True  # una-corda / lid / brightness from register

    # --- Group-specific tuning ---
    resonance_coupling: float = 0.15  # US5468906A coupling constant
    resonance_loop_gain: float = 0.99  # < 1.0 for stability
    key_off_noise_ms: float = 18.0
    performance_noise_cc: int | None = None  # CC driving continuous noise (CC2/CC16/CC11)
    variant: str = "default"  # e.g. 'grand' | 'upright' for piano
    decay_velocity_sensitivity: float = 0.0  # mallets: harder = shorter decay

    def to_dict(self) -> dict[str, Any]:
        return {
            "group": self.group.value,
            "ensemble": self.ensemble.to_dict(),
            "velocity_to_brightness": self.velocity_to_brightness,
            "velocity_to_decay": self.velocity_to_decay,
            "key_off_noise": self.key_off_noise,
            "legato_enabled": self.legato_enabled,
            "portamento_ms": self.portamento_ms,
            "articulation_keyswitch": self.articulation_keyswitch,
            "sympathetic_resonance": self.sympathetic_resonance,
            "damper_resonance": self.damper_resonance,
            "ensemble_detune": self.ensemble_detune,
            "phrase_detection": self.phrase_detection,
            "register_context": self.register_context,
            "resonance_coupling": self.resonance_coupling,
            "resonance_loop_gain": self.resonance_loop_gain,
            "key_off_noise_ms": self.key_off_noise_ms,
            "performance_noise_cc": self.performance_noise_cc,
            "variant": self.variant,
            "decay_velocity_sensitivity": self.decay_velocity_sensitivity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BehaviorConfig:
        group = InstrumentGroup(data.get("group", "acoustic_piano"))
        ensemble = EnsembleConfig.from_dict(data.get("ensemble", {}))
        return cls(
            group=group,
            ensemble=ensemble,
            velocity_to_brightness=data.get("velocity_to_brightness", True),
            velocity_to_decay=data.get("velocity_to_decay", False),
            key_off_noise=data.get("key_off_noise", True),
            legato_enabled=data.get("legato_enabled", True),
            portamento_ms=data.get("portamento_ms", 40.0),
            articulation_keyswitch=data.get("articulation_keyswitch", False),
            sympathetic_resonance=data.get("sympathetic_resonance", True),
            damper_resonance=data.get("damper_resonance", True),
            ensemble_detune=data.get("ensemble_detune", False),
            phrase_detection=data.get("phrase_detection", True),
            register_context=data.get("register_context", True),
            resonance_coupling=data.get("resonance_coupling", 0.15),
            resonance_loop_gain=data.get("resonance_loop_gain", 0.99),
            key_off_noise_ms=data.get("key_off_noise_ms", 18.0),
            performance_noise_cc=data.get("performance_noise_cc"),
            variant=data.get("variant", "default"),
            decay_velocity_sensitivity=data.get("decay_velocity_sensitivity", 0.0),
        )

    @classmethod
    def for_group(cls, group: InstrumentGroup, **overrides: Any) -> BehaviorConfig:
        """Factory with sensible per-group defaults."""
        defaults: dict[InstrumentGroup, dict[str, Any]] = {
            InstrumentGroup.ACOUSTIC_PIANO: {"velocity_to_decay": False, "key_off_noise": True},
            InstrumentGroup.MALLETS: {
                "velocity_to_decay": True,
                "sympathetic_resonance": True,
                "decay_velocity_sensitivity": 0.3,
            },
            InstrumentGroup.BOWED_STRINGS: {
                "ensemble_detune": True,
                "performance_noise_cc": 2,
                "legato_enabled": True,
            },
            InstrumentGroup.BRASS: {"performance_noise_cc": 2, "ensemble_detune": True},
            InstrumentGroup.REEDS_WOODWINDS: {"performance_noise_cc": 2},
            InstrumentGroup.ACOUSTIC_GUITAR: {"performance_noise_cc": 16},
            InstrumentGroup.ELECTRIC_GUITAR: {"performance_noise_cc": 16},
            InstrumentGroup.CHOIR: {"performance_noise_cc": 11},
            InstrumentGroup.ACCORDION: {"performance_noise_cc": 11},
        }
        cfg = cls(group=group)
        cfg.ensemble = EnsembleConfig(
            voicing_mode=(
                "section"
                if group in (InstrumentGroup.BOWED_STRINGS, InstrumentGroup.BRASS)
                else "solo"
            ),
            shared_vibrato=group in (InstrumentGroup.BOWED_STRINGS, InstrumentGroup.BRASS),
        )
        cfg.ensemble_detune = cfg.ensemble.voicing_mode == "section"
        for k, v in defaults.get(group, {}).items():
            setattr(cfg, k, v)
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg


# ---------------------------------------------------------------------------
# GM/XG program number -> InstrumentGroup mapping
# ---------------------------------------------------------------------------
# GM instrument families (program 0-127) grouped into the 18 acoustic groups.
# Used to auto-select the behavior recipe when a preset is loaded.
_GM_FAMILY_MAP: dict[int, InstrumentGroup] = {
    # 0-7 Pianos
    0: InstrumentGroup.ACOUSTIC_PIANO,
    1: InstrumentGroup.ACOUSTIC_PIANO,
    2: InstrumentGroup.ACOUSTIC_PIANO,
    3: InstrumentGroup.ACOUSTIC_PIANO,
    4: InstrumentGroup.ELECTRIC_PIANO,
    5: InstrumentGroup.ELECTRIC_PIANO,
    6: InstrumentGroup.ELECTRIC_PIANO,
    7: InstrumentGroup.ELECTRIC_PIANO,
    # 8-15 Chromatic percussion / organs
    8: InstrumentGroup.MALLETS,
    9: InstrumentGroup.MALLETS,
    10: InstrumentGroup.MALLETS,
    11: InstrumentGroup.MALLETS,
    12: InstrumentGroup.ORGAN,
    13: InstrumentGroup.ORGAN,
    14: InstrumentGroup.ORGAN,
    15: InstrumentGroup.ORGAN,
    # 16-23 Guitars
    16: InstrumentGroup.ACOUSTIC_GUITAR,
    17: InstrumentGroup.ACOUSTIC_GUITAR,
    18: InstrumentGroup.ACOUSTIC_GUITAR,
    19: InstrumentGroup.ELECTRIC_GUITAR,
    20: InstrumentGroup.ELECTRIC_GUITAR,
    21: InstrumentGroup.ELECTRIC_GUITAR,
    22: InstrumentGroup.ELECTRIC_GUITAR,
    23: InstrumentGroup.ELECTRIC_GUITAR,
    # 24-31 Basses
    24: InstrumentGroup.ACOUSTIC_BASS,
    25: InstrumentGroup.ACOUSTIC_BASS,
    26: InstrumentGroup.ACOUSTIC_BASS,
    27: InstrumentGroup.ELECTRIC_BASS,
    28: InstrumentGroup.ELECTRIC_BASS,
    29: InstrumentGroup.ELECTRIC_BASS,
    30: InstrumentGroup.ELECTRIC_BASS,
    31: InstrumentGroup.ELECTRIC_BASS,
    # 32-39 Strings
    32: InstrumentGroup.BOWED_STRINGS,
    33: InstrumentGroup.BOWED_STRINGS,
    34: InstrumentGroup.BOWED_STRINGS,
    35: InstrumentGroup.BOWED_STRINGS,
    36: InstrumentGroup.BOWED_STRINGS,
    37: InstrumentGroup.BOWED_STRINGS,
    38: InstrumentGroup.BOWED_STRINGS,
    39: InstrumentGroup.BOWED_STRINGS,
    # 40-47 Ensembles / choirs
    40: InstrumentGroup.BOWED_STRINGS,
    41: InstrumentGroup.BOWED_STRINGS,
    42: InstrumentGroup.CHOIR,
    43: InstrumentGroup.CHOIR,
    44: InstrumentGroup.CHOIR,
    45: InstrumentGroup.CHOIR,
    46: InstrumentGroup.CHOIR,
    47: InstrumentGroup.CHOIR,
    # 48-55 Brass
    48: InstrumentGroup.BRASS,
    49: InstrumentGroup.BRASS,
    50: InstrumentGroup.BRASS,
    51: InstrumentGroup.BRASS,
    52: InstrumentGroup.BRASS,
    53: InstrumentGroup.BRASS,
    54: InstrumentGroup.BRASS,
    55: InstrumentGroup.BRASS,
    # 56-63 Reeds / woodwinds
    56: InstrumentGroup.REEDS_WOODWINDS,
    57: InstrumentGroup.REEDS_WOODWINDS,
    58: InstrumentGroup.REEDS_WOODWINDS,
    59: InstrumentGroup.REEDS_WOODWINDS,
    60: InstrumentGroup.REEDS_WOODWINDS,
    61: InstrumentGroup.REEDS_WOODWINDS,
    62: InstrumentGroup.REEDS_WOODWINDS,
    63: InstrumentGroup.REEDS_WOODWINDS,
    # 64-71 Pipes / ethnic
    64: InstrumentGroup.REEDS_WOODWINDS,
    65: InstrumentGroup.REEDS_WOODWINDS,
    66: InstrumentGroup.REEDS_WOODWINDS,
    67: InstrumentGroup.ETHNIC,
    68: InstrumentGroup.ETHNIC,
    69: InstrumentGroup.ETHNIC,
    70: InstrumentGroup.ETHNIC,
    71: InstrumentGroup.ETHNIC,
    # 72-79 Ethnic / plucked world
    72: InstrumentGroup.PLUCKED_WORLD,
    73: InstrumentGroup.PLUCKED_WORLD,
    74: InstrumentGroup.PLUCKED_WORLD,
    75: InstrumentGroup.PLUCKED_WORLD,
    76: InstrumentGroup.PLUCKED_WORLD,
    77: InstrumentGroup.PLUCKED_WORLD,
    78: InstrumentGroup.PLUCKED_WORLD,
    79: InstrumentGroup.PLUCKED_WORLD,
    # 80-87 Synth / misc (treat as acoustic-ish where possible)
    80: InstrumentGroup.MALLETS,
    81: InstrumentGroup.MALLETS,
    82: InstrumentGroup.MALLETS,
    83: InstrumentGroup.MALLETS,
    84: InstrumentGroup.ACCORDION,
    85: InstrumentGroup.ACCORDION,
    86: InstrumentGroup.ACCORDION,
    87: InstrumentGroup.ACCORDION,
    # 88-95 Ethnic / percussion
    88: InstrumentGroup.ETHNIC,
    89: InstrumentGroup.ETHNIC,
    90: InstrumentGroup.ETHNIC,
    91: InstrumentGroup.ETHNIC,
    92: InstrumentGroup.TIMPANI,
    93: InstrumentGroup.TIMPANI,
    94: InstrumentGroup.MALLETS,
    95: InstrumentGroup.MALLETS,
    # 96-103 Sound effects / misc
    96: InstrumentGroup.ETHNIC,
    97: InstrumentGroup.ETHNIC,
    98: InstrumentGroup.ETHNIC,
    99: InstrumentGroup.ETHNIC,
    100: InstrumentGroup.ETHNIC,
    101: InstrumentGroup.ETHNIC,
    102: InstrumentGroup.ETHNIC,
    103: InstrumentGroup.ETHNIC,
    # 104-111 Ethnic / world
    104: InstrumentGroup.PLUCKED_WORLD,
    105: InstrumentGroup.PLUCKED_WORLD,
    106: InstrumentGroup.PLUCKED_WORLD,
    107: InstrumentGroup.PLUCKED_WORLD,
    108: InstrumentGroup.PLUCKED_WORLD,
    109: InstrumentGroup.PLUCKED_WORLD,
    110: InstrumentGroup.PLUCKED_WORLD,
    111: InstrumentGroup.PLUCKED_WORLD,
    # 112-119 Ethnic / plucked
    112: InstrumentGroup.PLUCKED_WORLD,
    113: InstrumentGroup.PLUCKED_WORLD,
    114: InstrumentGroup.PLUCKED_WORLD,
    115: InstrumentGroup.PLUCKED_WORLD,
    116: InstrumentGroup.PLUCKED_WORLD,
    117: InstrumentGroup.PLUCKED_WORLD,
    118: InstrumentGroup.PLUCKED_WORLD,
    119: InstrumentGroup.PLUCKED_WORLD,
    # 120-127 Percussion / misc
    120: InstrumentGroup.TIMPANI,
    121: InstrumentGroup.TIMPANI,
    122: InstrumentGroup.MALLETS,
    123: InstrumentGroup.MALLETS,
    124: InstrumentGroup.ETHNIC,
    125: InstrumentGroup.ETHNIC,
    126: InstrumentGroup.ETHNIC,
    127: InstrumentGroup.ETHNIC,
}


def program_to_group(program: int) -> InstrumentGroup:
    """Map a GM/XG program number (0-127) to an acoustic InstrumentGroup."""
    return _GM_FAMILY_MAP.get(int(program) % 128, InstrumentGroup.ACOUSTIC_PIANO)
