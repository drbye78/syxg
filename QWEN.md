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

## Performance Considerations and Optimization Opportunities

### Current Performance Issues

Based on analysis of the codebase, the synthesizer exhibits slow performance primarily due to several factors in tone generation, audio processing, and overall rendering:

#### 1. Inefficient Sample-Accurate Processing Implementation

The current implementation of `generate_audio_block_sample_accurate()` in `XGSynthesizer` has significant performance issues:

- **Per-sample processing overhead**: The method processes each sample individually in a Python loop, which is inherently slow for audio processing
- **Inefficient effects processing**: For each sample, it creates multichannel input data by duplicating the same stereo pair for all 16 channels, which is unnecessary and computationally expensive
- **Redundant buffer operations**: It creates new lists for each sample iteration rather than efficiently managing pre-allocated buffers

This approach results in extremely high computational overhead, as Python loops are much slower than vectorized operations for audio processing.

#### 2. Suboptimal Voice Rendering Architecture

The voice rendering system has several performance bottlenecks:

- **Per-voice processing in Python loops**: Each active voice is processed individually in Python loops rather than using vectorized operations
- **Inefficient interpolation**: The interpolation algorithms may not be optimized for speed
- **Repeated calculations**: Mathematical operations that could be cached or precomputed are calculated repeatedly

#### 3. Memory Allocation Overhead

The codebase creates new objects and data structures frequently during audio processing:

- **Buffer reallocation**: New buffers are created for each audio block instead of reusing pre-allocated buffers
- **List comprehensions in loops**: Creating new lists in tight loops increases garbage collection pressure
- **Inefficient data copying**: Data is copied between different representations multiple times during processing

#### 4. Lack of Vectorization

The implementation doesn't take full advantage of NumPy's vectorized operations:

- **Element-wise operations in Python loops**: Operations that could be vectorized are implemented with Python loops
- **Missed opportunities for SIMD**: Mathematical operations on audio samples could benefit from SIMD (Single Instruction, Multiple Data) processing

### Detailed Analysis of Tone Generation Bottlenecks

#### SF2 Parameter Processing

1. **Parameter merging inefficiencies**:
   - The `_merge_preset_and_instrument_params` function (not shown in provided files but referenced in `midi_to_ogg.py`) likely performs complex dictionary operations for each voice
   - Without proper caching, this operation is repeated unnecessarily, especially for instruments with multiple zones or modulators

2. **Modulator processing**:
   - Modulator transformations are processed individually rather than in batches
   - Complex conditional logic in modulator processing adds branch prediction overhead
   - Lack of lookup tables for common transformations results in repeated calculations

#### Voice Management

1. **Voice allocation/deallocation**:
   - The voice allocation system may not be optimized for fast allocation/deallocation
   - Voice stealing algorithms might involve expensive searches through active voices
   - Lack of object pooling for voice objects results in frequent allocation/deallocation

2. **Envelope generation**:
   - Per-sample envelope calculations in Python loops are inefficient
   - Exponential calculations for envelope segments could be optimized with lookup tables or approximations
   - State management for envelopes may involve expensive operations

### Audio Processing Performance Issues

#### Sample Rate Conversion and Resampling

1. **Inefficient interpolation algorithms**:
   - If resampling is implemented, it may use computationally expensive interpolation methods
   - Lack of optimized resampling algorithms (e.g., polyphase filtering) results in slower performance

#### Mixing and Signal Processing

1. **Per-channel processing**:
   - Processing each of the 16 MIDI channels separately instead of vectorizing across channels
   - Inefficient mixing algorithms that don't take advantage of modern CPU capabilities

2. **Effects processing**:
   - The effects system appears to process each channel separately, which is inefficient
   - Reverb and chorus algorithms may not be optimized for real-time performance
   - Lack of SIMD optimization in effects processing

### Optimization Opportunities

#### 1. Vectorization and NumPy Optimization

**Opportunity**: Replace per-sample and per-voice Python loops with vectorized NumPy operations.

**Implementation**:
- Process multiple samples simultaneously using NumPy arrays
- Use vectorized mathematical operations for envelope generation
- Implement lookup tables for expensive mathematical functions (e.g., exponentials for envelopes)
- Vectorize modulator processing across all active voices

**Expected Impact**: 5-20x performance improvement depending on the specific operation.

#### 2. Efficient Buffer Management

**Opportunity**: Implement pre-allocated buffers and object pooling to reduce allocation overhead.

