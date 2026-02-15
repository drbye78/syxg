"""
Constants and configuration for S.Art2 synthesizer.
"""

# Musical constants
SEMITONE_RATIO = 1.059463359  # 2^(1/12)
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_BLOCK_SIZE = 512
DEFAULT_BUFFER_SIZE = 2048

# MIDI constants
MIDI_NOTE_MIN = 0
MIDI_NOTE_MAX = 127
MIDI_VELOCITY_MIN = 0
MIDI_VELOCITY_MAX = 127

# Standard MIDI CC Controllers
CC_BANK_SELECT_MSB = 0       # Bank Select (MSB)
CC_MODULATION = 1            # Modulation Wheel
CC_BREATH_CONTROLLER = 2     # Breath Controller (common on wind controllers)
CC_FOOT_CONTROLLER = 4       # Foot Controller (often volume/expression)
CC_PORTAMENTO_TIME = 5        # Portamento Time
CC_DATA_ENTRY_MSB = 6        # Data Entry (MSB)
CC_VOLUME = 7                # Channel Volume
CC_PAN = 10                  # Pan
CC_EXPRESSION = 11           # Expression (dynamics)
CC_BANK_SELECT_LSB = 32      # Bank Select (LSB)
CC_SUSTAIN = 64              # Damper Pedal (Sustain)
CC_PORTAMENTO = 65           # Portamento On/Off
CC_SOSTENUTO = 66            # Sustenuto (soft hold)
CC_SOFT_PEDAL = 67           # Soft Pedal
CC_RESONANCE_FILTER = 71     # Resonance (Filter)
CC_RELEASE_TIME = 72         # Release Time
CC_ATTACK_TIME = 73          # Attack Time
CC_CUTOFF_FILTER = 74        # Filter Cutoff (Brightness)
CC_DECAY_TIME = 75           # Decay Time
CC_VIBRATO_RATE = 76         # Vibrato Rate
CC_VIBRATO_DEPTH = 77        # Vibrato Depth
CC_VIBRATO_DELAY = 78        # Vibrato Delay
CC_DATA_ENTRY_LSB = 38       # Data Entry (LSB)
CC_LOCAL_ON_OFF = 127        # Local On/Off

# Common controller aliases
MOD_WHEEL_CONTROL = CC_MODULATION
PITCH_BEND_CONTROL = CC_VOLUME + 7  # MIDI pitch bend is often mapped near volume

# NRPN and RPN
NRPN_MSB_CONTROL = 99        # Non-Registered Parameter Number (MSB)
NRPN_LSB_CONTROL = 98        # Non-Registered Parameter Number (LSB)
RPN_MSB_CONTROL = 101        # Registered Parameter Number (MSB)
RPN_LSB_CONTROL = 100        # Registered Parameter Number (LSB)
RPN_PITCH_BEND_SENS = 0     # RPN: Pitch Bend Sensitivity
RPN_FINE_TUNING = 1         # RPN: Master Fine Tuning
RPN_COARSE_TUNING = 2        # RPN: Master Coarse Tuning
RPN_TUNING_PROGRAM = 3       # RPN: Tuning Program Change
RPN_TUNING_BANK = 4          # RPN: Tuning Bank Select
RPN_MODULATION_DEPTH = 5     # RPN: Modulation Depth

# Controller defaults
DEFAULT_PITCH_BEND_RANGE = 2  # Semitones
DEFAULT_PORTAMENTO_TIME = 0   # Off by default
DEFAULT_EXPRESSION = 127      # Full volume
DEFAULT_VIBRATO_DELAY = 0     # No delay

# Maximum polyphony
MAX_POLYPHONY = 64

# Optional dependencies
MIDO_AVAILABLE = False
try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    mido = None

SOUNDDEVICE_AVAILABLE = False
try:
    import sounddevice
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    sounddevice = None

PYAUDIO_AVAILABLE = False
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None


# =============================================================================
# Data Classes
# =============================================================================

from dataclasses import dataclass
from typing import Optional


@dataclass
class SynthConfig:
    """Global synthesizer configuration."""
    sample_rate: int = DEFAULT_SAMPLE_RATE
    block_size: int = DEFAULT_BLOCK_SIZE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    num_channels: int = 2  # Stereo
    master_volume: float = 0.8
    enable_reverb: bool = True
    enable_delay: bool = True
    reverb_room_size: float = 0.5
    reverb_wet_dry: float = 0.3
    delay_time: float = 0.375  # In seconds (eighth note at 120 BPM)
    delay_feedback: float = 0.3
    delay_wet_dry: float = 0.2
