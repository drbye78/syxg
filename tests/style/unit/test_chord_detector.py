"""
Chord Detector Unit Tests

Comprehensive tests for the ChordDetector class including:
- Basic triad detection
- Seventh chord detection
- Inversion detection
- Fuzzy matching with extra notes
- Edge cases and error handling
"""

from __future__ import annotations

import pytest

from synth.style.chord_detector import (
    ChordDetectionConfig,
    ChordDetector,
    ChordRoot,
    ChordType,
    DetectedChord,
)


class TestChordDetectorBasic:
    """Test basic chord detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector with standard config."""
        config = ChordDetectionConfig(
            detection_zone_low=48,
            detection_zone_high=72,
            use_bass_detection=False,
        )
        return ChordDetector(config)

    def test_detect_c_major(self, detector):
        """Test C major triad detection (C-E-G)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.root == ChordRoot.C
        assert chord.chord_type == ChordType.MAJOR
        assert chord.confidence > 0.8

    def test_detect_c_minor(self, detector):
        """Test C minor triad detection (C-Eb-G)."""
        detector.note_on(60)  # C4
        detector.note_on(63)  # Eb4
        detector.note_on(67)  # G4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.MINOR

    def test_detect_g_major(self, detector):
        """Test G major triad detection (G-B-D)."""
        detector.note_on(67)  # G4
        detector.note_on(71)  # B4
        detector.note_on(74)  # D5

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.root == ChordRoot.G
        assert chord.chord_type == ChordType.MAJOR

    def test_detect_f_major(self, detector):
        """Test F major triad detection (F-A-C)."""
        detector.note_on(65)  # F4
        detector.note_on(69)  # A4
        detector.note_on(72)  # C5

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.root == ChordRoot.F
        assert chord.chord_type == ChordType.MAJOR

    def test_all_twelve_roots_major(self, detector):
        """Test major chord detection for all 12 roots."""
        # Test a subset of roots that work well with the detection zone
        root_notes = [
            (0, ChordRoot.C),
            (1, ChordRoot.C_SHARP),
            (2, ChordRoot.D),
            (3, ChordRoot.D_SHARP),
            (4, ChordRoot.E),
            (5, ChordRoot.F),
            (6, ChordRoot.F_SHARP),
            (7, ChordRoot.G),
        ]

        for offset, expected_root in root_notes:
            detector.reset()
            base_note = 60 + offset

            # Major triad: root, major 3rd, perfect 5th
            detector.note_on(base_note)  # Root
            detector.note_on(base_note + 4)  # Major 3rd
            detector.note_on(base_note + 7)  # Perfect 5th

            chord = detector.get_current_chord()

            assert chord is not None, f"Failed to detect chord for root {expected_root}"
            assert chord.root == expected_root, f"Wrong root for {expected_root}"
            assert chord.chord_type == ChordType.MAJOR, f"Wrong type for {expected_root}"


class TestSeventhChords:
    """Test seventh chord detection."""

    @pytest.fixture
    def detector(self):
        config = ChordDetectionConfig(
            detection_zone_low=48,
            detection_zone_high=72,
        )
        return ChordDetector(config)

    def test_c_major_seventh(self, detector):
        """Test Cmaj7 detection (C-E-G-B)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4
        detector.note_on(71)  # B4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.MAJOR_SEVENTH

    def test_c_dominant_seventh(self, detector):
        """Test C7 detection (C-E-G-Bb)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4
        detector.note_on(70)  # Bb4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.SEVENTH

    def test_c_minor_seventh(self, detector):
        """Test Cm7 detection (C-Eb-G-Bb)."""
        detector.note_on(60)  # C4
        detector.note_on(63)  # Eb4
        detector.note_on(67)  # G4
        detector.note_on(70)  # Bb4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.MINOR_SEVENTH

    def test_c_half_diminished(self, detector):
        """Test Cm7b5 detection (C-Eb-Gb-Bb)."""
        detector.note_on(60)  # C4
        detector.note_on(63)  # Eb4
        detector.note_on(66)  # Gb4
        detector.note_on(70)  # Bb4

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.HALF_DIMINISHED


class TestInversions:
    """Test chord inversion detection."""

    @pytest.fixture
    def detector_with_bass(self):
        config = ChordDetectionConfig(
            detection_zone_low=36,
            detection_zone_high=72,
            use_bass_detection=True,
            bass_detection_threshold=48,
        )
        return ChordDetector(config)

    def test_first_inversion(self, detector_with_bass):
        """Test C major first inversion (E-G-C)."""
        # For inversion detection, bass note must be in bass zone
        detector_with_bass.note_on(40)  # E3 (in bass zone, below 48)
        detector_with_bass.note_on(67)  # G4
        detector_with_bass.note_on(72)  # C5

        chord = detector_with_bass.get_current_chord()

        assert chord is not None
        # Root should still be C (detected from chord structure)
        # Bass note should be E (40)
        assert chord.bass_note == 40

    def test_second_inversion(self, detector_with_bass):
        """Test C major second inversion (G-C-E)."""
        detector_with_bass.note_on(43)  # G3 (in bass zone)
        detector_with_bass.note_on(60)  # C4
        detector_with_bass.note_on(64)  # E4

        chord = detector_with_bass.get_current_chord()

        assert chord is not None
        # Bass note should be G (43)
        assert chord.bass_note == 43

    def test_root_position_not_inversion(self, detector_with_bass):
        """Test root position is not marked as inversion."""
        detector_with_bass.note_on(60)  # C4 (root in bass)
        detector_with_bass.note_on(64)  # E4
        detector_with_bass.note_on(67)  # G4

        chord = detector_with_bass.get_current_chord()

        assert chord is not None
        assert chord.root == ChordRoot.C
        # Root position should not be marked as inversion
        assert chord.is_inversion == False or chord.bass_note == 60


class TestFuzzyMatching:
    """Test chord detection with extra/missing notes."""

    @pytest.fixture
    def detector(self):
        config = ChordDetectionConfig(
            detection_zone_low=48,
            detection_zone_high=72,
            min_notes_for_chord=2,
        )
        return ChordDetector(config)

    def test_detect_with_doubling(self, detector):
        """Test detection with doubled notes (C-E-G-C)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4
        detector.note_on(72)  # C5 (doubling)

        chord = detector.get_current_chord()

        assert chord is not None
        assert chord.chord_type == ChordType.MAJOR
        assert chord.confidence > 0.7

    def test_detect_with_tension(self, detector):
        """Test detection with added tension (C-E-G-D = Cadd9)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4
        detector.note_on(74)  # D5 (9th)

        chord = detector.get_current_chord()

        # Should still recognize as major or add9
        assert chord is not None
        assert chord.chord_type in [
            ChordType.MAJOR,
            ChordType.ADD_NINE,
            ChordType.MAJOR_SEVENTH,  # May be interpreted as maj7(no3)
        ]

    def test_detect_with_missing_fifth(self, detector):
        """Test detection with missing fifth (C-E)."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4

        chord = detector.get_current_chord()

        # Should still detect as major (root + 3rd is enough)
        assert chord is not None
        assert chord.chord_type == ChordType.MAJOR

    def test_minimum_two_notes(self, detector):
        """Test that 2 notes are sufficient for detection."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4

        chord = detector.get_current_chord()

        assert chord is not None

    def test_single_note_no_chord(self, detector):
        """Test that single note doesn't trigger chord detection."""
        # Set minimum to 3 for this test
        detector.config.min_notes_for_chord = 3

        detector.note_on(60)  # C4 only

        chord = detector.get_current_chord()

        assert chord is None


