"""XG Insertion Effect Type Definitions and Parameter Mappings.

Defines the 18 XG insertion effect types (0-17), their human-readable names,
and default parameter sets. Matches the effect types in
insertion/processor.py (ProductionXGInsertionEffectsProcessor).
"""

from __future__ import annotations

from typing import Any

# XG Insertion Effect Type Constants (0-17)
# These match the XG_INSERTION_PARAMS keys in insertion/processor.py
XG_INSERTION_DISTORTION = 0
XG_INSERTION_OVERDRIVE = 1
XG_INSERTION_COMPRESSOR = 2
XG_INSERTION_NOISE_GATE = 3
XG_INSERTION_ENVELOPE_FILTER = 4
XG_INSERTION_VOCODER = 5
XG_INSERTION_AMP_SIMULATOR = 6
XG_INSERTION_ROTARY_SPEAKER = 7
XG_INSERTION_LESLIE = 8
XG_INSERTION_ENHANCER = 9
XG_INSERTION_AUTO_WAH = 10
XG_INSERTION_TALK_WAH = 11
XG_INSERTION_HARMONIZER = 12
XG_INSERTION_OCTAVE = 13
XG_INSERTION_DETUNE = 14
XG_INSERTION_PHASER = 15
XG_INSERTION_FLANGER = 16
XG_INSERTION_WAH_WAH = 17

# Human-readable names for each XG insertion effect type
XG_INSERTION_NAMES: dict[int, str] = {
    0: "Distortion",
    1: "Overdrive",
    2: "Compressor",
    3: "Noise Gate",
    4: "Envelope Filter",
    5: "Vocoder",
    6: "Amp Simulator",
    7: "Rotary Speaker",
    8: "Leslie",
    9: "Enhancer",
    10: "Auto Wah",
    11: "Talk Wah",
    12: "Harmonizer",
    13: "Octave",
    14: "Detune",
    15: "Phaser",
    16: "Flanger",
    17: "Wah Wah",
}

# Default parameters for each XG insertion effect type.
# Structure matches ProductionXGInsertionEffectsProcessor.XG_INSERTION_PARAMS.
XG_INSERTION_PARAMETERS: dict[int, dict[str, dict[str, Any]]] = {
    0: {  # Distortion
        "drive": {"range": (0, 127), "default": 64, "name": "Drive"},
        "tone": {"range": (0, 127), "default": 64, "name": "Tone"},
        "level": {"range": (0, 127), "default": 100, "name": "Level"},
    },
    1: {  # Overdrive
        "drive": {"range": (0, 127), "default": 80, "name": "Drive"},
        "tone": {"range": (0, 127), "default": 50, "name": "Tone"},
        "level": {"range": (0, 127), "default": 90, "name": "Level"},
    },
    2: {  # Compressor
        "threshold": {"range": (-60, 0), "default": -20, "name": "Threshold"},
        "ratio": {"range": (1, 20), "default": 4, "name": "Ratio"},
        "attack": {"range": (0, 100), "default": 5, "name": "Attack"},
        "release": {"range": (10, 500), "default": 100, "name": "Release"},
    },
    3: {  # Noise Gate
        "threshold": {"range": (-80, 0), "default": -40, "name": "Threshold"},
        "ratio": {"range": (0.1, 1), "default": 0.3, "name": "Ratio"},
        "attack": {"range": (0, 50), "default": 1, "name": "Attack"},
        "release": {"range": (10, 200), "default": 50, "name": "Release"},
    },
    4: {  # Envelope Filter
        "sensitivity": {"range": (0, 127), "default": 64, "name": "Sensitivity"},
        "resonance": {"range": (0.1, 10), "default": 2.0, "name": "Resonance"},
        "frequency": {"range": (200, 5000), "default": 1000, "name": "Frequency"},
    },
    5: {  # Vocoder
        "bandwidth": {"range": (0.1, 2.0), "default": 0.5, "name": "Bandwidth"},
        "sensitivity": {"range": (0, 127), "default": 80, "name": "Sensitivity"},
        "dry_wet": {"range": (0, 127), "default": 64, "name": "Dry/Wet"},
    },
    6: {  # Amp Simulator
        "drive": {"range": (0, 127), "default": 100, "name": "Drive"},
        "tone": {"range": (0, 127), "default": 30, "name": "Tone"},
        "level": {"range": (0, 127), "default": 85, "name": "Level"},
    },
    7: {  # Rotary Speaker
        "speed": {"range": (0, 127), "default": 64, "name": "Speed"},
        "depth": {"range": (0, 127), "default": 100, "name": "Depth"},
        "crossover": {"range": (200, 2000), "default": 800, "name": "Crossover"},
    },
    8: {  # Leslie
        "speed": {"range": (0, 127), "default": 50, "name": "Speed"},
        "depth": {"range": (0, 127), "default": 90, "name": "Depth"},
        "reverb": {"range": (0, 127), "default": 30, "name": "Reverb"},
    },
    9: {  # Enhancer
        "enhance": {"range": (0, 127), "default": 64, "name": "Enhance"},
        "frequency": {"range": (1000, 10000), "default": 5000, "name": "Frequency"},
        "width": {"range": (0.1, 2.0), "default": 1.0, "name": "Width"},
    },
    10: {  # Auto Wah
        "rate": {"range": (0.1, 10), "default": 2.0, "name": "Rate"},
        "depth": {"range": (0, 127), "default": 80, "name": "Depth"},
        "resonance": {"range": (0.5, 10), "default": 3.0, "name": "Resonance"},
    },
    11: {  # Talk Wah
        "sensitivity": {"range": (0, 127), "default": 90, "name": "Sensitivity"},
        "resonance": {"range": (0.5, 10), "default": 4.0, "name": "Resonance"},
        "decay": {"range": (0.01, 1.0), "default": 0.1, "name": "Decay"},
    },
    12: {  # Harmonizer
        "interval": {"range": (-24, 24), "default": 7, "name": "Interval"},
        "mix": {"range": (0, 127), "default": 60, "name": "Mix"},
        "detune": {"range": (-50, 50), "default": 0, "name": "Detune"},
    },
    13: {  # Octave
        "octave": {"range": (-3, 3), "default": -1, "name": "Octave"},
        "mix": {"range": (0, 127), "default": 60, "name": "Mix"},
        "dry_wet": {"range": (0, 127), "default": 80, "name": "Dry/Wet"},
    },
    14: {  # Detune
        "detune": {"range": (-100, 100), "default": 10, "name": "Detune"},
        "mix": {"range": (0, 127), "default": 50, "name": "Mix"},
        "delay": {"range": (0, 50), "default": 5, "name": "Delay"},
    },
    15: {  # Phaser
        "rate": {"range": (0.1, 10), "default": 1.0, "name": "Rate"},
        "depth": {"range": (0, 127), "default": 64, "name": "Depth"},
        "feedback": {"range": (-0.9, 0.9), "default": 0.3, "name": "Feedback"},
        "stages": {"range": (2, 12), "default": 6, "name": "Stages"},
    },
    16: {  # Flanger
        "rate": {"range": (0.05, 5.0), "default": 0.5, "name": "Rate"},
        "depth": {"range": (0, 127), "default": 90, "name": "Depth"},
        "feedback": {"range": (-0.9, 0.9), "default": 0.5, "name": "Feedback"},
        "delay": {"range": (0.1, 10), "default": 2.0, "name": "Delay"},
    },
    17: {  # Wah Wah
        "sensitivity": {"range": (0, 127), "default": 115, "name": "Sensitivity"},
        "resonance": {"range": (0.5, 10), "default": 5.0, "name": "Resonance"},
        "frequency": {"range": (200, 2000), "default": 500, "name": "Frequency"},
    },
}