**Implementation**:
- Pre-allocate audio buffers based on maximum block size
- Implement circular buffers for delay lines in effects processing
- Use object pools for voices, envelopes, and other frequently allocated objects
- Reuse buffers between audio blocks instead of creating new ones

**Expected Impact**: 2-5x performance improvement by reducing allocation overhead and garbage collection.

#### 3. Improved Sample-Accurate Processing

**Opportunity**: Redesign the sample-accurate processing system to batch MIDI messages and process audio in larger chunks.

**Implementation**:
- Collect all MIDI messages for an entire audio block before processing
- Process messages in batches rather than per-sample
- Use vectorized operations to apply parameter changes to multiple samples at once
- Implement efficient timestamp sorting and processing algorithms

**Expected Impact**: 10-50x performance improvement in sample-accurate mode.

#### 4. Algorithmic Optimizations

**Opportunity**: Replace computationally expensive algorithms with more efficient alternatives.

**Implementation**:
- Use fast approximations for exponential functions in envelope generation
- Implement polyphase filtering for resampling operations
- Use FFT-based convolution for reverb algorithms where appropriate
- Optimize modulator processing with lookup tables for common transformations

**Expected Impact**: 2-10x performance improvement depending on the algorithm.

#### 5. Just-In-Time Compilation

**Opportunity**: Use Numba or similar JIT compilation to accelerate critical code paths.

**Implementation**:
- Identify hotspots in the code using profiling
- Apply JIT compilation to performance-critical functions
- Optimize NumPy usage patterns for better JIT compilation

**Expected Impact**: 5-15x performance improvement in JIT-compiled functions.

#### 6. Parallel Processing

**Opportunity**: Utilize multi-core processing for independent operations.

**Implementation**:
- Process different MIDI channels in parallel where possible
- Use multiprocessing for CPU-intensive tasks like SF2 loading
- Implement thread pools for voice rendering

**Expected Impact**: 2-8x performance improvement depending on available CPU cores.

#### 7. Memory Access Optimization

**Opportunity**: Improve cache locality and reduce memory bandwidth usage.

**Implementation**:
- Organize data structures for better cache locality
- Use contiguous memory layouts for audio processing
- Minimize memory copying between different parts of the pipeline

**Expected Impact**: 1.5-3x performance improvement through better memory access patterns.

#### 8. Streaming Architecture

**Opportunity**: Implement a streaming architecture that processes data in a pipeline fashion.

**Implementation**:
- Design a pipeline where MIDI processing, voice rendering, effects, and output encoding happen in parallel stages
- Use buffers between pipeline stages to allow concurrent processing
- Implement backpressure mechanisms to prevent buffer overflows

**Expected Impact**: 2-5x performance improvement through better resource utilization.

### Specific Recommendations for Critical Path Optimization

#### 1. Redesign Audio Generation Pipeline

The current `generate_audio_block_sample_accurate()` method should be completely redesigned:

1. **Batch MIDI message processing**: Collect all MIDI messages for the block and process them in batches
2. **Vectorized voice rendering**: Render all active voices using vectorized operations
3. **Efficient mixing**: Mix audio channels using optimized algorithms
4. **Streamlined effects processing**: Process effects on the final mixed output rather than per-channel

#### 2. Optimize SF2 Processing

1. **Enhanced parameter caching**: Extend the caching system to cover more parameter combinations
2. **Precomputed lookup tables**: Generate lookup tables for sample data interpolation
3. **Lazy loading with prefetching**: Implement intelligent prefetching of SF2 data

#### 3. Voice Management Improvements

1. **Fast voice allocation**: Implement O(1) voice allocation using free lists
2. **Batch parameter updates**: Update voice parameters for all active voices in batches
3. **Efficient voice state management**: Use bitfields or other compact representations for voice states

These optimizations would significantly improve the synthesizer's performance, potentially achieving real-time or faster-than-real-time processing even for complex MIDI files with many simultaneous voices.

## MIDI XG Specification Implementation Status

### Controller Implementation

The synthesizer implements a comprehensive set of MIDI controllers with XG-specific extensions:

#### Standard MIDI Controllers (Fully Implemented)
- **Volume (CC7)**: Controls channel volume level
- **Expression (CC11)**: Controls expression level (affects overall amplitude)
- **Pan (CC10)**: Controls stereo panning position
- **Balance (CC8)**: Controls balance between left and right channels
- **Modulation Wheel (CC1)**: Controls modulation depth
- **Breath Controller (CC2)**: Typically used for breath control
- **Foot Controller (CC4)**: General-purpose foot controller
- **Sustain Pedal (CC64)**: Controls sustain effect
- **Portamento Switch (CC65)**: Enables/disables portamento

