"""
Sequencer Data Types and Constants

Core data structures for the built-in sequencer including notes,
patterns, songs, and configuration types.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time


class QuantizeMode(Enum):
    """Quantization modes for rhythm correction"""
    OFF = 0
    Q_8TH = 1      # 1/8 notes
    Q_16TH = 2     # 1/16 notes
    Q_32ND = 3     # 1/32 notes
    Q_TRIPLET = 4  # Triplet quantization
    Q_SWING = 5    # Swing quantization


class GrooveTemplate(Enum):
    """Pre-defined groove templates"""
    STRAIGHT = 0
    SWING_8TH = 1
    SWING_16TH = 2
    TRIPLET = 3
    SHUFFLE = 4
    HALF_TIME = 5
    DOUBLE_TIME = 6


class RecordingMode(Enum):
    """Recording modes for the sequencer"""
    REAL_TIME = 0
    STEP_INPUT = 1
    OVERDUB = 2
    REPLACE = 3


@dataclass
class NoteEvent:
    """Represents a MIDI note event in the sequencer"""
    time: float          # Time in beats (quarter notes)
    duration: float      # Duration in beats
    note_number: int     # MIDI note number (0-127)
    velocity: int        # Note velocity (0-127)
    channel: int = 0     # MIDI channel (0-15)
    track_id: int = 0    # Track identifier

    def to_midi_bytes(self) -> Tuple[bytes, bytes]:
        """Convert to MIDI message bytes"""
        # Note on: 0x90 + channel, note, velocity
        note_on = bytes([0x90 + self.channel, self.note_number, self.velocity])
        # Note off: 0x80 + channel, note, 0
        note_off = bytes([0x80 + self.channel, self.note_number, 0])
        return note_on, note_off

    def get_end_time(self) -> float:
        """Get the end time of this note"""
        return self.time + self.duration


@dataclass
class ControlEvent:
    """Represents a MIDI control change event"""
    time: float          # Time in beats
    controller: int      # Controller number (0-127)
    value: int          # Controller value (0-127)
    channel: int = 0     # MIDI channel (0-15)
    track_id: int = 0    # Track identifier

    def to_midi_bytes(self) -> bytes:
        """Convert to MIDI message bytes"""
        # Control change: 0xB0 + channel, controller, value
        return bytes([0xB0 + self.channel, self.controller, self.value])


@dataclass
class Pattern:
    """A sequencer pattern containing note and control events"""
    id: int
    name: str
    length: int          # Length in beats (usually 1-16)
    resolution: int = 96 # PPQ (pulses per quarter note)

    # Event storage
    notes: List[NoteEvent] = None
    controls: List[ControlEvent] = None

    # Pattern settings
    tempo: float = 120.0
    time_signature: Tuple[int, int] = (4, 4)  # numerator, denominator
    swing_amount: float = 0.0  # 0.0 to 1.0
    quantize_mode: QuantizeMode = QuantizeMode.OFF

    # Metadata
    created_time: float = None
    modified_time: float = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []
        if self.controls is None:
            self.controls = []
        if self.created_time is None:
            self.created_time = time.time()
        if self.modified_time is None:
            self.modified_time = time.time()

    def add_note(self, note: NoteEvent):
        """Add a note event to the pattern"""
        self.notes.append(note)
        self._update_modified_time()

    def add_control(self, control: ControlEvent):
        """Add a control event to the pattern"""
        self.controls.append(control)
        self._update_modified_time()

    def remove_note(self, note_index: int):
        """Remove a note by index"""
        if 0 <= note_index < len(self.notes):
            del self.notes[note_index]
            self._update_modified_time()

    def remove_control(self, control_index: int):
        """Remove a control event by index"""
        if 0 <= control_index < len(self.controls):
            del self.controls[control_index]
            self._update_modified_time()

    def clear(self):
        """Clear all events"""
        self.notes.clear()
        self.controls.clear()
        self._update_modified_time()

    def get_notes_in_range(self, start_time: float, end_time: float) -> List[NoteEvent]:
        """Get all notes within a time range"""
        return [note for note in self.notes
                if note.time >= start_time and note.time < end_time]

    def get_total_duration(self) -> float:
        """Get total duration of the pattern in beats"""
        if not self.notes:
            return self.length

        max_end_time = max(note.get_end_time() for note in self.notes)
        return max(max_end_time, self.length)

    def quantize_notes(self, mode: QuantizeMode, strength: float = 1.0):
        """Apply quantization to notes"""
        if mode == QuantizeMode.OFF:
            return

        for note in self.notes:
            quantized_time = self._quantize_time(note.time, mode)
            note.time = note.time * (1.0 - strength) + quantized_time * strength

        self.quantize_mode = mode
        self._update_modified_time()

    def apply_swing(self, amount: float):
        """Apply swing timing to notes"""
        self.swing_amount = amount
        # Swing implementation would go here
        self._update_modified_time()

    def _quantize_time(self, time: float, mode: QuantizeMode) -> float:
        """Quantize a time value according to the mode"""
        if mode == QuantizeMode.Q_8TH:
            grid = 0.5  # Half beats (8th notes)
        elif mode == QuantizeMode.Q_16TH:
            grid = 0.25  # Quarter beats (16th notes)
        elif mode == QuantizeMode.Q_32ND:
            grid = 0.125  # Eighth beats (32nd notes)
        elif mode == QuantizeMode.Q_TRIPLET:
            grid = 1.0 / 3.0  # Triplet grid
        else:
            return time

        # Round to nearest grid line
        return round(time / grid) * grid

    def _update_modified_time(self):
        """Update the modification timestamp"""
        self.modified_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'length': self.length,
            'resolution': self.resolution,
            'tempo': self.tempo,
            'time_signature': list(self.time_signature),
            'swing_amount': self.swing_amount,
            'quantize_mode': self.quantize_mode.value,
            'notes': [
                {
                    'time': note.time,
                    'duration': note.duration,
                    'note_number': note.note_number,
                    'velocity': note.velocity,
                    'channel': note.channel,
                    'track_id': note.track_id
                }
                for note in self.notes
            ],
            'controls': [
                {
                    'time': ctrl.time,
                    'controller': ctrl.controller,
                    'value': ctrl.value,
                    'channel': ctrl.channel,
                    'track_id': ctrl.track_id
                }
                for ctrl in self.controls
            ],
            'created_time': self.created_time,
            'modified_time': self.modified_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create pattern from dictionary"""
        pattern = cls(
            id=data['id'],
            name=data['name'],
            length=data['length'],
            resolution=data.get('resolution', 96),
            tempo=data.get('tempo', 120.0),
            time_signature=tuple(data.get('time_signature', [4, 4])),
            swing_amount=data.get('swing_amount', 0.0)
        )

        pattern.quantize_mode = QuantizeMode(data.get('quantize_mode', 0))
        pattern.created_time = data.get('created_time', time.time())
        pattern.modified_time = data.get('modified_time', time.time())

        # Load notes
        for note_data in data.get('notes', []):
            note = NoteEvent(
                time=note_data['time'],
                duration=note_data['duration'],
                note_number=note_data['note_number'],
                velocity=note_data['velocity'],
                channel=note_data.get('channel', 0),
                track_id=note_data.get('track_id', 0)
            )
            pattern.notes.append(note)

        # Load controls
        for ctrl_data in data.get('controls', []):
            ctrl = ControlEvent(
                time=ctrl_data['time'],
                controller=ctrl_data['controller'],
                value=ctrl_data['value'],
                channel=ctrl_data.get('channel', 0),
                track_id=ctrl_data.get('track_id', 0)
            )
            pattern.controls.append(ctrl)

        return pattern


