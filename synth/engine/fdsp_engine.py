"""
Formant Dynamic Synthesis Processor (FDSP) Engine

Advanced formant synthesis for vocal and wind instrument modeling.
Provides authentic vocal synthesis with real-time formant manipulation,
anti-resonant filtering, and phoneme-based transitions.

Part of S90/S70 compatibility implementation - Phase 1.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .synthesis_engine import SynthesisEngine


class FormantFilter:
    """Anti-resonant formant filter for vocal synthesis"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.frequency = 1000.0  # Hz
        self.bandwidth = 100.0  # Hz
        self.gain = 1.0  # Linear gain

        # Filter state
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

        self._update_coefficients()

    def _update_coefficients(self):
        """Update filter coefficients based on current parameters"""
        # Anti-resonant (notch) filter design
        # H(z) = (b0*z^2 + b1*z + b2) / (a0*z^2 + a1*z + a2)

        omega = 2.0 * math.pi * self.frequency / self.sample_rate
        alpha = math.sin(omega) * math.sinh(
            math.log(2.0) * self.bandwidth * omega / (2.0 * math.sin(omega))
        )

        # Normalize
        a0 = 1.0 + alpha
        a1 = -2.0 * math.cos(omega)
        a2 = 1.0 - alpha

        # Anti-resonant: boost around center frequency
        b0 = self.gain * a0
        b1 = self.gain * a1
        b2 = self.gain * a2

        # Normalize by a0
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0

    def set_parameters(self, frequency: float, bandwidth: float, gain: float = 1.0):
        """Set filter parameters"""
        self.frequency = max(50.0, min(8000.0, frequency))
        self.bandwidth = max(10.0, min(2000.0, bandwidth))
        self.gain = max(0.1, min(10.0, gain))
        self._update_coefficients()

    def process_sample(self, input_sample: float) -> float:
        """Process one sample through the formant filter"""
        # Direct Form II implementation
        output = (
            self.b0 * input_sample
            + self.b1 * self.x1
            + self.b2 * self.x2
            - self.a1 * self.y1
            - self.a2 * self.y2
        )

        # Update state
        self.x2 = self.x1
        self.x1 = input_sample
        self.y2 = self.y1
        self.y1 = output

        return output

    def reset(self):
        """Reset filter state"""
        self.x1 = self.x2 = 0.0
        self.y1 = self.y2 = 0.0


class FormantFilterBank:
    """Bank of formant filters for vocal synthesis"""

    def __init__(self, sample_rate: int = 44100, num_formants: int = 5):
        self.sample_rate = sample_rate
        self.num_formants = num_formants
        self.filters: list[FormantFilter] = []

        # Initialize formant filters
        self._init_filters()

        # Formant gains
        self.formant_gains = np.ones(num_formants, dtype=np.float32)

        # Global parameters
        self.master_gain = 1.0
        self.tilt = 0.0  # Spectral tilt in dB/octave

    def _init_filters(self):
        """Initialize formant filters with default frequencies"""
        # Default formant frequencies for neutral vowel /ə/
        default_formants = [
            (730, 100),  # F1
            (1090, 120),  # F2
            (2440, 150),  # F3
            (3400, 200),  # F4
            (4500, 250),  # F5
        ]

        for freq, bw in default_formants[: self.num_formants]:
            filter = FormantFilter(self.sample_rate)
            filter.set_parameters(freq, bw, 1.0)
            self.filters.append(filter)

    def set_formant(
        self, formant_index: int, frequency: float, bandwidth: float, gain: float = 1.0
    ):
        """Set parameters for a specific formant"""
        if 0 <= formant_index < len(self.filters):
            self.filters[formant_index].set_parameters(frequency, bandwidth, gain)

    def set_formant_frequencies(self, frequencies: list[float]):
        """Set all formant frequencies at once"""
        for i, freq in enumerate(frequencies[: len(self.filters)]):
            current_bw = self.filters[i].bandwidth
            current_gain = self.formant_gains[i]
            self.filters[i].set_parameters(freq, current_bw, current_gain)

    def set_formant_bandwidths(self, bandwidths: list[float]):
        """Set all formant bandwidths at once"""
        for i, bw in enumerate(bandwidths[: len(self.filters)]):
            current_freq = self.filters[i].frequency
            current_gain = self.formant_gains[i]
            self.filters[i].set_parameters(current_freq, bw, current_gain)

    def set_formant_gains(self, gains: list[float]):
        """Set all formant gains at once"""
        self.formant_gains = np.array(gains[: len(self.filters)], dtype=np.float32)

    def set_tilt(self, tilt_db: float):
        """Set spectral tilt in dB/octave"""
        self.tilt = tilt_db

    def process_sample(self, input_sample: float) -> float:
        """Process one sample through the formant filter bank"""
        output = input_sample

        # Apply formant filters in series
        for i, filter in enumerate(self.filters):
            filter_output = filter.process_sample(output)
            # Apply formant gain and tilt compensation
            tilt_compensation = 10.0 ** (self.tilt * math.log2(filter.frequency / 1000.0) / 20.0)
            output = filter_output * self.formant_gains[i] * tilt_compensation

        # Apply master gain
        return output * self.master_gain

    def reset(self):
        """Reset all filters"""
        for filter in self.filters:
            filter.reset()


