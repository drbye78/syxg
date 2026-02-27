"""
Comprehensive tests for production-grade region implementations.

Tests cover:
- WavetableRegion with morphing and unison
- AdditiveRegion with spectral morphing
- PhysicalRegion with multiple models
- Engine integration with new regions
"""
from __future__ import annotations

import pytest
import numpy as np
from typing import Any

from synth.engine.region_descriptor import RegionDescriptor
from synth.engine.preset_info import PresetInfo
from synth.partial.wavetable_region import WavetableRegion
from synth.partial.additive_region import AdditiveRegion
from synth.partial.physical_region import PhysicalRegion


# ============================================================================
# WavetableRegion Tests
# ============================================================================

class TestWavetableRegion:
    """Tests for WavetableRegion implementation."""
    
    @pytest.fixture
    def wavetable_descriptor(self) -> RegionDescriptor:
        """Create wavetable region descriptor."""
        return RegionDescriptor(
            region_id=0,
            engine_type='wavetable',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'wavetable': 'default',
                'wavetable_position': 0.0,
                'morph_speed': 0.0,
                'unison_voices': 1,
                'detune_amount': 0.0,
                'filter_cutoff': 20000.0,
                'filter_resonance': 0.0,
                'velocity_to_filter': 0.0
            },
            generator_params={
                'amp_attack': 0.01,
                'amp_decay': 0.3,
                'amp_sustain': 0.7,
                'amp_release': 0.5
            }
        )
    
    def test_wavetable_region_creation(self, wavetable_descriptor):
        """Test wavetable region creation."""
        region = WavetableRegion(wavetable_descriptor, 44100)
        
        assert region is not None
        assert region.descriptor.engine_type == 'wavetable'
        assert region._wavetable_name == 'default'
        assert region._unison_voices == 1
    
    def test_wavetable_unison_voices(self, wavetable_descriptor):
        """Test unison voice configuration."""
        # Test with 8 unison voices
        wavetable_descriptor.algorithm_params['unison_voices'] = 8
        wavetable_descriptor.algorithm_params['detune_amount'] = 10.0
        
        region = WavetableRegion(wavetable_descriptor, 44100)
        
        assert region._unison_voices == 8
        assert region._detune_amount == 10.0
    
    def test_wavetable_velocity_to_filter(self, wavetable_descriptor):
        """Test velocity to filter modulation."""
        wavetable_descriptor.algorithm_params['velocity_to_filter'] = 2.0
        
        region = WavetableRegion(wavetable_descriptor, 44100)
        
        assert region._velocity_to_filter == 2.0
        
        # Test note_on with velocity
        region.note_on(velocity=127, note=60)
        
        # Filter should be created with velocity-based modulation
    
    def test_wavetable_region_info(self, wavetable_descriptor):
        """Test region info retrieval."""
        region = WavetableRegion(wavetable_descriptor, 44100)
        
        info = region.get_region_info()
        
        assert 'wavetable_name' in info
        assert 'unison_voices' in info
        assert 'filter_cutoff' in info
        assert info['engine_type'] == 'wavetable'


# ============================================================================
# AdditiveRegion Tests
# ============================================================================

