"""
SFZ Region Implementation

SFZ-specific region implementation with sample playback, envelopes,
filters, and modulation according to the SFZ v2 specification.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import math

from ..partial.region import Region
from ..audio.sample_manager import SFZSample, PyAVSampleManager
from ..modulation.advanced_matrix import AdvancedModulationMatrix
from ..core.oscillator import UltraFastXGLFO


class SFZEnvelope:
    """SFZ Envelope implementation with AHDSR (Attack, Hold, Decay, Sustain, Release)."""

    def __init__(self, params: Dict[str, float]):
        # Envelope parameters (in seconds)
        self.attack = params.get('attack', 0.0)
        self.hold = params.get('hold', 0.0)
        self.decay = params.get('decay', 0.0)
        self.sustain = params.get('sustain', 1.0)  # 0.0 to 1.0
        self.release = params.get('release', 0.0)
        self.delay = params.get('delay', 0.0)

        # Runtime state
        self.state = 'idle'  # idle, delay, attack, hold, decay, sustain, release
        self.current_level = 0.0
        self.time_in_state = 0.0
        self.release_level = 0.0

        # Pre-calculate envelope stages
        self._precalculate_stages()

    def _precalculate_stages(self):
        """Pre-calculate envelope stage parameters for efficiency."""
        # Convert times to avoid division by zero
        self.attack_rate = 1.0 / max(self.attack, 0.001)
        self.decay_rate = (1.0 - self.sustain) / max(self.decay, 0.001)
        self.release_rate = self.sustain / max(self.release, 0.001)

    def note_on(self, velocity: float = 1.0):
        """Trigger envelope note-on."""
        self.state = 'delay' if self.delay > 0 else 'attack'
        self.time_in_state = 0.0
        self.release_level = 0.0

    def note_off(self):
        """Trigger envelope note-off."""
        if self.state not in ['idle', 'release']:
            self.state = 'release'
            self.time_in_state = 0.0
            self.release_level = self.current_level

    def process(self, block_size: int, sample_rate: float) -> np.ndarray:
        """
        Process envelope for a block of samples.

        Args:
            block_size: Number of samples to process
            sample_rate: Audio sample rate

        Returns:
            Envelope modulation values for the block
        """
        output = np.zeros(block_size, dtype=np.float32)
        dt = 1.0 / sample_rate

        for i in range(block_size):
            self.time_in_state += dt

            if self.state == 'delay':
                if self.time_in_state >= self.delay:
                    self.state = 'attack'
                    self.time_in_state = 0.0

            elif self.state == 'attack':
                if self.time_in_state >= self.attack:
                    self.current_level = 1.0
                    self.state = 'hold' if self.hold > 0 else 'decay'
                    self.time_in_state = 0.0
                else:
                    self.current_level = self.time_in_state * self.attack_rate

            elif self.state == 'hold':
                if self.time_in_state >= self.hold:
                    self.state = 'decay'
                    self.time_in_state = 0.0
                # Hold at peak level (1.0)

            elif self.state == 'decay':
                if self.time_in_state >= self.decay:
                    self.current_level = self.sustain
                    self.state = 'sustain'
                else:
                    decay_amount = self.time_in_state * self.decay_rate
                    self.current_level = 1.0 - decay_amount

            elif self.state == 'sustain':
                # Hold sustain level
                pass

            elif self.state == 'release':
                if self.time_in_state >= self.release:
                    self.current_level = 0.0
                    self.state = 'idle'
                else:
                    release_amount = self.time_in_state * self.release_rate
                    self.current_level = max(0.0, self.release_level - release_amount)

            output[i] = self.current_level

        return output

    def is_finished(self) -> bool:
        """Check if envelope has finished."""
        return self.state == 'idle'

    def reset(self):
        """Reset envelope to initial state."""
        self.state = 'idle'
        self.current_level = 0.0
        self.time_in_state = 0.0
        self.release_level = 0.0


class SFZFilter:
    """SFZ Filter implementation with various filter types."""

    def __init__(self, filter_type: str = 'lpf_2p', cutoff: float = 1000.0,
                 resonance: float = 0.0, sample_rate: float = 44100.0):
        self.filter_type = filter_type
        self.cutoff = cutoff
        self.resonance = resonance
        self.sample_rate = sample_rate

        # Filter state
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

        # Update coefficients
        self._update_coefficients()

    def _update_coefficients(self):
        """Update filter coefficients based on current parameters."""
        # Normalize frequency
        normalized_freq = 2.0 * math.pi * self.cutoff / self.sample_rate
        normalized_freq = min(normalized_freq, math.pi * 0.99)  # Stability limit

        # Calculate coefficients for 2-pole lowpass
        if self.filter_type in ['lpf_2p', 'lowpass']:
            k = math.tan(normalized_freq * 0.5)
            k2 = k * k
            sqrt2 = math.sqrt(2.0)

            norm = 1.0 / (1.0 + k + k2)
            self.a0 = k2 * norm
            self.a1 = 2.0 * self.a0
            self.a2 = self.a0
            self.b1 = 2.0 * (k2 - 1.0) * norm
            self.b2 = (1.0 - k + k2) * norm

        # Add resonance
        if self.resonance > 0.0:
            q = 1.0 / (1.0 + self.resonance)
            self.a0 *= q
            self.a1 *= q
            self.a2 *= q

    def process(self, input_signal: np.ndarray) -> np.ndarray:
        """
        Process audio through the filter.

        Args:
            input_signal: Input audio buffer

        Returns:
            Filtered audio buffer
        """
        output = np.zeros_like(input_signal)

        for i, x0 in enumerate(input_signal):
            # Direct Form I implementation
            y0 = self.a0 * x0 + self.a1 * self.x1 + self.a2 * self.x2 - self.b1 * self.y1 - self.b2 * self.y2

            # Update state
            self.x2, self.x1 = self.x1, x0
            self.y2, self.y1 = self.y1, y0

            output[i] = y0

        return output

    def set_cutoff(self, cutoff: float):
        """Set filter cutoff frequency."""
        self.cutoff = max(20.0, min(cutoff, self.sample_rate * 0.4))  # Reasonable limits
        self._update_coefficients()

    def set_resonance(self, resonance: float):
        """Set filter resonance."""
        self.resonance = max(0.0, min(resonance, 0.99))  # Stability limit
        self._update_coefficients()

    def reset(self):
        """Reset filter state."""
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0


class SFZRegion(Region):
    """
    SFZ Region Implementation

    Full SFZ v2 region implementation with sample playback, envelopes,
    filters, and advanced modulation according to SFZ specification.
    """

    def __init__(self, region_params: Dict[str, Any], sample_manager: Optional[PyAVSampleManager] = None):
        super().__init__(region_params)

        # SFZ-specific initialization
        self.sample_manager = sample_manager

        # Load sample if specified
        if self.sample_path and self.sample_manager:
            try:
                self.sample = self.sample_manager.load_sample(self.sample_path)
            except Exception as e:
                print(f"Warning: Failed to load sample '{self.sample_path}': {e}")
                self.sample = None

        # Initialize SFZ components
        self.amp_env = SFZEnvelope(self.amplitude_envelope)
        self.filter_env = SFZEnvelope(self.filter_envelope)
        self.filter = SFZFilter(self.filter_type, self.cutoff, self.resonance, 44100.0)

        # SFZ LFO parameters
        self.lfo1_params = region_params.get('lfo1', {})
        self.lfo2_params = region_params.get('lfo2', {})

        # Create LFOs
        self.lfo1 = self._create_lfo(self.lfo1_params, lfo_id=0)
        self.lfo2 = self._create_lfo(self.lfo2_params, lfo_id=1)

        # Modulation matrix for this region
        self.modulation_matrix = AdvancedModulationMatrix(max_routes=50)  # Region-specific modulation

        # Runtime state
        self.playback_position = 0
        self.loop_count = 0

    def _create_lfo(self, lfo_params: Dict[str, Any], lfo_id: int) -> Optional[UltraFastXGLFO]:
        """
        Create an LFO from SFZ parameters.

        Args:
            lfo_params: SFZ LFO parameters
            lfo_id: LFO identifier (0 or 1)

        Returns:
            UltraFastXGLFO instance or None if no LFO parameters
        """
        if not lfo_params:
            return None

        try:
            # Extract LFO parameters
            waveform = lfo_params.get('waveform', 'sine')
            freq = lfo_params.get('freq', 5.0)  # Default 5 Hz
            depth = lfo_params.get('depth', 1.0)
            delay = lfo_params.get('delay', 0.0)
            fade = lfo_params.get('fade', 0.0)

            # Create LFO instance
            lfo = UltraFastXGLFO(
                id=lfo_id,
                waveform=waveform,
                rate=freq,
                depth=depth,
                delay=delay,
                sample_rate=44100
            )

            # Set fade-in if specified
            if fade > 0:
                lfo.set_pitch_modulation(delay=delay, fade_in=fade)

            return lfo

        except Exception as e:
            print(f"Failed to create LFO {lfo_id}: {e}")
            return None

    def generate_samples(self, block_size: int, modulation: Dict[str, float]) -> np.ndarray:
        """
        Generate audio samples for this SFZ region.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.sample or not self.is_active():
            return np.zeros((block_size, 2), dtype=np.float32)

        # Store current modulation for use in sample generation
        self.current_modulation = modulation

        # Generate sample data
        sample_data = self._generate_sample_data(block_size)

        # Apply amplitude envelope
        amp_env_values = self.amp_env.process(block_size, 44100.0)
        sample_data *= amp_env_values[:, np.newaxis]  # Apply to both channels

        # Apply filter
        if self.filter:
            # Modulate filter cutoff
            base_cutoff = self.cutoff
            if 'filter_cutoff' in modulation:
                base_cutoff *= (1.0 + modulation['filter_cutoff'])

            # Apply filter envelope
            filter_env_values = self.filter_env.process(block_size, 44100.0)
            modulated_cutoff = base_cutoff * (0.1 + 0.9 * filter_env_values)  # Avoid zero cutoff

            # Update filter and process
            self.filter.set_cutoff(float(np.mean(modulated_cutoff)))  # Use mean for now
            sample_data[:, 0] = self.filter.process(sample_data[:, 0])  # Left
            sample_data[:, 1] = self.filter.process(sample_data[:, 1])  # Right

        # Apply LFO modulation
        lfo_modulation = self._apply_lfo_modulation(block_size)

        # Apply amplitude modulation
        if 'volume' in modulation:
            sample_data *= (1.0 + modulation['volume'])

        # Apply LFO amplitude modulation
        if 'lfo1_volume' in lfo_modulation:
            sample_data *= (1.0 + lfo_modulation['lfo1_volume'])
        if 'lfo2_volume' in lfo_modulation:
            sample_data *= (1.0 + lfo_modulation['lfo2_volume'])

        # Apply pan modulation
        if 'pan' in modulation:
            pan = np.clip(self.pan + modulation['pan'], -1.0, 1.0)
            left_gain = 1.0 - max(0.0, pan)
            right_gain = 1.0 - max(0.0, -pan)
            sample_data[:, 0] *= left_gain
            sample_data[:, 1] *= right_gain

        # Apply LFO pan modulation
        if 'lfo1_pan' in lfo_modulation:
            pan_mod = lfo_modulation['lfo1_pan']
            left_gain = 1.0 - max(0.0, pan_mod)
            right_gain = 1.0 - max(0.0, -pan_mod)
            sample_data[:, 0] *= left_gain
            sample_data[:, 1] *= right_gain

        if 'lfo2_pan' in lfo_modulation:
            pan_mod = lfo_modulation['lfo2_pan']
            left_gain = 1.0 - max(0.0, pan_mod)
            right_gain = 1.0 - max(0.0, -pan_mod)
            sample_data[:, 0] *= left_gain
            sample_data[:, 1] *= right_gain

        # Apply pitch modulation
        if 'pitch' in modulation:
            # Simple pitch shifting (placeholder - full implementation would be more complex)
            pitch_ratio = 2.0 ** (modulation['pitch'] / 12.0)  # Convert semitones to ratio
            # For now, just apply a simple gain adjustment
            sample_data *= min(2.0, max(0.5, pitch_ratio))

        return sample_data

    def _generate_sample_data(self, block_size: int) -> np.ndarray:
        """
        Generate sample data with looping and high-quality pitch control.

        Implements proper pitch shifting using cubic interpolation for
        smooth playback at any pitch ratio.
        """
        if not self.sample:
            return np.zeros((block_size, 2), dtype=np.float32)

        output = np.zeros((block_size, 2), dtype=np.float32)

        # Calculate pitch ratio
        pitch_ratio = self.get_pitch_ratio(self.current_note)

        # Apply pitch modulation if present
        pitch_modulation = 0.0
        if hasattr(self, 'current_modulation') and 'pitch' in self.current_modulation:
            pitch_modulation = self.current_modulation['pitch']

        # Combine base pitch ratio with modulation
        total_pitch_ratio = pitch_ratio * (2.0 ** (pitch_modulation / 12.0))

        # Generate sample data with looping and interpolation
        for i in range(block_size):
            # Check for loop boundaries
            if self.end is not None and self.playback_position >= self.end:
                if self.loop_mode in ['loop_continuous', 'loop_sustain']:
                    # Loop back to loop_start
                    self.playback_position = self.loop_start
                    self.loop_count += 1
                else:
                    # End of sample
                    break

            # Get interpolated sample data
            if self.sample.is_stereo():
                left_sample = self._interpolate_sample(self.sample.data[:, 0], self.playback_position)
                right_sample = self._interpolate_sample(self.sample.data[:, 1], self.playback_position)
            else:
                mono_sample = self._interpolate_sample(self.sample.data, self.playback_position)
                left_sample = right_sample = mono_sample

            # Apply volume and pan from region parameters
            volume_linear = 10.0 ** (self.volume / 20.0)  # Convert dB to linear
            left_sample *= volume_linear
            right_sample *= volume_linear

            # Apply region pan
            if self.pan != 0.0:
                left_pan = 1.0 - max(0.0, self.pan)
                right_pan = 1.0 - max(0.0, -self.pan)
                left_sample *= left_pan
                right_sample *= right_pan

            output[i, 0] = left_sample
            output[i, 1] = right_sample

            # Advance playback position with pitch ratio
            self.playback_position += total_pitch_ratio

        return output

    def _interpolate_sample(self, sample_data: np.ndarray, position: float) -> float:
        """
        High-quality cubic interpolation for smooth pitch shifting.

        Args:
            sample_data: Sample data array
            position: Fractional position in samples

        Returns:
            Interpolated sample value
        """
        # Get integer and fractional parts
        int_pos = int(position)
        frac_pos = position - int_pos

        # Ensure we have valid indices for interpolation
        data_len = len(sample_data)
        if int_pos < 0 or int_pos >= data_len:
            return 0.0

        # Cubic interpolation requires 4 points: x[n-1], x[n], x[n+1], x[n+2]
        indices = [int_pos - 1, int_pos, int_pos + 1, int_pos + 2]

        # Clamp indices to valid range
        samples = []
        for idx in indices:
            if idx < 0:
                samples.append(0.0)  # Extend with silence
            elif idx >= data_len:
                samples.append(0.0)  # Extend with silence
            else:
                samples.append(float(sample_data[idx]))

        # Cubic Hermite interpolation
        # y = (2*x^3 - 3*x^2 + 1)*y0 + (-2*x^3 + 3*x^2)*y1 + (x^3 - 2*x^2 + x)*y0' + (x^3 - x^2)*y1'
        # For simplicity, use Catmull-Rom spline which is similar

        # Catmull-Rom spline coefficients
        x = frac_pos
        x2 = x * x
        x3 = x2 * x

        # Coefficients for Catmull-Rom
        a = -0.5 * x3 + x2 - 0.5 * x
        b = 1.5 * x3 - 2.5 * x2 + 1.0
        c = -1.5 * x3 + 2.0 * x2 + 0.5 * x
        d = 0.5 * x3 - 0.5 * x2

        return a * samples[0] + b * samples[1] + c * samples[2] + d * samples[3]

    def _apply_pitch_modulation(self, modulation: Dict[str, float]) -> float:
        """
        Apply pitch modulation with proper semitone conversion.

        Args:
            modulation: Modulation values dictionary

        Returns:
            Pitch ratio multiplier from modulation
        """
        if 'pitch' not in modulation:
            return 1.0

        # Convert semitones to frequency ratio
        pitch_semitones = modulation['pitch']

        # Clamp to reasonable range to prevent extreme pitch shifting
        pitch_semitones = max(-24.0, min(24.0, pitch_semitones))

        return 2.0 ** (pitch_semitones / 12.0)

    def _apply_lfo_modulation(self, block_size: int) -> Dict[str, np.ndarray]:
        """
        Apply LFO modulation for this block.

        Args:
            block_size: Number of samples to process

        Returns:
            Dictionary of LFO modulation values
        """
        modulation = {}

        # Generate LFO1 modulation
        if self.lfo1:
            lfo1_buffer = np.zeros(block_size, dtype=np.float32)
            self.lfo1.generate_block(lfo1_buffer)

            # Apply LFO1 modulation based on its parameters
            if 'volume' in self.lfo1_params:
                modulation['lfo1_volume'] = lfo1_buffer * self.lfo1_params['volume']
            if 'pan' in self.lfo1_params:
                modulation['lfo1_pan'] = lfo1_buffer * self.lfo1_params['pan']
            if 'pitch' in self.lfo1_params:
                modulation['lfo1_pitch'] = lfo1_buffer * self.lfo1_params['pitch']
            if 'filter' in self.lfo1_params:
                modulation['lfo1_filter'] = lfo1_buffer * self.lfo1_params['filter']

        # Generate LFO2 modulation
        if self.lfo2:
            lfo2_buffer = np.zeros(block_size, dtype=np.float32)
            self.lfo2.generate_block(lfo2_buffer)

            # Apply LFO2 modulation based on its parameters
            if 'volume' in self.lfo2_params:
                modulation['lfo2_volume'] = lfo2_buffer * self.lfo2_params['volume']
            if 'pan' in self.lfo2_params:
                modulation['lfo2_pan'] = lfo2_buffer * self.lfo2_params['pan']
            if 'pitch' in self.lfo2_params:
                modulation['lfo2_pitch'] = lfo2_buffer * self.lfo2_params['pitch']
            if 'filter' in self.lfo2_params:
                modulation['lfo2_filter'] = lfo2_buffer * self.lfo2_params['filter']

        return modulation

    def note_on(self, velocity: int, note: int) -> None:
        """Handle note-on for SFZ region."""
        super().note_on(velocity, note)

        # Reset playback position
        self.playback_position = self.offset
        self.loop_count = 0

        # Trigger envelopes with velocity scaling
        velocity_norm = velocity / 127.0

        if self.amp_env:
            self.amp_env.note_on(velocity_norm)
        if self.filter_env:
            self.filter_env.note_on(velocity_norm)

        # Reset filter state
        if self.filter:
            self.filter.reset()

    def note_off(self) -> None:
        """Handle note-off for SFZ region."""
        super().note_off()

        # Trigger release for envelopes
        if self.amp_env:
            self.amp_env.note_off()
        if self.filter_env:
            self.filter_env.note_off()

    def is_active(self) -> bool:
        """Check if region is still active."""
        envelope_active = bool(self.amp_env and not self.amp_env.is_finished())
        sample_active = bool(self.sample and self.playback_position < len(self.sample.data))
        return envelope_active or sample_active

    def get_region_info(self) -> Dict[str, Any]:
        """Get detailed region information."""
        info = super().get_region_info()
        info.update({
            'sample_loaded': self.sample is not None,
            'sample_channels': self.sample.channels if self.sample else 0,
            'sample_length': len(self.sample.data) if self.sample else 0,
            'envelope_state': self.amp_env.state if self.amp_env else 'none',
            'playback_position': self.playback_position,
            'loop_count': self.loop_count,
            'pitch_ratio': self.get_pitch_ratio(self.current_note)
        })
        return info

    def apply_channel_parameters(self, channel_params: Dict) -> None:
        """
        Apply channel-level parameters to this SFZ region.

        Args:
            channel_params: Dictionary of channel parameters
        """
        # Channel transpose affects pitch
        if 'transpose' in channel_params:
            # This would affect the region's pitch calculation
            # For now, store it and apply in get_pitch_ratio
            self._channel_transpose = channel_params['transpose']

        # Drum kit information (affects sample selection for percussion)
        if 'drum_kit' in channel_params:
            self._drum_kit = channel_params['drum_kit']

        # Other channel parameters could be applied here
        # (volume, pan, effects sends are typically handled at higher levels)

    def reset(self):
        """Reset region to clean state."""
        super().reset()
        self.playback_position = 0
        self.loop_count = 0

        if self.amp_env:
            self.amp_env.reset()
        if self.filter_env:
            self.filter_env.reset()
        if self.filter:
            self.filter.reset()
