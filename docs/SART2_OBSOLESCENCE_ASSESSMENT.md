# S.Art2 Package Obsolescence Assessment

**Assessment Date:** 2026-02-22  
**Package:** `synth/xg/sart`  
**Context:** After S.Art2 integration into Modern XG Synth

---

## Executive Summary

After integrating S.Art2 articulation technology into Modern XG Synth, several components in the original `synth/xg/sart` package have become **obsolete or redundant**. However, the **core articulation components remain essential** and are actively used.

### **Summary by Component**

| Component | Status | Reason |
|-----------|--------|--------|
| `sart2_region.py` | ✅ **ACTIVE** | Core S.Art2 integration wrapper |
| `articulation_controller.py` | ✅ **ACTIVE** | Used by SArt2Region |
| `nrpn.py` | ✅ **ACTIVE** | NRPN mapping for articulations |
| `synth.py` | ❌ **OBSOLETE** | Standalone synth (we use ModernXGSynthesizer) |
| `voice.py` | ❌ **OBSOLETE** | Duplicate of synth/voice/ |
| `effects.py` | ❌ **OBSOLETE** | Duplicate of synth/effects/ |
| `audio.py` | ❌ **OBSOLETE** | Duplicate of synth/audio/ |
| `wavetable.py` | ❌ **OBSOLETE** | Duplicate of synth/engine/wavetable_engine.py |
| `sf2_wavetable_adapter.py` | ❌ **OBSOLETE** | Replaced by SF2Region |
| `constants.py` | ⚠️ **PARTIAL** | Some constants duplicated |

---

## Detailed Assessment

### **✅ ACTIVE Components (Keep)**

#### **1. `sart2_region.py`** - CORE INTEGRATION

**Status:** ✅ **ACTIVE - ESSENTIAL**

**Purpose:** SArt2Region wrapper that adds articulation to any IRegion

**Used By:**
- All 13 synthesis engines (via `create_region()`)
- SArt2RegionFactory
- ModernXGSynthesizer

**Lines of Code:** ~450

**Recommendation:** **KEEP** - This is the core of S.Art2 integration

---

#### **2. `articulation_controller.py`** - ARTICULATION LOGIC

**Status:** ✅ **ACTIVE - ESSENTIAL**

**Purpose:** ArticulationController for articulation mapping and parameter management

**Used By:**
- SArt2Region
- ModernXGSynthesizer.articulation_manager

**Lines of Code:** ~600

**Key Features:**
- 35+ articulation mappings
- NRPN processing
- SYSEX parsing
- Parameter management

**Recommendation:** **KEEP** - Core articulation logic

---

#### **3. `nrpn.py`** - NRPN MAPPING

**Status:** ✅ **ACTIVE - ESSENTIAL**

**Purpose:** YamahaNRPNMapper for NRPN to articulation mapping

**Used By:**
- SArt2Region
- ModernXGSynthesizer.nrpn_mapper
- Tests

**Lines of Code:** ~320

**Key Features:**
- 70+ NRPN mappings
- Category-based articulations
- Genos2 voice bank mapping

**Recommendation:** **KEEP** - NRPN mapping is essential

---

### **❌ OBSOLETE Components (Remove or Archive)**

#### **4. `synth.py`** - STANDALONE SYNTHESIZER

**Status:** ❌ **OBSOLETE**

**Purpose:** SuperArticulation2Synthesizer - standalone synthesizer class

**Why Obsolete:**
- We now use `ModernXGSynthesizer` with S.Art2 integration
- Duplicate functionality
- Not integrated with engine registry
- No region-based architecture

**Lines of Code:** ~2,024

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart import SuperArticulation2Synthesizer
synth = SuperArticulation2Synthesizer()

# NEW (use this)
from synth import ModernXGSynthesizer
synth = ModernXGSynthesizer()  # S.Art2 enabled by default
```

**Recommendation:** **REMOVE** or move to `archive/` directory

---

#### **5. `voice.py`** - VOICE MANAGEMENT

**Status:** ❌ **OBSOLETE**

**Purpose:** VoiceManager, VoiceState, NoteEvent for voice management

**Why Obsolete:**
- We have `synth/voice/voice.py` (Voice class)
- We have `synth/voice/voice_instance.py` (VoiceInstance class)
- We have `synth/voice/voice_manager.py` (VoiceManager class)
- Duplicate functionality

**Lines of Code:** ~108

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart.voice import VoiceManager

# NEW (use this)
from synth.voice.voice_manager import VoiceManager
from synth.voice.voice import Voice
from synth.voice.voice_instance import VoiceInstance
```

