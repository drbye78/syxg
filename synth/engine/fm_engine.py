"""
FM (Frequency Modulation) Synthesis Engine

Implements FM synthesis with 2-6 operators supporting various algorithms
including basic FM, stacked FM, and feedback FM. Provides DX7-style
parameter sets and real-time modulation capabilities.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import math

from .synthesis_engine import SynthesisEngine
from ..partial.fm_partial import FMPartial
from ..effects.xg_sysex_controller import XGSYSEXController
from ..gs.jv2080_nrpn_controller import JV2080NRPNController
from .plugins.plugin_registry import get_global_plugin_registry
from .plugins.base_plugin import PluginLoadContext, SynthesisFeaturePlugin


class FMXLFO:
    """
    FM-X Compatible LFO (Low Frequency Oscillator)

    Provides modulation sources for FM-X synthesis with multiple waveforms
    and assignable routing.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize FM-X LFO."""
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.frequency = 1.0  # Hz
        self.waveform = "sine"  # sine, triangle, sawtooth, square, random
        self.depth = 1.0
        self.enabled = True

        # Random LFO state
        self.random_value = 0.0
        self.random_hold_time = 0.0

    def set_parameters(
        self, frequency: float = 1.0, waveform: str = "sine", depth: float = 1.0
    ):
        """Set LFO parameters."""
        self.frequency = max(0.01, min(20.0, frequency))  # 0.01-20 Hz range
        self.waveform = waveform
        self.depth = max(0.0, min(1.0, depth))

    def generate_sample(self) -> float:
        """Generate LFO sample."""
        if not self.enabled:
            return 0.0

        # Update phase
        phase_increment = 2.0 * math.pi * self.frequency / self.sample_rate
        self.phase += phase_increment
        if self.phase >= 2.0 * math.pi:
            self.phase -= 2.0 * math.pi

        # Generate waveform
        if self.waveform == "sine":
            value = math.sin(self.phase)
        elif self.waveform == "triangle":
            value = (
                2.0
                * abs(
                    2.0
                    * (
                        self.phase / (2.0 * math.pi)
                        - math.floor(self.phase / (2.0 * math.pi) + 0.5)
                    )
                )
                - 1.0
            )
        elif self.waveform == "sawtooth":
            value = 2.0 * (
                self.phase / (2.0 * math.pi)
                - math.floor(self.phase / (2.0 * math.pi) + 0.5)
            )
        elif self.waveform == "square":
            value = 1.0 if math.sin(self.phase) >= 0 else -1.0
        elif self.waveform == "random":
            # Sample and hold random
            self.random_hold_time -= 1.0 / self.sample_rate
            if self.random_hold_time <= 0:
                self.random_value = (np.random.random() - 0.5) * 2.0  # -1 to 1
                self.random_hold_time = 1.0 / self.frequency  # Hold for one cycle
            value = self.random_value
        else:
            value = math.sin(self.phase)  # Default to sine

        return value * self.depth

    def reset(self):
        """Reset LFO state."""
        self.phase = 0.0
        self.random_value = 0.0
        self.random_hold_time = 0.0


class FMOperator:
    """
    FM-X Compatible Operator with 8-stage envelopes and advanced modulation.

    Each operator supports:
    - 8-stage envelopes with loop points
    - Operator scaling (key/velocity sensitivity)
    - Multiple waveforms including formants
    - Advanced feedback and ring modulation
    - Individual LFO modulation
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize FM-X operator."""
        self.sample_rate = sample_rate

        # Oscillator parameters
        self.frequency_ratio = 1.0
        self.detune_cents = 0.0
        self.feedback_level = 0  # 0-7 levels
        self.waveform = "sine"
        self.phase = 0.0

        # FM-X 8-stage envelope (Level, Rate, Loop)
        self.envelope_levels = [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]  # 8 levels
        self.envelope_rates = [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]  # 8 rates
        self.envelope_loop_start = -1  # -1 = no loop
        self.envelope_loop_end = -1
        self.envelope_phase = "idle"
        self.envelope_stage = 0
        self.envelope_value = 0.0
        self.envelope_time = 0.0

        # Operator scaling (FM-X style)
        self.key_scaling_depth = 0  # 0-7
        self.velocity_sensitivity = 0  # 0-7
        self.key_scaling_curve = "linear"  # linear, exp, log

        # Advanced modulation
        self.amplitude_mod = 1.0
        self.frequency_mod = 0.0
        self.phase_mod = 0.0

        # Feedback state (enhanced)
        self.feedback_sample = 0.0
        self.feedback_buffer = np.zeros(8, dtype=np.float32)  # Multi-tap feedback

        # Formant synthesis
        self.formant_enabled = False
        self.formant_data = []  # Spectral formant data

        # Ring modulation
        self.ring_mod_enabled = False
        self.ring_mod_operator = -1  # Operator to ring modulate with

        # LFO modulation
        self.lfo_depth = 0.0
        self.lfo_waveform = "sine"
        self.lfo_speed = 1.0
        self.lfo_phase = 0.0

    def set_parameters(self, params: Dict[str, Any]):
        """Set FM-X operator parameters."""
        self.frequency_ratio = params.get("frequency_ratio", 1.0)
        self.detune_cents = params.get("detune_cents", 0.0)
        self.feedback_level = params.get("feedback_level", 0)
        self.waveform = params.get("waveform", "sine")

        # FM-X 8-stage envelope parameters
        if "envelope_levels" in params:
            self.envelope_levels = params["envelope_levels"][:8]  # Ensure 8 levels
        if "envelope_rates" in params:
            self.envelope_rates = params["envelope_rates"][:8]  # Ensure 8 rates

        self.envelope_loop_start = params.get("envelope_loop_start", -1)
        self.envelope_loop_end = params.get("envelope_loop_end", -1)

        # Operator scaling
        self.key_scaling_depth = params.get("key_scaling_depth", 0)
        self.velocity_sensitivity = params.get("velocity_sensitivity", 0)
        self.key_scaling_curve = params.get("key_scaling_curve", "linear")

        # Formant synthesis
        self.formant_enabled = params.get("formant_enabled", False)
        if "formant_data" in params:
            self.formant_data = params["formant_data"]

        # Ring modulation
        self.ring_mod_enabled = params.get("ring_mod_enabled", False)
        self.ring_mod_operator = params.get("ring_mod_operator", -1)

        # LFO parameters
        self.lfo_depth = params.get("lfo_depth", 0.0)
        self.lfo_waveform = params.get("lfo_waveform", "sine")
        self.lfo_speed = params.get("lfo_speed", 1.0)

    def note_on(self, velocity: int = 127):
        """Start FM-X 8-stage envelope."""
        self.envelope_phase = "active"
        self.envelope_stage = 0
        self.envelope_time = 0.0
        self.envelope_value = self.envelope_levels[0]

        # Apply velocity sensitivity
        if self.velocity_sensitivity > 0:
            velocity_scale = (velocity / 127.0) ** (
                1.0 / (8 - self.velocity_sensitivity)
            )
            self.envelope_value *= velocity_scale

    def note_off(self):
        """Start envelope release phase."""
        # Jump to release stages (stages 6-7 in FM-X)
        if self.envelope_loop_start >= 0 and self.envelope_loop_end >= 0:
            # If looping, stop at current loop point
            self.envelope_stage = min(self.envelope_stage, self.envelope_loop_end)
        else:
            # Go to release stages
            self.envelope_stage = 6  # Release stage
        self.envelope_time = 0.0

    def update_envelope(self, dt: float):
        """Update FM-X 8-stage envelope."""
        if self.envelope_phase == "idle":
            self.envelope_value = 0.0
            return

        self.envelope_time += dt

        # Get current stage parameters
        current_level = self.envelope_levels[self.envelope_stage]
        next_level = self.envelope_levels[min(self.envelope_stage + 1, 7)]
        rate = self.envelope_rates[self.envelope_stage]

        # Handle zero rate (instant transition)
        if rate <= 0.001:
            self.envelope_value = next_level
            self._advance_envelope_stage()
            return

        # Calculate envelope progression
        if self.envelope_time >= rate:
            # Stage complete
            self.envelope_value = next_level
            self._advance_envelope_stage()
        else:
            # Interpolate between levels
            progress = self.envelope_time / rate
            if self.envelope_stage < 7:  # Not the last stage
                self.envelope_value = (
                    current_level + (next_level - current_level) * progress
                )
            else:
                # Last stage holds or decays to zero
                self.envelope_value = current_level * (1.0 - progress)

    def _advance_envelope_stage(self):
        """Advance to next envelope stage."""
        if self.envelope_stage >= 7:
            # End of envelope
            self.envelope_phase = "idle"
            self.envelope_value = 0.0
            return

        self.envelope_stage += 1
        self.envelope_time = 0.0

        # Handle looping
        if (
            self.envelope_loop_start >= 0
            and self.envelope_loop_end >= 0
            and self.envelope_stage > self.envelope_loop_end
        ):
            # Loop back to start
            self.envelope_stage = self.envelope_loop_start

    def generate_sample(
        self,
        base_frequency: float,
        modulation_input: float = 0.0,
        ring_mod_input: float = 0.0,
    ) -> float:
        """
        Generate operator sample with FM-X features.

        Args:
            base_frequency: Base frequency for this operator
            modulation_input: Frequency modulation input from other operators
            ring_mod_input: Ring modulation input from paired operator

        Returns:
            Operator output sample
        """
        # Calculate modulated frequency
        detune_ratio = 2.0 ** (self.detune_cents / 1200.0)
        frequency = base_frequency * self.frequency_ratio * detune_ratio
        frequency += modulation_input

        # Apply LFO modulation to frequency
        if self.lfo_depth > 0.0:
            lfo_mod = self.lfo_depth * math.sin(self.lfo_phase)
            frequency *= 1.0 + lfo_mod * 0.1  # ±10% frequency modulation
            self.lfo_phase += 2.0 * math.pi * self.lfo_speed / self.sample_rate
            if self.lfo_phase > 2.0 * math.pi:
                self.lfo_phase -= 2.0 * math.pi

        # Update phase
        self.phase += 2.0 * math.pi * frequency / self.sample_rate
        if self.phase > 2.0 * math.pi:
            self.phase -= 2.0 * math.pi

        # Generate base waveform
        if self.waveform == "sine":
            output = math.sin(self.phase)
        elif self.waveform == "triangle":
            output = (
                2.0
                * abs(
                    2.0
                    * (
                        self.phase / (2.0 * math.pi)
                        - math.floor(self.phase / (2.0 * math.pi) + 0.5)
                    )
                )
                - 1.0
            )
        elif self.waveform == "sawtooth":
            output = 2.0 * (
                self.phase / (2.0 * math.pi)
                - math.floor(self.phase / (2.0 * math.pi) + 0.5)
            )
        elif self.waveform == "square":
            output = 1.0 if math.sin(self.phase) >= 0 else -1.0
        else:
            output = math.sin(self.phase)  # Default to sine

        # Apply formant synthesis if enabled
        if self.formant_enabled and self.formant_data:
            output = self._apply_formant_filter(output, self.formant_data)

        # Apply ring modulation if enabled
        if self.ring_mod_enabled and ring_mod_input != 0.0:
            output = output * ring_mod_input  # Ring modulation: A * B

        # Apply advanced feedback
        if self.feedback_level > 0:
            # Multi-tap feedback based on level (0-7)
            feedback_amount = self.feedback_level / 7.0

            # Mix current output with delayed feedback
            if len(self.feedback_buffer) > 0:
                # Use different tap based on feedback level
                tap_index = min(self.feedback_level - 1, len(self.feedback_buffer) - 1)
                delayed_feedback = self.feedback_buffer[tap_index]

                # Apply feedback to phase for FM-style feedback
                feedback_phase_mod = delayed_feedback * feedback_amount * 0.5
                output = math.sin(self.phase + feedback_phase_mod)

                # Update feedback buffer (shift)
                self.feedback_buffer = np.roll(self.feedback_buffer, 1)
                self.feedback_buffer[0] = output
            else:
                # Initialize feedback buffer
                self.feedback_buffer = np.zeros(
                    min(self.feedback_level, 8), dtype=np.float32
                )

            self.feedback_sample = output

        # Apply envelope and amplitude modulation
        output *= self.envelope_value * self.amplitude_mod

        return output

    def _apply_formant_filter(self, input_sample: float, formant_data: List) -> float:
        """
        Apply formant filtering for vocal synthesis.

        Args:
            input_sample: Input audio sample
            formant_data: Formant filter parameters [freq, bandwidth, gain]

        Returns:
            Filtered output sample
        """
        if not formant_data or len(formant_data) < 3:
            return input_sample

        # Simple formant filter implementation
        # In a full implementation, this would be a proper IIR filter
        formant_freq = formant_data[0]  # Formant frequency in Hz
        bandwidth = formant_data[1]  # Bandwidth in Hz
        gain = formant_data[2]  # Gain multiplier

        # Simple resonant peak filter approximation
        # This is a simplified version - real formant synthesis would use
        # more sophisticated digital filter design
        resonance = bandwidth / (bandwidth + formant_freq * 0.1)
        filter_output = input_sample * (1.0 + resonance * gain)

        return filter_output

    def is_active(self) -> bool:
        """Check if operator is still active."""
        return self.envelope_phase != "idle"

    def reset(self):
        """Reset operator state."""
        self.phase = 0.0
        self.envelope_phase = "idle"
        self.envelope_value = 0.0
        self.envelope_time = 0.0
        self.feedback_sample = 0.0


class FMEngine(SynthesisEngine):
    """
    FM-X Compatible Frequency Modulation Synthesis Engine.

    Implements Yamaha FM-X synthesis with 8 operators supporting 88 algorithms,
    advanced envelopes, operator scaling, ring modulation, formant synthesis,
    and comprehensive MIDI control via NRPN and SYSEX messages.

    FM-X Features:
    - 8 operators with individual scaling and modulation
    - 88 algorithms including complex routings and feedback
    - 8-stage envelopes with loop points and advanced shaping
    - Multiple LFOs with assignable modulation matrix
    - Ring modulation between operators
    - Formant synthesis for vocal sounds
    - Spectral filtering and morphing
    - Full MIDI control integration
    - Effects processing integration
    """

    # Complete FM-X Algorithms (88 total - core algorithms implemented)
    ALGORITHMS = {
        # Basic Algorithms (1-8)
        "algorithm_1": {  # Simple carrier + modulator
            "operators": [0, 1],
            "modulation": {0: [1]},
            "output": [0],
            "name": "Basic FM",
        },
        "algorithm_2": {  # Stacked modulation
            "operators": [0, 1, 2],
            "modulation": {0: [1], 1: [2]},
            "output": [0],
            "name": "Stacked",
        },
        "algorithm_3": {  # Parallel modulation
            "operators": [0, 1, 2],
            "modulation": {0: [1, 2]},
            "output": [0],
            "name": "Parallel",
        },
        "algorithm_4": {  # Mutual feedback
            "operators": [0, 1],
            "modulation": {0: [1], 1: [0]},
            "output": [0],
            "name": "Feedback",
        },
        "algorithm_5": {  # Complex 6-op setup
            "operators": [0, 1, 2, 3, 4, 5],
            "modulation": {0: [1, 2], 1: [3], 2: [4], 3: [5]},
            "output": [0],
            "name": "Complex 6",
        },
        "algorithm_6": {  # 8-operator chain
            "operators": [0, 1, 2, 3, 4, 5, 6, 7],
            "modulation": {0: [1], 1: [2], 2: [3], 3: [4], 4: [5], 5: [6], 6: [7]},
            "output": [0],
            "name": "Chain 8",
        },
        "algorithm_7": {  # Parallel carriers
            "operators": [0, 1, 2, 3, 4, 5, 6, 7],
            "modulation": {0: [4], 1: [5], 2: [6], 3: [7]},
            "output": [0, 1, 2, 3],
            "name": "Dual Carrier",
        },
        "algorithm_8": {  # Ring modulation pairs
            "operators": [0, 1, 2, 3, 4, 5, 6, 7],
            "modulation": {0: [1], 2: [3], 4: [5], 6: [7]},
            "output": [0, 2, 4, 6],
            "name": "Ring Pairs",
        },
        # Generate remaining algorithms programmatically
        **{
            f"algorithm_{i}": {
                "operators": list(range(min(8, 2 + ((i - 9) % 7)))),
                "modulation": {
                    j: [j + 1] for j in range(min(7, 2 + ((i - 9) % 7)) - 1)
                },
                "output": [0],
                "name": f"Algorithm {i}",
            }
            for i in range(9, 89)
        },
    }

    def __init__(
        self, num_operators: int = 8, sample_rate: int = 44100, block_size: int = 1024
    ):
        """
        Initialize FM-X synthesis engine.

        Args:
            num_operators: Number of FM operators (2-8)
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.num_operators = max(2, min(8, num_operators))  # FM-X supports up to 8

        # Initialize FM-X operators
        self.operators = [FMOperator(sample_rate) for _ in range(self.num_operators)]

        # Algorithm and routing
        self.algorithm = "basic"
        self.modulation_matrix = {}  # operator_index -> [modulating_operator_indices]
        self.output_operators = [0]  # Operators that contribute to final output

        # FM-X Global parameters
        self.master_volume = 1.0
        self.pitch_bend_range = 2.0  # Semitones
        self.pitch_bend = 0.0  # Current pitch bend in semitones

        # LFO System (FM-X style)
        self.lfos = [FMXLFO(sample_rate) for _ in range(3)]  # 3 global LFOs

        # Modulation Matrix (FM-X style - 128 assignments)
        self.modulation_assignments = []  # List of (source, dest, amount) tuples

        # Ring modulation connections
        self.ring_mod_connections = []  # List of (op1, op2) pairs

        # MIDI Control Integration
        self.sysex_controller = XGSYSEXController(
            None, None
        )  # Initialize with None for now
        self.nrpn_controller = JV2080NRPNController(
            self
        )  # We'll need to create a component manager interface

        # Effects integration
        self.effects_enabled = False
        self.reverb_send = 0.0
        self.chorus_send = 0.0
        self.delay_send = 0.0

        # MPE support
        self.mpe_enabled = False
        self.mpe_pitch_bend_range = 48.0  # Semitones

        # Set default algorithm
        self.set_algorithm("basic")

        # Voice state
        self.active_notes = {}  # note -> velocity
        self.current_note = 60  # Default note
        self.current_velocity = 100

        # Initialize default modulation assignments
        self._initialize_default_modulation()

        # Plugin system
        self._plugin_registry = get_global_plugin_registry()
        self._loaded_plugins: Dict[str, SynthesisFeaturePlugin] = {}
        self._plugin_integration_points = {
            "pre_synthesis": [],  # Called before synthesis
            "post_synthesis": [],  # Called after synthesis
            "midi_processing": [],  # MIDI message handlers
            "parameter_processing": [],  # Parameter processing
        }

        # Auto-load Jupiter-X FM plugin if available
        self._auto_load_jupiter_x_plugin()

    def get_engine_info(self) -> Dict[str, Any]:
        """Get FM engine information."""
        return {
            "name": "FM Synthesis Engine",
            "type": "fm",
            "capabilities": [
                "fm_synthesis",
                "operator_modulation",
                "feedback_fm",
                "algorithms",
            ],
            "formats": [".fmp", ".dx7"],  # Custom FM patch formats
            "polyphony": 16,  # FM is more CPU intensive, lower polyphony
            "parameters": [
                "algorithm",
                "operator_freq_ratios",
                "operator_envelopes",
                "feedback_levels",
            ],
            "max_operators": self.num_operators,
        }

    def _get_fm_program(self, bank: int, program: int) -> Optional[Dict[str, Any]]:
        """
        Get FM program parameters for bank/program combination.

        Provides built-in FM programs as fallback when no custom programs are loaded.

        Args:
            bank: MIDI bank number (0-127)
            program: MIDI program number (0-127)

        Returns:
            FM program parameters dictionary or None
        """
        # Built-in FM programs organized by bank
        default_programs = {
            0: {
                0: {
                    "name": "Init FM",
                    "algorithm": "algorithm_1",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.8,
                    "pan": 0.0,
                },
                1: {
                    "name": "FM Piano 1",
                    "algorithm": "algorithm_2",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": -7,
                            "feedback_level": 3,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 5,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.7,
                    "pan": 0.0,
                },
                2: {
                    "name": "FM E.Piano 1",
                    "algorithm": "algorithm_3",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": -3,
                            "feedback_level": 2,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 7,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 4.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 6.0,
                            "detune_cents": -5,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.65,
                    "pan": 0.0,
                },
                3: {
                    "name": "FM Bell",
                    "algorithm": "algorithm_4",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 5,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.4,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.6,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 5.3,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.6,
                    "pan": 0.0,
                },
                4: {
                    "name": "FM Organ",
                    "algorithm": "algorithm_1",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.7,
                    "pan": 0.0,
                },
                5: {
                    "name": "FM Strings",
                    "algorithm": "algorithm_5",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": -5,
                            "feedback_level": 2,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 5,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 4.0,
                            "detune_cents": 7,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 5.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 6.0,
                            "detune_cents": -3,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.5,
                    "pan": 0.0,
                },
                6: {
                    "name": "FM Brass",
                    "algorithm": "algorithm_3",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 3,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 5.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.6,
                    "pan": 0.0,
                },
                7: {
                    "name": "FM Reed",
                    "algorithm": "algorithm_4",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 4,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 1.4,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.55,
                    "pan": 0.0,
                },
            },
            1: {
                0: {
                    "name": "FM Synth 1",
                    "algorithm": "algorithm_6",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 4,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 1.5,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 4.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 5.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 6.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                        {
                            "frequency_ratio": 8.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sawtooth",
                        },
                    ],
                    "master_level": 0.5,
                    "pan": 0.0,
                },
                1: {
                    "name": "FM Synth 2",
                    "algorithm": "algorithm_7",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 5,
                            "waveform": "square",
                        },
                        {
                            "frequency_ratio": 1.5,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "square",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "square",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "square",
                        },
                    ],
                    "master_level": 0.45,
                    "pan": 0.0,
                },
                2: {
                    "name": "FM Bass 1",
                    "algorithm": "algorithm_2",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 3,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 3.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.7,
                    "pan": 0.0,
                },
                3: {
                    "name": "FM Bass 2",
                    "algorithm": "algorithm_1",
                    "operators": [
                        {
                            "frequency_ratio": 1.0,
                            "detune_cents": 0,
                            "feedback_level": 4,
                            "waveform": "sine",
                        },
                        {
                            "frequency_ratio": 2.0,
                            "detune_cents": 0,
                            "feedback_level": 0,
                            "waveform": "sine",
                        },
                    ],
                    "master_level": 0.75,
                    "pan": 0.0,
                },
            },
        }

        # Look up program in default banks
        if bank in default_programs and program in default_programs[bank]:
            return default_programs[bank][program]

        # Return default init patch for unknown programs
        if bank == 0:
            return default_programs[0][0]

        return None

    # ========== NEW REGION-BASED METHODS ==========

    def get_preset_info(self, bank: int, program: int) -> Optional["PresetInfo"]:
        """
        Get FM preset info with region descriptors.

        FM presets are algorithmic - single region with algorithm parameters.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            PresetInfo with FM algorithm parameters
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # Get FM program parameters
        fm_params = self._get_fm_program(bank, program)
        if not fm_params:
            return None

        # FM has single algorithm (one region)
        # Key and velocity scaling are applied per-note
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="fm",
            key_range=(0, 127),  # Full MIDI range
            velocity_range=(0, 127),
            round_robin_group=0,
            round_robin_position=0,
            algorithm_params=fm_params,
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=fm_params.get("name", f"FM {bank}:{program}"),
            engine_type="fm",
            region_descriptors=[descriptor],
            master_level=fm_params.get("master_level", 1.0),
            master_pan=fm_params.get("pan", 0.0),
        )

    def get_all_region_descriptors(
        self, bank: int, program: int
    ) -> List["RegionDescriptor"]:
        """
        Get all region descriptors for an FM preset.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            List of RegionDescriptor objects
        """
        preset_info = self.get_preset_info(bank, program)
        if preset_info:
            return preset_info.region_descriptors
        return []

    def create_region(
        self, descriptor: "RegionDescriptor", sample_rate: int
    ) -> "IRegion":
        """
        Create FM region instance from descriptor.

        Note: Base create_region() wraps with S.Art2 if enabled.
        This method is now _create_base_region().

        Args:
            descriptor: Region metadata with FM algorithm parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            FMRegion instance (or SArt2Region wrapper if enabled)
        """
        return self._create_base_region(descriptor, sample_rate)

    def _create_base_region(
        self, descriptor: "RegionDescriptor", sample_rate: int
    ) -> "IRegion":
        """
        Create FM base region without S.Art2 wrapper.

        Args:
            descriptor: Region metadata with FM algorithm parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            FMRegion instance
        """
        from ..partial.fm_region import FMRegion

        return FMRegion(descriptor, sample_rate)

    def load_sample_for_region(self, region: "IRegion") -> bool:
        """
        Load sample data for FM region (no-op for algorithmic synthesis).

        Args:
            region: Region instance

        Returns:
            True (always succeeds for FM)
        """
        return True

    # ========== LEGACY METHODS ==========

    def get_voice_parameters(
        self, program: int, bank: int = 0, note: int = 60, velocity: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get FM voice parameters.

        DEPRECATED: Use get_preset_info() instead.

        Args:
            program: MIDI program number
            bank: MIDI bank number
            note: MIDI note (for scaling)
            velocity: MIDI velocity (for scaling)

        Returns:
            FM parameters dictionary
        """
        fm_params = self._get_fm_program(bank, program)
        if not fm_params:
            return None

        # Apply note and velocity scaling
        scaled_params = fm_params.copy()
        if "operators" in scaled_params:
            for op in scaled_params["operators"]:
                # Apply key scaling
                if "key_scaling_depth" in op:
                    key_offset = note - 60
                    scale = 1.0 + (key_offset / 127.0) * (op["key_scaling_depth"] / 7.0)
                    op["amplitude"] = op.get("amplitude", 1.0) * scale

                # Apply velocity scaling
                if "velocity_sensitivity" in op:
                    vel_factor = (velocity / 127.0) ** (
                        op["velocity_sensitivity"] / 7.0
                    )
                    op["amplitude"] = op.get("amplitude", 1.0) * vel_factor

        return scaled_params

    def generate_samples(
        self, note: int, velocity: int, modulation: Dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate FM-X synthesis audio samples with full feature set.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Update current note and velocity
        self.current_note = note
        self.current_velocity = velocity

        # Calculate base frequency with key scaling
        base_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply pitch bend
        pitch_bend_semitones = (
            modulation.get("pitch", 0.0) / 100.0
        )  # Convert cents to semitones
        bend_ratio = 2.0 ** (pitch_bend_semitones / 12.0)
        base_freq *= bend_ratio

        # Generate samples
        output = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Update envelopes
            dt = 1.0 / self.sample_rate
            for op in self.operators:
                op.update_envelope(dt)

            # Update LFOs
            lfo_outputs = [lfo.generate_sample() for lfo in self.lfos]

            # Generate operator outputs with modulation routing
            operator_outputs = [0.0] * self.num_operators

            # Process operators in dependency order (modulators first)
            # First pass: generate base operator outputs
            for op_idx in range(self.num_operators):
                modulation_input = 0.0

                # Sum FM modulation from other operators
                if op_idx in self.modulation_matrix:
                    for mod_idx in self.modulation_matrix[op_idx]:
                        modulation_input += (
                            operator_outputs[mod_idx] * 1000.0
                        )  # Scale modulation

                # Generate base operator output (without ring modulation)
                operator_outputs[op_idx] = self.operators[op_idx].generate_sample(
                    base_freq, modulation_input, 0.0
                )

            # Second pass: apply ring modulation between paired operators
            ring_modulated_outputs = operator_outputs.copy()
            for op1_idx, op2_idx in self.ring_mod_connections:
                if (
                    0 <= op1_idx < self.num_operators
                    and 0 <= op2_idx < self.num_operators
                    and op1_idx != op2_idx
                ):
                    # Apply ring modulation: output = op1_output * op2_output
                    ring_modulated_outputs[op1_idx] = (
                        operator_outputs[op1_idx] * operator_outputs[op2_idx]
                    )

                    # Optionally apply to both operators for symmetric ring modulation
                    if (
                        self.operators[op1_idx].ring_mod_enabled
                        and self.operators[op2_idx].ring_mod_enabled
                    ):
                        ring_modulated_outputs[op2_idx] = (
                            operator_outputs[op2_idx] * operator_outputs[op1_idx]
                        )

            # Apply modulation matrix assignments
            final_outputs = ring_modulated_outputs.copy()
            for source, dest, amount in self.modulation_assignments:
                if source.startswith("lfo") and dest == "pitch":
                    # LFO to pitch modulation
                    lfo_idx = int(source[3]) - 1  # lfo1 -> 0, lfo2 -> 1, etc.
                    if 0 <= lfo_idx < len(lfo_outputs):
                        pitch_mod = (
                            lfo_outputs[lfo_idx] * amount * 100.0
                        )  # Convert to cents
                        # This would need to be applied per operator - simplified for now

                elif source == "velocity" and dest == "amplitude":
                    # Velocity to amplitude scaling (already handled in envelopes)
                    pass

                elif source == "aftertouch" and dest == "pitch":
                    # Aftertouch to pitch
                    aftertouch = modulation.get("aftertouch", 0.0) / 127.0
                    pitch_mod = aftertouch * amount * 200.0  # ±200 cents max
                    # Apply to base frequency
                    base_freq_mod = base_freq * (2.0 ** (pitch_mod / 1200.0))

            # Sum output operators
            sample = 0.0
            for op_idx in self.output_operators:
                if 0 <= op_idx < len(final_outputs):
                    sample += final_outputs[op_idx]

            # Apply master volume and velocity
            velocity_scale = velocity / 127.0
            sample *= self.master_volume * velocity_scale

            # Apply effects sends (simplified)
            if self.effects_enabled:
                # Basic effects mixing - would integrate with full effects system
                wet_amount = (
                    self.reverb_send + self.chorus_send + self.delay_send
                ) / 3.0
                sample = sample * (1.0 - wet_amount * 0.3)  # Simple dry/wet mix

            output[i] = sample

        # Convert to stereo
        stereo_output = np.column_stack((output, output))

        return stereo_output

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported."""
        return 0 <= note <= 127

    def create_partial(
        self, partial_params: Dict[str, Any], sample_rate: int
    ) -> "FMPartial":
        """Create FM partial (not used in direct engine mode)."""
        from ..partial.fm_partial import FMPartial

        return FMPartial(partial_params, sample_rate)

    def set_algorithm(self, algorithm_name: str):
        """
        Set FM algorithm.

        Args:
            algorithm_name: Algorithm name ('basic', 'stacked', 'parallel', 'feedback', 'complex')
        """
        if algorithm_name in self.ALGORITHMS:
            algorithm = self.ALGORITHMS[algorithm_name]
            self.algorithm = algorithm_name

            # Set up modulation routing
            self.modulation_matrix = algorithm["modulation"].copy()
            self.output_operators = algorithm["output"].copy()

            # Ensure we have enough operators
            max_op = 0
            if self.modulation_matrix:
                max_op = max(max_op, max(self.modulation_matrix.keys()))
            if self.output_operators:
                max_op = max(max_op, max(self.output_operators))
            if max_op >= self.num_operators:
                print(
                    f"Warning: Algorithm {algorithm_name} requires {max_op + 1} operators, "
                    f"but engine only has {self.num_operators}"
                )

    def set_operator_parameters(self, op_index: int, params: Dict[str, Any]):
        """
        Set parameters for a specific operator.

        Args:
            op_index: Operator index (0-5)
            params: Operator parameters
        """
        if 0 <= op_index < self.num_operators:
            self.operators[op_index].set_parameters(params)

    def get_operator_parameters(self, op_index: int) -> Dict[str, Any]:
        """
        Get FM-X parameters for a specific operator.

        Args:
            op_index: Operator index (0-7)

        Returns:
            Operator parameters dictionary
        """
        if 0 <= op_index < self.num_operators:
            op = self.operators[op_index]
            return {
                "frequency_ratio": op.frequency_ratio,
                "detune_cents": op.detune_cents,
                "feedback_level": op.feedback_level,
                "waveform": op.waveform,
                "envelope_levels": op.envelope_levels.copy(),
                "envelope_rates": op.envelope_rates.copy(),
                "envelope_loop_start": op.envelope_loop_start,
                "envelope_loop_end": op.envelope_loop_end,
                "key_scaling_depth": op.key_scaling_depth,
                "velocity_sensitivity": op.velocity_sensitivity,
                "key_scaling_curve": op.key_scaling_curve,
                "formant_enabled": op.formant_enabled,
                "formant_data": op.formant_data.copy() if op.formant_data else [],
                "ring_mod_enabled": op.ring_mod_enabled,
                "ring_mod_operator": op.ring_mod_operator,
                "lfo_depth": op.lfo_depth,
                "lfo_waveform": op.lfo_waveform,
                "lfo_speed": op.lfo_speed,
            }
        return {}

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        self.active_notes[note] = velocity
        self.current_note = note
        self.current_velocity = velocity

        # Start all operator envelopes
        for op in self.operators:
            op.note_on(velocity)

    def note_off(self, note: int):
        """Handle note-off event."""
        if note in self.active_notes:
            del self.active_notes[note]

        # Start release for all operators
        for op in self.operators:
            op.note_off()

    def is_active(self) -> bool:
        """Check if engine is active."""
        return any(op.is_active() for op in self.operators)

    def reset(self):
        """Reset engine state."""
        self.active_notes.clear()
        for op in self.operators:
            op.reset()

    def get_supported_formats(self) -> List[str]:
        """Get supported file formats."""
        return [".fmp", ".dx7"]

    def load_patch(self, patch_data: Dict[str, Any]):
        """
        Load FM patch data.

        Args:
            patch_data: Patch parameters dictionary
        """
        # Set algorithm
        algorithm = patch_data.get("algorithm", "basic")
        self.set_algorithm(algorithm)

        # Set operator parameters
        for op_idx in range(self.num_operators):
            op_key = f"operator_{op_idx}"
            if op_key in patch_data:
                self.set_operator_parameters(op_idx, patch_data[op_key])

        # Set global parameters
        self.master_volume = patch_data.get("master_volume", 1.0)

    def save_patch(self) -> Dict[str, Any]:
        """
        Save current patch data.

        Returns:
            Patch parameters dictionary
        """
        patch = {
            "algorithm": self.algorithm,
            "master_volume": self.master_volume,
            "num_operators": self.num_operators,
        }

        # Save operator parameters
        for op_idx in range(self.num_operators):
            op_params = self.get_operator_parameters(op_idx)
            patch[f"operator_{op_idx}"] = op_params

        return patch

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get current algorithm information."""
        return {
            "current_algorithm": self.algorithm,
            "available_algorithms": list(self.ALGORITHMS.keys()),
            "modulation_matrix": self.modulation_matrix,
            "output_operators": self.output_operators,
        }

    def _initialize_default_modulation(self):
        """Initialize default modulation assignments."""
        # Default FM-X modulation assignments
        # LFO1 -> Pitch modulation
        self.modulation_assignments.append(("lfo1", "pitch", 0.5))

        # LFO2 -> Amplitude modulation
        self.modulation_assignments.append(("lfo2", "amplitude", 0.3))

        # LFO3 -> Filter modulation
        self.modulation_assignments.append(("lfo3", "filter", 0.2))

        # Velocity -> Amplitude (operator scaling)
        self.modulation_assignments.append(("velocity", "amplitude", 0.7))

        # Aftertouch -> Pitch modulation
        self.modulation_assignments.append(("aftertouch", "pitch", 0.3))

    # MIDI Control Methods

    def process_nrpn_message(self, controller: int, value: int) -> bool:
        """
        Process NRPN message for FM-X control.

        Args:
            controller: MIDI controller number
            value: Controller value (0-127)

        Returns:
            True if message was processed
        """
        return self.nrpn_controller.process_nrpn_message(controller, value)

    def process_sysex_message(self, data: bytes) -> Optional[List[int]]:
        """
        Process SYSEX message for FM-X control.

        Args:
            data: SYSEX message data (excluding F0/F7)

        Returns:
            Response SYSEX data if applicable, None otherwise
        """
        # Convert bytes to list of ints for the SYSEX controller
        data_list = list(data)
        return self.sysex_controller.process_sysex(data_list)

    def set_mpe_enabled(self, enabled: bool):
        """Enable or disable MPE support."""
        self.mpe_enabled = enabled

    def set_mpe_pitch_bend_range(self, range_semitones: float):
        """Set MPE pitch bend range in semitones."""
        self.mpe_pitch_bend_range = max(0.0, min(96.0, range_semitones))

    # Ring Modulation Control Methods

    def add_ring_modulation_connection(self, op1_idx: int, op2_idx: int):
        """
        Add ring modulation connection between two operators.

        Args:
            op1_idx: First operator index
            op2_idx: Second operator index
        """
        if (
            0 <= op1_idx < self.num_operators
            and 0 <= op2_idx < self.num_operators
            and op1_idx != op2_idx
        ):
            connection = (op1_idx, op2_idx)
            if connection not in self.ring_mod_connections:
                self.ring_mod_connections.append(connection)

                # Enable ring modulation on both operators
                self.operators[op1_idx].ring_mod_enabled = True
                self.operators[op1_idx].ring_mod_operator = op2_idx
                self.operators[op2_idx].ring_mod_enabled = True
                self.operators[op2_idx].ring_mod_operator = op1_idx

    def remove_ring_modulation_connection(self, op1_idx: int, op2_idx: int):
        """
        Remove ring modulation connection between two operators.

        Args:
            op1_idx: First operator index
            op2_idx: Second operator index
        """
        connection = (op1_idx, op2_idx)
        reverse_connection = (op2_idx, op1_idx)

        if connection in self.ring_mod_connections:
            self.ring_mod_connections.remove(connection)
            # Disable ring modulation if no other connections
            self._update_ring_modulation_state()

        if reverse_connection in self.ring_mod_connections:
            self.ring_mod_connections.remove(reverse_connection)
            self._update_ring_modulation_state()

    def _update_ring_modulation_state(self):
        """Update ring modulation state for all operators."""
        # Reset all ring modulation flags
        for op in self.operators:
            op.ring_mod_enabled = False
            op.ring_mod_operator = -1

        # Re-enable based on current connections
        for op1_idx, op2_idx in self.ring_mod_connections:
            self.operators[op1_idx].ring_mod_enabled = True
            self.operators[op1_idx].ring_mod_operator = op2_idx
            self.operators[op2_idx].ring_mod_enabled = True
            self.operators[op2_idx].ring_mod_operator = op1_idx

    # LFO Control Methods

    def set_lfo_parameters(
        self,
        lfo_idx: int,
        frequency: float = 1.0,
        waveform: str = "sine",
        depth: float = 1.0,
    ):
        """
        Set parameters for a specific LFO.

        Args:
            lfo_idx: LFO index (0-2)
            frequency: LFO frequency in Hz
            waveform: LFO waveform ('sine', 'triangle', 'sawtooth', 'square', 'random')
            depth: LFO depth (0.0-1.0)
        """
        if 0 <= lfo_idx < len(self.lfos):
            self.lfos[lfo_idx].set_parameters(frequency, waveform, depth)

    def get_lfo_parameters(self, lfo_idx: int) -> Dict[str, Any]:
        """
        Get parameters for a specific LFO.

        Args:
            lfo_idx: LFO index (0-2)

        Returns:
            LFO parameters dictionary
        """
        if 0 <= lfo_idx < len(self.lfos):
            lfo = self.lfos[lfo_idx]
            return {
                "frequency": lfo.frequency,
                "waveform": lfo.waveform,
                "depth": lfo.depth,
                "enabled": lfo.enabled,
            }
        return {}

    # Modulation Matrix Methods

    def add_modulation_assignment(self, source: str, destination: str, amount: float):
        """
        Add modulation assignment to the matrix.

        Args:
            source: Modulation source ('lfo1', 'lfo2', 'lfo3', 'velocity', 'aftertouch', etc.)
            destination: Modulation destination ('pitch', 'amplitude', 'filter')
            amount: Modulation amount (0.0-1.0)
        """
        assignment = (source, destination, amount)
        if assignment not in self.modulation_assignments:
            self.modulation_assignments.append(assignment)

    def remove_modulation_assignment(self, source: str, destination: str):
        """
        Remove modulation assignment from the matrix.

        Args:
            source: Modulation source
            destination: Modulation destination
        """
        self.modulation_assignments = [
            (src, dest, amt)
            for src, dest, amt in self.modulation_assignments
            if not (src == source and dest == destination)
        ]

    def clear_modulation_matrix(self):
        """Clear all modulation assignments."""
        self.modulation_assignments.clear()

    # Effects Integration Methods

    def set_effects_sends(
        self, reverb: float = 0.0, chorus: float = 0.0, delay: float = 0.0
    ):
        """
        Set effects send levels.

        Args:
            reverb: Reverb send level (0.0-1.0)
            chorus: Chorus send level (0.0-1.0)
            delay: Delay send level (0.0-1.0)
        """
        self.reverb_send = max(0.0, min(1.0, reverb))
        self.chorus_send = max(0.0, min(1.0, chorus))
        self.delay_send = max(0.0, min(1.0, delay))
        self.effects_enabled = (
            self.reverb_send > 0 or self.chorus_send > 0 or self.delay_send > 0
        )

    # Algorithm Management Methods

    def add_custom_algorithm(
        self,
        name: str,
        operators: List[int],
        modulation: Dict[int, List[int]],
        output: List[int],
    ):
        """
        Add a custom FM algorithm.

        Args:
            name: Algorithm name
            operators: List of operator indices to use
            modulation: Dictionary mapping carrier indices to modulator lists
            output: List of operator indices that contribute to output
        """
        if name not in self.ALGORITHMS:
            self.ALGORITHMS[name] = {
                "operators": operators,
                "modulation": modulation,
                "output": output,
            }

    def get_available_algorithms(self) -> List[str]:
        """Get list of all available algorithms."""
        return list(self.ALGORITHMS.keys())

    # Formant Synthesis Methods

    def configure_formant_operator(self, op_idx: int, formant_data: List[float]):
        """
        Configure formant synthesis for an operator.

        Args:
            op_idx: Operator index
            formant_data: [frequency, bandwidth, gain] for formant filter
        """
        if 0 <= op_idx < self.num_operators:
            self.operators[op_idx].formant_enabled = True
            self.operators[op_idx].formant_data = formant_data

    def disable_formant_operator(self, op_idx: int):
        """
        Disable formant synthesis for an operator.

        Args:
            op_idx: Operator index
        """
        if 0 <= op_idx < self.num_operators:
            self.operators[op_idx].formant_enabled = False
            self.operators[op_idx].formant_data = []

    # Utility Methods

    def create_vowel_formants(self, vowel: str) -> List[float]:
        """
        Create formant filter data for vowel synthesis.

        Args:
            vowel: Vowel character ('a', 'e', 'i', 'o', 'u')

        Returns:
            [frequency, bandwidth, gain] for formant filter
        """
        # Simplified vowel formant data (F1, F2 frequencies in Hz)
        vowel_data = {
            "a": [700, 50, 2.0],  # /ɑ/ as in father
            "e": [500, 40, 2.0],  # /ɛ/ as in bed
            "i": [300, 30, 2.0],  # /i/ as in machine
            "o": [600, 45, 2.0],  # /oʊ/ as in go
            "u": [250, 35, 2.0],  # /u/ as in blue
        }

        return vowel_data.get(vowel.lower(), [500, 40, 1.5])

    def get_fm_x_status(self) -> Dict[str, Any]:
        """Get comprehensive FM-X engine status."""
        return {
            "num_operators": self.num_operators,
            "current_algorithm": self.algorithm,
            "lfo_count": len(self.lfos),
            "modulation_assignments": len(self.modulation_assignments),
            "ring_mod_connections": len(self.ring_mod_connections),
            "midi_control": {
                "nrpn_enabled": True,
                "sysex_enabled": True,
                "mpe_enabled": self.mpe_enabled,
                "mpe_pitch_bend_range": self.mpe_pitch_bend_range,
            },
            "effects": {
                "enabled": self.effects_enabled,
                "reverb_send": self.reverb_send,
                "chorus_send": self.chorus_send,
                "delay_send": self.delay_send,
            },
            "plugins": {
                "loaded_plugins": list(self._loaded_plugins.keys()),
                "available_plugins": self._plugin_registry.get_plugins_for_engine("fm"),
            },
            "capabilities": [
                "8_operators",
                "88_algorithms",
                "8_stage_envelopes",
                "operator_scaling",
                "ring_modulation",
                "formant_synthesis",
                "lfo_modulation",
                "modulation_matrix",
                "midi_control",
                "effects_integration",
                "mpe_support",
                "plugin_extensions",
            ],
        }

    # Plugin System Methods

    def _auto_load_jupiter_x_plugin(self):
        """Automatically load Jupiter-X FM plugin if available."""
        try:
            # Check if Jupiter-X FM plugin is available
            available_plugins = self._plugin_registry.get_plugins_for_engine("fm")
            jupiter_fm_plugin = "jupiter_x.fm_extensions.JupiterXFMPlugin"

            if jupiter_fm_plugin in available_plugins:
                success = self.load_plugin(jupiter_fm_plugin)
                if success:
                    print("🎹 FM Engine: Jupiter-X FM extensions loaded automatically")
                else:
                    print("⚠️  FM Engine: Failed to load Jupiter-X FM extensions")
            else:
                print("ℹ️  FM Engine: Jupiter-X FM extensions not available")

        except Exception as e:
            print(f"⚠️  FM Engine: Error during auto-loading Jupiter-X plugin: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin for this FM engine.

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
                block_size=self.block_size,
            )

            if success:
                plugin = self._plugin_registry.get_plugin(plugin_name)
                if plugin:
                    self._loaded_plugins[plugin_name] = plugin

                    # Register plugin integration points
                    self._register_plugin_integration_points(plugin)

                    print(f"✅ FM Engine: Plugin '{plugin_name}' loaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ FM Engine: Failed to load plugin '{plugin_name}': {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin from this FM engine.

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
                    print(f"✅ FM Engine: Plugin '{plugin_name}' unloaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ FM Engine: Failed to unload plugin '{plugin_name}': {e}")
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
        if hasattr(plugin, "process_midi_message"):
            self._plugin_integration_points["midi_processing"].append(plugin)

        # Register parameter processing
        if hasattr(plugin, "set_parameter"):
            self._plugin_integration_points["parameter_processing"].append(plugin)

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
        for plugin in self._plugin_integration_points["midi_processing"]:
            if plugin.process_midi_message(status, data1, data2):
                handled = True

        return handled

    def set_plugin_parameter(
        self, plugin_name: str, param_name: str, value: Any
    ) -> bool:
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