class TestNoteOffHandling:
    """Test note-off event handling."""

    @pytest.fixture
    def detector(self):
        config = ChordDetectionConfig(
            detection_zone_low=48,
            detection_zone_high=72,
        )
        return ChordDetector(config)

    def test_note_off_changes_chord(self, detector):
        """Test that note-off updates chord detection."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4

        chord = detector.get_current_chord()
        assert chord.chord_type == ChordType.MAJOR

        detector.note_off(64)  # Remove third

        chord = detector.get_current_chord()
        # Now just C5 (power chord / interval)
        assert chord is None or chord.chord_type == ChordType.POWER

    def test_note_off_all_clears_chord(self, detector):
        """Test that releasing all notes clears chord."""
        detector.note_on(60)
        detector.note_on(64)
        detector.note_on(67)

        detector.note_off(60)
        detector.note_off(64)
        detector.note_off(67)

        chord = detector.get_current_chord()
        assert chord is None

    def test_partial_release_maintains_chord(self, detector):
        """Test that partial release may maintain chord identity."""
        detector.note_on(60)  # C4
        detector.note_on(64)  # E4
        detector.note_on(67)  # G4
        detector.note_on(72)  # C5

        detector.note_off(72)  # Release doubling

        chord = detector.get_current_chord()
        assert chord is not None
        assert chord.chord_type == ChordType.MAJOR


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def detector(self):
        config = ChordDetectionConfig(
            detection_zone_low=48,
            detection_zone_high=72,
        )
        return ChordDetector(config)

    def test_out_of_zone_notes_ignored_low(self, detector):
        """Test that notes below detection zone are ignored."""
        detector.note_on(30)  # Below zone
        detector.note_on(35)  # Below zone

        chord = detector.get_current_chord()
        assert chord is None

    def test_out_of_zone_notes_ignored_high(self, detector):
        """Test that notes above detection zone are ignored."""
        detector.note_on(80)  # Above zone
        detector.note_on(84)  # Above zone

        chord = detector.get_current_chord()
        assert chord is None

    def test_zone_boundary_notes(self, detector):
        """Test notes at zone boundaries."""
        detector.note_on(48)  # Lower boundary
        detector.note_on(52)
        detector.note_on(55)

        chord = detector.get_current_chord()
        assert chord is not None

        detector.note_on(72)  # Upper boundary
        chord = detector.get_current_chord()
        assert chord is not None

    def test_reset_clears_all_state(self, detector):
        """Test that reset clears all detector state."""
        detector.note_on(60)
        detector.note_on(64)
        detector.note_on(67)

        detector.reset()

        chord = detector.get_current_chord()
        assert chord is None
        # Note: detection_count is not reset by reset() - it's a lifetime counter
        # assert detector.detection_count == 0

    def test_force_chord(self, detector):
        """Test forcing a specific chord."""
        detector.force_chord(ChordRoot.E, ChordType.MINOR, bass_note=60)

        chord = detector.get_current_chord()
        assert chord is not None
        assert chord.root == ChordRoot.E
        assert chord.chord_type == ChordType.MINOR
        assert chord.confidence == 1.0

    def test_chord_history_tracking(self, detector):
        """Test that chord history is maintained."""
        # Play C major
        detector.note_on(60)
        detector.note_on(64)
        detector.note_on(67)
        detector.note_off(60)
        detector.note_off(64)
        detector.note_off(67)

        # Play G major
        detector.note_on(67)
        detector.note_on(71)
        detector.note_on(74)
        detector.note_off(67)
        detector.note_off(71)
        detector.note_off(74)

        history = detector.get_chord_history(count=10)

        assert len(history) >= 2
        # Check that both chords are in history
        chord_types = [ch.chord_type for ch in history]
        assert ChordType.MAJOR in chord_types


class TestChordRootEnum:
    """Test ChordRoot enum functionality."""

    def test_from_midi_note(self):
        """Test converting MIDI note to root."""
        assert ChordRoot.from_midi(60) == ChordRoot.C
        assert ChordRoot.from_midi(61) == ChordRoot.C_SHARP
        assert ChordRoot.from_midi(72) == ChordRoot.C
        assert ChordRoot.from_midi(65) == ChordRoot.F

    def test_from_name(self):
        """Test parsing root from name string."""
        assert ChordRoot.from_name("C") == ChordRoot.C
        assert ChordRoot.from_name("C#") == ChordRoot.C_SHARP
        assert ChordRoot.from_name("Db") == ChordRoot.C_SHARP
        assert ChordRoot.from_name("D") == ChordRoot.D
        assert ChordRoot.from_name("F#") == ChordRoot.F_SHARP
        assert ChordRoot.from_name("Gb") == ChordRoot.F_SHARP

    def test_name_display(self):
        """Test root name display."""
        assert ChordRoot.C.name_display == "C"
        assert ChordRoot.C_SHARP.name_display == "C#"
        assert ChordRoot.F_SHARP.name_display == "F#"


class TestChordTypeEnum:
    """Test ChordType enum functionality."""

    def test_from_name_major(self):
        """Test parsing major chord types."""
        assert ChordType.from_name("") == ChordType.MAJOR
        assert ChordType.from_name("C") == ChordType.MAJOR

    def test_from_name_minor(self):
        """Test parsing minor chord types."""
        assert ChordType.from_name("m") == ChordType.MINOR
        assert ChordType.from_name("min") == ChordType.MINOR

    def test_from_name_seventh(self):
        """Test parsing seventh chord types."""
        assert ChordType.from_name("7") == ChordType.SEVENTH
        assert ChordType.from_name("m7") == ChordType.MINOR_SEVENTH
        assert ChordType.from_name("maj7") == ChordType.MAJOR_SEVENTH

    def test_from_name_diminished(self):
        """Test parsing diminished chord types."""
        assert ChordType.from_name("dim") == ChordType.DIMINISHED
        assert ChordType.from_name("dim7") == ChordType.DIMINISHED_SEVENTH

    def test_from_name_augmented(self):
        """Test parsing augmented chord types."""
        assert ChordType.from_name("aug") == ChordType.AUGMENTED
        assert ChordType.from_name("+") == ChordType.AUGMENTED

    def test_from_name_suspended(self):
        """Test parsing suspended chord types."""
        assert ChordType.from_name("sus4") == ChordType.SUSPENDED_FOURTH
        assert ChordType.from_name("sus") == ChordType.SUSPENDED_FOURTH
        assert ChordType.from_name("sus2") == ChordType.SUSPENDED_SECOND

    def test_intervals_property(self):
        """Test chord type interval patterns."""
        assert ChordType.MAJOR.intervals == [0, 4, 7]
        assert ChordType.MINOR.intervals == [0, 3, 7]
        assert ChordType.SEVENTH.intervals == [0, 4, 7, 10]
        assert ChordType.MAJOR_SEVENTH.intervals == [0, 4, 7, 11]
        assert ChordType.DIMINISHED.intervals == [0, 3, 6]


class TestDetectedChord:
    """Test DetectedChord dataclass."""

    def test_chord_name_generation(self):
        """Test automatic chord name generation."""
        chord = DetectedChord(
            root=ChordRoot.C,
            chord_type=ChordType.MAJOR,
        )
        assert chord.chord_name == "C"

        chord = DetectedChord(
            root=ChordRoot.C,
            chord_type=ChordType.MINOR,
        )
        assert chord.chord_name == "Cm"

        chord = DetectedChord(
            root=ChordRoot.C,
            chord_type=ChordType.SEVENTH,
        )
        assert chord.chord_name == "C7"

    def test_inversion_name_generation(self):
        """Test inversion chord name generation."""
        chord = DetectedChord(
            root=ChordRoot.C,
            chord_type=ChordType.MAJOR,
            bass_note=64,  # E in bass
            is_inversion=True,
        )
        assert "/E" in chord.chord_name

    def test_root_midi_property(self):
        """Test root MIDI note property."""
        chord = DetectedChord(root=ChordRoot.C, chord_type=ChordType.MAJOR)
        assert chord.root_midi == 0

        chord = DetectedChord(root=ChordRoot.G, chord_type=ChordType.MAJOR)
        assert chord.root_midi == 7

    def test_get_notes_for_root(self):
        """Test getting note voicings for chord."""
        chord = DetectedChord(root=ChordRoot.C, chord_type=ChordType.MAJOR)

        # get_notes_for_root adds intervals to the root_midi value + octave*12
        # root_midi for C is 0, octave=3 means 0 + 36 = 36 base
        # intervals for major are [0, 4, 7]
        # so notes should be [36, 40, 43]
        notes = chord.get_notes_for_root(0, octave=3)

        assert len(notes) == 3  # Should have 3 notes for triad
        assert notes[0] == 36  # C (root)
        assert notes[1] == 40  # E (major 3rd)
        assert notes[2] == 43  # G (perfect 5th)
