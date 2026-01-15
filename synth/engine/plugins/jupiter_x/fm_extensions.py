"""
Jupiter-X FM Engine Extensions

Plugin that adds Jupiter-X specific FM synthesis features to the base FM engine.
Eliminates duplication by extending the existing FMEngine rather than creating
a parallel implementation.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from ..base_plugin import (
    SynthesisFeaturePlugin, PluginMetadata, PluginLoadContext,
    PluginType, PluginCompatibility
)


class JupiterXFMPlugin(SynthesisFeaturePlugin):
    """
    Jupiter-X FM Synthesis Extensions

    Adds Jupiter-X specific FM features to the base FM engine:
    - Enhanced formant operators for vocal synthesis
    - Advanced feedback algorithms
    - Ring modulation between operators
    - Extended operator routing options
    """

    @classmethod
    def get_plugin_metadata(cls) -> PluginMetadata:
        """Get plugin metadata for registration."""
        return PluginMetadata(
            name="Jupiter-X FM Extensions",
            version="1.0.0",
            description="Advanced FM synthesis features from Roland Jupiter-X",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["fm"],
            dependencies=[],
            parameters={
                "vocal_formants": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable vocal formant synthesis"
                },
                "ring_modulation": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable ring modulation between operators"
                },
                "feedback_enhancement": {
                    "type": "float",
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "description": "Feedback enhancement factor"
                }
            }
        )

    def __init__(self):
        # Create metadata first before calling parent constructor
        metadata = PluginMetadata(
            name="Jupiter-X FM Extensions",
            version="1.0.0",
            description="Advanced FM synthesis features from Roland Jupiter-X",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["fm"],
            dependencies=[],
            parameters={
                "vocal_formants": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable vocal formant synthesis"
                },
                "ring_modulation": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable ring modulation between operators"
                },
                "feedback_enhancement": {
                    "type": "float",
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "description": "Feedback enhancement factor"
                }
            }
        )
        super().__init__(metadata)

        # ===== PHASE 2.5: ADVANCED FM SYNTHESIS FEATURES =====
        # Jupiter-X specific FM features
        self.vocal_formants_enabled = False
        self.ring_modulation_enabled = True
        self.feedback_enhancement = 1.0

        # Algorithm morphing system
        self.algorithm_morphing_enabled = False
        self.current_algorithm = 0
        self.target_algorithm = 1
        self.algorithm_morph_factor = 0.0
        self.algorithm_morph_speed = 0.1

        # Operator feedback routing
        self.multiple_feedback_paths = False
        self.feedback_coloring_enabled = False
        self.feedback_coloring_type = 'lowpass'  # lowpass, highpass, bandpass

        # Operator panning and stereo positioning
        self.operator_stereo_enabled = False
        self.operator_pan_positions = [0.0] * 6  # -1.0 to 1.0 for each operator
        self.operator_level_offsets = [0.0] * 6  # Level adjustment per operator

        # Velocity scaling per operator
        self.operator_velocity_scaling = [1.0] * 6  # Scaling factor for each operator

        # Key scaling and keyboard tracking
        self.operator_key_scaling = [1.0] * 6  # Key tracking amount per operator

        # Phase modulation and through-zero FM
        self.phase_modulation_enabled = False
        self.through_zero_fm_enabled = False
        self.fm_index_modulation = 1.0

        # Formant FM and vocal synthesis
        self.formant_fm_enabled = False
        self.vowel_transition_smoothing = 0.1

        # Dynamic algorithm switching
        self.dynamic_algorithm_switching = False
        self.algorithm_switch_threshold = 0.5

        # Formant data for vocal synthesis (vowel formants in Hz)
        self.vowel_formants = {
            'a': [800, 1150, 2900, 3900, 4950],  # "ah" as in "father"
            'e': [400, 1700, 2600, 3200, 3580],  # "eh" as in "bed"
            'i': [270, 2140, 2950, 3900, 4950],  # "ee" as in "beet"
            'o': [450, 800, 2830, 3800, 4950],   # "oh" as in "boat"
            'u': [325, 700, 2700, 3800, 4950],   # "oo" as in "boot"
        }

        # Ring modulation connections
        self.ring_mod_connections: List[Tuple[int, int]] = []

        # Operator detuning and pitch modulation
        self.operator_detune_amounts = [0.0] * 6  # In semitones
        self.operator_pitch_modulation = [0.0] * 6  # Modulation depth

        # Operator amplitude modulation
        self.operator_amplitude_modulation = [0.0] * 6  # AM depth

    def get_metadata(self) -> PluginMetadata:
        return self.metadata

    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """Check compatibility with FM engines."""
        return engine_type == "fm" and engine_version.startswith("1.")

    def load(self, context: PluginLoadContext) -> bool:
        """Load the Jupiter-X FM extensions."""
        try:
            self.load_context = context

            # Get reference to the base FM engine
            self.fm_engine = context.engine_instance
            if not self.fm_engine:
                return False

            # Initialize Jupiter-X specific features
            self._initialize_jupiter_x_fm_features()

            print("🎹 Jupiter-X FM Extensions loaded")
            return True

        except Exception as e:
            print(f"Failed to load Jupiter-X FM extensions: {e}")
            return False

    def unload(self) -> bool:
        """Unload the Jupiter-X FM extensions."""
        try:
            # Clean up any Jupiter-X specific resources
            self.ring_mod_connections.clear()
            self.vocal_formants_enabled = False

            print("🎹 Jupiter-X FM Extensions unloaded")
            return True

        except Exception as e:
            print(f"Error unloading Jupiter-X FM extensions: {e}")
            return False

    def _initialize_jupiter_x_fm_features(self):
        """Initialize Jupiter-X specific FM features."""
        # Set up enhanced feedback algorithms
        if hasattr(self.fm_engine, 'set_feedback_algorithm'):
            self.fm_engine.set_feedback_algorithm('jupiter_x_enhanced')

        # Initialize ring modulation system
        self._setup_ring_modulation()

    def _setup_ring_modulation(self):
        """Set up ring modulation between operators."""
        # Jupiter-X style ring modulation routing
        # Connect operator outputs to create complex timbres
        if hasattr(self.fm_engine, 'add_ring_modulation_connection'):
            # Example: Connect operator 1 output to operator 2 input
            self.fm_engine.add_ring_modulation_connection(0, 1)
            self.fm_engine.add_ring_modulation_connection(2, 3)
            self.ring_mod_connections = [(0, 1), (2, 3)]

    def get_synthesis_features(self) -> Dict[str, Any]:
        """Get Jupiter-X FM synthesis features."""
        return {
            'vocal_formants': {
                'enabled': self.vocal_formants_enabled,
                'available_vowels': list(self.vowel_formants.keys()),
                'formant_count': 5
            },
            'ring_modulation': {
                'enabled': self.ring_modulation_enabled,
                'connections': self.ring_mod_connections,
                'max_connections': 8
            },
            'feedback_enhancement': {
                'factor': self.feedback_enhancement,
                'algorithm': 'jupiter_x_enhanced'
            },
            'operator_extensions': {
                'formant_shaping': True,
                'harmonic_enhancement': True,
                'dynamic_feedback': True
            }
        }

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set plugin parameter."""
        if name == "vocal_formants":
            self.vocal_formants_enabled = bool(value)
            self._update_vocal_formants()
            return True
        elif name == "ring_modulation":
            self.ring_modulation_enabled = bool(value)
            self._update_ring_modulation()
            return True
        elif name == "feedback_enhancement":
            self.feedback_enhancement = max(0.0, min(2.0, float(value)))
            self._update_feedback_enhancement()
            return True

        return False

    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return {
            "vocal_formants": self.vocal_formants_enabled,
            "ring_modulation": self.ring_modulation_enabled,
            "feedback_enhancement": self.feedback_enhancement
        }

    def _update_vocal_formants(self):
        """Update vocal formant processing."""
        if not self.fm_engine:
            return

        if self.vocal_formants_enabled:
            # Configure operators for vocal synthesis
            if hasattr(self.fm_engine, 'configure_formant_operator'):
                # Set up formant filter on operator 4 (typically carrier)
                self.fm_engine.configure_formant_operator(3, self.vowel_formants['a'])
        else:
            # Disable formant processing
            if hasattr(self.fm_engine, 'disable_formant_operator'):
                self.fm_engine.disable_formant_operator(3)

    def _update_ring_modulation(self):
        """Update ring modulation connections."""
        if not self.fm_engine:
            return

        if self.ring_modulation_enabled:
            # Re-establish ring modulation connections
            self._setup_ring_modulation()
        else:
            # Remove all ring modulation connections
            if hasattr(self.fm_engine, 'clear_ring_modulation'):
                self.fm_engine.clear_ring_modulation()
            self.ring_mod_connections.clear()

    def _update_feedback_enhancement(self):
        """Update feedback enhancement settings."""
        if not self.fm_engine:
            return

        # Apply feedback enhancement factor
        if hasattr(self.fm_engine, 'set_feedback_factor'):
            self.fm_engine.set_feedback_factor(self.feedback_enhancement)

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI messages for Jupiter-X FM features."""
        # Handle Jupiter-X specific MIDI messages
        # For example, CC messages that control vocal formants
        if status >> 4 == 0xB:  # Control Change
            cc_number = data1
            value = data2

            # CC 76: Select vowel (0-4 for a,e,i,o,u)
            if cc_number == 76 and 0 <= value <= 4:
                vowels = list(self.vowel_formants.keys())
                selected_vowel = vowels[min(value, len(vowels) - 1)]
                self._set_vowel_formant(selected_vowel)
                return True

        return False

    def _set_vowel_formant(self, vowel: str):
        """Set the current vowel formant."""
        if vowel in self.vowel_formants and self.fm_engine:
            if hasattr(self.fm_engine, 'configure_formant_operator'):
                self.fm_engine.configure_formant_operator(3, self.vowel_formants[vowel])

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> Optional[np.ndarray]:
        """
        Generate additional FM samples with Jupiter-X features.

        This is called by the base FM engine to add Jupiter-X specific processing.
        """
        if not self.is_active() or not self.fm_engine:
            return None

        # Apply Jupiter-X specific processing to the base FM output
        # This could include additional formant filtering, ring modulation, etc.

        # For now, return None to indicate no additional samples
        # In a full implementation, this would return processed samples
        return None

    # ===== PHASE 2.5: ADVANCED FM SYNTHESIS METHODS =====

    def enable_algorithm_morphing(self, enabled: bool = True, morph_speed: float = 0.1):
        """Enable algorithm morphing between different FM algorithms."""
        self.algorithm_morphing_enabled = enabled
        self.algorithm_morph_speed = max(0.01, min(1.0, morph_speed))

        if self.fm_engine and hasattr(self.fm_engine, 'enable_algorithm_morphing'):
            self.fm_engine.enable_algorithm_morphing(enabled, self.algorithm_morph_speed)

        print(f"🎛️ Algorithm morphing {'enabled' if enabled else 'disabled'} (speed: {self.algorithm_morph_speed:.2f})")

    def set_algorithm_morph_targets(self, source_algorithm: int, target_algorithm: int, morph_factor: float = 0.0):
        """Set algorithm morphing targets and current morph factor."""
        self.current_algorithm = max(0, min(31, source_algorithm))  # 0-31 algorithms
        self.target_algorithm = max(0, min(31, target_algorithm))
        self.algorithm_morph_factor = max(0.0, min(1.0, morph_factor))

        if self.fm_engine and hasattr(self.fm_engine, 'set_algorithm_morphing'):
            self.fm_engine.set_algorithm_morphing(self.current_algorithm, self.target_algorithm, self.algorithm_morph_factor)

        print(f"🎛️ Algorithm morphing: {self.current_algorithm} → {self.target_algorithm} (factor: {self.algorithm_morph_factor:.2f})")

    def enable_multiple_feedback_paths(self, enabled: bool = True):
        """Enable multiple feedback paths for complex FM routing."""
        self.multiple_feedback_paths = enabled

        if self.fm_engine and hasattr(self.fm_engine, 'enable_multiple_feedback'):
            self.fm_engine.enable_multiple_feedback(enabled)

        print(f"🎛️ Multiple feedback paths {'enabled' if enabled else 'disabled'}")

    def enable_feedback_coloring(self, enabled: bool = True, filter_type: str = 'lowpass'):
        """Enable feedback coloring with filter types."""
        self.feedback_coloring_enabled = enabled
        valid_types = ['lowpass', 'highpass', 'bandpass']
        self.feedback_coloring_type = filter_type if filter_type in valid_types else 'lowpass'

        if self.fm_engine and hasattr(self.fm_engine, 'enable_feedback_coloring'):
            self.fm_engine.enable_feedback_coloring(enabled, self.feedback_coloring_type)

        print(f"🎛️ Feedback coloring {'enabled' if enabled else 'disabled'} ({self.feedback_coloring_type})")

    def enable_operator_stereo(self, enabled: bool = True):
        """Enable operator stereo positioning and panning."""
        self.operator_stereo_enabled = enabled

        if self.fm_engine and hasattr(self.fm_engine, 'enable_operator_stereo'):
            self.fm_engine.enable_operator_stereo(enabled)

        print(f"🎛️ Operator stereo {'enabled' if enabled else 'disabled'}")

    def set_operator_pan_positions(self, pan_positions: List[float]):
        """Set pan positions for each operator (-1.0 to 1.0)."""
        self.operator_pan_positions = [max(-1.0, min(1.0, p)) for p in pan_positions[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_pan_positions'):
            self.fm_engine.set_operator_pan_positions(self.operator_pan_positions)

        print(f"🎛️ Operator pan positions set: {self.operator_pan_positions}")

    def set_operator_velocity_scaling(self, scaling_factors: List[float]):
        """Set velocity scaling for each operator."""
        self.operator_velocity_scaling = [max(0.0, min(2.0, s)) for s in scaling_factors[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_velocity_scaling'):
            self.fm_engine.set_operator_velocity_scaling(self.operator_velocity_scaling)

        print(f"🎛️ Operator velocity scaling: {self.operator_velocity_scaling}")

    def set_operator_key_scaling(self, scaling_factors: List[float]):
        """Set key scaling for each operator."""
        self.operator_key_scaling = [max(0.0, min(2.0, s)) for s in scaling_factors[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_key_scaling'):
            self.fm_engine.set_operator_key_scaling(self.operator_key_scaling)

        print(f"🎛️ Operator key scaling: {self.operator_key_scaling}")

    def enable_phase_modulation(self, enabled: bool = True):
        """Enable phase modulation for operators."""
        self.phase_modulation_enabled = enabled

        if self.fm_engine and hasattr(self.fm_engine, 'enable_phase_modulation'):
            self.fm_engine.enable_phase_modulation(enabled)

        print(f"🎛️ Phase modulation {'enabled' if enabled else 'disabled'}")

    def enable_through_zero_fm(self, enabled: bool = True, index_mod: float = 1.0):
        """Enable through-zero FM synthesis."""
        self.through_zero_fm_enabled = enabled
        self.fm_index_modulation = max(0.1, min(5.0, index_mod))

        if self.fm_engine and hasattr(self.fm_engine, 'enable_through_zero_fm'):
            self.fm_engine.enable_through_zero_fm(enabled, self.fm_index_modulation)

        print(f"🎛️ Through-zero FM {'enabled' if enabled else 'disabled'} (index mod: {self.fm_index_modulation:.1f})")

    def enable_formant_fm(self, enabled: bool = True, smoothing: float = 0.1):
        """Enable formant-based FM synthesis for vocal sounds."""
        self.formant_fm_enabled = enabled
        self.vowel_transition_smoothing = max(0.01, min(1.0, smoothing))

        if self.fm_engine and hasattr(self.fm_engine, 'enable_formant_fm'):
            self.fm_engine.enable_formant_fm(enabled, self.vowel_transition_smoothing)

        print(f"🎛️ Formant FM {'enabled' if enabled else 'disabled'} (smoothing: {self.vowel_transition_smoothing:.2f})")

    def enable_dynamic_algorithm_switching(self, enabled: bool = True, threshold: float = 0.5):
        """Enable dynamic algorithm switching based on modulation."""
        self.dynamic_algorithm_switching = enabled
        self.algorithm_switch_threshold = max(0.0, min(1.0, threshold))

        if self.fm_engine and hasattr(self.fm_engine, 'enable_dynamic_algorithm_switching'):
            self.fm_engine.enable_dynamic_algorithm_switching(enabled, self.algorithm_switch_threshold)

        print(f"🎛️ Dynamic algorithm switching {'enabled' if enabled else 'disabled'} (threshold: {self.algorithm_switch_threshold:.2f})")

    def set_operator_detuning(self, detune_amounts: List[float]):
        """Set detuning amounts for each operator (in semitones)."""
        self.operator_detune_amounts = [max(-12.0, min(12.0, d)) for d in detune_amounts[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_detuning'):
            self.fm_engine.set_operator_detuning(self.operator_detune_amounts)

        print(f"🎛️ Operator detuning: {self.operator_detune_amounts}")

    def set_operator_pitch_modulation(self, modulation_depths: List[float]):
        """Set pitch modulation depths for each operator."""
        self.operator_pitch_modulation = [max(0.0, min(1.0, m)) for m in modulation_depths[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_pitch_modulation'):
            self.fm_engine.set_operator_pitch_modulation(self.operator_pitch_modulation)

        print(f"🎛️ Operator pitch modulation: {self.operator_pitch_modulation}")

    def set_operator_amplitude_modulation(self, modulation_depths: List[float]):
        """Set amplitude modulation depths for each operator."""
        self.operator_amplitude_modulation = [max(0.0, min(1.0, m)) for m in modulation_depths[:6]]

        if self.fm_engine and hasattr(self.fm_engine, 'set_operator_amplitude_modulation'):
            self.fm_engine.set_operator_amplitude_modulation(self.operator_amplitude_modulation)

        print(f"🎛️ Operator amplitude modulation: {self.operator_amplitude_modulation}")

    def create_custom_algorithm(self, name: str, connections: List[Tuple[int, int, float]]) -> bool:
        """Create a custom FM algorithm with specified operator connections."""
        if not self.fm_engine or not hasattr(self.fm_engine, 'create_custom_algorithm'):
            return False

        # Validate connections (operator indices 0-5, modulation amounts)
        valid_connections = []
        for src, dst, amount in connections:
            if 0 <= src <= 5 and 0 <= dst <= 5 and src != dst:  # No self-modulation
                valid_connections.append((src, dst, max(0.0, min(1.0, amount))))

        return self.fm_engine.create_custom_algorithm(name, valid_connections)

    def morph_between_algorithms(self, algorithm1: int, algorithm2: int, morph_factor: float) -> bool:
        """Morph between two algorithms in real-time."""
        if not self.algorithm_morphing_enabled or not self.fm_engine:
            return False

        if not hasattr(self.fm_engine, 'morph_algorithms'):
            return False

        factor = max(0.0, min(1.0, morph_factor))
        return self.fm_engine.morph_algorithms(algorithm1, algorithm2, factor)

    def apply_formant_to_operator(self, operator_index: int, vowel: str) -> bool:
        """Apply vocal formant characteristics to a specific operator."""
        if operator_index < 0 or operator_index > 5 or vowel not in self.vowel_formants:
            return False

        if not self.fm_engine or not hasattr(self.fm_engine, 'apply_formant_to_operator'):
            return False

        return self.fm_engine.apply_formant_to_operator(operator_index, self.vowel_formants[vowel])

    def set_feedback_routing_matrix(self, routing_matrix: List[List[float]]) -> bool:
        """Set custom feedback routing matrix for operators."""
        if not self.multiple_feedback_paths or not self.fm_engine:
            return False

        if not hasattr(self.fm_engine, 'set_feedback_routing_matrix'):
            return False

        # Validate 6x6 matrix
        if len(routing_matrix) != 6 or any(len(row) != 6 for row in routing_matrix):
            return False

        # Clamp values to 0.0-1.0
        clamped_matrix = [[max(0.0, min(1.0, val)) for val in row] for row in routing_matrix]

        return self.fm_engine.set_feedback_routing_matrix(clamped_matrix)

    def get_advanced_fm_features(self) -> Dict[str, Any]:
        """Get status of all advanced FM features."""
        return {
            'algorithm_morphing': {
                'enabled': self.algorithm_morphing_enabled,
                'current_algorithm': self.current_algorithm,
                'target_algorithm': self.target_algorithm,
                'morph_factor': self.algorithm_morph_factor,
                'morph_speed': self.algorithm_morph_speed
            },
            'feedback_system': {
                'multiple_paths': self.multiple_feedback_paths,
                'coloring_enabled': self.feedback_coloring_enabled,
                'coloring_type': self.feedback_coloring_type,
                'enhancement': self.feedback_enhancement
            },
            'operator_stereo': {
                'enabled': self.operator_stereo_enabled,
                'pan_positions': self.operator_pan_positions,
                'level_offsets': self.operator_level_offsets
            },
            'operator_modulation': {
                'velocity_scaling': self.operator_velocity_scaling,
                'key_scaling': self.operator_key_scaling,
                'detuning': self.operator_detune_amounts,
                'pitch_modulation': self.operator_pitch_modulation,
                'amplitude_modulation': self.operator_amplitude_modulation
            },
            'advanced_fm': {
                'phase_modulation': self.phase_modulation_enabled,
                'through_zero_fm': self.through_zero_fm_enabled,
                'fm_index_modulation': self.fm_index_modulation,
                'formant_fm': self.formant_fm_enabled,
                'vowel_transition_smoothing': self.vowel_transition_smoothing
            },
            'dynamic_features': {
                'algorithm_switching': self.dynamic_algorithm_switching,
                'switch_threshold': self.algorithm_switch_threshold
            },
            'vocal_synthesis': {
                'formants_enabled': self.vocal_formants_enabled,
                'available_vowels': list(self.vowel_formants.keys()),
                'current_vowel': 'a'  # Default
            }
        }

    def get_fm_x_status(self) -> Dict[str, Any]:
        """Get Jupiter-X FM engine status."""
        return {
            'vocal_formants': self.vocal_formants_enabled,
            'ring_modulation': self.ring_modulation_enabled,
            'feedback_enhancement': self.feedback_enhancement,
            'ring_mod_connections': len(self.ring_mod_connections),
            'advanced_fm_features': self.get_advanced_fm_features(),
            'features_active': self.is_active()
        }
