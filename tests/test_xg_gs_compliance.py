"""
XG/GS/GM Compliance Validation Tests

Tests production-grade XG/GS/GM synthesizer system for full specification
compliance including:
- XG part modes (Normal, Drum, Single)
- XG Drum Map 1-4 support
- GS sysex handling
- NRPN parameter handling
- Part mode integration with SF2 engine
"""

from __future__ import annotations

import pytest


class TestXGSynthesizerSystem:
    """Tests for XGSynthesizerSystem core functionality."""

    def test_xg_system_initialization(self):
        """Test XGSynthesizerSystem initializes correctly."""
        from synth.protocols.xg.xg_synthesizer_system import XGSynthesizerSystem

        xg_sys = XGSynthesizerSystem(sample_rate=44100, device_id=0x10)

        assert xg_sys.sample_rate == 44100
        assert xg_sys.device_id == 0x10
        assert xg_sys.mode.xg_enabled is False
        assert xg_sys.sysex_router is not None
        assert xg_sys.gs_handler is not None

    def test_xg_system_enable_xg_mode(self):
        """Test enabling XG mode."""
        from synth.protocols.xg.xg_synthesizer_system import XGSynthesizerSystem

        xg_sys = XGSynthesizerSystem(sample_rate=44100, device_id=0x10)
        xg_sys.enable_xg_mode()

        assert xg_sys.mode.xg_enabled is True

    def test_xg_system_enable_gs_mode(self):
        """Test enabling GS mode."""
        from synth.protocols.xg.xg_synthesizer_system import XGSynthesizerSystem

        xg_sys = XGSynthesizerSystem(sample_rate=44100, device_id=0x10)
        xg_sys.enable_gs_mode()

        assert xg_sys.mode.gs_enabled is True


class TestXGDrumMap:
    """Tests for XG Drum Map functionality."""

    def test_drum_map_manager_initialization(self):
        """Test XGDrumMapManager initializes with correct defaults."""
        from synth.protocols.xg.xg_drum_map import XGDrumMapManager

        manager = XGDrumMapManager(num_parts=16)

        assert manager.num_parts == 16
        assert len(manager.maps) == 4  # Drum Map 1-4

    def test_drum_map_selection(self):
        """Test selecting different drum maps."""
        from synth.protocols.xg.xg_drum_map import XGDrumMapManager

        manager = XGDrumMapManager(num_parts=16)

        # Select Drum Map 1 for part 0
        manager.select_drum_map(part=0, map_number=1)
        assert manager.get_drum_map_for_part(0) == 1

        # Select Drum Map 2 for part 1
        manager.select_drum_map(part=1, map_number=2)
        assert manager.get_drum_map_for_part(1) == 2

        # Select Drum Map 3 for part 9 (drum channel)
        manager.select_drum_map(part=9, map_number=3)
        assert manager.get_drum_map_for_part(9) == 3

    def test_drum_note_mapping(self):
        """Test drum note mapping functionality."""
        from synth.protocols.xg.xg_drum_map import XGDrumMapManager

        manager = XGDrumMapManager(num_parts=16)

        # Set drum note mapping
        manager.set_note_mapping(part=9, source_note=36, target_note=60, drum_sound="kick")

        # Get mapping
        result = manager.get_note_mapping(part=9, source_note=36)
        assert result is not None
        mapped_note, entry = result
        assert mapped_note == 60

    def test_drum_map_reset(self):
        """Test resetting drum maps to defaults."""
        from synth.protocols.xg.xg_drum_map import XGDrumMapManager

        manager = XGDrumMapManager(num_parts=16)

        # Modify a drum map
        manager.select_drum_map(part=0, map_number=2)

        # Reset
        manager.reset_to_defaults()

        # Should return to default (Drum Map 1)
        assert manager.get_drum_map_for_part(0) == 1


