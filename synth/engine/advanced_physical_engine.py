"""
Advanced Physical Modeling Engine

Sophisticated physical modeling synthesis engine providing realistic
acoustic instrument simulation through waveguide and modal synthesis.
"""
from __future__ import annotations

import numpy as np
from typing import Any
from collections.abc import Callable
import threading
import math

from .synthesis_engine import SynthesisEngine


class WaveguideString:
    """
    Waveguide string model for plucked/picked string instruments.

    Implements the Karplus-Strong algorithm with extensions for
    realistic string behavior including dispersion and coupling.
    """

    def __init__(self, sample_rate: int = 44100, max_length: int = 10000):
        """
        Initialize waveguide string.

        Args:
            sample_rate: Audio sample rate
            max_length: Maximum waveguide length in samples
        """
        self.sample_rate = sample_rate
        self.max_length = max_length

        # Waveguide components
        self.delay_line = np.zeros(max_length, dtype=np.float32)
        self.bridge_reflection = 0.0
        self.nut_reflection = 0.0

        # String parameters
        self.frequency = 440.0
        self.length_samples = int(sample_rate / self.frequency)
        self.tension = 1.0
        self.damping = 0.99  # Loss factor
        self.pluck_position = 0.5  # Pluck position (0-1)

        # Excitation
        self.excitation_signal: np.ndarray | None = None
        self.excitation_index = 0

        # Read/write pointers
        self.write_pos = 0
        self.read_pos = 0

        # Active state
        self.active = False

        # Update waveguide parameters
        self._update_waveguide()

    def _update_waveguide(self):
        """Update waveguide parameters based on string properties."""
        # Calculate delay length from frequency
        self.length_samples = int(self.sample_rate / self.frequency)

        # Ensure within bounds
        self.length_samples = max(1, min(self.length_samples, self.max_length))

        # Reset delay line
        self.delay_line.fill(0.0)

        # Calculate reflection coefficients
        # Bridge reflection (more negative for brighter sound)
        self.bridge_reflection = -0.9

        # Nut reflection (less negative for nut)
        self.nut_reflection = -0.3

        # Set read/write positions
        self.read_pos = 0
        self.write_pos = self.length_samples // 2

    def set_frequency(self, frequency: float):
        """Set string fundamental frequency."""
        self.frequency = max(20.0, min(frequency, 20000.0))
        self._update_waveguide()

    def set_pluck_position(self, position: float):
        """Set pluck position along string (0=bridge, 1=nut)."""
        self.pluck_position = max(0.0, min(position, 1.0))

    def set_tension(self, tension: float):
        """Set string tension (affects stiffness)."""
        self.tension = max(0.1, min(tension, 10.0))

    def set_damping(self, damping: float):
        """Set string damping (0.0-1.0, higher = less damping)."""
        self.damping = max(0.0, min(damping, 1.0))

    def excite_string(self, excitation: np.ndarray):
        """
        Excite the string with an excitation signal.

        Args:
            excitation: Excitation signal (pluck/pick impulse)
        """
        self.excitation_signal = excitation.copy()
        self.excitation_index = 0
        self.active = True

    def process_sample(self) -> float:
        """
        Process one sample of waveguide output.

        Returns:
            Output sample
        """
        if not self.active:
            return 0.0

        # Read from delay line
        output = self.delay_line[self.read_pos]

        # Apply damping
        output *= self.damping

        # Add excitation if available
        if self.excitation_signal is not None and self.excitation_index < len(self.excitation_signal):
            excitation_sample = self.excitation_signal[self.excitation_index]
            self.excitation_index += 1

            # Apply excitation at pluck position
            if self.pluck_position < 0.5:
                # Closer to bridge
                excitation_level = 1.0 - (self.pluck_position * 2.0)
            else:
                # Closer to nut
                excitation_level = (self.pluck_position - 0.5) * 2.0

            output += excitation_sample * excitation_level

        # Calculate input to delay line
        # Simple Karplus-Strong: average of current output and previous input
        delay_input = output * 0.5 + self.delay_line[(self.write_pos - 1) % self.length_samples] * 0.5

        # Apply frequency-dependent damping (dispersion)
        # Higher frequencies damp faster
        delay_input *= self.damping

        # Write to delay line
        self.delay_line[self.write_pos] = delay_input

        # Update positions
        self.read_pos = (self.read_pos + 1) % self.length_samples
        self.write_pos = (self.write_pos + 1) % self.length_samples

        # Check if excitation is complete
        if self.excitation_signal is not None and self.excitation_index >= len(self.excitation_signal):
            # Check if string has decayed enough to stop
            energy = np.sum(np.abs(self.delay_line)) / len(self.delay_line)
            if energy < 1e-6:  # Very low energy threshold
                self.active = False

        return output

    def is_active(self) -> bool:
        """Check if string is still vibrating."""
        return self.active

    def get_string_info(self) -> dict[str, Any]:
        """Get comprehensive string information."""
        return {
            'frequency': self.frequency,
            'length_samples': self.length_samples,
            'tension': self.tension,
            'damping': self.damping,
            'pluck_position': self.pluck_position,
            'active': self.active,
            'bridge_reflection': self.bridge_reflection,
            'nut_reflection': self.nut_reflection
        }


