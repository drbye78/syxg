"""
SF2 wavetable synthesis engine for XG synthesizer.

Implements the SynthesisEngine interface for SoundFont 2 (SF2) wavetable synthesis,
providing sample playback with loop modes, pitch modulation, and filter envelopes.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np

from .synthesis_engine import SynthesisEngine
from ..partial.sf2_partial import SF2Partial
from ..sf2.manager import SF2Manager


class SF2Engine(SynthesisEngine):
    """
    SF2 wavetable synthesis engine.

    Provides SoundFont 2 compatible wavetable synthesis with:
    - Sample playback with loop modes
    - Real-time pitch modulation
    - ADSR envelopes for amplitude and filter
    - Key scaling and velocity sensitivity
    """

    def __init__(self, sf2_manager: Optional[SF2Manager] = None, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize SF2 synthesis engine.

        Args:
            sf2_manager: SoundFont manager instance (created if None)
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.sf2_manager = sf2_manager or SF2Manager()
        self._engine_info = None

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return 'sf2'

    def create_partial(self, partial_params: Dict, sample_rate: int) -> SF2Partial:
        """
        Create an SF2 partial.

        Args:
            partial_params: SF2-specific partial parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            SF2Partial instance
        """
        return SF2Partial(partial_params, sample_rate, self.sf2_manager)

    def get_voice_parameters(self, program: int, bank: int = 0) -> Optional[Dict]:
        """
        Get SF2 voice parameters for a program/bank.

        Uses existing SF2Manager interface to get program parameters.
        """
        if self.sf2_manager:
            params = self.sf2_manager.get_program_parameters(program, bank)
            return params if params else self._get_default_voice_params()
        return self._get_default_voice_params()

    def supports_feature(self, feature: str) -> bool:
        """Check SF2 engine feature support."""
        sf2_features = {
            'loop_modes': True,           # SF2 supports forward/backward/alternating loops
            'sample_playback': True,      # Core SF2 functionality
            'filter_envelopes': True,     # SF2 modulation envelope
            'pitch_envelopes': True,      # SF2 modulation envelope can be used for pitch
            'fm_synthesis': False,        # Not supported
            'physical_modeling': False,   # Not supported
            'granular_synthesis': False,  # Not supported
            'wavetable_synthesis': True,  # Core SF2 functionality
            'subtractive_synthesis': True # Filters and envelopes
        }
        return sf2_features.get(feature, False)

    def get_default_partial_params(self) -> Dict:
        """Get default SF2 partial parameters."""
        return {
            'level': 1.0,
            'pan': 0.0,
            'coarse_tune': 0,
            'fine_tune': 0,
            'scale_tuning': 100,
            'overriding_root_key': -1,
            'key_range_low': 0,
            'key_range_high': 127,
            'velocity_range_low': 0,
            'velocity_range_high': 127,
            'filter_cutoff': 1000.0,
            'filter_resonance': 0.7,
            'filter_type': 'lowpass',
            'filter_key_follow': 0.5,
            'use_filter_env': True,
            'filter_attack': 0.1,
            'filter_decay': 0.5,
            'filter_sustain': 0.6,
            'filter_release': 0.8,
            'use_pitch_env': False,
            'pitch_attack': 0.05,
            'pitch_decay': 0.1,
            'pitch_sustain': 0.0,
            'pitch_release': 0.05,
            'pitch_envelope_depth': 1200.0,
            'amp_attack': 0.01,
            'amp_decay': 0.3,
            'amp_sustain': 0.7,
            'amp_release': 0.5,
            'amp_delay': 0.0,
            'amp_hold': 0.0
        }

    def _get_default_voice_params(self) -> Dict:
        """Get default XG voice parameters."""
        return {
            'name': 'Default SF2 Voice',
            'key_range_low': 0,
            'key_range_high': 127,
            'master_level': 1.0,
            'pan': 0.0,
            'assign_mode': 1,  # Polyphonic
            'partials': [self.get_default_partial_params()]
        }

    def get_engine_info(self) -> Dict[str, Any]:
        """Get SF2 engine information."""
        if self._engine_info is None:
            self._engine_info = {
                'name': 'SF2 Wavetable Engine',
                'type': 'sf2',
                'capabilities': ['wavetable_synthesis', 'sample_playback', 'loop_modes', 'filter_envelopes', 'pitch_envelopes'],
                'formats': ['.sf2'],
                'polyphony': 64,
                'parameters': ['level', 'pan', 'coarse_tune', 'fine_tune', 'filter_cutoff', 'filter_resonance']
            }
        return self._engine_info

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float], block_size: int) -> np.ndarray:
        """
        Generate audio samples for a note using SF2 synthesis.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Create a temporary partial for this note
        partial_params = self.get_default_partial_params()
        partial_params['note'] = note
        partial_params['velocity'] = velocity

        partial = self.create_partial(partial_params, self.sample_rate)
        partial.note_on(velocity, note)

        # Generate samples
        return partial.generate_samples(block_size, modulation)

    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by this engine.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if note can be played, False otherwise
        """
        # SF2 supports full MIDI note range
        return 0 <= note <= 127

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        return ['.sf2']

    def _get_supported_features(self) -> list[str]:
        """Get list of supported features."""
        return ['wavetable_synthesis', 'sample_playback', 'loop_modes', 'filter_envelopes', 'pitch_envelopes']
