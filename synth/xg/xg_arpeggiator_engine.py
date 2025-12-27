"""
Yamaha Motif Arpeggiator Engine

Core arpeggiator processing engine implementing Yamaha Motif series
arpeggiator functionality with chord detection, pattern generation,
and real-time control.

Copyright (c) 2025
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
import threading
import time
import math


class ArpeggiatorPattern:
    """
    Individual arpeggiator pattern definition.

    Contains note sequence, timing, velocity, and metadata for a single
    arpeggio pattern.
    """

    def __init__(self, pattern_id: int, name: str, category: str):
        self.pattern_id = pattern_id
        self.name = name
        self.category = category

        # Pattern data
        self.notes: List[Dict[str, Any]] = []  # Note sequence with timing/velocity
        self.length_beats = 1.0  # Pattern length in beats
        self.chord_types: List[str] = []  # Compatible chord types
        self.octave_range = 1  # Default octave range

        # Timing parameters
        self.gate_time = 0.8  # Note duration (0.0-1.0)
        self.swing_amount = 0.0  # Swing timing variation

        # Velocity parameters
        self.velocity_mode = 0  # 0=Original, 1=Fixed, 2=Accent pattern
        self.fixed_velocity = 100
        self.accent_pattern: List[float] = []  # Velocity multipliers

    def add_note(self, step: float, note_offset: int, velocity_mult: float = 1.0):
        """Add a note to the pattern."""
        self.notes.append({
            'step': step,  # Position within pattern (0.0-1.0)
            'note_offset': note_offset,  # Note offset from root
            'velocity_mult': velocity_mult  # Velocity multiplier
        })

    def get_notes_for_chord(self, root_note: int, chord_notes: List[int],
                           octave_range: int = 1) -> List[Dict[str, Any]]:
        """
        Generate note sequence for a specific chord.

        Args:
            root_note: Root note of the chord
            chord_notes: All notes in the chord
            octave_range: Number of octaves to arpeggiate

        Returns:
            List of note events with timing and velocity
        """
        arpeggio_notes = []
        octave_span = octave_range * 12

        for octave_offset in range(octave_range):
            octave_root = root_note + (octave_offset * 12)

            for i, pattern_note in enumerate(self.notes):
                # Calculate actual note
                if pattern_note['note_offset'] == 0:
                    # Root note
                    actual_note = octave_root
                else:
                    # Find closest chord note to the pattern offset
                    target_note = octave_root + pattern_note['note_offset']
                    # Find the closest note in the chord
                    actual_note = min(chord_notes,
                                    key=lambda x: abs(x - target_note))

                # Calculate velocity
                if self.velocity_mode == 0:  # Original
                    velocity = 100  # Will be scaled by input velocity
                elif self.velocity_mode == 1:  # Fixed
                    velocity = self.fixed_velocity
                else:  # Accent pattern
                    accent_index = i % len(self.accent_pattern)
                    velocity = int(self.fixed_velocity * self.accent_pattern[accent_index])

                arpeggio_notes.append({
                    'note': actual_note,
                    'velocity': velocity,
                    'step': pattern_note['step'] + (octave_offset * self.length_beats),
                    'gate_time': self.gate_time,
                    'original_velocity_mult': pattern_note['velocity_mult']
                })

        return arpeggio_notes


class ChordDetector:
    """
    Intelligent chord detection and analysis engine.

    Analyzes incoming notes to detect chord types and provide
    arpeggiator-compatible note sets.
    """

    # Chord type definitions (intervals from root)
    CHORD_TYPES = {
        'major': [0, 4, 7],
        'minor': [0, 3, 7],
        'dim': [0, 3, 6],
        'aug': [0, 4, 8],
        'sus4': [0, 5, 7],
        'sus2': [0, 2, 7],
        '7': [0, 4, 7, 10],
        'maj7': [0, 4, 7, 11],
        'm7': [0, 3, 7, 10],
        'dim7': [0, 3, 6, 9],
        'm7b5': [0, 3, 6, 10],
        '7sus4': [0, 5, 7, 10],
        '6': [0, 4, 7, 9],
        'm6': [0, 3, 7, 9],
        '9': [0, 4, 7, 10, 14],
        'm9': [0, 3, 7, 10, 14],
        '11': [0, 4, 7, 10, 14, 17],
        '13': [0, 4, 7, 10, 14, 21],
    }

    def __init__(self):
        self.active_notes: Dict[int, int] = {}  # note -> velocity
        self.detected_chord: Optional[Dict[str, Any]] = None

    def note_on(self, note: int, velocity: int):
        """Register a note-on event."""
        self.active_notes[note] = velocity
        self._update_chord_detection()

    def note_off(self, note: int):
        """Register a note-off event."""
        if note in self.active_notes:
            del self.active_notes[note]
            self._update_chord_detection()

    def _update_chord_detection(self):
        """Update chord detection based on active notes."""
        if not self.active_notes:
            self.detected_chord = None
            return

        notes = sorted(self.active_notes.keys())
        root_note = notes[0]

        # Normalize notes to root
        normalized_notes = [(n - root_note) % 12 for n in notes]

        # Find best chord match
        best_match = None
        best_score = 0

        for chord_name, chord_intervals in self.CHORD_TYPES.items():
            # Calculate match score
            matching_notes = sum(1 for interval in chord_intervals
                               if interval % 12 in normalized_notes)
            chord_coverage = matching_notes / len(chord_intervals)
            note_coverage = matching_notes / len(normalized_notes)

            score = (chord_coverage + note_coverage) / 2

            if score > best_score:
                best_score = score
                best_match = chord_name

        if best_match and best_score > 0.6:  # 60% match threshold
            self.detected_chord = {
                'root': root_note,
                'type': best_match,
                'notes': notes.copy(),
                'confidence': best_score
            }
        else:
            # Fallback to detected notes as custom chord
            self.detected_chord = {
                'root': root_note,
                'type': 'custom',
                'notes': notes.copy(),
                'confidence': 0.5
            }

    def get_current_chord(self) -> Optional[Dict[str, Any]]:
        """Get currently detected chord."""
        return self.detected_chord.copy() if self.detected_chord else None


class ArpeggiatorZone:
    """
    Arpeggiator zone configuration for key range-specific settings.

    Allows different arpeggiator settings for different key ranges
    within the same channel.
    """

    def __init__(self, lower_note: int = 0, upper_note: int = 127):
        self.lower_note = lower_note
        self.upper_note = upper_note
        self.enabled = False

        # Zone-specific parameters
        self.pattern: Optional[ArpeggiatorPattern] = None
        self.octave_range = 1
        self.gate_time = 0.8
        self.swing_amount = 0.0
        self.velocity_mode = 0
        self.fixed_velocity = 100

    def is_note_in_zone(self, note: int) -> bool:
        """Check if a note falls within this zone."""
        return self.lower_note <= note <= self.upper_note

    def get_zone_settings(self) -> Dict[str, Any]:
        """Get zone-specific settings."""
        return {
            'enabled': self.enabled,
            'pattern': self.pattern.pattern_id if self.pattern else None,
            'octave_range': self.octave_range,
            'gate_time': self.gate_time,
            'swing_amount': self.swing_amount,
            'velocity_mode': self.velocity_mode,
            'fixed_velocity': self.fixed_velocity,
            'note_range': (self.lower_note, self.upper_note)
        }


class ArpeggiatorInstance:
    """
    Individual arpeggiator instance for a single channel/part.

    Manages pattern playback, timing, and note scheduling for one arpeggiator.
    Enhanced with zone support for key range-specific arpeggiation.
    """

    def __init__(self, channel: int, arpeggiator_engine):
        self.channel = channel
        self.engine = arpeggiator_engine

        # State
        self.enabled = False
        self.hold_mode = False
        self.current_pattern: Optional[ArpeggiatorPattern] = None

        # Parameters
        self.octave_range = 1
        self.gate_time = 0.8
        self.swing_amount = 0.0
        self.velocity_mode = 0
        self.fixed_velocity = 100

        # Timing
        self.bpm = 120.0
        self.current_step = 0.0
        self.last_note_time = 0.0

        # Active notes and chord detection
        self.chord_detector = ChordDetector()
        self.active_arpeggio_notes: List[Dict[str, Any]] = []
        self.note_cache: Dict[int, Dict[str, Any]] = {}  # Cache for active notes

        # Zone support
        self.zones_enabled = False
        self.zones: List[ArpeggiatorZone] = []
        self._initialize_zones()

        # Performance optimizations
        self.pattern_cache: Dict[int, List[Dict[str, Any]]] = {}  # Cache generated patterns
        self.last_chord_hash = None  # For chord change detection
        self.velocity_scale_cache: Dict[int, int] = {}  # Cache velocity scaling

        # Callbacks
        self.note_on_callback: Optional[Callable] = None
        self.note_off_callback: Optional[Callable] = None

    def _initialize_zones(self):
        """Initialize default zones (can be customized)."""
        # Default: single zone covering full range
        default_zone = ArpeggiatorZone(0, 127)
        self.zones = [default_zone]

    def set_zone(self, zone_index: int, lower_note: int, upper_note: int,
                pattern_id: Optional[int] = None, **zone_params):
        """Configure an arpeggiator zone."""
        if 0 <= zone_index < len(self.zones):
            zone = self.zones[zone_index]
            zone.lower_note = max(0, min(127, lower_note))
            zone.upper_note = max(0, min(127, upper_note))
            zone.enabled = True

            # Set pattern for zone
            if pattern_id is not None and pattern_id in self.engine.patterns:
                zone.pattern = self.engine.patterns[pattern_id]

            # Set zone-specific parameters
            for param, value in zone_params.items():
                if hasattr(zone, param):
                    setattr(zone, param, value)

    def enable_zones(self, enabled: bool = True):
        """Enable or disable zone functionality."""
        self.zones_enabled = enabled

    def get_active_zone_for_note(self, note: int) -> Optional[ArpeggiatorZone]:
        """Get the active zone for a given note."""
        if not self.zones_enabled:
            return self.zones[0] if self.zones else None

        # Find the first enabled zone that contains this note
        for zone in self.zones:
            if zone.enabled and zone.is_note_in_zone(note):
                return zone

        return None

    def set_pattern(self, pattern: ArpeggiatorPattern):
        """Set the current arpeggio pattern."""
        self.current_pattern = pattern

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        self.chord_detector.note_on(note, velocity)

        if not self.enabled or not self.current_pattern:
            # Arpeggiator is inactive - pass note through to normal synthesis
            # This ensures notes aren't dropped when arpeggiator is disabled
            if self.note_on_callback:
                self.note_on_callback(self.channel, note, velocity)
            return

        # Generate arpeggio notes
        self._generate_arpeggio_notes()

        # Start arpeggio playback if not holding
        if not self.hold_mode:
            self._start_arpeggio()

    def note_off(self, note: int):
        """Handle note-off event."""
        self.chord_detector.note_off(note)

        if not self.hold_mode and not self.chord_detector.active_notes:
            # Stop arpeggio when all notes released
            self._stop_arpeggio()

    def _generate_arpeggio_notes(self):
        """Generate the arpeggio note sequence."""
        chord = self.chord_detector.get_current_chord()
        if not chord or not self.current_pattern:
            return

        # Update pattern parameters
        self.current_pattern.velocity_mode = self.velocity_mode
        self.current_pattern.fixed_velocity = self.fixed_velocity
        self.current_pattern.gate_time = self.gate_time

        # Generate notes for the chord
        self.active_arpeggio_notes = self.current_pattern.get_notes_for_chord(
            chord['root'], chord['notes'], self.octave_range
        )

    def _start_arpeggio(self):
        """Start arpeggio playback."""
        if not self.active_arpeggio_notes:
            return

        # Schedule first note immediately
        self._play_next_arpeggio_note()

    def _stop_arpeggio(self):
        """Stop arpeggio playback."""
        # Send note-offs for any active arpeggio notes
        for arpeggio_note in self.active_arpeggio_notes:
            if arpeggio_note.get('active', False):
                if self.note_off_callback:
                    self.note_off_callback(self.channel, arpeggio_note['note'])

        self.active_arpeggio_notes.clear()

    def _play_next_arpeggio_note(self):
        """Play the next note in the arpeggio sequence."""
        if not self.active_arpeggio_notes or not self.enabled:
            return

        # Find next note to play
        current_time = time.time()
        step_duration = 60.0 / self.bpm / 4.0  # 16th note duration

        for arpeggio_note in self.active_arpeggio_notes:
            note_time = self.last_note_time + (arpeggio_note['step'] * step_duration)

            if note_time <= current_time:
                # Play this note
                velocity = arpeggio_note['velocity']
                if self.note_on_callback:
                    self.note_on_callback(self.channel, arpeggio_note['note'], velocity)

                arpeggio_note['active'] = True

                # Schedule note-off
                gate_duration = arpeggio_note['gate_time'] * step_duration
                # Note: In real implementation, this would be scheduled properly

        self.last_note_time = current_time

    def process_timing(self, current_time: float):
        """Process timing for arpeggio playback."""
        if not self.enabled or not self.active_arpeggio_notes:
            return

        # This would be called regularly to advance arpeggio timing
        # For now, simplified implementation
        pass


class YamahaArpeggiatorEngine:
    """
    Yamaha Motif Arpeggiator Engine

    Main arpeggiator processing engine implementing Yamaha Motif series
    arpeggiator functionality with 16 independent arpeggiators.
    """

    def __init__(self):
        self.lock = threading.RLock()

        # 16 arpeggiator instances (one per MIDI channel)
        self.arpeggiators = [ArpeggiatorInstance(i, self) for i in range(16)]

        # Pattern library
        self.patterns: Dict[int, ArpeggiatorPattern] = {}
        self._initialize_builtin_patterns()

        # Global settings
        self.master_bpm = 120.0
        self.tempo_sync = True

        # Callbacks for note events
        self.note_on_callback: Optional[Callable] = None
        self.note_off_callback: Optional[Callable] = None

        print("🎹 Yamaha Arpeggiator Engine: Initialized")

    def _initialize_builtin_patterns(self):
        """Initialize comprehensive built-in arpeggio patterns."""
        pattern_id = 0

        # ===== BASIC PATTERNS =====
        # Up pattern (0)
        pattern = ArpeggiatorPattern(pattern_id, "Up", "Basic")
        pattern.add_note(0.0, 0)    # Root
        pattern.add_note(0.25, 4)   # Third
        pattern.add_note(0.5, 7)    # Fifth
        pattern.add_note(0.75, 12)  # Octave
        pattern.chord_types = ['major', 'minor', 'dim', 'aug', 'sus4', 'sus2', '7', 'm7', 'maj7', 'dim7', 'm7b5', '7sus4', '6', 'm6', '9', 'm9', '11', '13']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Down pattern (1)
        pattern = ArpeggiatorPattern(pattern_id, "Down", "Basic")
        pattern.add_note(0.0, 12)   # Octave
        pattern.add_note(0.25, 7)   # Fifth
        pattern.add_note(0.5, 4)    # Third
        pattern.add_note(0.75, 0)   # Root
        pattern.chord_types = ['major', 'minor', 'dim', 'aug', 'sus4', 'sus2', '7', 'm7', 'maj7', 'dim7', 'm7b5', '7sus4', '6', 'm6', '9', 'm9', '11', '13']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Up-Down pattern (2)
        pattern = ArpeggiatorPattern(pattern_id, "Up-Down", "Basic")
        pattern.add_note(0.0, 0)    # Root
        pattern.add_note(0.125, 4)  # Third
        pattern.add_note(0.25, 7)   # Fifth
        pattern.add_note(0.375, 12) # Octave
        pattern.add_note(0.5, 7)    # Fifth (down)
        pattern.add_note(0.625, 4)  # Third
        pattern.add_note(0.75, 0)   # Root
        pattern.length_beats = 0.5  # Half note for up-down
        pattern.chord_types = ['major', 'minor', 'dim', 'aug', 'sus4', 'sus2', '7', 'm7', 'maj7', 'dim7', 'm7b5', '7sus4', '6', 'm6', '9', 'm9', '11', '13']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== SEVENTH CHORD PATTERNS =====
        # Dominant 7th Up (3)
        pattern = ArpeggiatorPattern(pattern_id, "7th Up", "Seventh")
        pattern.add_note(0.0, 0)    # Root
        pattern.add_note(0.2, 4)    # Third
        pattern.add_note(0.4, 7)    # Fifth
        pattern.add_note(0.6, 10)   # Seventh
        pattern.add_note(0.8, 12)   # Octave
        pattern.chord_types = ['7', 'm7', 'dim7', 'm7b5', '7sus4', '9', 'm9', '11', '13']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Major 7th Arpeggio (4)
        pattern = ArpeggiatorPattern(pattern_id, "Maj7 Up", "Seventh")
        pattern.add_note(0.0, 0)    # Root
        pattern.add_note(0.2, 4)    # Third
        pattern.add_note(0.4, 7)    # Fifth
        pattern.add_note(0.6, 11)   # Major Seventh
        pattern.add_note(0.8, 12)   # Octave
        pattern.chord_types = ['maj7', '7', '6']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Minor 7th Down (5)
        pattern = ArpeggiatorPattern(pattern_id, "m7 Down", "Seventh")
        pattern.add_note(0.0, 12)   # Octave
        pattern.add_note(0.2, 10)   # Seventh
        pattern.add_note(0.4, 7)    # Fifth
        pattern.add_note(0.6, 3)    # Third
        pattern.add_note(0.8, 0)    # Root
        pattern.chord_types = ['m7', 'm6', 'm9', 'dim7', 'm7b5']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== EXTENDED CHORD PATTERNS =====
        # 9th Chord Arpeggio (6)
        pattern = ArpeggiatorPattern(pattern_id, "9th Up", "Extended")
        pattern.add_note(0.0, 0)    # Root
        pattern.add_note(0.166, 4)  # Third
        pattern.add_note(0.333, 7)  # Fifth
        pattern.add_note(0.5, 10)   # Seventh
        pattern.add_note(0.666, 14) # Ninth
        pattern.add_note(0.833, 12) # Octave
        pattern.chord_types = ['9', 'm9', '7', 'm7']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # 11th Chord Pattern (7)
        pattern = ArpeggiatorPattern(pattern_id, "11th Up", "Extended")
        pattern.add_note(0.0, 0)     # Root
        pattern.add_note(0.142, 4)   # Third
        pattern.add_note(0.285, 7)   # Fifth
        pattern.add_note(0.428, 10)  # Seventh
        pattern.add_note(0.571, 14)  # Ninth
        pattern.add_note(0.714, 17)  # Eleventh
        pattern.add_note(0.857, 12)  # Octave
        pattern.chord_types = ['11', '9', '7']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== RHYTHMIC PATTERNS =====
        # Funk Pattern (8)
        pattern = ArpeggiatorPattern(pattern_id, "Funk", "Rhythmic")
        pattern.add_note(0.0, 0, 1.0)      # Root (accent)
        pattern.add_note(0.25, 7, 0.7)     # Fifth
        pattern.add_note(0.5, 4, 0.7)      # Third
        pattern.add_note(0.75, 10, 0.5)    # Seventh (quiet)
        pattern.chord_types = ['7', 'm7', '9']
        pattern.velocity_mode = 2  # Accent pattern
        pattern.accent_pattern = [1.0, 0.7, 0.7, 0.5]  # Accent velocities
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Jazz Pattern (9)
        pattern = ArpeggiatorPattern(pattern_id, "Jazz", "Rhythmic")
        pattern.add_note(0.0, 0, 1.0)      # Root (accent)
        pattern.add_note(0.166, 4, 0.8)    # Third
        pattern.add_note(0.333, 7, 0.6)    # Fifth
        pattern.add_note(0.5, 11, 0.9)     # Major Seventh (accent)
        pattern.add_note(0.666, 4, 0.5)    # Third (quiet)
        pattern.add_note(0.833, 0, 0.7)    # Root (back to chord)
        pattern.chord_types = ['maj7', '7', '6']
        pattern.velocity_mode = 2  # Accent pattern
        pattern.accent_pattern = [1.0, 0.8, 0.6, 0.9, 0.5, 0.7]  # Jazz accents
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== WORLD MUSIC PATTERNS =====
        # Latin Pattern (10)
        pattern = ArpeggiatorPattern(pattern_id, "Latin", "World")
        pattern.add_note(0.0, 0, 1.0)      # Root
        pattern.add_note(0.187, 7, 0.8)    # Fifth (off-beat)
        pattern.add_note(0.375, 4, 0.6)    # Third
        pattern.add_note(0.562, 10, 0.9)   # Seventh (accent)
        pattern.add_note(0.75, 0, 0.7)     # Root
        pattern.chord_types = ['major', 'minor', '7', 'm7']
        pattern.swing_amount = 0.3  # Latin swing
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== SPECIAL EFFECTS =====
        # Trill Pattern (11)
        pattern = ArpeggiatorPattern(pattern_id, "Trill", "Special")
        # Fast alternation between root and third
        for i in range(16):  # 16 steps for fast trill
            step = i / 16.0
            note_offset = 0 if i % 2 == 0 else 4
            velocity_mult = 1.0 if i % 4 == 0 else 0.8  # Accents every 4th note
            pattern.add_note(step, note_offset, velocity_mult)
        pattern.chord_types = ['major', 'minor', '7', 'm7']
        pattern.length_beats = 0.25  # Fast pattern
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Glissando Pattern (12)
        pattern = ArpeggiatorPattern(pattern_id, "Glissando", "Special")
        # Chromatic run up to octave
        for i in range(13):  # Root to octave (13 semitones)
            step = i / 12.0
            pattern.add_note(step, i, 0.8)
        pattern.chord_types = ['major', 'minor']  # Any chord
        pattern.length_beats = 0.5
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== INVERSION PATTERNS =====
        # First Inversion (13)
        pattern = ArpeggiatorPattern(pattern_id, "1st Inv Up", "Inversions")
        pattern.add_note(0.0, 4)    # Third (now bass)
        pattern.add_note(0.25, 7)   # Fifth
        pattern.add_note(0.5, 12)   # Octave
        pattern.add_note(0.75, 16)  # Third + octave
        pattern.chord_types = ['major', 'minor', '7', 'm7']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Second Inversion (14)
        pattern = ArpeggiatorPattern(pattern_id, "2nd Inv Up", "Inversions")
        pattern.add_note(0.0, 7)    # Fifth (now bass)
        pattern.add_note(0.25, 12)  # Octave
        pattern.add_note(0.5, 16)   # Third + octave
        pattern.add_note(0.75, 19)  # Fifth + octave
        pattern.chord_types = ['major', 'minor', '7', 'm7']
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # ===== DRUM PATTERNS =====
        # Basic Rock Beat (15)
        pattern = ArpeggiatorPattern(pattern_id, "Rock Beat", "Drum")
        # Simple kick/snare pattern mapped to chord notes
        pattern.add_note(0.0, 0, 1.0)    # Root (kick)
        pattern.add_note(0.25, 7, 0.8)   # Fifth (snare)
        pattern.add_note(0.5, 0, 0.9)    # Root (kick)
        pattern.add_note(0.75, 7, 0.7)   # Fifth (snare)
        pattern.chord_types = ['major', 'minor', '7', 'm7']
        pattern.velocity_mode = 2  # Accent pattern
        pattern.accent_pattern = [1.0, 0.8, 0.9, 0.7]  # Rock dynamics
        self.patterns[pattern_id] = pattern
        pattern_id += 1

        # Get chord types from ChordDetector class
        chord_types = ChordDetector().CHORD_TYPES

        print(f"🎹 Arpeggiator: Loaded {len(self.patterns)} comprehensive built-in patterns")
        print(f"   Categories: Basic, Seventh, Extended, Rhythmic, World, Special, Inversions, Drum")
        print(f"   Chord Types: {len(chord_types)} supported ({', '.join(list(chord_types.keys())[:5])}...)")

    def get_arpeggiator(self, channel: int) -> Optional[ArpeggiatorInstance]:
        """Get arpeggiator instance for a channel."""
        with self.lock:
            if 0 <= channel < 16:
                return self.arpeggiators[channel]
        return None

    def set_pattern(self, channel: int, pattern_id: int) -> bool:
        """Set arpeggiator pattern for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator and pattern_id in self.patterns:
                arpeggiator.set_pattern(self.patterns[pattern_id])
                return True
        return False

    def enable_arpeggiator(self, channel: int, enabled: bool) -> bool:
        """Enable/disable arpeggiator for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.enabled = enabled
                if not enabled:
                    arpeggiator._stop_arpeggio()
                return True
        return False

    def set_arpeggiator_parameter(self, channel: int, param: str, value: Any) -> bool:
        """Set arpeggiator parameter for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                if param == 'hold_mode':
                    arpeggiator.hold_mode = bool(value)
                elif param == 'octave_range':
                    arpeggiator.octave_range = max(1, min(4, int(value)))
                elif param == 'gate_time':
                    arpeggiator.gate_time = max(0.1, min(1.0, float(value)))
                elif param == 'swing_amount':
                    arpeggiator.swing_amount = max(0.0, min(1.0, float(value)))
                elif param == 'velocity_mode':
                    arpeggiator.velocity_mode = max(0, min(2, int(value)))
                elif param == 'fixed_velocity':
                    arpeggiator.fixed_velocity = max(1, min(127, int(value)))
                elif param == 'bpm':
                    arpeggiator.bpm = max(60, min(200, float(value)))
                else:
                    return False
                return True
        return False

    def process_note_on(self, channel: int, note: int, velocity: int):
        """Process note-on event through arpeggiator."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.note_on(note, velocity)
            else:
                # Pass through to original callback
                if self.note_on_callback:
                    self.note_on_callback(channel, note, velocity)

    def process_note_off(self, channel: int, note: int):
        """Process note-off event through arpeggiator."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.note_off(note)
            else:
                # Pass through to original callback
                if self.note_off_callback:
                    self.note_off_callback(channel, note)

    def get_pattern_list(self) -> List[Dict[str, Any]]:
        """Get list of available patterns."""
        with self.lock:
            return [{
                'id': pattern.pattern_id,
                'name': pattern.name,
                'category': pattern.category,
                'chord_types': pattern.chord_types.copy()
            } for pattern in self.patterns.values()]

    def get_arpeggiator_status(self, channel: int) -> Optional[Dict[str, Any]]:
        """Get status of arpeggiator for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                return {
                    'enabled': arpeggiator.enabled,
                    'hold_mode': arpeggiator.hold_mode,
                    'current_pattern': arpeggiator.current_pattern.pattern_id if arpeggiator.current_pattern else None,
                    'octave_range': arpeggiator.octave_range,
                    'gate_time': arpeggiator.gate_time,
                    'swing_amount': arpeggiator.swing_amount,
                    'velocity_mode': arpeggiator.velocity_mode,
                    'fixed_velocity': arpeggiator.fixed_velocity,
                    'bpm': arpeggiator.bpm,
                    'active_notes': len(arpeggiator.active_arpeggio_notes),
                    'current_chord': arpeggiator.chord_detector.get_current_chord()
                }
        return None

    def set_arpeggiator_zone(self, channel: int, zone_index: int, lower_note: int, upper_note: int,
                           pattern_id: Optional[int] = None, **zone_params) -> bool:
        """Configure an arpeggiator zone for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.set_zone(zone_index, lower_note, upper_note, pattern_id, **zone_params)
                return True
        return False

    def enable_arpeggiator_zones(self, channel: int, enabled: bool = True) -> bool:
        """Enable or disable zone functionality for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                arpeggiator.enable_zones(enabled)
                return True
        return False

    def get_arpeggiator_zones(self, channel: int) -> Optional[List[Dict[str, Any]]]:
        """Get zone configuration for a channel."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(channel)
            if arpeggiator:
                return [zone.get_zone_settings() for zone in arpeggiator.zones]
        return None

    def reset_all_arpeggiators(self):
        """Reset all arpeggiators to default state."""
        with self.lock:
            for arpeggiator in self.arpeggiators:
                arpeggiator.enabled = False
                arpeggiator.hold_mode = False
                arpeggiator.zones_enabled = False
                arpeggiator._stop_arpeggio()

    def __str__(self) -> str:
        """String representation."""
        return f"YamahaArpeggiatorEngine(channels=16, patterns={len(self.patterns)})"

    def __repr__(self) -> str:
        return self.__str__()
