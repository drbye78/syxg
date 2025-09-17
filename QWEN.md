# XG Synthesizer Project - Context for Qwen Code

## Project Overview

This is a fully MIDI XG compatible software synthesizer implemented in Python. The synthesizer can convert MIDI files to audio formats (OGG/Opus or WAV) using SoundFont 2.0 files as the sound source. The project includes an optimized converter with performance improvements for efficient processing of MIDI files.

### Key Features

- **Full MIDI XG Compatibility**: Implements all MIDI messages including SYSEX and Bulk SYSEX
- **Audio Generation**: Generates audio in blocks of arbitrary size with support for different sample rates
- **Polyphony Management**: Configurable maximum polyphony with voice allocation
- **SoundFont 2.0 Support**: Uses SF2 files for tone generation with support for bank blacklists, preset blacklists, and bank mapping
- **Effect Processing**: Includes reverb, chorus, and other audio effects
- **Sample-Accurate Processing**: Supports both immediate and buffered operation modes with frame-by-frame MIDI message processing
- **Cross-Platform**: Works on Windows, Linux, and macOS

## Project Structure

```
/mnt/c/Work/guga/syxg/
├── config.yaml                 # Configuration file for audio settings and SF2 files
├── midi_to_ogg.py             # Main script to convert MIDI files to OGG/WAV
├── synth/                     # Core synthesizer modules
│   ├── core/                  # Core synthesizer components
│   ├── sf2/                   # SoundFont 2.0 handling
│   ├── xg/                    # XG-specific functionality
│   ├── midi/                  # MIDI message handling
│   ├── audio/                 # Audio engine and processing
│   ├── effects/               # Audio effects processing
│   └── ...                    # Other specialized modules
└── tests/                     # Test MIDI files and SoundFont files
```

## Core Components

### XGSynthesizer (synth/core/synthesizer.py)
The main synthesizer class that orchestrates all modules:
- Handles all MIDI messages and SYSEX processing
- Manages audio generation in blocks
- Supports sample-accurate processing with buffered mode
- Integrates with SF2 manager for sound generation
- Manages effects processing

### SF2 Manager (synth/sf2/manager.py)
Manages SoundFont 2.0 files:
- Loads and processes SF2 files
- Handles bank and preset blacklisting
- Supports bank mapping
- Provides program and drum parameters

### MIDI Processing
- BufferedProcessor: Handles timestamped MIDI messages for sample-accurate processing
- MIDIMessageHandler: Processes incoming MIDI messages

### Audio Engine
- Generates audio blocks from active channel renderers
- Applies effects processing
- Handles sample rate conversion

## Configuration

The `config.yaml` file controls the synthesizer settings:

```yaml
# Audio settings
sample_rate: 48000     # Audio sample rate (Hz)
block_size: 960        # Audio block size (samples)
max_polyphony: 512     # Maximum simultaneous voices
master_volume: 1.0     # Master volume (0.0-1.0)

# SoundFont files
sf2_files:
  - "tests/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"

# Optional blacklists and mappings
# bank_blacklists:     # Exclude specific banks from SF2 files
# preset_blacklists:   # Exclude specific presets from SF2 files
# bank_mappings:       # Map MIDI banks to SF2 banks
```

## Usage

### Command Line Interface

Convert MIDI to OGG/WAV:
```bash
# Basic conversion
python midi_to_ogg.py input.mid output.ogg

# With configuration file
python midi_to_ogg.py -c config.yaml input.mid output.ogg

# Specify SoundFont file
python midi_to_ogg.py --sf2 soundfont.sf2 input.mid output.ogg

# Set sample rate
python midi_to_ogg.py --sample-rate 48000 input.mid output.ogg

# Silent mode (no console output)
python midi_to_ogg.py --silent input.mid output.ogg

# Multiple input files
python midi_to_ogg.py --format wav file1.mid file2.mid output_directory/
```

### Keyboard Controls (during conversion)
- SPACE: Stop conversion gracefully
- Ctrl+C: Force quit conversion

### Advanced Options
- `--chunk-size-ms`: Audio processing chunk size in milliseconds
- `--polyphony`: Maximum polyphony
- `--volume`: Master volume (0.0-1.0)
- `--tempo`: Tempo ratio (default: 1.0 = original tempo)
- `--format`: Output format (wav or ogg)

## Dependencies

The project requires the following Python packages:
- `mido`: MIDI processing library
- `numpy`: Numerical computing
- `opuslib`: Opus audio codec
- `pyyaml`: YAML configuration parsing
- Platform-specific modules:
  - Windows: `msvcrt`
  - Unix/Linux/macOS: `select`, `termios`, `tty`

## Performance Optimizations

The optimized version includes several performance improvements:
1. SF2 parameter caching to reduce repeated computations
2. Memory pooling for object reuse
3. Batched modulator processing
4. Optimized attribute access patterns
5. Lazy loading of SF2 data
6. Vectorized block processing for improved performance

## Development Guidelines

### Code Structure
- Modular design with separate modules for different functionality
- Thread-safe implementation using locks
- Clear separation between immediate and buffered processing modes
- Extensive error handling and validation

### Testing
- Test with various MIDI files in the `tests/` directory
- Verify audio output quality
- Check performance with large polyphony settings
- Test cross-platform compatibility

### Extending Functionality
- Add new effects in the `effects/` directory
- Extend XG parameter support in the `xg/` modules
- Add new audio processing features in the `audio/` modules