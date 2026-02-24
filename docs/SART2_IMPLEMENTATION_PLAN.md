# S.Art2 Integration Implementation Plan
## Comprehensive Plan for Modern XG Synth

**Document Version:** 1.0  
**Date:** 2026-02-22  
**Status:** Ready for Implementation  
**Breaking Changes:** YES - No backward compatibility

---

## Executive Summary

This plan implements **full S.Art2 articulation technology** across **ALL synthesis engines** in Modern XG Synth. The integration uses a **wrapper architecture** where `SArt2Region` wraps any `IRegion` implementation to provide expressive articulation control.

**Key Decisions:**
- ✅ **No backward compatibility** - Clean break for better architecture
- ✅ **S.Art2 by default** - All regions are S.Art2-enabled
- ✅ **60% code reuse** from existing `sart/` package
- ✅ **5-week timeline** for full implementation

---

## Phase 1: Core S.Art2 Infrastructure (Week 1)

### **1.1 Create SArt2Region Wrapper**

**File:** `synth/xg/sart/sart2_region.py` (NEW - 350 lines)

```python
"""
S.Art2 Region Wrapper - Universal articulation layer for all synthesis engines.

This module provides the core S.Art2 integration by wrapping any IRegion
implementation with articulation control capabilities.
"""

from typing import Dict, Any, Optional, List
import numpy as np

from ...partial.region import IRegion, RegionState
from .articulation_controller import ArticulationController
from .nrpn import YamahaNRPNMapper


class SArt2Region(IRegion):
    """
    S.Art2 wrapper that adds articulation control to ANY base region.
    
    This is the PRIMARY integration class. It wraps any IRegion implementation
    (SF2Region, FMRegion, AdditiveRegion, etc.) and adds:
    
    - 35+ articulation types
    - NRPN/SYSEX real-time control
    - Expression parameter mapping
    - Instrument-specific techniques
    
    Architecture:
        SArt2Region
        ├── ArticulationController (from sart/)
        ├── base_region (any IRegion)
        └── articulation processing pipeline
    
    Usage:
        # Wrap any region with S.Art2
        base_region = SF2Region(descriptor, sample_rate, manager)
        sart2_region = SArt2Region(base_region)
        
        # Set articulation via method
        sart2_region.set_articulation('legato')
        
        # Or via NRPN (real-time MIDI)
        sart2_region.process_nrpn(msb=1, lsb=1)  # Sets 'legato'
        
        # Generate samples with articulation
        samples = sart2_region.generate_samples(1024, modulation)
    """
    
    __slots__ = [
        'base_region', 'articulation_controller', '_sample_modifier',
        '_articulation_cache', '_param_transition_buffer'
    ]
    
    def __init__(
        self, 
        base_region: IRegion, 
        sample_rate: int = 44100,
        enable_sample_modification: bool = True
    ):
        """
        Initialize S.Art2 wrapper.
        
        Args:
            base_region: Any IRegion implementation to wrap
            sample_rate: Audio sample rate in Hz
            enable_sample_modification: Enable articulation sample processing
        """
        super().__init__(base_region.descriptor, sample_rate)
        
        self.base_region = base_region
        self.articulation_controller = ArticulationController()
        self._sample_modifier = None
        self._articulation_cache = {}
        self._param_transition_buffer = {}
        
        if enable_sample_modification:
            from .sf2_wavetable_adapter import SF2SampleModifier
            self._sample_modifier = SF2SampleModifier(sample_rate)
    
    # ========== ARTICULATION CONTROL ==========
    
    def set_articulation(self, articulation: str) -> None:
        """
        Set current articulation.
        
        Args:
            articulation: Articulation name (e.g., 'legato', 'staccato')
        """
        self.articulation_controller.set_articulation(articulation)
        self._invalidate_cache()
    
    def get_articulation(self) -> str:
        """Get current articulation name."""
        return self.articulation_controller.get_articulation()
    
    def process_nrpn(self, msb: int, lsb: int) -> str:
        """
        Process NRPN message to set articulation.
        
        Args:
            msb: NRPN MSB value
            lsb: NRPN LSB value
        
        Returns:
            Articulation name that was set
        """
        articulation = self.articulation_controller.process_nrpn(msb, lsb)
        self._invalidate_cache()
        return articulation
    
    def process_sysex(self, sysex_data: bytes) -> Dict[str, Any]:
        """
        Process SYSEX message for articulation control.
        
        Args:
            sysex_data: SYSEX byte data
        
        Returns:
            SYSEX parsing result
        """
        result = self.articulation_controller.parse_sysex(sysex_data)
        
        if result['command'] == 'set_articulation':
            self.set_articulation(result['articulation'])
        
        return result
    
    def get_available_articulations(self) -> List[str]:
        """Get list of all available articulations."""
        return self.articulation_controller.get_available_articulations()
    
    def get_articulation_params(self) -> Dict[str, Any]:
        """Get parameters for current articulation."""
        return self.articulation_controller.get_articulation_params()
    
    def set_articulation_param(self, param: str, value: Any) -> None:
        """
        Set parameter for current articulation.
        
        Args:
            param: Parameter name
            value: Parameter value
        """
        self.articulation_controller.set_articulation_param(param, value)
        self._invalidate_cache()
    
    # ========== IRegion INTERFACE ==========
    
    def initialize(self) -> bool:
        """Initialize base region and S.Art2 processing."""
        return self.base_region.initialize()
    
    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on with articulation processing.
        
        Args:
            velocity: MIDI velocity
            note: MIDI note number
        
        Returns:
            True if note was triggered
        """
        result = self.base_region.note_on(velocity, note)
        
        if result:
            # Apply articulation-specific note-on processing
            self._apply_note_on_articulation(velocity, note)
        
        return result
    
    def note_off(self) -> None:
        """Trigger note-off with articulation release."""
        self.base_region.note_off()
        self._apply_note_off_articulation()
    
    def generate_samples(
        self, 
        block_size: int, 
        modulation: Dict[str, float]
    ) -> np.ndarray:
        """
        Generate samples with S.Art2 articulation processing.
        
        This is the CORE method where articulation affects synthesis:
        
        1. Generate samples from base region
        2. Apply articulation-specific sample modification
        3. Apply articulation parameters to synthesis
        4. Return processed samples
        
        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values
        
        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        # Step 1: Generate from base region
        samples = self.base_region.generate_samples(block_size, modulation)
        
        # Step 2: Get current articulation
        articulation = self.get_articulation()
        params = self.get_articulation_params()
        
        # Step 3: Apply articulation processing
        if articulation != 'normal' and self._sample_modifier:
            samples = self._sample_modifier.apply_articulation(
                samples, articulation, params
            )
        
        # Step 4: Apply articulation parameters to base region
        self._apply_articulation_params_to_base(params, modulation)
        
        return samples
    
    def is_active(self) -> bool:
        """Check if region is still producing sound."""
        return self.base_region.is_active()
    
    def reset(self) -> None:
        """Reset region and articulation state."""
        self.base_region.reset()
        self.articulation_controller.reset()
        self._invalidate_cache()
    
    def dispose(self) -> None:
        """Dispose of region resources."""
        self.base_region.dispose()
        self._sample_modifier = None
        self._articulation_cache.clear()
        self._param_transition_buffer.clear()
    
    def get_region_info(self) -> Dict[str, Any]:
        """Get region information including articulation state."""
        info = self.base_region.get_region_info()
        info['articulation'] = self.get_articulation()
        info['articulation_params'] = self.get_articulation_params()
        info['sart2_enabled'] = True
        return info
    
    # ========== INTERNAL METHODS ==========
    
    def _invalidate_cache(self) -> None:
        """Invalidate articulation parameter cache."""
        self._articulation_cache.clear()
    
    def _apply_note_on_articulation(self, velocity: int, note: int) -> None:
        """Apply articulation-specific note-on processing."""
        articulation = self.get_articulation()
        params = self.get_articulation_params()
        
        # Examples:
        if articulation == 'staccato':
            # Shorten release time
            self._set_base_param('amp_release', 0.05)
        
        elif articulation == 'legato':
            # Smooth transition
            self._set_base_param('transition_time', 0.05)
        
        elif articulation == 'accented':
            # Higher velocity
            self._set_base_param('velocity_boost', 1.2)
    
    def _apply_note_off_articulation(self) -> None:
        """Apply articulation-specific note-off processing."""
        articulation = self.get_articulation()
        
        if articulation == 'key_off':
            # Add key-off noise
            pass
    
    def _apply_articulation_params_to_base(
        self, 
        params: Dict[str, Any],
        modulation: Dict[str, float]
    ) -> None:
        """Apply articulation parameters to base region synthesis."""
        # Vibrato
        if 'rate' in params and 'depth' in params:
            modulation['vibrato_rate'] = params['rate']
            modulation['vibrato_depth'] = params['depth']
        
        # Trill
        if 'interval' in params and 'rate' in params:
            # Apply trill modulation
            pass
        
        # Crescendo/Diminuendo
        if 'target_level' in params and 'duration' in params:
            # Apply dynamic change
            pass
    
    def _set_base_param(self, param: str, value: Any) -> None:
        """Set parameter on base region."""
        if hasattr(self.base_region, 'update_parameter'):
            self.base_region.update_parameter(param, value)


class SArt2RegionFactory:
    """
    Factory for creating S.Art2-wrapped regions.
    
    This factory automatically wraps any region with SArt2,
    making articulation control universal across all engines.
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
    
    def create_sart2_region(self, base_region: IRegion) -> SArt2Region:
        """
        Wrap a base region with S.Art2 articulation.
        
        Args:
            base_region: Any IRegion implementation
        
        Returns:
            SArt2Region wrapper
        """
        return SArt2Region(base_region, self.sample_rate)
    
    def create_from_descriptor(
        self, 
        descriptor: 'RegionDescriptor',
        engine: 'SynthesisEngine'
    ) -> SArt2Region:
        """
        Create S.Art2 region from descriptor using engine.
        
        Args:
            descriptor: Region descriptor
            engine: Synthesis engine to create base region
        
        Returns:
            SArt2Region wrapper
        """
        # Create base region from engine
        base_region = engine.create_region(descriptor, self.sample_rate)
        
        # Wrap with S.Art2
        return self.create_sart2_region(base_region)
```

