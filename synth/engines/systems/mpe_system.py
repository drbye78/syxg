"""
MPE (Microtonal Expression) System - Complete MPE Implementation

Production-quality Microtonal Expression system with per-note pitch bending,
timbre control, and slide/lift parameters for expressive synthesis control.
"""

from __future__ import annotations

import threading
from typing import Any


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

        print("🎹 MPE (Microtonal Expression) system initialized")

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

        # Create MPE note
        mpe_note = self.mpe_manager.process_note_on(channel, note, velocity)
        if mpe_note:
            # Send to voice allocation with MPE parameters
            self._allocate_voice_with_mpe(mpe_note)
            return mpe_note

        return None

    def process_note_off(self, channel: int, note: int, velocity: int = 0):
        """
        Process note-off event with MPE support.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: Note-off velocity
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return

        # Release MPE note
        released_note = self.mpe_manager.process_note_off(channel, note, velocity)
        if released_note and hasattr(released_note, "voice_id"):
            # Release voice
            self._release_voice_mpe(released_note.voice_id)

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

        # Process MPE pitch bend
        self.mpe_manager.process_pitch_bend(channel, bend_value)
        # Update all active voices on this channel
        self._update_channel_voices_mpe(channel)
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

        # Process MPE per-note pressure
        self.mpe_manager.process_poly_pressure(channel, note, pressure)
        # Update specific voice
        self._update_note_voice_mpe(channel, note)

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
            self._update_channel_voices_mpe(channel)
            return True

        # Check for MPE slide control
        if controller == 75:
            self.mpe_manager.process_slide(channel, value)
            self._update_channel_voices_mpe(channel)
            return True

        # Check for MPE lift control
        if controller == 76:
            self.mpe_manager.process_lift(channel, value)
            self._update_channel_voices_mpe(channel)
            return True

        return False

    def _allocate_voice_with_mpe(self, mpe_note):
        """
        Allocate voice with MPE parameters.

        Args:
            mpe_note: MPE note object
        """
        # This would integrate with the voice allocation system
        # For now, use regular channel allocation but store MPE reference
        if 0 <= mpe_note.channel < len(self.synthesizer.channels):
            voice_id = self.synthesizer.channels[mpe_note.channel].note_on(
                mpe_note.note_number, mpe_note.velocity
            )
            if voice_id:
                mpe_note.voice_id = voice_id
                # Update voice with MPE parameters
                self._apply_mpe_to_voice(voice_id, mpe_note)

    def _release_voice_mpe(self, voice_id):
        """Release voice by ID (MPE version).

        Args:
            voice_id: Voice ID to release
        """
        if hasattr(self, "voice_manager") and self.voice_manager:
            self.voice_manager.release_voice(voice_id)

    def _update_channel_voices_mpe(self, channel: int):
        """
        Update all voices on channel with current MPE parameters.

        Args:
            channel: MIDI channel
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return

        active_notes = self.mpe_manager.get_channel_mpe_notes(channel)
        for mpe_note in active_notes:
            if hasattr(mpe_note, "voice_id") and mpe_note.voice_id:
                self._apply_mpe_to_voice(mpe_note.voice_id, mpe_note)

    def _update_note_voice_mpe(self, channel: int, note: int):
        """
        Update specific note's voice with MPE parameters.

        Args:
            channel: MIDI channel
            note: MIDI note number
        """
        if not self.mpe_enabled or not self.mpe_manager:
            return

        mpe_note = self.mpe_manager.active_notes.get((channel, note))
        if mpe_note and hasattr(mpe_note, "voice_id") and mpe_note.voice_id:
            self._apply_mpe_to_voice(mpe_note.voice_id, mpe_note)

    def _apply_mpe_to_voice(self, voice_id, mpe_note):
        """Apply MPE parameters to voice.

        Args:
            voice_id: Voice ID to update
            mpe_note: MPE note with parameters
        """
        if hasattr(self, "voice_manager") and self.voice_manager:
            voice = self.voice_manager.get_voice(voice_id)
            if voice:
                if hasattr(mpe_note, "pitch_bend"):
                    if hasattr(voice, "pitch_offset"):
                        voice.pitch_offset = mpe_note.pitch_bend

                if hasattr(mpe_note, "timbre"):
                    if hasattr(voice, "timbre"):
                        voice.timbre = mpe_note.timbre
                    if hasattr(voice, "filter_cutoff_offset"):
                        voice.filter_cutoff_offset = int(mpe_note.timbre * 20)

                if hasattr(mpe_note, "pressure"):
                    if hasattr(voice, "aftertouch"):
                        voice.aftertouch = mpe_note.pressure

                if hasattr(voice, "update"):
                    voice.update()

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
            "manager_info": self.mpe_manager.get_mpe_info()
            if hasattr(self.mpe_manager, "get_mpe_info")
            else {},
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
