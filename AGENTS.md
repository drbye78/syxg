# AGENTS.md - XG Synthesizer Project Guide

## Project Overview

**XG Synthesizer** is a professional-grade MIDI synthesizer and real-time workstation implemented in Python. It provides complete Yamaha XG specification compliance, multiple synthesis engines, real-time audio processing, and a comprehensive workstation interface (Vibexg).

## Key Characteristics

| Attribute | Value |
|-----------|-------|
| Language | Python 3.11+ |
| License | MIT |
| Status | Beta (actively developed) |
| Repository | https://github.com/drbye78/syxg |

## Two-Entrypoint Architecture

This project has two top-level synthesizer classes with distinct purposes:

| Class | File | Purpose |
|-------|------|---------|
| `ModernXGSynthesizer` | `synth/engine/modern_xg_synthesizer.py` | **MIDI rendering engine** — offline/batch processing of MIDI sequences to audio. Used by `render_notes.py`, CLI tools, and any non-real-time workflow. |
| `Synthesizer` | `synth/core/synthesizer.py` | **Virtual hardware workstation** — real-time appliance emulating physical workstations (Motif, Fathom, JV-2080). Includes style engine, registration memory, MIDI learn, chord detection, hardware control surface mapping. Used by `vibexg` TUI. |

They are NOT duplicates. They share underlying engines and effects but have different initialization paths, threading models, and APIs.

## Core Design Principles

1. **Zero-Allocation Audio Processing**: Pre-allocated buffers, no runtime memory allocation in audio thread
2. **Real-Time Performance**: <5ms latency, suitable for live performance
3. **SIMD Optimization**: Numba JIT compilation, vectorized NumPy operations
4. **Interleaved Stereo Buffers**: Shape `(block_size, 2)` throughout the pipeline
5. **Sample-Perfect Timing**: MIDI messages processed at exact sample positions

## Project Structure

```
syxg/
├── synth/                    # Core synthesizer library
│   ├── core/                # Fundamental components (buffer_pool, envelope, filter, oscillator, panner)
│   ├── engine/              # Synthesis engines (modern_xg_synthesizer, sf2_engine, fm_engine, etc.)
│   ├── channel/             # MIDI channel processing (channel.py)
│   ├── voice/               # Voice management (voice.py, voice_manager.py, voice_factory.py)
│   ├── effects/             # Effects processing (62+ types)
│   ├── modulation/          # Modulation matrix and LFOs
│   ├── xg/                  # XG/GS specification implementation
│   ├── midi/                # MIDI message parsing
│   ├── partial/             # Region-based partials (sf2_region.py, etc.)
│   └── sf2/                 # SF2 soundfont management
├── vibexg/                   # Real-time workstation interface
├── vst3_plugin/              # VST3 plugin (JUCE + pybind11 bridge)
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Architecture

### Audio Pipeline

```
MIDI Input → MIDI Processor → Voice Manager → Synthesis Engines → Effects → Audio Output
     ↓              ↓              ↓               ↓              ↓           ↓
  Message      Channel       Voice         SF2/FM/SFZ      System/      Interleaved
  Parsing      Routing      Allocation      Engines       Variation      Stereo
                                                                           Buffers
```

### Buffer Format

**Interleaved Stereo** - Shape `(block_size, 2)`:
- `buffer[i, 0]` = Left channel sample at position i
- `buffer[i, 1]` = Right channel sample at position i
- Dtype: `np.float32`
- Alignment: 32 bytes (SIMD-optimized)

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `ModernXGSynthesizer` | `synth/engine/modern_xg_synthesizer.py` | Main synthesizer orchestrator |
| `SF2Engine` | `synth/engine/sf2_engine.py` | SoundFont 2 playback |
| `Channel` | `synth/channel/channel.py` | MIDI channel processing |
| `Voice` | `synth/voice/voice.py` | Voice instance |
| `VoiceManager` | `synth/voice/voice_manager.py` | Polyphony and voice allocation |
| `VoiceFactory` | `synth/voice/voice_factory.py` | Voice creation from engines |
| `SF2Region` | `synth/partial/sf2_region.py` | SF2 region with full CC support |
| `XGBufferPool` | `synth/core/buffer_pool.py` | Zero-allocation buffer management |
| `XGWorkstation` | `vibexg/workstation.py` | Real-time workstation |

## Development Guidelines

### Code Style

- **Formatter**: Black (line length 100)
- **Linter**: Flake8 + Ruff
- **Type Checking**: MyPy (strict mode)
- **Python Version**: 3.11+ required
- **No comments** unless explicitly requested

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=synth --cov-report=html

# Specific file
pytest tests/test_voice_manager.py -v

# Fast tests only
pytest tests/ -m "not slow"
```

### Linting

```bash
black synth/ vibexg/
ruff check synth/ vibexg/
mypy synth/ vibexg/
```

### Building

```bash
pip install -e ".[dev,audio,workstation]"  # Dev mode
pip install -e ".[full]"                   # All features

# VST3 plugin
cd vst3_plugin && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

## Common Tasks

### Adding a New Synthesis Engine

1. Create engine class in `synth/engine/` implementing `SynthesisEngine`
2. Register in `ModernXGSynthesizer._register_engines()`
3. Add tests in `tests/`

### Modifying Audio Processing

1. Use Numba JIT: `@jit(nopython=True, fastmath=True, cache=True)`
2. Process blocks, not individual samples
3. Maintain zero-allocation in audio thread
4. Use interleaved stereo format `(block_size, 2)`

### Working with Buffers

```python
# Get buffer from pool
buffer = synthesizer.buffer_pool.get_stereo_buffer(block_size)

