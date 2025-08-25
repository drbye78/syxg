# XG Synthesizer Documentation

## Overview

The XG Synthesizer is a comprehensive MIDI XG compatible software synthesizer implemented in Python. It provides full support for:

- All MIDI messages including SYSEX and Bulk SYSEX
- Audio generation in configurable block sizes
- Maximum polyphony control
- Tone generation parameter control
- Effect processing
- SF2 file management with blacklists and bank mapping
- XG initialization according to the MIDI XG standard

## Installation

```bash
pip install numpy pygame
```

Note: This is a pure Python implementation, no additional compilation is required.

## Basic Usage

### Creating a Synthesizer Instance

```python
from xg_synthesizer import XGSynthesizer

# Create synthesizer with default parameters
synth = XGSynthesizer(
    sample_rate=44100,     # Audio sample rate
    block_size=512,        # Audio block size in samples
    max_polyphony=64       # Maximum simultaneous voices
)

# Set master volume (0.0 to 1.0)
synth.set_master_volume(0.8)
```

### Loading SoundFonts

```python
# Load SF2 files
sf2_paths = [
    "path/to/FluidR3_GM.sf2",
    "path/to/GeneralUserGS.sf2"
]
synth.set_sf2_files(sf2_paths)

# Configure blacklists for specific SF2 files
synth.set_bank_blacklist("path/to/FluidR3_GM.sf2", [120, 121, 122])
synth.set_preset_blacklist("path/to/FluidR3_GM.sf2", [(0, 30), (0, 31)])

# Configure bank mapping
synth.set_bank_mapping("path/to/FluidR3_GM.sf2", {1: 0, 2: 1})
```

### Sending MIDI Messages

```python
# Send basic MIDI messages
synth.send_midi_message(0x90, 60, 100)  # Note On: C4, velocity 100 on channel 0
synth.send_midi_message(0x80, 60, 64)   # Note Off: C4 on channel 0
synth.send_midi_message(0xC0, 0)        # Program Change: Piano on channel 0
synth.send_midi_message(0xB0, 7, 100)   # Control Change: Volume = 100 on channel 0

# Send SYSEX messages
xg_sys_on = [0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7]
synth.send_sysex(xg_sys_on)
```

### Generating Audio

```python
# Generate audio block
left_channel, right_channel = synth.generate_audio_block(1024)  # 1024 samples

# Process the audio data (values are in range [-1.0, 1.0])
print(f"Generated {len(left_channel)} stereo samples")
print(f"Left channel range: {min(left_channel):.3f} to {max(left_channel):.3f}")
```

## Advanced Features

### Polyphony Control

```python
# Set maximum polyphony
synth.set_max_polyphony(128)

# Get active voice count
active_voices = synth.get_active_voice_count()
print(f"Active voices: {active_voices}")
```

### Program Management

```python
# Get list of available programs
programs = synth.get_available_programs()
for bank, program, name in programs[:10]:  # First 10 programs
    print(f"Bank {bank}, Program {program}: {name}")
```

### Effect Processing

```python
# The synthesizer includes built-in effect processing
# Effects can be controlled via MIDI messages and SYSEX

# Enable/disable effects
synth.send_midi_message(0xB0, 91, 40)  # Reverb Send = 40
synth.send_midi_message(0xB0, 93, 20)  # Chorus Send = 20
```

## XG Standard Compliance

The synthesizer implements the Yamaha XG standard including:

- **System Exclusive Messages**: XG System On, Parameter Changes, Bulk Parameter Dumps
- **Control Changes**: All standard XG controllers
- **Program Changes**: Bank selection and program switching
- **RPN/NRPN**: Registered and Non-Registered Parameter Numbers
- **Effects**: Reverb, Chorus, Variation effects with XG parameters
- **Controllers**: Mod Wheel, Breath Controller, Foot Controller, etc.
- **Drum Mode**: Special handling for drum channels (typically channel 10)

## Performance Considerations

### Memory Management

The synthesizer uses efficient caching mechanisms:

- Sample cache with LRU eviction policy
- Configurable cache size limits
- Lazy loading of samples from SF2 files

### Real-time Performance

For optimal real-time performance:

```python
# Use larger block sizes for better performance
synth = XGSynthesizer(block_size=1024)  # Larger blocks reduce overhead

# Limit polyphony appropriately
synth.set_max_polyphony(64)  # Balance quality and performance

# Pre-load frequently used SF2 files
synth.set_sf2_files(["essential_soundfonts.sf2"])
```

## Integration Examples

### With PyGame for MIDI Input

```python
import pygame.midi

# Initialize PyGame MIDI
pygame.midi.init()

# Open MIDI input device
midi_input = pygame.midi.Input(0)  # First available device

# Process incoming MIDI messages
while True:
    if midi_input.poll():
        events = midi_input.read(10)  # Read up to 10 events
        for event in events:
            data = event[0]
            status, data1, data2 = data[0], data[1], data[2]
            synth.send_midi_message(status, data1, data2)
```

### With NumPy for Audio Processing

```python
import numpy as np

# Generate audio block
left, right = synth.generate_audio_block(512)

# Convert to NumPy arrays for further processing
left_array = np.array(left, dtype=np.float32)
right_array = np.array(right, dtype=np.float32)

# Apply additional processing (e.g., filtering, effects)
processed_left = np.clip(left_array * 1.2, -1.0, 1.0)  # Simple gain boost
processed_right = np.clip(right_array * 1.2, -1.0, 1.0)
```

## Error Handling

The synthesizer includes comprehensive error handling:

```python
try:
    synth.send_midi_message(0x90, 200, 100)  # Invalid note number
except ValueError as e:
    print(f"MIDI error: {e}")

try:
    synth.set_sf2_files(["nonexistent.sf2"])
except FileNotFoundError as e:
    print(f"File error: {e}")
```

## Configuration Options

### Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sample_rate` | 44100 | Audio sample rate in Hz |
| `block_size` | 512 | Audio processing block size |
| `max_polyphony` | 64 | Maximum simultaneous voices |

### Runtime Configuration

```python
# Adjust parameters during runtime
synth.set_max_polyphony(128)
synth.set_master_volume(0.75)

# Reset to initial state
synth.reset()
```

## Extending the Synthesizer

### Custom Effects

The synthesizer can be extended with custom effects by subclassing or modifying the effect manager.

### Additional SoundFonts

Support for additional SF2 files can be added dynamically:

```python
# Add more SF2 files at runtime
additional_sf2s = ["more_sounds.sf2", "extra_presets.sf2"]
synth.set_sf2_files(current_sf2s + additional_sf2s)
```

## Troubleshooting

### Common Issues

1. **No Audio Output**: Check that SF2 files are properly loaded
2. **Missing Programs**: Verify bank mappings and blacklists
3. **Performance Issues**: Reduce polyphony or increase block size
4. **MIDI Connection Problems**: Check device IDs and permissions

### Debugging

Enable verbose logging to diagnose issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Reference

See the source code documentation for complete API reference.

## License

This implementation is provided as open-source software for educational and research purposes.