## SYXG Fix Strategy — Prioritized Gap Resolution Plan

All issues are organized into five phases, ordered by dependency. Phases 1-2 unblock audio entirely. Phases 3-4 reach feature completeness. Phase 5 is maintenance/polish. Each phase lists the exact files to touch and what to do.

---

## Phase 1 — Critical Blockers (No Audio Without These)

These are the broken links that prevent even a single note from being synthesized by the modern engine.

### 1.1 Fix Engine Registration API (`synth/engine/engine_registry.py`)

**Problem:** `SynthesisEngineRegistry.register_engine()` requires an `engine_type` positional argument, but all call sites omit it. 22 tests fail on this alone.

**Fix:** Add `engine_type` as a keyword argument with a default derived from the engine class name, or make it truly optional by inferring it:
```python
def register_engine(self, engine, engine_type: str = None):
    if engine_type is None:
        engine_type = engine.__class__.__name__.lower().replace('engine', '')
    self._registry[engine_type] = engine
```
Alternatively, make `register_engine` a decorator that reads the class metadata. Either way, all existing call sites must be found (use `grep -r "register_engine"`) and made consistent.

**Files:** `synth/engine/engine_registry.py`, `synth/core/synthesizer.py`, all files that call `register_engine`.

### 1.2 Fix SF2Partial Constructor (`synth/partial/sf2_partial.py`)

**Problem:** `SF2Partial.__init__()` is called with 4 positional arguments but accepts only 3.