class TestXGPartModeController:
    """Tests for XG Part Mode Controller."""

    def test_part_mode_controller_initialization(self):
        """Test XGPartModeController initializes correctly."""
        from synth.protocols.xg.xg_drum_map import XGPartModeController

        controller = XGPartModeController(num_parts=16)

        assert controller.num_parts == 16
        assert len(controller.part_modes) == 16

    def test_setting_part_mode(self):
        """Test setting part modes."""
        from synth.protocols.xg.xg_drum_map import XGPartModeController

        controller = XGPartModeController(num_parts=16)

        # Set part 0 to Normal mode
        controller.set_part_mode(part=0, mode=0)  # MODE_NORMAL
        assert controller.get_part_mode(0) == 0

        # Set part 9 to Drum mode
        controller.set_part_mode(part=9, mode=1)  # MODE_DRUM
        assert controller.get_part_mode(9) == 1

        # Set part 0 to Single mode
        controller.set_part_mode(part=0, mode=4)  # MODE_SINGLE
        assert controller.get_part_mode(0) == 4

    def test_part_mode_with_bank(self):
        """Test setting part mode with bank selection."""
        from synth.protocols.xg.xg_drum_map import XGPartModeController

        controller = XGPartModeController(num_parts=16)

        # Set part 9 to drum with GS drum bank
        controller.set_part_mode(part=9, mode=1, bank_msb=127, bank_lsb=0)

        mode = controller.get_part_mode(9)
        assert mode == 1

    def test_drum_map_assignment(self):
        """Test assigning drum maps to parts."""
        from synth.protocols.xg.xg_drum_map import XGPartModeController

        controller = XGPartModeController(num_parts=16)

        # Set part 9 to drum mode with Drum Map 2
        controller.set_part_mode(part=9, mode=1)
        controller.drum_map_manager.select_drum_map(part=9, map_number=2)

        assert controller.drum_map_manager.get_drum_map_for_part(9) == 2


class TestGSSysexHandler:
    """Tests for GS sysex handler."""

    def test_gs_handler_initialization(self):
        """Test GSSysexHandler initializes correctly."""
        from synth.protocols.gs.gs_sysex_handler import GSSysexHandler

        handler = GSSysexHandler(device_id=0x10)

        assert handler.device_id == 0x10
        assert handler.gs_enabled is False

    def test_gs_handler_enable(self):
        """Test enabling GS mode."""
        from synth.protocols.gs.gs_sysex_handler import GSSysexHandler

        handler = GSSysexHandler(device_id=0x10)
        handler.enable_gs()

        assert handler.gs_enabled is True
        assert handler.gs_mode == "gs"

    def test_gs_channel_parameters(self):
        """Test GS channel parameter handling."""
        from synth.protocols.gs.gs_sysex_handler import GSSysexHandler

        handler = GSSysexHandler(device_id=0x10)
        handler.enable_gs()

        # Set channel volume
        handler.set_channel_parameter(channel=0, param="volume", value=100)
        vol = handler.get_channel_parameter(channel=0, param="volume")
        assert vol == 100

        # Set channel pan
        handler.set_channel_parameter(channel=0, param="pan", value=64)
        pan = handler.get_channel_parameter(channel=0, param="pan")
        assert pan == 64

    def test_gs_drum_part_setup(self):
        """Test GS drum part configuration."""
        from synth.protocols.gs.gs_sysex_handler import GSSysexHandler

        handler = GSSysexHandler(device_id=0x10)
        handler.enable_gs()

        # Configure part 9 as drum part
        handler.set_drum_part(channel=9, drum_map=1)
        assert handler.is_drum_part(9) is True

        # Regular part should not be drum
        assert handler.is_drum_part(0) is False


class TestUnifiedSysexRouter:
    """Tests for unified sysex router."""

    def test_router_initialization(self):
        """Test UnifiedSysexRouter initializes correctly."""
        from synth.io.midi.unified_sysex_router import UnifiedSysexRouter

        router = UnifiedSysexRouter(device_id=0x10)

        assert router.device_id == 0x10
        assert router.xg_enabled is False
        assert router.gs_enabled is False

    def test_enable_xg_mode(self):
        """Test enabling XG mode on router."""
        from synth.io.midi.unified_sysex_router import UnifiedSysexRouter

        router = UnifiedSysexRouter(device_id=0x10)
        router.enable_xg()

        assert router.xg_enabled is True

    def test_enable_gs_mode(self):
        """Test enabling GS mode on router."""
        from synth.io.midi.unified_sysex_router import UnifiedSysexRouter

        router = UnifiedSysexRouter(device_id=0x10)
        router.enable_gs()

        assert router.gs_enabled is True


