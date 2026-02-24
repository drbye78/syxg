# S.Art2 Integration Strategy for Modern XG Synth

**Document Version:** 1.0  
**Date:** 2026-02-22  
**Goal:** Integrate S.Art2 articulation technology across ALL synthesis engines

---

## Executive Summary

**Key Insight:** S.Art2 is an **articulation control layer** that is **synthesis-method agnostic**. It can wrap ANY synthesis engine (SF2, SFZ, FM, Additive, Wavetable, Physical, etc.) to provide expressive articulation control.

**Integration Approach:** Create a `SArt2Region` wrapper that implements `IRegion` interface and wraps any base region, applying articulation processing on top.

---

## 1. Current Architecture Analysis

### **1.1 Modern XG Synth Architecture**

```
ModernXGSynthesizer
├── EngineRegistry
│   ├── SF2Engine
│   ├── FMEngine
│   ├── AdditiveEngine
│   ├── WavetableEngine
│   ├── PhysicalEngine
│   ├── GranularEngine
│   └── SpectralEngine
├── VoiceFactory
│   └── creates Voice objects
├── Voice
│   └── contains IRegion instances
└── Channel
    └── manages Voice instances
```

### **1.2 S.Art2 Package Architecture**

```
synth/xg/sart/
├── ArticulationController    # NRPN/SYSEX → articulation mapping
├── YamahaNRPNMapper          # NRPN MSB/LSB → articulation name
├── VoiceManager              # Polyphonic voice management
├── VoiceState                # Per-voice state
├── effects/                  # Reverb, Delay
├── wavetable/                # Wavetable synthesis
└── sf2_wavetable_adapter/    # SF2 integration
```

---

## 2. Integration Architecture

### **2.1 High-Level Design**

```
┌─────────────────────────────────────────────────────────┐
│              ModernXGSynthesizer                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │          S.Art2 Integration Layer                │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  SArt2Region (IRegion wrapper)          │    │    │
│  │  │  ┌─────────────────────────────────┐    │    │    │
│  │  │  │  ArticulationController         │    │    │    │
│  │  │  │  • NRPN processing              │    │    │    │
│  │  │  │  • Articulation parameters      │    │    │    │
│  │  │  │  • Expression mapping           │    │    │    │
│  │  │  └──────────────┬──────────────────┘    │    │    │
│  │  │                 │                        │    │    │
│  │  │  ┌──────────────▼──────────────────┐    │    │    │
│  │  │  │  BaseRegion (any IRegion)       │    │    │    │
│  │  │  │  • SF2Region                    │    │    │    │
│  │  │  │  • FMRegion                     │    │    │    │
│  │  │  │  • AdditiveRegion               │    │    │    │
│  │  │  │  • WavetableRegion              │    │    │    │
│  │  │  │  • PhysicalRegion               │    │    │    │
│  │  │  │  • etc.                         │    │    │    │
│  │  │  └─────────────────────────────────┘    │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### **2.2 Key Integration Points**

| Component | Integration Point | Reuse from sart/ |
|-----------|------------------|------------------|
| **ArticulationController** | Wrap base region | ✅ 100% reuse |
| **YamahaNRPNMapper** | NRPN processing | ✅ 100% reuse |
| **VoiceState** | Extend existing Voice | ⚠️ Merge with Voice |
| **Effects** | Integrate with existing effects | ⚠️ Merge or replace |
| **Wavetable** | Use as additional engine | ✅ Can be separate |
| **SF2 Adapter** | Use existing SF2 integration | ❌ Use new SF2Region |

---

## 3. Implementation Plan

### **Phase 1: Core Integration (Week 1-2)**

#### **3.1.1 Create SArt2Region Wrapper**

**File:** `synth/xg/sart/sart2_region.py`

```python
"""
S.Art2 Region Wrapper - Applies articulation to any IRegion.
"""

from typing import Dict, Any, Optional
import numpy as np

