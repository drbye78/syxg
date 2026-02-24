"""
Scale Detection System

Provides musical scale/mode detection for intelligent chord voicings
and harmonic context awareness.

Features:
- 15+ scale types (major, minor modes, pentatonic, blues, etc.)
- Krumhansl-Schmiedler key-finding algorithm
- Scale-aware chord voicing suggestions
- Real-time scale detection from note history
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any
import threading
import time
import numpy as np


class ScaleType(Enum):
    """Musical scale types."""

    MAJOR = "major"
    NATURAL_MINOR = "natural_minor"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"
    BLUES_MAJOR = "blues_major"
    BLUES_MINOR = "blues_minor"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    WHOLE_TONE = "whole_tone"
    DIMINISHED = "diminished"
    CUSTOM = "custom"


@dataclass
class ScalePattern:
    """
    Scale pattern definition.
    
    Attributes:
        name: Human-readable scale name
        scale_type: ScaleType enum value
        intervals: Semitone intervals from root (e.g., [0, 2, 4, 5, 7, 9, 11] for major)
        chroma_profile: K-S profile weights for key detection (12 values)
    """
    name: str
    scale_type: ScaleType
    intervals: List[int]
    chroma_profile: List[float] = field(default_factory=list)


# Krumhansl-Schmiedler key profiles for major and minor keys
# These are empirically derived probe tone ratings
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Scale patterns with intervals and chroma profiles
SCALE_PATTERNS: Dict[ScaleType, ScalePattern] = {
    ScaleType.MAJOR: ScalePattern(
        name="Major (Ionian)",
        scale_type=ScaleType.MAJOR,
        intervals=[0, 2, 4, 5, 7, 9, 11],
        chroma_profile=MAJOR_PROFILE,
    ),
    ScaleType.NATURAL_MINOR: ScalePattern(
        name="Natural Minor (Aeolian)",
        scale_type=ScaleType.NATURAL_MINOR,
        intervals=[0, 2, 3, 5, 7, 8, 10],
        chroma_profile=MINOR_PROFILE,
    ),
    ScaleType.HARMONIC_MINOR: ScalePattern(
        name="Harmonic Minor",
        scale_type=ScaleType.HARMONIC_MINOR,
        intervals=[0, 2, 3, 5, 7, 8, 11],
        chroma_profile=[6.0, 2.5, 3.5, 5.0, 2.5, 3.5, 2.0, 5.5, 4.5, 2.5, 4.0, 3.5],
    ),
    ScaleType.MELODIC_MINOR: ScalePattern(
        name="Melodic Minor (Jazz)",
        scale_type=ScaleType.MELODIC_MINOR,
        intervals=[0, 2, 3, 5, 7, 9, 11],
        chroma_profile=[6.0, 2.5, 3.5, 5.0, 2.5, 4.0, 2.5, 5.0, 4.0, 3.5, 3.0, 3.0],
    ),
    ScaleType.DORIAN: ScalePattern(
        name="Dorian",
        scale_type=ScaleType.DORIAN,
        intervals=[0, 2, 3, 5, 7, 9, 10],
        chroma_profile=[5.5, 2.5, 3.5, 5.5, 2.5, 4.0, 2.5, 5.0, 3.5, 3.5, 3.0, 2.5],
    ),
    ScaleType.PHRYGIAN: ScalePattern(
        name="Phrygian",
        scale_type=ScaleType.PHRYGIAN,
        intervals=[0, 1, 3, 5, 7, 8, 10],
        chroma_profile=[5.5, 3.0, 3.5, 5.0, 2.5, 3.5, 2.5, 5.0, 3.5, 3.0, 3.0, 2.5],
    ),
    ScaleType.LYDIAN: ScalePattern(
        name="Lydian",
        scale_type=ScaleType.LYDIAN,
        intervals=[0, 2, 4, 6, 7, 9, 11],
        chroma_profile=[6.0, 2.5, 3.5, 2.0, 4.5, 4.5, 3.0, 5.5, 2.5, 3.5, 2.5, 3.0],
    ),
    ScaleType.MIXOLYDIAN: ScalePattern(
        name="Mixolydian",
        scale_type=ScaleType.MIXOLYDIAN,
        intervals=[0, 2, 4, 5, 7, 9, 10],
        chroma_profile=[6.0, 2.5, 3.5, 2.5, 4.5, 4.0, 2.5, 5.0, 2.5, 3.5, 2.5, 2.5],
    ),
    ScaleType.LOCRIAN: ScalePattern(
        name="Locrian",
        scale_type=ScaleType.LOCRIAN,
        intervals=[0, 1, 3, 5, 6, 8, 10],
        chroma_profile=[5.0, 3.0, 3.5, 5.0, 2.5, 3.5, 3.0, 4.5, 3.5, 3.0, 3.0, 2.5],
    ),
    ScaleType.PENTATONIC_MAJOR: ScalePattern(
        name="Pentatonic Major",
        scale_type=ScaleType.PENTATONIC_MAJOR,
        intervals=[0, 2, 4, 7, 9],
        chroma_profile=[6.5, 2.0, 4.0, 2.0, 4.5, 4.0, 2.0, 5.5, 2.0, 4.0, 2.0, 2.5],
    ),
    ScaleType.PENTATONIC_MINOR: ScalePattern(
        name="Pentatonic Minor",
        scale_type=ScaleType.PENTATONIC_MINOR,
        intervals=[0, 3, 5, 7, 10],
        chroma_profile=[6.0, 2.5, 2.5, 5.5, 2.5, 4.0, 2.5, 5.0, 2.5, 2.5, 3.5, 2.5],
    ),
    ScaleType.BLUES_MAJOR: ScalePattern(
        name="Blues Major",
        scale_type=ScaleType.BLUES_MAJOR,
        intervals=[0, 2, 3, 4, 7, 9],
        chroma_profile=[6.0, 2.5, 4.0, 3.5, 4.5, 3.5, 2.0, 5.5, 2.5, 4.0, 2.0, 2.5],
    ),
    ScaleType.BLUES_MINOR: ScalePattern(
        name="Blues Minor",
        scale_type=ScaleType.BLUES_MINOR,
        intervals=[0, 3, 4, 5, 7, 10],
        chroma_profile=[6.0, 2.5, 2.5, 5.5, 3.5, 4.0, 2.5, 5.0, 2.5, 2.5, 3.5, 2.5],
    ),
    ScaleType.WHOLE_TONE: ScalePattern(
        name="Whole Tone",
        scale_type=ScaleType.WHOLE_TONE,
        intervals=[0, 2, 4, 6, 8, 10],
        chroma_profile=[5.0, 3.0, 5.0, 3.0, 5.0, 3.0, 5.0, 3.0, 5.0, 3.0, 5.0, 3.0],
    ),
    ScaleType.DIMINISHED: ScalePattern(
        name="Diminished (Octatonic)",
        scale_type=ScaleType.DIMINISHED,
        intervals=[0, 1, 3, 4, 6, 7, 9, 10],
        chroma_profile=[5.0, 3.5, 3.5, 5.0, 3.5, 3.5, 5.0, 3.5, 3.5, 5.0, 3.5, 3.5],
    ),
}


@dataclass
class DetectedScale:
    """
    Result of scale/key detection.
    
    Attributes:
        root: Root note (0-11, C=0)
        scale_type: Detected scale type
        confidence: Confidence score (0.0-1.0)
        chroma: Current chroma vector
        fit_score: How well notes fit the detected scale
        notes_in_scale: List of MIDI note numbers in the scale
    """
    root: int
    scale_type: ScaleType
    confidence: float = 0.0
    chroma: Optional[np.ndarray] = None
    fit_score: float = 0.0
    notes_in_scale: List[int] = field(default_factory=list)

    @property
    def root_name(self) -> str:
        """Get root note name."""
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[self.root]

    @property
    def full_name(self) -> str:
        """Get full scale name."""
        return f"{self.root_name} {SCALE_PATTERNS[self.scale_type].name}"

    @property
    def is_major(self) -> bool:
        """Check if scale is major-type."""
        return self.scale_type in [
            ScaleType.MAJOR,
            ScaleType.LYDIAN,
            ScaleType.MIXOLYDIAN,
            ScaleType.PENTATONIC_MAJOR,
            ScaleType.BLUES_MAJOR,
        ]

    @property
    def is_minor(self) -> bool:
        """Check if scale is minor-type."""
        return self.scale_type in [
            ScaleType.NATURAL_MINOR,
            ScaleType.HARMONIC_MINOR,
            ScaleType.MELODIC_MINOR,
            ScaleType.DORIAN,
            ScaleType.PHRYGIAN,
            ScaleType.LOCRIAN,
            ScaleType.PENTATONIC_MINOR,
            ScaleType.BLUES_MINOR,
        ]

    def get_scale_notes(self, root_midi: int = 60, octaves: int = 2) -> List[int]:
        """
        Get all MIDI note numbers in the scale.
        
        Args:
            root_midi: Base MIDI note number for root
            octaves: Number of octaves to generate
            
        Returns:
            List of MIDI note numbers in the scale
        """
        pattern = SCALE_PATTERNS[self.scale_type]
        notes = []

        for octave in range(octaves):
            for interval in pattern.intervals:
                note = root_midi + (octave * 12) + interval
                notes.append(note)

        return notes

    def is_diatonic(self, note: int) -> bool:
        """
        Check if a note is in the scale.
        
        Args:
            note: MIDI note number to check
            
        Returns:
            True if note is in scale
        """
        pitch_class = note % 12
        pattern = SCALE_PATTERNS[self.scale_type]
        return pitch_class in pattern.intervals

    def get_tension_level(self, note: int) -> str:
        """
        Get tension level of a note relative to the scale.
        
        Args:
            note: MIDI note number
            
        Returns:
            'chord_tone', 'scale_tone', 'tension', or 'avoid'
        """
        pitch_class = note % 12
        pattern = SCALE_PATTERNS[self.scale_type]

        if pitch_class in pattern.intervals:
            # Check if it's a chord tone (1, 3, 5, 7)
            if pitch_class in [0, 4, 7, 11]:
                return "chord_tone"
            return "scale_tone"

        # Check common tensions
        tensions = {
            ScaleType.MAJOR: [2, 5, 9],  # 9, 11, 13
            ScaleType.NATURAL_MINOR: [2, 5, 8],  # b9, 11, b13
        }

        if pitch_class in tensions.get(self.scale_type, []):
            return "tension"

        return "avoid"


@dataclass
class ScaleDetectionConfig:
    """
    Configuration for scale detection.
    
    Attributes:
        history_size: Number of chords/notes to analyze
        min_confidence: Minimum confidence for detection
        update_interval: How often to update detection (ms)
        use_chord_history: Use chord history for detection
        use_note_history: Use individual note history
        key_change_threshold: Confidence drop to trigger key change
    """
    history_size: int = 50
    min_confidence: float = 0.6
    update_interval: int = 500
    use_chord_history: bool = True
    use_note_history: bool = True
    key_change_threshold: float = 0.3


class ScaleDetector:
    """
    Real-time scale/key detection system.
    
    Uses the Krumhansl-Schmiedler key-finding algorithm to detect
    the musical key from note and chord history.
    
    Features:
    - 15+ scale types supported
    - Real-time chroma analysis
    - Chord history integration
    - Confidence scoring
    - Scale-aware suggestions
    """

    def __init__(self, config: Optional[ScaleDetectionConfig] = None):
        self.config = config or ScaleDetectionConfig()
        self._lock = threading.RLock()

        # Note history for chroma computation
        self._note_history: List[Tuple[int, float]] = []  # (note, timestamp)
        self._chord_history: List[Any] = []  # DetectedChord objects
        self._chroma: np.ndarray = np.zeros(12)

        # Current detection
        self._current_scale: Optional[DetectedScale] = None
        self._last_update: float = 0.0
        self._detection_count: int = 0

    def add_note(self, note: int, velocity: int = 100, timestamp: Optional[float] = None):
        """
        Add a note to the detection history.
        
        Args:
            note: MIDI note number
            velocity: Note velocity (for weighting)
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            self._note_history.append((note, timestamp))

            # Trim history if too long
            if len(self._note_history) > self.config.history_size * 4:
                self._note_history = self._note_history[-self.config.history_size * 2:]

            # Update chroma
            self._update_chroma()

            # Check if we should update detection
            if time.time() - self._last_update > self.config.update_interval / 1000:
                self._detect_scale()

    def remove_note(self, note: int):
        """
        Remove a note from the detection history.
        
        Args:
            note: MIDI note number to remove
        """
        with self._lock:
            self._note_history = [(n, t) for n, t in self._note_history if n != note]

    def add_chord(self, chord: Any):
        """
        Add a detected chord to the history.
        
        Args:
            chord: DetectedChord object
        """
        with self._lock:
            self._chord_history.append(chord)

            # Trim history
            if len(self._chord_history) > self.config.history_size:
                self._chord_history = self._chord_history[-self.config.history_size // 2:]

            # Update detection
            if self.config.use_chord_history:
                self._detect_scale()

    def _update_chroma(self):
        """Update chroma vector from note history."""
        chroma = np.zeros(12)

        # Weight recent notes more heavily
        current_time = time.time()
        decay_factor = 0.95

        for note, timestamp in reversed(self._note_history[-100:]):
            age = current_time - timestamp
            weight = (decay_factor ** age) * 0.5  # Velocity weighting would go here
            chroma[note % 12] += weight

        # Normalize
        total = np.sum(chroma)
        if total > 0:
            chroma = chroma / total

        self._chroma = chroma

    def _detect_scale(self):
        """
        Detect the current scale/key using K-S algorithm.
        """
        self._last_update = time.time()

        if len(self._note_history) < 3 and len(self._chord_history) < 2:
            return

        # Combine chroma from notes and chords
        combined_chroma = self._chroma.copy()

        if self.config.use_chord_history and self._chord_history:
            chord_chroma = self._compute_chord_chroma()
            combined_chroma = (combined_chroma + chord_chroma) / 2

        # Find best matching key
        best_root = 0
        best_scale = ScaleType.MAJOR
        best_score = 0.0

        # Try all 24 keys (12 roots × 2 modes)
        for root in range(12):
            for scale_type in [ScaleType.MAJOR, ScaleType.NATURAL_MINOR]:
                pattern = SCALE_PATTERNS[scale_type]
                rotated_profile = np.roll(pattern.chroma_profile, root)

                # Correlation score
                score = np.corrcoef(combined_chroma, rotated_profile)[0, 1]

                if score > best_score:
                    best_score = score
                    best_root = root
                    best_scale = scale_type

        # Calculate fit score
        fit_score = self._calculate_fit_score(best_root, best_scale)

        # Create detection result
        if best_score >= self.config.min_confidence:
            self._current_scale = DetectedScale(
                root=best_root,
                scale_type=best_scale,
                confidence=best_score,
                chroma=combined_chroma.copy(),
                fit_score=fit_score,
                notes_in_scale=self._get_scale_notes_in_range(best_root, best_scale),
            )
            self._detection_count += 1

    def _compute_chord_chroma(self) -> np.ndarray:
        """Compute chroma from chord history."""
        chroma = np.zeros(12)

        for chord in self._chord_history[-20:]:
            if hasattr(chord, 'notes'):
                for note in chord.notes:
                    chroma[note % 12] += 1
            elif hasattr(chord, 'root_midi'):
                # Add chord tones based on type
                intervals = chord.intervals if hasattr(chord, 'intervals') else [0, 4, 7]
                for interval in intervals:
                    chroma[(chord.root_midi + interval) % 12] += 1

        # Normalize
        total = np.sum(chroma)
        if total > 0:
            chroma = chroma / total

        return chroma

    def _calculate_fit_score(self, root: int, scale_type: ScaleType) -> float:
        """
        Calculate how well recent notes fit the detected scale.
        
        Returns:
            Fit score (0.0-1.0)
        """
        pattern = SCALE_PATTERNS[scale_type]
        scale_pitches = set((root + i) % 12 for i in pattern.intervals)

        if not self._note_history:
            return 1.0

        # Check last N notes
        recent_notes = self._note_history[-20:]
        in_scale = sum(1 for note, _ in recent_notes if (note % 12) in scale_pitches)

        return in_scale / len(recent_notes)

    def _get_scale_notes_in_range(self, root: int, scale_type: ScaleType) -> List[int]:
        """Get scale notes in typical playing range."""
        pattern = SCALE_PATTERNS[scale_type]
        notes = []

        for octave in range(2, 6):  # C2 to C6
            for interval in pattern.intervals:
                note = root + (octave * 12) + interval
                if 36 <= note <= 96:  # Typical range
                    notes.append(note)

        return sorted(notes)

    def get_current_scale(self) -> Optional[DetectedScale]:
        """Get the currently detected scale."""
        with self._lock:
            return self._current_scale

    def get_suggested_voicing(self, chord_root: int, chord_type: str) -> List[int]:
        """
        Get a scale-appropriate voicing for a chord.
        
        Args:
            chord_root: Root note (0-11)
            chord_type: Chord type string
            
        Returns:
            List of intervals that fit the scale
        """
        scale = self._current_scale
        if not scale:
            return [0, 4, 7]  # Default major triad

        pattern = SCALE_PATTERNS[scale.scale_type]
        scale_intervals = set(pattern.intervals)

        # Build voicing from scale tones
        voicing = []
        current = chord_root % 12

        # Add chord tones that are in scale
        for interval in [0, 4, 7, 11, 3, 10, 2, 9, 5, 13]:  # Priority order
            pitch = (current + interval) % 12
            if pitch in scale_intervals and interval not in voicing:
                voicing.append(interval)
                if len(voicing) >= 4:  # 4-note voicing
                    break

        return voicing if voicing else [0, 4, 7]

    def is_chord_diatonic(self, chord_root: int, chord_type: str) -> bool:
        """
        Check if a chord is diatonic to the current scale.
        
        Args:
            chord_root: Root note (0-11)
            chord_type: Chord type string
            
        Returns:
            True if chord is diatonic
        """
        scale = self._current_scale
        if not scale:
            return True

        pattern = SCALE_PATTERNS[scale.scale_type]
        scale_pitches = set((scale.root + i) % 12 for i in pattern.intervals)

        # Check if chord root is in scale
        if chord_root % 12 not in scale_pitches:
            return False

        # Check chord tones
        from synth.style.chord_detector import ChordType
        type_map = {
            "major": [0, 4, 7],
            "minor": [0, 3, 7],
            "seventh": [0, 4, 7, 10],
            "major_seventh": [0, 4, 7, 11],
            "minor_seventh": [0, 3, 7, 10],
        }

        intervals = type_map.get(chord_type.lower(), [0, 4, 7])

        for interval in intervals:
            pitch = (chord_root + interval) % 12
            if pitch not in scale_pitches:
                return False

        return True

    def get_diatonic_chords(self) -> Dict[int, str]:
        """
        Get all diatonic chords in the current scale.
        
        Returns:
            Dict mapping scale degree to chord type
        """
        scale = self._current_scale
        if not scale:
            return {}

        # Diatonic chords for major scale
        major_chords = {
            0: "major",
            2: "minor",
            4: "minor",
            5: "major",
            7: "major",
            9: "minor",
            11: "diminished",
        }

        # Diatonic chords for natural minor
        minor_chords = {
            0: "minor",
            2: "diminished",
            3: "major",
            5: "minor",
            7: "minor",
            8: "major",
            10: "major",
        }

        if scale.is_major:
            return major_chords
        else:
            return minor_chords

    def reset(self):
        """Reset detector state."""
        with self._lock:
            self._note_history.clear()
            self._chord_history.clear()
            self._chroma = np.zeros(12)
            self._current_scale = None
            self._last_update = 0.0

    def get_status(self) -> Dict[str, Any]:
        """Get detector status."""
        with self._lock:
            return {
                "current_scale": self._current_scale.full_name if self._current_scale else None,
                "confidence": self._current_scale.confidence if self._current_scale else 0.0,
                "fit_score": self._current_scale.fit_score if self._current_scale else 0.0,
                "note_history_size": len(self._note_history),
                "chord_history_size": len(self._chord_history),
                "detection_count": self._detection_count,
            }


# Global scale detector instance
_default_scale_detector: Optional[ScaleDetector] = None


def get_scale_detector() -> ScaleDetector:
    """Get the default scale detector instance."""
    global _default_scale_detector
    if _default_scale_detector is None:
        _default_scale_detector = ScaleDetector()
    return _default_scale_detector
