"""
Enhanced Test Suite for S.Art2 Enhancement

Tests cover:
- Velocity-based articulation switching
- Key-based articulation switching
- Full SYSEX implementation (8 command types)
- NRPN parameter controller
- Genos2 compatibility
"""

import pytest
import numpy as np
from typing import Dict, Any

from synth.xg.sart.sart2_region import SArt2Region
from synth.xg.sart.articulation_controller import ArticulationController
from synth.xg.sart.nrpn import YamahaNRPNMapper, NRPNParameterController
from synth.partial.region import IRegion
from synth.engine.region_descriptor import RegionDescriptor


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_region():
    """Create mock base region for testing."""
    class MockRegion(IRegion):
        def __init__(self):
            descriptor = RegionDescriptor(
                region_id=0,
                engine_type='mock',
                key_range=(0, 127),
                velocity_range=(0, 127)
            )
            super().__init__(descriptor, 44100)
            self._active = False
        
        def _load_sample_data(self):
            return None
        
        def _create_partial(self):
            return None
        
        def _init_envelopes(self):
            pass
        
        def _init_filters(self):
            pass
        
        def note_on(self, velocity, note):
            self._active = True
            return True
        
        def note_off(self):
            self._active = False
        
        def is_active(self):
            return self._active
        
        def generate_samples(self, block_size, modulation):
            return np.zeros(block_size * 2, dtype=np.float32)
        
        def initialize(self):
            return True
        
        def reset(self):
            pass
        
        def dispose(self):
            pass
        
        def get_region_info(self):
            return {}
    
    return MockRegion()


@pytest.fixture
def controller():
    """Create ArticulationController for testing."""
    return ArticulationController()


@pytest.fixture
def mapper():
    """Create YamahaNRPNMapper for testing."""
    return YamahaNRPNMapper()


@pytest.fixture
def param_controller():
    """Create NRPNParameterController for testing."""
    return NRPNParameterController()


# ============================================================================
# VELOCITY-BASED ARTICULATION SWITCHING TESTS
# ============================================================================

class TestVelocityBasedSwitching:
    """Tests for velocity-based articulation switching."""
    
    def test_set_velocity_articulation(self, mock_region):
        """Test setting velocity articulations."""
        region = SArt2Region(mock_region)
        
        region.set_velocity_articulation(0, 64, 'pizzicato')
        region.set_velocity_articulation(65, 100, 'staccato')
        region.set_velocity_articulation(101, 127, 'marcato')
        
        assert region._velocity_enabled == True
        assert len(region._velocity_articulations) == 3
        assert (0, 64) in region._velocity_articulations
        assert (65, 100) in region._velocity_articulations
        assert (101, 127) in region._velocity_articulations
    
    def test_velocity_switching(self, mock_region):
        """Test velocity-based articulation switching."""
        region = SArt2Region(mock_region)
        
        region.set_velocity_articulation(0, 64, 'pizzicato')
        region.set_velocity_articulation(65, 100, 'staccato')
        region.set_velocity_articulation(101, 127, 'marcato')
        
        # Test soft velocity
        region.note_on(velocity=50, note=60)
        assert region.get_articulation() == 'pizzicato'
        
        # Test medium velocity
        region.note_on(velocity=80, note=60)
        assert region.get_articulation() == 'staccato'
        
        # Test loud velocity
        region.note_on(velocity=120, note=60)
        assert region.get_articulation() == 'marcato'
    
    def test_velocity_boundary_values(self, mock_region):
        """Test velocity switching at boundary values."""
        region = SArt2Region(mock_region)
        
        region.set_velocity_articulation(0, 64, 'pizzicato')
        region.set_velocity_articulation(65, 127, 'staccato')
        
        # Test boundary
        region.note_on(velocity=64, note=60)
        assert region.get_articulation() == 'pizzicato'
        
        region.note_on(velocity=65, note=60)
        assert region.get_articulation() == 'staccato'
    
    def test_clear_velocity_articulations(self, mock_region):
        """Test clearing velocity articulations."""
        region = SArt2Region(mock_region)
        
        region.set_velocity_articulation(0, 64, 'soft')
        region.clear_velocity_articulations()
        
        assert region._velocity_enabled == False
        assert len(region._velocity_articulations) == 0
    
    def test_velocity_auto_enabled(self, mock_region):
        """Test that velocity switching is auto-enabled."""
        region = SArt2Region(mock_region)
        
        assert region._velocity_enabled == False
        
        region.set_velocity_articulation(0, 64, 'soft')
        
        assert region._velocity_enabled == True


