"""
Block-optimized ADSR Envelope implementation for XG synthesizer.
Provides high-performance envelope generation with vectorized processing.
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class BlockADSREnvelope:
    """Block-optimized ADSR envelope with vectorized processing and sample-accurate timing"""

    def __init__(self, delay=0.0, attack=0.01, hold=0.0, decay=0.3, sustain=0.7, release=0.5,
                 velocity_sense=1.0, key_scaling=0.0, sample_rate=44100):
        self.delay = delay
        self.attack = attack
        self.hold = hold
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.velocity_sense = velocity_sense
        self.key_scaling = key_scaling
        self.sample_rate = sample_rate

        # State variables for sample-accurate processing
        self.state = "idle"
        self.level = 0.0
        self.release_start = 0.0
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.hold_notes = False

        # Pre-calculated sample counts for each stage
        self._attack_samples = max(1, int(self.attack * self.sample_rate))
        self._decay_samples = max(1, int(self.decay * self.sample_rate))
        self._hold_samples = max(0, int(self.hold * self.sample_rate))
        self._delay_samples = max(0, int(self.delay * self.sample_rate))
        self._release_samples = max(1, int(self.release * self.sample_rate))

        # Pre-calculated increments for optimal performance
        self._attack_inc = 1.0 / self._attack_samples
        self._decay_dec = (1.0 - self.sustain) / self._decay_samples
        self._release_dec = 1.0 / self._release_samples

        # State counters for sample-accurate timing
        self.delay_counter = 0
        self.attack_counter = 0
        self.hold_counter = 0
        self.decay_counter = 0

        # Modulation parameter support
        self.modulated_delay = delay
        self.modulated_attack = attack
        self.modulated_hold = hold
        self.modulated_decay = decay
        self.modulated_sustain = sustain
        self.modulated_release = release

    def process_block(self, block_size: int, velocity: float = 127.0, note: int = 60,
                     midi_events: List[Dict[str, Any]] = None) -> np.ndarray:
        """
        Process a block of samples with sample-accurate envelope generation.

        Args:
            block_size: Number of samples to generate
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
            midi_events: List of MIDI events within this block

        Returns:
            NumPy array of envelope values (0.0 to 1.0)
        """
        # Initialize output block
        envelope_block = np.zeros(block_size, dtype=np.float32)

        # Apply parameter modulation
        velocity_factor = min(1.0, (velocity / 127.0) ** self.velocity_sense)

        # Apply key scaling to parameters
        key_scaling_factor = self._calculate_key_scaling_factor(note)

        # Process each sample in the block
        for i in range(block_size):
            # Check for MIDI events at this sample
            if midi_events:
                for event in midi_events:
                    if event.get('sample_position', -1) == i:
                        self._process_midi_event(event)

            # Generate envelope sample with current parameters
            envelope_block[i] = self._process_sample(velocity_factor, key_scaling_factor)

        return envelope_block

    def _calculate_key_scaling_factor(self, note: int) -> float:
        """Calculate key scaling factor based on note position"""
        if abs(self.key_scaling) < 0.001:
            return 1.0

        # Normalize note around middle C (60)
        note_offset = (note - 60) / 60.0
        key_scaling_factor = 1.0 + note_offset * self.key_scaling

        return key_scaling_factor

    def _process_midi_event(self, event: Dict[str, Any]):
        """Process a MIDI event with sample-accurate timing"""
        command = event.get('command', 0)
        data1 = event.get('data1', 0)
        data2 = event.get('data2', 0)

        # Note On
        if command == 144 and data2 > 0:  # Note On with velocity > 0
            self.note_on(data2, data1)
        # Note Off or Note On with velocity 0
        elif (command == 128) or (command == 144 and data2 == 0):
            self.note_off()

    def _process_sample(self, velocity_factor: float, key_scaling_factor: float) -> float:
        """Process a single envelope sample"""
        if self.state == "idle":
            return 0.0

        elif self.state == "delay":
            self.delay_counter += 1
            if self.delay_counter >= self._delay_samples * key_scaling_factor:
                self.state = "attack"
                self.attack_counter = 0
            return 0.0

        elif self.state == "attack":
            self.attack_counter += 1
            attack_samples = self._attack_samples * key_scaling_factor
            attack_inc = 1.0 / attack_samples

            self.level = min(1.0, self.level + attack_inc)

            if self.level >= 1.0 or self.attack_counter >= attack_samples:
                self.level = 1.0
                self.state = "hold"
                self.hold_counter = 0

            return self.level * velocity_factor * (0.5 if self.soft_pedal else 1.0)

        elif self.state == "hold":
            self.hold_counter += 1
            hold_samples = self._hold_samples * key_scaling_factor

            if self.hold_counter >= hold_samples:
                self.state = "decay"
                self.decay_counter = 0

            return self.level * velocity_factor

        elif self.state == "decay":
            self.decay_counter += 1
            decay_samples = self._decay_samples * key_scaling_factor
            decay_dec = (1.0 - self.sustain) / decay_samples

            self.level = max(self.sustain, self.level - decay_dec)

            if abs(self.level - self.sustain) < 0.001 or self.decay_counter >= decay_samples:
                self.level = self.sustain
                self.state = "sustain"

            return self.level * velocity_factor

        elif self.state == "sustain":
            return self.level * velocity_factor

        elif self.state == "release":
            release_dec = self.level / max(1, self._release_samples * key_scaling_factor)
            self.level = max(0.0, self.level - release_dec)

            if self.level <= 0.0:
                self.level = 0.0
                self.state = "idle"

            return self.level * velocity_factor

        return 0.0

    def note_on(self, velocity: int, note: int = 60, soft_pedal: bool = False):
        """Handle Note On event - optimized for block processing"""
        # Reset state counters
        self.delay_counter = 0
        self.attack_counter = 0
        self.hold_counter = 0
        self.decay_counter = 0

        # Apply velocity sensitivity
        velocity_factor = min(1.0, (velocity / 127.0) ** self.velocity_sense)

        # Apply key scaling to parameters
        if abs(self.key_scaling) > 0.001:
            key_scaling_factor = self._calculate_key_scaling_factor(note)

            # Update modulated parameters with key scaling
            self.modulated_attack = self.attack * key_scaling_factor
            self.modulated_decay = self.decay * key_scaling_factor
            self.modulated_release = self.release * key_scaling_factor
            self.modulated_delay = self.delay * key_scaling_factor

            # Recalculate sample counts
            self._attack_samples = max(1, int(self.modulated_attack * self.sample_rate))
            self._decay_samples = max(1, int(self.modulated_decay * self.sample_rate))
            self._release_samples = max(1, int(self.modulated_release * self.sample_rate))
            self._delay_samples = max(0, int(self.modulated_delay * self.sample_rate))

        # Apply soft pedal
        if soft_pedal or self.soft_pedal:
            velocity_factor *= 0.5
            self._attack_samples = int(self._attack_samples * 2.0)

        # Recalculate increments
        self._attack_inc = 1.0 / self._attack_samples
        self._decay_dec = (1.0 - self.sustain) / self._decay_samples
        self._release_dec = 1.0 / self._release_samples

        # Start envelope
        self.level = 0.0
        if self._delay_samples > 0:
            self.state = "delay"
        else:
            self.state = "attack"

    def note_off(self):
        """Handle Note Off event"""
        if self.state not in ["idle"]:
            self.release_start = self.level
            self.state = "release"

    # Original controller methods for compatibility
    def sustain_pedal_on(self):
        self.sustain_pedal = True

    def sustain_pedal_off(self):
        self.sustain_pedal = False
        if self.state == "sustain" and not (self.sostenuto_pedal or self.hold_notes):
            self.state = "release"

    def sostenuto_pedal_on(self):
        self.sostenuto_pedal = True
        if self.state in ["sustain", "decay"]:
            self.held_by_sostenuto = True

    def sostenuto_pedal_off(self):
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        if self.state == "sustain" and not (self.sustain_pedal or self.hold_notes):
            self.state = "release"

    def soft_pedal_on(self):
        self.soft_pedal = True

    def soft_pedal_off(self):
        self.soft_pedal = False
        self._attack_samples = max(1, int(self.attack * self.sample_rate))
        self._attack_inc = 1.0 / self._attack_samples

    def all_notes_off(self):
        self.hold_notes = True
        if self.state in ["sustain"]:
            self.state = "sustain"

    def reset_all_notes(self):
        self.hold_notes = False
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.state = "release"
        self.release_start = self.level

    def process(self) -> float:
        """Original per-sample processing for compatibility"""
        return self._process_sample(1.0, 1.0)

    def update_parameters(self, delay=None, attack=None, hold=None, decay=None, sustain=None, release=None,
                         velocity_sense=None, key_scaling=None,
                         modulated_delay=None, modulated_attack=None, modulated_hold=None,
                         modulated_decay=None, modulated_sustain=None, modulated_release=None):
        """Update envelope parameters"""
        if delay is not None:
            self.delay = max(0.0, delay)
        if attack is not None:
            self.attack = max(0.001, attack)
        if hold is not None:
            self.hold = max(0.0, hold)
        if decay is not None:
            self.decay = max(0.001, decay)
        if sustain is not None:
            self.sustain = max(0.0, min(1.0, sustain))
        if release is not None:
            self.release = max(0.001, release)
        if velocity_sense is not None:
            self.velocity_sense = max(0.0, min(2.0, velocity_sense))
        if key_scaling is not None:
            self.key_scaling = key_scaling

        # Update modulated parameters
        if modulated_delay is not None:
            self.modulated_delay = max(0.0, modulated_delay)
        if modulated_attack is not None:
            self.modulated_attack = max(0.001, modulated_attack)
        if modulated_hold is not None:
            self.modulated_hold = max(0.0, modulated_hold)
        if modulated_decay is not None:
            self.modulated_decay = max(0.001, modulated_decay)
        if modulated_sustain is not None:
            self.modulated_sustain = max(0.0, min(1.0, modulated_sustain))
        if modulated_release is not None:
            self.modulated_release = max(0.001, modulated_release)

        # Recalculate derived values
        self._delay_samples = max(0, int(self.modulated_delay * self.sample_rate))
        self._attack_samples = max(1, int(self.modulated_attack * self.sample_rate))
        self._decay_samples = max(1, int(self.modulated_decay * self.sample_rate))
        self._release_samples = max(1, int(self.modulated_release * self.sample_rate))

        self._attack_inc = 1.0 / self._attack_samples
        self._decay_dec = (1.0 - self.sustain) / self._decay_samples
        self._release_dec = 1.0 / self._release_samples