---

### **1.2 Update SynthesisEngine Base Class**

**File:** `synth/engine/synthesis_engine.py` (MODIFIED)

```python
# Add S.Art2 configuration
class SynthesisEngine(ABC):
    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        # S.Art2 support - ENABLED BY DEFAULT
        self.sart2_enabled = True
        self.sart2_factory = None  # Set by ModernXGSynthesizer
    
    def create_region(self, descriptor: RegionDescriptor, 
                     sample_rate: int) -> IRegion:
        """
        Create region with S.Art2 wrapper (if enabled).
        
        ALL regions are S.Art2-enabled by default.
        """
        # Create base region (engine-specific)
        base_region = self._create_base_region(descriptor, sample_rate)
        
        # Wrap with S.Art2 if enabled
        if self.sart2_enabled and self.sart2_factory:
            return self.sart2_factory.create_sart2_region(base_region)
        
        return base_region
    
    @abstractmethod
    def _create_base_region(self, descriptor: RegionDescriptor, 
                           sample_rate: int) -> IRegion:
        """Engine-specific base region creation."""
        pass
```

---

### **1.3 Update All Engine Implementations**

**Pattern for ALL engines:**

```python
# synth/engine/sf2_engine.py
class SF2Engine(SynthesisEngine):
    def _create_base_region(self, descriptor: RegionDescriptor, 
                           sample_rate: int) -> IRegion:
        """Create SF2 region (base, without S.Art2)."""
        from ..partial.sf2_region import SF2Region
        return SF2Region(descriptor, sample_rate, self.soundfont_manager)

# synth/engine/fm_engine.py
class FMEngine(SynthesisEngine):
    def _create_base_region(self, descriptor: RegionDescriptor, 
                           sample_rate: int) -> IRegion:
        """Create FM region (base, without S.Art2)."""
        from ..partial.fm_region import FMRegion
        return FMRegion(descriptor, sample_rate)

# Repeat for ALL engines:
# - AdditiveEngine
# - WavetableEngine
# - PhysicalEngine
# - GranularEngine
# - SpectralEngine
# - FDSPEngine
# - ANEngine
# - ConvolutionReverbEngine
# - AdvancedPhysicalEngine
```

