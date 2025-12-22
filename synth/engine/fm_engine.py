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


class FMOperator:
    """
    FM synthesis operator with envelope and modulation controls.

    Each operator has its own oscillator, envelope, and modulation parameters,
    supporting the building blocks of FM synthesis algorithms.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize FM operator."""
        self.sample_rate = sample_rate

        # Oscillator parameters
        self.frequency_ratio = 1.0
        self.detune_cents = 0.0
        self.feedback_level = 0.0
        self.waveform = 'sine'
        self.phase = 0.0

        # Envelope parameters (ADSR)
        self.attack_time = 0.01
        self.decay_time = 0.3
        self.sustain_level = 0.7
        self.release_time = 0.5
        self.envelope_phase = 'idle'

        # Envelope state
        self.envelope_value = 0.0
        self.envelope_time = 0.0
        self.envelope_attack_target = 1.0
        self.envelope_decay_target = 0.7
        self.envelope_release_target = 0.0

        # Modulation targets
        self.amplitude_mod = 1.0
        self.frequency_mod = 0.0

        # Feedback state
        self.feedback_sample = 0.0

    def set_parameters(self, params: Dict[str, Any]):
        """Set operator parameters."""
        self.frequency_ratio = params.get('frequency_ratio', 1.0)
        self.detune_cents = params.get('detune_cents', 0.0)
        self.feedback_level = params.get('feedback_level', 0.0)
        self.waveform = params.get('waveform', 'sine')

        # Envelope parameters
        self.attack_time = params.get('attack_time', 0.01)
        self.decay_time = params.get('decay_time', 0.3)
        self.sustain_level = params.get('sustain_level', 0.7)
        self.release_time = params.get('release_time', 0.5)

        # Update envelope targets
        self.envelope_decay_target = self.sustain_level

    def note_on(self, velocity: int = 127):
        """Start operator envelope."""
        self.envelope_phase = 'attack'
        self.envelope_time = 0.0
        self.envelope_value = 0.0

    def note_off(self):
        """Start operator release."""
        self.envelope_phase = 'release'
        self.envelope_time = 0.0
        self.envelope_release_target = 0.0

    def update_envelope(self, dt: float):
        """Update envelope state."""
        self.envelope_time += dt

        if self.envelope_phase == 'attack':
            if self.envelope_time >= self.attack_time:
                self.envelope_value = self.envelope_attack_target
                self.envelope_phase = 'decay'
                self.envelope_time = 0.0
            else:
                self.envelope_value = (self.envelope_time / self.attack_time) * self.envelope_attack_target

        elif self.envelope_phase == 'decay':
            if self.envelope_time >= self.decay_time:
                self.envelope_value = self.envelope_decay_target
                self.envelope_phase = 'sustain'
            else:
                decay_progress = self.envelope_time / self.decay_time
                self.envelope_value = self.envelope_attack_target - decay_progress * (self.envelope_attack_target - self.envelope_decay_target)

        elif self.envelope_phase == 'sustain':
            self.envelope_value = self.envelope_decay_target

        elif self.envelope_phase == 'release':
            if self.envelope_time >= self.release_time:
                self.envelope_value = self.envelope_release_target
                self.envelope_phase = 'idle'
            else:
                release_progress = self.envelope_time / self.release_time
                self.envelope_value = self.envelope_decay_target - release_progress * (self.envelope_decay_target - self.envelope_release_target)

        elif self.envelope_phase == 'idle':
            self.envelope_value = 0.0

    def generate_sample(self, base_frequency: float, modulation_input: float = 0.0) -> float:
        """
        Generate operator sample.

        Args:
            base_frequency: Base frequency for this operator
            modulation_input: Frequency modulation input from other operators

        Returns:
            Operator output sample
        """
        # Calculate modulated frequency
        detune_ratio = 2.0 ** (self.detune_cents / 1200.0)
        frequency = base_frequency * self.frequency_ratio * detune_ratio
        frequency += modulation_input

        # Update phase
        self.phase += 2.0 * math.pi * frequency / self.sample_rate
        if self.phase > 2.0 * math.pi:
            self.phase -= 2.0 * math.pi

        # Generate waveform
        if self.waveform == 'sine':
            output = math.sin(self.phase)
        elif self.waveform == 'triangle':
            output = 2.0 * abs(2.0 * (self.phase / (2.0 * math.pi) - math.floor(self.phase / (2.0 * math.pi) + 0.5))) - 1.0
        elif self.waveform == 'sawtooth':
            output = 2.0 * (self.phase / (2.0 * math.pi) - math.floor(self.phase / (2.0 * math.pi) + 0.5))
        elif self.waveform == 'square':
            output = 1.0 if math.sin(self.phase) >= 0 else -1.0
        else:
            output = math.sin(self.phase)  # Default to sine

        # Apply feedback
        if self.feedback_level > 0.0:
            output = math.sin(self.phase + self.feedback_sample * self.feedback_level)
            self.feedback_sample = output

        # Apply envelope and amplitude modulation
        output *= self.envelope_value * self.amplitude_mod

        return output

    def is_active(self) -> bool:
        """Check if operator is still active."""
        return self.envelope_phase != 'idle'

    def reset(self):
        """Reset operator state."""
        self.phase = 0.0
        self.envelope_phase = 'idle'
        self.envelope_value = 0.0
        self.envelope_time = 0.0
        self.feedback_sample = 0.0


