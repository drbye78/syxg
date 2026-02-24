"""
XG Voice Instance - Refactored for unified region architecture.

Part of the unified region-based synthesis architecture.
VoiceInstance handles polyphonic playback of a single note with multiple regions.
Refactored to work with IRegion interface.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import time
import logging

from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class VoiceInstance:
    """
    Voice Instance - represents one playing note with multiple regions.
    
    A VoiceInstance is created for each note-on event and manages all regions
    that should play for that specific note/velocity combination.
    
    Refactored to work with IRegion interface from the unified architecture.
    
    Attributes:
        note: MIDI note number
        velocity: MIDI velocity
        channel: MIDI channel number
        sample_rate: Audio sample rate
    """
    
    __slots__ = [
        'note', 'velocity', 'channel', 'sample_rate',
        'regions', 'active_regions', 'start_time',
        'release_triggered', 'released',
        'modulation_state', 'per_note_modulation',
        'master_volume', 'pan', 'transpose',
        'articulation', 'articulation_parameters'
    ]

    def __init__(
        self,
        note: int,
        velocity: int,
        channel: int,
        sample_rate: int,
        articulation: str = 'normal'
    ):
        """
        Initialize VoiceInstance for a specific note.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz
            articulation: Initial articulation (default: 'normal')
        """
        self.note = note
        self.velocity = velocity
        self.channel = channel
        self.sample_rate = sample_rate

        # Region management (now uses IRegion interface)
        self.regions: List[IRegion] = []
        self.active_regions: List[IRegion] = []

        # Timing and state
        self.start_time = time.time()
        self.release_triggered = False
        self.released = False

        # Modulation state (shared across all regions in this voice)
        self.modulation_state: Dict[str, float] = {
            'pitch_bend': 0.0,
            'mod_wheel': 0.0,
            'breath_controller': 0.0,
            'expression': 1.0,
            'channel_aftertouch': 0.0,
            'volume_cc': 1.0,
            'pan': 0.0,
            'brightness': 0.5,
        }

        # Per-note modulation (for MPE/polyphonic expression)
        self.per_note_modulation: Dict[str, float] = {
            'per_note_pitch_bend': 0.0,
            'per_note_expression': 1.0,
            'per_note_brightness': 0.5,
            'per_note_pan': 0.0,
            'per_note_pressure': 0.0,
        }

        # Voice-level parameters
        self.master_volume = 1.0
        self.pan = 0.0
        self.transpose = 0
        
        # S.Art2 articulation support
        self.articulation = articulation
        self.articulation_parameters: Dict[str, float] = {}
    
    def add_region(self, region: IRegion) -> None:
        """
        Add a region to this voice instance.
        
        Args:
            region: Region object (implements IRegion interface)
        """
        self.regions.append(region)
    
    def note_on(self, velocity: int) -> None:
        """
        Trigger note-on for all regions in this voice.
        
        Args:
            velocity: New velocity (for velocity changes during note)
        """
        self.velocity = velocity
        
        for region in self.regions:
            try:
                region.note_on(velocity, self.note)
            except Exception as e:
                logger.error(f"VoiceInstance region note_on failed: {e}")
        
        self.active_regions = self.regions.copy()
    
    def note_off(self, velocity: int = 64) -> None:
        """
        Trigger note-off for all regions in this voice.

        Args:
            velocity: Note-off velocity
        """
        for region in self.active_regions:
            try:
                region.note_off()
            except Exception as e:
                logger.error(f"VoiceInstance region note_off failed: {e}")

        self.release_triggered = True
    
    # ========== S.Art2 ARTICULATION CONTROL ==========
    
    def set_articulation(self, articulation: str, **parameters) -> None:
        """
        Set articulation for this voice instance.
        
        Args:
            articulation: Articulation name
            **parameters: Articulation parameters
        """
        self.articulation = articulation
        self.articulation_parameters.update(parameters)
        
        # Propagate to all regions
        for region in self.regions:
            if hasattr(region, 'set_articulation'):
                region.set_articulation(articulation)
                for param, value in parameters.items():
                    if hasattr(region, 'set_articulation_param'):
                        region.set_articulation_param(param, value)
    
    def get_articulation(self) -> str:
        """Get current articulation."""
        return self.articulation
    
    def get_articulation_parameters(self) -> Dict[str, float]:
        """Get current articulation parameters."""
        return self.articulation_parameters.copy()
    
    def apply_articulation_preset(self, articulation: str, 
                                 parameters: Dict[str, float]) -> None:
        """
        Apply articulation preset.
        
        Args:
            articulation: Articulation name
            parameters: Articulation parameters
        """
        self.set_articulation(articulation, **parameters)
    
    def update_modulation(self, modulation_updates: Dict[str, float]) -> None:
        """
        Update modulation state for this voice.
        
        Args:
            modulation_updates: Dictionary of modulation parameter updates
        """
        self.modulation_state.update(modulation_updates)
        
        # Propagate modulation to all regions
        for region in self.active_regions:
            try:
                region.update_modulation(self.modulation_state)
            except Exception as e:
                logger.error(f"VoiceInstance modulation update failed: {e}")
    
    def update_per_note_modulation(
        self, 
        per_note_updates: Dict[str, float]
    ) -> None:
        """
        Update per-note modulation state for this voice instance.
        
        Args:
            per_note_updates: Dictionary of per-note modulation parameter updates
        """
        self.per_note_modulation.update(per_note_updates)
        
        # Propagate per-note modulation to all regions
        for region in self.active_regions:
            try:
                if hasattr(region, 'update_per_note_modulation'):
                    region.update_per_note_modulation(self.per_note_modulation)
            except Exception as e:
                logger.error(f"Per-note modulation update failed: {e}")
    
    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this voice instance.
        
        Args:
            block_size: Number of samples to generate
        
        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        if not self.active_regions:
            return np.zeros(block_size * 2, dtype=np.float32)
        
        output = np.zeros(block_size * 2, dtype=np.float32)
        active_count = 0
        
        for region in self.active_regions:
            if region.is_active():
                try:
                    # Generate samples from region
                    samples = region.generate_samples(
                        block_size, 
                        self.modulation_state
                    )
                    
                    # Apply region gain (crossfades, velocity scaling)
                    gain = self._calculate_region_gain(region)
                    if gain != 1.0:
                        samples *= gain
                    
                    output += samples
                    active_count += 1
                    
                except Exception as e:
                    logger.error(f"VoiceInstance sample generation failed: {e}")
        
        # Apply master volume
        if self.master_volume != 1.0:
            output *= self.master_volume
        
        # Apply pan
        if self.pan != 0.0:
            pan_left = 1.0 - max(0.0, self.pan)
            pan_right = 1.0 - max(0.0, -self.pan)
            output[::2] *= pan_left    # Left channel
            output[1::2] *= pan_right  # Right channel
        
        # Clean up inactive regions
        self.active_regions = [
            r for r in self.active_regions if r.is_active()
        ]
        
        return output
    
    def _calculate_region_gain(self, region: IRegion) -> float:
        """
        Calculate gain for region (crossfades, velocity scaling).
        
        Args:
            region: Region instance
        
        Returns:
            Gain multiplier (0.0 to 1.0)
        """
        gain = 1.0
        
        # Velocity-based gain
        if hasattr(region, 'current_velocity'):
            vel = region.current_velocity
            # Simple velocity to gain mapping
            gain *= (vel / 127.0) ** 0.3  # Slight compression
        
        # Crossfade gain from region
        if hasattr(region, 'calculate_crossfade_gain'):
            gain *= region.calculate_crossfade_gain(
                self.note, 
                self.velocity
            )
        
        return gain
    
    def is_active(self) -> bool:
        """
        Check if this voice instance is still active.
        
        Returns:
            True if any region is still producing sound
        """
        if not self.active_regions:
            return False
        
        return any(r.is_active() for r in self.active_regions)
    
    def get_active_region_count(self) -> int:
        """Get number of currently active regions."""
        return len(self.active_regions)
    
    def get_region_info(self) -> List[Dict[str, Any]]:
        """Get information about all regions."""
        return [r.get_region_info() for r in self.regions]
    
    def reset(self) -> None:
        """Reset voice instance state."""
        self.regions.clear()
        self.active_regions.clear()
        self.release_triggered = False
        self.released = False
        self.master_volume = 1.0
        self.pan = 0.0
    
    def dispose(self) -> None:
        """Release all region resources."""
        for region in self.regions:
            try:
                region.dispose()
            except Exception as e:
                logger.error(f"VoiceInstance region dispose failed: {e}")
        self.regions.clear()
        self.active_regions.clear()
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"VoiceInstance(note={self.note}, vel={self.velocity}, "
            f"channel={self.channel}, regions={len(self.regions)}, "
            f"active={len(self.active_regions)})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()
