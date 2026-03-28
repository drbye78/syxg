"""
Test Utilities for XG Synthesizer Test Suite

Provides helper functions for audio testing, MIDI processing, and test data generation.
"""

from .audio_utils import (
    calculate_rms,
    compare_audio_buffers,
    detect_clipping,
    generate_test_frequency,
    generate_white_noise,
    apply_window,
    calculate_snr,
    calculate_thd,
)
from .midi_utils import (
    create_note_on_message,
    create_note_off_message,
    create_control_change_message,
    create_program_change_message,
    create_pitch_bend_message,
    create_sysex_message,
)
from .test_data_generator import (
    generate_sf2_test_data,
    generate_midi_test_sequence,
    generate_reference_audio,
)

__all__ = [
    # Audio utilities
    "calculate_rms",
    "compare_audio_buffers",
    "detect_clipping",
    "generate_test_frequency",
    "generate_white_noise",
    "apply_window",
    "calculate_snr",
    "calculate_thd",
    # MIDI utilities
    "create_note_on_message",
    "create_note_off_message",
    "create_control_change_message",
    "create_program_change_message",
    "create_pitch_bend_message",
    "create_sysex_message",
    # Test data generators
    "generate_sf2_test_data",
    "generate_midi_test_sequence",
    "generate_reference_audio",
]