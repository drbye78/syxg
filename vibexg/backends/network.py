"""
Vibexg Network Backend - RTP-MIDI / AppleMIDI implementation

This module provides network MIDI (RTP-MIDI / AppleMIDI) connection handling.
"""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable

from synth.io.midi import MIDIMessage

logger = logging.getLogger(__name__)


class NetworkMIDIHandler:
    """
    Handles network MIDI (RTP-MIDI / AppleMIDI) connections.

    This class implements a UDP-based network MIDI server that can receive
    MIDI messages over the network using the RTP-MIDI protocol.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5004):
        """
        Initialize the network MIDI handler.

        Args:
            host: Host address to bind to (default: 0.0.0.0)
            port: Port number for RTP-MIDI (default: 5004)
        """
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.thread: threading.Thread | None = None
        self.connected_peers: list[tuple[str, int]] = []
        self.message_callback: Callable | None = None

    def start(self, callback: Callable):
        """
        Start network MIDI server.

        Args:
            callback: Function to call with received MIDIMessage objects
        """
        self.message_callback = callback

        try:
            # Create UDP socket for RTP-MIDI
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)

            self.running = True
            self.thread = threading.Thread(target=self._receive_thread, daemon=True)
            self.thread.start()

            logger.info(f"Network MIDI server started on {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start network MIDI: {e}")

    def stop(self):
        """Stop network MIDI server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.socket:
            self.socket.close()

    def _receive_thread(self):
        """Receive network MIDI packets."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)

                if addr not in self.connected_peers:
                    self.connected_peers.append(addr)
                    logger.info(f"Network MIDI peer connected: {addr}")

                # Parse RTP-MIDI packet (simplified)
                messages = self._parse_rtpmidi_packet(data)

                for msg in messages:
                    if self.message_callback:
                        self.message_callback(msg)

            except TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Network MIDI receive error: {e}")

    def _parse_rtpmidi_packet(self, data: bytes) -> list[MIDIMessage]:
        """
        Parse RTP-MIDI packet to MIDIMessages.

        Note: This is a simplified RTP-MIDI parsing implementation.
        Full implementation would handle:
        - RTP header
        - MIDI list header
        - Recovery journal
        - MIDI command recovery

        Args:
            data: Raw RTP-MIDI packet data

        Returns:
            List of parsed MIDIMessage objects
        """
        messages = []

        # Skip RTP header (typically 12 bytes) and MIDI list header
        offset = 0

        # Check for RTP-MIDI signature
        if len(data) > 4 and data[0:4] == b"\x00\x00\x00\x00":
            offset = 4  # Simple header

        # Parse MIDI commands
        while offset < len(data):
            byte = data[offset]
            offset += 1

            if byte & 0x80:  # Status byte
                status = byte
                if status in [0x80, 0x90, 0xA0, 0xB0, 0xE0]:  # 2 data bytes
                    if offset + 1 < len(data):
                        data1 = data[offset]
                        data2 = data[offset + 1]
                        offset += 2

                        msg = self._create_midimessage(status, data1, data2)
                        if msg:
                            messages.append(msg)

                elif status in [0xC0, 0xD0]:  # 1 data byte
                    if offset < len(data):
                        data1 = data[offset]
                        offset += 1

                        msg = self._create_midimessage(status, data1, 0)
                        if msg:
                            messages.append(msg)

        return messages

    def _create_midimessage(self, status: int, data1: int, data2: int) -> MIDIMessage | None:
        """
        Create MIDIMessage from status and data bytes.

        Args:
            status: MIDI status byte
            data1: First data byte
            data2: Second data byte

        Returns:
            MIDIMessage object or None if invalid
        """
        msg_type = (status >> 4) & 0x0F
        channel = status & 0x0F

        if msg_type == 0x8:
            return MIDIMessage(
                type="note_off", channel=channel, data={"note": data1, "velocity": data2}
            )
        elif msg_type == 0x9:
            return MIDIMessage(
                type="note_on", channel=channel, data={"note": data1, "velocity": data2}
            )
        elif msg_type == 0xB:
            return MIDIMessage(
                type="control_change", channel=channel, data={"controller": data1, "value": data2}
            )
        elif msg_type == 0xC:
            return MIDIMessage(type="program_change", channel=channel, data={"program": data1})
        elif msg_type == 0xE:
            pitch_value = (data2 << 7) | data1
            return MIDIMessage(type="pitch_bend", channel=channel, data={"value": pitch_value})

        return None