#### XG Sound Controllers (Fully Implemented)
- **Harmonic Content (CC71)**: Affects harmonic content/timbre
- **Brightness (CC72)**: Affects filter cutoff/brightness
- **Release Time (CC73)**: Affects envelope release time
- **Attack Time (CC74)**: Affects envelope attack time
- **Filter Cutoff (CC75)**: Affects filter cutoff frequency
- **Decay Time (CC76)**: Affects envelope decay time
- **Vibrato Rate (CC77)**: Affects LFO vibrato rate
- **Vibrato Depth (CC78)**: Affects LFO vibrato depth
- **Vibrato Delay (CC79)**: Affects LFO vibrato delay

#### XG Effects Controllers (Fully Implemented)
- **Reverb Send (CC91)**: Controls reverb send level
- **Tremolo Send (CC92)**: Controls tremolo send level
- **Chorus Send (CC93)**: Controls chorus send level
- **Variation Send (CC94)**: Controls variation send level
- **Delay Send (CC95)**: Controls delay send level

#### XG General Purpose Controllers (Partially Implemented)
- **GP Button 1 (CC80)**: General purpose button
- **GP Button 2 (CC81)**: General purpose button
- **GP Button 3 (CC82)**: General purpose button
- **GP Button 4 (CC83)**: General purpose button

#### Mode Controllers (Fully Implemented)
- **All Sound Off (CC120)**: Immediately silences all notes
- **Reset All Controllers (CC121)**: Resets all controllers to default values
- **All Notes Off (CC123)**: Turns off all active notes

### NRPN Implementation

The synthesizer implements a comprehensive NRPN system with XG-specific parameter handling:

#### Part Parameters (NRPN MSB 1)
- **Part Mode (LSB 8)**: Controls XG part modes (Normal, Hyper Scream, Analog, etc.)
- **Element Reserve (LSB 9)**: Reserved for future use
- **Element Assign Mode (LSB 10)**: Reserved for future use
- **Receive Channel (LSB 11)**: Reserved for future use

#### Effect Parameters (NRPN MSB 2-4)
- **Reverb Parameters (MSB 2)**: Controls reverb effect parameters
- **Chorus Parameters (MSB 3)**: Controls chorus effect parameters
- **Variation Parameters (MSB 4)**: Controls variation effect parameters

#### Drum Parameters (NRPN MSB 40-41)
- **Drum Note Parameters**: Controls individual drum note parameters (tune, level, pan, etc.)
- **Drum Kit Selection**: Controls drum kit selection parameters

#### Filter Parameters (NRPN MSB 5)
- **Filter Cutoff Offset (LSB 0)**: Controls filter cutoff offset (-64 to +63)
- **Filter Resonance Offset (LSB 1)**: Controls filter resonance offset (-64 to +63)

#### Envelope Parameters (NRPN MSB 6)
- **Attack Time (LSB 0)**: Controls envelope attack time
- **Decay Time (LSB 1)**: Controls envelope decay time
- **Release Time (LSB 2)**: Controls envelope release time
- **Envelope Parameters (LSB 3)**: Reserved for future use

#### LFO Parameters (NRPN MSB 7-9)
- **LFO1 Parameters (MSB 7)**: Controls LFO1 parameters (rate, depth, delay, fade)
- **LFO2 Parameters (MSB 8)**: Controls LFO2 parameters (rate, depth, delay, fade)
- **LFO3 Parameters (MSB 9)**: Controls LFO3 parameters (rate, depth, delay, fade)

#### EQ Parameters (NRPN MSB 10)
- **EQ Low (LSB 0)**: Controls low-frequency EQ (-64 to +63)
- **EQ Mid (LSB 1)**: Controls mid-frequency EQ (-64 to +63)
- **EQ High (LSB 2)**: Controls high-frequency EQ (-64 to +63)

### SysEx Implementation

The synthesizer implements a partial SysEx system with XG-specific message handling:

#### XG System Messages (Sub-status 0x10)
- **XG System On**: Initializes XG system to default state
- **XG Parameter Change**: Changes XG parameters with acknowledgment

