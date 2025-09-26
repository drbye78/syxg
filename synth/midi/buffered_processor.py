"""
XG Synthesizer Buffered Processor

Handles buffered MIDI message processing with sample-accurate timing synchronization.
"""

import heapq
from typing import List, Tuple, Optional, Dict, Any
from collections import deque


class BufferedProcessor:
    """
    Handles buffered MIDI message processing with sample-accurate timing.

    Provides functionality for:
    - Buffered MIDI message storage and retrieval
    - Sample-accurate timing synchronization
    - Message heap management for time-ordered processing
    - Frame-by-frame message processing
    - SYSEX message buffering and processing
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize buffered processor.

        Args:
            sample_rate: Sample rate in Hz for timing calculations
        """
        self.sample_rate = sample_rate

        # Message heaps for time-ordered processing
        # (time, priority, status, data1, data2)
        self.message_heap: List[Tuple[float, int, int, int, int]] = []

        # (time, priority, sysex_data)
        self.sysex_heap: List[Tuple[float, int, List[int]]] = []

        # Current time for buffered mode
        self.current_time: float = 0.0

        # Block start time for sample-accurate processing
        self.block_start_time: float = 0.0

        # Sample times for current block
        self.sample_times: List[float] = []

        # Message priority counter for stable sorting
        self.message_priority_counter: int = 0

        # Message buffers for immediate processing
        self.message_buffer: List[Tuple[float, int, int, int]] = []  # (time, status, data1, data2)
        self.sysex_buffer: List[Tuple[float, List[int]]] = []  # (time, sysex_data)

    def send_midi_message_at_time(self, status: int, data1: int, data2: int, time: float):
        """
        Send MIDI message at specified time.

        Args:
            status: MIDI status byte
            data1: First data byte
            data2: Second data byte
            time: Time in seconds to process message
        """
        # Add message to heap with unique priority for stable sorting
        priority = self.message_priority_counter
        self.message_priority_counter += 1

        heapq.heappush(self.message_heap, (time, priority, status, data1, data2))

    def send_sysex_at_time(self, data: List[int], time: float):
        """
        Send SYSEX message at specified time.

        Args:
            data: SYSEX message data
            time: Time in seconds to process message
        """
        # Add message to heap with unique priority for stable sorting
        priority = self.message_priority_counter
        self.message_priority_counter += 1

        heapq.heappush(self.sysex_heap, (time, priority, data))

    def send_midi_message_at_sample(self, status: int, data1: int, data2: int, sample: int):
        """
        Send MIDI message at specified sample.

        Args:
            status: MIDI status byte
            data1: First data byte
            data2: Second data byte
            sample: Sample number to process message
        """
        # Convert sample number to absolute time
        message_time = self.block_start_time + (sample / self.sample_rate)
        self.send_midi_message_at_time(status, data1, data2, message_time)

    def send_sysex_at_sample(self, data: List[int], sample: int):
        """
        Send SYSEX message at specified sample.

        Args:
            data: SYSEX message data
            sample: Sample number to process message
        """
        # Convert sample number to absolute time
        message_time = self.block_start_time + (sample / self.sample_rate)
        self.send_sysex_at_time(data, message_time)

    def send_midi_message_block(self, messages: List[Tuple[float, int, int, int]],
                               sysex_messages: Optional[List[Tuple[float, List[int]]]] = None):
        """
        Send block of timestamped MIDI messages.

        Args:
            messages: List of tuples (time_in_seconds, status, data1, data2)
            sysex_messages: List of tuples (time_in_seconds, SYSEX_data) (optional)
        """
        # Add regular MIDI messages to heap
        for time, status, data1, data2 in messages:
            self.send_midi_message_at_time(status, data1, data2, time)

        # Add SYSEX messages to heap if provided
        if sysex_messages:
            for time, data in sysex_messages:
                self.send_sysex_at_time(data, time)

    def set_buffered_mode_time(self, time: float):
        """
        Set current time for buffered mode.

        Args:
            time: Current time in seconds
        """
        self.current_time = time

    def get_buffered_mode_time(self) -> float:
        """
        Get current time for buffered mode.

        Returns:
            Current time in seconds
        """
        return self.current_time

    def process_buffered_messages(self, current_time: float) -> List[Tuple[int, int, int]]:
        """
        Process buffered MIDI messages up to specified time.

        Args:
            current_time: Current time in seconds

        Returns:
            List of processed messages as (status, data1, data2) tuples
        """
        processed_messages = []

        # Process all messages whose time has arrived
        while self.message_heap and self.message_heap[0][0] <= current_time:
            _, _, status, data1, data2 = heapq.heappop(self.message_heap)
            processed_messages.append((status, data1, data2))

        return processed_messages

    def process_buffered_sysex(self, current_time: float) -> List[List[int]]:
        """
        Process buffered SYSEX messages up to specified time.

        Args:
            current_time: Current time in seconds

        Returns:
            List of processed SYSEX messages
        """
        processed_sysex = []

        # Process all messages whose time has arrived
        while self.sysex_heap and self.sysex_heap[0][0] <= current_time:
            _, _, data = heapq.heappop(self.sysex_heap)
            processed_sysex.append(data)

        return processed_sysex

    def prepare_sample_times(self, block_size: int):
        """
        Prepare timestamps for each sample in block.

        Args:
            block_size: Block size in samples
        """
        # Calculate time for each sample in block
        self.sample_times = []
        sample_duration = 1.0 / self.sample_rate

        for i in range(block_size):
            sample_time = self.block_start_time + (i * sample_duration)
            self.sample_times.append(sample_time)

    def set_block_start_time(self, start_time: float):
        """
        Set the start time of the current audio block.

        Args:
            start_time: Start time in seconds
        """
        self.block_start_time = start_time

    def process_sample_accurate_messages(self, sample_index: int) -> Tuple[List[Tuple[int, int, int]], List[List[int]]]:
        """
        Process MIDI messages with sample-accurate synchronization.

        Args:
            sample_index: Sample index in current block (0 - block_size-1)

        Returns:
            Tuple of (midi_messages, sysex_messages) processed at this sample
        """
        if not self.sample_times or sample_index >= len(self.sample_times):
            return [], []

        # Get time for current sample
        current_sample_time = self.sample_times[sample_index]

        # Process regular MIDI messages whose time has arrived
        midi_messages = []
        for i, (msg_time, status, data1, data2) in enumerate(self.message_buffer):
            if msg_time <= current_sample_time:
                # Process message immediately
                midi_messages.append((status, data1, data2))
            else:
                break

        # Remove processed messages (in reverse order to not disrupt indices)
        for i in reversed(range(len(midi_messages))):
            del self.message_buffer[i]

        # Process SYSEX messages whose time has arrived
        sysex_messages = []
        for i, (msg_time, data) in enumerate(self.sysex_buffer):
            if msg_time <= current_sample_time:
                # Process SYSEX message immediately
                sysex_messages.append(data)
            else:
                break

        # Remove processed SYSEX messages (in reverse order to not disrupt indices)
        for i in reversed(range(len(sysex_messages))):
            del self.sysex_buffer[i]

        return midi_messages, sysex_messages

    def process_message_at_time(self, sample_time: float) -> Tuple[List[Tuple[int, int, int]], List[List[int]]]:
        """
        Process all MIDI messages whose time has arrived by specified time.

        Args:
            sample_time: Time in seconds to process messages

        Returns:
            Tuple of (midi_messages, sysex_messages) processed at this time
        """
        # Process regular MIDI messages
        midi_messages = []
        while self.message_heap and self.message_heap[0][0] <= sample_time:
            _, _, status, data1, data2 = heapq.heappop(self.message_heap)
            midi_messages.append((status, data1, data2))

        # Process SYSEX messages
        sysex_messages = []
        while self.sysex_heap and self.sysex_heap[0][0] <= sample_time:
            _, _, data = heapq.heappop(self.sysex_heap)
            sysex_messages.append(data)

        return midi_messages, sysex_messages

    def clear_message_buffers(self):
        """
        Clear all message buffers.
        """
        self.message_buffer.clear()
        self.sysex_buffer.clear()

    def clear_message_heaps(self):
        """
        Clear all message heaps.
        """
        self.message_heap.clear()
        self.sysex_heap.clear()

    def reset(self):
        """
        Reset the buffered processor to initial state.
        """
        self.message_heap.clear()
        self.sysex_heap.clear()
        self.current_time = 0.0
        self.block_start_time = 0.0
        self.sample_times.clear()
        self.message_priority_counter = 0
        self.message_buffer.clear()
        self.sysex_buffer.clear()

    def get_pending_message_count(self) -> int:
        """
        Get the number of pending messages in heaps.

        Returns:
            Number of pending messages
        """
        return len(self.message_heap) + len(self.sysex_heap)

    def get_next_message_time(self) -> Optional[float]:
        """
        Get the time of the next pending message.

        Returns:
            Time of next message or None if no messages pending
        """
        next_times = []

        if self.message_heap:
            next_times.append(self.message_heap[0][0])
        if self.sysex_heap:
            next_times.append(self.sysex_heap[0][0])

        return min(next_times) if next_times else None

    def get_message_heap_info(self) -> Dict[str, Any]:
        """
        Get information about the current state of message heaps.

        Returns:
            Dictionary with heap information
        """
        return {
            "midi_messages_pending": len(self.message_heap),
            "sysex_messages_pending": len(self.sysex_heap),
            "next_message_time": self.get_next_message_time(),
            "current_time": self.current_time,
            "block_start_time": self.block_start_time,
            "sample_times_count": len(self.sample_times)
        }

    def is_message_pending_at_time(self, time: float) -> bool:
        """
        Check if there are messages pending at or before the specified time.

        Args:
            time: Time in seconds to check

        Returns:
            True if messages are pending
        """
        if self.message_heap and self.message_heap[0][0] <= time:
            return True
        if self.sysex_heap and self.sysex_heap[0][0] <= time:
            return True
        return False
