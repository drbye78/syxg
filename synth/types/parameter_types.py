"""
Parameter types and protocols for the Modern XG Synthesizer.

This module defines the standardized parameter update protocol and types
used throughout the synthesizer architecture for hierarchical parameter routing.
"""

from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ParameterScope(Enum):
    """Parameter scope levels in the synthesizer hierarchy"""
    GLOBAL = "global"      # Affects entire synthesizer (reverb, master volume)
    CHANNEL = "channel"    # Affects specific MIDI channel (pan, volume, effects sends)
    VOICE = "voice"        # Affects specific note/voice (pitch bend, aftertouch)
    PARTIAL = "partial"    # Affects individual synthesis partial (filter, envelope)


class ParameterSource(Enum):
    """Source of parameter update"""
    NRPN = "nrpn"              # Non-Registered Parameter Number
    CONTROLLER = "controller"  # MIDI Controller (CC)
    SYSEX = "sysex"            # System Exclusive message
    INTERNAL = "internal"      # Internal synthesizer parameter
    XG_CHANNEL = "xg_channel"  # XG channel parameter
    AUTOMATION = "automation"  # DAW automation


@dataclass
class ParameterUpdate:
    """
    Standardized parameter update protocol for hierarchical routing.

    This structure is used throughout the synthesizer to ensure consistent
    parameter passing between architectural layers.
    """
    name: str                           # Parameter name (e.g., 'filter_cutoff', 'reverb_time')
    value: Union[float, int, str, bool] # Parameter value (pre-scaled to appropriate range)
    scope: ParameterScope              # Scope level (global/channel/voice/partial)
    channel: Optional[int]             # MIDI channel (0-15) for channel-scoped parameters
    source: ParameterSource            # Source of the parameter update
    metadata: Optional[Dict[str, Any]] = None  # Additional context information

    def __post_init__(self):
        """Validate parameter update after initialization"""
        if self.scope == ParameterScope.CHANNEL and self.channel is None:
            raise ValueError("Channel-scoped parameters must specify a channel")

        if self.scope == ParameterScope.GLOBAL and self.channel is not None:
            raise ValueError("Global-scoped parameters should not specify a channel")


# Parameter name constants for consistency
class ParameterNames:
    """Standardized parameter names used throughout the synthesizer"""

    # MIDI Controllers (converted to parameter names)
    MODULATION_WHEEL = "modulation_wheel"
    VOLUME = "volume"
    PAN = "pan"
    EXPRESSION = "expression"
    SUSTAIN_PEDAL = "sustain_pedal"
    PORTAMENTO = "portamento"
    PORTAMENTO_TIME = "portamento_time"
    Sostenuto = "sostenuto"
    SOFT_PEDAL = "soft_pedal"
    REVERB_SEND = "reverb_send"
    CHORUS_SEND = "chorus_send"
    VARIATION_SEND = "variation_send"

    # GM2 Controllers
    RELEASE_TIME = "release_time"
    ATTACK_TIME = "attack_time"
    BRIGHTNESS = "brightness"
    DECAY_TIME = "decay_time"
    VIBRATO_RATE = "vibrato_rate"
    VIBRATO_DEPTH = "vibrato_depth"
    VIBRATO_DELAY = "vibrato_delay"

    # Synth Parameters
    FILTER_CUTOFF = "filter_cutoff"
    FILTER_RESONANCE = "filter_resonance"
    FILTER_TYPE = "filter_type"
    FILTER_KEY_FOLLOW = "filter_key_follow"

    # Envelope Parameters
    AMPLITUDE_ATTACK = "amplitude_attack"
    AMPLITUDE_DECAY = "amplitude_decay"
    AMPLITUDE_SUSTAIN = "amplitude_sustain"
    AMPLITUDE_RELEASE = "amplitude_release"

    FILTER_ATTACK = "filter_attack"
    FILTER_DECAY = "filter_decay"
    FILTER_SUSTAIN = "filter_sustain"
    FILTER_RELEASE = "filter_release"

    PITCH_ATTACK = "pitch_attack"
    PITCH_DECAY = "pitch_decay"
    PITCH_SUSTAIN = "pitch_sustain"
    PITCH_RELEASE = "pitch_release"

    LFO_ATTACK = "lfo_attack"
    LFO_DECAY = "lfo_decay"
    LFO_SUSTAIN = "lfo_sustain"
    LFO_RELEASE = "lfo_release"

    # LFO Parameters
    LFO_RATE = "lfo_rate"
    LFO_DEPTH = "lfo_depth"
    LFO_WAVEFORM = "lfo_waveform"
    LFO_SYNC = "lfo_sync"
    LFO_PHASE = "lfo_phase"

    # Oscillator Parameters
    OSC_WAVEFORM = "osc_waveform"
    OSC_COARSE_TUNE = "osc_coarse_tune"
    OSC_FINE_TUNE = "osc_fine_tune"
    OSC_LEVEL = "osc_level"
    OSC_ROUTING = "osc_routing"

    # Effects Parameters
    REVERB_TIME = "reverb_time"
    REVERB_HF_DAMP = "reverb_hf_damp"
    REVERB_PREDELAY = "reverb_predelay"
    REVERB_TYPE = "reverb_type"

    CHORUS_RATE = "chorus_rate"
    CHORUS_DEPTH = "chorus_depth"
    CHORUS_FEEDBACK = "chorus_feedback"
    EFFECT_TYPE = "effect_type"

    DISTORTION_DRIVE = "distortion_drive"
    DISTORTION_TONE = "distortion_tone"
    DISTORTION_MIX = "distortion_mix"
    DISTORTION_TYPE = "distortion_type"

    # XG Channel Parameters
    PART_LEVEL = "part_level"
    PART_PAN = "part_pan"
    PART_COARSE_TUNE = "part_coarse_tune"
    PART_FINE_TUNE = "part_fine_tune"
    PART_CUTOFF = "part_cutoff"
    PART_RESONANCE = "part_resonance"
    DRUM_KIT = "drum_kit"

    # Global Parameters
    MASTER_VOLUME = "master_volume"
    MASTER_PAN = "master_pan"
    MASTER_TUNE = "master_tune"
    MASTER_TRANSPOSE = "master_transpose"

    # Advanced Parameters
    ARPEGGIATOR_PATTERN = "arpeggiator_pattern"
    ARPEGGIATOR_TEMPO = "arpeggiator_tempo"
    ARPEGGIATOR_OCTAVE_RANGE = "arpeggiator_octave_range"
    ARPEGGIATOR_GATE_TIME = "arpeggiator_gate_time"

    SEQUENCER_LENGTH = "sequencer_length"
    SEQUENCER_TEMPO = "sequencer_tempo"

    MOTION_LENGTH = "motion_length"
    MOTION_SMOOTH = "motion_smooth"
    MOTION_CURVE = "motion_curve"

    # XG System Parameters
    XG_REVERB_TYPE = "xg_reverb_type"
    XG_CHORUS_TYPE = "xg_chorus_type"
    XG_VARIATION_TYPE = "xg_variation_type"
    XG_TEMPERAMENT = "xg_temperament"
    XG_COMPATIBILITY_MODE = "xg_compatibility_mode"


