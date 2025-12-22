"""
Binary MIDI Message Parser

Converts raw binary MIDI message bytes to structured MIDIMessage objects
for use by the synthesizer. Provides efficient parsing of real-time MIDI
messages without file-based overhead.
"""

from typing import Optional, Tuple
from .parser import MIDIMessage


class BinaryMIDIParser:
    """
    Parser for raw binary MIDI messages.

    Converts raw MIDI message bytes (as received from MIDI devices) into
    structured MIDIMessage objects for consistent processing throughout
    the synthesizer.
    """

    def __init__(self):
        """Initialize the binary MIDI parser."""
        self.last_status = 0x00  # For running status support

    def parse_message(self, message_bytes: bytes, timestamp: float = 0.0) -> Optional[MIDIMessage]:
        """
        Parse raw MIDI message bytes into a MIDIMessage object.

        Args:
            message_bytes: Raw MIDI message bytes
            timestamp: Optional timestamp in seconds

        Returns:
            MIDIMessage object or None if invalid message
        """
        if not message_bytes:
            return None

        # Handle running status
        if message_bytes[0] < 0x80:
            # This is a data byte, use running status
            if self.last_status == 0x00:
                return None  # No previous status to use
            # Prepend the last status byte
            message_bytes = bytes([self.last_status]) + message_bytes

        status_byte = message_bytes[0]

        # Update running status for channel messages (not system messages)
        if status_byte >= 0x80 and status_byte < 0xF0:
            self.last_status = status_byte

        # System Real-Time messages (0xF8-0xFF) don't affect running status
        # System Common messages (0xF0-0xF7) reset running status
        if status_byte >= 0xF0:
            if status_byte < 0xF8:  # System Common (resets running status)
                self.last_status = 0x00

        if len(message_bytes) < 2:
            return None

        message_type = status_byte >> 4
        channel = status_byte & 0x0F

        # Create base message
        message = MIDIMessage(
            time=timestamp,
            status=status_byte,
            channel=channel
        )

        # Parse based on message type
        try:
            if message_type == 0x8:  # Note Off
                if len(message_bytes) >= 3:
                    message.update({
                        'type': 'note_off',
                        'note': message_bytes[1],
                        'velocity': message_bytes[2],
                        'data': [message_bytes[1], message_bytes[2]]
                    })
                    return message

            elif message_type == 0x9:  # Note On
                if len(message_bytes) >= 3:
                    message.update({
                        'type': 'note_on',
                        'note': message_bytes[1],
                        'velocity': message_bytes[2],
                        'data': [message_bytes[1], message_bytes[2]]
                    })
                    return message

            elif message_type == 0xA:  # Poly Pressure
                if len(message_bytes) >= 3:
                    message.update({
                        'type': 'poly_pressure',
                        'note': message_bytes[1],
                        'pressure': message_bytes[2],
                        'data': [message_bytes[1], message_bytes[2]]
                    })
                    return message

            elif message_type == 0xB:  # Control Change
                if len(message_bytes) >= 3:
                    message.update({
                        'type': 'control_change',
                        'control': message_bytes[1],
                        'value': message_bytes[2],
                        'data': [message_bytes[1], message_bytes[2]]
                    })
                    return message

            elif message_type == 0xC:  # Program Change
                if len(message_bytes) >= 2:
                    message.update({
                        'type': 'program_change',
                        'program': message_bytes[1],
                        'data': [message_bytes[1]]
                    })
                    return message

            elif message_type == 0xD:  # Channel Pressure
                if len(message_bytes) >= 2:
                    message.update({
                        'type': 'channel_pressure',
                        'pressure': message_bytes[1],
                        'data': [message_bytes[1]]
                    })
                    return message

            elif message_type == 0xE:  # Pitch Bend
                if len(message_bytes) >= 3:
                    pitch_value = (message_bytes[2] << 7) | message_bytes[1]
                    message.update({
                        'type': 'pitch_bend',
                        'pitch': pitch_value,
                        'data': [message_bytes[1], message_bytes[2]]
                    })
                    return message

            elif message_type == 0xF:  # System Messages
                if status_byte == 0xF0 or status_byte == 0xF7:  # SysEx
                    message.update({
                        'type': 'sysex',
                        'sysex_data': list(message_bytes[1:])  # Exclude status byte
                    })
                    return message

        except (IndexError, ValueError):
            return None

        return None

    def is_sysex_message(self, message_bytes: bytes) -> bool:
        """
        Check if message bytes represent a System Exclusive message.

        Args:
            message_bytes: Raw message bytes

        Returns:
            True if this is a SysEx message
        """
        if len(message_bytes) < 3:
            return False

        status_byte = message_bytes[0]
        return status_byte == 0xF0 or status_byte == 0xF7

    def extract_sysex_data(self, message_bytes: bytes) -> Optional[bytes]:
        """
        Extract SysEx data from a SysEx message.

        Args:
            message_bytes: Raw SysEx message bytes

        Returns:
            SysEx data bytes or None if not a valid SysEx message
        """
        if not self.is_sysex_message(message_bytes):
            return None

        # Return data excluding start/end markers
        return message_bytes[1:-1] if len(message_bytes) > 2 else message_bytes[1:]


# Global instance for efficiency
_binary_parser = BinaryMIDIParser()


def parse_binary_message(message_bytes: bytes, timestamp: float = 0.0) -> Optional[MIDIMessage]:
    """
    Convenience function to parse raw MIDI message bytes.

    Args:
        message_bytes: Raw MIDI message bytes
        timestamp: Optional timestamp in seconds

    Returns:
        MIDIMessage object or None if invalid
    """
    return _binary_parser.parse_message(message_bytes, timestamp)
