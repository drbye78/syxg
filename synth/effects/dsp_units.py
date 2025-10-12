"""
DSP UNITS - SHARED COMPONENTS FOR HIGH-PERFORMANCE EFFECTS

This module provides shared DSP components used across multiple effects implementations.
All components are optimized for real-time performance with vectorized operations and
zero-allocation processing where possible.

Components:
- BiquadFilterBank: Reusable IIR filters for tone control and modulation
- DelayLineNetwork: Multi-tap delays with feedback for chorus/reverb
- EnvelopeFollower: Attack/release detector for dynamic effects
- FFTProcessor: Shared FFT analysis/synthesis for spectral effects
- LFOManager: Per-channel LFO pooling with XG parameter control
- FilterManager: ResonantFilter pooling for multi-stage processing
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import math
import threading
from collections import deque
import numba as nb
from numba import jit, float32, int32, boolean

from ..core.oscillator import OscillatorPool
from ..core.envelope import EnvelopePool
from ..core.filter import FilterPool
from ..engine.optimized_coefficient_manager import OptimizedCoefficientManager


class BiquadFilterBank:
    """
    HIGH-PERFORMANCE BIQUAD FILTER BANK

    Provides reusable biquad filters for tone control and modulation effects.
    Optimized for real-time processing with pre-calculated coefficients.
    """

    def __init__(self, sample_rate: int = 44100, max_filters: int = 8):
        self.sample_rate = sample_rate
        self.max_filters = max_filters

        # Pre-allocate filter states
        self.filter_states = []
        for _ in range(max_filters):
            self.filter_states.append({
                'b0': 1.0, 'b1': 0.0, 'b2': 0.0,
                'a1': 0.0, 'a2': 0.0,
                'x1': 0.0, 'x2': 0.0,
                'y1': 0.0, 'y2': 0.0
            })

        self.coeff_manager = OptimizedCoefficientManager()

    def design_lowpass(self, filter_idx: int, cutoff: float, q: float = 0.707):
        """Design lowpass filter coefficients"""
        if not (0 <= filter_idx < self.max_filters):
            return

        omega = 2.0 * math.pi * cutoff / self.sample_rate
        alpha = math.sin(omega) / (2.0 * q)

        cos_omega = math.cos(omega)
        a0 = 1.0 + alpha

        state = self.filter_states[filter_idx]
        state['b0'] = (1.0 - cos_omega) / (2.0 * a0)
        state['b1'] = (1.0 - cos_omega) / a0
        state['b2'] = (1.0 - cos_omega) / (2.0 * a0)
        state['a1'] = -2.0 * cos_omega / a0
        state['a2'] = (1.0 - alpha) / a0

    def design_highpass(self, filter_idx: int, cutoff: float, q: float = 0.707):
        """Design highpass filter coefficients"""
        if not (0 <= filter_idx < self.max_filters):
            return

        omega = 2.0 * math.pi * cutoff / self.sample_rate
        alpha = math.sin(omega) / (2.0 * q)

        cos_omega = math.cos(omega)
        a0 = 1.0 + alpha

        state = self.filter_states[filter_idx]
        state['b0'] = (1.0 + cos_omega) / (2.0 * a0)
        state['b1'] = -(1.0 + cos_omega) / a0
        state['b2'] = (1.0 + cos_omega) / (2.0 * a0)
        state['a1'] = -2.0 * cos_omega / a0
        state['a2'] = (1.0 - alpha) / a0

    def design_bandpass(self, filter_idx: int, center: float, q: float = 0.707):
        """Design bandpass filter coefficients"""
        if not (0 <= filter_idx < self.max_filters):
            return

        omega = 2.0 * math.pi * center / self.sample_rate
        alpha = math.sin(omega) / (2.0 * q)

        cos_omega = math.cos(omega)
        a0 = 1.0 + alpha

        state = self.filter_states[filter_idx]
        state['b0'] = alpha / a0
        state['b1'] = 0.0
        state['b2'] = -alpha / a0
        state['a1'] = -2.0 * cos_omega / a0
        state['a2'] = (1.0 - alpha) / a0

    def design_peaking(self, filter_idx: int, center: float, q: float, gain_db: float):
        """Design peaking filter coefficients"""
        if not (0 <= filter_idx < self.max_filters):
            return

        omega = 2.0 * math.pi * center / self.sample_rate
        alpha = math.sin(omega) / (2.0 * q)
        gain_linear = 10.0 ** (gain_db / 20.0)

        cos_omega = math.cos(omega)
        a0 = 1.0 + alpha / gain_linear

        state = self.filter_states[filter_idx]
        state['b0'] = (1.0 + alpha * gain_linear) / a0
        state['b1'] = -2.0 * cos_omega / a0
        state['b2'] = (1.0 - alpha * gain_linear) / a0
        state['a1'] = -2.0 * cos_omega / a0
        state['a2'] = (1.0 - alpha / gain_linear) / a0

    def process_sample(self, filter_idx: int, sample: float) -> float:
        """Process single sample through specified filter"""
        if not (0 <= filter_idx < self.max_filters):
            return sample

        state = self.filter_states[filter_idx]

        # Direct Form I biquad
        output = (state['b0'] * sample +
                 state['b1'] * state['x1'] +
                 state['b2'] * state['x2'] -
                 state['a1'] * state['y1'] -
                 state['a2'] * state['y2'])

        # Update state
        state['x2'] = state['x1']
        state['x1'] = sample
        state['y2'] = state['y1']
        state['y1'] = output

        return output

    def reset_filter(self, filter_idx: int):
        """Reset filter state"""
        if 0 <= filter_idx < self.max_filters:
            state = self.filter_states[filter_idx]
            state['x1'] = state['x2'] = 0.0
            state['y1'] = state['y2'] = 0.0


class DelayLineNetwork:
    """
    HIGH-PERFORMANCE DELAY LINE NETWORK

    Provides multi-tap delay lines with feedback for chorus, reverb, and modulation effects.
    Optimized for real-time processing with circular buffer implementation.
    """

    def __init__(self, max_delay_samples: int = 44100, num_taps: int = 4):
        self.max_delay_samples = max_delay_samples
        self.num_taps = num_taps

        # Circular buffer for delay line
        self.delay_buffer = np.zeros(max_delay_samples, dtype=np.float32)
        self.write_pos = 0

        # Tap configurations
        self.tap_delays = np.zeros(num_taps, dtype=np.int32)
        self.tap_gains = np.zeros(num_taps, dtype=np.float32)
        self.tap_feedbacks = np.zeros(num_taps, dtype=np.float32)

    def set_tap(self, tap_idx: int, delay_samples: int, gain: float, feedback: float = 0.0):
        """Configure a delay tap"""
        if 0 <= tap_idx < self.num_taps:
            self.tap_delays[tap_idx] = min(delay_samples, self.max_delay_samples - 1)
            self.tap_gains[tap_idx] = gain
            self.tap_feedbacks[tap_idx] = feedback

    def process_sample(self, input_sample: float) -> float:
        """Process single sample through delay network"""
        # Write input to delay buffer
        self.delay_buffer[self.write_pos] = input_sample

        # Sum all tap outputs
        output = 0.0
        for i in range(self.num_taps):
            if self.tap_delays[i] > 0:
                read_pos = (self.write_pos - self.tap_delays[i]) % self.max_delay_samples
                tap_output = self.delay_buffer[read_pos] * self.tap_gains[i]
                output += tap_output

                # Apply feedback
                if self.tap_feedbacks[i] != 0.0:
                    feedback_sample = tap_output * self.tap_feedbacks[i]
                    self.delay_buffer[self.write_pos] += feedback_sample

        # Update write position
        self.write_pos = (self.write_pos + 1) % self.max_delay_samples

        return output

    def reset(self):
        """Reset delay line state"""
        self.delay_buffer.fill(0.0)
        self.write_pos = 0


class EnvelopeFollower:
    """
    ENVELOPE FOLLOWER FOR DYNAMIC EFFECTS

    Provides attack/release envelope following for effects like envelope filters and compressors.
    Uses optimized coefficient-based smoothing.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.envelope = 0.0
        self.attack_coeff = 0.0
        self.release_coeff = 0.0

    def set_attack_release(self, attack_ms: float, release_ms: float):
        """Set attack and release times in milliseconds"""
        self.attack_coeff = 1.0 - math.exp(-1.0 / (attack_ms * 0.001 * self.sample_rate))
        self.release_coeff = 1.0 - math.exp(-1.0 / (release_ms * 0.001 * self.sample_rate))

    def process_sample(self, input_sample: float) -> float:
        """Process single sample and return envelope value"""
        input_level = abs(input_sample)

        if input_level > self.envelope:
            # Attack
            self.envelope += self.attack_coeff * (input_level - self.envelope)
        else:
            # Release
            self.envelope += self.release_coeff * (input_level - self.envelope)

        return self.envelope

    def reset(self):
        """Reset envelope state"""
        self.envelope = 0.0


