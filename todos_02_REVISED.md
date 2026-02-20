# SYXG Fix Strategy — Revised Gap Resolution Plan

> **Original Assessment**: The original `todos_01.md` contained several inaccurate claims. This revised plan corrects those and provides an accurate implementation roadmap based on actual codebase analysis.

---

## Executive Summary

After analyzing the codebase, here's the actual state of the project:

| Category | Status |
|----------|--------|
| Engine Registration | Working (with 1 bug in example file) |
| SF2Partial | Implemented with extensive features |
| Audio Output | Exists in SART subdirectory, not wired to main Synthesizer |
| render_block() | Missing - needs implementation |
| Tests | Many failing (actual infrastructure exists) |
| README | Needs GitHub URL update only |

---

## Phase 1 — Verified Critical Issues

### 1.1 Fix register_engine Call in voice_integration_example.py ✅ CONFIRMED BUG

**Problem**: In `synth/engine/voice_integration_example.py` line 31:
```python
self.engine_registry.register_engine(sf2_engine)  # Missing engine_type!
```

The `SynthesisEngineRegistry.register_engine()` requires `engine_type` as a positional argument (verified in `synth/engine/synthesis_engine.py`), but this call omits it.

**Fix**:
```python
self.engine_registry.register_engine(sf2_engine, 'sf2')
```

**Files**: `synth/engine/voice_integration_example.py`

---

### 1.2 Implement render_block() in Synthesizer ✅ MISSING

**Problem**: The main `Synthesizer` class (`synth/core/synthesizer.py`) lacks a unified `render_block()` method that orchestrates the full audio pipeline.

**Current state**: The Synthesizer has `_generate_audio_block()` which does basic voice mixing, but doesn't include:
- Insertion effects processing
- System effects (reverb/chorus) sends and returns
- Master effects (EQ, compressor)

**Fix**: Add `render_block(out: np.ndarray)` method that:
1. Clears output buffer
2. Iterates channels → renders via `VectorizedChannelRenderer`
3. Applies insertion effects per channel
4. Accumulates send levels to reverb/chorus buses
5. Applies system effects to bus returns
6. Applies master EQ + compressor
7. Writes to output buffer

**Files**: `synth/core/synthesizer.py`, `synth/effects/effects_coordinator.py`

---

### 1.3 Wire Audio Output to Main Synthesizer ✅ NEEDS WIRING

**Problem**: Real-time audio output exists in `synth/xg/sart/audio.py` (class `SoundDeviceOutput`) but is not connected to the main `Synthesizer` class.

**Current state**:
- `SoundDeviceOutput` class exists in `synth/xg/sart/audio.py`
- Uses `sounddevice` library for real-time playback
- Has proper callback structure

**Fix**: Add optional audio output to `Synthesizer`:
```python
# In synth/core/synthesizer.py
def __init__(self, sample_rate=44100, buffer_size=1024, enable_audio_output=False):
    # ... existing init ...
    if enable_audio_output:
        from synth.xg.sart.audio import SoundDeviceOutput
        self.audio_output = SoundDeviceOutput(
            sample_rate=sample_rate,
            buffer_size=buffer_size,
            callback=self._audio_callback
        )
```

**Files**: `synth/core/synthesizer.py`, `synth/xg/sart/audio.py`

---

### 1.4 Modulation Matrix Output Not Wired to Engines ⚠️ NEEDS VERIFICATION

**Problem**: The report claims `ModulationMatrix.process()` computes values but nothing reads them. Need to verify if this is still true.

**Action**: Search for modulation wiring:
```bash
grep -r "modulation_matrix.process" synth/
grep -r "apply_modulation" synth/engine/
```

**Likely Fix**: Connect modulation matrix output to engine parameters in the render path.

**Files**: `synth/channel/channel_note.py`, engine files

---

## Phase 2 — Verified Quality Issues

### 2.1 LFO Phase Reset ⚠️ NEEDS VERIFICATION

**Problem**: Report claims LFO phases aren't reset on note-on. Need to verify in code.

**Action**: Check `synth/modulation/sources.py` for LFO implementation.