class TestSF2PartModeIntegrator:
    """Tests for SF2 part mode integration."""

    def test_integrator_initialization(self):
        """Test SF2PartModeIntegrator initializes correctly."""
        from synth.engines.sf2_engine_controller import SF2PartModeIntegrator

        class MockSF2Engine:
            pass

        engine = MockSF2Engine()
        integrator = SF2PartModeIntegrator(sf2_engine=engine)

        assert integrator.sf2_engine is engine
        assert len(integrator.channel_modes) == 16

    def test_set_channel_mode(self):
        """Test setting channel modes."""
        from synth.engines.sf2_engine_controller import SF2PartModeIntegrator

        class MockSF2Engine:
            pass

        engine = MockSF2Engine()
        integrator = SF2PartModeIntegrator(sf2_engine=engine)

        # Set channel 9 to drum mode
        result = integrator.set_channel_mode(channel=9, mode="drum", bank_msb=127)
        assert result is True
        assert integrator.channel_modes[9]["mode"] == "drum"

        # Set channel 0 to normal mode
        result = integrator.set_channel_mode(channel=0, mode="normal")
        assert result is True
        assert integrator.channel_modes[0]["mode"] == "normal"

    def test_get_drum_bank(self):
        """Test getting drum bank for channel."""
        from synth.engines.sf2_engine_controller import SF2PartModeIntegrator

        class MockSF2Engine:
            pass

        engine = MockSF2Engine()
        integrator = SF2PartModeIntegrator(sf2_engine=engine)

        # Set channel 9 to drum mode
        integrator.set_channel_mode(channel=9, mode="drum", bank_msb=127)

        # Get drum bank
        drum_bank = integrator.get_drum_bank_for_channel(9)
        assert drum_bank == 127

        # Normal channel should return 0
        normal_bank = integrator.get_drum_bank_for_channel(0)
        assert normal_bank == 0


class TestIntegrationWithSynthesizer:
    """Integration tests for XG/GS components with Synthesizer."""

    def test_synthesizer_has_xg_system(self):
        """Test that Synthesizer has XGSynthesizerSystem."""
        from synth.primitives.synthesizer import Synthesizer

        synth = Synthesizer(enable_audio_output=False)

        assert hasattr(synth, "xg_synthesizer")
        assert synth.xg_synthesizer is not None

    def test_xg_synthesizer_connected_to_engine_registry(self):
        """Test XGSynthesizerSystem is connected to engine registry."""
        from synth.primitives.synthesizer import Synthesizer

        synth = Synthesizer(enable_audio_output=False)

        assert synth.xg_synthesizer.engine_registry is not None

    def test_xg_synthesizer_has_required_components(self):
        """Test XGSynthesizerSystem has all required components."""
        from synth.primitives.synthesizer import Synthesizer

        synth = Synthesizer(enable_audio_output=False)
        xg_sys = synth.xg_synthesizer

        assert hasattr(xg_sys, "sysex_router")
        assert hasattr(xg_sys, "xg_multi_part")
        assert hasattr(xg_sys, "xg_part_mode")
        assert hasattr(xg_sys, "gs_handler")
        assert hasattr(xg_sys, "xg_drum_setup")


class TestXGSystemCompliance:
    """Tests for XG specification compliance."""

    def test_xg_multi_part_16_channels(self):
        """Test XG multi-part supports 16 channels."""
        from synth.protocols.xg.xg_multi_part_setup import XGMultiPartSetup

        setup = XGMultiPartSetup(num_parts=16)

        assert setup.num_parts == 16

        # All parts should be initially normal
        for part in range(16):
            part_info = setup.get_part_info(part)
            assert part_info is not None

    def test_xg_drum_setup_channels(self):
        """Test XG drum setup for drum channels."""
        from synth.protocols.xg.xg_drum_setup_parameters import XGDrumSetupParameters

        setup = XGDrumSetupParameters(num_channels=16)

        assert setup.num_channels == 16

        # Configure part 9 as drum
        setup.set_drum_kit(part=9, kit_number=1)
        kit = setup.get_drum_kit(part=9)
        assert kit == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
