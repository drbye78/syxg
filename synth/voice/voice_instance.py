"""
XG Voice Instance - Represents one playing note with multiple regions.

A VoiceInstance handles polyphonic playback of a single note, managing multiple
regions (SFZ or SF2) that may be triggered simultaneously for that note.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import time

from .voice import Voice
from ..partial.partial import SynthesisPartial


class VoiceInstance:
    """
    XG Voice Instance - represents one playing note with multiple regions.

    A VoiceInstance is created for each note-on event and manages all regions
    that should play for that specific note/velocity combination. This enables
    true polyphony with multiple regions per note (velocity layers, round robin, etc.).

    Key Features:
    - Multiple regions per note (velocity layers, RR groups, etc.)
    - Individual region state management
    - Polyphonic modulation support
    - Release triggering and envelope management
    """

    def __init__(self, note: int, velocity: int, channel: int,
                 sample_rate: int, voice_factory=None):
        """
        Initialize VoiceInstance for a specific note.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz
            voice_factory: Factory for creating voice objects (for compatibility)
        """
        self.note = note
        self.velocity = velocity
        self.channel = channel
        self.sample_rate = sample_rate

        # Region management
        self.regions: List[Any] = []  # List of Region objects (SFZRegion, SF2Region, etc.)
        self.active_regions: List[Any] = []

        # Timing and state
        self.start_time = time.time()
        self.release_triggered = False
        self.released = False

        # Modulation state (shared across all regions in this voice)
        self.modulation_state = {
            'pitch_bend': 0.0,      # Semitones
            'mod_wheel': 0.0,       # 0.0-1.0
            'breath_controller': 0.0,  # 0.0-1.0
            'foot_controller': 0.0,    # 0.0-1.0
            'expression': 1.0,         # 0.0-1.0
            'channel_aftertouch': 0.0, # 0.0-1.0
            'key_aftertouch': 0.0,     # 0.0-1.0 (polyphonic)
            'volume_cc': 1.0,          # 0.0-1.0
            'pan': 0.0,                # -1.0 to 1.0
            'brightness': 0.5,         # 0.0-1.0
            'harmonic_content': 0.5,   # 0.0-1.0
            'tremolo_rate': 4.0,       # Hz
            'tremolo_depth': 0.0,      # 0.0-1.0
        }
        
        # Per-note controller state for MIDI 2.0 (per-note control)
        self.per_note_modulation = {
            'per_note_pitch_bend': 0.0,      # Per-note pitch bend (semitones)
            'per_note_mod_wheel': 0.0,       # Per-note modulation wheel
            'per_note_expression': 1.0,      # Per-note expression
            'per_note_brightness': 0.5,      # Per-note brightness
            'per_note_harmonic_content': 0.5, # Per-note harmonic content
            'per_note_pan': 0.0,             # Per-note pan (-1.0 to 1.0)
            'per_note_pressure': 0.0,        # Per-note pressure (aftertouch)
            'per_note_timbre': 0.0,          # Per-note timbre
            'per_note_custom_1': 0.0,        # Custom per-note parameter 1
            'per_note_custom_2': 0.0,        # Custom per-note parameter 2
        }

        # Voice-level parameters
        self.master_volume = 1.0
        self.pan = 0.0
        self.transpose = 0

        # Legacy compatibility
        self.voice_factory = voice_factory

    def add_region(self, region: Any) -> None:
        """
        Add a region to this voice instance.

        Args:
            region: Region object (SFZRegion, SF2Region, etc.)
        """
        self.regions.append(region)

        # Initialize region if it has an initialization method
        if hasattr(region, 'initialize_for_note'):
            region.initialize_for_note(self.note, self.velocity)

    def note_on(self, velocity: int) -> None:
        """
        Trigger note-on for all regions in this voice.

        Args:
            velocity: New velocity (for velocity changes during note)
        """
        self.velocity = velocity

        for region in self.regions:
            if hasattr(region, 'note_on'):
                region.note_on(velocity, self.note)

        self.active_regions = self.regions.copy()

    def note_off(self, velocity: int = 64) -> None:
        """
        Trigger note-off for all regions in this voice.

        Args:
            velocity: Note-off velocity
        """
        for region in self.active_regions:
            if hasattr(region, 'note_off'):
                region.note_off()

        self.release_triggered = True

    def update_modulation(self, modulation_updates: Dict[str, float]) -> None:
        """
        Update modulation state for this voice.

        Args:
            modulation_updates: Dictionary of modulation parameter updates
        """
        self.modulation_state.update(modulation_updates)

        # Propagate modulation to all regions
        for region in self.active_regions:
            if hasattr(region, 'update_modulation'):
                region.update_modulation(self.modulation_state)

    def update_per_note_modulation(self, per_note_updates: Dict[str, float]) -> None:
        """
        Update per-note modulation state for this voice instance.

        Args:
            per_note_updates: Dictionary of per-note modulation parameter updates
        """
        self.per_note_modulation.update(per_note_updates)

        # Propagate per-note modulation to all regions
        for region in self.active_regions:
            if hasattr(region, 'update_per_note_modulation'):
                region.update_per_note_modulation(self.per_note_modulation)

    def set_per_note_controller(self, controller_name: str, value: float) -> None:
        """
        Set a specific per-note controller value.

        Args:
            controller_name: Name of the per-note controller
            value: Value to set (0.0-1.0 for most controllers)
        """
        if controller_name in self.per_note_modulation:
            self.per_note_modulation[controller_name] = value
        else:
            raise ValueError(f"Unknown per-note controller: {controller_name}")

    def get_per_note_controller(self, controller_name: str) -> float:
        """
        Get the current value of a per-note controller.

        Args:
            controller_name: Name of the per-note controller

        Returns:
            Current value of the controller
        """
        return self.per_note_modulation.get(controller_name, 0.0)

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this voice instance.

        Args:
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active_regions:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Generate samples from all active regions
        voice_output = np.zeros((block_size, 2), dtype=np.float32)
        active_count = 0

        for region in self.active_regions[:]:  # Copy list to allow modification
            if hasattr(region, 'generate_samples'):
                try:
                    # Combine modulation states for this region
                    combined_modulation = self.modulation_state.copy()
                    combined_modulation.update(self.per_note_modulation)
                    
                    region_audio = region.generate_samples(block_size, combined_modulation)

                    # Handle different region output formats
                    if region_audio.ndim == 1:
                        # Mono output - convert to stereo
                        region_audio = np.column_stack([region_audio, region_audio])
                    elif region_audio.shape[1] == 1:
                        # Single channel - duplicate to stereo
                        region_audio = np.column_stack([region_audio[:, 0], region_audio[:, 0]])

                    # Mix region into voice output
                    voice_output += region_audio
                    active_count += 1

                except Exception as e:
                    # Remove faulty region
                    print(f"Warning: Region failed to generate samples: {e}")
                    self.active_regions.remove(region)

        # Apply voice-level processing if we have active regions
        if active_count > 0:
            voice_output = self._apply_voice_processing(voice_output, block_size)

            # Update active regions list (remove completed regions)
            self.active_regions = [r for r in self.active_regions
                                 if hasattr(r, 'is_active') and r.is_active()]

        return voice_output

    def _apply_voice_processing(self, audio: np.ndarray, block_size: int) -> np.ndarray:
        """
        Apply voice-level audio processing.

        Args:
            audio: Input audio buffer
            block_size: Number of samples

        Returns:
            Processed audio buffer
        """
        # Apply master volume
        if self.master_volume != 1.0:
            audio *= self.master_volume

        # Apply pan
        if self.pan != 0.0:
            pan_left = 1.0 - max(0.0, self.pan)    # pan > 0 reduces left
            pan_right = 1.0 - max(0.0, -self.pan)  # pan < 0 reduces right
            audio[:, 0] *= pan_left   # Left channel
            audio[:, 1] *= pan_right  # Right channel

        return audio

    def is_active(self) -> bool:
        """
        Check if this voice instance is still active.

        Returns:
            True if any region is still producing sound
        """
        return len(self.active_regions) > 0 and \
               any(hasattr(r, 'is_active') and r.is_active() for r in self.active_regions)

    def get_voice_info(self) -> Dict[str, Any]:
        """
        Get information about this voice instance.

        Returns:
            Dictionary with voice instance information
        """
        return {
            'note': self.note,
            'velocity': self.velocity,
            'channel': self.channel,
            'active_regions': len(self.active_regions),
            'total_regions': len(self.regions),
            'release_triggered': self.release_triggered,
            'master_volume': self.master_volume,
            'pan': self.pan,
            'modulation_state': self.modulation_state.copy(),
            'start_time': self.start_time,
            'duration': time.time() - self.start_time
        }

    def all_notes_off(self) -> None:
        """Immediately silence all regions in this voice."""
        for region in self.active_regions:
            if hasattr(region, 'all_notes_off'):
                region.all_notes_off()

        self.active_regions.clear()
        self.release_triggered = True

    def reset(self) -> None:
        """Reset voice instance to clean state."""
        self.active_regions.clear()
        self.regions.clear()
        self.release_triggered = False
        self.released = False

        # Reset modulation state to defaults
        self.modulation_state = {
            'pitch_bend': 0.0,
            'mod_wheel': 0.0,
            'breath_controller': 0.0,
            'foot_controller': 0.0,
            'expression': 1.0,
            'channel_aftertouch': 0.0,
            'key_aftertouch': 0.0,
            'volume_cc': 1.0,
            'pan': 0.0,
            'brightness': 0.5,
            'harmonic_content': 0.5,
            'tremolo_rate': 4.0,
            'tremolo_depth': 0.0,
        }
