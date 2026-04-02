# Audio Buffer Format Standardization Plan

## Overview

Fix all components to use homogeneous interleaved stereo format `(block_size, 2)` throughout the audio synthesis pipeline.

## Current State

- **Correct format**: `(block_size, 2)` - 2D interleaved stereo
- **Incorrect format**: `(block_size * 2,)` - 1D flat array
- **Mitigation in place**: AudioProcessor converts 1D→2D (but causes overhead)

## Files to Fix

### Phase 1: Critical Base Classes

| File | Line(s) | Change Required |
|------|---------|-----------------|
| `synth/partial/region.py` | 187, 246 | Change `np.zeros(block_size * 2)` → `np.zeros((block_size, 2))` |
| `synth/partial/partial.py` | 328 | Update docstring to specify `(block_size, 2)` |
| `synth/voice/voice.py` | 266-271 | Change return buffer to 2D |

### Phase 2: All Region Classes (12 files)

| File | Method | Lines |
|------|--------|-------|
| `synth/partial/sf2_region.py` | `generate_samples()` | 1501, 1505, 1532-1533 |
| `synth/partial/fm_region.py` | `generate_samples()` | 257, 260, 281 |
| `synth/partial/wavetable_region.py` | `generate_samples()` | 327, 330, 352 |
| `synth/partial/physical_region.py` | `generate_samples()` | 326, 329, 350 |
| `synth/partial/spectral_region.py` | `generate_samples()` | 236, 239, 260 |
| `synth/partial/granular_region.py` | `generate_samples()` | 282, 285, 309 |
| `synth/partial/fdsp_region.py` | `generate_samples()` | 244, 247, 271 |
| `synth/partial/convolution_reverb_region.py` | `generate_samples()` | 304, 310, 323 |
| `synth/partial/an_region.py` | `generate_samples()` | 259, 262, 286 |
| `synth/partial/advanced_physical_region.py` | `generate_samples()` | 251, 254, 267 |
| `synth/partial/additive_region.py` | `generate_samples()` | 301, 304, 328 |
| `synth/xg/sart/sart2_region.py` | `generate_samples()` | 317 |

### Phase 3: Engine Classes

| File | Method | Lines |
|------|--------|-------|
| `synth/engine/sf2_engine.py` | `generate_samples()` | 951, 957, 967, 970 |
| `synth/engine/wavetable_engine.py` | Some methods | 529, 532, 545 |

### Phase 4: Partial Classes (completed)

| File | Method | Lines |
|------|--------|-------|
| `synth/partial/fm_partial.py` | `generate_samples()` | 53-65 |
| `synth/partial/physical_partial.py` | `generate_samples()` | 55-67 |
| `synth/partial/granular_partial.py` | `generate_samples()` | 63-75 |
| `synth/partial/additive_partial.py` | `generate_samples()` | 59-71 |

## Standard Fix Pattern

For each `generate_samples()` method, find:
```python
# OLD (incorrect):
output = np.zeros(block_size * 2, dtype=np.float32)
# or:
output = np.zeros(block_size * 2)
# or:
output = np.empty(block_size * 2, dtype=np.float32)

# NEW (correct):
output = np.zeros((block_size, 2), dtype=np.float32)
# or:
output = np.zeros((block_size, 2))
# or:
output = np.empty((block_size, 2), dtype=np.float32)
```

Also update any:
- Array slicing: `output[:block_size * 2]` → `output[:, :]`
- Channel access: `output[0]` (left) → `output[:, 0]`
- Stereo copy: `output[:] = mono` → `output[:, 0] = mono; output[:, 1] = mono`

## Implementation Order

1. **Phase 1**: Fix base classes first (region.py, partial.py, voice.py)
2. **Phase 2**: Fix all region classes - these are the primary synthesis path
3. **Phase 3**: Fix engine classes that wrap regions
4. **Phase 4**: Fix partial classes (completed)

## Testing

After each phase:
```bash
# Run tests
pytest tests/test_voice_manager.py -v
pytest tests/test_envelope.py -v

# Quick sanity check
python -c "
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
synth = ModernXGSynthesizer()
synth.load_soundfont('tests/ref.sf2')
synth.note_on(0, 60, 100)
audio = synth.generate_audio_block()
print(f'Output shape: {audio.shape}')  # Should be (1024, 2)
"
```

## Post-Fix Cleanup

After all fixes, remove conversion code in AudioProcessor:
- Remove 1D→2D conversion paths
- Add assertion to enforce 2D format input
- Simplify buffer handling

## Risk Mitigation

- Keep AudioProcessor conversion as fallback during transition
- Add runtime assertions to catch format mismatches
- Test with multiple soundfonts and engine configurations