**Recommendation:** **REMOVE** - Use synth/voice/ package

---

#### **6. `effects.py`** - EFFECTS PROCESSING

**Status:** ❌ **OBSOLETE**

**Purpose:** ReverbEffect, DelayEffect for effects processing

**Why Obsolete:**
- We have `synth/effects/system_effects.py` (XGSystemEffectsProcessor)
- We have `synth/effects/` package with 40+ effect types
- More comprehensive effects system
- Better integration with XG specification

**Lines of Code:** ~193

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart.effects import ReverbEffect

# NEW (use this)
from synth.effects.system_effects import XGSystemEffectsProcessor
```

**Recommendation:** **REMOVE** - Use synth/effects/ package

---

#### **7. `audio.py`** - AUDIO OUTPUT

**Status:** ❌ **OBSOLETE**

**Purpose:** Audio output backend (sounddevice, PyAudio)

**Why Obsolete:**
- We have `synth/audio/` package
- Better integration with ModernXGSynthesizer
- More audio backend options
- Better buffer management

**Lines of Code:** ~221

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart.audio import SoundDeviceOutput

# NEW (use this)
from synth.audio.writer import AudioWriter
```

**Recommendation:** **REMOVE** - Use synth/audio/ package

---

#### **8. `wavetable.py`** - WAVETABLE SYNTHESIS

**Status:** ❌ **OBSOLETE**

**Purpose:** WavetableSynthesisEngine for wavetable synthesis

**Why Obsolete:**
- We have `synth/engine/wavetable_engine.py`
- Integrated with engine registry
- Region-based architecture
- S.Art2 support

**Lines of Code:** ~652

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart.wavetable import WavetableSynthesisEngine

# NEW (use this)
from synth.engine.wavetable_engine import WavetableEngine
# Or use via engine registry
engine = synth.engine_registry.get_engine('wavetable')
```

**Recommendation:** **REMOVE** - Use synth/engine/wavetable_engine.py

---

#### **9. `sf2_wavetable_adapter.py`** - SF2 ADAPTER

**Status:** ❌ **OBSOLETE**

**Purpose:** SF2WavetableAdapter for SF2 integration

**Why Obsolete:**
- We have `synth/partial/sf2_region.py` (SF2Region)
- Full S.Art2 integration
- Better SF2 package integration
- Lazy sample loading

**Lines of Code:** ~504

**Replacement:**
```python
# OLD (obsolete)
from synth.xg.sart.sf2_wavetable_adapter import SF2WavetableAdapter

# NEW (use this)
from synth.partial.sf2_region import SF2Region
# Or via engine
region = sf2_engine.create_region(descriptor, sample_rate)
```

**Recommendation:** **REMOVE** - Use synth/partial/sf2_region.py

---

### **⚠️ PARTIALLY OBSOLETE Components**

#### **10. `constants.py`** - CONFIGURATION

**Status:** ⚠️ **PARTIALLY OBSOLETE**

**Purpose:** Constants and configuration for S.Art2

**What's Still Used:**
- MIDI CC constants (CC_MODULATION, CC_BREATH, etc.)
- NRPN constants (NRPN_MSB_CONTROL, etc.)
- These are referenced by articulation_controller.py

**What's Obsolete:**
- SynthConfig (we have our own config)
- Duplicate constants from synth/constants.py

**Lines of Code:** ~113

**Recommendation:** **MERGE** constants into `synth/core/constants.py` and remove file

---

## Migration Guide

### **For Code Using `synth/xg/sart/`**

#### **1. Update Imports**

```python
# OLD
from synth.xg.sart import SuperArticulation2Synthesizer
from synth.xg.sart.voice import VoiceManager
from synth.xg.sart.effects import ReverbEffect

