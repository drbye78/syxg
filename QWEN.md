# XG Synthesizer Project

## Project Overview

This is a fully MIDI XG compatible software synthesizer implemented in Python. The synthesizer supports:

- All MIDI messages including SYSEX and Bulk SYSEX
- Audio generation in blocks of arbitrary size
- Configurable maximum polyphony
- Full tone generation control
- Effect processing (reverb, chorus)
- SF2 file management with blacklists and bank mapping
- Initialization according to MIDI XG standard
- Full XG drum parameter support
- Both immediate and buffered operation modes with sample-accurate timing synchronization

The synthesizer can convert MIDI files to OGG or WAV audio formats with high-quality sound rendering.

## Building and Running

### Prerequisites

- Python 3.x
- Required Python packages (install via pip):
  - mido
  - numpy
  - pyyaml
  - opuslib
  - line_profiler

### Installation

1. Install the required Python packages:
   ```bash
   pip install mido numpy pyyaml opuslib line_profiler
   ```

### Running the Converter

The main entry point is `midi_to_ogg.py`. It can be run from the command line:

```bash
python midi_to_ogg.py [OPTIONS] INPUT_FILE OUTPUT_FILE
```

#### Options:
- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Path to YAML configuration file (default: config.yaml)
- `--sf2 SF2_FILE`: SoundFont (.sf2) file paths (can be used multiple times)
- `--sample-rate SAMPLE_RATE`: Audio sample rate in Hz (default: 48000)
- `--chunk-size-ms CHUNK_SIZE_MS`: Audio processing chunk size in milliseconds (default: 20)
- `--polyphony MAX_POLYPHONY`: Maximum polyphony (default: 64)
- `--volume MASTER_VOLUME`: Master volume (0.0 to 1.0, default: 1.0)
- `--tempo TEMPO_RATIO`: Tempo ratio (default: 1.0 = original tempo)
- `--silent`: Suppress console output during conversion
- `--format {wav,ogg}`: Output audio format (default: ogg)

#### Examples:
```bash
# Basic conversion
python midi_to_ogg.py input.mid output.ogg

# Using a configuration file
python midi_to_ogg.py -c config.yaml input.mid output.ogg

# Using a specific SoundFont file
python midi_to_ogg.py --sf2 soundfont.sf2 input.mid output.ogg

# Setting sample rate to 48kHz
python midi_to_ogg.py --sample-rate 48000 input.mid output.ogg

# Silent conversion
python midi_to_ogg.py --silent input.mid output.ogg
```

### Configuration

The synthesizer can be configured using a YAML configuration file (by default `config.yaml`). The configuration file supports the following parameters:

- `sample_rate`: Audio sample rate in Hz (default: 48000)
- `chunk_size_ms`: Audio processing chunk size in milliseconds (default: 20)
- `max_polyphony`: Maximum polyphony (default: 64)
- `master_volume`: Master volume (0.0 to 1.0, default: 1.0)
- `sf2_files`: List of SoundFont (.sf2) file paths
- `bank_blacklists`: Dictionary mapping SF2 file paths to lists of bank numbers to exclude
- `preset_blacklists`: Dictionary mapping SF2 file paths to lists of (bank, program) tuples to exclude
- `bank_mappings`: Dictionary mapping SF2 file paths to dictionaries that map MIDI banks to SF2 banks

## Testing

For testing purposes, the `tests/` directory contains both MIDI files and SF2 soundfonts that can be used to verify the functionality of the synthesizer. You can use these files to test various aspects of the synthesizer:

```bash
# Test with a MIDI file and SF2 from the tests directory
python midi_to_ogg.py tests/example.mid output.ogg --sf2 tests/Timbres\ Of\ Heaven\ GM_GS_XG_SFX\ V\ 3.4\ Final.sf2
```

## Architecture Description

### Core Components

1. **XGSynthesizer** (`synth/core/synthesizer.py`): 
   - Main orchestrator class that manages all other components
   - Handles initialization according to MIDI XG standard
   - Coordinates between different modules (SF2 manager, state manager, etc.)
   - Provides interface for sending MIDI messages and generating audio

2. **StateManager** (`synth/xg/manager.py`):
   - Manages state for all 16 MIDI channels
   - Handles RPN/NRPN parameter processing
   - Maintains controller values, program changes, pitch bend, etc.
   - Stores voice allocation modes and drum parameters

3. **SF2Manager** (`synth/sf2/manager.py`):
   - Manages loading and processing of SoundFont files
   - Handles preset blacklists and bank mappings
   - Provides interface for accessing instrument samples and parameters
   - Implements lazy loading and caching mechanisms for performance