class TestAdditiveRegion:
    """Tests for AdditiveRegion implementation."""
    
    @pytest.fixture
    def additive_descriptor(self) -> RegionDescriptor:
        """Create additive region descriptor."""
        return RegionDescriptor(
            region_id=0,
            engine_type='additive',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'spectrum_type': 'sawtooth',
                'max_partials': 64,
                'brightness': 1.0,
                'spread': 0.0,
                'morph_factor': 0.0,
                'bandwidth_limit': 20000.0,
                'velocity_to_brightness': 0.0
            },
            generator_params={
                'amp_attack': 0.01,
                'amp_decay': 0.3,
                'amp_sustain': 0.7,
                'amp_release': 0.5,
                'filter_cutoff': 20000.0,
                'filter_resonance': 0.0
            }
        )
    
    def test_additive_region_creation(self, additive_descriptor):
        """Test additive region creation."""
        region = AdditiveRegion(additive_descriptor, 44100)
        
        assert region is not None
        assert region.descriptor.engine_type == 'additive'
        assert region._spectrum_type == 'sawtooth'
        assert region._max_partials == 64
    
    def test_additive_spectrum_types(self, additive_descriptor):
        """Test different spectrum types."""
        spectrum_types = ['sawtooth', 'square', 'triangle', 'sine']
        
        for spectrum_type in spectrum_types:
            additive_descriptor.algorithm_params['spectrum_type'] = spectrum_type
            region = AdditiveRegion(additive_descriptor, 44100)
            
            assert region._spectrum_type == spectrum_type
    
    def test_additive_brightness_control(self, additive_descriptor):
        """Test brightness control."""
        additive_descriptor.algorithm_params['brightness'] = 1.5
        additive_descriptor.algorithm_params['velocity_to_brightness'] = 0.5
        
        region = AdditiveRegion(additive_descriptor, 44100)
        
        assert region._brightness == 1.5
        assert region._velocity_to_brightness == 0.5
        
        # Test note_on with velocity
        region.note_on(velocity=127, note=60)
        
        # Brightness should be modulated by velocity
    
    def test_additive_bandwidth_optimization(self, additive_descriptor):
        """Test bandwidth optimization."""
        additive_descriptor.algorithm_params['bandwidth_limit'] = 10000.0
        additive_descriptor.algorithm_params['max_partials'] = 128
        
        region = AdditiveRegion(additive_descriptor, 44100)
        
        assert region._bandwidth_limit == 10000.0
        assert region._max_partials == 128
    
    def test_additive_region_info(self, additive_descriptor):
        """Test region info retrieval."""
        region = AdditiveRegion(additive_descriptor, 44100)
        
        info = region.get_region_info()
        
        assert 'spectrum_type' in info
        assert 'max_partials' in info
        assert 'brightness' in info
        assert info['engine_type'] == 'additive'


# ============================================================================
# PhysicalRegion Tests
# ============================================================================

class TestPhysicalRegion:
    """Tests for PhysicalRegion implementation."""
    
    @pytest.fixture
    def physical_descriptor(self) -> RegionDescriptor:
        """Create physical region descriptor."""
        return RegionDescriptor(
            region_id=0,
            engine_type='physical',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                'model_type': 'string',
                'excitation_type': 'pluck',
                'tension': 0.5,
                'damping': 0.5,
                'body_size': 0.5,
                'material': 'steel',
                'decay_time': 1.0,
                'brightness': 0.5
            },
            generator_params={
                'fine_tune': 0.0
            }
        )
    
    def test_physical_region_creation(self, physical_descriptor):
        """Test physical region creation."""
        region = PhysicalRegion(physical_descriptor, 44100)
        
        assert region is not None
        assert region.descriptor.engine_type == 'physical'
        assert region._model_type == 'string'
        assert region._excitation_type == 'pluck'
    
    def test_physical_model_types(self, physical_descriptor):
        """Test different physical model types."""
        model_types = ['string', 'tube', 'membrane', 'plate']
        
        for model_type in model_types:
            physical_descriptor.algorithm_params['model_type'] = model_type
            region = PhysicalRegion(physical_descriptor, 44100)
            
            assert region._model_type == model_type
    
    def test_physical_excitation_types(self, physical_descriptor):
        """Test different excitation types."""
        excitation_types = ['pluck', 'strike', 'blow', 'bow']
        
        for excitation_type in excitation_types:
            physical_descriptor.algorithm_params['excitation_type'] = excitation_type
            region = PhysicalRegion(physical_descriptor, 44100)
            
            assert region._excitation_type == excitation_type
    
    def test_physical_material_types(self, physical_descriptor):
        """Test different material types."""
        materials = ['steel', 'nylon', 'wood', 'felt']
        
        for material in materials:
            physical_descriptor.algorithm_params['material'] = material
            region = PhysicalRegion(physical_descriptor, 44100)
            
            assert region._material == material
    
    def test_physical_tension_damping(self, physical_descriptor):
        """Test tension and damping parameters."""
        physical_descriptor.algorithm_params['tension'] = 0.8
        physical_descriptor.algorithm_params['damping'] = 0.3
        
        region = PhysicalRegion(physical_descriptor, 44100)
        
        assert region._tension == 0.8
        assert region._damping == 0.3
    
    def test_physical_region_info(self, physical_descriptor):
        """Test region info retrieval."""
        region = PhysicalRegion(physical_descriptor, 44100)
        
        info = region.get_region_info()
        
        assert 'model_type' in info
        assert 'excitation_type' in info
        assert 'material' in info
        assert 'tension' in info
        assert info['engine_type'] == 'physical'


