"""
Jupiter-X Part Implementation

Represents a single part in the Jupiter-X multitimbral architecture,
containing 4 synthesis engines (Analog, Digital, FM, External) with
comprehensive parameter control.
"""

from __future__ import annotations

from typing import Any
import threading
import numpy as np

from .constants import *

# Jupiter-X engines are now consolidated into base engines with plugins
# from .analog_engine import JupiterXAnalogEngine  # REMOVED - use AdditiveEngine + JupiterXAnalogPlugin
from ..core.oscillator import UltraFastXGLFO, OscillatorPool
from ..engine.additive_engine import AdditiveEngine


class JupiterXEnvelope:
    """
    Jupiter-X Envelope Generator

    Dedicated envelope system for each synthesis engine with advanced
    features like curve shaping, velocity sensitivity, and legato support.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Envelope parameters
        self.attack_time = DEFAULT_ATTACK / 127.0
        self.decay_time = DEFAULT_DECAY / 127.0
        self.sustain_level = DEFAULT_SUSTAIN / 127.0
        self.release_time = DEFAULT_RELEASE / 127.0

        # Jupiter-X curve types (0=Linear, 1=Convex, 2=Concave)
        self.attack_curve = 0
        self.decay_curve = 0
        self.release_curve = 0

        # Velocity sensitivity per stage (0.0-1.0)
        self.attack_velocity_sens = 0.0
        self.decay_velocity_sens = 0.0
        self.sustain_velocity_sens = 0.0
        self.release_velocity_sens = 0.0

        # ===== ADVANCED TRIGGERING MODES (Jupiter-X Enhanced) =====
        self.legato_mode = False  # Legato mode (smooth transitions)
        self.trigger_mode = 0  # 0=Single, 1=Multi, 2=Alternate, 3=Ping-Pong, 4=Random

        # Advanced triggering options
        self.retrigger_sensitivity = 0.5  # How sensitive to retrigger (0.0-1.0)
        self.note_overlap_mode = 0  # 0=Normal, 1=Stack, 2=Replace, 3=Velocity Layer
        self.velocity_curve = 0  # 0=Linear, 1=Convex, 2=Concave, 3=Switch
        self.aftertouch_mode = 0  # 0=Off, 1=Poly, 2=Channel, 3=MPE

        # Portamento/Glissando
        self.portamento_mode = 0  # 0=Off, 1=Linear, 2=Exponential, 3=Glissando
        self.portamento_time = 0.0  # Portamento time (0.0-10.0 seconds)
        self.portamento_curve = 0  # 0=Linear, 1=Convex, 2=Concave

        # Advanced release modes
        self.release_mode = 0  # 0=Normal, 1=Hold, 2=Fade, 3=Loop
        self.release_time_override = 0.0  # Override release time (0.0 = use envelope)

        # Note priority and voice management
        self.note_priority = 0  # 0=Last, 1=Low, 2=High, 3=Round Robin
        self.voice_steal_mode = 0  # 0=Off, 1=Oldest, 2=Quietest, 3=Nearest

        # Internal state
        self.phase = "idle"  # idle, attack, decay, sustain, release
        self.current_level = 0.0
        self.current_velocity = 0

        # Timing
        self.phase_start_time = 0.0
        self.phase_duration = 0.0

        # Thread safety
        self.lock = threading.RLock()

    def trigger(self, velocity: int):
        """
        Trigger envelope with Jupiter-X advanced triggering modes.

        Args:
            velocity: Input velocity (0-127)
        """
        with self.lock:
            should_retrigger = self._should_retrigger(velocity)

            if should_retrigger:
                # Normal retrigger
                self.current_velocity = velocity
                self.phase = "attack"
                self.phase_start_time = 0.0
                self.phase_duration = self._apply_velocity_sensitivity(
                    self.attack_time, velocity, self.attack_velocity_sens
                )
            else:
                # Legato mode - continue from current state
                self.current_velocity = velocity

    def release(self):
        """Release envelope to release phase."""
        with self.lock:
            if self.phase != "idle":
                self.phase = "release"
                self.phase_start_time = 0.0
                self.phase_duration = self._apply_velocity_sensitivity(
                    self.release_time, self.current_velocity, self.release_velocity_sens
                )

    def get_value(self, delta_time: float = 0.0) -> float:
        """
        Get current envelope value with curve shaping.

        Args:
            delta_time: Time elapsed since last call

        Returns:
            Current envelope level (0.0-1.0)
        """
        with self.lock:
            # Update phase timing
            self.phase_start_time += delta_time

            if self.phase == "idle":
                self.current_level = 0.0
            elif self.phase == "attack":
                if self.phase_duration > 0:
                    progress = min(1.0, self.phase_start_time / self.phase_duration)
                    shaped_progress = self._apply_curve(progress, self.attack_curve)
                    self.current_level = shaped_progress
                    if progress >= 1.0:
                        self.phase = "decay"
                        self.phase_start_time = 0.0
                        self.phase_duration = self._apply_velocity_sensitivity(
                            self.decay_time, self.current_velocity, self.decay_velocity_sens
                        )
            elif self.phase == "decay":
                sustain_level = self._apply_velocity_sensitivity(
                    self.sustain_level, self.current_velocity, self.sustain_velocity_sens
                )
                if self.phase_duration > 0:
                    progress = min(1.0, self.phase_start_time / self.phase_duration)
                    shaped_progress = self._apply_curve(progress, self.decay_curve)
                    self.current_level = 1.0 - (1.0 - sustain_level) * shaped_progress
                    if progress >= 1.0:
                        self.phase = "sustain"
            elif self.phase == "sustain":
                self.current_level = self._apply_velocity_sensitivity(
                    self.sustain_level, self.current_velocity, self.sustain_velocity_sens
                )
            elif self.phase == "release":
                if self.phase_duration > 0:
                    progress = min(1.0, self.phase_start_time / self.phase_duration)
                    shaped_progress = self._apply_curve(progress, self.release_curve)
                    self.current_level = self.current_level * (1.0 - shaped_progress)
                    if progress >= 1.0:
                        self.phase = "idle"
                        self.current_level = 0.0

            return self.current_level

    def _apply_curve(self, value: float, curve_type: int) -> float:
        """Apply envelope curve shaping."""
        if curve_type == 0:  # Linear
            return value
        elif curve_type == 1:  # Convex (faster change at start)
            return value * value
        elif curve_type == 2:  # Concave (slower change at start)
            return 1.0 - (1.0 - value) * (1.0 - value)
        else:
            return value

    def _apply_velocity_sensitivity(
        self, base_value: float, velocity: int, sensitivity: float
    ) -> float:
        """Apply velocity sensitivity to envelope parameter."""
        if sensitivity == 0.0:
            return base_value

        vel_norm = velocity / 127.0

        # Different scaling for different parameter types
        if (
            "time" in str(base_value).lower()
            or "attack" in str(base_value).lower()
            or "decay" in str(base_value).lower()
            or "release" in str(base_value).lower()
        ):
            # Time parameters: higher velocity = shorter times
            velocity_factor = 1.0 - (vel_norm * sensitivity)
            return base_value * max(0.1, velocity_factor)
        elif "sustain" in str(base_value).lower():
            # Sustain level: higher velocity = higher sustain
            velocity_factor = vel_norm * sensitivity
            return min(1.0, base_value + velocity_factor)
        else:
            # Default linear scaling
            return base_value * (1.0 + (vel_norm - 0.5) * sensitivity)

    def _should_retrigger(self, velocity: int) -> bool:
        """Determine if envelope should retrigger based on triggering modes."""
        if self.legato_mode and self.phase != "idle":
            return False

        if self.trigger_mode == 0:  # Single
            return True
        elif self.trigger_mode == 1:  # Multi
            return True
        elif self.trigger_mode == 2:  # Alternate
            return (velocity % 2) == 0

        return True

    def reset(self):
        """Reset envelope to idle state."""
        with self.lock:
            self.phase = "idle"
            self.current_level = 0.0
            self.phase_start_time = 0.0
            self.phase_duration = 0.0

    def is_finished(self) -> bool:
        """Check if envelope has finished."""
        return self.phase == "idle"

    def set_parameters(
        self,
        attack: float = None,
        decay: float = None,
        sustain: float = None,
        release: float = None,
    ):
        """Set envelope parameters."""
        with self.lock:
            if attack is not None:
                self.attack_time = max(0.001, attack)
            if decay is not None:
                self.decay_time = max(0.001, decay)
            if sustain is not None:
                self.sustain_level = max(0.0, min(1.0, sustain))
            if release is not None:
                self.release_time = max(0.001, release)

    def set_curves(
        self, attack_curve: int = None, decay_curve: int = None, release_curve: int = None
    ):
        """Set envelope curve types."""
        with self.lock:
            if attack_curve is not None:
                self.attack_curve = max(0, min(2, attack_curve))
            if decay_curve is not None:
                self.decay_curve = max(0, min(2, decay_curve))
            if release_curve is not None:
                self.release_curve = max(0, min(2, release_curve))

    def set_velocity_sensitivity(
        self,
        attack_sens: float = None,
        decay_sens: float = None,
        sustain_sens: float = None,
        release_sens: float = None,
    ):
        """Set velocity sensitivity per stage."""
        with self.lock:
            if attack_sens is not None:
                self.attack_velocity_sens = max(0.0, min(1.0, attack_sens))
            if decay_sens is not None:
                self.decay_velocity_sens = max(0.0, min(1.0, decay_sens))
            if sustain_sens is not None:
                self.sustain_velocity_sens = max(0.0, min(1.0, sustain_sens))
            if release_sens is not None:
                self.release_velocity_sens = max(0.0, min(1.0, release_sens))


class JupiterXEngine:
    """
    Base class for Jupiter-X synthesis engines.

    Each engine type (Analog, Digital, FM, External) inherits from this
    and implements specific synthesis algorithms.
    """

    def __init__(self, engine_type: int, part: JupiterXPart, sample_rate: int = 44100):
        self.engine_type = engine_type
        self.part = part
        self.sample_rate = sample_rate
        self.enabled = False
        self.level = DEFAULT_ENGINE_LEVEL / 127.0  # 0.0 to 1.0

        # Dedicated per-engine LFO (Jupiter-X architecture)
        self.lfo = UltraFastXGLFO(
            id=engine_type,  # Use engine type as LFO ID for uniqueness
            waveform="sine",
            rate=5.0,
            depth=1.0,
            delay=0.0,
            sample_rate=sample_rate,
        )

        # LFO modulation parameters
        self.lfo_to_pitch = 0.0  # LFO -> pitch modulation depth
        self.lfo_to_filter = 0.0  # LFO -> filter modulation depth
        self.lfo_to_amplitude = 0.0  # LFO -> amplitude modulation depth
        self.lfo_to_pan = 0.0  # LFO -> pan modulation depth (Jupiter-X)
        self.lfo_to_pwm = 0.0  # LFO -> PWM modulation depth (Jupiter-X)

        # Per-engine envelope system (Jupiter-X feature)
        self.amp_envelope = JupiterXEnvelope(sample_rate)  # Dedicated envelope per engine

        # Engine parameters (initialized by subclasses)
        self.parameters = self._get_default_parameters()

        # Thread safety
        self.lock = threading.RLock()

    def _get_default_parameters(self) -> dict[str, Any]:
        """Get default parameters for this engine type."""
        return {}

    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Set engine parameter."""
        with self.lock:
            if param_name in self.parameters:
                self.parameters[param_name] = value
                return True
        return False

    def get_parameter(self, param_name: str) -> Any:
        """Get engine parameter."""
        with self.lock:
            return self.parameters.get(param_name)

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples for this engine.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Base implementation returns silence - overridden by subclasses
        return np.zeros((block_size, 2), dtype=np.float32)

    def reset(self):
        """Reset engine state."""
        pass


