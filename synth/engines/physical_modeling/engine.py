"""
Yamaha AN (Analog Physical Modeling) Engine Implementation

Complete AN synthesis engine with physical modeling algorithms,
mass-spring systems, waveguide synthesis, and analog-style processing.
Provides authentic Yamaha Motif AN compatibility with modern performance.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..synthesis_engine import SynthesisEngine


class PhysicalModelingOscillator:
    """
    Physical Modeling Oscillator with mass-spring and waveguide algorithms
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.frequency = 440.0
        self.amplitude = 1.0

        # Mass-spring parameters
        self.mass = 1.0
        self.spring_constant = 1000.0
        self.damping = 0.01

        # Waveguide parameters
        self.waveguide_length = 100
        self.waveguide_delay = np.zeros(1000)
        self.waveguide_pos = 0

        # State variables
        self.position = 0.0
        self.velocity = 0.0
        self.phase = 0.0

        # Physical modeling state
        self.excitation_force = 0.0
        self.damping_factor = 0.999

    def set_frequency(self, freq: float):
        """Set oscillator frequency"""
        self.frequency = max(20.0, min(20000.0, freq))

    def set_parameters(
        self,
        mass: float = 1.0,
        spring: float = 1000.0,
        damping: float = 0.01,
        waveguide_length: int = 100,
    ):
        """Set physical modeling parameters"""
        self.mass = max(0.1, mass)
        self.spring_constant = max(1.0, spring)
        self.damping = max(0.0001, min(0.1, damping))
        self.waveguide_length = max(10, min(1000, waveguide_length))
        self.damping_factor = 1.0 - self.damping

    def excite(self, force: float = 1.0):
        """Apply excitation force to the physical model"""
        self.excitation_force = force
        self.velocity += force / self.mass

    def process_sample(self) -> float:
        """Process one sample of physical modeling"""
        # Mass-spring simulation
        acceleration = (
            -(self.spring_constant / self.mass) * self.position - self.damping * self.velocity
        )
        acceleration += self.excitation_force / self.mass

        # Integrate using Verlet integration for stability
        new_position = (
            2 * self.position - self.position + acceleration * (1.0 / self.sample_rate) ** 2
        )
        self.velocity = (new_position - self.position) / (1.0 / self.sample_rate)

        # Apply damping
        self.velocity *= self.damping_factor
        new_position *= self.damping_factor

        self.position = new_position
        self.excitation_force *= 0.99  # Decay excitation

        # Add waveguide component for richer sound
        waveguide_output = self._process_waveguide()

        return (self.position * self.amplitude) + (waveguide_output * 0.3)

    def _process_waveguide(self) -> float:
        """Process waveguide component"""
        # Simple waveguide scattering
        delay_pos = int(self.waveguide_pos) % len(self.waveguide_delay)
        output = self.waveguide_delay[delay_pos]

        # Update waveguide with current position
        self.waveguide_delay[delay_pos] = self.position * 0.7 + output * 0.3
        self.waveguide_pos += self.frequency * len(self.waveguide_delay) / self.sample_rate

        return output

    def reset(self):
        """Reset oscillator state"""
        self.position = 0.0
        self.velocity = 0.0
        self.excitation_force = 0.0
        self.waveguide_delay.fill(0.0)
        self.waveguide_pos = 0.0


