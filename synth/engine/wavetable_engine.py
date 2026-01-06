"""
Wavetable Synthesis Engine

Efficient, high-quality wavetable synthesis with real-time morphing capabilities.
Provides wavetable-based synthesis as an alternative to sample playback.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import math

from .synthesis_engine import SynthesisEngine
from ..audio.sample_manager import PyAVSampleManager
from ..partial.partial import SynthesisPartial
from ..partial.region import Region
from .plugins.plugin_registry import get_global_plugin_registry
from .plugins.base_plugin import PluginLoadContext, SynthesisFeaturePlugin


class Wavetable:
    """
    Single wavetable with interpolation and morphing capabilities.

    A wavetable is a single cycle waveform stored at high resolution
    for efficient playback with pitch control.
    """

    def __init__(self, data: np.ndarray, sample_rate: int = 44100, name: str = "unnamed"):
        """
        Initialize wavetable from audio data.

        Args:
            data: Audio waveform data (mono)
            sample_rate: Original sample rate
            name: Wavetable name for identification
        """
        self.name = name
        self.sample_rate = sample_rate

        # Ensure mono data
        if data.ndim > 1:
            data = data[:, 0]  # Take first channel

        # Remove DC offset
        data = data - np.mean(data)

        # Normalize to prevent clipping
        max_val = np.max(np.abs(data))
        if max_val > 0:
            data = data / max_val * 0.9  # Leave some headroom

        self.data = data.astype(np.float32)
        self.length = len(data)

        # Pre-compute for efficiency
        self._build_interpolation_tables()

    def _build_interpolation_tables(self):
        """Build interpolation tables for efficient playback."""
        # Linear interpolation is sufficient for wavetable synthesis
        # More advanced interpolation can be added later if needed
        pass

    def get_sample(self, phase: float) -> float:
        """
        Get sample at specified phase (0.0 to 1.0).

        Args:
            phase: Phase position (0.0 to 1.0)

        Returns:
            Interpolated sample value
        """
        # Convert phase to index
        index = phase * (self.length - 1)

        # Linear interpolation
        index_int = int(index)
        frac = index - index_int

        # Handle wraparound
        next_index = (index_int + 1) % self.length

        # Interpolate
        sample1 = self.data[index_int]
        sample2 = self.data[next_index]

        return sample1 + (sample2 - sample1) * frac

    def get_samples(self, phases: np.ndarray) -> np.ndarray:
        """
        Get multiple samples efficiently.

        Args:
            phases: Array of phase positions

        Returns:
            Array of interpolated samples
        """
        # Vectorized linear interpolation
        indices = phases * (self.length - 1)

        # Split into integer and fractional parts
        index_int = indices.astype(np.int32)
        frac = indices - index_int

        # Handle wraparound
        next_index = (index_int + 1) % self.length

        # Interpolate
        sample1 = self.data[index_int % self.length]
        sample2 = self.data[next_index % self.length]

        return sample1 + (sample2 - sample1) * frac


class WavetableOscillator:
    """
    Wavetable oscillator with frequency control and modulation.

    Provides efficient wavetable playback with pitch modulation,
    amplitude control, and multi-timbral capabilities.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.wavetable: Optional[Wavetable] = None

        # Oscillator state
        self.phase = 0.0
        self.frequency = 440.0
        self.amplitude = 1.0

        # Modulation inputs
        self.frequency_mod = 0.0
        self.amplitude_mod = 0.0
        self.wavetable_position = 0.0  # For wavetable morphing

        # Voice state
        self.active = False
        self.note = 60
        self.velocity = 100

    def set_wavetable(self, wavetable: Wavetable):
        """Set the wavetable for this oscillator."""
        self.wavetable = wavetable

    def set_frequency(self, frequency: float):
        """Set base frequency in Hz."""
        self.frequency = max(20.0, min(frequency, self.sample_rate / 2.0))

    def set_note(self, midi_note: int, velocity: int = 100):
        """Set oscillator to specific MIDI note."""
        self.note = midi_note
        self.velocity = velocity
        self.active = True

        # Convert MIDI note to frequency
        self.frequency = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

        # Apply velocity to amplitude
        self.amplitude = (velocity / 127.0) ** 0.3  # Slight compression

    def set_amplitude(self, amplitude: float):
        """Set amplitude (0.0 to 1.0)."""
        self.amplitude = max(0.0, min(amplitude, 1.0))

    def update_modulation(self, freq_mod: float = 0.0, amp_mod: float = 0.0,
                         wt_pos: float = 0.0):
        """Update modulation inputs."""
        self.frequency_mod = freq_mod
        self.amplitude_mod = amp_mod
        self.wavetable_position = wt_pos

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this oscillator.

        Args:
            block_size: Number of samples to generate

        Returns:
            Audio buffer (block_size,)
        """
        if not self.wavetable or not self.active:
            return np.zeros(block_size, dtype=np.float32)

        # Calculate phase increment
        base_increment = self.frequency / self.sample_rate
        modulated_freq = self.frequency * (1.0 + self.frequency_mod)
        phase_increment = modulated_freq / self.sample_rate

        # Generate phases
        phases = np.zeros(block_size)
        current_phase = self.phase

        for i in range(block_size):
            phases[i] = current_phase
            current_phase = (current_phase + phase_increment) % 1.0

        # Update oscillator phase
        self.phase = current_phase

        # Get samples from wavetable
        samples = self.wavetable.get_samples(phases)

        # Apply amplitude modulation
        modulated_amplitude = self.amplitude * (1.0 + self.amplitude_mod)
        samples *= modulated_amplitude

        return samples.astype(np.float32)

    def is_active(self) -> bool:
        """Check if oscillator is active."""
        return self.active

    def note_off(self):
        """Trigger note off (oscillator will continue until released)."""
        self.active = False

    def reset(self):
        """Reset oscillator state."""
        self.phase = 0.0
        self.frequency_mod = 0.0
        self.amplitude_mod = 0.0
        self.active = False


class WavetableBank:
    """
    Bank of wavetables with morphing capabilities.

    Manages multiple wavetables and provides crossfading/morphing
    between different wavetables for rich timbral control.
    """

    def __init__(self, max_wavetables: int = 64):
        self.max_wavetables = max_wavetables
        self.wavetables: Dict[str, Wavetable] = {}
        self.morph_groups: Dict[str, List[str]] = {}

    def add_wavetable(self, wavetable: Wavetable, name: str) -> bool:
        """
        Add wavetable to bank.

        Args:
            wavetable: Wavetable to add
            name: Unique name for the wavetable

        Returns:
            True if added successfully
        """
        if len(self.wavetables) >= self.max_wavetables:
            return False

        self.wavetables[name] = wavetable
        return True

    def load_wavetable_from_file(self, file_path: str, name: str,
                                sample_manager: Optional[PyAVSampleManager] = None) -> bool:
        """
        Load wavetable from audio file.

        Args:
            file_path: Path to audio file
            name: Name for the wavetable
            sample_manager: Optional sample manager for loading

        Returns:
            True if loaded successfully
        """
        try:
            if sample_manager:
                sample = sample_manager.load_sample(file_path)
                data = sample.data
                sample_rate = sample.sample_rate
            else:
                # Basic WAV loading implementation
                data, sample_rate = self._load_wav_file(file_path)

            # Extract single cycle (assume file contains one cycle)
            # In practice, you might want to analyze the file for cycle boundaries
            wavetable = Wavetable(data, sample_rate, name)
            return self.add_wavetable(wavetable, name)

        except Exception as e:
            print(f"Failed to load wavetable from {file_path}: {e}")
            return False

    def _load_wav_file(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Basic WAV file loader implementation.

        Args:
            file_path: Path to WAV file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        with open(file_path, 'rb') as f:
            # Read RIFF header
            riff_header = f.read(12)
            if riff_header[:4] != b'RIFF' or riff_header[8:12] != b'WAVE':
                raise ValueError("Not a valid WAV file")

            # Find fmt and data chunks
            fmt_chunk = None
            data_chunk = None

            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    break

                chunk_id = chunk_header[:4]
                chunk_size = int.from_bytes(chunk_header[4:8], byteorder='little')

                if chunk_id == b'fmt ':
                    fmt_chunk = f.read(chunk_size)
                elif chunk_id == b'data':
                    data_chunk = f.read(chunk_size)
                    break  # Data chunk is usually last
                else:
                    # Skip unknown chunks
                    f.seek(chunk_size, 1)

            if fmt_chunk is None or data_chunk is None:
                raise ValueError("WAV file missing fmt or data chunk")

            # Parse fmt chunk
            audio_format = int.from_bytes(fmt_chunk[0:2], byteorder='little')
            if audio_format != 1:
                raise ValueError("Only PCM WAV files are supported")

            num_channels = int.from_bytes(fmt_chunk[2:4], byteorder='little')
            sample_rate = int.from_bytes(fmt_chunk[4:8], byteorder='little')
            bits_per_sample = int.from_bytes(fmt_chunk[14:16], byteorder='little')

            if bits_per_sample not in [8, 16, 24, 32]:
                raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")

            # Parse data chunk
            data = None
            if bits_per_sample == 8:
                dtype = np.uint8
                data = np.frombuffer(data_chunk, dtype=dtype)
                # Convert unsigned 8-bit to signed float
                data = (data.astype(np.float32) - 128.0) / 128.0
            elif bits_per_sample == 16:
                dtype = np.int16
                data = np.frombuffer(data_chunk, dtype=dtype)
                data = data.astype(np.float32) / 32768.0
            elif bits_per_sample == 24:
                # 24-bit is tricky - need to handle manually
                data = np.zeros(len(data_chunk) // 3, dtype=np.float32)
                for i in range(len(data_chunk) // 3):
                    # Read 3 bytes as 24-bit signed integer
                    bytes_24 = data_chunk[i*3:(i+1)*3]
                    value = int.from_bytes(bytes_24, byteorder='little', signed=True)
                    # Convert to float (-1.0 to 1.0)
                    data[i] = value / 8388608.0
            elif bits_per_sample == 32:
                dtype = np.int32
                data = np.frombuffer(data_chunk, dtype=dtype)
                data = data.astype(np.float32) / 2147483648.0

            if data is None:
                raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")

            # Handle multi-channel (take first channel for wavetable)
            if num_channels > 1:
                data = data.reshape(-1, num_channels)[:, 0]

            return data, sample_rate

    def create_wavetable_from_waveform(self, waveform_type: str, name: str,
                                      size: int = 2048, harmonics: int = 16) -> bool:
        """
        Create wavetable from mathematical waveform.

        Args:
            waveform_type: Type of waveform ('sine', 'triangle', 'square', 'sawtooth')
            name: Name for the wavetable
            size: Wavetable size in samples
            harmonics: Number of harmonics for complex waveforms

        Returns:
            True if created successfully
        """
        try:
            # Generate single cycle
            t = np.linspace(0, 2 * np.pi, size, endpoint=False)

            if waveform_type == 'sine':
                data = np.sin(t)
            elif waveform_type == 'triangle':
                data = np.abs((t % (2 * np.pi)) - np.pi) / (np.pi / 2) - 1
            elif waveform_type == 'square':
                data = np.sign(np.sin(t))
            elif waveform_type == 'sawtooth':
                data = (t % (2 * np.pi)) / np.pi - 1
            elif waveform_type == 'noise':
                data = np.random.uniform(-1, 1, size)
            else:
                # Default to sine
                data = np.sin(t)

            wavetable = Wavetable(data, 44100, name)
            return self.add_wavetable(wavetable, name)

        except Exception as e:
            print(f"Failed to create wavetable '{name}': {e}")
            return False

    def get_wavetable(self, name: str) -> Optional[Wavetable]:
        """Get wavetable by name."""
        return self.wavetables.get(name)

    def get_morphed_wavetable(self, sources: List[str], position: float) -> Optional[Wavetable]:
        """
        Get morphed wavetable between multiple sources.

        Args:
            sources: List of wavetable names to morph between
            position: Morph position (0.0 = first source, 1.0 = last source)

        Returns:
            Morphed wavetable or None if sources not found
        """
        if not sources or len(sources) < 2:
            return self.get_wavetable(sources[0]) if sources else None

        # Get source wavetables
        source_tables = []
        for name in sources:
            wt = self.get_wavetable(name)
            if wt:
                source_tables.append(wt)
            else:
                return None

        # Simple linear morphing between first and last
        # More sophisticated morphing could interpolate between all sources
        wt1 = source_tables[0]
        wt2 = source_tables[-1]

        # Ensure same length for morphing
        min_length = min(wt1.length, wt2.length)
        morphed_data = (wt1.data[:min_length] * (1.0 - position) +
                       wt2.data[:min_length] * position)

        morphed_name = f"morph_{sources[0]}_{sources[-1]}_{position:.2f}"
        return Wavetable(morphed_data, wt1.sample_rate, morphed_name)

    def create_morph_group(self, group_name: str, wavetable_names: List[str]):
        """Create a morph group for easy access."""
        self.morph_groups[group_name] = wavetable_names.copy()

    def get_morph_group(self, group_name: str) -> List[str]:
        """Get wavetable names in a morph group."""
        return self.morph_groups.get(group_name, [])

    def list_wavetables(self) -> List[str]:
        """Get list of all wavetable names."""
        return list(self.wavetables.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get wavetable bank statistics."""
        total_samples = sum(wt.length for wt in self.wavetables.values())
        avg_length = total_samples / len(self.wavetables) if self.wavetables else 0

        return {
            'total_wavetables': len(self.wavetables),
            'total_samples': total_samples,
            'average_length': avg_length,
            'morph_groups': len(self.morph_groups),
            'memory_usage_mb': total_samples * 4 / (1024 * 1024)  # float32 = 4 bytes
        }


