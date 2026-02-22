"""
Preset Info - Lightweight preset metadata for lazy initialization.

Part of the unified region-based synthesis architecture.
PresetInfo contains all region descriptors for a preset without loading
sample data or creating region instances.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from .region_descriptor import RegionDescriptor


@dataclass(slots=True)
class PresetInfo:
    """
    Lightweight preset metadata.
    
    Created at program change, stored in Voice.
    Contains all region descriptors but no loaded samples.
    
    Attributes:
        bank: MIDI bank number
        program: MIDI program number
        name: Preset name
        engine_type: Type of synthesis engine
        region_descriptors: All regions for this preset
        master_level: Master output level (0.0-1.0)
        master_pan: Master pan position (-1.0 to 1.0)
        reverb_send: Reverb send level (0.0-1.0)
        chorus_send: Chorus send level (0.0-1.0)
        extra_params: Additional engine-specific parameters
    """
    
    bank: int
    program: int
    name: str
    engine_type: str
    
    # All regions for this preset (not filtered)
    region_descriptors: List[RegionDescriptor]
    
    # Preset-level parameters
    master_level: float = 1.0
    master_pan: float = 0.0
    reverb_send: float = 0.0
    chorus_send: float = 0.0
    
    # Additional engine-specific parameters
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    # ========== REGION SELECTION METHODS ==========
    
    def get_matching_descriptors(
        self, 
        note: int, 
        velocity: int
    ) -> List[RegionDescriptor]:
        """
        Get all region descriptors that match this note/velocity.
        
        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
        
        Returns:
            List of region descriptors that should play for this note/velocity
        """
        return [
            d for d in self.region_descriptors
            if d.should_play_for_note(note, velocity)
        ]
    
    def get_crossfade_groups(
        self, 
        note: int, 
        velocity: int
    ) -> List[List[RegionDescriptor]]:
        """
        Get regions grouped by crossfade zones.
        
        Returns groups of regions that should be crossfaded together.
        Used for velocity crossfades and key crossfades.
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
        
        Returns:
            List of region groups (each group is crossfaded together)
        """
        matching = self.get_matching_descriptors(note, velocity)
        
        if not matching:
            return []
        
        # Group by round-robin group
        # Regions in same RR group alternate, regions in different groups layer
        rr_groups: Dict[int, List[RegionDescriptor]] = {}
        for desc in matching:
            rr_id = desc.round_robin_group
            if rr_id not in rr_groups:
                rr_groups[rr_id] = []
            rr_groups[rr_id].append(desc)
        
        # Each RR group forms a layer (regions within layer may crossfade)
        return list(rr_groups.values())
    
    def get_layered_regions(
        self, 
        note: int, 
        velocity: int
    ) -> List[RegionDescriptor]:
        """
        Get all regions that should play (layered) for this note/velocity.
        
        This is the main method used by Voice to get regions for playback.
        Handles round-robin selection automatically.
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
        
        Returns:
            List of regions to play (after round-robin selection)
        """
        matching = self.get_matching_descriptors(note, velocity)
        
        if not matching:
            return []
        
        # Group by round-robin group and select one from each
        rr_groups: Dict[int, List[RegionDescriptor]] = {}
        for desc in matching:
            rr_id = desc.round_robin_group
            if rr_id not in rr_groups:
                rr_groups[rr_id] = []
            rr_groups[rr_id].append(desc)
        
        # Select one from each RR group (or all if only one in group)
        selected = []
        for rr_id, group in rr_groups.items():
            if len(group) == 1:
                selected.append(group[0])
            else:
                # Sort by priority and take highest
                # (Round-robin selection happens at Voice level with state)
                best = max(
                    group, 
                    key=lambda d: d.get_priority_score(note, velocity)
                )
                selected.append(best)
        
        return selected
    
    def get_region_count(self) -> int:
        """Get total number of regions in this preset."""
        return len(self.region_descriptors)
    
    def get_sample_based_region_count(self) -> int:
        """Get number of sample-based regions (SF2/SFZ)."""
        return sum(1 for d in self.region_descriptors if d.is_sample_based())
    
    def get_algorithmic_region_count(self) -> int:
        """Get number of algorithmic regions (FM, Additive, etc.)."""
        return sum(1 for d in self.region_descriptors if d.is_algorithmic())
    
    def get_key_range(self) -> Tuple[int, int]:
        """
        Get the combined key range of all regions.
        
        Returns:
            Tuple of (lowest_key, highest_key) across all regions
        """
        if not self.region_descriptors:
            return (0, 127)
        
        min_key = min(d.key_range[0] for d in self.region_descriptors)
        max_key = max(d.key_range[1] for d in self.region_descriptors)
        
        return (min_key, max_key)
    
    def get_velocity_range(self) -> Tuple[int, int]:
        """
        Get the combined velocity range of all regions.
        
        Returns:
            Tuple of (lowest_vel, highest_vel) across all regions
        """
        if not self.region_descriptors:
            return (0, 127)
        
        min_vel = min(d.velocity_range[0] for d in self.region_descriptors)
        max_vel = max(d.velocity_range[1] for d in self.region_descriptors)
        
        return (min_vel, max_vel)
    
    def has_velocity_splits(self) -> bool:
        """
        Check if preset has velocity splits (multiple velocity zones).
        
        Returns:
            True if preset has regions with different velocity ranges
        """
        if len(self.region_descriptors) < 2:
            return False
        
        # Check if any regions have overlapping key ranges but different vel ranges
        for i, d1 in enumerate(self.region_descriptors):
            for d2 in self.region_descriptors[i+1:]:
                # Overlapping key ranges?
                keys_overlap = (
                    d1.key_range[0] <= d2.key_range[1] and
                    d2.key_range[0] <= d1.key_range[1]
                )
                # Different velocity ranges?
                vels_different = (
                    d1.velocity_range != d2.velocity_range
                )
                if keys_overlap and vels_different:
                    return True
        
        return False
    
    def has_key_splits(self) -> bool:
        """
        Check if preset has key splits (different samples for different notes).
        
        Returns:
            True if preset has regions with non-overlapping key ranges
        """
        if len(self.region_descriptors) < 2:
            return False
        
        # Check if regions have different key centers
        key_centers = set(d.get_key_center() for d in self.region_descriptors)
        return len(key_centers) > 1
    
    def get_descriptor_by_id(self, region_id: int) -> Optional[RegionDescriptor]:
        """
        Get a specific region descriptor by ID.
        
        Args:
            region_id: Region identifier
        
        Returns:
            RegionDescriptor or None if not found
        """
        for desc in self.region_descriptors:
            if desc.region_id == region_id:
                return desc
        return None
    
    def copy(self) -> 'PresetInfo':
        """Create a deep copy of this preset info."""
        return PresetInfo(
            bank=self.bank,
            program=self.program,
            name=self.name,
            engine_type=self.engine_type,
            region_descriptors=[d.copy() for d in self.region_descriptors],
            master_level=self.master_level,
            master_pan=self.master_pan,
            reverb_send=self.reverb_send,
            chorus_send=self.chorus_send,
            extra_params=self.extra_params.copy()
        )
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"PresetInfo(bank={self.bank}, program={self.program}, "
            f"name='{self.name}', engine={self.engine_type}, "
            f"regions={len(self.region_descriptors)})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()
