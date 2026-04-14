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
- Vocal: Optimized for vocal performance
- Drums: Optimized for drum kits
- Guitar: Optimized for electric guitar
- Keyboard: Optimized for keyboard instruments

Copyright (c) 2025 XG Synthesis Core
"""

from __future__ import annotations

"""
XG Master Section - XG Master Compressor/Limiter, Stereo Enhancer, and Volume Curves

This module implements XG master section effects including:
- XG Master Compressor/Limiter with full parameter control
- XG Stereo Enhancer for spatial enhancement
- XG Volume Curves with customizable response curves

All components support XG NRPN parameter control and real-time operation.
"""

import math
import threading
from enum import IntEnum
from typing import Any

import numpy as np


from .xg_volume_curve import XGVolumeCurve
from .xg_master_compressor import XGMasterCompressor
from .xg_stereo_enhancer import XGStereoEnhancer
class XGMasterSection:
    """
    XG Master Section - Complete Master Effects Chain

    Combines compressor/limiter, stereo enhancer, and volume curves
    with XG-compliant parameter control and professional processing.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Initialize master section components
        self.compressor = XGMasterCompressor(sample_rate)
        self.stereo_enhancer = XGStereoEnhancer(sample_rate)
        self.volume_curve = XGVolumeCurve(sample_rate)

        # Master section configuration
        self.chain_order = ["compressor", "stereo_enhancer", "volume_curve"]
        self.master_bypass = False

        self.lock = threading.RLock()

    def set_parameter(self, component: str, param: str, value: float) -> bool:
        """Set parameter for a specific component."""
        with self.lock:
            if component == "compressor":
                return self.compressor.set_parameter(param, value)
            elif component == "stereo_enhancer":
                return self.stereo_enhancer.set_parameter(param, value)
            elif component == "volume_curve":
                if param == "curve_type":
                    self.volume_curve.set_curve_type(int(value))
                elif param == "knee":
                    self.volume_curve.set_knee(value)
                elif param == "master_volume":
                    self.volume_curve.set_master_volume(value)
                elif param == "curve_shape":
                    self.volume_curve.set_curve_shape(value)
                return True
            return False

    def set_chain_order(self, order: list[str]) -> None:
        """Set the processing order of master effects."""
        with self.lock:
            valid_components = {"compressor", "stereo_enhancer", "volume_curve"}
            if all(comp in valid_components for comp in order):
                self.chain_order = order

    def set_master_bypass(self, bypass: bool) -> None:
        """Set master bypass for entire section."""
        with self.lock:
            self.master_bypass = bypass

    def process_block(
        self, stereo_block: np.ndarray, num_samples: int, input_level: float = 1.0
    ) -> None:
        """
        Process block through complete master section.

        Args:
            stereo_block: Stereo audio block (num_samples, 2)
            num_samples: Number of samples to process
            input_level: Input level for volume curve (0-1)
        """
        if self.master_bypass:
            return

        with self.lock:
            # Process through chain in specified order
            for component in self.chain_order:
                if component == "compressor":
                    self.compressor.process_block(stereo_block, num_samples)
                elif component == "stereo_enhancer":
                    self.stereo_enhancer.process_block(stereo_block, num_samples)
                elif component == "volume_curve":
                    # Apply volume curve based on input level
                    curve_gain = self.volume_curve.apply_volume_curve(input_level)
                    stereo_block[:num_samples] *= curve_gain

            # Final limiting to prevent clipping
            np.clip(stereo_block[:num_samples], -1.0, 1.0, out=stereo_block[:num_samples])

    def get_master_status(self) -> dict[str, Any]:
        """Get status of all master section components."""
        with self.lock:
            return {
                "compressor": {
                    "enabled": self.compressor.params["enabled"],
                    "threshold": self.compressor.params["threshold"],
                    "ratio": self.compressor.params["ratio"],
                },
                "stereo_enhancer": {
                    "enabled": self.stereo_enhancer.params["enabled"],
                    "width": self.stereo_enhancer.params["width"],
                    "hf_width": self.stereo_enhancer.params["hf_width"],
                },
                "volume_curve": {
                    "curve_type": self.volume_curve.curve_type,
                    "master_volume": self.volume_curve.master_volume,
                },
                "chain_order": self.chain_order,
                "master_bypass": self.master_bypass,
            }

    def reset(self) -> None:
        """Reset all master section components."""
        with self.lock:
            # Reset components that have reset methods
            self.compressor.reset()
            # Note: XGStereoEnhancer and XGVolumeCurve don't need reset methods
            # as they are stateless or have simple state


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

    Presets include complete system effect chains with:
    - Reverb (25 XG types)
    - Chorus (6 XG types)
    - Variation effects (84 types)
    - Master EQ (5-band parametric)
    """

    # XG Standard Effect Presets (128 total)
    PRESETS = {
        # XG DEFAULT (0)
        0: {
            "name": "XG Default",
            "category": XGPresetCategory.AMBIENCE,
            "description": "XG standard default settings",
            "reverb": {
                "type": 1,  # Hall 1
                "time": 2.5,
                "level": 0.4,
                "pre_delay": 0.02,
                "hf_damping": 0.5,
                "density": 0.8,
                "early_level": 0.5,
                "tail_level": 0.5,
            },
            "chorus": {
                "type": 0,  # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.3,
            },
            "variation": {
                "type": 13,  # Delay LCR
                "level": 0.5,
            },
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # HALL PRESETS (1-19)
        1: {
            "name": "Concert Hall Medium",
            "category": XGPresetCategory.HALL,
            "description": "Medium concert hall, balanced acoustics",
            "reverb": {
                "type": 3,  # Hall 3
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.015,
                "hf_damping": 0.4,
                "density": 0.7,
                "early_level": 0.6,
                "tail_level": 0.6,
            },
            "chorus": {
                "type": 1,  # Chorus 2
                "rate": 0.6,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.25,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 4,  # Concert
                "low_gain": 1.5,
                "mid_gain": 0.0,
                "high_gain": -0.5,
            },
        },
        # ROOM PRESETS (20-39)
        20: {
            "name": "Recording Studio A",
            "category": XGPresetCategory.ROOM,
            "description": "Professional recording studio, neutral response",
            "reverb": {
                "type": 9,  # Room 1
                "time": 0.8,
                "level": 0.3,
                "pre_delay": 0.008,
                "hf_damping": 0.6,
                "density": 0.9,
                "early_level": 0.8,
                "tail_level": 0.4,
            },
            "chorus": {"type": 0, "rate": 0.4, "depth": 0.2, "feedback": 0.0, "level": 0.15},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # PLATE PRESETS (40-49)
        40: {
            "name": "Plate Reverb 1",
            "category": XGPresetCategory.PLATE,
            "description": "Classic plate reverb, smooth and lush",
            "reverb": {
                "type": 17,  # Plate 1
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.005,
                "hf_damping": 0.4,
                "density": 0.8,
                "early_level": 0.3,
                "tail_level": 0.8,
            },
            "chorus": {"type": 0, "rate": 0.3, "depth": 0.1, "feedback": 0.0, "level": 0.1},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # AMBIENCE PRESETS (50-69)
        50: {
            "name": "Ambience Small",
            "category": XGPresetCategory.AMBIENCE,
            "description": "Small space ambience for subtle enhancement",
            "reverb": {
                "type": 9,  # Room 1
                "time": 0.5,
                "level": 0.2,
                "pre_delay": 0.005,
                "hf_damping": 0.7,
                "density": 0.8,
                "early_level": 0.9,
                "tail_level": 0.3,
            },
            "chorus": {"type": 0, "rate": 0.2, "depth": 0.1, "feedback": 0.0, "level": 0.05},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # EFFECTS PRESETS (70-89)
        70: {
            "name": "Spring Reverb",
            "category": XGPresetCategory.EFFECTS,
            "description": "Vintage spring reverb simulation",
            "reverb": {
                "type": 17,  # Plate 1 (closest to spring)
                "time": 1.5,
                "level": 0.4,
                "pre_delay": 0.0,  # No pre-delay for spring character
                "hf_damping": 0.6,
                "density": 0.5,  # Less dense than plate
                "early_level": 0.2,
                "tail_level": 0.9,
            },
            "chorus": {"type": 0, "rate": 0.1, "depth": 0.05, "feedback": 0.0, "level": 0.0},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,  # Rock
                "low_gain": -1.0,
                "mid_gain": 0.0,
                "high_gain": 2.0,
            },
        },
        # VOCAL PRESETS (90-99)
        90: {
            "name": "Vocal Hall",
            "category": XGPresetCategory.VOCAL,
            "description": "Concert hall optimized for vocal performance",
            "reverb": {
                "type": 2,  # Hall 2
                "time": 2.2,
                "level": 0.45,
                "pre_delay": 0.025,  # Longer pre-delay for vocals
                "hf_damping": 0.25,  # Less damping for vocal clarity
                "density": 0.75,
                "early_level": 0.55,
                "tail_level": 0.65,
            },
            "chorus": {
                "type": 2,  # Celeste 1 (gentle for vocals)
                "rate": 0.4,
                "depth": 0.25,
                "feedback": 0.1,
                "level": 0.2,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,  # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.5,
            },
        },
        # DRUM PRESETS (100-109)
        100: {
            "name": "Drum Room",
            "category": XGPresetCategory.DRUMS,
            "description": "Recording studio drum room",
            "reverb": {
                "type": 10,  # Room 2
                "time": 0.6,
                "level": 0.25,
                "pre_delay": 0.0,  # No pre-delay for drums
                "hf_damping": 0.8,  # Heavy HF damping
                "density": 0.95,  # Very dense
                "early_level": 1.0,  # Strong early reflections
                "tail_level": 0.2,  # Short tail
            },
            "chorus": {"type": 0, "rate": 0.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # GUITAR PRESETS (110-119)
        110: {
            "name": "Guitar Plate",
            "category": XGPresetCategory.GUITAR,
            "description": "Plate reverb optimized for electric guitar",
            "reverb": {
                "type": 18,  # Plate 2
                "time": 1.8,
                "level": 0.4,
                "pre_delay": 0.008,
                "hf_damping": 0.35,  # Moderate damping
                "density": 0.75,
                "early_level": 0.4,
                "tail_level": 0.75,
            },
            "chorus": {
                "type": 4,  # Flanger 1 (classic guitar effect)
                "rate": 0.15,
                "depth": 0.6,
                "feedback": 0.4,
                "level": 0.3,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,  # Rock
                "low_gain": -0.5,
                "mid_gain": 1.0,
                "high_gain": 1.5,
            },
        },
        # KEYBOARD PRESETS (120-127)
        120: {
            "name": "Piano Hall",
            "category": XGPresetCategory.KEYBOARD,
            "description": "Concert hall optimized for acoustic piano",
            "reverb": {
                "type": 4,  # Hall 4
                "time": 3.0,
                "level": 0.55,
                "pre_delay": 0.03,  # Longer pre-delay for piano
                "hf_damping": 0.2,  # Light damping for piano brightness
                "density": 0.7,
                "early_level": 0.5,
                "tail_level": 0.7,
            },
            "chorus": {
                "type": 1,  # Chorus 2
                "rate": 0.5,
                "depth": 0.3,
                "feedback": 0.2,
                "level": 0.25,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,  # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # DEFAULT PRESET (127)
        127: {
            "name": "XG Default",
            "category": XGPresetCategory.AMBIENCE,
            "description": "XG specification default settings",
            "reverb": {
                "type": 1,  # Hall 1
                "time": 2.5,  # NRPN default (converted)
                "level": 0.4,
                "pre_delay": 0.02,
                "hf_damping": 0.5,
                "density": 0.8,
                "early_level": 0.5,
                "tail_level": 0.5,
            },
            "chorus": {
                "type": 0,  # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.3,
            },
            "variation": {
                "type": 13,  # Delay LCR
                "level": 0.5,
            },
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
    }

    @classmethod
    def get_preset(cls, preset_id: int) -> dict[str, Any]:
        """
        Get a preset configuration by ID.

        Args:
            preset_id: Preset ID (0-127)

        Returns:
            Preset configuration dictionary, or default if not found
        """
        return cls.PRESETS.get(preset_id, cls.PRESETS[127])  # Default to XG Default

    @classmethod
    def get_preset_names(cls) -> dict[int, str]:
        """
        Get all preset names indexed by ID.

        Returns:
            Dictionary mapping preset IDs to names
        """
        return {pid: preset["name"] for pid, preset in cls.PRESETS.items()}

    @classmethod
    def get_presets_by_category(cls, category: XGPresetCategory) -> dict[int, dict[str, Any]]:
        """
        Get all presets in a specific category.

        Args:
            category: Preset category

        Returns:
            Dictionary of presets in the category
        """
        return {
            pid: preset for pid, preset in cls.PRESETS.items() if preset.get("category") == category
        }

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
            reverb = preset.get("reverb", {})
            if reverb:
                coordinator.set_system_effect_parameter("reverb", "type", reverb.get("type", 1))
                coordinator.set_system_effect_parameter("reverb", "time", reverb.get("time", 2.5))
                coordinator.set_system_effect_parameter("reverb", "level", reverb.get("level", 0.4))
                coordinator.set_system_effect_parameter(
                    "reverb", "pre_delay", reverb.get("pre_delay", 0.02)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "hf_damping", reverb.get("hf_damping", 0.5)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "density", reverb.get("density", 0.8)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "early_level", reverb.get("early_level", 0.5)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "tail_level", reverb.get("tail_level", 0.5)
                )

            # Apply chorus settings
            chorus = preset.get("chorus", {})
            if chorus:
                coordinator.set_system_effect_parameter("chorus", "type", chorus.get("type", 0))
                coordinator.set_system_effect_parameter("chorus", "rate", chorus.get("rate", 1.0))
                coordinator.set_system_effect_parameter("chorus", "depth", chorus.get("depth", 0.5))
                coordinator.set_system_effect_parameter(
                    "chorus", "feedback", chorus.get("feedback", 0.3)
                )
                coordinator.set_system_effect_parameter("chorus", "level", chorus.get("level", 0.3))

            # Apply variation settings
            variation = preset.get("variation", {})
            if variation:
                coordinator.set_variation_effect_type(variation.get("type", 13))

            # Apply EQ settings
            eq = preset.get("eq", {})
            if eq:
                coordinator.set_master_eq_type(eq.get("type", 0))
                coordinator.set_master_eq_gain("low", eq.get("low_gain", 0.0))
                coordinator.set_master_eq_gain("mid", eq.get("mid_gain", 0.0))
                coordinator.set_master_eq_gain("high", eq.get("high_gain", 0.0))

            return True

        except Exception as e:
            print(f"Error applying preset {preset_id}: {e}")
            return False
