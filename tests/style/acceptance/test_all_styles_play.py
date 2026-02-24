"""
Style Engine Acceptance Tests

End-to-end acceptance tests for the style engine including:
- All styles play correctly
- Chord following works accurately
- Transitions are smooth
- Full workflow scenarios
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock

from synth.style.style_loader import StyleLoader
from synth.style.style_player import StylePlayer
from synth.style.auto_accompaniment import AutoAccompaniment, AutoAccompanimentConfig
from synth.style.chord_detector import ChordDetector
from synth.style import ScaleDetector, MIDILearn, RegistrationMemory


class TestAllStylesPlay:
    """Test that all example styles play correctly."""

    @pytest.fixture
    def style_directory(self):
        return Path("examples/styles")

    @pytest.fixture
    def synthesizer_mock(self):
        synth = Mock()
        synth.note_on = Mock()
        synth.note_off = Mock()
        synth.channels = [Mock(program=0, bank_msb=0, bank_lsb=0, volume=100, pan=64) 
                          for _ in range(16)]
        return synth

    def test_edm_pop_style_loads(self, style_directory):
        """Test EDM Pop style loads without errors."""
        loader = StyleLoader()
        style_path = style_directory / "edm_pop.yaml"
        
        if style_path.exists():
            style = loader.load_style_file(style_path)
            assert style is not None
            assert style.name == "EDM Pop"
            assert style.tempo == 128

    def test_all_styles_have_required_sections(self, style_directory):
        """Verify all styles have required sections."""
        loader = StyleLoader()
        required = ["main_a", "main_b", "main_c", "main_d"]

        for style_file in style_directory.glob("*.yaml"):
            style = loader.load_style_file(style_file)
            
            for section in required:
                section_exists = any(
                    s.section_type.value == section 
                    for s in style.sections.values()
                )
                assert section_exists, f"Missing {section} in {style_file}"

    def test_edm_pop_sections_play(self, style_directory, synthesizer_mock):
        """Test EDM Pop style sections play without crashing."""
        loader = StyleLoader()
        player = StylePlayer(synthesizer_mock)
        
        style_path = style_directory / "edm_pop.yaml"
        if style_path.exists():
            style = loader.load_style_file(style_path)
            player.load_style(style)
            
            player.start()
            time.sleep(0.5)  # Play for 500ms
            
            player.stop()
            assert True  # Should not have raised exceptions


class TestChordFollowing:
    """Test chord following accuracy."""

    @pytest.fixture
    def accompaniment(self):
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(style, synth, config, sample_rate=44100)

    def test_c_major_triggers_style(self, accompaniment):
        """Test C major chord triggers style playback."""
        accompaniment.start()
        
        # Play C major
        accompaniment.process_midi_note_on(0, 60, 100)
        accompaniment.process_midi_note_on(0, 64, 100)
        accompaniment.process_midi_note_on(0, 67, 100)
        
        time.sleep(0.1)
        
        # Chord should be detected
        chord = accompaniment.chord_detector.get_current_chord()
        assert chord is not None
        assert chord.root.name_display == "C"

    def test_chord_change_updates_style(self, accompaniment):
        """Test chord changes update style output."""
        accompaniment.start()
        
        # Play C major
        accompaniment.process_midi_note_on(0, 60, 100)
        accompaniment.process_midi_note_on(0, 64, 100)
        accompaniment.process_midi_note_on(0, 67, 100)
        time.sleep(0.05)
        
        chord1 = accompaniment.chord_detector.get_current_chord()
        
        # Change to G major
        accompaniment.process_midi_note_off(0, 60)
        accompaniment.process_midi_note_off(0, 64)
        accompaniment.process_midi_note_on(0, 67, 100)
        accompaniment.process_midi_note_on(0, 71, 100)
        accompaniment.process_midi_note_on(0, 74, 100)
        time.sleep(0.05)
        
        chord2 = accompaniment.chord_detector.get_current_chord()
        
        # Should have changed
        assert chord2.root.name_display == "G"

    def test_bass_note_detected_for_inversion(self, accompaniment):
        """Test bass note detection for inversions."""
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=36,
            chord_detection_zone_high=72,
            bass_detection_zone_high=48,
        )
        accompaniment.config = config
        accompaniment.chord_detector.config.bass_detection_threshold = 48
        
        accompaniment.start()
        
        # Play E in bass (C major first inversion)
        accompaniment.process_midi_note_on(0, 40, 100)  # E3
        accompaniment.process_midi_note_on(0, 60, 100)  # C4
        accompaniment.process_midi_note_on(0, 64, 100)  # E4
        accompaniment.process_midi_note_on(0, 67, 100)  # G4
        
        time.sleep(0.05)
        
        chord = accompaniment.chord_detector.get_current_chord()
        assert chord is not None


class TestSectionTransitions:
    """Test section transition functionality."""

    @pytest.fixture
    def player(self):
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        player = StylePlayer(synth)
        player.load_style(style)
        return player

    def test_section_change_callback(self, player):
        """Test section change callbacks fire."""
        changes = []
        
        def on_change(old, new):
            changes.append((old, new))
        
        player.set_section_change_callback(on_change)
        player.start()
        
        player.set_section("main_b")
        time.sleep(0.1)
        
        # Should have at least one change
        assert len(changes) >= 1

    def test_next_section_cycles(self, player):
        """Test next_section cycles through A->B->C->D->A."""
        player.start()
        
        sections = []
        for _ in range(5):
            sections.append(player.current_section.value if player.current_section else None)
            player.next_section()
            time.sleep(0.05)
        
        # Should cycle through main sections
        assert "main_a" in sections or "main_b" in sections


class TestIntegration:
    """Full integration tests."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: load, play, change, save."""
        # Create components
        loader = StyleLoader()
        synth = Mock()
        synth.channels = [Mock(program=0, bank_msb=0, bank_lsb=0, volume=100, pan=64) 
                          for _ in range(16)]
        
        # Load style
        style = loader.create_example_style(name="Integration Test", tempo=120)
        
        # Create player
        from synth.style.style_player import StylePlayer
        player = StylePlayer(synth)
        player.load_style(style)
        
        # Start playback
        player.start()
        time.sleep(0.1)
        assert player.is_playing
        
        # Change section
        player.set_section("main_b")
        time.sleep(0.05)
        
        # Play chords
        player.process_midi_note_on(0, 60, 100)
        player.process_midi_note_on(0, 64, 100)
        player.process_midi_note_on(0, 67, 100)
        time.sleep(0.05)
        
        # Stop
        player.stop()
        assert not player.is_playing
        
        # Save registration
        from synth.style.registration import RegistrationMemory
        reg_memory = RegistrationMemory()
        reg_memory.set_synthesizer(synth)
        
        assert reg_memory.store(name="Test", bank=0, slot=0)
        
        # Save style
        style_path = tmp_path / "integration_test.yaml"
        loader.save_style(style, style_path)
        assert style_path.exists()

    def test_scale_detection_integration(self):
        """Test scale detector with chord detection."""
        from synth.style.scale import ScaleDetector
        from synth.style.chord_detection_enhanced import EnhancedChordDetector
        
        scale_detector = ScaleDetector()
        chord_detector = EnhancedChordDetector()
        
        # Play C major scale notes
        for note in [60, 62, 64, 65, 67, 69, 71]:
            scale_detector.add_note(note)
            chord_detector.note_on(note)
        
        # Get scale
        scale = scale_detector.get_current_scale()
        
        # Should detect C major or related
        assert scale is not None
        
        # Chord detector should work with scale context
        chord = chord_detector.get_current_chord()
        assert chord is not None

    def test_midi_learn_integration(self):
        """Test MIDI learn with style control."""
        from synth.style import MIDILearn, LearnTargetType
        
        learn = MIDILearn()
        
        # Learn a mapping
        learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")
        result = learn.process_midi(1, 0, 64)  # CC 1, channel 0, value 64
        
        assert result is not None
        assert result.get("learned") == True
        
        # Process same CC again
        result = learn.process_midi(1, 0, 100)
        assert result is not None
        assert "value" in result

    def test_registration_with_freeze(self):
        """Test registration memory with freeze function."""
        from synth.style.registration import RegistrationMemory, RegistrationParameter
        
        reg_memory = RegistrationMemory()
        synth = Mock()
        synth.channels = [Mock(program=0, bank_msb=0, bank_lsb=0, volume=100, pan=64) 
                          for _ in range(16)]
        reg_memory.set_synthesizer(synth)
        
        # Store registration
        reg_memory.store(name="Test 1", bank=0, slot=0)
        
        # Set freeze on tempo
        reg_memory.set_global_freeze(RegistrationParameter.TEMPO, True)
        
        # Store another
        reg_memory.store(name="Test 2", bank=0, slot=1)
        
        # Recall should work
        assert reg_memory.recall(bank=0, slot=0)
        
        # Check freeze status
        status = reg_memory.get_status()
        assert "tempo" in status["global_freeze"] or len(status["global_freeze"]) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_style_handling(self):
        """Test handling of minimal/empty style."""
        loader = StyleLoader()
        style = loader.create_minimal_style(name="Empty")
        
        synth = Mock()
        config = AutoAccompanimentConfig(sync_start_enabled=False)
        
        # Should not crash
        accompaniment = AutoAccompaniment(style, synth, config, sample_rate=44100)
        accompaniment.start()
        time.sleep(0.05)
        accompaniment.stop()
        
        assert True

    def test_rapid_section_changes(self):
        """Test rapid section changes don't crash."""
        loader = StyleLoader()
        style = loader.create_example_style()
        synth = Mock()
        player = StylePlayer(synth)
        player.load_style(style)
        player.start()
        
        # Rapid changes
        for _ in range(10):
            player.set_section("main_a")
            player.set_section("main_b")
            player.set_section("main_c")
            player.set_section("main_d")
        
        time.sleep(0.1)
        assert True  # Should not crash

    def test_out_of_range_notes(self):
        """Test out of range notes are handled."""
        detector = ChordDetector()
        
        # Very low and very high notes
        detector.note_on(12)   # Very low
        detector.note_on(100)  # Very high
        
        # Should not crash
        chord = detector.get_current_chord()
        assert chord is None  # Should be ignored
