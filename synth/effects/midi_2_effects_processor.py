"""
MIDI 2.0 Effects Processing System

Advanced effects processing system with full MIDI 2.0 support including 32-bit parameter resolution,
per-note effects control, and profile-based effects configuration.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
import numpy as np
import math
from enum import IntEnum
from dataclasses import dataclass


class MIDI2EffectType(IntEnum):
    """MIDI 2.0 Effect Types with 32-bit parameter support"""
    # Standard Effects with Enhanced Resolution
    REVERB_HALL_32BIT = 0x100
    REVERB_ROOM_32BIT = 0x101
    REVERB_PLATE_32BIT = 0x102
    REVERB_CHAMBER_32BIT = 0x103
    REVERB_SPRING_32BIT = 0x104
    REVERB_CONVOLUTION_32BIT = 0x105
    
    CHORUS_STANDARD_32BIT = 0x110
    CHORUS_FLANGER_32BIT = 0x111
    CHORUS_CELESTE_32BIT = 0x112
    CHORUS_DIMENSION_32BIT = 0x113
    CHORUS_ENSEMBLE_32BIT = 0x114
    
    DELAY_STEREO_32BIT = 0x120
    DELAY_MULTI_TAP_32BIT = 0x121
    DELAY_CROSS_32BIT = 0x122
    DELAY_MODULATED_32BIT = 0x123
    DELAY_ANALOG_32BIT = 0x124
    DELAY_DIGITAL_32BIT = 0x125
    
    FILTER_LOW_PASS_32BIT = 0x130
    FILTER_HIGH_PASS_32BIT = 0x131
    FILTER_BAND_PASS_32BIT = 0x132
    FILTER_NOTCH_32BIT = 0x133
    FILTER_ALL_PASS_32BIT = 0x134
    FILTER_FORMANT_32BIT = 0x135
    FILTER_STATE_VARIABLE_32BIT = 0x136
    FILTER_RESONANT_32BIT = 0x137
    FILTER_WOW_FLUTTER_32BIT = 0x138
    
    MODULATION_TREMOLO_32BIT = 0x140
    MODULATION_VIBRATO_32BIT = 0x141
    MODULATION_AUTO_PANNER_32BIT = 0x142
    MODULATION_PHASER_32BIT = 0x143
    MODULATION_FLANGER_32BIT = 0x144
    MODULATION_ROTARY_SPEAKER_32BIT = 0x145
    MODULATION_ENVELOPE_FOLLOWER_32BIT = 0x146
    
    DYNAMICS_COMPRESSOR_32BIT = 0x150
    DYNAMICS_LIMITER_32BIT = 0x151
    DYNAMICS_EXPANDER_32BIT = 0x152
    DYNAMICS_GATE_32BIT = 0x153
    DYNAMICS_SIDECHAIN_COMPRESSOR_32BIT = 0x154
    
    DISTORTION_SOFT_CLIP_32BIT = 0x160
    DISTORTION_HARD_CLIP_32BIT = 0x161
    DISTORTION_FUZZ_32BIT = 0x162
    DISTORTION_OVERDRIVE_32BIT = 0x163
    DISTORTION_AMP_SIMULATOR_32BIT = 0x164
    DISTORTION_TRANSISTOR_32BIT = 0x165
    DISTORTION_TUBE_32BIT = 0x166
    DISTORTION_DIODE_32BIT = 0x167
    
    EQ_PARAMETRIC_32BIT = 0x170
    EQ_GRAPHIC_32BIT = 0x171
    EQ_SHELVING_32BIT = 0x172
    EQ_HIGH_PASS_32BIT = 0x173
    EQ_LOW_PASS_32BIT = 0x174
    EQ_BAND_PASS_32BIT = 0x175
    EQ_NOTCH_32BIT = 0x176
    EQ_ALL_PASS_32BIT = 0x177
    
    # Per-Note Effects
    PER_NOTE_REVERB_SEND_32BIT = 0x200
    PER_NOTE_CHORUS_SEND_32BIT = 0x201
    PER_NOTE_DELAY_SEND_32BIT = 0x202
    PER_NOTE_DISTORTION_SEND_32BIT = 0x203
    PER_NOTE_FILTER_CUTOFF_32BIT = 0x204
    PER_NOTE_FILTER_RESONANCE_32BIT = 0x205
    PER_NOTE_PAN_32BIT = 0x206
    PER_NOTE_WIDTH_32BIT = 0x207
    PER_NOTE_POSITION_32BIT = 0x208
    PER_NOTE_DIRECTION_32BIT = 0x209
    PER_NOTE_DISTANCE_32BIT = 0x20A
    PER_NOTE_ELEVATION_32BIT = 0x20B
    PER_NOTE_AZIMUTH_32BIT = 0x20C
    PER_NOTE_SPREAD_32BIT = 0x20D
    PER_NOTE_HEIGHT_32BIT = 0x20E
    PER_NOTE_DEPTH_32BIT = 0x20F
    
    # Advanced Effects
    PITCH_SHIFTER_32BIT = 0x300
    HARMONIZER_32BIT = 0x301
    VOCODER_32BIT = 0x302
    RING_MODULATOR_32BIT = 0x303
    FREQUENCY_SHIFTER_32BIT = 0x304
    PHASE_SHIFTER_32BIT = 0x305
    GRANULAR_32BIT = 0x306
    SPECTRAL_32BIT = 0x307
    CONVOLUTION_REVERB_32BIT = 0x308
    SPECTRAL_DELAY_32BIT = 0x309
    SPECTRAL_MODULATION_32BIT = 0x30A
    SPECTRAL_FILTER_32BIT = 0x30B
    SPECTRAL_MORPHING_32BIT = 0x30C
    SPECTRAL_FREEZE_32BIT = 0x30D
    SPECTRAL_STRETCH_32BIT = 0x30E
    SPECTRAL_COMPRESS_32BIT = 0x30F
    SPECTRAL_EXPAND_32BIT = 0x310
    SPECTRAL_PITCH_SHIFT_32BIT = 0x311
    SPECTRAL_HARMONIZER_32BIT = 0x312
    SPECTRAL_VOCODER_32BIT = 0x313
    SPECTRAL_RING_MOD_32BIT = 0x314
    SPECTRAL_FREQUENCY_SHIFT_32BIT = 0x315
    SPECTRAL_PHASE_SHIFT_32BIT = 0x316
    SPECTRAL_GRANULAR_32BIT = 0x317
    SPECTRAL_CONVOLUTION_32BIT = 0x318
    SPECTRAL_FORMANT_32BIT = 0x319
    SPECTRAL_TUBE_32BIT = 0x31A
    SPECTRAL_TRANSISTOR_32BIT = 0x31B
    SPECTRAL_DIODE_32BIT = 0x31C
    SPECTRAL_FUZZ_32BIT = 0x31D
    SPECTRAL_OVERDRIVE_32BIT = 0x31E
    SPECTRAL_AMP_SIM_32BIT = 0x31F


@dataclass
class EffectParameter:
    """Effect parameter with 32-bit resolution support"""
    name: str
    min_value: float
    max_value: float
    default_value: float
    unit: str = ""
    description: str = ""
    resolution_bits: int = 32  # MIDI 2.0: 32-bit resolution
    is_per_note: bool = False  # Whether this is a per-note parameter
    supports_mpe_plus: bool = False  # Whether MPE+ extensions are supported
    parameter_type: str = "continuous"  # "continuous", "discrete", "enumerated"
    enumeration_values: Optional[Dict[int, str]] = None  # For enumerated parameters


class MIDI2EffectProcessor:
    """
    MIDI 2.0 Effects Processor with 32-bit Parameter Resolution
    
    Processes audio effects with full MIDI 2.0 parameter resolution and per-note control.
    Supports both standard effects and per-note effects processing.
    """
    
    def __init__(self, sample_rate: int = 48000):
        """
        Initialize MIDI 2.0 effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False
        
        # Effect instances
        self.effects: Dict[int, Any] = {}  # effect_id -> effect_instance
        self.active_effects: Set[int] = set()
        
        # Effect parameters with 32-bit resolution
        self.effect_parameters: Dict[int, Dict[str, float]] = {}  # effect_id -> param_name -> value
        self.per_note_effect_parameters: Dict[int, Dict[int, Dict[str, float]]] = {}  # note -> effect_id -> param_name -> value
        
        # Effect routing
        self.send_levels: Dict[int, float] = {}  # effect_id -> send_level (0.0-1.0)
        self.return_levels: Dict[int, float] = {}  # effect_id -> return_level (0.0-1.0)
        self.pan_controls: Dict[int, float] = {}  # effect_id -> pan (-1.0 to 1.0)
        
        # Processing buffers
        self.audio_buffer = None
        self.processing_buffer = None
        
        # Initialize default effects
        self._initialize_default_effects()
    
    def _initialize_default_effects(self):
        """Initialize default effects with MIDI 2.0 parameter resolution."""
        # Create default reverb effect with 32-bit parameters
        reverb_id = self.create_effect(MIDI2EffectType.REVERB_HALL_32BIT)
        if reverb_id is not None:
            # Set default parameters with high resolution
            self.set_effect_parameter(reverb_id, 'size', 0.8, resolution_bits=32)
            self.set_effect_parameter(reverb_id, 'time', 2.5, resolution_bits=32)
            self.set_effect_parameter(reverb_id, 'damping', 0.5, resolution_bits=32)
            self.set_effect_parameter(reverb_id, 'early_reflection', 0.7, resolution_bits=32)
            self.set_effect_parameter(reverb_id, 'diffusion', 0.8, resolution_bits=32)
            self.set_effect_parameter(reverb_id, 'density', 0.6, resolution_bits=32)
            self.enable_effect(reverb_id)
        
        # Create default chorus effect
        chorus_id = self.create_effect(MIDI2EffectType.CHORUS_STANDARD_32BIT)
        if chorus_id is not None:
            self.set_effect_parameter(chorus_id, 'rate', 1.2, resolution_bits=32)
            self.set_effect_parameter(chorus_id, 'depth', 0.4, resolution_bits=32)
            self.set_effect_parameter(chorus_id, 'feedback', 0.3, resolution_bits=32)
            self.set_effect_parameter(chorus_id, 'delay', 0.007, resolution_bits=32)
            self.enable_effect(chorus_id)
    
    def create_effect(self, effect_type: MIDI2EffectType, effect_id: Optional[int] = None) -> Optional[int]:
        """
        Create a new effect instance with MIDI 2.0 capabilities.

        Args:
            effect_type: Type of effect to create
            effect_id: Optional specific ID for the effect

        Returns:
            Effect ID or None if creation failed
        """
        if effect_id is None:
            effect_id = len(self.effects)
        
        # Create effect based on type
        if effect_type in [MIDI2EffectType.REVERB_HALL_32BIT, MIDI2EffectType.REVERB_ROOM_32BIT, 
                          MIDI2EffectType.REVERB_PLATE_32BIT, MIDI2EffectType.REVERB_CHAMBER_32BIT,
                          MIDI2EffectType.REVERB_SPRING_32BIT, MIDI2EffectType.REVERB_CONVOLUTION_32BIT]:
            from .reverb import ReverbEffect
            effect_instance = ReverbEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.CHORUS_STANDARD_32BIT, MIDI2EffectType.CHORUS_FLANGER_32BIT,
                            MIDI2EffectType.CHORUS_CELESTE_32BIT, MIDI2EffectType.CHORUS_DIMENSION_32BIT,
                            MIDI2EffectType.CHORUS_ENSEMBLE_32BIT]:
            from .chorus import ChorusEffect
            effect_instance = ChorusEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.DELAY_STEREO_32BIT, MIDI2EffectType.DELAY_MULTI_TAP_32BIT,
                            MIDI2EffectType.DELAY_CROSS_32BIT, MIDI2EffectType.DELAY_MODULATED_32BIT,
                            MIDI2EffectType.DELAY_ANALOG_32BIT, MIDI2EffectType.DELAY_DIGITAL_32BIT]:
            from .delay import DelayEffect
            effect_instance = DelayEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.FILTER_LOW_PASS_32BIT, MIDI2EffectType.FILTER_HIGH_PASS_32BIT,
                            MIDI2EffectType.FILTER_BAND_PASS_32BIT, MIDI2EffectType.FILTER_NOTCH_32BIT,
                            MIDI2EffectType.FILTER_ALL_PASS_32BIT, MIDI2EffectType.FILTER_FORMANT_32BIT,
                            MIDI2EffectType.FILTER_STATE_VARIABLE_32BIT, MIDI2EffectType.FILTER_RESONANT_32BIT]:
            from .filter import FilterEffect
            effect_instance = FilterEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.MODULATION_TREMOLO_32BIT, MIDI2EffectType.MODULATION_VIBRATO_32BIT,
                            MIDI2EffectType.MODULATION_AUTO_PANNER_32BIT, MIDI2EffectType.MODULATION_PHASER_32BIT,
                            MIDI2EffectType.MODULATION_FLANGER_32BIT, MIDI2EffectType.MODULATION_ROTARY_SPEAKER_32BIT]:
            from .modulation import ModulationEffect
            effect_instance = ModulationEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.DYNAMICS_COMPRESSOR_32BIT, MIDI2EffectType.DYNAMICS_LIMITER_32BIT,
                            MIDI2EffectType.DYNAMICS_EXPANDER_32BIT, MIDI2EffectType.DYNAMICS_GATE_32BIT]:
            from .dynamics import DynamicsEffect
            effect_instance = DynamicsEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.DISTORTION_SOFT_CLIP_32BIT, MIDI2EffectType.DISTORTION_HARD_CLIP_32BIT,
                            MIDI2EffectType.DISTORTION_FUZZ_32BIT, MIDI2EffectType.DISTORTION_OVERDRIVE_32BIT,
                            MIDI2EffectType.DISTORTION_AMP_SIMULATOR_32BIT]:
            from .distortion import DistortionEffect
            effect_instance = DistortionEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.EQ_PARAMETRIC_32BIT, MIDI2EffectType.EQ_GRAPHIC_32BIT,
                            MIDI2EffectType.EQ_SHELVING_32BIT, MIDI2EffectType.EQ_HIGH_PASS_32BIT]:
            from .eq import EQEffect
            effect_instance = EQEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.PITCH_SHIFTER_32BIT, MIDI2EffectType.HARMONIZER_32BIT,
                            MIDI2EffectType.VOCODER_32BIT, MIDI2EffectType.RING_MODULATOR_32BIT]:
            from .pitch import PitchEffect
            effect_instance = PitchEffect(self.sample_rate, effect_type=effect_type.name)
        else:
            # For per-note effects and other specialized effects
            effect_instance = self._create_specialized_effect(effect_type)
        
        if effect_instance:
            self.effects[effect_id] = effect_instance
            self.effect_parameters[effect_id] = {}
            self.send_levels[effect_id] = 0.0
            self.return_levels[effect_id] = 1.0
            self.pan_controls[effect_id] = 0.0
            return effect_id
        
        return None
    
    def _create_specialized_effect(self, effect_type: MIDI2EffectType):
        """Create specialized effects that don't fit standard categories."""
        if effect_type in [MIDI2EffectType.PER_NOTE_REVERB_SEND_32BIT, MIDI2EffectType.PER_NOTE_CHORUS_SEND_32BIT,
                          MIDI2EffectType.PER_NOTE_DELAY_SEND_32BIT, MIDI2EffectType.PER_NOTE_DISTORTION_SEND_32BIT]:
            # These are routing effects that control per-note sends
            from .routing import PerNoteRoutingEffect
            return PerNoteRoutingEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.PER_NOTE_FILTER_CUTOFF_32BIT, MIDI2EffectType.PER_NOTE_FILTER_RESONANCE_32BIT,
                            MIDI2EffectType.PER_NOTE_PAN_32BIT, MIDI2EffectType.PER_NOTE_WIDTH_32BIT]:
            # These are per-note parameter control effects
            from .parameter_control import PerNoteParameterEffect
            return PerNoteParameterEffect(self.sample_rate, effect_type=effect_type.name)
        elif effect_type in [MIDI2EffectType.SPECTRAL_32BIT, MIDI2EffectType.CONVOLUTION_REVERB_32BIT]:
            # Advanced spectral effects
            from .spectral import SpectralEffect
            return SpectralEffect(self.sample_rate, effect_type=effect_type.name)
        else:
            # Default effect for unrecognized types
            from .basic import BasicEffect
            return BasicEffect(self.sample_rate, effect_type=effect_type.name)
    
    def enable_effect(self, effect_id: int) -> bool:
        """
        Enable an effect.

        Args:
            effect_id: ID of effect to enable

        Returns:
            True if effect was enabled
        """
        if effect_id in self.effects:
            self.active_effects.add(effect_id)
            return True
        return False
    
    def disable_effect(self, effect_id: int) -> bool:
        """
        Disable an effect.

        Args:
            effect_id: ID of effect to disable

        Returns:
            True if effect was disabled
        """
        if effect_id in self.active_effects:
            self.active_effects.remove(effect_id)
            return True
        return False
    
    def set_effect_parameter(self, effect_id: int, param_name: str, value: float, 
                           resolution_bits: int = 32, note: Optional[int] = None):
        """
        Set an effect parameter with specified resolution.

        Args:
            effect_id: Effect ID
            param_name: Parameter name
            value: Parameter value (0.0-1.0 normalized)
            resolution_bits: Parameter resolution (7, 14, 32, or 64)
            note: Optional note number for per-note parameters
        """
        if note is not None:
            # Per-note parameter
            if note not in self.per_note_effect_parameters:
                self.per_note_effect_parameters[note] = {}
            if effect_id not in self.per_note_effect_parameters[note]:
                self.per_note_effect_parameters[note][effect_id] = {}
            
            # Normalize value to parameter range based on resolution
            if resolution_bits == 7:
                # 7-bit: 0-127
                normalized_value = max(0.0, min(1.0, value))
            elif resolution_bits == 14:
                # 14-bit: 0-16383
                normalized_value = max(0.0, min(1.0, value))
            elif resolution_bits == 32:
                # 32-bit: 0-4294967295, but we use 0.0-1.0 range for internal processing
                normalized_value = max(0.0, min(1.0, value))
            else:
                # Default to 32-bit
                normalized_value = max(0.0, min(1.0, value))
            
            self.per_note_effect_parameters[note][effect_id][param_name] = normalized_value
        else:
            # Global parameter
            if effect_id in self.effect_parameters:
                # Normalize value based on resolution
                if resolution_bits == 7:
                    normalized_value = max(0.0, min(1.0, value))
                elif resolution_bits == 14:
                    normalized_value = max(0.0, min(1.0, value))
                elif resolution_bits == 32:
                    normalized_value = max(0.0, min(1.0, value))
                else:
                    normalized_value = max(0.0, min(1.0, value))
                
                self.effect_parameters[effect_id][param_name] = normalized_value
                
                # Update the actual effect parameter if it has a method for that
                effect = self.effects.get(effect_id)
                if effect and hasattr(effect, 'set_parameter'):
                    effect.set_parameter(param_name, normalized_value)
    
    def get_effect_parameter(self, effect_id: int, param_name: str, note: Optional[int] = None) -> float:
        """
        Get an effect parameter value.

        Args:
            effect_id: Effect ID
            param_name: Parameter name
            note: Optional note number for per-note parameters

        Returns:
            Parameter value (0.0-1.0)
        """
        if note is not None:
            # Per-note parameter
            return self.per_note_effect_parameters.get(note, {}).get(effect_id, {}).get(param_name, 0.0)
        else:
            # Global parameter
            return self.effect_parameters.get(effect_id, {}).get(param_name, 0.0)
    
    def set_send_level(self, effect_id: int, level: float):
        """
        Set the send level for an effect.

        Args:
            effect_id: Effect ID
            level: Send level (0.0-1.0)
        """
        self.send_levels[effect_id] = max(0.0, min(1.0, level))
    
    def set_return_level(self, effect_id: int, level: float):
        """
        Set the return level for an effect.

        Args:
            effect_id: Effect ID
            level: Return level (0.0-1.0)
        """
        self.return_levels[effect_id] = max(0.0, min(1.0, level))
    
    def set_effect_pan(self, effect_id: int, pan: float):
        """
        Set the pan position for an effect.

        Args:
            effect_id: Effect ID
            pan: Pan position (-1.0 to 1.0, 0.0 = center)
        """
        self.pan_controls[effect_id] = max(-1.0, min(1.0, pan))
    
    def process_audio(self, audio_input: np.ndarray, note: Optional[int] = None) -> np.ndarray:
        """
        Process audio through active effects with MIDI 2.0 parameter resolution.

        Args:
            audio_input: Input audio as numpy array (samples, channels)
            note: Optional note number for per-note processing

        Returns:
            Processed audio as numpy array
        """
        if not self.enabled or not self.active_effects:
            return audio_input.copy()
        
        # Start with input audio
        processed_audio = audio_input.copy()
        
        # Process through each active effect
        for effect_id in self.active_effects:
            effect = self.effects.get(effect_id)
            if effect:
                # Get per-note parameters if available
                if note is not None and note in self.per_note_effect_parameters:
                    per_note_params = self.per_note_effect_parameters[note].get(effect_id, {})
                    # Apply per-note parameters to the effect
                    for param_name, param_value in per_note_params.items():
                        if hasattr(effect, 'set_parameter'):
                            effect.set_parameter(param_name, param_value)
                
                # Process audio with the effect
                if hasattr(effect, 'process_audio'):
                    processed_audio = effect.process_audio(processed_audio)
        
        return processed_audio
    
    def process_midi_control(self, controller: int, value: int, channel: int = 0, 
                           resolution_bits: int = 32, note: Optional[int] = None):
        """
        Process MIDI control change for effect parameter control.

        Args:
            controller: MIDI controller number
            value: Controller value
            channel: MIDI channel
            resolution_bits: Controller resolution
            note: Optional note number for per-note controllers
        """
        # Convert controller value to normalized 0.0-1.0 range based on resolution
        if resolution_bits == 7:
            normalized_value = value / 127.0
        elif resolution_bits == 14:
            normalized_value = value / 16383.0
        elif resolution_bits == 32:
            # For MIDI 2.0, we have 32-bit values but we'll normalize to 0.0-1.0 for internal use
            normalized_value = min(1.0, max(0.0, value / 4294967295.0))
        else:
            normalized_value = value / 127.0  # Default to 7-bit
        
        # Map common controllers to effect parameters
        if controller == 91:  # Reverb send
            for effect_id in self.active_effects:
                effect_type = getattr(self.effects.get(effect_id), 'effect_type', '')
                if 'reverb' in effect_type.lower():
                    self.set_send_level(effect_id, normalized_value)
        elif controller == 93:  # Chorus send
            for effect_id in self.active_effects:
                effect_type = getattr(self.effects.get(effect_id), 'effect_type', '')
                if 'chorus' in effect_type.lower():
                    self.set_send_level(effect_id, normalized_value)
        elif controller == 94:  # Variation send (XG)
            for effect_id in self.active_effects:
                effect_type = getattr(self.effects.get(effect_id), 'effect_type', '')
                if 'delay' in effect_type.lower() or 'modulation' in effect_type.lower():
                    self.set_send_level(effect_id, normalized_value)
        # Add more controller mappings as needed
    
    def get_effect_info(self, effect_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about an effect.

        Args:
            effect_id: Effect ID

        Returns:
            Dictionary with effect information or None
        """
        if effect_id in self.effects:
            effect = self.effects[effect_id]
            return {
                'id': effect_id,
                'type': getattr(effect, 'effect_type', 'unknown'),
                'enabled': effect_id in self.active_effects,
                'parameters': self.effect_parameters.get(effect_id, {}),
                'send_level': self.send_levels.get(effect_id, 0.0),
                'return_level': self.return_levels.get(effect_id, 1.0),
                'pan': self.pan_controls.get(effect_id, 0.0),
                'supports_32bit': True,
                'supports_per_note': getattr(effect, 'supports_per_note', False),
                'supports_mpe_plus': getattr(effect, 'supports_mpe_plus', False)
            }
        return None
    
    def get_all_effects_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all effects.

        Returns:
            List of effect information dictionaries
        """
        return [self.get_effect_info(eid) for eid in self.effects.keys() if self.get_effect_info(eid)]
    
    def reset_all_effects(self):
        """Reset all effects to default parameters."""
        for effect_id in self.effects:
            effect = self.effects[effect_id]
            if hasattr(effect, 'reset'):
                effect.reset()
            
            # Reset our parameter tracking
            self.effect_parameters[effect_id] = {}
            self.send_levels[effect_id] = 0.0
            self.return_levels[effect_id] = 1.0
            self.pan_controls[effect_id] = 0.0
        
        # Clear per-note parameters
        self.per_note_effect_parameters.clear()
    
    def bypass_all_effects(self, bypass: bool = True):
        """
        Bypass all effects.

        Args:
            bypass: True to bypass, False to enable
        """
        self.bypass = bypass
    
    def get_active_effect_count(self) -> int:
        """
        Get the number of active effects.

        Returns:
            Number of active effects
        """
        return len(self.active_effects)


class XGMIDI2EffectsProcessor(MIDI2EffectProcessor):
    """
    XG-specific MIDI 2.0 Effects Processor
    
    Extends the base MIDI 2.0 effects processor with XG-specific effects
    and parameter mappings that leverage 32-bit resolution.
    """
    
    def __init__(self, sample_rate: int = 48000):
        """
        Initialize XG MIDI 2.0 effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(sample_rate)
        
        # XG-specific effect IDs
        self.system_reverb_id = None
        self.system_chorus_id = None
        self.system_variation_id = None
        self.insertion_effects_ids = []
        
        # Initialize XG-specific effects
        self._initialize_xg_effects()
    
    def _initialize_xg_effects(self):
        """Initialize XG-specific effects with 32-bit parameter support."""
        # System reverb (XG has 40+ types)
        self.system_reverb_id = self.create_effect(MIDI2EffectType.REVERB_HALL_32BIT)
        if self.system_reverb_id is not None:
            # Set XG-specific defaults with high resolution
            self.set_effect_parameter(self.system_reverb_id, 'type', 0.0, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'time', 2.5, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'pre_delay', 0.02, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'early_reflection', 0.7, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'damping', 0.5, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'density', 0.6, resolution_bits=32)
            self.set_effect_parameter(self.system_reverb_id, 'diffusion', 0.8, resolution_bits=32)
            self.enable_effect(self.system_reverb_id)
        
        # System chorus (XG has 8 types)
        self.system_chorus_id = self.create_effect(MIDI2EffectType.CHORUS_STANDARD_32BIT)
        if self.system_chorus_id is not None:
            self.set_effect_parameter(self.system_chorus_id, 'type', 0.0, resolution_bits=32)
            self.set_effect_parameter(self.system_chorus_id, 'rate', 1.2, resolution_bits=32)
            self.set_effect_parameter(self.system_chorus_id, 'depth', 0.4, resolution_bits=32)
            self.set_effect_parameter(self.system_chorus_id, 'feedback', 0.3, resolution_bits=32)
            self.set_effect_parameter(self.system_chorus_id, 'delay', 0.007, resolution_bits=32)
            self.set_effect_parameter(self.system_chorus_id, 'pre_delay', 0.0, resolution_bits=32)
            self.enable_effect(self.system_chorus_id)
        
        # System variation (XG has 120+ types)
        self.system_variation_id = self.create_effect(MIDI2EffectType.DELAY_STEREO_32BIT)
        if self.system_variation_id is not None:
            self.set_effect_parameter(self.system_variation_id, 'type', 0.0, resolution_bits=32)
            self.set_effect_parameter(self.system_variation_id, 'time', 0.5, resolution_bits=32)
            self.set_effect_parameter(self.system_variation_id, 'feedback', 0.2, resolution_bits=32)
            self.set_effect_parameter(self.system_variation_id, 'high_freq_damp', 0.3, resolution_bits=32)
            self.enable_effect(self.system_variation_id)
    
    def set_xg_parameter(self, parameter_address: int, value: int, resolution_bits: int = 32):
        """
        Set an XG parameter with MIDI 2.0 resolution.

        Args:
            parameter_address: XG parameter address (as used in NRPN)
            value: Parameter value
            resolution_bits: Parameter resolution
        """
        # Convert to normalized value based on resolution
        if resolution_bits == 7:
            normalized_value = value / 127.0
        elif resolution_bits == 14:
            normalized_value = value / 16383.0
        elif resolution_bits == 32:
            normalized_value = min(1.0, max(0.0, value / 4294967295.0))
        else:
            normalized_value = value / 127.0
        
        # Map XG parameter addresses to effect parameters
        # System reverb parameters (addresses 0x000000 - 0x0000FF)
        if 0x000000 <= parameter_address <= 0x0000FF:
            if self.system_reverb_id is not None:
                self._set_xg_reverb_parameter(parameter_address, normalized_value)
        
        # System chorus parameters (addresses 0x000100 - 0x0001FF)
        elif 0x000100 <= parameter_address <= 0x0001FF:
            if self.system_chorus_id is not None:
                self._set_xg_chorus_parameter(parameter_address, normalized_value)
        
        # System variation parameters (addresses 0x000200 - 0x0002FF)
        elif 0x000200 <= parameter_address <= 0x0002FF:
            if self.system_variation_id is not None:
                self._set_xg_variation_parameter(parameter_address, normalized_value)
        
        # Insertion effects parameters (addresses 0x000400 - 0x0004FF)
        elif 0x000400 <= parameter_address <= 0x0004FF:
            self._set_xg_insertion_parameter(parameter_address, normalized_value)
    
    def _set_xg_reverb_parameter(self, address: int, value: float):
        """Set XG system reverb parameter."""
        # XG reverb parameters mapping
        if address == 0x000000:  # REV TYPE
            self.set_effect_parameter(self.system_reverb_id, 'type', value, resolution_bits=32)
        elif address == 0x000001:  # REV TIME
            self.set_effect_parameter(self.system_reverb_id, 'time', value * 10.0, resolution_bits=32)  # Scale to 0-10s
        elif address == 0x000002:  # REV PRE-DELAY TIME
            self.set_effect_parameter(self.system_reverb_id, 'pre_delay', value * 0.5, resolution_bits=32)  # Scale to 0-0.5s
        elif address == 0x000003:  # REV PRE-DELAY FEED
            self.set_effect_parameter(self.system_reverb_id, 'pre_delay_feedback', value, resolution_bits=32)
        elif address == 0x000004:  # REV ER LEVEL
            self.set_effect_parameter(self.system_reverb_id, 'early_reflection_level', value, resolution_bits=32)
        elif address == 0x000005:  # REV HF DAMP
            self.set_effect_parameter(self.system_reverb_id, 'damping', value, resolution_bits=32)
        # Add more reverb parameters as needed
    
    def _set_xg_chorus_parameter(self, address: int, value: float):
        """Set XG system chorus parameter."""
        # XG chorus parameters mapping
        if address == 0x000100:  # CHO TYPE
            self.set_effect_parameter(self.system_chorus_id, 'type', value, resolution_bits=32)
        elif address == 0x000101:  # CHO PRE-LPF
            self.set_effect_parameter(self.system_chorus_id, 'pre_lpf', value, resolution_bits=32)
        elif address == 0x000102:  # CHO LEVEL
            self.set_effect_parameter(self.system_chorus_id, 'level', value, resolution_bits=32)
        elif address == 0x000103:  # CHO FEEDBACK
            self.set_effect_parameter(self.system_chorus_id, 'feedback', value, resolution_bits=32)
        elif address == 0x000104:  # CHO PRE-DELAY
            self.set_effect_parameter(self.system_chorus_id, 'pre_delay', value * 0.1, resolution_bits=32)  # Scale to 0-0.1s
        elif address == 0x000105:  # CHO RATE
            self.set_effect_parameter(self.system_chorus_id, 'rate', value * 10.0, resolution_bits=32)  # Scale to 0-10 Hz
        elif address == 0x000106:  # CHO DEPTH
            self.set_effect_parameter(self.system_chorus_id, 'depth', value, resolution_bits=32)
        elif address == 0x000107:  # CHO SEND TO RVB
            self.set_send_level(self.system_chorus_id, value)
        # Add more chorus parameters as needed
    
    def _set_xg_variation_parameter(self, address: int, value: float):
        """Set XG system variation parameter."""
        # XG variation parameters mapping
        if address == 0x000200:  # VAR TYPE
            self.set_effect_parameter(self.system_variation_id, 'type', value, resolution_bits=32)
        elif address == 0x000201:  # VAR CHORUS SEND
            self.set_send_level(self.system_variation_id, value)
        elif address == 0x000202:  # VAR RVB SEND
            if self.system_reverb_id:
                self.set_send_level(self.system_reverb_id, value)
        # Add more variation parameters as needed
    
    def _set_xg_insertion_parameter(self, address: int, value: float):
        """Set XG insertion effect parameter."""
        # For now, just store the parameter - insertion effects would be implemented separately
        insertion_effect_id = (address >> 8) & 0xFF  # Extract effect number from address
        parameter_num = address & 0xFF  # Extract parameter number
        
        # This would map to specific insertion effect parameters
        # Implementation would depend on which insertion effect is active
        pass
    
    def process_xg_sysex(self, data: List[int]) -> bool:
        """
        Process XG System Exclusive messages for effects control.

        Args:
            data: SYSEX data as list of integers

        Returns:
            True if message was handled
        """
        # Check if this is an XG SYSEX message (manufacturer ID 0x43 = Yamaha)
        if len(data) < 5 or data[0] != 0x43:  # Yamaha manufacturer ID
            return False
        
        # Check if this is an XG parameter change (model ID 0x4C = XG)
        if data[2] != 0x4C:  # XG model ID
            return False
        
        # Process XG parameter change messages
        if data[3] == 0x00:  # Parameter change
            if len(data) >= 7:
                # Extract parameter address and value
                addr_msb = data[4]
                addr_lsb = data[5]
                value = data[6]
                
                # Combine address bytes and process as XG parameter
                param_address = (addr_msb << 8) | addr_lsb
                self.set_xg_parameter(param_address, value, resolution_bits=7)  # 7-bit for SYSEX
                return True
        
        # Process XG bulk dump messages
        elif data[3] == 0x07:  # Bulk dump
            return self._process_xg_bulk_dump(data[4:])
        
        # Process XG data set messages
        elif data[3] == 0x08:  # Data set
            return self._process_xg_data_set(data[4:])
        
        return False
    
    def _process_xg_bulk_dump(self, data: List[int]) -> bool:
        """Process XG bulk dump data."""
        # XG bulk dump format: [address_msb, address_lsb, value_msb, value_lsb, ...]
        if len(data) < 4 or len(data) % 4 != 0:
            return False
        
        for i in range(0, len(data), 4):
            if i + 3 < len(data):
                addr_msb = data[i]
                addr_lsb = data[i+1]
                val_msb = data[i+2]
                val_lsb = data[i+3]
                
                # Combine to get 14-bit value
                value_14bit = (val_msb << 7) | val_lsb
                param_address = (addr_msb << 8) | addr_lsb
                
                # Process with 14-bit resolution
                self.set_xg_parameter(param_address, value_14bit, resolution_bits=14)
        
        return True
    
    def _process_xg_data_set(self, data: List[int]) -> bool:
        """Process XG data set message."""
        # XG data set format: [address_msb, address_lsb, value]
        if len(data) < 3:
            return False
        
        addr_msb = data[0]
        addr_lsb = data[1]
        value = data[2]
        
        param_address = (addr_msb << 8) | addr_lsb
        self.set_xg_parameter(param_address, value, resolution_bits=7)  # 7-bit for data set
        return True


# Global instance
midi2_effects_processor = XGMIDI2EffectsProcessor()


def get_midi2_effects_processor() -> XGMIDI2EffectsProcessor:
    """
    Get the global MIDI 2.0 effects processor instance.

    Returns:
        XGMIDI2EffectsProcessor instance
    """
    return midi2_effects_processor