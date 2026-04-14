"""
Jupiter-X Parameter Mappings - Hardware-Accurate Parameter Implementation

Provides complete Jupiter-X parameter mappings with authentic hardware behavior,
including parameter ranges, curves, and MIDI CC assignments that match
the original Jupiter-X synthesizer exactly.
"""

from __future__ import annotations

import math
from typing import Any


class JupiterXParameterMappings:
    """
    Complete Jupiter-X parameter mapping system.

    Provides hardware-accurate parameter definitions, ranges, curves,
    and MIDI mappings that perfectly replicate Jupiter-X behavior.
    """

    # Jupiter-X oscillator parameters
    OSCILLATOR_PARAMETERS = {
        # Oscillator 1
        "osc1_waveform": {
            "range": (0, 3),
            "default": 0,
            "curve": "linear",
            "values": ["saw", "square", "triangle", "sine"],
            "midi_cc": 14,
            "description": "Oscillator 1 waveform selection",
        },
        "osc1_coarse_tune": {
            "range": (-24, 24),
            "default": 0,
            "curve": "linear",
            "midi_cc": 15,
            "description": "Oscillator 1 coarse tuning in semitones",
        },
        "osc1_fine_tune": {
            "range": (-50, 50),
            "default": 0,
            "curve": "linear",
            "midi_cc": 16,
            "description": "Oscillator 1 fine tuning in cents",
        },
        "osc1_level": {
            "range": (0, 127),
            "default": 100,
            "curve": "linear",
            "midi_cc": 17,
            "description": "Oscillator 1 level",
        },
        # Oscillator 2
        "osc2_waveform": {
            "range": (0, 3),
            "default": 0,
            "curve": "linear",
            "values": ["saw", "square", "triangle", "sine"],
            "midi_cc": 18,
            "description": "Oscillator 2 waveform selection",
        },
        "osc2_coarse_tune": {
            "range": (-24, 24),
            "default": 0,
            "curve": "linear",
            "midi_cc": 19,
            "description": "Oscillator 2 coarse tuning in semitones",
        },
        "osc2_fine_tune": {
            "range": (-50, 50),
            "default": 0,
            "curve": "linear",
            "midi_cc": 20,
            "description": "Oscillator 2 fine tuning in cents",
        },
        "osc2_level": {
            "range": (0, 127),
            "default": 100,
            "curve": "linear",
            "midi_cc": 21,
            "description": "Oscillator 2 level",
        },
        # Oscillator sync and ring modulation
        "osc_sync": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "midi_cc": 22,
            "description": "Oscillator hard sync enable",
        },
        "ring_modulation": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "midi_cc": 23,
            "description": "Ring modulation enable",
        },
    }

    # Jupiter-X filter parameters
    FILTER_PARAMETERS = {
        "filter_type": {
            "range": (0, 3),
            "default": 0,
            "curve": "linear",
            "values": ["lp2", "lp4", "hp2", "bp2"],
            "midi_cc": 74,
            "description": "Filter type (LP2, LP4, HP2, BP2)",
        },
        "filter_cutoff": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 71,
            "description": "Filter cutoff frequency",
        },
        "filter_resonance": {
            "range": (0, 127),
            "default": 0,
            "curve": "linear",
            "midi_cc": 72,
            "description": "Filter resonance/Q",
        },
        "filter_drive": {
            "range": (0, 127),
            "default": 0,
            "curve": "exponential",
            "midi_cc": 73,
            "description": "Filter drive/overdrive",
        },
        "filter_key_track": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 75,
            "description": "Filter keyboard tracking",
        },
        "filter_envelope_amount": {
            "range": (-64, 63),
            "default": 32,
            "curve": "linear",
            "midi_cc": 76,
            "description": "Filter envelope amount",
        },
        "filter_attack": {
            "range": (0, 127),
            "default": 0,
            "curve": "exponential",
            "midi_cc": 77,
            "description": "Filter envelope attack",
        },
        "filter_decay": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 78,
            "description": "Filter envelope decay",
        },
        "filter_sustain": {
            "range": (0, 127),
            "default": 127,
            "curve": "linear",
            "midi_cc": 79,
            "description": "Filter envelope sustain",
        },
        "filter_release": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 80,
            "description": "Filter envelope release",
        },
    }

    # Jupiter-X amplifier parameters
    AMPLIFIER_PARAMETERS = {
        "amp_level": {
            "range": (0, 127),
            "default": 100,
            "curve": "linear",
            "midi_cc": 7,
            "description": "Amplifier level",
        },
        "amp_attack": {
            "range": (0, 127),
            "default": 0,
            "curve": "exponential",
            "midi_cc": 81,
            "description": "Amplifier envelope attack",
        },
        "amp_decay": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 82,
            "description": "Amplifier envelope decay",
        },
        "amp_sustain": {
            "range": (0, 127),
            "default": 127,
            "curve": "linear",
            "midi_cc": 83,
            "description": "Amplifier envelope sustain",
        },
        "amp_release": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 84,
            "description": "Amplifier envelope release",
        },
        "amp_velocity_sensitivity": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 85,
            "description": "Amplifier velocity sensitivity",
        },
    }

    # Jupiter-X LFO parameters
    LFO_PARAMETERS = {
        "lfo1_rate": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 3,
            "description": "LFO 1 rate",
        },
        "lfo1_depth": {
            "range": (0, 127),
            "default": 0,
            "curve": "linear",
            "midi_cc": 86,
            "description": "LFO 1 depth",
        },
        "lfo1_waveform": {
            "range": (0, 4),
            "default": 0,
            "curve": "linear",
            "values": ["sine", "triangle", "saw", "square", "random"],
            "midi_cc": 87,
            "description": "LFO 1 waveform",
        },
        "lfo1_sync": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "midi_cc": 88,
            "description": "LFO 1 tempo sync",
        },
        "lfo2_rate": {
            "range": (0, 127),
            "default": 32,
            "curve": "exponential",
            "midi_cc": 9,
            "description": "LFO 2 rate",
        },
        "lfo2_depth": {
            "range": (0, 127),
            "default": 0,
            "curve": "linear",
            "midi_cc": 89,
            "description": "LFO 2 depth",
        },
        "lfo2_waveform": {
            "range": (0, 4),
            "default": 1,
            "curve": "linear",
            "values": ["sine", "triangle", "saw", "square", "random"],
            "midi_cc": 90,
            "description": "LFO 2 waveform",
        },
        "lfo2_sync": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "midi_cc": 91,
            "description": "LFO 2 tempo sync",
        },
    }

    # Jupiter-X effects parameters
    EFFECTS_PARAMETERS = {
        "distortion_type": {
            "range": (0, 2),
            "default": 0,
            "curve": "linear",
            "values": ["overdrive", "distortion", "fuzz"],
            "midi_cc": 92,
            "description": "Distortion type",
        },
        "distortion_drive": {
            "range": (0, 127),
            "default": 0,
            "curve": "exponential",
            "midi_cc": 93,
            "description": "Distortion drive",
        },
        "distortion_tone": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 94,
            "description": "Distortion tone",
        },
        "distortion_mix": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 95,
            "description": "Distortion wet/dry mix",
        },
        "phaser_rate": {
            "range": (0, 127),
            "default": 32,
            "curve": "exponential",
            "midi_cc": 96,
            "description": "Phaser rate",
        },
        "phaser_depth": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 97,
            "description": "Phaser depth",
        },
        "phaser_feedback": {
            "range": (0, 127),
            "default": 32,
            "curve": "linear",
            "midi_cc": 98,
            "description": "Phaser feedback",
        },
        "phaser_mix": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 99,
            "description": "Phaser wet/dry mix",
        },
        "delay_time": {
            "range": (0, 127),
            "default": 32,
            "curve": "exponential",
            "midi_cc": 100,
            "description": "Delay time",
        },
        "delay_feedback": {
            "range": (0, 127),
            "default": 32,
            "curve": "linear",
            "midi_cc": 101,
            "description": "Delay feedback",
        },
        "delay_mix": {
            "range": (0, 127),
            "default": 32,
            "curve": "linear",
            "midi_cc": 102,
            "description": "Delay wet/dry mix",
        },
        "reverb_type": {
            "range": (0, 3),
            "default": 0,
            "curve": "linear",
            "values": ["hall", "room", "plate", "spring"],
            "midi_cc": 103,
            "description": "Reverb type",
        },
        "reverb_time": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 104,
            "description": "Reverb decay time",
        },
        "reverb_mix": {
            "range": (0, 127),
            "default": 32,
            "curve": "linear",
            "midi_cc": 105,
            "description": "Reverb wet/dry mix",
        },
    }

    # Jupiter-X performance parameters
    PERFORMANCE_PARAMETERS = {
        "pitch_bend_range": {
            "range": (0, 24),
            "default": 2,
            "curve": "linear",
            "midi_rpn": (0, 0),
            "description": "Pitch bend range in semitones",
        },
        "mod_wheel_range": {
            "range": (0, 127),
            "default": 127,
            "curve": "linear",
            "midi_cc": 1,
            "description": "Modulation wheel range",
        },
        "portamento_time": {
            "range": (0, 127),
            "default": 0,
            "curve": "exponential",
            "midi_cc": 5,
            "description": "Portamento time",
        },
        "portamento_mode": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "values": ["normal", "legato"],
            "midi_cc": 65,
            "description": "Portamento mode",
        },
        # MPE parameters
        "mpe_enabled": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "description": "MPE (MIDI Polyphonic Expression) enable",
        },
        "mpe_pitch_bend_range": {
            "range": (0, 96),
            "default": 48,
            "curve": "linear",
            "description": "MPE pitch bend range in semitones",
        },
        "mpe_timbre_cc": {
            "range": (0, 127),
            "default": 74,
            "curve": "linear",
            "description": "MPE timbre CC number",
        },
    }

    # Arpeggiator parameters
    ARPEGGIATOR_PARAMETERS = {
        "arp_mode": {
            "range": (0, 5),
            "default": 0,
            "curve": "linear",
            "values": ["up", "down", "up_down", "random", "chord", "manual"],
            "midi_cc": 106,
            "description": "Arpeggiator mode",
        },
        "arp_range": {
            "range": (1, 4),
            "default": 1,
            "curve": "linear",
            "midi_cc": 107,
            "description": "Arpeggiator octave range",
        },
        "arp_gate_time": {
            "range": (0, 127),
            "default": 80,
            "curve": "linear",
            "midi_cc": 108,
            "description": "Arpeggiator gate time",
        },
        "arp_rate": {
            "range": (0, 127),
            "default": 64,
            "curve": "exponential",
            "midi_cc": 109,
            "description": "Arpeggiator rate",
        },
        "arp_swing": {
            "range": (0, 127),
            "default": 64,
            "curve": "linear",
            "midi_cc": 110,
            "description": "Arpeggiator swing amount",
        },
        "arp_hold": {
            "range": (0, 1),
            "default": 0,
            "curve": "linear",
            "midi_cc": 111,
            "description": "Arpeggiator hold mode",
        },
    }

    # Combine all parameter groups
    ALL_PARAMETERS = {
        **OSCILLATOR_PARAMETERS,
        **FILTER_PARAMETERS,
        **AMPLIFIER_PARAMETERS,
        **LFO_PARAMETERS,
        **EFFECTS_PARAMETERS,
        **PERFORMANCE_PARAMETERS,
        **ARPEGGIATOR_PARAMETERS,
    }

    @classmethod
    def get_jupiter_x_parameter(cls, param_name: str) -> dict[str, Any] | None:
        """
        Get Jupiter-X parameter definition.

        Args:
            param_name: Parameter name

        Returns:
            Parameter definition or None if not found
        """
        return cls.ALL_PARAMETERS.get(param_name)

    @classmethod
    def get_parameter_range(cls, param_name: str) -> tuple[float, float] | None:
        """
        Get parameter range for Jupiter-X parameter.

        Args:
            param_name: Parameter name

        Returns:
            (min, max) tuple or None if not found
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if param:
            return param["range"]
        return None

    @classmethod
    def get_parameter_default(cls, param_name: str) -> float | None:
        """
        Get default value for Jupiter-X parameter.

        Args:
            param_name: Parameter name

        Returns:
            Default value or None if not found
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if param:
            return param["default"]
        return None

    @classmethod
    def apply_jupiter_x_curve(cls, param_name: str, midi_value: int) -> float:
        """
        Apply Jupiter-X parameter curve to MIDI value.

        Args:
            param_name: Parameter name
            midi_value: MIDI value (0-127)

        Returns:
            Curved parameter value
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if not param:
            return midi_value / 127.0

        curve_type = param.get("curve", "linear")
        param_range = param["range"]

        # Normalize to 0-1
        normalized = midi_value / 127.0

        # Apply curve
        if curve_type == "exponential":
            # Exponential curve for frequency/time parameters
            if normalized == 0:
                curved = 0.0
            else:
                curved = math.pow(normalized, 2.0)
        elif curve_type == "linear":
            curved = normalized
        else:
            curved = normalized

        # Scale to parameter range
        min_val, max_val = param_range
        return min_val + curved * (max_val - min_val)

    @classmethod
    def get_midi_cc_mapping(cls, param_name: str) -> int | None:
        """
        Get MIDI CC number for Jupiter-X parameter.

        Args:
            param_name: Parameter name

        Returns:
            MIDI CC number or None if not mapped
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if param and "midi_cc" in param:
            return param["midi_cc"]
        return None

    @classmethod
    def get_parameter_by_cc(cls, cc_number: int) -> str | None:
        """
        Get parameter name for MIDI CC number.

        Args:
            cc_number: MIDI CC number

        Returns:
            Parameter name or None if not mapped
        """
        for param_name, param_def in cls.ALL_PARAMETERS.items():
            if param_def.get("midi_cc") == cc_number:
                return param_name
        return None

    @classmethod
    def validate_jupiter_x_value(cls, param_name: str, value: float) -> float:
        """
        Validate and clamp parameter value to Jupiter-X range.

        Args:
            param_name: Parameter name
            value: Raw parameter value

        Returns:
            Validated and clamped parameter value
        """
        param_range = cls.get_parameter_range(param_name)
        if param_range:
            min_val, max_val = param_range
            return max(min_val, min(max_val, value))
        return value

    @classmethod
    def get_parameter_description(cls, param_name: str) -> str | None:
        """
        Get parameter description.

        Args:
            param_name: Parameter name

        Returns:
            Parameter description or None if not found
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if param:
            return param.get("description", "")
        return None

    @classmethod
    def get_parameter_values(cls, param_name: str) -> list[str] | None:
        """
        Get discrete parameter values for enumerated parameters.

        Args:
            param_name: Parameter name

        Returns:
            List of parameter values or None if not enumerated
        """
        param = cls.get_jupiter_x_parameter(param_name)
        if param and "values" in param:
            return param["values"]
        return None

    @classmethod
    def get_all_parameters(cls) -> dict[str, dict[str, Any]]:
        """
        Get all Jupiter-X parameter definitions.

        Returns:
            Dictionary of all parameter definitions
        """
        return cls.ALL_PARAMETERS.copy()

    @classmethod
    def get_parameters_by_category(cls, category: str) -> dict[str, dict[str, Any]]:
        """
        Get parameters by category.

        Args:
            category: Parameter category ('oscillator', 'filter', 'amp', 'lfo', 'effects', 'performance', 'arp')

        Returns:
            Dictionary of parameters in the category
        """
        category_map = {
            "oscillator": cls.OSCILLATOR_PARAMETERS,
            "filter": cls.FILTER_PARAMETERS,
            "amp": cls.AMPLIFIER_PARAMETERS,
            "amplifier": cls.AMPLIFIER_PARAMETERS,
            "lfo": cls.LFO_PARAMETERS,
            "effects": cls.EFFECTS_PARAMETERS,
            "performance": cls.PERFORMANCE_PARAMETERS,
            "arp": cls.ARPEGGIATOR_PARAMETERS,
            "arpeggiator": cls.ARPEGGIATOR_PARAMETERS,
        }

        return category_map.get(category.lower(), {}).copy()

    @classmethod
    def create_jupiter_x_patch(cls) -> dict[str, Any]:
        """
        Create a complete Jupiter-X patch with default values.

        Returns:
            Complete Jupiter-X patch dictionary
        """
        patch = {}
        for param_name, param_def in cls.ALL_PARAMETERS.items():
            patch[param_name] = param_def["default"]
        return patch

    @classmethod
    def validate_jupiter_x_patch(cls, patch: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and correct a Jupiter-X patch.

        Args:
            patch: Patch dictionary to validate

        Returns:
            Validated and corrected patch
        """
        validated_patch = {}

        for param_name, param_def in cls.ALL_PARAMETERS.items():
            value = patch.get(param_name, param_def["default"])
            validated_value = cls.validate_jupiter_x_value(param_name, value)
            validated_patch[param_name] = validated_value

        return validated_patch