---

## **Phase 2: ModernXGSynthesizer Integration (Week 2)**

### **2.1 Add S.Art2 to ModernXGSynthesizer**

**File:** `synth/engine/modern_xg_synthesizer.py` (MODIFIED)

```python
class ModernXGSynthesizer:
    def __init__(self, sample_rate: int = 44100, max_channels: int = 32, ...):
        # ... existing init ...
        
        # S.Art2 Integration
        self._init_sart2()
    
    def _init_sart2(self) -> None:
        """Initialize S.Art2 articulation system."""
        from ..xg.sart import YamahaNRPNMapper, ArticulationController
        from ..xg.sart.sart2_region import SArt2RegionFactory
        
        # NRPN mapper for articulation control
        self.nrpn_mapper = YamahaNRPNMapper()
        
        # Global articulation controller
        self.articulation_manager = ArticulationController()
        
        # S.Art2 factory for all engines
        self.sart2_factory = SArt2RegionFactory(self.sample_rate)
        
        # Configure all engines with S.Art2
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if engine:
                engine.sart2_enabled = True
                engine.sart2_factory = self.sart2_factory
    
    # ========== NRPN PROCESSING ==========
    
    def process_nrpn(self, channel: int, msb: int, lsb: int, value: int) -> None:
        """
        Process NRPN message for S.Art2 articulation control.
        
        Args:
            channel: MIDI channel number
            msb: NRPN MSB value
            lsb: NRPN LSB value
            value: NRPN data value
        """
        # Get articulation from NRPN
        articulation = self.nrpn_mapper.get_articulation(msb, lsb)
        
        # Set articulation for channel
        self.channels[channel].set_articulation(articulation)
        
        # Log for debugging
        logger.debug(f"Channel {channel}: NRPN ({msb}, {lsb}) → {articulation}")
    
    # ========== SYSEX PROCESSING ==========
    
    def process_sysex(self, data: bytes) -> None:
        """
        Process SYSEX message for S.Art2 articulation.
        
        Args:
            data: SYSEX byte data
        """
        from ..xg.sart import ArticulationController
        
        controller = ArticulationController()
        result = controller.parse_sysex(data)
        
        if result['command'] == 'set_articulation':
            # Set articulation from SYSEX
            articulation = result['articulation']
            # Apply to appropriate channel/voice
            pass
    
    # ========== CHANNEL ARTICULATION ==========
    
    def set_channel_articulation(self, channel: int, articulation: str) -> None:
        """
        Set articulation for a specific channel.
        
        Args:
            channel: MIDI channel number
            articulation: Articulation name
        """
        if 0 <= channel < len(self.channels):
            self.channels[channel].set_articulation(articulation)
    
    def get_channel_articulation(self, channel: int) -> str:
        """Get current articulation for channel."""
        if 0 <= channel < len(self.channels):
            return self.channels[channel].get_articulation()
        return 'normal'
```

