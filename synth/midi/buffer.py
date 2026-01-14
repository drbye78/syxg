"""
Unified Buffered MIDI Processing

Time-ordered message buffering and processing for both real-time and sequenced MIDI.
Provides a clean interface for managing MIDI message timing and delivery.
"""

import heapq
from typing import List, Optional, Tuple
import threading

from .message import MIDIMessage


class MessageBuffer:
    """
    Unified buffered MIDI message processor.

    Handles time-ordered message buffering and processing for both
    real-time and sequenced MIDI applications. Provides efficient
    message scheduling and retrieval based on timestamps.
    """

    def __init__(self, sample_rate: float = 44100.0):
        """
        Initialize message buffer.

        Args:
            sample_rate: Sample rate in Hz for timing calculations
        """
        self.sample_rate = sample_rate

        # Message heaps for time-ordered processing
        self.message_heap: List[Tuple[float, int, MIDIMessage]] = []  # (time, priority, message)
        self.sysex_heap: List[Tuple[float, int, MIDIMessage]] = []    # (time, priority, message)

        # Current time tracking
        self.current_time = 0.0
        self.block_start_time = 0.0

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

            # Process regular messages
            while self.message_heap and self.message_heap[0][0] <= target_time:
                _, _, message = heapq.heappop(self.message_heap)
                processed.append(message)

            # Process SYSEX messages
            while self.sysex_heap and self.sysex_heap[0][0] <= target_time:
                _, _, message = heapq.heappop(self.sysex_heap)
                processed.append(message)

            return processed

    def get_messages_in_range(self, start_time: float, end_time: float) -> List[MIDIMessage]:
        """
        Get all messages within a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of messages in the range (preserving timestamps)
        """
        with self.lock:
            messages = []

            # Collect messages in range without removing them
            for time_val, _, message in self.message_heap:
                if start_time <= time_val <= end_time:
                    messages.append(message)

            for time_val, _, message in self.sysex_heap:
                if start_time <= time_val <= end_time:
                    messages.append(message)

            # Sort by time
            messages.sort(key=lambda msg: msg.timestamp)

            return messages

    def get_next_message_time(self) -> Optional[float]:
        """Get timestamp of next pending message."""
        with self.lock:
            next_times = []

            if self.message_heap:
                next_times.append(self.message_heap[0][0])
            if self.sysex_heap:
                next_times.append(self.sysex_heap[0][0])

            return min(next_times) if next_times else None

    def peek_next_message(self) -> Optional[MIDIMessage]:
        """Peek at the next message without removing it."""
        with self.lock:
            candidates = []

            if self.message_heap:
                candidates.append((self.message_heap[0][0], self.message_heap[0][2]))
            if self.sysex_heap:
                candidates.append((self.sysex_heap[0][0], self.sysex_heap[0][2]))

            if not candidates:
                return None

            # Return message with earliest timestamp
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

    def clear(self):
        """Clear all buffered messages."""
        with self.lock:
            self.message_heap.clear()
            self.sysex_heap.clear()
            self.priority_counter = 0

    def set_current_time(self, time: float):
        """Set current time for processing."""
        self.current_time = time

    def get_pending_count(self) -> int:
        """Get number of pending messages."""
        with self.lock:
            return len(self.message_heap) + len(self.sysex_heap)

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self.lock:
            return not self.message_heap and not self.sysex_heap

    def get_buffer_info(self) -> dict:
        """Get buffer status information."""
        with self.lock:
            return {
                'pending_messages': len(self.message_heap),
                'pending_sysex': len(self.sysex_heap),
                'total_pending': self.get_pending_count(),
                'next_message_time': self.get_next_message_time(),
                'current_time': self.current_time,
                'block_start_time': self.block_start_time
            }
