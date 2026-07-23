"""

SF2 Region - Production-grade SoundFont 2 region with full SF2 package integration.

Part of the unified region-based synthesis architecture.
SF2Region implements SF2 wavetable synthesis with:
- Full SF2 v2.04 specification compliance
- Lazy sample loading via SF2SoundFontManager
- SF2 modulation matrix integration
- Mip-map sample anti-aliasing
- AVL range tree zone lookups
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import numpy as np

from ...engines.region_descriptor import RegionDescriptor
from ...processing.partial.region import IRegion, RegionState
from .sf2_modulator_evaluator import (
    SF2ModulatorEvaluator,
    apply_modulation_to_params,
)

logger = logging.getLogger(__name__)


class SF2Region(IRegion):
    """
    Production-grade SF2 region with full SF2 package integration.

    Features:
    - Full SF2 v2.04 specification compliance
    - Lazy sample loading via SF2SoundFontManager
    - SF2 generator inheritance (preset + instrument levels)
    - SF2 modulation matrix integration
    - Mip-map sample anti-aliasing
    - All 60+ SF2 generators supported

    Attributes:
        descriptor: Region metadata with SF2 parameters
        sample_rate: Audio sample rate
        soundfont_manager: SF2SoundFontManager for sample/zone access
    """

    __slots__ = [
        # Core state
        # Mip-map cache
        # Generator params
        # Zone cache
        # Silent buffer for early return paths
        # External references
        # LFO objects (zero-allocation: reused)
        # LFO buffers (pre-allocated, zero-allocation)
        # Modulation envelope buffer
        # Pitch envelope buffer
        # Pitch modulation
        # Filter modulation
        # Volume modulation
        # Pan
        # Modulation envelope state
        # Modulation envelope params
        # LFO params
        # Key tracking
        # Effects sends
        # Controller modulation
        # Filter type
        # Velocity processing
        # Pitch envelope
        # Drum mode
        # Reverse playback
        # Loop crossfade
        # Current block size for buffer sizing
        # Portamento
        # Pedals
        # XG Sound Controllers
        # Envelope/Vibrato XG (CC73-79)
        # General Purpose Buttons
        # Tremolo (CC92)
        # Balance (CC8)
        # Previous note for portamento
        "_active",
        "_aftertouch_mod",
        "_attack_mod_env",
        "_balance",
        "_base_phase_step",
        "_breath_mod",
        "_cached_mip_data",
        "_cached_mip_level",
        "_chorus_send",
        "_coarse_tune",
        "_current_block_size",
        "_decay_mod_env",
        "_decay_mod_env_tc",
        "_delay_mod_env",
        "_delay_mod_lfo",
        "_delay_vib_lfo",
        "_exclusive_class",
        "_expression_mod",
        "_filter_key_track",
        "_filter_mod",
        "_filter_type",
        "_filter_work_left",
        "_filter_work_right",
        "_fine_tune",
        "_foot_mod",
        "_freq_mod_lfo",
        "_freq_vib_lfo",
        "_generator_params",
        "_gp_button_1",
        "_gp_button_2",
        "_gp_button_3",
        "_gp_button_4",
        "_gs_amp_attack",
        "_gs_amp_decay",
        "_gs_amp_release",
        "_gs_chorus_send",
        "_gs_filter_cutoff",
        "_gs_filter_resonance",
        "_gs_pan",
        "_gs_reverb_send",
        "_gs_vibrato_delay",
        "_gs_vibrato_depth",
        "_gs_vibrato_rate",
        "_gs_volume",
        "_held_by_hold2",
        "_held_by_sostenuto",
        "_hold2_pedal",
        "_hold_mod_env",
        "_hold_mod_env_tc",
        "_initial_attenuation_db",
        "_is_drum_mode",
        "_key_range",
        "_keynum_to_mod_env_decay",
        "_keynum_to_mod_env_hold",
        "_keynum_to_vol_env_decay",
        "_keynum_to_vol_env_hold",
        "_last_note",
        "_legato_active",
        "_loop_crossfade_samples",
        "_loop_end",
        "_base_loop_end",
        "_base_loop_start",
        "_loop_mode",
        "_loop_start",
        "_mod_env_buffer",
        "_mod_env_level",
        "_mod_env_stage",
        "_mod_env_stage_time",
        "_mod_env_time_in_stage",
        "_mod_env_to_filter",
        "_mod_env_to_pan",
        "_mod_env_to_pitch",
        "_mod_env_to_volume",
        "_mod_lfo",
        "_modulators_warned",
        "_mod_lfo_buffer",
        "_mod_lfo_to_filter",
        "_mod_lfo_to_pan",
        "_mod_lfo_to_pitch",
        "_mod_lfo_to_volume",
        "_vib_lfo_to_volume",
        "_modulators",
        "_mod_evaluator",
        "_modwheel_mod",
        "_note_start_time",          # Voice stealing: note start timestamp
        "_pan_position",
        "_phase_step",
        "_pitch_env_active",
        "_read_positions",
        "_pitch_env_attack",
        "_pitch_env_buffer",
        "_pitch_env_decay",
        "_pitch_env_delay",
        "_pitch_env_depth",
        "_pitch_env_level",
        "_pitch_env_release",
        "_pitch_env_stage",
        "_pitch_env_sustain",
        "_pitch_env_time_in_stage",
        "_pitch_mod",
        "_portamento_active",
        "_portamento_glide_phase",
        "_portamento_note",
        "_portamento_target",
        "_portamento_time",
        "_release_mod_env",
        "_reverb_send",
        "_reverse_playback",
        "_root_key",
        "_sample_data",
        "_sample_position",
        "_effective_end",  # frame index where playback must stop (gen 1/12 end offset)
        "_sf2_instrument",
        "_sf2_preset",
        "_sf2_zone",
        "_silence_buffer",
        "_soft_pedal",
        "_soft_pedal_depth",
        "_sostenuto_pedal",
        "_stereo_width",             # Stereo width (0.0=mono, 1.0=full, 2.0=wide)
        "_sound_controller_1",
        "_sustain_mod_env",
        "_sustain_pedal",
        "_tremolo_depth",
        "_velocity_curve",
        "_velocity_range",
        "_vib_lfo",
        "_vib_lfo_buffer",
        "_vib_lfo_to_pan",
        "_vib_lfo_to_pitch",
        "_vib_lfo_to_pitch_base",
        "_voice_priority",           # Voice stealing priority (lower = stolen first)
        "_volume_mod",
        "_xg_attack_time",
        "_xg_decay_time",
        "_xg_filter_cutoff",
        "_xg_release_time",
        "_xg_vibrato_delay",
        "_xg_vibrato_depth",
        "_xg_vibrato_rate",
        "soundfont_manager",
        "synth",
    ]

    def __init__(
        self,
        descriptor: RegionDescriptor,
        sample_rate: int = 44100,
        soundfont_manager: Any | None = None,
        synth: Any | None = None,
        buffer_pool: Any | None = None,
    ):
        """
        Initialize SF2 region with full SF2 package integration.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz
            soundfont_manager: SF2SoundFontManager for sample/zone access
            synth: ModernXGSynthesizer instance for infrastructure access
            buffer_pool: Optional BufferPool for zero-allocation audio paths
        """
        super().__init__(descriptor, sample_rate, buffer_pool=buffer_pool)
        self.synth = synth
        self.soundfont_manager = soundfont_manager

        # SF2-specific state (lazy loaded)
        self._sample_data: np.ndarray | None = None

        # Mip-map cache (stereo interleaved format)
        self._cached_mip_level: int = -1
        self._cached_mip_data: np.ndarray | None = None

        self._loop_start: int = 0
        self._loop_end: int = 0
        self._base_loop_start: int = 0
        self._base_loop_end: int = 0
        self._loop_mode: int = 0

        # SF2 zone cache (lazy loaded from SF2 package)
        self._sf2_zone: Any | None = None
        self._sf2_preset: Any | None = None
        self._sf2_instrument: Any | None = None

        # SF2 generator parameters (merged from preset + instrument levels)
        self._generator_params: dict[int, int] = {}
        self._modulators: list[dict[str, Any]] = []
        self._modulators_warned: bool = False
        self._mod_evaluator: SF2ModulatorEvaluator | None = None

        # SF2 zone ranges
        self._key_range: tuple[int, int] = (0, 127)
        self._velocity_range: tuple[int, int] = (0, 127)
        self._exclusive_class: int = 0

        # Playback state
        self._root_key: int = 60
        self._coarse_tune: int = 0
        self._fine_tune: float = 0.0
        self._sample_position: float = 0.0
        self._effective_end: int = 0  # 0 = unset; set by _apply_address_offsets
        self._phase_step: float = 1.0
        self._base_phase_step: float = 1.0

        # Initial attenuation (gen 48)
        self._initial_attenuation_db: float = 0.0

        # Voice active state
        self._active: bool = False
        self._current_block_size: int = 1024
        self._note_start_time: float = 0.0
        self._voice_priority: float = 0.0

        # Silent buffer for early return paths (lazy allocated)
        self._silence_buffer: np.ndarray | None = None

        # Initialize LFO objects (zero-allocation: created once)
        self._mod_lfo = None
        self._vib_lfo = None
        self._mod_lfo_buffer: np.ndarray | None = None
        self._vib_lfo_buffer: np.ndarray | None = None
        self._mod_env_buffer: np.ndarray | None = None
        self._pitch_env_buffer: np.ndarray | None = None
        self._read_positions: np.ndarray | None = None
        self._filter_work_left: np.ndarray | None = None
        self._filter_work_right: np.ndarray | None = None

        # Pitch modulation
        self._pitch_mod: float = 0.0
        self._vib_lfo_to_pitch: float = 0.0
        self._vib_lfo_to_pitch_base: float = 0.0  # Clean value for modwheel modulation
        self._mod_lfo_to_pitch: float = 0.0
        self._mod_env_to_pitch: float = 0.0

        # Filter modulation
        self._filter_mod: float = 0.0
        self._mod_lfo_to_filter: float = 0.0
        self._mod_env_to_filter: float = 0.0
        self._filter_key_track: float = 0.0

        # Volume modulation
        self._volume_mod: float = 1.0
        self._mod_lfo_to_volume: float = 0.0
        self._vib_lfo_to_volume: float = 0.0
        self._mod_env_to_volume: float = 0.0

        # Pan
        self._pan_position: float = 0.0
        self._mod_lfo_to_pan: float = 0.0
        self._vib_lfo_to_pan: float = 0.0
        self._mod_env_to_pan: float = 0.0

        # Stereo width
        self._stereo_width: float = 1.0

        # Modulation envelope state
        self._mod_env_stage: int = (
            0  # 0=idle, 1=delay, 2=attack, 3=hold, 4=decay, 5=sustain, 6=release
        )
        self._mod_env_level: float = 0.0
        self._mod_env_stage_time: float = 0.0
        self._mod_env_time_in_stage: float = 0.0

        # Modulation envelope params
        self._delay_mod_env: float = 0.0
        self._attack_mod_env: float = 0.0
        self._hold_mod_env: float = 0.0
        self._decay_mod_env: float = 0.0
        self._sustain_mod_env: float = 0.0
        self._release_mod_env: float = 0.0

        # LFO params
        self._delay_mod_lfo: float = 0.0
        self._freq_mod_lfo: float = 8.176
        self._delay_vib_lfo: float = 0.0
        self._freq_vib_lfo: float = 8.176

        # Key tracking
        self._keynum_to_mod_env_hold: float = 0.0
        self._keynum_to_mod_env_decay: float = 0.0
        self._keynum_to_vol_env_hold: float = 0.0
        self._keynum_to_vol_env_decay: float = 0.0

        # Effects sends
        self._reverb_send: float = 0.0
        self._chorus_send: float = 0.0

        # Controller modulation
        self._aftertouch_mod: float = 0.0
        self._breath_mod: float = 0.0
        self._modwheel_mod: float = 0.0
        self._foot_mod: float = 0.0
        self._expression_mod: float = 1.0  # CC11 defaults to 127 (full)

        # Filter type
        self._filter_type: int = 0

        # Velocity processing
        self._velocity_curve: int = 0

        # Pitch envelope
        self._pitch_env_active: bool = False
        self._pitch_env_stage: int = 0
        self._pitch_env_level: float = 0.0
        self._pitch_env_time_in_stage: float = 0.0
        self._pitch_env_delay: float = 0.0
        self._pitch_env_attack: float = 0.0
        self._pitch_env_decay: float = 0.0
        self._pitch_env_sustain: float = 0.0
        self._pitch_env_release: float = 0.0
        self._pitch_env_depth: float = 0.0

        # Drum mode
        self._is_drum_mode: bool = False

        # Reverse playback
        self._reverse_playback: bool = False

        # Loop crossfade
        self._loop_crossfade_samples: int = 0

        # Portamento
        self._portamento_active: bool = False
        self._portamento_time: float = 0.0
        self._portamento_note: int | None = None
        self._portamento_target: int | None = None
        self._portamento_glide_phase: float = 0.0

        # Pedals
        self._sustain_pedal: bool = False
        self._sostenuto_pedal: bool = False
        self._soft_pedal: bool = False
        self._soft_pedal_depth: float = 0.6
        self._legato_active: bool = False
        self._hold2_pedal: bool = False
        self._held_by_sostenuto: bool = False
        self._held_by_hold2: bool = False

        # XG Sound Controllers
        self._sound_controller_1: float = 0.0

        # Envelope/Vibrato XG (CC73-79)
        self._xg_release_time: float = 0.0
        self._xg_attack_time: float = 0.0
        self._xg_filter_cutoff: float = 0.0
        self._xg_decay_time: float = 0.0
        self._xg_vibrato_rate: float = 0.0
        self._xg_vibrato_depth: float = 0.0
        self._xg_vibrato_delay: float = 0.0

        # General Purpose Buttons
        self._gp_button_1: float = 0.0
        self._gp_button_2: float = 0.0
        self._gp_button_3: float = 0.0
        self._gp_button_4: float = 0.0

        # Tremolo (CC92)
        self._tremolo_depth: float = 0.0

        # Balance (CC8)
        self._balance: float = 0.0

        # GS parameter state (from GS sysex bridge, -1.0 = unset/use default)
        self._gs_filter_cutoff: float = -1.0
        self._gs_filter_resonance: float = -1.0
        self._gs_amp_attack: float = -1.0
        self._gs_amp_decay: float = -1.0
        self._gs_amp_release: float = -1.0
        self._gs_vibrato_rate: float = -1.0
        self._gs_vibrato_depth: float = -1.0
        self._gs_vibrato_delay: float = -1.0
        self._gs_volume: float = -1.0
        self._gs_pan: float = -1.0
        self._gs_reverb_send: float = -1.0
        self._gs_chorus_send: float = -1.0

        # Previous note for portamento
        self._last_note: int | None = None

    def initialize(self) -> bool:
        """
        Initialize SF2 region resources.

        SF2Region handles audio generation directly without a partial.

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        try:
            if self.descriptor.sample_id is not None or self.descriptor.sample_path:
                self._sample_data = self._load_sample_data()
                if self._sample_data is None and self.descriptor.is_sample_based():
                    return False

            self._init_envelopes()
            self._init_filters()
            self._allocate_buffers()

            self._initialized = True
            self.state = RegionState.INITIALIZED
            return True

        except Exception as e:
            logger.error(f"SF2Region initialization failed: {e}")
            return False

    def _load_sample_data(self) -> np.ndarray | None:
        """
        Load sample data from SF2SoundFontManager with mip-map support.

        Returns:
            Sample data as numpy array, or None if loading failed
        """
        if self.descriptor.sample_id is None:
            return None

        try:
            # Use SF2SoundFontManager's optimized sample loading
            # This includes mip-map anti-aliasing
            sample_data = self.soundfont_manager.get_sample_data(self.descriptor.sample_id)

            if sample_data is not None:
                self._sample_data = np.asarray(sample_data, dtype=np.float32)
                self.descriptor.is_sample_loaded = True

                # Extract loop information from SF2 sample header
                self._load_loop_info()

                # Extract root key from sample
                self._load_sample_info()

                return self._sample_data

            logger.warning(f"Failed to load SF2 sample {self.descriptor.sample_id}")
            return None

        except Exception as e:
            logger.error(f"SF2 sample loading failed: {e}")
            return None

    def _load_loop_info(self) -> None:
        """Load loop information from SF2 sample header."""
        if self.descriptor.sample_id is None:
            return

        # Get loop info from SF2SoundFontManager
        if hasattr(self.soundfont_manager, "get_sample_loop_info"):
            loop_info = self.soundfont_manager.get_sample_loop_info(self.descriptor.sample_id)
            if loop_info:
                self._loop_start = loop_info.get("start", 0)
                self._loop_end = loop_info.get("end", len(self._sample_data))
                self._base_loop_start = self._loop_start
                self._base_loop_end = self._loop_end
                self._loop_mode = loop_info.get("mode", 0)

    def _load_sample_info(self) -> None:
        """Load sample root key and tuning from SF2 sample header.

        Supports overridingRootKey (gen 58): if set (>= 0), the root key
        comes from the generator instead of the sample header (SF2.01 §8.1.3).
        """
        if self.descriptor.sample_id is None:
            return

        # Get sample info from SF2SoundFontManager
        if hasattr(self.soundfont_manager, "get_sample_info"):
            sample_info = self.soundfont_manager.get_sample_info(self.descriptor.sample_id)
            if sample_info:
                self._root_key = sample_info.get("original_pitch", 60)

        # Check for overridingRootKey (gen 58) — zone-level override wins
        overriding_root = self._get_generator_value(58, -1)
        if overriding_root >= 0:
            self._root_key = overriding_root

    def _get_sf2_zone(self) -> Any | None:
        """
        Get cached SF2Zone object from descriptor.

        Returns:
            SF2Zone instance or None
        """
        if self._sf2_zone is not None:
            return self._sf2_zone

        # Load zone from SF2SoundFontManager if available
        if self.soundfont_manager and hasattr(self.soundfont_manager, "get_zone"):
            try:
                self._sf2_zone = self.soundfont_manager.get_zone(self.descriptor.region_id)

                if self._sf2_zone:
                    # Cache generator parameters from zone
                    self._cache_zone_generators()

            except Exception as e:
                logger.error(f"Failed to load SF2 zone: {e}")

        return self._sf2_zone

    def _cache_zone_generators(self) -> None:
        """Cache generator parameters from SF2 zone."""
        if self._sf2_zone is None:
            return

        # Cache key/velocity ranges
        self._key_range = self._sf2_zone.key_range
        self._velocity_range = self._sf2_zone.velocity_range

        # Cache generators
        self._generator_params = self._sf2_zone.generators.copy()

        # Cache modulators
        self._modulators = self._sf2_zone.modulators.copy()

        # Cache exclusive class (SF2 gen 57)
        self._exclusive_class = self._get_generator_value(57, 0)  # exclusiveClass

        # Apply SF2 address-offset generators (0-4, 12, 45, 50) to loop/playback bounds
        self._apply_address_offsets()

    def _apply_address_offsets(self) -> None:
        """
        Apply SF2 address-offset generators to loop and playback bounds.

        SF2.01 §8.1.3: fine offsets are in sample words; coarse offsets are
        32768 sample words. Stereo samples store 2 words per frame, so word
        offsets are divided by 2 to land on frame boundaries (matching the
        stereo handling in ``get_sample_loop_info``). Mono samples use 1 word
        per frame, so no division is applied.

        Offsets are applied to the cached frame-space bounds (``_loop_start``,
        ``_loop_end``, ``_sample_position``, ``_effective_end``) only. The
        shared ``_sample_data`` array is never mutated, so concurrent voices
        that share the same sample cache are unaffected.
        """
        if self._sample_data is None or len(self._sample_data) == 0:
            return

        # 1 word = 1 frame for mono; 2 words = 1 frame for stereo.
        words_per_frame = 2 if self.descriptor.is_stereo else 1

        def offset_frames(fine_gen: int, coarse_gen: int) -> int:
            words = self._get_generator_value(fine_gen, 0) + 32768 * self._get_generator_value(
                coarse_gen, 0
            )
            # Floor toward zero to stay within the source frame; clamp to >= 0.
            frames = words // words_per_frame if words >= 0 else -((-words) // words_per_frame)
            return frames

        start_off = offset_frames(0, 4)  # gen0 startAddrsOffset + gen4 startAddrsCoarseOffset
        end_off = offset_frames(1, 12)  # gen1 endAddrsOffset + gen12 endAddrsCoarseOffset
        loop_start_off = offset_frames(2, 45)  # gen2 + gen45
        loop_end_off = offset_frames(3, 50)  # gen3 + gen50

        sample_length = len(self._sample_data)

        # Playback start position (gen0/gen4)
        self._sample_position = float(max(0, min(start_off, sample_length - 1)))

        # Loop bounds (gen2/3 + gen45/50)
        if self._loop_start > 0 or self._loop_end > 0:
            self._loop_start = max(0, self._loop_start + loop_start_off)
            self._loop_end = max(self._loop_start + 1, self._loop_end + loop_end_off)
            self._loop_end = min(self._loop_end, sample_length - 1)

        # Effective end-of-sample bound (gen1/gen12). The render path stops at
        # len(mip_data) for one-shot regions, so record an explicit bound here.
        self._effective_end = max(0, min(sample_length - 1, sample_length - 1 + end_off))

    def _get_generator_value(self, gen_type: int, default: int = 0) -> int:
        """
        Get SF2 generator value with inheritance from global zone.

        Args:
            gen_type: SF2 generator type (0-65)
            default: Default value if not found

        Returns:
            Generator value
        """
        # First check local zone generators
        if self._generator_params and gen_type in self._generator_params:
            return self._generator_params[gen_type]

        # Fall back to descriptor generator params
        if self.descriptor.generator_params:
            # Map common generator types (SF2 spec gen numbers)
            gen_mapping = {
                33: "amp_delay",      # delayVolEnv
                34: "amp_attack",     # attackVolEnv
                35: "amp_hold",       # holdVolEnv
                36: "amp_decay",      # decayVolEnv
                37: "amp_sustain",    # sustainVolEnv
                38: "amp_release",    # releaseVolEnv
                8: "filter_cutoff",   # initialFilterFc
                9: "filter_resonance", # initialFilterQ
                51: "coarse_tune",    # coarseTune
                52: "fine_tune",      # fineTune
            }

            param_name = gen_mapping.get(gen_type)
            if param_name and param_name in self.descriptor.generator_params:
                return self.descriptor.generator_params[param_name]

        return default

    def _create_partial(self) -> Any | None:
        """
        SF2Region handles sample playback directly, no partial needed.
        """
        return None

    def _build_partial_params_from_generators(self) -> dict[str, Any]:
        """
        Build partial parameters from SF2 generators (all 60+).
        Uses nested structure compatible with SF2Partial._load_sf2_parameters().

        Returns:
            Dictionary of partial parameters with nested structure
        """
        params = {
            # Sample data
            "sample_data": self._sample_data,
            "note": self.current_note,
            "velocity": self.current_velocity,
            "original_pitch": self._root_key,
            # Loop info (nested)
            "loop": {
                "mode": self._get_generator_value(54, 0),  # sampleModes
                "start": self._loop_start,
                "end": self._loop_end,
            },
            # Volume envelope (nested, SF2 gen 33-38)
            "amp_envelope": {
                "delay": self._timecents_to_seconds(self._get_generator_value(33, -12000)),
                "attack": self._timecents_to_seconds(self._get_generator_value(34, -12000)),
                "hold": self._timecents_to_seconds(self._get_generator_value(35, -12000)),
                "decay": self._timecents_to_seconds(self._get_generator_value(36, -12000)),
                "sustain": self._get_generator_value(37, 0) / 1000.0,
                "release": self._timecents_to_seconds(self._get_generator_value(38, -12000)),
            },
            # Modulation envelope (nested, SF2 gen 25-30)
            "mod_envelope": {
                "delay": self._timecents_to_seconds(self._get_generator_value(25, -12000)),
                "attack": self._timecents_to_seconds(self._get_generator_value(26, -12000)),
                "hold": self._timecents_to_seconds(self._get_generator_value(27, -12000)),
                "decay": self._timecents_to_seconds(self._get_generator_value(28, -12000)),
                "sustain": self._get_generator_value(29, 0) / 1000.0,
                "release": self._timecents_to_seconds(self._get_generator_value(30, -12000)),
                "to_pitch": self._get_generator_value(7, 0) / 100.0,  # modEnvToPitch
            },
            # Mod LFO (nested, SF2 gen 21-22)
            "mod_lfo": {
                "delay": self._timecents_to_seconds(self._get_generator_value(21, -12000)),
                "frequency": self._cents_to_frequency(self._get_generator_value(22, 0)),
                "to_volume": self._get_generator_value(13, 0) / 960.0,  # modLfoToVolume
                "to_filter": self._get_generator_value(10, 0) / 1200.0,  # modLfoToFilterFc
                "to_pitch": self._get_generator_value(5, 0) / 1200.0,  # modLfoToPitch
            },
            # Vib LFO (nested, SF2 gen 6)
            "vib_lfo": {
                "delay": self._timecents_to_seconds(self._get_generator_value(23, -12000)),  # delayVibLFO
                "frequency": self._cents_to_frequency(self._get_generator_value(24, 0)),  # freqVibLFO
                "to_pitch": self._get_generator_value(6, 0) / 1200.0,  # vibLfoToPitch
            },
            # Filter (nested, SF2 gen 8-9)
            "filter": {
                "cutoff": self._cents_to_frequency(self._get_filter_cutoff_cents()),
                "resonance": self._get_generator_value(9, 0) / 10.0,
                "type": "lowpass",
            },
            # Effects (nested, SF2 gen 15-17)
            "effects": {
                "reverb_send": self._get_generator_value(16, 0) / 1000.0,
                "chorus_send": self._get_generator_value(15, 0) / 1000.0,
                "pan": self._get_generator_value(17, 0) / 500.0,
            },
            # Pitch modulation (nested, SF2 gen 51-52, 56)
            "pitch_modulation": {
                "coarse_tune": self._get_generator_value(51, 0),
                "fine_tune": self._get_generator_value(52, 0) / 100.0,
                "scale_tuning": self._get_generator_value(56, 100) / 100.0,
            },
            # Key tracking (nested, SF2 gen 31-32, 39-40)
            "key_tracking": {
                "to_mod_env_hold": self._get_generator_value(31, 0),
                "to_mod_env_decay": self._get_generator_value(32, 0),
                "to_vol_env_hold": self._get_generator_value(39, 0),
                "to_vol_env_decay": self._get_generator_value(40, 0),
            },
            # Sample settings (nested)
            "sample_settings": {
                "mode": self._get_generator_value(54, 0),  # sampleModes
                "exclusive_class": self._get_generator_value(57, 0),  # exclusiveClass
            },
            # Modulators list
            "modulators": self._modulators,
            # Generators dict for direct access
            "generators": dict(self._generator_params),
        }

        return params

    def _timecents_to_seconds(self, timecents: int) -> float:
        """Convert SF2 timecents to seconds."""
        if timecents <= -12000:
            return 0.0  # -inf means instant
        return 2.0 ** (timecents / 1200.0)

    def _cents_to_frequency(self, cents: int) -> float:
        """Convert SF2 absolute cents to frequency in Hz.

        SF2 specifies pitch in absolute cents where 0 cents = C0 = 8.176 Hz
        (MIDI note 0), NOT 440 Hz. Using 440 Hz as the base shifts every
        computed frequency (notably the initialFilterFc lowpass cutoff) by
        ~5 octaves, which silently mutes most instruments.
        """
        return 8.176 * (2.0 ** (cents / 1200.0))

    # SF2 spec valid range for initialFilterFc (gen 8): 1500..13500 cents
    # (~19.7 Hz .. ~19.7 kHz). Values outside this range are corrupt data and
    # must be clamped, otherwise the lowpass collapses to sub-audio and the
    # voice goes silent. The spec default is 13500 (open filter).
    _SF2_FILTER_FC_MIN = 1500
    _SF2_FILTER_FC_MAX = 13500

    def _get_filter_cutoff_cents(self) -> int:
        """Read initialFilterFc (gen 8), clamped to the valid SF2 range.

        The SF2 spec range is 1500..13500 cents. Values below 1500 are corrupt
        (e.g. a negative generator from a broken soundfont). Clamping such a
        value to the 1500 minimum still yields a sub-audio lowpass (~19 Hz)
        that mutes the voice, so for clearly-invalid values we fall back to the
        spec default (13500 = open filter), which preserves the intended
        bright timbre instead of silencing the note.
        """
        raw = self._get_generator_value(8, self._SF2_FILTER_FC_MAX)
        if raw < self._SF2_FILTER_FC_MIN:
            return self._SF2_FILTER_FC_MAX
        return min(self._SF2_FILTER_FC_MAX, raw)

    def _init_lfos(self) -> None:
        """Initialize LFO objects from SF2 generators (zero-allocation)."""
        from ...primitives.oscillator import UltraFastXGLFO

        # Get LFO parameters from generators
        self._delay_mod_lfo = self._timecents_to_seconds(self._get_generator_value(21, -12000))
        self._freq_mod_lfo = self._cents_to_frequency(self._get_generator_value(22, 0))

        self._delay_vib_lfo = self._timecents_to_seconds(self._get_generator_value(23, -12000))  # delayVibLFO
        self._freq_vib_lfo = self._cents_to_frequency(self._get_generator_value(24, 0))  # freqVibLFO

        # LFO waveform: gen 43 is keyRange (standard SF2), not lfo_waveform.
        # Default to sine. Custom waveform selection belongs in XG, not SF2 gens.
        waveform_name = "sine"

        # Create LFO objects (zero-allocation: created once)
        self._mod_lfo = UltraFastXGLFO(
            id=0, sample_rate=self.sample_rate, block_size=self._current_block_size
        )
        self._mod_lfo.set_parameters(
            waveform=waveform_name, rate=self._freq_mod_lfo, depth=1.0, delay=self._delay_mod_lfo
        )

        self._vib_lfo = UltraFastXGLFO(
            id=1, sample_rate=self.sample_rate, block_size=self._current_block_size
        )
        self._vib_lfo.set_parameters(
            waveform=waveform_name, rate=self._freq_vib_lfo, depth=1.0, delay=self._delay_vib_lfo
        )

        # Load LFO modulation depths from generators (SF2 spec gen numbers)
        self._vib_lfo_to_pitch = self._get_generator_value(6, 0) / 100.0  # vibLfoToPitch
        self._vib_lfo_to_pitch_base = self._vib_lfo_to_pitch  # Save clean value for modwheel
        self._mod_lfo_to_pitch = self._get_generator_value(5, 0) / 100.0  # modLfoToPitch
        self._mod_lfo_to_filter = self._get_generator_value(10, 0) / 1200.0  # modLfoToFilterFc
        self._mod_lfo_to_volume = self._get_generator_value(13, 0) / 960.0  # modLfoToVolume
        self._vib_lfo_to_volume = self._get_generator_value(14, 0) / 960.0  # vibLfoToVolume
        # vib_lfo_to_pan: NOT stored at gen 35 (gen 35 = holdVolEnv). Disabled.
        self._vib_lfo_to_pan = 0.0
        self._mod_lfo_to_pan = self._get_generator_value(42, 0) / 10.0

    def _init_modulation_envelope(self) -> None:
        """Initialize modulation envelope state and parameters."""
        # Reset envelope state
        self._mod_env_stage = 0  # idle
        self._mod_env_level = 0.0
        self._mod_env_stage_time = 0.0
        self._mod_env_time_in_stage = 0.0

        # Load modulation envelope parameters from generators (SF2 gen 25-30)
        self._delay_mod_env = self._timecents_to_seconds(self._get_generator_value(25, -12000))  # delayModEnv
        self._attack_mod_env = self._timecents_to_seconds(self._get_generator_value(26, -12000))  # attackModEnv
        self._hold_mod_env_tc = self._get_generator_value(27, -12000)  # holdModEnv
        self._decay_mod_env_tc = self._get_generator_value(28, -12000)  # decayModEnv
        self._hold_mod_env = self._timecents_to_seconds(self._hold_mod_env_tc)
        self._decay_mod_env = self._timecents_to_seconds(self._decay_mod_env_tc)
        self._sustain_mod_env = self._get_generator_value(29, 0) / 1000.0  # sustainModEnv
        self._release_mod_env = self._timecents_to_seconds(self._get_generator_value(30, -12000))  # releaseModEnv

        # Load modulation depths (SF2 gen 7, 11)
        self._mod_env_to_pitch = self._get_generator_value(7, 0) / 100.0  # modEnvToPitch
        self._mod_env_to_filter = self._get_generator_value(11, 0) / 1200.0  # modEnvToFilterFc (gen 11)
        # Mod env → volume/pan: reserved for SF2 modulator matrix processing.
        # Currently always 0 since no standard SF2 generator maps to these.
        # (When BUG-4 modulator processing is implemented, the modulation
        #  matrix can write into these fields.)
        self._mod_env_to_volume = 0.0
        self._mod_env_to_pan = 0.0

        # Load key tracking for mod envelope
        self._keynum_to_mod_env_hold = self._get_generator_value(31, 0) / 100.0
        self._keynum_to_mod_env_decay = self._get_generator_value(32, 0) / 100.0

    def _init_pitch_envelope(self) -> None:
        """Initialize pitch envelope (separate from mod envelope).

        NOTE: The pitch envelope is a NON-STANDARD extension. Standard SF2
        generators 54 (sampleModes), 52 (fineTune), and 58 (overridingRootKey)
        were previously read here, causing false activation on any looping
        soundfont. This has been fixed:
        - Activation uses ONLY gen 55 (non-standard, no collision in spec)
        - Stages use extended generator range 55-61 to avoid conflicts
        - If pitch envelope is needed, set gen 55 > -12000 timecents
          (e.g., the attack portion of the pitch envelope).

        NOTE: Non-standard pitch envelope uses gens 55-61 which COLLIDE with
        standard SF2 generators 56 (scaleTuning) and 57 (exclusiveClass).
        When gen 55 > -12000 (pitch env active), these standard gens are
        reinterpreted as pitch env attack/decay times. Gen 55 defaults to
        -12000 (inactive) per SF2 spec, so collision is harmless in practice.
        """
        # Check if pitch envelope is active — ONLY gen 55 (non-standard extension)
        self._pitch_env_active = self._get_generator_value(55, -12000) > -12000

        if self._pitch_env_active:
            self._pitch_env_stage = 0  # idle
            self._pitch_env_level = 0.0
            self._pitch_env_time_in_stage = 0.0

            # Non-standard generators (55-61) — no collision with standard SF2
            self._pitch_env_delay = self._timecents_to_seconds(
                self._get_generator_value(55, -12000)
            )
            self._pitch_env_attack = self._timecents_to_seconds(
                self._get_generator_value(56, -12000)
            )
            self._pitch_env_decay = self._timecents_to_seconds(
                self._get_generator_value(57, -12000)
            )
            self._pitch_env_sustain = self._get_generator_value(59, 0) / 100.0
            self._pitch_env_release = self._timecents_to_seconds(
                self._get_generator_value(60, -12000)
            )
            self._pitch_env_depth = self._get_generator_value(61, 0) / 100.0

    def _init_envelopes(self) -> None:
        """Initialize envelopes from SF2 generator parameters."""
        from ...primitives.envelope import UltraFastADSREnvelope

        # Get key-scaled parameters
        note = self.current_note
        key_offset = (note - 60) / 60.0 if note > 0 else 0.0

        # Amplitude envelope with key scaling (SF2 gen 39-40)
        self._keynum_to_vol_env_hold = self._get_generator_value(39, 0) / 100.0
        self._keynum_to_vol_env_decay = self._get_generator_value(40, 0) / 100.0

        _key_scaled_hold = 1.0 + self._keynum_to_vol_env_hold * key_offset
        key_scaled_decay = 1.0 + self._keynum_to_vol_env_decay * key_offset

        # Get timecents values from SF2 volume envelope generators (33-38)
        gen33_val = self._get_generator_value(33, -12000)  # delayVolEnv
        gen34_val = self._get_generator_value(34, -12000)  # attackVolEnv
        gen35_val = self._get_generator_value(35, -12000)  # holdVolEnv
        gen36_val = self._get_generator_value(36, -12000)  # decayVolEnv
        gen37_val = self._get_generator_value(37, 1000)    # sustainVolEnv (0-1000)
        gen38_val = self._get_generator_value(38, -12000)  # releaseVolEnv

        delay = self._timecents_to_seconds(gen33_val)
        attack = self._timecents_to_seconds(gen34_val)
        hold = self._timecents_to_seconds(gen35_val)
        if _key_scaled_hold != 1.0:
            hold *= _key_scaled_hold
        decay = self._timecents_to_seconds(gen36_val) * key_scaled_decay
        sustain = gen37_val / 1000.0
        release = self._timecents_to_seconds(gen38_val)

        amp_env = UltraFastADSREnvelope(
            delay=delay,
            attack=attack,
            hold=hold,
            decay=decay,
            sustain=sustain,
            release=release,
            sample_rate=self.sample_rate,
        )
        self._envelopes["amp_env"] = amp_env

        # Initialize modulation envelope
        self._init_modulation_envelope()

        # Initialize pitch envelope
        self._init_pitch_envelope()

    def _init_filters(self) -> None:
        """Initialize filters from SF2 generator parameters."""
        from ...primitives.filter import UltraFastResonantFilter

        cutoff = self._cents_to_frequency(self._get_filter_cutoff_cents())  # initialFilterFc
        # SF2 initialFilterQ is in centibels (0.1 dB increments). Convert to Q factor.
        # 0 centibels = 0 dB boost = Butterworth Q ≈ 0.707
        # Formula: Q_factor = 0.707 * 10^(ceB / 200)
        sf2_q_centibels = self._get_generator_value(9, 0)  # initialFilterQ
        resonance = 0.707 * (10.0 ** (sf2_q_centibels / 200.0))

        # Filter type: gen 36 is decayVolEnv (standard SF2), not filter_type.
        # Default to lowpass. Custom filter type belongs in XG modulation matrix.
        self._filter_type = 0
        filter_type_str = "lowpass"

        filter_obj = UltraFastResonantFilter(
            cutoff=cutoff,
            resonance=resonance,
            filter_type=filter_type_str,
            sample_rate=self.sample_rate,
        )
        self._filters["filter"] = filter_obj

    def _allocate_buffers_for_block(self, block_size: int) -> None:
        """Allocate buffers for specific block size (zero-allocation)."""
        # Init-time buffer sizing (one-time allocation per block size change)
        if self._mod_lfo_buffer is None or len(self._mod_lfo_buffer) < block_size:
            self._mod_lfo_buffer = np.zeros(block_size, dtype=np.float32)
        if self._vib_lfo_buffer is None or len(self._vib_lfo_buffer) < block_size:
            self._vib_lfo_buffer = np.zeros(block_size, dtype=np.float32)
        if self._mod_env_buffer is None or len(self._mod_env_buffer) < block_size:
            self._mod_env_buffer = np.zeros(block_size, dtype=np.float32)
        if self._pitch_env_buffer is None or len(self._pitch_env_buffer) < block_size:
            self._pitch_env_buffer = np.zeros(block_size, dtype=np.float32)

    def _allocate_buffers(self) -> None:
        """Allocate processing buffers (zero-allocation)."""
        super()._allocate_buffers()

        # Reset playback state
        self._sample_position = 0.0
        self._calculate_phase_step()

        # Allocate LFO buffers if needed (zero-allocation: reuse)
        if self._mod_lfo_buffer is None or len(self._mod_lfo_buffer) < self._current_block_size:
            self._mod_lfo_buffer = np.zeros(self._current_block_size, dtype=np.float32)
        if self._vib_lfo_buffer is None or len(self._vib_lfo_buffer) < self._current_block_size:
            self._vib_lfo_buffer = np.zeros(self._current_block_size, dtype=np.float32)
        if self._mod_env_buffer is None or len(self._mod_env_buffer) < self._current_block_size:
            self._mod_env_buffer = np.zeros(self._current_block_size, dtype=np.float32)
        if self._pitch_env_buffer is None or len(self._pitch_env_buffer) < self._current_block_size:
            self._pitch_env_buffer = np.zeros(self._current_block_size, dtype=np.float32)

    def _calculate_phase_step(self) -> None:
        """Calculate phase step for sample playback."""
        if self._sample_data is None:
            self._phase_step = 1.0
            self._base_phase_step = 1.0
            return

        # Calculate pitch ratio based on note and SF2 tuning (gen 51-52, 56)
        note_diff = self.current_note - self._root_key
        coarse_tune = self._get_generator_value(51, 0)  # coarseTune
        fine_tune = self._get_generator_value(52, 0) / 100.0  # fineTune
        scale_tuning = self._get_generator_value(56, 100) / 100.0  # scaleTuning

        # Apply scale tuning
        total_semitones = (note_diff + coarse_tune + fine_tune) * scale_tuning
        self._base_phase_step = 2.0 ** (total_semitones / 12.0)
        self._phase_step = self._base_phase_step

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this SF2 region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        # Check SF2 zone ranges
        if not self._matches_note_velocity(note, velocity):
            return False

        if not super().note_on(velocity, note):
            return False

        # Reset playback position
        self._sample_position = 0.0
        self._effective_end = 0
        self._active = True
        self._note_start_time = time.time()
        self._calculate_phase_step()

        # Handle portamento (CC5, CC65)
        if self._portamento_active and self._last_note is not None:
            self._portamento_note = self._last_note
            self._portamento_target = note
            self._portamento_glide_phase = 0.0

        self._last_note = note

        # NOTE: gen 41 is the instrument index in standard SF2 (SF2.01 §8.1.3).
        # The _generator_params dict already has the instrument index from the
        # zone linking step.  Reading it here as "velocity_curve" is a non-
        # standard repurposing that yields the instrument index, not a correct
        # velocity response curve.  This field is not currently used in audio
        # processing; it is captured for future velocity-sensitive mapping.
        self._velocity_curve = self._get_generator_value(41, 0)

        # Check for drum mode / one-shot (gen 54 sampleModes)
        sample_mode = self._get_generator_value(54, 0)  # sampleModes
        self._is_drum_mode = bool(sample_mode & 4)

        # Reverse playback: gen 57 is exclusiveClass (standard SF2). Disabled.

        # Loop crossfade: gen 45 is startloopAddrsCoarseOffset (standard SF2). Disabled.
        self._loop_crossfade_samples = 0

        # Load effects sends (SF2 gen 15-17)
        self._reverb_send = self._get_generator_value(16, 0) / 1000.0  # reverbEffectsSend
        self._chorus_send = self._get_generator_value(15, 0) / 1000.0  # chorusEffectsSend

        # Load panning (gen 17)
        self._pan_position = self._get_generator_value(17, 0) / 500.0  # pan

        # Load initial attenuation (gen 48) — centibels, valid SF2 range 0-1000
        # (attenuation is always >= 0; negative values are invalid and clamped
        # to 0 so a corrupt generator cannot become a gain boost).
        _att_cB = max(0, min(1000, self._get_generator_value(48, 0)))
        self._initial_attenuation_db = _att_cB / 10.0

        # Load stereo width (default 1.0 = normal)
        self._stereo_width = 1.0

        # Trigger amplitude envelope
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "note_on"):
                env.note_on(velocity, note)

        # Trigger modulation envelope
        self._trigger_modulation_envelope()

        # Calculate voice stealing priority
        self._calculate_voice_priority()

        # Trigger pitch envelope if active
        if self._pitch_env_active:
            self._pitch_env_stage = 1  # delay
            self._pitch_env_level = 0.0
            self._pitch_env_time_in_stage = 0.0

        # Reset LFO phases
        if self._mod_lfo:
            self._mod_lfo.reset()
        if self._vib_lfo:
            self._vib_lfo.reset()

        # Initialize SF2 modulator evaluator for this note
        # Merges default modulators (SF2 §8.4.11) with zone-specific modulators
        self._mod_evaluator = SF2ModulatorEvaluator(self._modulators)
        self._modulators_warned = True  # suppress historic BUG-4 warning

        # Reset modulation values
        self._pitch_mod = 0.0
        self._filter_mod = 0.0
        self._volume_mod = 1.0

        # Reset GS parameter state (-1 = unset/use default)
        self._gs_filter_cutoff = -1.0
        self._gs_filter_resonance = -1.0
        self._gs_amp_attack = -1.0
        self._gs_amp_decay = -1.0
        self._gs_amp_release = -1.0
        self._gs_vibrato_rate = -1.0
        self._gs_vibrato_depth = -1.0
        self._gs_vibrato_delay = -1.0
        self._gs_volume = -1.0
        self._gs_pan = -2.0
        self._gs_reverb_send = -1.0
        self._gs_chorus_send = -1.0

        return True

    def _calculate_voice_priority(self) -> float:
        """Calculate voice priority for stealing decisions.

        Lower priority = stolen first. Combines:
        - Velocity factor (quieter = lower priority)
        - Age factor (older = lower priority)
        - Note factor (extreme notes = lower priority)

        Returns:
            Priority score (0.0 = steal first, 1.0 = keep last)
        """
        # Velocity: 0.0-0.3 range (quieter = stolen first)
        velocity_factor = (127 - self.current_velocity) / 127.0 * 0.3

        # Age: 0.0-0.3 range (older = stolen first, capped at 30s)
        if self._note_start_time > 0:
            age = time.time() - self._note_start_time
            age_factor = min(age / 30.0, 1.0) * 0.3
        else:
            age_factor = 0.0

        # Note: 0.0-0.2 range (extreme notes = stolen first)
        note_factor = abs(self.current_note - 60) / 60.0 * 0.2

        # GS drum channels get slightly higher priority
        drum_bonus = 0.1 if self._is_drum_mode else 0.0

        self._voice_priority = velocity_factor + age_factor + note_factor + drum_bonus
        return self._voice_priority

    def note_off(self) -> bool:
        """Trigger note-off with envelope release."""
        # Trigger amplitude envelope release
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "note_off"):
                env.note_off()

        # Trigger modulation envelope release
        self._release_modulation_envelope()

        # Trigger pitch envelope release
        if self._pitch_env_active:
            self._pitch_env_stage = 6  # release

        self.state = RegionState.RELEASING
        return True

    def control_change(self, controller: int, value: int) -> None:
        """
        Handle MIDI control change message.

        NOTE: This runs on the MIDI thread. The audio thread reads these fields.
        All field writes are atomic on x86-64 (aligned <= 64-bit). Compound
        assignments (*=, +=) are NOT atomic but the race window is small.
        A proper fix would use atomic operations or a spinlock.

        Args:
            controller: CC number (0-127)
            value: CC value (0-127)
        """
        normalized = value / 127.0

        if controller == 1:  # Modulation Wheel
            self._modwheel_mod = normalized
            # Modulation applied per-block in _apply_global_modulation

        elif controller == 2:  # Breath Controller
            self._breath_mod = normalized
            self._filter_mod = normalized * 1.0

        elif controller == 4:  # Foot Controller
            self._foot_mod = normalized
            self._vib_lfo_to_pitch = normalized * 0.5
            self._vib_lfo_to_pitch_base = self._vib_lfo_to_pitch

        elif controller == 5:  # Portamento Time
            self._portamento_time = self._calculate_portamento_time(value)

        elif controller == 7:  # Volume (handled by channel pre-gain)
            pass

        elif controller == 8:  # Balance
            self._balance = (value - 64) / 64.0

        elif controller == 10:  # Pan
            self._pan_position = (value - 64) / 64.0

        elif controller == 11:  # Expression
            self._expression_mod = normalized

        elif controller == 64:  # Sustain
            self._sustain_pedal = value >= 64
            if not self._sustain_pedal:
                self._handle_sustain_release()

        elif controller == 65:  # Portamento On/Off
            self._portamento_active = value >= 64

        elif controller == 66:  # Sostenuto
            if value >= 64 and not self._sostenuto_pedal:
                self._sostenuto_pedal = True
                self._held_by_sostenuto = True
            elif value < 64:
                self._sostenuto_pedal = False
                self._handle_sostenuto_release()

        elif controller == 67:  # Soft Pedal
            self._soft_pedal = value >= 64

        elif controller == 68:  # Legato
            self._legato_active = value >= 64

        elif controller == 69:  # Hold 2
            if value >= 64 and not self._hold2_pedal:
                self._hold2_pedal = True
                self._held_by_hold2 = True
            elif value < 64:
                self._hold2_pedal = False
                self._handle_hold2_release()

        elif controller == 70:  # Sound Controller 1 (Variation)
            self._sound_controller_1 = normalized
            self._filter_mod = (normalized - 0.5) * 1.0

        elif controller == 71:  # Harmonic Content (FIX - was swapped)
            self._apply_harmonic_content(normalized)

        elif controller == 72:  # Brightness (FIX - was swapped)
            self._apply_brightness(normalized)

        elif controller == 73:  # Release Time
            self._xg_release_time = normalized
            self._apply_xg_release_time(normalized)

        elif controller == 74:  # Attack Time
            self._xg_attack_time = normalized
            self._apply_xg_attack_time(normalized)

        elif controller == 75:  # Filter Cutoff
            self._xg_filter_cutoff = normalized
            self._apply_xg_filter_cutoff(normalized)

        elif controller == 76:  # Decay Time
            self._xg_decay_time = normalized
            self._apply_xg_decay_time(normalized)

        elif controller == 77:  # Vibrato Rate
            self._xg_vibrato_rate = normalized
            self._apply_xg_vibrato_rate(normalized)

        elif controller == 78:  # Vibrato Depth
            self._xg_vibrato_depth = normalized
            self._apply_xg_vibrato_depth(normalized)

        elif controller == 79:  # Vibrato Delay
            self._xg_vibrato_delay = normalized
            self._delay_vib_lfo = normalized * 2.0
            # Update LFO delay without resetting phase
            if self._vib_lfo:
                self._vib_lfo.delay = self._delay_vib_lfo
                self._vib_lfo.delay_samples = int(self._delay_vib_lfo * self.sample_rate)

        elif controller == 80:  # GP Button 1
            self._gp_button_1 = normalized

        elif controller == 81:  # GP Button 2
            self._gp_button_2 = normalized

        elif controller == 82:  # GP Button 3
            self._gp_button_3 = normalized

        elif controller == 83:  # GP Button 4
            self._gp_button_4 = normalized

        elif controller == 91:  # Reverb Send
            self._reverb_send = normalized

        elif controller == 92:  # Tremolo Depth
            self._tremolo_depth = normalized
            self._mod_lfo_to_volume = normalized

        elif controller == 93:  # Chorus Send
            self._chorus_send = normalized

    def _calculate_portamento_time(self, value: int) -> float:
        """Calculate portamento time from CC value."""
        if value < 64:
            return value / 64.0
        else:
            return 1.0 + (value - 64) / 63.0 * 7.0

    def _handle_sustain_release(self) -> None:
        """Handle sustain pedal release."""
        if self.state == RegionState.RELEASING:
            pass

    def _handle_sostenuto_release(self) -> None:
        """Handle sostenuto pedal release."""
        if self._held_by_sostenuto:
            self._held_by_sostenuto = False
            if self.state == RegionState.RELEASING:
                pass

    def _handle_hold2_release(self) -> None:
        """Handle hold2 pedal release."""
        if self._held_by_hold2:
            self._held_by_hold2 = False

    def _apply_harmonic_content(self, normalized: float) -> None:
        """CC71: XG Harmonic Content - modify filter resonance."""
        if hasattr(self, "_filter_resonance"):
            self._filter_resonance = 0.5 + normalized * 1.5
        self._mod_env_to_filter = normalized * 0.5

    def _apply_brightness(self, normalized: float) -> None:
        """CC72: XG Brightness - modify filter cutoff."""
        self._filter_mod = normalized * 1.5

    def _apply_xg_release_time(self, normalized: float) -> None:
        """Apply XG release time (CC73).

        Per XG spec: logarithmic mapping 0-127 to ~0.001-40.96 seconds.
        """
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            # Exponential curve: 0.001 * 2^(normalized * 15.3) ≈ 0.001-41s
            release_time = 0.001 * (2.0 ** (normalized * 15.3))
            if hasattr(env, "release"):
                env.release = release_time
            # Recalculate increments for the Numba JIT path
            if hasattr(env, "_recalculate_increments"):
                env._recalculate_increments()

    def _apply_xg_attack_time(self, normalized: float) -> None:
        """Apply XG attack time (CC74).

        Per XG spec: logarithmic mapping 0-127 to ~0.001-40.96 seconds.
        """
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            # Exponential curve: 0.001 * 2^(normalized * 15.3) ≈ 0.001-41s
            attack_time = 0.001 * (2.0 ** (normalized * 15.3))
            if hasattr(env, "attack"):
                env.attack = attack_time
            # Recalculate increments for the Numba JIT path
            if hasattr(env, "_recalculate_increments"):
                env._recalculate_increments()

    def _apply_xg_filter_cutoff(self, normalized: float) -> None:
        """CC75: XG Filter Cutoff - modify filter cutoff."""
        cutoff_mod = (normalized - 0.5) * 2.0
        self._filter_mod = cutoff_mod * 2.0

    def _apply_xg_decay_time(self, normalized: float) -> None:
        """Apply XG decay time (CC76).

        Per XG spec: logarithmic mapping 0-127 to ~0.001-40.96 seconds.
        """
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            # Exponential curve: 0.001 * 2^(normalized * 15.3) ≈ 0.001-41s
            decay_time = 0.001 * (2.0 ** (normalized * 15.3))
            if hasattr(env, "decay"):
                env.decay = decay_time
            # Recalculate increments for the Numba JIT path
            if hasattr(env, "_recalculate_increments"):
                env._recalculate_increments()

    def _apply_xg_vibrato_rate(self, normalized: float) -> None:
        """Apply XG vibrato rate (CC77).

        Per XG spec: maps 0-127 to ~0.05-20.0 Hz using exponential curve.
        """
        if self._vib_lfo:
            # Exponential mapping: 0.05 * 2^(normalized * 8.6) ≈ 0.05-20 Hz
            rate = 0.05 * (2.0 ** (normalized * 8.6))
            self._freq_vib_lfo = rate
            self._vib_lfo.set_frequency(rate)

    def _apply_xg_vibrato_depth(self, normalized: float) -> None:
        """Apply XG vibrato depth (CC78).

        Per XG spec: ~0-5 semitones via exponential curve.
        """
        # XG vibrato depth: ~0-5 semitones via exponential curve
        self._vib_lfo_to_pitch = 0.01 * (2.0 ** (normalized * 9.0)) - 0.01
        self._vib_lfo_to_pitch_base = self._vib_lfo_to_pitch

    def _trigger_modulation_envelope(self) -> None:
        """Trigger modulation envelope attack."""
        self._mod_env_stage = 1  # delay
        self._mod_env_level = 0.0
        self._mod_env_time_in_stage = 0.0

    def _release_modulation_envelope(self) -> None:
        """Trigger modulation envelope release phase."""
        self._mod_env_stage = 6  # release
        self._mod_env_time_in_stage = 0.0  # Reset stage time for proper release duration

    def _apply_global_modulation(self, modulation: dict[str, float]) -> None:
        """Apply modulation from modulation matrix (zero-allocation)."""
        # Pitch modulation
        self._pitch_mod = modulation.get("pitch", 0.0)

        # Filter modulation (in octaves)
        self._filter_mod = modulation.get("filter_cutoff", 0.0)

        # Volume modulation
        self._volume_mod = modulation.get("volume", 1.0)

        # Controller sources
        self._aftertouch_mod = modulation.get(
            "channel_aftertouch", modulation.get("aftertouch", 0.0)
        )
        self._breath_mod = modulation.get("breath_controller", modulation.get("breath", 0.0))
        self._modwheel_mod = modulation.get("mod_wheel", modulation.get("modwheel", 0.0))
        self._foot_mod = modulation.get("foot_controller", modulation.get("foot", 0.0))
        self._expression_mod = modulation.get("expression", 1.0)

        # Effect sends from modulation dict
        reverb_send = modulation.get("reverb_send")
        if reverb_send is not None:
            self._reverb_send = max(0.0, min(1.0, float(reverb_send)))
        chorus_send = modulation.get("chorus_send")
        if chorus_send is not None:
            self._chorus_send = max(0.0, min(1.0, float(chorus_send)))

        # XG harmonic content (CC71): modify filter resonance
        harmon_content = modulation.get("harmon_content")
        if harmon_content is not None:
            normalized = float(harmon_content)
            if hasattr(self, "_filter_resonance"):
                self._filter_resonance = 0.5 + normalized * 1.5
            self._mod_env_to_filter = normalized * 0.5

        # XG brightness (CC72): modify filter cutoff
        brightness = modulation.get("brightness")
        if brightness is not None:
            self._filter_mod = float(brightness) * 1.5

        # XG NRPN filter parameters — apply to filter similarly to GS filter path
        xg_cutoff = modulation.get("xg_filter_cutoff")
        if xg_cutoff is not None:
            v = float(xg_cutoff)
            self._xg_filter_cutoff = v
            self._filter_mod = (v - 0.5) * 4.0

        xg_resonance = modulation.get("xg_filter_resonance")
        if xg_resonance is not None:
            # Apply XG filter resonance via GS path (same rendering code)
            self._gs_filter_resonance = float(xg_resonance)

        # Apply controller effects to modulation depths
        if self._modwheel_mod != 0.0:
            # Compute from base to avoid compounding across blocks
            self._vib_lfo_to_pitch = self._vib_lfo_to_pitch_base * (1.0 + self._modwheel_mod)
            self._filter_mod += self._modwheel_mod * 1.5
        else:
            # Reset to base when modwheel is zero (no compounding carry-over)
            self._vib_lfo_to_pitch = self._vib_lfo_to_pitch_base

        if self._aftertouch_mod != 0.0:
            self._volume_mod *= 1.0 + self._aftertouch_mod * 0.5
            self._filter_mod += self._aftertouch_mod * 2.0

        # GS part parameters (from GS sysex bridge)
        self._gs_filter_cutoff = modulation.get("gs_filter_cutoff", -1.0)  # -1 = unset
        self._gs_filter_resonance = modulation.get("gs_filter_resonance", -1.0)
        self._gs_amp_attack = modulation.get("gs_amp_attack", -1.0)
        self._gs_amp_decay = modulation.get("gs_amp_decay", -1.0)
        self._gs_amp_release = modulation.get("gs_amp_release", -1.0)
        self._gs_vibrato_rate = modulation.get("gs_vibrato_rate", -1.0)
        self._gs_vibrato_depth = modulation.get("gs_vibrato_depth", -1.0)
        self._gs_vibrato_delay = modulation.get("gs_vibrato_delay", -1.0)
        self._gs_volume = modulation.get("gs_volume", -1.0)
        raw_pan = modulation.get("gs_pan", -2.0)
        self._gs_pan = max(-1.0, min(1.0, raw_pan)) if raw_pan >= -1.5 else -2.0
        self._gs_reverb_send = modulation.get("gs_reverb_send", -1.0)
        self._gs_chorus_send = modulation.get("gs_chorus_send", -1.0)

        # Stereo width (from XG parameter / S.Art2 articulation routing)
        sw = modulation.get("stereo_width")
        if sw is not None:
            self._stereo_width = float(sw)

    def _generate_lfo_signals(self, block_size: int) -> None:
        """Generate LFO modulation signals (zero-allocation)."""
        # Ensure buffers are allocated
        self._allocate_buffers_for_block(block_size)

        if self._mod_lfo:
            result = self._mod_lfo.generate_block(block_size)
            if isinstance(result, np.ndarray):
                self._mod_lfo_buffer[:block_size] = result[:block_size]

        if self._vib_lfo:
            result = self._vib_lfo.generate_block(block_size)
            if isinstance(result, np.ndarray):
                self._vib_lfo_buffer[:block_size] = result[:block_size]

    def _generate_modulation_envelope_block(self, block_size: int) -> np.ndarray:
        """Generate modulation envelope block sample-by-sample (zero-allocation)."""
        if self._mod_env_buffer is None or len(self._mod_env_buffer) < block_size:
            self._mod_env_buffer = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            self._mod_env_buffer[i] = self._mod_env_level
            self._update_modulation_envelope_state(1.0 / self.sample_rate)

        return self._mod_env_buffer[:block_size]

    def _update_modulation_envelope_state(self, delta_time: float) -> None:
        """Update modulation envelope state (sample-accurate)."""
        self._mod_env_time_in_stage += delta_time
        stage_time = self._mod_env_time_in_stage

        if self._mod_env_stage == 0:  # idle
            pass
        elif self._mod_env_stage == 1:  # delay
            if stage_time >= self._delay_mod_env:
                self._mod_env_stage = 2  # attack
                self._mod_env_time_in_stage = 0.0
        elif self._mod_env_stage == 2:  # attack
            if stage_time >= self._attack_mod_env:
                self._mod_env_stage = 3  # hold
                self._mod_env_time_in_stage = 0.0
            else:
                self._mod_env_level = (
                    stage_time / self._attack_mod_env if self._attack_mod_env > 0 else 1.0
                )
        elif self._mod_env_stage == 3:  # hold
            # Apply key tracking to mod envelope hold (generator 31)
            if self._keynum_to_mod_env_hold != 0 and self.current_note > 0:
                key_offset = (self.current_note - 60) / 60.0
                adjusted_hold_tc = max(
                    -12000,
                    self._hold_mod_env_tc + self._keynum_to_mod_env_hold * key_offset * 100.0,
                )
                hold_time = self._timecents_to_seconds(adjusted_hold_tc)
            else:
                hold_time = self._hold_mod_env
            if stage_time >= hold_time:
                self._mod_env_stage = 4  # decay
                self._mod_env_time_in_stage = 0.0
        elif self._mod_env_stage == 4:  # decay
            # Apply key tracking to mod envelope decay (generator 32)
            if self._keynum_to_mod_env_decay != 0 and self.current_note > 0:
                key_offset = (self.current_note - 60) / 60.0
                adjusted_decay_tc = max(
                    -12000,
                    self._decay_mod_env_tc + self._keynum_to_mod_env_decay * key_offset * 100.0,
                )
                decay_time = self._timecents_to_seconds(adjusted_decay_tc)
            else:
                decay_time = self._decay_mod_env
            if stage_time >= decay_time:
                self._mod_env_stage = 5  # sustain
                self._mod_env_level = self._sustain_mod_env
            else:
                decay_progress = stage_time / decay_time if decay_time > 0 else 1.0
                self._mod_env_level = 1.0 - decay_progress * (1.0 - self._sustain_mod_env)
        elif self._mod_env_stage == 5:  # sustain
            self._mod_env_level = self._sustain_mod_env
        elif self._mod_env_stage == 6:  # release
            if stage_time >= self._release_mod_env:
                self._mod_env_level = 0.0
                self._mod_env_stage = 0  # idle
            else:
                # Exponential decay: level *= exp(-dt / tau)
                tau = self._release_mod_env if self._release_mod_env > 0.001 else 0.001
                decay_factor = np.exp(-delta_time / tau)
                self._mod_env_level *= decay_factor

    def _generate_pitch_envelope(self, block_size: int) -> None:
        """Generate pitch envelope buffer for this block.

        Processes the pitch envelope state machine per-sample,
        contributing to pitch modulation via _pitch_env_buffer.
        The stored stage times are already in seconds from _init_pitch_envelope().
        """
        if self._pitch_env_stage == 0:  # Idle
            self._pitch_env_buffer[:block_size] = 0.0
            return

        # Times are already in seconds from _init_pitch_envelope()
        delay_time = self._pitch_env_delay
        attack_time = self._pitch_env_attack if self._pitch_env_attack > 0 else 0.001
        decay_time = self._pitch_env_decay if self._pitch_env_decay > 0 else 0.001
        sustain_level = max(0.0, min(1.0, self._pitch_env_sustain))
        release_time = self._pitch_env_release if self._pitch_env_release > 0 else 0.001

        depth = self._pitch_env_depth  # Already in semitones (gen_value / 100)

        delay_samples = int(delay_time * self.sample_rate)
        attack_samples = int(attack_time * self.sample_rate) if attack_time > 0 else 1
        decay_samples = int(decay_time * self.sample_rate) if decay_time > 0 else 1
        release_samples = int(release_time * self.sample_rate) if release_time > 0 else 1

        for i in range(block_size):
            if self._pitch_env_stage == 1:  # Delay
                self._pitch_env_time_in_stage += 1
                self._pitch_env_level = 0.0
                if self._pitch_env_time_in_stage >= delay_samples:
                    self._pitch_env_stage = 2
                    self._pitch_env_time_in_stage = 0

            elif self._pitch_env_stage == 2:  # Attack (0→1)
                self._pitch_env_time_in_stage += 1
                progress = min(1.0, self._pitch_env_time_in_stage / attack_samples)
                self._pitch_env_level = progress
                if progress >= 1.0:
                    self._pitch_env_stage = 3  # Hold
                    self._pitch_env_time_in_stage = 0

            elif self._pitch_env_stage == 3:  # Hold (1.0)
                self._pitch_env_level = 1.0
                if decay_time <= 0:
                    self._pitch_env_stage = 5  # Sustain
                else:
                    self._pitch_env_time_in_stage += 1
                    if self._pitch_env_time_in_stage >= decay_samples:
                        self._pitch_env_stage = 4
                        self._pitch_env_time_in_stage = 0

            elif self._pitch_env_stage == 4:  # Decay (1→sustain)
                self._pitch_env_time_in_stage += 1
                progress = min(1.0, self._pitch_env_time_in_stage / decay_samples)
                self._pitch_env_level = 1.0 - progress * (1.0 - sustain_level)
                if progress >= 1.0:
                    self._pitch_env_stage = 5  # Sustain
                    self._pitch_env_time_in_stage = 0

            elif self._pitch_env_stage == 5:  # Sustain
                self._pitch_env_level = sustain_level

            elif self._pitch_env_stage == 6:  # Release (sustain→0)
                self._pitch_env_time_in_stage += 1
                progress = min(1.0, self._pitch_env_time_in_stage / release_samples)
                self._pitch_env_level = sustain_level * (1.0 - progress)
                if progress >= 1.0:
                    self._pitch_env_stage = 0  # Idle
                    self._pitch_env_level = 0.0

            self._pitch_env_buffer[i] = self._pitch_env_level * depth

    def _calculate_sample_pitch_modulation(self, sample_index: int) -> float:
        """Calculate total pitch modulation for a specific sample (zero-allocation)."""
        total = self._pitch_mod

        # Add portamento glide
        if (
            self._portamento_active
            and self._portamento_note is not None
            and self._portamento_target is not None
        ):
            glide_progress = min(1.0, self._portamento_glide_phase)
            portamento_mod = (self._portamento_target - self._portamento_note) * glide_progress
            total += portamento_mod

        # Add vibrato LFO modulation
        if self._vib_lfo_buffer is not None and sample_index < len(self._vib_lfo_buffer):
            total += self._vib_lfo_buffer[sample_index] * self._vib_lfo_to_pitch

        # Add modulation LFO modulation
        if self._mod_lfo_buffer is not None and sample_index < len(self._mod_lfo_buffer):
            total += self._mod_lfo_buffer[sample_index] * self._mod_lfo_to_pitch

        # Add modulation envelope modulation
        if self._mod_env_buffer is not None and sample_index < len(self._mod_env_buffer):
            total += self._mod_env_buffer[sample_index] * self._mod_env_to_pitch

        return total

    def _apply_filter_with_modulation(self, output: np.ndarray, block_size: int) -> None:
        """Apply filter with LFO and modulation envelope (zero-allocation)."""
        if "filter" not in self._filters:
            return

        filter_obj = self._filters["filter"]
        if not hasattr(filter_obj, "process_block"):
            return

        try:
            # Get base filter parameters
            base_cutoff = self._cents_to_frequency(self._get_filter_cutoff_cents())  # initialFilterFc
            # SF2 initialFilterQ is in centibels: convert to Q factor (Butterworth at 0 ceB)
            sf2_q_centibels = self._get_generator_value(9, 0)  # initialFilterQ
            base_resonance = 0.707 * (10.0 ** (sf2_q_centibels / 200.0))

            # Apply GS filter cutoff/resonance
            if self._gs_filter_cutoff >= 0.0:
                base_cutoff *= 0.2 + self._gs_filter_cutoff * 0.8
            if self._gs_filter_resonance >= 0.0:
                base_resonance = self._gs_filter_resonance * 10.0

            # Calculate non-LFO filter modulation (env + key track)
            filter_mod_total = self._filter_mod

            # Add mod envelope filter modulation (block-mean)
            if self._mod_env_buffer is not None and self._mod_env_to_filter != 0.0:
                mean_env = np.mean(self._mod_env_buffer[:block_size])
                filter_mod_total += mean_env * self._mod_env_to_filter * 12.0

            # Add VCF key tracking
            if self._filter_key_track != 0.0:
                filter_mod_total += self._filter_key_track

            if self._mod_lfo_buffer is not None and self._mod_lfo_to_filter != 0.0:
                # NOTE: Sub-block LFO→filter modulation provides a practical compromise between
                # block-constant modulation (stepping artifacts) and per-sample modulation
                # (which would require per-sample filter parameter updates, causing zipper noise).
                # 4 sub-blocks capture the LFO envelope shape with minimal overhead.
                sub_blocks = 4
                sub_size = block_size // sub_blocks
                for sb in range(sub_blocks):
                    start = sb * sub_size
                    end = start + sub_size if sb < sub_blocks - 1 else block_size

                    # Mean LFO value for this sub-block
                    mean_lfo = np.mean(self._mod_lfo_buffer[start:end])
                    sub_filter_mod = filter_mod_total + mean_lfo * self._mod_lfo_to_filter * 12.0

                    # Update filter cutoff for this sub-block
                    sub_cutoff = base_cutoff * (2.0**sub_filter_mod)
                    sub_cutoff = max(20.0, min(20000.0, sub_cutoff))
                    filter_obj.set_parameters(cutoff=sub_cutoff, resonance=base_resonance)

                    # Process this sub-block (2D interleaved format)
                    sub_len = end - start
                    if self._filter_work_left is None or len(self._filter_work_left) < sub_len:
                        self._filter_work_left = np.empty(sub_len, dtype=np.float32)
                        self._filter_work_right = np.empty(sub_len, dtype=np.float32)
                    left = self._filter_work_left[:sub_len]
                    right = self._filter_work_right[:sub_len]
                    np.copyto(left, output[start:end, 0])
                    np.copyto(right, output[start:end, 1])
                    filtered_left, filtered_right = filter_obj.process_block(left, right)
                    np.copyto(output[start:end, 0], filtered_left)
                    np.copyto(output[start:end, 1], filtered_right)
            else:
                # No LFO modulation, constant filter per block
                modulated_cutoff = base_cutoff * (2.0**filter_mod_total)
                modulated_cutoff = max(20.0, min(20000.0, modulated_cutoff))
                filter_obj.set_parameters(cutoff=modulated_cutoff, resonance=base_resonance)

                # Process (2D interleaved format)
                if self._filter_work_left is None or len(self._filter_work_left) < block_size:
                    self._filter_work_left = np.empty(block_size, dtype=np.float32)
                    self._filter_work_right = np.empty(block_size, dtype=np.float32)
                left = self._filter_work_left[:block_size]
                right = self._filter_work_right[:block_size]
                np.copyto(left, output[:, 0])
                np.copyto(right, output[:, 1])
                filtered_left, filtered_right = filter_obj.process_block(left, right)
                np.copyto(output[:, 0], filtered_left)
                np.copyto(output[:, 1], filtered_right)

        except Exception:
            pass  # Skip filter on error

    def _apply_tremolo_and_pan(self, output: np.ndarray, block_size: int) -> None:
        """Apply tremolo (LFO→volume), balance, and auto-pan (LFO→pan) (zero-allocation)."""
        # Apply tremolo (mod LFO → volume)
        if self._mod_lfo_to_volume != 0.0 and self._mod_lfo_buffer is not None:
            tremolo = 1.0 + self._mod_lfo_buffer[:block_size] * self._mod_lfo_to_volume * 0.5
            output[:, :] *= tremolo[:, np.newaxis]

        # Apply tremolo (vib LFO → volume, SF2 gen 14)
        if self._vib_lfo_to_volume != 0.0 and self._vib_lfo_buffer is not None:
            tremolo = 1.0 + self._vib_lfo_buffer[:block_size] * self._vib_lfo_to_volume * 0.5
            output[:, :] *= tremolo[:, np.newaxis]

        # Apply tremolo depth from CC92
        if self._tremolo_depth > 0.0 and self._mod_lfo_buffer is not None:
            tremolo = 1.0 - self._tremolo_depth * (1.0 - self._mod_lfo_buffer[:block_size])
            output[:, :] *= tremolo[:, np.newaxis]

        # Apply mod env to volume
        if self._mod_env_to_volume != 0.0 and self._mod_env_buffer is not None:
            env_mod = 1.0 + self._mod_env_buffer[:block_size] * self._mod_env_to_volume * 0.5
            output[:, :] *= env_mod[:, np.newaxis]

        # Apply balance (CC8)
        if self._balance != 0.0:
            balance = self._balance
            if balance < 0:
                left_gain = 1.0 + balance
                right_gain = 1.0
            else:
                left_gain = 1.0
                right_gain = 1.0 - balance
            output[:, 0] *= left_gain
            output[:, 1] *= right_gain

        # Per-sample LFO → pan modulation (replaces block-mean for waveform-accurate pan)
        pan_center = self._pan_position  # -1 to 1

        # Compute per-sample pan offset from LFO sources (zero-allocation)
        if self._buffer_pool is not None:
            lfo_pan_offset = self._buffer_pool.get_mono_buffer(block_size)
            lfo_pan_offset.fill(0.0)
        else:
            lfo_pan_offset = np.zeros(block_size, dtype=np.float32)
        if self._mod_lfo_to_pan != 0.0 and self._mod_lfo_buffer is not None:
            lfo_pan_offset += self._mod_lfo_buffer[:block_size] * self._mod_lfo_to_pan
        if self._vib_lfo_to_pan != 0.0 and self._vib_lfo_buffer is not None:
            lfo_pan_offset += self._vib_lfo_buffer[:block_size] * self._vib_lfo_to_pan

        if pan_center != 0.0 or np.any(lfo_pan_offset != 0.0):
            # Per-sample pan positions clamped to [-1, 1]
            pan_positions = np.clip(pan_center + lfo_pan_offset, -1.0, 1.0)
            # Constant-power pan law per sample
            left_gains = np.cos((pan_positions + 1.0) * np.pi / 4.0)
            right_gains = np.sin((pan_positions + 1.0) * np.pi / 4.0)
            output[:, 0] *= left_gains
            output[:, 1] *= right_gains

        # Apply stereo width (mid/side processing)
        if self._stereo_width != 1.0:
            # Extract mid (L+R) and side (L-R)
            mid = (output[:, 0] + output[:, 1]) * 0.5
            side = (output[:, 0] - output[:, 1]) * 0.5 * self._stereo_width
            output[:, 0] = mid + side
            output[:, 1] = mid - side

        # Return temp buffer to pool
        if self._buffer_pool is not None:
            self._buffer_pool.return_buffer(lfo_pan_offset)

    def get_modulation_outputs(self) -> dict[str, float]:
        """Provide SF2 modulation sources to global modulation matrix."""
        outputs = {}

        if self._vib_lfo_buffer is not None and len(self._vib_lfo_buffer) > 0:
            outputs["sf2_vibrato_lfo"] = float(self._vib_lfo_buffer[-1])

        if self._mod_lfo_buffer is not None and len(self._mod_lfo_buffer) > 0:
            outputs["sf2_modulation_lfo"] = float(self._mod_lfo_buffer[-1])

        if self._mod_env_buffer is not None and len(self._mod_env_buffer) > 0:
            outputs["sf2_modulation_env"] = float(self._mod_env_buffer[-1])

        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "get_current_level"):
                outputs["sf2_amplitude_env"] = float(env.get_current_level())

        return outputs

    def _matches_note_velocity(self, note: int, velocity: int) -> bool:
        """
        Check if note/velocity matches SF2 zone ranges.

        Args:
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            True if matches
        """
        # Use cached ranges from SF2 zone, or fallback to descriptor ranges
        key_range = self._key_range if self._key_range != (0, 127) else self.descriptor.key_range
        velocity_range = (
            self._velocity_range
            if self._velocity_range != (0, 127)
            else self.descriptor.velocity_range
        )

        return (
            key_range[0] <= note <= key_range[1]
            and velocity_range[0] <= velocity <= velocity_range[1]
        )

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from SF2 region with full SF2 modulation processing.

        Implements:
        - Sample-accurate envelope processing
        - Per-sample LFO modulation
        - Modulation envelope modulation
        - Filter modulation
        - Tremolo and auto-pan

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values from modulation matrix

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Lazily allocate silent buffer for early return paths (one-time per block size change)
        if self._silence_buffer is None or self._silence_buffer.shape[0] < block_size:
            if self._buffer_pool is not None:
                self._silence_buffer = self._buffer_pool.get_stereo_buffer(block_size)
            else:
                self._silence_buffer = np.zeros((block_size, 2), dtype=np.float32)

        # Handle inactive state
        if not self._active:
            return self._silence_buffer[:block_size]

        # Initialize if needed
        if self._sample_data is None:
            loaded_data = self._load_sample_data()
            if loaded_data is not None:
                self._sample_data = loaded_data
            else:
                self._active = False
                return self._silence_buffer[:block_size]

        if not self._initialized:
            if not self.initialize():
                self._active = False
                return self._silence_buffer[:block_size]

        # Update block size if changed
        if block_size != self._current_block_size:
            self._current_block_size = block_size
            # Resize LFO buffers
            if self._mod_lfo:
                self._mod_lfo.set_block_size(block_size)
            if self._vib_lfo:
                self._vib_lfo.set_block_size(block_size)

        # Allocate output buffer (2D interleaved) — one-time per block size change
        if self._output_buffer is None or self._output_buffer.shape[0] != block_size:
            if self._buffer_pool is not None:
                self._output_buffer = self._buffer_pool.get_stereo_buffer(block_size)
            else:
                self._output_buffer = np.zeros((block_size, 2), dtype=np.float32)
        if self._work_buffer is None or self._work_buffer.shape[0] != block_size:
            if self._buffer_pool is not None:
                self._work_buffer = self._buffer_pool.get_mono_buffer(block_size)
            else:
                self._work_buffer = np.zeros(block_size, dtype=np.float32)
        output = self._output_buffer

        # 1. Apply global modulation from modulation matrix
        self._apply_global_modulation(modulation)

        # 1a. Apply GS vibrato parameters to vibrato LFO
        if self._gs_vibrato_rate >= 0.0 and self._vib_lfo:
            self._freq_vib_lfo = self._gs_vibrato_rate
            self._vib_lfo.set_frequency(self._gs_vibrato_rate)
        if self._gs_vibrato_depth >= 0.0:
            self._vib_lfo_to_pitch = self._gs_vibrato_depth
            self._vib_lfo_to_pitch_base = self._vib_lfo_to_pitch
        if self._gs_vibrato_delay >= 0.0 and self._vib_lfo:
            self._delay_vib_lfo = self._gs_vibrato_delay
            self._vib_lfo.delay = self._gs_vibrato_delay
            self._vib_lfo.delay_samples = int(self._gs_vibrato_delay * self.sample_rate)

        # 1b. Apply GS reverb/chorus send
        if self._gs_reverb_send >= 0.0:
            self._reverb_send = self._gs_reverb_send
        if self._gs_chorus_send >= 0.0:
            self._chorus_send = self._gs_chorus_send

        # 1c. Evaluate SF2 modulators against current controller state
        if self._mod_evaluator is not None:
            # Build controller state dict from the region's modulation inputs
            cc_state: dict[int, float] = {}
            if modulation:
                # Map known modulation keys to CC numbers
                for key, cc_num in {
                    "mod_wheel": 1,
                    "breath_controller": 2,
                    "foot_controller": 4,
                    "expression": 11,
                    "volume": 7,
                    "pan": 10,
                }.items():
                    val = modulation.get(key)
                    if val is not None:
                        cc_state[cc_num] = float(val)
                # Channel aftertouch (special index — not a CC number)
                at_val = modulation.get(
                    "channel_aftertouch", modulation.get("aftertouch", 0.0)
                )
                if at_val:
                    cc_state["channel_aftertouch"] = float(at_val)
                # Include raw CC values from modulation dict
                for key, val in modulation.items():
                    if key.startswith("cc_") and isinstance(val, (int, float)):
                        try:
                            cc_state[int(key.split("_")[1])] = float(val)
                        except (ValueError, IndexError):
                            pass
                # Pitch bend
                if "pitch" in modulation:
                    cc_state["pitch"] = float(modulation["pitch"])

            # Evaluate modulators
            mod_values = self._mod_evaluator.evaluate(
                cc_state, self.current_velocity, self.current_note
            )
            if mod_values:
                # Convert integer-gen → string-keyed params for apply_modulation_to_params
                gen_to_name = {
                    8: "initial_filter_fc",
                    9: "initial_filter_q",
                    48: "initial_attenuation",
                    51: "coarse_tune",
                    52: "fine_tune",
                    17: "pan",
                    16: "reverb_send",
                    15: "chorus_send",
                    6: "vib_lfo_to_pitch",
                    5: "mod_lfo_to_pitch",
                    13: "mod_lfo_to_volume",
                    11: "mod_lfo_to_filter_fc",
                    38: "release_vol_env",
                    22: "freq_mod_lfo",
                    24: "freq_vib_lfo",
                    34: "attack_vol_env",
                    35: "hold_vol_env",
                    36: "decay_vol_env",
                    37: "sustain_vol_env",
                    33: "delay_vol_env",
                }
                string_params = {
                    gen_to_name[k]: v
                    for k, v in self._generator_params.items()
                    if k in gen_to_name
                }
                apply_modulation_to_params(string_params, mod_values, self.current_note)

                # Recalculate pitch if coarse/fine tune modified
                if 51 in mod_values or 52 in mod_values:
                    if 51 in mod_values:
                        self._generator_params[51] = int(string_params.get("coarse_tune", 0))
                    if 52 in mod_values:
                        self._generator_params[52] = int(string_params.get("fine_tune", 0))
                    self._calculate_phase_step()

                # Update attenuation for volume stage — don't re-init envelopes
                # every block; let the gain stage (step 9) pick up _initial_attenuation_db
                if 48 in mod_values:
                    att_cb = max(0, int(string_params.get("initial_attenuation", 0)))
                    self._initial_attenuation_db = att_cb / 10.0  # centibels → dB

        # 2. Generate LFO signals (zero-allocation)
        self._generate_lfo_signals(block_size)

        # 2a. Generate pitch envelope
        self._generate_pitch_envelope(block_size)

        # 3. Generate modulation envelope
        self._generate_modulation_envelope_block(block_size)

        # 4. Calculate pitch modulation for each sample
        sample_delta_time = 1.0 / self.sample_rate

        # 5. Generate wavetable samples with per-sample pitch modulation
        self._generate_samples_with_mipmap_and_modulation(output, block_size, sample_delta_time)

        # 5a. Apply GS amp envelope time multipliers
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if self._gs_amp_attack >= 0.0 and hasattr(env, "attack"):
                env.attack *= self._gs_amp_attack
            if self._gs_amp_decay >= 0.0 and hasattr(env, "decay"):
                env.decay *= self._gs_amp_decay
            if self._gs_amp_release >= 0.0 and hasattr(env, "release"):
                env.release *= self._gs_amp_release
            # Recalculate increments if Numba JIT path
            if hasattr(env, "_recalculate_increments"):
                env._recalculate_increments()

        # 6. Apply amplitude envelope
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "generate_block"):
                env_buffer = self._work_buffer
                if env_buffer is not None:
                    env.generate_block(env_buffer[:block_size], block_size)
                    output[:, :] *= env_buffer[:block_size, np.newaxis]

        # 6a. Apply expression (CC11) — multiplicative with channel volume
        if self._expression_mod != 1.0:
            output[:, :] *= self._expression_mod

        # 6b. Apply soft pedal
        if self._soft_pedal:
            output[:, :] *= self._soft_pedal_depth

        # 7. Apply filter with modulation
        self._apply_filter_with_modulation(output, block_size)

        # 8. Apply tremolo and auto-pan
        self._apply_tremolo_and_pan(output, block_size)

        # 9. Apply final volume modulation (includes GS volume, initialAttenuation)
        volume_factor = self._volume_mod
        if self._gs_volume >= 0.0:
            volume_factor *= self._gs_volume
        # Apply initialAttenuation (gen 48) — centibels to linear gain
        if self._initial_attenuation_db > 0.0:
            volume_factor *= 10.0 ** (-self._initial_attenuation_db / 20.0)
        if volume_factor != 1.0:
            output[:, :] *= volume_factor

        # 9a. Apply GS pan if set
        if self._gs_pan >= -1.0:
            # GS pan: -1.0 (left) to 1.0 (right), applied as additional pan factor
            gs_left = min(1.0, max(0.0, 1.0 - max(0.0, self._gs_pan)))
            gs_right = min(1.0, max(0.0, 1.0 + min(0.0, self._gs_pan)))
            output[:, 0] *= gs_left
            output[:, 1] *= gs_right

        # Check if voice is done
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "is_active") and not env.is_active():
                if self.state == RegionState.RELEASING:
                    self._active = False

        if output.shape[0] != block_size:
            output = (
                output[:block_size]
                if output.shape[0] > block_size
                else np.vstack(
                    [
                        output,
                        (
                            self._buffer_pool.get_stereo_buffer(block_size - output.shape[0])
                            if self._buffer_pool is not None
                            else np.zeros((block_size - output.shape[0], 2), dtype=np.float32)
                        ),
                    ]
                )
            )

        return output

    def _generate_samples_with_mipmap(self, output: np.ndarray, block_size: int) -> None:
        """
        Generate samples with mip-map anti-aliasing (legacy method for compatibility).

        Args:
            output: Output buffer (stereo interleaved)
            block_size: Number of stereo frames
        """
        self._generate_samples_with_mipmap_and_modulation(
            output, block_size, 1.0 / self.sample_rate
        )

    def _generate_samples_with_mipmap_and_modulation(
        self, output: np.ndarray, block_size: int, sample_delta_time: float
    ) -> None:
        """
        Generate samples with mip-map anti-aliasing and per-sample pitch modulation.

        Uses vectorized operations for forward playback and cached interleaved
        stereo data for efficiency.

        Args:
            output: Output buffer (stereo interleaved)
            block_size: Number of stereo frames
            sample_delta_time: Time per sample in seconds (unused, kept for API compat)
        """
        if self._sample_data is None or len(self._sample_data) == 0:
            return

        mip_level = self._select_mip_map_level()
        mip_data = self._get_mip_map_data(mip_level)

        if mip_data is None or len(mip_data) == 0:
            return

        decimation_factor = 2**mip_level
        mip_sample_length = len(mip_data)

        # Effective end-of-sample bound from gen1/gen12 address offsets (in mip space).
        # Falls back to the full mip length when no end offset was applied.
        effective_end_mip = (
            self._effective_end // decimation_factor
            if self._effective_end > 0
            else mip_sample_length
        )
        effective_end_mip = max(1, min(effective_end_mip, mip_sample_length))

        pos = self._sample_position / decimation_factor
        loop_start_mip = self._loop_start / decimation_factor
        loop_end_mip = self._loop_end / decimation_factor
        base_phase_step_mip = self._base_phase_step / decimation_factor
        crossfade_len = self._loop_crossfade_samples / decimation_factor

        # --- REVERSE PLAYBACK: use serial fallback (rare path) ---
        if self._reverse_playback:
            self._generate_samples_reverse(
                output,
                block_size,
                mip_data,
                effective_end_mip,
                pos,
                loop_start_mip,
                loop_end_mip,
                base_phase_step_mip,
                crossfade_len,
                decimation_factor,
            )
            return

        # --- VECTORIZED PATH (forward playback) ---

        # 1. Pre-compute pitch modulation for entire block (vectorized)
        pitch_mods = np.full(block_size, self._pitch_mod, dtype=np.float64)
        if self._vib_lfo_buffer is not None:
            pitch_mods += self._vib_lfo_buffer[:block_size] * self._vib_lfo_to_pitch
        if self._mod_lfo_buffer is not None:
            pitch_mods += self._mod_lfo_buffer[:block_size] * self._mod_lfo_to_pitch
        if self._mod_env_buffer is not None:
            pitch_mods += self._mod_env_buffer[:block_size] * self._mod_env_to_pitch
        if self._pitch_env_buffer is not None:
            pitch_mods += self._pitch_env_buffer[:block_size]
        if (
            self._portamento_active
            and self._portamento_note is not None
            and self._portamento_target is not None
            and self._portamento_time > 0.0
        ):
            glide_start = self._portamento_glide_phase
            glide_increment = 1.0 / (self._portamento_time * self.sample_rate)
            glide_progress = np.minimum(
                1.0,
                glide_start + np.arange(block_size, dtype=np.float64) * glide_increment,
            )
            pitch_mods += (self._portamento_target - self._portamento_note) * glide_progress
            # Update glide phase for next block
            self._portamento_glide_phase = min(1.0, glide_start + glide_increment * block_size)

        # 2. Calculate phase steps (vectorized)
        phase_steps = base_phase_step_mip * np.power(2.0, pitch_mods / 12.0)

        # 3. Build cumulative read positions
        cumsum = np.cumsum(phase_steps)
        # TODO: Use BufferPool when available (requires float64 pool)
        if self._read_positions is None or len(self._read_positions) < block_size:
            self._read_positions = np.empty(block_size, dtype=np.float64)
        read_positions = self._read_positions[:block_size]
        read_positions[0] = pos
        if block_size > 1:
            read_positions[1:] = pos + cumsum[:-1]

        # 4. Apply loop wrapping based on mode
        if self._loop_mode == 1 and loop_end_mip > loop_start_mip:
            loop_length = loop_end_mip - loop_start_mip
            if loop_length > 0:
                in_loop = read_positions >= loop_end_mip
                if np.any(in_loop):
                    wraps = np.floor((read_positions[in_loop] - loop_start_mip) / loop_length)
                    read_positions[in_loop] -= wraps * loop_length

        elif self._loop_mode == 3:
            loop_length = loop_end_mip - loop_start_mip
            if loop_length > 0 and loop_end_mip > loop_start_mip:
                in_loop = read_positions >= loop_end_mip
                if np.any(in_loop):
                    wraps = np.floor((read_positions[in_loop] - loop_start_mip) / loop_length)
                    read_positions[in_loop] -= wraps * loop_length

        elif self._loop_mode == 0:
            past_end = read_positions >= effective_end_mip
            if np.any(past_end):
                read_positions[past_end] = effective_end_mip - 1
                self.state = RegionState.RELEASING

        # 5. Clamp positions to safe range
        read_positions = np.clip(read_positions, 0, effective_end_mip - 1)

        # 6. Linear interpolation (vectorized over entire block)
        int_pos = np.floor(read_positions).astype(np.int64)
        frac = read_positions - int_pos
        i0 = np.clip(int_pos, 0, mip_sample_length - 1)
        i1 = np.clip(int_pos + 1, 0, mip_sample_length - 1)
        if mip_sample_length > 0:
            s1 = mip_data[i0]  # (block_size, 2)
            s2 = mip_data[i1]  # (block_size, 2)
            sample = s1 + frac[:, np.newaxis] * (s2 - s1)
        else:
            sample = (
                self._buffer_pool.get_stereo_buffer(block_size)
                if self._buffer_pool is not None
                else np.zeros((block_size, 2), dtype=np.float32)
            )

        # 7. Loop crossfade (vectorized) — fade-out at loop end, fade-in at start
        if crossfade_len > 0 and loop_end_mip > loop_start_mip:
            in_crossfade_end = (read_positions >= loop_end_mip - crossfade_len) & (
                read_positions < loop_end_mip
            )
            if np.any(in_crossfade_end):
                dist_to_end = loop_end_mip - read_positions[in_crossfade_end]
                fade = 0.5 * (1.0 + np.cos(np.pi * dist_to_end / crossfade_len))
                sample[in_crossfade_end, 0] *= fade
                sample[in_crossfade_end, 1] *= fade

            in_crossfade_start = (read_positions >= loop_start_mip) & (
                read_positions < loop_start_mip + crossfade_len
            )
            if np.any(in_crossfade_start):
                dist_from_start = read_positions[in_crossfade_start] - loop_start_mip
                fade = 0.5 * (1.0 - np.cos(np.pi * dist_from_start / crossfade_len))
                sample[in_crossfade_start, 0] *= fade
                sample[in_crossfade_start, 1] *= fade

        # 8. Write to output
        output[:block_size] = sample[:block_size]

        # 9. Calculate next sample position for next block
        next_pos = pos + np.sum(phase_steps)

        # Apply loop wrapping to next position
        if self._loop_mode == 1 and loop_end_mip > loop_start_mip:
            loop_length = loop_end_mip - loop_start_mip
            if loop_length > 0 and next_pos >= loop_end_mip:
                wraps = np.floor((next_pos - loop_start_mip) / loop_length)
                next_pos -= wraps * loop_length
        elif self._loop_mode == 3:
            loop_length = loop_end_mip - loop_start_mip
            if loop_length > 0 and loop_end_mip > loop_start_mip and next_pos >= loop_end_mip:
                wraps = np.floor((next_pos - loop_start_mip) / loop_length)
                next_pos -= wraps * loop_length
            if next_pos >= mip_sample_length:
                next_pos = mip_sample_length - 1
                self.state = RegionState.RELEASING
        elif self._loop_mode == 0:
            if next_pos >= mip_sample_length:
                next_pos = mip_sample_length - 1
                self.state = RegionState.RELEASING

        # Bounds clamp for next_pos (matches original behavior)
        if next_pos < 0:
            next_pos = 0.0
        if next_pos >= mip_sample_length:
            if self._is_drum_mode:
                next_pos = mip_sample_length - 1
            else:
                self._active = False

        # Store position back in base sample space
        self._sample_position = next_pos * decimation_factor

    def _generate_samples_reverse(
        self,
        output: np.ndarray,
        block_size: int,
        mip_data: np.ndarray,
        mip_sample_length: int,
        pos: float,
        loop_start_mip: float,
        loop_end_mip: float,
        base_phase_step_mip: float,
        crossfade_len: float,
        decimation_factor: int,
    ) -> None:
        """
        Generate samples for reverse playback (serial fallback for rare path).

        Args:
            output: Output buffer (stereo interleaved)
            block_size: Number of stereo frames
            mip_data: Mip-map sample data (samples, 2)
            mip_sample_length: Length of mip data in samples
            pos: Current sample position (in mip space)
            loop_start_mip: Loop start position (in mip space)
            loop_end_mip: Loop end position (in mip space)
            base_phase_step_mip: Base phase step (in mip space)
            crossfade_len: Crossfade length (in mip space)
            decimation_factor: Mip-map decimation factor
        """
        for i in range(block_size):
            pitch_mod = self._calculate_sample_pitch_modulation(i)
            phase_step = base_phase_step_mip * (2.0 ** (pitch_mod / 12.0))

            pos_int = int(pos)
            frac = pos - pos_int

            if pos_int < mip_sample_length - 1:
                s1 = mip_data[pos_int]
                s2 = mip_data[min(pos_int + 1, mip_sample_length - 1)]
                sample_left = s1[0] + frac * (s2[0] - s1[0])
                sample_right = s1[1] + frac * (s2[1] - s1[1])
            else:
                last = mip_data[-1] if mip_sample_length > 0 else (0.0, 0.0)
                sample_left = last[0]
                sample_right = last[1]

            # Handle loop crossfade (fade-out at loop end, fade-in at start)
            if crossfade_len > 0 and loop_end_mip > loop_start_mip:
                if loop_start_mip <= pos < loop_end_mip:
                    dist_to_end = loop_end_mip - pos
                    dist_from_start = pos - loop_start_mip
                    if dist_to_end < crossfade_len:
                        fade_out = 0.5 * (1.0 + np.cos(np.pi * dist_to_end / crossfade_len))
                        sample_left *= fade_out
                        sample_right *= fade_out
                    if dist_from_start < crossfade_len:
                        fade_in = 0.5 * (1.0 - np.cos(np.pi * dist_from_start / crossfade_len))
                        sample_left *= fade_in
                        sample_right *= fade_in

            # Reverse playback stepping
            pos = pos - phase_step
            if pos < loop_start_mip:
                pos = loop_end_mip - (loop_start_mip - pos)

            # Check bounds
            if pos < 0:
                pos = 0.0
            if pos >= mip_sample_length:
                if self._is_drum_mode:
                    pos = mip_sample_length - 1
                else:
                    self._active = False
                    break

            output[i, 0] = sample_left
            output[i, 1] = sample_right

        self._sample_position = pos * decimation_factor

    def _select_mip_map_level(self) -> int:
        """
        Select appropriate mip-map level based on pitch ratio.

        Mip-maps are pre-computed lower-resolution versions of samples
        used to prevent aliasing when playing back at higher pitches.

        Returns:
            Mip-map level (0 = full resolution, 1 = half, 2 = quarter, etc.)
        """
        if self._phase_step <= 1.0:
            return 0  # Normal or lower pitch - use full resolution

        # Calculate mip level based on pitch ratio
        # Each doubling of pitch ratio increases mip level by 1
        mip_level = int(math.log2(self._phase_step))

        # Cap at reasonable level (typically 4-5 levels max)
        return min(mip_level, 4)

    def _get_mip_map_data(self, mip_level: int) -> np.ndarray | None:
        """
        Get sample data for the specified mip-map level.

        Uses caching to avoid repeated lookups when mip_level hasn't changed.
        All data is stereo interleaved (samples, 2).

        Args:
            mip_level: Mip-map level to retrieve

        Returns:
            Stereo interleaved sample data (samples, 2) or None
        """
        if self._sample_data is None:
            return None

        if mip_level == 0:
            # Restore base-level loop bounds (mip-space bounds only apply > 0).
            self._loop_start = self._base_loop_start
            self._loop_end = self._base_loop_end
            return self._sample_data

        if mip_level == self._cached_mip_level and self._cached_mip_data is not None:
            return self._cached_mip_data

        mip_data = self.soundfont_manager.get_mip_map_sample_data(
            self.descriptor.sample_id, mip_level
        )

        if mip_data is not None:
            self._cached_mip_level = mip_level
            self._cached_mip_data = mip_data
            # NOTE: loop bounds stay in BASE-level frames. The render path
            # converts them to mip space via `loop_start / decimation_factor`.
            # Do NOT overwrite them with mip-space integers here — that would
            # double-divide and place the loop region in the wrong part of the
            # (shorter) mip data, causing out-of-range reads and full-scale
            # clicks on every mip level > 0.
            return mip_data

        return None

    def _handle_sf2_looping(self, position: float, sample_length: int) -> float:
        """
        Handle SF2 sample looping modes.

        Args:
            position: Current sample position
            sample_length: Total sample length

        Returns:
            Adjusted position after looping
        """
        if self._loop_mode == 0:
            # No loop - stop at end
            if position >= sample_length:
                position = sample_length - 1
                self.state = RegionState.RELEASING

        elif self._loop_mode == 1:
            # Forward loop
            if position >= self._loop_end and self._loop_end > self._loop_start:
                loop_length = self._loop_end - self._loop_start
                if loop_length > 0:
                    excess = position - self._loop_end
                    position = self._loop_start + (excess % loop_length)

        elif self._loop_mode == 3:
            # Loop and continue (position >= loop_end wraps to loop_start)
            if position >= self._loop_end and self._loop_end > self._loop_start:
                loop_length = self._loop_end - self._loop_start
                if loop_length > 0:
                    excess = position - self._loop_end
                    position = self._loop_start + (excess % loop_length)
            elif position >= sample_length:
                position = sample_length - 1
                self.state = RegionState.RELEASING

        return position

    def _handle_sf2_looping_mip(
        self,
        position: float,
        sample_length: int,
        loop_start: float,
        loop_end: float,
    ) -> float:
        """
        Handle SF2 sample looping modes in mip-map space.

        Args:
            position: Current sample position (in mip space)
            sample_length: Total sample length (in mip space)
            loop_start: Loop start position (in mip space)
            loop_end: Loop end position (in mip space)

        Returns:
            Adjusted position after looping
        """
        if self._loop_mode == 0:
            # No loop - stop at end
            if position >= sample_length:
                position = sample_length - 1
                self.state = RegionState.RELEASING

        elif self._loop_mode == 1:
            # Forward loop
            if position >= loop_end and loop_end > loop_start:
                loop_length = loop_end - loop_start
                if loop_length > 0:
                    excess = position - loop_end
                    position = loop_start + (excess % loop_length)

        elif self._loop_mode == 3:
            # Loop and continue (position >= loop_end wraps to loop_start)
            if position >= loop_end and loop_end > loop_start:
                loop_length = loop_end - loop_start
                if loop_length > 0:
                    excess = position - loop_end
                    position = loop_start + (excess % loop_length)
            elif position >= sample_length:
                position = sample_length - 1
                self.state = RegionState.RELEASING

        return position

    def is_active(self) -> bool:
        """Check if SF2 region is still producing sound."""
        if not self._active:
            return False

        if self.state == RegionState.RELEASED:
            return False

        if self.state == RegionState.RELEASING:
            # Check if envelope has completed
            if "amp_env" in self._envelopes:
                env = self._envelopes["amp_env"]
                if hasattr(env, "is_active"):
                    return env.is_active()
            return False

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def reset(self) -> None:
        """Reset region state for reuse."""
        super().reset()
        self._sample_position = 0.0
        self._phase_step = 1.0
        self._base_phase_step = 1.0
        self._active = False

        # Reset modulation state
        self._pitch_mod = 0.0
        self._filter_mod = 0.0
        self._volume_mod = 1.0
        self._pan_position = 0.0

        # Reset modulation envelope
        self._mod_env_stage = 0
        self._mod_env_level = 0.0
        self._mod_env_time_in_stage = 0.0

        # Reset pitch envelope
        self._pitch_env_stage = 0
        self._pitch_env_level = 0.0

        # Reset GS parameter state (-1 = unset/use default)
        self._gs_filter_cutoff = -1.0
        self._gs_filter_resonance = -1.0
        self._gs_amp_attack = -1.0
        self._gs_amp_decay = -1.0
        self._gs_amp_release = -1.0
        self._gs_vibrato_rate = -1.0
        self._gs_vibrato_depth = -1.0
        self._gs_vibrato_delay = -1.0
        self._gs_volume = -1.0
        self._gs_pan = -1.0
        self._gs_reverb_send = -1.0
        self._gs_chorus_send = -1.0

    def dispose(self) -> None:
        """Release resources."""
        super().dispose()
        self._sample_data = None
        self._sf2_zone = None
        self.descriptor.is_sample_loaded = False

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "sample_id": self.descriptor.sample_id,
                "sample_loaded": self._sample_data is not None,
                "loop_mode": self._loop_mode,
                "root_key": self._root_key,
                "sample_position": self._sample_position,
                "sf2_zone_cached": self._sf2_zone is not None,
                "key_range": self._key_range,
                "velocity_range": self._velocity_range,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SF2Region(id={self.descriptor.region_id}, "
            f"sample={self.descriptor.sample_id}, "
            f"loaded={self._sample_data is not None}, "
            f"zone_cached={self._sf2_zone is not None})"
        )