4. **AudioEngine** (`synth/audio/engine.py`):
   - Generates audio blocks from active voices
   - Mixes audio from different channels
   - Applies master volume processing
   - Handles audio buffering and sample rate conversion

5. **BufferedProcessor** (`synth/midi/buffered_processor.py`):
   - Implements sample-accurate MIDI message processing
   - Buffers messages with timestamps for precise timing
   - Processes messages at the correct sample time during audio generation
   - Supports both immediate and buffered operation modes

6. **XGChannelRenderer** (`synth/xg/channel_renderer.py`):
   - Renders audio for individual MIDI channels
   - Handles program changes and instrument selection
   - Processes MIDI messages for specific channel parameters
   - Manages drum channel enhancements for XG compatibility

7. **XGEffectManager** (`synth/effects/core.py`):
   - Manages audio effects processing (reverb, chorus)
   - Handles effect parameter control via NRPN messages
   - Processes SYSEX messages for effect configuration
   - Applies effects to audio channels with proper send levels

8. **Voice Management** (`synth/voice/`):
   - Handles polyphony and voice allocation
   - Manages individual voice rendering
   - Implements voice stealing algorithms when needed
   - Processes envelope generators and filters for each voice

9. **Modulation System** (`synth/modulation/`):
   - Processes modulator parameters from SF2 files
   - Handles modulation sources and destinations
   - Implements modulation transformations and scaling

### Data Flow

1. **Initialization**:
   - XGSynthesizer initializes all components
   - SF2Manager loads SoundFont files
   - StateManager sets up default channel states
   - EffectManager initializes default effect parameters

2. **MIDI Message Processing**:
   - Messages received via `send_midi_message()` or buffered via `send_midi_message_at_time()`
   - BufferedProcessor handles timestamped messages for sample-accurate processing
   - Messages are dispatched to appropriate channel renderers
   - StateManager updates channel states accordingly

3. **Audio Generation**:
   - Audio blocks generated via `generate_audio_block()` or `generate_audio_block_sample_accurate()`
   - Each channel renderer generates audio based on active voices
   - AudioEngine mixes all channel outputs
   - EffectManager processes audio with applied effects
   - Final mixed audio is returned as numpy arrays

### Module Interactions

- **XGSynthesizer** acts as the central hub, coordinating all other components
- **SF2Manager** provides wavetable data to **XGChannelRenderer** instances
- **StateManager** maintains state that is accessed by both **XGSynthesizer** and **XGChannelRenderer**
- **BufferedProcessor** feeds timestamped MIDI messages back to **XGSynthesizer** during sample-accurate processing
- **XGEffectManager** receives NRPN/SYSEX messages from **XGSynthesizer** and processes audio from **AudioEngine**

## Performance Considerations

The synthesizer includes several key performance optimizations:

### 1. SF2 Parameter Caching
- Implements `ParameterCache` in `midi_to_ogg.py` to avoid repeated computations of merged preset and instrument parameters
- Reduces calls to `_merge_preset_and_instrument_params` by caching results based on hashable parameter keys
- Significantly improves performance when the same instrument parameters are used multiple times

### 2. Memory Pooling
- Uses `MemoryPool` class to reuse objects like modulator and zone dictionaries
- Reduces allocation overhead by reusing objects instead of creating new ones
- Implemented for both modulator and zone objects with configurable pool sizes

### 3. Optimized Attribute Access
- Batched modulator processing to reduce per-sample overhead
- Direct attribute access patterns instead of method calls where possible
- Reduced number of function calls in critical audio generation paths

### 4. Lazy Loading
- SF2 data is loaded on-demand rather than all at initialization
- Reduces memory footprint and startup time
- Only loads instrument data when actually needed for sound generation

### 5. Sample-Accurate Processing
- Implements frame-by-frame MIDI message processing for precise timing
- Each audio sample is processed separately with checking for MIDI messages at that moment
- Uses efficient heap-based buffering for timestamped messages

### 6. Efficient Data Structures
- Uses numpy arrays for audio processing to leverage optimized C implementations
- Implements efficient sorting and searching for MIDI messages
- Uses threading locks only where necessary to minimize contention

### 7. Optimized Configuration
- Default sample rate set to 48kHz (higher quality than standard 44.1kHz)
- Block size optimized for performance (512 samples by default)
- Chunk size configurable in milliseconds for Opus encoding optimization

### 8. Profiling-Driven Optimizations
- Includes line profiler integration for performance analysis
- Identifies and optimizes bottlenecks in critical code paths
- Regular performance monitoring and optimization

These optimizations work together to provide real-time or faster-than-real-time MIDI to audio conversion while maintaining high audio quality and full XG compatibility.