class FFTProcessor:
    """
    FFT PROCESSOR FOR SPECTRAL EFFECTS

    Provides FFT analysis and synthesis for vocoder and spectral filtering effects.
    Optimized for real-time processing with windowing and overlap-add.
    """

    def __init__(self, fft_size: int = 1024, hop_size: int = 256):
        self.fft_size = fft_size
        self.hop_size = hop_size

        # FFT buffers
        self.input_buffer = np.zeros(fft_size, dtype=np.float32)
        self.output_buffer = np.zeros(fft_size, dtype=np.float32)
        self.fft_buffer = np.zeros(fft_size, dtype=complex)
        self.ifft_buffer = np.zeros(fft_size, dtype=complex)

        # Window function
        self.window = np.hanning(fft_size)

        # Buffer management
        self.buffer_pos = 0
        self.overlap_buffer = np.zeros(fft_size - hop_size, dtype=np.float32)

    def process_frame(self, input_frame: np.ndarray) -> np.ndarray:
        """Process one FFT frame"""
        if len(input_frame) != self.fft_size:
            return np.zeros(self.fft_size, dtype=np.float32)

        # Apply window
        windowed = input_frame * self.window

        # FFT
        self.fft_buffer = np.fft.rfft(windowed)

        # Process frequency domain (subclass should override)
        self.process_spectrum(self.fft_buffer)

        # Inverse FFT
        self.ifft_buffer = np.fft.irfft(self.fft_buffer)

        # Overlap-add
        output_frame = self.ifft_buffer * self.window

        # Add overlap from previous frame
        if len(self.overlap_buffer) > 0:
            output_frame[:len(self.overlap_buffer)] += self.overlap_buffer

        # Save overlap for next frame
        if self.fft_size > self.hop_size:
            self.overlap_buffer = output_frame[self.hop_size:].copy()

        return output_frame

    def process_spectrum(self, spectrum: np.ndarray):
        """Process frequency spectrum (override in subclass)"""
        pass

    def reset(self):
        """Reset FFT processor state"""
        self.input_buffer.fill(0.0)
        self.output_buffer.fill(0.0)
        self.fft_buffer.fill(0.0)
        self.ifft_buffer.fill(0.0)
        self.overlap_buffer.fill(0.0)
        self.buffer_pos = 0


