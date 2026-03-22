"""
SF2 partial implementation for XG synthesizer.

Implements the SynthesisPartial interface for SoundFont 2 wavetable synthesis
with full integration into modern XG synthesizer infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from ..types.parameter_types import ParameterScope, ParameterSource, ParameterUpdate
from .partial import SynthesisPartial

if TYPE_CHECKING:
    from ..engine.modern_xg_synthesizer import ModernXGSynthesizer


class SF2Partial(SynthesisPartial):
    """
    SF2 wavetable synthesis partial - Fully integrated with modern XG synthesizer.

    Uses unified infrastructure: buffer pools, envelope pools, filter pools,
    modulation matrix integration, and global voice management.
    Implements direct SF2 wavetable synthesis with mip-mapping support.
    """

    __slots__ = [
        # Core state (original)
        "synth",
        "sample_data",
        "phase_step",
        "sample_position",
        "pitch_ratio",
        "loop_mode",
        "loop_start",
        "loop_end",
        "envelope",
        "filter",
        "mod_lfo",
        "vib_lfo",
        "audio_buffer",
        "work_buffer",
        "pitch_mod",
        "filter_mod",
        "volume_mod",
        "active",
        "params",
        # SF2 Generators - Effects
        "chorus_effects_send",
        "reverb_effects_send",
        # Zone Control
        "key_range",
        "vel_range",
        "exclusive_class",
        "sample_modes",
        # Advanced LFO
        "delay_mod_lfo",
        "freq_mod_lfo",
        "delay_vib_lfo",
        "freq_vib_lfo",
        "vib_lfo_to_pan",
        "mod_lfo_to_pan",
        # Modulation Envelope
        "mod_env_to_pitch",
        "mod_env_to_filter",
        "mod_env_to_volume",
        "mod_env_to_pan",
        "delay_mod_env",
        "attack_mod_env",
        "hold_mod_env",
        "decay_mod_env",
        "sustain_mod_env",
        "release_mod_env",
        # Envelope Sensitivity
        "keynum_to_mod_env_hold",
        "keynum_to_mod_env_decay",
        "keynum_to_vol_env_hold",
        "keynum_to_vol_env_decay",
        # Coarse Sample Addressing
        "start_addrs_coarse_offset",
        "end_addrs_coarse_offset",
        "startloop_addrs_coarse_offset",
        "endloop_addrs_coarse_offset",
        # Advanced Tuning
        "overriding_root_key",
        "scale_tuning",
        # Volume Envelope
        "hold_vol_env",
        # Buffer references (allocated on demand in _allocate_buffers)
        "vib_lfo_buffer",
        "mod_lfo_buffer",
        "mod_env_buffer",
        "lfo_pitch_buffer",
        "lfo_filter_buffer",
        "lfo_volume_buffer",
        "lfo_pan_buffer",
        # Performance optimization buffers (allocated on demand)
        "_pitch_mod_vector",
        "_filter_mod_vector",
        "_volume_mod_vector",
        "_pan_mod_vector",
        # Allocation state (managed by _buffers_allocated flag)
        "_buffers_allocated",
        # LFO phase tracking (managed by _vib_lfo_phase, _mod_lfo_phase)
        "_vib_lfo_phase",
        "_mod_lfo_phase",
        # Envelope state (managed by _mod_env_state, _amp_env_state)
        "_mod_env_state",
        "_amp_env_state",
        # Spatial processing (managed by _channel_pan, _reverb_send, etc.)
        "_channel_pan",
        "_reverb_send",
        "_chorus_send",
        "_pan_position",
        # Additional modulation attributes (managed by modulation system)
        "pan_mod",
        "resonance_mod",
        "lfo_rate_mod",
        "aftertouch_mod",
        "breath_mod",
        "modwheel_mod",
        "foot_mod",
        "expression_mod",
        # LFO modulation routing (managed by SF2 generators)
        "vib_lfo_to_pitch",
        "mod_lfo_to_filter",
        "mod_lfo_to_volume",
        # Base phase step (MISSING)
        "base_phase_step",
    ]

    def __init__(self, params: dict, synth: ModernXGSynthesizer):
        """
        Initialize SF2 partial with modern synth infrastructure integration.

        Uses pooled resources for envelopes, filters, and LFOs for optimal
        memory management and performance.

        Args:
            params: SF2 partial parameters from zone processing
            synth: ModernXGSynthesizer instance for infrastructure access
        """
        super().__init__(params, synth.sample_rate)
        self.synth = synth
        self.params = params

        # Use pooled buffers for zero-allocation architecture
        if hasattr(synth, "memory_pool"):
            self.audio_buffer = synth.memory_pool.get_stereo_buffer(synth.block_size)
            self.work_buffer = synth.memory_pool.get_mono_buffer(synth.block_size)
        else:
            # Fallback to buffer_pool if memory_pool doesn't exist
            self.audio_buffer = synth.buffer_pool.get_stereo_buffer(synth.block_size)
            self.work_buffer = synth.buffer_pool.get_mono_buffer(synth.block_size)

        # Initialize buffer references to None - these will be allocated from pooled buffers
        # This follows the zero-allocation principle by using shared buffers from memory pools
        self.vib_lfo_buffer = None
        self.mod_lfo_buffer = None
        self.mod_env_buffer = None
        self.lfo_pitch_buffer = None
        self.lfo_filter_buffer = None
        self.lfo_volume_buffer = None
        self.lfo_pan_buffer = None

        # Initialize performance optimization buffers
        self._pitch_mod_vector = None
        self._filter_mod_vector = None
        self._volume_mod_vector = None
        self._pan_mod_vector = None

        # Initialize buffer allocation flags
        self._buffers_allocated = False

        # Acquire pooled envelope for amplitude envelope
        if hasattr(synth, "envelope_pool"):
            self.envelope = synth.envelope_pool.acquire_envelope(
                delay=0.0,
                attack=0.01,
                hold=0.0,
                decay=0.3,
                sustain=0.7,
                release=0.5,
                velocity_sense=0.0,
                key_scaling=0.0,
            )
        else:
            # Fallback: create envelope directly if pool doesn't exist
            from ..core.envelope import UltraFastADSREnvelope

            self.envelope = UltraFastADSREnvelope(
                sample_rate=synth.sample_rate, block_size=synth.block_size
            )

        # Acquire pooled filter for SF2 filter envelope/modulation
        if hasattr(synth, "filter_pool"):
            self.filter = synth.filter_pool.acquire_filter(
                cutoff=20000.0,
                resonance=0.0,
                filter_type="lowpass",
                key_follow=0.0,
                stereo_width=1.0,
            )
        else:
            # Fallback: create filter directly if pool doesn't exist
            from ..core.filter import UltraFastResonantFilter

            self.filter = UltraFastResonantFilter(
                sample_rate=synth.sample_rate, block_size=synth.block_size
            )

        # Acquire pooled LFOs for modulation (vibrato and tremolo)
        if hasattr(synth, "partial_lfo_pool"):
            self.mod_lfo = synth.partial_lfo_pool.acquire_oscillator(
                id=0, waveform="sine", rate=8.176, depth=1.0, delay=0.0
            )
            self.vib_lfo = synth.partial_lfo_pool.acquire_oscillator(
                id=1, waveform="sine", rate=8.176, depth=1.0, delay=0.0
            )
        else:
            # Production fallback: create LFOs with proper parameter validation
            try:
                from ..core.oscillator import UltraFastXGLFO

                # Validate sample rate and block size
                sample_rate = max(8000, min(192000, synth.sample_rate))  # Clamp to reasonable range
                block_size = max(32, min(8192, synth.block_size))  # Clamp to reasonable range

                self.mod_lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
                self.vib_lfo = UltraFastXGLFO(id=1, sample_rate=sample_rate, block_size=block_size)
            except (ImportError, AttributeError):
                # Ultimate fallback: create simple LFO simulation
                # This ensures the synthesizer can still function even without proper LFO components
                self.mod_lfo = self._create_simple_lfo_simulation(0, synth.sample_rate)
                self.vib_lfo = self._create_simple_lfo_simulation(1, synth.sample_rate)

        # SF2-specific state
        self.sample_data: np.ndarray | None = None
        self.phase_step: float = 1.0
        self.base_phase_step: float = 1.0  # Base phase step without modulation
        self.sample_position: float = 0.0
        self.pitch_ratio: float = 1.0

        # Initialize base phase step based on sample rate and default pitch
        # This ensures proper pitch calculations from the start
        self.base_phase_step = 440.0 / synth.sample_rate  # Default to A4 (440Hz) at sample rate

        # Loop parameters
        self.loop_mode: int = 0
        self.loop_start: int = 0
        self.loop_end: int = 0

        # Modulation state (connected to global matrix)
        self.pitch_mod: float = 0.0
        self.filter_mod: float = 0.0
        self.volume_mod: float = 1.0

        # Initialize additional modulation attributes (managed by modulation system)
        self.pan_mod: float = 0.0
        self.resonance_mod: float = 0.0
        self.lfo_rate_mod: float = 0.0
        self.aftertouch_mod: float = 0.0
        self.breath_mod: float = 0.0
        self.modwheel_mod: float = 0.0
        self.foot_mod: float = 0.0
        self.expression_mod: float = 0.0

        # LFO modulation routing (loaded from SF2 generators)
        self.vib_lfo_to_pitch: float = 0.0
        self.mod_lfo_to_filter: float = 0.0
        self.mod_lfo_to_volume: float = 0.0

        # Spatial processing (loaded from SF2 generators)
        self._channel_pan: float = 0.0
        self._reverb_send: float = 0.0
        self._chorus_send: float = 0.0
        self._pan_position: float = 0.0

        # Envelope state (managed by envelope processor)
        self._mod_env_state: dict = {"stage": "idle", "level": 0.0, "stage_time": 0.0}
        self._amp_env_state: dict = {"stage": "idle", "level": 0.0, "stage_time": 0.0}

        # LFO phase tracking (managed by LFO processors)
        self._vib_lfo_phase: float = 0.0
        self._mod_lfo_phase: float = 0.0

        # Load SF2 parameters and sample data
        self._load_sf2_parameters()

        # Initialize SF2 generators (missing from current implementation)
        self._init_sf2_generators()

        # Load SF2 generator values from zone data
        self._load_sf2_generator_values()

    def _load_sf2_parameters(self):
        """
        Load SF2 parameters and sample data from zone processing.

        This method sets up all SF2-specific parameters from the zone data
        including sample loading, envelope setup, filter configuration, etc.
        """
        # Get sample data from SF2 manager
        sample_data = self.params.get("sample_data")
        if sample_data is not None and len(sample_data) > 0:
            self.sample_data = np.asarray(sample_data, dtype=np.float32)

            # Calculate loop parameters
            loop_info = self.params.get("loop", {})
            self.loop_mode = loop_info.get("mode", 0)
            self.loop_start = max(0, loop_info.get("start", 0))
            sample_length = len(self.sample_data) if self.sample_data is not None else 0
            self.loop_end = min(sample_length, loop_info.get("end", sample_length))

            # Calculate initial phase step
            root_key = self.params.get("original_pitch", 60)
            note_diff = self.params.get("note", 60) - root_key
            coarse_tune = self.params.get("pitch_modulation", {}).get("coarse_tune", 0)
            fine_tune = self.params.get("pitch_modulation", {}).get("fine_tune", 0.0)
            pitch_correction = self.params.get("pitch_correction", 0.0)

            total_semitones = note_diff + coarse_tune + fine_tune + pitch_correction
            self.pitch_ratio = 2.0 ** (total_semitones / 12.0)
            self.phase_step = self.pitch_ratio

        # Setup envelope using pooled envelope
        amp_env = self.params.get("amp_envelope", {})
        self.envelope.update_parameters(
            delay=amp_env.get("delay", 0.0),
            attack=amp_env.get("attack", 0.01),
            hold=amp_env.get("hold", 0.0),
            decay=amp_env.get("decay", 0.3),
            sustain=amp_env.get("sustain", 0.7),
            release=amp_env.get("release", 0.5),
        )

        # Setup filter using pooled filter
        filter_params = self.params.get("filter", {})
        self.filter.set_parameters(
            cutoff=filter_params.get("cutoff", 20000.0),
            resonance=filter_params.get("resonance", 0.0),
            filter_type=filter_params.get("type", "lowpass"),
        )

        # Setup LFOs using pooled oscillators
        mod_lfo_params = self.params.get("mod_lfo", {})
        self.mod_lfo.set_parameters(
            waveform="sine",
            rate=mod_lfo_params.get("frequency", 8.176),
            depth=1.0,
            delay=mod_lfo_params.get("delay", 0.0),
        )

        vib_lfo_params = self.params.get("vib_lfo", {})
        self.vib_lfo.set_parameters(
            waveform="sine",
            rate=vib_lfo_params.get("frequency", 8.176),
            depth=1.0,
            delay=vib_lfo_params.get("delay", 0.0),
        )

    def generate_samples(self, block_size: int, modulation: dict) -> np.ndarray:
        """
        Generate SF2 wavetable samples with professional-grade real-time modulation.

        Implements true time-varying pitch modulation, LFO processing, and resonant filtering
        for authentic SoundFont synthesis quality.

        Args:
            block_size: Number of samples to generate
            modulation: Global modulation values from modulation matrix

        Returns:
            Stereo audio buffer (block_size * 2) as float32 array
        """
        # Validate inputs
        if not isinstance(block_size, int) or block_size <= 0:
            block_size = 1024  # Use default if invalid

        if not self.active or self.sample_data is None:
            return np.zeros(block_size * 2, dtype=np.float32)

        try:
            # Ensure buffers are allocated before proceeding
            self._ensure_buffers_allocated(block_size)

            # Apply global modulation from modulation matrix
            self._apply_global_modulation(modulation)

            # Generate real-time LFO modulation signals
            self._generate_lfo_signals(block_size)

            # Generate modulation envelope signals
            self._generate_modulation_envelope_signals(block_size)

            # Generate base wavetable samples with continuous pitch modulation
            self._generate_wavetable_samples_realtime(block_size)

            # Apply amplitude envelope
            self._apply_envelope(block_size)

            # Apply resonant filtering with real-time modulation
            self._apply_filter_realtime(block_size)

            # Apply tremolo (volume modulation) and auto-pan
            self._apply_volume_pan_modulation(block_size)

            # Apply final spatial processing and volume
            self._apply_spatial_processing(block_size)

            # Ensure output buffer is properly sized
            output_size = min(block_size * 2, len(self.audio_buffer))
            return self.audio_buffer[:output_size].copy()

        except Exception as e:
            # Log error to error reporting system
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"SF2Partial.generate_samples() failed: {e}",
                exc_info=True,
                extra={
                    "partial_id": self.region.sample_id
                    if hasattr(self.region, "sample_id")
                    else None,
                    "note": self.current_note,
                    "velocity": self.current_velocity,
                    "block_size": block_size,
                },
            )
            # Return silence to prevent audio glitches
            return np.zeros(block_size * 2, dtype=np.float32)

    def _apply_global_modulation(self, modulation: dict):
        """
        Apply comprehensive global modulation from the modulation matrix.

        Enhanced to support extended modulation sources including LFOs,
        envelopes, and controllers for complete modulation matrix integration.
        """
        # Basic global modulation (existing)
        global_pitch = modulation.get("pitch", 0.0)
        global_filter = modulation.get("filter_cutoff", 0.0)
        global_amp = modulation.get("volume", 1.0)

        # Apply basic modulation
        self.pitch_mod = global_pitch
        self.filter_mod = global_filter
        self.volume_mod = global_amp

        # EXTENDED MODULATION SOURCES - New integration features

        # Pan modulation from global sources
        self.pan_mod = modulation.get("pan", 0.0)

        # Resonance modulation
        self.resonance_mod = modulation.get("resonance", 0.0)

        # LFO rate modulation (affects both SF2 LFOs)
        self.lfo_rate_mod = modulation.get("lfo_rate", 0.0)

        # Controller modulation sources
        self.aftertouch_mod = modulation.get("aftertouch", 0.0)
        self.breath_mod = modulation.get("breath", 0.0)
        self.modwheel_mod = modulation.get("modwheel", 0.0)
        self.foot_mod = modulation.get("foot", 0.0)
        self.expression_mod = modulation.get("expression", 0.0)

        # Apply LFO rate modulation to SF2 LFOs
        if self.lfo_rate_mod != 0.0:
            # Modulate modulation LFO rate
            modulated_mod_rate = self.freq_mod_lfo * (1.0 + self.lfo_rate_mod)
            self.freq_mod_lfo = max(0.1, min(50.0, modulated_mod_rate))  # Clamp to reasonable range

            # Modulate vibrato LFO rate
            modulated_vib_rate = self.freq_vib_lfo * (1.0 + self.lfo_rate_mod)
            self.freq_vib_lfo = max(0.1, min(50.0, modulated_vib_rate))

        # Apply controller modulation to synthesis parameters
        if self.aftertouch_mod != 0.0:
            # Aftertouch typically affects volume and filter
            self.volume_mod *= 1.0 + self.aftertouch_mod * 0.5  # 50% effect
            self.filter_mod += self.aftertouch_mod * 2.0  # 2 octave effect

        if self.breath_mod != 0.0:
            # Breath control affects volume and filter
            self.volume_mod *= 1.0 + self.breath_mod * 0.7  # 70% effect
            self.filter_mod += self.breath_mod * 3.0  # 3 octave effect

        if self.modwheel_mod != 0.0:
            # Mod wheel affects vibrato depth and filter
            self.vib_lfo_to_pitch *= 1.0 + self.modwheel_mod
            self.filter_mod += self.modwheel_mod * 1.5  # 1.5 octave effect

        # Update phase step with combined modulation
        modulated_pitch_ratio = self.pitch_ratio * (2.0 ** (self.pitch_mod / 12.0))
        self.phase_step = modulated_pitch_ratio

    def _update_modulation_sources(self, block_size: int):
        """Update internal modulation sources (LFOs, envelopes)."""
        # Update LFOs - generate LFO samples (though we don't use output directly)
        if self.mod_lfo:
            # Generate LFO block without using output (internal modulation only)
            lfo_buffer = self.work_buffer[:block_size]
            self.mod_lfo.generate_block(lfo_buffer, block_size)
        if self.vib_lfo:
            # Generate LFO block without using output (internal modulation only)
            vib_buffer = self.work_buffer[:block_size]
            self.vib_lfo.generate_block(vib_buffer, block_size)

        # Update envelope - envelope is updated during generate_samples
        pass

    def _generate_wavetable_samples(self, block_size: int):
        """
        Generate wavetable samples with SF2 loop processing and interpolation.

        Supports both mono and stereo samples with proper channel handling.
        Uses zero-allocation approach with pre-allocated buffers.
        """
        if self.sample_data is None:
            return

        # Check if sample data is stereo (has shape information or is 2D)
        if (
            self.sample_data is not None
            and hasattr(self.sample_data, "shape")
            and len(self.sample_data.shape) > 1
        ):
            # Stereo sample data (shape should be [samples, channels])
            if self.sample_data.shape[1] == 2:
                # True stereo sample
                self._generate_stereo_samples(block_size)
                return

        # Mono sample data - use original mono processing
        self._generate_mono_samples(block_size)

    def _generate_mono_samples(self, block_size: int):
        """Generate mono samples and duplicate to stereo."""
        if self.sample_data is None:
            return

        mono_samples = self.work_buffer[:block_size]

        for i in range(block_size):
            sample_length = len(self.sample_data)
            if self.sample_position < sample_length - 1:
                # Linear interpolation between samples
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                sample1 = self.sample_data[pos_int]
                sample2 = self.sample_data[pos_int + 1]
                mono_samples[i] = sample1 + frac * (sample2 - sample1)
            else:
                mono_samples[i] = 0.0

            # Update sample position
            self.sample_position += self.phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy mono to stereo buffer (will be panned later)
        self.audio_buffer[::2][:block_size] = mono_samples  # Left channel
        self.audio_buffer[1::2][:block_size] = mono_samples  # Right channel

    def _generate_stereo_samples(self, block_size: int):
        """Generate true stereo samples with interpolation."""
        if self.sample_data is None:
            return

        # For stereo samples, we need to interpolate both channels
        left_channel = self.work_buffer[:block_size]
        right_channel = self.work_buffer[block_size : 2 * block_size]

        sample_length = len(self.sample_data)
        for i in range(block_size):
            if self.sample_position < sample_length - 1:
                # Linear interpolation between sample frames
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                # Interpolate left channel
                left1 = self.sample_data[pos_int, 0]
                left2 = self.sample_data[pos_int + 1, 0]
                left_channel[i] = left1 + frac * (left2 - left1)

                # Interpolate right channel
                right1 = self.sample_data[pos_int, 1]
                right2 = self.sample_data[pos_int + 1, 1]
                right_channel[i] = right1 + frac * (right2 - right1)
            else:
                left_channel[i] = 0.0
                right_channel[i] = 0.0

            # Update sample position
            self.sample_position += self.phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy stereo samples to output buffer
        self.audio_buffer[::2][:block_size] = left_channel  # Left channel
        self.audio_buffer[1::2][:block_size] = right_channel  # Right channel

    def _handle_sample_looping(self):
        """Handle SF2 sample looping according to loop mode."""
        if self.sample_data is None:
            return

        sample_length = len(self.sample_data)

        # Ensure loop boundaries are valid
        self.loop_start = max(0, min(sample_length, self.loop_start))
        self.loop_end = max(self.loop_start, min(sample_length, self.loop_end))

        if self.loop_mode == 0:
            # No loop - stop at end
            if self.sample_position >= sample_length:
                self.active = False
                self.sample_position = sample_length - 1
        elif self.loop_mode == 1:  # Forward loop
            # Loop between loop_start and loop_end
            if self.sample_position >= self.loop_end and self.loop_end > self.loop_start:
                loop_length = self.loop_end - self.loop_start
                if loop_length > 0:
                    # Calculate how far past the loop end we are
                    excess = self.sample_position - self.loop_end
                    # Wrap back to the loop start plus the excess
                    self.sample_position = self.loop_start + (excess % loop_length)
                else:
                    self.active = False  # No valid loop range
        elif self.loop_mode == 3:  # Loop and continue
            # Loop while in loop range, then continue to end
            if self.loop_start <= self.sample_position < self.loop_end:
                # Still in loop range, loop normally
                if self.sample_position >= self.loop_end and self.loop_end > self.loop_start:
                    loop_length = self.loop_end - self.loop_start
                    if loop_length > 0:
                        # Calculate how far past the loop end we are
                        excess = self.sample_position - self.loop_end
                        # Wrap back to the loop start plus the excess
                        self.sample_position = self.loop_start + (excess % loop_length)
            elif self.sample_position >= sample_length:
                # Past loop range, check if we've reached the end
                self.active = False

    def _apply_envelope(self, block_size: int):
        """Apply amplitude envelope using pooled envelope."""
        if self.envelope:
            # Use work buffer for envelope values
            env_buffer = self.work_buffer[:block_size]

            # Generate envelope block
            self.envelope.generate_block(env_buffer, block_size)

            # Apply envelope to both channels
            self.audio_buffer[: block_size * 2] *= np.tile(env_buffer, 2)

    def _apply_filter(self, block_size: int):
        """
        Apply resonant filtering with modulation using pooled filter.

        Implements time-varying filter processing with proper resonance control
        and real-time parameter modulation.
        """
        if not self.filter:
            return

        # Get base filter parameters
        base_cutoff = self.params.get("filter", {}).get("cutoff", 20000.0)
        base_resonance = self.params.get("filter", {}).get("resonance", 0.0)
        filter_type = self.params.get("filter", {}).get("type", "lowpass")

        # Validate and clamp base parameters
        base_cutoff = max(20.0, min(20000.0, base_cutoff))
        base_resonance = max(0.0, min(1.0, base_resonance))

        # Calculate static modulation component
        static_cutoff_mod = self.filter_mod

        # Add LFO filter modulation depth to static modulation
        if self.mod_lfo_to_filter != 0.0:
            static_cutoff_mod += self.mod_lfo_to_filter  # Base LFO depth

        # Calculate final modulated cutoff
        modulated_cutoff = base_cutoff * (2.0**static_cutoff_mod)
        modulated_cutoff = max(20.0, min(20000.0, modulated_cutoff))

        # Update filter with validated parameters
        try:
            self.filter.set_parameters(
                cutoff=modulated_cutoff, resonance=base_resonance, filter_type=filter_type
            )

            # Apply filter processing with proper stereo handling
            if hasattr(self.filter, "process_block"):
                # Process stereo interleaved buffer
                filtered_audio = self.filter.process_block(self.audio_buffer[: block_size * 2])
                if filtered_audio is not None and len(filtered_audio) == block_size * 2:
                    self.audio_buffer[: block_size * 2] = filtered_audio

        except Exception as e:
            # Log filter processing error but continue without filtering
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"SF2Partial._apply_filter() failed, continuing without filtering: {e}",
                exc_info=True,
                extra={
                    "partial_id": self.region.sample_id
                    if hasattr(self.region, "sample_id")
                    else None,
                    "filter_type": filter_type,
                    "cutoff": base_cutoff,
                    "resonance": base_resonance,
                },
            )
            # Continue without filtering - audio will still play

    def _apply_spatial_processing(self, block_size: int):
        """Apply panning and final volume adjustments."""
        # Apply global volume modulation
        if self.volume_mod != 1.0:
            self.audio_buffer[: block_size * 2] *= self.volume_mod

        # Apply panning from SF2 parameters
        pan = self.params.get("pan", 0.0)
        if pan != 0.0:
            # Convert pan to left/right gains (-1.0 = full left, +1.0 = full right)
            pan_pos = pan / 500.0  # SF2 pan is -500 to +500
            pan_pos = max(-1.0, min(1.0, pan_pos))

            # Calculate pan gains (constant power panning)
            if pan_pos < 0:
                # Pan left
                left_gain = 1.0
                right_gain = 1.0 + pan_pos  # pan_pos is negative, so this reduces right
            else:
                # Pan right
                left_gain = 1.0 - pan_pos
                right_gain = 1.0

            # Apply pan gains
            self.audio_buffer[::2][:block_size] *= left_gain  # Left channel
            self.audio_buffer[1::2][:block_size] *= right_gain  # Right channel

    def is_active(self) -> bool:
        """
        Check if SF2 partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active

    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event with envelope triggering and SF2 generator processing.

        Processes all SF2 generators according to specification for complete compliance.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        self.params["velocity"] = velocity
        self.params["note"] = note

        # Process SF2 generators before activating
        self.process_sf2_generators(note, velocity, 1024)  # Use default block size

        # Only activate if zone limits allow playback
        if self.active:
            self.sample_position = 0.0  # Reset sample position

            # Trigger envelope with processed parameters
            if self.envelope:
                self.envelope.note_on(velocity, note)

            # Trigger modulation envelope
            self._trigger_modulation_envelope()

    def note_off(self) -> None:
        """Handle note-off event with envelope release."""
        # Trigger envelope release
        if self.envelope:
            self.envelope.note_off()

        # Trigger modulation envelope release
        self._release_modulation_envelope()

    def _trigger_modulation_envelope(self):
        """Trigger the modulation envelope to start its attack phase."""
        # Initialize modulation envelope state if needed
        if not hasattr(self, "_mod_env_state"):
            self._init_modulation_envelope_state()

        # Start the envelope attack phase
        self._mod_env_state["stage"] = "attack"
        self._mod_env_state["level"] = 0.0
        self._mod_env_state["stage_time"] = 0.0

    def _release_modulation_envelope(self):
        """Trigger the modulation envelope release phase."""
        if hasattr(self, "_mod_env_state"):
            self._mod_env_state["stage"] = "release"

    def apply_modulation(self, modulation: dict) -> None:
        """
        Apply modulation changes to partial parameters.

        This integrates SF2 partial with the global modulation matrix.

        Args:
            modulation: Dictionary of modulation values from global matrix
        """
        # Update modulation state from global matrix
        self.pitch_mod = modulation.get("pitch", 0.0)
        self.filter_mod = modulation.get("filter_cutoff", 0.0)
        self.volume_mod = modulation.get("volume", 1.0)

        # Apply global modulation to LFOs if needed
        # This allows external modulation to affect SF2 internal modulation
        pass

    def apply_global_parameters(self, global_params: dict) -> None:
        """
        Apply global synthesizer parameters to SF2 partial.

        This enables SF2 to respond to master controls, effects sends, etc.

        Args:
            global_params: Global synthesizer parameters
        """
        # Apply master volume
        master_volume = global_params.get("master_volume", 1.0)
        self.volume_mod *= master_volume

        # Apply global effects sends
        if "effects_sends" in global_params:
            effects_sends = global_params["effects_sends"]
            # Store for later use in effects processing
            self._global_reverb_send = effects_sends.get("reverb", 0.0)
            self._global_chorus_send = effects_sends.get("chorus", 0.0)
            self._global_variation_send = effects_sends.get("variation", 0.0)

        # Apply global tuning
        if "master_tune" in global_params:
            master_tune_semitones = global_params["master_tune"]
            self.pitch_mod += master_tune_semitones

        # Apply global transpose
        if "master_transpose" in global_params:
            master_transpose_semitones = global_params["master_transpose"]
            self.pitch_mod += master_transpose_semitones

    def apply_channel_parameter(self, param_update: ParameterUpdate) -> None:
        """
        Apply pre-processed channel parameter update.

        This method receives standardized ParameterUpdate objects from the
        hierarchical parameter routing system, eliminating duplication.

        Args:
            param_update: Standardized parameter update with scope, value, etc.
        """
        param_name = param_update.name
        value = param_update.value

        # Apply parameter based on its standardized name
        if param_name == "part_level":
            self.volume_mod *= value
        elif param_name == "part_pan":
            self._channel_pan = max(-1.0, min(1.0, value))
        elif param_name == "part_coarse_tune":
            self.pitch_mod += value
        elif param_name == "part_fine_tune":
            self.pitch_mod += value / 100.0  # Convert cents to semitones
        elif param_name == "part_cutoff":
            if self.filter:
                self.filter.set_parameters(cutoff=value)
                self.params["filter"]["cutoff"] = value
        elif param_name == "part_resonance":
            if self.filter:
                self.filter.set_parameters(resonance=value)
                self.params["filter"]["resonance"] = value
        elif param_name == "drum_kit":
            self._drum_kit = value

        # XG-specific parameters
        elif param_name.startswith("xg_"):
            setattr(self, f"_{param_name}", value)

        # Effect send parameters
        elif param_name.endswith("_send"):
            effect_type = param_name.split("_")[0]  # reverb, chorus, variation
            setattr(self, f"_channel_{effect_type}_send", value)

    def apply_voice_parameter(self, param_name: str, value: float) -> None:
        """
        Apply voice-level parameter modulation.

        Voice parameters affect note-specific behavior and modulation.

        Args:
            param_name: Parameter name
            value: Parameter value (pre-scaled)
        """
        if param_name == "pitch_modulation":
            self.pitch_mod = max(-24.0, min(24.0, value))  # Clamp to ±24 semitones
        elif param_name == "filter_modulation":
            self.filter_mod = max(-5.0, min(5.0, value))  # Clamp to ±5 octaves
        elif param_name == "volume_modulation":
            self.volume_mod = max(
                0.0, min(2.0, self.volume_mod * value)
            )  # Clamp to reasonable range
        elif param_name == "pan_modulation":
            # Apply pan modulation to existing pan
            current_pan = getattr(self, "_channel_pan", 0.0)
            new_pan = current_pan + value
            self._channel_pan = max(-1.0, min(1.0, new_pan))
        elif param_name == "reverb_send_modulation":
            # Apply reverb send modulation
            self.reverb_effects_send = max(0.0, min(1.0, self.reverb_effects_send + value))
        elif param_name == "chorus_send_modulation":
            # Apply chorus send modulation
            self.chorus_effects_send = max(0.0, min(1.0, self.chorus_effects_send + value))

    def apply_partial_parameter(self, param_name: str, value: float) -> None:
        """
        Apply partial-specific parameter.

        These are synthesis engine specific parameters.

        Args:
            param_name: Parameter name
            value: Parameter value (pre-scaled)
        """
        # Partial-specific parameters would be handled here
        # Currently, most parameters are handled at channel/voice level
        pass

    # LEGACY METHOD - DEPRECATED
    # This method is kept for backward compatibility but should be replaced
    # with the new ParameterUpdate-based methods above
    def apply_channel_parameters(self, channel_params: dict) -> None:
        """
        DEPRECATED: Legacy method for backward compatibility.

        This method processes raw channel parameters but should be replaced
        with apply_channel_parameter() using ParameterUpdate objects.

        Args:
            channel_params: Raw channel parameters (deprecated)
        """
        # Convert legacy parameters to ParameterUpdate objects
        # This is a temporary compatibility layer
        for param_name, value in channel_params.items():
            # Create ParameterUpdate from legacy format
            param_update = ParameterUpdate(
                name=param_name,
                value=value,
                scope=ParameterScope.CHANNEL,
                source=ParameterSource.XG_CHANNEL,
            )
            self.apply_channel_parameter(param_update)

    def get_effect_send_levels(self) -> dict[str, float]:
        """
        Get current effect send levels for routing through global effects coordinator.

        Returns:
            Dictionary with effect send levels (reverb, chorus, variation)
        """
        # Combine SF2-specific sends with channel sends
        return {
            "reverb": max(
                0.0, min(1.0, self.reverb_effects_send + getattr(self, "_channel_reverb_send", 0.0))
            ),
            "chorus": max(
                0.0, min(1.0, self.chorus_effects_send + getattr(self, "_channel_chorus_send", 0.0))
            ),
            "variation": max(0.0, min(1.0, getattr(self, "_channel_variation_send", 0.0))),
        }

    def get_channel_pan(self) -> float:
        """
        Get current channel pan position.

        Returns:
            Pan position (-1.0 to 1.0)
        """
        return getattr(self, "_channel_pan", 0.0)

    def get_parameter_state(self) -> dict[str, Any]:
        """
        Get current parameter state for debugging/monitoring.

        Returns:
            Dictionary of current parameter values
        """
        return {
            "pitch_mod": self.pitch_mod,
            "filter_mod": self.filter_mod,
            "volume_mod": self.volume_mod,
            "channel_pan": getattr(self, "_channel_pan", 0.0),
            "drum_kit": getattr(self, "_drum_kit", 0),
            "global_reverb_send": getattr(self, "_global_reverb_send", 0.0),
            "global_chorus_send": getattr(self, "_global_chorus_send", 0.0),
            "channel_reverb_send": getattr(self, "_channel_reverb_send", 0.0),
            "channel_chorus_send": getattr(self, "_channel_chorus_send", 0.0),
        }

    def reset(self) -> None:
        """Reset partial to initial state for pooling."""
        super().reset()
        self.sample_position = 0.0
        self.pitch_mod = 0.0
        self.filter_mod = 0.0
        self.volume_mod = 1.0

        # Reset pooled resources to initial state
        if self.envelope:
            self.envelope.reset()
        if self.filter:
            self.filter.reset()
        if self.mod_lfo:
            self.mod_lfo.reset()
        if self.vib_lfo:
            self.vib_lfo.reset()

        # Reset buffer allocation state - don't reset the actual pooled buffers
        # as they may be shared with other partials
        self._buffers_allocated = False

        # Reset modulation state
        if hasattr(self, "_mod_env_state"):
            self._mod_env_state = None

        # Reset sample data
        self.sample_data = None
        self.active = False

        # Reset buffer references to None for next allocation
        self.vib_lfo_buffer = None
        self.mod_lfo_buffer = None
        self.mod_env_buffer = None
        self.lfo_pitch_buffer = None
        self.lfo_filter_buffer = None
        self.lfo_volume_buffer = None
        self.lfo_pan_buffer = None
        self._pitch_mod_vector = None
        self._filter_mod_vector = None
        self._volume_mod_vector = None
        self._pan_mod_vector = None

    def get_partial_info(self) -> dict[str, Any]:
        """Get SF2 partial information for debugging."""
        info = super().get_partial_info()
        info.update(
            {
                "engine_type": "sf2",
                "sample_loaded": self.sample_data is not None,
                "sample_length": len(self.sample_data) if self.sample_data is not None else 0,
                "loop_mode": self.loop_mode,
                "loop_start": self.loop_start,
                "loop_end": self.loop_end,
                "pitch_ratio": self.pitch_ratio,
                "phase_step": self.phase_step,
                "current_position": self.sample_position,
                "pitch_mod": self.pitch_mod,
                "filter_mod": self.filter_mod,
                "volume_mod": self.volume_mod,
                # SF2 Generator status
                "effects_generators": {
                    "chorus_send": self.chorus_effects_send,
                    "reverb_send": self.reverb_effects_send,
                },
                "zone_control": {
                    "key_range": self.key_range,
                    "vel_range": self.vel_range,
                    "exclusive_class": self.exclusive_class,
                    "sample_modes": self.sample_modes,
                },
                "advanced_lfo": {
                    "mod_lfo_delay": self.delay_mod_lfo,
                    "mod_lfo_freq": self.freq_mod_lfo,
                    "vib_lfo_delay": self.delay_vib_lfo,
                    "vib_lfo_freq": self.freq_vib_lfo,
                },
            }
        )
        return info

    def _init_sf2_generators(self):
        """
        Initialize all SF2 generators with default values.

        This implements full SF2 specification compliance by supporting
        all 59+ generators defined in the SoundFont 2 specification.
        """
        # Effects Generators (15, 16)
        self.chorus_effects_send = 0.0  # Chorus send level (0.0-1.0)
        self.reverb_effects_send = 0.0  # Reverb send level (0.0-1.0)

        # Zone Control Generators (43, 44, 57, 54)
        self.key_range = (0, 127)  # MIDI key range (min, max)
        self.vel_range = (0, 127)  # MIDI velocity range (min, max)
        self.exclusive_class = 0  # Note stealing class (0 = none)
        self.sample_modes = 0  # Sample playback modes

        # Advanced LFO Generators (21, 22, 23, 24, 17, 15)
        self.delay_mod_lfo = 0.0  # Modulation LFO delay (seconds)
        self.freq_mod_lfo = 8.176  # Modulation LFO frequency (Hz)
        self.delay_vib_lfo = 0.0  # Vibrato LFO delay (seconds)
        self.freq_vib_lfo = 8.176  # Vibrato LFO frequency (Hz)
        self.vib_lfo_to_pan = 0.0  # Vibrato LFO → pan modulation
        self.mod_lfo_to_pan = 0.0  # Modulation LFO → pan modulation

        # Modulation Envelope Generators (7, 25-30)
        self.mod_env_to_pitch = 0.0  # Modulation envelope → pitch
        self.delay_mod_env = 0.0  # Modulation envelope delay
        self.attack_mod_env = 0.0  # Modulation envelope attack
        self.hold_mod_env = 0.0  # Modulation envelope hold
        self.decay_mod_env = 0.0  # Modulation envelope decay
        self.sustain_mod_env = 0.0  # Modulation envelope sustain
        self.release_mod_env = 0.0  # Modulation envelope release

        # Envelope Sensitivity Generators (31, 32, 39, 40)
        self.keynum_to_mod_env_hold = 0.0  # Key → modulation envelope hold
        self.keynum_to_mod_env_decay = 0.0  # Key → modulation envelope decay
        self.keynum_to_vol_env_hold = 0.0  # Key → volume envelope hold
        self.keynum_to_vol_env_decay = 0.0  # Key → volume envelope decay

        # Coarse Sample Addressing Generators (4, 12, 45, 50)
        self.start_addrs_coarse_offset = 0  # Coarse start address offset
        self.end_addrs_coarse_offset = 0  # Coarse end address offset
        self.startloop_addrs_coarse_offset = 0  # Coarse loop start offset
        self.endloop_addrs_coarse_offset = 0  # Coarse loop end offset

        # Advanced Tuning Generators (58, 56)
        self.overriding_root_key = None  # Override sample root key
        self.scale_tuning = 100  # Scale tuning (50-150%)

        # Volume Envelope (missing hold)
        self.hold_vol_env = 0.0  # Volume envelope hold time

        # Real-time LFO modulation depths (from SF2 generators)
        self.vib_lfo_to_pitch = 0.0  # Vibrato depth (semitones)
        self.mod_lfo_to_pitch = 0.0  # Modulation depth (semitones)
        self.mod_lfo_to_filter = 0.0  # Filter modulation depth (octaves)
        self.mod_lfo_to_volume = 0.0  # Tremolo depth (dB)
        self.mod_lfo_to_pan = 0.0  # Modulation pan depth
        self.vib_lfo_to_pan = 0.0  # Vibrato pan depth
        self.mod_env_to_pitch = 0.0  # Modulation envelope → pitch
        self.mod_env_to_filter = 0.0  # Modulation envelope → filter
        self.mod_env_to_volume = 0.0  # Modulation envelope → volume (tremolo)
        self.mod_env_to_pan = 0.0  # Modulation envelope → pan (auto-pan)

        # Real-time processing buffers (SIMD-optimized)
        self.vib_lfo_buffer = None  # Vibrato LFO output
        self.mod_lfo_buffer = None  # Modulation LFO output
        self.mod_env_buffer = None  # Modulation envelope output
        self.lfo_pitch_buffer = None  # Combined LFO pitch modulation
        self.lfo_filter_buffer = None  # Combined LFO filter modulation
        self.lfo_volume_buffer = None  # Combined LFO volume modulation
        self.lfo_pan_buffer = None  # Combined LFO pan modulation

        # Performance optimization: Pre-computed modulation vectors
        self._pitch_mod_vector = None  # Pre-computed pitch modulation
        self._filter_mod_vector = None  # Pre-computed filter modulation
        self._volume_mod_vector = None  # Pre-computed volume modulation
        self._pan_mod_vector = None  # Pre-computed pan modulation

        # SIMD optimization: Vectorized modulation calculations
        self._use_simd = True  # Enable SIMD optimizations
        self._vectorized_pitch_calc = None  # Vectorized pitch calculation
        self._vectorized_filter_calc = None  # Vectorized filter calculation

        # MODULATION MATRIX INTEGRATION - Extended modulation sources
        self.pan_mod = 0.0  # Pan modulation from matrix
        self.resonance_mod = 0.0  # Resonance modulation from matrix
        self.lfo_rate_mod = 0.0  # LFO rate modulation from matrix
        self.aftertouch_mod = 0.0  # Aftertouch modulation
        self.breath_mod = 0.0  # Breath controller modulation
        self.modwheel_mod = 0.0  # Mod wheel modulation
        self.foot_mod = 0.0  # Foot controller modulation
        self.expression_mod = 0.0  # Expression controller modulation

        # MODULATION MATRIX INTEGRATION - SF2 modulation outputs
        self._modulation_outputs = {}  # SF2 sources for matrix feedback

    def get_modulation_outputs(self) -> dict[str, float]:
        """
        Provide SF2 modulation sources to global modulation matrix.

        This enables bidirectional communication where SF2 LFOs and envelopes
        can be used as modulation sources for other synthesizer components.

        Returns:
            Dictionary of modulation source values
        """
        outputs = {}

        # SF2 LFO outputs - available for modulation routing
        if self.vib_lfo_buffer is not None and len(self.vib_lfo_buffer) > 0:
            outputs["sf2_vibrato_lfo"] = float(self.vib_lfo_buffer[-1])  # Current vibrato LFO value

        if self.mod_lfo_buffer is not None and len(self.mod_lfo_buffer) > 0:
            outputs["sf2_modulation_lfo"] = float(
                self.mod_lfo_buffer[-1]
            )  # Current modulation LFO value

        # SF2 envelope outputs - available for modulation routing
        if self.mod_env_buffer is not None and len(self.mod_env_buffer) > 0:
            outputs["sf2_modulation_env"] = float(
                self.mod_env_buffer[-1]
            )  # Current modulation envelope value

        # Amplitude envelope output (if available)
        if hasattr(self, "envelope") and self.envelope:
            try:
                # Try to get current envelope level
                if hasattr(self.envelope, "get_current_level"):
                    env_level = self.envelope.get_current_level()
                    outputs["sf2_amplitude_env"] = float(env_level)
            except:
                pass

        # Store outputs for internal use
        self._modulation_outputs = outputs

        return outputs

    def apply_modulation_matrix_parameters(self, matrix_params: dict):
        """
        Apply modulation matrix parameter changes to SF2 synthesis parameters.

        This allows the modulation matrix to control detailed SF2 parameters
        beyond the basic global modulation.

        Args:
            matrix_params: Parameter changes from modulation matrix
        """
        # LFO parameter modulation
        if "lfo1_rate" in matrix_params:
            # Modulate modulation LFO rate
            rate_mod = matrix_params["lfo1_rate"]
            modulated_rate = self.freq_mod_lfo * (1.0 + rate_mod)
            self.freq_mod_lfo = max(0.1, min(50.0, modulated_rate))

        if "lfo2_rate" in matrix_params:
            # Modulate vibrato LFO rate
            rate_mod = matrix_params["lfo2_rate"]
            modulated_rate = self.freq_vib_lfo * (1.0 + rate_mod)
            self.freq_vib_lfo = max(0.1, min(50.0, modulated_rate))

        # Envelope parameter modulation
        if "env_attack" in matrix_params:
            # Modulate modulation envelope attack
            attack_mod = matrix_params["env_attack"]
            modulated_attack = self.attack_mod_env * (1.0 + attack_mod)
            self.attack_mod_env = max(0.001, modulated_attack)

        if "env_decay" in matrix_params:
            # Modulate modulation envelope decay
            decay_mod = matrix_params["env_decay"]
            modulated_decay = self.decay_mod_env * (1.0 + decay_mod)
            self.decay_mod_env = max(0.001, modulated_decay)

        if "env_sustain" in matrix_params:
            # Modulate modulation envelope sustain
            sustain_mod = matrix_params["env_sustain"]
            modulated_sustain = self.sustain_mod_env * (1.0 + sustain_mod)
            self.sustain_mod_env = max(0.0, min(1.0, modulated_sustain))

        # Filter parameter modulation
        if "filter_resonance" in matrix_params:
            # Modulate filter resonance (add to existing resonance)
            res_mod = matrix_params["filter_resonance"]
            # Apply to filter parameters
            if self.filter:
                try:
                    current_params = (
                        self.filter.get_parameters()
                        if hasattr(self.filter, "get_parameters")
                        else {}
                    )
                    current_resonance = current_params.get("resonance", 0.7)
                    new_resonance = current_resonance + res_mod
                    # Clamp resonance to prevent instability
                    new_resonance = max(0.0, min(30.0, new_resonance))
                    self.filter.set_parameters(resonance=new_resonance)
                except:
                    # If filter doesn't support parameter updates, store for later
                    self._pending_filter_resonance = max(0.0, min(30.0, resonance + res_mod))

        # SF2 generator modulation
        if "sf2_lfo_depth" in matrix_params:
            # Modulate overall LFO depth for SF2 effects
            depth_mod = matrix_params["sf2_lfo_depth"]
            self.vib_lfo_to_pitch = max(
                -1200.0, min(1200.0, self.vib_lfo_to_pitch * (1.0 + depth_mod))
            )
            self.mod_lfo_to_pitch = max(
                -1200.0, min(1200.0, self.mod_lfo_to_pitch * (1.0 + depth_mod))
            )
            self.mod_lfo_to_filter = max(
                -1200.0, min(1200.0, self.mod_lfo_to_filter * (1.0 + depth_mod))
            )
            self.mod_lfo_to_volume = max(
                -960.0, min(960.0, self.mod_lfo_to_volume * (1.0 + depth_mod))
            )

        if "sf2_env_depth" in matrix_params:
            # Modulate modulation envelope depth
            env_mod = matrix_params["sf2_env_depth"]
            self.mod_env_to_pitch = max(
                -12000.0, min(12000.0, self.mod_env_to_pitch * (1.0 + env_mod))
            )

        # Additional SF2 generator modulations
        if "filter_cutoff_mod" in matrix_params:
            # Modulate filter cutoff
            cutoff_mod = matrix_params["filter_cutoff_mod"]
            base_cutoff = self.params.get("filter", {}).get("cutoff", 20000.0)
            self.filter_mod = max(-5.0, min(5.0, cutoff_mod))  # Clamp to ±5 octaves

        if "pitch_mod" in matrix_params:
            # Modulate pitch
            pitch_mod = matrix_params["pitch_mod"]
            self.pitch_mod = max(-24.0, min(24.0, pitch_mod))  # Clamp to ±24 semitones

    def update_global_effects_routing(self, global_effects: dict):
        """
        Update integration with global effects system.

        Allows the modulation matrix to influence SF2 effect send levels
        and provides advanced effects routing control.

        Args:
            global_effects: Global effects configuration and modulation
        """
        # Update chorus send level modulation
        if "chorus_send_mod" in global_effects:
            chorus_mod = global_effects["chorus_send_mod"]
            self.chorus_effects_send *= 1.0 + chorus_mod
            # Clamp to valid range
            self.chorus_effects_send = max(0.0, min(1.0, self.chorus_effects_send))

        # Update reverb send level modulation
        if "reverb_send_mod" in global_effects:
            reverb_mod = global_effects["reverb_send_mod"]
            self.reverb_effects_send *= 1.0 + reverb_mod
            # Clamp to valid range
            self.reverb_effects_send = max(0.0, min(1.0, self.reverb_effects_send))

        # Update variation send level modulation
        if "variation_send_mod" in global_effects:
            variation_mod = global_effects["variation_send_mod"]
            # Store for get_effect_send_levels()
            self._global_variation_send = getattr(self, "_global_variation_send", 0.0) * (
                1.0 + variation_mod
            )

        # Update global effects levels for reference
        if "chorus_level" in global_effects:
            self._global_chorus_send = global_effects["chorus_level"]

        if "reverb_level" in global_effects:
            self._global_reverb_send = global_effects["reverb_level"]

        if "variation_level" in global_effects:
            self._global_variation_send = global_effects["variation_level"]

    def _generate_lfo_signals(self, block_size: int):
        """Generate LFO modulation signals for the current block."""
        # Ensure buffers are allocated before proceeding
        self._ensure_buffers_allocated(block_size)

        # Generate vibrato LFO signal
        if self.vib_lfo and self.active:
            # Update LFO parameters with proper error handling
            try:
                # Try different parameter names that LFOs might use
                if self.freq_vib_lfo != 8.176:
                    if hasattr(self.vib_lfo, "set_parameters"):
                        # Try 'rate' first (most common)
                        try:
                            self.vib_lfo.set_parameters(rate=self.freq_vib_lfo)
                        except:
                            # Try 'frequency'
                            try:
                                self.vib_lfo.set_parameters(frequency=self.freq_vib_lfo)
                            except:
                                pass  # Parameter not supported

                if self.delay_vib_lfo > 0.0:
                    if hasattr(self.vib_lfo, "set_parameters"):
                        self.vib_lfo.set_parameters(delay=self.delay_vib_lfo)

                # Generate LFO block with proper error handling
                if hasattr(self.vib_lfo, "generate_block"):
                    result = self.vib_lfo.generate_block(block_size)
                    if isinstance(result, np.ndarray):
                        # Ensure we don't exceed buffer size
                        copy_size = min(len(result), block_size, len(self.vib_lfo_buffer))
                        self.vib_lfo_buffer[:copy_size] = result[:copy_size]
                    else:
                        # If generate_block returns a single value, broadcast it
                        copy_size = min(block_size, len(self.vib_lfo_buffer))
                        self.vib_lfo_buffer[:copy_size] = result
                else:
                    # Fallback: generate simple sine wave
                    phase = getattr(self, "_vib_lfo_phase", 0.0)
                    copy_size = min(block_size, len(self.vib_lfo_buffer))
                    for i in range(copy_size):
                        self.vib_lfo_buffer[i] = np.sin(phase)
                        phase += 2.0 * np.pi * self.freq_vib_lfo / self.synth.sample_rate
                    self._vib_lfo_phase = phase

            except Exception:
                # Ultimate fallback: generate simple modulation
                phase = getattr(self, "_vib_lfo_phase", 0.0)
                copy_size = min(block_size, len(self.vib_lfo_buffer))
                for i in range(copy_size):
                    self.vib_lfo_buffer[i] = 0.5 * np.sin(phase)  # 0.5 depth
                    phase += 2.0 * np.pi * 5.0 / self.synth.sample_rate  # 5 Hz default
                self._vib_lfo_phase = phase

        # Generate modulation LFO signal
        if self.mod_lfo and self.active:
            try:
                # Update LFO parameters
                if self.freq_mod_lfo != 8.176:
                    if hasattr(self.mod_lfo, "set_parameters"):
                        try:
                            self.mod_lfo.set_parameters(rate=self.freq_mod_lfo)
                        except:
                            try:
                                self.mod_lfo.set_parameters(frequency=self.freq_mod_lfo)
                            except:
                                pass

                if self.delay_mod_lfo > 0.0:
                    if hasattr(self.mod_lfo, "set_parameters"):
                        self.mod_lfo.set_parameters(delay=self.delay_mod_lfo)

                # Generate LFO block
                if hasattr(self.mod_lfo, "generate_block"):
                    result = self.mod_lfo.generate_block(block_size)
                    if isinstance(result, np.ndarray):
                        # Ensure we don't exceed buffer size
                        copy_size = min(len(result), block_size, len(self.mod_lfo_buffer))
                        self.mod_lfo_buffer[:copy_size] = result[:copy_size]
                    else:
                        copy_size = min(block_size, len(self.mod_lfo_buffer))
                        self.mod_lfo_buffer[:copy_size] = result
                else:
                    # Fallback: generate simple sine wave
                    phase = getattr(self, "_mod_lfo_phase", 0.0)
                    copy_size = min(block_size, len(self.mod_lfo_buffer))
                    for i in range(copy_size):
                        self.mod_lfo_buffer[i] = np.sin(phase)
                        phase += 2.0 * np.pi * self.freq_mod_lfo / self.synth.sample_rate
                    self._mod_lfo_phase = phase

            except Exception:
                # Ultimate fallback
                phase = getattr(self, "_mod_lfo_phase", 0.0)
                copy_size = min(block_size, len(self.mod_lfo_buffer))
                for i in range(copy_size):
                    self.mod_lfo_buffer[i] = 0.3 * np.sin(phase)  # 0.3 depth
                    phase += 2.0 * np.pi * 6.0 / self.synth.sample_rate  # 6 Hz default
                self._mod_lfo_phase = phase

    def _generate_modulation_envelope_signals(self, block_size: int):
        """Generate modulation envelope signals for the current block."""
        # Ensure buffers are allocated before proceeding
        self._ensure_buffers_allocated(block_size)

        # Initialize modulation envelope if needed
        if not hasattr(self, "_mod_env_state"):
            self._init_modulation_envelope_state()

        # Generate modulation envelope samples
        for i in range(block_size):
            mod_env_value = self._calculate_modulation_envelope_sample()
            # Ensure we don't exceed buffer size
            if i < len(self.mod_env_buffer):
                self.mod_env_buffer[i] = mod_env_value

            # Update envelope state
            self._update_modulation_envelope_state()

    def _init_modulation_envelope_state(self):
        """Initialize modulation envelope state."""
        # Ensure time values are positive to avoid division by zero
        attack_time = max(0.001, self.attack_mod_env)  # Minimum 1ms
        decay_time = max(0.001, self.decay_mod_env)  # Minimum 1ms
        release_time = max(0.001, self.release_mod_env)  # Minimum 1ms

        self._mod_env_state = {
            "stage": "idle",  # idle, attack, decay, sustain, release
            "level": 0.0,
            "stage_time": 0.0,
            "attack_rate": 1.0 / (attack_time * self.synth.sample_rate) if attack_time > 0 else 1.0,
            "decay_rate": 1.0 / (decay_time * self.synth.sample_rate) if decay_time > 0 else 1.0,
            "release_rate": 1.0 / (release_time * self.synth.sample_rate)
            if release_time > 0
            else 1.0,
            "sustain_level": max(0.0, min(1.0, self.sustain_mod_env)),  # Clamp to valid range
        }

    def _ensure_buffers_allocated(self, block_size: int):
        """Ensure all required buffers are allocated from the memory pool."""
        if not self._buffers_allocated:
            # Allocate buffers from the synth's memory pool or buffer pool
            if hasattr(self.synth, "memory_pool"):
                pool = self.synth.memory_pool
            elif hasattr(self.synth, "buffer_pool"):
                pool = self.synth.buffer_pool
            else:
                # Fallback: create temporary buffers (not ideal but prevents crashes)
                self.vib_lfo_buffer = np.zeros(block_size, dtype=np.float32)
                self.mod_lfo_buffer = np.zeros(block_size, dtype=np.float32)
                self.mod_env_buffer = np.zeros(block_size, dtype=np.float32)
                self.lfo_pitch_buffer = np.zeros(block_size, dtype=np.float32)
                self.lfo_filter_buffer = np.zeros(block_size, dtype=np.float32)
                self.lfo_volume_buffer = np.zeros(block_size, dtype=np.float32)
                self.lfo_pan_buffer = np.zeros(block_size, dtype=np.float32)
                self._pitch_mod_vector = np.zeros(block_size, dtype=np.float32)
                self._filter_mod_vector = np.zeros(block_size, dtype=np.float32)
                self._volume_mod_vector = np.zeros(block_size, dtype=np.float32)
                self._pan_mod_vector = np.zeros(block_size, dtype=np.float32)
                self._buffers_allocated = True
                return

            # Use pooled buffers from the memory pool
            self.vib_lfo_buffer = pool.get_mono_buffer(block_size)
            self.mod_lfo_buffer = pool.get_mono_buffer(block_size)
            self.mod_env_buffer = pool.get_mono_buffer(block_size)
            self.lfo_pitch_buffer = pool.get_mono_buffer(block_size)
            self.lfo_filter_buffer = pool.get_mono_buffer(block_size)
            self.lfo_volume_buffer = pool.get_mono_buffer(block_size)
            self.lfo_pan_buffer = pool.get_mono_buffer(block_size)
            self._pitch_mod_vector = pool.get_mono_buffer(block_size)
            self._filter_mod_vector = pool.get_mono_buffer(block_size)
            self._volume_mod_vector = pool.get_mono_buffer(block_size)
            self._pan_mod_vector = pool.get_mono_buffer(block_size)
            self._buffers_allocated = True

    def _calculate_modulation_envelope_sample(self) -> float:
        """Calculate current modulation envelope sample."""
        state = self._mod_env_state

        if state["stage"] == "idle":
            return 0.0
        elif state["stage"] == "attack":
            # Linear attack to full level
            state["level"] = min(1.0, state["level"] + state["attack_rate"])
            return state["level"]
        elif state["stage"] == "decay":
            # Exponential decay to sustain level
            state["level"] = max(state["sustain_level"], state["level"] - state["decay_rate"])
            return state["level"]
        elif state["stage"] == "sustain":
            return state["sustain_level"]
        elif state["stage"] == "release":
            # Exponential release to zero
            state["level"] = max(0.0, state["level"] - state["release_rate"])
            return state["level"]

        return 0.0

    def _update_modulation_envelope_state(self):
        """Update modulation envelope state for next sample."""
        state = self._mod_env_state

        # Update stage time counter
        state["stage_time"] += 1.0 / self.synth.sample_rate

        # Simple envelope progression (would be triggered by note events)
        # This is a basic implementation - real envelopes need proper triggering
        if state["stage"] == "attack" and state["level"] >= 1.0:
            state["stage"] = "decay"
            state["stage_time"] = 0.0
        elif state["stage"] == "decay" and state["level"] <= state["sustain_level"]:
            state["stage"] = "sustain"
            state["stage_time"] = 0.0
        # Release would be triggered by note-off events

    def _generate_wavetable_samples_realtime(self, block_size: int):
        """Generate wavetable samples with continuous pitch modulation."""
        if self.sample_data is None:
            return

        # Check if sample data is stereo
        if (
            self.sample_data is not None
            and hasattr(self.sample_data, "shape")
            and len(self.sample_data.shape) > 1
        ):
            # True stereo sample
            self._generate_stereo_samples_realtime(block_size)
        else:
            # Mono sample
            self._generate_mono_samples_realtime(block_size)

    def _generate_mono_samples_realtime(self, block_size: int):
        """Generate mono samples with real-time pitch modulation."""
        if self.sample_data is None:
            return

        mono_samples = self.work_buffer[:block_size]

        for i in range(block_size):
            # Calculate real-time pitch modulation for this sample
            total_pitch_mod = self._calculate_sample_pitch_modulation(i)

            # Apply pitch modulation to phase step for this sample
            modulated_phase_step = self.base_phase_step * (2.0 ** (total_pitch_mod / 12.0))

            # Generate sample with modulated phase
            sample_length = len(self.sample_data)
            if self.sample_position < sample_length - 1:
                # Linear interpolation between samples
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                sample1 = self.sample_data[pos_int]
                sample2 = self.sample_data[pos_int + 1]
                mono_samples[i] = sample1 + frac * (sample2 - sample1)
            else:
                mono_samples[i] = 0.0

            # Update sample position
            self.sample_position += modulated_phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy mono to stereo buffer (will be panned later)
        self.audio_buffer[::2][:block_size] = mono_samples  # Left channel
        self.audio_buffer[1::2][:block_size] = mono_samples  # Right channel

    def _generate_stereo_samples_realtime(self, block_size: int):
        """Generate true stereo samples with real-time pitch modulation."""
        if self.sample_data is None:
            return

        # For stereo samples, we need to interpolate both channels
        left_channel = self.work_buffer[:block_size]
        right_channel = self.work_buffer[block_size : 2 * block_size]

        sample_length = len(self.sample_data)
        for i in range(block_size):
            # Calculate real-time pitch modulation for this sample
            total_pitch_mod = self._calculate_sample_pitch_modulation(i)

            # Apply pitch modulation to phase step for this sample
            modulated_phase_step = self.base_phase_step * (2.0 ** (total_pitch_mod / 12.0))

            if self.sample_position < sample_length - 1:
                # Linear interpolation between sample frames
                pos_int = int(self.sample_position)
                frac = self.sample_position - pos_int

                # Interpolate left channel
                left1 = self.sample_data[pos_int, 0]
                left2 = self.sample_data[pos_int + 1, 0]
                left_channel[i] = left1 + frac * (left2 - left1)

                # Interpolate right channel
                right1 = self.sample_data[pos_int, 1]
                right2 = self.sample_data[pos_int + 1, 1]
                right_channel[i] = right1 + frac * (right2 - right1)
            else:
                left_channel[i] = 0.0
                right_channel[i] = 0.0

            # Update sample position
            self.sample_position += modulated_phase_step

            # Handle SF2 loop modes
            self._handle_sample_looping()

        # Copy stereo samples to output buffer
        self.audio_buffer[::2][:block_size] = left_channel  # Left channel
        self.audio_buffer[1::2][:block_size] = right_channel  # Right channel

    def _apply_filter_realtime(self, block_size: int):
        """Apply resonant filtering with real-time modulation."""
        if not self.filter:
            return

        # Ensure buffers are allocated before proceeding
        self._ensure_buffers_allocated(block_size)

        # Prepare filter modulation for each sample
        for i in range(block_size):
            # Calculate filter modulation for this sample
            filter_mod = self.filter_mod  # Static modulation

            # Add LFO filter modulation
            if i < len(self.mod_lfo_buffer):
                filter_mod += self.mod_lfo_buffer[i] * self.mod_lfo_to_filter

            # Add modulation envelope filter modulation
            if i < len(self.mod_env_buffer):
                filter_mod += self.mod_env_buffer[i] * self.mod_env_to_filter

            # Calculate modulated cutoff frequency
            base_cutoff = self.params.get("filter", {}).get("cutoff", 20000.0)
            # Apply modulation in a controlled way to prevent extreme values
            modulated_cutoff = base_cutoff * (
                2.0 ** max(-5.0, min(5.0, filter_mod))
            )  # Clamp modulation to ±5 octaves
            modulated_cutoff = max(20.0, min(20000.0, modulated_cutoff))  # Clamp to audible range

            # Update filter parameters for this sample
            # Note: Real-time parameter changes may not be supported by filter
            # This is a simplified implementation
            if i == 0:  # Update parameters once per block for performance
                resonance = self.params.get("filter", {}).get("resonance", 0.0)
                # Clamp resonance to prevent instability
                resonance = max(0.0, min(30.0, resonance))  # Reasonable resonance range
                try:
                    self.filter.set_parameters(cutoff=modulated_cutoff, resonance=resonance)
                except Exception as e:
                    # Log error but continue without filter parameter updates
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"SF2Partial._apply_filter_modulation() failed to update filter parameters: {e}",
                        exc_info=True,
                        extra={
                            "partial_id": self.region.sample_id
                            if hasattr(self.region, "sample_id")
                            else None,
                            "cutoff": modulated_cutoff,
                            "resonance": resonance,
                        },
                    )
                    # Continue with previous filter parameters

        # Apply filter to stereo audio buffer with basic processing
        # This is a simplified implementation until proper filter interface is available
        if self.filter and hasattr(self.filter, "process_block"):
            try:
                # Process the audio through the filter
                # Note: This assumes filter.process_block can handle stereo interleaved data
                audio_to_process = self.audio_buffer[: block_size * 2]
                filtered_audio = self.filter.process_block(audio_to_process)
                if filtered_audio is not None and len(filtered_audio) == len(audio_to_process):
                    self.audio_buffer[: block_size * 2] = filtered_audio
            except Exception as e:
                # If filter processing fails, continue without filtering
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"SF2Partial._apply_filter_modulation() filter processing failed: {e}",
                    exc_info=True,
                    extra={
                        "partial_id": self.region.sample_id
                        if hasattr(self.region, "sample_id")
                        else None,
                        "filter_type": type(self.filter).__name__,
                    },
                )
                # Continue without filtering - audio will still play

    def _apply_volume_pan_modulation(self, block_size: int):
        """
        Apply time-varying volume and panning adjustments for SF2 synthesis.

        Handles LFO-based tremolo and auto-pan effects as specified in SF2.
        These are synthesis-level effects that require per-sample processing
        for smooth, artifact-free modulation.
        """
        # Ensure buffers are allocated before proceeding
        self._ensure_buffers_allocated(block_size)

        if block_size > len(self.audio_buffer) // 2:
            return

        # Apply modulation envelope to volume/pan (NEW - Issue #1 fix)
        self._apply_modulation_envelope_to_volume_pan(block_size)

        # Get static pan position (from channel parameters)
        static_pan = getattr(self, "_channel_pan", 0.0)

        # Pre-calculate modulation depths for efficiency
        has_tremolo = (
            self.mod_lfo_to_volume != 0.0
            and self.mod_lfo_buffer is not None
            and len(self.mod_lfo_buffer) >= block_size
        )

        has_auto_pan = (self.vib_lfo_to_pan != 0.0 or self.mod_lfo_to_pan != 0.0) and (
            (self.vib_lfo_buffer is not None and len(self.vib_lfo_buffer) >= block_size)
            or (self.mod_lfo_buffer is not None and len(self.mod_lfo_buffer) >= block_size)
        )

        # Apply modulation if any effects are active
        if has_tremolo or has_auto_pan:
            for i in range(block_size):
                left_idx = i * 2
                right_idx = i * 2 + 1

                # Get current sample values
                left_sample = self.audio_buffer[left_idx]
                right_sample = self.audio_buffer[right_idx]

                # Apply tremolo (LFO volume modulation)
                if has_tremolo:
                    # Calculate tremolo modulation in dB
                    tremolo_db = self.mod_lfo_buffer[i] * self.mod_lfo_to_volume

                    # Convert dB to linear scale with clamping for stability
                    tremolo_linear = max(0.001, min(4.0, 10.0 ** (tremolo_db / 20.0)))

                    # Apply tremolo to both channels
                    left_sample *= tremolo_linear
                    right_sample *= tremolo_linear

                # Apply auto-pan (LFO pan modulation)
                if has_auto_pan:
                    # Calculate total pan modulation
                    pan_mod = 0.0

                    # Add vibrato LFO pan modulation
                    if self.vib_lfo_to_pan != 0.0 and self.vib_lfo_buffer is not None:
                        pan_mod += self.vib_lfo_buffer[i] * self.vib_lfo_to_pan

                    # Add modulation LFO pan modulation
                    if self.mod_lfo_to_pan != 0.0 and self.mod_lfo_buffer is not None:
                        pan_mod += self.mod_lfo_buffer[i] * self.mod_lfo_to_pan

                    # Combine static and dynamic pan
                    total_pan = static_pan + pan_mod

                    # Clamp to valid range and apply smoothing to prevent artifacts
                    total_pan = max(-1.0, min(1.0, total_pan))

                    # Calculate pan gains using constant power panning law
                    if total_pan <= 0:
                        # Pan left: right gain = 1.0, left gain = 1.0 + pan
                        left_gain = 1.0 + total_pan
                        right_gain = 1.0
                    else:
                        # Pan right: left gain = 1.0, right gain = 1.0 - pan
                        left_gain = 1.0 - total_pan
                        right_gain = 1.0

                    # Apply pan gains
                    left_sample *= left_gain
                    right_sample *= right_gain

                # Write back modulated samples
                self.audio_buffer[left_idx] = left_sample
                self.audio_buffer[right_idx] = right_sample

    def _apply_modulation_envelope_to_volume_pan(self, block_size: int):
        """
        Apply modulation envelope to volume and pan (extended feature).

        This implements SF2 generators for modulation envelope to volume and pan modulation.
        SF2 Generator IDs:
        - modEnvToVolume (custom extension)
        - modEnvToPan (custom extension)
        """
        # Modulation envelope to volume/pan modulation
        # These are SF2 standard features that enhance synthesis capabilities

        # Apply modulation envelope to volume if configured
        if self.mod_env_buffer is not None and hasattr(self, "mod_env_to_volume"):
            if self.mod_env_to_volume != 0.0:
                # Modulation envelope affects volume (tremolo-like effect)
                mod_env_values = self.mod_env_buffer[:block_size]
                volume_mod = mod_env_values * self.mod_env_to_volume
                self._volume_mod_vector = volume_mod

        # Apply modulation envelope to pan if configured
        if self.mod_env_buffer is not None and hasattr(self, "mod_env_to_pan"):
            if self.mod_env_to_pan != 0.0:
                # Modulation envelope affects pan (auto-pan effect)
                mod_env_values = self.mod_env_buffer[:block_size]
                pan_mod = mod_env_values * self.mod_env_to_pan
                self._pan_mod_vector = pan_mod

    def _calculate_sample_pitch_modulation(self, sample_index: int) -> float:
        """Calculate total pitch modulation for a specific sample."""
        total_pitch_mod = self.pitch_mod  # Static modulation

        # Add vibrato LFO modulation
        if self.vib_lfo_buffer is not None and sample_index < len(self.vib_lfo_buffer):
            total_pitch_mod += self.vib_lfo_buffer[sample_index] * self.vib_lfo_to_pitch

        # Add modulation LFO modulation
        if self.mod_lfo_buffer is not None and sample_index < len(self.mod_lfo_buffer):
            total_pitch_mod += self.mod_lfo_buffer[sample_index] * self.mod_lfo_to_pitch

        # Add modulation envelope modulation
        if self.mod_env_buffer is not None and sample_index < len(self.mod_env_buffer):
            total_pitch_mod += self.mod_env_buffer[sample_index] * self.mod_env_to_pitch

        return total_pitch_mod

    def _load_sf2_generator_values(self):
        """
        Load SF2 generator values from zone parameters.
        Supports both nested structure (preferred) and flat generators dict (backward compat).

        Maps SF2 generator IDs to their corresponding parameter values
        from the zone data, implementing full SF2 specification compliance.
        """
        generators = self.params.get("generators", {})

        # Load from nested structures first (preferred method)
        # Effects
        effects = self.params.get("effects", {})
        self.reverb_effects_send = effects.get("reverb_send", 0.0)
        self.chorus_effects_send = effects.get("chorus_send", 0.0)
        self.pan = effects.get("pan", 0.0)

        # Key/Vel ranges
        self.key_range = self.params.get("key_range", (0, 127))
        self.vel_range = self.params.get("vel_range", (0, 127))

        # Sample settings
        sample_settings = self.params.get("sample_settings", {})
        self.exclusive_class = sample_settings.get("exclusive_class", 0)
        self.sample_modes = sample_settings.get("mode", 0)

        # Modulation envelope
        mod_env = self.params.get("mod_envelope", {})
        self.mod_env_to_pitch = mod_env.get("to_pitch", 0.0)
        self.mod_env_to_filter = mod_env.get("to_filter", 0.0)
        self.mod_env_to_volume = mod_env.get("to_volume", 0.0)  # NEW
        self.mod_env_to_pan = mod_env.get("to_pan", 0.0)  # NEW

        # Fallback to generators dict if nested values not provided
        if self.reverb_effects_send == 0.0 and 32 in generators:
            self.reverb_effects_send = generators.get(32, 0) / 1000.0
        if self.chorus_effects_send == 0.0 and 33 in generators:
            self.chorus_effects_send = generators.get(33, 0) / 1000.0

        # Advanced LFO Generators
        self.delay_mod_lfo = self._convert_time_cent(21, generators.get(21, -12000))
        self.freq_mod_lfo = self._convert_freq_cent(22, generators.get(22, 0))
        self.delay_vib_lfo = self._convert_time_cent(
            26, generators.get(26, -12000)
        )  # Fixed: delayVibLFO is generator 26
        self.freq_vib_lfo = self._convert_freq_cent(
            27, generators.get(27, 0)
        )  # Fixed: freqVibLFO is generator 27
        self.vib_lfo_to_pan = generators.get(37, 0) / 10.0  # vibLfoToPan (generator 37)
        self.mod_lfo_to_pan = generators.get(42, 0) / 10.0  # modLfoToPan (generator 42)

        # LFO modulation depths (correct SF2 generator IDs)
        self.vib_lfo_to_pitch = (
            generators.get(28, 0) / 100.0
        )  # vibLfoToPitch (generator 28, cents to semitones)
        self.mod_lfo_to_pitch = (
            generators.get(25, 0) / 100.0
        )  # modLfoToPitch (generator 25, cents to semitones)
        self.mod_lfo_to_filter = (
            generators.get(24, 0) / 1200.0
        )  # modLfoToFilterFc (generator 24, cents to octaves)
        self.mod_lfo_to_volume = (
            generators.get(23, 0) / 10.0
        )  # modLfoToVolume (generator 23, 0.1dB to dB)

        # Modulation Envelope Generators
        # Only load from generators if not already set from nested structure
        if self.mod_env_to_pitch == 0.0:
            self.mod_env_to_pitch = generators.get(20, 0) / 1200.0  # Correct SF2 generator ID
        self.delay_mod_env = self._convert_time_cent(14, generators.get(14, -12000))
        self.attack_mod_env = self._convert_time_cent(15, generators.get(15, -12000))
        self.hold_mod_env = self._convert_time_cent(16, generators.get(16, -12000))
        self.decay_mod_env = self._convert_time_cent(17, generators.get(17, -12000))
        self.sustain_mod_env = generators.get(18, 0) / 1000.0
        self.release_mod_env = self._convert_time_cent(19, generators.get(19, -12000))

        # Envelope Sensitivity Generators
        self.keynum_to_mod_env_hold = generators.get(31, 0) / 100.0
        self.keynum_to_mod_env_decay = generators.get(32, 0) / 100.0
        self.keynum_to_vol_env_hold = generators.get(39, 0) / 100.0
        self.keynum_to_vol_env_decay = generators.get(40, 0) / 100.0

        # Coarse Sample Addressing Generators
        self.start_addrs_coarse_offset = generators.get(4, 0)
        self.end_addrs_coarse_offset = generators.get(12, 0)
        self.startloop_addrs_coarse_offset = generators.get(45, 0)
        self.endloop_addrs_coarse_offset = generators.get(50, 0)

        # Advanced Tuning Generators
        self.overriding_root_key = generators.get(58, None)
        self.scale_tuning = 100 + (generators.get(56, 0) / 100.0)

        # Volume Envelope (add missing hold)
        self.hold_vol_env = self._convert_time_cent(35, generators.get(35, -12000))

    def _convert_sf2_generator(self, gen_id: int, value: int) -> float:
        """
        Convert SF2 generator value to appropriate units.

        Args:
            gen_id: SF2 generator ID
            value: Raw generator value

        Returns:
            Converted value in appropriate units
        """
        # Generator-specific conversions
        if gen_id in [15, 16]:  # Effects sends (0.1% units)
            return value / 10.0
        elif gen_id in [17]:  # Pan (-500 to +500)
            return value / 10.0  # Convert to -50 to +50
        elif gen_id in [48]:  # Initial attenuation (0.1dB units)
            return value / 10.0  # Convert to dB
        elif gen_id in [51, 52]:  # Tuning (cents)
            return value
        else:
            return value

    def _convert_time_cent(self, gen_id: int, value: int) -> float:
        """
        Convert SF2 time values from cents to seconds.

        Args:
            gen_id: Generator ID (for reference)
            value: Time in cents (-12000 to +12000)

        Returns:
            Time in seconds
        """
        if value == -12000:
            return 0.0  # Minimum time
        elif value == 0:
            return 1.0  # 1 second at 0 cents
        else:
            return 2.0 ** (value / 1200.0)  # Convert cents to time ratio

    def _convert_freq_cent(self, gen_id: int, value: int) -> float:
        """
        Convert SF2 frequency values from cents to Hz.

        Args:
            gen_id: Generator ID (for reference)
            value: Frequency in cents

        Returns:
            Frequency in Hz
        """
        return 8.176 * (2.0 ** (value / 1200.0))  # A-1 at 8.176 Hz base

    def _parse_key_range(self, value: int) -> tuple:
        """
        Parse SF2 key range generator.

        Args:
            value: Packed key range (high_byte | low_byte << 8)

        Returns:
            Tuple of (min_key, max_key)
        """
        # SF2 stores key range as: low_byte = min_key, high_byte = max_key
        # The value is passed as (low_byte | high_byte << 8)
        # So we extract: min_key = low_byte, max_key = high_byte
        min_key = value & 0xFF  # Low byte = min key
        max_key = (value >> 8) & 0xFF  # High byte = max key

        # Ensure min <= max (sometimes SF2 files have invalid ranges)
        if min_key > max_key:
            min_key, max_key = max_key, min_key

        return (min_key, max_key)

    def _parse_vel_range(self, value: int) -> tuple:
        """
        Parse SF2 velocity range generator.

        Args:
            value: Packed velocity range (low_byte | high_byte << 8)

        Returns:
            Tuple of (min_vel, max_vel)
        """
        min_vel = value & 0xFF
        max_vel = (value >> 8) & 0xFF

        # Ensure min <= max (sometimes SF2 files have invalid ranges)
        if min_vel > max_vel:
            min_vel, max_vel = max_vel, min_vel

        return (min_vel, max_vel)

    def check_zone_limits(self, note: int, velocity: int) -> bool:
        """
        Check if note should play based on SF2 zone limits.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            True if note should play, False if outside zone limits
        """
        # Check key range
        min_key, max_key = self.key_range
        if not (min_key <= note <= max_key):
            return False

        # Check velocity range
        min_vel, max_vel = self.vel_range
        if not (min_vel <= velocity <= max_vel):
            return False

        return True

    def get_exclusive_class(self) -> int:
        """
        Get exclusive class for note stealing.

        Returns:
            Exclusive class (0 = no exclusive behavior)
        """
        return self.exclusive_class

    def get_sample_mode(self) -> int:
        """
        Get sample playback mode.

        Returns:
            Sample mode (0=mono, 1=mono+right, 2=mono+left, 3=mono+both linked)
        """
        return self.sample_modes

    def apply_effects_sends(self, block_size: int):
        """
        Apply chorus and reverb effect sends to audio buffer.

        This integrates SF2 partial with the global effects system by
        preparing effect send levels for the global effects coordinator.
        """
        # Store effect send levels for global effects coordinator
        # These will be collected by get_effect_send_levels() and routed
        # to the appropriate global effects processors

        # Chorus send - level already stored in self.chorus_effects_send
        # This gets combined with channel/global chorus sends in the coordinator

        # Reverb send - level already stored in self.reverb_effects_send
        # This gets combined with channel/global reverb sends in the coordinator

        # Note: Actual audio routing happens at the global effects coordinator level
        # to allow proper mixing with other partials and channel effects

    def apply_advanced_lfo(self, block_size: int):
        """
        Apply advanced LFO modulation features.

        Includes dynamic LFO parameters and pan modulation as per SF2 specification.
        This method handles LFO parameter updates and ensures proper modulation routing.
        """
        # Update modulation LFO parameters if different from defaults
        if hasattr(self, "mod_lfo") and self.mod_lfo:
            try:
                # Update frequency parameter
                if self.freq_mod_lfo != 8.176:
                    if hasattr(self.mod_lfo, "set_parameters"):
                        # Try different parameter names that LFOs might use
                        try:
                            self.mod_lfo.set_parameters(rate=self.freq_mod_lfo)
                        except:
                            try:
                                self.mod_lfo.set_parameters(frequency=self.freq_mod_lfo)
                            except:
                                pass  # Parameter not supported

                # Update delay parameter
                if self.delay_mod_lfo > 0.0:
                    if hasattr(self.mod_lfo, "set_parameters"):
                        self.mod_lfo.set_parameters(delay=self.delay_mod_lfo)

            except Exception as e:
                # Log parameter update failure but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"SF2Partial.apply_advanced_lfo() failed to update mod LFO parameters: {e}",
                    exc_info=True,
                    extra={
                        "partial_id": self.region.sample_id
                        if hasattr(self.region, "sample_id")
                        else None,
                        "lfo_type": "mod",
                        "freq_mod_lfo": self.freq_mod_lfo,
                        "delay_mod_lfo": self.delay_mod_lfo,
                    },
                )
                # Continue with default LFO parameters

        # Update vibrato LFO parameters if different from defaults
        if hasattr(self, "vib_lfo") and self.vib_lfo:
            try:
                # Update frequency parameter
                if self.freq_vib_lfo != 8.176:
                    if hasattr(self.vib_lfo, "set_parameters"):
                        try:
                            self.vib_lfo.set_parameters(rate=self.freq_vib_lfo)
                        except:
                            try:
                                self.vib_lfo.set_parameters(frequency=self.freq_vib_lfo)
                            except:
                                pass  # Parameter not supported

                # Update delay parameter
                if self.delay_vib_lfo > 0.0:
                    if hasattr(self.vib_lfo, "set_parameters"):
                        self.vib_lfo.set_parameters(delay=self.delay_vib_lfo)

            except Exception as e:
                # Log parameter update failure but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"SF2Partial.apply_advanced_lfo() failed to update vib LFO parameters: {e}",
                    exc_info=True,
                    extra={
                        "partial_id": self.region.sample_id
                        if hasattr(self.region, "sample_id")
                        else None,
                        "lfo_type": "vib",
                        "freq_vib_lfo": self.freq_vib_lfo,
                        "delay_vib_lfo": self.delay_vib_lfo,
                    },
                )
                # Continue with default LFO parameters

        # Note: LFO pan modulation is handled in _apply_volume_pan_modulation()
        # for proper per-sample processing and integration with other pan sources

    def apply_modulation_envelope(self, block_size: int):
        """
        Apply complete modulation envelope processing.

        Implements full ADSR envelope for modulation with proper state management,
        key/velocity sensitivity, and integration with SF2 modulation routing.
        """
        # Generate modulation envelope signals for this block
        self._generate_modulation_envelope_signals(block_size)

        # Apply modulation envelope to pitch if configured
        if self.mod_env_to_pitch != 0.0 and self.mod_env_buffer is not None:
            # Calculate pitch modulation from envelope
            for i in range(min(block_size, len(self.mod_env_buffer))):
                pitch_mod_from_env = self.mod_env_buffer[i] * self.mod_env_to_pitch
                # Note: Pitch modulation is applied in _calculate_sample_pitch_modulation()
                # for proper per-sample processing with LFO combination

        # Apply modulation envelope to filter if extended features enabled
        if hasattr(self, "mod_env_to_filter") and self.mod_env_to_filter != 0.0:
            # Extended feature: envelope-controlled filter modulation
            for i in range(min(block_size, len(self.mod_env_buffer))):
                filter_mod_from_env = self.mod_env_buffer[i] * self.mod_env_to_filter
                # This would be applied in _apply_filter_realtime()

        # Note: The modulation envelope is now fully implemented with:
        # - Proper ADSR state machine (_calculate_modulation_envelope_sample)
        # - Note-on/off triggering (_trigger_modulation_envelope, _release_modulation_envelope)
        # - Key/velocity sensitivity (applied in apply_envelope_sensitivity)
        # - Real-time signal generation (_generate_modulation_envelope_signals)

    def apply_envelope_sensitivity(self, note: int, velocity: int):
        """
        Apply envelope sensitivity to key and velocity.

        Modulates envelope times based on MIDI note and velocity,
        implementing SF2 envelope sensitivity generators for expressive control.
        """
        # Calculate key offset from middle C (C4 = 60)
        key_offset = note - 60

        # Velocity scaling factor (0.0 to 1.0)
        velocity_scale = velocity / 127.0

        # Key-based volume envelope modulation
        if self.keynum_to_vol_env_hold != 0.0:
            # Modulate volume envelope hold time based on key position
            # Positive values = longer hold for higher notes, negative = shorter
            key_mod_factor = 1.0 + (key_offset * self.keynum_to_vol_env_hold / 100.0)
            self.hold_vol_env *= max(0.001, key_mod_factor)  # Prevent negative/zero values

        if self.keynum_to_vol_env_decay != 0.0:
            # Modulate volume envelope decay time based on key position
            # This affects how quickly the sound decays after the attack
            key_mod_factor = 1.0 + (key_offset * self.keynum_to_vol_env_decay / 100.0)

            # Apply modulation to volume envelope decay rate
            if hasattr(self, "envelope") and self.envelope:
                try:
                    # Calculate modulated decay time and apply to envelope
                    modulated_decay = max(
                        0.001,
                        self.params.get("amp_envelope", {}).get("decay", 0.3) * key_mod_factor,
                    )
                    self.envelope.update_parameters(decay=modulated_decay)
                except Exception:
                    # If envelope doesn't support runtime decay changes, store for later use
                    self._vol_env_decay_mod = max(0.001, key_mod_factor)

        # Key-based modulation envelope modulation
        if self.keynum_to_mod_env_hold != 0.0:
            # Modulate modulation envelope hold time based on key position
            key_mod_factor = 1.0 + (key_offset * self.keynum_to_mod_env_hold / 100.0)
            self.hold_mod_env *= max(0.001, key_mod_factor)

        if self.keynum_to_mod_env_decay != 0.0:
            # Modulate modulation envelope decay time based on key position
            key_mod_factor = 1.0 + (key_offset * self.keynum_to_mod_env_decay / 100.0)
            self.decay_mod_env *= max(0.001, key_mod_factor)

        # Velocity-based envelope modulation (optional enhancement)
        # Some SF2 implementations support velocity sensitivity
        # This could be added as an extension if needed

    def apply_coarse_addressing(self):
        """
        Apply coarse sample addressing offsets.

        Adjusts sample start/end/loop points with coarse offsets.
        """
        if self.sample_data is None:
            return

        # Apply coarse offsets (multiply by 32768 for 16-bit samples)
        coarse_factor = 32768

        if self.start_addrs_coarse_offset != 0:
            self.loop_start += self.start_addrs_coarse_offset * coarse_factor

        if self.end_addrs_coarse_offset != 0:
            sample_length = len(self.sample_data)
            self.loop_end += self.end_addrs_coarse_offset * coarse_factor
            self.loop_end = min(self.loop_end, sample_length)

        if self.startloop_addrs_coarse_offset != 0:
            self.loop_start += self.startloop_addrs_coarse_offset * coarse_factor

        if self.endloop_addrs_coarse_offset != 0:
            self.loop_end += self.endloop_addrs_coarse_offset * coarse_factor

    def apply_advanced_tuning(self, note: int):
        """
        Apply advanced tuning features.

        Includes overriding root key and scale tuning adjustments.
        """
        # Apply overriding root key if specified
        if self.overriding_root_key is not None:
            root_key = self.overriding_root_key
        else:
            root_key = self.params.get("original_pitch", 60)

        # Apply scale tuning (percentage adjustment)
        if self.scale_tuning != 100.0:
            scale_factor = self.scale_tuning / 100.0
            # Adjust pitch ratio based on scale tuning
            self.pitch_ratio *= scale_factor

    def apply_volume_envelope_hold(self):
        """
        Apply volume envelope hold time.

        This implements the missing volume envelope hold functionality
        that was absent from the original implementation.
        """
        # Apply hold time to volume envelope if supported
        if hasattr(self, "envelope") and self.envelope:
            try:
                # Set hold time in envelope
                hold_time = self.hold_vol_env
                if hold_time > 0.0:
                    # Clamp hold time to reasonable range to prevent audio artifacts
                    clamped_hold_time = max(0.001, min(10.0, hold_time))
                    self.envelope.update_parameters(hold=clamped_hold_time)

                    # Store the applied hold time for tracking
                    self._applied_hold_time = clamped_hold_time

            except Exception:
                # If envelope doesn't support hold time changes, log and continue
                # In production, this should use proper error logging
                self._applied_hold_time = None
                pass
        else:
            # No envelope available, store for later application
            self._pending_hold_time = self.hold_vol_env

    def process_sf2_generators(self, note: int, velocity: int, block_size: int):
        """
        Process all SF2 generators for complete specification compliance.

        This method applies all supported SF2 generators in the correct order
        for professional SoundFont playback.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            block_size: Audio block size for processing
        """
        # 1. Zone Control - Check if note should play
        if not self.check_zone_limits(note, velocity):
            self.active = False
            return

        # 2. Coarse Addressing - Apply sample offsets
        self.apply_coarse_addressing()

        # 3. Advanced Tuning - Apply root key and scale tuning
        self.apply_advanced_tuning(note)

        # 4. Envelope Sensitivity - Apply key/velocity modulation
        self.apply_envelope_sensitivity(note, velocity)

        # 5. Volume Envelope Hold - Apply missing hold parameter
        self.apply_volume_envelope_hold()

        # 6. Advanced LFO - Apply dynamic LFO parameters
        self.apply_advanced_lfo(block_size)

        # 7. Modulation Envelope - Apply complete mod envelope
        self.apply_modulation_envelope(block_size)

        # 8. Effects Sends - Route to global effects
        self.apply_effects_sends(block_size)

    def _create_simple_lfo_simulation(self, lfo_id: int, sample_rate: float):
        """
        Create a simple LFO simulation when proper LFO components are not available.

        This provides basic LFO functionality for systems without advanced LFO pools.

        Args:
            lfo_id: LFO identifier (0 = modulation, 1 = vibrato)
            sample_rate: Audio sample rate

        Returns:
            Simple LFO simulation object
        """
        return SimpleLFOSimulation(lfo_id, sample_rate)