@dataclass
class Track:
    """A track within a song containing pattern references and settings"""
    id: int
    name: str
    channel: int = 0      # MIDI channel for this track
    pattern_id: int = 0   # Current pattern assigned to this track
    muted: bool = False
    solo: bool = False
    volume: int = 100     # Track volume (0-127)
    pan: int = 64         # Track pan (0-127, 64=center)

    # Pattern sequence for this track (pattern_id, start_time, length_multiplier)
    sequence: List[Tuple[int, float, float]] = None

    def __post_init__(self):
        if self.sequence is None:
            self.sequence = []

    def add_pattern_instance(self, pattern_id: int, start_time: float,
                           length_multiplier: float = 1.0):
        """Add a pattern instance to this track"""
        self.sequence.append((pattern_id, start_time, length_multiplier))

    def remove_pattern_instance(self, index: int):
        """Remove a pattern instance by index"""
        if 0 <= index < len(self.sequence):
            del self.sequence[index]

    def get_patterns_at_time(self, time: float) -> List[Tuple[int, float, float]]:
        """Get all pattern instances that should play at the given time"""
        active_patterns = []
        for pattern_id, start_time, length_mult in self.sequence:
            pattern_length = 4.0 * length_mult  # Assume 4 beats per pattern
            if start_time <= time < start_time + pattern_length:
                active_patterns.append((pattern_id, start_time, length_mult))
        return active_patterns

    def clear_sequence(self):
        """Clear all pattern instances"""
        self.sequence.clear()


