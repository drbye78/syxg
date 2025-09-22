"""
ADSR Envelope implementation for XG synthesizer.
Provides envelope generation with MIDI XG standard compliance.
"""

import math
import time
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class ADSREnvelope:
    """ADSR envelope in accordance with MIDI XG standard with extended controller support"""
    def __init__(self, delay=0.0, attack=0.01, hold=0.0, decay=0.3, sustain=0.7, release=0.5,
                 velocity_sense=1.0, key_scaling=0.0, sample_rate=44100):
        self.delay = delay
        self.attack = attack
        self.hold = hold
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.velocity_sense = velocity_sense  # Velocity sensitivity
        self.key_scaling = key_scaling  # Note height dependency
        self.sample_rate = sample_rate
        self.state = "idle"
        self.level = 0.0
        self.release_start = 0.0
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.hold_notes = False

        # Parameter modulation support
        self.modulated_delay = delay
        self.modulated_attack = attack
        self.modulated_hold = hold
        self.modulated_decay = decay
        self.modulated_sustain = sustain
        self.modulated_release = release
        self._recalculate_increments()

    def _recalculate_increments(self):
        """Recalculation of increments for current parameters"""
        # Using modulated parameters
        delay = self.modulated_delay
        attack = self.modulated_attack
        hold = self.modulated_hold
        decay = self.modulated_decay
        sustain = self.modulated_sustain
        release = self.modulated_release

        # Delay - just delay before attack starts
        self.delay_samples = int(delay * self.sample_rate)
        self.delay_counter = 0

        # Attack - logarithmic growth (more natural for hearing)
        if attack > 0:
            self.attack_increment = 1.0 / (attack * self.sample_rate * 2)
        else:
            self.attack_increment = 1.0  # instant attack

        # Hold - level fixation after attack
        self.hold_samples = int(hold * self.sample_rate)
        self.hold_counter = 0

        # Decay - linear decrease to sustain level
        if decay > 0:
            self.decay_decrement = (1.0 - sustain) / (decay * self.sample_rate)
        else:
            self.decay_decrement = 1.0 - sustain  # instant decay

        # Release - linear decrease
        if release > 0:
            self.release_decrement = 1.0 / (release * self.sample_rate)
        else:
            self.release_decrement = 1.0  # instant release

    def update_parameters(self, delay=None, attack=None, hold=None, decay=None, sustain=None, release=None,
                          velocity_sense=None, key_scaling=None,
                          modulated_delay=None, modulated_attack=None, modulated_hold=None,
                          modulated_decay=None, modulated_sustain=None, modulated_release=None):
        """Dynamic envelope parameter update"""
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

        # Updating modulated parameters
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

        self._recalculate_increments()

        # Current level adjustment when sustain changes
        if self.state == "sustain" and sustain is not None:
            self.level = self.sustain

    def note_on(self, velocity, note=60, soft_pedal=False):
        """Note On event processing"""
        # Applying velocity sensitivity
        velocity_factor = min(1.0, (velocity / 127.0) ** self.velocity_sense)

        # Applying key scaling (parameter dependency on note height)
        if self.key_scaling != 0.0:
            # Note normalization (60 = C3)
            note_factor = (note - 60) / 60.0
            key_factor = 1.0 + note_factor * self.key_scaling
            # Apply to all time parameters
            self.update_parameters(
                modulated_delay=self.delay * key_factor,
                modulated_attack=self.attack * key_factor,
                modulated_hold=self.hold * key_factor,
                modulated_decay=self.decay * key_factor,
                modulated_release=self.release * key_factor
            )
        else:
            # If key scaling is not applied, ensure modulated parameters equal base parameters
            self.update_parameters(
                modulated_delay=self.delay,
                modulated_attack=self.attack,
                modulated_hold=self.hold,
                modulated_decay=self.decay,
                modulated_release=self.release
            )

        # Applying soft pedal (reduces volume and attack)
        if soft_pedal:
            velocity_factor *= 0.5
            # Increasing attack time with soft pedal
            self.update_parameters(modulated_attack=self.attack * 2.0)

        self.state = "delay"
        self.delay_counter = 0
        self.level = 0.0 * velocity_factor

        if self.hold_notes:
            self.state = "sustain"
            self.level = self.sustain * velocity_factor

    def note_off(self):
        """Note Off event processing"""
        if not self.sustain_pedal and not self.sostenuto_pedal and not self.hold_notes:
            if self.state not in ["release", "idle"]:
                self.release_start = self.level
                self.state = "release"

    def sustain_pedal_on(self):
        """Sustain pedal on"""
        self.sustain_pedal = True

    def sustain_pedal_off(self):
        """Sustain pedal off"""
        self.sustain_pedal = False
        if self.state == "sustain" and not (self.sostenuto_pedal or self.hold_notes):
            self.release_start = self.level
            self.state = "release"

    def sostenuto_pedal_on(self):
        """Sostenuto pedal on (holding current notes)"""
        self.sostenuto_pedal = True
        if self.state in ["sustain", "decay"]:
            self.held_by_sostenuto = True

    def sostenuto_pedal_off(self):
        """Sostenuto pedal off"""
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        if self.state == "sustain" and not (self.sustain_pedal or self.hold_notes):
            self.release_start = self.level
            self.state = "release"

    def soft_pedal_on(self):
        """Soft pedal on"""
        self.soft_pedal = True

    def soft_pedal_off(self):
        """Soft pedal off"""
        self.soft_pedal = False
        # Restoring original parameters
        self.update_parameters(
            modulated_attack=self.attack,
            modulated_hold=self.hold,
            modulated_decay=self.decay,
            modulated_release=self.release
        )

    def all_notes_off(self):
        """All notes off (like with All Notes Off controller)"""
        self.hold_notes = True
        if self.state not in ["release", "idle"]:
            self.state = "sustain"
            self.level = self.sustain

    def reset_all_notes(self):
        """Complete reset (All Sound Off)"""
        self.hold_notes = False
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.release_start = self.level
        self.state = "release"

    def process(self):
        """Processing one envelope sample"""
        if self.state == "delay":
            self.delay_counter += 1
            if self.delay_counter >= self.delay_samples:
                self.state = "attack"

        elif self.state == "attack":
            self.level = min(1.0, self.level + self.attack_increment)
            if self.level >= 1.0:
                self.level = 1.0
                self.state = "hold"
                self.hold_counter = 0

        elif self.state == "hold":
            self.hold_counter += 1
            if self.hold_counter >= self.hold_samples:
                self.state = "decay"

        elif self.state == "decay":
            self.level = max(self.sustain, self.level - self.decay_decrement)
            if abs(self.level - self.sustain) < 0.001:
                self.level = self.sustain
                self.state = "sustain"

        elif self.state == "sustain":
            # Level remains at sustain level
            pass

        elif self.state == "release":
            self.level = max(0.0, self.level - self.release_decrement)
            if self.level <= 0:
                self.level = 0.0
                self.state = "idle"

        return self.level