from ..partial.region import IRegion, RegionState
from .articulation_controller import ArticulationController


class SArt2Region(IRegion):
    """
    S.Art2 wrapper that adds articulation control to any base region.
    
    This is the KEY integration class that makes S.Art2 work with
    ANY synthesis engine (SF2, FM, Additive, Wavetable, etc.).
    
    Usage:
        # Wrap any region with S.Art2 articulation
        base_region = SF2Region(descriptor, sample_rate, soundfont_manager)
        sart2_region = SArt2Region(base_region)
        sart2_region.set_articulation('legato')
    """
    
    def __init__(self, base_region: IRegion, sample_rate: int = 44100):
        """
        Initialize S.Art2 wrapper.
        
        Args:
            base_region: Any IRegion implementation (SF2, FM, etc.)
            sample_rate: Audio sample rate
        """
        super().__init__(base_region.descriptor, sample_rate)
        
        self.base_region = base_region
        self.articulation_controller = ArticulationController()
        
        # Articulation-specific processing
        self._sample_modifier = None  # Optional sample modifier
        
    def set_articulation(self, articulation: str) -> None:
        """Set current articulation."""
        self.articulation_controller.set_articulation(articulation)
    
    def get_articulation(self) -> str:
        """Get current articulation."""
        return self.articulation_controller.get_articulation()
    
    def process_nrpn(self, msb: int, lsb: int) -> str:
        """Process NRPN message to set articulation."""
        articulation = self.articulation_controller.process_nrpn(msb, lsb)
        return articulation
    
    def generate_samples(
        self, 
        block_size: int, 
        modulation: Dict[str, float]
    ) -> np.ndarray:
        """
        Generate samples with articulation processing.
        
        This is where the magic happens:
        1. Generate samples from base region
        2. Apply articulation processing
        3. Return processed samples
        """
        # Step 1: Generate from base region
        samples = self.base_region.generate_samples(block_size, modulation)
        
        # Step 2: Apply articulation processing
        articulation = self.get_articulation()
        params = self.articulation_controller.get_articulation_params()
        
        if self._sample_modifier and articulation != 'normal':
            # Apply articulation-specific processing
            samples = self._sample_modifier.apply_articulation(
                samples, articulation, params
            )
        
        # Step 3: Apply articulation parameters to base region
        self._apply_articulation_params(params)
        
        return samples
    
    def _apply_articulation_params(self, params: Dict[str, Any]) -> None:
        """Apply articulation parameters to base region."""
        # This is where articulation affects synthesis parameters
        # Examples:
        # - legato: smooth parameter transitions
        # - staccato: shorten envelope release
        # - vibrato: add LFO modulation
        # - growl: add modulation to filter/pitch
        
        if 'transition_time' in params:
            # Smooth parameter transitions
            pass
        
        if 'rate' in params and 'depth' in params:
            # Vibrato/tremolo modulation
            pass
    
    # Delegate all other methods to base_region
    def note_on(self, velocity: int, note: int) -> bool:
        return self.base_region.note_on(velocity, note)
    
    def note_off(self) -> None:
        self.base_region.note_off()
    
    def is_active(self) -> bool:
        return self.base_region.is_active()
    
    def initialize(self) -> bool:
        return self.base_region.initialize()
    
    def dispose(self) -> None:
        self.base_region.dispose()
```

#### **3.1.2 Create SArt2VoiceFactory**

**File:** `synth/xg/sart/sart2_voice_factory.py`

```python
"""
S.Art2 Voice Factory - Creates S.Art2-enabled voices.
"""

from typing import Optional
from ..voice.voice_factory import VoiceFactory
from ..engine.synthesis_engine import SynthesisEngineRegistry
from .sart2_region import SArt2Region