@dataclass
class Song:
    """A song containing multiple tracks and arrangement data"""
    id: int
    name: str
    tempo: float = 120.0
    time_signature: Tuple[int, int] = (4, 4)

    # Track management
    tracks: List[Track] = None

    # Song structure (could be expanded for more complex arrangements)
    length: int = 16  # Length in measures

    # Metadata
    created_time: float = None
    modified_time: float = None

    def __post_init__(self):
        if self.tracks is None:
            self.tracks = []
        if self.created_time is None:
            self.created_time = time.time()
        if self.modified_time is None:
            self.modified_time = time.time()

    def add_track(self, track: Track):
        """Add a track to the song"""
        self.tracks.append(track)
        self._update_modified_time()

    def remove_track(self, track_id: int):
        """Remove a track by ID"""
        self.tracks = [t for t in self.tracks if t.id != track_id]
        self._update_modified_time()

    def get_track(self, track_id: int) -> Optional[Track]:
        """Get track by ID"""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None

    def get_active_tracks_at_time(self, time: float) -> List[Track]:
        """Get tracks that have content at the given time"""
        active_tracks = []
        for track in self.tracks:
            if not track.muted and track.get_patterns_at_time(time):
                active_tracks.append(track)
        return active_tracks

    def _update_modified_time(self):
        """Update modification timestamp"""
        self.modified_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert song to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'tempo': self.tempo,
            'time_signature': list(self.time_signature),
            'length': self.length,
            'tracks': [
                {
                    'id': track.id,
                    'name': track.name,
                    'channel': track.channel,
                    'pattern_id': track.pattern_id,
                    'muted': track.muted,
                    'solo': track.solo,
                    'volume': track.volume,
                    'pan': track.pan,
                    'sequence': list(track.sequence)
                }
                for track in self.tracks
            ],
            'created_time': self.created_time,
            'modified_time': self.modified_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        """Create song from dictionary"""
        song = cls(
            id=data['id'],
            name=data['name'],
            tempo=data.get('tempo', 120.0),
            time_signature=tuple(data.get('time_signature', [4, 4])),
            length=data.get('length', 16)
        )

        song.created_time = data.get('created_time', time.time())
        song.modified_time = data.get('modified_time', time.time())

        # Load tracks
        for track_data in data.get('tracks', []):
            track = Track(
                id=track_data['id'],
                name=track_data['name'],
                channel=track_data.get('channel', 0),
                pattern_id=track_data.get('pattern_id', 0),
                muted=track_data.get('muted', False),
                solo=track_data.get('solo', False),
                volume=track_data.get('volume', 100),
                pan=track_data.get('pan', 64)
            )

            # Load sequence
            track.sequence = [tuple(seq) for seq in track_data.get('sequence', [])]

            song.tracks.append(track)

        return song
