# Migration Guide: Region-Based Architecture

**Version:** 4.0  
**Date:** 2026-02-22  
**Breaking Changes:** YES

---

## Overview

The XG synthesizer has been refactored to use a unified region-based architecture. This guide helps you migrate from the old architecture to the new one.

---

## Key Changes

### 1. Voice Creation Now Uses PresetInfo

**Before:**
```python
# Old architecture - Voice created with fixed partials
voice_params = engine.get_voice_parameters(program, bank)
voice = Voice(engine, voice_params, channel, sample_rate)
```

**After:**
```python
# New architecture - Voice created with preset info
preset_info = engine.get_preset_info(bank, program)
voice = Voice(preset_info, engine, channel, sample_rate)
```

### 2. Region Selection at Note-On Time

**Before:**
```python
# Old - Partials created at Voice creation
voice = Voice(engine, voice_params, channel, sample_rate)
voice.note_on(note=60, velocity=100)  # Uses same partials for all notes
```

**After:**
```python
# New - Regions selected at note-on
voice = Voice(preset_info, engine, channel, sample_rate)
regions = voice.get_regions_for_note(note=60, velocity=100)  # Correct zones!
voice.note_on(note=60, velocity=100)
```

### 3. New Region Classes

| Old Class | New Class | Notes |
|-----------|-----------|-------|
| `SynthesisPartial` | `IRegion` | Base interface |
| `SF2Partial` | `SF2Region` | Lazy sample loading |
| `FMPartial` | `FMRegion` | Per-note scaling |
| N/A | `WavetableRegion` | New: morphing, unison |
| N/A | `AdditiveRegion` | New: 128 partials |
| N/A | `PhysicalRegion` | New: waveguide |
| N/A | `GranularRegion` | New: grain clouds |
| N/A | `FDSPRegion` | New: formant synthesis |
| N/A | `ANRegion` | New: Jupiter-X AN |

---

## Migration Steps

### Step 1: Update Engine Calls

**Old:**
```python
from synth.engine.sf2_engine import SF2Engine

engine = SF2Engine(sample_rate=44100)
params = engine.get_voice_parameters(program=0, bank=0)
```

**New:**
```python
from synth.engine.sf2_engine import SF2Engine

engine = SF2Engine(sample_rate=44100)
preset_info = engine.get_preset_info(bank=0, program=0)
```

### Step 2: Update Voice Creation

**Old:**
```python
from synth.voice.voice import Voice

voice = Voice(engine, voice_params, channel=0, sample_rate=44100)
```

**New:**
```python
from synth.voice.voice import Voice

voice = Voice(preset_info, engine, channel=0, sample_rate=44100)
```

### Step 3: Update Note-On Handling

**Old:**
```python
# Voice had fixed partials
voice.note_on(note=60, velocity=100)
samples = voice.generate_samples(note=60, velocity=100, modulation={}, block_size=1024)
```

**New:**
```python
# Voice selects correct regions at note-on
regions = voice.get_regions_for_note(note=60, velocity=100)
voice.note_on(note=60, velocity=100)
samples = voice.generate_samples(block_size=1024, modulation={})
```

### Step 4: Update Channel Integration

**Old:**
```python
# Channel used legacy voice loading
channel.load_program(program=0, bank=0)
channel.note_on(note=60, velocity=100)
```

**New:**
```python
# Channel now uses VoiceFactory
channel.load_program(program=0, bank=0)  # Now creates Voice with preset_info
channel.note_on(note=60, velocity=100)  # Automatically selects correct regions
```

---

## New Features

### Multi-Zone SF2 Presets

**Now Working:**
```python
# SF2 preset with key splits (bass/treble) and velocity splits (soft/loud)
preset_info = sf2_engine.get_preset_info(bank=0, program=0)

# Bass soft (C2, vel 50)
regions = preset_info.get_matching_descriptors(note=36, velocity=50)
# Returns bass soft zone

# Treble loud (C5, vel 100)
regions = preset_info.get_matching_descriptors(note=72, velocity=100)
# Returns treble loud zone
```

### Wavetable Morphing

**New Feature:**
```python
from synth.partial.wavetable_region import WavetableRegion

region = WavetableRegion(descriptor, sample_rate=44100)

# Real-time wavetable position morphing
region._wavetable_position = 0.5  # Middle of wavetable
region._morph_speed = 0.1  # Morph speed

# Unison with detuning
region._unison_voices = 8
region._detune_amount = 15.0  # Cents
```

### Additive Spectral Morphing

**New Feature:**
```python
from synth.partial.additive_region import AdditiveRegion

region = AdditiveRegion(descriptor, sample_rate=44100)

# 128 partials with brightness control
region._max_partials = 128
region._brightness = 1.5  # Boost high harmonics

# Velocity affects brightness
region._velocity_to_brightness = 0.5
```

---

## Performance Improvements

### Lazy Sample Loading

**Before:**
- All samples loaded at program change
- High memory usage (200-500MB typical)
- Slow program changes (50-500ms)

**After:**
- Samples loaded only when note is played
- Low memory usage (50-150MB typical)
- Fast program changes (<5ms)

### Region Pooling

**New Feature:**
```python
from synth.voice.region_pool import RegionPool

pool = RegionPool(max_pooled_per_type=64)

# Acquire region from pool
region = pool.acquire('sf2', lambda: SF2Region(descriptor, 44100))

# Release back to pool after use
pool.release(region)
```

---

## Backward Compatibility

### Deprecated Methods

The following methods are deprecated but still work:

| Method | Replacement | Notes |
|--------|-------------|-------|
| `get_voice_parameters()` | `get_preset_info()` | Returns params for note 60 only |
| `create_partial()` | `create_region()` | Use new region classes |

### Legacy Code Support

Legacy code will continue to work but won't benefit from multi-zone support:

```python
# This still works but only returns zones for note 60
params = engine.get_voice_parameters(program, bank)

# For full multi-zone support, use new API
preset_info = engine.get_preset_info(bank, program)
```

---

## Troubleshooting

### Issue: "No module named 'synth.partial.wavetable_region'"

**Solution:** Ensure you're importing from the correct path:
```python
from synth.partial.wavetable_region import WavetableRegion
```

### Issue: "Abstract method not implemented"

**Solution:** Ensure all engines implement the new methods:
- `get_preset_info()`
- `get_all_region_descriptors()`
- `create_region()`
- `load_sample_for_region()`

### Issue: "Region creation too slow"

**Solution:** Use region pooling:
```python
from synth.voice.region_pool import get_global_region_pool

pool = get_global_region_pool()
region = pool.acquire('wavetable', lambda: WavetableRegion(descriptor, 44100))
```

---

## Testing

### Run Unit Tests

```bash
cd /mnt/c/work/guga/syxg
python -m pytest tests/test_region_architecture.py -v
python -m pytest tests/test_production_regions.py -v
```

### Run Benchmarks

```bash
cd /mnt/c/work/guga/syxg
python benchmarks/benchmark_regions.py
```

### Expected Results

- Region creation: <1ms average
- Sample generation: >44100 samples/second (real-time)
- Memory usage: <150MB for typical multi-zone preset

---

## Additional Resources

- [`docs/architecture_refactor_plan.md`](docs/architecture_refactor_plan.md) - Full architecture documentation
- [`docs/production_region_implementation_plan.md`](docs/production_region_implementation_plan.md) - Implementation details
- [`tests/test_region_architecture.py`](tests/test_region_architecture.py) - Unit tests
- [`tests/test_production_regions.py`](tests/test_production_regions.py) - Production region tests

---

**End of Migration Guide**
