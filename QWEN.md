# XG Synthesizer Project Context

## Project Overview

This is a high-performance MIDI XG (eXtended General MIDI) synthesizer implemented in Python with optimized vectorized processing. The project converts MIDI files to high-quality audio using SoundFont files and implements the Yamaha XG specification with comprehensive parameter mapping, effects processing, and real-time performance capabilities.

Key features:
- **XG Specification Compliant**: Fully compatible with Yamaha XG MIDI format
- **Vectorized Processing**: Uses NumPy for maximum performance (5-20x speedup)
- **8 Partials per Note**: Extended from XG standard of 4
- **SF2 SoundFont Support**: Full SoundFont 2.04 file format implementation
- **Real-time Performance**: Optimized for live audio processing
- **Sample-accurate Timing**: Block-segment MIDI message processing
- **Advanced Effects**: Reverb, chorus, variation, and insertion effects
- **Memory Optimized**: Object pooling and pre-allocated buffers

## Architecture

### Core Components
1. **OptimizedXGSynthesizer**: Main synthesizer engine with performance optimizations
2. **VectorizedChannelRenderer**: Per-channel audio generation with proper XG insertion effects
3. **MemoryPool**: Ultra-fast buffer management with pre-allocated audio buffers
4. **SF2Manager**: SoundFont file loading and sample management
5. **VectorizedEffectManager**: Comprehensive effects processing per XG specification

### Directory Structure
```
sxg/
├── config.yaml              # Configuration for audio settings and SF2 files
├── render_midi.py           # Main MIDI to audio conversion script
├── synth/                   # Core synthesizer implementation
│   ├── engine/              # Synthesizer core and channel renderers
│   ├── audio/               # Audio writers and format handling
│   ├── midi/                # MIDI parsing and message handling
│   ├── sf2/                 # SoundFont file processing
│   ├── effects/             # Reverb, chorus, and other effects
│   ├── dsp/                 # Digital signal processing components
│   ├── core/                # Core synthesis building blocks
│   └── utils/               # Utility functions
├── docs/                    # Documentation including XG specification
├── tests/                   # Test files
├── testsuite/               # Comprehensive test suite for XG compliance
├── profiling_analysis.md    # Performance profiling and optimization notes
└── updated_profiling_analysis.md
```

## Building and Running

### Main Entry Point
The primary script is `render_midi.py` which converts MIDI files to audio:

```bash
# Basic usage - converts to OGG format by default
python render_midi.py input.mid

# Convert to specific format
python render_midi.py --format wav input.mid

# Convert with custom parameters
python render_midi.py --sample-rate 48000 --volume 0.8 input.mid output.mp3

# Process multiple files
python render_midi.py --format mp3 *.mid

# With keyboard abort capability
python render_midi.py --keyboard-abort input.mid
```

### Configuration
The `config.yaml` file contains audio settings and SoundFont file paths:
- Sample rate (default: 48000 Hz)
- Audio processing chunk size (default: 50ms)
- Maximum polyphony (default: 512)
- Master volume (default: 1.0)
- SoundFont files to use

### Dependencies
The project requires NumPy for vectorized operations and likely other audio processing libraries. Dependencies would typically be found in requirements.txt or setup.py, though these were not found in this project.

## Development Conventions

### Performance Optimizations
- All audio processing uses vectorized NumPy operations
- Memory pools for buffer reutilization to minimize allocation overhead
- Pre-allocated buffers for zero-allocation rendering
- Object pooling for expensive objects
- Sample-accurate MIDI processing with block-segment timing

### Code Structure
- Clear separation of concerns with modular components
- Thread-safe design for concurrent access
- XG specification compliance throughout implementation
- Proper error handling and cleanup mechanisms

### Testing
The project includes a comprehensive test suite in the `testsuite/` directory with:
- Basic MIDI processing tests
- XG-specific parameter tests
- Effects processing validation
- SysEx message handling
- Sample-perfect timing accuracy
- Performance benchmarks

## Key Functionality

### XG Parameter Support
- Sound controllers (CC 71-78): Harmonic Content, Brightness, Release/Attack/Decay Times, Filter Cutoff, Vibrato Rate/Depth
- NRPN parameter processing for XG-specific features
- SysEx message handling for Yamaha XG commands

### Effects Processing
- System effects: Reverb, Chorus, Variation
- Insertion effects: 60+ professional effects with real-time modulation
- Effect routing with proper signal flow

### SF2 Loop Handling
- Forward, backward, and alternating loop modes
- Proper loop detection and playback logic
- Sustained sound implementation

### Voice Allocation
- Configurable polyphony limits
- Multiple voice allocation modes
- Proper note-off handling and voice stealing

## Performance Considerations

Based on profiling analysis, the main bottlenecks are:
1. Reverb processing (57.4% of total time)
2. Chorus processing (25.0% of total time)
3. Overall effect processing framework (91.9% of total time)

The core audio generation is relatively fast compared to effects processing. For performance-critical applications, consider:
- Disabling unused effects
- Using lower-quality effects when high performance is needed
- Optimizing the reverb and chorus algorithms

## Documentation
Detailed technical documentation is available in `docs/xg_synthesizer_guide.md` covering:
- XG parameter mappings
- Controller scaling formulas
- SF2 loop mode handling
- Modulation matrix specifications
- Envelope parameters
- Implementation details and performance optimizations