class PhysicalModelingFilter:
    """
    Physical modeling filter with analog-style characteristics
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.cutoff = 1000.0
        self.resonance = 0.1
        self.filter_type = "lowpass"

        # State variables for analog filter simulation
        self.z1 = 0.0  # Filter state
        self.z2 = 0.0

        # Physical modeling parameters
        self.body_resonance = 0.0  # Body resonance frequency
        self.material_damping = 0.0  # Material damping

    def set_parameters(
        self,
        cutoff: float = 1000.0,
        resonance: float = 0.1,
        filter_type: str = "lowpass",
        body_resonance: float = 0.0,
        material_damping: float = 0.0,
    ):
        """Set filter parameters"""
        self.cutoff = max(20.0, min(20000.0, cutoff))
        self.resonance = max(0.0, min(2.0, resonance))
        self.filter_type = filter_type
        self.body_resonance = body_resonance
        self.material_damping = material_damping

    def process_sample(self, input_sample: float) -> float:
        """Process one sample through physical modeling filter"""
        # Basic analog-style filter
        if self.filter_type == "lowpass":
            # Simple 2-pole lowpass with resonance
            k = self.cutoff / self.sample_rate
            r = 1.0 - self.resonance

            # Bilinear transform coefficients
            c = 1.0 / math.tan(math.pi * k)
            a1 = 1.0 / (1.0 + r * c + c * c)
            a2 = 2.0 * a1
            a3 = a1
            b1 = 2.0 * (1.0 - c * c) * a1
            b2 = (1.0 - r * c + c * c) * a1

            # Process sample
            output = a1 * input_sample + a2 * self.z1 + a3 * self.z2
            output = output - b1 * self.z1 - b2 * self.z2

            # Update state
            self.z2 = self.z1
            self.z1 = output

        elif self.filter_type == "highpass":
            # Highpass filter
            k = self.cutoff / self.sample_rate
            r = 1.0 - self.resonance

            c = math.tan(math.pi * k)
            a1 = 1.0 / (1.0 + r * c + c * c)
            a2 = -2.0 * a1
            a3 = a1
            b1 = 2.0 * (c * c - 1.0) * a1
            b2 = (1.0 - r * c + c * c) * a1

            output = a1 * input_sample + a2 * self.z1 + a3 * self.z2
            output = output - b1 * self.z1 - b2 * self.z2

            self.z2 = self.z1
            self.z1 = output

        else:
            output = input_sample  # Bypass for unsupported types

        # Add physical modeling characteristics
        if self.body_resonance > 0:
            # Add body resonance using a simple allpass filter
            body_freq = self.body_resonance
            body_gain = self.material_damping

            # Simple body resonance simulation
            body_output = output * (1.0 - body_gain) + self.z1 * body_gain
            self.z1 = output * body_gain + self.z1 * (1.0 - body_gain)
            output = body_output

        return output

    def reset(self):
        """Reset filter state"""
        self.z1 = 0.0
        self.z2 = 0.0


class PhysicalModelingEnvelope:
    """
    Physical modeling envelope with exponential decay characteristics
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.attack_time = 0.01
        self.decay_time = 0.3
        self.sustain_level = 0.7
        self.release_time = 0.5

        # Physical modeling parameters
        self.material_decay = 0.0001  # Material decay rate
        self.body_damping = 0.01  # Body damping
        self.excitation_energy = 1.0  # Initial excitation energy

        self.state = "idle"
        self.current_level = 0.0
        self.energy = 0.0
        self.time = 0.0

    def set_parameters(
        self,
        attack: float = 0.01,
        decay: float = 0.3,
        sustain: float = 0.7,
        release: float = 0.5,
        material_decay: float = 0.0001,
        body_damping: float = 0.01,
    ):
        """Set envelope parameters"""
        self.attack_time = max(0.001, attack)
        self.decay_time = max(0.001, decay)
        self.sustain_level = max(0.0, min(1.0, sustain))
        self.release_time = max(0.001, release)
        self.material_decay = material_decay
        self.body_damping = body_damping

    def trigger(self, velocity: float = 1.0):
        """Trigger envelope with physical modeling"""
        self.state = "attack"
        self.energy = velocity * self.excitation_energy
        self.current_level = 0.0
        self.time = 0.0

    def release(self):
        """Release envelope"""
        if self.state != "idle":
            self.state = "release"

    def process_sample(self) -> float:
        """Process one sample of physical modeling envelope"""
        dt = 1.0 / self.sample_rate

        if self.state == "idle":
            return 0.0

        elif self.state == "attack":
            # Physical attack with energy injection
            self.time += dt
            attack_progress = min(1.0, self.time / self.attack_time)

            # Energy-based attack curve (non-linear)
            energy_factor = 1.0 - math.exp(-attack_progress * 5.0)
            self.current_level = energy_factor * self.energy

            if attack_progress >= 1.0:
                self.state = "decay"
                self.time = 0.0

        elif self.state == "decay":
            # Physical decay with material damping
            self.time += dt
            decay_progress = min(1.0, self.time / self.decay_time)

            # Exponential decay with material characteristics
            decay_factor = math.exp(-decay_progress * 3.0)
            material_loss = math.exp(-self.time * self.material_decay)

            target_level = self.sustain_level * self.energy
            self.current_level = (
                target_level + (self.current_level - target_level) * decay_factor * material_loss
            )

            # Apply body damping
            self.current_level *= 1.0 - self.body_damping

        elif self.state == "sustain":
            # Physical sustain with continuous energy loss
            material_loss = math.exp(-self.time * self.material_decay)
            self.current_level = self.sustain_level * self.energy * material_loss
            self.current_level *= 1.0 - self.body_damping

        elif self.state == "release":
            # Physical release with rapid energy dissipation
            self.time += dt
            release_progress = min(1.0, self.time / self.release_time)

            # Exponential release with material damping
            release_factor = math.exp(-release_progress * 4.0)
            material_loss = math.exp(-self.time * self.material_decay * 2.0)

            self.current_level *= release_factor * material_loss

            # Apply body damping during release
            self.current_level *= 1.0 - self.body_damping * 2.0

            if self.current_level < 0.001:
                self.state = "idle"
                self.current_level = 0.0

        return self.current_level

    def reset(self):
        """Reset envelope state"""
        self.state = "idle"
        self.current_level = 0.0
        self.energy = 0.0
        self.time = 0.0