class SArt2VoiceFactory(VoiceFactory):
    """
    Voice factory that wraps all regions with S.Art2 articulation.
    
    This factory creates voices where every region is S.Art2-enabled,
    allowing articulation control for ANY synthesis engine.
    """
    
    def create_voice(self, bank: int, program: int, channel: int,
                    sample_rate: int) -> Optional['Voice']:
        """
        Create voice with S.Art2 articulation support.
        
        All regions in the voice will be wrapped with SArt2Region.
        """
        # Create base voice using parent factory
        voice = super().create_voice(bank, program, channel, sample_rate)
        
        if voice:
            # Wrap all regions with S.Art2
            self._wrap_regions_with_sart2(voice)
        
        return voice
    
    def _wrap_regions_with_sart2(self, voice: 'Voice') -> None:
        """Wrap all regions in voice with S.Art2."""
        # This would need to modify Voice to support region wrapping
        # Alternative: Create SArt2Voice that wraps regions on note_on
        pass
```

#### **3.1.3 Integrate NRPN Processing into ModernXGSynthesizer**

**File:** `synth/engine/modern_xg_synthesizer.py`

```python
class ModernXGSynthesizer:
    # Add S.Art2 support
    
    def __init__(self, ...):
        # ... existing init ...
        
        # S.Art2 integration
        from ..xg.sart import YamahaNRPNMapper, ArticulationController
        self.nrpn_mapper = YamahaNRPNMapper()
        self.articulation_manager = ArticulationManager()
    
    def process_nrpn(self, channel: int, msb: int, lsb: int, value: int) -> None:
        """
        Process NRPN message for S.Art2 articulation control.
        
        Args:
            channel: MIDI channel
            msb: NRPN MSB
            lsb: NRPN LSB
            value: NRPN value
        """
        # Get articulation from NRPN
        articulation = self.nrpn_mapper.get_articulation(msb, lsb)
        
        # Set articulation for channel
        self.channels[channel].set_articulation(articulation)
        
        # Or set for specific voice if polyphonic articulation
        # self.voice_manager.set_articulation(channel, articulation)
    
    def process_sysex(self, data: bytes) -> None:
        """Process SYSEX message for S.Art2."""
        from ..xg.sart import ArticulationController
        
        controller = ArticulationController()
        result = controller.parse_sysex(data)
        
        if result['command'] == 'set_articulation':
            # Set articulation from SYSEX
            pass
```

---

### **Phase 2: Engine-Specific Integration (Week 2-3)**

#### **3.2.1 SF2 Engine Integration**

**File:** `synth/engine/sf2_engine.py`

```python
class SF2Engine(SynthesisEngine):
    def create_region(self, descriptor: RegionDescriptor, 
                     sample_rate: int) -> IRegion:
        """Create SF2 region with optional S.Art2 wrapper."""
        from ..partial.sf2_region import SF2Region
        from ..xg.sart.sart2_region import SArt2Region
        
        # Create base SF2 region
        sf2_region = SF2Region(descriptor, sample_rate, self.soundfont_manager)
        
        # Wrap with S.Art2 for articulation control
        if self.sart2_enabled:
            return SArt2Region(sf2_region, sample_rate)
        
        return sf2_region
```

#### **3.2.2 FM Engine Integration**

```python
class FMEngine(SynthesisEngine):
    def create_region(self, descriptor: RegionDescriptor, 
                     sample_rate: int) -> IRegion:
        """Create FM region with S.Art2 wrapper."""
        from ..partial.fm_region import FMRegion
        from ..xg.sart.sart2_region import SArt2Region
        
        fm_region = FMRegion(descriptor, sample_rate)
        
        if self.sart2_enabled:
            return SArt2Region(fm_region, sample_rate)
        
        return fm_region
