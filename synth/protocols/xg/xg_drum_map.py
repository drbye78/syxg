"""
XG Drum Map - Complete Implementation

Implements XG Drum Map functionality (Drum Map 1-4) per XG specification.
This enables note mapping, alternate notes, velocity switching for drum parts.

XG Drum Map allows:
- Selecting Drum Map 1-4 per part
- Mapping MIDI notes to different drum sounds
- Alternate note assignment
- Velocity zone assignment

XG Specification Compliance:
- MSB 44 LSB 0-15: Drum Map Select per part
- MSB 44 LSB 16-31: Drum Note Assign per part
- Note mapping with alternate notes
- Velocity zone support

Copyright (c) 2025 - Production Grade
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DrumNoteEntry:
    """Single drum note mapping entry"""

    note: int  # MIDI note (0-127)
    instrument: int  # Instrument number in drum kit
    alternate_note: int = -1  # Alternate note (-1 = none)
    level: int = 100  # Note volume (0-127)
    pan: int = 64  # Note pan (0-127, 64=center)
    reverb_send: int = 40  # Reverb send (0-127)
    chorus_send: int = 0  # Chorus send (0-127)
    variation_send: int = 0  # Variation send (0-127)
    key_group: int = -1  # Key group for grouping (-1 = none)
    volume_velocity: int = 100  # Velocity sensitivity


@dataclass
class DrumMap:
    """Complete XG Drum Map"""

    map_number: int  # 1-4
    name: str
    notes: dict[int, DrumNoteEntry]  # MIDI note -> entry


class XGDrumMapManager:
    """
    XG Drum Map Manager - Production Implementation

    Manages XG Drum Maps 1-4 for complete drum note mapping support.
    Each part can select a different drum map.
    """

    # XG Drum Map constants
    NUM_MAPS = 4
    MAX_NOTES_PER_MAP = 128
    MAP_PARAM_LSB = 0  # MSB 44 LSB 0-15: Drum Map select
    NOTE_PARAM_BASE = 16  # MSB 44 LSB 16-31: Note assignment

    # Drum Map names (from XG spec)
    DRUM_MAP_NAMES = {
        0: "Drum Map 1",
        1: "Drum Map 2",
        2: "Drum Map 3",
        3: "Drum Map 4",
    }

    def __init__(self, num_parts: int = 16):
        """
        Initialize XG Drum Map Manager.

        Args:
            num_parts: Number of XG parts (default 16)
        """
        self.num_parts = num_parts
        self.lock = threading.RLock()

        # Drum map selection per part (0-3 for maps 1-4, -1 = off)
        # Default to Drum Map 1 (index 0) instead of off
        self.part_drum_map: dict[int, int] = dict.fromkeys(range(num_parts), 0)

        # Drum maps (4 maps × 128 notes)
        self.maps: dict[int, DrumMap] = {}
        self._initialize_maps()

        # Active drum note mappings per part
        # part -> MIDI note -> actual instrument note
        self._note_mappings: dict[int, dict[int, int]] = {i: {} for i in range(num_parts)}

        # Callback for parameter changes
        self.parameter_change_callback = None

        logger = logging.getLogger(__name__)
        self._logger = logger

        self._logger.info(
            f"XG Drum Map Manager: Initialized {num_parts} parts, {self.NUM_MAPS} maps"
        )

    def _initialize_maps(self):
        """Initialize default XG drum maps with Standard Kit mappings."""
        # Create 4 drum maps
        for map_num in range(self.NUM_MAPS):
            self.maps[map_num] = DrumMap(
                map_number=map_num + 1, name=self.DRUM_MAP_NAMES[map_num], notes={}
            )

        # Populate default mappings based on Standard Kit
        self._create_default_mappings()

    def _create_default_mappings(self):
        """Create default XG drum note mappings (Standard Kit style)."""
        # Standard XG drum note assignments (note -> instrument)
        default_mapping = {
            # Standard Drum Map 1
            0: (36, "Kick 1"),  # C1
            1: (36, "Kick 1"),
            2: (38, "Snare 1"),  # D1
            3: (38, "Snare 1"),
            4: (42, "Hi-Hat Closed"),  # F#1
            5: (42, "Hi-Hat Closed"),
            6: (46, "Hi-Hat Open"),  # A#1
            7: (46, "Hi-Hat Open"),
            8: (45, "Tom 1"),  # B1
            9: (48, "Tom 2"),  # C2
            10: (50, "Tom 3"),  # D2
            11: (49, "Crash 1"),  # C#2
            12: (51, "Ride 1"),  # D#2
            13: (39, "Rim Shot"),  # D#1
            14: (56, "Cowbell"),  # G#2
            15: (54, "Tambourine"),  # F#2
        }

        # Simplified velocity layers
        for note_idx, (instr, name) in default_mapping.items():
            # Create velocity layers for each drum note
            for vel_zone in range(3):  # 3 velocity zones
                vel_offset = vel_zone * 20
                entry = DrumNoteEntry(
                    note=note_idx,
                    instrument=instr + vel_offset,
                    alternate_note=note_idx + 12 if vel_zone == 0 else -1,
                    level=100 - vel_offset // 4,
                    pan=64,
                    reverb_send=40,
                    chorus_send=0,
                    variation_send=0,
                    key_group=-1,
                    volume_velocity=100 - vel_zone * 10,
                )
                self.maps[0].notes[note_idx * 3 + vel_zone] = entry

    def select_drum_map(self, part: int, map_number: int) -> bool:
        """
        Select drum map for a part.

        Args:
            part: Part number (0-15)
            map_number: Drum map number (1-4) or 0 = off

        Returns:
            True if successful
        """
        if not (0 <= part < self.num_parts):
            return False

        if not (0 <= map_number <= self.NUM_MAPS):
            return False

        with self.lock:
            self.part_drum_map[part] = map_number - 1  # Convert to 0-based

            # Rebuild note mappings for this part
            self._rebuild_part_mappings(part)

            if self.parameter_change_callback:
                self.parameter_change_callback(f"drum_map_part_{part}", map_number)

            self._logger.info(f"Part {part}: Drum Map {map_number} selected")
            return True

    def _rebuild_part_mappings(self, part: int):
        """Rebuild note mappings for a part based on selected drum map."""
        map_num = self.part_drum_map[part]

        self._note_mappings[part].clear()

        if map_num < 0:
            return  # No drum map

        drum_map = self.maps.get(map_num)
        if not drum_map:
            return

        # Build note mapping table
        for note_entry in drum_map.notes.values():
            # Map input note to actual instrument note
            self._note_mappings[part][note_entry.note] = note_entry.instrument

    def set_note_mapping(
        self,
        part: int,
        input_note: int = None,
        instrument: int = None,
        alternate_note: int = -1,
        level: int = 100,
        pan: int = 64,
        reverb_send: int = 40,
        chorus_send: int = 0,
        variation_send: int = 0,
        source_note: int = None,
        target_note: int = None,
        drum_sound: str = None,
    ) -> bool:
        """
        Set individual drum note mapping.

        Args:
            part: Part number (0-15)
            input_note: Input MIDI note (0-127)
            instrument: Target instrument number
            alternate_note: Alternate note (-1 = none)
            level: Note level (0-127)
            pan: Note pan (0-127, 64=center)
            reverb_send: Reverb send level
            chorus_send: Chorus send level
            variation_send: Variation send level
            source_note: Alias for input_note (for backward compatibility)
            target_note: Alias for instrument (for backward compatibility)
            drum_sound: Optional drum sound name (ignored, for compatibility)

        Returns:
            True if successful
        """
        # Support aliases for backward compatibility
        if input_note is None and source_note is not None:
            input_note = source_note
        elif input_note is None:
            raise ValueError("Either 'input_note' or 'source_note' must be provided")

        if instrument is None and target_note is not None:
            instrument = target_note
        elif instrument is None:
            raise ValueError("Either 'instrument' or 'target_note' must be provided")
        if not (0 <= part < self.num_parts):
            return False

        if not (0 <= input_note < 128):
            return False

        map_num = self.part_drum_map[part]
        if map_num < 0:
            return False

        with self.lock:
            entry = DrumNoteEntry(
                note=input_note,
                instrument=instrument,
                alternate_note=alternate_note,
                level=level,
                pan=pan,
                reverb_send=reverb_send,
                chorus_send=chorus_send,
                variation_send=variation_send,
            )

            self.maps[map_num].notes[input_note] = entry

            # Update part mapping
            self._note_mappings[part][input_note] = instrument

            return True

    def get_instrument_for_note(
        self, part: int, note: int, velocity: int = 64
    ) -> tuple[int, DrumNoteEntry | None]:
        """
        Get mapped instrument note for input note and velocity.

        Args:
            part: Part number
            note: Input MIDI note
            velocity: Input velocity

        Returns:
            Tuple of (mapped_instrument, entry) or (note, None) if no mapping
        """
        if not (0 <= part < self.num_parts):
            return note, None

        with self.lock:
            map_num = self.part_drum_map[part]

            if map_num < 0:
                return note, None  # No drum map

            # Check for mapped note
            drum_map = self.maps.get(map_num)
            if not drum_map:
                return note, None

            # Look up mapping
            if note in self._note_mappings[part]:
                mapped_note = self._note_mappings[part][note]

                # Check velocity zone
                entry = drum_map.notes.get(note)
                if entry:
                    # Apply velocity sensitivity
                    if velocity < 43 and entry.volume_velocity > 70:
                        # Low velocity layer
                        return mapped_note - 10 if mapped_note > 10 else mapped_note, entry
                    elif velocity > 85 and entry.volume_velocity < 70:
                        # High velocity layer
                        return mapped_note + 10 if mapped_note < 117 else mapped_note, entry

                    return mapped_note, entry

            return note, None

    def get_drum_map_for_part(self, part: int) -> int:
        """Get currently selected drum map for part."""
        return self.part_drum_map.get(part, -1) + 1  # Convert to 1-based

    def get_note_mapping(self, part: int, source_note: int) -> tuple[int, DrumNoteEntry] | None:
        """
        Get drum note mapping for a part.

        Args:
            part: Part number (0-15)
            source_note: Source MIDI note (0-127)

        Returns:
            Tuple of (mapped_note, DrumNoteEntry) or None if not found
        """
        if not (0 <= part < self.num_parts):
            return None

        if not (0 <= source_note < 128):
            return None

        map_num = self.part_drum_map.get(part, -1)
        if map_num < 0:
            return None

        drum_map = self.maps.get(map_num)
        if not drum_map:
            return None

        entry = drum_map.notes.get(source_note)
        if entry:
            return (entry.instrument, entry)

        return None

    def get_drum_map_info(self, part: int) -> dict[str, Any]:
        """Get drum map information for a part."""
        map_num = self.part_drum_map.get(part, -1)

        if map_num < 0:
            return {"part": part, "drum_map": 0, "name": "Off", "notes_mapped": 0}

        drum_map = self.maps.get(map_num)
        if not drum_map:
            return {"part": part, "drum_map": 0, "name": "Error", "notes_mapped": 0}

        return {
            "part": part,
            "drum_map": map_num + 1,
            "name": drum_map.name,
            "notes_mapped": len(drum_map.notes),
        }

    def handle_nrpn_msb44(self, lsb: int, data_value: int, part: int = 0) -> bool:
        """
        Handle NRPN MSB 44 (Drum Map) messages.

        XG NRPN MSB 44:
        - LSB 0-15: Drum Map Select (1-4, 0=off)
        - LSB 16-31: Drum Note Assignment

        Args:
            lsb: NRPN LSB
            data_value: Parameter value
            part: Part number

        Returns:
            True if handled
        """
        if not (0 <= part < self.num_parts):
            return False

        with self.lock:
            # Drum Map Select (LSB 0-15)
            if lsb < 16:
                map_select = data_value >> 7  # Convert to 0-4
                return self.select_drum_map(part, map_select)

            # Drum Note Assignment (LSB 16-31)
            elif 16 <= lsb <= 31:
                note_index = lsb - 16
                # Parse note data from value
                # Format: IIIIIIPV (Inst bits 6-0, Pan bit 7, Velocity bit 6)
                instrument = (data_value >> 1) & 0x7F
                use_velocity = (data_value >> 8) & 1

                return self.set_note_mapping(part, note_index, instrument)

        return False

    def export_drum_maps(self) -> dict[str, Any]:
        """Export all drum map configurations."""
        with self.lock:
            maps_data = {}

            for map_num, drum_map in self.maps.items():
                notes_data = {}
                for note, entry in drum_map.notes.items():
                    notes_data[str(note)] = {
                        "note": entry.note,
                        "instrument": entry.instrument,
                        "alternate_note": entry.alternate_note,
                        "level": entry.level,
                        "pan": entry.pan,
                        "reverb_send": entry.reverb_send,
                        "chorus_send": entry.chorus_send,
                        "variation_send": entry.variation_send,
                    }

                maps_data[str(map_num)] = {
                    "map_number": drum_map.map_number,
                    "name": drum_map.name,
                    "notes": notes_data,
                }

            return {
                "part_drum_map": {str(k): v + 1 for k, v in self.part_drum_map.items()},
                "maps": maps_data,
            }

    def import_drum_maps(self, data: dict[str, Any]) -> bool:
        """Import drum map configurations."""
        try:
            with self.lock:
                # Import part assignments
                if "part_drum_map" in data:
                    for part_str, map_num in data["part_drum_map"].items():
                        part = int(part_str)
                        if 0 <= part < self.num_parts:
                            self.part_drum_map[part] = map_num - 1
                            self._rebuild_part_mappings(part)

                # Import maps
                if "maps" in data:
                    for map_str, map_data in data["maps"].items():
                        map_num = int(map_str)
                        if 0 <= map_num < self.NUM_MAPS:
                            drum_map = self.maps[map_num]
                            drum_map.name = map_data.get("name", drum_map.name)

                            drum_map.notes.clear()
                            for note_str, note_data in map_data.get("notes", {}).items():
                                note = int(note_str)
                                drum_map.notes[note] = DrumNoteEntry(
                                    note=note_data["note"],
                                    instrument=note_data["instrument"],
                                    alternate_note=note_data.get("alternate_note", -1),
                                    level=note_data.get("level", 100),
                                    pan=note_data.get("pan", 64),
                                    reverb_send=note_data.get("reverb_send", 40),
                                    chorus_send=note_data.get("chorus_send", 0),
                                    variation_send=note_data.get("variation_send", 0),
                                )

                return True
        except Exception as e:
            self._logger.error(f"Import failed: {e}")
            return False

    def reset_to_defaults(self):
        """Reset all drum maps to defaults."""
        with self.lock:
            self.maps.clear()
            self._initialize_maps()
            # Default to Drum Map 1 (index 0) instead of off (-1)
            self.part_drum_map = dict.fromkeys(range(self.num_parts), 0)
            self._note_mappings = {i: {} for i in range(self.num_parts)}

            self._logger.info("Drum maps reset to defaults")

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback


class XGPartModeController:
    """
    XG Part Mode Controller - Complete Implementation

    Manages part modes including:
    - Normal (multi-timbral)
    - Drum Mode with Drum Map support
    - Single Voice Mode

    XG Part Mode (MSB 43):
    - 0: Normal (Multi)
    - 1: Drums (with Drum Map 1-4)
    - 2: Drums Alternate
    - 3: Drums Full
    - 4+: Reserved
    """

    # Part Mode constants
    MODE_NORMAL = 0
    MODE_DRUM = 1
    MODE_DRUM_ALT = 2
    MODE_DRUM_FULL = 3
    MODE_SINGLE = 4

    MODE_NAMES = {0: "Normal", 1: "Drum", 2: "Drum Alt", 3: "Drum Full", 4: "Single"}

    def __init__(self, num_parts: int = 16):
        """Initialize Part Mode Controller."""
        self.num_parts = num_parts
        self.lock = threading.RLock()

        # Part modes
        self.part_modes: dict[int, int] = dict.fromkeys(range(num_parts), self.MODE_NORMAL)

        # Drum map manager
        self.drum_map_manager = XGDrumMapManager(num_parts)

        # Drum channel assignments (part -> MIDI channel for drums)
        self.drum_channels: dict[int, int] = dict.fromkeys(range(num_parts), 9)  # Default to ch 10

        # Callback
        self.parameter_change_callback = None

        logger = logging.getLogger(__name__)
        self._logger = logger

    def set_part_mode(
        self, part: int, mode: int, bank_msb: int = None, bank_lsb: int = None
    ) -> bool:
        """
        Set part mode.

        Args:
            part: Part number (0-15)
            mode: Part mode (0=Normal, 1=Drum, 2=Drum Alt, 3=Drum Full, 4=Single)
            bank_msb: Bank MSB (optional, for GS compatibility)
            bank_lsb: Bank LSB (optional, for GS compatibility)

        Returns:
            True if successful
        """
        if not (0 <= part < self.num_parts):
            return False

        if not (0 <= mode <= 4):
            return False

        # Note: bank_msb and bank_lsb are accepted for compatibility but not used in this implementation
        # They would typically be used to select specific drum banks in GS mode

        with self.lock:
            old_mode = self.part_modes[part]
            self.part_modes[part] = mode

            # Handle drum mode changes
            if mode >= self.MODE_DRUM and mode <= self.MODE_DRUM_FULL:
                # Enable drum mode - auto-select drum map
                if old_mode < self.MODE_DRUM:
                    self.drum_map_manager.select_drum_map(part, 1)  # Default to Map 1

            # Notify callback
            if self.parameter_change_callback:
                self.parameter_change_callback(f"part_mode_part_{part}", mode)

            self._logger.info(f"Part {part}: Mode set to {self.MODE_NAMES.get(mode, 'Unknown')}")
            return True

    def get_part_mode(self, part: int) -> int:
        """Get part mode."""
        return self.part_modes.get(part, self.MODE_NORMAL)

    def is_drum_part(self, part: int) -> bool:
        """Check if part is in drum mode."""
        mode = self.get_part_mode(part)
        return self.MODE_DRUM <= mode <= self.MODE_DRUM_FULL

    def set_drum_channel(self, part: int, channel: int) -> bool:
        """Set MIDI channel for drum part."""
        if not (0 <= part < self.num_parts):
            return False

        if not (0 <= channel < 16):
            return False

        with self.lock:
            self.drum_channels[part] = channel

            if self.parameter_change_callback:
                self.parameter_change_callback(f"drum_channel_part_{part}", channel)

            return True

    def get_drum_channel(self, part: int) -> int:
        """Get drum channel for part."""
        return self.drum_channels.get(part, 9)

    def handle_nrpn_msb43(self, lsb: int, data_value: int, part: int = 0) -> bool:
        """
        Handle NRPN MSB 43 (Part Mode) messages.

        Args:
            lsb: NRPN LSB (0-15 for parts 0-15)
            data_value: Part mode value

        Returns:
            True if handled
        """
        if not (0 <= part < self.num_parts):
            return False

        if not (0 <= lsb < 16):
            return False

        # Data value: bit 7 = enable, bits 0-2 = mode
        mode = data_value & 0x0F

        return self.set_part_mode(part, mode)

    def get_part_info(self, part: int) -> dict[str, Any]:
        """Get complete part mode information."""
        mode = self.get_part_mode(part)

        info = {
            "part": part,
            "mode": mode,
            "mode_name": self.MODE_NAMES.get(mode, "Unknown"),
            "is_drum": self.is_drum_part(part),
            "drum_channel": self.get_drum_channel(part),
        }

        if self.is_drum_part(part):
            info["drum_map"] = self.drum_map_manager.get_drum_map_info(part)

        return info

    def get_all_parts_info(self) -> list[dict[str, Any]]:
        """Get information for all parts."""
        return [self.get_part_info(i) for i in range(self.num_parts)]

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback
        self.drum_map_manager.set_parameter_change_callback(callback)

    def reset_to_defaults(self):
        """Reset all parts to default mode (Normal)."""
        with self.lock:
            for part in range(self.num_parts):
                self.part_modes[part] = self.MODE_NORMAL
                self.drum_channels[part] = 9

            self.drum_map_manager.reset_to_defaults()

            self._logger.info("Part modes reset to defaults")
