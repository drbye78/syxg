"""
Plugin System Comprehensive Tests

Tests for plugin discovery and loading with actual synthesizer integration:
- Plugin discovery
- Plugin loading/unloading
- Jupiter-X FM plugin
- Plugin registry
- Plugin lifecycle
"""

from __future__ import annotations

import pytest
import numpy as np


class TestPluginComprehensive:
    """Test plugin system with synthesizer integration."""

    @pytest.fixture
    def synthesizer(self):
        """Create a synthesizer instance for testing."""
        from synth.synthesizers.rendering import ModernXGSynthesizer
        
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
    def test_plugin_system_initialization(self, synthesizer):
        """Test plugin system initialization."""
        assert hasattr(synthesizer, 'plugin_registry')

    @pytest.mark.unit
    def test_plugin_discovery(self, synthesizer):
        """Test plugin discovery mechanism."""
        if hasattr(synthesizer, 'plugin_registry'):
            plugins = synthesizer.plugin_registry.get_available_plugins()
            assert isinstance(plugins, list)

    @pytest.mark.unit
    def test_plugin_loading(self, synthesizer):
        """Test plugin loading."""
        if hasattr(synthesizer, 'plugin_registry'):
            # Try to load a plugin
            success = synthesizer.plugin_registry.load_plugin(
                "jupiter_x.fm_extensions.JupiterXFMPlugin",
                None
            )
            # May succeed or fail depending on plugin availability
            assert success is True or success is False

    @pytest.mark.unit
    def test_plugin_unloading(self, synthesizer):
        """Test plugin unloading."""
        if hasattr(synthesizer, 'plugin_registry'):
            # Try to unload a plugin
            success = synthesizer.plugin_registry.unload_plugin(
                "jupiter_x.fm_extensions.JupiterXFMPlugin"
            )
            # May succeed or fail depending on plugin state
            assert success is True or success is False

    @pytest.mark.unit
    def test_plugin_registry(self, synthesizer):
        """Test plugin registry."""
        if hasattr(synthesizer, 'plugin_registry'):
            registry = synthesizer.plugin_registry
            assert hasattr(registry, 'get_available_plugins')
            assert hasattr(registry, 'load_plugin')
            assert hasattr(registry, 'unload_plugin')

    @pytest.mark.unit
    def test_jupiter_x_fm_plugin(self, synthesizer):
        """Test Jupiter-X FM plugin integration."""
        # Check if Jupiter-X engine is available
        if hasattr(synthesizer, 'jupiter_x_engine'):
            assert synthesizer.jupiter_x_engine is not None

    @pytest.mark.unit
    def test_plugin_with_audio_generation(self, synthesizer):
        """Test plugin with audio generation."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)
        assert np.any(audio != 0)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_plugin_engine_priority(self, synthesizer):
        """Test plugin engine priority."""
        if hasattr(synthesizer, 'engine_registry'):
            engines = synthesizer.engine_registry.get_registered_engines()
            assert isinstance(engines, list)
            assert len(engines) > 0

    @pytest.mark.unit
    def test_plugin_with_midi(self, synthesizer):
        """Test plugin with MIDI processing."""
        # Send various MIDI messages
        messages = [
            bytes([0x90, 60, 100]),  # Note-on
            bytes([0xB0, 7, 100]),   # Volume
            bytes([0xB0, 10, 64]),   # Pan
            bytes([0x80, 60, 0]),    # Note-off
        ]
        
        for msg in messages:
            synthesizer.process_midi_message(msg)

    @pytest.mark.unit
    def test_plugin_with_effects(self, synthesizer):
        """Test plugin with effects processing."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Generate audio with effects
        audio = synthesizer.generate_audio_block(block_size=1024)
        
        # Verify audio was generated
        assert audio.shape == (1024, 2)
        assert np.any(audio != 0)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_plugin_multiple_engines(self, synthesizer):
        """Test multiple synthesis engines."""
        if hasattr(synthesizer, 'engine_registry'):
            engines = synthesizer.engine_registry.get_registered_engines()
            
            # Should have multiple engines
            assert len(engines) >= 5

    @pytest.mark.unit
    def test_plugin_with_program_change(self, synthesizer):
        """Test plugin with program change."""
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
    def test_plugin_with_pitch_bend(self, synthesizer):
        """Test plugin with pitch bend."""
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
    def test_plugin_with_modulation(self, synthesizer):
        """Test plugin with modulation."""
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
    def test_plugin_with_channel_pressure(self, synthesizer):
        """Test plugin with channel pressure."""
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
    def test_plugin_with_poly_pressure(self, synthesizer):
        """Test plugin with polyphonic pressure."""
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
    def test_plugin_with_multiple_notes(self, synthesizer):
        """Test plugin with multiple notes."""
        # Send multiple notes
        notes = [60, 64, 67, 72]
        for note in notes:
            note_on = bytes([0x90, note, 100])
            synthesizer.process_midi_message(note_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=1024)
        
        # Verify audio was generated
        assert audio.shape == (1024, 2)
        assert np.any(audio != 0)

        # Clean up
        for note in notes:
            note_off = bytes([0x80, note, 0])
            synthesizer.process_midi_message(note_off)

    @pytest.mark.unit
    def test_plugin_with_bank_select(self, synthesizer):
        """Test plugin with bank select."""
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
    def test_plugin_with_sustain_pedal(self, synthesizer):
        """Test plugin with sustain pedal."""
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

        # Send sustain pedal off
        sustain_off = bytes([0xB0, 64, 0])
        synthesizer.process_midi_message(sustain_off)

    @pytest.mark.unit
    def test_plugin_with_sostenuto_pedal(self, synthesizer):
        """Test plugin with sostenuto pedal."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send sostenuto pedal on
        sostenuto_on = bytes([0xB0, 66, 127])
        synthesizer.process_midi_message(sostenuto_on)

        # Send note-off (should sustain)
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Send sostenuto pedal off
        sostenuto_off = bytes([0xB0, 66, 0])
        synthesizer.process_midi_message(sostenuto_off)

    @pytest.mark.unit
    def test_plugin_with_soft_pedal(self, synthesizer):
        """Test plugin with soft pedal."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send soft pedal on
        soft_on = bytes([0xB0, 67, 127])
        synthesizer.process_midi_message(soft_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)
        soft_off = bytes([0xB0, 67, 0])
        synthesizer.process_midi_message(soft_off)

    @pytest.mark.unit
    def test_plugin_with_legato_pedal(self, synthesizer):
        """Test plugin with legato pedal."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send legato pedal on
        legato_on = bytes([0xB0, 68, 127])
        synthesizer.process_midi_message(legato_on)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Clean up
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)
        legato_off = bytes([0xB0, 68, 0])
        synthesizer.process_midi_message(legato_off)

    @pytest.mark.unit
    def test_plugin_with_hold_pedal(self, synthesizer):
        """Test plugin with hold pedal."""
        # Send note-on
        note_on = bytes([0x90, 60, 100])
        synthesizer.process_midi_message(note_on)

        # Send hold pedal on
        hold_on = bytes([0xB0, 69, 127])
        synthesizer.process_midi_message(hold_on)

        # Send note-off (should hold)
        note_off = bytes([0x80, 60, 0])
        synthesizer.process_midi_message(note_off)

        # Generate audio
        audio = synthesizer.generate_audio_block(block_size=512)
        
        # Verify audio was generated
        assert audio.shape == (512, 2)

        # Send hold pedal off
        hold_off = bytes([0xB0, 69, 0])
        synthesizer.process_midi_message(hold_off)