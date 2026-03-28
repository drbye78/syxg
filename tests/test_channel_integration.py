"""
Channel Integration Tests

Tests for channel volume/pan, effects routing, controller processing,
and channel poly/mono modes in the XG synthesizer.
"""

from __future__ import annotations

import pytest
import numpy as np

from synth.midi.message import MIDIMessage
from tests.utils.audio_utils import calculate_rms
from tests.utils.midi_utils import create_control_change_message, create_program_change_message


class TestChannelIntegration:
    """Test channel processing integration."""

    @pytest.mark.integration
    def test_channel_volume_pan(self, sample_rate, block_size):
        """Test channel volume and pan control."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test volume control
        renderer.control_change(7, 100)  # Volume
        assert renderer.volume == 100

        # Test pan control
        renderer.control_change(10, 64)  # Pan center
        assert renderer.pan == 64

    @pytest.mark.integration
    def test_channel_effects_routing(self, sample_rate, block_size):
        """Test channel effects send routing."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test reverb send
        renderer.control_change(91, 40)  # Reverb send
        assert renderer.controllers[91] == 40

        # Test chorus send
        renderer.control_change(93, 30)  # Chorus send
        assert renderer.controllers[93] == 30

    @pytest.mark.integration
    def test_channel_controller_processing(self, sample_rate, block_size):
        """Test channel controller processing."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test mod wheel
        renderer.control_change(1, 64)  # Mod wheel
        assert renderer.controllers[1] == 64

        # Test expression
        renderer.control_change(11, 100)  # Expression
        assert renderer.expression == 100

        # Test sustain pedal
        renderer.control_change(64, 127)  # Sustain on
        assert renderer.controllers[64] == 127

    @pytest.mark.integration
    def test_channel_nrpn_handling(self, sample_rate, block_size):
        """Test channel NRPN handling."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test NRPN sequence
        renderer.control_change(99, 1)  # NRPN MSB
        renderer.control_change(98, 8)  # NRPN LSB
        renderer.control_change(6, 64)  # Data entry MSB

        assert renderer.nrpn_msb == 1
        assert renderer.nrpn_lsb == 8

    @pytest.mark.integration
    def test_channel_rpn_handling(self, sample_rate, block_size):
        """Test channel RPN handling."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test RPN sequence
        renderer.control_change(101, 0)  # RPN MSB
        renderer.control_change(100, 0)  # RPN LSB
        renderer.control_change(6, 2)  # Pitch bend range

        assert renderer.rpn_msb == 0
        assert renderer.rpn_lsb == 0

    @pytest.mark.integration
    def test_channel_poly_mono_modes(self, sample_rate, block_size):
        """Test channel poly and mono voice modes."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Default should be poly mode
        assert renderer.voice_mode == renderer.VOICE_MODE_POLY

        # Test mono mode
        renderer.control_change(126, 1)  # Mono on
        assert renderer.mono_mode is True

        # Test poly mode
        renderer.control_change(127, 1)  # Poly on
        assert renderer.mono_mode is False

    @pytest.mark.integration
    def test_channel_pitch_bend(self, sample_rate, block_size):
        """Test channel pitch bend processing."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Test pitch bend center
        renderer.pitch_bend(0, 64)  # Center
        assert renderer.pitch_bend_value == 8192

        # Test pitch bend up
        renderer.pitch_bend(127, 127)  # Max up
        assert renderer.pitch_bend_value == 16383

        # Test pitch bend down
        renderer.pitch_bend(0, 0)  # Max down
        assert renderer.pitch_bend_value == 0