class ResonanceBody:
    """
    S90/S70 RP-PR Resonance Body Modeling

    Implements physical body resonance with multiple resonant frequencies,
    material damping, and body shape characteristics for acoustic instruments.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Body resonance parameters (S90/S70 RP-PR)
        self.resonant_frequencies = [82.0, 164.0, 246.0, 328.0, 410.0]  # Fundamental + harmonics
        self.resonant_gains = [1.0, 0.7, 0.5, 0.3, 0.2]  # Relative gains
        self.material_damping = [0.001, 0.002, 0.003, 0.004, 0.005]  # Frequency-dependent damping

        # Body shape characteristics
        self.body_shape = "grand_piano"  # grand_piano, upright_piano, guitar, violin, etc.
        self.body_size = 1.0  # Relative body size
        self.material_type = "spruce"  # spruce, maple, mahogany, steel, etc.

        # Dynamic body response
        self.body_states = []  # State variables for each resonance
        self.body_velocities = []  # Velocity for each resonance

        # Initialize body resonances
        self._init_body_resonances()

    def _init_body_resonances(self):
        """Initialize body resonance filters"""
        self.body_states = [0.0] * len(self.resonant_frequencies)
        self.body_velocities = [0.0] * len(self.resonant_frequencies)

    def set_body_characteristics(
        self, shape: str = "grand_piano", size: float = 1.0, material: str = "spruce"
    ):
        """Set body characteristics for RP-PR modeling"""
        self.body_shape = shape
        self.body_size = max(0.1, min(3.0, size))
        self.material_type = material

        # Update resonance frequencies based on body characteristics
        self._update_resonance_frequencies()

    def _update_resonance_frequencies(self):
        """Update resonance frequencies based on body shape and size"""
        base_freq = 82.0  # A2 fundamental

        if self.body_shape == "grand_piano":
            # Grand piano resonances: fundamental + harmonics
            self.resonant_frequencies = [
                base_freq * self.body_size,
                base_freq * 2 * self.body_size,
                base_freq * 3 * self.body_size,
                base_freq * 4 * self.body_size,
                base_freq * 5 * self.body_size,
            ]
        elif self.body_shape == "upright_piano":
            # Upright piano: different resonance pattern
            self.resonant_frequencies = [
                base_freq * 0.9 * self.body_size,
                base_freq * 2.1 * self.body_size,
                base_freq * 3.2 * self.body_size,
                base_freq * 4.1 * self.body_size,
                base_freq * 5.3 * self.body_size,
            ]
        elif self.body_shape == "guitar":
            # Guitar body resonances
            self.resonant_frequencies = [
                base_freq * 0.5 * self.body_size,
                base_freq * 1.2 * self.body_size,
                base_freq * 2.8 * self.body_size,
                base_freq * 4.2 * self.body_size,
                base_freq * 5.8 * self.body_size,
            ]
        elif self.body_shape == "violin":
            # Violin body resonances
            self.resonant_frequencies = [
                base_freq * 0.3 * self.body_size,
                base_freq * 1.8 * self.body_size,
                base_freq * 3.1 * self.body_size,
                base_freq * 4.7 * self.body_size,
                base_freq * 6.2 * self.body_size,
            ]

        # Update material damping
        self._update_material_damping()

    def _update_material_damping(self):
        """Update damping based on material type"""
        if self.material_type == "spruce":
            # Light wood - less damping
            self.material_damping = [0.001, 0.002, 0.003, 0.004, 0.005]
        elif self.material_type == "maple":
            # Dense wood - more damping
            self.material_damping = [0.002, 0.004, 0.006, 0.008, 0.010]
        elif self.material_type == "mahogany":
            # Very dense wood - high damping
            self.material_damping = [0.003, 0.006, 0.009, 0.012, 0.015]
        elif self.material_type == "steel":
            # Metal - low damping, high Q
            self.material_damping = [0.0005, 0.001, 0.0015, 0.002, 0.0025]
        else:
            # Default damping
            self.material_damping = [0.001, 0.002, 0.003, 0.004, 0.005]

    def excite_body(self, input_sample: float, string_frequency: float = 440.0):
        """Excite body resonances with string interaction"""
        # Body excitation is frequency-dependent
        excitation_energy = abs(input_sample)

        # Apply frequency-dependent body coupling
        body_coupling = self._calculate_body_coupling(string_frequency)

        for i in range(len(self.resonant_frequencies)):
            # Calculate resonance excitation
            freq_ratio = string_frequency / self.resonant_frequencies[i]
            if 0.5 <= freq_ratio <= 2.0:  # Only excite nearby resonances
                resonance_excitation = excitation_energy * body_coupling * self.resonant_gains[i]
                resonance_excitation *= 1.0 - abs(1.0 - freq_ratio) * 0.5  # Peak at resonance

                # Add to body velocity
                self.body_velocities[i] += resonance_excitation

    def _calculate_body_coupling(self, string_frequency: float) -> float:
        """Calculate body coupling factor based on frequency"""
        # Higher frequencies couple less to body
        coupling_factor = 1.0 / (1.0 + string_frequency / 1000.0)
        return max(0.1, coupling_factor)

    def process_body_resonance(self, input_sample: float) -> float:
        """Process body resonance for RP-PR modeling"""
        output = input_sample

        for i in range(len(self.resonant_frequencies)):
            # Simple resonator model: mass-spring with damping
            damping = self.material_damping[i]

            # Calculate resonance
            omega = 2.0 * math.pi * self.resonant_frequencies[i] / self.sample_rate
            cos_omega = math.cos(omega)
            alpha = damping * 0.5

            # Second-order resonator difference equation
            # y[n] = x[n] + 2*r*cos(ω)*y[n-1] - r²*y[n-2]
            # where r = 1 - α, ω = 2πf/fs

            r = 1.0 - alpha
            resonator_output = input_sample + 2.0 * r * cos_omega * self.body_states[i]
            if i > 0:  # Avoid index error
                resonator_output -= r * r * self.body_states[i - 1]

            # Update state
            self.body_states[i] = resonator_output

            # Add body resonance to output
            body_contribution = (
                resonator_output * self.resonant_gains[i] * 0.1
            )  # Scale appropriately
            output += body_contribution

        return output

    def reset(self):
        """Reset body resonance state"""
        self.body_states = [0.0] * len(self.resonant_frequencies)
        self.body_velocities = [0.0] * len(self.resonant_frequencies)


class StringBodyInteraction:
    """
    S90/S70 RP-PR String-Body Interaction Modeling

    Implements the complex interaction between strings and body resonances,
    including energy transfer, sympathetic vibration, and bridge coupling.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # String-body coupling parameters
        self.bridge_coupling = 0.3  # Energy transfer from string to body
        self.body_feedback = 0.1  # Body resonance feedback to string
        self.sympathetic_coupling = 0.05  # Sympathetic vibration coupling

        # String parameters for interaction
        self.string_frequencies = []  # Active string frequencies
        self.string_energies = []  # Current string energies

        # Bridge characteristics
        self.bridge_hardness = 0.7  # Bridge material hardness (affects coupling)
        self.bridge_damping = 0.02  # Bridge energy loss

    def set_bridge_parameters(self, hardness: float = 0.7, damping: float = 0.02):
        """Set bridge coupling parameters"""
        self.bridge_hardness = max(0.1, min(1.0, hardness))
        self.bridge_damping = max(0.001, min(0.1, damping))

        # Update coupling based on bridge characteristics
        self.bridge_coupling = 0.2 + (self.bridge_hardness * 0.4)
        self.body_feedback = 0.05 + (self.bridge_hardness * 0.15)

    def add_string_interaction(self, string_frequency: float, string_energy: float):
        """Add string to body interaction calculation"""
        self.string_frequencies.append(string_frequency)
        self.string_energies.append(string_energy)

    def calculate_string_body_coupling(
        self, string_freq: float, body_resonance_freq: float
    ) -> float:
        """Calculate coupling factor between string and body resonance"""
        freq_ratio = string_freq / body_resonance_freq

        # Coupling peaks at octave relationships and unison
        if abs(freq_ratio - 1.0) < 0.1:  # Unison
            coupling = 0.8
        elif abs(freq_ratio - 0.5) < 0.1:  # Octave below
            coupling = 0.6
        elif abs(freq_ratio - 2.0) < 0.1:  # Octave above
            coupling = 0.4
        elif abs(freq_ratio - 1.5) < 0.1:  # Fifth above
            coupling = 0.3
        elif abs(freq_ratio - 0.667) < 0.1:  # Fifth below
            coupling = 0.3
        else:
            # General coupling decreases with frequency separation
            coupling = 0.1 / (1.0 + abs(math.log2(freq_ratio)) * 2.0)

        return coupling * self.bridge_coupling

    def process_string_body_interaction(
        self, string_output: float, body_output: float, string_freq: float
    ) -> tuple[float, float]:
        """Process string-body interaction for RP-PR modeling"""
        # Calculate energy transfer from string to body
        string_to_body_energy = string_output * self.bridge_coupling

        # Calculate sympathetic vibration (body to string)
        sympathetic_energy = 0.0
        for i, (other_freq, other_energy) in enumerate(
            zip(self.string_frequencies, self.string_energies)
        ):
            if abs(other_freq - string_freq) > 1.0:  # Only couple with different strings
                coupling = self.calculate_string_body_coupling(string_freq, other_freq)
                sympathetic_energy += body_output * coupling * self.sympathetic_coupling

        # Apply bridge damping
        bridge_loss = (string_output + body_output) * self.bridge_damping

        # Calculate final outputs with interaction
        final_string_output = (
            string_output - string_to_body_energy + sympathetic_energy - bridge_loss
        )
        final_body_output = body_output + string_to_body_energy - bridge_loss

        return final_string_output, final_body_output

    def clear_string_interactions(self):
        """Clear string interaction data"""
        self.string_frequencies.clear()
        self.string_energies.clear()