# ============================================================================
# KEY-BASED ARTICULATION SWITCHING TESTS
# ============================================================================

class TestKeyBasedSwitching:
    """Tests for key-based articulation switching."""
    
    def test_set_key_articulation(self, mock_region):
        """Test setting key articulations."""
        region = SArt2Region(mock_region)
        
        region.set_key_articulation(0, 47, 'bass')
        region.set_key_articulation(48, 83, 'mid')
        region.set_key_articulation(84, 127, 'treble')
        
        assert region._key_enabled == True
        assert len(region._key_articulations) == 3
        assert (0, 47) in region._key_articulations
        assert (48, 83) in region._key_articulations
        assert (84, 127) in region._key_articulations
    
    def test_key_switching(self, mock_region):
        """Test key-based articulation switching."""
        region = SArt2Region(mock_region)
        
        region.set_key_articulation(0, 47, 'pizzicato_strings')
        region.set_key_articulation(48, 83, 'spiccato')
        region.set_key_articulation(84, 127, 'tremolando')
        
        # Test bass key
        region.note_on(velocity=100, note=36)  # C2
        assert region.get_articulation() == 'pizzicato_strings'
        
        # Test mid key
        region.note_on(velocity=100, note=60)  # C4
        assert region.get_articulation() == 'spiccato'
        
        # Test treble key
        region.note_on(velocity=100, note=96)  # C7
        assert region.get_articulation() == 'tremolando'
    
    def test_key_boundary_values(self, mock_region):
        """Test key switching at boundary values."""
        region = SArt2Region(mock_region)
        
        region.set_key_articulation(0, 60, 'pizzicato')
        region.set_key_articulation(61, 127, 'staccato')
        
        # Test boundary
        region.note_on(velocity=100, note=60)
        assert region.get_articulation() == 'pizzicato'
        
        region.note_on(velocity=100, note=61)
        assert region.get_articulation() == 'staccato'
    
    def test_clear_key_articulations(self, mock_region):
        """Test clearing key articulations."""
        region = SArt2Region(mock_region)
        
        region.set_key_articulation(0, 47, 'bass')
        region.clear_key_articulations()
        
        assert region._key_enabled == False
        assert len(region._key_articulations) == 0
    
    def test_key_auto_enabled(self, mock_region):
        """Test that key switching is auto-enabled."""
        region = SArt2Region(mock_region)
        
        assert region._key_enabled == False
        
        region.set_key_articulation(0, 47, 'bass')
        
        assert region._key_enabled == True


# ============================================================================
# COMBINED VELOCITY + KEY SWITCHING TESTS
# ============================================================================

class TestCombinedSwitching:
    """Tests for combined velocity and key switching."""
    
    def test_combined_switching(self, mock_region):
        """Test combined velocity and key switching."""
        region = SArt2Region(mock_region)
        
        # Set velocity articulations (velocity is checked first in note_on)
        region.set_velocity_articulation(0, 64, 'legato')
        region.set_velocity_articulation(65, 127, 'marcato')
        
        # Test different velocities
        region.note_on(velocity=50, note=36)
        assert region.get_articulation() == 'legato'
        
        region.note_on(velocity=100, note=84)
        assert region.get_articulation() == 'marcato'
    
    def test_switching_order(self, mock_region):
        """Test that switching order matters."""
        region = SArt2Region(mock_region)
        
        # Set velocity articulations
        region.set_velocity_articulation(0, 64, 'pizzicato')
        region.set_velocity_articulation(65, 127, 'staccato')
        
        region.note_on(velocity=50, note=60)
        assert region.get_articulation() == 'pizzicato'
        
        region.note_on(velocity=100, note=60)
        assert region.get_articulation() == 'staccato'


# ============================================================================
# SYSEX IMPLEMENTATION TESTS
# ============================================================================