class FMEngine(SynthesisEngine):
    """
    FM (Frequency Modulation) Synthesis Engine.

    Implements 2-6 operator FM synthesis with support for:
    - Basic FM algorithms (carrier + modulator)
    - Stacked FM (multiple modulation layers)
    - Feedback FM (operator self-modulation)
    - DX7-style parameter compatibility
    """

    # FM Algorithms (operator routing patterns)
    ALGORITHMS = {
        'basic': {  # Algorithm 1: Simple carrier + modulator
            'operators': [0, 1],  # Operator indices
            'modulation': {0: [1]},  # Operator 0 modulated by operator 1
            'output': [0]  # Operator 0 is the output
        },
        'stacked': {  # Algorithm 2: Two modulators, one carrier
            'operators': [0, 1, 2],
            'modulation': {0: [1], 1: [2]},  # 0 modulated by 1, 1 modulated by 2
            'output': [0]
        },
        'parallel': {  # Algorithm 3: Parallel modulation
            'operators': [0, 1, 2],
            'modulation': {0: [1, 2]},  # 0 modulated by both 1 and 2
            'output': [0]
        },
        'feedback': {  # Algorithm 4: Feedback modulation
            'operators': [0, 1],
            'modulation': {0: [1], 1: [0]},  # Mutual modulation
            'output': [0]
        },
        'complex': {  # Algorithm 5: Complex 6-operator setup
            'operators': [0, 1, 2, 3, 4, 5],
            'modulation': {0: [1, 2], 1: [3], 2: [4], 3: [5]},
            'output': [0]
        }
    }

    def __init__(self, num_operators: int = 6, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize FM synthesis engine.

        Args:
            num_operators: Number of FM operators (2-6)
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.num_operators = max(2, min(6, num_operators))

        # Initialize operators
        self.operators = [FMOperator(sample_rate) for _ in range(self.num_operators)]

        # Algorithm and routing
        self.algorithm = 'basic'
        self.modulation_matrix = {}  # operator_index -> [modulating_operator_indices]
        self.output_operators = [0]  # Operators that contribute to final output

        # Global parameters
        self.master_volume = 1.0
        self.pitch_bend_range = 2.0  # Semitones
        self.pitch_bend = 0.0  # Current pitch bend in semitones

        # Set default algorithm
        self.set_algorithm('basic')

        # Voice state
        self.active_notes = {}  # note -> velocity
        self.current_note = 60  # Default note
        self.current_velocity = 100

    def get_engine_info(self) -> Dict[str, Any]:
        """Get FM engine information."""
        return {
            'name': 'FM Synthesis Engine',
            'type': 'fm',
            'capabilities': ['fm_synthesis', 'operator_modulation', 'feedback_fm', 'algorithms'],
            'formats': ['.fmp', '.dx7'],  # Custom FM patch formats
            'polyphony': 16,  # FM is more CPU intensive, lower polyphony
            'parameters': ['algorithm', 'operator_freq_ratios', 'operator_envelopes', 'feedback_levels'],
            'max_operators': self.num_operators
        }

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float], block_size: int) -> np.ndarray:
        """
        Generate FM synthesis audio samples.

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

        # Calculate base frequency
        base_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply pitch bend
        pitch_bend_semitones = modulation.get('pitch', 0.0) / 100.0  # Convert cents to semitones
        bend_ratio = 2.0 ** (pitch_bend_semitones / 12.0)
        base_freq *= bend_ratio

        # Generate samples
        output = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Update envelopes
            dt = 1.0 / self.sample_rate
            for op in self.operators:
                op.update_envelope(dt)

            # Generate operator outputs with modulation routing
            operator_outputs = [0.0] * self.num_operators

            # Process operators in dependency order (modulators first)
            for op_idx in range(self.num_operators):
                modulation_input = 0.0

                # Sum modulation from other operators
                if op_idx in self.modulation_matrix:
                    for mod_idx in self.modulation_matrix[op_idx]:
                        modulation_input += operator_outputs[mod_idx] * 1000.0  # Scale modulation

                # Generate operator output
                operator_outputs[op_idx] = self.operators[op_idx].generate_sample(base_freq, modulation_input)

            # Sum output operators
            sample = 0.0
            for op_idx in self.output_operators:
                sample += operator_outputs[op_idx]

            # Apply master volume and velocity
            velocity_scale = velocity / 127.0
            sample *= self.master_volume * velocity_scale

            output[i] = sample

        # Convert to stereo
        stereo_output = np.column_stack((output, output))

        return stereo_output

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported."""
        return 0 <= note <= 127

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> 'FMPartial':
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
            self.modulation_matrix = algorithm['modulation'].copy()
            self.output_operators = algorithm['output'].copy()

            # Ensure we have enough operators
            max_op = 0
            if self.modulation_matrix:
                max_op = max(max_op, max(self.modulation_matrix.keys()))
            if self.output_operators:
                max_op = max(max_op, max(self.output_operators))
            if max_op >= self.num_operators:
                print(f"Warning: Algorithm {algorithm_name} requires {max_op + 1} operators, "
                      f"but engine only has {self.num_operators}")

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
        Get parameters for a specific operator.

        Args:
            op_index: Operator index (0-5)

        Returns:
            Operator parameters dictionary
        """
        if 0 <= op_index < self.num_operators:
            op = self.operators[op_index]
            return {
                'frequency_ratio': op.frequency_ratio,
                'detune_cents': op.detune_cents,
                'feedback_level': op.feedback_level,
                'waveform': op.waveform,
                'attack_time': op.attack_time,
                'decay_time': op.decay_time,
                'sustain_level': op.sustain_level,
                'release_time': op.release_time
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
        return ['.fmp', '.dx7']

    def load_patch(self, patch_data: Dict[str, Any]):
        """
        Load FM patch data.

        Args:
            patch_data: Patch parameters dictionary
        """
        # Set algorithm
        algorithm = patch_data.get('algorithm', 'basic')
        self.set_algorithm(algorithm)

        # Set operator parameters
        for op_idx in range(self.num_operators):
            op_key = f'operator_{op_idx}'
            if op_key in patch_data:
                self.set_operator_parameters(op_idx, patch_data[op_key])

        # Set global parameters
        self.master_volume = patch_data.get('master_volume', 1.0)

    def save_patch(self) -> Dict[str, Any]:
        """
        Save current patch data.

        Returns:
            Patch parameters dictionary
        """
        patch = {
            'algorithm': self.algorithm,
            'master_volume': self.master_volume,
            'num_operators': self.num_operators
        }

        # Save operator parameters
        for op_idx in range(self.num_operators):
            op_params = self.get_operator_parameters(op_idx)
            patch[f'operator_{op_idx}'] = op_params

        return patch

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get current algorithm information."""
        return {
            'current_algorithm': self.algorithm,
            'available_algorithms': list(self.ALGORITHMS.keys()),
            'modulation_matrix': self.modulation_matrix,
            'output_operators': self.output_operators
        }
