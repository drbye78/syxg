"""
S.Art2 Region Wrapper - Universal articulation layer for all synthesis engines.

This module provides the core S.Art2 integration by wrapping any IRegion
implementation with articulation control capabilities.

S.Art2 is synthesis-method agnostic - it works with ANY IRegion implementation
(SF2, FM, Additive, Wavetable, Physical, etc.) to provide expressive
articulation control via NRPN/SYSEX messages.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ....processing.partial.region import IRegion
from .articulation_controller import ArticulationController


class SArt2Region(IRegion):
    """
    S.Art2 wrapper that adds articulation control to ANY base region.

    This is the PRIMARY integration class. It wraps any IRegion implementation
    (SF2Region, FMRegion, AdditiveRegion, etc.) and adds:

    - 35+ articulation types
    - NRPN/SYSEX real-time control
    - Expression parameter mapping
    - Instrument-specific techniques

    Architecture:
        SArt2Region
        ├── ArticulationController (from sart/)
        ├── base_region (any IRegion)
        └── articulation processing pipeline

    Usage:
        # Wrap any region with S.Art2
        base_region = SF2Region(descriptor, sample_rate, manager)
        sart2_region = SArt2Region(base_region)

        # Set articulation via method
        sart2_region.set_articulation('legato')

        # Or via NRPN (real-time MIDI)
        sart2_region.process_nrpn(msb=1, lsb=1)  # Sets 'legato'

        # Generate samples with articulation
        samples = sart2_region.generate_samples(1024, modulation)
    """

    __slots__ = [
        "_articulation_cache",
        "_key_articulations",
        "_key_enabled",
        "_param_transition_buffer",
        "_sample_modifier",
        "_velocity_articulations",
        "_velocity_enabled",
        "articulation_controller",
        "base_region",
    ]

    def __init__(
        self,
        base_region: IRegion,
        sample_rate: int = 44100,
        enable_sample_modification: bool = True,
    ):
        """
        Initialize S.Art2 wrapper.

        Args:
            base_region: Any IRegion implementation to wrap
            sample_rate: Audio sample rate in Hz
            enable_sample_modification: Enable articulation sample processing
        """
        super().__init__(descriptor=base_region.descriptor, sample_rate=sample_rate)

        self.base_region = base_region
        self.articulation_controller = ArticulationController()
        self._sample_modifier = None
        self._articulation_cache: dict[str, Any] = {}
        self._param_transition_buffer: dict[str, Any] = {}

        # Velocity-based articulation switching
        self._velocity_articulations: dict[tuple, str] = {}
        self._velocity_enabled = False

        # Key-based articulation switching
        self._key_articulations: dict[tuple, str] = {}
        self._key_enabled = False

        if enable_sample_modification:
            try:
                from .modifiers import SF2SampleModifier

                self._sample_modifier = SF2SampleModifier(sample_rate)
            except ImportError:
                # SF2 modules not available - sample modification disabled
                pass

    # ========== ARTICULATION CONTROL ==========

    def set_articulation(self, articulation: str) -> None:
        """
        Set current articulation.

        Args:
            articulation: Articulation name (e.g., 'legato', 'staccato', 'growl')
        """
        self.articulation_controller.set_articulation(articulation)
        self._invalidate_cache()

    def get_articulation(self) -> str:
        """Get current articulation name."""
        return self.articulation_controller.get_articulation()

    def process_nrpn(self, msb: int, lsb: int) -> str:
        """
        Process NRPN message to set articulation.

        Args:
            msb: NRPN MSB value (0-127)
            lsb: NRPN LSB value (0-127)

        Returns:
            Articulation name that was set
        """
        articulation = self.articulation_controller.process_nrpn(msb, lsb)
        self._invalidate_cache()
        return articulation

    def process_sysex(self, sysex_data: bytes) -> dict[str, Any]:
        """
        Process SYSEX message for articulation control.

        Args:
            sysex_data: SYSEX byte data

        Returns:
            SYSEX parsing result dictionary
        """
        result = self.articulation_controller.parse_sysex(sysex_data)

        if result["command"] == "set_articulation":
            self.set_articulation(result["articulation"])

        return result

    def get_available_articulations(self) -> list[str]:
        """Get list of all available articulations."""
        return self.articulation_controller.get_available_articulations()

    def get_articulation_params(self) -> dict[str, Any]:
        """Get parameters for current articulation."""
        articulation = self.get_articulation()

        # Check cache first
        if articulation in self._articulation_cache:
            return self._articulation_cache[articulation]

        # Get from controller and cache
        params = self.articulation_controller.get_articulation_params()
        self._articulation_cache[articulation] = params
        return params

    def set_articulation_param(self, param: str, value: Any) -> None:
        """
        Set parameter for current articulation.

        Args:
            param: Parameter name (e.g., 'rate', 'depth', 'blend')
            value: Parameter value
        """
        self.articulation_controller.set_articulation_param(param, value)
        self._invalidate_cache()

    # ========== VELOCITY-BASED ARTICULATION SWITCHING ==========

    def set_velocity_articulation(self, vel_low: int, vel_high: int, articulation: str) -> None:
        """
        Set articulation for velocity range.

        Args:
            vel_low: Low velocity bound (0-127)
            vel_high: High velocity bound (0-127)
            articulation: Articulation name

        Example:
            region.set_velocity_articulation(0, 64, 'soft')
            region.set_velocity_articulation(65, 100, 'medium')
            region.set_velocity_articulation(101, 127, 'hard')
        """
        vel_low = max(0, min(127, vel_low))
        vel_high = max(0, min(127, vel_high))

        if vel_low > vel_high:
            vel_low, vel_high = vel_high, vel_low

        self._velocity_articulations[(vel_low, vel_high)] = articulation
        self._velocity_enabled = True

    def clear_velocity_articulations(self) -> None:
        """Clear all velocity-based articulations."""
        self._velocity_articulations.clear()
        self._velocity_enabled = False

    def _get_articulation_for_velocity(self, velocity: int) -> str | None:
        """Get articulation for velocity."""
        for (vel_low, vel_high), articulation in self._velocity_articulations.items():
            if vel_low <= velocity <= vel_high:
                return articulation
        return None

    # ========== KEY-BASED ARTICULATION SWITCHING ==========

    def set_key_articulation(self, key_low: int, key_high: int, articulation: str) -> None:
        """
        Set articulation for key range.

        Args:
            key_low: Low key bound (0-127)
            key_high: High key bound (0-127)
            articulation: Articulation name

        Example:
            region.set_key_articulation(0, 47, 'bass')
            region.set_key_articulation(48, 83, 'mid')
            region.set_key_articulation(84, 127, 'treble')
        """
        key_low = max(0, min(127, key_low))
        key_high = max(0, min(127, key_high))

        if key_low > key_high:
            key_low, key_high = key_high, key_low

        self._key_articulations[(key_low, key_high)] = articulation
        self._key_enabled = True

    def clear_key_articulations(self) -> None:
        """Clear all key-based articulations."""
        self._key_articulations.clear()
        self._key_enabled = False

    def _get_articulation_for_key(self, note: int) -> str | None:
        """Get articulation for key."""
        for (key_low, key_high), articulation in self._key_articulations.items():
            if key_low <= note <= key_high:
                return articulation
        return None

    # ========== ENHANCED NOTE-ON WITH VELOCITY/KEY SWITCHING ==========

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on with velocity and key-based articulation switching.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)

        Returns:
            True if note was triggered
        """
        # Apply velocity-based articulation if enabled
        if self._velocity_enabled:
            velocity_art = self._get_articulation_for_velocity(velocity)
            if velocity_art:
                self.set_articulation(velocity_art)

        # Apply key-based articulation if enabled
        if self._key_enabled:
            key_art = self._get_articulation_for_key(note)
            if key_art:
                self.set_articulation(key_art)

        # Call base region note_on
        result = self.base_region.note_on(velocity, note)

        if result:
            # Apply articulation-specific processing
            self._apply_note_on_articulation(velocity, note)

        return result

    # ========== IRegion INTERFACE ==========

    def initialize(self) -> bool:
        """Initialize base region and S.Art2 processing."""
        return self.base_region.initialize()

    def note_off(self) -> None:
        """Trigger note-off with articulation release."""
        self.base_region.note_off()
        self._apply_note_off_articulation()

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples with S.Art2 articulation processing.

        This is the CORE method where articulation affects synthesis:

        1. Apply articulation parameters to modulation dict FIRST
           (so the base engine uses them during synthesis)
        2. Generate samples from base region
        3. Apply articulation-specific sample modification (DSP layer)
        4. Return processed samples

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values (modified in-place)

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Step 1: Get current articulation and parameters
        articulation = self.get_articulation()
        params = self.get_articulation_params()

        # Step 2: Apply articulation params to modulation BEFORE base engine
        # generates samples — this is how articulations like legato, staccato,
        # pizzicato actually affect synthesis (envelopes, filter, LFO).
        self._apply_articulation_to_modulation(params, modulation)

        # Step 3: Generate from base region (sees the updated modulation)
        samples = self.base_region.generate_samples(block_size, modulation)

        # Step 4: Apply articulation DSP processing if not normal
        if articulation != "normal" and self._sample_modifier:
            samples = self._sample_modifier.apply_articulation(samples, articulation, params)

        return samples

    def is_active(self) -> bool:
        """Check if region is still producing sound."""
        return self.base_region.is_active()

    def reset(self) -> None:
        """Reset region and articulation state."""
        self.base_region.reset()
        self.articulation_controller.reset()
        self._invalidate_cache()

    def dispose(self) -> None:
        """Dispose of region resources."""
        self.base_region.dispose()
        self._sample_modifier = None
        self._articulation_cache.clear()
        self._param_transition_buffer.clear()

    def get_region_info(self) -> dict[str, Any]:
        """Get region information including articulation state."""
        info = self.base_region.get_region_info()
        info["articulation"] = self.get_articulation()
        info["articulation_params"] = self.get_articulation_params()
        info["sart2_enabled"] = True
        return info

    # ========== IRegion ABSTRACT METHODS (delegated to base_region) ==========

    def _load_sample_data(self) -> np.ndarray | None:
        """Delegate to base region."""
        if hasattr(self.base_region, "_load_sample_data"):
            return self.base_region._load_sample_data()
        return None

    def _create_partial(self) -> Any | None:
        """Delegate to base region."""
        if hasattr(self.base_region, "_create_partial"):
            return self.base_region._create_partial()
        return None

    def _init_envelopes(self) -> None:
        """Delegate to base region."""
        if hasattr(self.base_region, "_init_envelopes"):
            self.base_region._init_envelopes()

    def _init_filters(self) -> None:
        """Delegate to base region."""
        if hasattr(self.base_region, "_init_filters"):
            self.base_region._init_filters()

    # ========== INTERNAL METHODS ==========

    def _invalidate_cache(self) -> None:
        """Invalidate articulation parameter cache."""
        self._articulation_cache.clear()

    def _apply_note_on_articulation(self, velocity: int, note: int) -> None:
        """
        Apply articulation-specific note-on processing.

        Sets persistent base region parameters at note-on time.
        These differ from the modulation-dict updates (per-block) in that
        they persist for the entire note's lifetime unless explicitly
        changed later.

        Articulation categories:
        - Envelope-shaping: staccato, pizzicato, marcato, dead_note, swell
        - LFO / modulation: vibrato, tremolo, growl, flutter, trill
        - Filter/timbre: palm_mute, sul_ponticello, harmonics, con_sordino
        - Dynamics: accented, marcato, crescendo, diminuendo
        - Transition: legato, portamento
        """
        articulation = self.get_articulation()
        params = self.get_articulation_params()

        # ---- Envelope-shaping articulations ----
        if articulation == "staccato":
            # Short, detached note
            self._set_base_param("amp_release", 0.05)

        elif articulation == "pizzicato":
            # Plucked string — very short decay and release
            self._set_base_param("amp_decay", 0.05)
            self._set_base_param("amp_release", 0.02)

        elif articulation == "marcato":
            # Strong accent with quick decay
            self._set_base_param("velocity_boost", 1.3)
            self._set_base_param("amp_decay", 0.1)

        elif articulation == "dead_note":
            # Damped note — instant decay
            self._set_base_param("amp_decay", 0.01)
            self._set_base_param("amp_release", 0.005)

        elif articulation == "swell":
            # Gradual fade-in
            attack_param = params.get("attack", 0.1)
            self._set_base_param("amp_attack", attack_param)

        # ---- Transition / legato articulations ----
        elif articulation == "legato":
            # Smooth transition between notes
            transition = params.get("transition_time", 0.05)
            self._set_base_param("transition_time", transition)

        elif articulation == "portamento":
            # Pitch glide between notes
            port_time = params.get("speed", 0.05)
            self._set_base_param("portamento_time", port_time)

        # ---- Dynamic / accent articulations ----
        elif articulation == "accented":
            # Boosted velocity
            self._set_base_param("velocity_boost", 1.2)

        elif articulation == "crescendo":
            # Start quiet — target level applied via modulation
            self._set_base_param("velocity_boost", 0.5)

        elif articulation == "diminuendo":
            # Start at full level — target level applied via modulation
            pass

        # ---- Vibrato / LFO articulations ----
        elif articulation == "vibrato":
            # Set LFO parameters for vibrato effect
            rate = params.get("rate", 5.0)
            depth = params.get("depth", 0.5)
            self._set_base_param("vibrato_rate", rate)
            self._set_base_param("vibrato_depth", depth)

        elif articulation == "tremolo":
            # Amplitude modulation LFO
            rate = params.get("rate", 6.0)
            depth = params.get("depth", 0.5)
            self._set_base_param("tremolo_rate", rate)
            self._set_base_param("tremolo_depth", depth)

        elif articulation == "trill":
            # Pitch alternation — set up rapid LFO
            trill_rate = params.get("rate", 8.0)
            interval = params.get("interval", 2)
            self._set_base_param("vibrato_rate", trill_rate)
            self._set_base_param("vibrato_depth", interval * 0.5)

        elif articulation == "growl":
            # Low-frequency growl modulation
            mod_freq = params.get("mod_freq", 25.0)
            depth = params.get("depth", 0.25)
            self._set_base_param("growl_freq", mod_freq)
            self._set_base_param("growl_depth", depth)

        elif articulation == "flutter":
            # Fast flutter modulation
            rate = params.get("mod_freq", 12.0)
            depth = params.get("depth", 0.15)
            self._set_base_param("tremolo_rate", rate)
            self._set_base_param("tremolo_depth", depth)

        # ---- Filter / timbre articulations ----
        elif articulation == "palm_mute":
            # Dampened string sound
            self._set_base_param("filter_cutoff", 0.3)
            self._set_base_param("volume", 0.6)

        elif articulation == "sul_ponticello":
            # Bright, scratchy sound
            self._set_base_param("filter_cutoff", 1.5)  # Boost cutoff

        elif articulation == "harmonics":
            # Natural harmonics — brighter
            self._set_base_param("filter_cutoff", 1.3)

        elif articulation == "con_sordino":
            # Muted (violin mute) — darker
            mute_amount = params.get("mute_level", 0.5)
            self._set_base_param("filter_cutoff", max(0.1, 1.0 - mute_amount))

        # ---- Fallback: voice param from params dict ----
        else:
            # Generic: forward known synthesis params to base region
            for key in ("amp_attack", "amp_decay", "amp_release",
                        "filter_cutoff", "filter_resonance",
                        "vibrato_rate", "vibrato_depth",
                        "volume", "velocity_boost"):
                if key in params:
                    self._set_base_param(key, params[key])

    def _apply_note_off_articulation(self) -> None:
        """
        Apply articulation-specific note-off processing.

        Called when a note-off is received. Some articulations
        need specific release behavior:
        - staccato: Already handled by shortened release in note_on
        - key_off: Could add key-off noise (finger noise)
        """
        articulation = self.get_articulation()

        if articulation == "staccato":
            # Already handled by shortened release — nothing extra needed
            pass

        elif articulation == "key_off":
            # Key-off click/noise would go here
            pass

    def _apply_articulation_to_modulation(
        self, params: dict[str, Any], modulation: dict[str, float]
    ) -> None:
        """
        Apply articulation parameters to modulation values.

        This is the SYNTHESIS PARAMETER ROUTING path of the two-path architecture.
        It maps articulation parameters to modulation keys that the base engine
        (SF2Region) consumes directly — affecting envelope, filter, vibrato LFO,
        volume, pan, and effect sends.

        The complementary DSP path (post-hoc sample manipulation) runs after
        base_region.generate_samples() via self._sample_modifier.apply_articulation().

        Key modulation destinations (consumed by sf2_region.py):
          gs_vibrato_rate / gs_vibrato_depth / gs_vibrato_delay
          gs_filter_cutoff / gs_filter_resonance
          gs_amp_attack / gs_amp_decay / gs_amp_release
          gs_volume / gs_pan
          gs_reverb_send / gs_chorus_send
        """
        # Fast path: no articulation parameters to route (e.g. "normal" articulation)
        if not params:
            return

        # ---- Vibrato LFO (gs_vibrato_* keys) ----
        rate = params.get("rate")
        depth = params.get("depth")
        if rate is not None:
            modulation["gs_vibrato_rate"] = float(rate)
        if depth is not None:
            # Scale depth 0-1 → 0-1.0 for gs consumption
            modulation["gs_vibrato_depth"] = float(depth)
        delay = params.get("delay")
        if delay is not None:
            modulation["gs_vibrato_delay"] = float(delay)

        # Trill — route interval to synthesis vibrato depth
        interval = params.get("interval")
        trill_rate = params.get("trill_rate", params.get("rate"))
        if interval is not None:
            modulation["gs_vibrato_depth"] = float(interval) * 0.5  # semitones
            if trill_rate is not None:
                modulation["gs_vibrato_rate"] = float(trill_rate)

        # ---- Filter parameters (gs_filter_* keys) ----
        cutoff = params.get("cutoff")
        if cutoff is not None:
            modulation["gs_filter_cutoff"] = float(cutoff)
        resonance = params.get("resonance")
        if resonance is not None:
            modulation["gs_filter_resonance"] = float(resonance)
        # Tone darkness/brightness → filter cutoff adjustment
        darkness = params.get("tone_darkness")
        if darkness is not None:
            modulation["gs_filter_cutoff"] = max(0.0, 1.0 - float(darkness))
        brightness = params.get("tone_brightness")
        if brightness is not None:
            modulation["gs_filter_cutoff"] = min(1.0, float(brightness))
        # Filter sweep endpoints
        cutoff_start = params.get("cutoff_start")
        if cutoff_start is not None:
            modulation["gs_filter_cutoff"] = float(cutoff_start) / 163850.0

        # ---- Volume / dynamics (gs_volume key) ----
        volume = params.get("volume")
        if volume is not None:
            modulation["gs_volume"] = float(volume)
        target_level = params.get("target_level")
        if target_level is not None:
            modulation["gs_volume"] = float(target_level)
        breath_level = params.get("breath_level")
        if breath_level is not None:
            modulation["gs_volume"] = float(breath_level)

        # ---- Pan ----
        pan = params.get("pan")
        if pan is not None:
            modulation["gs_pan"] = float(pan)

        # ---- Effect sends ----
        reverb = params.get("reverb_send")
        if reverb is not None:
            modulation["gs_reverb_send"] = float(reverb)
        chorus = params.get("chorus_send")
        if chorus is not None:
            modulation["gs_chorus_send"] = float(chorus)

        # ---- Stereo width ----
        stereo_width = params.get("stereo_width")
        if stereo_width is not None:
            modulation["stereo_width"] = float(stereo_width)

        # ---- Growl / Flutter (modulation effects also synthesizer-relevant) ----
        mod_freq = params.get("mod_freq")
        mod_depth = params.get("mod_depth", params.get("depth"))
        if mod_freq is not None:
            # Growl is below ~30 Hz — route as LFO modulation to filter cutoff
            # if it's in the sub-audio range
            if float(mod_freq) < 100.0:
                modulation["gs_vibrato_rate"] = float(mod_freq)
                if mod_depth is not None:
                    modulation["gs_vibrato_depth"] = float(mod_depth) * 0.5
            modulation["growl_freq"] = float(mod_freq)
            if mod_depth is not None:
                modulation["growl_depth"] = float(mod_depth)

        # ---- Mute / sordino → filter + volume ----
        mute_level = params.get("mute_level")
        if mute_level is not None:
            # Mute dampens both filter and volume
            modulation["gs_filter_cutoff"] = max(0.05, 1.0 - float(mute_level) * 0.7)
            modulation["gs_volume"] = max(0.1, 1.0 - float(mute_level) * 0.5)
        pressure = params.get("pressure")
        if pressure is not None:
            # Palm mute pressure → darker filter + lower volume
            modulation["gs_filter_cutoff"] = max(0.05, 1.0 - float(pressure))
            modulation["gs_volume"] = max(0.05, 1.0 - float(pressure) * 0.5)

        # ---- Brightness / hardness ----
        hardness = params.get("hardness")
        if hardness is not None:
            modulation["gs_filter_cutoff"] = min(1.0, float(hardness))
        click_level = params.get("click_level")
        if click_level is not None:
            # Click level → brighter attack filter
            modulation["gs_filter_cutoff"] = min(1.0, float(click_level))

    def _set_base_param(self, param: str, value: Any) -> None:
        """
        Set parameter on base region.

        Args:
            param: Parameter name
            value: Parameter value
        """
        if hasattr(self.base_region, "update_parameter"):
            self.base_region.update_parameter(param, value)