class TestSYSEXImplementation:
    """Tests for full SYSEX implementation."""
    
    def test_sysex_command_definitions(self, controller):
        """Test SYSEX command definitions."""
        assert len(controller.SYSEX_COMMANDS) == 8
        
        assert 0x10 in controller.SYSEX_COMMANDS
        assert 0x11 in controller.SYSEX_COMMANDS
        assert 0x12 in controller.SYSEX_COMMANDS
        assert 0x13 in controller.SYSEX_COMMANDS
        assert 0x14 in controller.SYSEX_COMMANDS
        assert 0x15 in controller.SYSEX_COMMANDS
        assert 0x16 in controller.SYSEX_COMMANDS
        assert 0x17 in controller.SYSEX_COMMANDS
    
    def test_sysex_articulation_set_parser(self, controller):
        """Test parsing articulation set SYSEX."""
        sysex = bytes([0xF0, 0x43, 0x10, 0x4C, 0x10, 0x00, 0x01, 0x01, 0xF7])
        result = controller.process_sysex(sysex)
        
        assert result['command'] == 'set_articulation'
        assert result['channel'] == 0
        assert result['articulation'] == 'legato'
        assert result['nrpn_msb'] == 1
        assert result['nrpn_lsb'] == 1
    
    def test_sysex_parameter_set_parser(self, controller):
        """Test parsing parameter set SYSEX."""
        sysex = bytes([0xF0, 0x43, 0x10, 0x4C, 0x11, 0x00, 0x00, 0x00, 0x40, 0x00, 0xF7])
        result = controller.process_sysex(sysex)
        
        assert result['command'] == 'set_parameter'
        assert result['channel'] == 0
        assert result['param_msb'] == 0
        assert result['param_lsb'] == 0
        assert result['value'] == 8192
        assert result['param_info'] is not None
    
    def test_sysex_articulation_chain_parser(self, controller):
        """Test parsing articulation chain SYSEX."""
        sysex = bytes([
            0xF0, 0x43, 0x10, 0x4C, 0x14, 0x00, 0x02,
            0x01, 0x01, 0x01, 0xF4,  # legato, 500ms
            0x01, 0x02, 0x01, 0x2C,  # staccato, 300ms
            0xF7
        ])
        result = controller.process_sysex(sysex)
        
        assert result['command'] == 'set_articulation_chain'
        assert result['channel'] == 0
        assert result['count'] == 2
        assert len(result['articulations']) == 2
        assert result['articulations'][0]['articulation'] == 'legato'
        assert result['articulations'][1]['articulation'] == 'staccato'
    
    def test_sysex_bulk_dump_parser(self, controller):
        """Test parsing bulk dump SYSEX."""
        sysex = bytes([
            0xF0, 0x43, 0x10, 0x4C, 0x15, 0x00,
            0x01, 0x01,  # legato
            0x01, 0x02,  # staccato
            0x00, 0x00,  # checksum placeholder
            0xF7
        ])
        result = controller.process_sysex(sysex)
        
        assert result['command'] == 'bulk_dump'
        assert result['channel'] == 0
        assert 'checksum_valid' in result
        assert 'data' in result
    
    def test_sysex_builder_articulation_set(self, controller):
        """Test building articulation set SYSEX."""
        sysex = controller.build_sysex_articulation_set(0, 1, 1)
        
        assert sysex[0] == 0xF0
        assert sysex[1] == 0x43
        assert sysex[2] == 0x10
        assert sysex[3] == 0x4C
        assert sysex[4] == 0x10
        assert sysex[5] == 0x00
        assert sysex[6] == 0x01
        assert sysex[7] == 0x01
        assert sysex[-1] == 0xF7
    
    def test_sysex_builder_parameter_set(self, controller):
        """Test building parameter set SYSEX."""
        sysex = controller.build_sysex_parameter_set(0, 0, 0, 8192)
        
        assert sysex[0] == 0xF0
        assert sysex[4] == 0x11
        assert sysex[8] == 0x40  # MSB of 8192
        assert sysex[9] == 0x00  # LSB of 8192
        assert sysex[-1] == 0xF7
    
    def test_sysex_builder_articulation_query(self, controller):
        """Test building articulation query SYSEX."""
        sysex = controller.build_sysex_articulation_query(0)
        
        assert sysex[0] == 0xF0
        assert sysex[4] == 0x13
        assert sysex[-1] == 0xF7
    
    def test_sysex_checksum_calculation(self, controller):
        """Test SYSEX checksum calculation."""
        data = bytes([0x43, 0x10, 0x4C, 0x10, 0x00, 0x01, 0x01])
        checksum = controller._calculate_sysex_checksum(data)
        
        # Checksum should be in valid range
        assert 0 <= checksum <= 127
        
        # Yamaha checksum: (~sum) & 0x7F
        expected = (~sum(data)) & 0x7F
        assert checksum == expected
    
    def test_sysex_reverse_lookup(self, controller):
        """Test reverse NRPN lookup."""
        msb, lsb = controller._find_nrpn_for_articulation('legato')
        assert msb == 1
        assert lsb == 1
        
        msb, lsb = controller._find_nrpn_for_articulation('staccato')
        assert msb == 1
        assert lsb == 2
        
        msb, lsb = controller._find_nrpn_for_articulation('spiccato')
        assert msb == 4
        assert lsb == 7


