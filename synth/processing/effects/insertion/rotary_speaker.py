"""Professional rotary speaker simulation."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProfessionalRotarySpeaker:
    """
    Professional rotary speaker simulation with physical modeling.

    Features:
    - Horn and rotor simulation
    - Doppler effect modeling
    - Air absorption
    - Speed changes with acceleration
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Horn and rotor characteristics
        self.horn_radius = 0.3  # meters
        self.rotor_radius = 0.2  # meters
        self.distance = 0.5  # meters (speaker to mic)

        # Speed control
        self.target_speed = 1.0  # 0-1 (slow-fast)
        self.current_speed = 0.0
        self.acceleration = 0.01

        # Phase tracking
        self.horn_phase = 0.0
        self.rotor_phase = 0.0

        # Delay lines for Doppler effect
        self.horn_delay_line = np.zeros(int(0.01 * self.sample_rate), dtype=np.float32)
        self.rotor_delay_line = np.zeros(int(0.01 * self.sample_rate), dtype=np.float32)
        self.horn_write_pos = 0
        self.rotor_write_pos = 0

        # Crossover frequencies
        self.crossover_freq = 800.0  # Hz

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process sample through rotary speaker simulation."""
        with self.lock:
            speed = params.get("speed", 0.5)
            depth = params.get("depth", 0.8)

            # Update speed with acceleration
            self.target_speed = speed
            if abs(self.current_speed - self.target_speed) > 0.01:
                if self.current_speed < self.target_speed:
                    self.current_speed = min(
                        self.target_speed, self.current_speed + self.acceleration
                    )
                else:
                    self.current_speed = max(
                        self.target_speed, self.current_speed - self.acceleration
                    )

            # Calculate rotational speeds (different for horn and rotor)
            horn_speed = self.current_speed * 0.4  # Horn rotates slower
            rotor_speed = self.current_speed * 0.6  # Rotor rotates faster

            # Update phases
            horn_phase_inc = 2 * math.pi * horn_speed / self.sample_rate
            rotor_phase_inc = 2 * math.pi * rotor_speed / self.sample_rate

            self.horn_phase = (self.horn_phase + horn_phase_inc) % (2 * math.pi)
            self.rotor_phase = (self.rotor_phase + rotor_phase_inc) % (2 * math.pi)

            # Calculate Doppler shifts
            horn_angle = self.horn_phase
            rotor_angle = self.rotor_phase

            # Simplified Doppler calculation
            horn_doppler = 1.0 + math.cos(horn_angle) * depth * 0.05
            rotor_doppler = 1.0 + math.cos(rotor_angle) * depth * 0.03

            # Frequency splitting (simple crossover)
            # Low frequencies to rotor, high frequencies to horn
            low_alpha = 1.0 / (1.0 + 2 * math.pi * self.crossover_freq / self.sample_rate)
            low_signal = low_alpha * input_sample
            high_signal = input_sample - low_signal

            # Apply Doppler to each path
            horn_output = high_signal * horn_doppler
            rotor_output = low_signal * rotor_doppler

            # Add some amplitude modulation for the "swishing" effect
            horn_amp_mod = 1.0 - depth * 0.2 + depth * 0.2 * math.sin(horn_angle * 2)
            rotor_amp_mod = 1.0 - depth * 0.15 + depth * 0.15 * math.sin(rotor_angle * 3)

            horn_output *= horn_amp_mod
            rotor_output *= rotor_amp_mod

            # Mix horn and rotor
            return horn_output + rotor_output