---

### 2.2 Voice Leak on Repeated Notes ⚠️ NEEDS VERIFICATION

**Problem**: Report claims `VoiceManager.allocate_voice()` doesn't release existing voice for same note.

**Action**: Check `synth/voice/voice_manager.py` for this behavior.

---

### 2.3 ADSR Envelope ⚠️ NEEDS VERIFICATION

**Problem**: Report claims ADSR missing hold segment and exponential segments.

**Action**: Check `synth/partial/partial_generator.py` and `synth/core/envelope.py` for current envelope implementation.

---

## Phase 3 — Verified Cleanup Items

### 3.1 Fix README GitHub URL ✅ CONFIRMED

**Problem**: README.md line shows `github.com/roger/syxg.git` but should be `github.com/drbye78/syxg.git`

**Fix**: Update the GitHub URL in README.md

**Files**: `README.md`

---

### 3.2 Duplicate engines/ Directory ⚠️ NEEDS VERIFICATION

**Problem**: Report claims `synth/engines/` (plural) is duplicate of `synth/engine/`.

**Action**: Verify if `synth/engines/` is empty or has different content.

---

### 3.3 Rename Typo - VERIFY STATUS

**Problem**: Original report claimed need to rename `xg_sart_symth.py` → `xg_sart_synth.py`

**Actual state**: Both files exist:
- `synth/xg/xg_sart_symth.py` (typo version - reference impl)
- `synth/xg/xg_sart_synth.py` (correct version - also exists?)

**Action**: Verify which files exist and their purposes.

---

### 3.4 midi_to_xgml.py Note Events ⚠️ NEEDS VERIFICATION

**Problem**: Report claims converter ignores `note_on`/`note_off` messages.

**Action**: Check `midi_to_xgml.py` for note event handling.

---

## Implementation Plan

### Priority 1: Get Audio Working (Week 1)

| Task | Files | Effort |
|------|-------|--------|
| Fix register_engine call | voice_integration_example.py | 1 hour |
| Implement render_block() | synthesizer.py | 2 days |
| Wire audio output | synthesizer.py | 1 day |
| **Total** | | **~4 days** |

### Priority 2: Fix Modulation (Week 2)

| Task | Files | Effort |
|------|-------|--------|
| Verify modulation wiring | channel_note.py, engines | 1 day |
| Wire modulation matrix output | channel_note.py | 2 days |
| **Total** | | **~3 days** |

### Priority 3: Quality Improvements (Week 3)

| Task | Files | Effort |
|------|-------|--------|
| LFO phase reset | sources.py | 1 day |
| Voice leak fix | voice_manager.py | 1 day |
| ADSR improvements | envelope.py, partial_generator.py | 2 days |
| **Total** | | **~4 days** |

### Priority 4: Cleanup (Week 4)

| Task | Files | Effort |
|------|-------|--------|
| Fix README URL | README.md | 15 min |
| Verify/remove duplicate dirs | engines/ | 1 hour |
| midi_to_xgml note events | midi_to_xgml.py | 1 day |
| **Total** | | **~2 days** |

---

## Verification Commands

Run these to verify issues before fixing:

```bash
# Check register_engine calls
grep -n "register_engine(" synth/engine/voice_integration_example.py

# Check for render_block method
grep -n "def render_block" synth/core/synthesizer.py

# Check audio output wiring
grep -n "SoundDeviceOutput" synth/core/synthesizer.py

# Check modulation wiring
grep -rn "modulation_matrix.process" synth/channel/

# Check tests
python -m pytest tests/test_voice_architecture.py -v --tb=short 2>&1 | head -50
```

---

## Conclusion

The original report overestimated some issues but correctly identified:
1. The register_engine bug (confirmed)
2. Missing render_block() method (confirmed)
3. Audio output not wired (confirmed)
4. Test failures (confirmed)
5. README URL needs update (confirmed)

The implementation plan above prioritizes getting actual audio output working first, then fixing modulation, then quality improvements, then cleanup.

---

*Generated: 2026-02-20*
*Based on: codebase analysis of /mnt/c/work/guga/syxg*
