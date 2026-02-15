"""
S.Art2 (Super Articulation 2) Synthesizer Package.

A comprehensive implementation of Yamaha's S.Art2 technology with FM and 
Karplus-Strong synthesis, full MIDI/NRPN support, and real-time playback.

Package structure:
- synth: Main synthesizer class
- constants: Configuration and constants
- nrpn: NRPN mapping and MIDI utilities
- voice: Voice management
- effects: Reverb and delay effects
- audio: Audio output backend
"""

from .synth import SuperArticulation2Synthesizer
from .constants import (
    DEFAULT_SAMPLE_RATE,
    SynthConfig,
)
from .nrpn import YamahaNRPNMapper, midi_note_to_frequency
from .voice import VoiceManager, VoiceState, NoteEvent

__version__ = "2.0.0"

__all__ = [
    "SuperArticulation2Synthesizer",
    "YamahaNRPNMapper",
    "VoiceManager",
    "VoiceState",
    "NoteEvent",
    "SynthConfig",
    "midi_note_to_frequency",
    "DEFAULT_SAMPLE_RATE",
]
