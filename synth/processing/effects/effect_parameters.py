"""Effect parameter schema system — typed, validated, named parameters.

Replaces the ad-hoc "parameter1"-"parameter4" dict keys with named,
ranged parameters that can be validated at registration time.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EffectParameter:
    """A single typed effect parameter with range and default."""

    name: str
    display_name: str
    min_val: float
    max_val: float
    default: float
    description: str = ""


@dataclass(slots=True)
class EffectParameterSchema:
    """Schema for a set of effect parameters.

    Usage:
        schema = EffectParameterSchema([
            EffectParameter("drive", "Drive", 0.0, 1.0, 0.5, "Drive amount"),
            EffectParameter("tone", "Tone", 0.0, 1.0, 0.5, "Tone control"),
        ])

        errors = schema.validate({"drive": 0.8, "tone": 0.3})
        normalized = schema.normalize({"drive": 0.8})  # fills defaults
    """

    parameters: list[EffectParameter] = field(default_factory=list)

    def validate(self, params: dict[str, float]) -> list[str]:
        """Validate params against schema. Returns list of error strings."""
        errors = []
        for param in self.parameters:
            value = params.get(param.name)
            if value is not None:
                if not (param.min_val <= value <= param.max_val):
                    errors.append(
                        f"'{param.name}': {value} out of range "
                        f"[{param.min_val}, {param.max_val}]"
                    )
        return errors

    def normalize(self, params: dict[str, float]) -> dict[str, float]:
        """Clamp params to valid ranges. Fill defaults for missing keys."""
        result: dict[str, float] = {}
        for param in self.parameters:
            value = params.get(param.name, param.default)
            result[param.name] = max(param.min_val, min(param.max_val, value))
        return result


# — Predefined schemas for effect categories —


# Delay effects (types 0-9) — 4 named parameters
DELAY_PARAM_SCHEMA = EffectParameterSchema([
    EffectParameter("time", "Delay Time", 0.0, 1.0, 0.5, "Delay time (0-1 maps to ms range)"),
    EffectParameter("feedback", "Feedback", 0.0, 1.0, 0.3, "Feedback amount"),
    EffectParameter("level", "Output Level", 0.0, 1.0, 0.8, "Output level"),
    EffectParameter("stereo_width", "Stereo Width", 0.0, 1.0, 1.0, "Stereo spread"),
])

# Chorus/Modulation effects (types 10-31) — 4 named parameters
CHORUS_PARAM_SCHEMA = EffectParameterSchema([
    EffectParameter("rate", "Modulation Rate", 0.0, 1.0, 0.5, "LFO rate"),
    EffectParameter("depth", "Modulation Depth", 0.0, 1.0, 0.5, "LFO depth"),
    EffectParameter("feedback", "Feedback", 0.0, 1.0, 0.3, "Feedback (some types)"),
    EffectParameter("level", "Output Level", 0.0, 1.0, 0.8, "Output level"),
])

# Distortion effects (types 32-52) — 3 primary parameters
DISTORTION_PARAM_SCHEMA = EffectParameterSchema([
    EffectParameter("drive", "Drive", 0.0, 1.0, 0.5, "Distortion drive"),
    EffectParameter("tone", "Tone", 0.0, 1.0, 0.5, "Tone/filter control"),
    EffectParameter("level", "Output Level", 0.0, 1.0, 0.8, "Output level"),
])

# Dynamics effects (types 53-57) — 4 parameters
DYNAMICS_PARAM_SCHEMA = EffectParameterSchema([
    EffectParameter("threshold", "Threshold", 0.0, 1.0, 0.5, "Threshold level"),
    EffectParameter("ratio", "Ratio", 0.0, 1.0, 0.5, "Compression/expansion ratio"),
    EffectParameter("attack", "Attack", 0.0, 1.0, 0.3, "Attack time"),
    EffectParameter("level", "Output Level", 0.0, 1.0, 0.8, "Makeup gain"),
])

# Schema lookup by effect type range
_PARAM_SCHEMAS: dict[str, EffectParameterSchema] = {
    "delay": DELAY_PARAM_SCHEMA,
    "chorus": CHORUS_PARAM_SCHEMA,
    "distortion": DISTORTION_PARAM_SCHEMA,
    "dynamics": DYNAMICS_PARAM_SCHEMA,
}


def get_schema_for_type(effect_type: int) -> EffectParameterSchema | None:
    """Return the parameter schema for a given effect type ID."""
    if 0 <= effect_type <= 9:
        return DELAY_PARAM_SCHEMA
    elif 10 <= effect_type <= 31:
        return CHORUS_PARAM_SCHEMA
    elif 32 <= effect_type <= 52:
        return DISTORTION_PARAM_SCHEMA
    elif 53 <= effect_type <= 57:
        return DYNAMICS_PARAM_SCHEMA
    return None