class WavetablePartial(SynthesisPartial):
    """
    Wavetable synthesis partial that wraps a WavetableOscillator.

    Implements the SynthesisPartial interface for wavetable-based synthesis.
    """

    def __init__(self, params: Dict[str, Any], sample_rate: int,
                 wavetable_bank: WavetableBank):
        """
        Initialize wavetable partial.

        Args:
            params: Partial parameters
            sample_rate: Audio sample rate
            wavetable_bank: Reference to wavetable bank
        """
        super().__init__(params, sample_rate)
        self.wavetable_bank = wavetable_bank
        self.oscillator = WavetableOscillator(sample_rate)

        # Configure oscillator
        self._configure_oscillator()

    def _configure_oscillator(self):
        """Configure the oscillator based on current parameters."""
        # Set wavetable
        wt_name = self.params.get('wavetable', 'sine')
        wavetable = self.wavetable_bank.get_wavetable(wt_name)
        if wavetable:
            self.oscillator.set_wavetable(wavetable)

        # Set other parameters
        if 'frequency' in self.params:
            self.oscillator.set_frequency(self.params['frequency'])
        if 'amplitude' in self.params:
            self.oscillator.set_amplitude(self.params['amplitude'])

    def generate_samples(self, block_size: int, modulation: Dict[str, float]) -> np.ndarray:
        """
        Generate audio samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size * 2,)
        """
        if not self.active:
            return np.zeros(block_size * 2, dtype=np.float32)

        # Apply modulation
        freq_mod = modulation.get('pitch', 0.0) / 1200.0  # Convert cents to ratio
        amp_mod = modulation.get('volume', 0.0)
        wt_pos = modulation.get('timbre', 0.0)

        self.oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

        # Generate mono samples
        mono_samples = self.oscillator.generate_samples(block_size)

        # Convert to stereo (duplicate mono channel)
        stereo_samples = np.zeros(block_size * 2, dtype=np.float32)
        stereo_samples[0::2] = mono_samples  # Left channel
        stereo_samples[1::2] = mono_samples  # Right channel

        return stereo_samples

    def is_active(self) -> bool:
        """Check if partial is active."""
        return self.active and self.oscillator.is_active()

    def note_on(self, velocity: int, note: int) -> None:
        """Handle note-on event."""
        self.active = True
        self.oscillator.set_note(note, velocity)

    def note_off(self) -> None:
        """Handle note-off event."""
        self.oscillator.note_off()
        # Keep partial active for release if needed

    def apply_modulation(self, modulation: Dict[str, float]) -> None:
        """Apply modulation changes."""
        # Update oscillator modulation
        freq_mod = modulation.get('pitch', 0.0) / 1200.0
        amp_mod = modulation.get('volume', 0.0)
        wt_pos = modulation.get('timbre', 0.0)

        self.oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        self.oscillator.reset()

    def update_parameter(self, param_name: str, value: Any) -> None:
        """Update a parameter and reconfigure if needed."""
        super().update_parameter(param_name, value)

        # Reconfigure oscillator if relevant parameters changed
        if param_name in ['wavetable', 'frequency', 'amplitude']:
            self._configure_oscillator()


