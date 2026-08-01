# SF2 Engine — Real-Time Safety

## Overview

The SF2 (SoundFont 2.0) engine has been refactored for real-time safety. Key fixes that eliminate audio-thread violations:

### Pre-Loaded Samples (Phase 1)

**Before:** `generate_samples()` loaded samples lazily if `_sample_data is None` — file I/O on the audio thread.

**After:** Samples are loaded at `note_on()` time (non-audio-thread). `generate_samples()` asserts the sample is already loaded.

### Zero-Allocation Audio Path (Phase 2)

**Before:** `cc_state` dict allocated every block per voice (~11,000 allocations/sec at 64 voices).

**After:** `cc_state` dict pre-allocated in `__init__`, reused via `.clear()` each block.

### Lock-Free Parameter Sync (Phase 3)

**Before:** `control_change()` wrote fields directly on the MIDI thread, audio thread read them unsynchronized.

**After:** MIDI thread pushes (controller, value) pairs to a deque. Audio thread drains them via `_drain_param_updates()` at block boundaries.

### Cubic Hermite Interpolation (Phase 5)

**Before:** Linear interpolation only.

**After:** 4-point cubic Hermite spline interpolation with Catmull-Rom tangent estimation. Linear fallback for short samples (<4 frames).

### Bug Fixes (Phase 3)

- **is_active() false negative**: RELEASING voice defaults to `True` (not `False`) when envelope lacks `is_active()`
- **GS amp compounding**: Envelope time scaling applied once at `note_on()`, not every block
- **Loop-wrapping DC click**: Transition to RELEASING without clamping to last frame
- **Multi-SF2 sample ID collision**: `soundfont_path` passed through all sample data calls

## Generator Coverage

24 core SF2 generators are extracted in `_extract_generator_params()`. The remaining ~35 generators are accessed via `_get_generator_value()` in `SF2Region`. This is a two-pipeline design — not a coverage gap.
