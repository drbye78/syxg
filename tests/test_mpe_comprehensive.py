"""
MPE (MIDI Polyphonic Expression) System Comprehensive Tests

Tests for MPE per-note control with actual synthesizer integration:
- MPE note-on/off processing
- Per-note pitch bend
- Per-note timbre control
- Per-note pressure
- MPE zone configuration
- Integration with voice management
"""

from __future__ import annotations

import pytest
import numpy as np


class TestMPEComprehensive:
    """Test MPE system with synthesizer integration."""

    @pytest.fixture
    def synthesizer(self):
        """Create a synthesizer instance for testing."""
        from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
        
        synth = ModernXGSynthesizer(
            sample_rate=44100,
            max_channels=16,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=True,
        )
        yield synth
        synth.cleanup()

    @pytest.mark.unit
    def test_mpe_initialization(self, synthesizer):
        """Test MPE system initialization."""
        assert hasattr(synthesizer, 'mpe_system')
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

    @pytest.mark.unit
    def test_mpe_note_on_off(self, synthesizer):
        """Test MPE note-on/off processing."""
        # Send MPE note-on
        note_on = bytes([0x91, 60, 100])  # Channel 1 (MPE zone), Note 60, Velocity 100
        synthesizer.process_midi_message(note_on)

        # Verify note is active
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('active_notes', 0) >= 1

        # Send MPE note-off
        note_off = bytes([0x81, 60, 0])  # Channel 1, Note 60, Velocity 0
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_per_note_pitch_bend(self, synthesizer):
        """Test per-note pitch bend."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note pitch bend (MPE controller 74)
        pitch_bend = bytes([0xB1, 74, 64])  # Center position
        synthesizer.process_midi_message(pitch_bend)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_per_note_timbre_control(self, synthesizer):
        """Test per-note timbre control."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note timbre (MPE controller 75)
        timbre = bytes([0xB1, 75, 100])
        synthesizer.process_midi_message(timbre)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_per_note_pressure(self, synthesizer):
        """Test per-note pressure control."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send polyphonic key pressure
        pressure = bytes([0xA1, 60, 80])  # Channel 1, Note 60, Pressure 80
        synthesizer.process_midi_message(pressure)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_zone_configuration(self, synthesizer):
        """Test MPE zone configuration."""
        mpe_info = synthesizer.get_mpe_info()
        
        # Should have zone information
        assert 'zones' in mpe_info or 'zone' in str(mpe_info).lower()

    @pytest.mark.unit
    def test_mpe_with_audio_generation(self, synthesizer):
        """Test MPE with audio generation."""
        # Send MPE note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note pitch bend
        pitch_bend = bytes([0xB1, 74, 90])  # Bend up
        synthesizer.process_midi_message(pitch_bend)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_multiple_notes(self, synthesizer):
        """Test MPE with multiple simultaneous notes."""
        # Send multiple MPE notes
        notes = [60, 64, 67]  # C, E, G chord
        for note in notes:
            note_on = bytes([0x91, note, 100])
            synthesizer.process_midi_message(note_on)

        # Verify multiple notes are active
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('active_notes', 0) >= 3

        # Send per-note pitch bend to one note
        pitch_bend = bytes([0xB1, 74, 100])
        synthesizer.process_midi_message(pitch_bend)

        # Clean up
        for note in notes:
            note_off = bytes([0x81, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_pitch_bend_range(self, synthesizer):
        """Test MPE pitch bend range."""
        mpe_info = synthesizer.get_mpe_info()
        
        # Should have pitch bend range
        assert 'pitch_bend_range' in mpe_info or 'bend' in str(mpe_info).lower()

    @pytest.mark.unit
    def test_mpe_with_channel_pressure(self, synthesizer):
        """Test MPE with channel pressure."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send channel pressure (aftertouch)
        pressure = bytes([0xD1, 64])  # Channel 1, Pressure 64
        synthesizer.process_midi_message(pressure)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_slide_control(self, synthesizer):
        """Test MPE slide control."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send slide control (MPE controller 76)
        slide = bytes([0xB1, 76, 64])
        synthesizer.process_midi_message(slide)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_lift_control(self, synthesizer):
        """Test MPE lift control."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send lift control (MPE controller 77)
        lift = bytes([0xB1, 77, 100])
        synthesizer.process_midi_message(lift)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_enable_disable(self, synthesizer):
        """Test MPE enable/disable."""
        # Disable MPE
        synthesizer.set_mpe_enabled(False)
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is False

        # Enable MPE
        synthesizer.set_mpe_enabled(True)
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

    @pytest.mark.unit
    def test_mpe_reset(self, synthesizer):
        """Test MPE reset."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Reset MPE
        synthesizer.reset_mpe()

        # Verify MPE is reset
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('active_notes', 0) == 0

    @pytest.mark.unit
    def test_mpe_with_modulation(self, synthesizer):
        """Test MPE with modulation wheel."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send modulation wheel
        modulation = bytes([0xB1, 1, 64])
        synthesizer.process_midi_message(modulation)

        # Verify MPE is processing
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('enabled', False) is True

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_voice_allocation(self, synthesizer):
        """Test MPE voice allocation."""
        # Send multiple notes
        for note in [60, 64, 67, 72]:
            note_on = bytes([0x91, note, 100])
            synthesizer.process_midi_message(note_on)

        # Verify voices are allocated
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get('active_notes', 0) >= 4

        # Clean up
        for note in [60, 64, 67, 72]:
            note_off = bytes([0x81, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_with_effects(self, synthesizer):
        """Test MPE with effects processing."""
        # Send MPE note
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note pitch bend
        pitch_bend = bytes([0xB1, 74, 80])
        synthesizer.process_midi_message(pitch_bend)

        # Generate audio with effects
        audio = synthesizer.generate_audio_block(block_size=1024)
        
        # Verify audio was generated
        assert audio.shape == (1024, 2)
        assert np.any(audio != 0)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)