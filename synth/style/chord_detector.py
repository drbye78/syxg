"""
Chord Detection System - Real-time Musical Chord Recognition

Provides comprehensive chord detection for auto-accompaniment,
supporting multiple detection algorithms and chord types.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np


class ChordRoot(Enum):
    """Musical root notes (C through B)"""

    C = 0
    C_SHARP = 1
    D = 2
    D_SHARP = 3
    E = 4
    F = 5
    F_SHARP = 6
    G = 7
    G_SHARP = 8
    A = 9
    A_SHARP = 10
    B = 11

    @property
    def name_display(self) -> str:
        names = {
            0: "C",
            1: "C#",
            2: "D",
            3: "D#",
            4: "E",
            5: "F",
            6: "F#",
            7: "G",
            8: "G#",
            9: "A",
            10: "A#",
            11: "B",
        }
        return names.get(self.value, "C")

    @classmethod
    def from_midi(cls, note: int) -> ChordRoot:
        return cls(note % 12)

    @classmethod
    def from_name(cls, name: str) -> ChordRoot:
        mapping = {
            "c": 0,
            "c#": 1,
            "db": 1,
            "d": 2,
            "d#": 3,
            "eb": 3,
            "e": 4,
            "f": 5,
            "f#": 6,
            "gb": 6,
            "g": 7,
            "g#": 8,
            "ab": 8,
            "a": 9,
            "a#": 10,
            "bb": 10,
            "b": 11,
        }
        return cls(mapping.get(name.lower().replace("♯", "#").replace("♭", "b"), 0))


class ChordType(Enum):
    """
    Chord type classifications with interval patterns.
    Based on Yamaha chord naming conventions.
    """

    MAJOR = auto()
    MINOR = auto()
    SEVENTH = auto()
    MAJOR_SEVENTH = auto()
    MINOR_SEVENTH = auto()
    DIMINISHED = auto()
    DIMINISHED_SEVENTH = auto()
    AUGMENTED = auto()
    SUSPENDED_SECOND = auto()
    SUSPENDED_FOURTH = auto()
    ADD_NINE = auto()
    MAJOR_SEVENTH_NINTH = auto()
    MINOR_MAJOR_SEVENTH = auto()
    SIXTH = auto()
    MINOR_SIXTH = auto()
    NINTH = auto()
    MAJOR_NINTH = auto()
    MINOR_NINTH = auto()
    ELEVENTH = auto()
    MAJOR_THIRTEENTH = auto()
    MINOR_THIRTEENTH = auto()
    HALF_DIMINISHED = auto()
    POWER = auto()
    UNKNOWN = auto()

    @property
    def intervals(self) -> list[int]:
        """Return interval semitones from root"""
        intervals = {
            ChordType.MAJOR: [0, 4, 7],
            ChordType.MINOR: [0, 3, 7],
            ChordType.SEVENTH: [0, 4, 7, 10],
            ChordType.MAJOR_SEVENTH: [0, 4, 7, 11],
            ChordType.MINOR_SEVENTH: [0, 3, 7, 10],
            ChordType.DIMINISHED: [0, 3, 6],
            ChordType.DIMINISHED_SEVENTH: [0, 3, 6, 9],
            ChordType.AUGMENTED: [0, 4, 8],
            ChordType.SUSPENDED_SECOND: [0, 2, 7],
            ChordType.SUSPENDED_FOURTH: [0, 5, 7],
            ChordType.ADD_NINE: [0, 4, 7, 14],
            ChordType.MAJOR_SEVENTH_NINTH: [0, 4, 7, 11, 14],
            ChordType.MINOR_MAJOR_SEVENTH: [0, 3, 7, 11],
            ChordType.SIXTH: [0, 4, 7, 9],
            ChordType.MINOR_SIXTH: [0, 3, 7, 9],
            ChordType.NINTH: [0, 4, 7, 10, 14],
            ChordType.MAJOR_NINTH: [0, 4, 7, 11, 14],
            ChordType.MINOR_NINTH: [0, 3, 7, 10, 14],
            ChordType.ELEVENTH: [0, 4, 7, 10, 14, 17],
            ChordType.MAJOR_THIRTEENTH: [0, 4, 7, 11, 14, 21],
            ChordType.MINOR_THIRTEENTH: [0, 3, 7, 10, 14, 21],
            ChordType.HALF_DIMINISHED: [0, 3, 6, 10],
            ChordType.POWER: [0, 7],
            ChordType.UNKNOWN: [],
        }
        return intervals.get(self, [])

    @property
    def name_display(self) -> str:
        names = {
            ChordType.MAJOR: "",
            ChordType.MINOR: "m",
            ChordType.SEVENTH: "7",
            ChordType.MAJOR_SEVENTH: "maj7",
            ChordType.MINOR_SEVENTH: "m7",
            ChordType.DIMINISHED: "dim",
            ChordType.DIMINISHED_SEVENTH: "dim7",
            ChordType.AUGMENTED: "aug",
            ChordType.SUSPENDED_SECOND: "sus2",
            ChordType.SUSPENDED_FOURTH: "sus4",
            ChordType.ADD_NINE: "add9",
            ChordType.MAJOR_SEVENTH_NINTH: "maj9",
            ChordType.MINOR_MAJOR_SEVENTH: "mMaj7",
            ChordType.SIXTH: "6",
            ChordType.MINOR_SIXTH: "m6",
            ChordType.NINTH: "9",
            ChordType.MAJOR_NINTH: "maj9",
            ChordType.MINOR_NINTH: "m9",
            ChordType.ELEVENTH: "11",
            ChordType.MAJOR_THIRTEENTH: "13",
            ChordType.MINOR_THIRTEENTH: "m13",
            ChordType.HALF_DIMINISHED: "m7♭5",
            ChordType.POWER: "5",
            ChordType.UNKNOWN: "?",
        }
        return names.get(self, "")

    @property
    def bass_interval(self) -> int | None:
        """Interval for bass note (inversions)"""
        return None

    @classmethod
    def from_intervals(cls, intervals: list[int]) -> ChordType:
        """Identify chord type from intervals"""
        normalized = sorted(set(i % 12 for i in intervals))

        type_mapping = {
            tuple([0, 4, 7]): ChordType.MAJOR,
            tuple([0, 3, 7]): ChordType.MINOR,
            tuple([0, 4, 7, 10]): ChordType.SEVENTH,
            tuple([0, 4, 7, 11]): ChordType.MAJOR_SEVENTH,
            tuple([0, 3, 7, 10]): ChordType.MINOR_SEVENTH,
            tuple([0, 3, 6]): ChordType.DIMINISHED,
            tuple([0, 3, 6, 9]): ChordType.DIMINISHED_SEVENTH,
            tuple([0, 4, 8]): ChordType.AUGMENTED,
            tuple([0, 2, 7]): ChordType.SUSPENDED_SECOND,
            tuple([0, 5, 7]): ChordType.SUSPENDED_FOURTH,
            tuple([0, 4, 7, 9]): ChordType.SIXTH,
            tuple([0, 3, 7, 9]): ChordType.MINOR_SIXTH,
            tuple([0, 3, 6, 10]): ChordType.HALF_DIMINISHED,
            tuple([0, 7]): ChordType.POWER,
        }

        return type_mapping.get(tuple(normalized), ChordType.UNKNOWN)

    @classmethod
    def from_name(cls, name: str) -> ChordType:
        """Parse chord type from name string"""
        name = name.lower().replace("♭", "b").replace("♯", "#").replace("Δ", "maj7")

        if "dim7" in name or "diminished7" in name:
            return ChordType.DIMINISHED_SEVENTH
        elif "dim" in name or "°" in name:
            return ChordType.DIMINISHED
        elif "aug" in name or "+" in name:
            return ChordType.AUGMENTED
        elif "sus2" in name:
            return ChordType.SUSPENDED_SECOND
        elif "sus4" in name or "sus" in name:
            return ChordType.SUSPENDED_FOURTH
        elif "m7b5" in name or "m7♭5" in name or "ø" in name:
            return ChordType.HALF_DIMINISHED
        elif "maj7" in name or "Δ7" in name or "maj9" in name:
            return ChordType.MAJOR_SEVENTH_NINTH if "9" in name else ChordType.MAJOR_SEVENTH
        elif "m7" in name or "min7" in name:
            return ChordType.MINOR_SEVENTH
        elif "mMaj7" in name:
            return ChordType.MINOR_MAJOR_SEVENTH
        elif "m9" in name:
            return ChordType.MINOR_NINTH
        elif "m6" in name:
            return ChordType.MINOR_SIXTH
        elif "m" in name or "min" in name:
            return ChordType.MINOR
        elif "7" in name:
            return ChordType.SEVENTH
        elif "9" in name:
            return ChordType.NINTH
        elif "11" in name:
            return ChordType.ELEVENTH
        elif "13" in name:
            return ChordType.MAJOR_THIRTEENTH
        elif "6" in name:
            return ChordType.SIXTH
        elif "5" in name:
            return ChordType.POWER
        elif "add9" in name:
            return ChordType.ADD_NINE
        else:
            return ChordType.MAJOR


@dataclass(slots=True)
class DetectedChord:
    """Result of chord detection"""

    root: ChordRoot
    chord_type: ChordType
    bass_note: int | None = None
    inversion: int = 0
    confidence: float = 0.0
    notes: list[int] = field(default_factory=list)
    timestamps: dict[int, float] = field(default_factory=dict)
    is_inversion: bool = False
    chord_name: str = ""

    def __post_init__(self):
        if not self.chord_name:
            self.chord_name = f"{self.root.name_display}{self.chord_type.name_display}"
            if self.is_inversion and self.bass_note is not None:
                bass_name = ChordRoot.from_midi(self.bass_note).name_display
                self.chord_name = (
                    f"{self.root.name_display}{self.chord_type.name_display}/{bass_name}"
                )

    @property
    def root_midi(self) -> int:
        return self.root.value

    @property
    def intervals(self) -> list[int]:
        return self.chord_type.intervals

    def get_notes_for_root(self, root_midi: int, octave: int = 3) -> list[int]:
        """Get actual MIDI notes for this chord"""
        base = root_midi + (octave * 12)
        return [base + i for i in self.chord_type.intervals]

    def get_all_notes(self, min_note: int = 36, max_note: int = 84) -> list[int]:
        """Get all notes in the chord within range"""
        if not self.notes:
            return []

        root = min(self.notes) if self.notes else 60
        result = []
        for interval in self.chord_type.intervals:
            for octave in range(-2, 6):
                note = root + interval + (octave * 12)
                if min_note <= note <= max_note:
                    result.append(note)
        return sorted(set(result))


@dataclass(slots=True)
class ChordDetectionConfig:
    """Configuration for chord detection"""

    detection_zone_low: int = 36
    detection_zone_high: int = 72
    min_notes_for_chord: int = 2
    max_notes_for_chord: int = 8
    detection_timeout_ms: int = 50
    voice_leading_threshold: float = 0.3
    use_bass_detection: bool = True
    bass_detection_threshold: int = 48
    ignore_root_octave: bool = True
    chroma_weighting: bool = True
    template_matching: bool = True
    on_chord_change: Callable[[DetectedChord], None] | None = None


class ChordDetector:
    """
    Real-time chord detection system for auto-accompaniment.

    Supports:
    - Multi-finger chord recognition
    - Bass note detection for inversions
    - Multiple detection algorithms
    - Configurable detection zones
    - Real-time callbacks
    """

    CHORD_TEMPLATES: dict[tuple[int, ...], ChordType] = {}

    def __init__(self, config: ChordDetectionConfig | None = None):
        self.config = config or ChordDetectionConfig()
        self._lock = threading.RLock()

        self._active_notes: dict[int, tuple[int, float]] = {}
        self._last_chord: DetectedChord | None = None
        self._chord_history: list[DetectedChord] = []
        self._detection_count = 0

        self._initialize_chord_templates()

    def _initialize_chord_templates(self):
        """Initialize chord recognition templates"""
        self.CHORD_TEMPLATES = {
            (0,): ChordType.MAJOR,
            (0, 4): ChordType.MAJOR,
            (0, 7): ChordType.MAJOR,
            (0, 4, 7): ChordType.MAJOR,
            (0, 3): ChordType.MINOR,
            (0, 3, 7): ChordType.MINOR,
            (0, 4, 7, 10): ChordType.SEVENTH,
            (0, 4, 7, 11): ChordType.MAJOR_SEVENTH,
            (0, 3, 7, 10): ChordType.MINOR_SEVENTH,
            (0, 3, 6): ChordType.DIMINISHED,
            (0, 3, 6, 9): ChordType.DIMINISHED_SEVENTH,
            (0, 4, 8): ChordType.AUGMENTED,
            (0, 2, 7): ChordType.SUSPENDED_SECOND,
            (0, 5, 7): ChordType.SUSPENDED_FOURTH,
            (0, 4, 7, 9): ChordType.SIXTH,
            (0, 3, 7, 9): ChordType.MINOR_SIXTH,
            (0, 3, 6, 10): ChordType.HALF_DIMINISHED,
            (0, 7): ChordType.POWER,
            (0, 4, 7, 10, 14): ChordType.NINTH,
            (0, 4, 7, 11, 14): ChordType.MAJOR_NINTH,
            (0, 3, 7, 10, 14): ChordType.MINOR_NINTH,
            (0, 4, 7, 10, 14, 17): ChordType.ELEVENTH,
        }

    def note_on(self, note: int, velocity: int = 100, timestamp: float | None = None):
        """Register a note-on event"""
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            if self.config.detection_zone_low <= note <= self.config.detection_zone_high:
                self._active_notes[note] = (velocity, timestamp)
                self._detect_chord()

    def note_off(self, note: int):
        """Register a note-off event"""
        with self._lock:
            if note in self._active_notes:
                del self._active_notes[note]
                self._detect_chord()

    def get_active_notes(self) -> list[int]:
        """Get currently active notes in detection zone"""
        with self._lock:
            return list(self._active_notes.keys())

    def _detect_chord(self):
        """Main chord detection routine"""
        if len(self._active_notes) < self.config.min_notes_for_chord:
            self._last_chord = None
            return

        notes = sorted(self._active_notes.keys())

        if notes[-1] - notes[0] > self.config.detection_zone_high - self.config.detection_zone_low:
            self._last_chord = None
            return

        if self.config.template_matching:
            chord = self._template_matching_detection(notes)
        else:
            chord = self._interval_based_detection(notes)

        if chord:
            self._last_chord = chord
            self._chord_history.append(chord)
            if len(self._chord_history) > 100:
                self._chord_history = self._chord_history[-50:]

            self._detection_count += 1

            if self.config.on_chord_change:
                self.config.on_chord_change(chord)

    def _template_matching_detection(self, notes: list[int]) -> DetectedChord | None:
        """Template-matching based chord detection"""
        if not notes:
            return None

        root = notes[0] % 12
        intervals = tuple(sorted((n % 12 - root) % 12 for n in notes))

        if intervals in self.CHORD_TEMPLATES:
            chord_type = self.CHORD_TEMPLATES[intervals]
        else:
            normalized = tuple(i % 12 for i in notes)
            interval_set = tuple(sorted(set((n - notes[0]) % 12 for n in notes)))
            chord_type = ChordType.from_intervals(list(interval_set))

        bass_note = None
        if self.config.use_bass_detection:
            bass_notes = [n for n in notes if n < self.config.bass_detection_threshold]
            if bass_notes:
                bass_note = bass_notes[0]

        confidence = self._calculate_confidence(notes, chord_type)

        chord = DetectedChord(
            root=ChordRoot(root),
            chord_type=chord_type,
            bass_note=bass_note,
            confidence=confidence,
            notes=notes,
            timestamps={n: t for n, (v, t) in self._active_notes.items()},
            is_inversion=bass_note is not None and bass_note % 12 != root,
        )

        return chord

    def _interval_based_detection(self, notes: list[int]) -> DetectedChord | None:
        """Interval-based chord detection"""
        if not notes:
            return None

        chroma = self._compute_chroma(notes)

        root = np.argmax(chroma)

        intervals = [(i - root) % 12 for i in range(12) if chroma[i] > 0]
        chord_type = ChordType.from_intervals(intervals)

        bass_note = None
        if self.config.use_bass_detection:
            bass_notes = [n for n in notes if n < self.config.bass_detection_threshold]
            if bass_notes:
                bass_note = bass_notes[0]

        confidence = self._calculate_confidence(notes, chord_type)

        return DetectedChord(
            root=ChordRoot(root),
            chord_type=chord_type,
            bass_note=bass_note,
            confidence=confidence,
            notes=notes,
            timestamps={n: t for n, (v, t) in self._active_notes.items()},
            is_inversion=bass_note is not None and bass_note % 12 != root,
        )

    def _compute_chroma(self, notes: list[int]) -> np.ndarray:
        """Compute chromagram from notes"""
        chroma = np.zeros(12)
        for note in notes:
            chroma[note % 12] += 1
        if self.config.chroma_weighting:
            weights = np.array([1.0, 0.8, 0.9, 0.8, 1.0, 0.9, 0.8, 1.0, 0.8, 0.9, 0.8, 0.9])
            chroma = chroma * weights
        return chroma / (np.sum(chroma) + 0.001)

    def _calculate_confidence(self, notes: list[int], chord_type: ChordType) -> float:
        """Calculate detection confidence"""
        if not notes:
            return 0.0

        intervals = [n % 12 for n in notes]
        expected = chord_type.intervals

        matches = sum(1 for i in intervals if i in expected)
        confidence = matches / max(len(expected), len(notes))

        note_count_bonus = min(1.0, len(notes) / 4.0)

        return min(1.0, confidence * 0.7 + note_count_bonus * 0.3)

    def get_current_chord(self) -> DetectedChord | None:
        """Get the currently detected chord"""
        with self._lock:
            return self._last_chord

    def get_chord_history(self, count: int = 10) -> list[DetectedChord]:
        """Get recent chord detection history"""
        with self._lock:
            return self._chord_history[-count:]

    def force_chord(self, root: ChordRoot, chord_type: ChordType, bass_note: int | None = None):
        """Force a specific chord (for manual input)"""
        chord = DetectedChord(
            root=root,
            chord_type=chord_type,
            bass_note=bass_note,
            confidence=1.0,
            notes=[root.value + (bass_note or root.value) % 12],
            is_inversion=bass_note is not None,
        )

        with self._lock:
            self._last_chord = chord
            self._chord_history.append(chord)

    def reset(self):
        """Reset detector state"""
        with self._lock:
            self._active_notes.clear()
            self._last_chord = None

    @property
    def detection_count(self) -> int:
        return self._detection_count

    def get_detailed_info(self) -> dict:
        """Get detailed detector information"""
        with self._lock:
            return {
                "active_notes": len(self._active_notes),
                "current_chord": self._last_chord.chord_name if self._last_chord else None,
                "detection_count": self._detection_count,
                "history_count": len(self._chord_history),
                "config": {
                    "zone_low": self.config.detection_zone_low,
                    "zone_high": self.config.detection_zone_high,
                    "bass_detection": self.config.use_bass_detection,
                },
            }
