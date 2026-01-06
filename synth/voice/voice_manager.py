"""
Voice Manager - Polyphony Management and Voice Allocation

Professional voice management system with intelligent allocation,
polyphony control, and real-time voice state tracking.

Part of S90/S70 compatibility - Core Infrastructure (Phase 1).
"""

from typing import Dict, List, Any, Optional, Callable, Set
import threading
import time
from dataclasses import dataclass
from enum import Enum


class VoiceState(Enum):
    """Voice allocation states"""
    FREE = "free"
    ATTACK = "attack"
    DECAY = "decay"
    SUSTAIN = "sustain"
    RELEASE = "release"
    PENDING_RELEASE = "pending_release"


class VoiceStealingStrategy(Enum):
    """Voice stealing strategies for polyphony management"""
    OLDEST = "oldest"      # Steal oldest voice first
    QUIETEST = "quietest"  # Steal quietest voice first
    LOWEST = "lowest"      # Steal lowest note first
    HIGHEST = "highest"    # Steal highest note first
    PRIORITY = "priority"  # Priority-based stealing (engine-specific)


@dataclass
class VoiceInfo:
    """Information about an allocated voice"""
    voice_id: int
    channel: int
    note: int
    velocity: int
    engine_type: str
    state: VoiceState
    start_time: float
    priority: int = 0
    effects_chain: Optional[List[str]] = None
    modulation_data: Optional[Dict[str, Any]] = None