# NEW
from synth import ModernXGSynthesizer
from synth.voice.voice_manager import VoiceManager
from synth.effects.system_effects import XGSystemEffectsProcessor
```

#### **2. Update Synthesizer Creation**

```python
# OLD
from synth.xg.sart import SuperArticulation2Synthesizer
synth = SuperArticulation2Synthesizer()

# NEW
from synth import ModernXGSynthesizer
synth = ModernXGSynthesizer()
# S.Art2 is enabled by default!
```

#### **3. Update Articulation Control**

```python
# OLD
from synth.xg.sart import ArticulationController
controller = ArticulationController()
controller.set_articulation('legato')

# NEW (same API, but via ModernXGSynthesizer)
synth.set_channel_articulation(0, 'legato')
# OR
synth.process_nrpn(0, 1, 1, 0)  # NRPN for legato
```

---

## Removal Plan

### **Phase 1: Archive (Week 1)**

Move obsolete components to `synth/xg/sart/archive/`:
- `synth.py`
- `voice.py`
- `effects.py`
- `audio.py`
- `wavetable.py`
- `sf2_wavetable_adapter.py`

### **Phase 2: Merge Constants (Week 1)**

- Merge MIDI CC constants into `synth/core/constants.py`
- Remove `constants.py`

### **Phase 3: Update Documentation (Week 2)**

- Update all documentation to reference new locations
- Update import examples
- Update API references

### **Phase 4: Remove Archive (Week 4)**

- After verifying no code uses archived components
- Remove `synth/xg/sart/archive/` directory

---

## Impact Analysis

### **Code That Will Break**

| Component | Impact | Mitigation |
|-----------|--------|------------|
| `synth.py` | Low | Update to ModernXGSynthesizer |
| `voice.py` | Low | Update to synth/voice/ |
| `effects.py` | Low | Update to synth/effects/ |
| `audio.py` | Low | Update to synth/audio/ |
| `wavetable.py` | Low | Update to wavetable_engine.py |
| `sf2_wavetable_adapter.py` | Low | Update to sf2_region.py |

### **Code That Will Continue Working**

| Component | Impact | Notes |
|-----------|--------|-------|
| `sart2_region.py` | None | Core integration - KEEP |
| `articulation_controller.py` | None | Core logic - KEEP |
| `nrpn.py` | None | NRPN mapping - KEEP |

---

## Final Package Structure

### **After Cleanup:**

```
synth/xg/sart/
├── __init__.py              # Updated exports
├── sart2_region.py          # ✅ KEEP - Core integration
├── articulation_controller.py # ✅ KEEP - Articulation logic
└── nrpn.py                  # ✅ KEEP - NRPN mapping

synth/xg/sart/archive/       # Move obsolete here
├── synth.py                 # ❌ OBSOLETE
├── voice.py                 # ❌ OBSOLETE
├── effects.py               # ❌ OBSOLETE
├── audio.py                 # ❌ OBSOLETE
├── wavetable.py             # ❌ OBSOLETE
├── sf2_wavetable_adapter.py # ❌ OBSOLETE
└── constants.py             # ⚠️ MERGE constants
```

---

## Recommendations

### **Immediate Actions:**

1. ✅ **Keep** `sart2_region.py`, `articulation_controller.py`, `nrpn.py`
2. ❌ **Archive** `synth.py`, `voice.py`, `effects.py`, `audio.py`, `wavetable.py`, `sf2_wavetable_adapter.py`
3. ⚠️ **Merge** `constants.py` into `synth/core/constants.py`

### **Documentation Updates:**

1. Update `synth/xg/sart/__init__.py` to export only active components
2. Update all documentation to reference new locations
3. Add deprecation warnings to obsolete components before removal

### **Testing:**

1. Verify no external code uses obsolete components
2. Update tests to use new locations
3. Run full test suite after cleanup

---

## Summary

| Category | Count | Lines |
|----------|-------|-------|
| **Active (Keep)** | 3 | ~1,370 |
| **Obsolete (Remove)** | 6 | ~3,703 |
| **Partial (Merge)** | 1 | ~113 |

**Total Lines to Remove:** ~3,703 (73% of package)  
**Total Lines to Keep:** ~1,370 (27% of package)

**Net Result:** Cleaner, more focused package with only essential S.Art2 integration components.

---

**Assessment Complete** ✅