---

### **2.2 Update Channel Class**

**File:** `synth/channel/channel.py` (MODIFIED)

```python
class Channel:
    def __init__(self, channel_number: int, voice_factory, sample_rate, synth):
        # ... existing init ...
        
        # S.Art2 articulation
        self._articulation = 'normal'
        self._articulation_params = {}
    
    def set_articulation(self, articulation: str) -> None:
        """
        Set articulation for this channel.
        
        Args:
            articulation: Articulation name
        """
        self._articulation = articulation
        
        # Propagate to current voice
        if self.current_voice:
            self.current_voice.set_articulation(articulation)
    
    def get_articulation(self) -> str:
        """Get current articulation."""
        return self._articulation
    
    def load_program(self, program: int, bank_msb: int = 0, bank_lsb: int = 0):
        """Load program with S.Art2 support."""
        # ... existing program loading ...
        
        # Reset articulation on program change
        self.set_articulation('normal')
```

---

### **2.3 Update Voice Class**

**File:** `synth/voice/voice.py` (MODIFIED)

```python
class Voice:
    def __init__(self, preset_info, engine, channel, sample_rate):
        # ... existing init ...
        
        # S.Art2 articulation
        self._articulation = 'normal'
    
    def set_articulation(self, articulation: str) -> None:
        """Set articulation for this voice."""
        self._articulation = articulation
        
        # Propagate to all active regions
        for region in self._active_instances:
            if hasattr(region, 'set_articulation'):
                region.set_articulation(articulation)
    
    def get_articulation(self) -> str:
        """Get current articulation."""
        return self._articulation
    
    def get_regions_for_note(self, note: int, velocity: int) -> List[IRegion]:
        """Get regions with articulation applied."""
        regions = super().get_regions_for_note(note, velocity)
        
        # Set articulation on all regions
        for region in regions:
            if hasattr(region, 'set_articulation'):
                region.set_articulation(self._articulation)
        
        return regions
```

