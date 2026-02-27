"""
Yamaha Motif User Sampling System

Complete sampling and sample management system providing professional
workstation-grade recording, editing, and manipulation capabilities.
Provides authentic Motif-compatible sampling workflow.
"""
from __future__ import annotations

import numpy as np
from typing import Any
from collections.abc import Callable
import threading
import time
import math
import wave
import audioop
from pathlib import Path


class Sample:
    """
    Sample data container with metadata and processing capabilities
    """

    def __init__(self, data: np.ndarray, sample_rate: int, name: str = "Untitled"):
        self.data = data.astype(np.float32)  # Always float32 internally
        self.sample_rate = sample_rate
        self.name = name
        self.length = len(data)

        # Metadata
        self.original_format = "float32"
        self.bit_depth = 32
        self.channels = 1 if data.ndim == 1 else data.shape[1]

        # Loop points
        self.loop_start = 0
        self.loop_end = self.length - 1
        self.loop_enabled = False

        # Sample properties
        self.root_note = 60  # MIDI note number
        self.fine_tune = 0   # cents
        self.volume = 1.0

        # Processing flags
        self.normalized = False
        self.fade_in_applied = False
        self.fade_out_applied = False

    def get_duration(self) -> float:
        """Get sample duration in seconds"""
        return self.length / self.sample_rate

    def get_rms_level(self) -> float:
        """Get RMS level of the sample"""
        return np.sqrt(np.mean(self.data ** 2))

    def normalize(self, target_level: float = 1.0):
        """Normalize sample to target level"""
        current_rms = self.get_rms_level()
        if current_rms > 0:
            scale_factor = target_level / current_rms
            self.data *= scale_factor
            self.volume *= scale_factor
        self.normalized = True

    def apply_fade_in(self, duration_ms: int = 10):
        """Apply fade-in to sample"""
        fade_samples = int(duration_ms * self.sample_rate / 1000)
        if fade_samples > 0:
            fade_curve = np.linspace(0.0, 1.0, fade_samples)
            self.data[:fade_samples] *= fade_curve
        self.fade_in_applied = True

    def apply_fade_out(self, duration_ms: int = 10):
        """Apply fade-out to sample"""
        fade_samples = int(duration_ms * self.sample_rate / 1000)
        if fade_samples > 0:
            fade_curve = np.linspace(1.0, 0.0, fade_samples)
            self.data[-fade_samples:] *= fade_curve
        self.fade_out_applied = True

    def trim(self, start_sample: int, end_sample: int):
        """Trim sample to specified range"""
        if 0 <= start_sample < end_sample <= self.length:
            self.data = self.data[start_sample:end_sample]
            self.length = len(self.data)

            # Adjust loop points
            if self.loop_start < start_sample:
                self.loop_start = 0
            else:
                self.loop_start -= start_sample

            if self.loop_end >= end_sample:
                self.loop_end = self.length - 1
            else:
                self.loop_end -= start_sample

    def reverse(self):
        """Reverse sample"""
        self.data = np.flip(self.data)

    def to_mono(self):
        """Convert to mono if stereo"""
        if self.channels > 1:
            self.data = np.mean(self.data, axis=1)
            self.channels = 1

    def resample(self, new_sample_rate: int):
        """Resample to new sample rate"""
        if new_sample_rate != self.sample_rate:
            from scipy import signal
            # Simple resampling (in practice, use better algorithms)
            ratio = new_sample_rate / self.sample_rate
            new_length = int(self.length * ratio)
            self.data = signal.resample(self.data, new_length)
            self.sample_rate = new_sample_rate
            self.length = len(self.data)

    def get_sample_info(self) -> dict[str, Any]:
        """Get comprehensive sample information"""
        return {
            'name': self.name,
            'length': self.length,
            'duration': self.get_duration(),
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bit_depth': self.bit_depth,
            'rms_level': self.get_rms_level(),
            'root_note': self.root_note,
            'fine_tune': self.fine_tune,
            'loop_enabled': self.loop_enabled,
            'loop_start': self.loop_start,
            'loop_end': self.loop_end,
            'normalized': self.normalized,
            'fade_in_applied': self.fade_in_applied,
            'fade_out_applied': self.fade_out_applied
        }


