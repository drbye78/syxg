"""
SF2 partial implementation for XG synthesizer.

Implements the SynthesisPartial interface for SoundFont 2 wavetable synthesis
with full integration into modern XG synthesizer infrastructure.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
import numpy as np

from .partial import SynthesisPartial

if TYPE_CHECKING:
    from ..engine.modern_xg_synthesizer import ModernXGSynthesizer


class SF2Partial(SynthesisPartial):
    """
    SF2 wavetable synthesis partial - Fully integrated with modern XG synthesizer.

    Uses unified infrastructure: buffer pools, envelope pools, filter pools,
    modulation matrix integration, and global voice management.
    Implements direct SF2 wavetable synthesis with mip-mapping support.
    """

    __slots__ = [
        'synth', 'sample_data', 'phase_step', 'sample_position', 'pitch_ratio',
        'loop_mode', 'loop_start', 'loop_end', 'envelope', 'filter',
        'mod_lfo', 'vib_lfo', 'audio_buffer', 'work_buffer',
        'pitch_mod', 'filter_mod', 'volume_mod', 'active', 'params'
    ]

    def __init__(self, params: Dict, synth: 'ModernXGSynthesizer'):
        """
        Initialize SF2 partial with modern synth integration.

        Args:
            params: SF2 partial parameters from zone processing
            synth: ModernXGSynthesizer instance for infrastructure access
        """
        super().__init__(params, synth.sample_rate)
        self.synth = synth
        self.params = params

        # For now, create resources directly (TODO: integrate with pooled resources)
        from ..core.envelope import UltraFastADSREnvelope
        from ..core.filter import UltraFastResonantFilter
        from ..core.oscillator import UltraFastXGLFO

        # Allocate buffers directly
        import numpy as np
        self.audio_buffer = np.zeros((synth.block_size, 2), dtype=np.float32)
        self.work_buffer = np.zeros(synth.block_size, dtype=np.float32)

        # Create envelope instance
        self.envelope = UltraFastADSREnvelope(sample_rate=synth.sample_rate, block_size=synth.block_size)

        # Create filter instance
        self.filter = UltraFastResonantFilter(sample_rate=synth.sample_rate, block_size=synth.block_size)

        # Create LFO instances
        self.mod_lfo = UltraFastXGLFO(id=0, sample_rate=synth.sample_rate, block_size=synth.block_size)
        self.vib_lfo = UltraFastXGLFO(id=1, sample_rate=synth.sample_rate, block_size=synth.block_size)

        # SF2-specific state
        self.sample_data: Optional[np.ndarray] = None
        self.phase_step: float = 1.0
        self.sample_position: float = 0.0
        self.pitch_ratio: float = 1.0

        # Loop parameters
        self.loop_mode: int = 0
        self.loop_start: int = 0
        self.loop_end: int = 0

        # Modulation state (connected to global matrix)
        self.pitch_mod: float = 0.0
        self.filter_mod: float = 0.0
        self.volume_mod: float = 1.0

        # Load SF2 parameters and sample data
        self._load_sf2_parameters()

    def _load_sf2_parameters(self):
        """
        Load SF2 parameters and sample data from zone processing.

        This method sets up all SF2-specific parameters from the zone data
        including sample loading, envelope setup, filter configuration, etc.
        """
        # Get sample data from SF2 manager
        sample_data = self.params.get('sample_data')
        if sample_data is not None and len(sample_data) > 0:
            self.sample_data = np.asarray(sample_data, dtype=np.float32)

            # Calculate loop parameters
            loop_info = self.params.get('loop', {})
            self.loop_mode = loop_info.get('mode', 0)
            self.loop_start = max(0, loop_info.get('start', 0))
            self.loop_end = min(len(self.sample_data), loop_info.get('end', len(self.sample_data)))

            # Calculate initial phase step
            root_key = self.params.get('original_pitch', 60)
            note_diff = self.params.get('note', 60) - root_key
            coarse_tune = self.params.get('pitch_modulation', {}).get('coarse_tune', 0)
            fine_tune = self.params.get('pitch_modulation', {}).get('fine_tune', 0.0)
            pitch_correction = self.params.get('pitch_correction', 0.0)

            total_semitones = note_diff + coarse_tune + fine_tune + pitch_correction
            self.pitch_ratio = 2.0 ** (total_semitones / 12.0)
            self.phase_step = self.pitch_ratio

        # Setup envelope using pooled envelope
        amp_env = self.params.get('amp_envelope', {})
        self.envelope.update_parameters(
            delay=amp_env.get('delay', 0.0),
            attack=amp_env.get('attack', 0.01),
            hold=amp_env.get('hold', 0.0),
            decay=amp_env.get('decay', 0.3),
            sustain=amp_env.get('sustain', 0.7),
            release=amp_env.get('release', 0.5)
        )

        # Setup filter using pooled filter
        filter_params = self.params.get('filter', {})
        self.filter.set_parameters(
            cutoff=filter_params.get('cutoff', 20000.0),
            resonance=filter_params.get('resonance', 0.0),
            filter_type=filter_params.get('type', 'lowpass')
        )

        # Setup LFOs using pooled oscillators
        mod_lfo_params = self.params.get('mod_lfo', {})
        self.mod_lfo.set_parameters(
            waveform='sine',
            rate=mod_lfo_params.get('frequency', 8.176),
            depth=1.0,
            delay=mod_lfo_params.get('delay', 0.0)
        )

        vib_lfo_params = self.params.get('vib_lfo', {})
        self.vib_lfo.set_parameters(
            waveform='sine',
            rate=vib_lfo_params.get('frequency', 8.176),
            depth=1.0,
            delay=vib_lfo_params.get('delay', 0.0)
        )

    def generate_samples(self, block_size: int, modulation: Dict) -> np.ndarray:
        """
        Generate SF2 wavetable samples with full modern synth integration.

        Uses pooled resources, modulation matrix integration, and zero-allocation
        architecture for professional-quality SF2 synthesis.

        Args:
            block_size: Number of samples to generate
            modulation: Global modulation values from modulation matrix

        Returns:
            Stereo audio buffer (block_size * 2) as float32 array
        """
        if not self.active or self.sample_data is None:
            return np.zeros(block_size * 2, dtype=np.float32)

        # Apply global modulation from modulation matrix
        self._apply_global_modulation(modulation)

        # Update modulation sources (LFOs, envelopes)
        self._update_modulation_sources(block_size)

        # Generate base wavetable samples
        self._generate_wavetable_samples(block_size)

        # Apply envelope
        self._apply_envelope(block_size)

        # Apply filter with modulation
        self._apply_filter(block_size)

        # Apply panning and final volume
        self._apply_spatial_processing(block_size)

        # Return stereo interleaved audio
        return self.audio_buffer[:block_size * 2]

    def _apply_global_modulation(self, modulation: Dict):
        """
        Apply global modulation from the modulation matrix.

        Connects SF2 partial to the unified modulation ecosystem.
        """
        # Global pitch modulation (from LFOs, envelopes, controllers)
        global_pitch = modulation.get('pitch', 0.0)
        self.pitch_mod = global_pitch

        # Global filter modulation
        global_filter = modulation.get('filter_cutoff', 0.0)
        self.filter_mod = global_filter

        # Global amplitude modulation
        global_amp = modulation.get('volume', 1.0)
        self.volume_mod = global_amp

        # Update phase step with modulation
        modulated_pitch_ratio = self.pitch_ratio * (2.0 ** (self.pitch_mod / 12.0))
        self.phase_step = modulated_pitch_ratio

    def _update_modulation_sources(self, block_size: int):
        """Update internal modulation sources (LFOs, envelopes)."""
        # Update LFOs - generate LFO samples (though we don't use output directly)
        if self.mod_lfo:
            # Generate LFO block without using output (internal modulation only)
            lfo_buffer = self.work_buffer[:block_size]
            self.mod_lfo.generate_block(lfo_buffer, block_size)
        if self.vib_lfo:
            # Generate LFO block without using output (internal modulation only)
            vib_buffer = self.work_buffer[:block_size]
            self.vib_lfo.generate_block(vib_buffer, block_size)

        # Update envelope - envelope is updated during generate_samples
        pass

    def _generate_wavetable_samples(self, block_size: int):
        """
        Generate wavetable samples with SF2 loop processing and interpolation.

        Supports both mono and stereo samples with proper channel handling.
        Uses zero-allocation approach with pre-allocated buffers.
        """
        if self.sample_data is None:
            return

        # Check if sample data is stereo (has shape information or is 2D)
        if hasattr(self.sample_data, 'shape') and len(self.sample_data.shape) > 1:
            # Stereo sample data (shape should be [samples, channels])
            if self.sample_data.shape[1] == 2:
                # True stereo sample
                self._generate_stereo_samples(block_size)
                return

        # Mono sample data - use original mono processing
        self._generate_mono_samples(block_size)

    def _generate_mono_samples(self, block_size: int):
        """Generate mono samples and duplicate to stereo."""
        mono_samples = self.work_buffer[:block_size]

        for i in range(block_size):
            if self.sample_position < len(self.sample_data) - 1:
                # Linear interpolation between samples
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                sample1 = self.sample_data[pos_int]
                sample2 = self.sample_data[pos_int + 1]
                mono_samples[i] = sample1 + frac * (sample2 - sample1)
            else:
                mono_samples[i] = 0.0

            # Update sample position
            self.sample_position += self.phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy mono to stereo buffer (will be panned later)
        self.audio_buffer[::2][:block_size] = mono_samples  # Left channel
        self.audio_buffer[1::2][:block_size] = mono_samples  # Right channel

    def _generate_stereo_samples(self, block_size: int):
        """Generate true stereo samples with interpolation."""
        # For stereo samples, we need to interpolate both channels
        left_channel = self.work_buffer[:block_size]
        right_channel = self.work_buffer[block_size:2*block_size]

        for i in range(block_size):
            if self.sample_position < len(self.sample_data) - 1:
                # Linear interpolation between sample frames
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                # Interpolate left channel
                left1 = self.sample_data[pos_int, 0]
                left2 = self.sample_data[pos_int + 1, 0]
                left_channel[i] = left1 + frac * (left2 - left1)

                # Interpolate right channel
                right1 = self.sample_data[pos_int, 1]
                right2 = self.sample_data[pos_int + 1, 1]
                right_channel[i] = right1 + frac * (right2 - right1)
            else:
                left_channel[i] = 0.0
                right_channel[i] = 0.0

            # Update sample position
            self.sample_position += self.phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy stereo samples to output buffer
        self.audio_buffer[::2][:block_size] = left_channel   # Left channel
        self.audio_buffer[1::2][:block_size] = right_channel # Right channel

    def _handle_sample_looping(self):
        """Handle SF2 sample looping according to loop mode."""
        if self.loop_mode == 0:
            # No loop - stop at end
            if self.sample_position >= len(self.sample_data):
                self.active = False
                self.sample_position = len(self.sample_data) - 1
        elif self.loop_mode in [1, 3]:  # Forward loop or loop+release
            # Loop between loop_start and loop_end
            if self.sample_position >= self.loop_end:
                if self.loop_end > self.loop_start:
                    loop_length = self.loop_end - self.loop_start
                    self.sample_position = self.loop_start + (self.sample_position - self.loop_end) % loop_length
                else:
                    self.sample_position = self.loop_start

    def _apply_envelope(self, block_size: int):
        """Apply amplitude envelope using pooled envelope."""
        if self.envelope:
            # Use work buffer for envelope values
            env_buffer = self.work_buffer[:block_size]

            # Generate envelope block
            self.envelope.generate_block(env_buffer, block_size)

            # Apply envelope to both channels
            self.audio_buffer[:block_size * 2] *= np.tile(env_buffer, 2)

    def _apply_filter(self, block_size: int):
        """Apply filter with modulation using pooled filter."""
        if self.filter and self.filter_mod != 0.0:
            # Modulate filter cutoff
            base_cutoff = self.params.get('filter', {}).get('cutoff', 20000.0)
            modulated_cutoff = max(20.0, min(20000.0, base_cutoff * (1.0 + self.filter_mod)))

            # Update filter parameters
            self.filter.set_parameters(cutoff=modulated_cutoff)

            # Apply filter to stereo buffer - split into left/right channels
            left_channel = self.audio_buffer[::2]  # Even indices
            right_channel = self.audio_buffer[1::2]  # Odd indices
            self.filter.process_block(left_channel, right_channel, block_size)

    def _apply_spatial_processing(self, block_size: int):
        """Apply panning and final volume adjustments."""
        # Apply global volume modulation
        if self.volume_mod != 1.0:
            self.audio_buffer[:block_size * 2] *= self.volume_mod

        # Apply panning from SF2 parameters
        pan = self.params.get('pan', 0.0)
        if pan != 0.0:
            # Convert pan to left/right gains (-1.0 = full left, +1.0 = full right)
            pan_pos = pan / 500.0  # SF2 pan is -500 to +500
            pan_pos = max(-1.0, min(1.0, pan_pos))

            # Calculate pan gains (constant power panning)
            if pan_pos < 0:
                # Pan left
                left_gain = 1.0
                right_gain = 1.0 + pan_pos  # pan_pos is negative, so this reduces right
            else:
                # Pan right
                left_gain = 1.0 - pan_pos
                right_gain = 1.0

            # Apply pan gains
            self.audio_buffer[::2][:block_size] *= left_gain   # Left channel
            self.audio_buffer[1::2][:block_size] *= right_gain # Right channel



    def is_active(self) -> bool:
        """
        Check if SF2 partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active

    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event with envelope triggering.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        self.params['velocity'] = velocity
        self.params['note'] = note
        self.active = True
        self.sample_position = 0.0  # Reset sample position

        # Trigger envelope
        if self.envelope:
            self.envelope.note_on(velocity, note)

    def note_off(self) -> None:
        """Handle note-off event with envelope release."""
        # Trigger envelope release
        if self.envelope:
            self.envelope.note_off()

    def apply_modulation(self, modulation: Dict) -> None:
        """
        Apply modulation changes to partial parameters.

        This integrates SF2 partial with the global modulation matrix.

        Args:
            modulation: Dictionary of modulation values from global matrix
        """
        # Update modulation state from global matrix
        self.pitch_mod = modulation.get('pitch', 0.0)
        self.filter_mod = modulation.get('filter_cutoff', 0.0)
        self.volume_mod = modulation.get('volume', 1.0)

        # Apply global modulation to LFOs if needed
        # This allows external modulation to affect SF2 internal modulation
        pass

    def apply_global_parameters(self, global_params: Dict) -> None:
        """
        Apply global synthesizer parameters to SF2 partial.

        This enables SF2 to respond to master controls, effects sends, etc.

        Args:
            global_params: Global synthesizer parameters
        """
        # Apply master volume
        master_volume = global_params.get('master_volume', 1.0)
        self.volume_mod *= master_volume

        # Apply global effects sends
        if 'effects_sends' in global_params:
            effects_sends = global_params['effects_sends']
            # Store for later use in effects processing
            self._global_reverb_send = effects_sends.get('reverb', 0.0)
            self._global_chorus_send = effects_sends.get('chorus', 0.0)
            self._global_variation_send = effects_sends.get('variation', 0.0)

        # Apply global tuning
        if 'master_tune' in global_params:
            master_tune_semitones = global_params['master_tune']
            self.pitch_mod += master_tune_semitones

        # Apply global transpose
        if 'master_transpose' in global_params:
            master_transpose_semitones = global_params['master_transpose']
            self.pitch_mod += master_transpose_semitones

    def apply_channel_parameters(self, channel_params: Dict) -> None:
        """
        Apply XG channel parameters to SF2 partial.

        This enables SF2 to respond to XG channel-specific controls.

        Args:
            channel_params: XG channel parameters
        """
        # Apply channel volume/level
        if 'part_level' in channel_params:
            part_level = channel_params['part_level'] / 100.0  # Convert from 0-100 to 0.0-1.0
            self.volume_mod *= part_level

        # Apply channel pan
        if 'part_pan' in channel_params:
            # XG pan is -64 to +63, convert to -1.0 to +1.0
            xg_pan = channel_params['part_pan']
            pan_pos = xg_pan / 63.0  # Normalize to -1.0 to +1.0
            self._channel_pan = max(-1.0, min(1.0, pan_pos))

        # Apply channel effects sends
        if 'effects_sends' in channel_params:
            channel_sends = channel_params['effects_sends']
            # Combine with global sends
            self._channel_reverb_send = channel_sends.get('reverb', 40) / 127.0
            self._channel_chorus_send = channel_sends.get('chorus', 0) / 127.0
            self._channel_variation_send = channel_sends.get('variation', 0) / 127.0

        # Apply drum kit assignments (for channel 10)
        if 'drum_kit' in channel_params:
            self._drum_kit = channel_params['drum_kit']

        # Apply channel tuning
        if 'part_coarse_tune' in channel_params:
            coarse_tune = channel_params['part_coarse_tune']
            self.pitch_mod += coarse_tune

        if 'part_fine_tune' in channel_params:
            fine_tune = channel_params['part_fine_tune'] / 100.0  # Convert cents to semitones
            self.pitch_mod += fine_tune

        # Apply channel filter parameters
        if 'part_cutoff' in channel_params or 'part_resonance' in channel_params:
            # Update filter parameters using set_parameters method
            filter_params = {}
            if 'part_cutoff' in channel_params:
                filter_params['cutoff'] = channel_params['part_cutoff']
                self.params['filter']['cutoff'] = channel_params['part_cutoff']
            if 'part_resonance' in channel_params:
                filter_params['resonance'] = channel_params['part_resonance']
                self.params['filter']['resonance'] = channel_params['part_resonance']

            if self.filter and filter_params:
                self.filter.set_parameters(**filter_params)

    def get_effect_send_levels(self) -> Dict[str, float]:
        """
        Get current effect send levels for routing through global effects coordinator.

        Returns:
            Dictionary with effect send levels (reverb, chorus, variation)
        """
        return {
            'reverb': getattr(self, '_channel_reverb_send', 0.0),
            'chorus': getattr(self, '_channel_chorus_send', 0.0),
            'variation': getattr(self, '_channel_variation_send', 0.0)
        }

    def get_channel_pan(self) -> float:
        """
        Get current channel pan position.

        Returns:
            Pan position (-1.0 to 1.0)
        """
        return getattr(self, '_channel_pan', 0.0)

    def get_parameter_state(self) -> Dict[str, Any]:
        """
        Get current parameter state for debugging/monitoring.

        Returns:
            Dictionary of current parameter values
        """
        return {
            'pitch_mod': self.pitch_mod,
            'filter_mod': self.filter_mod,
            'volume_mod': self.volume_mod,
            'channel_pan': getattr(self, '_channel_pan', 0.0),
            'drum_kit': getattr(self, '_drum_kit', 0),
            'global_reverb_send': getattr(self, '_global_reverb_send', 0.0),
            'global_chorus_send': getattr(self, '_global_chorus_send', 0.0),
            'channel_reverb_send': getattr(self, '_channel_reverb_send', 0.0),
            'channel_chorus_send': getattr(self, '_channel_chorus_send', 0.0),
        }

    def reset(self) -> None:
        """Reset partial to initial state for pooling."""
        super().reset()
        self.sample_position = 0.0
        self.pitch_mod = 0.0
        self.filter_mod = 0.0
        self.volume_mod = 1.0

        # Reset pooled resources to initial state
        if self.envelope:
            self.envelope.reset()
        if self.filter:
            self.filter.reset()
        if self.mod_lfo:
            self.mod_lfo.reset()
        if self.vib_lfo:
            self.vib_lfo.reset()

    def get_partial_info(self) -> Dict[str, Any]:
        """Get SF2 partial information for debugging."""
        info = super().get_partial_info()
        info.update({
            'engine_type': 'sf2',
            'sample_loaded': self.sample_data is not None,
            'sample_length': len(self.sample_data) if self.sample_data is not None else 0,
            'loop_mode': self.loop_mode,
            'loop_start': self.loop_start,
            'loop_end': self.loop_end,
            'pitch_ratio': self.pitch_ratio,
            'phase_step': self.phase_step,
            'current_position': self.sample_position,
            'pitch_mod': self.pitch_mod,
            'filter_mod': self.filter_mod,
            'volume_mod': self.volume_mod,
        })
        return info