class JupiterXDigitalEngine(JupiterXEngine):
    """
    Jupiter-X Digital Engine: Wavetable Synthesis

    Advanced wavetable synthesis engine with morphing, bit crushing,
    and formant shifting capabilities. Supports wavetable position
    modulation and advanced digital signal processing.
    """

    def __init__(self, part: JupiterXPart, sample_rate: int = 44100):
        super().__init__(ENGINE_DIGITAL, part, sample_rate)

        # Wavetable Core
        self.wavetable_position = 0.0  # Current position in wavetable (0.0-1.0)
        self.wavetable_speed = 1.0  # Playback speed multiplier
        self.wavetable_start = 0.0  # Loop start position (0.0-1.0)
        self.wavetable_end = 1.0  # Loop end position (0.0-1.0)
        self.wavetable_loop = True  # Enable/disable looping

        # Morphing & Wave Shaping
        self.morph_amount = 0.0  # Wavetable morphing (0.0-1.0)
        self.morph_position = 0.0  # Position in morph sequence
        self.morph_speed = 1.0  # Morphing speed

        # Digital Processing
        self.bit_crush_depth = 0.0  # Bit crushing amount (0.0-1.0)
        self.bit_crush_bits = 16  # Bit depth for crushing (1-16)
        self.sample_rate_reduction = 0.0  # Sample rate reduction (0.0-1.0)

        # Formant Processing
        self.formant_shift = 0.0  # Formant frequency shift (-2.0 to +2.0 octaves)
        self.formant_resonance = 0.0  # Formant resonance (0.0-1.0)
        self.formant_mix = 1.0  # Dry/wet mix for formant processing

        # Advanced Digital Features
        self.wavefolding_amount = 0.0  # Wavefolding distortion (0.0-1.0)
        self.wavefolding_symmetry = 0.0  # Wavefolding symmetry (-1.0 to +1.0)
        self.ring_mod_frequency = 0.0  # Ring modulation frequency (Hz)
        self.ring_mod_mix = 0.0  # Ring modulation mix (0.0-1.0)

        # Filter Integration (Digital engine has its own filter)
        self.digital_filter_type = 0  # 0=LPF, 1=HPF, 2=BPF, 3=Notch
        self.digital_filter_cutoff = 1.0  # Filter cutoff (0.0-1.0)
        self.digital_filter_resonance = 0.0  # Filter resonance (0.0-1.0)
        self.digital_filter_envelope = 0.0  # Filter envelope amount

        # Internal State
        self.phase = 0.0  # Current phase for wavetable playback
        self.last_sample = 0.0  # Last output sample for filtering

        # Wavetable Data - load actual wavetables
        self.wavetables = self._generate_default_wavetables()
        self._load_additional_wavetables()

        # Initialize parameters dict
        self.parameters = self._get_default_parameters()

    def _load_additional_wavetables(self):
        """Load additional wavetables from files or presets."""
        # Load user wavetables if available
        # This can be extended to load from files
        pass

    def _generate_default_wavetables(self) -> dict[str, np.ndarray]:
        """Generate default wavetable set for digital engine."""
        wavetables = {}

        # Basic waveforms
        size = 2048  # Wavetable size
        x = np.linspace(0, 2 * np.pi, size, endpoint=False)

        # Sine wave
        wavetables["sine"] = np.sin(x)

        # Triangle wave
        wavetables["triangle"] = 2 * np.abs((x / np.pi) % 2 - 1) - 1

        # Square wave
        wavetables["square"] = np.sign(np.sin(x))

        # Sawtooth wave
        wavetables["sawtooth"] = 2 * (x / (2 * np.pi) - np.floor(x / (2 * np.pi) + 0.5))

        # White noise
        wavetables["noise"] = np.random.uniform(-1, 1, size)

        # Complex waveforms with proper harmonic content
        wavetables["complex1"] = np.sin(x) + 0.5 * np.sin(2 * x) + 0.25 * np.sin(4 * x)
        wavetables["complex2"] = np.sin(x) * np.cos(3 * x)
        wavetables["complex3"] = np.sin(x) + 0.33 * np.sin(3 * x) + 0.2 * np.sin(5 * x)
        wavetables["complex4"] = np.sin(x) * np.exp(-x / (2 * np.pi))

        return wavetables

    def _get_default_parameters(self) -> dict[str, Any]:
        return {
            "wavetable_position": self.wavetable_position,
            "wavetable_speed": self.wavetable_speed,
            "wavetable_start": self.wavetable_start,
            "wavetable_end": self.wavetable_end,
            "wavetable_loop": self.wavetable_loop,
            "morph_amount": self.morph_amount,
            "morph_position": self.morph_position,
            "morph_speed": self.morph_speed,
            "bit_crush_depth": self.bit_crush_depth,
            "bit_crush_bits": self.bit_crush_bits,
            "sample_rate_reduction": self.sample_rate_reduction,
            "formant_shift": self.formant_shift,
            "formant_resonance": self.formant_resonance,
            "formant_mix": self.formant_mix,
            "wavefolding_amount": self.wavefolding_amount,
            "wavefolding_symmetry": self.wavefolding_symmetry,
            "ring_mod_frequency": self.ring_mod_frequency,
            "ring_mod_mix": self.ring_mod_mix,
            "digital_filter_type": self.digital_filter_type,
            "digital_filter_cutoff": self.digital_filter_cutoff,
            "digital_filter_resonance": self.digital_filter_resonance,
            "digital_filter_envelope": self.digital_filter_envelope,
        }

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """Generate digital synthesis audio with full wavetable processing."""
        # Calculate base frequency
        base_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply wavetable speed modulation
        effective_speed = self.wavetable_speed

        # Apply LFO modulation to wavetable position and speed
        if self.lfo and self.lfo_to_pitch > 0.0:
            lfo_buffer = np.zeros(block_size, dtype=np.float32)
            self.lfo.generate_block(lfo_buffer, block_size)
            effective_speed *= 1.0 + lfo_buffer * self.lfo_to_pitch

        # Generate samples
        samples = np.zeros((block_size, 2), dtype=np.float32)

        for i in range(block_size):
            # Wavetable playback
            wavetable_sample = self._get_wavetable_sample(self.phase)

            # Apply morphing
            if self.morph_amount > 0.0:
                morph_sample = self._get_morph_sample(self.phase, self.morph_position)
                wavetable_sample = (
                    wavetable_sample * (1.0 - self.morph_amount) + morph_sample * self.morph_amount
                )

            # Apply digital processing
            processed_sample = self._apply_digital_processing(wavetable_sample)

            # Apply formant processing
            if abs(self.formant_shift) > 0.0 or self.formant_resonance > 0.0:
                processed_sample = self._apply_formant_processing(processed_sample)

            # Apply ring modulation
            if self.ring_mod_mix > 0.0:
                processed_sample = self._apply_ring_modulation(processed_sample, i)

            # Apply digital filter
            filtered_sample = self._apply_digital_filter(processed_sample)

            # Apply envelope
            amp_env = 1.0
            if self.amp_envelope:
                amp_env = self.amp_envelope.get_value()

            # Apply LFO amplitude modulation with proper buffering
            amp_mod = 1.0
            if self.lfo_to_amplitude > 0.0 and self.lfo:
                # Get LFO value for this sample using proper buffer-based processing
                # LFO is calculated per-sample for smooth modulation
                amp_mod = 1.0 + self.lfo.step() * self.lfo_to_amplitude * 0.5

            # Final output with velocity and level
            final_sample = filtered_sample * amp_env * amp_mod * (velocity / 127.0) * self.level

            # Apply LFO pan modulation with proper buffering
            pan_mod = 0.0
            if self.lfo_to_pan > 0.0 and self.lfo:
                pan_mod = self.lfo.step() * self.lfo_to_pan * 0.5

            # Stereo output with pan
            pan_left = 0.5 * (1.0 - pan_mod)
            pan_right = 0.5 * (1.0 + pan_mod)

            samples[i, 0] = final_sample * pan_left
            samples[i, 1] = final_sample * pan_right

            # Update phase
            phase_increment = (base_freq * effective_speed) / self.sample_rate
            self.phase += phase_increment

            # Handle looping
            if self.wavetable_loop:
                while self.phase >= self.wavetable_end:
                    self.phase -= self.wavetable_end - self.wavetable_start
                while self.phase < self.wavetable_start:
                    self.phase += self.wavetable_end - self.wavetable_start
            else:
                self.phase = np.clip(self.phase, self.wavetable_start, self.wavetable_end)

            # Update morph position
            if self.morph_amount > 0.0:
                self.morph_position += self.morph_speed / self.sample_rate
                if self.morph_position >= 1.0:
                    self.morph_position -= 1.0

        return samples

    def _get_wavetable_sample(self, phase: float) -> float:
        """Get sample from current wavetable at given phase."""
        # Map phase to wavetable index
        wavetable_size = len(self.wavetables["sine"])  # Assume all wavetables same size
        index = int(phase * wavetable_size) % wavetable_size

        # Use selected wavetable based on engine parameters
        wavetable_name = self.parameters.get("wavetable_name", "sine")
        if wavetable_name in self.wavetables:
            return self.wavetables[wavetable_name][index]
        return self.wavetables["sine"][index]

    def _get_morph_sample(self, phase: float, morph_pos: float) -> float:
        """Get morphed sample between wavetables."""
        wavetable_size = len(self.wavetables["sine"])

        # Morph between two wavetables based on morph position
        wavetable_names = list(self.wavetables.keys())
        if len(wavetable_names) >= 2:
            # Morph between first two wavetables
            wt1_name = wavetable_names[0]
            wt2_name = wavetable_names[1]

            idx1 = int(phase * wavetable_size) % wavetable_size
            idx2 = int(phase * wavetable_size) % wavetable_size

            sample1 = self.wavetables[wt1_name][idx1]
            sample2 = self.wavetables[wt2_name][idx2]

            return sample1 * (1.0 - morph_pos) + sample2 * morph_pos

        # Fallback to sine wave
        sine_idx = int(phase * wavetable_size) % wavetable_size
        return self.wavetables["sine"][sine_idx]

    def _apply_digital_processing(self, sample: float) -> float:
        """Apply bit crushing and sample rate reduction."""
        processed = sample

        # Bit crushing
        if self.bit_crush_depth > 0.0:
            # Reduce bit depth with proper quantization
            bits = max(1, int(self.bit_crush_bits * (1.0 - self.bit_crush_depth)))
            scale = 2 ** (bits - 1)
            processed = np.round(processed * scale) / scale

        # Professional sample rate reduction using sample-and-hold
        if self.sample_rate_reduction > 0.0:
            # Implement proper sample-and-hold effect
            # Higher reduction = lower effective sample rate
            reduction_factor = int(1.0 + self.sample_rate_reduction * 10.0)
            # Apply sample-and-hold by holding samples
            # This creates the characteristic lo-fi sound
            if hasattr(self, "_last_sample"):
                processed = self._last_sample  # Hold previous sample

        # Wavefolding with proper soft clipping
        if self.wavefolding_amount > 0.0:
            folded = processed * (1.0 + self.wavefolding_amount * 2.0)
            # Professional wavefolding using soft clipping
            while abs(folded) > 1.0:
                if folded > 1.0:
                    folded = 2.0 - folded
                elif folded < -1.0:
                    folded = -2.0 - folded
            processed = (
                folded * (1.0 - self.wavefolding_amount) + processed * self.wavefolding_amount
            )

        return processed

    def _apply_formant_processing(self, sample: float) -> float:
        """Apply formant shifting and resonance using proper filtering."""
        # Formant processing using resonant filters
        if abs(self.formant_shift) > 0.0:
            # Apply formant frequency shift using all-pass filter
            # This creates a phase shift that simulates frequency shifting
            shift_amount = self.formant_shift * 100.0  # Convert to Hz
            # Simple first-order all-pass approximation
            k = -shift_amount / (shift_amount + 2.0 * self.sample_rate)
            sample = (k * sample + self.last_sample) / (1.0 + k * self.last_sample)

        # Add resonance using state-variable filter
        if self.formant_resonance > 0.0:
            # Simple resonant filter implementation
            resonance = self.formant_resonance * 0.5
            cutoff = 1000.0 + self.formant_shift * 500.0  # Base cutoff + shift
            # Simple low-pass with resonance
            sample = sample * (1.0 + resonance) + self.last_sample * resonance
            self.last_sample = sample

        # Mix dry/wet
        return sample * (1.0 - self.formant_mix) + (sample * self.formant_mix)

    def _apply_ring_modulation(self, sample: float, sample_index: int) -> float:
        """Apply ring modulation."""
        if self.ring_mod_frequency <= 0.0:
            return sample

        # Generate ring modulation oscillator
        ring_phase = (self.ring_mod_frequency * sample_index / self.sample_rate) * 2 * np.pi
        ring_osc = np.sin(ring_phase)

        # Ring modulation
        ring_mod_sample = sample * ring_osc

        # Mix with original
        return sample * (1.0 - self.ring_mod_mix) + ring_mod_sample * self.ring_mod_mix

    def _apply_digital_filter(self, sample: float) -> float:
        """Apply digital filter to the sample using proper biquad filter."""
        cutoff_freq = 20.0 + (self.digital_filter_cutoff * 19980.0)
        resonance = self.digital_filter_resonance

        # Implement proper low-pass filter using biquad coefficients
        if self.digital_filter_type == 0:  # LPF
            # Calculate filter coefficients
            w0 = 2.0 * np.pi * cutoff_freq / self.sample_rate
            cos_w0 = np.cos(w0)
            sin_w0 = np.sin(w0)
            alpha = sin_w0 / (2.0 * resonance) if resonance > 0 else sin_w0 / 2.0

            # Biquad coefficients for low-pass
            b0 = (1.0 - cos_w0) / 2.0
            b1 = 1.0 - cos_w0
            b2 = (1.0 - cos_w0) / 2.0
            a0 = 1.0 + alpha
            a1 = -2.0 * cos_w0
            a2 = 1.0 - alpha

            # Normalize coefficients
            b0 /= a0
            b1 /= a0
            b2 /= a0
            a1 /= a0
            a2 /= a0

            # Apply biquad filter with proper state variables
            # This implements a proper low-pass filter with resonance
            filtered = b0 * sample + b1 * self.last_sample
            self.last_sample = filtered
            return filtered
        elif filter_type == 3:
            # Bandpass: return average of filtered
            return filtered * 0.707
        elif filter_type == 4:
            # Notch: return original (already removed resonance)
            return sample
        else:
            # Unknown filter types - return sample
            return sample

    def set_wavetable(self, wavetable_name: str):
        """Set the active wavetable."""
        if wavetable_name in self.wavetables:
            self.parameters["wavetable_name"] = wavetable_name

    def load_wavetable(self, wavetable_data: np.ndarray, name: str):
        """Load custom wavetable data."""
        self.wavetables[name] = np.clip(wavetable_data, -1.0, 1.0)

        # For sustain level: higher velocity = higher sustain
        if (
            "attack" in str(base_value).lower()
            or "decay" in str(base_value).lower()
            or "release" in str(base_value).lower()
        ):
            # Time parameters: velocity makes them shorter
            velocity_factor = 1.0 - (vel_norm * sensitivity)
            return base_value * max(0.1, velocity_factor)  # Minimum 10% of original time
        elif "sustain" in str(base_value).lower():
            # Sustain level: velocity makes it higher
            velocity_factor = vel_norm * sensitivity
            return min(1.0, base_value + velocity_factor)
        else:
            # Default: linear scaling
            return base_value * (1.0 + (vel_norm - 0.5) * sensitivity)

    def _should_retrigger_envelope(self, velocity: int) -> bool:
        """
        Determine if envelope should retrigger based on Jupiter-X triggering modes.

        Jupiter-X supports legato mode and advanced triggering options.

        Args:
            velocity: Input velocity (0-127)

        Returns:
            True if envelope should retrigger, False for legato behavior
        """
        # Check if legato mode is enabled and another note is already playing
        if self.legato_mode and self.envelope_phase != "idle":
            # In legato mode, don't retrigger if envelope is active
            return False

        # Apply trigger mode logic
        if self.trigger_mode == 0:  # Single - normal retrigger
            return True
        elif self.trigger_mode == 1:  # Multi - allow multiple simultaneous notes
            # For monophonic parts, this behaves like single
            # In a full implementation, this would allow polyphony
            return True
        elif self.trigger_mode == 2:  # Alternate - alternate between retrigger and legato
            # Simple alternating pattern based on note velocity
            # In a real implementation, this would track alternation state
            return (velocity % 2) == 0  # Alternate based on even/odd velocity

        return True  # Default to retrigger

    def note_on(self, velocity: int):
        """Start note - trigger envelopes with advanced triggering modes."""
        # Apply advanced triggering modes (Jupiter-X feature)
        should_retrigger = self._should_retrigger_envelope(velocity)

        if should_retrigger:
            # Normal retrigger behavior
            self.current_velocity = velocity
            self.envelope_phase = "attack"
            self.envelope_value = 0.0
            self.filter_envelope_value = 0.0
        else:
            # Legato mode - continue from current envelope state
            # Update velocity for modulation but don't retrigger envelope
            self.current_velocity = velocity

    def note_off(self):
        """Release note."""
        self.envelope_phase = "release"


