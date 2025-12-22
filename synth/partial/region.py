"""
Region Base Class - Abstract base for SFZ/SF2 regions.

Defines the common interface for all region types (SFZ regions, SF2 regions, etc.)
that can be played as part of a voice instance.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Import core synthesis components
from ..core.envelope import UltraFastADSREnvelope
from ..core.filter import UltraFastResonantFilter
from ..modulation.matrix import ModulationMatrix


class Region(ABC):
    """
    Abstract base class for synthesis regions.

    A Region represents a single playable element within a voice, such as:
    - An SFZ region with sample playback
    - An SF2 region with wavetable synthesis
    - A procedural synthesis region

    Regions handle their own modulation, envelopes, and sample playback,
    and can be mixed together within a VoiceInstance.

    Key Features:
    - Key and velocity range definitions
    - Individual modulation processing
    - Envelope management
    - Sample/filter processing
    - Crossfading support
    """

    def __init__(self, region_params: Dict[str, Any]):
        """
        Initialize region with parameters.

        Args:
            region_params: Dictionary of region parameters
        """
        # Key and velocity ranges
        self.key_range: Tuple[int, int] = region_params.get('key_range', (0, 127))
        self.velocity_range: Tuple[int, int] = region_params.get('velocity_range', (0, 127))

        # Round robin and sequence
        self.round_robin_group: int = region_params.get('round_robin_group', 0)
        self.round_robin_position: int = region_params.get('round_robin_position', 0)
        self.round_robin_length: int = region_params.get('round_robin_length', 1)
        self.sequence_position: int = region_params.get('sequence_position', 0)
        self.sequence_length: int = region_params.get('sequence_length', 1)

        # Trigger types
        self.trigger: str = region_params.get('trigger', 'attack')  # attack, release, first, legato

        # Crossfading
        self.velocity_crossfade: Tuple[float, float] = region_params.get('velocity_crossfade', (0.0, 0.0))
        self.note_crossfade: Tuple[float, float] = region_params.get('note_crossfade', (0.0, 0.0))

        # Sample information
        self.sample: Optional[Any] = None  # Sample object (SFZSample, SF2Sample, etc.)
        self.sample_path: Optional[str] = region_params.get('sample_path')

        # Timing
        self.offset: int = region_params.get('offset', 0)  # Sample offset in frames
        self.end: Optional[int] = region_params.get('end')  # End position in frames
        self.loop_mode: str = region_params.get('loop_mode', 'no_loop')
        self.loop_start: int = region_params.get('loop_start', 0)
        self.loop_end: int = region_params.get('loop_end', 0)

        # Pitch
        self.pitch_keycenter: int = region_params.get('pitch_keycenter', 60)
        self.tune: int = region_params.get('tune', 0)  # Coarse tune in cents
        self.fine_tune: float = region_params.get('fine_tune', 0.0)  # Fine tune in cents

        # Amplitude
        self.volume: float = region_params.get('volume', 0.0)  # dB
        self.pan: float = region_params.get('pan', 0.0)  # -1.0 to 1.0

        # Filter
        self.filter_type: str = region_params.get('filter_type', 'lpf_2p')
        self.cutoff: float = region_params.get('cutoff', 1000.0)  # Hz
        self.resonance: float = region_params.get('resonance', 0.7)

        # Envelope parameters
        self.amplitude_envelope: Dict[str, float] = region_params.get('amplitude_envelope', {
            'attack': 0.01, 'decay': 0.3, 'sustain': 0.7, 'release': 0.5, 'delay': 0.0, 'hold': 0.0
        })

        self.filter_envelope: Dict[str, float] = region_params.get('filter_envelope', {
            'attack': 0.1, 'decay': 0.5, 'sustain': 0.6, 'release': 0.8
        })

        # Modulation matrix (region-specific modulation)
        self.modulation_routes: List[Dict[str, Any]] = region_params.get('modulation_routes', [])

        # State
        self.active: bool = False
        self.current_note: int = 60
        self.current_velocity: int = 64
        self.sample_position: int = 0

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize region components (envelopes, filters, etc.)"""
        # Create envelopes
        self.amp_env = self._create_envelope('amplitude', self.amplitude_envelope)
        self.filter_env = self._create_envelope('filter', self.filter_envelope)

        # Create filter
        self.filter = self._create_filter(self.filter_type, self.cutoff, self.resonance)

        # Create modulation matrix for this region
        self.modulation_matrix = self._create_modulation_matrix()

    def _create_envelope(self, env_type: str, params: Dict[str, float]):
        """Create envelope for this region"""
        try:
            # Extract envelope parameters
            delay = params.get('delay', 0.0)
            attack = params.get('attack', 0.01)
            hold = params.get('hold', 0.0)
            decay = params.get('decay', 0.3)
            sustain = params.get('sustain', 0.7)
            release = params.get('release', 0.5)

            # Create UltraFastADSREnvelope
            return UltraFastADSREnvelope(
                delay=delay,
                attack=attack,
                hold=hold,
                decay=decay,
                sustain=sustain,
                release=release,
                sample_rate=44100  # Default sample rate, can be overridden
            )
        except Exception as e:
            print(f"Failed to create {env_type} envelope: {e}")
            return None

    def _create_filter(self, filter_type: str, cutoff: float, resonance: float):
        """Create filter for this region"""
        try:
            # Map filter type strings to internal types
            filter_type_map = {
                'lpf_1p': 'lowpass',
                'lpf_2p': 'lowpass',
                'hpf_1p': 'highpass',
                'hpf_2p': 'highpass',
                'bpf_2p': 'bandpass',
                'notch_2p': 'notch_2p',
                'apf_1p': 'allpass_1p',
                'peq': 'peaking_eq',
                'lsh': 'low_shelf',
                'hsh': 'high_shelf'
            }

            internal_type = filter_type_map.get(filter_type, 'lowpass')

            # Create UltraFastResonantFilter
            return UltraFastResonantFilter(
                cutoff=cutoff,
                resonance=resonance,
                filter_type=internal_type,
                sample_rate=44100  # Default sample rate, can be overridden
            )
        except Exception as e:
            print(f"Failed to create {filter_type} filter: {e}")
            return None

    def _create_modulation_matrix(self):
        """Create modulation matrix for this region"""
        try:
            # Create a basic modulation matrix for this region
            matrix = ModulationMatrix(num_routes=8)  # Smaller matrix for regions

            # Add default routes based on region's modulation_routes parameter
            route_index = 0
            for route in self.modulation_routes:
                try:
                    source = route.get('source')
                    destination = route.get('destination')
                    amount = route.get('amount', 1.0)

                    if source and destination and route_index < 8:
                        matrix.set_route(route_index, source, destination, amount)
                        route_index += 1
                except Exception as e:
                    print(f"Failed to add modulation route: {e}")

            return matrix
        except Exception as e:
            print(f"Failed to create modulation matrix: {e}")
            return None

    @abstractmethod
    def generate_samples(self, block_size: int, modulation: Dict[str, float]) -> np.ndarray:
        """
        Generate audio samples for this region.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Audio buffer (block_size, channels) - mono or stereo
        """
        pass

    def note_on(self, velocity: int, note: int) -> None:
        """
        Trigger note-on for this region.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        self.active = True
        self.current_note = note
        self.current_velocity = velocity
        self.sample_position = self.offset

        # Trigger envelopes
        if self.amp_env:
            self.amp_env.note_on(velocity, note)
        if self.filter_env:
            self.filter_env.note_on(velocity, note)

    def note_off(self) -> None:
        """
        Trigger note-off for this region.
        """
        # Trigger release phase of envelopes
        if self.amp_env:
            self.amp_env.note_off()
        if self.filter_env:
            self.filter_env.note_off()

    def update_modulation(self, modulation: Dict[str, float]) -> None:
        """
        Update modulation state for this region.

        Args:
            modulation: Dictionary of modulation parameter updates
        """
        # Update modulation matrix
        if self.modulation_matrix:
            # Process modulation matrix with current sources and note info
            self.modulation_matrix.process(modulation, self.current_velocity, self.current_note)

    def is_active(self) -> bool:
        """
        Check if this region is still active.

        Returns:
            True if region is still producing sound
        """
        # Check if envelope is still active (not in IDLE state)
        envelope_active = True
        if self.amp_env:
            # Envelope is active if not in IDLE state (0)
            envelope_active = self.amp_env.state != 0

        return self.active and envelope_active

    def should_play_for_note(self, note: int, velocity: int) -> bool:
        """
        Check if this region should play for the given note and velocity.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            True if region should play
        """
        # Check key range
        if not (self.key_range[0] <= note <= self.key_range[1]):
            return False

        # Check velocity range
        if not (self.velocity_range[0] <= velocity <= self.velocity_range[1]):
            return False

        return True

    def calculate_crossfade_gain(self, note: int, velocity: int) -> float:
        """
        Calculate crossfade gain for this region.

        Args:
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Gain multiplier (0.0 to 1.0)
        """
        gain = 1.0

        # Velocity crossfading
        if self.velocity_crossfade[1] > self.velocity_crossfade[0]:
            vel_low, vel_high = self.velocity_crossfade
            if velocity < vel_low:
                gain *= 0.0
            elif velocity < vel_high:
                # Linear fade in
                gain *= (velocity - vel_low) / (vel_high - vel_low)

        # Note crossfading
        if self.note_crossfade[1] > self.note_crossfade[0]:
            note_low, note_high = self.note_crossfade
            if note < note_low:
                gain *= 0.0
            elif note < note_high:
                # Linear fade in
                gain *= (note - note_low) / (note_high - note_low)

        return gain

    def get_pitch_ratio(self, note: int) -> float:
        """
        Calculate pitch ratio for the given note.

        Args:
            note: MIDI note number

        Returns:
            Pitch ratio multiplier
        """
        # Calculate semitone offset from keycenter
        semitones = note - self.pitch_keycenter

        # Add coarse and fine tuning
        total_cents = semitones * 100 + self.tune + self.fine_tune

        # Convert cents to ratio
        return 2 ** (total_cents / 1200)

    def get_region_info(self) -> Dict[str, Any]:
        """
        Get information about this region.

        Returns:
            Dictionary with region information
        """
        return {
            'key_range': self.key_range,
            'velocity_range': self.velocity_range,
            'round_robin_group': self.round_robin_group,
            'trigger': self.trigger,
            'sample_path': self.sample_path,
            'pitch_keycenter': self.pitch_keycenter,
            'volume': self.volume,
            'pan': self.pan,
            'filter_type': self.filter_type,
            'cutoff': self.cutoff,
            'active': self.active,
            'current_note': self.current_note,
            'current_velocity': self.current_velocity
        }

    def reset(self) -> None:
        """Reset region to clean state."""
        self.active = False
        self.sample_position = 0

        # Reset envelopes
        if self.amp_env:
            self.amp_env.reset()
        if self.filter_env:
            self.filter_env.reset()

    def __str__(self) -> str:
        """String representation of the region."""
        return f"{self.__class__.__name__}(key={self.key_range}, vel={self.velocity_range}, sample={self.sample_path})"

    def __repr__(self) -> str:
        return self.__str__()
