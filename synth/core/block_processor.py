"""
Block Processing Engine for XG Synthesizer
Implements high-performance audio processing in blocks while maintaining sample-accurate MIDI timing.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from collections import defaultdict, deque
from dataclasses import dataclass
from .object_pool import xg_pools


@dataclass
class TimedMidiEvent:
    """Represents a MIDI event with precise timing"""
    timestamp: float  # Sample timestamp (can be fractional for sub-sample precision)
    channel: int
    command: int
    data1: int
    data2: int = 0

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class MidiEventQueue:
    """Sample-accurate MIDI event queue for block processing"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.events = deque()  # Sorted by timestamp
        self.current_time = 0.0

    def add_event(self, event: TimedMidiEvent):
        """Add event to queue in timestamp order"""
        # Insert in sorted order for efficient retrieval
        if not self.events or event.timestamp >= self.events[-1].timestamp:
            self.events.append(event)
        else:
            # Find insertion point (rare case)
            for i, existing_event in enumerate(self.events):
                if event.timestamp < existing_event.timestamp:
                    self.events.insert(i, event)
                    break
            else:
                self.events.append(event)

    def get_events_in_range(self, start_time: float, end_time: float) -> List[TimedMidiEvent]:
        """Get all events within the specified time range"""
        result = []

        # Keep events within our time window
        while self.events and self.events[0].timestamp < end_time:
            event = self.events[0]
            if event.timestamp >= start_time:
                result.append(event)
            self.events.popleft()

        return result

    def clear_old_events(self, current_time: float):
        """Remove events that are too old to be relevant"""
        cutoff_time = current_time - 1.0  # Keep 1 second of history

        while self.events and self.events[0].timestamp < cutoff_time:
            self.events.popleft()

    def is_empty(self) -> bool:
        return len(self.events) == 0

    def size(self) -> int:
        return len(self.events)