class PhonemeData:
    """Phoneme data structure for vocal synthesis"""

    def __init__(
        self,
        name: str,
        formant_frequencies: list[float],
        formant_bandwidths: list[float],
        duration_ms: float = 200.0,
    ):
        self.name = name
        self.formant_frequencies = np.array(formant_frequencies, dtype=np.float32)
        self.formant_bandwidths = np.array(formant_bandwidths, dtype=np.float32)
        self.duration_ms = duration_ms

        # Ensure we have enough formants (pad with neutral values if needed)
        while len(self.formant_frequencies) < 5:
            self.formant_frequencies = np.append(self.formant_frequencies, 3000.0)
            self.formant_bandwidths = np.append(self.formant_bandwidths, 200.0)


class VocalDatabase:
    """Database of phonemes and vocal characteristics"""

    def __init__(self):
        self.phonemes: dict[str, PhonemeData] = {}
        self._init_phoneme_database()

        # Transition parameters
        self.transition_time_ms = 50.0  # Default transition time

    def _init_phoneme_database(self):
        """Initialize phoneme database with standard English phonemes"""

        # Vowels (based on standard formant values)
        self.phonemes["i"] = PhonemeData(
            "i", [270, 2290, 3010, 3500, 4500], [50, 80, 120, 150, 200]
        )  # "ee" as in "beet"
        self.phonemes["ɪ"] = PhonemeData(
            "ɪ", [400, 2000, 2550, 3100, 4000], [60, 100, 120, 150, 200]
        )  # "i" as in "bit"
        self.phonemes["eɪ"] = PhonemeData(
            "eɪ", [530, 1840, 2480, 3300, 4000], [70, 90, 110, 140, 180]
        )  # "ay" as in "bait"
        self.phonemes["ɛ"] = PhonemeData(
            "ɛ", [660, 1720, 2410, 3200, 4000], [80, 100, 120, 150, 200]
        )  # "e" as in "bet"
        self.phonemes["æ"] = PhonemeData(
            "æ", [730, 1090, 2440, 3400, 4500], [90, 120, 130, 160, 200]
        )  # "a" as in "bat"
        self.phonemes["ɑ"] = PhonemeData(
            "ɑ", [850, 1220, 2810, 3600, 4500], [100, 130, 140, 170, 200]
        )  # "ah" as in "father"
        self.phonemes["ɔ"] = PhonemeData(
            "ɔ", [570, 840, 2410, 3300, 4000], [80, 110, 120, 150, 180]
        )  # "aw" as in "law"
        self.phonemes["oʊ"] = PhonemeData(
            "oʊ", [570, 840, 2410, 3300, 4000], [80, 110, 120, 150, 180]
        )  # "oh" as in "boat"
        self.phonemes["ʊ"] = PhonemeData(
            "ʊ", [300, 870, 2240, 3200, 4000], [60, 100, 120, 140, 180]
        )  # "oo" as in "book"
        self.phonemes["u"] = PhonemeData(
            "u", [300, 870, 2240, 3200, 4000], [60, 100, 120, 140, 180]
        )  # "oo" as in "boot"
        self.phonemes["ʌ"] = PhonemeData(
            "ʌ", [640, 1190, 2390, 3400, 4500], [80, 110, 130, 160, 200]
        )  # "uh" as in "but"
        self.phonemes["ə"] = PhonemeData(
            "ə", [550, 1770, 2490, 3200, 4000], [70, 90, 110, 140, 180]
        )  # schwa as in "about"
        self.phonemes["ɜ"] = PhonemeData(
            "ɜ", [550, 1770, 2490, 3200, 4000], [70, 90, 110, 140, 180]
        )  # "ur" as in "bird"

        # Consonants (simplified formant representations)
        self.phonemes["p"] = PhonemeData(
            "p", [150, 800, 2200, 3000, 4000], [200, 300, 400, 500, 600], 50
        )
        self.phonemes["t"] = PhonemeData(
            "t", [200, 1800, 2600, 3200, 4000], [250, 350, 450, 550, 650], 50
        )
        self.phonemes["k"] = PhonemeData(
            "k", [250, 2000, 2800, 3400, 4200], [300, 400, 500, 600, 700], 50
        )
        self.phonemes["m"] = PhonemeData(
            "m", [300, 1000, 2200, 3000, 4000], [150, 200, 300, 400, 500], 80
        )
        self.phonemes["n"] = PhonemeData(
            "n", [300, 1400, 2400, 3200, 4000], [150, 200, 300, 400, 500], 80
        )
        self.phonemes["s"] = PhonemeData(
            "s", [4500, 5500, 6500, 7500, 8500], [1000, 1200, 1400, 1600, 1800], 100
        )
        self.phonemes["ʃ"] = PhonemeData(
            "ʃ", [2500, 3500, 4500, 5500, 6500], [800, 1000, 1200, 1400, 1600], 100
        )
        self.phonemes["h"] = PhonemeData(
            "h", [800, 1800, 2800, 3800, 4800], [500, 600, 700, 800, 900], 60
        )

    def get_phoneme(self, phoneme_name: str) -> PhonemeData | None:
        """Get phoneme data by name"""
        return self.phonemes.get(phoneme_name)

    def get_phoneme_names(self) -> list[str]:
        """Get list of available phoneme names"""
        return list(self.phonemes.keys())

    def interpolate_phonemes(
        self, phoneme1: PhonemeData, phoneme2: PhonemeData, interpolation_factor: float
    ) -> PhonemeData:
        """Interpolate between two phonemes"""
        factor = max(0.0, min(1.0, interpolation_factor))

        # Interpolate formant frequencies and bandwidths
        interp_freqs = (
            phoneme1.formant_frequencies * (1.0 - factor) + phoneme2.formant_frequencies * factor
        )
        interp_bws = (
            phoneme1.formant_bandwidths * (1.0 - factor) + phoneme2.formant_bandwidths * factor
        )

        # Interpolate duration
        interp_duration = phoneme1.duration_ms * (1.0 - factor) + phoneme2.duration_ms * factor

        return PhonemeData(
            f"{phoneme1.name}-{phoneme2.name}",
            interp_freqs.tolist(),
            interp_bws.tolist(),
            interp_duration,
        )