class AudioRecorder:
    """
    Professional audio recording system for Motif-compatible sampling
    """

    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.recorded_data = []

        # Recording settings
        self.monitor_level = 0.7
        self.record_level = 1.0
        self.pre_roll_samples = 0

        # Callbacks
        self.level_callback: Callable | None = None

    def start_recording(self):
        """Start audio recording"""
        self.is_recording = True
        self.recorded_data = []
        print(f"🎤 Started recording: {self.channels}ch @ {self.sample_rate}Hz")

    def stop_recording(self) -> Sample | None:
        """Stop recording and return recorded sample"""
        if not self.is_recording:
            return None

        self.is_recording = False

        if not self.recorded_data:
            return None

        # Concatenate recorded data
        recorded_array = np.concatenate(self.recorded_data)

        # Create sample
        sample_name = f"Recording_{int(time.time())}"
        sample = Sample(recorded_array, self.sample_rate, sample_name)

        print(f"🎤 Recording complete: {sample.get_duration():.2f}s, {len(recorded_array)} samples")
        return sample

    def process_audio_input(self, audio_data: np.ndarray):
        """Process incoming audio data for recording"""
        if not self.is_recording:
            return

        # Apply record level
        processed_data = audio_data * self.record_level

        # Store data
        self.recorded_data.append(processed_data.copy())

        # Update level monitoring
        if self.level_callback:
            rms_level = np.sqrt(np.mean(processed_data ** 2))
            self.level_callback(rms_level)


class SampleEditor:
    """
    Professional sample editing tools for Motif workstation workflow
    """

    def __init__(self):
        self.current_sample: Sample | None = None

    def load_sample(self, sample: Sample):
        """Load sample for editing"""
        self.current_sample = sample

    def trim_sample(self, start_time: float, end_time: float) -> bool:
        """Trim sample between start and end times"""
        if not self.current_sample:
            return False

        start_sample = int(start_time * self.current_sample.sample_rate)
        end_sample = int(end_time * self.current_sample.sample_rate)

        if 0 <= start_sample < end_sample <= self.current_sample.length:
            self.current_sample.trim(start_sample, end_sample)
            return True
        return False

    def set_loop_points(self, start_time: float, end_time: float) -> bool:
        """Set loop points for sample"""
        if not self.current_sample:
            return False

        start_sample = int(start_time * self.current_sample.sample_rate)
        end_sample = int(end_time * self.current_sample.sample_rate)

        if 0 <= start_sample < end_sample <= self.current_sample.length:
            self.current_sample.loop_start = start_sample
            self.current_sample.loop_end = end_sample
            self.current_sample.loop_enabled = True
            return True
        return False

    def apply_crossfade(self, crossfade_time: float = 0.01) -> bool:
        """Apply crossfade at loop points"""
        if not self.current_sample or not self.current_sample.loop_enabled:
            return False

        fade_samples = int(crossfade_time * self.current_sample.sample_rate)
        if fade_samples <= 0:
            return False

        start = self.current_sample.loop_start
        end = self.current_sample.loop_end

        # Ensure we have enough samples
        if start + fade_samples > end - fade_samples:
            return False

        # Create crossfade curves
        fade_out = np.linspace(1.0, 0.0, fade_samples)
        fade_in = np.linspace(0.0, 1.0, fade_samples)

        # Apply crossfade
        self.current_sample.data[start:start + fade_samples] *= fade_out
        self.current_sample.data[end - fade_samples:end] *= fade_in

        # Mix the crossfade regions
        crossfade_region = (
            self.current_sample.data[start:start + fade_samples] +
            self.current_sample.data[end - fade_samples:end]
        )

        self.current_sample.data[start:start + fade_samples] = crossfade_region
        self.current_sample.data[end - fade_samples:end] = crossfade_region

        return True

    def normalize_sample(self, target_level: float = 1.0) -> bool:
        """Normalize sample to target level"""
        if not self.current_sample:
            return False

        self.current_sample.normalize(target_level)
        return True

    def reverse_sample(self) -> bool:
        """Reverse sample"""
        if not self.current_sample:
            return False

        self.current_sample.reverse()
        return True

    def apply_time_stretch(self, stretch_factor: float) -> bool:
        """Apply time stretching to sample"""
        if not self.current_sample or stretch_factor <= 0:
            return False

        # Simple time stretching (in practice, use better algorithms)
        new_length = int(self.current_sample.length / stretch_factor)
        self.current_sample.data = np.interp(
            np.linspace(0, self.current_sample.length - 1, new_length),
            np.arange(self.current_sample.length),
            self.current_sample.data
        )
        self.current_sample.length = len(self.current_sample.data)
        return True

    def apply_pitch_shift(self, semitones: float) -> bool:
        """Apply pitch shifting to sample"""
        if not self.current_sample:
            return False

        # Calculate new sample rate for pitch shift
        ratio = 2 ** (semitones / 12.0)
        new_sample_rate = int(self.current_sample.sample_rate * ratio)

        # Resample
        self.current_sample.resample(new_sample_rate)
        self.current_sample.root_note = int(self.current_sample.root_note + semitones)
        return True


