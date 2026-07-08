"""XG Insertion Effects Processor - orchestrator."""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np

from ..distortion import DynamicEQEnhancer, ProfessionalCompressor, TubeSaturationProcessor
from ..pitch_effects import ProductionPitchEffectsProcessor
from ..spatial_enhanced import EnhancedEarlyReflections
from .envelope_filter import ProductionEnvelopeFilter
from .flanger import ProductionFlangerProcessor
from .phaser import ProductionPhaserProcessor
from .rotary_speaker import ProfessionalRotarySpeaker
from .vocoder import CarrierVocoder


class ProductionXGInsertionEffectsProcessor:
    """
    XG Insertion Effects Processor - Production Implementation

    Handles all insertion effects (types 0-17) with XG-compliant parameters
    and presets. Each effect type has proper XG parameter mappings.
    """

    # XG Insertion Effect Parameter Definitions
    XG_INSERTION_PARAMS = {
        0: {  # Distortion
            "drive": {"range": (0, 127), "default": 64, "name": "Drive"},
            "tone": {"range": (0, 127), "default": 64, "name": "Tone"},
            "level": {"range": (0, 127), "default": 100, "name": "Level"},
        },
        1: {  # Overdrive
            "drive": {"range": (0, 127), "default": 80, "name": "Drive"},
            "tone": {"range": (0, 127), "default": 50, "name": "Tone"},
            "level": {"range": (0, 127), "default": 90, "name": "Level"},
        },
        2: {  # Compressor
            "threshold": {"range": (-60, 0), "default": -20, "name": "Threshold"},
            "ratio": {"range": (1, 20), "default": 4, "name": "Ratio"},
            "attack": {"range": (0, 100), "default": 5, "name": "Attack"},
            "release": {"range": (10, 500), "default": 100, "name": "Release"},
        },
        3: {  # Noise Gate
            "threshold": {"range": (-80, 0), "default": -40, "name": "Threshold"},
            "ratio": {"range": (0.1, 1), "default": 0.3, "name": "Ratio"},
            "attack": {"range": (0, 50), "default": 1, "name": "Attack"},
            "release": {"range": (10, 200), "default": 50, "name": "Release"},
        },
        4: {  # Envelope Filter
            "sensitivity": {"range": (0, 127), "default": 64, "name": "Sensitivity"},
            "resonance": {"range": (0.1, 10), "default": 2.0, "name": "Resonance"},
            "frequency": {"range": (200, 5000), "default": 1000, "name": "Frequency"},
        },
        5: {  # Vocoder
            "bandwidth": {"range": (0.1, 2.0), "default": 0.5, "name": "Bandwidth"},
            "sensitivity": {"range": (0, 127), "default": 80, "name": "Sensitivity"},
            "dry_wet": {"range": (0, 127), "default": 64, "name": "Dry/Wet"},
        },
        6: {  # Amp Simulator
            "drive": {"range": (0, 127), "default": 100, "name": "Drive"},
            "tone": {"range": (0, 127), "default": 30, "name": "Tone"},
            "level": {"range": (0, 127), "default": 85, "name": "Level"},
        },
        7: {  # Rotary Speaker
            "speed": {"range": (0, 127), "default": 64, "name": "Speed"},
            "depth": {"range": (0, 127), "default": 100, "name": "Depth"},
            "crossover": {"range": (200, 2000), "default": 800, "name": "Crossover"},
            "dry_wet": {"range": (0, 127), "default": 64, "name": "Dry/Wet"},
        },
        8: {  # Leslie
            "speed": {"range": (0, 127), "default": 50, "name": "Speed"},
            "depth": {"range": (0, 127), "default": 90, "name": "Depth"},
            "reverb": {"range": (0, 127), "default": 30, "name": "Reverb"},
        },
        9: {  # Enhancer
            "enhance": {"range": (0, 127), "default": 64, "name": "Enhance"},
            "frequency": {"range": (1000, 10000), "default": 5000, "name": "Frequency"},
            "width": {"range": (0.1, 2.0), "default": 1.0, "name": "Width"},
        },
        10: {  # Auto Wah
            "rate": {"range": (0.1, 10), "default": 2.0, "name": "Rate"},
            "depth": {"range": (0, 127), "default": 80, "name": "Depth"},
            "resonance": {"range": (0.5, 10), "default": 3.0, "name": "Resonance"},
        },
        11: {  # Talk Wah
            "sensitivity": {"range": (0, 127), "default": 90, "name": "Sensitivity"},
            "resonance": {"range": (0.5, 10), "default": 4.0, "name": "Resonance"},
            "decay": {"range": (0.01, 1.0), "default": 0.1, "name": "Decay"},
        },
        12: {  # Harmonizer
            "interval": {"range": (-24, 24), "default": 7, "name": "Interval"},
            "mix": {"range": (0, 127), "default": 60, "name": "Mix"},
            "detune": {"range": (-50, 50), "default": 0, "name": "Detune"},
        },
        13: {  # Octave
            "octave": {"range": (-3, 3), "default": -1, "name": "Octave"},
            "mix": {"range": (0, 127), "default": 60, "name": "Mix"},
            "dry_wet": {"range": (0, 127), "default": 80, "name": "Dry/Wet"},
        },
        14: {  # Detune
            "detune": {"range": (-100, 100), "default": 10, "name": "Detune"},
            "mix": {"range": (0, 127), "default": 50, "name": "Mix"},
            "delay": {"range": (0, 50), "default": 5, "name": "Delay"},
        },
        15: {  # Phaser
            "rate": {"range": (0.1, 10), "default": 1.0, "name": "Rate"},
            "depth": {"range": (0, 127), "default": 64, "name": "Depth"},
            "feedback": {"range": (-0.9, 0.9), "default": 0.3, "name": "Feedback"},
            "dry_wet": {"range": (0.0, 1.0), "default": 0.5, "name": "Dry/Wet"},
        },
        16: {  # Flanger
            "rate": {"range": (0.05, 5.0), "default": 0.5, "name": "Rate"},
            "depth": {"range": (0, 127), "default": 90, "name": "Depth"},
            "feedback": {"range": (-0.9, 0.9), "default": 0.5, "name": "Feedback"},
            "delay": {"range": (0.1, 10), "default": 2.0, "name": "Delay"},
            "dry_wet": {"range": (0, 127), "default": 64, "name": "Dry/Wet"},
        },
        17: {  # Wah Wah
            "sensitivity": {"range": (0, 127), "default": 115, "name": "Sensitivity"},
            "resonance": {"range": (0.5, 10), "default": 5.0, "name": "Resonance"},
            "frequency": {"range": (200, 2000), "default": 500, "name": "Frequency"},
        },
    }

    def __init__(self, sample_rate: int, max_delay_samples: int = 8192):
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Initialize production processors (reusing from variation effects)
        self.tube_saturation = TubeSaturationProcessor(sample_rate)
        self.compressor = ProfessionalCompressor(sample_rate)
        self.phaser = ProductionPhaserProcessor(sample_rate)
        self.flanger = ProductionFlangerProcessor(sample_rate, max_delay_samples)
        self.rotary = ProfessionalRotarySpeaker(sample_rate)
        self.envelope_filter = ProductionEnvelopeFilter(sample_rate)
        self.vocoder = CarrierVocoder(sample_rate)
        self.enhancer = DynamicEQEnhancer(sample_rate, freq=5000.0, peaking=True)

        # Pitch effects from variation effects
        self.pitch_processor = ProductionPitchEffectsProcessor(sample_rate, max_delay_samples)

        # Early reflections for Leslie effect
        self.early_reflections = EnhancedEarlyReflections(sample_rate)

        # Pre-allocated work buffers (avoid allocation in audio path)
        self._pitch_stereo_buffer: np.ndarray | None = None
        self._leslie_temp: np.ndarray | None = None

        # Current insertion effects configuration
        self.insertion_types: list[int] = [0, 0, 0]  # Effect types for slots 0-2
        self.insertion_bypass: list[bool] = [True, True, True]  # Bypass flags

        # XG parameter storage per slot
        self.slot_parameters: list[dict[str, float]] = [
            {},
            {},
            {},  # One dict per slot
        ]

        # Initialize default parameters for each slot
        for slot in range(3):
            self._initialize_slot_defaults(slot)

        self.lock = threading.RLock()

    def _initialize_slot_defaults(self, slot: int) -> None:
        """Initialize default XG parameters for a slot."""
        effect_type = self.insertion_types[slot]
        if effect_type in self.XG_INSERTION_PARAMS:
            params = self.XG_INSERTION_PARAMS[effect_type]
            self.slot_parameters[slot] = {
                param_name: param_def["default"] for param_name, param_def in params.items()
            }
        else:
            self.slot_parameters[slot] = {}

    def get_xg_parameter_info(self, effect_type: int) -> dict[str, dict]:
        """Get XG parameter information for an effect type."""
        return self.XG_INSERTION_PARAMS.get(effect_type, {})

    def set_xg_parameter(self, slot: int, param_name: str, value: float) -> bool:
        """Set an XG parameter for a specific slot."""
        with self.lock:
            if not (0 <= slot < 3):
                return False

            effect_type = self.insertion_types[slot]
            if effect_type not in self.XG_INSERTION_PARAMS:
                return False

            param_info = self.XG_INSERTION_PARAMS[effect_type].get(param_name)
            if not param_info:
                return False

            # Validate range
            min_val, max_val = param_info["range"]
            clamped_value = max(min_val, min(max_val, value))

            self.slot_parameters[slot][param_name] = clamped_value
            return True

    def get_xg_parameter(self, slot: int, param_name: str) -> float | None:
        """Get an XG parameter value for a specific slot."""
        with self.lock:
            if 0 <= slot < 3:
                return self.slot_parameters[slot].get(param_name)
            return None

    def set_insertion_effect_type(self, slot: int, effect_type: int) -> bool:
        """Set the effect type for an insertion slot."""
        with self.lock:
            if 0 <= slot < 3 and 0 <= effect_type <= 17:
                self.insertion_types[slot] = effect_type
                return True
            return False

    def set_insertion_effect_bypass(self, slot: int, bypass: bool) -> bool:
        """Set bypass for an insertion slot."""
        with self.lock:
            if 0 <= slot < 3:
                self.insertion_bypass[slot] = bypass
                return True
            return False

    def set_effect_parameter(self, effect_type: int, param: str, value: float) -> bool:
        """Set a parameter for an effect type."""
        # This would route parameters to individual processors
        # For simplicity, we'll handle this in the process method
        return True

    def apply_insertion_effect_to_channel_zero_alloc(
        self,
        target_buffer: np.ndarray,
        channel_array: np.ndarray,
        insertion_params: dict[str, Any],
        num_samples: int,
        channel_idx: int,
        modulation_buffer: np.ndarray | None = None,
    ) -> None:
        """Apply complete insertion effects chain to a channel buffer."""
        with self.lock:
            # Copy input to target buffer first
            if channel_array.ndim == 2:
                np.copyto(target_buffer[:num_samples], channel_array[:num_samples])
            else:
                # Mono to stereo
                target_buffer[:num_samples, 0] = channel_array[:num_samples]
                target_buffer[:num_samples, 1] = channel_array[:num_samples]

            # Apply insertion effects chain in order
            for slot in range(3):
                if slot >= len(self.insertion_types) or self.insertion_bypass[slot]:
                    continue

                effect_type = self.insertion_types[slot]

                # Process both channels through the effect
                for ch in range(2):
                    channel_samples = target_buffer[:num_samples, ch]
                    self._apply_single_effect_to_samples(
                        channel_samples,
                        num_samples,
                        effect_type,
                        insertion_params,
                        slot,
                        modulation_buffer,
                    )

            # Convert back to mono if input was mono
            if channel_array.ndim == 1:
                mono_output = (
                    target_buffer[:num_samples, 0] + target_buffer[:num_samples, 1]
                ) * 0.5
                target_buffer[:num_samples, 0] = mono_output
                target_buffer[:num_samples, 1] = mono_output

    def _apply_single_effect_to_samples(
        self,
        samples: np.ndarray,
        num_samples: int,
        effect_type: int,
        params: dict[str, float],
        slot: int = 0,
        modulation_buffer: np.ndarray | None = None,
    ) -> np.ndarray:
        """Apply a single insertion effect to mono samples using XG parameters."""

        # Get XG parameters for this effect slot
        slot_params = self.slot_parameters[slot]

        # Route to appropriate processor based on XG insertion type
        if effect_type == 0:  # Distortion
            drive = slot_params.get("drive", 64) / 127.0
            tone = slot_params.get("tone", 64) / 127.0
            level = slot_params.get("level", 100) / 127.0

            for i in range(num_samples):
                samples[i] = self.tube_saturation.process_sample(
                    samples[i], drive * 3.0, tone, level
                )

        elif effect_type == 1:  # Overdrive
            drive = slot_params.get("drive", 80) / 127.0
            tone = slot_params.get("tone", 50) / 127.0
            level = slot_params.get("level", 90) / 127.0

            for i in range(num_samples):
                samples[i] = self.tube_saturation.process_sample(
                    samples[i], drive * 2.5, tone, level
                )

        elif effect_type == 2:  # Compressor
            threshold = slot_params.get("threshold", -20.0)
            ratio = slot_params.get("ratio", 4.0)
            attack = slot_params.get("attack", 5.0) / 1000.0
            release = slot_params.get("release", 100.0) / 1000.0

            self.compressor.set_parameters(threshold, ratio, attack, release)
            for i in range(num_samples):
                samples[i] = self.compressor.process_sample(samples[i])

        elif effect_type == 3:  # Noise Gate
            threshold = slot_params.get("threshold", -40.0)
            ratio = slot_params.get("ratio", 0.3)
            attack = slot_params.get("attack", 1.0) / 1000.0
            release = slot_params.get("release", 50.0) / 1000.0

            self.compressor.set_parameters(threshold, 1.0 / ratio, attack, release)
            for i in range(num_samples):
                samples[i] = self.compressor.process_sample(samples[i])

        elif effect_type == 4:  # Envelope Filter
            sensitivity = slot_params.get("sensitivity", 64) / 127.0
            resonance = slot_params.get("resonance", 2.0)
            frequency = slot_params.get("frequency", 1000)

            # Update envelope filter frequency range
            self.envelope_filter.freq_range = (frequency * 0.1, frequency * 2.0)

            filter_params = {"sensitivity": sensitivity, "resonance": resonance}
            self.envelope_filter.process_block(samples[:num_samples], filter_params)

        elif effect_type == 5:  # Vocoder
            bandwidth = slot_params.get("bandwidth", 0.5)
            sensitivity = slot_params.get("sensitivity", 80) / 127.0
            dry_wet = slot_params.get("dry_wet", 64) / 127.0

            if modulation_buffer is not None:
                # Full multiband vocoder with external modulation
                self.vocoder.set_attack_release(10.0, 50.0 * (1.0 + bandwidth))
                for i in range(num_samples):
                    mod = (
                        modulation_buffer[i]
                        if modulation_buffer.ndim == 1
                        else modulation_buffer[i, 0]
                    )
                    wet = self.vocoder.process_sample(mod, samples[i])
                    samples[i] = samples[i] * (1.0 - dry_wet) + wet * dry_wet
            else:
                # Same-signal vocoder: multiband spectral shaping
                self.vocoder.set_attack_release(10.0, 50.0 * (1.0 + bandwidth))
                for i in range(num_samples):
                    wet = self.vocoder.process_sample(samples[i], samples[i])
                    # Scale by sensitivity
                    mixed = samples[i] * (1.0 - sensitivity * dry_wet) + wet * sensitivity * dry_wet
                    samples[i] = mixed

        elif effect_type == 6:  # Amp Simulator
            drive = slot_params.get("drive", 100) / 127.0
            tone = slot_params.get("tone", 30) / 127.0
            level = slot_params.get("level", 85) / 127.0

            for i in range(num_samples):
                samples[i] = self.tube_saturation.process_sample(
                    samples[i], drive * 4.0, tone, level
                )

        elif effect_type == 7:  # Rotary Speaker
            speed = slot_params.get("speed", 64) / 127.0
            depth = slot_params.get("depth", 100) / 127.0
            crossover = slot_params.get("crossover", 800)
            dry_wet = slot_params.get("dry_wet", 64) / 127.0

            # Update rotary crossover
            self.rotary.crossover_freq = crossover

            rotary_params = {"speed": speed, "depth": depth, "dry_wet": dry_wet}
            self.rotary.process_block(samples[:num_samples], rotary_params)

        elif effect_type == 8:  # Leslie
            speed = slot_params.get("speed", 50) / 127.0
            depth = slot_params.get("depth", 90) / 127.0
            reverb_amount = slot_params.get("reverb", 30) / 127.0
            dry_wet = slot_params.get("dry_wet", 64) / 127.0

            if self._leslie_temp is None or len(self._leslie_temp) < num_samples:
                self._leslie_temp = np.zeros(num_samples, dtype=np.float32)
            temp = self._leslie_temp[:num_samples]

            rotary_params = {"speed": speed, "depth": depth, "dry_wet": dry_wet}
            self.rotary.process_block(temp[:num_samples], rotary_params)

            # Add reverb
            self.early_reflections.configure_room("studio_light", reverb_amount)
            for i in range(num_samples):
                temp[i] += self.early_reflections.process_sample(temp[i])

            samples[:num_samples] = temp[:num_samples]

        elif effect_type == 9:  # Enhancer
            enhance = slot_params.get("enhance", 64) / 127.0
            frequency = slot_params.get("frequency", 5000)
            width = slot_params.get("width", 1.0)

            self.enhancer.center_freq = frequency
            for i in range(num_samples):
                samples[i] = self.enhancer.process_sample(samples[i], enhance * width)

        elif effect_type == 10:  # Auto Wah
            rate = slot_params.get("rate", 2.0)
            depth = slot_params.get("depth", 80) / 127.0
            resonance = slot_params.get("resonance", 3.0)

            # Auto Wah: LFO-driven sensitivity
            if not hasattr(self, "_autowah_phase"):
                self._autowah_phase = 0.0

            for i in range(num_samples):
                phase_inc = 2 * math.pi * rate / self.sample_rate
                self._autowah_phase = (self._autowah_phase + phase_inc) % (2 * math.pi)
                lfo = (math.sin(self._autowah_phase) + 1.0) * 0.5  # 0 to 1

                # LFO-driven sensitivity
                filter_params = {"sensitivity": lfo * depth, "resonance": resonance}
                samples[i] = self.envelope_filter.process_sample(samples[i], filter_params)

        elif effect_type == 11:  # Talk Wah
            sensitivity = slot_params.get("sensitivity", 90) / 127.0
            resonance = slot_params.get("resonance", 4.0)
            decay = slot_params.get("decay", 0.1)

            if not hasattr(self, "_talkwah_envelope"):
                self._talkwah_envelope = 0.0

            for i in range(num_samples):
                # Envelope follower with decay
                abs_input = abs(samples[i])
                if abs_input > self._talkwah_envelope:
                    self._talkwah_envelope = abs_input  # Instant attack
                else:
                    self._talkwah_envelope += decay * (abs_input - self._talkwah_envelope)  # Decay

                # Talk wah: formant-like bandpass with envelope-driven frequency
                # Vowel formants typically around 500-3000 Hz
                formant_freq = 500.0 + self._talkwah_envelope * sensitivity * 2500.0
                self.envelope_filter.freq_range = (formant_freq * 0.6, formant_freq * 2.0)
                filter_params = {"sensitivity": 1.0, "resonance": resonance}
                samples[i] = self.envelope_filter.process_sample(samples[i], filter_params)

        elif effect_type == 12:  # Harmonizer
            interval = slot_params.get("interval", 7)
            mix = slot_params.get("mix", 60) / 127.0
            detune = slot_params.get("detune", 0)

            # Use pitch processor for harmonizer
            harmonizer_params = {
                "parameter1": interval,  # Interval in semitones
                "parameter2": mix,  # Mix level
                "parameter3": detune,  # Fine detune
            }
            if (
                self._pitch_stereo_buffer is None
                or self._pitch_stereo_buffer.shape[0] < num_samples
            ):
                self._pitch_stereo_buffer = np.zeros((num_samples, 2), dtype=np.float32)
            buf = self._pitch_stereo_buffer[:num_samples]
            buf[:, 0] = samples[:num_samples]
            buf[:, 1] = samples[:num_samples]
            self.pitch_processor.process_effect(64, buf, num_samples, harmonizer_params)
            samples[:num_samples] = buf[:, 0]

        elif effect_type == 13:  # Octave
            octave = slot_params.get("octave", -1)
            mix = slot_params.get("mix", 60) / 127.0
            dry_wet = slot_params.get("dry_wet", 80) / 127.0

            # Use pitch processor for octave
            octave_params = {
                "parameter1": octave * 12,  # Convert octaves to semitones
                "parameter2": mix,
                "parameter3": dry_wet,
            }
            if (
                self._pitch_stereo_buffer is None
                or self._pitch_stereo_buffer.shape[0] < num_samples
            ):
                self._pitch_stereo_buffer = np.zeros((num_samples, 2), dtype=np.float32)
            buf = self._pitch_stereo_buffer[:num_samples]
            buf[:, 0] = samples[:num_samples]
            buf[:, 1] = samples[:num_samples]
            self.pitch_processor.process_effect(60, buf, num_samples, octave_params)
            samples[:num_samples] = buf[:, 0]

        elif effect_type == 14:  # Detune
            detune = slot_params.get("detune", 10)
            mix = slot_params.get("mix", 50) / 127.0
            delay = slot_params.get("delay", 5)

            # Use pitch processor for detune
            detune_params = {"parameter1": detune, "parameter2": mix, "parameter3": delay}
            if (
                self._pitch_stereo_buffer is None
                or self._pitch_stereo_buffer.shape[0] < num_samples
            ):
                self._pitch_stereo_buffer = np.zeros((num_samples, 2), dtype=np.float32)
            buf = self._pitch_stereo_buffer[:num_samples]
            buf[:, 0] = samples[:num_samples]
            buf[:, 1] = samples[:num_samples]
            self.pitch_processor.process_effect(65, buf, num_samples, detune_params)
            samples[:num_samples] = buf[:, 0]

        elif effect_type == 15:  # Phaser
            rate = slot_params.get("rate", 1.0)
            depth = slot_params.get("depth", 64) / 127.0
            feedback = slot_params.get("feedback", 0.3)
            dry_wet = slot_params.get("dry_wet", 0.5)

            phaser_params = {
                "rate": rate,
                "depth": depth,
                "feedback": feedback,
                "dry_wet": dry_wet,
            }
            self.phaser.process_block(samples[:num_samples], phaser_params)

        elif effect_type == 16:  # Flanger
            rate = slot_params.get("rate", 0.5)
            depth = slot_params.get("depth", 90) / 127.0
            feedback = slot_params.get("feedback", 0.5)
            delay_ms = slot_params.get("delay", 2.0)
            delay_samples = int(delay_ms * self.sample_rate / 1000.0)

            # Update flanger delay range
            self.flanger.min_delay = max(1, delay_samples - 1000)
            self.flanger.max_delay = delay_samples + 1000

            dry_wet = slot_params.get("dry_wet", 64) / 127.0
            hf_damping = slot_params.get("hf_damping", 64) * 0.99 / 127.0

            flanger_params = {
                "rate": rate,
                "depth": depth,
                "feedback": feedback,
                "dry_wet": dry_wet,
                "hf_damping": hf_damping,
            }
            self.flanger.process_block(samples[:num_samples], flanger_params)

        elif effect_type == 17:  # Wah Wah
            sensitivity = slot_params.get("sensitivity", 115) / 127.0
            resonance = slot_params.get("resonance", 5.0)
            frequency = slot_params.get("frequency", 500)

            # Update envelope filter for wah characteristics
            self.envelope_filter.freq_range = (frequency * 0.3, frequency * 3.0)

            filter_params = {"sensitivity": sensitivity, "resonance": resonance}
            self.envelope_filter.process_block(samples[:num_samples], filter_params)

        return samples

    def get_supported_types(self) -> list:
        """Get list of supported effect types."""
        return list(range(18))  # Types 0-17

    def reset(self) -> None:
        """Reset all effect states."""
        with self.lock:
            self.phaser.reset()
            self.envelope_filter.x1 = self.envelope_filter.x2 = 0.0
            self.envelope_filter.y1 = self.envelope_filter.y2 = 0.0
            self.enhancer.x1 = self.enhancer.x2 = 0.0
            self.enhancer.y1 = self.enhancer.y2 = 0.0
            self.enhancer.envelope.reset()
            self.flanger.delay_line.fill(0.0)
            self.flanger.write_pos = 0
            self.flanger.fb_lowpass_state = 0.0
            self.rotary.horn_delay.fill(0.0)
            self.rotary.rotor_delay.fill(0.0)
            self.rotary.horn_write = 0
            self.rotary.rotor_write = 0
            self.rotary._svf_lp = 0.0
            self.rotary._svf_bp = 0.0
            self.pitch_processor.reset()