---

## **Phase 3: Documentation (Week 3)**

### **3.1 API Documentation**

**File:** `docs/SART2_API.md` (NEW)

```markdown
# S.Art2 API Reference

## SArt2Region

### Constructor
```python
SArt2Region(base_region: IRegion, sample_rate: int = 44100)
```

### Methods
- `set_articulation(articulation: str)` - Set articulation
- `get_articulation() -> str` - Get current articulation
- `process_nrpn(msb: int, lsb: int) -> str` - Process NRPN
- `generate_samples(block_size, modulation) -> np.ndarray` - Generate audio

## Available Articulations

### Common
- normal, legato, staccato, bend, vibrato, breath, glissando

### Wind
- growl, flutter, tongue_slap, smear, flip, scoop, rip

### Strings
- pizzicato, harmonics, sul_ponticello, bow_up, bow_down, col_legno

### Guitar
- hammer_on, pull_off, harmonics, palm_mute, tap, slide

### Dynamics
- ppp, pp, p, mp, mf, f, ff, fff, crescendo, diminuendo
```

### **3.2 User Guide**

**File:** `docs/SART2_USER_GUIDE.md` (NEW)

```markdown
# S.Art2 User Guide

## Quick Start

```python
from synth import ModernXGSynthesizer

# Create synthesizer (S.Art2 enabled by default)
synth = ModernXGSynthesizer()

# Load soundfont
synth.load_soundfont('piano.sf2')

# Set articulation via method
synth.set_channel_articulation(0, 'legato')

# Or via NRPN (MIDI)
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)  # legato

# Play notes with articulation
synth.note_on(channel=0, note=60, velocity=100)
```

## NRPN Reference

| MSB | LSB | Articulation |
|-----|-----|--------------|
| 1 | 0 | normal |
| 1 | 1 | legato |
| 1 | 2 | staccato |
| 1 | 7 | growl |
| 1 | 8 | flutter |
```

### **3.3 Migration Guide**

**File:** `docs/SART2_MIGRATION.md` (NEW)

```markdown
# S.Art2 Migration Guide

## Breaking Changes

### Before (Old API)
```python
# Old: No S.Art2
region = SF2Region(descriptor, sample_rate, manager)
```

### After (New API)
```python
# New: S.Art2 enabled by default
region = SArt2Region(SF2Region(descriptor, sample_rate, manager))
# OR simply use engine.create_region() which wraps automatically
```

## NRPN Support

S.Art2 adds NRPN support for real-time articulation control:

```python
# MIDI NRPN messages now control articulation
# CC 98 (NRPN LSB), CC 99 (NRPN MSB)
```
```

---

## **Phase 4: Test Suite (Week 4)**

### **4.1 Unit Tests**

**File:** `tests/test_sart2_region.py` (NEW - 400 lines)

