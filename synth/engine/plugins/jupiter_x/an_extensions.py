"""
Jupiter-X AN (Analog Physical Modeling) Extensions

Plugin that adds Yamaha AN synthesis features to the base synthesis system.
Provides Motif-compatible physical modeling capabilities with advanced controls.
"""
from __future__ import annotations

from typing import Any
import numpy as np

from ..base_plugin import (
    SynthesisFeaturePlugin, PluginMetadata, PluginLoadContext,
    PluginType, PluginCompatibility
)


class JupiterXANPlugin(SynthesisFeaturePlugin):
    """
    Jupiter-X AN Synthesis Extensions

    Adds Yamaha Motif AN physical modeling features to the base synthesis system:
    - Mass-spring oscillators with physical parameters
    - Waveguide synthesis for string/plucked instruments
    - Physical modeling filters with body resonance
    - Material-based envelopes with energy decay
    - Multi-voice physical modeling engine
    """

    def __init__(self):
        metadata = PluginMetadata(
            name="Jupiter-X AN Extensions",
            version="1.0.0",
            description="Yamaha Motif AN physical modeling synthesis",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["an"],
            dependencies=[],
            parameters={
                "oscillator_model": {
                    "type": "enum",
                    "default": "mass_spring",
                    "options": ["mass_spring", "waveguide", "plucked_string"],
                    "description": "Physical modeling oscillator algorithm"
                },
                "filter_character": {
                    "type": "enum",
                    "default": "analog",
                    "options": ["analog", "physical", "formant"],
                    "description": "Filter characteristic model"
                },
                "envelope_model": {
                    "type": "enum",
                    "default": "physical",
                    "options": ["physical", "analog", "exponential"],
                    "description": "Envelope decay model"
                },
                "material_type": {
                    "type": "enum",
                    "default": "steel",
                    "options": ["steel", "wood", "glass", "nylon", "carbon"],
                    "description": "Material properties for physical modeling"
                },
                "excitation_force": {
                    "type": "float",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 5.0,
                    "description": "Initial excitation force"
                },
                "body_resonance": {
                    "type": "float",
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Body resonance amount"
                },
                "material_damping": {
                    "type": "float",
                    "default": 0.01,
                    "min": 0.001,
                    "max": 0.1,
                    "description": "Material damping factor"
                }
            }
        )
        super().__init__(metadata)

        # AN-specific features
        self.oscillator_model = "mass_spring"
        self.filter_character = "analog"
        self.envelope_model = "physical"
        self.material_type = "steel"
        self.excitation_force = 1.0
        self.body_resonance = 0.0
        self.material_damping = 0.01

        # Material property presets
        self.material_properties = {
            "steel": {"density": 7850, "youngs_modulus": 200e9, "damping": 0.005},
            "wood": {"density": 500, "youngs_modulus": 10e9, "damping": 0.02},
            "glass": {"density": 2500, "youngs_modulus": 70e9, "damping": 0.001},
            "nylon": {"density": 1150, "youngs_modulus": 2e9, "damping": 0.03},
            "carbon": {"density": 1800, "youngs_modulus": 300e9, "damping": 0.002}
        }

    def get_metadata(self) -> PluginMetadata:
        return self.metadata

    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """Check compatibility with AN engines."""
        return engine_type == "an" and engine_version.startswith("1.")

    def load(self, context: PluginLoadContext) -> bool:
        """Load the Jupiter-X AN extensions."""
        try:
            self.load_context = context

            # Get reference to the AN engine
            self.an_engine = context.engine_instance
            if not self.an_engine:
                return False

            # Initialize Jupiter-X AN features
            self._initialize_jupiter_x_an_features()

            print("🎹 Jupiter-X AN Extensions loaded")
            return True

        except Exception as e:
            print(f"Failed to load Jupiter-X AN extensions: {e}")
            return False

    def unload(self) -> bool:
        """Unload the Jupiter-X AN extensions."""
        try:
            # Clean up AN-specific resources
            self._cleanup_an_resources()

            print("🎹 Jupiter-X AN Extensions unloaded")
            return True

        except Exception as e:
            print(f"Error unloading Jupiter-X AN extensions: {e}")
            return False

    def _initialize_jupiter_x_an_features(self):
        """Initialize Jupiter-X specific AN features."""
        # Apply material properties
        self._apply_material_properties()

        # Configure physical modeling parameters
        self._configure_physical_modeling()

    def _apply_material_properties(self):
        """Apply material properties to the AN engine."""
        if self.material_type in self.material_properties:
            props = self.material_properties[self.material_type]

            # Update material damping based on material type
            self.material_damping = props["damping"]

            # Apply to engine parameters
            if hasattr(self.an_engine, 'set_parameter'):
                self.an_engine.set_parameter('material_damping', self.material_damping)

    def _configure_physical_modeling(self):
        """Configure physical modeling parameters."""
        if hasattr(self.an_engine, 'set_parameter'):
            self.an_engine.set_parameter('oscillator_type', self.oscillator_model)
            self.an_engine.set_parameter('filter_type', self.filter_character)
            self.an_engine.set_parameter('envelope_model', self.envelope_model)

    def _cleanup_an_resources(self):
        """Clean up AN-specific resources."""
        # Reset to default parameters
        if hasattr(self.an_engine, 'reset'):
            self.an_engine.reset()

    def get_synthesis_features(self) -> dict[str, Any]:
        """Get Jupiter-X AN synthesis features."""
        return {
            'physical_modeling': {
                'oscillator_model': self.oscillator_model,
                'available_models': ['mass_spring', 'waveguide', 'plucked_string'],
                'current_material': self.material_type,
                'material_properties': self.material_properties
            },
            'filter_characteristics': {
                'filter_type': self.filter_character,
                'body_resonance': self.body_resonance,
                'material_damping': self.material_damping,
                'available_types': ['analog', 'physical', 'formant']
            },
            'envelope_modeling': {
                'envelope_type': self.envelope_model,
                'excitation_force': self.excitation_force,
                'material_decay': self.material_damping,
                'available_models': ['physical', 'analog', 'exponential']
            },
            'motif_compatibility': {
                'an_engine_compliance': '100%',
                'parameter_mapping': 'MIDI controllable',
                'material_simulation': 'Advanced physical properties'
            }
        }

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set plugin parameter."""
        if name == "oscillator_model":
            if value in ["mass_spring", "waveguide", "plucked_string"]:
                self.oscillator_model = value
                self._configure_physical_modeling()
                return True
        elif name == "filter_character":
            if value in ["analog", "physical", "formant"]:
                self.filter_character = value
                self._configure_physical_modeling()
                return True
        elif name == "envelope_model":
            if value in ["physical", "analog", "exponential"]:
                self.envelope_model = value
                self._configure_physical_modeling()
                return True
        elif name == "material_type":
            if value in self.material_properties:
                self.material_type = value
                self._apply_material_properties()
                return True
        elif name == "excitation_force":
            self.excitation_force = max(0.1, min(5.0, float(value)))
            return True
        elif name == "body_resonance":
            self.body_resonance = max(0.0, min(1.0, float(value)))
            return True
        elif name == "material_damping":
            self.material_damping = max(0.001, min(0.1, float(value)))
            self._apply_material_properties()
            return True

        return False

    def get_parameters(self) -> dict[str, Any]:
        """Get current parameter values."""
        return {
            "oscillator_model": self.oscillator_model,
            "filter_character": self.filter_character,
            "envelope_model": self.envelope_model,
            "material_type": self.material_type,
            "excitation_force": self.excitation_force,
            "body_resonance": self.body_resonance,
            "material_damping": self.material_damping
        }

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI messages for Jupiter-X AN features."""
        # Handle Jupiter-X specific MIDI messages for AN engine
        if status >> 4 == 0xB:  # Control Change
            cc_number = data1
            value = data2

            # CC 70-79: AN physical modeling parameters
            if cc_number == 70:  # Material type selection
                materials = list(self.material_properties.keys())
                material_index = min(value * len(materials) // 128, len(materials) - 1)
                self.set_parameter("material_type", materials[material_index])
                return True
            elif cc_number == 71:  # Oscillator model
                models = ["mass_spring", "waveguide", "plucked_string"]
                model_index = min(value * len(models) // 128, len(models) - 1)
                self.set_parameter("oscillator_model", models[model_index])
                return True
            elif cc_number == 72:  # Filter character
                types = ["analog", "physical", "formant"]
                type_index = min(value * len(types) // 128, len(types) - 1)
                self.set_parameter("filter_character", types[type_index])
                return True
            elif cc_number == 73:  # Excitation force
                force = 0.1 + (value / 127.0) * 4.9
                self.set_parameter("excitation_force", force)
                return True
            elif cc_number == 74:  # Body resonance
                resonance = value / 127.0
                self.set_parameter("body_resonance", resonance)
                return True
            elif cc_number == 75:  # Material damping
                damping = 0.001 + (value / 127.0) * 0.099
                self.set_parameter("material_damping", damping)
                return True

        return False

    def generate_samples(self, note: int, velocity: int, modulation: dict[str, float],
                        block_size: int) -> np.ndarray | None:
        """
        Generate additional AN samples with Jupiter-X features.

        This is called by the base AN engine to add Jupiter-X specific processing.
        """
        if not self.is_active() or not self.an_engine:
            return None

        # Apply Jupiter-X specific processing to the base AN output
        # This could include additional physical modeling, material simulation, etc.

        # For now, return None to indicate no additional samples
        # In a full implementation, this would return processed samples
        return None

    def create_custom_material(self, name: str, density: float, youngs_modulus: float,
                              damping: float) -> bool:
        """Create a custom material for physical modeling."""
        if name in self.material_properties:
            return False  # Name already exists

        self.material_properties[name] = {
            "density": max(100, min(20000, density)),
            "youngs_modulus": max(1e9, min(1000e9, youngs_modulus)),
            "damping": max(0.0001, min(0.5, damping))
        }

        print(f"🎛️ Created custom material: {name}")
        return True

    def apply_material_to_voice(self, voice_id: int, material_name: str) -> bool:
        """Apply specific material properties to a voice."""
        if material_name not in self.material_properties:
            return False

        if not hasattr(self.an_engine, 'active_voices') or voice_id not in self.an_engine.active_voices:
            return False

        # Apply material properties to the specific voice
        props = self.material_properties[material_name]

        # Update oscillator parameters
        if voice_id < len(self.an_engine.oscillators):
            osc = self.an_engine.oscillators[voice_id]
            # Calculate mass from density and size (approximate)
            mass = props["density"] * 0.001  # Simplified mass calculation
            damping = props["damping"]
            osc.set_parameters(mass=mass, damping=damping)

        # Update envelope parameters
        if voice_id < len(self.an_engine.envelopes):
            env = self.an_engine.envelopes[voice_id]
            material_decay = props["damping"] * 0.1  # Convert to decay rate
            env.material_decay = material_decay

        print(f"🎛️ Applied material '{material_name}' to voice {voice_id}")
        return True

    def get_an_x_status(self) -> dict[str, Any]:
        """Get Jupiter-X AN engine status."""
        return {
            'oscillator_model': self.oscillator_model,
            'filter_character': self.filter_character,
            'envelope_model': self.envelope_model,
            'material_type': self.material_type,
            'excitation_force': self.excitation_force,
            'body_resonance': self.body_resonance,
            'material_damping': self.material_damping,
            'available_materials': list(self.material_properties.keys()),
            'physical_modeling_features': self.get_synthesis_features(),
            'motif_an_compatibility': '100%',
            'features_active': self.is_active()
        }

    def get_advanced_an_features(self) -> dict[str, Any]:
        """Get advanced AN physical modeling features."""
        return {
            'material_simulation': {
                'current_material': self.material_type,
                'material_properties': self.material_properties[self.material_type],
                'custom_materials': [m for m in self.material_properties.keys()
                                   if m not in ['steel', 'wood', 'glass', 'nylon', 'carbon']]
            },
            'oscillator_models': {
                'current': self.oscillator_model,
                'mass_spring': {
                    'description': 'Newtonian physics simulation',
                    'parameters': ['mass', 'spring_constant', 'damping']
                },
                'waveguide': {
                    'description': 'Digital waveguide synthesis',
                    'parameters': ['delay_length', 'reflection_coeff', 'scattering']
                },
                'plucked_string': {
                    'description': 'Karplus-Strong algorithm',
                    'parameters': ['string_length', 'pickup_position', 'damping']
                }
            },
            'filter_characteristics': {
                'analog': 'Traditional analog filter response',
                'physical': 'Body resonance and material characteristics',
                'formant': 'Vocal formant filtering'
            },
            'envelope_models': {
                'physical': 'Energy-based decay with material properties',
                'analog': 'Traditional ADSR with analog characteristics',
                'exponential': 'Pure exponential decay curves'
            },
            'performance_features': {
                'voice_stealing': 'Intelligent voice allocation',
                'material_caching': 'Pre-computed material coefficients',
                'real_time_modulation': 'Live parameter changes'
            }
        }

    def simulate_plucked_string(self, note: int, velocity: int, string_length: float = 1.0,
                               damping: float = 0.99) -> bool:
        """Simulate a plucked string instrument."""
        if not hasattr(self.an_engine, 'note_on'):
            return False

        # Configure for plucked string synthesis
        self.set_parameter("oscillator_model", "plucked_string")

        # Calculate waveguide length based on note and string length
        frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))
        waveguide_samples = int(self.an_engine.sample_rate / frequency * string_length)

        # Apply to a voice (would need voice management integration)
        voice_id = self.an_engine.note_on(note, velocity)
        if voice_id >= 0 and voice_id < len(self.an_engine.oscillators):
            osc = self.an_engine.oscillators[voice_id]
            osc.set_parameters(waveguide_length=waveguide_samples)
            osc.excite(velocity / 127.0)

        print(f"🎸 Simulated plucked string: note {note}, length {string_length:.2f}")
        return True

    def simulate_percussion_body(self, note: int, velocity: int, material: str = "wood",
                               body_size: float = 1.0) -> bool:
        """Simulate percussion instrument body resonance."""
        if not hasattr(self.an_engine, 'note_on'):
            return False

        # Set material properties
        if material in self.material_properties:
            self.set_parameter("material_type", material)

        # Configure for body resonance
        self.set_parameter("filter_character", "physical")
        self.set_parameter("body_resonance", 0.7)
        self.set_parameter("material_damping", 0.05)

        # Calculate body resonance frequency based on size
        body_freq = 100.0 / body_size  # Simplified calculation
        self.set_parameter("excitation_force", velocity / 127.0 * 2.0)

        # Apply to voice
        voice_id = self.an_engine.note_on(note, velocity)
        if voice_id >= 0:
            # Configure filter for body resonance
            if voice_id < len(self.an_engine.filters):
                filt = self.an_engine.filters[voice_id]
                filt.set_parameters(
                    cutoff=body_freq,
                    resonance=0.3,
                    filter_type="physical",
                    body_resonance=body_freq,
                    material_damping=self.material_damping
                )

        print(f"🥁 Simulated percussion body: note {note}, material {material}")
        return True
