"""Wavetable region."""
from __future__ import annotations
from typing import Any
import numpy as np
from ...processing.partial.region import Region
from .partial import WavetablePartial
class WavetableRegion(Region):
    """
    Wavetable region implementation.

    A region that uses wavetable synthesis with oscillator-based playback.
    """

    def __init__(self, region_params: dict[str, Any], wavetable_bank: WavetableBank):
        """
        Initialize wavetable region.

        Args:
            region_params: Region parameters
            wavetable_bank: Reference to wavetable bank
        """
        super().__init__(region_params)
        self.wavetable_bank = wavetable_bank
        self.oscillator = WavetableOscillator(44100)  # Default sample rate

        # Configure oscillator
        self._configure_oscillator()

    def _configure_oscillator(self):
        """Configure the oscillator for this region."""
        # Set wavetable from sample_path or default
        wt_name = "sine"  # Default
        if hasattr(self, "sample_path") and self.sample_path:
            # Try to load wavetable from file
            if self.wavetable_bank.load_wavetable_from_file(self.sample_path, self.sample_path):
                wt_name = self.sample_path

        wavetable = self.wavetable_bank.get_wavetable(wt_name)
        if wavetable:
            self.oscillator.set_wavetable(wavetable)

    def _create_envelope(self, env_type: str, params: dict[str, float]):
        """
        Create envelope for this region.

        Args:
            env_type: Type of envelope ('amp', 'filter', 'pitch')
            params: Envelope parameters

        Returns:
            Configured envelope or None
        """
        try:
            from ..primitives.envelope import UltraFastADSREnvelope

            # Create envelope with region parameters
            envelope = UltraFastADSREnvelope(
                attack=params.get("attack", 0.01),
                decay=params.get("decay", 0.1),
                sustain=params.get("sustain", 0.8),
                release=params.get("release", 0.2),
                sample_rate=44100,
            )

            return envelope

        except Exception as e:
            print(f"Failed to create {env_type} envelope: {e}")
            return None

    def _create_filter(self, filter_type: str, cutoff: float, resonance: float):
        """
        Create filter for this region.

        Args:
            filter_type: Type of filter ('lpf', 'hpf', 'bpf', 'notch')
            cutoff: Filter cutoff frequency
            resonance: Filter resonance/Q factor

        Returns:
            Configured filter or None
        """
        try:
            from ..primitives.filter import BiquadFilter

            # Map SFZ filter types to internal types
            filter_map = {
                "lpf_1p": "lowpass_1p",
                "lpf_2p": "lowpass_2p",
                "hpf_1p": "highpass_1p",
                "hpf_2p": "highpass_2p",
                "bpf_2p": "bandpass",
                "notch": "notch",
            }

            internal_type = filter_map.get(filter_type, "lowpass_2p")

            # Create filter
            filter_instance = BiquadFilter(
                filter_type=internal_type, cutoff=cutoff, resonance=resonance, sample_rate=44100
            )

            return filter_instance

        except Exception as e:
            print(f"Failed to create {filter_type} filter: {e}")
            return None

    def _create_modulation_matrix(self):
        """
        Create modulation matrix for this region.

        Returns:
            Configured modulation matrix or None
        """
        try:
            from ..processing.modulation.advanced_matrix import AdvancedModulationMatrix

            # Create modulation matrix with reasonable defaults
            matrix = AdvancedModulationMatrix(max_routes=16)  # Smaller for regions

            # Add some default modulation routes based on region parameters
            # These would be configured based on SFZ modulation opcodes

            return matrix

        except Exception as e:
            print(f"Failed to create modulation matrix: {e}")
            return None

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate audio samples for this region.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Audio buffer (block_size, channels) - mono or stereo
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Calculate pitch ratio
        pitch_ratio = self.get_pitch_ratio(self.current_note)

        # Set oscillator frequency
        base_freq = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))
        self.oscillator.set_frequency(base_freq * pitch_ratio)

        # Set amplitude with velocity and crossfade
        velocity_gain = self.current_velocity / 127.0
        crossfade_gain = self.calculate_crossfade_gain(self.current_note, self.current_velocity)
        amplitude = self.volume * velocity_gain * crossfade_gain
        self.oscillator.set_amplitude(amplitude)

        # Apply modulation
        freq_mod = modulation.get("pitch", 0.0) / 1200.0
        amp_mod = modulation.get("volume", 0.0)
        self.oscillator.update_modulation(freq_mod, amp_mod, 0.0)

        # Generate mono samples
        mono_samples = self.oscillator.generate_samples(block_size)

        # Apply filter if available
        if self.filter:
            mono_samples = self.filter.process_block(mono_samples)

        # Apply envelope
        if self.amp_env:
            env_values = self.amp_env.get_envelope(block_size)
            mono_samples *= env_values

        # Convert to stereo
        stereo_samples = np.column_stack([mono_samples, mono_samples])

        # Apply pan
        if self.pan != 0.0:
            pan_left = 1.0 - max(0.0, self.pan)
            pan_right = 1.0 - max(0.0, -self.pan)
            stereo_samples[:, 0] *= pan_left
            stereo_samples[:, 1] *= pan_right

        return stereo_samples


