"""Professional rotary speaker simulation with delay-based Doppler effect."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProfessionalRotarySpeaker:
    """
    Professional rotary speaker (Leslie) simulation.

    Features:
    - Horn (treble drum) and rotor (bass drum) with independent speeds
    - Delay-based Doppler effect (variable delay lines)
    - State-variable filter (2nd-order, 12 dB/oct) crossover at 800 Hz
    - Acceleration ramp (2 seconds) for realistic speed transitions
    - Amplitude modulation for spatial "swish"
    - Dry/wet mix via ``params["dry_wet"]``

    Parameters accepted by ``process_sample()``:
        speed (float): 0-1, mapped to 0.5-6.5 Hz overall speed.
        depth (float): 0-1, modulation depth for Doppler and amplitude.
        dry_wet (float): 0-1, dry/wet balance.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Speed state with 2-second acceleration ramp
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.accel = 1.0 / (2.0 * float(sample_rate))

        # LFO phase accumulators
        self.horn_phase = 0.0
        self.rotor_phase = 0.0

        # Delay lines for Doppler effect (max 5 ms)
        delay_len = int(0.005 * sample_rate)
        self.delay_len = max(delay_len, 4)
        self.horn_delay = np.zeros(self.delay_len, dtype=np.float32)
        self.rotor_delay = np.zeros(self.delay_len, dtype=np.float32)
        self.horn_write = 0
        self.rotor_write = 0
        self.base_delay_samples = int(0.002 * sample_rate)

        # State-variable filter (2nd-order Butterworth crossover)
        self._crossover_freq = 800.0
        self._last_crossover_freq = 800.0
        self._svf_f = 0.0
        self._svf_lp = 0.0
        self._svf_bp = 0.0
        self._update_crossover_coeffs()

        self.lock = threading.RLock()

    # ── crossover_freq property ──────────────────────────────────────────

    @property
    def crossover_freq(self) -> float:
        """Crossover frequency in Hz (default 800 Hz)."""
        return self._crossover_freq

    @crossover_freq.setter
    def crossover_freq(self, value: float) -> None:
        if abs(self._crossover_freq - value) > 1.0:
            self._crossover_freq = value
            self._update_crossover_coeffs()
            self._last_crossover_freq = value

    # ── internal helpers ──────────────────────────────────────────────────

    def _update_crossover_coeffs(self) -> None:
        """Recalculate SVF coefficient from crossover frequency."""
        self._svf_f = 2.0 * math.sin(math.pi * self._crossover_freq / self.sample_rate)

    # ── sample processing ─────────────────────────────────────────────────

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process a single sample through the rotary speaker."""
        with self.lock:
            speed = params.get("speed", 0.5)
            depth = params.get("depth", 0.8)
            dry_wet = params.get("dry_wet", 0.5)

            # ── speed ramp (2-second acceleration) ────────────────────────
            self.target_speed = speed
            diff = self.target_speed - self.current_speed
            if abs(diff) > self.accel:
                self.current_speed += math.copysign(self.accel, diff)
            else:
                self.current_speed = self.target_speed

            # ── convert 0-1 to Hz ─────────────────────────────────────────
            speed_hz = 0.5 + self.current_speed * 6.0  # 0.5-6.5 Hz
            horn_hz = speed_hz * 1.0
            rotor_hz = speed_hz * 0.15  # ≈1/7 of horn (real Leslie 122 ratio)

            # ── update LFO phases ─────────────────────────────────────────
            self.horn_phase = (self.horn_phase + 2.0 * math.pi * horn_hz / self.sample_rate) % (
                2.0 * math.pi
            )

            self.rotor_phase = (self.rotor_phase + 2.0 * math.pi * rotor_hz / self.sample_rate) % (
                2.0 * math.pi
            )

            # ── SVF 2nd-order crossover ───────────────────────────────────
            hp = input_sample - self._svf_lp - 0.707 * self._svf_bp
            self._svf_bp += self._svf_f * hp
            self._svf_lp += self._svf_f * self._svf_bp
            low_signal = self._svf_lp  # bass → rotor
            high_signal = hp  # treble → horn

            # ── delay-based Doppler read helper ───────────────────────────
            def _read(
                buf: np.ndarray,
                write_pos: int,
                delay: float,
                buf_len: int,
            ) -> float:
                delay_int = int(delay)
                delay_frac = delay - delay_int
                read1 = (write_pos - delay_int) % buf_len
                read2 = (read1 - 1) % buf_len
                return float(buf[read1]) * (1.0 - delay_frac) + float(buf[read2]) * delay_frac

            # ── horn path (treble) ────────────────────────────────────────
            self.horn_delay[self.horn_write] = high_signal
            horn_del = self.base_delay_samples * (1.0 + depth * math.cos(self.horn_phase))
            horn_del = max(1.0, min(horn_del, self.delay_len - 0.01))
            horn_out = _read(self.horn_delay, self.horn_write, horn_del, self.delay_len)
            self.horn_write = (self.horn_write + 1) % self.delay_len

            # ── rotor path (bass) ─────────────────────────────────────────
            self.rotor_delay[self.rotor_write] = low_signal
            rotor_del = self.base_delay_samples * (1.0 + depth * math.cos(self.rotor_phase))
            rotor_del = max(1.0, min(rotor_del, self.delay_len - 0.01))
            rotor_out = _read(self.rotor_delay, self.rotor_write, rotor_del, self.delay_len)
            self.rotor_write = (self.rotor_write + 1) % self.delay_len

            # ── amplitude modulation (spatial "swish") ────────────────────
            horn_amp = 1.0 + depth * 0.3 * math.sin(self.horn_phase * 2.0)
            rotor_amp = 1.0 + depth * 0.3 * math.sin(self.rotor_phase * 3.0)

            wet = horn_out * horn_amp + rotor_out * rotor_amp

            # ── dry/wet mix ───────────────────────────────────────────────
            return input_sample * (1.0 - dry_wet) + wet * dry_wet

    def process_block(self, samples: np.ndarray, params: dict[str, float]) -> None:
        """Process a block of samples with a single lock acquisition.

        Args:
            samples: Block of audio samples (modified in-place).
            params: Dictionary with optional keys:
                "speed" - Speed (0-1)
                "depth" - Modulation depth (0-1)
                "dry_wet" - Dry/wet mix (0-1)
        """
        with self.lock:
            speed = params.get("speed", 0.5)
            depth = params.get("depth", 0.8)
            dry_wet_val = params.get("dry_wet", 0.5)

            # Speed ramp (once per block)
            self.target_speed = speed
            diff = self.target_speed - self.current_speed
            if abs(diff) > self.accel * len(samples):
                self.current_speed += math.copysign(self.accel * len(samples), diff)
            else:
                self.current_speed = self.target_speed

            # Convert 0-1 to Hz
            speed_hz = 0.5 + self.current_speed * 6.0
            horn_hz = speed_hz * 1.0
            rotor_hz = speed_hz * 0.15

            # Update SVF crossover coeffs if needed
            if abs(self._last_crossover_freq - self._crossover_freq) > 1.0:
                self._update_crossover_coeffs()
                self._last_crossover_freq = self._crossover_freq

            phase_inc_horn = 2.0 * math.pi * horn_hz / self.sample_rate
            phase_inc_rotor = 2.0 * math.pi * rotor_hz / self.sample_rate

            for i in range(len(samples)):
                input_sample = float(samples[i])

                # Update phases
                self.horn_phase = (self.horn_phase + phase_inc_horn) % (2.0 * math.pi)
                self.rotor_phase = (self.rotor_phase + phase_inc_rotor) % (2.0 * math.pi)

                # SVF 2nd-order crossover
                hp = input_sample - self._svf_lp - 0.707 * self._svf_bp
                self._svf_bp += self._svf_f * hp
                self._svf_lp += self._svf_f * self._svf_bp
                low_signal = self._svf_lp  # bass → rotor
                high_signal = hp  # treble → horn

                # Horn path (treble)
                self.horn_delay[self.horn_write] = high_signal
                horn_del = self.base_delay_samples * (1.0 + depth * math.cos(self.horn_phase))
                horn_del = max(1.0, min(horn_del, self.delay_len - 0.01))
                horn_di, horn_df = int(horn_del), horn_del - int(horn_del)
                horn_r1 = (self.horn_write - horn_di) % self.delay_len
                horn_r2 = (horn_r1 - 1) % self.delay_len
                horn_out = (
                    float(self.horn_delay[horn_r1]) * (1.0 - horn_df)
                    + float(self.horn_delay[horn_r2]) * horn_df
                )
                self.horn_write = (self.horn_write + 1) % self.delay_len

                # Rotor path (bass)
                self.rotor_delay[self.rotor_write] = low_signal
                rotor_del = self.base_delay_samples * (1.0 + depth * math.cos(self.rotor_phase))
                rotor_del = max(1.0, min(rotor_del, self.delay_len - 0.01))
                rotor_di, rotor_df = int(rotor_del), rotor_del - int(rotor_del)
                rotor_r1 = (self.rotor_write - rotor_di) % self.delay_len
                rotor_r2 = (rotor_r1 - 1) % self.delay_len
                rotor_out = (
                    float(self.rotor_delay[rotor_r1]) * (1.0 - rotor_df)
                    + float(self.rotor_delay[rotor_r2]) * rotor_df
                )
                self.rotor_write = (self.rotor_write + 1) % self.delay_len

                # Amplitude modulation (spatial "swish")
                horn_amp = 1.0 + depth * 0.3 * math.sin(self.horn_phase * 2.0)
                rotor_amp = 1.0 + depth * 0.3 * math.sin(self.rotor_phase * 3.0)

                wet = horn_out * horn_amp + rotor_out * rotor_amp
                samples[i] = input_sample * (1.0 - dry_wet_val) + wet * dry_wet_val
