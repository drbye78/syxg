"""
XG Effects Integration System

Integrates XG-specific effects with MIDI 2.0 parameter resolution and per-note control.
Provides comprehensive support for XG system effects, insertion effects, and variation effects
with 32-bit parameter precision.
"""

from __future__ import annotations

import math
from enum import IntEnum

import numpy as np

from .midi_2_effects_processor import (
    EffectParameter,
    EffectProcessor,
    EffectType,
    ParameterResolution,
)


class XGEffectType(IntEnum):
    """XG-specific effect types"""

    # System Effects (applied globally)
    REVERB_PLATE = 0x00
    REVERB_HALL = 0x01
    REVERB_ROOM = 0x02
    REVERB_STUDIO = 0x03
    REVERB_GATED = 0x04
    REVERB_REVERSE = 0x05
    REVERB_SHORT = 0x06
    REVERB_LONG = 0x07

    CHORUS_STANDARD = 0x10
    CHORUS_FLANGER = 0x11
    CHORUS_CELESTE = 0x12
    CHORUS_DETUNE = 0x13
    CHORUS_DIMENSION = 0x14

    # Variation Effects (multi-function)
    VARIATION_MULTI_CHORUS = 0x20
    VARIATION_STEREO_DELAY = 0x21
    VARIATION_TREMOLO = 0x22
    VARIATION_AUTO_PANNER = 0x23
    VARIATION_PHASER = 0x24
    VARIATION_FLANGER = 0x25
    VARIATION_ROTARY_SPEAKER = 0x26
    VARIATION_DISTORTION = 0x27
    VARIATION_COMPRESSOR = 0x28
    VARIATION_GATE = 0x29
    VARIATION_EQ = 0x2A
    VARIATION_FILTER = 0x2B
    VARIATION_OCTAVE = 0x2C
    VARIATION_PITCH_SHIFTER = 0x2D
    VARIATION_FEEDBACK_DELAY = 0x2E
    VARIATION_LOFI = 0x2F

    # Insertion Effects (per-part)
    INSERT_DUAL_DELAY = 0x40
    INSERT_STEREO_DELAY = 0x41
    INSERT_MULTI_TAP_DELAY = 0x42
    INSERT_CROSS_DELAY = 0x43
    INSERT_MOD_DELAY = 0x44
    INSERT_STEREO_CHORUS = 0x45
    INSERT_MONO_CHORUS = 0x46
    INSERT_MULTI_CHORUS = 0x47
    INSERT_STEREO_FLANGER = 0x48
    INSERT_MONO_FLANGER = 0x49
    INSERT_STEREO_PHASER = 0x4A
    INSERT_MONO_PHASER = 0x4B
    INSERT_STEREO_TREMOLO = 0x4C
    INSERT_MONO_TREMOLO = 0x4D
    INSERT_AUTO_PANNER = 0x4E
    INSERT_ROTARY_SPEAKER = 0x4F
    INSERT_DISTORTION = 0x50
    INSERT_OVERDRIVE = 0x51
    INSERT_AMP_SIMULATOR = 0x52
    INSERT_COMPRESSOR = 0x53
    INSERT_LIMITER = 0x54
    INSERT_GATE = 0x55
    INSERT_EXPANDER = 0x56
    INSERT_EQ_3_BAND = 0x57
    INSERT_EQ_5_BAND = 0x58
    INSERT_EQ_7_BAND = 0x59
    INSERT_EQ_15_BAND = 0x5A
    INSERT_EQ_PARAMETRIC = 0x5B
    INSERT_FILTER_LOW_PASS = 0x5C
    INSERT_FILTER_HIGH_PASS = 0x5D
    INSERT_FILTER_BAND_PASS = 0x5E
    INSERT_FILTER_NOTCH = 0x5F
    INSERT_FILTER_FORMANT = 0x60
    INSERT_FILTER_WOW_FLUTTER = 0x61
    INSERT_PITCH_SHIFTER = 0x62
    INSERT_MONO_TO_STEREO = 0x63
    INSERT_SIX_BAND_EQ = 0x64
    INSERT_DRIVE = 0x65
    INSERT_TALK_MODULATOR = 0x66
    INSERT_ENSEMBLE = 0x67
    INSERT_HARMONIZER = 0x68
    INSERT_ACOUSTIC_SIMULATOR = 0x69
    INSERT_CROSSOVER = 0x6A
    INSERT_LOFI = 0x6B
    INSERT_VOCODER = 0x6C
    INSERT_GRANULAR = 0x6D
    INSERT_SPECTRAL = 0x6E
    INSERT_CONVOLUTION_REVERB = 0x6F


