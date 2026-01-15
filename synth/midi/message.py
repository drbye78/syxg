"""
Unified MIDI Message System

Single, unified MIDIMessage class for all MIDI data across the synthesizer.
Provides a clean, consistent interface for both real-time and file-based MIDI processing.
"""

from typing import Dict, Any, Optional
import time


class MIDIMessage:
    """
    Unified MIDI message representation for all use cases.

    This single class replaces the previous MIDIMessage/MIDIMessageFile split,
    providing a consistent interface for real-time MIDI processing, file parsing,
    and buffered message handling.

    Attributes:
        timestamp (float): Message timestamp in seconds (from epoch for real-time,
                          from file start for file parsing)
        type (str): Message type ('note_on', 'note_off', 'control_change', etc.)
        channel (Optional[int]): MIDI channel (0-15) or None for system messages
        data (Dict[str, Any]): Type-specific message data
    """

    __slots__ = ('timestamp', 'type', 'channel', 'data', '_xg_metadata')

    def __init__(self, type: str, channel: Optional[int] = None,
                 data: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[float] = None, **kwargs):
        """
        Initialize a MIDI message.

        Args:
            type: Message type identifier
            channel: MIDI channel (0-15) or None for system messages
            data: Message-specific data dictionary
            timestamp: Message timestamp (auto-generated if None)
            **kwargs: Additional data fields (merged into data dict)
        """
        self.timestamp = timestamp or time.time()
        self.type = type
        self.channel = channel
        self.data = data or {}
        self._xg_metadata = None
        # Merge any additional keyword arguments into data
        if kwargs:
            self.data.update(kwargs)

    def __repr__(self) -> str:
        """String representation for debugging."""
        channel_str = f" ch{self.channel}" if self.channel is not None else ""
        return f"MIDIMessage({self.type}{channel_str}, {self.data})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.__repr__()

    def copy(self) -> 'MIDIMessage':
        """Create a copy of this message."""
        return MIDIMessage(
            type=self.type,
            channel=self.channel,
            data=self.data.copy(),
            timestamp=self.timestamp
        )

    def with_timestamp(self, timestamp: float) -> 'MIDIMessage':
        """Create a new message with different timestamp."""
        return MIDIMessage(
            type=self.type,
            channel=self.channel,
            data=self.data,
            timestamp=timestamp
        )

    # Convenience properties for common message data
    @property
    def note(self) -> Optional[int]:
        """Note number for note messages."""
        return self.data.get('note')

    @property
    def velocity(self) -> Optional[int]:
        """Velocity for note messages."""
        return self.data.get('velocity')

    @property
    def controller(self) -> Optional[int]:
        """Controller number for CC messages."""
        return self.data.get('controller')

    @property
    def value(self) -> Optional[int]:
        """Controller value for CC messages."""
        return self.data.get('value')

    @property
    def program(self) -> Optional[int]:
        """Program number for program change messages."""
        return self.data.get('program')

    @property
    def pressure(self) -> Optional[int]:
        """Pressure value for pressure messages."""
        return self.data.get('pressure')

    @property
    def pitch(self) -> Optional[int]:
        """Pitch bend value."""
        return self.data.get('pitch')

    @property
    def bend_value(self) -> Optional[int]:
        """Alias for pitch bend value."""
        return self.data.get('value', self.data.get('pitch'))

    # Message type checking
    def is_note_on(self) -> bool:
        """Check if this is a note on message."""
        return self.type == 'note_on'

    def is_note_off(self) -> bool:
        """Check if this is a note off message."""
        return self.type == 'note_off'

    def is_control_change(self) -> bool:
        """Check if this is a control change message."""
        return self.type == 'control_change'

    def is_program_change(self) -> bool:
        """Check if this is a program change message."""
        return self.type == 'program_change'

    def is_pitch_bend(self) -> bool:
        """Check if this is a pitch bend message."""
        return self.type == 'pitch_bend'

    def is_channel_pressure(self) -> bool:
        """Check if this is a channel pressure message."""
        return self.type == 'channel_pressure'

    def is_poly_pressure(self) -> bool:
        """Check if this is a polyphonic pressure message."""
        return self.type == 'poly_pressure'

    def is_system_message(self) -> bool:
        """Check if this is a system message."""
        return self.channel is None

    def is_channel_message(self) -> bool:
        """Check if this is a channel message."""
        return self.channel is not None