class SArt2RegionFactory:
    """
    Factory for creating S.Art2-wrapped regions.

    This factory automatically wraps any region with S.Art2,
    making articulation control universal across all engines.

    Usage:
        factory = SArt2RegionFactory(44100)

        # Wrap existing region
        base_region = SF2Region(descriptor, sample_rate, manager)
        sart2_region = factory.create_sart2_region(base_region)

        # Or create from engine
        region = factory.create_from_engine(descriptor, engine)
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize S.Art2 region factory.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

    def create_sart2_region(self, base_region: IRegion) -> SArt2Region:
        """
        Wrap a base region with S.Art2 articulation.

        Args:
            base_region: Any IRegion implementation

        Returns:
            SArt2Region wrapper with articulation control
        """
        return SArt2Region(base_region, self.sample_rate)

    def create_from_engine(
        self, descriptor: RegionDescriptor, engine: SynthesisEngine
    ) -> SArt2Region:
        """
        Create S.Art2 region from descriptor using engine.

        This method:
        1. Creates base region from engine
        2. Wraps it with S.Art2

        Args:
            descriptor: Region descriptor with parameters
            engine: Synthesis engine to create base region

        Returns:
            SArt2Region wrapper
        """
        # Create base region from engine
        base_region = engine.create_region(descriptor, self.sample_rate)

        # Wrap with S.Art2
        return self.create_sart2_region(base_region)
