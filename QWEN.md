# Project Context for Qwen Code

## Project Overview

This project is a MIDI XG synthesizer implementation in Python. The main goal is to create a fully MIDI XG compatible software synthesizer that can convert MIDI files to audio formats like OGG or WAV.

### Key Components

1. **XG Synthesizer Core** (`synth/core/synthesizer.py`) - Main synthesizer class that orchestrates all modules
2. **MIDI Processing** - Handles all MIDI messages including SYSEX and Bulk SYSEX
3. **Audio Generation** - Generates audio in blocks of arbitrary size with sample-accurate timing
4. **SF2 File Management** - Loads and manages SoundFont files for sound generation
5. **XG Compatibility** - Implements XG-specific features like part modes, drum parameters, effects
6. **MIDI to Audio Conversion** (`midi_to_ogg.py`) - Main entry point for converting MIDI files to audio

## Project Structure

```
/mnt/c/work/guga/syxg/
├── midi_to_ogg.py          # Main conversion script
├── config.yaml             # Configuration file
├── LICENSE
├── QWEN.md                 # This file
├── TECHNICAL_XG_ANALYSIS.md # Detailed technical analysis of XG conformance issues
├── XG_CONFORMANCE_ANALYSIS.md # Analysis of MIDI XG standard conformance
├── XG_IMPLEMENTATION_PLAN.md # Detailed implementation plan for XG features
├── XG_IMPLEMENTATION_ROADMAP.md # Implementation roadmap with timeline and priorities
├── __pycache__/
├── .git/
├── .idea/
├── .vscode/
├── docs/
├── synth/                  # Core synthesizer modules
│   ├── core/               # Core synthesizer components
│   │   ├── synthesizer.py  # Main synthesizer class
│   │   ├── oscillator.py   # Audio oscillators (LFOs)
│   │   ├── filter.py       # Audio filters
│   │   ├── envelope.py     # ADSR envelopes
│   │   ├── panner.py       # Stereo panning
│   │   └── constants.py    # System constants
│   ├── sf2/                # SoundFont management
│   │   ├── manager.py      # SF2 file manager
│   │   └── core/
│   │       └── wavetable_manager.py # Wavetable sample manager
│   ├── xg/                 # XG-specific implementations
│   │   ├── channel_renderer.py  # Per-channel MIDI processing
│   │   ├── manager.py      # XG state management
│   │   ├── drum_manager.py # Drum parameter handling
│   │   ├── channel_note.py # Active note representation
│   │   └── partial_generator.py # Partial structure handling
│   ├── midi/               # MIDI message handling
│   │   ├── message_handler.py # MIDI message processing
│   │   └── buffered_processor.py # Buffered MIDI processing with timing
│   ├── audio/              # Audio engine
│   │   └── engine.py       # Audio block generation and processing
│   ├── effects/            # Audio effects processing
│   │   ├── core.py         # Effects manager
│   │   └── [many effect modules]
│   ├── modulation/         # Modulation system
│   │   ├── matrix.py       # Modulation matrix
│   │   ├── routes.py       # Modulation routes
│   │   ├── sources.py      # Modulation sources
│   │   └── destinations.py # Modulation destinations
│   └── voice/              # Voice management
│       ├── voice_manager.py # Voice allocation and management
│       ├── voice_info.py   # Voice information
│       └── voice_priority.py # Voice priority levels
├── tests/                  # Test files (currently empty)
└── docs/                   # Documentation
```

## Technologies Used

- **Python 3** - Main programming language
- **NumPy** - Numerical computing for audio processing
- **Mido** - MIDI file handling
- **Opuslib** - OGG audio encoding
- **PyYAML** - Configuration file parsing
- **SoundFont (SF2)** - Sound sample format
- **line_profiler** - Performance profiling (for optimization)

## Key Features

### MIDI XG Compatibility
- All MIDI messages including SYSEX and Bulk SYSEX
- XG Part Modes (Normal, Hyper Scream, Analog, Max Resonance, etc.)
- NRPN/RPN parameter handling
- Drum note mapping and parameters
- Effect processing (Reverb, Chorus, Variation effects)
- Multi-timbral operation (16-part multi-timbral)

