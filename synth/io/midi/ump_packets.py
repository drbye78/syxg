"""
Universal MIDI Packet (UMP) Implementation for MIDI 2.0 Support

This module implements the complete UMP specification for MIDI 2.0 support,
including packet parsing, serialization, and conversion between MIDI 1.0 and MIDI 2.0 formats.
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from enum import IntEnum


class UMPMessageType(IntEnum):
    """UMP Message Type Identifiers (UMPI)"""

    MIDI_2_CHANNEL = 0x2  # MIDI 2.0 Channel Voice Messages
    MIDI_1_CHANNEL = 0x1  # MIDI 1.0 Channel Voice Messages
    SYSEX = 0x3  # System Exclusive
    SYS_COMMON = 0x4  # System Common Messages
    SYS_RT = 0x5  # System Real-Time Messages
    POWER = 0x6  # Power Messages
    EXTENDED = 0x7  # Extended Messages
    UTILITY = 0x4  # Utility Messages (when in 32-bit format)


class UMPGroup(int):
    """UMP Group (4 bits) - represents the MIDI port/group"""

    def __new__(cls, value: int):
        if not 0 <= value <= 15:
            raise ValueError("UMP Group must be between 0 and 15")
        return super().__new__(cls, value)


class UMPPacket(ABC):
    """Base class for Universal MIDI Packets"""

    def __init__(self, ump_type: UMPMessageType, group: UMPGroup = UMPGroup(0)):
        self.ump_type = ump_type
        self.group = group

    @abstractmethod
    def to_bytes(self) -> bytes:
        """Convert packet to bytes representation"""
        pass

    @abstractmethod
    def to_words(self) -> list[int]:
        """Convert packet to 32-bit word array"""
        pass


class MIDI2ChannelVoicePacket(UMPPacket):
    """MIDI 2.0 Channel Voice Message Packet (64-bit)"""

    def __init__(
        self, group: UMPGroup, channel: int, message_type: int, data_word_1: int, data_word_2: int
    ):
        super().__init__(UMPMessageType.MIDI_2_CHANNEL, group)
        if not 0 <= channel <= 15:
            raise ValueError("Channel must be between 0 and 15")
        if not 0 <= message_type <= 15:
            raise ValueError("Message type must be between 0 and 15")
        if not 0 <= data_word_1 <= 0xFFFFFFFF:
            raise ValueError("Data word 1 must be a valid 32-bit value")
        if not 0 <= data_word_2 <= 0xFFFFFFFF:
            raise ValueError("Data word 2 must be a valid 32-bit value")

        self.channel = channel
        self.message_type = message_type  # Upper nibble of status byte
        self.data_word_1 = data_word_1
        self.data_word_2 = data_word_2

    def to_words(self) -> list[int]:
        """Convert to 2-word (64-bit) UMP representation"""
        header = (
            (self.ump_type << 28)
            | (self.group << 24)
            | (self.message_type << 20)
            | (self.channel << 16)
        )
        return [header | (self.data_word_1 & 0xFFFF), self.data_word_2]

    def to_bytes(self) -> bytes:
        """Convert to 8-byte representation"""
        words = self.to_words()
        return struct.pack(">II", words[0], words[1])

    @classmethod
    def from_words(cls, words: list[int]) -> MIDI2ChannelVoicePacket | None:
        """Parse from 2-word (64-bit) UMP representation"""
        if len(words) < 2:
            return None

        header = words[0]
        ump_type = (header >> 28) & 0xF
        if ump_type != UMPMessageType.MIDI_2_CHANNEL:
            return None

        group = UMPGroup((header >> 24) & 0xF)
        message_type = (header >> 20) & 0xF
        channel = (header >> 16) & 0xF
        data_word_1 = header & 0xFFFF
        data_word_2 = words[1]

        return cls(group, channel, message_type, data_word_1, data_word_2)

    def get_status_byte(self) -> int:
        """Get the MIDI 2.0 status byte"""
        return (self.message_type << 4) | self.channel

    def get_property_data(self) -> tuple[int, int, int, int]:
        """Get property data fields (for Property Exchange messages)"""
        # For property exchange messages, data is organized differently
        property_id = (self.data_word_1 >> 24) & 0xFF
        property_index = (self.data_word_1 >> 16) & 0xFF
        data_type = (self.data_word_1 >> 8) & 0xFF
        value = self.data_word_1 & 0xFF
        return property_id, property_index, data_type, value


class MIDI1ChannelVoicePacket(UMPPacket):
    """MIDI 1.0 Channel Voice Message Packet (32-bit)"""

    def __init__(self, group: UMPGroup, status_byte: int, data1: int = 0, data2: int = 0):
        super().__init__(UMPMessageType.MIDI_1_CHANNEL, group)
        if not 0x80 <= status_byte <= 0xEF:
            raise ValueError("Status byte must be between 0x80 and 0xEF for channel messages")
        if not 0 <= data1 <= 127:
            raise ValueError("Data byte 1 must be between 0 and 127")
        if not 0 <= data2 <= 127:
            raise ValueError("Data byte 2 must be between 0 and 127")

        self.status_byte = status_byte
        self.data1 = data1
        self.data2 = data2

    def to_words(self) -> list[int]:
        """Convert to 1-word (32-bit) UMP representation"""
        header = (
            (self.ump_type << 28)
            | (self.group << 24)
            | (self.status_byte << 16)
            | (self.data1 << 8)
            | self.data2
        )
        return [header]

    def to_bytes(self) -> bytes:
        """Convert to 4-byte representation"""
        word = self.to_words()[0]
        return struct.pack(">I", word)

    @classmethod
    def from_words(cls, words: list[int]) -> MIDI1ChannelVoicePacket | None:
        """Parse from 1-word (32-bit) UMP representation"""
        if len(words) < 1:
            return None

        header = words[0]
        ump_type = (header >> 28) & 0xF
        if ump_type != UMPMessageType.MIDI_1_CHANNEL:
            return None

        group = UMPGroup((header >> 24) & 0xF)
        status_byte = (header >> 16) & 0xFF
        data1 = (header >> 8) & 0xFF
        data2 = header & 0xFF

        return cls(group, status_byte, data1, data2)


class SysExUMP(UMPPacket):
    """System Exclusive UMP (128-bit, 256-bit, 512-bit, etc.)"""

    def __init__(self, group: UMPGroup, sys_ex_data: bytes, complete: bool = True):
        super().__init__(UMPMessageType.SYSEX, group)
        self.sys_ex_data = sys_ex_data
        self.complete = complete  # True if this is a complete SysEx message

    def to_words(self) -> list[int]:
        """Convert to UMP word array (variable length)"""
        # Calculate number of 32-bit words needed
        data_len = len(self.sys_ex_data)
        num_words = (data_len + 3) // 4  # Round up to nearest 4-byte boundary

        # Create header word
        header = (
            (self.ump_type << 28)
            | (self.group << 24)
            | ((num_words - 1) << 16)
            | (0x00 if self.complete else 0x01)
        )
        words = [header]

        # Add data words
        for i in range(0, data_len, 4):
            chunk = self.sys_ex_data[i : i + 4]
            # Pad with zeros if needed
            chunk = chunk.ljust(4, b"\x00")
            word = struct.unpack(">I", chunk)[0]
            words.append(word)

        return words

    def to_bytes(self) -> bytes:
        """Convert to byte representation"""
        words = self.to_words()
        byte_data = b""
        for word in words:
            byte_data += struct.pack(">I", word)
        return byte_data

    @classmethod
    def from_words(cls, words: list[int]) -> SysExUMP | None:
        """Parse from UMP word array"""
        if len(words) < 1:
            return None

        header = words[0]
        ump_type = (header >> 28) & 0xF
        if ump_type != UMPMessageType.SYSEX:
            return None

        group = UMPGroup((header >> 24) & 0xF)
        num_data_words = ((header >> 16) & 0xFF) + 1
        complete = ((header >> 8) & 0xFF) == 0x00

        if len(words) < num_data_words + 1:
            return None  # Not enough words

        # Extract data
        sys_ex_data = b""
        for i in range(1, min(len(words), num_data_words + 1)):
            word = words[i]
            sys_ex_data += struct.pack(">I", word)

        # Remove padding zeros
        sys_ex_data = sys_ex_data.rstrip(b"\x00")

        return cls(group, sys_ex_data, complete)


class UtilityUMP(UMPPacket):
    """Utility Message UMP (32-bit)"""

    def __init__(self, group: UMPGroup, utility_type: int, data: int = 0):
        super().__init__(UMPMessageType.UTILITY, group)
        if not 0 <= utility_type <= 15:
            raise ValueError("Utility type must be between 0 and 15")
        if not 0 <= data <= 0xFFFF:
            raise ValueError("Data must be between 0 and 0xFFFF")

        self.utility_type = utility_type  # 0x0=Reserved, 0x1=JRTS, 0x2=MIDI Time Code, etc.
        self.data = data

    def to_words(self) -> list[int]:
        """Convert to 1-word (32-bit) UMP representation"""
        header = (self.ump_type << 28) | (self.group << 24) | (self.utility_type << 16) | self.data
        return [header]

    def to_bytes(self) -> bytes:
        """Convert to 4-byte representation"""
        word = self.to_words()[0]
        return struct.pack(">I", word)

    @classmethod
    def from_words(cls, words: list[int]) -> UtilityUMP | None:
        """Parse from 1-word (32-bit) UMP representation"""
        if len(words) < 1:
            return None

        header = words[0]
        ump_type = (header >> 28) & 0xF
        if ump_type != UMPMessageType.UTILITY:
            return None

        group = UMPGroup((header >> 24) & 0xF)
        utility_type = (header >> 16) & 0xFF
        data = header & 0xFFFF

        return cls(group, utility_type, data)


class UMPParser:
    """Universal MIDI Packet Parser for MIDI 2.0"""

    @staticmethod
    def parse_packet(packet_bytes: bytes) -> UMPPacket | None:
        """Parse a UMP packet from bytes"""
        if len(packet_bytes) < 4:
            return None

        # Convert first 4 bytes to get header
        header = struct.unpack(">I", packet_bytes[:4])[0]
        ump_type = (header >> 28) & 0xF
        group = UMPGroup((header >> 24) & 0xF)

        if ump_type == UMPMessageType.MIDI_2_CHANNEL:
            if len(packet_bytes) < 8:
                return None
            word1 = header
            word2 = struct.unpack(">I", packet_bytes[4:8])[0]
            return MIDI2ChannelVoicePacket.from_words([word1, word2])

        elif ump_type == UMPMessageType.MIDI_1_CHANNEL:
            return MIDI1ChannelVoicePacket.from_words([header])

        elif ump_type == UMPMessageType.SYSEX:
            # Need to determine how many words based on header
            num_data_words = ((header >> 16) & 0xFF) + 1
            total_bytes_needed = (num_data_words + 1) * 4  # +1 for header

            if len(packet_bytes) < total_bytes_needed:
                return None  # Incomplete packet

            words = []
            for i in range(0, total_bytes_needed, 4):
                if i + 4 <= len(packet_bytes):
                    word = struct.unpack(">I", packet_bytes[i : i + 4])[0]
                    words.append(word)

            return SysExUMP.from_words(words)

        elif ump_type == UMPMessageType.UTILITY:
            return UtilityUMP.from_words([header])

        else:
            # Unsupported or unknown UMP type
            return None

    @staticmethod
    def parse_packet_stream(data: bytes) -> list[UMPPacket]:
        """Parse a stream of UMP packets"""
        packets = []
        offset = 0

        while offset < len(data):
            # Look at the first byte to determine packet size
            if offset + 4 > len(data):
                break  # Not enough data for a header

            header = struct.unpack(">I", data[offset : offset + 4])[0]
            ump_type = (header >> 28) & 0xF

            # Determine packet size based on UMP type
            if ump_type == UMPMessageType.MIDI_2_CHANNEL:
                packet_size = 8  # 64-bit packet
            elif ump_type == UMPMessageType.MIDI_1_CHANNEL:
                packet_size = 4  # 32-bit packet
            elif ump_type == UMPMessageType.UTILITY:
                packet_size = 4  # 32-bit packet
            elif ump_type == UMPMessageType.SYSEX:
                num_data_words = ((header >> 16) & 0xFF) + 1
                packet_size = (num_data_words + 1) * 4  # Header + data words
            else:
                # Unknown packet type, skip 4 bytes and continue
                offset += 4
                continue

            if offset + packet_size > len(data):
                # Incomplete packet at end, break
                break

            # Parse the packet
            packet_data = data[offset : offset + packet_size]
            packet = UMPParser.parse_packet(packet_data)
            if packet:
                packets.append(packet)

            offset += packet_size

        return packets


class MIDI1ToMIDI2Converter:
    """Converter between MIDI 1.0 and MIDI 2.0 messages"""

    @staticmethod
    def midi1_to_midi2_channel_voice(
        status_byte: int, data1: int, data2: int
    ) -> MIDI2ChannelVoicePacket:
        """Convert MIDI 1.0 channel voice message to MIDI 2.0 format"""
        channel = status_byte & 0x0F
        message_type = (status_byte >> 4) & 0x0F

        # Convert MIDI 1.0 data to MIDI 2.0 32-bit format
        # MIDI 2.0 uses 32-bit values with different resolutions:
        # - Note/CC numbers: 8-bit unsigned
        # - Velocities: 32-bit unsigned (scaled from 7-bit)
        # - Controller values: 32-bit unsigned (scaled from 7-bit)
        # - Pitch bend: 32-bit signed (centered at 0x7FFFFFFF)

        if message_type == 0x8:  # Note Off
            data_word_1 = (data1 & 0xFF) << 24  # Note number
            data_word_2 = (data2 & 0xFF) << 24  # Release velocity
        elif message_type == 0x9:  # Note On
            data_word_1 = (data1 & 0xFF) << 24  # Note number
            data_word_2 = (data2 & 0xFF) << 24  # Velocity
        elif message_type == 0xA:  # Poly Pressure
            data_word_1 = (data1 & 0xFF) << 24  # Note number
            data_word_2 = (data2 & 0xFF) << 24  # Pressure
        elif message_type == 0xB:  # Control Change
            data_word_1 = (data1 & 0xFF) << 24  # Controller number
            data_word_2 = (data2 & 0xFF) << 24  # Controller value
        elif message_type == 0xC:  # Program Change
            data_word_1 = (data1 & 0xFF) << 24  # Program number
            data_word_2 = 0  # Unused
        elif message_type == 0xD:  # Channel Pressure
            data_word_1 = (data1 & 0xFF) << 24  # Pressure
            data_word_2 = 0  # Unused
        elif message_type == 0xE:  # Pitch Bend
            # MIDI 1.0 pitch bend is 14-bit (0-16383), centered at 8192
            # MIDI 2.0 pitch bend is 32-bit, centered at 0x7FFFFFFF
            pitch_14bit = (data2 << 7) | data1
            pitch_32bit = ((pitch_14bit - 8192) * (0x7FFFFFFF // 8192)) + 0x7FFFFFFF
            data_word_1 = pitch_32bit & 0xFFFFFFFF
            data_word_2 = 0  # Unused
        else:
            # Unknown message type, use raw conversion
            data_word_1 = (data1 & 0xFF) << 24
            data_word_2 = (data2 & 0xFF) << 24

        return MIDI2ChannelVoicePacket(UMPGroup(0), channel, message_type, data_word_1, data_word_2)

    @staticmethod
    def midi2_to_midi1_channel_voice(packet: MIDI2ChannelVoicePacket) -> tuple[int, int, int]:
        """Convert MIDI 2.0 channel voice message to MIDI 1.0 format"""
        status_byte = (packet.message_type << 4) | packet.channel

        # Extract data based on message type
        if packet.message_type == 0x8:  # Note Off
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Note number
            data2 = (packet.data_word_2 >> 24) & 0xFF  # Release velocity
        elif packet.message_type == 0x9:  # Note On
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Note number
            data2 = (packet.data_word_2 >> 24) & 0xFF  # Velocity
        elif packet.message_type == 0xA:  # Poly Pressure
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Note number
            data2 = (packet.data_word_2 >> 24) & 0xFF  # Pressure
        elif packet.message_type == 0xB:  # Control Change
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Controller number
            data2 = (packet.data_word_2 >> 24) & 0xFF  # Controller value
        elif packet.message_type == 0xC:  # Program Change
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Program number
            data2 = 0  # Unused
        elif packet.message_type == 0xD:  # Channel Pressure
            data1 = (packet.data_word_1 >> 24) & 0xFF  # Pressure
            data2 = 0  # Unused
        elif packet.message_type == 0xE:  # Pitch Bend
            # MIDI 2.0 pitch bend is 32-bit, centered at 0x7FFFFFFF
            # MIDI 1.0 pitch bend is 14-bit (0-16383), centered at 8192
            pitch_32bit = packet.data_word_1
            pitch_14bit = ((pitch_32bit - 0x7FFFFFFF) * (8192 // 0x7FFFFFFF)) + 8192
            pitch_14bit = max(0, min(16383, pitch_14bit))  # Clamp to valid range
            data1 = pitch_14bit & 0x7F  # LSB
            data2 = (pitch_14bit >> 7) & 0x7F  # MSB
        else:
            # Unknown message type
            data1 = (packet.data_word_1 >> 24) & 0xFF
            data2 = (packet.data_word_2 >> 24) & 0xFF

        return status_byte, data1, data2


# Example usage and testing
if __name__ == "__main__":
    # Test MIDI 1.0 to MIDI 2.0 conversion
    print("Testing MIDI 1.0 to MIDI 2.0 conversion...")

    # Test Note On
    status, d1, d2 = 0x90, 60, 100  # Note On, middle C, velocity 100
    midi2_packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(status, d1, d2)
    print(f"MIDI 1.0: {hex(status)}, {d1}, {d2}")
    print(f"MIDI 2.0 packet words: {midi2_packet.to_words()}")

    # Convert back
    status_back, d1_back, d2_back = MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2_packet)
    print(f"Converted back: {hex(status_back)}, {d1_back}, {d2_back}")
    print(f"Match: {status == status_back and d1 == d1_back and d2 == d2_back}")

    # Test SysEx
    print("\nTesting SysEx UMP...")
    sys_ex_data = bytes([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7])  # Example SysEx
    sys_ex_packet = SysExUMP(UMPGroup(0), sys_ex_data, complete=True)
    print(f"SysEx packet words: {sys_ex_packet.to_words()}")

    # Test parsing
    print("\nTesting UMP parsing...")
    packet_bytes = sys_ex_packet.to_bytes()
    parsed_packet = UMPParser.parse_packet(packet_bytes)
    if isinstance(parsed_packet, SysExUMP):
        print(f"Parsed SysEx data: {parsed_packet.sys_ex_data}")
        print(f"Complete: {parsed_packet.complete}")