class FormantAnalyzer:
    """Real-time formant analysis for adaptive vocal synthesis"""

    def __init__(self, sample_rate: int = 44100, frame_size: int = 1024):
        self.sample_rate = sample_rate
        self.frame_size = frame_size

        # Analysis parameters
        self.min_formant_freq = 200.0  # Hz
        self.max_formant_freq = 5000.0  # Hz
        self.num_formants = 5

        # LPC analysis parameters
        self.lpc_order = 12

        # Analysis buffer
        self.analysis_buffer = np.zeros(frame_size)
        self.buffer_index = 0

    def analyze_frame(self, audio_frame: np.ndarray) -> list[tuple[float, float, float]]:
        """Analyze audio frame and return formant frequencies, bandwidths, and gains"""
        # Simple formant estimation using autocorrelation (simplified)
        # In a full implementation, this would use more sophisticated analysis

        formants = []

        # Estimate fundamental frequency (simplified)
        f0 = self._estimate_fundamental(audio_frame)

        # Estimate formants based on spectral peaks
        spectrum = np.abs(np.fft.rfft(audio_frame))
        freqs = np.fft.rfftfreq(len(audio_frame), 1.0 / self.sample_rate)

        # Find spectral peaks in formant range
        formant_candidates = []
        for i in range(1, len(spectrum) - 1):
            if (
                freqs[i] >= self.min_formant_freq
                and freqs[i] <= self.max_formant_freq
                and spectrum[i] > spectrum[i - 1]
                and spectrum[i] > spectrum[i + 1]
                and spectrum[i] > np.mean(spectrum) * 0.5
            ):  # Above noise floor
                formant_candidates.append((freqs[i], spectrum[i]))

        # Sort by amplitude and take top formants
        formant_candidates.sort(key=lambda x: x[1], reverse=True)
        formant_candidates = formant_candidates[: self.num_formants]

        # Convert to (frequency, bandwidth, gain) tuples
        for freq, amplitude in formant_candidates:
            # Estimate bandwidth (simplified)
            bandwidth = freq * 0.1  # Rough estimate: 10% of frequency
            gain = amplitude / np.max(spectrum) if np.max(spectrum) > 0 else 1.0
            formants.append((freq, bandwidth, gain))

        # Pad with default values if needed
        while len(formants) < self.num_formants:
            default_freq = 1000.0 + len(formants) * 500.0
            formants.append((default_freq, 100.0, 0.1))

        return formants

    def _estimate_fundamental(self, audio_frame: np.ndarray) -> float:
        """Estimate fundamental frequency using autocorrelation"""
        # Simplified autocorrelation-based F0 estimation
        corr = np.correlate(audio_frame, audio_frame, mode="full")
        corr = corr[len(corr) // 2 :]

        # Find first peak after the center
        min_period = int(self.sample_rate / self.max_formant_freq)
        max_period = int(self.sample_rate / self.min_formant_freq)

        peak_index = min_period
        max_corr = 0

        for i in range(min_period, min(max_period, len(corr))):
            if corr[i] > max_corr:
                max_corr = corr[i]
                peak_index = i

        return self.sample_rate / peak_index if peak_index > 0 else 100.0


class FDSPEngine:
    """
    Formant Dynamic Synthesis Processor (FDSP) Engine

    Advanced vocal synthesis engine with real-time formant manipulation,
    phoneme-based transitions, and adaptive analysis capabilities.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Core components
        self.filter_bank = FormantFilterBank(sample_rate, num_formants=5)
        self.vocal_database = VocalDatabase()
        self.formant_analyzer = FormantAnalyzer(sample_rate)

        # Synthesis parameters
        self.pitch = 220.0  # Hz
        self.formant_shift = 1.0  # Formant frequency multiplier
        self.tilt = 0.0  # Spectral tilt in dB/octave
        self.vibrato_rate = 5.0  # Hz
        self.vibrato_depth = 0.0  # Semitones

        # Phoneme transition state
        self.current_phoneme: PhonemeData | None = None
        self.target_phoneme: PhonemeData | None = None
        self.transition_progress = 0.0
        self.transition_samples = 0
        self.total_transition_samples = 0

        # Vibrato state
        self.vibrato_phase = 0.0

        # Breath noise parameters
        self.breath_level = 0.0
        self.breath_noise = np.random.normal(0, 1, 1024)  # Pre-generated noise
        self.breath_index = 0

        # Excitation source
        self.excitation_type = "pulse"  # 'pulse', 'noise', 'mixed'

        # Performance monitoring
        self.samples_processed = 0

    def set_phoneme(self, phoneme_name: str, transition_time_ms: float = 50.0):
        """Set target phoneme with transition"""
        target = self.vocal_database.get_phoneme(phoneme_name)
        if target:
            self.target_phoneme = target
            if self.current_phoneme is None:
                # First phoneme - set immediately
                self.current_phoneme = target
                self._apply_phoneme(target)
            else:
                # Start transition
                self.transition_progress = 0.0
                self.total_transition_samples = int(transition_time_ms * self.sample_rate / 1000.0)
                self.transition_samples = 0

    def process_sample(self, input_sample: float) -> float:
        """Process one sample through the FDSP engine"""
        self.samples_processed += 1

        # Handle phoneme transitions
        if (
            self.target_phoneme
            and self.current_phoneme
            and self.transition_samples < self.total_transition_samples
        ):
            self.transition_samples += 1
            self.transition_progress = self.transition_samples / self.total_transition_samples

            # Interpolate between phonemes
            interp_phoneme = self.vocal_database.interpolate_phonemes(
                self.current_phoneme, self.target_phoneme, self.transition_progress
            )
            self._apply_phoneme(interp_phoneme)

            # Check if transition complete
            if self.transition_samples >= self.total_transition_samples:
                self.current_phoneme = self.target_phoneme
                self.target_phoneme = None

        # Apply vibrato to formants
        if self.vibrato_depth > 0:
            vibrato_semitones = math.sin(self.vibrato_phase) * self.vibrato_depth
            vibrato_ratio = 2.0 ** (vibrato_semitones / 12.0)
            self.vibrato_phase += 2.0 * math.pi * self.vibrato_rate / self.sample_rate

            # Apply vibrato to formant frequencies
            current_freqs = []
            for filter in self.filter_bank.filters:
                vibrato_freq = filter.frequency * vibrato_ratio
                current_freqs.append(vibrato_freq)
            self.filter_bank.set_formant_frequencies(current_freqs)

        # Generate excitation source
        excitation = self._generate_excitation(input_sample)

        # Add breath noise
        if self.breath_level > 0:
            breath_sample = self.breath_noise[self.breath_index % len(self.breath_noise)]
            self.breath_index += 1
            excitation += breath_sample * self.breath_level

        # Process through formant filter bank
        output = self.filter_bank.process_sample(excitation)

        return output

    def _generate_excitation(self, input_sample: float) -> float:
        """Generate excitation source based on type"""
        if self.excitation_type == "pulse":
            # Pulse train at fundamental frequency
            pulse_phase = (self.samples_processed * self.pitch * 2.0 * math.pi) / self.sample_rate
            return math.sin(pulse_phase) * 0.5 + 0.5  # Half-wave rectified sine

        elif self.excitation_type == "noise":
            # White noise
            return np.random.normal(0, 1)

        elif self.excitation_type == "mixed":
            # Mix of pulse and noise
            pulse_phase = (self.samples_processed * self.pitch * 2.0 * math.pi) / self.sample_rate
            pulse = math.sin(pulse_phase) * 0.3
            noise = np.random.normal(0, 0.7)
            return pulse + noise

        else:
            # Default to input sample
            return input_sample

    def _apply_phoneme(self, phoneme: PhonemeData):
        """Apply phoneme parameters to filter bank"""
        # Apply formant shift
        shifted_freqs = phoneme.formant_frequencies * self.formant_shift

        # Set formant frequencies and bandwidths
        self.filter_bank.set_formant_frequencies(shifted_freqs.tolist())
        self.filter_bank.set_formant_bandwidths(phoneme.formant_bandwidths.tolist())

        # Set spectral tilt
        self.filter_bank.set_tilt(self.tilt)

    def set_pitch(self, pitch_hz: float):
        """Set fundamental pitch in Hz"""
        self.pitch = max(50.0, min(1000.0, pitch_hz))

    def set_formant_shift(self, shift_ratio: float):
        """Set formant frequency shift ratio"""
        self.formant_shift = max(0.5, min(2.0, shift_ratio))

    def set_tilt(self, tilt_db: float):
        """Set spectral tilt in dB/octave"""
        self.tilt = max(-12.0, min(12.0, tilt_db))

    def set_vibrato(self, rate_hz: float, depth_semitones: float):
        """Set vibrato parameters"""
        self.vibrato_rate = max(0.1, min(20.0, rate_hz))
        self.vibrato_depth = max(0.0, min(2.0, depth_semitones))

    def set_breath_level(self, level: float):
        """Set breath noise level (0.0 to 1.0)"""
        self.breath_level = max(0.0, min(1.0, level))

    def set_excitation_type(self, exc_type: str):
        """Set excitation source type"""
        if exc_type in ["pulse", "noise", "mixed"]:
            self.excitation_type = exc_type

    def analyze_audio(self, audio_frame: np.ndarray) -> list[tuple[float, float, float]]:
        """Analyze audio frame and return formant information"""
        return self.formant_analyzer.analyze_frame(audio_frame)

    def reset(self):
        """Reset engine state"""
        self.filter_bank.reset()
        self.current_phoneme = None
        self.target_phoneme = None
        self.transition_progress = 0.0
        self.transition_samples = 0
        self.total_transition_samples = 0
        self.vibrato_phase = 0.0
        self.breath_index = 0
        self.samples_processed = 0

    def get_engine_info(self) -> dict[str, Any]:
        """Get engine status and parameters"""
        return {
            "sample_rate": self.sample_rate,
            "pitch": self.pitch,
            "formant_shift": self.formant_shift,
            "tilt": self.tilt,
            "vibrato_rate": self.vibrato_rate,
            "vibrato_depth": self.vibrato_depth,
            "breath_level": self.breath_level,
            "excitation_type": self.excitation_type,
            "current_phoneme": self.current_phoneme.name if self.current_phoneme else None,
            "transition_active": self.target_phoneme is not None,
            "transition_progress": self.transition_progress,
            "available_phonemes": self.vocal_database.get_phoneme_names(),
        }

    # ========== REGION-BASED ARCHITECTURE IMPLEMENTATION ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get FDSP preset information with proper region descriptors.

        Args:
            bank: Preset bank number (0-127)
            program: Preset program number (0-127)

        Returns:
            PresetInfo with region descriptors, or None if preset not found
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # FDSP uses formant-based vocal synthesis
        # Each program defines a set of formant configurations (phonemes)
        preset_name = self.vocal_database.get_preset_name(bank, program)
        if not preset_name:
            preset_name = f"FDSP Vocal {bank}:{program}"

        # Create region descriptors for full keyboard range
        # FDSP is monophonic but supports full keyboard range
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type=self.get_engine_type(),
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                "phoneme_set": preset_name,
                "formant_count": 5,  # Standard 5-formant vocal model
                "excitation_type": "mixed",  # Mixed noise/periodic
                "breathiness": 0.0,
                "vibrato_rate": 5.0,  # Hz
                "vibrato_depth": 0.3,
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=preset_name,
            engine_type=self.get_engine_type(),
            region_descriptors=[descriptor],
            is_monophonic=True,
            category="vocal_synthesis",
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """
        Get all region descriptors for a preset.

        Args:
            bank: Preset bank number
            program: Preset program number

        Returns:
            List of RegionDescriptor objects
        """
        preset_info = self.get_preset_info(bank, program)
        return preset_info.region_descriptors if preset_info else []

    def create_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create FDSP region instance from descriptor.

        Args:
            descriptor: Region descriptor with parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance for FDSP synthesis
        """
        from ..partial.fdsp_region import FDSPRegion

        # Create FDSP region with proper initialization
        region = FDSPRegion(descriptor, sample_rate)

        # Initialize the region (loads formant data, creates partial)
        if not region.initialize():
            raise RuntimeError("Failed to initialize FDSP region")

        return region

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for region (FDSP is algorithmic, no samples needed).

        Args:
            region: Region to load sample for

        Returns:
            True (FDSP doesn't use samples)
        """
        # FDSP is formant synthesis - no sample loading required
        # Formant data is loaded during region initialization
        return True


class FDSPSynthesisEngine(SynthesisEngine):
    """
    FDSP Synthesis Engine - Implements SynthesisEngine interface for formant synthesis

    Provides vocal and wind instrument synthesis through the FDSP engine,
    integrated with the standard synthesis engine framework.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize FDSP synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)

        # Create FDSP engine instance
        self.fdsp_engine = FDSPEngine(sample_rate)

        # Voice management
        self.active_voices: dict[int, dict[str, Any]] = {}
        self.next_voice_id = 1

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples for a note using FDSP synthesis.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Convert MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply pitch modulation
        pitch_modulation = modulation.get("pitch_bend", 0.0) + modulation.get("pitch_mod", 0.0)
        frequency *= 2.0 ** (pitch_modulation / 12.0)

        # Set FDSP engine parameters
        self.fdsp_engine.set_pitch(frequency)

        # Apply formant shift based on modulation
        formant_shift = 1.0 + modulation.get("formant_shift", 0.0) * 0.5
        self.fdsp_engine.set_formant_shift(formant_shift)

        # Apply vibrato
        vibrato_rate = modulation.get("vibrato_rate", 5.0)
        vibrato_depth = modulation.get("vibrato_depth", 0.0)
        self.fdsp_engine.set_vibrato(vibrato_rate, vibrato_depth)

        # Set breath level based on velocity/modulation
        breath_level = (1.0 - velocity / 127.0) * 0.1  # More breath at lower velocities
        self.fdsp_engine.set_breath_level(breath_level)

        # Generate mono audio block
        output_samples = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Process one sample (using 0.0 as input for pure synthesis)
            sample = self.fdsp_engine.process_sample(0.0)
            output_samples[i] = sample

        # Convert to stereo
        stereo_output = np.column_stack((output_samples, output_samples))

        return stereo_output

    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by FDSP engine.

        FDSP supports the full MIDI range for vocal synthesis.
        """
        return 0 <= note <= 127

    def get_engine_info(self) -> dict[str, Any]:
        """Get FDSP engine information and capabilities."""
        return {
            "name": "FDSP Formant Synthesis",
            "type": "fdsp",
            "capabilities": [
                "formant_synthesis",
                "phoneme_transition",
                "vibrato",
                "breath_noise",
                "vocal_modeling",
                "wind_instrument_modeling",
            ],
            "formats": [],
            "polyphony": 32,  # FDSP is more CPU intensive, limit polyphony
            "parameters": [
                "pitch",
                "formant_shift",
                "tilt",
                "vibrato_rate",
                "vibrato_depth",
                "breath_level",
                "phoneme",
                "excitation_type",
            ],
        }

    # ========== REGION-BASED ARCHITECTURE IMPLEMENTATION ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get FDSP preset information with proper region descriptors.

        Args:
            bank: Preset bank number (0-127)
            program: Preset program number (0-127)

        Returns:
            PresetInfo with region descriptors for FDSP synthesis
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # FDSP uses formant-based vocal synthesis (second engine instance)
        preset_name = f"FDSP {bank}:{program}"

        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="fdsp",
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                "phoneme_set": preset_name,
                "formant_count": 5,
                "excitation_type": "mixed",
                "breathiness": 0.0,
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=preset_name,
            engine_type="fdsp",
            region_descriptors=[descriptor],
            is_monophonic=True,
            category="vocal_synthesis",
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """Get all region descriptors for FDSP preset."""
        preset_info = self.get_preset_info(bank, program)
        return preset_info.region_descriptors if preset_info else []

    def create_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create region instance. Base implementation wraps with S.Art2.
        """
        return self._create_base_region(descriptor, sample_rate)

    def _create_base_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create FDSPRegion base region without S.Art2 wrapper.

        Args:
            descriptor: Region descriptor
            sample_rate: Audio sample rate in Hz

        Returns:
            FDSPRegion instance
        """
        from ..partial.fdsp_region import FDSPRegion

        return FDSPRegion(descriptor, sample_rate)

    def load_sample_for_region(self, region: IRegion) -> bool:
        return True

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int) -> SynthesisPartial:
        """Create a partial instance for FDSP synthesis."""
        # Import here to avoid circular imports

        # Create FDSP partial with default parameters
        fdsp_partial = FDSPSynthesisPartial(
            partial_params.get("note", 60), partial_params.get("velocity", 64), sample_rate
        )

        # Apply partial-specific parameters
        if "phoneme" in partial_params:
            fdsp_partial.set_phoneme(partial_params["phoneme"])
        if "formant_shift" in partial_params:
            fdsp_partial.set_formant_shift(partial_params["formant_shift"])

        return fdsp_partial

    def get_engine_type(self) -> str:
        """Get the engine type identifier."""
        return "fdsp"

    def get_max_polyphony(self) -> int:
        """Get maximum polyphony supported by FDSP engine."""
        return 32  # Limited due to CPU intensity of formant processing

    def supports_modulation(self, modulation_type: str) -> bool:
        """Check if FDSP engine supports a specific modulation type."""
        return modulation_type in ["pitch", "formant_shift", "vibrato", "breath"]

    def get_parameter_info(self, parameter_name: str) -> dict[str, Any] | None:
        """Get information about an FDSP parameter."""
        param_info = {
            "pitch": {"type": "float", "range": [50.0, 1000.0], "default": 220.0, "unit": "Hz"},
            "formant_shift": {
                "type": "float",
                "range": [0.5, 2.0],
                "default": 1.0,
                "unit": "ratio",
            },
            "tilt": {"type": "float", "range": [-12.0, 12.0], "default": 0.0, "unit": "dB/octave"},
            "vibrato_rate": {"type": "float", "range": [0.1, 20.0], "default": 5.0, "unit": "Hz"},
            "vibrato_depth": {
                "type": "float",
                "range": [0.0, 2.0],
                "default": 0.0,
                "unit": "semitones",
            },
            "breath_level": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "unit": "level"},
            "phoneme": {"type": "string", "range": None, "default": "ə", "unit": "phoneme"},
            "excitation_type": {
                "type": "string",
                "range": ["pulse", "noise", "mixed"],
                "default": "pulse",
                "unit": "type",
            },
        }
        return param_info.get(parameter_name)

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize FDSP parameters."""
        validated = {}

        # Validate each parameter
        for param_name, param_value in parameters.items():
            param_info = self.get_parameter_info(param_name)
            if param_info:
                param_type = param_info["type"]
                param_range = param_info["range"]

                if param_type == "float" and param_range:
                    validated[param_name] = max(
                        param_range[0], min(param_range[1], float(param_value))
                    )
                elif param_type == "string":
                    if param_range and param_value in param_range:
                        validated[param_name] = param_value
                    elif param_name == "phoneme":
                        # Allow any phoneme string
                        validated[param_name] = str(param_value)
                else:
                    validated[param_name] = param_value
            else:
                # Pass through unknown parameters
                validated[param_name] = param_value

        return validated

    def reset(self) -> None:
        """Reset FDSP engine to clean state."""
        self.fdsp_engine.reset()
        self.active_voices.clear()
        self.next_voice_id = 1

    def get_memory_usage(self) -> dict[str, Any]:
        """Get FDSP engine memory usage."""
        return {
            "samples_loaded": 0,  # FDSP is generative, no samples loaded
            "memory_used_mb": 0.1,  # Minimal memory usage
            "cache_efficiency": 1.0,  # Always 100% efficient (generative)
        }


class FDSPSynthesisPartial:
    """
    FDSP Synthesis Partial - Represents a single voice in FDSP synthesis

    Manages the state of an individual FDSP voice with its own parameters
    and synthesis state.
    """

    def __init__(self, note: int, velocity: int, sample_rate: int):
        """
        Initialize FDSP partial.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            sample_rate: Audio sample rate
        """
        self.note = note
        self.velocity = velocity
        self.sample_rate = sample_rate

        # FDSP-specific parameters
        self.frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))
        self.formant_shift = 1.0
        self.phoneme = "ə"  # Default to schwa
        self.vibrato_rate = 5.0
        self.vibrato_depth = 0.0
        self.breath_level = 0.0

        # Create dedicated FDSP engine for this partial
        self.fdsp_engine = FDSPEngine(sample_rate)
        self.fdsp_engine.set_pitch(self.frequency)
        self.fdsp_engine.set_phoneme(self.phoneme)

        # State
        self.is_active = True
        self.age = 0  # Sample counter

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this partial.

        Args:
            block_size: Number of samples to generate

        Returns:
            Mono audio buffer as float32 array
        """
        if not self.is_active:
            return np.zeros(block_size, dtype=np.float32)

        output_samples = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Process one sample
            sample = self.fdsp_engine.process_sample(0.0)
            output_samples[i] = sample
            self.age += 1

        return output_samples

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """Apply modulation to this partial."""
        # Apply pitch modulation
        pitch_modulation = modulation.get("pitch_bend", 0.0) + modulation.get("pitch_mod", 0.0)
        modulated_freq = self.frequency * 2.0 ** (pitch_modulation / 12.0)
        self.fdsp_engine.set_pitch(modulated_freq)

        # Apply formant shift modulation
        formant_mod = modulation.get("formant_shift", 0.0)
        self.fdsp_engine.set_formant_shift(self.formant_shift + formant_mod)

        # Apply vibrato
        vibrato_rate = modulation.get("vibrato_rate", self.vibrato_rate)
        vibrato_depth = modulation.get("vibrato_depth", self.vibrato_depth)
        self.fdsp_engine.set_vibrato(vibrato_rate, vibrato_depth)

    def set_phoneme(self, phoneme: str) -> None:
        """Set phoneme for this partial."""
        self.phoneme = phoneme
        self.fdsp_engine.set_phoneme(phoneme)

    def set_formant_shift(self, shift: float) -> None:
        """Set formant shift for this partial."""
        self.formant_shift = max(0.5, min(2.0, shift))
        self.fdsp_engine.set_formant_shift(self.formant_shift)

    def release(self) -> None:
        """Release this partial (begin decay)."""
        self.is_active = False

    def is_finished(self) -> bool:
        """Check if this partial has finished playing."""
        return not self.is_active


# Export classes
__all__ = [
    "FDSPEngine",
    "FDSPSynthesisEngine",
    "FDSPSynthesisPartial",
    "FormantAnalyzer",
    "FormantFilter",
    "FormantFilterBank",
    "PhonemeData",
    "VocalDatabase",
]