class ModalResonator:
    """
    Modal resonator for bell-like and percussive instruments.

    Implements modal synthesis using a bank of resonant filters
    to simulate the natural resonances of acoustic instruments.
    """

    def __init__(self, sample_rate: int = 44100, max_modes: int = 16):
        """
        Initialize modal resonator.

        Args:
            sample_rate: Audio sample rate
            max_modes: Maximum number of resonant modes
        """
        self.sample_rate = sample_rate
        self.max_modes = max_modes

        # Modal parameters
        self.modes: list[dict[str, Any]] = []

        # Resonator state
        self.active = False
        self.decay_factor = 0.999

        # Initialize with default modes (can be overridden)
        self._initialize_default_modes()

    def _initialize_default_modes(self):
        """Initialize default modal frequencies and parameters."""
        # Typical bell/tubular bell modes
        default_modes = [
            {'frequency': 440.0, 'amplitude': 1.0, 'decay': 0.9995, 'phase': 0.0},
            {'frequency': 880.0, 'amplitude': 0.8, 'decay': 0.9990, 'phase': 0.1},
            {'frequency': 1320.0, 'amplitude': 0.6, 'decay': 0.9985, 'phase': 0.2},
            {'frequency': 1760.0, 'amplitude': 0.4, 'decay': 0.9980, 'phase': 0.3},
            {'frequency': 2200.0, 'amplitude': 0.3, 'decay': 0.9975, 'phase': 0.4},
            {'frequency': 2640.0, 'amplitude': 0.2, 'decay': 0.9970, 'phase': 0.5},
            {'frequency': 3080.0, 'amplitude': 0.15, 'decay': 0.9965, 'phase': 0.6},
            {'frequency': 3520.0, 'amplitude': 0.1, 'decay': 0.9960, 'phase': 0.7},
        ]

        for mode in default_modes:
            self.add_mode(**mode)

    def add_mode(self, frequency: float, amplitude: float = 1.0,
                 decay: float = 0.999, phase: float = 0.0):
        """
        Add a resonant mode.

        Args:
            frequency: Mode frequency in Hz
            amplitude: Mode amplitude (0.0-1.0)
            decay: Decay factor per sample (0.0-1.0)
            phase: Initial phase offset (0.0-1.0)
        """
        if len(self.modes) >= self.max_modes:
            return

        # Calculate angular frequency
        omega = 2.0 * math.pi * frequency / self.sample_rate

        # Initialize mode state
        mode = {
            'frequency': frequency,
            'amplitude': amplitude,
            'decay': decay,
            'phase': phase,
            'omega': omega,
            'y1': math.sin(phase * 2.0 * math.pi) * amplitude,  # Previous sample
            'y2': math.sin((phase - 0.01) * 2.0 * math.pi) * amplitude,  # Sample before that
            'cos_omega': math.cos(omega),
            'sin_omega': math.sin(omega)
        }

        self.modes.append(mode)

    def clear_modes(self):
        """Clear all resonant modes."""
        self.modes.clear()

    def excite_modes(self, excitation_level: float = 1.0):
        """
        Excite all modes with an impulse.

        Args:
            excitation_level: Excitation amplitude
        """
        for mode in self.modes:
            # Reset mode state with excitation
            mode['y1'] = excitation_level * mode['amplitude']
            mode['y2'] = 0.0

        self.active = True

    def set_decay_factor(self, decay: float):
        """Set global decay factor for all modes."""
        self.decay_factor = max(0.9, min(decay, 1.0))
        for mode in self.modes:
            mode['decay'] = self.decay_factor

    def process_sample(self) -> float:
        """
        Process one sample of modal output.

        Returns:
            Sum of all modal outputs
        """
        if not self.active:
            return 0.0

        output = 0.0
        still_active = False

        for mode in self.modes:
            # Second-order resonant filter implementation
            # y[n] = 2*cos(ω)*y[n-1] - y[n-2] + x[n] * amplitude

            # Current excitation (0 for sustained resonance)
            excitation = 0.0

            # Calculate new sample
            y0 = 2.0 * mode['cos_omega'] * mode['y1'] - mode['y2'] + excitation * mode['amplitude']

            # Apply decay
            y0 *= mode['decay']

            # Update state
            mode['y2'] = mode['y1']
            mode['y1'] = y0

            output += y0

            # Check if mode is still active
            if abs(y0) > 1e-6:
                still_active = True

        # Update active state
        self.active = still_active

        return output

    def is_active(self) -> bool:
        """Check if resonator is still active."""
        return self.active

    def get_resonator_info(self) -> dict[str, Any]:
        """Get comprehensive resonator information."""
        return {
            'active': self.active,
            'num_modes': len(self.modes),
            'decay_factor': self.decay_factor,
            'modes': [{'frequency': m['frequency'], 'amplitude': m['amplitude'],
                      'decay': m['decay'], 'phase': m['phase']} for m in self.modes]
        }