### Audio Processing
- Sample-accurate timing synchronization
- Real-time audio generation
- Configurable sample rates (48kHz default)
- Polyphonic voice management
- LFOs (Low-Frequency Oscillators)
- Modulation matrix
- Panning and spatialization

### Performance Optimizations
- SF2 parameter caching
- Memory pooling for objects
- Batched modulator processing
- Optimized attribute access

## Building and Running

### Prerequisites
- Python 3.7+
- Required Python packages (installed via pip):
  - mido
  - numpy
  - pyyaml
  - opuslib
  - line_profiler (for profiling)

### Installation
```bash
# Install required packages
pip install mido numpy pyyaml opuslib line_profiler
```

### Usage
```bash
# Convert a MIDI file to OGG
python midi_to_ogg.py input.mid output.ogg

# Convert with custom configuration
python midi_to_ogg.py -c config.yaml input.mid output.ogg

# Convert to WAV format
python midi_to_ogg.py --format wav input.mid output.wav

# Convert with specific SoundFont
python midi_to_ogg.py --sf2 soundfont.sf2 input.mid output.ogg

# Convert with custom sample rate
python midi_to_ogg.py --sample-rate 48000 input.mid output.ogg
```

### Configuration
The `config.yaml` file supports the following options:
- `sample_rate`: Audio sample rate (default: 48000)
- `chunk_size_ms`: Audio processing chunk size in milliseconds (default: 20)
- `max_polyphony`: Maximum polyphony (default: 64)
- `master_volume`: Master volume (0.0 to 1.0, default: 1.0)
- `sf2_files`: List of SoundFont (.sf2) file paths

## Development Conventions

### Code Organization
1. Modular design with separate modules for each functionality
2. XG-specific implementations in the `synth/xg/` directory
3. Core audio processing in the `synth/core/` directory
4. SF2 file handling in the `synth/sf2/` directory
5. Effects processing in the `synth/effects/` directory
6. Modulation system in the `synth/modulation/` directory
7. Voice management in the `synth/voice/` directory

### XG Implementation Status
The project is currently working toward full XG compliance. Key areas that need implementation:

1. **Part Mode Implementation** - Complete implementation of all XG part modes with proper sound characteristics
2. **NRPN Parameter Handling** - Ensure all mapped NRPN parameters are properly implemented and validated
3. **SysEx Message Handling** - Implement full XG SysEx message support for all defined message types
4. **Drum Parameter Implementation** - Complete implementation of all drum note parameters according to XG specification
5. **Controller Implementation** - Ensure all XG-specific controllers are properly implemented
6. **Effect Processing Integration** - Integrate complete effect processing with proper XG effect types

### Testing
Currently, there are no automated tests in the `tests/` directory. Testing is done manually by converting MIDI files and listening to the output.

## Key Files for Development

1. **`midi_to_ogg.py`** - Main entry point for MIDI to audio conversion
2. **`synth/core/synthesizer.py`** - Main synthesizer class orchestrating all modules
3. **`synth/xg/channel_renderer.py`** - Per-channel MIDI processing with XG features
4. **`synth/xg/manager.py`** - XG state management
5. **`synth/xg/drum_manager.py`** - Drum parameter handling
6. **`config.yaml`** - Configuration file for synthesizer settings

## Performance Considerations

1. The synthesizer uses parameter caching to avoid repeated computations
2. Memory pooling is used for object reuse to reduce allocation overhead
3. Sample-accurate processing ensures precise timing but requires more CPU
4. Polyphony is limited to prevent excessive memory usage

## Keyboard Controls

During conversion, the following keyboard controls work:
- **Space** - Stop conversion gracefully
- **Ctrl+C** - Force quit conversion

## Documentation Files

The project includes several important documentation files:
- `TECHNICAL_XG_ANALYSIS.md` - Detailed technical analysis of XG conformance issues
- `XG_CONFORMANCE_ANALYSIS.md` - Analysis of MIDI XG standard conformance
- `XG_IMPLEMENTATION_PLAN.md` - Detailed implementation plan for XG features
- `XG_IMPLEMENTATION_ROADMAP.md` - Implementation roadmap with timeline and priorities