```

#### **3.2.3 Repeat for All Engines**

Same pattern for:
- AdditiveEngine
- WavetableEngine
- PhysicalEngine
- GranularEngine
- SpectralEngine

---

### **Phase 3: Voice Integration (Week 3-4)**

#### **3.3.1 Extend Voice for S.Art2**

**File:** `synth/voice/voice.py`

```python
class Voice:
    """Extend Voice with S.Art2 support."""
    
    def __init__(self, preset_info, engine, channel, sample_rate):
        # ... existing init ...
        
        # S.Art2 support
        self._articulation = 'normal'
        self._articulation_params = {}
    
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
        
        # Apply articulation to region selection
        # (e.g., different articulations for different velocity ranges)
        if self._articulation != 'normal':
            self._apply_articulation_to_regions(regions)
        
        return regions
```

#### **3.3.2 Extend VoiceInstance for S.Art2**

```python
class VoiceInstance:
    """Extend VoiceInstance with per-note articulation."""
    
    def __init__(self, note, velocity, channel, sample_rate):
        # ... existing init ...
        
        # Per-note articulation
        self._note_articulation = 'normal'
    
    def set_articulation(self, articulation: str) -> None:
        """Set articulation for this voice instance."""
        self._note_articulation = articulation
        
        for region in self.regions:
            if hasattr(region, 'set_articulation'):
                region.set_articulation(articulation)
```

---

### **Phase 4: Effects Integration (Week 4)**

#### **3.4.1 Merge S.Art2 Effects with Existing Effects**

**Option A:** Use existing XG effects (recommended)
```python
# synth/xg/sart/effects.py → DEPRECATED
# Use existing: synth/effects/system_effects.py
```

**Option B:** Integrate S.Art2 effects
```python
class EffectsSystem:
    def __init__(self, synthesizer):
        # ... existing effects ...
        
        # Add S.Art2 effects if needed
        from ..xg.sart.effects import ReverbEffect, DelayEffect
        self.sart2_reverb = ReverbEffect()
        self.sart2_delay = DelayEffect()
```

---

## 4. Code Reuse Matrix

| S.Art2 Package Component | Reuse Strategy | Effort |
|-------------------------|----------------|--------|
| **ArticulationController** | ✅ Direct reuse in SArt2Region | Low |
| **YamahaNRPNMapper** | ✅ Direct reuse in ModernXGSynthesizer | Low |
| **VoiceManager** | ⚠️ Merge with existing Voice/VoiceInstance | Medium |
| **VoiceState** | ⚠️ Merge with existing Voice | Medium |
| **effects.py** | ❌ Use existing XG effects | N/A |
| **wavetable.py** | ⚠️ Optional additional engine | Medium |
| **sf2_wavetable_adapter.py** | ❌ Use new SF2Region | N/A |
| **audio.py** | ❌ Use existing audio system | N/A |
| **constants.py** | ✅ Merge with existing constants | Low |
| **nrpn.py** | ✅ Direct reuse | Low |

**Overall Reuse: ~60% of S.Art2 package can be directly reused**

---

## 5. Integration Benefits

### **5.1 For Users**

| Benefit | Description |
|---------|-------------|
| **Universal Articulation** | Same articulation control for ALL engines |
| **NRPN Support** | Standard MIDI NRPN for articulation switching |
| **SYSEX Support** | Yamaha SYSEX compatibility |
| **Expressive Performance** | Real-time articulation changes |
| **Instrument Authenticity** | Proper wind/string/guitar techniques |

### **5.2 For Developers**

| Benefit | Description |
|---------|-------------|
| **Clean Architecture** | S.Art2 as wrapper layer |
| **Engine Agnostic** | Works with any IRegion |
| **Code Reuse** | 60% of S.Art2 package reused |
| **Extensible** | Easy to add new articulations |
| **Tested** | S.Art2 package already tested |

---

## 6. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Core** | Week 1-2 | SArt2Region, NRPN integration |
| **Phase 2: Engines** | Week 2-3 | All engines wrapped |
| **Phase 3: Voice** | Week 3-4 | Voice/VoiceInstance extended |
| **Phase 4: Effects** | Week 4 | Effects merged |
| **Testing** | Week 5 | Full test suite |

**Total: 5 weeks for full integration**

---

## 7. Testing Strategy

### **7.1 Unit Tests**

```python
class TestSArt2Region:
    def test_sart2_wraps_sf2_region(self):
        """Test S.Art2 wraps SF2 region correctly."""
        sf2_region = SF2Region(descriptor, 44100, manager)
        sart2_region = SArt2Region(sf2_region)
        
        assert sart2_region.base_region is sf2_region
    
    def test_sart2_articulation_switching(self):
        """Test articulation switching."""
        region = SArt2Region(base_region)
        region.set_articulation('legato')
        
        assert region.get_articulation() == 'legato'
    
    def test_sart2_nrpn_processing(self):
        """Test NRPN message processing."""
        region = SArt2Region(base_region)
        articulation = region.process_nrpn(1, 1)  # MSB 1, LSB 1 = legato
        
        assert articulation == 'legato'
