"""
Region Descriptor - Lightweight region metadata for lazy initialization.

Part of the unified region-based synthesis architecture.
RegionDescriptor contains all metadata needed to identify and match regions
without loading sample data or creating region instances.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple


@dataclass(slots=True)
class RegionDescriptor:
    """
    Lightweight region metadata - no sample data loaded.
    
    Created at program change, stored in Voice.
    Used to determine which regions should play for a note.
    
    Attributes:
        region_id: Unique identifier for this region within a preset
        engine_type: Type of synthesis engine ('sf2', 'fm', 'additive', etc.)
        key_range: MIDI note range (low, high) this region responds to
        velocity_range: Velocity range (low, high) this region responds to
        round_robin_group: Group ID for round-robin alternation
        round_robin_position: Position within round-robin sequence
        sequence_position: Position in sequence chain
        sample_id: Sample identifier (SF2/SFZ only, None for algorithmic)
        sample_path: Sample file path (SFZ only)
        algorithm_params: Algorithm parameters (FM, Additive, etc.)
        generator_params: Common generator parameters (envelopes, filters, etc.)
        is_sample_loaded: Whether sample data has been loaded
    """
    
    # Identification
    region_id: int
    engine_type: str
    
    # Matching criteria
    key_range: Tuple[int, int] = (0, 127)
    velocity_range: Tuple[int, int] = (0, 127)
    
    # Round robin / sequence
    round_robin_group: int = 0
    round_robin_position: int = 0
    sequence_position: int = 0
    
    # Sample reference (SF2/SFZ only)
    sample_id: Optional[int] = None
    sample_path: Optional[str] = None
    
    # Algorithm parameters (FM, Additive, etc.)
    algorithm_params: Optional[Dict[str, Any]] = None
    
    # Generator parameters (common)
    generator_params: Dict[str, Any] = field(default_factory=dict)
    
    # Loading state
    is_sample_loaded: bool = False
    
    # ========== MATCHING METHODS ==========
    
    def should_play_for_note(self, note: int, velocity: int) -> bool:
        """
        Check if this region should play for given note and velocity.
        
        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
        
        Returns:
            True if region should play for this note/velocity combination
        """
        return (
            self.key_range[0] <= note <= self.key_range[1] and
            self.velocity_range[0] <= velocity <= self.velocity_range[1]
        )
    
    def get_priority_score(self, note: int, velocity: int) -> float:
        """
        Calculate priority score for region selection.
        
        Higher score = region is more appropriate for this note/velocity.
        Used when multiple regions match (velocity crossfades, etc.)
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
        
        Returns:
            Priority score (0.0 to 1.0, higher is better)
        """
        # Calculate distance from center of key/velocity range
        key_center = (self.key_range[0] + self.key_range[1]) / 2
        vel_center = (self.velocity_range[0] + self.velocity_range[1]) / 2
        
        # Score based on distance from center (lower distance = higher score)
        key_distance = abs(note - key_center) / 127.0
        vel_distance = abs(velocity - vel_center) / 127.0
        
        return 1.0 - (key_distance + vel_distance) / 2.0
    
    def get_key_center(self) -> int:
        """Get the center key of this region's key range."""
        return (self.key_range[0] + self.key_range[1]) // 2
    
    def get_velocity_center(self) -> int:
        """Get the center velocity of this region's velocity range."""
        return (self.velocity_range[0] + self.velocity_range[1]) // 2
    
    def is_sample_based(self) -> bool:
        """Check if this is a sample-based region (SF2/SFZ)."""
        return self.sample_id is not None or self.sample_path is not None
    
    def is_algorithmic(self) -> bool:
        """Check if this is an algorithmic region (FM, Additive, etc.)."""
        return self.algorithm_params is not None and self.sample_id is None
    
    def copy(self) -> 'RegionDescriptor':
        """Create a deep copy of this descriptor."""
        return RegionDescriptor(
            region_id=self.region_id,
            engine_type=self.engine_type,
            key_range=self.key_range,
            velocity_range=self.velocity_range,
            round_robin_group=self.round_robin_group,
            round_robin_position=self.round_robin_position,
            sequence_position=self.sequence_position,
            sample_id=self.sample_id,
            sample_path=self.sample_path,
            algorithm_params=(
                self.algorithm_params.copy() 
                if self.algorithm_params else None
            ),
            generator_params=self.generator_params.copy(),
            is_sample_loaded=self.is_sample_loaded
        )
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"RegionDescriptor(id={self.region_id}, type={self.engine_type}, "
            f"key={self.key_range}, vel={self.velocity_range})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()
