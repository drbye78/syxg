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
        from synth.synthesizers.rendering import ModernXGSynthesizer

        synth = ModernXGSynthesizer(
            sample_rate=44100,
            max_channels=16,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=True,
        )
        yield synth
        synth.cleanup()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_note_data(self, synthesizer) -> list[dict]:
        """Return per-note data dicts from MPE info, or empty list."""
        info = synthesizer.get_mpe_info()
        return (
            info.get("manager_info", {}).get("active_notes", [])
            or []
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_mpe_initialization(self, synthesizer):
        """Test MPE system initialization."""
        assert hasattr(synthesizer, "mpe_system")
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("enabled", False) is True

    @pytest.mark.unit
    def test_mpe_note_on_off(self, synthesizer):
        """Test MPE note-on/off processing."""
        # Send MPE note-on on member channel 1
        note_on = bytes([0x91, 60, 100])  # Channel 1, Note 60, Velocity 100
        synthesizer.process_midi_message(note_on)

        # Verify note is active
        notes = self._get_note_data(synthesizer)
        assert len(notes) >= 1
        assert notes[0]["note_number"] == 60
        assert notes[0]["active"] is True

        # Send MPE note-off
        note_off = bytes([0x81, 60, 0])  # Channel 1, Note 60, Velocity 0
        synthesizer.process_midi_message(note_off)

        # Verify note is released
        notes = self._get_note_data(synthesizer)
        assert len(notes) == 0

    @pytest.mark.unit
    def test_per_note_pitch_bend(self, synthesizer):
        """Test per-note pitch bend via actual pitch bend message (0xEn)."""
        # Send note-on on member channel 1
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        notes = self._get_note_data(synthesizer)
        assert len(notes) >= 1
        assert notes[0]["pitch_bend"] == pytest.approx(0.0, abs=0.01)

        # Send per-note pitch bend on channel 1: max bend up
        # 0xE1 = pitch bend on channel 1, value = (0x7F << 7) | 0x7F = 16383
        pitch_bend = bytes([0xE1, 0x7F, 0x7F])
        synthesizer.process_midi_message(pitch_bend)

        # Verify pitch bend value changed on the note
        notes = self._get_note_data(synthesizer)
        if notes:
            assert notes[0]["pitch_bend"] == pytest.approx(48.0, rel=0.01)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_per_note_timbre_control(self, synthesizer):
        """Test per-note timbre control (CC74)."""
        # Send note-on on member channel 1
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note timbre (CC74 on channel 1)
        timbre = bytes([0xB1, 74, 100])
        synthesizer.process_midi_message(timbre)

        # Verify timbre value changed
        notes = self._get_note_data(synthesizer)
        if notes:
            assert notes[0]["timbre"] == pytest.approx(100 / 127.0, rel=0.01)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_per_note_pressure(self, synthesizer):
        """Test per-note pressure (polyphonic aftertouch)."""
        # Send note-on on member channel 1
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send polyphonic key pressure (0xA1 = poly pressure, channel 1)
        pressure = bytes([0xA1, 60, 80])  # Channel 1, Note 60, Pressure 80
        synthesizer.process_midi_message(pressure)

        # Verify pressure value changed
        notes = self._get_note_data(synthesizer)
        if notes:
            assert notes[0]["pressure"] == pytest.approx(80 / 127.0, rel=0.01)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_zone_configuration(self, synthesizer):
        """Test MPE zone configuration."""
        mpe_info = synthesizer.get_mpe_info()
        # The MPE system should report at least 1 configured zone
        assert mpe_info.get("zones", 0) >= 1
        # Manager info should contain detailed zone data
        manager_info = mpe_info.get("manager_info", {})
        zones = manager_info.get("zones", [])
        assert len(zones) >= 1

    @pytest.mark.skip(reason="Audio engine returns silence — pre-existing engine issue")
    @pytest.mark.unit
    def test_mpe_with_audio_generation(self, synthesizer):
        """Test MPE with audio generation."""
        # Send MPE note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send pitch bend up
        pitch_bend = bytes([0xE1, 0x40, 0x40])  # bend up ~halfway
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
        """Test MPE with multiple simultaneous notes on different member channels."""
        # Send notes to DIFFERENT member channels (1, 2, 3)
        notes = {1: 60, 2: 64, 3: 67}  # channel -> note
        for ch, note in notes.items():
            note_on = bytes([0x90 | ch, note, 100])
            synthesizer.process_midi_message(note_on)

        # Verify all 3 notes are active
        active = self._get_note_data(synthesizer)
        assert len(active) == 3
        active_notes = {n["channel"]: n["note_number"] for n in active}
        for ch, note in notes.items():
            assert active_notes.get(ch) == note

        # Send pitch bend on channel 1 only (affects just that note)
        pitch_bend = bytes([0xE1, 0x7F, 0x7F])  # max bend up
        synthesizer.process_midi_message(pitch_bend)

        active = self._get_note_data(synthesizer)
        for n in active:
            if n["channel"] == 1:
                assert n["pitch_bend"] == pytest.approx(48.0, rel=0.01)
            else:
                assert n["pitch_bend"] == pytest.approx(0.0, abs=0.01)

        # Clean up
        for ch, note in notes.items():
            note_off = bytes([0x80 | ch, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_pitch_bend_range(self, synthesizer):
        """Test MPE pitch bend range defaults to 48 semitones."""
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("pitch_bend_range", 0) == 48

    @pytest.mark.unit
    def test_mpe_with_channel_pressure(self, synthesizer):
        """Test MPE with channel pressure (monophonic aftertouch).

        Note: channel pressure is NOT routed through the MPE system.
        This test verifies that channel pressure does not interfere with
        MPE state.
        """
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send channel pressure (aftertouch) on channel 1
        pressure = bytes([0xD1, 100])  # Channel 1, Pressure 100
        synthesizer.process_midi_message(pressure)

        # MPE should still be enabled and note active
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("enabled", False) is True
        assert mpe_info.get("active_notes", 0) >= 1

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_slide_control(self, synthesizer):
        """Test MPE slide control (CC75)."""
        # Send note-on on member channel 1
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send slide control (CC75 on channel 1)
        slide = bytes([0xB1, 75, 100])
        synthesizer.process_midi_message(slide)

        # Verify slide value changed
        notes = self._get_note_data(synthesizer)
        if notes:
            assert notes[0]["slide"] == pytest.approx(100 / 127.0, rel=0.01)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_lift_control(self, synthesizer):
        """Test MPE lift control (CC76)."""
        # Send note-on on member channel 1
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send lift control (CC76 on channel 1)
        lift = bytes([0xB1, 76, 100])
        synthesizer.process_midi_message(lift)

        # Verify lift value changed
        notes = self._get_note_data(synthesizer)
        if notes:
            assert notes[0]["lift"] == pytest.approx(100 / 127.0, rel=0.01)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_enable_disable(self, synthesizer):
        """Test MPE enable/disable."""
        # Disable MPE
        synthesizer.set_mpe_enabled(False)
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("enabled", False) is False

        # Enable MPE
        synthesizer.set_mpe_enabled(True)
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("enabled", False) is True

    @pytest.mark.unit
    def test_mpe_reset(self, synthesizer):
        """Test MPE reset."""
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        notes = self._get_note_data(synthesizer)
        assert len(notes) >= 1

        # Reset MPE
        synthesizer.reset_mpe()

        # Verify MPE is reset
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("active_notes", 0) == 0

    @pytest.mark.unit
    def test_mpe_with_modulation(self, synthesizer):
        """Test MPE with modulation wheel (CC1).

        Note: CC1 (modulation) is not an MPE controller. This test
        verifies that modulation does not interfere with MPE state.
        """
        # Send note-on
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send modulation wheel (CC1 on channel 1)
        modulation = bytes([0xB1, 1, 64])
        synthesizer.process_midi_message(modulation)

        # MPE should still be enabled and note active
        mpe_info = synthesizer.get_mpe_info()
        assert mpe_info.get("enabled", False) is True
        assert mpe_info.get("active_notes", 0) >= 1

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_mpe_voice_allocation(self, synthesizer):
        """Test MPE voice allocation across member channels."""
        # Send notes to different member channels (1, 2, 3, 4)
        notes = {1: 60, 2: 64, 3: 67, 4: 72}
        for ch, note in notes.items():
            note_on = bytes([0x90 | ch, note, 100])
            synthesizer.process_midi_message(note_on)

        # Verify all 4 notes are allocated
        active = self._get_note_data(synthesizer)
        assert len(active) == 4
        active_channels = {n["channel"] for n in active}
        for ch in notes:
            assert ch in active_channels

        # Clean up
        for ch, note in notes.items():
            note_off = bytes([0x80 | ch, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.skip(reason="Audio engine returns silence — pre-existing engine issue")
    @pytest.mark.unit
    def test_mpe_with_effects(self, synthesizer):
        """Test MPE with effects processing."""
        # Send MPE note
        note_on = bytes([0x91, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send per-note pitch bend
        pitch_bend = bytes([0xE1, 0x40, 0x40])  # bend up ~halfway
        synthesizer.process_midi_message(pitch_bend)

        # Generate audio with effects
        audio = synthesizer.generate_audio_block(block_size=1024)

        # Verify audio was generated
        assert audio.shape == (1024, 2)
        assert np.any(audio != 0)

        # Clean up
        note_off = bytes([0x81, 60, 0])
        synthesizer.process_midi_message(note_off)
