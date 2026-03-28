# AGENTS.md - XG Synthesizer Project Guide

## Project Overview

**XG Synthesizer** is a professional-grade MIDI synthesizer and real-time workstation implemented in Python. It provides complete Yamaha XG (eXtended General MIDI) specification compliance, multiple synthesis engines, real-time audio processing, and a comprehensive workstation interface (Vibexg).

## Key Characteristics

- **Language**: Python 3.11+
- **License**: MIT
- **Status**: Beta (actively developed)
- **Repository**: https://github.com/drbye78/syxg

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
│   ├── core/                # Fundamental components
│   │   ├── buffer_pool.py   # Zero-allocation buffer management
│   │   ├── config.py        # Configuration system
│   │   ├── envelope.py      # AHDSR envelope generators
│   │   ├── filter.py        # Resonant filters (Numba-optimized)
│   │   ├── oscillator.py    # LFO and waveform generation
│   │   └── panner.py        # Stereo panning
│   ├── engine/              # Synthesis engines
│   │   ├── modern_xg_synthesizer.py  # Main synthesizer class
│   │   ├── sf2_engine.py    # SoundFont 2.0 playback
│   │   ├── fm_engine.py     # FM synthesis
│   │   ├── sfz_engine.py    # SFZ sample playback
│   │   └── plugins/         # Engine plugins
│   ├── channel/             # MIDI channel processing
│   ├── voice/               # Voice management and allocation
│   ├── effects/             # Effects processing (62+ types)
│   ├── modulation/          # Modulation matrix and LFOs
│   ├── xg/                  # XG/GS specification implementation
│   └── midi/                # MIDI message parsing
├── vibexg/                   # Real-time workstation interface
│   ├── cli.py               # Command-line interface
│   ├── tui.py               # Text-based user interface
│   ├── workstation.py       # Main workstation orchestrator
│   └── midi_inputs.py       # MIDI input sources
├── tests/                    # Test suite
├── docs/                     # Documentation
├── examples/                 # Usage examples
└── vst3_plugin/             # VST3/AAX plugin (C++/JUCE)
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
| `XGBufferPool` | `synth/core/buffer_pool.py` | Zero-allocation buffer management |
| `AudioProcessor` | `synth/engine/processors/audio_processor.py` | Audio block generation |
| `VoiceManager` | `synth/voice/voice_manager.py` | Polyphony and voice allocation |
| `VectorizedChannelRenderer` | `synth/channel/vectorized_channel_renderer.py` | Channel audio processing |
| `XGWorkstation` | `vibexg/workstation.py` | Real-time workstation |

## Development Guidelines

### Code Style

- **Formatter**: Black (line length 100)
- **Linter**: Flake8 + Ruff
- **Type Checking**: MyPy (strict mode)
- **Python Version**: 3.11+ required

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=synth --cov-report=html

# Run specific test file
pytest tests/test_voice_manager.py -v

# Run fast tests only (skip slow)
pytest tests/ -m "not slow"
```

### Linting

```bash
# Format code
black synth/ vibexg/

# Lint code
flake8 synth/ vibexg/
ruff check synth/ vibexg/

# Type check
mypy synth/ vibexg/
```

### Building

```bash
# Install in development mode
pip install -e ".[dev,audio,workstation]"

# Install with all features
pip install -e ".[full]"

# Build VST3 plugin
cd vst3_plugin && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

## Common Tasks

### Adding a New Synthesis Engine

1. Create engine class in `synth/engine/`
2. Implement `SynthesisEngine` interface
3. Register in `ModernXGSynthesizer._register_engines()`
4. Add tests in `tests/test_*_engine.py`

### Adding a New Effect

1. Create effect class in `synth/effects/types.py`
2. Implement effect processing logic
3. Register in effects coordinator
4. Add to XGML configuration support

### Modifying Audio Processing

1. All audio functions should use Numba JIT when possible
2. Use `@jit(nopython=True, fastmath=True, cache=True)` decorator
3. Process blocks, not individual samples
4. Maintain zero-allocation in audio thread
5. Use interleaved stereo format `(block_size, 2)`

### Working with Buffers

