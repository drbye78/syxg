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
        super().__init__(base_region.descriptor, sample_rate)

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

        1. Generate samples from base region
        2. Apply articulation-specific sample modification
        3. Apply articulation parameters to synthesis
        4. Return processed samples

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Step 1: Generate from base region
        samples = self.base_region.generate_samples(block_size, modulation)

        # Step 2: Get current articulation and parameters
        articulation = self.get_articulation()
        params = self.get_articulation_params()

        # Step 3: Apply articulation processing if not normal
        if articulation != "normal" and self._sample_modifier:
            samples = self._sample_modifier.apply_articulation(samples, articulation, params)

        # Step 4: Apply articulation parameters to modulation
        self._apply_articulation_to_modulation(params, modulation)

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

        Different articulations affect note-on behavior:
        - staccato: Shorter envelope release
        - accented: Higher velocity
        - legato: Smooth parameter transitions
        """
        articulation = self.get_articulation()
        params = self.get_articulation_params()

        # Apply articulation-specific processing
        if articulation == "staccato":
            # Shorten release time for short, detached notes
            self._set_base_param("amp_release", 0.05)

        elif articulation == "legato":
            # Enable smooth transitions between notes
            self._set_base_param("transition_time", 0.05)

        elif articulation == "accented":
            # Boost velocity for accented notes
            self._set_base_param("velocity_boost", 1.2)

        elif articulation == "pizzicato":
            # Very short decay for plucked strings
            self._set_base_param("amp_decay", 0.05)
            self._set_base_param("amp_release", 0.02)

        elif articulation == "marcato":
            # Strong accent with quick decay
            self._set_base_param("velocity_boost", 1.3)
            self._set_base_param("amp_decay", 0.1)

    def _apply_note_off_articulation(self) -> None:
        """
        Apply articulation-specific note-off processing.

        Different articulations affect note-off behavior:
        - key_off: Add key-off noise
        - staccato: Immediate release
        """
        articulation = self.get_articulation()

        if articulation == "key_off":
            # Add key-off noise (finger lifting off key)
            pass

        elif articulation == "staccato":
            # Already handled by shortened release
            pass

    def _apply_articulation_to_modulation(
        self, params: dict[str, Any], modulation: dict[str, float]
    ) -> None:
        """
        Apply articulation parameters to modulation values.

        This method maps articulation parameters to synthesis parameters:
        - vibrato: rate, depth → LFO modulation
        - trill: interval, rate → Pitch modulation
        - crescendo: target_level, duration → Volume envelope
        """
        # Vibrato/Tremolo
        if "rate" in params and "depth" in params:
            modulation["vibrato_rate"] = params.get("rate", 5.0)
            modulation["vibrato_depth"] = params.get("depth", 0.05)

        # Trill
        if "interval" in params and "rate" in params:
            # Apply trill pitch modulation
            modulation["trill_interval"] = params.get("interval", 2)
            modulation["trill_rate"] = params.get("rate", 6.0)

        # Crescendo/Diminuendo
        if "target_level" in params and "duration" in params:
            # Apply dynamic change over time
            modulation["crescendo_target"] = params.get("target_level", 1.0)
            modulation["crescendo_duration"] = params.get("duration", 1.0)

        # Growl/Flutter (modulation effects)
        if "mod_freq" in params and "mod_depth" in params:
            modulation["growl_freq"] = params.get("mod_freq", 25.0)
            modulation["growl_depth"] = params.get("mod_depth", 0.25)

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