class LFOManager:
    """
    LFO MANAGER FOR MODULATION EFFECTS

    Provides per-channel LFO pooling with XG parameter control.
    Manages multiple LFOs for complex modulation effects.
    """

    def __init__(self, sample_rate: int = 44100, max_lfos: int = 16):
        self.sample_rate = sample_rate
        self.max_lfos = max_lfos

        # LFO pool
        self.lfo_pool = OscillatorPool(
            max_oscillators=max_lfos,
            block_size=1024,
            sample_rate=sample_rate
        )

        # Active LFOs
        self.active_lfos = {}
        self.lfo_channels = {}  # channel -> lfo_id mapping

    def get_channel_lfo(self, channel: int, waveform: str = "sine",
                       rate: float = 1.0, depth: float = 1.0) -> Any:
        """Get or create LFO for specific channel"""
        if channel in self.lfo_channels:
            lfo_id = self.lfo_channels[channel]
            if lfo_id in self.active_lfos:
                return self.active_lfos[lfo_id]

        # Create new LFO
        lfo = self.lfo_pool.acquire_oscillator(
            id=channel, waveform=waveform, rate=rate, depth=depth
        )

        self.active_lfos[channel] = lfo
        self.lfo_channels[channel] = channel

        return lfo

    def release_channel_lfo(self, channel: int):
        """Release LFO for specific channel"""
        if channel in self.lfo_channels:
            lfo_id = self.lfo_channels[channel]
            if lfo_id in self.active_lfos:
                self.lfo_pool.release_oscillator(self.active_lfos[lfo_id])
                del self.active_lfos[lfo_id]
            del self.lfo_channels[channel]

    def reset(self):
        """Reset all LFOs"""
        for lfo in self.active_lfos.values():
            self.lfo_pool.release_oscillator(lfo)
        self.active_lfos.clear()
        self.lfo_channels.clear()


