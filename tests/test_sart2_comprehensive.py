"""
S.Art2 Articulation System Comprehensive Tests

Tests for S.Art2 articulation control with actual synthesizer integration:
- NRPN articulation control
- SYSEX articulation messages
- Articulation presets
- Per-channel articulation
- Integration with voice management
"""

from __future__ import annotations

import pytest
import numpy as np


class TestSArt2Comprehensive:
    """Test S.Art2 articulation system with synthesizer integration."""

    @pytest.fixture
    def synthesizer(self):
        """Create a synthesizer instance for testing."""
        from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
        
        synth = ModernXGSynthesizer(
            sample_rate=44100,
            max_channels=16,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=False,
        )
        yield synth
        synth.cleanup()

    @pytest.mark.unit
    def test_sart2_initialization(self, synthesizer):
        """Test S.Art2 system initialization."""
        assert hasattr(synthesizer, 'articulation_manager')
        assert hasattr(synthesizer, 'nrpn_mapper')
        assert hasattr(synthesizer, 'articulation_preset_manager')
        assert hasattr(synthesizer, 'sart2_factory')

    @pytest.mark.unit
    def test_articulation_nrpn_control(self, synthesizer):
        """Test articulation control via NRPN messages."""
        # Test normal articulation (MSB=1, LSB=0)
        synthesizer.process_nrpn(channel=0, msb=1, lsb=0, value=0)
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "normal"

        # Test legato articulation (MSB=1, LSB=1)
        synthesizer.process_nrpn(channel=0, msb=1, lsb=1, value=0)
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "legato"

        # Test staccato articulation (MSB=1, LSB=2)
        synthesizer.process_nrpn(channel=0, msb=1, lsb=2, value=0)
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "staccato"

    @pytest.mark.unit
    def test_articulation_sysex_control(self, synthesizer):
        """Test articulation control via SYSEX messages."""
        # Create SYSEX message for articulation
        sysex_data = bytes([0xF0, 0x43, 0x10, 0x4C, 0x08, 0x00, 0x00, 0x00, 0xF7])
        
        # Process SYSEX
        synthesizer.process_sysex(sysex_data)
        
        # Verify articulation was set
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation in synthesizer.get_available_articulations()

    @pytest.mark.unit
    def test_articulation_presets(self, synthesizer):
        """Test articulation preset loading."""
        # Get preset count
        preset_count = synthesizer.get_articulation_preset_count()
        assert preset_count > 0

        # Get presets by category
        categories = ["strings", "brass", "woodwinds", "percussion"]
        for category in categories:
            presets = synthesizer.get_articulation_presets_by_category(category)
            assert isinstance(presets, list)

    @pytest.mark.unit
    def test_per_channel_articulation(self, synthesizer):
        """Test per-channel articulation isolation."""
        # Set different articulations on different channels
        synthesizer.set_channel_articulation(0, "legato")
        synthesizer.set_channel_articulation(1, "staccato")
        synthesizer.set_channel_articulation(2, "normal")

        # Verify each channel has correct articulation
        assert synthesizer.get_channel_articulation(0) == "legato"
        assert synthesizer.get_channel_articulation(1) == "staccato"
        assert synthesizer.get_channel_articulation(2) == "normal"

    @pytest.mark.unit
    def test_articulation_with_midi(self, synthesizer):
        """Test articulation affects MIDI processing."""
        # Set legato articulation
        synthesizer.set_channel_articulation(0, "legato")

        # Send note-on message
        note_on = bytes([0x90, 60, 100])  # Channel 0, Note 60, Velocity 100
        synthesizer.process_midi_message(note_on)

        # Verify channel has articulation set
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "legato"

        # Send note-off message
        note_off = bytes([0x80, 60, 0])  # Channel 0, Note 60, Velocity 0
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_articulation_parameter_validation(self, synthesizer):
        """Test articulation parameter validation."""
        # Test valid articulation
        synthesizer.set_channel_articulation(0, "normal")
        assert synthesizer.get_channel_articulation(0) == "normal"

        # Test invalid channel (should not crash)
        synthesizer.set_channel_articulation(100, "legato")
        
        # Test invalid articulation name (should not crash)
        synthesizer.set_channel_articulation(0, "invalid_articulation")

    @pytest.mark.unit
    def test_articulation_preset_save_load(self, synthesizer, tmp_path):
        """Test articulation preset save and load."""
        # Save presets to file
        preset_file = tmp_path / "test_presets.json"
        synthesizer.save_articulation_presets(str(preset_file))
        
        # Verify file was created
        assert preset_file.exists()

        # Load presets from file
        loaded_count = synthesizer.load_articulation_presets_from_file(str(preset_file))
        assert loaded_count > 0

    @pytest.mark.unit
    def test_articulation_with_voice_allocation(self, synthesizer):
        """Test articulation affects voice allocation."""
        # Set articulation
        synthesizer.set_channel_articulation(0, "legato")

        # Send multiple notes
        for note in [60, 64, 67]:
            note_on = bytes([0x90, note, 100])
            synthesizer.process_midi_message(note_on)

        # Verify articulation is maintained
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "legato"

        # Send note-offs
        for note in [60, 64, 67]:
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_available_articulations(self, synthesizer):
        """Test getting available articulations."""
        articulations = synthesizer.get_available_articulations()
        
        # Should have common articulations
        assert "normal" in articulations
        assert "legato" in articulations
        assert "staccato" in articulations
        
        # Should have extended articulations
        assert len(articulations) >= 10

    @pytest.mark.unit
    def test_articulation_with_effects(self, synthesizer):
        """Test articulation with effects processing."""
        # Set articulation
        synthesizer.set_channel_articulation(0, "legato")

        # Send note and generate audio
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio block
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)  # Should have some audio

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_articulation_preset_categories(self, synthesizer):
        """Test articulation preset categories."""
        categories = ["strings", "brass", "woodwinds", "percussion", "vocals"]
        
        for category in categories:
            presets = synthesizer.get_articulation_presets_by_category(category)
            assert isinstance(presets, list)

    @pytest.mark.unit
    def test_articulation_with_pitch_bend(self, synthesizer):
        """Test articulation with pitch bend."""
        # Set articulation
        synthesizer.set_channel_articulation(0, "legato")

        # Send pitch bend
        pitch_bend = bytes([0xE0, 0x00, 0x40])  # Center pitch bend
        synthesizer.process_midi_message(pitch_bend)

        # Verify articulation is maintained
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "legato"

    @pytest.mark.unit
    def test_articulation_with_modulation(self, synthesizer):
        """Test articulation with modulation wheel."""
        # Set articulation
        synthesizer.set_channel_articulation(0, "legato")

        # Send modulation
        modulation = bytes([0xB0, 1, 64])  # Modulation wheel
        synthesizer.process_midi_message(modulation)

        # Verify articulation is maintained
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "legato"

    @pytest.mark.unit
    def test_articulation_reset(self, synthesizer):
        """Test articulation reset."""
        # Set articulation
        synthesizer.set_channel_articulation(0, "legato")
        assert synthesizer.get_channel_articulation(0) == "legato"

        # Reset synthesizer
        synthesizer.reset()

        # Verify articulation is reset to normal
        articulation = synthesizer.get_channel_articulation(0)
        assert articulation == "normal"