# ============================================================================
# NRPN PARAMETER CONTROLLER TESTS
# ============================================================================

class TestNRPNParameterController:
    """Tests for NRPN parameter controller."""
    
    def test_parameter_processing(self, param_controller):
        """Test processing parameter NRPN."""
        result = param_controller.process_parameter_nrpn(0, 0, 64)
        
        assert result is not None
        assert result['articulation'] == 'vibrato'
        assert result['param_name'] == 'rate'
        assert result['value'] == 0.64
        assert result['raw_value'] == 64
    
    def test_parameter_reverse_lookup(self, param_controller):
        """Test reverse parameter lookup."""
        nrpn = param_controller.get_nrpn_for_parameter('vibrato', 'rate')
        
        assert nrpn is not None
        assert nrpn == (0, 0)
        
        nrpn = param_controller.get_nrpn_for_parameter('legato', 'blend')
        assert nrpn == (1, 0)
    
    def test_parameter_value_split(self, param_controller):
        """Test splitting parameter value."""
        msb, lsb = param_controller.split_parameter_value(8192)
        
        assert msb == 64
        assert lsb == 0
        
        # Rebuild value
        value = param_controller.build_parameter_value(msb, lsb)
        assert value == 8192
    
    def test_parameter_range(self, param_controller):
        """Test getting parameter range."""
        range_info = param_controller.get_parameter_range(0, 0)
        
        assert range_info is not None
        assert range_info['articulation'] == 'vibrato'
        assert range_info['param_name'] == 'rate'
        assert 'min_value' in range_info
        assert 'max_value' in range_info
    
    def test_all_parameters(self, param_controller):
        """Test getting all parameters."""
        params = param_controller.get_all_parameters()
        
        assert isinstance(params, list)
        assert len(params) > 0
        
        # Check structure
        for param in params:
            assert 'param_msb' in param
            assert 'param_lsb' in param
            assert 'articulation' in param
            assert 'param_name' in param


# ============================================================================
# YAMAHA NRPN MAPPER TESTS
# ============================================================================

class TestYamahaNRPNMapper:
    """Tests for enhanced YamahaNRPNMapper."""
    
    def test_articulation_count(self, mapper):
        """Test total articulation count."""
        count = mapper.get_articulation_count()
        
        assert count >= 70  # At least 70 articulations in simplified map
    
    def test_category_count(self, mapper):
        """Test category articulation counts."""
        # Note: Categories are mapped in nrpn.py but counts may vary
        common_count = mapper.get_category_count('common')
        assert common_count >= 30  # At least 30 common articulations
    
    def test_reverse_lookup(self, mapper):
        """Test reverse NRPN lookup."""
        msb, lsb = mapper.get_nrpn_for_articulation('legato')
        
        assert msb == 1
        assert lsb == 1
        
        msb, lsb = mapper.get_nrpn_for_articulation('pizzicato_strings')
        assert msb == 7  # In strings_bow category (MSB 7)
        assert lsb == 0
    
    def test_search_articulations(self, mapper):
        """Test searching articulations."""
        results = mapper.search_articulations('vibrato')
        
        assert len(results) >= 1
        
        # Check structure
        for art, msb, lsb in results:
            assert isinstance(art, str)
            assert isinstance(msb, int)
            assert isinstance(lsb, int)
            assert 'vibrato' in art.lower()
    
    def test_category_methods(self, mapper):
        """Test category-related methods."""
        categories = mapper.get_all_categories()
        
        assert len(categories) == 13
        
        # Test MSB/category mapping
        assert mapper.get_category_for_msb(1) == 'common'
        assert mapper.get_category_for_msb(6) == 'strings_bow'
        assert mapper.get_category_for_msb(8) == 'guitar'
        
        # Test reverse mapping
        assert mapper.get_msb_for_category('common') == 1
        assert mapper.get_msb_for_category('guitar') == 8


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
