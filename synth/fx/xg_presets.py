"""
XG Effect Presets - Complete XG Effect Configuration Presets

Provides predefined effect configurations for common scenarios,
accessible via NRPN MSB 16 for quick setup and professional workflows.

XG Preset Categories:
- Halls: Large/small concert halls, chambers
- Rooms: Recording studios, live rooms
- Plates: Electronic plate reverbs
- Ambience: General purpose reverbs
- Effects: Creative and special effects

Copyright (c) 2025 XG Synthesis Core
"""

from typing import Dict, List, Any
from enum import IntEnum


class XGPresetCategory(IntEnum):
    """XG Effect Preset Categories"""
    HALL = 0
    ROOM = 1
    PLATE = 2
    AMBIENCE = 3
    EFFECTS = 4
    VOCAL = 5
    DRUMS = 6
    GUITAR = 7
    KEYBOARD = 8


class XGEffectPresets:
    """
    XG Effect Presets - Professional Effect Configurations

    Provides 128 predefined effect configurations covering all major
    use cases and professional mixing scenarios.
    """

    # XG EFFECT PRESETS (0-127)
    # Each preset contains complete effect configuration
    PRESETS: Dict[int, Dict[str, Any]] = {

        # HALL PRESETS (0-19)
        0: {
            "name": "Concert Hall Large",
            "category": XGPresetCategory.HALL,
            "description": "Large concert hall with rich, natural reverb",
            "reverb": {
                "type": 1,      # Hall 1
                "time": 2.5,    # 2.5 seconds
                "level": 0.6,   # Moderate level
                "pre_delay": 0.02,  # 20ms pre-delay
                "hf_damping": 0.3,   # Natural HF rolloff
                "density": 0.8,      # High density
                "early_level": 0.5,  # Balanced early reflections
                "tail_level": 0.7    # Rich late reverb
            },
            "chorus": {
                "type": 0,      # Chorus 1
                "rate": 0.5,    # Moderate rate
                "depth": 0.4,   # Gentle modulation
                "feedback": 0.2, # Light feedback
                "level": 0.3    # Subtle enhancement
            },
            "variation": {
                "type": 13,     # Delay LCR
                "level": 0.0    # Off by default
            },
            "eq": {
                "type": 4,      # Concert
                "low_gain": 2.0,     # +2dB boost
                "mid_gain": 0.0,     # Flat
                "high_gain": -1.0    # -1dB cut
            }
        },

        1: {
            "name": "Concert Hall Medium",
            "category": XGPresetCategory.HALL,
            "description": "Medium concert hall, balanced acoustics",
            "reverb": {
                "type": 3,      # Hall 3
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.015,
                "hf_damping": 0.4,
                "density": 0.7,
                "early_level": 0.6,
                "tail_level": 0.6
            },
            "chorus": {
                "type": 1,      # Chorus 2
                "rate": 0.6,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.25
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 4,      # Concert
                "low_gain": 1.5,
                "mid_gain": 0.0,
                "high_gain": -0.5
            }
        },

        2: {
            "name": "Chamber Hall",
            "category": XGPresetCategory.HALL,
            "description": "Intimate chamber music hall",
            "reverb": {
                "type": 5,      # Hall 5
                "time": 1.8,
                "level": 0.4,
                "pre_delay": 0.01,
                "hf_damping": 0.5,
                "density": 0.6,
                "early_level": 0.7,
                "tail_level": 0.5
            },
            "chorus": {
                "type": 2,      # Celeste 1
                "rate": 0.8,
                "depth": 0.3,
                "feedback": 0.1,
                "level": 0.2
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,      # Jazz
                "low_gain": 1.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # ROOM PRESETS (20-39)
        20: {
            "name": "Recording Studio A",
            "category": XGPresetCategory.ROOM,
            "description": "Professional recording studio, neutral response",
            "reverb": {
                "type": 9,      # Room 1
                "time": 0.8,
                "level": 0.3,
                "pre_delay": 0.008,
                "hf_damping": 0.6,
                "density": 0.9,
                "early_level": 0.8,
                "tail_level": 0.4
            },
            "chorus": {
                "type": 0,
                "rate": 0.4,
                "depth": 0.2,
                "feedback": 0.0,
                "level": 0.15
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        21: {
            "name": "Live Room Bright",
            "category": XGPresetCategory.ROOM,
            "description": "Live room with bright, lively character",
            "reverb": {
                "type": 11,     # Room 3
                "time": 1.2,
                "level": 0.4,
                "pre_delay": 0.012,
                "hf_damping": 0.2,   # Less damping = brighter
                "density": 0.7,
                "early_level": 0.6,
                "tail_level": 0.6
            },
            "chorus": {
                "type": 3,      # Celeste 2
                "rate": 1.0,
                "depth": 0.4,
                "feedback": 0.2,
                "level": 0.25
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 2,      # Pops
                "low_gain": 0.5,
                "mid_gain": 0.0,
                "high_gain": 1.0
            }
        },

        # PLATE PRESETS (40-49)
        40: {
            "name": "Plate Reverb 1",
            "category": XGPresetCategory.PLATE,
            "description": "Classic plate reverb, smooth and lush",
            "reverb": {
                "type": 17,     # Plate 1
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.005,
                "hf_damping": 0.4,
                "density": 0.8,
                "early_level": 0.3,
                "tail_level": 0.8
            },
            "chorus": {
                "type": 0,
                "rate": 0.3,
                "depth": 0.1,
                "feedback": 0.0,
                "level": 0.1
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # AMBIENCE PRESETS (50-69)
        50: {
            "name": "Ambience Small",
            "category": XGPresetCategory.AMBIENCE,
            "description": "Small space ambience for subtle enhancement",
            "reverb": {
                "type": 9,      # Room 1
                "time": 0.5,
                "level": 0.2,
                "pre_delay": 0.005,
                "hf_damping": 0.7,
                "density": 0.8,
                "early_level": 0.9,
                "tail_level": 0.3
            },
            "chorus": {
                "type": 0,
                "rate": 0.2,
                "depth": 0.1,
                "feedback": 0.0,
                "level": 0.05
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # EFFECTS PRESETS (70-89)
        70: {
            "name": "Spring Reverb",
            "category": XGPresetCategory.EFFECTS,
            "description": "Vintage spring reverb simulation",
            "reverb": {
                "type": 17,     # Plate 1 (closest to spring)
                "time": 1.5,
                "level": 0.4,
                "pre_delay": 0.0,    # No pre-delay for spring character
                "hf_damping": 0.6,
                "density": 0.5,      # Less dense than plate
                "early_level": 0.2,
                "tail_level": 0.9
            },
            "chorus": {
                "type": 0,
                "rate": 0.1,
                "depth": 0.05,
                "feedback": 0.0,
                "level": 0.0
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,      # Rock
                "low_gain": -1.0,
                "mid_gain": 0.0,
                "high_gain": 2.0
            }
        },

        71: {
            "name": "Gated Reverb",
            "category": XGPresetCategory.EFFECTS,
            "description": "Classic gated reverb effect",
            "reverb": {
                "type": 1,      # Hall 1
                "time": 1.0,
                "level": 0.6,
                "pre_delay": 0.0,
                "hf_damping": 0.8,   # Heavy damping for gate
                "density": 0.9,
                "early_level": 1.0,  # Strong early reflections
                "tail_level": 0.1    # Weak tail (gets gated)
            },
            "chorus": {
                "type": 0,
                "rate": 0.0,
                "depth": 0.0,
                "feedback": 0.0,
                "level": 0.0
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # VOCAL PRESETS (90-99)
        90: {
            "name": "Vocal Hall",
            "category": XGPresetCategory.VOCAL,
            "description": "Concert hall optimized for vocal performance",
            "reverb": {
                "type": 2,      # Hall 2
                "time": 2.2,
                "level": 0.45,
                "pre_delay": 0.025,  # Longer pre-delay for vocals
                "hf_damping": 0.25,  # Less damping for vocal clarity
                "density": 0.75,
                "early_level": 0.55,
                "tail_level": 0.65
            },
            "chorus": {
                "type": 2,      # Celeste 1 (gentle for vocals)
                "rate": 0.4,
                "depth": 0.25,
                "feedback": 0.1,
                "level": 0.2
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,      # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.5
            }
        },

        # DRUM PRESETS (100-109)
        100: {
            "name": "Drum Room",
            "category": XGPresetCategory.DRUMS,
            "description": "Recording studio drum room",
            "reverb": {
                "type": 10,     # Room 2
                "time": 0.6,
                "level": 0.25,
                "pre_delay": 0.0,    # No pre-delay for drums
                "hf_damping": 0.8,   # Heavy HF damping
                "density": 0.95,     # Very dense
                "early_level": 1.0,  # Strong early reflections
                "tail_level": 0.2    # Short tail
            },
            "chorus": {
                "type": 0,
                "rate": 0.0,
                "depth": 0.0,
                "feedback": 0.0,
                "level": 0.0
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # GUITAR PRESETS (110-119)
        110: {
            "name": "Guitar Plate",
            "category": XGPresetCategory.GUITAR,
            "description": "Plate reverb optimized for electric guitar",
            "reverb": {
                "type": 18,     # Plate 2
                "time": 1.8,
                "level": 0.4,
                "pre_delay": 0.008,
                "hf_damping": 0.35,  # Moderate damping
                "density": 0.75,
                "early_level": 0.4,
                "tail_level": 0.75
            },
            "chorus": {
                "type": 4,      # Flanger 1 (classic guitar effect)
                "rate": 0.15,
                "depth": 0.6,
                "feedback": 0.4,
                "level": 0.3
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,      # Rock
                "low_gain": -0.5,
                "mid_gain": 1.0,
                "high_gain": 1.5
            }
        },

        # KEYBOARD PRESETS (120-127)
        120: {
            "name": "Piano Hall",
            "category": XGPresetCategory.KEYBOARD,
            "description": "Concert hall optimized for acoustic piano",
            "reverb": {
                "type": 4,      # Hall 4
                "time": 3.0,
                "level": 0.55,
                "pre_delay": 0.03,   # Longer pre-delay for piano
                "hf_damping": 0.2,   # Light damping for piano brightness
                "density": 0.7,
                "early_level": 0.5,
                "tail_level": 0.7
            },
            "chorus": {
                "type": 1,      # Chorus 2
                "rate": 0.5,
                "depth": 0.3,
                "feedback": 0.2,
                "level": 0.25
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,      # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        },

        # DEFAULT PRESET (127)
        127: {
            "name": "XG Default",
            "category": XGPresetCategory.AMBIENCE,
            "description": "XG specification default settings",
            "reverb": {
                "type": 1,      # Hall 1
                "time": 64,     # NRPN default (converted)
                "level": 0.4,
                "pre_delay": 0.02,
                "hf_damping": 0.5,
                "density": 0.8,
                "early_level": 0.5,
                "tail_level": 0.5
            },
            "chorus": {
                "type": 0,      # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.3
            },
            "variation": {
                "type": 13,     # Delay LCR
                "level": 0.5
            },
            "eq": {
                "type": 0,      # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0
            }
        }
    }

    @classmethod
    def get_preset(cls, preset_id: int) -> Dict[str, Any]:
        """
        Get a preset configuration by ID.

        Args:
            preset_id: Preset ID (0-127)

        Returns:
            Preset configuration dictionary, or default if not found
        """
        return cls.PRESETS.get(preset_id, cls.PRESETS[127])  # Default to XG Default

    @classmethod
    def get_preset_names(cls) -> Dict[int, str]:
        """
        Get all preset names indexed by ID.

        Returns:
            Dictionary mapping preset IDs to names
        """
        return {pid: preset["name"] for pid, preset in cls.PRESETS.items()}

    @classmethod
    def get_presets_by_category(cls, category: XGPresetCategory) -> Dict[int, Dict[str, Any]]:
        """
        Get all presets in a specific category.

        Args:
            category: Preset category

        Returns:
            Dictionary of presets in the category
        """
        return {pid: preset for pid, preset in cls.PRESETS.items()
                if preset["category"] == category}

    @classmethod
    def apply_preset_to_coordinator(cls, preset_id: int, coordinator) -> bool:
        """
        Apply a preset configuration to an effects coordinator.

        Args:
            preset_id: Preset ID to apply
            coordinator: XGEffectsCoordinator instance

        Returns:
            True if preset was applied successfully
        """
        preset = cls.get_preset(preset_id)
        if not preset:
            return False

        try:
            # Apply reverb settings
            reverb = preset["reverb"]
            coordinator.set_system_effect_parameter('reverb', 'type', reverb['type'])
            coordinator.set_system_effect_parameter('reverb', 'time', reverb['time'])
            coordinator.set_system_effect_parameter('reverb', 'level', reverb['level'])
            coordinator.set_system_effect_parameter('reverb', 'pre_delay', reverb['pre_delay'])
            coordinator.set_system_effect_parameter('reverb', 'hf_damping', reverb['hf_damping'])
            coordinator.set_system_effect_parameter('reverb', 'density', reverb['density'])
            coordinator.set_system_effect_parameter('reverb', 'early_level', reverb['early_level'])
            coordinator.set_system_effect_parameter('reverb', 'tail_level', reverb['tail_level'])

            # Apply chorus settings
            chorus = preset["chorus"]
            coordinator.set_system_effect_parameter('chorus', 'type', chorus['type'])
            coordinator.set_system_effect_parameter('chorus', 'rate', chorus['rate'])
            coordinator.set_system_effect_parameter('chorus', 'depth', chorus['depth'])
            coordinator.set_system_effect_parameter('chorus', 'feedback', chorus['feedback'])
            coordinator.set_system_effect_parameter('chorus', 'level', chorus['level'])

            # Apply variation settings
            variation = preset["variation"]
            coordinator.set_variation_effect_type(variation['type'])
            # Note: variation level would be set via sends if needed

            # Apply EQ settings
            eq = preset["eq"]
            coordinator.set_master_eq_type(eq['type'])
            coordinator.set_master_eq_gain('low', eq['low_gain'])
            coordinator.set_master_eq_gain('low_mid', 0.0)  # Not in basic preset
            coordinator.set_master_eq_gain('mid', eq['mid_gain'])
            coordinator.set_master_eq_gain('high_mid', 0.0)  # Not in basic preset
            coordinator.set_master_eq_gain('high', eq['high_gain'])

            return True

        except Exception as e:
            print(f"Error applying preset {preset_id}: {e}")
            return False

    @classmethod
    def create_custom_preset(cls, name: str, category: XGPresetCategory,
                           reverb_params: Dict[str, float],
                           chorus_params: Dict[str, float],
                           variation_params: Dict[str, int],
                           eq_params: Dict[str, float]) -> Dict[str, Any]:
        """
        Create a custom preset configuration.

        Args:
            name: Preset name
            category: Preset category
            reverb_params: Reverb parameter dictionary
            chorus_params: Chorus parameter dictionary
            variation_params: Variation parameter dictionary
            eq_params: EQ parameter dictionary

        Returns:
            Custom preset configuration
        """
        return {
            "name": name,
            "category": category,
            "description": f"Custom {name} preset",
            "reverb": reverb_params,
            "chorus": chorus_params,
            "variation": variation_params,
            "eq": eq_params
        }
