# XG Synthesizer - MIDI to OGG Converter

## Overview

This project is a complete MIDI to OGG converter with a built-in XG-compatible software synthesizer. It's designed to convert MIDI files into high-quality audio by rendering them using a sophisticated synthesis engine that supports the Yamaha XG standard.

The synthesizer features a channel-based architecture using persistent `XGChannelRenderer` instances for improved performance and resource management. It also supports multi-port MIDI rendering, allowing you to handle multiple simultaneous MIDI streams.

## Key Features

### Core Synthesis Features
- ✅ **Complete MIDI XG Standard Support**: All standard MIDI messages, SysEx, and NRPN parameters
- ✅ **Advanced Tone Generation**: Multi-LFO, ADSR envelopes, resonant filters, modulation matrix
- ✅ **Channel-Based Architecture**: Persistent channel renderers for improved performance
- ✅ **Multi-Port MIDI Support**: Handle multiple MIDI ports with independent channel sets
- ✅ **Key Pressure (Polyphonic Aftertouch)**: Complete per-note aftertouch support
- ✅ **Complete Portamento Functionality**: Smooth frequency sliding with configurable time
- ✅ **Extended XG Controllers**: Support for all XG controllers (75, 76, 80-83, 91, 93-95)
- ✅ **Mono/Poly Mode Switching**: Proper handling of mono/poly mode with note stealing
- ✅ **Balance Controller**: Combined pan/balance stereo positioning

### Advanced Features
- ✅ **Modulation Matrix**: Full 16-route modulation matrix with extensive source/destination support
- ✅ **LFO System**: Three LFOs with multiple waveform types and modulation capabilities
- ✅ **Envelope Generators**: ADSR envelopes for amplitude, filter, and pitch with extensive modulation
- ✅ **Filter Processing**: Resonant filters with stereo width and panning
- ✅ **Partial Structure**: Multi-layer sound generation with crossfading
- ✅ **Drum Parameters**: Complete drum instrument parameter control
- ✅ **Effects Processing**: Reverb, chorus, and variation effects with parameter control
- ✅ **SoundFont 2.0 Support**: Full support for SF2 files with proper generator/modulator handling

## Files

- `xg_synthesizer.py`: Main synthesizer engine implementing the Yamaha XG standard
- `tg.py`: Contains the `XGChannelRenderer` class for channel-based tone generation
- `sf2.py`: SoundFont 2.0 file loader and parser with wavetable management
- `fx.py`: Effect processing system (Reverb, Chorus, etc.)
- `midi_to_ogg.py`: Main command-line utility for converting MIDI to OGG
- `config.yaml`: Configuration file for audio settings and SoundFont files

## Usage

### Command Line Usage

```bash
# Basic conversion
python midi_to_ogg.py input.mid output.ogg

# With specific options
python midi_to_ogg.py --sf2 my_soundfont.sf2 --sample-rate 48000 input.mid output.ogg

# Show all options
python midi_to_ogg.py -h
```

### Programmatic Usage

```python
from xg_synthesizer import XGSynthesizer

# Create synthesizer with default 2 ports (32 MIDI channels)
synth = XGSynthesizer(sample_rate=48000, block_size=960)  # 20ms blocks at 48kHz

# Create synthesizer with custom number of ports
synth = XGSynthesizer(sample_rate=48000, block_size=960, num_ports=4)  # 4 ports (64 MIDI channels)

# Send MIDI messages
synth.send_midi_message(0x90, 60, 100)  # Note On: C4, velocity 100 on channel 1 (port 0)
synth.send_midi_message(0x80, 60, 64)   # Note Off: C4, velocity 64 on channel 1 (port 0)

# Send MIDI message to specific port
synth.send_midi_message_to_port(0, 0x90, 60, 100)  # Send to port 0, channel 1
synth.send_midi_message_to_port(1, 0x90, 65, 100)  # Send to port 1, channel 1

# Generate audio
left_channel, right_channel = synth.generate_audio_block(960)
```

## Configuration

The `config.yaml` file controls synthesizer settings:

```yaml
# Audio settings
sample_rate: 44100
block_size: 512
max_polyphony: 512
master_volume: 1.0

# SoundFont files
sf2_files:
  - "path/to/soundfont.sf2"

# Optional bank/preset blacklists and mappings
```

## Multi-Port MIDI Support

The synthesizer supports multiple MIDI ports, each with its own set of 16 MIDI channels:

- **Default Configuration**: 2 ports (32 MIDI channels total)
- **Custom Configuration**: Specify any number of ports when creating the synthesizer
- **Port Addressing**: Send messages to specific ports using `send_midi_message_to_port()`
- **Independent Processing**: Each port's channels are processed independently
- **Drum Channels**: Each port has its own drum channel (channel 10, 0-indexed as channel 9)

## Performance Benefits

### Channel-Based Architecture
- **Reduced Object Creation**: Persistent channel renderers instead of per-note generators
- **Efficient State Management**: Channel-wide state maintained in one location
- **Better Resource Utilization**: Significantly reduced memory allocation and garbage collection pressure

### Memory Efficiency
- Efficient memory usage with persistent channel renderers
- Reduced garbage collection pressure
- SoundFont sample caching for improved performance

### CPU Efficiency
- Eliminated redundant initialization and cleanup operations
- Better cache locality with channel-level data kept together
- Faster message processing with improved state management

## Compatibility

The implementation maintains full compatibility with:
- MIDI XG standard
- SoundFont 2.0 files
- All MIDI message types
- Yamaha SysEx messages
- NRPN parameter system

## License

This implementation is provided as open source software under the MIT license.