"""

MPE (Microtonal Expression) System - Complete MPE Implementation

Production-quality Microtonal Expression system with per-note pitch bending,
timbre control, and slide/lift parameters for expressive synthesis control.
"""

from __future__ import annotations
import logging


import threading
from typing import Any

logger = logging.getLogger(__name__)


class MPESystem:
    """
    Complete MPE (Microtonal Expression) system implementation.

    Provides per-note pitch bending, timbre control, and additional expression
    parameters for microtonal and expressive synthesis applications.
    """

    def __init__(self, synthesizer, max_channels: int = 32):
        """
        Initialize MPE system.

        Args:
            synthesizer: Reference to the parent synthesizer
            max_channels: Maximum number of MIDI channels
        """
        self.synthesizer = synthesizer
        self.max_channels = max_channels
        self.lock = threading.RLock()

        # MPE state
        self.mpe_enabled = True
        self.mpe_plus_enabled = False  # MIDI 2.0 MPE+ high-precision mode
        self.mpe_manager = None
        self.global_pitch_bend_range = 48  # semitones

        # Initialize MPE if enabled
        if self.mpe_enabled:
            self._init_mpe_system()

    def _init_mpe_system(self):
        """Initialize MPE (Microtonal Expression) system"""
        # Import MPE manager
        from ...mpe.mpe_manager import MPEManager

        # Create MPE manager
        self.mpe_manager = MPEManager(max_channels=self.max_channels)

        logger.info("🎹 MPE (Microtonal Expression) system initialized")

    def process_note_on(self, channel: int, note: int, velocity: int):
        """
        Process note-on event with MPE support.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: Note velocity

        Returns:
            MPE note if processed, None otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return None

        # Create MPE note and return it; caller handles voice allocation
        return self.mpe_manager.process_note_on(channel, note, velocity)

    def process_note_off(self, channel: int, note: int, velocity: int = 0):
        """
        Process note-off event with MPE support.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: Note-off velocity

        Returns:
            Released MPE note if found, None otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return None

        # Release MPE note state; caller handles voice release
        return self.mpe_manager.process_note_off(channel, note, velocity)

    def process_pitch_bend(self, channel: int, bend_value: int) -> bool:
        """
        Process pitch bend with MPE support.

        Args:
            channel: MIDI channel
            bend_value: Pitch bend value

        Returns:
            True if MPE handled it, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        # Process MPE pitch bend; caller handles voice updates
        self.mpe_manager.process_pitch_bend(channel, bend_value)
        return True

    def process_pitch_bend_32bit(self, channel: int, bend_value_32bit: int) -> bool:
        """
        Process pitch bend with 32-bit precision (MIDI 2.0).

        Args:
            channel: MIDI channel
            bend_value_32bit: 32-bit pitch bend value
                (0=full down, 0x7FFFFFFF=center, 0xFFFFFFFF=full up)

        Returns:
            True if MPE handled it, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        with self.mpe_manager.lock:
            zone = self.mpe_manager.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return False

            # Scale 32-bit to -1.0 to +1.0 (center = 0.0)
            normalized = (bend_value_32bit - 0x7FFFFFFF) / 0x7FFFFFFF
            bend_semitones = normalized * zone.pitch_bend_range

            # Feature P2.3: Master channel routes to all member channels
            if zone.mpe_channel.is_master_channel(channel):
                for note in zone.mpe_channel.get_active_notes():
                    note.pitch_bend = bend_semitones
            else:
                for note in zone.mpe_channel.get_active_notes():
                    if note.channel == channel:
                        note.pitch_bend = bend_semitones

        return True

    def process_poly_pressure(self, channel: int, note: int, pressure: int):
        """
        Process polyphonic pressure with MPE support.

        Args:
            channel: MIDI channel
            note: MIDI note number
            pressure: Pressure value
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return

        # Process MPE per-note pressure; caller handles voice updates
        self.mpe_manager.process_poly_pressure(channel, note, pressure)

    def process_mpe_controller(self, channel: int, controller: int, value: int) -> bool:
        """
        Process MPE controllers (timbre, slide, lift).

        Args:
            channel: MIDI channel
            controller: MIDI controller number
            value: Controller value

        Returns:
            True if MPE controller handled, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        # Check for MPE timbre control (CC74)
        if controller == 74:
            self.mpe_manager.process_timbre(channel, value)
            return True

        # Check for MPE slide control
        if controller == 75:
            self.mpe_manager.process_slide(channel, value)
            return True

        # Check for MPE lift control
        if controller == 76:
            self.mpe_manager.process_lift(channel, value)
            return True

        return False

    def process_mpe_controller_32bit(
        self, channel: int, controller: int, value_32bit: int
    ) -> bool:
        """
        Process MPE controllers with 32-bit precision (MIDI 2.0).

        Args:
            channel: MIDI channel
            controller: MIDI controller number (74=timbre, 75=slide, 76=lift)
            value_32bit: 32-bit value (0-4294967295)

        Returns:
            True if MPE controller handled, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        normalized = value_32bit / 4294967295.0  # Scale 32-bit to 0.0-1.0

        with self.mpe_manager.lock:
            zone = self.mpe_manager.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return False

            if controller == 74:  # Timbre
                if zone.mpe_channel.is_master_channel(channel):
                    for note in zone.mpe_channel.get_active_notes():
                        note.timbre = normalized
                else:
                    for note in zone.mpe_channel.get_active_notes():
                        if note.channel == channel:
                            note.timbre = normalized
                return True

            elif controller == 75:  # Slide
                if zone.mpe_channel.is_master_channel(channel):
                    for note in zone.mpe_channel.get_active_notes():
                        note.slide = normalized
                else:
                    for note in zone.mpe_channel.get_active_notes():
                        if note.channel == channel:
                            note.slide = normalized
                return True

            elif controller == 76:  # Lift
                if zone.mpe_channel.is_master_channel(channel):
                    for note in zone.mpe_channel.get_active_notes():
                        note.lift = normalized
                else:
                    for note in zone.mpe_channel.get_active_notes():
                        if note.channel == channel:
                            note.lift = normalized
                return True

        return False

    def process_per_note_controller(
        self, channel: int, note: int, controller: int, value_24bit: int
    ) -> bool:
        """
        Process MIDI 2.0 per-note controller with 24-bit precision.

        Args:
            channel: MIDI channel
            note: Note number
            controller: MIDI controller number (e.g., 74=timbre, 75=slide, 76=lift)
            value_24bit: 24-bit value (0-16777215)

        Returns:
            True if handled, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        # Check for MPE per-note controllers
        with self.mpe_manager.lock:
            # Find the specific note
            note_key = (channel, note)
            if note_key not in self.mpe_manager.active_notes:
                return False

            mpe_note = self.mpe_manager.active_notes[note_key]

            # Scale 24-bit to normalized float (0.0-1.0)
            normalized_value = value_24bit / 16777215.0

            if controller == 74:  # Timbre
                mpe_note.timbre = normalized_value
                return True
            elif controller == 75:  # Slide
                mpe_note.slide = normalized_value
                return True
            elif controller == 76:  # Lift
                mpe_note.lift = normalized_value
                return True

        return False

    def process_per_note_management(
        self, channel: int, note: int, assign: bool
    ) -> bool:
        """
        Process Per-Note Management message.
        
        Explicitly assigns or removes a note from an MPE zone.
        
        Args:
            channel: MIDI channel
            note: Note number
            assign: True to assign note to zone, False to remove
            
        Returns:
            True if handled, False otherwise
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False
        
        with self.mpe_manager.lock:
            zone = self.mpe_manager.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return False
            
            if assign:
                # Assign note to member channel
                # Check one-note-per-member-channel rule
                if zone.mpe_channel.is_member_channel(channel):
                    existing = zone.mpe_channel.get_note_on_channel(channel)
                    if existing is not None:
                        zone.mpe_channel.remove_note(existing.note_number)
                        self.mpe_manager.active_notes.pop(
                            (channel, existing.note_number), None
                        )
                
                # Create and register the MPE note
                from ...mpe.mpe_manager import MPENote
                mpe_note = MPENote(note, channel, velocity=64)
                zone.mpe_channel.add_note(mpe_note)
                self.mpe_manager.active_notes[(channel, note)] = mpe_note
            else:
                # Remove note from zone
                note_key = (channel, note)
                if note_key in self.mpe_manager.active_notes:
                    mpe_note = self.mpe_manager.active_notes[note_key]
                    mpe_note.active = False
                    zone.mpe_channel.remove_note(note)
                    del self.mpe_manager.active_notes[note_key]
            
            return True

    def handle_rpn(self, channel: int, controller: int, value: int) -> bool | None:
        """
        Handle RPN messages for MPE.

        Returns True if handled (RPN consumed), False if not an RPN message,
        None if RPN data is incomplete.
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return False

        return self.mpe_manager.handle_rpn(channel, controller, value)

    def get_mpe_info(self) -> dict[str, Any]:
        """
        Get MPE system information.

        Returns:
            Dictionary with MPE system status
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return {"enabled": False, "status": "MPE disabled"}

        return {
            "enabled": True,
            "zones": len(self.mpe_manager.zones),
            "active_notes": len(self.mpe_manager.active_notes),
            "pitch_bend_range": self.global_pitch_bend_range,
            "manager_info": (
                self.mpe_manager.get_mpe_info() if hasattr(self.mpe_manager, "get_mpe_info") else {}
            ),
        }

    def set_mpe_enabled(self, enabled: bool):
        """
        Enable or disable MPE.

        Args:
            enabled: Whether to enable MPE
        """
        self.mpe_enabled = enabled
        if self.mpe_manager:
            self.mpe_manager.set_mpe_enabled(enabled)

    def set_mpe_plus_enabled(self, enabled: bool):
        """Enable or disable MPE+ high-precision mode."""
        self.mpe_plus_enabled = enabled

    def reset_mpe(self):
        """Reset MPE system"""
        if self.mpe_manager:
            self.mpe_manager.reset_all_notes()

    def is_mpe_enabled(self) -> bool:
        """
        Check if MPE is enabled.

        Returns:
            True if MPE is enabled, False otherwise
        """
        return self.mpe_enabled and self.mpe_manager is not None

    def get_active_mpe_notes(self, channel: int | None = None) -> list[Any]:
        """
        Get active MPE notes.

        Args:
            channel: Optional channel filter, None for all channels

        Returns:
            List of active MPE notes
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return []

        if channel is not None:
            return self.mpe_manager.get_channel_mpe_notes(channel)
        else:
            return list(self.mpe_manager.active_notes.values())

    def set_global_pitch_bend_range(self, range_semitones: int):
        """
        Set global pitch bend range for MPE.

        Args:
            range_semitones: Pitch bend range in semitones
        """
        self.global_pitch_bend_range = max(1, min(96, range_semitones))  # Clamp to reasonable range

    def get_global_pitch_bend_range(self) -> int:
        """
        Get global pitch bend range.

        Returns:
            Pitch bend range in semitones
        """
        return self.global_pitch_bend_range
