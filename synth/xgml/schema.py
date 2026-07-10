"""JSON Schema definitions for XGML document validation."""

from __future__ import annotations

from typing import Any

# =============================================================================
# Section Schemas
# =============================================================================

BASIC_MESSAGES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "channels": {
            "type": "object",
            "patternProperties": {
                "^(1[0-5]|[0-9])$": {  # 0-15
                    "type": "object",
                    "properties": {
                        "program": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                        "volume": {"type": "integer", "minimum": 0, "maximum": 127},
                        "pan": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                        "expression": {"type": "integer", "minimum": 0, "maximum": 127},
                        "reverb_send": {"type": "integer", "minimum": 0, "maximum": 127},
                        "chorus_send": {"type": "integer", "minimum": 0, "maximum": 127},
                        "variation_send": {"type": "integer", "minimum": 0, "maximum": 127},
                        "pitch_bend_range": {"type": "integer", "minimum": 0, "maximum": 24},
                        "bank_msb": {"type": "integer", "minimum": 0, "maximum": 127},
                        "bank_lsb": {"type": "integer", "minimum": 0, "maximum": 127},
                        "portamento": {"type": "boolean"},
                        "sostenuto": {"type": "boolean"},
                        "soft_pedal": {"type": "boolean"},
                        "hold": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                },
            },
        },
    },
}

FILTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cutoff": {"type": "integer", "minimum": 0, "maximum": 127},
        "resonance": {"type": "integer", "minimum": 0, "maximum": 127},
        "type": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 3}]},
        "envelope_attack": {"type": "integer", "minimum": 0, "maximum": 127},
        "envelope_decay": {"type": "integer", "minimum": 0, "maximum": 127},
        "envelope_sustain": {"type": "integer", "minimum": 0, "maximum": 127},
        "envelope_release": {"type": "integer", "minimum": 0, "maximum": 127},
        "envelope_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "velocity_sensitivity": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

LFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "waveform": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 3}]},
        "speed": {"type": "integer", "minimum": 0, "maximum": 127},
        "delay": {"type": "integer", "minimum": 0, "maximum": 127},
        "fade": {"type": "integer", "minimum": 0, "maximum": 127},
        "pitch_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "filter_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "amp_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "key_sync": {"type": "boolean"},
    },
}

CHANNEL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "patternProperties": {
        "^(1[0-5]|[0-9])$": {
            "type": "object",
            "properties": {
                "filter": FILTER_SCHEMA,
                "lfo": {
                    "type": "object",
                    "patternProperties": {
                        "^lfo[12]$": LFO_SCHEMA,
                    },
                },
                "amp_envelope": {
                    "type": "object",
                    "properties": {
                        "attack": {"type": "integer", "minimum": 0, "maximum": 127},
                        "decay": {"type": "integer", "minimum": 0, "maximum": 127},
                        "sustain": {"type": "integer", "minimum": 0, "maximum": 127},
                        "release": {"type": "integer", "minimum": 0, "maximum": 127},
                        "velocity_sensitivity": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                },
                "pitch": {
                    "type": "object",
                    "properties": {
                        "coarse": {"type": "integer", "minimum": -24, "maximum": 24},
                        "fine": {"type": "integer", "minimum": -64, "maximum": 63},
                        "random": {"type": "integer", "minimum": 0, "maximum": 127},
                        "envelope_depth": {"type": "integer", "minimum": -64, "maximum": 63},
                    },
                },
                "effects_sends": {
                    "type": "object",
                    "properties": {
                        "reverb": {"type": "integer", "minimum": 0, "maximum": 127},
                        "chorus": {"type": "integer", "minimum": 0, "maximum": 127},
                        "variation": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                },
                "mono_poly": {"type": "string", "enum": ["mono", "poly"]},
                "note_shift": {"type": "integer", "minimum": -24, "maximum": 24},
            },
        },
    },
}

EFFECTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reverb": {
            "type": "object",
            "properties": {
                "type": {"oneOf": [{"type": "integer", "minimum": 1, "maximum": 26}, {"type": "string"}]},
                "time": {"type": "number", "minimum": 0.1, "maximum": 30.0},
                "level": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "hf_damping": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "pre_delay": {"type": "number", "minimum": 0.0, "maximum": 50.0},
            },
        },
        "chorus": {
            "type": "object",
            "properties": {
                "type": {"oneOf": [{"type": "integer", "minimum": 0, "maximum": 17}, {"type": "string"}]},
                "rate": {"type": "number", "minimum": 0.0},
                "depth": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "feedback": {"type": "number", "minimum": -1.0, "maximum": 1.0},
                "level": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
        },
        "variation": {
            "type": "object",
            "properties": {
                "type": {"type": "integer", "minimum": 0, "maximum": 83},
                "level": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "params": {"type": "object"},
            },
        },
    },
}

SEQUENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tempo": {"type": "number", "minimum": 1.0},
        "time_signature": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1},
            "minItems": 2,
            "maxItems": 2,
        },
        "tracks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "channel": {"type": "integer", "minimum": 0, "maximum": 15},
                    "program": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                    "volume": {"type": "integer", "minimum": 0, "maximum": 127},
                    "pan": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "at": {"type": "number", "minimum": 0.0},
                                "note_on": {
                                    "type": "object",
                                    "properties": {
                                        "note": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                                        "velocity": {"type": "integer", "minimum": 0, "maximum": 127},
                                        "duration": {"type": "number", "minimum": 0.0},
                                    },
                                    "required": ["note"],
                                },
                                "control": {
                                    "type": "object",
                                    "properties": {
                                        "controller": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                                        "value": {"type": "number"},
                                    },
                                    "required": ["controller", "value"],
                                },
                                "program": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                                "tempo": {"type": "number", "minimum": 1.0},
                                "text": {"type": "string"},
                                "note_off": {
                                    "type": "object",
                                    "properties": {
                                        "note": {"oneOf": [{"type": "string"}, {"type": "integer", "minimum": 0, "maximum": 127}]},
                                        "velocity": {"type": "integer", "minimum": 0, "maximum": 127},
                                        "duration": {"type": "number", "minimum": 0.0},
                                    },
                                    "required": ["note"],
                                },
                                "nrpn": {
                                    "type": "object",
                                    "properties": {
                                        "msb": {"type": "integer", "minimum": 0, "maximum": 127},
                                        "lsb": {"type": "integer", "minimum": 0, "maximum": 127},
                                        "value": {"type": "integer", "minimum": 0, "maximum": 127},
                                    },
                                    "required": ["msb", "lsb", "value"],
                                },
                                "channel_pressure": {"type": "integer", "minimum": 0, "maximum": 127},
                                "poly_pressure": {
                                    "oneOf": [
                                        {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "note": {"type": "integer", "minimum": 0, "maximum": 127},
                                                    "pressure": {"type": "integer", "minimum": 0, "maximum": 127},
                                                },
                                                "required": ["note", "pressure"],
                                            },
                                        },
                                        {
                                            "type": "object",
                                            "additionalProperties": {"type": "integer", "minimum": 0, "maximum": 127},
                                        },
                                    ],
                                },
                                "sysex": {
                                    "type": "array",
                                    "items": {"type": "integer", "minimum": 0, "maximum": 127},
                                },
                                "pitch_bend": {"type": "integer", "minimum": -8192, "maximum": 8191},
                            },
                            "required": ["at"],
                        },
                    },
                },
            },
        },
    },
}

# =============================================================================
# GS Schema
# =============================================================================

GS_PART_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "program": {"type": "integer", "minimum": 0, "maximum": 127},
        "bank_msb": {"type": "integer", "minimum": 0, "maximum": 127},
        "bank_lsb": {"type": "integer", "minimum": 0, "maximum": 127},
        "volume": {"type": "integer", "minimum": 0, "maximum": 127},
        "pan": {"type": "integer", "minimum": 0, "maximum": 127},
        "coarse_tune": {"type": "integer", "minimum": -24, "maximum": 24},
        "fine_tune": {"type": "integer", "minimum": -64, "maximum": 63},
        "reverb_send": {"type": "integer", "minimum": 0, "maximum": 127},
        "chorus_send": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