class WaveformGenerator:
    """
    Waveform creation and manipulation for Motif sampling system
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def create_sine_wave(self, frequency: float, duration: float, amplitude: float = 1.0) -> Sample:
        """Create sine wave sample"""
        length = int(duration * self.sample_rate)
        t = np.linspace(0, duration, length, endpoint=False)
        data = amplitude * np.sin(2 * np.pi * frequency * t)

        sample = Sample(data, self.sample_rate, f"Sine_{frequency}Hz")
        return sample

    def create_square_wave(self, frequency: float, duration: float, amplitude: float = 1.0) -> Sample:
        """Create square wave sample"""
        length = int(duration * self.sample_rate)
        t = np.linspace(0, duration, length, endpoint=False)
        data = amplitude * np.sign(np.sin(2 * np.pi * frequency * t))

        sample = Sample(data, self.sample_rate, f"Square_{frequency}Hz")
        return sample

    def create_sawtooth_wave(self, frequency: float, duration: float, amplitude: float = 1.0) -> Sample:
        """Create sawtooth wave sample"""
        length = int(duration * self.sample_rate)
        t = np.linspace(0, duration, length, endpoint=False)
        data = amplitude * (2 * (t * frequency - np.floor(t * frequency + 0.5)))

        sample = Sample(data, self.sample_rate, f"Saw_{frequency}Hz")
        return sample

    def create_triangle_wave(self, frequency: float, duration: float, amplitude: float = 1.0) -> Sample:
        """Create triangle wave sample"""
        length = int(duration * self.sample_rate)
        t = np.linspace(0, duration, length, endpoint=False)
        data = amplitude * (2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1)

        sample = Sample(data, self.sample_rate, f"Triangle_{frequency}Hz")
        return sample

    def create_white_noise(self, duration: float, amplitude: float = 1.0) -> Sample:
        """Create white noise sample"""
        length = int(duration * self.sample_rate)
        data = amplitude * np.random.normal(0, 1, length)

        sample = Sample(data, self.sample_rate, f"Noise_{duration}s")
        return sample

    def create_impulse(self, duration: float = 1.0) -> Sample:
        """Create impulse response sample"""
        length = int(duration * self.sample_rate)
        data = np.zeros(length)
        data[0] = 1.0  # Single impulse at start

        sample = Sample(data, self.sample_rate, f"Impulse_{duration}s")
        return sample

    def combine_samples(self, samples: list[Sample], mode: str = "mix") -> Sample | None:
        """Combine multiple samples"""
        if not samples:
            return None

        if mode == "mix":
            # Mix samples together
            max_length = max(s.length for s in samples)
            combined_data = np.zeros(max_length)

            for sample in samples:
                if sample.length < max_length:
                    # Pad shorter samples
                    padded = np.pad(sample.data, (0, max_length - sample.length))
                    combined_data += padded
                else:
                    combined_data += sample.data[:max_length]

            combined_data /= len(samples)  # Average mix

        elif mode == "concatenate":
            # Concatenate samples
            combined_data = np.concatenate([s.data for s in samples])

        else:
            return None

        combined_sample = Sample(combined_data, self.sample_rate, f"Combined_{mode}")
        return combined_sample


class SampleManager:
    """
    Comprehensive sample management system for Motif workstation
    """

    def __init__(self, max_samples: int = 1000, max_memory_mb: int = 512):
        self.samples: dict[str, Sample] = {}
        self.max_samples = max_samples
        self.max_memory_mb = max_memory_mb

        # Sample categories
        self.categories = {
            'user': [],      # User-recorded samples
            'factory': [],   # Factory samples
            'generated': []  # Generated waveforms
        }

        # Tools
        self.recorder = AudioRecorder()
        self.editor = SampleEditor()
        self.generator = WaveformGenerator()

        # Memory tracking
        self.memory_used_mb = 0.0

        print(f"🎵 Sample Manager initialized: {max_samples} samples, {max_memory_mb}MB limit")

    def add_sample(self, sample: Sample, category: str = "user") -> bool:
        """Add sample to manager"""
        # Check limits
        if len(self.samples) >= self.max_samples:
            print("❌ Sample limit reached")
            return False

        # Estimate memory usage (float32 = 4 bytes per sample)
        sample_memory_mb = (sample.length * sample.channels * 4) / (1024 * 1024)

        if self.memory_used_mb + sample_memory_mb > self.max_memory_mb:
            print("❌ Memory limit reached")
            return False

        # Generate unique name if needed
        name = sample.name
        counter = 1
        while name in self.samples:
            name = f"{sample.name}_{counter}"
            counter += 1

        sample.name = name
        self.samples[name] = sample

        # Add to category
        if category in self.categories:
            self.categories[category].append(name)

        self.memory_used_mb += sample_memory_mb
        print(f"✅ Added sample: {name} ({sample_memory_mb:.1f}MB)")
        return True

    def remove_sample(self, name: str) -> bool:
        """Remove sample from manager"""
        if name not in self.samples:
            return False

        sample = self.samples[name]
        sample_memory_mb = (sample.length * sample.channels * 4) / (1024 * 1024)

        # Remove from categories
        for category_samples in self.categories.values():
            if name in category_samples:
                category_samples.remove(name)

        del self.samples[name]
        self.memory_used_mb -= sample_memory_mb
        print(f"🗑️ Removed sample: {name}")
        return True

    def get_sample(self, name: str) -> Sample | None:
        """Get sample by name"""
        return self.samples.get(name)

    def list_samples(self, category: str | None = None) -> list[str]:
        """List samples, optionally by category"""
        if category and category in self.categories:
            return self.categories[category].copy()
        return list(self.samples.keys())

    def save_sample(self, name: str, file_path: str) -> bool:
        """Save sample to WAV file"""
        sample = self.get_sample(name)
        if not sample:
            return False

        try:
            # Convert to 16-bit integers for WAV
            if sample.data.dtype != np.int16:
                # Normalize to [-1, 1] range
                normalized = sample.data / np.max(np.abs(sample.data))
                # Convert to 16-bit
                wav_data = (normalized * 32767).astype(np.int16)
            else:
                wav_data = sample.data

            # Write WAV file
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(sample.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample.sample_rate)
                wav_file.writeframes(wav_data.tobytes())

            print(f"💾 Saved sample: {name} -> {file_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to save sample: {e}")
            return False

    def load_sample_from_file(self, file_path: str, name: str | None = None) -> bool:
        """Load sample from WAV file"""
        try:
            with wave.open(file_path, 'rb') as wav_file:
                # Get file info
                channels = wav_file.getnchannels()
                sample_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                num_frames = wav_file.getnframes()

                # Read data
                raw_data = wav_file.readframes(num_frames)

                # Convert based on sample width
                if sample_width == 2:  # 16-bit
                    data = np.frombuffer(raw_data, dtype=np.int16)
                    data = data.astype(np.float32) / 32768.0
                elif sample_width == 4:  # 32-bit float
                    data = np.frombuffer(raw_data, dtype=np.float32)
                else:
                    print("❌ Unsupported sample format")
                    return False

                # Reshape for multi-channel
                if channels > 1:
                    data = data.reshape(-1, channels)

                # Create sample
                sample_name = name or Path(file_path).stem
                sample = Sample(data, sample_rate, sample_name)

                return self.add_sample(sample, "user")

        except Exception as e:
            print(f"❌ Failed to load sample: {e}")
            return False

    def start_recording(self, sample_rate: int = 44100, channels: int = 1) -> bool:
        """Start audio recording"""
        self.recorder = AudioRecorder(sample_rate, channels)
        self.recorder.start_recording()
        return True

    def stop_recording(self, name: str | None = None) -> str | None:
        """Stop recording and add recorded sample"""
        recorded_sample = self.recorder.stop_recording()
        if recorded_sample:
            if name:
                recorded_sample.name = name
            if self.add_sample(recorded_sample, "user"):
                return recorded_sample.name
        return None

    def generate_waveform(self, waveform_type: str, **params) -> str | None:
        """Generate waveform sample"""
        try:
            if waveform_type == "sine":
                sample = self.generator.create_sine_wave(**params)
            elif waveform_type == "square":
                sample = self.generator.create_square_wave(**params)
            elif waveform_type == "sawtooth":
                sample = self.generator.create_sawtooth_wave(**params)
            elif waveform_type == "triangle":
                sample = self.generator.create_triangle_wave(**params)
            elif waveform_type == "noise":
                sample = self.generator.create_white_noise(**params)
            elif waveform_type == "impulse":
                sample = self.generator.create_impulse(**params)
            else:
                return None

            if self.add_sample(sample, "generated"):
                return sample.name

        except Exception as e:
            print(f"❌ Failed to generate waveform: {e}")

        return None

    def edit_sample(self, name: str, operation: str, **params) -> bool:
        """Edit sample with specified operation"""
        sample = self.get_sample(name)
        if not sample:
            return False

        self.editor.load_sample(sample)

        try:
            if operation == "trim":
                return self.editor.trim_sample(**params)
            elif operation == "loop":
                return self.editor.set_loop_points(**params)
            elif operation == "crossfade":
                return self.editor.apply_crossfade(**params)
            elif operation == "normalize":
                return self.editor.normalize_sample(**params)
            elif operation == "reverse":
                return self.editor.reverse_sample()
            elif operation == "stretch":
                return self.editor.apply_time_stretch(**params)
            elif operation == "pitch_shift":
                return self.editor.apply_pitch_shift(**params)
            else:
                return False

        except Exception as e:
            print(f"❌ Failed to edit sample: {e}")
            return False

    def get_manager_status(self) -> dict[str, Any]:
        """Get comprehensive manager status"""
        total_samples = len(self.samples)
        total_duration = sum(s.get_duration() for s in self.samples.values())

        return {
            'total_samples': total_samples,
            'total_duration': total_duration,
            'memory_used_mb': self.memory_used_mb,
            'memory_limit_mb': self.max_memory_mb,
            'sample_limit': self.max_samples,
            'categories': {cat: len(samples) for cat, samples in self.categories.items()},
            'recording_active': self.recorder.is_recording if hasattr(self.recorder, 'is_recording') else False,
            'samples': {name: s.get_sample_info() for name, s in list(self.samples.items())[:10]}  # First 10 samples
        }


# Export classes
__all__ = [
    'Sample', 'AudioRecorder', 'SampleEditor', 'WaveformGenerator', 'SampleManager'
]