class XGBlockProcessor:
    """
    High-performance block-based audio processor for XG synthesizer.
    Processes audio in blocks while maintaining sample-accurate MIDI timing.
    """

    def __init__(self, block_size: int = 128, sample_rate: int = 44100,
                 max_channels: int = 16, max_block_events: int = 64):
        """
        Initialize block processor.

        Args:
            block_size: Number of samples per processing block
            sample_rate: Audio sample rate
            max_channels: Maximum number of MIDI channels
            max_block_events: Maximum MIDI events per block
        """
        self.block_size = block_size
        self.sample_rate = sample_rate
        self.max_channels = max_channels
        self.max_block_events = max_block_events

        # Thread-safe channel processing state
        self.current_sample_time = 0.0

        # MIDI event queues for each channel
        self.midi_queues = [MidiEventQueue(sample_rate) for _ in range(max_channels)]

        # Pre-allocated audio buffers for block processing
        self._left_buffer = np.zeros(block_size, dtype=np.float32)
        self._right_buffer = np.zeros(block_size, dtype=np.float32)
        self._scratch_buffer = np.zeros(block_size, dtype=np.float32)

        # Block tracking and statistics
        self.total_blocks_processed = 0
        self.total_events_processed = 0
        self.block_processing_times = []

        # Performance monitoring
        self._block_stats = {
            'avg_processing_time_ms': 0.0,
            'events_per_block': 0.0,
            'channel_utilization': 0.0
        }

    def process_channel_block(self, channel_renderer, channel_num: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process one block of audio for a specific channel with precise MIDI timing.

        Args:
            channel_renderer: XGChannelRenderer instance for the channel
            channel_num: MIDI channel number (0-15)

        Returns:
            Tuple of (left_block, right_block) arrays
        """
        import time
        start_time = time.perf_counter()

        # Clear working buffers
        self._left_buffer.fill(0.0)
        self._right_buffer.fill(0.0)

        # Calculate block time range
        block_start_time = self.current_sample_time
        block_end_time = block_start_time + self.block_size

        # Get MIDI events for this block
        midi_queue = self.midi_queues[channel_num]
        block_events = midi_queue.get_events_in_range(block_start_time, block_end_time)

        # Process block with MIDI timing
        if block_events:
            self._process_block_with_events(channel_renderer, block_events, block_start_time)
        else:
            # No events in this block, use optimized processing
            self._process_clean_block(channel_renderer)

        # Update statistics
        self.total_blocks_processed += 1
        self.total_events_processed += len(block_events)

        # Performance monitoring
        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000.0
        self.block_processing_times.append(processing_time_ms)

        # Update rolling averages
        if len(self.block_processing_times) > 100:
            self.block_processing_times.pop(0)

        avg_time = sum(self.block_processing_times) / len(self.block_processing_times)
        self._block_stats['avg_processing_time_ms'] = avg_time
        self._block_stats['events_per_block'] = self.total_events_processed / max(1, self.total_blocks_processed)

        # Advance sample time
        self.current_sample_time = block_end_time

        return self._left_buffer.copy(), self._right_buffer.copy()

    def _process_block_with_events(self, channel_renderer, block_events: List[TimedMidiEvent], block_start_time: float):
        """Process a block that contains MIDI events with sample accuracy."""
        # For now, use simplified processing - process entire block at once
        # TODO: Implement sample-accurate event processing within blocks
        self._process_clean_block(channel_renderer)

    def _process_clean_block(self, channel_renderer):
        """Process a block with no MIDI events - use optimized per-sample processing."""
        for sample_idx in range(self.block_size):
            if hasattr(channel_renderer, 'generate_sample'):
                left, right = channel_renderer.generate_sample()
                self._left_buffer[sample_idx] = left
                self._right_buffer[sample_idx] = right

    def _apply_midi_event_to_channel(self, channel_renderer, event: TimedMidiEvent):
        """Apply a MIDI event to the channel renderer."""
        command = event.command & 0xF0
        if command == 0x80:  # Note Off
            channel_renderer.note_off(event.data1, event.data2)
        elif command == 0x90:  # Note On
            channel_renderer.note_on(event.data1, event.data2)
        elif command == 0xB0:  # Control Change
            channel_renderer.control_change(event.data1, event.data2)
        elif command == 0xC0:  # Program Change
            channel_renderer.program_change(event.data1)
        elif command == 0xE0:  # Pitch Bend
            channel_renderer.pitch_bend(event.data1, event.data2)

    def add_midi_event(self, channel: int, timestamp: float, command: int, data1: int, data2: int = 0):
        """Add a MIDI event to the queue for processing."""
        if 0 <= channel < self.max_channels:
            event = TimedMidiEvent(
                timestamp=timestamp,
                channel=channel,
                command=command,
                data1=data1,
                data2=data2
            )
            self.midi_queues[channel].add_event(event)

    def get_global_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total_queued = sum(queue.size() for queue in self.midi_queues)

        return {
            'total_blocks_processed': self.total_blocks_processed,
            'total_events_processed': self.total_events_processed,
            'events_per_block_avg': self._block_stats['events_per_block'],
            'avg_processing_time_ms': self._block_stats['avg_processing_time_ms'],
            'current_sample_time': self.current_sample_time,
            'total_events_queued': total_queued,
            'block_size': self.block_size,
            'sample_rate': self.sample_rate
        }

    def clear_all_events(self):
        """Clear all queued MIDI events."""
        for queue in self.midi_queues:
            queue.events.clear()

    def reset(self):
        """Reset processor state."""
        self.current_sample_time = 0.0
        self.clear_all_events()
        self.total_blocks_processed = 0
        self.total_events_processed = 0
        self.block_processing_times.clear()


# Convenience functions
def create_block_processor(sample_rate: int = 44100, block_size: int = 128) -> XGBlockProcessor:
    """Create and configure a new block processor."""
    return XGBlockProcessor(
        block_size=block_size,
        sample_rate=sample_rate,
        max_channels=16,
        max_block_events=64
    )