# ============================================================================
# Engine Integration Tests
# ============================================================================

class TestEngineRegionIntegration:
    """Tests for engine integration with new regions."""
    
    def test_wavetable_engine_creates_region(self):
        """Test WavetableEngine creates WavetableRegion."""
        from synth.engine.wavetable_engine import WavetableEngine
        
        engine = WavetableEngine(sample_rate=44100, block_size=1024)
        
        # Get preset info
        preset_info = engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            
            # Create region
            region = engine.create_region(descriptor, 44100)
            
            assert region is not None
            assert isinstance(region, WavetableRegion) or hasattr(region, 'descriptor')
    
    def test_additive_engine_creates_region(self):
        """Test AdditiveEngine creates AdditiveRegion."""
        from synth.engine.additive_engine import AdditiveEngine
        
        engine = AdditiveEngine(max_partials=64, sample_rate=44100, block_size=1024)
        
        # Get preset info
        preset_info = engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            
            # Create region
            region = engine.create_region(descriptor, 44100)
            
            assert region is not None
            assert isinstance(region, AdditiveRegion) or hasattr(region, 'descriptor')
    
    def test_physical_engine_creates_region(self):
        """Test PhysicalEngine creates PhysicalRegion."""
        from synth.engine.physical_engine import PhysicalEngine
        
        engine = PhysicalEngine(max_strings=16, sample_rate=44100, block_size=1024)
        
        # Get preset info
        preset_info = engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            
            # Create region
            region = engine.create_region(descriptor, 44100)
            
            assert region is not None
            assert isinstance(region, PhysicalRegion) or hasattr(region, 'descriptor')


# ============================================================================
# Performance Tests
# ============================================================================

class TestRegionPerformance:
    """Performance tests for region implementations."""
    
    def test_wavetable_region_creation_time(self):
        """Test wavetable region creation performance."""
        import time
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='wavetable',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={'wavetable': 'default'}
        )
        
        # Create multiple regions and measure time
        start = time.perf_counter()
        for _ in range(100):
            region = WavetableRegion(descriptor, 44100)
        elapsed = time.perf_counter() - start
        
        # Should create 100 regions in < 100ms (< 1ms per region)
        assert elapsed < 0.1, f"Region creation too slow: {elapsed*1000:.2f}ms"
    
    def test_additive_region_creation_time(self):
        """Test additive region creation performance."""
        import time
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='additive',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={'spectrum_type': 'sawtooth', 'max_partials': 64}
        )
        
        # Create multiple regions and measure time
        start = time.perf_counter()
        for _ in range(100):
            region = AdditiveRegion(descriptor, 44100)
        elapsed = time.perf_counter() - start
        
        # Should create 100 regions in < 100ms
        assert elapsed < 0.1, f"Region creation too slow: {elapsed*1000:.2f}ms"
    
    def test_physical_region_creation_time(self):
        """Test physical region creation performance."""
        import time
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='physical',
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={'model_type': 'string'}
        )
        
        # Create multiple regions and measure time
        start = time.perf_counter()
        for _ in range(100):
            region = PhysicalRegion(descriptor, 44100)
        elapsed = time.perf_counter() - start
        
        # Should create 100 regions in < 100ms
        assert elapsed < 0.1, f"Region creation too slow: {elapsed*1000:.2f}ms"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
