"""
Auto-Accompaniment Engine - Main Style Playback System

This is the core engine that generates real-time accompaniment based on
detected chords and style data.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any, Tuple
import threading
import time
import math
import random
import numpy as np


class AccompanimentMode(Enum):
    """Operating modes for auto-accompaniment"""

    OFF = auto()
    ON = auto()
    SYNC_START = auto()
    WAITING = auto()


class StylePlaybackState(Enum):
    """Style playback states"""

    STOPPED = auto()
    PLAYING = auto()
    FADING_IN = auto()
    FADING_OUT = auto()
    COUNT_IN = auto()
    TRANSITIONING = auto()


@dataclass
class TrackState:
    """Runtime state for a single style track"""

    track_type: Any
    muted: bool = False
    soloed: bool = False
    volume: float = 1.0
    pan: int = 64
    current_tick: int = 0
    loop_count: int = 0
    velocity_scale: float = 1.0
    note_events: List[Any] = field(default_factory=list)


@dataclass
class AutoAccompanimentConfig:
    """Configuration for auto-accompaniment"""

    chord_detection_zone_low: int = 36
    chord_detection_zone_high: int = 60
    bass_detection_zone_high: int = 48
    minimum_chord_interval_ms: int = 100
    section_transition_delay_ms: int = 0
    fill_trigger_beats: int = 1
    auto_fill_enabled: bool = True
    sync_start_enabled: bool = True
    count_in_enabled: bool = True
    count_in_bars: int = 1
    default_intro_section: str = "intro_1"
    default_main_section: str = "main_a"
    default_ending_section: str = "ending_1"
    dynamics_enabled: bool = True
    velocity_sensitivity: float = 1.0
    humanize_amount: float = 0.0
    swing_amount: float = 0.0


class StyleEvent:
    """Internal style event for scheduling"""

    def __init__(
        self,
        tick: int,
        note: int,
        velocity: int,
        duration: int,
        channel: int,
        track_type: Any,
        section: Any,
    ):
        self.tick = tick
        self.note = note
        self.velocity = velocity
        self.duration = duration
        self.channel = channel
        self.track_type = track_type
        self.section = section
        self.played = False
        self.timestamp: Optional[float] = None


class AutoAccompaniment:
    """
    Main auto-accompaniment engine.

    This engine:
    1. Monitors MIDI input for chord detection
    2. Loads and plays style data based on detected chords
    3. Manages section transitions (Main A/B/C/D, Fill, Intro, Ending)
    4. Generates MIDI events for the synthesizer
    """

    def __init__(
        self,
        style: Any,
        synthesizer: Any,
        config: Optional[AutoAccompanimentConfig] = None,
        sample_rate: int = 44100,
    ):
        self.style = style
        self.synthesizer = synthesizer
        self.config = config or AutoAccompanimentConfig()
        self.sample_rate = sample_rate

        self._lock = threading.RLock()

        from .chord_detector import ChordDetector, ChordDetectionConfig

        chord_config = ChordDetectionConfig(
            detection_zone_low=self.config.chord_detection_zone_low,
            detection_zone_high=self.config.chord_detection_zone_high,
            use_bass_detection=True,
            bass_detection_threshold=self.config.bass_detection_zone_high,
        )
        self.chord_detector = ChordDetector(chord_config)

        self.mode = AccompanimentMode.OFF
        self.playback_state = StylePlaybackState.STOPPED

        self._current_section: Any = None
        self._next_section: Any = None
        self._target_section: Any = None
        self._fill_section: Optional[Any] = None
        self._is_filling = False

        self._tick_position: int = 0
        self._bar_position: int = 0
        self._beat_position: int = 0
        self._loop_count: int = 0

        self._tempo: float = float(style.metadata.tempo)
        self._time_signature_num: int = style.metadata.time_signature_numerator
        self._time_signature_den: int = style.metadata.time_signature_denominator

        self._tick_per_beat: int = 480
        self._ticks_per_bar: int = self._tick_per_beat * self._time_signature_num
        self._ms_per_tick: float = 60000.0 / (self._tempo * self._tick_per_beat)

        self._track_states: Dict[Any, TrackState] = {}
        self._scheduled_events: List[StyleEvent] = []
        self._active_notes: Dict[Tuple[int, int], int] = {}

        self._running = False
        self._processing_thread: Optional[threading.Thread] = None
        self._internal_mode = False  # Prevent recursive note triggering

        self._on_note_on: Optional[Callable[[int, int, int], None]] = None
        self._on_note_off: Optional[Callable[[int, int], None]] = None
        self._on_section_change: Optional[Callable[[Any, Any], None]] = None
        self._on_chord_change: Optional[Callable[[Any], None]] = None

        # Groove and humanize
        self._groove_enabled = False
        self._groove_intensity: float = 0.5
        self._groove_type: str = "swing_1_3"
        self._humanize_amount: float = 0.0
        self._humanize_velocity: float = 0.0
        self._humanize_timing: float = 0.0
        self._swing_amount: float = 0.0
        self._random = random.Random()

        self._init_track_states()

        self.chord_detector.config.on_chord_change = self._handle_chord_change

    def _init_track_states(self):
        """Initialize track states"""
        from .style import TrackType

        for track_type in TrackType:
            self._track_states[track_type] = TrackState(track_type=track_type)

    @property
    def tempo(self) -> float:
        return self._tempo

    @tempo.setter
    def tempo(self, value: float):
        with self._lock:
            self._tempo = max(20, min(300, value))
            self._ms_per_tick = 60000.0 / (self._tempo * self._tick_per_beat)

    @property
    def current_section(self) -> Any:
        return self._current_section

    @property
    def is_playing(self) -> bool:
        return self.playback_state == StylePlaybackState.PLAYING

    def set_note_callbacks(
        self,
        note_on: Optional[Callable[[int, int, int], None]] = None,
        note_off: Optional[Callable[[int, int], None]] = None,
    ):
        """Set MIDI output callbacks"""
        self._on_note_on = note_on
        self._on_note_off = note_off

    def set_section_change_callback(self, callback: Callable[[Any, Any], None]):
        """Set callback for section changes"""
        self._on_section_change = callback

    def set_chord_change_callback(self, callback: Callable[[Any], None]):
        """Set callback for chord changes"""
        self._on_chord_change = callback
        self.chord_detector.config.on_chord_change = callback

    def start(self, section: Optional[Any] = None):
        """Start auto-accompaniment"""
        with self._lock:
            if self._running:
                return

            target_section = section or self._get_section_by_name(
                self.config.default_main_section
            )

            if self.config.sync_start_enabled:
                self.mode = AccompanimentMode.SYNC_START
                self._target_section = target_section
            else:
                self._start_playback(target_section)

            self._running = True
            self._processing_thread = threading.Thread(
                target=self._processing_loop, daemon=True
            )
            self._processing_thread.start()

    def stop(self, ending: bool = True):
        """Stop auto-accompaniment"""
        with self._lock:
            if not self._running:
                return

            if ending and self.config.default_ending_section:
                ending_section = self._get_section_by_name(
                    self.config.default_ending_section
                )
                if ending_section:
                    self._transition_to(ending_section)
                    return

            self._stop_playback()

    def _start_playback(self, section: Any):
        """Start playback of a section"""
        from .style import StyleSectionType

        self._current_section = section
        self._tick_position = 0
        self._bar_position = 0
        self._beat_position = 0
        self._loop_count = 0
        self._is_filling = False

        if section.count_in_bars > 0 and self.config.count_in_enabled:
            self.playback_state = StylePlaybackState.COUNT_IN
        else:
            self.playback_state = StylePlaybackState.PLAYING

        self.mode = AccompanimentMode.ON
        self._schedule_section_events(section)

    def _stop_playback(self):
        """Stop playback and cleanup"""
        self._all_notes_off()
        self.mode = AccompanimentMode.OFF
        self.playback_state = StylePlaybackState.STOPPED
        self._current_section = None
        self._scheduled_events.clear()

    def _transition_to(self, section: Any):
        """Transition to a new section"""
        from .style import StyleSectionType

        old_section = self._current_section

        if section.section_type.is_ending:
            self._target_section = section
            self.playback_state = StylePlaybackState.TRANSITIONING
            self._schedule_section_events(section)
        else:
            self._current_section = section
            self._tick_position = 0
            self._bar_position = 0
            self._beat_position = 0
            self._schedule_section_events(section)

            if self._on_section_change:
                self._on_section_change(old_section, section)

    def trigger_fill(self):
        """Trigger fill in before next section change"""
        if not self._current_section or not self.config.auto_fill_enabled:
            return

        from .style import StyleSectionType

        current = self._current_section.section_type
        if current.is_main:
            fills = self.style.get_fill_for_main(current)
            if fills:
                self._fill_section = fills[0]
                self._is_filling = True

    def trigger_section_change(self, target_section: str, use_fill: bool = True):
        """
        Trigger a section change with optional fill.

        Args:
            target_section: Target section name
            use_fill: Whether to play fill before changing
        """
        if not self._current_section:
            return

        target = self._get_section_by_name(target_section)
        if not target:
            return

        from .style import StyleSectionType

        # If we're going to a main section and fill is enabled
        if use_fill and target.section_type.is_main:
            current = self._current_section.section_type

            # Get the fill for current main section
            if current.is_main:
                fills = self.style.get_fill_for_main(current)
                if fills:
                    # Schedule fill then transition
                    self._target_section = target
                    self._fill_section = fills[0]
                    self._is_filling = True
                    return

        # Direct transition
        self._transition_to(target)

    def set_main_section(self, section_name: str):
        """Set main section directly"""
        section = self._get_section_by_name(section_name)
        if section:
            self._transition_to(section)

    def next_main_section(self):
        """Advance to next main section"""
        if not self._current_section:
            return

        current = self._current_section.section_type
        if current.is_main:
            next_main = self.style.get_next_main(current)
            if next_main:
                # Check if we should play fill first
                if self.config.auto_fill_enabled:
                    fills = self.style.get_fill_for_main(current)
                    if fills:
                        self._target_section = self.style.get_section(next_main)
                        self._fill_section = fills[0]
                        self._is_filling = True
                        return

                self._transition_to(self.style.get_section(next_main))

    def set_track_mute(self, track_type: Any, muted: bool):
        """Mute/unmute a track"""
        if track_type in self._track_states:
            self._track_states[track_type].muted = muted

    def set_track_solo(self, track_type: Any, soloed: bool):
        """Solo/unsolo a track"""
        if track_type in self._track_states:
            self._track_states[track_type].soloed = soloed

    def set_track_volume(self, track_type: Any, volume: float):
        """Set track volume (0.0 - 1.0)"""
        if track_type in self._track_states:
            self._track_states[track_type].volume = max(0.0, min(1.0, volume))

    # ===== Groove and Humanize Methods =====

    def set_groove(self, groove_type: str, intensity: float = 0.5):
        """
        Set groove type and intensity.

        Args:
            groove_type: Groove type name (swing_1_3, swing_2_3, shuffle, funk, pop, latin, jazz, bossa, waltz)
            intensity: Groove intensity (0.0 to 1.0)
        """
        self._groove_type = groove_type
        self._groove_intensity = max(0.0, min(1.0, intensity))
        self._groove_enabled = groove_type != "off"

    def set_swing(self, amount: float):
        """
        Set swing amount.

        Args:
            amount: Swing amount (-1.0 to 1.0), 0 = no swing
        """
        self._swing_amount = max(-1.0, min(1.0, amount))

    def set_humanize(
        self, amount: float = 0.0, velocity: float = 0.0, timing: float = 0.0
    ):
        """
        Set humanize parameters.

        Args:
            amount: Overall humanize amount (0.0 to 1.0)
            velocity: Velocity variation amount (0.0 to 1.0)
            timing: Timing variation amount (0.0 to 1.0)
        """
        self._humanize_amount = max(0.0, min(1.0, amount))
        self._humanize_velocity = max(0.0, min(1.0, velocity))
        self._humanize_timing = max(0.0, min(1.0, timing))

    def _apply_groove_to_tick(self, tick: int, position_16th: int) -> int:
        """Apply groove timing offset to a tick position"""
        if not self._groove_enabled:
            return tick

        # Calculate swing offset for even 16ths (positions 1, 3, 5, 7, etc.)
        if position_16th % 2 == 1:  # Off-beat 16th
            swing_ticks = int(self._swing_amount * 30 * self._groove_intensity)
            return tick + swing_ticks

        return tick

    def _apply_humanize_to_velocity(self, velocity: int, note_index: int) -> int:
        """Apply humanize to velocity"""
        if self._humanize_amount == 0 and self._humanize_velocity == 0:
            return velocity

        # Random variation based on note index for consistency
        self._random.seed(note_index)
        variation = int(
            (self._random.random() - 0.5)
            * 20
            * self._humanize_velocity
            * self._humanize_amount
        )

        return max(1, min(127, velocity + variation))

    def _apply_humanize_to_timing(self, tick: int, note_index: int) -> int:
        """Apply humanize to timing"""
        if self._humanize_amount == 0 and self._humanize_timing == 0:
            return tick

        self._random.seed(note_index + 1000)
        variation = int(
            (self._random.random() - 0.5)
            * 10
            * self._humanize_timing
            * self._humanize_amount
        )

        return tick + variation

    def _get_section_by_name(self, name: str) -> Any:
        """Get section by name string"""
        from .style import StyleSectionType

        try:
            st = StyleSectionType(name)
            return self.style.get_section(st)
        except ValueError:
            return self.style.get_section(StyleSectionType.MAIN_A)

    def _schedule_section_events(self, section: Any):
        """Schedule all note events for a section"""
        from .style import TrackType, StyleSectionType

        self._scheduled_events.clear()

        for track_type in TrackType:
            track_data = section.get_track(track_type)
            if track_data.mute:
                continue

            channel = track_type.default_midi_channel

            for note_event in track_data.notes:
                mapped_note = self._map_note_to_chord(
                    note_event.note, track_type, self.chord_detector.get_current_chord()
                )

                if mapped_note is not None:
                    event = StyleEvent(
                        tick=note_event.tick,
                        note=mapped_note,
                        velocity=int(
                            note_event.velocity * track_data.velocity_offset / 127
                        ),
                        duration=note_event.duration,
                        channel=channel,
                        track_type=track_type,
                        section=section,
                    )
                    self._scheduled_events.append(event)

    def _map_note_to_chord(
        self, note: int, track_type: Any, chord: Any
    ) -> Optional[int]:
        """Map a style note to the current chord using chord tables"""
        if chord is None:
            return note

        from .style import TrackType

        if track_type.is_drum:
            return note

        # Try to use chord table first
        mapped_note = self._map_using_chord_table(note, track_type, chord)
        if mapped_note is not None:
            return mapped_note

        # Fall back to basic chord mapping
        if track_type == TrackType.BASS:
            root = chord.root_midi
            if chord.is_inversion and chord.bass_note:
                root = chord.bass_note % 12
            return root + 36

        root = chord.root_midi
        note_in_chord = (note - 60) % 12

        chord_intervals = chord.intervals
        if note_in_chord in chord_intervals:
            offset = chord_intervals.index(note_in_chord)
            return root + (note // 12) * 12 + chord_intervals[offset]

        return root + note_in_chord

    def _map_using_chord_table(
        self, note: int, track_type: Any, chord: Any
    ) -> Optional[int]:
        """Map note using style's chord table"""
        if not self.style or not self._current_section:
            return None

        section_type = self._current_section.section_type

        # Get chord table for current section
        if section_type not in self.style.chord_tables:
            return None

        chord_table = self.style.chord_tables[section_type]

        # Build chord key (root_type format like "0_major", "2_minor", etc.)
        root_val = chord.root.value
        chord_type_name = chord.chord_type.name.lower()
        chord_key = f"{root_val}_{chord_type_name}"

        # Try to get notes from chord table
        if chord_key in chord_table.chord_type_mappings:
            mapping = chord_table.chord_type_mappings[chord_key]
            if track_type in mapping:
                intervals = mapping[track_type]
                if intervals:
                    # Use the first interval as base
                    base_interval = intervals[0]
                    # Adjust octave to keep note in reasonable range
                    octave = (note // 12) - 5  # Start from around C3
                    return chord.root.value + base_interval + (octave * 12)

        # Try generic chord type (just root + type without bass inversion)
        generic_key = f"{root_val}_{chord.chord_type.name_display}"
        if generic_key in chord_table.chord_type_mappings:
            mapping = chord_table.chord_type_mappings[generic_key]
            if track_type in mapping:
                intervals = mapping[track_type]
                if intervals:
                    base_interval = intervals[0]
                    octave = (note // 12) - 5
                    return chord.root.value + base_interval + (octave * 12)

        return None

    def _handle_chord_change(self, chord: Any):
        """Handle detected chord changes"""
        if self.mode != AccompanimentMode.ON:
            return

        if self._current_section and self._is_filling:
            self._is_filling = False
            if self._target_section:
                self._transition_to(self._target_section)
                self._target_section = None
            else:
                self.next_main_section()

    def _processing_loop(self):
        """Main processing loop"""
        last_time = time.time()

        while self._running:
            current_time = time.time()
            elapsed = current_time - last_time
            last_time = current_time

            tick_increment = int(elapsed * 1000 / self._ms_per_tick)

            with self._lock:
                if self.playback_state == StylePlaybackState.PLAYING:
                    self._tick_position += tick_increment
                    self._process_events()

                    if self._tick_position >= self._ticks_per_bar:
                        self._tick_position = 0
                        self._bar_position += 1
                        self._beat_position = (
                            self._beat_position + 1
                        ) % self._time_signature_num

                        if self._bar_position >= self._current_section.length_bars:
                            self._loop_count += 1
                            self._bar_position = 0
                            self._tick_position = 0
                            self._schedule_section_events(self._current_section)

                elif self.playback_state == StylePlaybackState.COUNT_IN:
                    self._tick_position += tick_increment
                    if self._tick_position >= self._ticks_per_bar:
                        self._tick_position = 0
                        self._bar_position += 1
                        if self._bar_position >= self._current_section.count_in_bars:
                            self.playback_state = StylePlaybackState.PLAYING

            time.sleep(0.001)

    def _process_events(self):
        """Process and trigger scheduled events"""
        current_tick = self._tick_position

        for event in self._scheduled_events:
            if event.played:
                continue

            if event.tick <= current_tick:
                self._trigger_event(event)
                event.played = True

    def _trigger_event(self, event: StyleEvent):
        """Trigger a single note event"""
        track_state = self._track_states.get(event.track_type)
        if not track_state or track_state.muted:
            return

        if any(s.soloed for s in self._track_states.values()):
            if not track_state.soloed:
                return

        velocity = int(event.velocity * track_state.volume)
        if velocity < 1:
            return

        key = (event.channel, event.note)
        if key in self._active_notes:
            self._send_note_off(event.channel, event.note)

        self._send_note_on(event.channel, event.note, velocity)
        self._active_notes[key] = event.note

    def _send_note_on(self, channel: int, note: int, velocity: int):
        """Send note-on message"""
        if self._on_note_on:
            self._on_note_on(channel, note, velocity)

        if self.synthesizer and not self._internal_mode:
            try:
                self._internal_mode = True
                self.synthesizer.note_on(channel, note, velocity)
            except Exception:
                pass
            finally:
                self._internal_mode = False

    def _send_note_off(self, channel: int, note: int):
        """Send note-off message"""
        if self._on_note_off:
            self._on_note_off(channel, note)

        if self.synthesizer and not self._internal_mode:
            try:
                self._internal_mode = True
                self.synthesizer.note_off(channel, note)
            except Exception:
                pass
            finally:
                self._internal_mode = False

    def _all_notes_off(self):
        """Send all notes off for all channels"""
        for channel in range(16):
            for note in range(128):
                self._send_note_off(channel, note)
        self._active_notes.clear()

    def process_midi_note_on(self, channel: int, note: int, velocity: int):
        """Process incoming MIDI note-on for chord detection"""
        if self.mode in (AccompanimentMode.ON, AccompanimentMode.SYNC_START):
            if (
                self.config.chord_detection_zone_low
                <= note
                <= self.config.chord_detection_zone_high
            ):
                self.chord_detector.note_on(note, velocity)

        if self.mode == AccompanimentMode.SYNC_START:
            self.mode = AccompanimentMode.ON
            self._start_playback(self._target_section)

    def process_midi_note_off(self, channel: int, note: int):
        """Process incoming MIDI note-off"""
        if (
            self.config.chord_detection_zone_low
            <= note
            <= self.config.chord_detection_zone_high
        ):
            self.chord_detector.note_off(note)

    def get_status(self) -> Dict[str, Any]:
        """Get current status information"""
        return {
            "mode": self.mode.name,
            "playback_state": self.playback_state.name,
            "current_section": self._current_section.section_type.value
            if self._current_section
            else None,
            "tempo": self._tempo,
            "tick_position": self._tick_position,
            "bar_position": self._bar_position,
            "loop_count": self._loop_count,
            "is_filling": self._is_filling,
            "current_chord": self.chord_detector.get_current_chord().chord_name
            if self.chord_detector.get_current_chord()
            else None,
            "active_notes": len(self._active_notes),
            "scheduled_events": len(
                [e for e in self._scheduled_events if not e.played]
            ),
        }

    def reset(self):
        """Reset accompaniment state"""
        with self._lock:
            self._all_notes_off()
            self.chord_detector.reset()
            self._tick_position = 0
            self._bar_position = 0
            self._beat_position = 0
            self._loop_count = 0
            self._scheduled_events.clear()

    def shutdown(self):
        """Shutdown the accompaniment engine"""
        self._running = False
        self._all_notes_off()
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=1.0)
