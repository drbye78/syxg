"""
Arpeggiator System - Yamaha Motif Compatible Arpeggiation

Complete arpeggiator system with multi-arpeggiator support, pattern sequencing,
and SYSEX/NRPN control for professional workstation-style arpeggiation.
"""

from __future__ import annotations

import threading
from typing import Any


class ArpeggiatorSystem:
    """
    Complete arpeggiator system for Yamaha Motif-style arpeggiation.

    Provides multi-arpeggiator support with pattern sequencing, tempo sync,
    and comprehensive SYSEX/NRPN control for professional applications.
    """

    def __init__(self, synthesizer):
        """
        Initialize arpeggiator system.

        Args:
            synthesizer: Reference to the parent synthesizer
        """
        self.synthesizer = synthesizer
        self.lock = threading.RLock()

        # Arpeggiator components
        self.arpeggiator_engine = None
        self.arpeggiator_manager = None
        self.arpeggiator_sysex_controller = None
        self.arpeggiator_nrpn_controller = None

        # Initialize systems
        self._init_arpeggiator_system()
        self._init_multi_arpeggiator_system()

    def _init_arpeggiator_system(self):
        """Initialize Yamaha Motif Arpeggiator system"""
        # Import arpeggiator components
        from ...protocols.xg.xg_arpeggiator_engine import YamahaArpeggiatorEngine
        from ...protocols.xg.xg_arpeggiator_nrpn_controller import YamahaArpeggiatorNRPNController
        from ...protocols.xg.xg_arpeggiator_sysex_controller import YamahaArpeggiatorSysexController

        # Create arpeggiator engine
        self.arpeggiator_engine = YamahaArpeggiatorEngine()

        # Create SYSEX controller
        self.arpeggiator_sysex_controller = YamahaArpeggiatorSysexController(
            self.arpeggiator_engine
        )

        # Create NRPN controller
        self.arpeggiator_nrpn_controller = YamahaArpeggiatorNRPNController(self.arpeggiator_engine)

        # Connect arpeggiator to MIDI processing pipeline
        self.arpeggiator_engine.note_on_callback = self._handle_arpeggiator_note_on
        self.arpeggiator_engine.note_off_callback = self._handle_arpeggiator_note_off

        print("🎹 Arpeggiator system initialized and connected to MIDI processing")

    def _init_multi_arpeggiator_system(self):
        """Initialize Multi-Arpeggiator system (Yamaha Motif compatible)"""
        # Import Multi-Arpeggiator Manager
        from ...protocols.xg.xg_arpeggiator_manager import MotifArpeggiatorManager

        # Create Multi-Arpeggiator Manager
        self.arpeggiator_manager = MotifArpeggiatorManager()

        # Load Motif-compatible patterns
        self.arpeggiator_manager.load_motif_patterns()

        # Connect callbacks
        self.arpeggiator_manager.note_on_callback = self._handle_arpeggiator_note_on
        self.arpeggiator_manager.note_off_callback = self._handle_arpeggiator_note_off

        print("🎹 Multi-Arpeggiator system initialized with 4 arpeggiators and 128+ patterns")

    def _handle_arpeggiator_note_on(self, channel: int, note: int, velocity: int):
        """
        Handle note-on events from arpeggiator engine.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: Note velocity
        """
        # Convert arpeggiator output to actual MIDI note events
        # This will trigger the normal channel processing
        if 0 <= channel < len(self.synthesizer.channels):
            self.channels[channel].note_on(note, velocity)

    def _handle_arpeggiator_note_off(self, channel: int, note: int):
        """
        Handle note-off events from arpeggiator engine.

        Args:
            channel: MIDI channel
            note: MIDI note number
        """
        # Convert arpeggiator output to actual MIDI note events
        if 0 <= channel < len(self.synthesizer.channels):
            self.channels[channel].note_off(note)

    def process_midi_message(self, message_bytes: bytes) -> bool:
        """
        Process MIDI message for arpeggiator control.

        Args:
            message_bytes: Raw MIDI message bytes

        Returns:
            True if arpeggiator handled the message, False otherwise
        """
        # Check for arpeggiator SYSEX messages
        if self.arpeggiator_sysex_controller:
            result = self.arpeggiator_sysex_controller.process_sysex_message(message_bytes)
            if result:
                return True

        return False

    def process_nrpn(self, controller: int, value: int) -> bool:
        """
        Process NRPN messages for arpeggiator control.

        Args:
            controller: NRPN controller number
            value: Controller value

        Returns:
            True if arpeggiator handled the NRPN, False otherwise
        """
        if self.arpeggiator_nrpn_controller:
            return self.arpeggiator_nrpn_controller.process_nrpn_message(controller, value)
        return False

    def process_note_event(self, channel: int, note: int, velocity: int, is_note_on: bool) -> bool:
        """
        Process note events through arpeggiator system.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: Note velocity
            is_note_on: True for note-on, False for note-off

        Returns:
            True if arpeggiator handled the note, False otherwise
        """
        if not self.arpeggiator_engine:
            return False

        # Check if arpeggiator is active for this channel
        arpeggiator = self.arpeggiator_engine.get_arpeggiator(channel)
        if arpeggiator and arpeggiator.enabled and arpeggiator.current_pattern:
            # Arpeggiator is active - let it handle the note
            if is_note_on:
                self.arpeggiator_engine.process_note_on(channel, note, velocity)
            else:
                self.arpeggiator_engine.process_note_off(channel, note)
            # Arpeggiator will generate its own note events via callbacks
            return True

        # Arpeggiator is inactive - don't handle
        return False

    def get_arpeggiator_status(self) -> dict[str, Any]:
        """
        Get arpeggiator system status.

        Returns:
            Dictionary with arpeggiator system information
        """
        status = {
            "engine_active": self.arpeggiator_engine is not None,
            "manager_active": self.arpeggiator_manager is not None,
            "sysex_controller_active": self.arpeggiator_sysex_controller is not None,
            "nrpn_controller_active": self.arpeggiator_nrpn_controller is not None,
        }

        if self.arpeggiator_manager:
            status["manager_status"] = self.arpeggiator_manager.get_manager_status()

        return status

    def enable_arpeggiator(self, channel: int, enabled: bool = True):
        """
        Enable or disable arpeggiator for a specific channel.

        Args:
            channel: MIDI channel
            enabled: Whether to enable arpeggiator
        """
        if self.arpeggiator_engine:
            arpeggiator = self.arpeggiator_engine.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.enabled = enabled

    def set_arpeggiator_pattern(self, channel: int, pattern_id: int):
        """
        Set arpeggiator pattern for a channel.

        Args:
            channel: MIDI channel
            pattern_id: Pattern ID to set
        """
        if self.arpeggiator_engine:
            arpeggiator = self.arpeggiator_engine.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.set_pattern(pattern_id)

    def get_arpeggiator_info(self, channel: int) -> dict[str, Any] | None:
        """
        Get information about arpeggiator on a specific channel.

        Args:
            channel: MIDI channel

        Returns:
            Dictionary with arpeggiator information, or None if not found
        """
        if self.arpeggiator_engine:
            arpeggiator = self.arpeggiator_engine.get_arpeggiator(channel)
            if arpeggiator:
                return {
                    "enabled": arpeggiator.enabled,
                    "current_pattern": arpeggiator.current_pattern,
                    "tempo": arpeggiator.tempo,
                    "gate_time": arpeggiator.gate_time,
                    "velocity": arpeggiator.velocity,
                    "octave_range": arpeggiator.octave_range,
                    "swing": arpeggiator.swing,
                }
        return None

    def reset_arpeggiators(self):
        """Reset all arpeggiators to default state"""
        if self.arpeggiator_engine:
            self.arpeggiator_engine.reset_all_arpeggiators()
        if self.arpeggiator_manager:
            self.arpeggiator_manager.reset_all()

    def get_available_patterns(self) -> list[str]:
        """
        Get list of available arpeggiator patterns.

        Returns:
            List of pattern names
        """
        if self.arpeggiator_manager:
            return self.arpeggiator_manager.get_available_patterns()
        return []

    def load_pattern_set(self, pattern_set_name: str) -> bool:
        """
        Load a specific pattern set.

        Args:
            pattern_set_name: Name of pattern set to load

        Returns:
            True if loaded successfully, False otherwise
        """
        if self.arpeggiator_manager:
            return self.arpeggiator_manager.load_pattern_set(pattern_set_name)
        return False

    def get_pattern_sets(self) -> list[str]:
        """
        Get list of available pattern sets.

        Returns:
            List of pattern set names
        """
        if self.arpeggiator_manager:
            return self.arpeggiator_manager.get_pattern_sets()
        return []

    def is_arpeggiator_active(self, channel: int) -> bool:
        """
        Check if arpeggiator is active on a channel.

        Args:
            channel: MIDI channel

        Returns:
            True if arpeggiator is active, False otherwise
        """
        if self.arpeggiator_engine:
            arpeggiator = self.arpeggiator_engine.get_arpeggiator(channel)
            return (
                arpeggiator is not None
                and arpeggiator.enabled
                and arpeggiator.current_pattern is not None
            )
        return False