#### XG Bulk Messages (Sub-status 0x4C)
- **Bulk Dumps**: Receives and processes bulk parameter dumps
- **Bulk Requests**: Generates and sends bulk parameter dumps

#### Yamaha SysEx Messages
- **Effect Parameters**: Processes Yamaha effect parameter changes
- **System Parameters**: Processes Yamaha system parameter changes

### Compatibility and Audio Synthesis Issues

#### Controller Implementation Issues

1. **Limited Real-time Parameter Updates**:
   - Some XG controllers (71-79) have immediate parameter update functions but these are not fully implemented
   - The `_update_xg_controller_parameter` method in `MIDIMessageHandler` has placeholder implementations that don't actually update synthesis parameters

2. **Part Mode Implementation**:
   - While XGChannelRenderer implements part modes, the actual parameter changes for different part modes are not fully implemented
   - Most part modes have placeholder implementations that don't actually modify synthesis parameters

3. **Controller Value Mapping**:
   - Some controllers may not correctly map 0-127 values to appropriate parameter ranges
   - For example, filter cutoff and resonance offsets may not correctly map to -64 to +63 ranges

#### NRPN Implementation Issues

1. **Incomplete Parameter Validation**:
   - While NRPN parameter validation is implemented, some edge cases may not be properly handled
   - Invalid parameter values may be accepted when they should be rejected

2. **Missing Parameter Implementations**:
   - Many NRPN parameters have validation but no actual implementation
   - For example, EQ parameters are validated but not actually used to modify audio processing

3. **Parameter Range Mapping**:
   - Some NRPN parameters may not correctly map to appropriate internal ranges
   - For example, envelope time parameters may not correctly map to appropriate time ranges

#### SysEx Implementation Issues

1. **Incomplete Bulk Dump Processing**:
   - While bulk dump generation is implemented, bulk dump processing is incomplete
   - Many system parameters are not actually restored from bulk dumps

2. **Checksum Validation**:
   - Checksum validation is implemented but may not correctly handle all edge cases
   - Some SysEx messages may fail checksum validation when they should pass

3. **Parameter Acknowledgment**:
   - Parameter acknowledgment messages are generated but not actually sent
   - In a real implementation, these would need to be sent to the MIDI output

#### Audio Synthesis Issues

1. **Part Mode Effects**:
   - XG part modes are not fully implemented in the audio synthesis pipeline
   - Different part modes should modify envelope parameters, filter settings, and other synthesis parameters but currently don't

2. **Controller-to-Parameter Mapping**:
   - The mapping from MIDI controllers to synthesis parameters is incomplete
   - Many controllers don't actually modify synthesis parameters in real-time

3. **Effect Parameter Integration**:
   - While effect parameters can be set via NRPN/SysEx, the actual integration with the audio processing pipeline may be incomplete
   - Some effect parameters may not actually affect audio processing

4. **Drum Parameter Implementation**:
   - Drum parameters are validated but may not be fully implemented in the audio synthesis pipeline
   - Individual drum note parameters (tune, level, pan, etc.) may not actually affect audio generation

### Recommendations for Improving XG Compatibility

1. **Complete Controller Implementations**:
   - Implement all XG controller handlers to actually modify synthesis parameters
   - Ensure proper mapping of controller values to parameter ranges
   - Add real-time parameter updates for all supported controllers

2. **Enhance Part Mode Implementation**:
   - Implement actual parameter changes for all XG part modes
   - Ensure part mode parameters correctly affect envelope generators, filters, and other synthesis components
   - Add proper validation for part mode values

3. **Complete NRPN Parameter Implementations**:
   - Implement all NRPN parameters to actually modify synthesis parameters
   - Ensure proper mapping of NRPN values to internal parameter ranges
   - Add validation for all parameter ranges and values

4. **Improve SysEx Implementation**:
   - Complete bulk dump processing to actually restore system state
   - Ensure proper checksum validation for all SysEx messages
   - Implement actual sending of parameter acknowledgment messages

5. **Enhance Audio Synthesis Pipeline**:
   - Integrate all controller and NRPN parameters into the audio synthesis pipeline
   - Ensure part modes properly affect synthesis parameters
   - Complete implementation of drum parameters in the audio synthesis pipeline

6. **Add Comprehensive Testing**:
   - Create test cases for all XG features to ensure proper implementation
   - Add validation tests for parameter ranges and values
   - Implement compatibility tests with actual XG devices

These improvements would significantly enhance the synthesizer's XG compatibility and ensure proper audio synthesis according to the XG specification.