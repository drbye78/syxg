"""
SF2 partial implementation for XG synthesizer.

Implements the SynthesisPartial interface for SoundFont 2 wavetable synthesis,
wrapping the existing XGPartialGenerator functionality.
"""

from typing import Dict, Any, List
import numpy as np

from .partial import SynthesisPartial
# Import XGPartialGenerator dynamically to avoid circular imports
import importlib
from ..sf2.conversion.modulation_converter import AdvancedModulationProcessor


class SF2Partial(SynthesisPartial):
    """
    SF2 wavetable synthesis partial.

    Wraps XGPartialGenerator to provide SF2-compatible wavetable synthesis
    with sample playback, loop modes, and real-time modulation.
    """

    def __init__(self, params: Dict, sample_rate: int, sf2_manager):
        """
        Initialize SF2 partial.

        Args:
            params: SF2 partial parameters
            sample_rate: Audio sample rate in Hz
            sf2_manager: SF2 manager instance
        """
        super().__init__(params, sample_rate)

        # Store SF2 manager reference
        self.sf2_manager = sf2_manager

        # Create advanced modulation processor
        self.modulation_processor = AdvancedModulationProcessor()

        # Create XG partial generator with adapted parameters
        self._create_xg_partial_generator()

    def _create_xg_partial_generator(self):
        """Create and configure XG partial generator."""
        # Import XGPartialGenerator dynamically to avoid circular imports
        partial_generator_module = importlib.import_module('synth.partial.partial_generator')
        XGPartialGenerator = partial_generator_module.XGPartialGenerator

        # Convert SF2 parameters to XG format
        xg_params = self._convert_sf2_params_to_xg(self.params)

        # Create a mock synth object with required pools for XGPartialGenerator
        # In the full voice architecture, this would be passed from the voice
        class MockSynth:
            def __init__(self):
                # Import pools dynamically to avoid circular imports
                from ..core.buffer_pool import XGBufferPool
                from ..core.envelope import EnvelopePool
                from ..core.filter import FilterPool
                from ..core.oscillator import OscillatorPool

                self.memory_pool = XGBufferPool(sample_rate=44100)
                self.envelope_pool = EnvelopePool()
                self.filter_pool = FilterPool()
                self.partial_lfo_pool = OscillatorPool()
                self.block_size = 1024  # Default block size

        mock_synth = MockSynth()

        # Create XG partial generator
        self.xg_partial = XGPartialGenerator(
            synth=mock_synth,  # Provide mock synth with pools
            note=self.params.get('note', 60),
            velocity=self.params.get('velocity', 64),
            program=self.params.get('program', 0),
            partial_id=self.params.get('partial_id', 0),
            partial_params=xg_params,
            is_drum=self.params.get('is_drum', False),
            sample_rate=self.sample_rate
        )

    def _convert_sf2_params_to_xg(self, sf2_params: Dict) -> Dict:
        """
        Convert SF2 partial parameters to XG format.

        Args:
            sf2_params: SF2 parameter dictionary

        Returns:
            XG parameter dictionary
        """
        # Most parameters can be passed through directly
        xg_params = sf2_params.copy()

        # Ensure required XG parameters exist
        xg_params.setdefault('element_type', 'normal')
        xg_params.setdefault('level', 1.0)
        xg_params.setdefault('pan', 0.0)
        xg_params.setdefault('key_range_low', 0)
        xg_params.setdefault('key_range_high', 127)
        xg_params.setdefault('velocity_range_low', 0)
        xg_params.setdefault('velocity_range_high', 127)

        # Envelope parameters
        xg_params.setdefault('amp_attack', 0.01)
        xg_params.setdefault('amp_decay', 0.3)
        xg_params.setdefault('amp_sustain', 0.7)
        xg_params.setdefault('amp_release', 0.5)
        xg_params.setdefault('amp_delay', 0.0)
        xg_params.setdefault('amp_hold', 0.0)

        # Filter parameters
        xg_params.setdefault('filter_cutoff', 1000.0)
        xg_params.setdefault('filter_resonance', 0.7)
        xg_params.setdefault('filter_type', 'lowpass')
        xg_params.setdefault('filter_key_follow', 0.5)

        # Pitch parameters
        xg_params.setdefault('coarse_tune', 0)
        xg_params.setdefault('fine_tune', 0)
        xg_params.setdefault('scale_tuning', 100)
        xg_params.setdefault('overriding_root_key', -1)

        return xg_params

    def generate_samples(self, block_size: int, modulation: Dict) -> np.ndarray:
        """
        Generate SF2 samples using XG partial generator.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Numpy array with stereo audio samples
        """
        if not self.active:
            return np.zeros(block_size * 2, dtype=np.float32)

        # Convert modulation dict to XG format
        global_pitch_mod = modulation.get('pitch', 0.0)
        velocity_crossfade = modulation.get('velocity_crossfade', 0.0)
        note_crossfade = modulation.get('note_crossfade', 0.0)

        # Create LFO instances from modulation - get LFOs from voice/channel
        lfos = self._get_lfo_instances()

        # Generate samples using XG partial
        left_block = np.zeros(block_size, dtype=np.float32)
        right_block = np.zeros(block_size, dtype=np.float32)

        self.xg_partial.generate_sample_block(
            block_size,
            left_block,
            right_block,
            lfos=lfos,  # Pass combined channel + note LFOs
            global_pitch_mod=global_pitch_mod,
            velocity_crossfade=velocity_crossfade,
            note_crossfade=note_crossfade
        )

        # Interleave left/right into single stereo array
        stereo_output = np.empty(block_size * 2, dtype=np.float32)
        stereo_output[0::2] = left_block
        stereo_output[1::2] = right_block

        return stereo_output

    def _get_lfo_instances(self) -> List:
        """
        Get LFO instances for modulation.

        Creates or retrieves LFO instances from the voice/channel architecture.
        In the voice architecture, LFOs are managed at the voice level and passed down.

        Returns:
            List of XGLFO instances for modulation
        """
        # For now, create basic LFO instances
        # In a full implementation, these would be passed from the voice/channel
        lfos = []

        # Create 3 basic LFOs (pitch, filter, amplitude)
        if hasattr(self, 'xg_partial') and self.xg_partial and hasattr(self.xg_partial, 'dedicated_lfos'):
            # Use dedicated LFOs from XG partial if available
            lfos = self.xg_partial.dedicated_lfos
        else:
            # Fallback: create basic LFOs (this should be improved)
            try:
                from synth.core.oscillator import XGLFO
                # Create basic LFOs for compatibility
                lfo1 = XGLFO(id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0)
                lfo1.set_modulation_routing(pitch=True, filter=False, amplitude=False)
                lfo1.set_modulation_depths(pitch_cents=50.0, filter_depth=0.0, amplitude_depth=0.0)

                lfo2 = XGLFO(id=1, waveform="triangle", rate=2.0, depth=0.3, delay=0.0)
                lfo2.set_modulation_routing(pitch=False, filter=True, amplitude=False)
                lfo2.set_modulation_depths(pitch_cents=0.0, filter_depth=0.3, amplitude_depth=0.0)

                lfo3 = XGLFO(id=2, waveform="sawtooth", rate=0.5, depth=0.1, delay=0.5)
                lfo3.set_modulation_routing(pitch=False, filter=False, amplitude=True)
                lfo3.set_modulation_depths(pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3)

                lfos = [lfo1, lfo2, lfo3]
            except Exception:
                # If LFO creation fails, return empty list (no modulation)
                lfos = []

        return lfos

    def is_active(self) -> bool:
        """
        Check if SF2 partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active and self.xg_partial.is_active()

    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        self.params['velocity'] = velocity
        self.params['note'] = note
        self.xg_partial.note_on(velocity, note)

    def note_off(self) -> None:
        """Handle note-off event."""
        self.xg_partial.note_off()

    def apply_modulation(self, modulation: Dict) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        # Update XG partial with new modulation values
        modulation_values = {
            'pitch_mod': modulation.get('pitch', 0.0),
            'filter_mod': modulation.get('filter_cutoff', 0.0),
            'amp_mod': modulation.get('amp', 1.0)
        }
        self.xg_partial.set_modulation_values(**modulation_values)

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        if hasattr(self, 'xg_partial'):
            self.xg_partial._reset_for_pool()

    def get_partial_info(self) -> Dict[str, Any]:
        """Get SF2 partial information."""
        info = super().get_partial_info()
        info.update({
            'engine_type': 'sf2',
            'sample_loaded': hasattr(self, 'xg_partial') and self.xg_partial._cached_sample_table is not None,
            'loop_mode': getattr(self.xg_partial, 'loop_mode', 0) if hasattr(self, 'xg_partial') else 0,
        })
        return info