```python
# Get buffer from pool (zero-allocation)
buffer = synthesizer.buffer_pool.get_stereo_buffer(block_size)

# Process audio
np.add(output_buffer, channel_audio, out=output_buffer)

# Return buffer to pool
synthesizer.buffer_pool.return_buffer(buffer)

# Or use context manager
with buffer_pool.temporary_buffer(1024, 2) as buffer:
    process_audio(buffer)
# Buffer automatically returned
```

## Configuration

### XGML Configuration

The synthesizer uses XGML v3.0 (YAML-based) for configuration:

```yaml
xg_dsl_version: "3.0"
description: "Configuration description"

# Channel setup
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100

# Effects configuration
effects_configuration:
  system_effects:
    reverb:
      type: hall
      time: 2.5
```

### Environment Variables

- `XG_SYNTH_DEBUG`: Enable debug logging
- `XG_SYNTH_SAMPLE_RATE`: Override sample rate (default: 44100)
- `XG_SYNTH_BUFFER_SIZE`: Override buffer size (default: 1024)

## Performance Considerations

### Audio Thread Safety

- **Never** allocate memory in audio thread
- **Never** use Python objects with `__del__` in audio thread
- **Always** use pre-allocated buffers from pool
- **Always** use Numba-compiled functions for heavy computation

### SIMD Optimization

- Buffers are 32-byte aligned for AVX-256
- Use NumPy vectorized operations (automatically SIMD)
- Numba functions use `fastmath=True` for SIMD
- Process blocks, not samples

### Memory Management

- Buffer pool pre-allocates common sizes
- Dynamic allocation within budget (default 256MB)
- Emergency cleanup under memory pressure
- Leak detection in debug mode

## Dependencies

### Core

- `numpy>=1.21.0`: Array operations and audio buffers
- `scipy>=1.7.0`: Signal processing
- `numba>=0.56.0`: JIT compilation for performance
- `av>=9.0.0`: Audio file I/O (PyAV/FFmpeg)
- `PyYAML>=6.0`: XGML configuration parsing

### Workstation (Vibexg)

- `rtmidi>=2.0.0`: MIDI port access
- `sounddevice>=0.4.0`: Real-time audio output
- `rich>=13.0.0`: Text-based user interface

### Development

- `pytest>=6.0`: Testing framework
- `black>=21.0.0`: Code formatting
- `flake8>=3.8.0`: Linting
- `mypy>=0.812`: Type checking

## Troubleshooting

### Common Issues

1. **Audio glitches**: Check buffer underruns, increase buffer size
2. **High CPU**: Verify Numba compilation, check voice count
3. **Memory leaks**: Use buffer pool statistics, check for unreleased buffers
4. **MIDI timing**: Ensure sample-accurate processing is enabled

### Debug Mode

```bash
# Enable debug logging
XG_SYNTH_DEBUG=1 python -m vibexg

# Check buffer pool statistics
synth.buffer_pool.get_pool_statistics()

# Validate pool integrity
synth.buffer_pool.validate_pool_integrity()
```

## Additional Resources

- **README.md**: Project overview and quick start
- **docs/**: Comprehensive documentation
- **examples/**: Usage examples and tutorials
- **tests/**: Test suite with examples
- **CONTRIBUTING.md**: Contribution guidelines

## Debugging Reference Files

For debugging and testing purposes, the following reference files are available:

| File | Location | Purpose |
|------|----------|---------|
| `test.mid` | `tests/test.mid` | Reference MIDI file for testing playback and rendering |
| `ref.sf2` | `tests/ref.sf2` | Reference SoundFont for testing SF2 engine and audio output |

### Using Reference Files

```bash
# Test MIDI playback with reference SoundFont
render-midi tests/test.mid output.wav --soundfont tests/ref.sf2

# Debug MIDI parsing
python -c "
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
synth = ModernXGSynthesizer()
synth.load_soundfont('tests/ref.sf2')
# Process MIDI from tests/test.mid
"
```

These files are useful for:
- Verifying audio output quality
- Testing MIDI parsing and timing
- Debugging synthesis engine issues
- Validating effects processing
- Benchmarking performance
