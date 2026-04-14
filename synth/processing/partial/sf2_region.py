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
from typing import Any

import numpy as np

from ...engines.region_descriptor import RegionDescriptor
from ...processing.partial.region import IRegion, RegionState

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
        "_active",
        "_sample_data",
        # Mip-map cache
        "_cached_mip_level",
        "_cached_mip_data",
        "_sample_position",
        "_phase_step",
        "_base_phase_step",
        "_root_key",
        "_coarse_tune",
        "_fine_tune",
        "_loop_start",
        "_loop_end",
        "_loop_mode",
        "_key_range",
        "_velocity_range",
        "_exclusive_class",
        # Generator params
        "_generator_params",
        "_modulators",
        # Zone cache
        "_sf2_zone",
        "_sf2_preset",
        "_sf2_instrument",
        # External references
        "soundfont_manager",
        "synth",
        # LFO objects (zero-allocation: reused)
        "_mod_lfo",
        "_vib_lfo",
        # LFO buffers (pre-allocated, zero-allocation)
        "_mod_lfo_buffer",
        "_vib_lfo_buffer",
        # Modulation envelope buffer
        "_mod_env_buffer",
        # Pitch modulation
        "_pitch_mod",
        "_vib_lfo_to_pitch",
        "_mod_lfo_to_pitch",
        "_mod_env_to_pitch",
        # Filter modulation
        "_filter_mod",
        "_mod_lfo_to_filter",
        "_mod_env_to_filter",
        "_filter_key_track",
        # Volume modulation
        "_volume_mod",
        "_mod_lfo_to_volume",
        "_mod_env_to_volume",
        # Pan
        "_pan_position",
        "_mod_lfo_to_pan",
        "_vib_lfo_to_pan",
        "_mod_env_to_pan",
        # Modulation envelope state
        "_mod_env_stage",
        "_mod_env_level",
        "_mod_env_stage_time",
        "_mod_env_time_in_stage",
        # Modulation envelope params
        "_delay_mod_env",
        "_attack_mod_env",
        "_hold_mod_env",
        "_decay_mod_env",
        "_sustain_mod_env",
        "_release_mod_env",
        # LFO params
        "_delay_mod_lfo",
        "_freq_mod_lfo",
        "_delay_vib_lfo",
        "_freq_vib_lfo",
        # Key tracking
        "_keynum_to_mod_env_hold",
        "_keynum_to_mod_env_decay",
        "_keynum_to_vol_env_hold",
        "_keynum_to_vol_env_decay",
        # Effects sends
        "_reverb_send",
        "_chorus_send",
        # Controller modulation
        "_aftertouch_mod",
        "_breath_mod",
        "_modwheel_mod",
        "_foot_mod",
        "_expression_mod",
        # Filter type
        "_filter_type",
        # Velocity processing
        "_velocity_curve",
        # Pitch envelope
        "_pitch_env_active",
        "_pitch_env_stage",
        "_pitch_env_level",
        "_pitch_env_time_in_stage",
        "_pitch_env_delay",
        "_pitch_env_attack",
        "_pitch_env_decay",
        "_pitch_env_sustain",
        "_pitch_env_release",
        "_pitch_env_depth",
        # Drum mode
        "_is_drum_mode",
        # Reverse playback
        "_reverse_playback",
        # Loop crossfade
        "_loop_crossfade_samples",
        # Current block size for buffer sizing
        "_current_block_size",
        # Portamento
        "_portamento_active",
        "_portamento_time",
        "_portamento_note",
        "_portamento_target",
        "_portamento_glide_phase",
        # Pedals
        "_sustain_pedal",
        "_sostenuto_pedal",
        "_soft_pedal",
        "_legato_active",
        "_hold2_pedal",
        "_held_by_sostenuto",
        "_held_by_hold2",
        # XG Sound Controllers
        "_sound_controller_1",
        # Envelope/Vibrato XG (CC73-79)
        "_xg_release_time",
        "_xg_attack_time",
        "_xg_filter_cutoff",
        "_xg_decay_time",
        "_xg_vibrato_rate",
        "_xg_vibrato_depth",
        "_xg_vibrato_delay",
        # General Purpose Buttons
        "_gp_button_1",
        "_gp_button_2",
        "_gp_button_3",
        "_gp_button_4",
        # Tremolo (CC92)
        "_tremolo_depth",
        # Balance (CC8)
        "_balance",
        # Previous note for portamento
        "_last_note",
    ]

    def __init__(
        self,
        descriptor: RegionDescriptor,
        sample_rate: int = 44100,
        soundfont_manager: Any | None = None,
        synth: Any | None = None,
    ):
        """
        Initialize SF2 region with full SF2 package integration.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz
            soundfont_manager: SF2SoundFontManager for sample/zone access
            synth: ModernXGSynthesizer instance for infrastructure access
        """
        super().__init__(descriptor, sample_rate)
        self.synth = synth
        self.soundfont_manager = soundfont_manager

        # SF2-specific state (lazy loaded)
        self._sample_data: np.ndarray | None = None

        # Mip-map cache (stereo interleaved format)
        self._cached_mip_level: int = -1
        self._cached_mip_data: np.ndarray | None = None

        self._loop_start: int = 0
        self._loop_end: int = 0
        self._loop_mode: int = 0

        # SF2 zone cache (lazy loaded from SF2 package)
        self._sf2_zone: Any | None = None
        self._sf2_preset: Any | None = None
        self._sf2_instrument: Any | None = None

        # SF2 generator parameters (merged from preset + instrument levels)
        self._generator_params: dict[int, int] = {}
        self._modulators: list[dict[str, Any]] = []

        # SF2 zone ranges
        self._key_range: tuple[int, int] = (0, 127)
        self._velocity_range: tuple[int, int] = (0, 127)
        self._exclusive_class: int = 0

        # Playback state
        self._root_key: int = 60
        self._coarse_tune: int = 0
        self._fine_tune: float = 0.0
        self._sample_position: float = 0.0
        self._phase_step: float = 1.0
        self._base_phase_step: float = 1.0

        # Voice active state
        self._active: bool = False
        self._current_block_size: int = 1024

        # Initialize LFO objects (zero-allocation: created once)
        self._mod_lfo = None
        self._vib_lfo = None
        self._mod_lfo_buffer: np.ndarray | None = None
        self._vib_lfo_buffer: np.ndarray | None = None
        self._mod_env_buffer: np.ndarray | None = None

        # Pitch modulation
        self._pitch_mod: float = 0.0
        self._vib_lfo_to_pitch: float = 0.0
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
        self._mod_env_to_volume: float = 0.0

        # Pan
        self._pan_position: float = 0.0
        self._mod_lfo_to_pan: float = 0.0
        self._vib_lfo_to_pan: float = 0.0
        self._mod_env_to_pan: float = 0.0

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
        self._expression_mod: float = 0.0

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
                self._loop_mode = loop_info.get("mode", 0)

    def _load_sample_info(self) -> None:
        """Load sample root key and tuning from SF2 sample header."""
        if self.descriptor.sample_id is None:
            return

        # Get sample info from SF2SoundFontManager
        if hasattr(self.soundfont_manager, "get_sample_info"):
            sample_info = self.soundfont_manager.get_sample_info(self.descriptor.sample_id)
            if sample_info:
                self._root_key = sample_info.get("original_pitch", 60)

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

        # Cache exclusive class
        self._exclusive_class = self._generator_params.get(53, 0)  # exclusiveClass

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
            # Map common generator types
            gen_mapping = {
                8: "amp_delay",
                9: "amp_attack",
                10: "amp_hold",
                11: "amp_decay",
                12: "amp_sustain",
                13: "amp_release",
                29: "filter_cutoff",
                30: "filter_resonance",
                48: "coarse_tune",
                49: "fine_tune",
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
                "mode": self._get_generator_value(51, 0),  # sampleMode
                "start": self._loop_start,
                "end": self._loop_end,
            },
            # Volume envelope (nested)
            "amp_envelope": {
                "delay": self._timecents_to_seconds(self._get_generator_value(8, -12000)),
                "attack": self._timecents_to_seconds(self._get_generator_value(9, -12000)),
                "hold": self._timecents_to_seconds(self._get_generator_value(10, -12000)),
                "decay": self._timecents_to_seconds(self._get_generator_value(11, -12000)),
                "sustain": self._get_generator_value(12, 0) / 1000.0,
                "release": self._timecents_to_seconds(self._get_generator_value(13, -12000)),
            },
            # Modulation envelope (nested)
            "mod_envelope": {
                "delay": self._timecents_to_seconds(self._get_generator_value(14, -12000)),
                "attack": self._timecents_to_seconds(self._get_generator_value(15, -12000)),
                "hold": self._timecents_to_seconds(self._get_generator_value(16, -12000)),
                "decay": self._timecents_to_seconds(self._get_generator_value(17, -12000)),
                "sustain": self._get_generator_value(18, 0) / 1000.0,
                "release": self._timecents_to_seconds(self._get_generator_value(19, -12000)),
                "to_pitch": self._get_generator_value(20, 0) / 1200.0,
            },
            # Mod LFO (nested)
            "mod_lfo": {
                "delay": self._timecents_to_seconds(self._get_generator_value(21, -12000)),
                "frequency": self._cents_to_frequency(self._get_generator_value(22, 0)),
                "to_volume": self._get_generator_value(23, 0) / 960.0,
                "to_filter": self._get_generator_value(24, 0) / 1200.0,
                "to_pitch": self._get_generator_value(25, 0) / 1200.0,
            },
            # Vib LFO (nested)
            "vib_lfo": {
                "delay": self._timecents_to_seconds(self._get_generator_value(26, -12000)),
                "frequency": self._cents_to_frequency(self._get_generator_value(27, 0)),
                "to_pitch": self._get_generator_value(28, 0) / 1200.0,
            },
            # Filter (nested)
            "filter": {
                "cutoff": self._cents_to_frequency(self._get_generator_value(29, 13500)),
                "resonance": self._get_generator_value(30, 0) / 10.0,
                "type": "lowpass",
            },
            # Effects (nested)
            "effects": {
                "reverb_send": self._get_generator_value(32, 0) / 1000.0,
                "chorus_send": self._get_generator_value(33, 0) / 1000.0,
                "pan": self._get_generator_value(34, 0) / 500.0,
            },
            # Pitch modulation (nested)
            "pitch_modulation": {
                "coarse_tune": self._get_generator_value(48, 0),
                "fine_tune": self._get_generator_value(49, 0) / 100.0,
                "scale_tuning": self._get_generator_value(52, 100) / 100.0,
            },
            # Key tracking (nested)
            "key_tracking": {
                "to_mod_env_hold": self._get_generator_value(35, 0),
                "to_mod_env_decay": self._get_generator_value(36, 0),
                "to_vol_env_hold": self._get_generator_value(37, 0),
                "to_vol_env_decay": self._get_generator_value(38, 0),
            },
            # Sample settings (nested)
            "sample_settings": {
                "mode": self._get_generator_value(51, 0),
                "exclusive_class": self._get_generator_value(53, 0),
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
        """Convert SF2 cents to frequency in Hz."""
        return 440.0 * (2.0 ** (cents / 1200.0))

    def _init_lfos(self) -> None:
        """Initialize LFO objects from SF2 generators (zero-allocation)."""
        from ...primitives.oscillator import UltraFastXGLFO

        # Get LFO parameters from generators
        self._delay_mod_lfo = self._timecents_to_seconds(self._get_generator_value(21, -12000))
        self._freq_mod_lfo = self._cents_to_frequency(self._get_generator_value(22, 0))

        self._delay_vib_lfo = self._timecents_to_seconds(self._get_generator_value(26, -12000))
        self._freq_vib_lfo = self._cents_to_frequency(self._get_generator_value(27, 0))

        # Get LFO waveform (gen 43) - default to sine
        lfo_waveform = self._get_generator_value(43, 0)
        waveform_name = "sine"
        if lfo_waveform == 1:
            waveform_name = "triangle"
        elif lfo_waveform == 2:
            waveform_name = "square"
        elif lfo_waveform == 3:
            waveform_name = "sawtooth"
        elif lfo_waveform == 4:
            waveform_name = "sample_hold"

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

        # Load LFO modulation depths from generators (scaled)
        self._vib_lfo_to_pitch = self._get_generator_value(28, 0) / 100.0
        self._mod_lfo_to_pitch = self._get_generator_value(25, 0) / 100.0
        self._mod_lfo_to_filter = self._get_generator_value(24, 0) / 1200.0
        self._mod_lfo_to_volume = self._get_generator_value(23, 0) / 10.0
        self._vib_lfo_to_pan = self._get_generator_value(37, 0) / 10.0
        self._mod_lfo_to_pan = self._get_generator_value(42, 0) / 10.0

    def _init_modulation_envelope(self) -> None:
        """Initialize modulation envelope state and parameters."""
        # Reset envelope state
        self._mod_env_stage = 0  # idle
        self._mod_env_level = 0.0
        self._mod_env_stage_time = 0.0
        self._mod_env_time_in_stage = 0.0

        # Load modulation envelope parameters from generators
        self._delay_mod_env = self._timecents_to_seconds(self._get_generator_value(14, -12000))
        self._attack_mod_env = self._timecents_to_seconds(self._get_generator_value(15, -12000))
        self._hold_mod_env = self._timecents_to_seconds(self._get_generator_value(16, -12000))
        self._decay_mod_env = self._timecents_to_seconds(self._get_generator_value(17, -12000))
        self._sustain_mod_env = self._get_generator_value(18, 0) / 1000.0
        self._release_mod_env = self._timecents_to_seconds(self._get_generator_value(19, -12000))

        # Load modulation depths
        self._mod_env_to_pitch = self._get_generator_value(20, 0) / 1200.0
        self._mod_env_to_filter = self._get_generator_value(44, 0) / 1200.0
        self._mod_env_to_volume = 0.0  # Custom extension
        self._mod_env_to_pan = 0.0  # Custom extension

        # Load key tracking for mod envelope
        self._keynum_to_mod_env_hold = self._get_generator_value(31, 0) / 100.0
        self._keynum_to_mod_env_decay = self._get_generator_value(32, 0) / 100.0

    def _init_pitch_envelope(self) -> None:
        """Initialize pitch envelope (separate from mod envelope)."""
        # Check if pitch envelope is active
        self._pitch_env_active = (
            self._get_generator_value(54, -12000) > -12000
            or self._get_generator_value(55, -12000) > -12000
        )

        if self._pitch_env_active:
            self._pitch_env_stage = 0  # idle
            self._pitch_env_level = 0.0
            self._pitch_env_time_in_stage = 0.0

            self._pitch_env_delay = self._timecents_to_seconds(
                self._get_generator_value(54, -12000)
            )
            self._pitch_env_attack = self._timecents_to_seconds(
                self._get_generator_value(55, -12000)
            )
            self._pitch_env_decay = self._timecents_to_seconds(
                self._get_generator_value(57, -12000)
            )
            self._pitch_env_sustain = self._get_generator_value(58, 0) / 100.0
            self._pitch_env_release = self._timecents_to_seconds(
                self._get_generator_value(59, -12000)
            )
            self._pitch_env_depth = self._get_generator_value(52, 0) / 100.0

    def _init_envelopes(self) -> None:
        """Initialize envelopes from SF2 generator parameters."""
        from ...primitives.envelope import UltraFastADSREnvelope

        # Get key-scaled parameters
        note = self.current_note
        key_offset = (note - 60) / 60.0 if note > 0 else 0.0

        # Amplitude envelope with key scaling
        self._keynum_to_vol_env_hold = self._get_generator_value(37, 0) / 100.0
        self._keynum_to_vol_env_decay = self._get_generator_value(38, 0) / 100.0

        key_scaled_hold = 1.0 + self._keynum_to_vol_env_hold * key_offset
        key_scaled_decay = 1.0 + self._keynum_to_vol_env_decay * key_offset

        # Get timecents values - fix for incorrect defaults from descriptors storing seconds instead of timecents
        gen8_val = self._get_generator_value(8, -12000)
        gen9_val = self._get_generator_value(9, -12000)
        gen10_val = self._get_generator_value(10, -12000)
        gen11_val = self._get_generator_value(11, -12000)
        gen12_val = self._get_generator_value(12, 1000)
        gen13_val = self._get_generator_value(13, -12000)

        # Values from descriptor might be in wrong format (0.0 instead of -12000 for "instant")
        # For time-related generators, if value is >= 0, treat as seconds to convert back to timecents
        # SF2 timecents: -12000 = instant, -11999 = ~1ms, 0 = 1 second
        if gen8_val >= 0:
            gen8_val = int(-12000)  # instant
        if gen9_val >= 0:
            gen9_val = int(-12000)  # instant
        if gen10_val >= 0:
            gen10_val = int(-12000)  # instant
        if gen11_val >= 0:
            gen11_val = int(-12000)  # instant
        if gen13_val >= 0:
            gen13_val = int(-12000)  # instant

        # Sustain is in centibels (0-1000), default to full (1000) when unset
        if gen12_val <= 0:
            gen12_val = 1000

        delay = self._timecents_to_seconds(gen8_val)
        attack = self._timecents_to_seconds(gen9_val)
        hold = self._timecents_to_seconds(gen10_val)
        decay = self._timecents_to_seconds(gen11_val) * key_scaled_decay
        sustain = gen12_val / 1000.0
        release = self._timecents_to_seconds(gen13_val)

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

        cutoff = self._cents_to_frequency(self._get_generator_value(29, 13500))
        resonance = self._get_generator_value(30, 0) / 10.0

        # Get filter type (gen 36) - default to lowpass
        self._filter_type = self._get_generator_value(36, 0)
        filter_type_str = "lowpass"
        if self._filter_type == 1:
            filter_type_str = "highpass"
        elif self._filter_type == 2:
            filter_type_str = "bandpass"
        elif self._filter_type == 3:
            filter_type_str = "notch"
        elif self._filter_type == 4:
            filter_type_str = "peaking"

        filter_obj = UltraFastResonantFilter(
            cutoff=cutoff,
            resonance=resonance,
            filter_type=filter_type_str,
            sample_rate=self.sample_rate,
        )
        self._filters["filter"] = filter_obj

        # Initialize VCF key tracking (gen 31)
        vcf_key_track = self._get_generator_value(31, 0)  # -1200 to +1200 cents
        self._filter_key_track = vcf_key_track / 100.0  # Convert to semitones

    def _allocate_buffers_for_block(self, block_size: int) -> None:
        """Allocate buffers for specific block size (zero-allocation)."""
        if self._mod_lfo_buffer is None or len(self._mod_lfo_buffer) < block_size:
            self._mod_lfo_buffer = np.zeros(block_size, dtype=np.float32)
        if self._vib_lfo_buffer is None or len(self._vib_lfo_buffer) < block_size:
            self._vib_lfo_buffer = np.zeros(block_size, dtype=np.float32)
        if self._mod_env_buffer is None or len(self._mod_env_buffer) < block_size:
            self._mod_env_buffer = np.zeros(block_size, dtype=np.float32)

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

    def _calculate_phase_step(self) -> None:
        """Calculate phase step for sample playback."""
        if self._sample_data is None:
            self._phase_step = 1.0
            self._base_phase_step = 1.0
            return

        # Calculate pitch ratio based on note and SF2 tuning
        note_diff = self.current_note - self._root_key
        coarse_tune = self._get_generator_value(48, 0)
        fine_tune = self._get_generator_value(49, 0) / 100.0
        scale_tuning = self._get_generator_value(52, 100) / 100.0

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
        self._active = True
        self._calculate_phase_step()

        # Handle portamento (CC5, CC65)
        if self._portamento_active and self._last_note is not None:
            self._portamento_note = self._last_note
            self._portamento_target = note
            self._portamento_glide_phase = 0.0

        self._last_note = note

        # Load velocity curve (gen 41)
        self._velocity_curve = self._get_generator_value(41, 0)

        # Check for drum mode / one-shot (gen 57)
        sample_mode = self._get_generator_value(51, 0)
        self._is_drum_mode = sample_mode in [0, 1, 2, 3]

        # Check for reverse playback (gen 57)
        self._reverse_playback = self._get_generator_value(57, 0) == 1

        # Initialize loop crossfade (gen 45)
        self._loop_crossfade_samples = self._get_generator_value(45, 0)

        # Load effects sends
        self._reverb_send = self._get_generator_value(32, 0) / 1000.0
        self._chorus_send = self._get_generator_value(33, 0) / 1000.0

        # Load panning (gen 34)
        self._pan_position = self._get_generator_value(34, 0) / 500.0

        # Trigger amplitude envelope
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "note_on"):
                env.note_on(velocity, note)

        # Trigger modulation envelope
        self._trigger_modulation_envelope()

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

        # Reset modulation values
        self._pitch_mod = 0.0
        self._filter_mod = 0.0
        self._volume_mod = 1.0

        return True

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

        Args:
            controller: CC number (0-127)
            value: CC value (0-127)
        """
        normalized = value / 127.0

        if controller == 1:  # Modulation Wheel
            self._modwheel_mod = normalized
            self._vib_lfo_to_pitch *= 1.0 + normalized
            self._filter_mod += normalized * 1.5

        elif controller == 2:  # Breath Controller
            self._breath_mod = normalized
            self._filter_mod += normalized * 1.0

        elif controller == 4:  # Foot Controller
            self._foot_mod = normalized
            self._vib_lfo_to_pitch += normalized * 0.5

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
            self._filter_mod += (normalized - 0.5) * 1.0

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
        self._mod_env_to_filter += normalized * 0.5

    def _apply_brightness(self, normalized: float) -> None:
        """CC72: XG Brightness - modify filter cutoff."""
        self._filter_mod += normalized * 1.5

    def _apply_xg_release_time(self, normalized: float) -> None:
        """CC73: XG Release Time - modify amp envelope release."""
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            release_time = 0.001 + normalized * 4.999
            if hasattr(env, "release"):
                env.release = release_time

    def _apply_xg_attack_time(self, normalized: float) -> None:
        """CC74: XG Attack Time - modify amp envelope attack."""
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            attack_time = 0.001 + normalized * 9.999
            if hasattr(env, "attack"):
                env.attack = attack_time

    def _apply_xg_filter_cutoff(self, normalized: float) -> None:
        """CC75: XG Filter Cutoff - modify filter cutoff."""
        cutoff_mod = (normalized - 0.5) * 2.0
        self._filter_mod += cutoff_mod * 2.0

    def _apply_xg_decay_time(self, normalized: float) -> None:
        """CC76: XG Decay Time - modify amp envelope decay."""
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            decay_time = 0.01 + normalized * 4.99
            if hasattr(env, "decay"):
                env.decay = decay_time

    def _apply_xg_vibrato_rate(self, normalized: float) -> None:
        """CC77: XG Vibrato Rate - modify vib LFO rate."""
        if self._vib_lfo:
            rate = 0.5 + normalized * 8.0
            self._freq_vib_lfo = rate
            self._vib_lfo.set_frequency(rate)

    def _apply_xg_vibrato_depth(self, normalized: float) -> None:
        """CC78: XG Vibrato Depth - modify vib LFO depth."""
        self._vib_lfo_to_pitch = normalized * 1.0

    def _trigger_modulation_envelope(self) -> None:
        """Trigger modulation envelope attack."""
        self._mod_env_stage = 1  # delay
        self._mod_env_level = 0.0
        self._mod_env_time_in_stage = 0.0

    def _release_modulation_envelope(self) -> None:
        """Trigger modulation envelope release phase."""
        self._mod_env_stage = 6  # release

    def _apply_global_modulation(self, modulation: dict[str, float]) -> None:
        """Apply modulation from modulation matrix (zero-allocation)."""
        # Pitch modulation
        self._pitch_mod = modulation.get("pitch", 0.0)

        # Filter modulation (in octaves)
        self._filter_mod = modulation.get("filter_cutoff", 0.0)

        # Volume modulation
        self._volume_mod = modulation.get("volume", 1.0)

        # Controller sources
        self._aftertouch_mod = modulation.get("aftertouch", 0.0)
        self._breath_mod = modulation.get("breath", 0.0)
        self._modwheel_mod = modulation.get("modwheel", 0.0)
        self._foot_mod = modulation.get("foot", 0.0)
        self._expression_mod = modulation.get("expression", 0.0)

        # Apply controller effects to modulation depths
        if self._modwheel_mod != 0.0:
            self._vib_lfo_to_pitch *= 1.0 + self._modwheel_mod
            self._filter_mod += self._modwheel_mod * 1.5

        if self._aftertouch_mod != 0.0:
            self._volume_mod *= 1.0 + self._aftertouch_mod * 0.5
            self._filter_mod += self._aftertouch_mod * 2.0

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
            if stage_time >= self._hold_mod_env:
                self._mod_env_stage = 4  # decay
                self._mod_env_time_in_stage = 0.0
        elif self._mod_env_stage == 4:  # decay
            if stage_time >= self._decay_mod_env:
                self._mod_env_stage = 5  # sustain
                self._mod_env_level = self._sustain_mod_env
            else:
                decay_progress = (
                    stage_time / self._decay_mod_env if self._decay_mod_env > 0 else 1.0
                )
                self._mod_env_level = 1.0 - decay_progress * (1.0 - self._sustain_mod_env)
        elif self._mod_env_stage == 5:  # sustain
            self._mod_env_level = self._sustain_mod_env
        elif self._mod_env_stage == 6:  # release
            if stage_time >= self._release_mod_env:
                self._mod_env_level = 0.0
                self._mod_env_stage = 0  # idle
            else:
                release_progress = (
                    stage_time / self._release_mod_env if self._release_mod_env > 0 else 1.0
                )
                self._mod_env_level = self._sustain_mod_env * (1.0 - release_progress)

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
            base_cutoff = self._cents_to_frequency(self._get_generator_value(29, 13500))
            base_resonance = self._get_generator_value(30, 0) / 10.0

            # Calculate total filter modulation
            filter_mod_total = self._filter_mod

            # Add LFO filter modulation
            if self._mod_lfo_buffer is not None and self._mod_lfo_to_filter != 0.0:
                mean_lfo = np.mean(self._mod_lfo_buffer[:block_size])
                filter_mod_total += mean_lfo * self._mod_lfo_to_filter * 12.0  # Convert to octaves

            # Add mod envelope filter modulation
            if self._mod_env_buffer is not None and self._mod_env_to_filter != 0.0:
                mean_env = np.mean(self._mod_env_buffer[:block_size])
                filter_mod_total += mean_env * self._mod_env_to_filter * 12.0

            # Add VCF key tracking
            if self._filter_key_track != 0.0:
                filter_mod_total += self._filter_key_track

            # Calculate final cutoff
            modulated_cutoff = base_cutoff * (2.0**filter_mod_total)
            modulated_cutoff = max(20.0, min(20000.0, modulated_cutoff))

            # Update filter
            filter_obj.set_parameters(cutoff=modulated_cutoff, resonance=base_resonance)

            # Process (2D interleaved format)
            left = output[:, 0].copy()
            right = output[:, 1].copy()

            filtered_left, filtered_right = filter_obj.process_block(left, right)

            output[:, 0] = filtered_left
            output[:, 1] = filtered_right

        except Exception:
            pass  # Skip filter on error

    def _apply_tremolo_and_pan(self, output: np.ndarray, block_size: int) -> None:
        """Apply tremolo (LFO→volume), balance, and auto-pan (LFO→pan) (zero-allocation)."""
        # Apply tremolo (mod LFO → volume)
        if self._mod_lfo_to_volume != 0.0 and self._mod_lfo_buffer is not None:
            tremolo = 1.0 + self._mod_lfo_buffer[:block_size] * self._mod_lfo_to_volume * 0.5
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

        # Calculate total pan modulation
        total_pan = self._pan_position

        # Add LFO pan modulation
        if self._mod_lfo_to_pan != 0.0 and self._mod_lfo_buffer is not None:
            total_pan += np.mean(self._mod_lfo_buffer[:block_size]) * self._mod_lfo_to_pan
        if self._vib_lfo_to_pan != 0.0 and self._vib_lfo_buffer is not None:
            total_pan += np.mean(self._vib_lfo_buffer[:block_size]) * self._vib_lfo_to_pan

        # Apply pan (constant power)
        total_pan = max(-1.0, min(1.0, total_pan))
        if total_pan != 0.0:
            if total_pan < 0:
                left_gain = 1.0 + total_pan
                right_gain = 1.0
            else:
                left_gain = 1.0 - total_pan
                right_gain = 1.0

            output[:, 0] *= left_gain
            output[:, 1] *= right_gain

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
        # Handle inactive state
        if not self._active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Initialize if needed
        if self._sample_data is None:
            loaded_data = self._load_sample_data()
            if loaded_data is not None:
                self._sample_data = loaded_data
            else:
                self._active = False
                return np.zeros((block_size, 2), dtype=np.float32)

        if not self._initialized:
            if not self.initialize():
                self._active = False
                return np.zeros((block_size, 2), dtype=np.float32)

        # Update block size if changed
        if block_size != self._current_block_size:
            self._current_block_size = block_size
            # Resize LFO buffers
            if self._mod_lfo:
                self._mod_lfo.set_block_size(block_size)
            if self._vib_lfo:
                self._vib_lfo.set_block_size(block_size)

        # Allocate output buffer (2D interleaved)
        if self._output_buffer is None or self._output_buffer.shape[0] != block_size:
            self._output_buffer = np.zeros((block_size, 2), dtype=np.float32)
        if self._work_buffer is None or self._work_buffer.shape[0] != block_size:
            self._work_buffer = np.zeros(block_size, dtype=np.float32)
        output = self._output_buffer

        # 1. Apply global modulation from modulation matrix
        self._apply_global_modulation(modulation)

        # 2. Generate LFO signals (zero-allocation)
        self._generate_lfo_signals(block_size)

        # 3. Generate modulation envelope
        self._generate_modulation_envelope_block(block_size)

        # 4. Calculate pitch modulation for each sample
        sample_delta_time = 1.0 / self.sample_rate

        # 5. Generate wavetable samples with per-sample pitch modulation
        self._generate_samples_with_mipmap_and_modulation(output, block_size, sample_delta_time)

        # 6. Apply amplitude envelope
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "generate_block"):
                env_buffer = self._work_buffer
                if env_buffer is not None:
                    env.generate_block(env_buffer[:block_size], block_size)
                    output[:, :] *= env_buffer[:block_size, np.newaxis]

        # 6b. Apply soft pedal
        if self._soft_pedal:
            output[:, :] *= 0.6

        # 7. Apply filter with modulation
        self._apply_filter_with_modulation(output, block_size)

        # 8. Apply tremolo and auto-pan
        self._apply_tremolo_and_pan(output, block_size)

        # 9. Apply final volume modulation
        if self._volume_mod != 1.0:
            output[:, :] *= self._volume_mod

        # Check if voice is done
        if "amp_env" in self._envelopes:
            env = self._envelopes["amp_env"]
            if hasattr(env, "is_active") and not env.is_active():
                if self.state == RegionState.RELEASING:
                    self._active = False

        # Update portamento glide
        if (
            self._portamento_active
            and self._portamento_note is not None
            and self._portamento_target is not None
        ):
            glide_increment = sample_delta_time / max(0.001, self._portamento_time)
            self._portamento_glide_phase = min(
                1.0, self._portamento_glide_phase + glide_increment * block_size
            )

        if output.shape[0] != block_size:
            output = (
                output[:block_size]
                if output.shape[0] > block_size
                else np.vstack(
                    [output, np.zeros((block_size - output.shape[0], 2), dtype=np.float32)]
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

        Uses cached interleaved stereo data for efficiency.

        Args:
            output: Output buffer (stereo interleaved)
            block_size: Number of stereo frames
            sample_delta_time: Time per sample in seconds
        """
        if self._sample_data is None or len(self._sample_data) == 0:
            return

        mip_level = self._select_mip_map_level()
        mip_data = self._get_mip_map_data(mip_level)

        if mip_data is None or len(mip_data) == 0:
            return

        decimation_factor = 2**mip_level
        mip_sample_length = len(mip_data)

        pos = self._sample_position / decimation_factor
        loop_start_mip = self._loop_start / decimation_factor
        loop_end_mip = self._loop_end / decimation_factor
        base_phase_step_mip = self._base_phase_step / decimation_factor
        crossfade_len = self._loop_crossfade_samples / decimation_factor

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

            # Handle loop crossfade
            if crossfade_len > 0 and loop_end_mip > loop_start_mip:
                if loop_start_mip <= pos < loop_end_mip:
                    dist_to_end = loop_end_mip - pos
                    if dist_to_end < crossfade_len:
                        fade = 0.5 * (1.0 + np.cos(np.pi * dist_to_end / crossfade_len))
                        sample_left *= fade
                        sample_right *= fade

            # Handle SF2 looping in mip space
            if self._reverse_playback:
                pos = pos - phase_step
                if pos < loop_start_mip:
                    pos = loop_end_mip - (loop_start_mip - pos)
            else:
                pos = self._handle_sf2_looping_mip(
                    pos + phase_step,
                    mip_sample_length,
                    loop_start_mip,
                    loop_end_mip,
                )

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

        # Store position back in base sample space
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
        import math

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
            return self._sample_data

        if mip_level == self._cached_mip_level and self._cached_mip_data is not None:
            return self._cached_mip_data

        mip_data = self.soundfont_manager.get_mip_map_sample_data(
            self.descriptor.sample_id, mip_level
        )

        if mip_data is not None:
            self._cached_mip_level = mip_level
            self._cached_mip_data = mip_data
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
            # Loop and continue
            if self._loop_start <= position < self._loop_end:
                if position >= self._loop_end:
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
            # Loop and continue
            if loop_start <= position < loop_end:
                if position >= loop_end:
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
