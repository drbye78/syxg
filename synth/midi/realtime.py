"""
Real-time MIDI Processing

Handles real-time MIDI input processing for live synthesizer control.
Converts raw MIDI bytes to structured messages and manages real-time message buffering.
"""

import time
from typing import List, Optional, Callable
import threading

from .message import MIDIMessage
from .types import MIDIStatus, get_message_type_from_status


class RealtimeParser:
    """
    Real-time MIDI byte parser for live synthesizer input.

    Converts raw MIDI bytes from devices into structured MIDIMessage objects
    with proper running status handling and system exclusive processing.
    """

    def __init__(self):
        """Initialize the real-time MIDI parser."""
        self.last_status = 0x00  # For running status support
        self.sysex_buffer: List[int] = []
        self.in_sysex = False
        self.lock = threading.RLock()

    def parse_bytes(self, data: bytes) -> List[MIDIMessage]:
        """
        Parse raw MIDI bytes into structured messages.

        Args:
            data: Raw MIDI byte data

        Returns:
            List of parsed MIDIMessage objects
        """
        with self.lock:
            messages = []

            for byte in data:
                message = self._parse_byte(byte)
                if message:
                    messages.append(message)

            return messages

    def _parse_byte(self, byte: int) -> Optional[MIDIMessage]:
        """
        Parse a single MIDI byte.

        Args:
            byte: MIDI byte value (0-255)

        Returns:
            Parsed MIDIMessage or None if incomplete
        """
        # Handle system exclusive
        if self.in_sysex:
            if byte == MIDIStatus.END_OF_EXCLUSIVE:
                # End of sysex
                self.in_sysex = False
                sysex_data = self.sysex_buffer.copy()
                self.sysex_buffer.clear()

                # Create sysex message
                return MIDIMessage(
                    type='sysex',
                    data={'raw_data': sysex_data}
                )
            else:
                # Continue collecting sysex data
                self.sysex_buffer.append(byte)
            return None

        # Check for status byte
        if byte & 0x80:
            # Status byte - handle system messages
            if byte == MIDIStatus.SYSTEM_EXCLUSIVE:
                # Start of system exclusive
                self.in_sysex = True
                self.sysex_buffer.clear()
                return None
            elif byte >= MIDIStatus.SYSTEM_RESET:
                # System real-time message (doesn't affect running status)
                return self._parse_system_message(byte)
            else:
                # Channel message status - update running status
                self.last_status = byte
                return None
        else:
            # Data byte - use running status if available
            if self.last_status == 0x00:
                return None  # No previous status to use

            status = self.last_status
            return self._parse_channel_message(status, byte)

    def _parse_system_message(self, status: int) -> Optional[MIDIMessage]:
        """Parse system real-time message."""
        message_type = get_message_type_from_status(status)

        # System real-time messages have no data
        return MIDIMessage(type=message_type)

    def _parse_channel_message(self, status: int, first_data: int) -> Optional[MIDIMessage]:
        """
        Parse channel message with first data byte.

        For real-time parsing, we only handle messages that can be completed
        with the first data byte (program change, channel pressure) or assume
        standard 2-byte format for others.
        """
        message_type = get_message_type_from_status(status)
        channel = status & 0x0F

        if message_type in ('program_change', 'channel_pressure'):
            # Single data byte messages
            return MIDIMessage(
                type=message_type,
                channel=channel,
                data={message_type.split('_')[1]: first_data}
            )
        else:
            # Assume 2-byte message format for real-time (velocity=0 for simplicity)
            if message_type == 'note_on':
                return MIDIMessage(
                    type='note_on',
                    channel=channel,
                    data={'note': first_data, 'velocity': 64}  # Default velocity
                )
            elif message_type == 'note_off':
                return MIDIMessage(
                    type='note_off',
                    channel=channel,
                    data={'note': first_data, 'velocity': 0}
                )
            elif message_type == 'control_change':
                return MIDIMessage(
                    type='control_change',
                    channel=channel,
                    data={'controller': first_data, 'value': 0}  # Default value
                )
            elif message_type == 'pitch_bend':
                return MIDIMessage(
                    type='pitch_bend',
                    channel=channel,
                    data={'value': first_data}  # Partial pitch bend
                )
            elif message_type == 'poly_pressure':
                return MIDIMessage(
                    type='poly_pressure',
                    channel=channel,
                    data={'note': first_data, 'pressure': 0}  # Default pressure
                )

        return None

    def reset(self):
        """Reset parser to clean state."""
        with self.lock:
            self.last_status = 0x00
            self.sysex_buffer.clear()
            self.in_sysex = False