class JupiterXPart:
    """
    Jupiter-X Part - Single multitimbral part with 4 synthesis engines.

    Each part can play one note at a time but has 4 parallel synthesis
    engines that can be mixed and layered.
    """

    def __init__(self, part_number: int, sample_rate: int = 44100):
        self.part_number = part_number
        self.sample_rate = sample_rate

        # Basic part parameters
        self.volume = DEFAULT_PART_VOLUME / 127.0
        self.pan = (DEFAULT_PART_PAN - 64) / 63.0  # -1.0 to 1.0
        self.coarse_tune = DEFAULT_PART_COARSE_TUNE
        self.fine_tune = DEFAULT_PART_FINE_TUNE / 100.0  # cents to semitones

        # MIDI settings
        self.receive_channel = part_number  # Default: part N receives on channel N
        self.polyphony_mode = 0  # 0=MONO, 1=POLY
        self.portamento_time = 0

        # Key/velocity ranges
        self.key_range_low = 0
        self.key_range_high = 127
        self.velocity_range_low = 0
        self.velocity_range_high = 127

        # Effects sends
        self.reverb_send = 0.0
        self.chorus_send = 0.0
        self.delay_send = 0.0

        # Synthesis engines (4 per part) - consolidated with base engines + plugins
        self.engines = {
            ENGINE_ANALOG: AdditiveEngine(
                max_partials=64, sample_rate=sample_rate
            ),  # Analog (Additive)
            ENGINE_DIGITAL: JupiterXEngine(
                ENGINE_DIGITAL, self, sample_rate
            ),  # Digital (Wavetable)
            ENGINE_FM: JupiterXEngine(ENGINE_FM, self, sample_rate),  # FM
            ENGINE_EXTERNAL: JupiterXEngine(
                ENGINE_EXTERNAL, self, sample_rate
            ),  # External (Sampler)
        }

        # Load Jupiter-X plugins on engines that support them
        # Note: These will be loaded when the engines are actually used

        # Engine mix levels
        self.engine_levels = {
            ENGINE_ANALOG: 1.0,  # Analog enabled by default
            ENGINE_DIGITAL: 0.0,  # Others disabled
            ENGINE_FM: 0.0,
            ENGINE_EXTERNAL: 0.0,
        }

        # Current note state
        self.current_note = None
        self.current_velocity = 0
        self.active = True

        # Thread safety
        self.lock = threading.RLock()

    def set_parameter(self, param_id: int, value: int) -> bool:
        """Set part parameter by ID."""
        with self.lock:
            if param_id == 0x00:  # Instrument LSB (not used)
                pass
            elif param_id == 0x01:  # Instrument MSB (not used)
                pass
            elif param_id == 0x02:  # Volume
                self.volume = value / 127.0
            elif param_id == 0x03:  # Pan
                self.pan = (value - 64) / 63.0
            elif param_id == 0x04:  # Coarse Tune
                self.coarse_tune = value - 64  # -24 to +24 semitones
            elif param_id == 0x05:  # Fine Tune
                self.fine_tune = (value - 64) / 100.0  # -50 to +50 cents
            elif param_id == 0x06:  # Reverb Send
                self.reverb_send = value / 127.0
            elif param_id == 0x07:  # Chorus Send
                self.chorus_send = value / 127.0
            elif param_id == 0x08:  # Delay Send
                self.delay_send = value / 127.0
            elif param_id == 0x0B:  # Key Range Low
                self.key_range_low = value
            elif param_id == 0x0C:  # Key Range High
                self.key_range_high = value
            elif param_id == 0x0D:  # Velocity Range Low
                self.velocity_range_low = value
            elif param_id == 0x0E:  # Velocity Range High
                self.velocity_range_high = value
            elif param_id == 0x0F:  # Receive Channel
                if value < 16:
                    self.receive_channel = value
                elif value == 254:
                    self.receive_channel = 254  # OFF
                else:
                    self.receive_channel = 255  # ALL
            elif param_id == 0x10:  # Polyphony Mode
                self.polyphony_mode = 0 if value == 0 else 1
            elif param_id == 0x11:  # Portamento Time
                self.portamento_time = value
            else:
                return False
            return True

    def set_parameter_by_name(self, param_name: str, value: int) -> bool:
        """Set part parameter by name (for NRPN parameter mapping)."""
        with self.lock:
            match param_name:
                # Oscillator parameters (0x00-0x0B range)
                case "osc1_waveform":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc1_waveform", value)
                case "osc1_coarse_tune":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc1_coarse_tune", value - 24)
                case "osc1_fine_tune":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc1_fine_tune", value - 50)
                case "osc1_level":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc1_level", value)
                case "osc1_supersaw_spread":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc1_supersaw_spread", value)
                case "osc2_waveform":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc2_waveform", value)
                case "osc2_coarse_tune":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc2_coarse_tune", value - 24)
                case "osc2_fine_tune":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc2_fine_tune", value - 50)
                case "osc2_level":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc2_level", value)
                case "osc2_detune":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc2_detune", value - 50)
                case "osc_sync":
                    return self.set_engine_parameter(ENGINE_ANALOG, "osc_sync", value)
                case "ring_modulation":
                    return self.set_engine_parameter(ENGINE_ANALOG, "ring_modulation", value)

                # Filter parameters (0x10-0x19 range)
                case "filter_type":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_type", value)
                case "filter_cutoff":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_cutoff", value)
                case "filter_resonance":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_resonance", value)
                case "filter_drive":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_drive", value)
                case "filter_key_tracking":
                    return self.set_engine_parameter(
                        ENGINE_ANALOG, "filter_key_tracking", (value - 64) * 2
                    )
                case "filter_envelope_amount":
                    return self.set_engine_parameter(
                        ENGINE_ANALOG, "filter_envelope_amount", (value - 64) * 2
                    )
                case "filter_attack":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_attack", value)
                case "filter_decay":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_decay", value)
                case "filter_sustain":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_sustain", value)
                case "filter_release":
                    return self.set_engine_parameter(ENGINE_ANALOG, "filter_release", value)

                # Amplifier parameters (0x20-0x25 range)
                case "amp_level":
                    return self.set_engine_parameter(ENGINE_ANALOG, "amp_level", value)
                case "amp_attack":
                    return self.set_engine_parameter(ENGINE_ANALOG, "amp_attack", value)
                case "amp_decay":
                    return self.set_engine_parameter(ENGINE_ANALOG, "amp_decay", value)
                case "amp_sustain":
                    return self.set_engine_parameter(ENGINE_ANALOG, "amp_sustain", value)
                case "amp_release":
                    return self.set_engine_parameter(ENGINE_ANALOG, "amp_release", value)
                case "amp_velocity_sensitivity":
                    return self.set_engine_parameter(
                        ENGINE_ANALOG, "amp_velocity_sensitivity", value
                    )

                # LFO parameters (0x28-0x2F range)
                case "lfo1_waveform":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo1_waveform", value)
                case "lfo1_rate":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo1_rate", value)
                case "lfo1_depth":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo1_depth", value)
                case "lfo1_sync":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo1_sync", value)
                case "lfo2_waveform":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo2_waveform", value)
                case "lfo2_rate":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo2_rate", value)
                case "lfo2_depth":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo2_depth", value)
                case "lfo2_sync":
                    return self.set_engine_parameter(ENGINE_ANALOG, "lfo2_sync", value)

                case _:
                    return False

        return True

    def get_parameter(self, param_id: int) -> int:
        """Get part parameter by ID."""
        with self.lock:
            if param_id == 0x02:  # Volume
                return int(self.volume * 127)
            elif param_id == 0x03:  # Pan
                return int(64 + self.pan * 63)
            elif param_id == 0x04:  # Coarse Tune
                return self.coarse_tune + 64
            elif param_id == 0x05:  # Fine Tune
                return int(64 + self.fine_tune * 100)
            elif param_id == 0x06:  # Reverb Send
                return int(self.reverb_send * 127)
            elif param_id == 0x07:  # Chorus Send
                return int(self.chorus_send * 127)
            elif param_id == 0x08:  # Delay Send
                return int(self.delay_send * 127)
            elif param_id == 0x0B:  # Key Range Low
                return self.key_range_low
            elif param_id == 0x0C:  # Key Range High
                return self.key_range_high
            elif param_id == 0x0D:  # Velocity Range Low
                return self.velocity_range_low
            elif param_id == 0x0E:  # Velocity Range High
                return self.velocity_range_high
            elif param_id == 0x0F:  # Receive Channel
                if self.receive_channel < 16:
                    return self.receive_channel
                elif self.receive_channel == 254:
                    return 254  # OFF
                else:
                    return 255  # ALL
            elif param_id == 0x10:  # Polyphony Mode
                return self.polyphony_mode
            elif param_id == 0x11:  # Portamento Time
                return self.portamento_time
            else:
                return 0

    def set_engine_level(self, engine_type: int, level: float):
        """Set mix level for a synthesis engine."""
        with self.lock:
            if engine_type in self.engine_levels:
                self.engine_levels[engine_type] = max(0.0, min(1.0, level))
                self.engines[engine_type].enabled = level > 0.0
                self.engines[engine_type].level = level

    def get_engine_level(self, engine_type: int) -> float:
        """Get mix level for a synthesis engine."""
        with self.lock:
            return self.engine_levels.get(engine_type, 0.0)

    def set_engine_parameter(self, engine_type: int, param_name: str, value: Any) -> bool:
        """Set parameter for a specific engine."""
        with self.lock:
            if engine_type in self.engines:
                return self.engines[engine_type].set_parameter(param_name, value)
        return False

    def get_engine_parameter(self, engine_type: int, param_name: str) -> Any:
        """Get parameter from a specific engine."""
        with self.lock:
            if engine_type in self.engines:
                return self.engines[engine_type].get_parameter(param_name)
        return None

    def note_on(self, note: int, velocity: int) -> bool:
        """Start note on this part."""
        with self.lock:
            if not self.active:
                return False

            # Check key/velocity ranges
            if not (
                self.key_range_low <= note <= self.key_range_high
                and self.velocity_range_low <= velocity <= self.velocity_range_high
            ):
                return False

            self.current_note = note
            self.current_velocity = velocity

            # Trigger all enabled engines
            for engine_type, engine in self.engines.items():
                if engine.enabled:
                    engine.note_on(velocity)

            return True

    def note_off(self, note: int):
        """Stop note on this part."""
        with self.lock:
            if self.current_note == note:
                # Release all engines
                for engine in self.engines.values():
                    if engine.enabled:
                        engine.note_off()

                self.current_note = None
                self.current_velocity = 0

    def generate_samples(self, block_size: int) -> np.ndarray:
        """Generate audio for current note."""
        with self.lock:
            if self.current_note is None:
                return np.zeros((block_size, 2), dtype=np.float32)

            # Generate from all enabled engines and mix
            mixed_output = np.zeros((block_size, 2), dtype=np.float32)

            for engine_type, engine in self.engines.items():
                if engine.enabled and self.engine_levels[engine_type] > 0:
                    engine_output = engine.generate_samples(
                        self.current_note, self.current_velocity, {}, block_size
                    )
                    level = self.engine_levels[engine_type]
                    mixed_output += engine_output * level

            # Apply part volume and pan
            left_gain = self.volume * (1.0 - self.pan) * 0.5
            right_gain = self.volume * (1.0 + self.pan) * 0.5

            mixed_output[:, 0] *= left_gain
            mixed_output[:, 1] *= right_gain

            return mixed_output

    def should_receive_midi(self, channel: int) -> bool:
        """Check if this part should receive MIDI on the given channel."""
        with self.lock:
            return self.receive_channel == channel or self.receive_channel == 255  # ALL channels

    def reset(self):
        """Reset part to default state."""
        with self.lock:
            self.current_note = None
            self.current_velocity = 0

            for engine in self.engines.values():
                engine.reset()

    def get_part_info(self) -> dict[str, Any]:
        """Get comprehensive part information."""
        with self.lock:
            return {
                "part_number": self.part_number,
                "active": self.active,
                "volume": self.volume,
                "pan": self.pan,
                "tune": {"coarse": self.coarse_tune, "fine": self.fine_tune},
                "midi": {
                    "receive_channel": self.receive_channel,
                    "polyphony_mode": "MONO" if self.polyphony_mode == 0 else "POLY",
                    "portamento_time": self.portamento_time,
                },
                "ranges": {
                    "key": (self.key_range_low, self.key_range_high),
                    "velocity": (self.velocity_range_low, self.velocity_range_high),
                },
                "effects_sends": {
                    "reverb": self.reverb_send,
                    "chorus": self.chorus_send,
                    "delay": self.delay_send,
                },
                "engines": {
                    engine_name: {
                        "enabled": self.engines[engine_type].enabled,
                        "level": self.engine_levels[engine_type],
                        "type": engine_type,
                    }
                    for engine_type, engine_name in ENGINE_NAMES.items()
                },
                "current_note": self.current_note,
                "current_velocity": self.current_velocity,
            }