```python
"""
Unit tests for SArt2Region wrapper.
"""

import pytest
import numpy as np

from synth.xg.sart.sart2_region import SArt2Region, SArt2RegionFactory
from synth.partial.sf2_region import SF2Region
from synth.engine.region_descriptor import RegionDescriptor


class TestSArt2Region:
    """Tests for SArt2Region wrapper."""
    
    @pytest.fixture
    def base_region(self):
        """Create mock base region."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='mock',
            key_range=(0, 127),
            velocity_range=(0, 127)
        )
        return MockRegion(descriptor, 44100)
    
    def test_sart2_wraps_base_region(self, base_region):
        """Test SArt2Region properly wraps base region."""
        sart2 = SArt2Region(base_region)
        
        assert sart2.base_region is base_region
        assert sart2.descriptor == base_region.descriptor
    
    def test_sart2_articulation_setting(self, base_region):
        """Test articulation setting."""
        sart2 = SArt2Region(base_region)
        
        sart2.set_articulation('legato')
        assert sart2.get_articulation() == 'legato'
        
        sart2.set_articulation('staccato')
        assert sart2.get_articulation() == 'staccato'
    
    def test_sart2_nrpn_processing(self, base_region):
        """Test NRPN message processing."""
        sart2 = SArt2Region(base_region)
        
        # MSB 1, LSB 1 = legato
        articulation = sart2.process_nrpn(1, 1)
        assert articulation == 'legato'
        assert sart2.get_articulation() == 'legato'
    
    def test_sart2_generate_samples(self, base_region):
        """Test sample generation with articulation."""
        sart2 = SArt2Region(base_region)
        sart2.initialize()
        sart2.note_on(100, 60)
        
        samples = sart2.generate_samples(1024, {})
        
        assert isinstance(samples, np.ndarray)
        assert len(samples) == 1024 * 2
        assert samples.dtype == np.float32
    
    def test_sart2_available_articulations(self, base_region):
        """Test getting available articulations."""
        sart2 = SArt2Region(base_region)
        
        articulations = sart2.get_available_articulations()
        
        assert isinstance(articulations, list)
        assert len(articulations) > 0
        assert 'normal' in articulations
        assert 'legato' in articulations
    
    def test_sart2_params(self, base_region):
        """Test articulation parameters."""
        sart2 = SArt2Region(base_region)
        sart2.set_articulation('vibrato')
        
        params = sart2.get_articulation_params()
        
        assert isinstance(params, dict)
        assert 'rate' in params or 'depth' in params
    
    def test_sart2_reset(self, base_region):
        """Test reset clears articulation."""
        sart2 = SArt2Region(base_region)
        sart2.set_articulation('legato')
        sart2.reset()
        
        assert sart2.get_articulation() == 'normal'
    
    def test_sart2_dispose(self, base_region):
        """Test dispose cleans up resources."""
        sart2 = SArt2Region(base_region)
        sart2.dispose()
        
        assert sart2._sample_modifier is None


class TestSArt2RegionFactory:
    """Tests for SArt2RegionFactory."""
    
    def test_factory_creates_sart2_region(self):
        """Test factory creates S.Art2-wrapped regions."""
        factory = SArt2RegionFactory(44100)
        base_region = MockRegion(descriptor, 44100)
        
        sart2_region = factory.create_sart2_region(base_region)
        
        assert isinstance(sart2_region, SArt2Region)
        assert sart2_region.base_region is base_region


class MockRegion(IRegion):
    """Mock region for testing."""
    
    def _load_sample_data(self):
        return None
    
    def _create_partial(self):
        return MockPartial()
    
    def _init_envelopes(self):
        pass
    
    def _init_filters(self):
        pass
    
    def generate_samples(self, block_size, modulation):
        return np.zeros(block_size * 2, dtype=np.float32)


class MockPartial:
    """Mock partial for testing."""
    
    def note_on(self, velocity, note):
        pass
    
    def note_off(self):
        pass
    
    def is_active(self):
        return False
    
    def generate_samples(self, block_size, modulation):
        return np.zeros(block_size * 2, dtype=np.float32)
```

### **4.2 Integration Tests**

