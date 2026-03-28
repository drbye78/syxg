"""
XG Voice - Refactored with lazy region selection.

Part of the unified region-based synthesis architecture.
Voice stores preset definition (all region descriptors) and creates
region instances at note-on time based on note/velocity matching.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ..engine.preset_info import PresetInfo
from ..engine.region_descriptor import RegionDescriptor
from ..engine.synthesis_engine import SynthesisEngine
from ..partial.region import IRegion

logger = logging.getLogger(__name__)


class Voice:
    """
    Refactored Voice with lazy region selection.

    Stores preset definition (all region descriptors).
    Creates region instances at note-on time based on note/velocity.

    This is the KEY class that fixes multi-zone presets:
    - Old: Voice created with fixed partials for note 60 only
    - New: Voice stores ALL regions, selects at note-on time

    Attributes:
        preset_info: Preset metadata with all region descriptors
        engine: Synthesis engine for this voice
        channel: MIDI channel number
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_active_instances",
        "_articulation",
        "_chorus_send",
        "_master_level",
        "_master_pan",
        "_region_cache",
        "_reverb_send",
        "_round_robin_state",
        "channel",
        "engine",
        "preset_info",
        "sample_rate",
    ]

    def __init__(
        self, preset_info: PresetInfo, engine: SynthesisEngine, channel: int, sample_rate: int
    ):
        """
        Initialize Voice with preset definition.

        Args:
            preset_info: Preset metadata with all region descriptors
            engine: Synthesis engine for this voice
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz
        """
        self.preset_info = preset_info
        self.engine = engine
        self.channel = channel
        self.sample_rate = sample_rate

        # Active region instances for current note
        self._active_instances: list[IRegion] = []

        # Optional: cache of recently used region instances
        self._region_cache: dict[int, IRegion] = {}

        # Round-robin state per group
        self._round_robin_state: dict[int, int] = {}

        # Voice-level parameters (from preset)
        self._master_level = preset_info.master_level
        self._master_pan = preset_info.master_pan
        self._reverb_send = preset_info.reverb_send
        self._chorus_send = preset_info.chorus_send

        # S.Art2 articulation support
        self._articulation = "normal"

    # ========== REGION SELECTION (KEY METHOD) ==========

    def get_regions_for_note(self, note: int, velocity: int) -> list[IRegion]:
        """
        Get region instances for a specific note/velocity.

        This is the KEY method that fixes multi-zone presets.
        Called at note-on time, not at Voice creation time.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of region instances that should play for this note/velocity
        """
        # Get matching descriptors from preset info
        matching_descriptors = self.preset_info.get_matching_descriptors(note, velocity)

        if not matching_descriptors:
            return []

        # Apply round-robin selection
        selected_descriptors = self._apply_round_robin(matching_descriptors, note, velocity)

        # Create region instances
        regions = []
        for descriptor in selected_descriptors:
            region = self._get_or_create_region(descriptor)
            regions.append(region)

        return regions

    def _apply_round_robin(
        self, descriptors: list[RegionDescriptor], note: int, velocity: int
    ) -> list[RegionDescriptor]:
        """
        Apply round-robin selection to descriptors.

        Args:
            descriptors: Matching region descriptors
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Selected descriptors after round-robin
        """
        # Group by round-robin group
        rr_groups: dict[int, list[RegionDescriptor]] = {}
        for d in descriptors:
            rr_id = d.round_robin_group
            if rr_id not in rr_groups:
                rr_groups[rr_id] = []
            rr_groups[rr_id].append(d)

        # Select one from each round-robin group
        selected = []
        for group_id, group_descriptors in rr_groups.items():
            if len(group_descriptors) == 1:
                selected.append(group_descriptors[0])
            else:
                # Round-robin selection - with bounds check
                current_pos = self._round_robin_state.get(group_id, 0)
                # Ensure position is valid for current group size
                if current_pos >= len(group_descriptors):
                    current_pos = 0
                selected.append(group_descriptors[current_pos])

                # Advance position for next note
                next_pos = (current_pos + 1) % len(group_descriptors)
                self._round_robin_state[group_id] = next_pos

        return selected

    def _get_or_create_region(self, descriptor: RegionDescriptor) -> IRegion:
        """
        Get or create region for descriptor.

        Args:
            descriptor: Region descriptor

        Returns:
            Region instance ready for initialization
        """
        # Try cache first (optional optimization)
        if descriptor.region_id in self._region_cache:
            region = self._region_cache[descriptor.region_id]
            # Reset region state for reuse
            region.reset()
            return region

        # Create new region using engine
        try:
            region = self.engine.create_region(descriptor, self.sample_rate)

            # Optional: cache for reuse
            # self._region_cache[descriptor.region_id] = region

            return region

        except Exception as e:
            logger.error(f"Failed to create region: {e}")
            # Return a silent dummy region
            return _create_silent_region(descriptor, self.sample_rate)

    # ========== PLAYBACK ==========

    def note_on(self, note: int, velocity: int) -> list[IRegion]:
        """
        Trigger note-on for all matching regions.

        Args:
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            List of activated regions
        """
        # Get regions for this note/velocity
        regions = self.get_regions_for_note(note, velocity)

        if not regions:
            return []

        # Trigger note-on for all regions
        activated = []
        for region in regions:
            try:
                if region.note_on(velocity, note):
                    activated.append(region)
            except Exception as e:
                logger.error(f"Region note_on failed: {e}")

        self._active_instances = activated
        return activated

    def note_off(self, note: int) -> None:
        """
        Trigger note-off for active regions.

        Args:
            note: MIDI note number
        """
        for region in self._active_instances:
            try:
                region.note_off()
            except Exception as e:
                logger.error(f"Region note_off failed: {e}")

    def is_note_supported(self, note: int) -> bool:
        """
        Check if this voice supports the given note.

        Args:
            note: MIDI note number

        Returns:
            True if any region supports this note
        """
        # Check if any region descriptor matches this note
        for descriptor in self.preset_info.region_descriptors:
            if descriptor.should_play_for_note(note, 64):  # Assume medium velocity
                return True
        return False

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from all active regions.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        if not self._active_instances:
            return np.zeros(block_size * 2, dtype=np.float32)

        output = np.zeros(block_size * 2, dtype=np.float32)

        for region in self._active_instances:
            if region.is_active():
                try:
                    # Update modulation
                    region.update_modulation(modulation)

                    # Generate samples
                    samples = region.generate_samples(block_size, modulation)

                    # Apply region gain (crossfades, velocity scaling)
                    gain = self._calculate_region_gain(region)
                    if gain != 1.0:
                        samples *= gain

                    output += samples

                except Exception as e:
                    logger.error(f"Region sample generation failed: {e}")

        # Clean up inactive regions
        self._active_instances = [r for r in self._active_instances if r.is_active()]

        # Apply master level
        if self._master_level != 1.0:
            output *= self._master_level

        return output

    def _calculate_region_gain(self, region: IRegion) -> float:
        """
        Calculate gain for region (crossfades, velocity scaling).

        Args:
            region: Region instance

        Returns:
            Gain multiplier (0.0 to 1.0)
        """
        # Default implementation returns 1.0
        # Can be overridden for crossfade support
        return 1.0

    # ========== PARAMETER UPDATES ==========

    def set_master_level(self, level: float) -> None:
        """Set master output level (0.0-1.0)."""
        self._master_level = max(0.0, min(1.0, level))

    def set_master_pan(self, pan: float) -> None:
        """Set master pan position (-1.0 to 1.0)."""
        self._master_pan = max(-1.0, min(1.0, pan))

    def set_effects_sends(self, reverb: float | None = None, chorus: float | None = None) -> None:
        """Set effects send levels."""
        if reverb is not None:
            self._reverb_send = max(0.0, min(1.0, reverb))
        if chorus is not None:
            self._chorus_send = max(0.0, min(1.0, chorus))

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation for all active regions.

        Args:
            modulation: Modulation parameter updates
        """
        for region in self._active_instances:
            region.update_modulation(modulation)

    # ========== UTILITY METHODS ==========

    def is_active(self) -> bool:
        """Check if voice has any active regions."""
        return any(r.is_active() for r in self._active_instances)

    def get_active_region_count(self) -> int:
        """Get number of currently active regions."""
        return len(self._active_instances)

    def get_region_info(self) -> list[dict[str, Any]]:
        """Get information about active regions."""
        return [r.get_region_info() for r in self._active_instances]

    def get_preset_name(self) -> str:
        """Get preset name."""
        return self.preset_info.name

    def get_engine_type(self) -> str:
        """Get engine type."""
        return self.preset_info.engine_type

    def has_key_splits(self) -> bool:
        """Check if preset has key splits."""
        return self.preset_info.has_key_splits()

    def has_velocity_splits(self) -> bool:
        """Check if preset has velocity splits."""
        return self.preset_info.has_velocity_splits()

    def get_region_count(self) -> int:
        """Get total number of regions in preset."""
        return self.preset_info.get_region_count()

    # ========== S.Art2 ARTICULATION CONTROL ==========

    def set_articulation(self, articulation: str) -> None:
        """
        Set articulation for this voice.

        Args:
            articulation: Articulation name
        """
        self._articulation = articulation

        # Propagate to all active regions
        for region in self._active_instances:
            if hasattr(region, "set_articulation"):
                region.set_articulation(articulation)

    def get_articulation(self) -> str:
        """Get current articulation."""
        return self._articulation

    # ========== RESOURCE MANAGEMENT ==========

    def reset(self) -> None:
        """Reset voice state (for reuse)."""
        # Release all active regions
        for region in self._active_instances:
            region.dispose()
        self._active_instances.clear()

        # Reset round-robin state
        self._round_robin_state.clear()

        # Reset parameters to preset defaults
        self._master_level = self.preset_info.master_level
        self._master_pan = self.preset_info.master_pan
        self._reverb_send = self.preset_info.reverb_send
        self._chorus_send = self.preset_info.chorus_send

        # Reset articulation
        self._articulation = "normal"

    def dispose(self) -> None:
        """Release all region resources."""
        self.reset()

        # Clear cache
        for region in self._region_cache.values():
            region.dispose()
        self._region_cache.clear()

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Voice(preset='{self.preset_info.name}', "
            f"engine={self.preset_info.engine_type}, "
            f"regions={self.preset_info.get_region_count()}, "
            f"active={len(self._active_instances)})"
        )

    def __repr__(self) -> str:
        return self.__str__()


def _create_silent_region(descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
    """
    Create a silent region for error handling.

    Returns a region that generates silence when region creation fails.
    """
    from ..partial.region import IRegion

    class SilentRegion(IRegion):
        def _load_sample_data(self) -> np.ndarray | None:
            return None

        def _create_partial(self) -> Any | None:
            return None

        def _init_envelopes(self) -> None:
            pass

        def _init_filters(self) -> None:
            pass

        def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
            return np.zeros(block_size * 2, dtype=np.float32)

    return SilentRegion(descriptor, sample_rate)
