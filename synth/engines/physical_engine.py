"""
Physical Modeling Synthesis Engine

Implements physical modeling synthesis using digital waveguide synthesis,
Karplus-Strong plucked string algorithm, and waveguide mesh techniques.
Provides realistic instrument emulation with proper physical behavior.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..primitives.waveguide import DigitalWaveguide
from ..processing.partial.physical_partial import PhysicalPartial
from .synthesis_engine import SynthesisEngine


class KarplusStrongString:
    """
    Karplus-Strong plucked string synthesis.

    Classic physical modeling algorithm for realistic string synthesis.
    """

    def __init__(self, sample_rate: int, max_length_samples: int = 44100):
        """
        Initialize Karplus-Strong string.

        Args:
            sample_rate: Audio sample rate in Hz
            max_length_samples: Maximum string length in samples
        """
        self.sample_rate = sample_rate
        self.max_length_samples = max_length_samples

        # Delay line for string
        self.delay_line = np.zeros(max_length_samples, dtype=np.float32)
        self.delay_pos = 0
        self.delay_length = max_length_samples // 2

        # Filtering for decay
        self.lowpass_coeff = 0.99  # Close to 1.0 for longer sustain
        self.allpass_coeff = 0.7  # Allpass filter for dispersion

        # Allpass filter state
        self.allpass_z1 = 0.0

        # Excitation state
        self.excited = False

    def set_frequency(self, frequency: float):
        """
        Set string frequency.

        Args:
            frequency: Frequency in Hz
        """
        # Calculate delay length for frequency
        delay_samples = int(self.sample_rate / frequency)
        self.delay_length = max(1, min(delay_samples, self.max_length_samples - 1))

    def pluck(self, amplitude: float = 1.0):
        """
        Pluck the string.

        Args:
            amplitude: Pluck amplitude
        """
        # Fill delay line with noise
        noise_length = min(self.delay_length, 1000)  # Limit noise burst length
        noise = np.random.uniform(-amplitude, amplitude, noise_length)

        # Apply simple envelope to noise
        envelope = np.linspace(1.0, 0.1, noise_length)
        excitation = noise * envelope

        # Fill delay line
        fill_length = min(len(excitation), len(self.delay_line))
        self.delay_line[:fill_length] = excitation[:fill_length]

        self.excited = True

    def process_sample(self) -> float:
        """
        Process one sample through the string.

        Returns:
            Output sample
        """
        # Get current sample
        current = self.delay_line[self.delay_pos]

        # Lowpass filter for energy decay
        filtered = current * self.lowpass_coeff

        # Allpass filter for dispersion (simulates string stiffness)
        allpass_input = filtered
        allpass_output = self.allpass_coeff * (allpass_input - self.allpass_z1) + self.allpass_z1
        self.allpass_z1 = allpass_input

        # Store filtered sample back (with feedback)
        feedback = allpass_output * 0.999  # Slight energy loss
        self.delay_line[self.delay_pos] = feedback

        # Update position
        self.delay_pos = (self.delay_pos + 1) % self.delay_length

        return current

    def is_active(self) -> bool:
        """Check if string is still vibrating."""
        energy = np.sum(np.abs(self.delay_line)) / len(self.delay_line)
        return energy > 0.0001

    def reset(self):
        """Reset string state."""
        self.delay_line.fill(0.0)
        self.delay_pos = 0
        self.allpass_z1 = 0.0
        self.excited = False


class PhysicalEngine(SynthesisEngine):
    """
    Physical Modeling Synthesis Engine.

    Implements digital waveguide synthesis and Karplus-Strong algorithms
    for realistic acoustic instrument simulation.

    Supports:
    - Plucked strings (guitar, harp, etc.)
    - Struck instruments (piano, percussion)
    - Wind instruments (flute, clarinet)
    - Bowed strings (violin, cello)
    """

    # Physical model types
    MODEL_TYPES = {
        "pluck": "Karplus-Strong plucked string",
        "strike": "Digital waveguide struck instrument",
        "blow": "Digital waveguide wind instrument",
        "bow": "Digital waveguide bowed string",
    }

    def __init__(self, max_strings: int = 16, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize physical modeling engine.

        Args:
            max_strings: Maximum number of simultaneous strings/waveguides
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.max_strings = max_strings

        # Initialize waveguides and strings
        self.waveguides = [DigitalWaveguide(sample_rate) for _ in range(max_strings)]
        self.strings = [KarplusStrongString(sample_rate) for _ in range(max_strings)]

        # Model type per voice
        self.model_types = ["pluck"] * max_strings

        # Global parameters
        self.master_volume = 1.0
        self.brightness = 1.0  # Timbre control
        self.damping = 0.99  # Energy decay rate

        # Active voices tracking
        self.active_voices = {}  # voice_index -> (note, velocity, start_time)

    def get_engine_info(self) -> dict[str, Any]:
        """Get physical modeling engine information."""
        return {
            "name": "Physical Modeling Engine",
            "type": "physical",
            "capabilities": ["waveguide_synthesis", "karplus_strong", "physical_modeling"],
            "formats": [".phys", ".mdl"],  # Custom physical modeling formats
            "polyphony": self.max_strings,  # Limited by CPU intensive nature
            "parameters": ["model_type", "brightness", "damping", "excitation_type"],
            "max_strings": self.max_strings,
        }

    # ========== REGION-BASED ARCHITECTURE IMPLEMENTATION ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get physical modeling preset information with proper region descriptors.

        Args:
            bank: Preset bank number (0-127)
            program: Preset program number (0-127)

        Returns:
            PresetInfo with region descriptors for physical modeling synthesis
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # Physical engine uses waveguide/modal synthesis
        # Programs define physical parameters for strings/bars/tubes
        preset_name = f"Physical {bank}:{program}"

        # Create region descriptors for physical modeling synthesis
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type=self.get_engine_type(),
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                "model_type": "waveguide",  # Physical model type
                "material": "steel",  # Material properties
                "damping": 0.3,  # Damping factor
                "brightness": 0.5,  # Brightness control
                "release": 0.5,  # Release time
                "max_strings": self.max_strings,
                "excitation_type": "pluck",  # Excitation method
                "body_size": 1.0,  # Resonant body size
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=preset_name,
            engine_type=self.get_engine_type(),
            region_descriptors=[descriptor],
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """
        Get all region descriptors for physical modeling preset.

        Args:
            bank: Preset bank number
            program: Preset program number

        Returns:
            List of RegionDescriptor objects
        """
        preset_info = self.get_preset_info(bank, program)
        return preset_info.region_descriptors if preset_info else []

    def create_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create physical modeling region instance from descriptor.

        Args:
            descriptor: Region descriptor with physical parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance for physical modeling synthesis
        """
        from ..processing.partial.physical_region import PhysicalRegion

        # Create physical region with proper initialization
        region = PhysicalRegion(descriptor, sample_rate)

        # Initialize the region (creates waveguides, resonators)
        if not region.initialize():
            raise RuntimeError("Failed to initialize Physical region")

        return region

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for physical region (algorithmic, no samples needed).

        Args:
            region: Region to load sample for

        Returns:
            True (Physical doesn't use samples)
        """
        # Physical modeling is algorithmic - no sample loading required
        # Waveguides and resonators are created during region initialization
        return region._initialized if hasattr(region, "_initialized") else False

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate physical modeling audio samples.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Calculate base frequency
        base_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply pitch bend
        pitch_bend_semitones = modulation.get("pitch", 0.0) / 100.0
        bend_ratio = 2.0 ** (pitch_bend_semitones / 12.0)
        base_freq *= bend_ratio

        # Use pre-allocated or pooled buffer (zero-filled already)
        output = self.get_mono_buffer(block_size)

        for i in range(block_size):
            sample = 0.0

            # Sum all active strings/waveguides
            for idx in range(self.max_strings):
                if idx in self.active_voices:
                    model_type = self.model_types[idx]

                    if model_type == "pluck":
                        sample += self.strings[idx].process_sample()
                    else:
                        # Waveguide models
                        sample += self.waveguides[idx].process_sample()

            # Apply brightness filter (simple high-frequency boost)
            if self.brightness != 1.0:
                # Simple brightness control via amplitude scaling
                brightness_factor = 1.0 + (self.brightness - 1.0) * 0.5
                sample *= brightness_factor

            # Apply master volume and velocity
            velocity_scale = velocity / 127.0
            sample *= self.master_volume * velocity_scale

            output[i] = sample

        # Convert mono->stereo via pooled/scratch buffer
        stereo_output = self.get_stereo_buffer(block_size)
        stereo_output[:, 0] = output
        stereo_output[:, 1] = output

        return stereo_output

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported."""
        return 21 <= note <= 108  # Standard piano range, can be extended

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int) -> PhysicalPartial:
        """Create physical modeling partial."""
        from ..processing.partial.physical_partial import PhysicalPartial

        return PhysicalPartial(partial_params, sample_rate)

    def set_model_type(self, voice_index: int, model_type: str):
        """
        Set the physical model type for a voice.

        Args:
            voice_index: Voice index (0-max_strings)
            model_type: Model type ('pluck', 'strike', 'blow', 'bow')
        """
        if 0 <= voice_index < self.max_strings and model_type in self.MODEL_TYPES:
            self.model_types[voice_index] = model_type

    def excite_voice(
        self, voice_index: int, note: int, velocity: int, model_params: dict[str, Any] = None
    ):
        """
        Excite a physical model voice.

        Args:
            voice_index: Voice index to excite
            note: MIDI note number
            velocity: MIDI velocity
            model_params: Additional model parameters
        """
        if not (0 <= voice_index < self.max_strings):
            return

        model_params = model_params or {}
        model_type = self.model_types[voice_index]

        # Calculate frequency
        frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply detuning if specified
        detune_cents = model_params.get("detune_cents", 0)
        if detune_cents != 0:
            frequency *= 2.0 ** (detune_cents / 1200.0)

        # Set frequency for the model
        if model_type == "pluck":
            self.strings[voice_index].set_frequency(frequency)
            self.strings[voice_index].pluck(velocity / 127.0)
        else:
            # Waveguide models
            self.waveguides[voice_index].set_frequency(frequency)

            # Set waveguide parameters
            waveguide_params = {
                "scattering_coeff": model_params.get("scattering_coeff", 0.5),
                "loop_filter_coeff": self.damping,
            }
            self.waveguides[voice_index].set_parameters(waveguide_params)

            # Excite based on model type
            excitation_type = model_type  # 'strike', 'blow', or 'bow'
            amplitude = velocity / 127.0
            self.waveguides[voice_index].excite(excitation_type, amplitude)

        # Track active voice with proper timestamp
        import time

        self.active_voices[voice_index] = (note, velocity, time.time())

    def release_voice(self, voice_index: int):
        """
        Release a physical model voice (let it decay naturally).

        Args:
            voice_index: Voice index to release
        """
        if voice_index in self.active_voices:
            del self.active_voices[voice_index]

    def set_brightness(self, brightness: float):
        """
        Set overall brightness/timbre control.

        Args:
            brightness: Brightness factor (0.0-2.0)
        """
        self.brightness = max(0.0, min(2.0, brightness))

    def set_damping(self, damping: float):
        """
        Set energy damping/decay rate.

        Args:
            damping: Damping factor (0.9-1.0, higher = longer sustain)
        """
        self.damping = max(0.9, min(1.0, damping))

        # Update all waveguides
        for waveguide in self.waveguides:
            waveguide.set_parameters({"loop_filter_coeff": self.damping})

    def get_voice_parameters(self, program: int, bank: int = 0) -> dict[str, Any] | None:
        """Get physical modeling voice parameters."""
        # Default parameters for different instrument types
        if program < 40:  # Piano
            return {
                "name": f"Physical Piano {program}",
                "model_type": "strike",
                "brightness": 1.2,
                "damping": 0.995,
                "scattering_coeff": 0.3,
            }
        elif program < 80:  # Chromatic percussion
            return {
                "name": f"Physical Percussion {program}",
                "model_type": "strike",
                "brightness": 1.5,
                "damping": 0.98,
                "scattering_coeff": 0.6,
            }
        else:  # Strings/winds
            return {
                "name": f"Physical String {program}",
                "model_type": "pluck",
                "brightness": 1.0,
                "damping": 0.997,
                "scattering_coeff": 0.5,
            }

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        # Find available voice
        for voice_idx in range(self.max_strings):
            if voice_idx not in self.active_voices:
                self.excite_voice(voice_idx, note, velocity)
                break

    def note_off(self, note: int):
        """Handle note-off event."""
        # Find voice playing this note and release it
        for voice_idx, (voice_note, _, _) in self.active_voices.items():
            if voice_note == note:
                self.release_voice(voice_idx)
                break

    def is_active(self) -> bool:
        """Check if engine is active."""
        return len(self.active_voices) > 0

    def reset(self):
        """Reset engine state."""
        self.active_voices.clear()
        for waveguide in self.waveguides:
            waveguide.reset()
        for string in self.strings:
            string.reset()

    def get_supported_formats(self) -> list[str]:
        """Get supported file formats."""
        return [".phys", ".mdl"]

    def save_model(self, model_data: dict[str, Any]) -> dict[str, Any]:
        """
        Save physical model data.

        Args:
            model_data: Model parameters

        Returns:
            Complete model data dictionary
        """
        return {
            "engine_type": "physical",
            "model_types": self.model_types.copy(),
            "master_volume": self.master_volume,
            "brightness": self.brightness,
            "damping": self.damping,
            **model_data,
        }

    def _create_base_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create Physical base region without S.Art2 wrapper.

        Args:
            descriptor: Region descriptor with physical parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            PhysicalRegion instance
        """
        from ..processing.partial.physical_region import PhysicalRegion

        return PhysicalRegion(descriptor, sample_rate)

    def load_model(self, model_data: dict[str, Any]):
        """
        Load physical model data.

        Args:
            model_data: Model data dictionary
        """
        self.model_types = model_data.get("model_types", self.model_types)
        self.master_volume = model_data.get("master_volume", 1.0)
        self.brightness = model_data.get("brightness", 1.0)
        self.damping = model_data.get("damping", 0.99)
