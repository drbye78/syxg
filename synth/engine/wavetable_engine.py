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
                # Basic WAV loading (fallback)
                # This would need proper WAV parsing in production
                raise NotImplementedError("Basic WAV loading not implemented")

            # Extract single cycle (assume file contains one cycle)
            # In practice, you might want to analyze the file for cycle boundaries
            wavetable = Wavetable(data, sample_rate, name)
            return self.add_wavetable(wavetable, name)

        except Exception as e:
            print(f"Failed to load wavetable from {file_path}: {e}")
            return False

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

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> WavetableOscillator:
        """
        Create wavetable oscillator for synthesis.

        Args:
            partial_params: Parameters for the oscillator
            sample_rate: Audio sample rate

        Returns:
            Configured WavetableOscillator
        """
        oscillator = WavetableOscillator(sample_rate)

        # Set wavetable
        wt_name = partial_params.get('wavetable', self.current_wavetable)
        wavetable = self.wavetable_bank.get_wavetable(wt_name)
        if wavetable:
            oscillator.set_wavetable(wavetable)

        # Configure oscillator
        if 'frequency' in partial_params:
            oscillator.set_frequency(partial_params['frequency'])
        if 'amplitude' in partial_params:
            oscillator.set_amplitude(partial_params['amplitude'])

        return oscillator

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