**Fix:** Read the call sites to determine which argument is the extra one, then add it to the signature. Most likely it is a `sample_rate` parameter added later to other Partial subclasses but missed here. Make the signature consistent with other `Partial` subclasses (check `partial.py`'s base class `__init__` signature and mirror it).

**Files:** `synth/partial/sf2_partial.py`, any call site constructing `SF2Partial`.

### 1.3 Wire Audio Output (`synth/audio/`)

**Problem:** The modern engine has no audio output binding. `synth/audio/` contains stubs.

**Fix:** Implement a `SoundDeviceOutput` class in `synth/audio/output.py` that:
- Opens a `sounddevice.OutputStream` with `sample_rate` and `blocksize=buffer_size`
- In the callback, calls `synthesizer.render_block(outdata)` — this must be the `VectorizedChannelRenderer` path
- Handles underruns gracefully (zero-fill, log warning, no exception in callback)
- Provides `start()`, `stop()`, `close()` lifecycle methods

Wire this in `Synthesizer.__init__` optionally (only if `sounddevice` is importable), keeping the offline render path independent.

**Files:** `synth/audio/output.py` (create/implement), `synth/core/synthesizer.py`.

### 1.4 Implement `Synthesizer.render_block()` as the Unified Render Entry Point

**Problem:** There is no single method that orchestrates: tick LFOs → render partials → apply insertion effects → sum channels → apply system effects → apply master effects → write to buffer.

**Fix:** Add `render_block(out: np.ndarray) -> None` to `Synthesizer`:
```python
def render_block(self, out: np.ndarray) -> None:
    out.fill(0.0)
    for channel in self.channels:
        ch_buf = channel.renderer.render_block()   # VectorizedChannelRenderer
        # apply insertion effects to ch_buf
        self.effects_coordinator.apply_insertion(channel.index, ch_buf)
        # send to reverb/chorus buses
        self.effects_coordinator.accumulate_send(channel.index, ch_buf)
        out += ch_buf
    # apply system effects (reverb, chorus) to bus returns, add to out
    self.effects_coordinator.apply_system_effects(out)
    # apply master EQ + compressor
    self.effects_coordinator.apply_master_effects(out)
```

**Files:** `synth/core/synthesizer.py`, `synth/effects/effects_coordinator.py`.

---

## Phase 2 — Integration Gaps (Audio Exists, But Modulation and Effects Are Silent)

### 2.1 Connect Modulation Matrix Output to Engine Parameters

**Problem:** `ModulationMatrix.process()` computes destination values but nothing reads them.

**Fix:** After `ModulationMatrix.process()` in `ChannelNote.render()`, read the result array and apply each destination:

```python
mod_values = self.modulation_matrix.process(sources_array)

# PITCH destination → add to partial phase increment
pitch_offset_cents = mod_values[ModulationDestination.PITCH]
self.partial_pool.set_pitch_offset(pitch_offset_cents)

# FILTER_CUTOFF → update biquad coefficients
cutoff_mod = mod_values[ModulationDestination.FILTER_CUTOFF]
self.filter.update_cutoff(self.base_cutoff + cutoff_mod)

# AMP → scale output
amp_mod = mod_values[ModulationDestination.AMP]
output_buffer *= (1.0 + amp_mod)
```

Each engine's `render_block()` must accept these as parameters or have setters that are called before rendering. The clean approach: engines expose a `ModulationTarget` protocol with `apply_modulation(dest, value)`.

**Files:** `synth/channel/channel_note.py`, `synth/engine/fm_engine.py`, `synth/engine/wavetable_engine.py`, `synth/modulation/matrix.py`.

### 2.2 Wire `XGEffectsCoordinator.process_audio()` into the Render Path

**Problem:** The coordinator is instantiated but its `process_audio()` is never called.

**Fix:** Implement the three-tier call in `Synthesizer.render_block()` (shown in 1.4 above). Additionally ensure `XGEffectsCoordinator` has:
- `apply_insertion(channel_index, buffer)` — iterates insertion slots for that channel
- `accumulate_send(channel_index, buffer)` — multiplies by reverb/chorus send levels and adds to bus buffers
- `apply_system_effects(mix_buffer)` — processes the reverb/chorus bus buffers and adds returns to mix
- `apply_master_effects(mix_buffer)` — runs master EQ then compressor in series

**Files:** `synth/effects/effects_coordinator.py`, `synth/core/synthesizer.py`.

### 2.3 Fix LFO → Parameter Binding

**Problem:** `LFOState.tick()` updates `current_value` but nothing passes this to engine frequency/amplitude parameters.

**Fix:** Add LFO values as explicit inputs to `ModulationMatrix.process()`:
```python
sources_array[ModulationSource.LFO1] = self.lfos[0].current_value
sources_array[ModulationSource.LFO2] = self.lfos[1].current_value
```
This bridges the LFO to the already-correct modulation matrix routing system, completing the chain without adding new coupling.

**Files:** `synth/channel/channel_note.py`, `synth/modulation/sources.py`.

### 2.4 Fix Parameter Router → Engine Parameter Setter Mapping

**Problem:** `Synthesizer.set_parameter()` handles volume/pan but drops filter, LFO, envelope, FM parameters.

**Fix:** Extend `set_parameter()` with a dispatch table:
```python
PARAM_DISPATCH = {
    'filter_cutoff':   lambda ch, v: ch.set_filter_cutoff(v),
    'filter_resonance':lambda ch, v: ch.set_filter_resonance(v),
    'lfo1_rate':       lambda ch, v: ch.set_lfo_rate(0, v),
    'lfo1_depth':      lambda ch, v: ch.set_lfo_depth(0, v),
    'fm_op1_level':    lambda ch, v: ch.set_fm_operator_level(0, v),
    # ... etc
}
```
This is straightforward to extend as each engine gains parameter support.

**Files:** `synth/core/synthesizer.py`, `synth/channel/channel.py`.

---

## Phase 3 — Algorithm Correctness (Sound Quality)

### 3.1 Fix ADSR: Add Hold Segment and Exponential Attack/Decay

**Problem:** Linear attack sounds wrong on most instrument patches; the XG EG has a 5-segment model (Attack/Hold/Decay/Sustain/Release) but the engine implements only 4.

**Fix in `partial/partial_generator.py`:**
1. Add `hold_time` and `hold_level` fields to `EnvelopeState`
2. Add `HOLD` as a new phase between `DECAY` and `SUSTAIN` in the Numba function
3. Replace linear ramp in attack with exponential: `level = target * (1 - exp(-t/attack_tau))` where `tau = attack_time / 5` (reaches 99% at `attack_time`)
4. Same for decay: `level = sustain + (peak - sustain) * exp(-t/decay_tau)`

Since this is Numba JIT code, the recompile is automatic on signature change. Delete the `.nbc`/`.nbi` cache files after the change.

**Files:** `synth/partial/partial_generator.py`, `synth/voice/voice_instance.py` (EnvelopeState dataclass).

### 3.2 Fix LFO Phase Reset on Note-On

**Problem:** LFO phases are not reset when a new note is triggered, causing polyphonic LFO beating.

**Fix in `channel/channel_note.py`:** In the `ChannelNote` constructor (called on note-on):
```python
for lfo in self.lfos:
    lfo.phase = 0.0  # reset to zero (or synth-level phase lock value)
    lfo.delay_elapsed = 0.0
    lfo.fade_elapsed = 0.0
```
Add a `sync_mode` flag: if `SYNC_TO_CLOCK`, set phase from MIDI clock tick count instead.

**Files:** `synth/channel/channel_note.py`, `synth/modulation/sources.py`.

### 3.3 Fix Voice Leak on Repeated Note (Same Note Retriggering)

**Problem:** `VoiceManager.allocate_voice()` doesn't release an existing voice for the same note before allocating a new one.

**Fix in `synth/voice/voice_manager.py`:**
```python
def allocate_voice(self, channel, note, velocity):
    # Release existing voice for same channel+note first
    existing = self._find_voice(channel, note)
    if existing:
        existing.release()  # trigger release phase, will be stolen after natural decay
    return self._allocate_new_voice(channel, note, velocity)
```

**Files:** `synth/voice/voice_manager.py`.

### 3.4 Upgrade Reverb from Schroeder to FDN

**Problem:** The 4-comb Schroeder reverb sounds metallic and colored — not suitable for XG Hall/Room presets.

**Fix:** Replace `system_effects.py`'s reverb with an 8×8 Feedback Delay Network (Jot, 1991):
- 8 delay lines with lengths chosen as mutually prime (e.g., Hadamard matrix feedback)
- One-pole damping filter per delay line (frequency-dependent decay)
- Pre-delay line for early reflections simulation
- Room size / damping parameters mapped to XG reverb SysEx parameters

This is ~100 lines of numpy and can be written as a drop-in replacement for the existing `Reverb` class interface.

**Files:** `synth/effects/system_effects.py`.

### 3.5 Add Sinc Interpolation to Sample Playback

**Problem:** `wavetable_engine.py` uses `resample_poly` (batch) or linear interpolation for pitch shifting. Linear interpolation causes audible aliasing above ~C5.

**Fix:** Implement a windowed-sinc interpolator (8-point or 16-point Blackman-windowed sinc) as a numpy vectorized function:
```python
def sinc_interpolate(samples, phase, window_size=8):
    # Precompute sinc kernel table at init (256 phases × window_size taps)
    # At render: look up nearest table entry, dot with sample window
```
Use the precomputed table approach (polyphase filterbank) so there is no per-sample sin() call. This is the standard professional sampler approach.

**Files:** `synth/engine/wavetable_engine.py`, `synth/sampling/pitch_shifting.py`.

### 3.6 Add FM Operator Key Scaling and 8-Operator Support

**Problem:** The FM engine is 4-operator only, missing key scaling (higher notes decay faster).

**Fix:**
1. Add `rate_scaling` and `level_scaling` fields to `FMOperator`
2. In the envelope section of `fm_engine.py`, scale attack/decay rates by `note_number * rate_scaling / 128`
3. For 8-operator support: extend `ALGORITHM_DEFS` from 8 to 88 algorithms (DX7 has 32; FM-X has 88). At minimum, add DX7's 32 standard algorithms as a lookup table of carrier/modulator topology graphs.

**Files:** `synth/engine/fm_engine.py`.

### 3.7 Implement SFZ Renderer (Complete the Stub)

**Problem:** `SFZEngine.render_block()` returns zeros.

**Fix:** Wire `SFZRegion` → `SampleManager.get_sample()` → pitch-shift to note → apply SFZ-defined envelope → return block. This is essentially the same path as `SF2Partial` and can share the sinc interpolator from 3.5.

**Files:** `synth/sfz/sfz_engine.py`.

---

## Phase 4 — Performance & Latency

### 4.1 Replace Batch `resample_poly` with Streaming Pitch Reader

**Problem:** `scipy.signal.resample_poly` re-processes the entire sample on every render call — O(N·sample_length) per block.

**Fix:** Implement a streaming sample reader with a phase accumulator:
```python
class StreamingSampleReader:
    def __init__(self, sample, pitch_ratio):
        self.phase = 0.0
        self.pitch_ratio = pitch_ratio  # output_freq / root_freq
        self.sample = sample

    def read_block(self, n_frames) -> np.ndarray:
        # vectorized: positions = phase + np.arange(n_frames) * pitch_ratio
        # use sinc table to interpolate
        # advance self.phase
```
This is O(n_frames) per block regardless of sample length.

**Files:** `synth/engine/wavetable_engine.py`, new `synth/sampling/streaming_reader.py`.

### 4.2 Eliminate the Spectral Engine's Render Latency

**Problem:** FFT size 2048 introduces 46ms latency. The <5ms claim requires buffer sizes of ≤220 samples.

**Options:**
- Reduce FFT size to 256 (5.8ms at 44100 Hz) — lower quality but real-time capable
- Move spectral synthesis offline (pre-compute spectrogram, stream frames) — best quality
- Use the **OLA (Overlap-Add) with smaller FFT** and accept slightly lower pitch resolution

Document this tradeoff explicitly and add a `latency_mode` parameter to the spectral engine.

**Files:** `synth/engine/spectral_engine.py`.

### 4.3 Confirm Numba JIT Scope and Add Fallback

**Problem:** Numba is a hard dependency for the critical render path. If not installed, the engine silently breaks.

**Fix:** In `partial/partial_generator.py`, wrap the Numba import:
```python
try:
    import numba
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    numba = type('numba', (), {'njit': lambda f: f})()  # identity decorator
```
The numpy fallback will be slower but correct. Add a warning log when Numba is absent.

**Files:** `synth/partial/partial_generator.py`.

---

## Phase 5 — Test, Documentation, and Cleanup

### 5.1 Fix All Failing Tests

**Target:** `test_voice_architecture.py` (22 tests, all failing).

After Phase 1 fixes, re-run the tests. The `register_engine` and `SF2Partial` fixes should resolve the majority. Update any remaining test assertions to match the corrected API. Add new integration tests covering:
- `note_on → render_block → audio samples present (not zeros)`
- `note_on → note_off → envelope reaches release phase`
- `CC11 (expression) → changes amplitude of rendered block`
- `reverb send > 0 → reverb effect output audible`

### 5.2 Rename `xg_sart_symth.py` → `xg_sart_synth.py`

One-line fix. Update all imports. Use `git mv` to preserve history.

**Files:** `synth/xg/xg_sart_symth.py` → `synth/xg/xg_sart_synth.py`.

### 5.3 Fix README Entry Point Reference

Change `synth.engine.modern_xg_synthesizer.ModernXGSynthesizer` → `synth.core.synthesizer.Synthesizer`. Fix GitHub URL from `roger/syxg` → `drbye78/syxg`.

**Files:** `README.md`.

### 5.4 Remove or Implement Deployment Stubs

`deploy/midi2_deployment_package.py` is architecture fiction. Either:
- Delete it and remove from packaging
- Or define a concrete deployment target (e.g., a REST API server wrapping `Synthesizer`) and implement it

### 5.5 Fix `midi_to_xgml.py` — Add Note Event Handling

The converter ignores `note_on`/`note_off` messages. Add a pass that extracts note sequences and emits XGML `<note>` elements. Without this, the tool produces empty XGML for any performance-containing MIDI file.

**Files:** `midi_to_xgml.py`.

### 5.6 Remove Duplicate `synth/engines/` Stub Directory

`synth/engines/` (plural) exists as an empty duplicate of `synth/engine/`. Delete it.

---

## Execution Order & Dependency Graph

```
Phase 1 (Blockers) → must all be done before any audio test is possible
  1.1 register_engine fix
  1.2 SF2Partial fix
  1.3 audio output
  1.4 render_block() method

Phase 2 (Integration) → after Phase 1; can be done in parallel
  2.1 modulation matrix wiring   ──┐
  2.2 effects coordinator wiring ──┤ independent of each other
  2.3 LFO → mod matrix bridge   ──┤
  2.4 parameter router extension ──┘

Phase 3 (Quality) → after Phase 2; each item is independent
  3.1 ADSR hold + exponential
  3.2 LFO phase reset
  3.3 voice leak fix
  3.4 FDN reverb
  3.5 sinc interpolation         ← prerequisite for 3.7
  3.6 FM key scaling + 8-op
  3.7 SFZ renderer

Phase 4 (Performance) → after Phase 3
  4.1 streaming sample reader    ← requires 3.5
  4.2 spectral engine latency
  4.3 Numba fallback

Phase 5 (Cleanup) → can start anytime after Phase 1
  5.1 fix tests
  5.2 rename typo
  5.3 fix README
  5.4 deploy stubs
  5.5 midi_to_xgml notes
  5.6 remove engines/ dir
```

---

## Estimated Scope

| Phase | Files Changed | Complexity | Unblocks |
|---|---|---|---|
| 1 | ~8 files | Low–Medium | Everything |
| 2 | ~12 files | Medium | Modulation, effects |
| 3 | ~10 files | Medium–High | Sound quality |
| 4 | ~6 files | High | Real-time performance |
| 5 | ~8 files | Low | Tests, docs |

**Phase 1 alone** — roughly 2-3 days of focused work — would produce the first actual synthesized audio from the modern engine. Phases 2+3 together represent the core musical quality milestone. Phases 4+5 bring production readiness.

The SART2 pocket synth (`synth/xg/sart/`) can remain as the validated reference implementation to A/B test against as each phase of the modern engine comes online.