class VoiceManager:
    """
    Voice Manager - Professional Polyphony Management

    Intelligent voice allocation system with configurable stealing strategies,
    real-time voice state tracking, and performance monitoring.
    """

    def __init__(self, max_voices: int = 64):
        """
        Initialize voice manager.

        Args:
            max_voices: Maximum number of simultaneous voices
        """
        self.max_voices = max_voices
        self.active_voices: Dict[int, VoiceInfo] = {}
        self.free_voice_ids: Set[int] = set(range(max_voices))
        self.next_voice_id = max_voices

        # Voice stealing configuration
        self.stealing_strategy = VoiceStealingStrategy.PRIORITY
        self.voice_priorities = {
            'fdsp': 10,      # Highest priority (vocal synthesis)
            'an': 9,         # Analog engines
            'sf2': 8,        # Sample-based
            'xg': 7,         # XG synthesis
            'fm': 6,         # FM synthesis
            'wavetable': 5,  # Wavetable
            'additive': 4,   # Additive synthesis
            'granular': 3,   # Granular
            'physical': 2,   # Physical modeling
        }

        # Performance monitoring
        self.allocation_stats = {
            'total_allocations': 0,
            'total_deallocations': 0,
            'voice_stealing_events': 0,
            'peak_concurrent_voices': 0,
            'allocation_failures': 0,
            'average_voice_lifetime': 0.0
        }

        # Voice lifetime tracking
        self.voice_lifetimes: List[float] = []
        self.max_lifetime_history = 1000

        # Thread safety
        self.lock = threading.RLock()

        # Callbacks
        self.voice_allocated_callback: Optional[Callable[[VoiceInfo], None]] = None
        self.voice_deallocated_callback: Optional[Callable[[int], None]] = None
        self.voice_stolen_callback: Optional[Callable[[VoiceInfo, VoiceInfo], None]] = None

    def allocate_voice(self, channel: int, note: int, velocity: int,
                      engine_type: str) -> Optional[int]:
        """
        Allocate a voice for note playback.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            engine_type: Synthesis engine type

        Returns:
            Voice ID or None if allocation failed
        """
        with self.lock:
            # Check if voice already exists for this note/channel
            existing_voice = self.find_voice(channel, note)
            if existing_voice is not None:
                # Retrigger existing voice
                self._update_voice(existing_voice, velocity)
                return existing_voice

            # Try to allocate a free voice
            voice_id = self._allocate_free_voice()
            if voice_id is not None:
                return self._initialize_voice(voice_id, channel, note, velocity, engine_type)

            # No free voices, attempt stealing
            stolen_voice_id = self._steal_voice(channel, note, velocity, engine_type)
            if stolen_voice_id is not None:
                return self._reallocate_voice(stolen_voice_id, channel, note, velocity, engine_type)

            # Allocation failed
            self.allocation_stats['allocation_failures'] += 1
            return None

    def _allocate_free_voice(self) -> Optional[int]:
        """Allocate a free voice if available"""
        if self.free_voice_ids:
            return self.free_voice_ids.pop()
        return None

    def _initialize_voice(self, voice_id: int, channel: int, note: int,
                         velocity: int, engine_type: str) -> int:
        """Initialize a newly allocated voice"""
        voice_info = VoiceInfo(
            voice_id=voice_id,
            channel=channel,
            note=note,
            velocity=velocity,
            engine_type=engine_type,
            state=VoiceState.ATTACK,
            start_time=time.time(),
            priority=self.voice_priorities.get(engine_type, 0)
        )

        self.active_voices[voice_id] = voice_info
        self.allocation_stats['total_allocations'] += 1
        self.allocation_stats['peak_concurrent_voices'] = max(
            self.allocation_stats['peak_concurrent_voices'],
            len(self.active_voices)
        )

        # Notify callback
        if self.voice_allocated_callback:
            self.voice_allocated_callback(voice_info)

        return voice_id

    def _reallocate_voice(self, voice_id: int, channel: int, note: int,
                         velocity: int, engine_type: str) -> int:
        """Reallocate a stolen voice"""
        old_voice_info = self.active_voices[voice_id]

        # Create new voice info
        new_voice_info = VoiceInfo(
            voice_id=voice_id,
            channel=channel,
            note=note,
            velocity=velocity,
            engine_type=engine_type,
            state=VoiceState.ATTACK,
            start_time=time.time(),
            priority=self.voice_priorities.get(engine_type, 0)
        )

        self.active_voices[voice_id] = new_voice_info
        self.allocation_stats['voice_stealing_events'] += 1

        # Notify callback
        if self.voice_stolen_callback:
            self.voice_stolen_callback(old_voice_info, new_voice_info)

        return voice_id

    def _steal_voice(self, channel: int, note: int, velocity: int,
                    engine_type: str) -> Optional[int]:
        """
        Attempt to steal a voice using the configured strategy.

        Returns:
            Voice ID to steal or None
        """
        if not self.active_voices:
            return None

        requesting_priority = self.voice_priorities.get(engine_type, 0)

        if self.stealing_strategy == VoiceStealingStrategy.PRIORITY:
            return self._steal_by_priority(requesting_priority)
        elif self.stealing_strategy == VoiceStealingStrategy.OLDEST:
            return self._steal_oldest()
        elif self.stealing_strategy == VoiceStealingStrategy.QUIETEST:
            return self._steal_quietest()
        elif self.stealing_strategy == VoiceStealingStrategy.LOWEST:
            return self._steal_lowest()
        elif self.stealing_strategy == VoiceStealingStrategy.HIGHEST:
            return self._steal_highest()
        else:
            return self._steal_oldest()  # Default fallback

    def _steal_by_priority(self, requesting_priority: int) -> Optional[int]:
        """Steal voice with lowest priority"""
        lowest_priority = requesting_priority + 1  # Only steal lower priority
        candidate_voice = None

        for voice_id, voice_info in self.active_voices.items():
            if voice_info.priority < lowest_priority:
                lowest_priority = voice_info.priority
                candidate_voice = voice_id

        return candidate_voice

    def _steal_oldest(self) -> Optional[int]:
        """Steal the oldest allocated voice"""
        oldest_time = float('inf')
        oldest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            if voice_info.start_time < oldest_time:
                oldest_time = voice_info.start_time
                oldest_voice = voice_id

        return oldest_voice

    def _steal_quietest(self) -> Optional[int]:
        """Steal the voice with lowest velocity"""
        lowest_velocity = float('inf')
        quietest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            if voice_info.velocity < lowest_velocity:
                lowest_velocity = voice_info.velocity
                quietest_voice = voice_id

        return quietest_voice

    def _steal_lowest(self) -> Optional[int]:
        """Steal the voice with lowest note"""
        lowest_note = float('inf')
        lowest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            if voice_info.note < lowest_note:
                lowest_note = voice_info.note
                lowest_voice = voice_id

        return lowest_voice

    def _steal_highest(self) -> Optional[int]:
        """Steal the voice with highest note"""
        highest_note = float('-inf')
        highest_voice = None

        for voice_id, voice_info in self.active_voices.items():
            if voice_info.note > highest_note:
                highest_note = voice_info.note
                highest_voice = voice_id

        return highest_voice

    def deallocate_voice(self, voice_id: int) -> bool:
        """
        Deallocate a voice.

        Args:
            voice_id: Voice to deallocate

        Returns:
            True if deallocated successfully
        """
        with self.lock:
            if voice_id in self.active_voices:
                voice_info = self.active_voices[voice_id]

                # Record lifetime
                lifetime = time.time() - voice_info.start_time
                self.voice_lifetimes.append(lifetime)
                if len(self.voice_lifetimes) > self.max_lifetime_history:
                    self.voice_lifetimes.pop(0)

                # Update statistics
                self.allocation_stats['total_deallocations'] += 1
                self.allocation_stats['average_voice_lifetime'] = sum(self.voice_lifetimes) / len(self.voice_lifetimes)

                # Free the voice
                del self.active_voices[voice_id]
                self.free_voice_ids.add(voice_id)

                # Notify callback
                if self.voice_deallocated_callback:
                    self.voice_deallocated_callback(voice_id)

                return True
            return False

    def find_voice(self, channel: int, note: int) -> Optional[int]:
        """
        Find voice playing a specific note on a channel.

        Args:
            channel: MIDI channel
            note: MIDI note number

        Returns:
            Voice ID or None if not found
        """
        with self.lock:
            for voice_id, voice_info in self.active_voices.items():
                if voice_info.channel == channel and voice_info.note == note:
                    return voice_id
            return None

    def get_active_voices(self) -> List[VoiceInfo]:
        """Get list of all active voices"""
        with self.lock:
            return list(self.active_voices.values())

    def get_voice_info(self, voice_id: int) -> Optional[VoiceInfo]:
        """Get information about a specific voice"""
        with self.lock:
            return self.active_voices.get(voice_id)

    def update_voice_state(self, voice_id: int, new_state: VoiceState) -> bool:
        """
        Update the state of a voice.

        Args:
            voice_id: Voice to update
            new_state: New voice state

        Returns:
            True if updated successfully
        """
        with self.lock:
            if voice_id in self.active_voices:
                self.active_voices[voice_id].state = new_state
                return True
            return False

    def _update_voice(self, voice_id: int, new_velocity: int):
        """Update an existing voice (retrigger)"""
        if voice_id in self.active_voices:
            voice_info = self.active_voices[voice_id]
            voice_info.velocity = new_velocity
            voice_info.state = VoiceState.ATTACK
            voice_info.start_time = time.time()  # Reset lifetime

    def clear_channel(self, channel: int):
        """
        Clear all voices on a specific channel.

        Args:
            channel: MIDI channel to clear
        """
        with self.lock:
            voices_to_remove = []
            for voice_id, voice_info in self.active_voices.items():
                if voice_info.channel == channel:
                    voices_to_remove.append(voice_id)

            for voice_id in voices_to_remove:
                self.deallocate_voice(voice_id)

    def clear_all_voices(self):
        """Clear all active voices"""
        with self.lock:
            voice_ids = list(self.active_voices.keys())
            for voice_id in voice_ids:
                self.deallocate_voice(voice_id)

    def set_stealing_strategy(self, strategy: VoiceStealingStrategy) -> bool:
        """
        Set voice stealing strategy.

        Args:
            strategy: Voice stealing strategy

        Returns:
            True if strategy is valid
        """
        if isinstance(strategy, VoiceStealingStrategy):
            self.stealing_strategy = strategy
            return True
        return False

    def set_voice_priority(self, engine_type: str, priority: int) -> bool:
        """
        Set priority for an engine type.

        Args:
            engine_type: Engine type
            priority: Priority level (higher = less likely to be stolen)

        Returns:
            True if set successfully
        """
        self.voice_priorities[engine_type] = priority

        # Update priorities for existing voices
        with self.lock:
            for voice_info in self.active_voices.values():
                if voice_info.engine_type == engine_type:
                    voice_info.priority = priority

        return True

    def get_voice_statistics(self) -> Dict[str, Any]:
        """Get comprehensive voice statistics"""
        with self.lock:
            active_count = len(self.active_voices)
            free_count = len(self.free_voice_ids)

            # Voice distribution by engine
            engine_counts = {}
            for voice_info in self.active_voices.values():
                engine = voice_info.engine_type
                engine_counts[engine] = engine_counts.get(engine, 0) + 1

            # Voice distribution by channel
            channel_counts = {}
            for voice_info in self.active_voices.values():
                channel = voice_info.channel
                channel_counts[channel] = channel_counts.get(channel, 0) + 1

            return {
                'active_voices': active_count,
                'free_voices': free_count,
                'total_capacity': self.max_voices,
                'utilization_percent': (active_count / self.max_voices) * 100,
                'by_engine': engine_counts,
                'by_channel': channel_counts,
                'allocation_stats': self.allocation_stats.copy(),
                'stealing_strategy': self.stealing_strategy.value,
                'voice_priorities': self.voice_priorities.copy()
            }

    def get_channel_info(self, channel: int) -> Dict[str, Any]:
        """
        Get information about voices on a specific channel.

        Args:
            channel: MIDI channel

        Returns:
            Channel voice information
        """
        with self.lock:
            channel_voices = []
            for voice_info in self.active_voices.values():
                if voice_info.channel == channel:
                    channel_voices.append({
                        'voice_id': voice_info.voice_id,
                        'note': voice_info.note,
                        'velocity': voice_info.velocity,
                        'engine_type': voice_info.engine_type,
                        'state': voice_info.state.value,
                        'lifetime': time.time() - voice_info.start_time
                    })

            return {
                'channel': channel,
                'active_voices': len(channel_voices),
                'voices': channel_voices
            }

    def optimize_polyphony(self, target_utilization: float = 0.8) -> Dict[str, Any]:
        """
        Optimize polyphony settings based on usage patterns.

        Args:
            target_utilization: Target voice utilization (0.0-1.0)

        Returns:
            Optimization recommendations
        """
        stats = self.get_voice_statistics()

        recommendations = []

        current_utilization = stats['utilization_percent'] / 100.0

        if current_utilization > target_utilization:
            recommendations.append("Consider increasing max_voices for better headroom")

        if stats['allocation_stats']['voice_stealing_events'] > 0:
            recommendations.append("Voice stealing occurring - consider higher polyphony limit")

        # Check for unbalanced engine usage
        total_voices = sum(stats['by_engine'].values())
        if total_voices > 0:
            for engine, count in stats['by_engine'].items():
                percentage = (count / total_voices) * 100
                if percentage > 70:  # Engine using >70% of voices
                    recommendations.append(f"Engine '{engine}' using {percentage:.1f}% of voices - consider load balancing")

        return {
            'current_utilization': current_utilization,
            'target_utilization': target_utilization,
            'recommendations': recommendations,
            'statistics': stats
        }

    def set_max_voices(self, max_voices: int) -> bool:
        """
        Set maximum number of voices.

        Args:
            max_voices: New maximum voice count

        Returns:
            True if set successfully
        """
        if max_voices < 1 or max_voices > 256:
            return False

        with self.lock:
            # If reducing max voices, deallocate excess voices
            while len(self.active_voices) > max_voices:
                # Find oldest voice to deallocate
                oldest_voice = None
                oldest_time = float('inf')
                for voice_id, voice_info in self.active_voices.items():
                    if voice_info.start_time < oldest_time:
                        oldest_time = voice_info.start_time
                        oldest_voice = voice_id

                if oldest_voice is not None:
                    self.deallocate_voice(oldest_voice)
                else:
                    break

            # Update voice ID pool
            self.free_voice_ids = set(range(max_voices))
            for voice_id in self.active_voices:
                if voice_id in self.free_voice_ids:
                    self.free_voice_ids.remove(voice_id)

            # Add new voice IDs if expanding
            if max_voices > self.max_voices:
                for voice_id in range(self.max_voices, max_voices):
                    if voice_id not in self.active_voices:
                        self.free_voice_ids.add(voice_id)

            self.max_voices = max_voices
            return True

    def reset_statistics(self):
        """Reset allocation statistics"""
        with self.lock:
            self.allocation_stats = {
                'total_allocations': 0,
                'total_deallocations': 0,
                'voice_stealing_events': 0,
                'peak_concurrent_voices': 0,
                'allocation_failures': 0,
                'average_voice_lifetime': 0.0
            }
            self.voice_lifetimes.clear()

    # Callback setters
    def set_voice_allocated_callback(self, callback: Callable[[VoiceInfo], None]):
        """Set callback for voice allocation events"""
        self.voice_allocated_callback = callback

    def set_voice_deallocated_callback(self, callback: Callable[[int], None]):
        """Set callback for voice deallocation events"""
        self.voice_deallocated_callback = callback

    def set_voice_stolen_callback(self, callback: Callable[[VoiceInfo, VoiceInfo], None]):
        """Set callback for voice stealing events"""
        self.voice_stolen_callback = callback
