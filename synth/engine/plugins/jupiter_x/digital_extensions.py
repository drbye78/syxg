"""
Jupiter-X Digital/Wavetable Engine Extensions

Plugin that adds Jupiter-X specific wavetable synthesis features to the base wavetable engine.
Eliminates duplication by extending the existing WavetableEngine rather than creating
a parallel implementation.
"""

from typing import Dict, List, Any, Optional
import numpy as np

from ..base_plugin import (
    SynthesisFeaturePlugin, PluginMetadata, PluginLoadContext,
    PluginType, PluginCompatibility
)


class JupiterXDigitalPlugin(SynthesisFeaturePlugin):
    """
    Jupiter-X Digital Synthesis Extensions

    Adds Jupiter-X specific wavetable features to the base wavetable engine:
    - Advanced wavetable morphing with multiple morphing types
    - Formant wavetable processing for vocal synthesis
    - Ring modulation integration
    - Dynamic wavetable loading and processing
    - Enhanced filter integration
    """

    def __init__(self):
        metadata = PluginMetadata(
            name="Jupiter-X Digital Extensions",
            version="1.0.0",
            description="Advanced wavetable synthesis from Roland Jupiter-X",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["wavetable"],
            dependencies=[],
            parameters={
                "morphing_type": {
                    "type": "enum",
                    "default": "linear",
                    "options": ["linear", "spectral", "harmonic", "formant"],
                    "description": "Type of wavetable morphing"
                },
                "formant_processing": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable formant processing for vocal synthesis"
                },
                "ring_modulation": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable ring modulation with wavetable output"
                },
                "dynamic_loading": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable dynamic wavetable loading"
                }
            }
        )
        super().__init__(metadata)

        # ===== PHASE 2.4: ADVANCED WAVETABLE FEATURES =====
        # Jupiter-X specific digital features
        self.morphing_type = "linear"
        self.formant_processing_enabled = False
        self.ring_modulation_enabled = True
        self.dynamic_loading_enabled = True

        # Multi-timbral wavetable system
        self.multi_timbral_enabled = False
        self.wavetable_layers = 4  # Up to 4 simultaneous wavetables
        self.layer_allocation = [True, False, False, False]  # Which layers are active

        # Wavetable scanning and modulation
        self.wavetable_scanning_enabled = False
        self.scan_position = 0.0  # 0.0 to 1.0
        self.scan_speed = 1.0  # Speed multiplier
        self.scan_modulation_depth = 0.0  # LFO modulation depth

        # Spectral processing
        self.spectral_processing_enabled = False
        self.fft_size = 2048
        self.spectral_enhancement = 0.0  # -1.0 to +1.0 (suppress/enhance)
        self.harmonic_focus = 0.5  # Focus on specific harmonics

        # Formant processing for vocal synthesis
        self.formant_tracking_enabled = False
        self.current_vowel = 'a'
        self.vowel_transition_speed = 0.1  # Smoothness of vowel changes

        # Ring modulation with wavetable carriers
        self.wavetable_ring_mod_enabled = False
        self.ring_mod_carrier_freq = 440.0
        self.ring_mod_index = 1.0

        # Real-time wavetable editing
        self.wavetable_editing_enabled = False
        self.editing_wavetable = None
        self.edit_position = 0
        self.edit_value = 0.0

        # Harmonic processing
        self.harmonic_enhancement_enabled = False
        self.harmonic_boost = [1.0] * 16  # Boost for first 16 harmonics
        self.harmonic_suppression = [1.0] * 16  # Suppression for first 16 harmonics

        # Morphing algorithms
        self.morphing_algorithms = {
            'linear': self._linear_morph,
            'spectral': self._spectral_morph,
            'harmonic': self._harmonic_morph,
            'formant': self._formant_morph
        }

        # Formant data for vocal wavetable processing
        self.vowel_formants = {
            'a': [800, 1150, 2900],   # "ah" as in "father"
            'e': [400, 1700, 2600],   # "eh" as in "bed"
            'i': [270, 2140, 2950],   # "ee" as in "beet"
            'o': [450, 800, 2830],    # "oh" as in "boat"
            'u': [325, 700, 2700],    # "oo" as in "boot"
        }

        # Ring modulation state
        self.ring_mod_carrier = None
        self.ring_mod_modulator = None

    def get_metadata(self) -> PluginMetadata:
        return self.metadata

    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """Check compatibility with wavetable engines."""
        return engine_type == "wavetable" and engine_version.startswith("1.")

    def load(self, context: PluginLoadContext) -> bool:
        """Load the Jupiter-X digital extensions."""
        try:
            self.load_context = context

            # Get reference to the base wavetable engine
            self.wavetable_engine = context.engine_instance
            if not self.wavetable_engine:
                return False

            # Initialize Jupiter-X specific features
            self._initialize_jupiter_x_digital_features()

            print("🎹 Jupiter-X Digital Extensions loaded")
            return True

        except Exception as e:
            print(f"Failed to load Jupiter-X digital extensions: {e}")
            return False

    def unload(self) -> bool:
        """Unload the Jupiter-X digital extensions."""
        try:
            # Clean up Jupiter-X specific resources
            self.ring_mod_carrier = None
            self.ring_mod_modulator = None
            self.formant_processing_enabled = False

            print("🎹 Jupiter-X Digital Extensions unloaded")
            return True

        except Exception as e:
            print(f"Error unloading Jupiter-X digital extensions: {e}")
            return False

    def _initialize_jupiter_x_digital_features(self):
        """Initialize Jupiter-X specific digital features."""
        # Set up advanced morphing capabilities
        if hasattr(self.wavetable_engine, 'enable_advanced_morphing'):
            self.wavetable_engine.enable_advanced_morphing(True)

        # Initialize ring modulation system
        self._setup_ring_modulation()

        # Load Jupiter-X specific wavetables if available
        if self.dynamic_loading_enabled:
            self._load_jupiter_x_wavetables()

    def _setup_ring_modulation(self):
        """Set up ring modulation system."""
        # Jupiter-X style ring modulation for wavetable output
        # This creates additional harmonics and complex timbres
        if hasattr(self.wavetable_engine, 'setup_ring_modulation'):
            self.wavetable_engine.setup_ring_modulation(True)

    def _load_jupiter_x_wavetables(self):
        """Load Jupiter-X specific wavetables."""
        # Jupiter-X has specific wavetable sets for different synthesis types
        jupiter_x_wavetables = [
            "JX_Analog_Square",
            "JX_Analog_Saw",
            "JX_Digital_Harmonics",
            "JX_Formant_Vowels",
            "JX_Complex_Timbres"
        ]

        for wavetable_name in jupiter_x_wavetables:
            if hasattr(self.wavetable_engine, 'load_wavetable'):
                # Attempt to load Jupiter-X wavetable
                # In practice, this would load from resource files
                self.wavetable_engine.load_wavetable(f"jupiter_x/{wavetable_name}", wavetable_name)

    def get_synthesis_features(self) -> Dict[str, Any]:
        """Get Jupiter-X digital synthesis features."""
        return {
            'morphing': {
                'type': self.morphing_type,
                'algorithms': list(self.morphing_algorithms.keys()),
                'advanced_morphing': True
            },
            'formant_processing': {
                'enabled': self.formant_processing_enabled,
                'vowels': list(self.vowel_formants.keys()),
                'formant_count': 3
            },
            'ring_modulation': {
                'enabled': self.ring_modulation_enabled,
                'carrier_active': self.ring_mod_carrier is not None,
                'modulator_active': self.ring_mod_modulator is not None
            },
            'dynamic_loading': {
                'enabled': self.dynamic_loading_enabled,
                'jupiter_x_wavetables': True
            },
            'filter_integration': {
                'biquad_filters': True,
                'formant_filtering': True,
                'dynamic_filtering': True
            }
        }

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set plugin parameter."""
        if name == "morphing_type":
            if value in self.morphing_algorithms:
                self.morphing_type = value
                self._update_morphing_algorithm()
                return True
        elif name == "formant_processing":
            self.formant_processing_enabled = bool(value)
            self._update_formant_processing()
            return True
        elif name == "ring_modulation":
            self.ring_modulation_enabled = bool(value)
            self._update_ring_modulation()
            return True
        elif name == "dynamic_loading":
            self.dynamic_loading_enabled = bool(value)
            self._update_dynamic_loading()
            return True

        return False

    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return {
            "morphing_type": self.morphing_type,
            "formant_processing": self.formant_processing_enabled,
            "ring_modulation": self.ring_modulation_enabled,
            "dynamic_loading": self.dynamic_loading_enabled
        }

    def _update_morphing_algorithm(self):
        """Update the morphing algorithm."""
        if not self.wavetable_engine:
            return

        # Set the morphing algorithm on the base engine
        if hasattr(self.wavetable_engine, 'set_morphing_algorithm'):
            self.wavetable_engine.set_morphing_algorithm(self.morphing_type)

    def _update_formant_processing(self):
        """Update formant processing settings."""
        if not self.wavetable_engine:
            return

        if self.formant_processing_enabled:
            # Enable formant processing with default vowel
            if hasattr(self.wavetable_engine, 'enable_formant_processing'):
                self.wavetable_engine.enable_formant_processing(True, self.vowel_formants['a'])
        else:
            # Disable formant processing
            if hasattr(self.wavetable_engine, 'enable_formant_processing'):
                self.wavetable_engine.enable_formant_processing(False)

    def _update_ring_modulation(self):
        """Update ring modulation settings."""
        if not self.wavetable_engine:
            return

        if self.ring_modulation_enabled:
            self._setup_ring_modulation()
        else:
            # Disable ring modulation
            if hasattr(self.wavetable_engine, 'setup_ring_modulation'):
                self.wavetable_engine.setup_ring_modulation(False)

    def _update_dynamic_loading(self):
        """Update dynamic loading settings."""
        if not self.wavetable_engine:
            return

        if self.dynamic_loading_enabled:
            # Re-enable Jupiter-X wavetable loading
            self._load_jupiter_x_wavetables()
        else:
            # Disable dynamic loading features
            if hasattr(self.wavetable_engine, 'disable_dynamic_loading'):
                self.wavetable_engine.disable_dynamic_loading()

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI messages for Jupiter-X digital features."""
        # Handle Jupiter-X specific MIDI messages for digital engine
        if status >> 4 == 0xB:  # Control Change
            cc_number = data1
            value = data2

            # CC 77: Morphing position (0-127)
            if cc_number == 77:
                morph_pos = value / 127.0
                self._set_morphing_position(morph_pos)
                return True

            # CC 78: Vowel selection (0-4 for a,e,i,o,u)
            if cc_number == 78 and 0 <= value <= 4:
                vowels = list(self.vowel_formants.keys())
                selected_vowel = vowels[min(value, len(vowels) - 1)]
                self._set_vowel_formant(selected_vowel)
                return True

        return False

    def _set_morphing_position(self, position: float):
        """Set the morphing position."""
        if self.wavetable_engine and hasattr(self.wavetable_engine, 'set_morphing_position'):
            self.wavetable_engine.set_morphing_position(position)

    def _set_vowel_formant(self, vowel: str):
        """Set the current vowel formant for processing."""
        if vowel in self.vowel_formants and self.wavetable_engine:
            if hasattr(self.wavetable_engine, 'set_formant_frequencies'):
                self.wavetable_engine.set_formant_frequencies(self.vowel_formants[vowel])

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> Optional[np.ndarray]:
        """
        Generate additional wavetable samples with Jupiter-X features.

        This is called by the base wavetable engine to add Jupiter-X specific processing.
        """
        if not self.is_active() or not self.wavetable_engine:
            return None

        # Apply Jupiter-X specific processing to the base wavetable output
        # This could include additional formant filtering, ring modulation, etc.

        # For now, return None to indicate no additional samples
        # In a full implementation, this would return processed samples
        return None

    # Jupiter-X specific morphing algorithms
    def _linear_morph(self, wavetable1: np.ndarray, wavetable2: np.ndarray,
                     morph_factor: float) -> np.ndarray:
        """Linear morphing between two wavetables."""
        return (1.0 - morph_factor) * wavetable1 + morph_factor * wavetable2

    def _spectral_morph(self, wavetable1: np.ndarray, wavetable2: np.ndarray,
                       morph_factor: float) -> np.ndarray:
        """Spectral morphing using FFT."""
        # Convert to frequency domain
        fft1 = np.fft.rfft(wavetable1)
        fft2 = np.fft.rfft(wavetable2)

        # Morph in frequency domain
        morphed_fft = (1.0 - morph_factor) * fft1 + morph_factor * fft2

        # Convert back to time domain
        return np.fft.irfft(morphed_fft).real

    def _harmonic_morph(self, wavetable1: np.ndarray, wavetable2: np.ndarray,
                       morph_factor: float) -> np.ndarray:
        """Morph based on harmonic content."""
        # Analyze harmonic content and morph accordingly
        # This is a simplified implementation
        return self._linear_morph(wavetable1, wavetable2, morph_factor)

    def _formant_morph(self, wavetable1: np.ndarray, wavetable2: np.ndarray,
                      morph_factor: float) -> np.ndarray:
        """Formant-based morphing for vocal transitions."""
        # Use formant information to create smooth vocal transitions
        # This would interpolate between vowel formants
        return self._linear_morph(wavetable1, wavetable2, morph_factor)

    def apply_morphing(self, source_wavetable: str, target_wavetable: str,
                      morph_factor: float) -> Optional[np.ndarray]:
        """
        Apply Jupiter-X style morphing between wavetables.

        Args:
            source_wavetable: Name of source wavetable
            target_wavetable: Name of target wavetable
            morph_factor: Morphing factor (0.0 to 1.0)

        Returns:
            Morphed wavetable data or None if not available
        """
        if not self.wavetable_engine:
            return None

        # Get wavetable data from engine
        source_data = None
        target_data = None

        if hasattr(self.wavetable_engine, 'get_wavetable_data'):
            source_data = self.wavetable_engine.get_wavetable_data(source_wavetable)
            target_data = self.wavetable_engine.get_wavetable_data(target_wavetable)

        if source_data is None or target_data is None:
            return None

        # Apply the selected morphing algorithm
        morph_func = self.morphing_algorithms.get(self.morphing_type, self._linear_morph)
        return morph_func(source_data, target_data, morph_factor)

    # ===== PHASE 2.4: ADVANCED WAVETABLE METHODS =====

    def enable_multi_timbral(self, enabled: bool = True, layers: int = 4):
        """Enable multi-timbral wavetable playback."""
        self.multi_timbral_enabled = enabled
        self.wavetable_layers = max(1, min(4, layers))
        self.layer_allocation = [True] + [False] * (self.wavetable_layers - 1)

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_multi_timbral'):
            self.wavetable_engine.enable_multi_timbral(enabled, self.wavetable_layers)

        print(f"🎛️ Multi-timbral {'enabled' if enabled else 'disabled'} ({self.wavetable_layers} layers)")

    def enable_wavetable_scanning(self, enabled: bool = True, speed: float = 1.0, modulation_depth: float = 0.0):
        """Enable wavetable scanning with position modulation."""
        self.wavetable_scanning_enabled = enabled
        self.scan_speed = max(0.1, min(10.0, speed))
        self.scan_modulation_depth = max(0.0, min(1.0, modulation_depth))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_scanning'):
            self.wavetable_engine.enable_scanning(enabled, self.scan_speed, self.scan_modulation_depth)

        print(f"🎛️ Wavetable scanning {'enabled' if enabled else 'disabled'} (speed: {self.scan_speed:.1f}x, mod: {self.scan_modulation_depth:.2f})")

    def set_scan_position(self, position: float):
        """Set the wavetable scan position (0.0 to 1.0)."""
        self.scan_position = max(0.0, min(1.0, position))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'set_scan_position'):
            self.wavetable_engine.set_scan_position(self.scan_position)

    def enable_spectral_processing(self, enabled: bool = True, fft_size: int = 2048,
                                 enhancement: float = 0.0, harmonic_focus: float = 0.5):
        """Enable spectral processing with FFT manipulation."""
        self.spectral_processing_enabled = enabled
        self.fft_size = max(512, min(8192, fft_size))
        self.spectral_enhancement = max(-1.0, min(1.0, enhancement))
        self.harmonic_focus = max(0.0, min(1.0, harmonic_focus))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_spectral_processing'):
            self.wavetable_engine.enable_spectral_processing(enabled, self.fft_size,
                                                           self.spectral_enhancement,
                                                           self.harmonic_focus)

        print(f"🎛️ Spectral processing {'enabled' if enabled else 'disabled'} (FFT: {self.fft_size}, enhancement: {self.spectral_enhancement:.2f})")

    def enable_formant_tracking(self, enabled: bool = True, transition_speed: float = 0.1):
        """Enable formant tracking for vocal synthesis."""
        self.formant_tracking_enabled = enabled
        self.vowel_transition_speed = max(0.01, min(1.0, transition_speed))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_formant_tracking'):
            self.wavetable_engine.enable_formant_tracking(enabled, self.vowel_transition_speed)

        print(f"🎛️ Formant tracking {'enabled' if enabled else 'disabled'} (transition: {self.vowel_transition_speed:.2f})")

    def set_vowel_formants(self, vowel: str, custom_formants: Optional[List[float]] = None):
        """Set vowel formants for vocal synthesis."""
        if custom_formants:
            # Allow custom formant frequencies
            self.vowel_formants[vowel] = custom_formants[:3]  # Limit to 3 formants
        elif vowel in self.vowel_formants:
            # Use predefined vowels
            self.current_vowel = vowel
        else:
            return

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'set_vowel_formants'):
            self.wavetable_engine.set_vowel_formants(vowel, self.vowel_formants.get(vowel, []))

        print(f"🎛️ Vowel formants set to '{vowel}': {self.vowel_formants.get(vowel, [])}")

    def enable_wavetable_ring_modulation(self, enabled: bool = True, carrier_freq: float = 440.0, index: float = 1.0):
        """Enable ring modulation with wavetable carriers."""
        self.wavetable_ring_mod_enabled = enabled
        self.ring_mod_carrier_freq = max(20.0, min(20000.0, carrier_freq))
        self.ring_mod_index = max(0.0, min(10.0, index))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_ring_modulation'):
            self.wavetable_engine.enable_ring_modulation(enabled, self.ring_mod_carrier_freq, self.ring_mod_index)

        print(f"🎛️ Wavetable ring modulation {'enabled' if enabled else 'disabled'} (carrier: {self.ring_mod_carrier_freq:.0f}Hz, index: {self.ring_mod_index:.1f})")

    def enable_realtime_editing(self, enabled: bool = True, wavetable_name: Optional[str] = None):
        """Enable real-time wavetable editing via MIDI."""
        self.wavetable_editing_enabled = enabled
        self.editing_wavetable = wavetable_name

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_realtime_editing'):
            self.wavetable_engine.enable_realtime_editing(enabled, wavetable_name)

        print(f"🎛️ Real-time wavetable editing {'enabled' if enabled else 'disabled'} ({'all wavetables' if not wavetable_name else wavetable_name})")

    def edit_wavetable_point(self, position: int, value: float, wavetable_name: Optional[str] = None):
        """Edit a single point in a wavetable."""
        if not self.wavetable_editing_enabled:
            return False

        target_wavetable = wavetable_name or self.editing_wavetable
        if not target_wavetable:
            return False

        # Validate parameters
        position = max(0, min(2047, position))  # Assuming 2048-point wavetables
        value = max(-1.0, min(1.0, value))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'edit_wavetable_point'):
            return self.wavetable_engine.edit_wavetable_point(target_wavetable, position, value)

        return False

    def enable_harmonic_processing(self, enabled: bool = True, boost_factors: Optional[List[float]] = None,
                                 suppression_factors: Optional[List[float]] = None):
        """Enable harmonic enhancement and suppression."""
        self.harmonic_enhancement_enabled = enabled

        if boost_factors:
            self.harmonic_boost = list(boost_factors[:16]) + [1.0] * (16 - len(boost_factors))
        if suppression_factors:
            self.harmonic_suppression = list(suppression_factors[:16]) + [1.0] * (16 - len(suppression_factors))

        if self.wavetable_engine and hasattr(self.wavetable_engine, 'enable_harmonic_processing'):
            self.wavetable_engine.enable_harmonic_processing(enabled, self.harmonic_boost, self.harmonic_suppression)

        print(f"🎛️ Harmonic processing {'enabled' if enabled else 'disabled'}")

    def apply_spectral_enhancement(self, wavetable_data: np.ndarray) -> np.ndarray:
        """Apply spectral enhancement to wavetable data."""
        if not self.spectral_processing_enabled or self.spectral_enhancement == 0.0:
            return wavetable_data

        # Perform FFT
        fft_data = np.fft.rfft(wavetable_data, n=self.fft_size)

        # Apply spectral enhancement
        if self.spectral_enhancement > 0:
            # Enhance higher harmonics
            enhancement_curve = np.linspace(1.0, 1.0 + self.spectral_enhancement, len(fft_data))
            fft_data *= enhancement_curve
        else:
            # Suppress higher harmonics
            suppression_curve = np.linspace(1.0, 1.0 + self.spectral_enhancement, len(fft_data))
            fft_data *= suppression_curve

        # Apply harmonic focus
        if self.harmonic_focus != 0.5:
            # Create focus curve based on harmonic content
            harmonic_positions = np.arange(len(fft_data)) / len(fft_data)
            focus_curve = 1.0 + (self.harmonic_focus - 0.5) * 2.0 * np.sin(np.pi * harmonic_positions)
            fft_data *= focus_curve

        # Inverse FFT
        enhanced_data = np.fft.irfft(fft_data).real

        # Normalize to prevent clipping
        max_val = np.max(np.abs(enhanced_data))
        if max_val > 0:
            enhanced_data /= max_val

        return enhanced_data

    def apply_formant_filtering(self, wavetable_data: np.ndarray) -> np.ndarray:
        """Apply formant filtering for vocal synthesis."""
        if not self.formant_tracking_enabled:
            return wavetable_data

        # Get current vowel formants
        formants = self.vowel_formants.get(self.current_vowel, [800, 1150, 2900])

        # Apply formant filtering (simplified implementation)
        filtered_data = wavetable_data.copy()

        # This would implement proper formant filtering
        # For now, return original data
        return filtered_data

    def generate_multi_layer_wavetable(self, base_wavetable: np.ndarray, layer_count: int = 4) -> np.ndarray:
        """Generate multi-layer wavetable from base wavetable."""
        if not self.multi_timbral_enabled or layer_count <= 1:
            return base_wavetable

        # Create variations of the base wavetable for each layer
        layers = [base_wavetable]

        for i in range(1, min(layer_count, len(self.layer_allocation))):
            if self.layer_allocation[i]:
                # Create layer variation (phase shift, amplitude modulation, etc.)
                phase_shift = (i / layer_count) * 2 * np.pi
                layer_data = base_wavetable * np.sin(np.arange(len(base_wavetable)) * 0.01 + phase_shift)
                layers.append(layer_data)

        # Mix layers according to allocation
        result = np.zeros_like(base_wavetable)
        for i, layer in enumerate(layers):
            if i < len(self.layer_allocation) and self.layer_allocation[i]:
                result += layer * (1.0 / len(layers))  # Equal mixing

        return result

    def process_wavetable_scanning(self, base_output: np.ndarray, lfo_value: float = 0.0) -> np.ndarray:
        """Process wavetable scanning with modulation."""
        if not self.wavetable_scanning_enabled:
            return base_output

        # Calculate scan position with LFO modulation
        scan_pos = self.scan_position
        if self.scan_modulation_depth > 0:
            scan_pos += lfo_value * self.scan_modulation_depth
            scan_pos = max(0.0, min(1.0, scan_pos))

        # Update scan position based on speed
        self.scan_position = (self.scan_position + self.scan_speed * 0.001) % 1.0

        # Apply scanning effect (simplified - would interpolate between wavetable positions)
        return base_output

    def create_custom_wavetable(self, name: str, size: int = 2048, waveform_type: str = 'sine') -> bool:
        """Create a custom wavetable programmatically."""
        if not self.wavetable_editing_enabled:
            return False

        # Generate wavetable data based on type
        if waveform_type == 'sine':
            data = np.sin(2 * np.pi * np.arange(size) / size)
        elif waveform_type == 'sawtooth':
            data = 2 * (np.arange(size) / size) - 1
        elif waveform_type == 'square':
            data = np.where(np.arange(size) < size // 2, 1.0, -1.0)
        elif waveform_type == 'triangle':
            data = 2 * np.abs(2 * (np.arange(size) / size) - 1) - 1
        else:
            data = np.random.uniform(-1.0, 1.0, size)  # Noise

        # Apply spectral enhancement if enabled
        if self.spectral_processing_enabled:
            data = self.apply_spectral_enhancement(data)

        # Load into engine
        if self.wavetable_engine and hasattr(self.wavetable_engine, 'create_wavetable'):
            return self.wavetable_engine.create_wavetable(name, data)

        return False

    def get_advanced_wavetable_features(self) -> Dict[str, Any]:
        """Get status of all advanced wavetable features."""
        return {
            'multi_timbral': {
                'enabled': self.multi_timbral_enabled,
                'layers': self.wavetable_layers,
                'allocation': self.layer_allocation
            },
            'scanning': {
                'enabled': self.wavetable_scanning_enabled,
                'position': self.scan_position,
                'speed': self.scan_speed,
                'modulation_depth': self.scan_modulation_depth
            },
            'spectral_processing': {
                'enabled': self.spectral_processing_enabled,
                'fft_size': self.fft_size,
                'enhancement': self.spectral_enhancement,
                'harmonic_focus': self.harmonic_focus
            },
            'formant_tracking': {
                'enabled': self.formant_tracking_enabled,
                'current_vowel': self.current_vowel,
                'transition_speed': self.vowel_transition_speed,
                'available_vowels': list(self.vowel_formants.keys())
            },
            'ring_modulation': {
                'enabled': self.wavetable_ring_mod_enabled,
                'carrier_freq': self.ring_mod_carrier_freq,
                'index': self.ring_mod_index
            },
            'realtime_editing': {
                'enabled': self.wavetable_editing_enabled,
                'editing_wavetable': self.editing_wavetable,
                'edit_position': self.edit_position,
                'edit_value': self.edit_value
            },
            'harmonic_processing': {
                'enabled': self.harmonic_enhancement_enabled,
                'boost_factors': self.harmonic_boost,
                'suppression_factors': self.harmonic_suppression
            }
        }

    def get_digital_engine_status(self) -> Dict[str, Any]:
        """Get Jupiter-X digital engine status."""
        return {
            'morphing_type': self.morphing_type,
            'formant_processing': self.formant_processing_enabled,
            'ring_modulation': self.ring_modulation_enabled,
            'dynamic_loading': self.dynamic_loading_enabled,
            'morphing_algorithms': list(self.morphing_algorithms.keys()),
            'available_vowels': list(self.vowel_formants.keys()),
            'advanced_wavetable_features': self.get_advanced_wavetable_features(),
            'features_active': self.is_active()
        }