def get_effect_name(effect_type: int) -> str:
    """Get the human-readable name for an XG insertion effect type.

    Args:
        effect_type: XG insertion effect type number (0-17)

    Returns:
        Effect name string, or "Unknown" if the type is not recognised.
    """
    return XG_INSERTION_NAMES.get(effect_type, "Unknown")


def get_effect_parameters(effect_type: int) -> dict[str, dict[str, Any]]:
    """Get the default parameter definitions for an XG insertion effect type.

    Args:
        effect_type: XG insertion effect type number (0-17)

    Returns:
        Dictionary mapping parameter names to their definitions
        (range, default, name), or an empty dict if the type is unknown.
    """
    return XG_INSERTION_PARAMETERS.get(effect_type, {}).copy()


def get_default_parameter_values(effect_type: int) -> dict[str, Any]:
    """Get default parameter *values* for an XG insertion effect type.

    This is a convenience wrapper around ``get_effect_parameters`` that
    extracts only the default value for each parameter.

    Args:
        effect_type: XG insertion effect type number (0-17)

    Returns:
        Dictionary mapping parameter name to its default value.
    """
    params = get_effect_parameters(effect_type)
    return {name: pdef["default"] for name, pdef in params.items()}


__all__ = [
    "XG_INSERTION_DISTORTION",
    "XG_INSERTION_OVERDRIVE",
    "XG_INSERTION_COMPRESSOR",
    "XG_INSERTION_NOISE_GATE",
    "XG_INSERTION_ENVELOPE_FILTER",
    "XG_INSERTION_VOCODER",
    "XG_INSERTION_AMP_SIMULATOR",
    "XG_INSERTION_ROTARY_SPEAKER",
    "XG_INSERTION_LESLIE",
    "XG_INSERTION_ENHANCER",
    "XG_INSERTION_AUTO_WAH",
    "XG_INSERTION_TALK_WAH",
    "XG_INSERTION_HARMONIZER",
    "XG_INSERTION_OCTAVE",
    "XG_INSERTION_DETUNE",
    "XG_INSERTION_PHASER",
    "XG_INSERTION_FLANGER",
    "XG_INSERTION_WAH_WAH",
    "XG_INSERTION_NAMES",
    "XG_INSERTION_PARAMETERS",
    "get_effect_name",
    "get_effect_parameters",
    "get_default_parameter_values",
]