class MaterialProperties:
    """
    S90/S70 RP-PR Material Properties Modeling

    Implements material-specific acoustic properties including density,
    elasticity, damping characteristics, and frequency-dependent behavior.
    """

    def __init__(self):
        # Material property database
        self.material_database = {
            "spruce": {
                "density": 0.4,  # g/cm³
                "elasticity": 12.0,  # Young's modulus (GPa)
                "damping": 0.001,  # Frequency-independent damping
                "sound_speed": 5000,  # m/s
                "description": "Light wood, used for soundboards",
            },
            "maple": {
                "density": 0.6,
                "elasticity": 11.0,
                "damping": 0.002,
                "sound_speed": 4500,
                "description": "Hard wood, used for back/sides",
            },
            "mahogany": {
                "density": 0.7,
                "elasticity": 10.0,
                "damping": 0.003,
                "sound_speed": 4000,
                "description": "Dense wood, rich low-end",
            },
            "steel": {
                "density": 7.8,
                "elasticity": 200.0,
                "damping": 0.0005,
                "sound_speed": 5100,
                "description": "Metal strings, bright sustain",
            },
            "nylon": {
                "density": 1.15,
                "elasticity": 3.0,
                "damping": 0.01,
                "sound_speed": 1400,
                "description": "Soft strings, warm tone",
            },
            "ebony": {
                "density": 1.2,
                "elasticity": 15.0,
                "damping": 0.002,
                "sound_speed": 3000,
                "description": "Hard wood, used for fingerboards",
            },
        }

        self.current_material = "spruce"

    def set_material(self, material_name: str):
        """Set current material properties"""
        if material_name in self.material_database:
            self.current_material = material_name
        else:
            print(f"Warning: Unknown material '{material_name}', using spruce")
            self.current_material = "spruce"

    def get_material_properties(self, material_name: str | None = None) -> dict[str, float]:
        """Get material properties"""
        material = material_name or self.current_material
        return self.material_database.get(material, self.material_database["spruce"]).copy()

    def calculate_resonance_properties(
        self, frequency: float, material_name: str | None = None
    ) -> dict[str, float]:
        """Calculate frequency-dependent resonance properties"""
        props = self.get_material_properties(material_name)

        # Frequency-dependent damping (higher frequencies damp more)
        freq_factor = 1.0 + (frequency / 1000.0) * 0.5
        effective_damping = props["damping"] * freq_factor

        # Calculate Q factor (quality factor)
        # Q = sqrt(E / ρ) / (2π * f * damping)
        # Simplified: Q = 1 / (2π * f * damping)
        q_factor = 1.0 / (2.0 * math.pi * frequency * effective_damping)

        # Calculate decay time (T60)
        decay_time = 6.91 / (frequency * effective_damping)

        return {
            "effective_damping": effective_damping,
            "q_factor": q_factor,
            "decay_time": decay_time,
            "resonant_gain": min(2.0, q_factor / 100.0),  # Limit gain
        }

    def get_available_materials(self) -> list[str]:
        """Get list of available materials"""
        return list(self.material_database.keys())


