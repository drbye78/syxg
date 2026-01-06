"""
Jupiter-X External/Sample Engine Extensions

Plugin that adds Jupiter-X specific sample playback features to the base sample engine.
Eliminates duplication by extending the existing sample engine rather than creating
a parallel implementation.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from ..base_plugin import (
    SynthesisFeaturePlugin, PluginMetadata, PluginLoadContext,
    PluginType, PluginCompatibility
)


class JupiterXExternalPlugin(SynthesisFeaturePlugin):
    """
    Jupiter-X External Synthesis Extensions

    Adds Jupiter-X specific sample playback features to the base sample engine:
    - Advanced granular synthesis with Jupiter-X specific parameters
    - Sample scrubbing and manipulation
    - Time-stretching algorithms optimized for Jupiter-X
    - Multi-sample layering and crossfading
    - Jupiter-X style sample mapping and keygroups
    """

    def __init__(self):
        metadata = PluginMetadata(
            name="Jupiter-X External Extensions",
            version="1.0.0",
            description="Advanced sample playback from Roland Jupiter-X",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["sample", "granular"],
            dependencies=[],
            parameters={
                "playback_mode": {
                    "type": "enum",
                    "default": "normal",
                    "options": ["normal", "granular", "scrub", "stretch"],
                    "description": "Sample playback mode"
                },
                "time_stretch_algorithm": {
                    "type": "enum",
                    "default": "jupiter_x",
                    "options": ["jupiter_x", "phase_vocoder", "granular"],
                    "description": "Time-stretching algorithm"
                },
                "granular_density": {
                    "type": "float",
                    "default": 10.0,
                    "min": 1.0,
                    "max": 100.0,
                    "description": "Granular synthesis density (grains per second)"
                },
                "scrub_speed": {
                    "type": "float",
                    "default": 1.0,
                    "min": -4.0,
                    "max": 4.0,
                    "description": "Sample scrubbing speed"
                },
                "multi_sample_layering": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable multi-sample layering"
                }
            }
        )
        super().__init__(metadata)

        # Jupiter-X specific external features
        self.playback_mode = "normal"
        self.time_stretch_algorithm = "jupiter_x"
        self.granular_density = 10.0
        self.scrub_speed = 1.0
        self.multi_sample_layering = True

        # Granular synthesis parameters
        self.grain_size_ms = 50.0
        self.grain_pitch_randomization = 0.0
        self.grain_time_randomization = 0.0
        self.grain_overlap = 2

        # Sample scrubbing parameters
        self.scrub_position = 0.0
        self.scrub_loop_start = 0.0
        self.scrub_loop_end = 1.0

        # Multi-sample state
        self.sample_layers: List[Dict[str, Any]] = []
        self.crossfade_points: List[float] = []

        # ===== PHASE 2.6: ADVANCED MULTI-SAMPLING FEATURES =====
        # Time-stretching state
        self.stretch_factor = 1.0
        self.pitch_shift = 0.0

        # Multi-sample mapping system
        self.keygroups: List[Dict[str, Any]] = []  # Keygroup definitions
        self.velocity_layers: List[Dict[str, Any]] = []  # Velocity layers
        self.round_robin_groups: List[List[int]] = []  # Round-robin sample indices
        self.current_round_robin_index = 0

        # Advanced granular synthesis
        self.grain_cloud_enabled = False
        self.grain_cloud_density = 20.0
        self.grain_cloud_size_variation = 0.3
        self.grain_cloud_pitch_variation = 0.2
        self.grain_cloud_position_randomization = 0.1

        # Time-stretching with formant correction
        self.formant_correction_enabled = True
        self.formant_correction_strength = 0.7
        self.preserve_transients = True

        # Sample looping modes
        self.loop_mode = 'forward'  # forward, reverse, ping-pong, one-shot
        self.loop_crossfade_enabled = False
        self.loop_crossfade_time_ms = 10.0

        # Advanced sample manipulation
        self.sample_stretching_enabled = False
        self.pitch_shifting_algorithm = 'phase_vocoder'  # phase_vocoder, granular, spectral
        self.time_stretching_quality = 'high'  # low, medium, high

        # Keygroup parameters
        self.keygroup_crossfade_enabled = True
        self.keygroup_crossfade_range_semitones = 2.0

        # Velocity switching
        self.velocity_switching_enabled = True
        self.velocity_switch_points = [25, 50, 75, 100]  # MIDI velocity switch points

    def get_metadata(self) -> PluginMetadata:
        return self.metadata

    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """Check compatibility with sample/granular engines."""
        return engine_type in ["sample", "granular"] and engine_version.startswith("1.")

    def load(self, context: PluginLoadContext) -> bool:
        """Load the Jupiter-X external extensions."""
        try:
            self.load_context = context

            # Get reference to the base sample engine
            self.sample_engine = context.engine_instance
            if not self.sample_engine:
                return False

            # Initialize Jupiter-X specific features
            self._initialize_jupiter_x_external_features()

            print("🎹 Jupiter-X External Extensions loaded")
            return True

        except Exception as e:
            print(f"Failed to load Jupiter-X external extensions: {e}")
            return False

    def unload(self) -> bool:
        """Unload the Jupiter-X external extensions."""
        try:
            # Clean up Jupiter-X specific resources
            self.sample_layers.clear()
            self.crossfade_points.clear()

            print("🎹 Jupiter-X External Extensions unloaded")
            return True

        except Exception as e:
            print(f"Error unloading Jupiter-X external extensions: {e}")
            return False

    def _initialize_jupiter_x_external_features(self):
        """Initialize Jupiter-X specific external features."""
        # Set up Jupiter-X specific granular parameters
        if hasattr(self.sample_engine, 'set_granular_parameters'):
            self.sample_engine.set_granular_parameters(
                density=self.granular_density,
                size_ms=self.grain_size_ms,
                overlap=self.grain_overlap
            )

        # Configure time-stretching algorithm
        self._setup_time_stretching()

        # Initialize multi-sample layering
        if self.multi_sample_layering:
            self._setup_multi_sample_layering()

    def _setup_time_stretching(self):
        """Set up Jupiter-X time-stretching algorithm."""
        if not self.sample_engine:
            return

        if hasattr(self.sample_engine, 'set_time_stretch_algorithm'):
            self.sample_engine.set_time_stretch_algorithm(self.time_stretch_algorithm)

    def _setup_multi_sample_layering(self):
        """Set up multi-sample layering system."""
        # Jupiter-X style velocity and key switching
        # This creates smooth transitions between samples
        if hasattr(self.sample_engine, 'enable_multi_sample_layering'):
            self.sample_engine.enable_multi_sample_layering(True)

            # Set up default crossfade points
            self.crossfade_points = [0.2, 0.4, 0.6, 0.8]  # Velocity layers
            if hasattr(self.sample_engine, 'set_crossfade_points'):
                self.sample_engine.set_crossfade_points(self.crossfade_points)

    def get_synthesis_features(self) -> Dict[str, Any]:
        """Get Jupiter-X external synthesis features."""
        return {
            'playback_modes': {
                'current_mode': self.playback_mode,
                'available_modes': ['normal', 'granular', 'scrub', 'stretch'],
                'jupiter_x_optimized': True
            },
            'granular_synthesis': {
                'density': self.granular_density,
                'grain_size_ms': self.grain_size_ms,
                'overlap': self.grain_overlap,
                'pitch_randomization': self.grain_pitch_randomization,
                'time_randomization': self.grain_time_randomization
            },
            'time_stretching': {
                'algorithm': self.time_stretch_algorithm,
                'stretch_factor': self.stretch_factor,
                'pitch_shift': self.pitch_shift,
                'algorithms': ['jupiter_x', 'phase_vocoder', 'granular']
            },
            'sample_scrubbing': {
                'speed': self.scrub_speed,
                'position': self.scrub_position,
                'loop_start': self.scrub_loop_start,
                'loop_end': self.scrub_loop_end
            },
            'multi_sample': {
                'enabled': self.multi_sample_layering,
                'layers': len(self.sample_layers),
                'crossfade_points': self.crossfade_points
            }
        }

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set plugin parameter."""
        if name == "playback_mode":
            if value in ["normal", "granular", "scrub", "stretch"]:
                self.playback_mode = value
                self._update_playback_mode()
                return True
        elif name == "time_stretch_algorithm":
            if value in ["jupiter_x", "phase_vocoder", "granular"]:
                self.time_stretch_algorithm = value
                self._setup_time_stretching()
                return True
        elif name == "granular_density":
            self.granular_density = max(1.0, min(100.0, float(value)))
            self._update_granular_parameters()
            return True
        elif name == "scrub_speed":
            self.scrub_speed = max(-4.0, min(4.0, float(value)))
            self._update_scrub_parameters()
            return True
        elif name == "multi_sample_layering":
            self.multi_sample_layering = bool(value)
            if self.multi_sample_layering:
                self._setup_multi_sample_layering()
            else:
                self._disable_multi_sample_layering()
            return True

        return False

    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return {
            "playback_mode": self.playback_mode,
            "time_stretch_algorithm": self.time_stretch_algorithm,
            "granular_density": self.granular_density,
            "scrub_speed": self.scrub_speed,
            "multi_sample_layering": self.multi_sample_layering
        }

    def _update_playback_mode(self):
        """Update playback mode."""
        if not self.sample_engine:
            return

        if hasattr(self.sample_engine, 'set_playback_mode'):
            self.sample_engine.set_playback_mode(self.playback_mode)

    def _update_granular_parameters(self):
        """Update granular synthesis parameters."""
        if not self.sample_engine:
            return

        if hasattr(self.sample_engine, 'set_granular_parameters'):
            self.sample_engine.set_granular_parameters(
                density=self.granular_density,
                size_ms=self.grain_size_ms,
                overlap=self.grain_overlap
            )

    def _update_scrub_parameters(self):
        """Update sample scrubbing parameters."""
        if not self.sample_engine:
            return

        if hasattr(self.sample_engine, 'set_scrub_parameters'):
            self.sample_engine.set_scrub_parameters(
                speed=self.scrub_speed,
                position=self.scrub_position,
                loop_start=self.scrub_loop_start,
                loop_end=self.scrub_loop_end
            )

    def _disable_multi_sample_layering(self):
        """Disable multi-sample layering."""
        if self.sample_engine and hasattr(self.sample_engine, 'enable_multi_sample_layering'):
            self.sample_engine.enable_multi_sample_layering(False)

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI messages for Jupiter-X external features."""
        # Handle Jupiter-X specific MIDI messages for external engine
        if status >> 4 == 0xB:  # Control Change
            cc_number = data1
            value = data2

            # CC 83: Granular density (0-127 -> 1-100)
            if cc_number == 83:
                density = 1.0 + (value / 127.0) * 99.0
                self.set_parameter("granular_density", density)
                return True

            # CC 84: Scrub position (0-127 -> 0.0-1.0)
            if cc_number == 84:
                position = value / 127.0
                self._set_scrub_position(position)
                return True

            # CC 85: Time stretch factor (0-127 -> 0.25-4.0)
            if cc_number == 85:
                stretch = 0.25 * (4.0 / 0.25) ** (value / 127.0)
                self._set_time_stretch_factor(stretch)
                return True

            # CC 86: Scrub speed (-64 to +63 centered on 64)
            if cc_number == 86:
                speed = (value - 64) / 64.0 * 4.0
                self.set_parameter("scrub_speed", speed)
                return True

        return False

    def _set_scrub_position(self, position: float):
        """Set sample scrubbing position."""
        self.scrub_position = max(0.0, min(1.0, position))
        self._update_scrub_parameters()

    def _set_time_stretch_factor(self, factor: float):
        """Set time-stretching factor."""
        self.stretch_factor = max(0.25, min(4.0, factor))
        if self.sample_engine and hasattr(self.sample_engine, 'set_time_stretch_factor'):
            self.sample_engine.set_time_stretch_factor(self.stretch_factor)

    def load_sample(self, sample_data: np.ndarray, sample_rate: int,
                   name: str = "jupiter_x_sample") -> bool:
        """
        Load a sample with Jupiter-X specific processing.

        Args:
            sample_data: Audio sample data
            sample_rate: Sample rate of the audio
            name: Name for the sample

        Returns:
            True if loaded successfully
        """
        if not self.sample_engine:
            return False

        # Apply Jupiter-X specific sample processing
        processed_sample = self._process_sample_for_jupiter_x(sample_data)

        # Load into the base engine
        if hasattr(self.sample_engine, 'load_sample'):
            return self.sample_engine.load_sample(processed_sample, sample_rate, name)

        return False

    def _process_sample_for_jupiter_x(self, sample_data: np.ndarray) -> np.ndarray:
        """
        Apply Jupiter-X specific sample processing.

        This includes normalization, filtering, and format optimization.
        """
        # Normalize sample
        if np.max(np.abs(sample_data)) > 0:
            sample_data = sample_data / np.max(np.abs(sample_data))

        # Apply subtle high-frequency rolloff (Jupiter-X style)
        # This would be a simple low-pass filter

        # Add to sample layers if multi-sample layering is enabled
        if self.multi_sample_layering:
            self.sample_layers.append({
                'data': sample_data.copy(),
                'processed': True,
                'jupiter_x_format': True
            })

        return sample_data

    def set_granular_parameters(self, density: float = None, size_ms: float = None,
                               overlap: int = None, pitch_rand: float = None,
                               time_rand: float = None) -> bool:
        """
        Set granular synthesis parameters.

        Args:
            density: Grains per second
            size_ms: Grain size in milliseconds
            overlap: Grain overlap factor
            pitch_rand: Pitch randomization (0.0-1.0)
            time_rand: Time randomization (0.0-1.0)

        Returns:
            True if parameters were set
        """
        if density is not None:
            self.granular_density = max(1.0, min(100.0, float(density)))
        if size_ms is not None:
            self.grain_size_ms = max(1.0, min(500.0, float(size_ms)))
        if overlap is not None:
            self.grain_overlap = max(1, min(8, int(overlap)))
        if pitch_rand is not None:
            self.grain_pitch_randomization = max(0.0, min(1.0, float(pitch_rand)))
        if time_rand is not None:
            self.grain_time_randomization = max(0.0, min(1.0, float(time_rand)))

        self._update_granular_parameters()
        return True

    def set_scrub_loop_points(self, start: float, end: float) -> bool:
        """
        Set sample scrubbing loop points.

        Args:
            start: Loop start position (0.0-1.0)
            end: Loop end position (0.0-1.0)

        Returns:
            True if loop points were set
        """
        if not (0.0 <= start < end <= 1.0):
            return False

        self.scrub_loop_start = start
        self.scrub_loop_end = end
        self._update_scrub_parameters()
        return True

    def get_sample_info(self) -> Dict[str, Any]:
        """Get information about loaded samples."""
        return {
            'sample_layers': len(self.sample_layers),
            'multi_sample_enabled': self.multi_sample_layering,
            'playback_mode': self.playback_mode,
            'time_stretch_algorithm': self.time_stretch_algorithm,
            'granular_density': self.granular_density,
            'scrub_speed': self.scrub_speed,
            'jupiter_x_features': True
        }

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> Optional[np.ndarray]:
        """
        Generate additional sample-based audio with Jupiter-X features.

        This is called by the base sample engine to add Jupiter-X specific processing.
        """
        if not self.is_active() or not self.sample_engine:
            return None

        # Apply Jupiter-X specific processing to the base sample output
        # This could include additional granular processing, scrubbing, etc.

        # For now, return None to indicate no additional samples
        # In a full implementation, this would return processed samples
        return None

    # ===== PHASE 2.6: ADVANCED MULTI-SAMPLING METHODS =====

    def create_keygroup(self, low_key: int, high_key: int, sample_index: int,
                       root_key: int = None, tune: float = 0.0, level: float = 1.0) -> bool:
        """Create a keygroup for multi-sample mapping."""
        if not (0 <= low_key <= high_key <= 127):
            return False

        if root_key is None:
            root_key = (low_key + high_key) // 2

        keygroup = {
            'low_key': low_key,
            'high_key': high_key,
            'sample_index': sample_index,
            'root_key': root_key,
            'tune': tune,
            'level': level,
            'active': True
        }

        self.keygroups.append(keygroup)

        # Update engine if available
        if self.sample_engine and hasattr(self.sample_engine, 'add_keygroup'):
            self.sample_engine.add_keygroup(keygroup)

        print(f"🎛️ Created keygroup: keys {low_key}-{high_key}, sample {sample_index}")
        return True

    def create_velocity_layer(self, low_velocity: int, high_velocity: int, sample_index: int,
                             crossfade_range: int = 5) -> bool:
        """Create a velocity layer for multi-sample mapping."""
        if not (0 <= low_velocity <= high_velocity <= 127):
            return False

        velocity_layer = {
            'low_velocity': low_velocity,
            'high_velocity': high_velocity,
            'sample_index': sample_index,
            'crossfade_range': crossfade_range,
            'active': True
        }

        self.velocity_layers.append(velocity_layer)

        # Update engine if available
        if self.sample_engine and hasattr(self.sample_engine, 'add_velocity_layer'):
            self.sample_engine.add_velocity_layer(velocity_layer)

        print(f"🎛️ Created velocity layer: vel {low_velocity}-{high_velocity}, sample {sample_index}")
        return True

    def create_round_robin_group(self, sample_indices: List[int]) -> int:
        """Create a round-robin group for alternating between samples."""
        if not sample_indices:
            return -1

        self.round_robin_groups.append(sample_indices.copy())
        group_index = len(self.round_robin_groups) - 1

        # Update engine if available
        if self.sample_engine and hasattr(self.sample_engine, 'add_round_robin_group'):
            self.sample_engine.add_round_robin_group(group_index, sample_indices)

        print(f"🎛️ Created round-robin group {group_index}: {sample_indices}")
        return group_index

    def get_next_round_robin_sample(self, group_index: int) -> int:
        """Get the next sample index from a round-robin group."""
        if group_index < 0 or group_index >= len(self.round_robin_groups):
            return -1

        group = self.round_robin_groups[group_index]
        if not group:
            return -1

        # Get next sample and advance counter
        sample_index = group[self.current_round_robin_index % len(group)]
        self.current_round_robin_index += 1

        return sample_index

    def enable_grain_cloud(self, enabled: bool = True, density: float = 20.0,
                          size_variation: float = 0.3, pitch_variation: float = 0.2,
                          position_randomization: float = 0.1):
        """Enable advanced grain cloud synthesis."""
        self.grain_cloud_enabled = enabled
        self.grain_cloud_density = max(5.0, min(200.0, density))
        self.grain_cloud_size_variation = max(0.0, min(1.0, size_variation))
        self.grain_cloud_pitch_variation = max(0.0, min(2.0, pitch_variation))
        self.grain_cloud_position_randomization = max(0.0, min(1.0, position_randomization))

        if self.sample_engine and hasattr(self.sample_engine, 'enable_grain_cloud'):
            self.sample_engine.enable_grain_cloud(enabled, {
                'density': self.grain_cloud_density,
                'size_variation': self.grain_cloud_size_variation,
                'pitch_variation': self.grain_cloud_pitch_variation,
                'position_randomization': self.grain_cloud_position_randomization
            })

        print(f"🎛️ Grain cloud {'enabled' if enabled else 'disabled'} (density: {self.grain_cloud_density:.1f})")

    def configure_formant_correction(self, enabled: bool = True, strength: float = 0.7,
                                   preserve_transients: bool = True):
        """Configure time-stretching with formant correction."""
        self.formant_correction_enabled = enabled
        self.formant_correction_strength = max(0.0, min(1.0, strength))
        self.preserve_transients = preserve_transients

        if self.sample_engine and hasattr(self.sample_engine, 'configure_formant_correction'):
            self.sample_engine.configure_formant_correction(enabled, {
                'strength': self.formant_correction_strength,
                'preserve_transients': self.preserve_transients
            })

        print(f"🎛️ Formant correction {'enabled' if enabled else 'disabled'} (strength: {self.formant_correction_strength:.2f})")

    def set_sample_loop_mode(self, mode: str = 'forward', crossfade_enabled: bool = False,
                           crossfade_time_ms: float = 10.0):
        """Set sample looping mode."""
        valid_modes = ['forward', 'reverse', 'ping-pong', 'one-shot']
        self.loop_mode = mode if mode in valid_modes else 'forward'
        self.loop_crossfade_enabled = crossfade_enabled
        self.loop_crossfade_time_ms = max(1.0, min(100.0, crossfade_time_ms))

        if self.sample_engine and hasattr(self.sample_engine, 'set_loop_mode'):
            self.sample_engine.set_loop_mode(self.loop_mode, {
                'crossfade_enabled': self.loop_crossfade_enabled,
                'crossfade_time_ms': self.loop_crossfade_time_ms
            })

        print(f"🎛️ Loop mode set to {self.loop_mode} (crossfade: {self.loop_crossfade_enabled})")

    def configure_sample_stretching(self, enabled: bool = True, algorithm: str = 'phase_vocoder',
                                  quality: str = 'high'):
        """Configure advanced sample stretching parameters."""
        self.sample_stretching_enabled = enabled
        valid_algorithms = ['phase_vocoder', 'granular', 'spectral']
        self.pitch_shifting_algorithm = algorithm if algorithm in valid_algorithms else 'phase_vocoder'
        valid_qualities = ['low', 'medium', 'high']
        self.time_stretching_quality = quality if quality in valid_qualities else 'high'

        if self.sample_engine and hasattr(self.sample_engine, 'configure_sample_stretching'):
            self.sample_engine.configure_sample_stretching(enabled, {
                'algorithm': self.pitch_shifting_algorithm,
                'quality': self.time_stretching_quality
            })

        print(f"🎛️ Sample stretching {'enabled' if enabled else 'disabled'} ({self.pitch_shifting_algorithm}, {self.time_stretching_quality} quality)")

    def set_keygroup_crossfade(self, enabled: bool = True, range_semitones: float = 2.0):
        """Configure keygroup crossfading."""
        self.keygroup_crossfade_enabled = enabled
        self.keygroup_crossfade_range_semitones = max(0.1, min(12.0, range_semitones))

        if self.sample_engine and hasattr(self.sample_engine, 'set_keygroup_crossfade'):
            self.sample_engine.set_keygroup_crossfade(enabled, self.keygroup_crossfade_range_semitones)

        print(f"🎛️ Keygroup crossfade {'enabled' if enabled else 'disabled'} (range: {self.keygroup_crossfade_range_semitones:.1f} semitones)")

    def configure_velocity_switching(self, enabled: bool = True, switch_points: Optional[List[int]] = None):
        """Configure velocity switching points."""
        self.velocity_switching_enabled = enabled

        if switch_points is None:
            switch_points = [25, 50, 75, 100]

        # Validate and clamp switch points
        self.velocity_switch_points = [max(0, min(127, p)) for p in switch_points[:5]]  # Max 5 layers

        if self.sample_engine and hasattr(self.sample_engine, 'configure_velocity_switching'):
            self.sample_engine.configure_velocity_switching(enabled, self.velocity_switch_points)

        print(f"🎛️ Velocity switching {'enabled' if enabled else 'disabled'} (points: {self.velocity_switch_points})")

    def find_sample_for_note(self, note: int, velocity: int) -> int:
        """Find the appropriate sample index for a given note and velocity."""
        # Check keygroups first
        for keygroup in self.keygroups:
            if keygroup['active'] and keygroup['low_key'] <= note <= keygroup['high_key']:
                return keygroup['sample_index']

        # Check velocity layers
        if self.velocity_switching_enabled:
            for i, layer in enumerate(self.velocity_layers):
                if layer['active'] and layer['low_velocity'] <= velocity <= layer['high_velocity']:
                    # Check if this velocity layer has round-robin
                    if i < len(self.round_robin_groups):
                        return self.get_next_round_robin_sample(i)
                    else:
                        return layer['sample_index']

        # Default to first sample
        return 0

    def apply_time_stretch_with_formants(self, sample_data: np.ndarray, stretch_factor: float) -> np.ndarray:
        """Apply time-stretching with formant correction."""
        if not self.formant_correction_enabled or abs(stretch_factor - 1.0) < 0.01:
            return sample_data

        # This would implement formant-preserving time-stretching
        # For now, return original data
        return sample_data

    def create_grain_cloud(self, source_sample: np.ndarray, num_grains: int = 50) -> np.ndarray:
        """Create a grain cloud from source sample."""
        if not self.grain_cloud_enabled or num_grains <= 0:
            return source_sample

        sample_length = len(source_sample)
        grain_size_samples = int(self.grain_size_ms * 44.1)  # Assume 44.1kHz

        # Create grain cloud
        cloud_output = np.zeros_like(source_sample)

        for _ in range(num_grains):
            # Random grain parameters
            start_pos = np.random.randint(0, max(1, sample_length - grain_size_samples))
            grain_size = int(grain_size_samples * (1.0 + (np.random.random() - 0.5) * self.grain_cloud_size_variation))
            grain_size = max(1, min(grain_size, sample_length - start_pos))

            # Extract grain
            grain = source_sample[start_pos:start_pos + grain_size]

            # Apply pitch variation
            if self.grain_cloud_pitch_variation > 0:
                pitch_factor = 1.0 + (np.random.random() - 0.5) * self.grain_cloud_pitch_variation
                # Simple pitch shifting (would need proper implementation)
                grain = grain  # Placeholder

            # Random position variation
            position_offset = int(np.random.random() * self.grain_cloud_position_randomization * sample_length)
            target_start = (start_pos + position_offset) % sample_length

            # Add grain to cloud
            end_pos = min(target_start + len(grain), len(cloud_output))
            actual_length = end_pos - target_start

            if actual_length > 0:
                cloud_output[target_start:end_pos] += grain[:actual_length] * 0.1  # Quiet mix

        # Normalize
        max_val = np.max(np.abs(cloud_output))
        if max_val > 0:
            cloud_output /= max_val

        return cloud_output

    def get_multi_sample_mapping(self) -> Dict[str, Any]:
        """Get current multi-sample mapping configuration."""
        return {
            'keygroups': self.keygroups,
            'velocity_layers': self.velocity_layers,
            'round_robin_groups': self.round_robin_groups,
            'current_round_robin_index': self.current_round_robin_index,
            'keygroup_crossfade': {
                'enabled': self.keygroup_crossfade_enabled,
                'range_semitones': self.keygroup_crossfade_range_semitones
            },
            'velocity_switching': {
                'enabled': self.velocity_switching_enabled,
                'switch_points': self.velocity_switch_points
            }
        }

    def get_advanced_granular_features(self) -> Dict[str, Any]:
        """Get advanced granular synthesis features."""
        return {
            'grain_cloud': {
                'enabled': self.grain_cloud_enabled,
                'density': self.grain_cloud_density,
                'size_variation': self.grain_cloud_size_variation,
                'pitch_variation': self.grain_cloud_pitch_variation,
                'position_randomization': self.grain_cloud_position_randomization
            },
            'time_stretching': {
                'formant_correction': {
                    'enabled': self.formant_correction_enabled,
                    'strength': self.formant_correction_strength,
                    'preserve_transients': self.preserve_transients
                },
                'sample_stretching': {
                    'enabled': self.sample_stretching_enabled,
                    'algorithm': self.pitch_shifting_algorithm,
                    'quality': self.time_stretching_quality
                }
            },
            'looping': {
                'mode': self.loop_mode,
                'crossfade_enabled': self.loop_crossfade_enabled,
                'crossfade_time_ms': self.loop_crossfade_time_ms
            }
        }

    def get_external_engine_status(self) -> Dict[str, Any]:
        """Get Jupiter-X external engine status."""
        return {
            'playback_mode': self.playback_mode,
            'time_stretch_algorithm': self.time_stretch_algorithm,
            'granular_density': self.granular_density,
            'scrub_speed': self.scrub_speed,
            'multi_sample_layering': self.multi_sample_layering,
            'sample_layers': len(self.sample_layers),
            'crossfade_points': self.crossfade_points,
            'stretch_factor': self.stretch_factor,
            'pitch_shift': self.pitch_shift,
            'multi_sample_mapping': self.get_multi_sample_mapping(),
            'advanced_granular_features': self.get_advanced_granular_features(),
            'features_active': self.is_active()
        }