# Process audio (in-place)
np.add(output_buffer, channel_audio, out=output_buffer)

# Return to pool
synthesizer.buffer_pool.return_stereo_buffer(buffer)

# Or context manager
with buffer_pool.temporary_buffer(1024, 2) as buffer:
    process_audio(buffer)
```

## Configuration

### Environment Variables

- `XG_SYNTH_DEBUG`: Enable debug logging
- `XG_SYNTH_SAMPLE_RATE`: Override sample rate (default: 44100)
- `XG_SYNTH_BUFFER_SIZE`: Override buffer size (default: 1024)

### XGML (YAML-based config)

```yaml
xg_dsl_version: "3.0"
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
effects_configuration:
  system_effects:
    reverb:
      type: hall
      time: 2.5
```

## Performance Considerations

### Audio Thread Safety

- **Never** allocate memory in audio thread
- **Never** use Python objects with `__del__` in audio thread
- **Always** use pre-allocated buffers from pool
- **Always** use Numba-compiled functions for heavy computation

### SIMD Optimization

- Buffers 32-byte aligned for AVX-256
- Use NumPy vectorized operations (automatically SIMD)
- Numba functions use `fastmath=True`
- Process blocks, not samples

## Dependencies

| Package | Purpose |
|---------|---------|
| numpy | Array operations, audio buffers |
| scipy | Signal processing |
| numba | JIT compilation |
| av | Audio file I/O (PyAV/FFmpeg) |
| PyYAML | XGML configuration |
| rtmidi | MIDI port access |
| sounddevice | Real-time audio output |
| rich | TUI |
| pytest/black/flake8/mypy | Development |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Audio glitches | Increase buffer size |
| High CPU | Verify Numba compilation, check voice count |
| Memory leaks | Use buffer pool statistics |
| MIDI timing issues | Enable sample-accurate processing |

### Debug Mode

```bash
XG_SYNTH_DEBUG=1 python -m vibexg

# Check pool stats
synth.buffer_pool.get_pool_statistics()
```

## Reference Files

| File | Location | Purpose |
|------|----------|---------|
| `test.mid` | `tests/test.mid` | Reference MIDI |
| `ref.sf2` | `tests/ref.sf2` | Reference SoundFont |

```bash
# Test playback
render_midi tests/test.mid output.wav --sf2 tests/ref.sf2
```

## Development Guidelines

### Code Rules

1. **No duplicate method definitions** — Python allows redefining methods; the second definition silently shadows the first. Always search for existing methods before adding.
2. **No bare `except:` clauses** — Always use `except Exception:` to avoid swallowing `KeyboardInterrupt` and `SystemExit`.
3. **No `print()` in production code** — Use the `logging` module with appropriate levels (`logger.info`, `logger.warning`, `logger.error`).
4. **No memory allocation in audio paths** — Use pre-allocated buffers from the buffer pool. Never call `np.zeros()`, `np.empty()`, or list/dict creation in `generate_samples` hot paths.
5. **Validate buffer shapes at API boundaries** — When mixing audio from regions/voices/channels, always verify shapes match before `+=` operations.
6. **No debug prints left in code** — Remove all `print(f"DEBUG: ...")` statements before committing.

### Threading Rules

1. **Audio thread must be real-time safe** — No GIL acquisition, no memory allocation, no file I/O, no Python API calls.
2. **VST3 plugin uses deferred processing** — The `PythonProcessingThread` handles all Python calls off the audio thread. `processBlock` only copies data to/from lock-free queues.
3. **Use proper memory ordering** — Lock-free data structures require `memory_order_acquire`/`memory_order_release` semantics.

### VST3 Plugin Architecture

The VST3 plugin bridges JUCE (C++) with the Python synthesizer via pybind11:

| Component | Purpose |
|-----------|---------|
| `PluginProcessor` | JUCE AudioProcessor — handles audio I/O, MIDI routing, parameter management |
| `PythonIntegration` | pybind11 bridge — creates Python interpreter, manages `ModernXGSynthesizer` instance |
| `PythonProcessingThread` | Background thread — runs Python audio generation off the audio thread |
| `XGParameterManager` | Parameter mapping — maps VST3 parameters to Python synthesizer methods |
| `LockFreeRingBuffer` | Thread-safe audio queue — SPSC ring buffer with proper memory ordering |

**Critical paths:**
- `processBlock` (audio thread) → copies MIDI/audio to queues → returns immediately
- `PythonProcessingThread::run()` (background) → reads queues → calls Python → writes results
- `parameterChanged` → forwards to `PythonIntegration.setParameter()` → calls Python synthesizer

### Testing Requirements

All integration paths between components must have tests. Key areas:
- Voice allocation → engine → region pipeline
- Buffer shape compatibility across all audio generation paths
- MIDI message byte construction (all message types)
- State save/restore completeness
- Thread safety of shared data structures
```