class BufferedProcessor:
    """
    Unified buffered MIDI message processor with optional optimization.

    Provides time-ordered message buffering and processing for both
    real-time and sequenced MIDI applications.
    """

    def __init__(self, sample_rate: float = 44100.0, optimized: bool = False):
        """
        Initialize buffered processor.

        Args:
            sample_rate: Sample rate in Hz
            optimized: Whether to use optimized (NumPy-based) processing
        """
        self.sample_rate = sample_rate
        self.optimized = optimized

        # Message heaps for time-ordered processing
        self.message_heap: List[tuple] = []  # (time, priority, message)
        self.sysex_heap: List[tuple] = []    # (time, priority, message)

        # Current time tracking
        self.current_time = 0.0
        self.block_start_time = 0.0

        # Sample times for current block
        if optimized:
            import numpy as np
            self.sample_times = np.zeros(1024, dtype=np.float64)
        else:
            self.sample_times = [0.0] * 1024

        # Priority counter for stable sorting
        self.priority_counter = 0

        # Thread safety
        self.lock = threading.RLock()

    def send_message(self, message: MIDIMessage, timestamp: Optional[float] = None):
        """
        Send a MIDI message at specified time.

        Args:
            message: MIDIMessage to send
            timestamp: Time to send message (uses message.timestamp if None)
        """
        with self.lock:
            send_time = timestamp or message.timestamp
            priority = self.priority_counter
            self.priority_counter += 1

            import heapq
            heapq.heappush(self.message_heap, (send_time, priority, message))

    def send_sysex_message(self, message: MIDIMessage, timestamp: Optional[float] = None):
        """
        Send a System Exclusive message at specified time.

        Args:
            message: SYSEX MIDIMessage to send
            timestamp: Time to send message
        """
        with self.lock:
            send_time = timestamp or message.timestamp
            priority = self.priority_counter
            self.priority_counter += 1

            import heapq
            heapq.heappush(self.sysex_heap, (send_time, priority, message))

    def process_until_time(self, target_time: float) -> List[MIDIMessage]:
        """
        Process all messages up to specified time.

        Args:
            target_time: Target time to process messages

        Returns:
            List of messages processed
        """
        with self.lock:
            processed = []
            import heapq

            # Process regular messages
            while self.message_heap and self.message_heap[0][0] <= target_time:
                _, _, message = heapq.heappop(self.message_heap)
                processed.append(message)

            # Process SYSEX messages
            while self.sysex_heap and self.sysex_heap[0][0] <= target_time:
                _, _, message = heapq.heappop(self.sysex_heap)
                processed.append(message)

            return processed

    def get_next_message_time(self) -> Optional[float]:
        """Get timestamp of next pending message."""
        with self.lock:
            next_times = []

            if self.message_heap:
                next_times.append(self.message_heap[0][0])
            if self.sysex_heap:
                next_times.append(self.sysex_heap[0][0])

            return min(next_times) if next_times else None

    def clear(self):
        """Clear all buffered messages."""
        with self.lock:
            self.message_heap.clear()
            self.sysex_heap.clear()
            self.priority_counter = 0

    def set_block_start_time(self, start_time: float):
        """Set the start time of current audio block."""
        self.block_start_time = start_time

    def prepare_sample_times(self, block_size: int):
        """Prepare timestamp array for sample-accurate processing."""
        if self.optimized:
            import numpy as np
            if len(self.sample_times) < block_size:
                self.sample_times = np.resize(self.sample_times, block_size)

            sample_duration = 1.0 / self.sample_rate
            self.sample_times[:block_size] = np.linspace(
                self.block_start_time,
                self.block_start_time + (block_size * sample_duration),
                block_size,
                endpoint=False
            )
        else:
            # For non-optimized mode (list)
            if isinstance(self.sample_times, list):
                if len(self.sample_times) < block_size:
                    # Extend list for non-optimized mode
                    self.sample_times.extend([0.0] * (block_size - len(self.sample_times)))

                sample_duration = 1.0 / self.sample_rate
                for i in range(block_size):
                    self.sample_times[i] = self.block_start_time + (i * sample_duration)