GS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "system": {
            "type": "object",
            "properties": {
                "master_tune": {"type": "integer", "minimum": -64, "maximum": 63},
                "master_volume": {"type": "integer", "minimum": 0, "maximum": 127},
                "master_transpose": {"type": "integer", "minimum": -24, "maximum": 24},
            },
        },
        "parts": {
            "type": "object",
            "additionalProperties": GS_PART_SCHEMA,
        },
        "effects": {
            "type": "object",
            "properties": {
                "reverb": {
                    "type": "object",
                    "properties": {
                        "type": {"type": ["string", "integer"]},
                        "level": {"type": "integer", "minimum": 0, "maximum": 127},
                        "time": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                },
                "chorus": {
                    "type": "object",
                    "properties": {
                        "type": {"type": ["string", "integer"]},
                        "level": {"type": "integer", "minimum": 0, "maximum": 127},
                    },
                },
            },
        },
    },
}

# =============================================================================
# Jupiter-X Schema
# =============================================================================

JX_SYSTEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "master_volume": {"type": "integer", "minimum": 0, "maximum": 127},
        "master_tune": {"type": "integer", "minimum": -64, "maximum": 63},
        "master_transpose": {"type": "integer", "minimum": -12, "maximum": 12},
        "master_pan": {"type": "integer", "minimum": -64, "maximum": 63},
    },
}

JX_ENGINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enable": {"type": "boolean"},
        "level": {"type": "integer", "minimum": 0, "maximum": 127},
        "pan": {"type": "integer", "minimum": -64, "maximum": 63},
        "coarse_tune": {"type": "integer", "minimum": -24, "maximum": 24},
        "fine_tune": {"type": "integer", "minimum": -50, "maximum": 50},
        "parameters": {"type": "object"},
    },
}

JX_LFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "waveform": {"type": "integer", "minimum": 0, "maximum": 7},
        "rate": {"type": "integer", "minimum": 0, "maximum": 127},
        "depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "fade": {"type": "integer", "minimum": 0, "maximum": 127},
        "key_trigger": {"type": "boolean"},
        "delay": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

JX_ENV_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "attack": {"type": "integer", "minimum": 0, "maximum": 127},
        "decay": {"type": "integer", "minimum": 0, "maximum": 127},
        "sustain": {"type": "integer", "minimum": 0, "maximum": 127},
        "release": {"type": "integer", "minimum": 0, "maximum": 127},
        "attack_curve": {"type": "integer", "minimum": 0, "maximum": 2},
        "decay_curve": {"type": "integer", "minimum": 0, "maximum": 2},
        "release_curve": {"type": "integer", "minimum": 0, "maximum": 2},
        "velocity_sensitivity": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

JX_MOD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mod_wheel_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "aftertouch_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "velocity_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "key_tracking_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "super_knob_depth": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

JX_PART_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "level": {"type": "integer", "minimum": 0, "maximum": 127},
        "pan": {"type": "integer", "minimum": -64, "maximum": 63},
        "volume": {"type": "integer", "minimum": 0, "maximum": 127},
        "coarse_tune": {"type": "integer", "minimum": -24, "maximum": 24},
        "fine_tune": {"type": "integer", "minimum": -50, "maximum": 50},
        "key_range_low": {"type": "integer", "minimum": 0, "maximum": 127},
        "key_range_high": {"type": "integer", "minimum": 0, "maximum": 127},
        "reverb_send": {"type": "integer", "minimum": 0, "maximum": 127},
        "chorus_send": {"type": "integer", "minimum": 0, "maximum": 127},
        "delay_send": {"type": "integer", "minimum": 0, "maximum": 127},
        "engine_mode": {"type": "integer", "minimum": 0, "maximum": 1},
        "active_engine": {"type": "integer", "minimum": 0, "maximum": 3},
        "engines": {
            "type": "object",
            "properties": {
                "analog": JX_ENGINE_SCHEMA,
                "digital": JX_ENGINE_SCHEMA,
                "fm": JX_ENGINE_SCHEMA,
                "external": JX_ENGINE_SCHEMA,
            },
        },
        "lfo": JX_LFO_SCHEMA,
        "envelope": JX_ENV_SCHEMA,
        "modulation": JX_MOD_SCHEMA,
    },
}