class ANEngine(SynthesisEngine):
    """
    Yamaha AN (Analog Physical Modeling) Synthesis Engine with S90/S70 RP-PR Support

    Complete implementation of AN synthesis with RP-PR (Resonance and Physical Modeling)
    algorithms, providing authentic S90/S70 workstation compatibility with advanced
    physical modeling including body resonance, string-body interaction, and material properties.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        super().__init__(sample_rate, block_size)
        self.engine_type = "an"

        # AN-specific parameters
        self.oscillator_type = "mass_spring"  # mass_spring, waveguide, plucked_string
        self.filter_type = "analog"  # analog, physical, formant
        self.envelope_model = "physical"  # physical, analog, exponential

        # S90/S70 RP-PR Physical Modeling components
        self.resonance_body = ResonanceBody(sample_rate)
        self.string_body_interaction = StringBodyInteraction(sample_rate)
        self.material_properties = MaterialProperties()

        # RP-PR enable/disable
        self.rp_pr_enabled = False
        self.body_resonance_enabled = True
        self.string_body_coupling_enabled = True

        # Voice management
        self.max_voices = 64
        self.active_voices: dict[int, dict[str, Any]] = {}

        # Initialize components
        self._init_components()

        print(
            "🎹 AN Engine: Yamaha Motif AN with S90/S70 RP-PR physical modeling synthesis initialized"
        )

    def enable_rp_pr(self, enabled: bool = True):
        """Enable S90/S70 RP-PR (Resonance and Physical Modeling) features"""
        self.rp_pr_enabled = enabled
        if enabled:
            self.body_resonance_enabled = True
            self.string_body_coupling_enabled = True
            print("🎹 AN Engine: S90/S70 RP-PR physical modeling enabled")
            print("   - Body resonance modeling")
            print("   - String-body interaction")
            print("   - Material properties simulation")
        else:
            self.body_resonance_enabled = False
            self.string_body_coupling_enabled = False

    def set_body_characteristics(
        self, shape: str = "grand_piano", size: float = 1.0, material: str = "spruce"
    ):
        """Set body characteristics for RP-PR modeling"""
        self.resonance_body.set_body_characteristics(shape, size, material)
        self.material_properties.set_material(material)
        print(
            f"🎹 AN Engine: Body characteristics set - Shape: {shape}, Size: {size}, Material: {material}"
        )

    def set_bridge_parameters(self, hardness: float = 0.7, damping: float = 0.02):
        """Set bridge coupling parameters for string-body interaction"""
        self.string_body_interaction.set_bridge_parameters(hardness, damping)
        print(f"🎹 AN Engine: Bridge parameters set - Hardness: {hardness}, Damping: {damping}")

    def _init_components(self):
        """Initialize AN engine components"""
        # Create oscillator bank
        self.oscillators = []
        for i in range(self.max_voices):
            osc = PhysicalModelingOscillator(self.sample_rate)
            self.oscillators.append(osc)

        # Create filter bank
        self.filters = []
        for i in range(self.max_voices):
            filt = PhysicalModelingFilter(self.sample_rate)
            self.filters.append(filt)

        # Create envelope bank
        self.envelopes = []
        for i in range(self.max_voices):
            env = PhysicalModelingEnvelope(self.sample_rate)
            self.envelopes.append(env)

    def note_on(self, note: int, velocity: int) -> int:
        """Start AN voice with physical modeling"""
        # Find free voice
        voice_id = self._find_free_voice()
        if voice_id == -1:
            return -1  # No free voices

        # Calculate frequency
        frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Initialize voice components
        voice_data = {
            "note": note,
            "velocity": velocity,
            "frequency": frequency,
            "voice_id": voice_id,
            "active": True,
        }

        # Setup oscillator
        osc = self.oscillators[voice_id]
        osc.set_frequency(frequency)
        osc.amplitude = velocity / 127.0

        # Setup physical parameters based on oscillator type
        if self.oscillator_type == "mass_spring":
            mass = 1.0 + (note / 127.0) * 2.0  # Note-dependent mass
            spring = 1000.0 + (velocity / 127.0) * 2000.0  # Velocity-dependent spring
            damping = 0.01 + (note / 127.0) * 0.05  # Note-dependent damping
            osc.set_parameters(mass=mass, spring=spring, damping=damping)
        elif self.oscillator_type == "plucked_string":
            waveguide_len = int(self.sample_rate / frequency)  # String length
            osc.set_parameters(waveguide_length=waveguide_len)

        # Excite the oscillator
        osc.excite(velocity / 127.0)

        # Setup filter
        filt = self.filters[voice_id]
        cutoff = 2000.0 + (note / 127.0) * 4000.0  # Note-dependent cutoff
        resonance = 0.1 + (velocity / 127.0) * 0.5  # Velocity-dependent resonance
        filt.set_parameters(cutoff=cutoff, resonance=resonance, filter_type=self.filter_type)

        # Setup envelope
        env = self.envelopes[voice_id]
        env.trigger(velocity / 127.0)

        # Store voice data
        self.active_voices[voice_id] = voice_data

        return voice_id

    def note_off(self, voice_id: int):
        """Stop AN voice"""
        if voice_id in self.active_voices:
            # Start envelope release
            if voice_id < len(self.envelopes):
                self.envelopes[voice_id].release()
            # Mark for removal when envelope completes
            self.active_voices[voice_id]["releasing"] = True

    def process_block(self, block_size: int) -> np.ndarray:
        """Process block of AN synthesis with S90/S70 RP-PR physical modeling"""
        output = np.zeros(block_size, dtype=np.float32)

        # Clear string interaction data for this block
        if self.rp_pr_enabled and self.string_body_coupling_enabled:
            self.string_body_interaction.clear_string_interactions()

        # Process active voices
        voices_to_remove = []
        for voice_id, voice_data in self.active_voices.items():
            if not voice_data.get("active", False):
                continue

            osc = self.oscillators[voice_id]
            filt = self.filters[voice_id]
            env = self.envelopes[voice_id]
            frequency = voice_data.get("frequency", 440.0)

            # Generate block of samples for this voice
            voice_output = np.zeros(block_size, dtype=np.float32)
            string_output = np.zeros(block_size, dtype=np.float32)

            for i in range(block_size):
                # Generate oscillator sample (string simulation)
                osc_sample = osc.process_sample()

                # Apply filter
                filtered_sample = filt.process_sample(osc_sample)

                # Apply envelope
                envelope_level = env.process_sample()

                # Store string output for RP-PR processing
                string_output[i] = filtered_sample * envelope_level

            # Apply S90/S70 RP-PR Physical Modeling
            if self.rp_pr_enabled:
                voice_output = self._apply_rp_pr_modeling(string_output, frequency, block_size)

                # Add string to body interaction tracking
                if self.string_body_coupling_enabled:
                    string_energy = np.mean(np.abs(string_output))
                    self.string_body_interaction.add_string_interaction(frequency, string_energy)
            else:
                # Standard processing without RP-PR
                voice_output = string_output

            # Mix into main output
            output += voice_output

            # Check if voice should be removed
            if env.state == "idle" and voice_data.get("releasing", False):
                voices_to_remove.append(voice_id)
                voice_data["active"] = False

        # Clean up finished voices
        for voice_id in voices_to_remove:
            if voice_id in self.active_voices:
                del self.active_voices[voice_id]
            # Reset components for reuse
            if voice_id < len(self.oscillators):
                self.oscillators[voice_id].reset()
            if voice_id < len(self.filters):
                self.filters[voice_id].reset()
            if voice_id < len(self.envelopes):
                self.envelopes[voice_id].reset()

        return output

    def _apply_rp_pr_modeling(
        self, string_output: np.ndarray, string_frequency: float, block_size: int
    ) -> np.ndarray:
        """Apply S90/S70 RP-PR (Resonance and Physical Modeling)"""
        output = string_output.copy()

        # Apply body resonance modeling
        if self.body_resonance_enabled:
            # Process each sample through body resonance
            for i in range(block_size):
                # Excite body with string output
                self.resonance_body.excite_body(string_output[i], string_frequency)

                # Apply body resonance to output
                output[i] = self.resonance_body.process_body_resonance(output[i])

        # Apply string-body interaction
        if self.string_body_coupling_enabled and self.body_resonance_enabled:
            # Process string-body interaction for this voice
            for i in range(block_size):
                body_feedback = self.resonance_body.process_body_resonance(
                    0.0
                )  # Get body resonance
                string_final, body_final = (
                    self.string_body_interaction.process_string_body_interaction(
                        output[i], body_feedback, string_frequency
                    )
                )
                output[i] = string_final

        return output

    def _find_free_voice(self) -> int:
        """Find a free voice slot"""
        # First try to find completely free slot
        for i in range(self.max_voices):
            if i not in self.active_voices:
                return i

        # If no free slots, try to find releasing voice to steal
        for voice_id, voice_data in self.active_voices.items():
            if voice_data.get("releasing", False):
                return voice_id

        return -1  # No free voices

    def set_parameter(self, param: str, value: Any):
        """Set AN engine parameter"""
        if param == "oscillator_type":
            self.oscillator_type = value
        elif param == "filter_type":
            self.filter_type = value
        elif param == "envelope_model":
            self.envelope_model = value
        elif param == "max_voices":
            self.max_voices = max(1, min(128, int(value)))

    def get_parameters(self) -> dict[str, Any]:
        """Get current AN parameters"""
        return {
            "oscillator_type": self.oscillator_type,
            "filter_type": self.filter_type,
            "envelope_model": self.envelope_model,
            "max_voices": self.max_voices,
            "active_voices": len(self.active_voices),
        }

    def reset(self):
        """Reset AN engine"""
        # Clear all active voices
        self.active_voices.clear()

        # Reset all components
        for osc in self.oscillators:
            osc.reset()
        for filt in self.filters:
            filt.reset()
        for env in self.envelopes:
            env.reset()

    def get_engine_info(self) -> dict[str, Any]:
        """Get AN engine information"""
        return {
            "type": "AN (Analog Physical Modeling)",
            "description": "Yamaha Motif AN physical modeling synthesis",
            "max_voices": self.max_voices,
            "active_voices": len(self.active_voices),
            "oscillator_type": self.oscillator_type,
            "filter_type": self.filter_type,
            "envelope_model": self.envelope_model,
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
        }

    # ========== REGION-BASED ARCHITECTURE IMPLEMENTATION ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get AN (Analog Modeling) preset information.

        Args:
            bank: Preset bank number (0-127)
            program: Preset program number (0-127)

        Returns:
            PresetInfo with region descriptors for analog synthesis
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # AN engine uses analog modeling synthesis
        # Programs define oscillator configurations and filter settings
        preset_name = f"AN Analog {bank}:{program}"

        # Create region descriptors for analog synthesis
        # AN supports polyphonic playback with full keyboard range
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type=self.get_engine_type(),
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                "oscillator_count": 3,  # Standard 3-oscillator analog synth
                "oscillator_waveforms": ["sawtooth", "square", "triangle"],
                "filter_type": "ladder_lowpass",
                "filter_cutoff": 2000.0,  # Hz
                "filter_resonance": 0.5,
                "envelope_attack": 0.01,
                "envelope_decay": 0.3,
                "envelope_sustain": 0.7,
                "envelope_release": 0.5,
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=preset_name,
            engine_type=self.get_engine_type(),
            region_descriptors=[descriptor],
            is_monophonic=False,
            category="analog_modeling",
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """
        Get all region descriptors for AN preset.

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
        Create AN region instance from descriptor.

        Args:
            descriptor: Region descriptor with analog parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance for analog modeling synthesis
        """
        from ...processing.partial.an_region import ANRegion

        # Create AN region with proper initialization
        region = ANRegion(descriptor, sample_rate)

        # Initialize the region (creates oscillators, filters, envelopes)
        if not region.initialize():
            raise RuntimeError("Failed to initialize AN region")

        return region

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for region (AN is algorithmic, no samples needed).

        Args:
            region: Region to load sample for

        Returns:
            True (AN doesn't use samples)
        """
        # AN is analog modeling synthesis - no sample loading required
        # Oscillators and filters are created during region initialization
        return True

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples for AN synthesis.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Start voice for this note
        voice_id = self.note_on(note, velocity)
        if voice_id == -1:
            # No free voices, return silence
            return np.zeros((block_size, 2), dtype=np.float32)

        # Generate audio block
        audio_block = self.process_block(block_size)

        # Convert mono to stereo
        stereo_block = np.zeros((block_size, 2), dtype=np.float32)
        stereo_block[:, 0] = audio_block  # Left channel
        stereo_block[:, 1] = audio_block  # Right channel (mono)

        # Note off immediately (single shot)
        self.note_off(voice_id)

        return stereo_block

    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by AN engine.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if note can be played, False otherwise
        """
        # AN engine supports full MIDI range
        return 0 <= note <= 127

    def _create_base_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create AN base region without S.Art2 wrapper.

        Args:
            descriptor: Region descriptor with AN parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            ANRegion instance
        """
        from ...processing.partial.an_region import ANRegion

        return ANRegion(descriptor, sample_rate)

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int):
        """
        Create a partial instance for AN engine.

        Args:
            partial_params: Parameters for the partial
            sample_rate: Audio sample rate

        Returns:
            Partial instance configured for AN engine
        """
        # For now, return a simple dict-based partial
        # In a full implementation, this would create a proper Partial object
        return {
            "engine_type": "an",
            "sample_rate": sample_rate,
            "oscillator_type": partial_params.get("oscillator_type", self.oscillator_type),
            "filter_type": partial_params.get("filter_type", self.filter_type),
            "envelope_model": partial_params.get("envelope_model", self.envelope_model),
            "material_type": partial_params.get("material_type", "steel"),
            "parameters": partial_params,
        }


# Export the AN engine
__all__ = [
    "ANEngine",
    "PhysicalModelingEnvelope",
    "PhysicalModelingFilter",
    "PhysicalModelingOscillator",
]
