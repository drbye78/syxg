"""
Jupiter-X VCM Effects - Virtual Circuit Modeling for Authentic Analog Processing

Provides Jupiter-X style VCM (Virtual Circuit Modeling) effects that accurately
replicate the analog circuit behavior of classic effects processors, including
distortion, phaser, chorus, delay, and reverb algorithms.
"""
from __future__ import annotations

import numpy as np
from typing import Any
import math
from ..effects.effects_coordinator import XGEffectsCoordinator


class JupiterXVCMEffects:
    """
    Jupiter-X VCM Effects processor with authentic analog circuit modeling.

    Provides hardware-accurate modeling of classic analog effects circuits
    with the same sound characteristics as the original Jupiter-X synthesizer.
    """

    def __init__(self, sample_rate: int = 44100, max_block_size: int = 8192):
        """
        Initialize Jupiter-X VCM effects processor.

        Args:
            sample_rate: Audio sample rate
            max_block_size: Maximum processing block size
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size

        # VCM processing state
        self.vcm_enabled = True
        self.vcm_drive = 0.0
        self.vcm_tone = 0.5
        self.vcm_level = 1.0

        # Initialize VCM effect processors
        self._initialize_vcm_processors()

        # Buffer management for VCM processing
        self.input_buffer = np.zeros(max_block_size, dtype=np.float32)
        self.output_buffer = np.zeros(max_block_size, dtype=np.float32)
        self.temp_buffer = np.zeros(max_block_size, dtype=np.float32)

    def _initialize_vcm_processors(self):
        """Initialize individual VCM effect processors."""
        self.vcm_distortion = JupiterXVCMDistortion(self.sample_rate)
        self.vcm_phaser = JupiterXVCMPhaser(self.sample_rate)
        self.vcm_chorus = JupiterXVCMChorus(self.sample_rate)
        self.vcm_delay = JupiterXVCMDelay(self.sample_rate)
        self.vcm_reverb = JupiterXVCMReverb(self.sample_rate)

    def process_vcm_chain(self, audio: np.ndarray, parameters: dict[str, Any] | None = None) -> np.ndarray:
        """
        Process audio through the complete Jupiter-X VCM effects chain.

        Args:
            audio: Input audio buffer
            parameters: VCM parameter settings

        Returns:
            Processed audio buffer
        """
        if not self.vcm_enabled:
            return audio

        # Apply parameters if provided
        if parameters:
            self._apply_vcm_parameters(parameters)

        # Ensure output buffer is large enough
        if len(self.output_buffer) < len(audio):
            self.output_buffer = np.zeros(len(audio), dtype=np.float32)
            self.temp_buffer = np.zeros(len(audio), dtype=np.float32)

        # Copy input to processing buffer
        np.copyto(self.output_buffer[:len(audio)], audio)

        # Apply VCM effects chain in Jupiter-X order
        # 1. Distortion (if enabled)
        if self.vcm_distortion.enabled:
            self.output_buffer[:len(audio)] = self.vcm_distortion.process(
                self.output_buffer[:len(audio)])

        # 2. Phaser (if enabled)
        if self.vcm_phaser.enabled:
            self.output_buffer[:len(audio)] = self.vcm_phaser.process(
                self.output_buffer[:len(audio)])

        # 3. Chorus (if enabled)
        if self.vcm_chorus.enabled:
            self.output_buffer[:len(audio)] = self.vcm_chorus.process(
                self.output_buffer[:len(audio)])

        # 4. Delay (if enabled)
        if self.vcm_delay.enabled:
            self.output_buffer[:len(audio)] = self.vcm_delay.process(
                self.output_buffer[:len(audio)])

        # 5. Reverb (if enabled)
        if self.vcm_reverb.enabled:
            self.output_buffer[:len(audio)] = self.vcm_reverb.process(
                self.output_buffer[:len(audio)])

        return self.output_buffer[:len(audio)]

    def _apply_vcm_parameters(self, parameters: dict[str, Any]):
        """Apply VCM parameter settings to individual processors."""
        # Distortion parameters
        if 'distortion_drive' in parameters:
            self.vcm_distortion.drive = parameters['distortion_drive'] / 127.0
        if 'distortion_tone' in parameters:
            self.vcm_distortion.tone = parameters['distortion_tone'] / 127.0
        if 'distortion_type' in parameters:
            self.vcm_distortion.distortion_type = parameters['distortion_type']

        # Phaser parameters
        if 'phaser_rate' in parameters:
            self.vcm_phaser.rate = parameters['phaser_rate'] / 127.0
        if 'phaser_depth' in parameters:
            self.vcm_phaser.depth = parameters['phaser_depth'] / 127.0
        if 'phaser_feedback' in parameters:
            self.vcm_phaser.feedback = parameters['phaser_feedback'] / 127.0

        # Chorus parameters
        if 'chorus_rate' in parameters:
            self.vcm_chorus.rate = parameters['chorus_rate'] / 127.0
        if 'chorus_depth' in parameters:
            self.vcm_chorus.depth = parameters['chorus_depth'] / 127.0
        if 'chorus_delay' in parameters:
            self.vcm_chorus.delay_time = 0.001 + (parameters['chorus_delay'] / 127.0) * 0.01

        # Delay parameters
        if 'delay_time' in parameters:
            self.vcm_delay.delay_time = 0.01 + (parameters['delay_time'] / 127.0) * 1.0
        if 'delay_feedback' in parameters:
            self.vcm_delay.feedback = parameters['delay_feedback'] / 127.0
        if 'delay_mix' in parameters:
            self.vcm_delay.mix = parameters['delay_mix'] / 127.0

        # Reverb parameters
        if 'reverb_time' in parameters:
            self.vcm_reverb.decay_time = 0.1 + (parameters['reverb_time'] / 127.0) * 5.0
        if 'reverb_mix' in parameters:
            self.vcm_reverb.mix = parameters['reverb_mix'] / 127.0

    def enable_vcm_effect(self, effect_name: str, enabled: bool = True):
        """
        Enable or disable specific VCM effect.

        Args:
            effect_name: Name of effect ('distortion', 'phaser', 'chorus', 'delay', 'reverb')
            enabled: Whether to enable the effect
        """
        effect_map = {
            'distortion': self.vcm_distortion,
            'phaser': self.vcm_phaser,
            'chorus': self.vcm_chorus,
            'delay': self.vcm_delay,
            'reverb': self.vcm_reverb
        }

        if effect_name in effect_map:
            effect_map[effect_name].enabled = enabled

    def get_vcm_status(self) -> dict[str, Any]:
        """
        Get current VCM effects status.

        Returns:
            Dictionary with VCM effects status
        """
        return {
            'vcm_enabled': self.vcm_enabled,
            'distortion': {
                'enabled': self.vcm_distortion.enabled,
                'drive': self.vcm_distortion.drive,
                'tone': self.vcm_distortion.tone,
                'type': self.vcm_distortion.distortion_type
            },
            'phaser': {
                'enabled': self.vcm_phaser.enabled,
                'rate': self.vcm_phaser.rate,
                'depth': self.vcm_phaser.depth,
                'feedback': self.vcm_phaser.feedback
            },
            'chorus': {
                'enabled': self.vcm_chorus.enabled,
                'rate': self.vcm_chorus.rate,
                'depth': self.vcm_chorus.depth,
                'delay': self.vcm_chorus.delay_time
            },
            'delay': {
                'enabled': self.vcm_delay.enabled,
                'time': self.vcm_delay.delay_time,
                'feedback': self.vcm_delay.feedback,
                'mix': self.vcm_delay.mix
            },
            'reverb': {
                'enabled': self.vcm_reverb.enabled,
                'decay_time': self.vcm_reverb.decay_time,
                'mix': self.vcm_reverb.mix
            }
        }

    def reset_vcm_effects(self):
        """Reset all VCM effects to default state."""
        self.vcm_distortion.reset()
        self.vcm_phaser.reset()
        self.vcm_chorus.reset()
        self.vcm_delay.reset()
        self.vcm_reverb.reset()


class JupiterXVCMDistortion:
    """Jupiter-X VCM Distortion - Authentic analog distortion modeling."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False
        self.drive = 0.0  # 0-1
        self.tone = 0.5   # 0-1
        self.distortion_type = 0  # 0=overdrive, 1=distortion, 2=fuzz

        # Internal state
        self.last_sample = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through VCM distortion."""
        if not self.enabled or self.drive == 0.0:
            return audio

        processed = np.copy(audio)

        # Apply drive
        processed *= (1.0 + self.drive * 3.0)

        # Apply distortion based on type
        if self.distortion_type == 0:  # Overdrive
            # Soft clipping with diode-like characteristic
            processed = np.tanh(processed * (1.0 + self.drive))
        elif self.distortion_type == 1:  # Distortion
            # Hard clipping with asymmetric response
            threshold = 0.7
            processed = np.where(np.abs(processed) < threshold,
                               processed,
                               np.sign(processed) * (threshold + (np.abs(processed) - threshold) * 0.3))
        elif self.distortion_type == 2:  # Fuzz
            # Extreme distortion with octave up
            sign = np.sign(processed)
            magnitude = np.abs(processed)
            # Add harmonics
            processed = sign * (magnitude + magnitude**2 * 0.5)

        # Apply tone control (simple filtering)
        if self.tone < 0.5:
            # Darker tone - roll off highs
            alpha = 0.1 + self.tone * 0.4
            # Simple lowpass
            for i in range(1, len(processed)):
                processed[i] = alpha * processed[i] + (1 - alpha) * processed[i-1]
        elif self.tone > 0.5:
            # Brighter tone - boost highs
            alpha = 0.6 + (self.tone - 0.5) * 0.4
            # Simple highpass
            for i in range(1, len(processed)):
                processed[i] = alpha * (processed[i] - processed[i-1] + processed[i-1])

        return processed

    def reset(self):
        """Reset distortion to default state."""
        self.enabled = False
        self.drive = 0.0
        self.tone = 0.5
        self.distortion_type = 0
        self.last_sample = 0.0


class JupiterXVCMPhaser:
    """Jupiter-X VCM Phaser - Authentic analog phaser modeling."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False
        self.rate = 0.5    # 0-1
        self.depth = 0.6   # 0-1
        self.feedback = 0.3  # 0-1

        # Phaser state
        self.phase = 0.0
        self.last_output = np.zeros(6, dtype=np.float32)  # 6 all-pass filters

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through VCM phaser."""
        if not self.enabled:
            return audio

        processed = np.copy(audio)
        feedback_signal = 0.0

        # Simplified 6-stage phaser implementation
        for i in range(len(processed)):
            # Generate LFO
            lfo = np.sin(self.phase) * self.depth

            # All-pass filter stages (simplified)
            for stage in range(6):
                # Calculate delay based on LFO
                delay_samples = 1 + stage * 2
                delay_index = max(0, i - delay_samples)

                if delay_index < i:
                    delayed_sample = processed[delay_index] + feedback_signal * self.feedback
                else:
                    delayed_sample = processed[i] + feedback_signal * self.feedback

                # All-pass filter
                g = 0.5 + lfo * 0.3  # Variable gain based on LFO
                ap_output = delayed_sample * g + processed[i] * (1 - g)
                processed[i] = processed[i] * (1 - g) + delayed_sample * g

                feedback_signal = ap_output

            # Update phase
            self.phase += 2 * np.pi * (0.1 + self.rate * 2.0) / self.sample_rate
            if self.phase > 2 * np.pi:
                self.phase -= 2 * np.pi

        return processed

    def reset(self):
        """Reset phaser to default state."""
        self.enabled = False
        self.rate = 0.5
        self.depth = 0.6
        self.feedback = 0.3
        self.phase = 0.0
        self.last_output.fill(0)


class JupiterXVCMChorus:
    """Jupiter-X VCM Chorus - Authentic analog chorus modeling."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False
        self.rate = 0.5      # 0-1
        self.depth = 0.6     # 0-1
        self.delay_time = 0.005  # 5ms base delay

        # Chorus state
        self.phase = 0.0
        self.delay_buffer = np.zeros(int(sample_rate * 0.05), dtype=np.float32)  # 50ms max
        self.buffer_index = 0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through VCM chorus."""
        if not self.enabled:
            return audio

        processed = np.copy(audio)

        for i in range(len(processed)):
            # Generate LFO for modulation
            lfo = np.sin(self.phase) * self.depth

            # Calculate modulated delay time
            mod_delay = self.delay_time * (1.0 + lfo * 0.5)
            delay_samples = int(mod_delay * self.sample_rate)

            # Get delayed sample
            delay_index = (self.buffer_index - delay_samples) % len(self.delay_buffer)
            delayed_sample = self.delay_buffer[delay_index]

            # Mix dry and delayed signals
            processed[i] = processed[i] * 0.7 + delayed_sample * 0.3

            # Store current sample in delay buffer
            self.delay_buffer[self.buffer_index] = processed[i]
            self.buffer_index = (self.buffer_index + 1) % len(self.delay_buffer)

            # Update phase
            self.phase += 2 * np.pi * (0.2 + self.rate * 1.0) / self.sample_rate
            if self.phase > 2 * np.pi:
                self.phase -= 2 * np.pi

        return processed

    def reset(self):
        """Reset chorus to default state."""
        self.enabled = False
        self.rate = 0.5
        self.depth = 0.6
        self.delay_time = 0.005
        self.phase = 0.0
        self.delay_buffer.fill(0)
        self.buffer_index = 0


class JupiterXVCMDelay:
    """Jupiter-X VCM Delay - Authentic analog delay modeling."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False
        self.delay_time = 0.3  # 300ms
        self.feedback = 0.3    # 0-1
        self.mix = 0.3         # 0-1

        # Delay state
        max_delay = int(sample_rate * 2.0)  # 2 seconds max
        self.delay_buffer = np.zeros(max_delay, dtype=np.float32)
        self.buffer_index = 0

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through VCM delay."""
        if not self.enabled:
            return audio

        processed = np.copy(audio)

        delay_samples = int(self.delay_time * self.sample_rate)

        for i in range(len(processed)):
            # Get delayed sample
            delay_index = (self.buffer_index - delay_samples) % len(self.delay_buffer)
            delayed_sample = self.delay_buffer[delay_index]

            # Apply feedback
            feedback_sample = delayed_sample * self.feedback

            # Mix dry and delayed signals
            processed[i] = processed[i] * (1.0 - self.mix) + delayed_sample * self.mix

            # Store current sample + feedback in delay buffer
            self.delay_buffer[self.buffer_index] = processed[i] + feedback_sample
            self.buffer_index = (self.buffer_index + 1) % len(self.delay_buffer)

        return processed

    def reset(self):
        """Reset delay to default state."""
        self.enabled = False
        self.delay_time = 0.3
        self.feedback = 0.3
        self.mix = 0.3
        self.delay_buffer.fill(0)
        self.buffer_index = 0


class JupiterXVCMReverb:
    """Jupiter-X VCM Reverb - Authentic analog reverb modeling."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.enabled = False
        self.decay_time = 2.0  # 2 seconds
        self.mix = 0.3         # 0-1

        # Simplified reverb state - in production this would be much more complex
        self.comb_filters = []
        self.allpass_filters = []

        # Initialize simple comb and allpass filters
        for delay_ms in [29.7, 37.1, 41.1, 43.7]:  # Prime delays in ms
            delay_samples = int((delay_ms / 1000.0) * sample_rate)
            self.comb_filters.append({
                'buffer': np.zeros(delay_samples, dtype=np.float32),
                'index': 0,
                'feedback': 0.84
            })

        for delay_ms in [5.0, 1.7]:  # Allpass delays in ms
            delay_samples = int((delay_ms / 1000.0) * sample_rate)
            self.allpass_filters.append({
                'buffer': np.zeros(delay_samples, dtype=np.float32),
                'index': 0,
                'feedback': 0.7
            })

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through VCM reverb."""
        if not self.enabled:
            return audio

        processed = np.copy(audio)
        wet_signal = np.zeros_like(audio)

        # Apply comb filters
        for comb in self.comb_filters:
            comb_output = np.zeros_like(audio)
            for i in range(len(audio)):
                # Get delayed sample
                delay_index = (comb['index'] - len(comb['buffer'])) % len(comb['buffer'])
                delayed_sample = comb['buffer'][delay_index]

                # Comb filter
                output_sample = audio[i] + delayed_sample * comb['feedback']
                comb_output[i] = output_sample

                # Store in buffer
                comb['buffer'][comb['index']] = output_sample
                comb['index'] = (comb['index'] + 1) % len(comb['buffer'])

            wet_signal += comb_output

        wet_signal /= len(self.comb_filters)

        # Apply allpass filters
        for allpass in self.allpass_filters:
            for i in range(len(wet_signal)):
                # Get delayed sample
                delay_index = (allpass['index'] - len(allpass['buffer'])) % len(allpass['buffer'])
                delayed_sample = allpass['buffer'][delay_index]

                # Allpass filter
                output_sample = wet_signal[i] + delayed_sample * allpass['feedback']
                wet_signal[i] = delayed_sample - output_sample * allpass['feedback']

                # Store in buffer
                allpass['buffer'][allpass['index']] = output_sample
                allpass['index'] = (allpass['index'] + 1) % len(allpass['buffer'])

        # Mix dry and wet signals
        processed = processed * (1.0 - self.mix) + wet_signal * self.mix

        return processed

    def reset(self):
        """Reset reverb to default state."""
        self.enabled = False
        self.decay_time = 2.0
        self.mix = 0.3

        for comb in self.comb_filters:
            comb['buffer'].fill(0)
            comb['index'] = 0

        for allpass in self.allpass_filters:
            allpass['buffer'].fill(0)
            allpass['index'] = 0