# Parameter range definitions for validation
PARAMETER_RANGES = {
    # Volume/Pan/Level parameters (0.0-1.0)
    ParameterNames.VOLUME: (0.0, 1.0),
    ParameterNames.PART_LEVEL: (0.0, 1.0),
    ParameterNames.MASTER_VOLUME: (0.0, 1.0),
    ParameterNames.EXPRESSION: (0.0, 1.0),
    ParameterNames.REVERB_SEND: (0.0, 1.0),
    ParameterNames.CHORUS_SEND: (0.0, 1.0),
    ParameterNames.VARIATION_SEND: (0.0, 1.0),

    # Bipolar parameters (-1.0 to +1.0)
    ParameterNames.PAN: (-1.0, 1.0),
    ParameterNames.PART_PAN: (-1.0, 1.0),
    ParameterNames.MASTER_PAN: (-1.0, 1.0),

    # Frequency parameters (20Hz-20kHz)
    ParameterNames.FILTER_CUTOFF: (20.0, 20000.0),

    # Resonance (0.0-4.0)
    ParameterNames.FILTER_RESONANCE: (0.0, 4.0),

    # Time parameters (various ranges)
    ParameterNames.AMPLITUDE_ATTACK: (0.001, 10.0),
    ParameterNames.AMPLITUDE_DECAY: (0.01, 30.0),
    ParameterNames.AMPLITUDE_SUSTAIN: (0.0, 1.0),
    ParameterNames.AMPLITUDE_RELEASE: (0.01, 30.0),

    # LFO Rate (0.1Hz-50Hz)
    ParameterNames.LFO_RATE: (0.1, 50.0),

    # LFO Depth (0.0-1.0)
    ParameterNames.LFO_DEPTH: (0.0, 1.0),

    # Tuning (±24 semitones, ±100 cents)
    ParameterNames.OSC_COARSE_TUNE: (-24, 24),
    ParameterNames.OSC_FINE_TUNE: (-100, 100),
    ParameterNames.PART_COARSE_TUNE: (-24, 24),
    ParameterNames.PART_FINE_TUNE: (-100, 100),
}


def validate_parameter_update(update: ParameterUpdate) -> bool:
    """
    Validate a parameter update against defined ranges and constraints.

    Args:
        update: Parameter update to validate

    Returns:
        True if valid, False otherwise
    """
    # Check scope/channel consistency
    if update.scope == ParameterScope.CHANNEL and update.channel is None:
        return False
    if update.scope == ParameterScope.GLOBAL and update.channel is not None:
        return False

    # Check parameter range if defined
    if update.name in PARAMETER_RANGES:
        min_val, max_val = PARAMETER_RANGES[update.name]
        if not (min_val <= update.value <= max_val):
            return False

    return True


def create_parameter_update(
    name: str,
    value: Union[float, int, str, bool],
    scope: ParameterScope,
    source: ParameterSource,
    channel: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ParameterUpdate:
    """
    Factory function to create validated ParameterUpdate instances.

    Args:
        name: Parameter name
        value: Parameter value
        scope: Parameter scope
        source: Parameter source
        channel: MIDI channel (required for channel scope)
        metadata: Additional metadata

    Returns:
        Validated ParameterUpdate instance

    Raises:
        ValueError: If parameter validation fails
    """
    update = ParameterUpdate(
        name=name,
        value=value,
        scope=scope,
        channel=channel,
        source=source,
        metadata=metadata
    )

    if not validate_parameter_update(update):
        raise ValueError(f"Invalid parameter update: {update}")

    return update
