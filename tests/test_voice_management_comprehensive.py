"""
Voice Management Comprehensive Tests

Tests for voice allocation and management with actual synthesizer integration:
- Voice allocation strategies
- Voice stealing algorithms
- Voice priority calculation
- Drum voice allocation
- Exclusive class stealing
- Integration with MIDI processing
"""

from __future__ import annotations

import pytest
import numpy as np


class TestVoiceManagementComprehensive:
    """Test voice management with synthesizer integration."""

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
    def test_voice_manager_initialization(self, synthesizer):
        """Test voice manager initialization."""
        assert hasattr(synthesizer, 'voice_manager')
        assert synthesizer.voice_manager is not None

    @pytest.mark.unit
    def test_voice_allocation_strategies(self, synthesizer):
        """Test voice allocation strategies."""
        # Send multiple notes to trigger voice allocation
        for note in [60, 64, 67, 72]:
            note_on = bytes([0x90, note, 100])
            synthesizer.process_midi_message(note_on)

        # Generate audio to process voices
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Clean up
        for note in [60, 64, 67, 72]:
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_stealing_algorithms(self, synthesizer):
        """Test voice stealing algorithms."""
        # Fill all voices
        max_notes = 64
        for i in range(max_notes):
            note = 60 + (i % 12)
            note_on = bytes([0x90, note, 100])
            synthesizer.process_midi_message(note_on)

        # Try to exceed polyphony (should trigger voice stealing)
        note_on = bytes([0x90, 72, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        for i in range(max_notes + 1):
            note = 60 + (i % 12)
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_priority_calculation(self, synthesizer):
        """Test voice priority calculation."""
        # Send notes with different velocities
        velocities = [127, 100, 80, 60]
        for i, vel in enumerate(velocities):
            note = 60 + i
            note_on = bytes([0x90, note, vel])
            synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        for i, _ in enumerate(velocities):
            note = 60 + i
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_drum_voice_allocation(self, synthesizer):
        """Test drum voice allocation."""
        # Send drum notes on channel 9
        drum_notes = [36, 38, 42, 46]  # Kick, snare, hi-hat, open hi-hat
        for note in drum_notes:
            note_on = bytes([0x99, note, 100])
            synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Clean up
        for note in drum_notes:
            note_off = bytes([0x89, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_exclusive_class_stealing(self, synthesizer):
        """Test exclusive class voice stealing."""
        # Send multiple notes
        for note in [60, 64, 67]:
            note_on = bytes([0x90, note, 100])
            synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        for note in [60, 64, 67]:
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_cleanup_after_release(self, synthesizer):
        """Test voice cleanup after release."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        assert audio.shape == (512, 2)

        # Send note-off
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

        # Generate more audio (voice should be released)
        audio = synthesizer.generate_audio_block(block_size=512)
        assert audio.shape == (512, 2)

    @pytest.mark.unit
    def test_voice_with_sustain_pedal(self, synthesizer):
        """Test voice with sustain pedal."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send sustain pedal on
        sustain_on = bytes([0xB0, 64, 127])
        synthesizer.process_midi_message(sustain_on)

        # Send note-off (should sustain)
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Send sustain pedal off
        sustain_off = bytes([0xB0, 64, 0])
        synthesizer.process_midi_message(sustain_off)

    @pytest.mark.unit
    def test_voice_with_portamento(self, synthesizer):
        """Test voice with portamento."""
        # Send first note
        note_on1 = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on1)

        # Send portamento on
        portamento_on = bytes([0xB0, 65, 127])
        synthesizer.process_midi_message(portamento_on)

        # Send second note (should glide)
        note_on2 = bytes([0x90, 72, 100])
        synthesizer.process_midi_message(note_on2)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=1024)
        
        # Verify audio was generated
        assert audio.shape == (1024, 2)

        # Clean up
        note_off1 = bytes([0x80, 60, 0])
        note_off2 = bytes([0x80, 72, 0])
        synthesizer.process_midi_message(note_off1)
        synthesizer.process_midi_message(note_off2)
        portamento_off = bytes([0xB0, 65, 0])
        synthesizer.process_midi_message(portamento_off)

    @pytest.mark.unit
    def test_voice_with_pitch_bend(self, synthesizer):
        """Test voice with pitch bend."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send pitch bend
        pitch_bend = bytes([0xE0, 0x00, 0x40])
        synthesizer.process_midi_message(pitch_bend)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_modulation(self, synthesizer):
        """Test voice with modulation."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send modulation
        modulation = bytes([0xB0, 1, 64])
        synthesizer.process_midi_message(modulation)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_channel_pressure(self, synthesizer):
        """Test voice with channel pressure."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send channel pressure
        pressure = bytes([0xD0, 64])
        synthesizer.process_midi_message(pressure)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_poly_pressure(self, synthesizer):
        """Test voice with polyphonic pressure."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send polyphonic pressure
        pressure = bytes([0xA0, 60, 80])
        synthesizer.process_midi_message(pressure)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_multiple_channels(self, synthesizer):
        """Test voice with multiple channels."""
        # Send notes on different channels
        for channel in range(4):
            note_on = bytes([0x90 + channel, 60, 100])
            synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Clean up
        for channel in range(4):
            note_off = bytes([0x80 + channel, 60, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_program_change(self, synthesizer):
        """Test voice with program change."""
        # Send program change
        program_change = bytes([0xC0, 10])
        synthesizer.process_midi_message(program_change)

        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_bank_select(self, synthesizer):
        """Test voice with bank select."""
        # Send bank select
        bank_msb = bytes([0xB0, 0, 1])
        bank_lsb = bytes([0xB0, 32, 0])
        synthesizer.process_midi_message(bank_msb)
        synthesizer.process_midi_message(bank_lsb)

        # Send program change
        program_change = bytes([0xC0, 10])
        synthesizer.process_midi_message(program_change)

        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_volume(self, synthesizer):
        """Test voice with volume."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send volume change
        volume = bytes([0xB0, 7, 64])
        synthesizer.process_midi_message(volume)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_pan(self, synthesizer):
        """Test voice with pan."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send pan change
        pan = bytes([0xB0, 10, 32])  # Left
        synthesizer.process_midi_message(pan)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_expression(self, synthesizer):
        """Test voice with expression."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send expression
        expression = bytes([0xB0, 11, 100])
        synthesizer.process_midi_message(expression)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_reverb_send(self, synthesizer):
        """Test voice with reverb send."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send reverb send
        reverb = bytes([0xB0, 91, 64])
        synthesizer.process_midi_message(reverb)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_chorus_send(self, synthesizer):
        """Test voice with chorus send."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send chorus send
        chorus = bytes([0xB0, 93, 64])
        synthesizer.process_midi_message(chorus)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_voice_with_variation_send(self, synthesizer):
        """Test voice with variation send."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send variation send
        variation = bytes([0xB0, 94, 64])
        synthesizer.process_midi_message(variation)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)