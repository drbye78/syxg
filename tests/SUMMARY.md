# Test Suite Summary

*Last updated: 2026-07-14*

## DSP Primitive Advanced Tests (added 2026-07-14)

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_buffer_pool.py` | 20 | XGBufferPool lifecycle, SIMD alignment (32-byte), pool exhaustion, fallback, context manager, stats tracking |
| `test_panner_advanced.py` | 25 | Constant power law across 10 pan positions (<1% deviation), MIDI CC10 mapping, block processing, PannerPool |
| `test_oscillator_advanced.py` | 67 | Waveform shape (sine THD, triangle linearity, square duty cycle), frequency accuracy (<5%), phase continuity across block boundaries, delay, fade-in, XG controller modulation, OscillatorPool |
| `test_filter_advanced.py` | 31 | Spectral response (LPF/HPF/BPF attenuation via FFT), -3dB cutoff, resonance peak, self-oscillation stability, stereo width, BiquadFilter 6 types, FilterPool |
| `test_dsp_pipeline.py` | 19 | Full chain integration (envelope → LFO → filter → panner), 4-voice polyphonic mix, 100-block real-time simulation, stereo routing |
| `test_midi_render_features.py` | 18 | MIDI→audio effect verification: CC7 volume amplitude, CC10 pan stereo image, CC11 expression, CC64 sustain, pitch bend frequency shift (zero-crossing rate), CC1 vibrato detection, aftertouch, program change cross-correlation, polyphony, 32-bit precision |

## Bugs Found & Fixed During DSP Testing

- `buffer_pool.py`: Mono buffer shape `(size,1)` not `(size,)` — fixed reshape. SIMD alignment byte offset computed vs element index — fixed cast to `"B"`.
- `oscillator.py`: `set_parameters()` didn't recalc `phase_step` on rate change — fixed. `generate_block()` didn't clamp to buffer capacity causing Numba segfault — fixed. `set_block_size()` float64→float32 mismatch — fixed.

## Statistics

- **Total tests:** 1,923 (all passing)
- **New tests added (Phase 2):** 252
- **Worthless tests cleaned up (Phase 1):** ~200 stubs/skeletons removed
- **22 skipped dead tests** removed from `test_phases_1-7_comprehensive.py`

## New Test Files Added

| File | Tests | Coverage |
|------|-------|----------|
| `test_primitives_fast_math.py` | 15 | `synth/primitives/fast_math.py` — fast math approximation functions |
| `test_primitives_validation.py` | 51 | `synth/primitives/validation.py` — AudioValidator, parameter range, MIDI msg, system resources |
| `test_fm_engine.py` | 51 | `synth/engines/fm_operator.py`, `fm_lfo.py`, `fm_engine.py` — FM synthesis engine, operators, LFO |
| `test_sampling.py` | 26 | `synth/sampling/` — SampleManager, SampleFormatHandler, SampleMetadata, Keygroup |
| `test_audio_io.py` | 7 | `synth/io/audio/` — AudioWriter, converters, sample cache manager |
| `test_physical_engine.py` | 9 | `synth/engines/physical_engine.py` — physical modeling synthesis engine |
| `test_sfz_parser.py` | 34 | `synth/io/sfz/` — SFZ parser, data model (Opcode/Region/Group/Instrument), envelope, engine |
| `test_s90_s70_hardware.py` | 59 | `synth/hardware/s90_s70/` — hardware specs, control surface, preset compat, voice allocation |
| **Total** | **252** | |

## Files Cleaned Up (Phase 1)

| Action | Files |
|--------|-------|
| **Deleted** | 16 worthless test files (no real assertions, just pass/skip stubs) |
| **Moved** | 2 utility scripts → `tests/utils/` |
| **Trimmed** | 3 bloated files (production_regions, production_fixes, sart2_comprehensive) |
| **Removed skips** | 22 dead skipped tests from `test_phases_1-7_comprehensive.py` |

## Key Existing Test Files (Stable)

- `test_voice_manager.py` — Voice manager core
- `test_modulation_matrix.py` — Modulation routing
- `test_engine_registry.py` — Engine registry
- `test_types.py` — Shared type definitions
- `test_production_fixes.py` — Production instantiation tests (154 tests)
- `test_envelope.py` — Envelope processing
- `test_midi_controllers.py` — MIDI controller handling
- `test_primitives_waveguide.py` — Waveguide primitive
- Various XG/GS/midi2/sf2 test files

## Run Commands

```bash
# All tests (may take >2min)
pytest tests/ -v

# Fast tests only
pytest tests/ -m "not slow"

# Just new tests
pytest tests/test_fm_engine.py tests/test_sampling.py tests/test_audio_io.py tests/test_physical_engine.py tests/test_sfz_parser.py tests/test_s90_s70_hardware.py tests/test_primitives_fast_math.py tests/test_primitives_validation.py -v --tb=short -p no:cov
```

## Coverage Gaps (Remaining)

Still untested (low priority / integration-heavy):
- `synth/hardware/jupiter_x/` — Jupiter-X hardware emulation (heavy deps)
- `synth/synthesizers/` — Top-level orchestrators (integration-level)
- `synth/style/` — Auto-accompaniment engine
- `synth/sequencer/` — Pattern sequencer (complex state)
- `synth/protocols/gs/` — GS protocol handlers
- `synth/protocols/xg/` — XG protocol handlers (partially covered)
- `vibexg/` — TUI workstation (test via integration)
- `vst3_plugin/` — JUCE plugin (C++/pybind11)