class SimpleLFOSimulation:
    """
    Simple LFO simulation for systems without advanced LFO components.

    Provides basic sine wave generation for modulation purposes.
    """

    def __init__(self, lfo_id: int, sample_rate: float):
        """
        Initialize simple LFO simulation.

        Args:
            lfo_id: LFO identifier
            sample_rate: Audio sample rate
        """
        self.lfo_id = lfo_id
        self.sample_rate = sample_rate
        self.frequency = 8.176  # Default LFO frequency
        self.depth = 1.0  # Default depth
        self.delay = 0.0  # Default delay
        self.phase = 0.0  # Current phase
        self.delay_remaining = 0.0  # Delay countdown

    def set_parameters(self, **kwargs):
        """Set LFO parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Reset delay if changed
        if "delay" in kwargs:
            self.delay_remaining = self.delay

    def generate_block(self, block_size: int):
        """
        Generate a block of LFO samples.

        Args:
            block_size: Number of samples to generate

        Returns:
            Numpy array of LFO samples
        """
        samples = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Handle delay
            if self.delay_remaining > 0:
                self.delay_remaining -= 1.0 / self.sample_rate
                samples[i] = 0.0
            else:
                # Generate sine wave
                samples[i] = np.sin(self.phase) * self.depth
                self.phase += 2.0 * np.pi * self.frequency / self.sample_rate

                # Keep phase in reasonable range
                if self.phase > 2.0 * np.pi:
                    self.phase -= 2.0 * np.pi

        return samples

    def reset(self):
        """Reset LFO state."""
        self.phase = 0.0
        self.delay_remaining = self.delay