JX_VCM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "distortion_type": {"type": ["integer", "string"]},
        "distortion_drive": {"type": "integer", "minimum": 0, "maximum": 127},
        "distortion_level": {"type": "integer", "minimum": 0, "maximum": 127},
        "phaser_polarity": {"type": "integer"},
        "phaser_rate": {"type": "integer", "minimum": 0, "maximum": 127},
        "phaser_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "phaser_level": {"type": "integer", "minimum": 0, "maximum": 127},
        "chorus_type": {"type": ["integer", "string"]},
        "chorus_rate": {"type": "integer", "minimum": 0, "maximum": 127},
        "chorus_depth": {"type": "integer", "minimum": 0, "maximum": 127},
        "chorus_level": {"type": "integer", "minimum": 0, "maximum": 127},
        "delay_type": {"type": ["integer", "string"]},
        "delay_time": {"type": "integer", "minimum": 0, "maximum": 127},
        "delay_feedback": {"type": "integer", "minimum": 0, "maximum": 127},
        "delay_level": {"type": "integer", "minimum": 0, "maximum": 127},
        "reverb_type": {"type": ["integer", "string"]},
        "reverb_time": {"type": "integer", "minimum": 0, "maximum": 127},
        "reverb_level": {"type": "integer", "minimum": 0, "maximum": 127},
        "reverb_density": {"type": "integer", "minimum": 0, "maximum": 127},
    },
}

JX_ARP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enable": {"type": "boolean"},
        "style": {"type": "integer", "minimum": 0, "maximum": 7},
        "type": {"type": "integer", "minimum": 0, "maximum": 7},
        "range": {"type": "integer", "minimum": 1, "maximum": 4},
        "rate": {"type": "integer", "minimum": 0, "maximum": 127},
        "swing": {"type": "integer", "minimum": -50, "maximum": 50},
        "latch": {"type": "boolean"},
        "target": {"type": "integer", "minimum": 0, "maximum": 2},
        "tempo": {"type": "integer", "minimum": 20, "maximum": 300},
        "gate_time": {"type": "integer", "minimum": 0, "maximum": 127},
        "pattern_length": {"type": "integer", "minimum": 1, "maximum": 64},
    },
}

JX_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "system": JX_SYSTEM_SCHEMA,
        "parts": {
            "type": "object",
            "additionalProperties": JX_PART_SCHEMA,
        },
        "effects": JX_VCM_SCHEMA,
        "arpeggiator": JX_ARP_SCHEMA,
    },
}

# =============================================================================
# Root Document Schema
# =============================================================================

XGML_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "XGML Document",
    "type": "object",
    "properties": {
        "xg_dsl_version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
        "description": {"type": "string"},
        "meta": {
            "type": "object",
            "properties": {
                "author": {"type": "string"},
                "created": {"type": "string"},
                "modified": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
        # Goal 1: Configuration
        "basic_messages": BASIC_MESSAGES_SCHEMA,
        "channel_parameters": CHANNEL_PARAMETERS_SCHEMA,
        "drum_parameters": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 0, "maximum": 15},
                "kit_number": {"type": "integer", "minimum": 0, "maximum": 127},
                "notes": {
                    "type": "object",
                    "patternProperties": {
                        "^([1][0-0][0-7]|[0-9][0-9]?)$": {  # 0-107
                            "type": "object",
                            "properties": {
                                "pitch_coarse": {"type": "integer", "minimum": -24, "maximum": 24},
                                "pitch_fine": {"type": "integer", "minimum": -64, "maximum": 63},
                                "level": {"type": "integer", "minimum": 0, "maximum": 127},
                                "pan": {"type": "integer", "minimum": 0, "maximum": 127},
                                "reverb_send": {"type": "integer", "minimum": 0, "maximum": 127},
                                "chorus_send": {"type": "integer", "minimum": 0, "maximum": 127},
                                "variation_send": {"type": "integer", "minimum": 0, "maximum": 127},
                                "filter_cutoff": {"type": "integer", "minimum": 0, "maximum": 127},
                                "filter_resonance": {"type": "integer", "minimum": 0, "maximum": 127},
                                "decay": {"type": "integer", "minimum": 0, "maximum": 127},
                                "attack": {"type": "integer", "minimum": 0, "maximum": 127},
                                "alternate_group": {"type": "integer", "minimum": 0, "maximum": 127},
                            },
                        },
                    },
                },
            },
        },
        "effects": EFFECTS_SCHEMA,
        "gs": GS_SCHEMA,
        "jupiter_x": JX_SCHEMA,
        # Goal 2: Composition
        "sequences": {
            "type": "object",
            "additionalProperties": SEQUENCE_SCHEMA,
        },
    },
    "required": [],
    "additionalProperties": False,
}