class WavetableRegion(Region):
    """
    Wavetable region implementation.

    A region that uses wavetable synthesis with oscillator-based playback.
    """

    def __init__(self, region_params: Dict[str, Any], wavetable_bank: WavetableBank):
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
        wt_name = 'sine'  # Default
        if hasattr(self, 'sample_path') and self.sample_path:
            # Try to load wavetable from file
            if self.wavetable_bank.load_wavetable_from_file(self.sample_path, self.sample_path):
                wt_name = self.sample_path

        wavetable = self.wavetable_bank.get_wavetable(wt_name)
        if wavetable:
            self.oscillator.set_wavetable(wavetable)

    def _create_envelope(self, env_type: str, params: Dict[str, float]):
        """
        Create envelope for this region.

        Args:
            env_type: Type of envelope ('amp', 'filter', 'pitch')
            params: Envelope parameters

        Returns:
            Configured envelope or None
        """
        try:
            from ..core.envelope import UltraFastADSREnvelope

            # Create envelope with region parameters
            envelope = UltraFastADSREnvelope(
                attack=params.get('attack', 0.01),
                decay=params.get('decay', 0.1),
                sustain=params.get('sustain', 0.8),
                release=params.get('release', 0.2),
                sample_rate=44100
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
            from ..core.filter import BiquadFilter

            # Map SFZ filter types to internal types
            filter_map = {
                'lpf_1p': 'lowpass_1p',
                'lpf_2p': 'lowpass_2p',
                'hpf_1p': 'highpass_1p',
                'hpf_2p': 'highpass_2p',
                'bpf_2p': 'bandpass',
                'notch': 'notch'
            }

            internal_type = filter_map.get(filter_type, 'lowpass_2p')

            # Create filter
            filter_instance = BiquadFilter(
                filter_type=internal_type,
                cutoff=cutoff,
                resonance=resonance,
                sample_rate=44100
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
            from ..modulation.advanced_matrix import AdvancedModulationMatrix

            # Create modulation matrix with reasonable defaults
            matrix = AdvancedModulationMatrix(max_routes=16)  # Smaller for regions

            # Add some default modulation routes based on region parameters
            # These would be configured based on SFZ modulation opcodes

            return matrix

        except Exception as e:
            print(f"Failed to create modulation matrix: {e}")
            return None

    def generate_samples(self, block_size: int, modulation: Dict[str, float]) -> np.ndarray:
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
        freq_mod = modulation.get('pitch', 0.0) / 1200.0
        amp_mod = modulation.get('volume', 0.0)
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


class WavetableEngine(SynthesisEngine):
    """
    Wavetable Synthesis Engine

    Provides efficient wavetable-based synthesis with real-time morphing,
    multiple oscillators, and advanced modulation capabilities.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024,
                 max_oscillators: int = 64):
        """
        Initialize wavetable synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            max_oscillators: Maximum number of simultaneous oscillators
        """
        super().__init__(sample_rate, block_size)

        # Core components
        self.wavetable_bank = WavetableBank()
        self.oscillators = [WavetableOscillator(sample_rate) for _ in range(max_oscillators)]
        self.sample_manager = PyAVSampleManager()

        # Engine state
        self.active_oscillators: List[int] = []  # Indices of active oscillators
        self.current_wavetable = "sine"  # Default wavetable

        # Initialize with basic wavetables
        self._initialize_basic_wavetables()

        # Plugin system
        self._plugin_registry = get_global_plugin_registry()
        self._loaded_plugins: Dict[str, SynthesisFeaturePlugin] = {}
        self._plugin_integration_points = {
            'pre_synthesis': [],      # Called before synthesis
            'post_synthesis': [],     # Called after synthesis
            'midi_processing': [],    # MIDI message handlers
            'parameter_processing': [] # Parameter processing
        }

        # Auto-load Jupiter-X digital plugin if available
        self._auto_load_jupiter_x_plugin()

    def _initialize_basic_wavetables(self):
        """Initialize engine with basic mathematical wavetables."""
        basic_waveforms = ['sine', 'triangle', 'square', 'sawtooth']

        for waveform in basic_waveforms:
            self.wavetable_bank.create_wavetable_from_waveform(
                waveform, waveform, size=2048
            )

        # Set default wavetable for all oscillators
        default_wt = self.wavetable_bank.get_wavetable('sine')
        if default_wt:
            for osc in self.oscillators:
                osc.set_wavetable(default_wt)

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return 'wavetable'

    def load_wavetable(self, file_path: str, name: str) -> bool:
        """
        Load wavetable from audio file.

        Args:
            file_path: Path to audio file
            name: Name for the wavetable

        Returns:
            True if loaded successfully
        """
        return self.wavetable_bank.load_wavetable_from_file(
            file_path, name, self.sample_manager
        )

    def create_wavetable(self, waveform_type: str, name: str,
                        size: int = 2048) -> bool:
        """
        Create mathematical wavetable.

        Args:
            waveform_type: Type of waveform
            name: Name for the wavetable
            size: Wavetable size

        Returns:
            True if created successfully
        """
        return self.wavetable_bank.create_wavetable_from_waveform(
            waveform_type, name, size
        )

    def set_wavetable(self, name: str):
        """
        Set current wavetable for new notes.

        Args:
            name: Name of wavetable to use
        """
        wavetable = self.wavetable_bank.get_wavetable(name)
        if wavetable:
            self.current_wavetable = name
            # Update all oscillators to use this wavetable
            for osc in self.oscillators:
                osc.set_wavetable(wavetable)

    def create_morph_group(self, group_name: str, wavetable_names: List[str]):
        """Create a wavetable morph group."""
        self.wavetable_bank.create_morph_group(group_name, wavetable_names)

    def get_morph_group(self, group_name: str) -> List[str]:
        """Get wavetable names in morph group."""
        return self.wavetable_bank.get_morph_group(group_name)

    def get_regions_for_note(self, note: int, velocity: int, program: int = 0, bank: int = 0) -> List[Any]:
        """
        Get regions for note (wavetable engine creates regions dynamically).

        Returns:
            List containing a single dynamic region
        """
        # Wavetable engine creates regions on-demand
        # Return a placeholder that indicates wavetable synthesis should be used
        class WavetableRegion:
            def __init__(self, note, velocity, wavetable_name):
                self.note = note
                self.velocity = velocity
                self.wavetable_name = wavetable_name

            def should_play_for_note(self, n, v):
                return n == self.note and v == self.velocity

        return [WavetableRegion(note, velocity, self.current_wavetable)]

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> SynthesisPartial:
        """
        Create wavetable partial for synthesis.

        Args:
            partial_params: Parameters for the partial
            sample_rate: Audio sample rate

        Returns:
            Configured WavetablePartial
        """
        return WavetablePartial(partial_params, sample_rate, self.wavetable_bank)

    def create_region(self, region_params: Dict[str, Any], sample_rate: int) -> Optional[Region]:
        """
        Create a wavetable region instance.

        Args:
            region_params: Parameters for the region
            sample_rate: Audio sample rate

        Returns:
            WavetableRegion instance configured for this engine, or None if unsupported
        """
        try:
            # Load wavetable from file if specified
            sample_path = region_params.get('sample', region_params.get('sample_path'))
            if sample_path:
                # Try to load wavetable from the sample file
                wt_name = str(sample_path)
                if self.wavetable_bank.load_wavetable_from_file(sample_path, wt_name, self.sample_manager):
                    region_params['wavetable_name'] = wt_name
                else:
                    # Fall back to default wavetable
                    region_params['wavetable_name'] = self.current_wavetable

            return WavetableRegion(region_params, self.wavetable_bank)

        except Exception as e:
            print(f"Failed to create wavetable region: {e}")
            return None

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> np.ndarray:
        """
        Generate audio samples using wavetable synthesis.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Find or allocate oscillator for this note
        oscillator = self._find_or_allocate_oscillator(note)

        if not oscillator:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Configure oscillator
        oscillator.set_note(note, velocity)

        # Apply modulation
        freq_mod = modulation.get('pitch', 0.0) / 1200.0  # Convert cents to ratio
        amp_mod = modulation.get('volume', 0.0)
        wt_pos = modulation.get('timbre', 0.0)  # Use timbre for wavetable position

        oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

        # Generate samples
        mono_audio = oscillator.generate_samples(block_size)

        # Convert to stereo
        stereo_audio = np.column_stack([mono_audio, mono_audio])

        # Apply additional processing
        stereo_audio = self._apply_modulation(stereo_audio, modulation, block_size)

        return stereo_audio

    def _find_or_allocate_oscillator(self, note: int) -> Optional[WavetableOscillator]:
        """Find existing oscillator for note or allocate new one."""
        # First, check if we already have an oscillator for this note
        for idx in self.active_oscillators:
            if self.oscillators[idx].note == note and self.oscillators[idx].is_active():
                return self.oscillators[idx]

        # Find free oscillator
        for i, osc in enumerate(self.oscillators):
            if not osc.is_active():
                # Set current wavetable
                wavetable = self.wavetable_bank.get_wavetable(self.current_wavetable)
                if wavetable:
                    osc.set_wavetable(wavetable)

                if i not in self.active_oscillators:
                    self.active_oscillators.append(i)

                return osc

        # No free oscillators
        return None

    def _apply_modulation(self, audio: np.ndarray, modulation: Dict[str, float],
                         block_size: int) -> np.ndarray:
        """Apply additional modulation effects to generated audio."""
        # Pan modulation
        if 'pan' in modulation:
            pan = np.clip(modulation['pan'], -1.0, 1.0)
            left_gain = 1.0 - max(0.0, pan)
            right_gain = 1.0 - max(0.0, -pan)
            audio[:, 0] *= left_gain
            audio[:, 1] *= right_gain

        # Filter modulation (simple lowpass)
        if 'cutoff' in modulation:
            cutoff_norm = np.clip(modulation['cutoff'] / 20000.0, 0.0, 1.0)
            # Simple smoothing filter based on cutoff
            alpha = 0.1 + cutoff_norm * 0.8  # Higher cutoff = less smoothing

            # Apply simple lowpass per channel
            for ch in range(2):
                for i in range(1, block_size):
                    audio[i, ch] = alpha * audio[i, ch] + (1 - alpha) * audio[i-1, ch]

        return audio

    def is_note_supported(self, note: int) -> bool:
        """Check if note is supported (all notes supported in wavetable synthesis)."""
        return 0 <= note <= 127

    def get_supported_formats(self) -> List[str]:
        """Get supported file formats for wavetable loading."""
        return ['.wav', '.aiff', '.flac', '.ogg']

    def get_engine_info(self) -> Dict[str, Any]:
        """Get comprehensive engine information."""
        bank_stats = self.wavetable_bank.get_stats()

        return {
            'name': 'Wavetable Synthesis Engine',
            'type': 'wavetable',
            'version': '1.0',
            'capabilities': [
                'wavetable_synthesis', 'real_time_morphing', 'mathematical_waveforms',
                'frequency_modulation', 'amplitude_modulation', 'multi_oscillator',
                'unison_detuning', 'wavetable_scanning'
            ],
            'formats': self.get_supported_formats(),
            'max_oscillators': len(self.oscillators),
            'active_oscillators': len(self.active_oscillators),
            'wavetable_bank': bank_stats,
            'parameters': [
                'wavetable', 'frequency', 'amplitude', 'pan', 'cutoff',
                'pitch_mod', 'amp_mod', 'timbre_mod'
            ],
            'modulation_sources': [
                'velocity', 'key', 'cc1-cc127', 'pitch_bend', 'aftertouch'
            ],
            'modulation_destinations': [
                'frequency', 'amplitude', 'pan', 'cutoff', 'wavetable_position'
            ]
        }

    def get_available_wavetables(self) -> List[str]:
        """Get list of available wavetable names."""
        return self.wavetable_bank.list_wavetables()

    def get_wavetable_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific wavetable."""
        wavetable = self.wavetable_bank.get_wavetable(name)
        if not wavetable:
            return None

        return {
            'name': wavetable.name,
            'length': wavetable.length,
            'sample_rate': wavetable.sample_rate,
            'duration_ms': (wavetable.length / wavetable.sample_rate) * 1000
        }

    def reset(self) -> None:
        """Reset engine to clean state."""
        for osc in self.oscillators:
            osc.reset()
        self.active_oscillators.clear()

    def cleanup(self) -> None:
        """Clean up engine resources."""
        self.reset()
        self.wavetable_bank.wavetables.clear()

    def __str__(self) -> str:
        """String representation."""
        info = self.get_engine_info()
        return (f"WavetableEngine(oscillators={info['max_oscillators']}, "
                f"active={info['active_oscillators']}, "
                f"wavetables={info['wavetable_bank']['total_wavetables']})")

    def __repr__(self) -> str:
        return self.__str__()

    # Plugin System Methods

    def _auto_load_jupiter_x_plugin(self):
        """Automatically load Jupiter-X digital plugin if available."""
        try:
            # Check if Jupiter-X digital plugin is available
            available_plugins = self._plugin_registry.get_plugins_for_engine('wavetable')
            jupiter_digital_plugin = 'jupiter_x.digital_extensions.JupiterXDigitalPlugin'

            if jupiter_digital_plugin in available_plugins:
                success = self.load_plugin(jupiter_digital_plugin)
                if success:
                    print("🎹 Wavetable Engine: Jupiter-X digital extensions loaded automatically")
                else:
                    print("⚠️  Wavetable Engine: Failed to load Jupiter-X digital extensions")
            else:
                print("ℹ️  Wavetable Engine: Jupiter-X digital extensions not available")

        except Exception as e:
            print(f"⚠️  Wavetable Engine: Error during auto-loading Jupiter-X plugin: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin for this wavetable engine.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Load plugin using registry
            success = self._plugin_registry.load_plugin(
                plugin_name,
                engine_instance=self,
                sample_rate=self.sample_rate,
                block_size=self.block_size
            )

            if success:
                plugin = self._plugin_registry.get_plugin(plugin_name)
                if plugin:
                    self._loaded_plugins[plugin_name] = plugin

                    # Register plugin integration points
                    self._register_plugin_integration_points(plugin)

                    print(f"✅ Wavetable Engine: Plugin '{plugin_name}' loaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Wavetable Engine: Failed to load plugin '{plugin_name}': {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin from this wavetable engine.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if plugin_name in self._loaded_plugins:
                plugin = self._loaded_plugins[plugin_name]

                # Unregister plugin integration points
                self._unregister_plugin_integration_points(plugin)

                # Unload from registry
                success = self._plugin_registry.unload_plugin(plugin_name)

                if success:
                    del self._loaded_plugins[plugin_name]
                    print(f"✅ Wavetable Engine: Plugin '{plugin_name}' unloaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Wavetable Engine: Failed to unload plugin '{plugin_name}': {e}")
            return False

    def get_loaded_plugins(self) -> Dict[str, SynthesisFeaturePlugin]:
        """Get all plugins loaded for this engine."""
        return self._loaded_plugins.copy()

    def _register_plugin_integration_points(self, plugin: SynthesisFeaturePlugin):
        """
        Register plugin integration points.

        Args:
            plugin: Plugin to register
        """
        # Register modulation sources
        modulation_sources = plugin.get_modulation_sources()
        for source_name, source_func in modulation_sources.items():
            # Add to engine's modulation sources (would need modulation system)
            pass

        # Register modulation destinations
        modulation_destinations = plugin.get_modulation_destinations()
        for dest_name, dest_func in modulation_destinations.items():
            # Add to engine's modulation destinations
            pass

        # Register MIDI processing
        if hasattr(plugin, 'process_midi_message'):
            self._plugin_integration_points['midi_processing'].append(plugin)

        # Register parameter processing
        if hasattr(plugin, 'set_parameter'):
            self._plugin_integration_points['parameter_processing'].append(plugin)

    def _unregister_plugin_integration_points(self, plugin: SynthesisFeaturePlugin):
        """
        Unregister plugin integration points.

        Args:
            plugin: Plugin to unregister
        """
        # Remove from integration points
        for point_name, plugins in self._plugin_integration_points.items():
            if plugin in plugins:
                plugins.remove(plugin)

    def process_plugin_midi(self, status: int, data1: int, data2: int) -> bool:
        """
        Process MIDI message through loaded plugins.

        Args:
            status: MIDI status byte
            data1: MIDI data byte 1
            data2: MIDI data byte 2

        Returns:
            True if any plugin handled the message
        """
        handled = False
        for plugin in self._plugin_integration_points['midi_processing']:
            if plugin.process_midi_message(status, data1, data2):
                handled = True

        return handled

    def set_plugin_parameter(self, plugin_name: str, param_name: str, value: Any) -> bool:
        """
        Set parameter on a loaded plugin.

        Args:
            plugin_name: Name of the plugin
            param_name: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set
        """
        if plugin_name in self._loaded_plugins:
            plugin = self._loaded_plugins[plugin_name]
            return plugin.set_parameter(param_name, value)
        return False

    def get_plugin_parameter(self, plugin_name: str, param_name: str) -> Any:
        """
        Get parameter value from a loaded plugin.

        Args:
            plugin_name: Name of the plugin
            param_name: Parameter name

        Returns:
            Parameter value or None if not found
        """
        if plugin_name in self._loaded_plugins:
            plugin = self._loaded_plugins[plugin_name]
            params = plugin.get_parameters()
            return params.get(param_name)
        return None

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin information dictionary or None
        """
        return self._plugin_registry.get_plugin_info(plugin_name)