class FilterManager:
    """
    FILTER MANAGER FOR MULTI-STAGE PROCESSING

    Provides ResonantFilter pooling for effects requiring multiple filter stages.
    Optimized for guitar amp simulation and multi-band processing.
    """

    def __init__(self, sample_rate: int = 44100, max_filters: int = 8):
        self.sample_rate = sample_rate
        self.max_filters = max_filters

        # Filter pool
        self.filter_pool = FilterPool(
            max_filters=max_filters,
            block_size=1024,
            sample_rate=sample_rate
        )

        # Active filters
        self.active_filters = {}
        self.filter_stages = {}  # effect_name -> [filter_ids]

    def get_filter_stage(self, stage_name: str, stage_idx: int,
                        cutoff: float = 1000.0, resonance: float = 0.7,
                        filter_type: str = "lowpass") -> Any:
        """Get filter for specific processing stage"""
        stage_key = f"{stage_name}_{stage_idx}"

        if stage_key in self.active_filters:
            return self.active_filters[stage_key]

        # Create new filter
        filter_obj = self.filter_pool.acquire_filter(
            cutoff=cutoff, resonance=resonance, filter_type=filter_type
        )

        self.active_filters[stage_key] = filter_obj

        # Track stages
        if stage_name not in self.filter_stages:
            self.filter_stages[stage_name] = []
        self.filter_stages[stage_name].append(stage_key)

        return filter_obj

    def release_filter_stage(self, stage_name: str, stage_idx: int):
        """Release filter for specific stage"""
        stage_key = f"{stage_name}_{stage_idx}"

        if stage_key in self.active_filters:
            self.filter_pool.release_filter(self.active_filters[stage_key])
            del self.active_filters[stage_key]

            if stage_name in self.filter_stages:
                self.filter_stages[stage_name].remove(stage_key)

    def release_all_stages(self, stage_name: str):
        """Release all filters for an effect"""
        if stage_name in self.filter_stages:
            for stage_key in self.filter_stages[stage_name][:]:  # Copy list
                if stage_key in self.active_filters:
                    self.filter_pool.release_filter(self.active_filters[stage_key])
                    del self.active_filters[stage_key]
            del self.filter_stages[stage_name]

    def reset(self):
        """Reset all filters"""
        for filter_obj in self.active_filters.values():
            self.filter_pool.release_filter(filter_obj)
        self.active_filters.clear()
        self.filter_stages.clear()


class DSPUnitsManager:
    """
    CENTRAL DSP UNITS MANAGER

    Provides unified access to all DSP components with proper resource management.
    Ensures thread-safe operation and efficient resource pooling.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Initialize all DSP units
        self.biquad_bank = BiquadFilterBank(sample_rate)
        self.delay_network = DelayLineNetwork()
        self.envelope_follower = EnvelopeFollower(sample_rate)
        self.fft_processor = FFTProcessor()
        self.lfo_manager = LFOManager(sample_rate)
        self.filter_manager = FilterManager(sample_rate)

        # Coefficient manager for optimized math
        self.coeff_manager = OptimizedCoefficientManager()

        # Thread safety
        self.lock = threading.RLock()

    def reset_all(self):
        """Reset all DSP units"""
        with self.lock:
            self.biquad_bank = BiquadFilterBank(self.sample_rate)
            self.delay_network.reset()
            self.envelope_follower.reset()
            self.fft_processor.reset()
            self.lfo_manager.reset()
            self.filter_manager.reset()

    def get_biquad_bank(self) -> BiquadFilterBank:
        """Get biquad filter bank"""
        return self.biquad_bank

    def get_delay_network(self) -> DelayLineNetwork:
        """Get delay line network"""
        return self.delay_network

    def get_envelope_follower(self) -> EnvelopeFollower:
        """Get envelope follower"""
        return self.envelope_follower

    def get_fft_processor(self) -> FFTProcessor:
        """Get FFT processor"""
        return self.fft_processor

    def get_lfo_manager(self) -> LFOManager:
        """Get LFO manager"""
        return self.lfo_manager

    def get_filter_manager(self) -> FilterManager:
        """Get filter manager"""
        return self.filter_manager

    def get_coeff_manager(self) -> OptimizedCoefficientManager:
        """Get coefficient manager"""
        return self.coeff_manager