```

### **7.2 Integration Tests**

```python
class TestSArt2Integration:
    def test_sart2_with_all_engines(self):
        """Test S.Art2 works with all synthesis engines."""
        engines = ['sf2', 'fm', 'additive', 'wavetable', 'physical']
        
        for engine_type in engines:
            region = create_region_for_engine(engine_type)
            sart2_region = SArt2Region(region)
            
            # Should work without errors
            samples = sart2_region.generate_samples(1024, {})
            assert len(samples) == 1024 * 2
    
    def test_sart2_nrpn_through_synth(self):
        """Test NRPN messages through full synth."""
        synth = ModernXGSynthesizer()
        synth.load_soundfont('test.sf2')
        
        # Send NRPN for legato articulation
        synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)
        
        # Verify articulation is set
        voice = synth.channels[0].current_voice
        assert voice.get_articulation() == 'legato'
```

---

## 8. Migration Path

### **For Existing Code**

```python
# BEFORE: No S.Art2
region = SF2Region(descriptor, sample_rate, manager)
samples = region.generate_samples(1024, {})

# AFTER: With S.Art2 (opt-in)
region = SF2Region(descriptor, sample_rate, manager)
sart2_region = SArt2Region(region)  # Wrap with S.Art2
sart2_region.set_articulation('legato')
samples = sart2_region.generate_samples(1024, {})

# OR: Enable globally
synth = ModernXGSynthesizer(sart2_enabled=True)
```

### **Backward Compatibility**

- ✅ Existing code continues to work
- ✅ S.Art2 is opt-in (wrapper)
- ✅ No breaking changes to IRegion interface
- ✅ Existing regions unchanged

---

## 9. Success Criteria

| Criteria | Target | Measurement |
|----------|--------|-------------|
| **Code Reuse** | >60% | Lines reused from sart/ |
| **Engine Coverage** | 100% | All engines support S.Art2 |
| **NRPN Support** | Full | All 70+ NRPN mappings work |
| **Performance** | <5% overhead | Benchmark with/without S.Art2 |
| **Test Coverage** | >80% | Unit + integration tests |
| **Documentation** | Complete | API docs + user guide |

---

## 10. Conclusion

### **Key Takeaways**

1. **S.Art2 is synthesis-agnostic** - Works with ANY IRegion implementation
2. **SArt2Region wrapper** is the key integration class
3. **60% code reuse** from existing S.Art2 package
4. **5-week timeline** for full integration
5. **Zero breaking changes** - fully backward compatible

### **Next Steps**

1. ✅ Create SArt2Region wrapper class
2. ✅ Integrate NRPN processing into ModernXGSynthesizer
3. ✅ Wrap all engine region creation
4. ✅ Extend Voice/VoiceInstance for articulation
5. ✅ Write comprehensive tests
6. ✅ Document API and usage

---

**Integration Plan Complete!** 🎉