from .xg_system_reverb import XGSystemReverb
from .xg_variation_effect import XGVariationEffect
from .xg_insertion_effect import XGInsertionEffect
class XGMIDIEffectsProcessor:
    """
    XG MIDI Effects Processor with Full MIDI 2.0 Integration

    Manages XG system, variation, and insertion effects with 32-bit parameter
    resolution and per-note control capabilities.
    """

    def __init__(self, sample_rate: int = 48000):
        """
        Initialize XG MIDI effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.enabled = True

        # XG effect slots
        self.system_reverb: XGSystemReverb | None = None
        self.system_chorus: EffectProcessor | None = None
        self.variation_effect: XGVariationEffect | None = None
        self.insertion_effects: list[XGInsertionEffect] = []

        # Initialize default XG effects
        self._initialize_xg_effects()

    def _initialize_xg_effects(self):
        """Initialize default XG effects."""
        self.system_reverb = XGSystemReverb(self.sample_rate, XGEffectType.REVERB_HALL)
        self.variation_effect = XGVariationEffect(
            self.sample_rate, XGEffectType.VARIATION_MULTI_CHORUS
        )

        # Add default insertion effect
        default_insertion = XGInsertionEffect(self.sample_rate, XGEffectType.INSERT_DUAL_DELAY)
        self.insertion_effects.append(default_insertion)

    def set_system_reverb_type(self, reverb_type: XGEffectType):
        """Set system reverb type."""
        if self.system_reverb:
            self.system_reverb.xg_effect_type = reverb_type
            # Reinitialize parameters for the new type
            self.system_reverb._initialize_xg_parameters()

    def set_variation_type(self, var_type: XGEffectType):
        """Set variation effect type."""
        if self.variation_effect:
            self.variation_effect.xg_effect_type = var_type
            # Reinitialize parameters for the new type
            self.variation_effect._initialize_xg_variation_parameters()

    def add_insertion_effect(self, effect_type: XGEffectType) -> int:
        """
        Add an insertion effect.

        Args:
            effect_type: Type of insertion effect to add

        Returns:
            Index of the added effect
        """
        effect = XGInsertionEffect(self.sample_rate, effect_type)
        self.insertion_effects.append(effect)
        return len(self.insertion_effects) - 1

    def remove_insertion_effect(self, index: int) -> bool:
        """
        Remove an insertion effect.

        Args:
            index: Index of effect to remove

        Returns:
            True if removed successfully
        """
        if 0 <= index < len(self.insertion_effects):
            del self.insertion_effects[index]
            return True
        return False

    def process_audio_with_xg_effects(
        self, audio_input: np.ndarray, part: int = 0, note: int | None = None
    ) -> np.ndarray:
        """
        Process audio through XG effects chain.

        Args:
            audio_input: Input audio as numpy array
            part: Part number for part-specific processing
            note: Note number for per-note processing

        Returns:
            Processed audio as numpy array
        """
        if not self.enabled:
            return audio_input

        # Start with input audio
        processed_audio = audio_input.copy()

        # Apply insertion effects first (they're part-specific)
        for insertion_effect in self.insertion_effects:
            if insertion_effect.enabled and not insertion_effect.bypass:
                processed_audio = insertion_effect.process_audio(processed_audio, note)

        # Apply system effects
        if self.system_reverb and self.system_reverb.enabled and not self.system_reverb.bypass:
            processed_audio = self.system_reverb.process_audio(processed_audio, note)

        # Apply variation effect
        if (
            self.variation_effect
            and self.variation_effect.enabled
            and not self.variation_effect.bypass
        ):
            processed_audio = self.variation_effect.process_audio(processed_audio, note)

        return processed_audio

    def set_xg_parameter(
        self,
        effect_slot: str,
        param_name: str,
        value: float,
        resolution: ParameterResolution = ParameterResolution.MIDI_2_32_BIT,
    ):
        """
        Set an XG parameter with specified resolution.

        Args:
            effect_slot: 'system_reverb', 'system_chorus', 'variation', or 'insertion_N' where N is index
            param_name: Parameter name
            value: Parameter value
            resolution: Parameter resolution
        """
        if effect_slot.startswith("insertion_"):
            # Parse insertion effect index
            try:
                idx = int(effect_slot.split("_")[1])
                if 0 <= idx < len(self.insertion_effects):
                    effect = self.insertion_effects[idx]
                    effect.set_parameter(param_name, value, resolution)
            except (ValueError, IndexError):
                pass
        elif effect_slot == "system_reverb" and self.system_reverb:
            self.system_reverb.set_parameter(param_name, value, resolution)
        elif effect_slot == "variation" and self.variation_effect:
            self.variation_effect.set_parameter(param_name, value, resolution)

    def set_per_note_xg_parameter(
        self,
        note: int,
        effect_slot: str,
        param_name: str,
        value: float,
        resolution: ParameterResolution = ParameterResolution.MIDI_2_32_BIT,
    ):
        """
        Set a per-note XG parameter.

        Args:
            note: MIDI note number
            effect_slot: Effect slot identifier
            param_name: Parameter name
            value: Parameter value
            resolution: Parameter resolution
        """
        if effect_slot.startswith("insertion_"):
            # Parse insertion effect index
            try:
                idx = int(effect_slot.split("_")[1])
                if 0 <= idx < len(self.insertion_effects):
                    effect = self.insertion_effects[idx]
                    effect.set_per_note_parameter(note, param_name, value, resolution)
            except (ValueError, IndexError):
                pass
        elif effect_slot == "system_reverb" and self.system_reverb:
            self.system_reverb.set_per_note_parameter(note, param_name, value, resolution)
        elif effect_slot == "variation" and self.variation_effect:
            self.variation_effect.set_per_note_parameter(note, param_name, value, resolution)


# Global instance for XG effects
xg_midi_effects_processor = XGMIDIEffectsProcessor()


def get_xg_midi_effects_processor() -> XGMIDIEffectsProcessor:
    """
    Get the global XG MIDI effects processor instance.

    Returns:
        XGMIDIEffectsProcessor instance
    """
    return xg_midi_effects_processor