**File:** `tests/test_sart2_integration.py` (NEW - 500 lines)

```python
"""
Integration tests for S.Art2 with all synthesis engines.
"""

import pytest
import numpy as np

from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer


class TestSArt2Integration:
    """Integration tests for S.Art2 across all engines."""
    
    @pytest.fixture
    def synth(self):
        """Create synthesizer with S.Art2 enabled."""
        synth = ModernXGSynthesizer(sample_rate=44100)
        return synth
    
    def test_sart2_enabled_by_default(self, synth):
        """Test S.Art2 is enabled by default."""
        for engine_type in synth.engine_registry.get_priority_order():
            engine = synth.engine_registry.get_engine(engine_type)
            if engine:
                assert engine.sart2_enabled == True
                assert engine.sart2_factory is not None
    
    def test_sart2_nrpn_through_synth(self, synth):
        """Test NRPN processing through full synth."""
        # Process NRPN for legato
        synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)
        
        # Verify articulation is set
        articulation = synth.get_channel_articulation(0)
        assert articulation == 'legato'
    
    def test_sart2_with_sf2_engine(self, synth):
        """Test S.Art2 works with SF2 engine."""
        # SF2 engine should create SArt2Region
        engine = synth.engine_registry.get_engine('sf2')
        
        if engine:
            preset_info = engine.get_preset_info(0, 0)
            if preset_info:
                regions = engine.get_all_region_descriptors(0, 0)
                if regions:
                    region = engine.create_region(regions[0], 44100)
                    
                    # Should be SArt2Region
                    from synth.xg.sart.sart2_region import SArt2Region
                    assert isinstance(region, SArt2Region)
    
    def test_sart2_with_fm_engine(self, synth):
        """Test S.Art2 works with FM engine."""
        engine = synth.engine_registry.get_engine('fm')
        
        if engine:
            region = engine.create_region(descriptor, 44100)
            
            from synth.xg.sart.sart2_region import SArt2Region
            assert isinstance(region, SArt2Region)
    
    def test_sart2_channel_articulation(self, synth):
        """Test channel articulation control."""
        synth.set_channel_articulation(0, 'staccato')
        
        articulation = synth.get_channel_articulation(0)
        assert articulation == 'staccato'
    
    def test_sart2_note_on_with_articulation(self, synth):
        """Test note-on with articulation."""
        synth.set_channel_articulation(0, 'legato')
        synth.note_on(channel=0, note=60, velocity=100)
        
        # Verify voice has articulation
        channel = synth.channels[0]
        if channel.current_voice:
            assert channel.current_voice.get_articulation() == 'legato'
    
    def test_sart2_articulation_change(self, synth):
        """Test articulation change during playback."""
        synth.note_on(channel=0, note=60, velocity=100)
        synth.set_channel_articulation(0, 'staccato')
        
        # Articulation should change
        articulation = synth.get_channel_articulation(0)
        assert articulation == 'staccato'
```

### **4.3 Performance Tests**

**File:** `tests/test_sart2_performance.py` (NEW - 200 lines)

```python
"""
Performance tests for S.Art2 overhead.
"""

import pytest
import time
import numpy as np


class TestSArt2Performance:
    """Performance tests for S.Art2."""
    
    def test_sart2_overhead(self):
        """Test S.Art2 adds <5% overhead."""
        # Generate samples without S.Art2
        start = time.perf_counter()
        for _ in range(100):
            samples_base = base_region.generate_samples(1024, {})
        base_time = time.perf_counter() - start
        
        # Generate samples with S.Art2
        start = time.perf_counter()
        for _ in range(100):
            samples_sart2 = sart2_region.generate_samples(1024, {})
        sart2_time = time.perf_counter() - start
        
        # Overhead should be <5%
        overhead = (sart2_time - base_time) / base_time
        assert overhead < 0.05, f"S.Art2 overhead too high: {overhead*100:.1f}%"
    
    def test_sart2_latency(self):
        """Test S.Art2 adds minimal latency."""
        # Measure latency
        start = time.perf_counter()
        samples = sart2_region.generate_samples(1024, {})
        latency = time.perf_counter() - start
        
        # Should be <1ms for 1024 samples at 44100Hz
        assert latency < 0.001, f"Latency too high: {latency*1000:.2f}ms"
```