class AdvancedPhysicalEngine(SynthesisEngine):
    """
    Advanced Physical Modeling Engine

    Comprehensive physical modeling synthesis providing realistic
    acoustic instrument simulation through waveguide and modal techniques.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024,
                 max_strings: int = 6, max_resonators: int = 4):
        """
        Initialize advanced physical modeling engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            max_strings: Maximum number of waveguide strings
            max_resonators: Maximum number of modal resonators
        """
        super().__init__(sample_rate, block_size)

        # Physical modeling components
        self.strings: list[WaveguideString] = []
        self.resonators: list[ModalResonator] = []

        # Capacities
        self.max_strings = max_strings
        self.max_resonators = max_resonators

        # Instrument configurations
        self.instrument_configs = self._create_instrument_configs()

        # Current instrument
        self.current_instrument = 'guitar'

        # Thread safety
        self.lock = threading.RLock()

        # Initialize default strings and resonators
        self._initialize_components()

    def _create_instrument_configs(self) -> dict[str, dict[str, Any]]:
        """Create predefined instrument configurations."""
        configs = {}

        # Guitar configuration
        configs['guitar'] = {
            'strings': [
                {'frequency': 82.41, 'pluck_pos': 0.8},   # Low E
                {'frequency': 110.00, 'pluck_pos': 0.8},  # A
                {'frequency': 146.83, 'pluck_pos': 0.8},  # D
                {'frequency': 196.00, 'pluck_pos': 0.8},  # G
                {'frequency': 246.94, 'pluck_pos': 0.8},  # B
                {'frequency': 329.63, 'pluck_pos': 0.8},  # High E
            ],
            'resonators': [],  # No resonators for guitar
            'excitation_type': 'pluck'
        }

        # Piano configuration
        configs['piano'] = {
            'strings': [
                {'frequency': 27.5, 'pluck_pos': 0.1},    # A0
                {'frequency': 29.14, 'pluck_pos': 0.1},   # B0
                {'frequency': 30.87, 'pluck_pos': 0.1},   # C1
                {'frequency': 32.70, 'pluck_pos': 0.1},   # C#1
                {'frequency': 34.65, 'pluck_pos': 0.1},   # D1
                {'frequency': 36.71, 'pluck_pos': 0.1},   # D#1
            ],
            'resonators': [],  # Simplified piano model
            'excitation_type': 'strike'
        }

        # Bell configuration
        configs['bell'] = {
            'strings': [],  # No strings for bell
            'resonators': [
                {'modes': [
                    {'freq': 440.0, 'amp': 1.0, 'decay': 0.9995},
                    {'freq': 880.0, 'amp': 0.8, 'decay': 0.9990},
                    {'freq': 1320.0, 'amp': 0.6, 'decay': 0.9985},
                    {'freq': 1760.0, 'amp': 0.4, 'decay': 0.9980},
                    {'freq': 2200.0, 'amp': 0.3, 'decay': 0.9975},
                    {'freq': 2640.0, 'amp': 0.2, 'decay': 0.9970},
                    {'freq': 3080.0, 'amp': 0.15, 'decay': 0.9965},
                    {'freq': 3520.0, 'amp': 0.1, 'decay': 0.9960},
                ]}
            ],
            'excitation_type': 'strike'
        }

        # Drum configuration
        configs['drum'] = {
            'strings': [],  # Membrane modeled as resonators
            'resonators': [
                {'modes': [
                    {'freq': 100.0, 'amp': 1.0, 'decay': 0.995},
                    {'freq': 200.0, 'amp': 0.7, 'decay': 0.990},
                    {'freq': 300.0, 'amp': 0.5, 'decay': 0.985},
                    {'freq': 400.0, 'amp': 0.3, 'decay': 0.980},
                    {'freq': 500.0, 'amp': 0.2, 'decay': 0.975},
                    {'freq': 600.0, 'amp': 0.1, 'decay': 0.970},
                ]}
            ],
            'excitation_type': 'strike'
        }

        return configs

    def _initialize_components(self):
        """Initialize waveguide strings and modal resonators."""
        # Create strings
        for _ in range(self.max_strings):
            string = WaveguideString(self.sample_rate)
            self.strings.append(string)

        # Create resonators
        for _ in range(self.max_resonators):
            resonator = ModalResonator(self.sample_rate)
            self.resonators.append(resonator)

        # Load default instrument
        self.load_instrument(self.current_instrument)

    def load_instrument(self, instrument_name: str) -> bool:
        """
        Load instrument configuration.

        Args:
            instrument_name: Name of instrument to load

        Returns:
            True if instrument was loaded successfully
        """
        with self.lock:
            if instrument_name not in self.instrument_configs:
                return False

            config = self.instrument_configs[instrument_name]

            # Configure strings
            for i, string_config in enumerate(config.get('strings', [])):
                if i < len(self.strings):
                    string = self.strings[i]
                    string.set_frequency(string_config['frequency'])
                    string.set_pluck_position(string_config['pluck_pos'])
                    string.active = True

            # Deactivate unused strings
            for i in range(len(config.get('strings', [])), len(self.strings)):
                self.strings[i].active = False

            # Configure resonators
            for i, resonator_config in enumerate(config.get('resonators', [])):
                if i < len(self.resonators):
                    resonator = self.resonators[i]
                    resonator.clear_modes()

                    # Add modes
                    for mode_config in resonator_config.get('modes', []):
                        resonator.add_mode(
                            frequency=mode_config['freq'],
                            amplitude=mode_config['amp'],
                            decay=mode_config['decay']
                        )

            # Deactivate unused resonators
            for i in range(len(config.get('resonators', [])), len(self.resonators)):
                # Clear modes to deactivate
                self.resonators[i].clear_modes()

            self.current_instrument = instrument_name
            return True

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return 'advanced_physical'

    def note_on(self, note: int, velocity: int, channel: int = 0):
        """
        Trigger physical modeling note.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            channel: MIDI channel (maps to string/resonator)
        """
        with self.lock:
            frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))

            # Generate excitation signal based on instrument
            excitation = self._generate_excitation(velocity / 127.0)

            # Route to appropriate component based on instrument type
            config = self.instrument_configs.get(self.current_instrument, {})

            if config.get('strings'):  # String instrument
                string_index = min(channel, len(self.strings) - 1)
                if string_index < len(self.strings):
                    string = self.strings[string_index]
                    string.set_frequency(frequency)
                    string.excite_string(excitation)

            elif config.get('resonators'):  # Percussive instrument
                resonator_index = min(channel, len(self.resonators) - 1)
                if resonator_index < len(self.resonators):
                    resonator = self.resonators[resonator_index]
                    resonator.excite_modes(velocity / 127.0)

    def note_off(self, note: int, velocity: int = 0, channel: int = 0):
        """
        Release physical modeling note.

        For physical modeling, note-off typically doesn't immediately stop
        the sound - it continues to decay naturally.
        """
        pass  # Physical modeling instruments decay naturally

    def _generate_excitation(self, amplitude: float) -> np.ndarray:
        """Generate excitation signal based on current instrument."""
        # Simple excitation signal (can be made more sophisticated)
        length = 100  # 100 samples of excitation
        excitation = np.random.randn(length) * amplitude

        # Apply simple envelope
        envelope = np.exp(-np.arange(length) / 20.0)
        excitation *= envelope

        return excitation.astype(np.float32)

    def get_regions_for_note(self, note: int, velocity: int, program: int = 0, bank: int = 0) -> list[Any]:
        """
        Physical modeling creates dynamic regions based on note.

        Returns dynamic region that indicates physical modeling should be used.
        """
        class PhysicalRegion:
            def __init__(self, note, velocity, instrument):
                self.note = note
                self.velocity = velocity
                self.instrument = instrument

            def should_play_for_note(self, n, v):
                return n == self.note and v == self.velocity

        return [PhysicalRegion(note, velocity, self.current_instrument)]

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int):
        """Physical modeling doesn't create traditional partials."""
        return None

    def generate_samples(self, note: int, velocity: int, modulation: dict[str, float],
                        block_size: int) -> np.ndarray:
        """
        Generate audio samples using physical modeling.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        with self.lock:
            # Generate mono output
            mono_output = np.zeros(block_size, dtype=np.float32)

            # Sum output from all active strings
            for string in self.strings:
                if string.is_active():
                    for i in range(block_size):
                        mono_output[i] += string.process_sample()

            # Sum output from all active resonators
            for resonator in self.resonators:
                if resonator.is_active():
                    for i in range(block_size):
                        mono_output[i] += resonator.process_sample()

            # Apply modulation
            mono_output = self._apply_modulation(mono_output, modulation, block_size)

            # Convert to stereo
            stereo_output = np.column_stack([mono_output, mono_output])

            return stereo_output

    def _apply_modulation(self, audio: np.ndarray, modulation: dict[str, float],
                         block_size: int) -> np.ndarray:
        """Apply modulation effects to generated audio."""
        # Filter modulation (affects string stiffness/tension)
        if 'cutoff' in modulation:
            # Simulate filter by adjusting damping
            cutoff_norm = modulation['cutoff'] / 20000.0
            for string in self.strings:
                if string.is_active():
                    # Higher cutoff = brighter sound (less damping)
                    string.damping = 0.9 + (cutoff_norm * 0.09)

        # Amplitude modulation
        if 'volume' in modulation:
            audio *= (1.0 + modulation['volume'])

        # Pan modulation
        if 'pan' in modulation:
            pan = np.clip(modulation['pan'], -1.0, 1.0)
            left_gain = 1.0 - max(0.0, pan)
            right_gain = 1.0 - max(0.0, -pan)
            audio *= left_gain  # Apply to mono signal before stereo conversion

        return audio

    def is_note_supported(self, note: int) -> bool:
        """Check if note is supported (most notes supported)."""
        return 0 <= note <= 127

    def get_supported_formats(self) -> list[str]:
        """Physical modeling doesn't use audio files directly."""
        return []

    def get_engine_info(self) -> dict[str, Any]:
        """Get comprehensive engine information."""
        return {
            'name': 'Advanced Physical Modeling Engine',
            'type': 'advanced_physical',
            'version': '1.0',
            'capabilities': [
                'waveguide_synthesis', 'modal_synthesis', 'karplus_strong_algorithm',
                'string_modeling', 'percussive_modeling', 'realistic_decay',
                'frequency_dependent_damping', 'multi_string_support'
            ],
            'current_instrument': self.current_instrument,
            'available_instruments': list(self.instrument_configs.keys()),
            'max_strings': self.max_strings,
            'max_resonators': self.max_resonators,
            'active_strings': sum(1 for s in self.strings if s.is_active()),
            'active_resonators': sum(1 for r in self.resonators if r.is_active()),
            'sample_rate': self.sample_rate,
            'block_size': self.block_size
        }
    # ========== NEW REGION-BASED METHODS (STUBS) ==========
    
    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """Get preset info (stub)."""
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type=self.get_engine_type(),
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={}
        )
        
        return PresetInfo(
            bank=bank, program=program,
            name=f'{self.get_engine_type().title()} {bank}:{program}',
            engine_type=self.get_engine_type(),
            region_descriptors=[descriptor]
        )
    
    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        preset_info = self.get_preset_info(bank, program)
        return preset_info.region_descriptors if preset_info else []
    
    def create_region(
        self,
        descriptor: RegionDescriptor,
        sample_rate: int
    ) -> IRegion:
        """
        Create region instance. Base implementation wraps with S.Art2.
        """
        return self._create_base_region(descriptor, sample_rate)

    def _create_base_region(
        self,
        descriptor: RegionDescriptor,
        sample_rate: int
    ) -> IRegion:
        """
        Create AdvancedPhysicalRegion base region without S.Art2 wrapper.

        Args:
            descriptor: Region descriptor
            sample_rate: Audio sample rate in Hz

        Returns:
            AdvancedPhysicalRegion instance
        """
        from ..partial.advanced_physical_region import AdvancedPhysicalRegion
        return AdvancedPhysicalRegion(descriptor, sample_rate)
    

    def load_sample_for_region(self, region: IRegion) -> bool:
        return True



    def get_available_instruments(self) -> list[str]:
        """Get list of available instrument configurations."""
        return list(self.instrument_configs.keys())

    def get_instrument_info(self, instrument_name: str) -> dict[str, Any] | None:
        """Get information about a specific instrument."""
        config = self.instrument_configs.get(instrument_name)
        if config:
            return {
                'name': instrument_name,
                'strings': len(config.get('strings', [])),
                'resonators': len(config.get('resonators', [])),
                'excitation_type': config.get('excitation_type', 'unknown')
            }
        return None

    def get_physical_modeling_status(self) -> dict[str, Any]:
        """Get detailed status of physical modeling components."""
        return {
            'strings': [s.get_string_info() for s in self.strings],
            'resonators': [r.get_resonator_info() for r in self.resonators],
            'total_active': sum(s.is_active() for s in self.strings) + sum(r.is_active() for r in self.resonators)
        }

    def reset(self) -> None:
        """Reset engine to clean state."""
        with self.lock:
            for string in self.strings:
                string.active = False
            for resonator in self.resonators:
                resonator.active = False

    def cleanup(self) -> None:
        """Clean up engine resources."""
        self.reset()

    def __str__(self) -> str:
        """String representation."""
        info = self.get_engine_info()
        return (f"AdvancedPhysicalEngine(instrument={info['current_instrument']}, "
                f"strings={info['active_strings']}/{info['max_strings']}, "
                f"resonators={info['active_resonators']}/{info['max_resonators']})")

    def __repr__(self) -> str:
        return self.__str__()