---

## **Phase 5: Final Integration & Testing (Week 5)**

### **5.1 Full System Tests**

**File:** `tests/test_sart2_full_system.py` (NEW)

```python
"""
Full system tests for S.Art2 integration.
"""

import pytest
import numpy as np
from pathlib import Path


class TestSArt2FullSystem:
    """Full system integration tests."""
    
    @pytest.fixture
    def synth_with_soundfont(self):
        """Create synth with test soundfont."""
        synth = ModernXGSynthesizer()
        
        # Load test soundfont
        sf2_path = Path(__file__).parent.parent / 'sine_test.sf2'
        if sf2_path.exists():
            synth.load_soundfont(str(sf2_path))
        
        return synth
    
    def test_full_sart2_workflow(self, synth_with_soundfont):
        """Test complete S.Art2 workflow."""
        synth = synth_with_soundfont
        
        # 1. Set articulation via NRPN
        synth.process_nrpn(0, 1, 1, 0)  # legato
        
        # 2. Verify articulation
        assert synth.get_channel_articulation(0) == 'legato'
        
        # 3. Play note
        synth.note_on(0, 60, 100)
        
        # 4. Generate audio
        samples = synth.generate_samples(1024)
        
        # 5. Verify audio generated
        assert isinstance(samples, np.ndarray)
        assert len(samples) == 1024 * 2
        
        # 6. Change articulation
        synth.set_channel_articulation(0, 'staccato')
        
        # 7. Verify change
        assert synth.get_channel_articulation(0) == 'staccato'
```

---

## **Implementation Timeline**

| Week | Phase | Deliverables |
|------|-------|--------------|
| **1** | Core Infrastructure | SArt2Region, factory, engine updates |
| **2** | ModernXGSynthesizer | NRPN, SYSEX, Channel, Voice integration |
| **3** | Documentation | API docs, user guide, migration guide |
| **4** | Test Suite | Unit, integration, performance tests |
| **5** | Final Integration | Full system tests, bug fixes |

---

## **Files Created/Modified**

### **Created (12 files)**
1. `synth/xg/sart/sart2_region.py` (350 lines)
2. `docs/SART2_API.md` (200 lines)
3. `docs/SART2_USER_GUIDE.md` (300 lines)
4. `docs/SART2_MIGRATION.md` (150 lines)
5. `tests/test_sart2_region.py` (400 lines)
6. `tests/test_sart2_integration.py` (500 lines)
7. `tests/test_sart2_performance.py` (200 lines)
8. `tests/test_sart2_full_system.py` (250 lines)

### **Modified (15 files)**
1. `synth/engine/synthesis_engine.py`
2. `synth/engine/sf2_engine.py`
3. `synth/engine/fm_engine.py`
4. `synth/engine/additive_engine.py`
5. `synth/engine/wavetable_engine.py`
6. `synth/engine/physical_engine.py`
7. `synth/engine/granular_engine.py`
8. `synth/engine/spectral_engine.py`
9. `synth/engine/fdsp_engine.py`
10. `synth/engine/an_engine.py`
11. `synth/engine/convolution_reverb_engine.py`
12. `synth/engine/advanced_physical_engine.py`
13. `synth/engine/modern_xg_synthesizer.py`
14. `synth/channel/channel.py`
15. `synth/voice/voice.py`

---

## **Success Criteria**

| Criteria | Target | Measurement |
|----------|--------|-------------|
| **Code Reuse** | >60% | Lines from `sart/` package |
| **Engine Coverage** | 100% | All 13 engines support S.Art2 |
| **NRPN Support** | Full | All 70+ NRPN mappings |
| **Performance** | <5% overhead | Benchmark comparison |
| **Test Coverage** | >85% | Unit + integration tests |
| **Documentation** | Complete | API + user + migration guides |

---

**Implementation Plan Complete!** 🎉
