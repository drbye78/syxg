# Jupiter-X Synthesizer User Guide

## Overview

The Jupiter-X synthesizer represents the most advanced software synthesizer implementation available, providing complete Roland Jupiter-X compatibility with modern performance capabilities. This guide covers installation, setup, and comprehensive usage instructions.

## System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows 10+
- **CPU**: Quad-core 2.5GHz or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 1GB free space
- **Audio**: ASIO/Core Audio compliant interface

### Recommended Requirements
- **OS**: Linux (Ubuntu 20.04+) or macOS 11+
- **CPU**: 8-core 3.0GHz+ with AVX2 support
- **RAM**: 16GB or higher
- **Storage**: SSD with 2GB+ free space
- **Audio**: Professional audio interface with <3ms latency

## Installation

### From Source
```bash
git clone https://github.com/drbye78/syxg.git
cd syxg
pip install -r requirements.txt
python setup.py develop
```

### Docker Installation
```bash
docker build -t jupiter-x .
docker run -it --device /dev/snd jupiter-x
```

### Verification
```bash
python -c "import synth.jupiter_x; print('Jupiter-X installed successfully')"
```

## Quick Start

### Basic Setup
```python
from synth.jupiter_x import JupiterXSynthesizer

# Initialize synthesizer
synth = JupiterXSynthesizer(sample_rate=44100, buffer_size=1024)

# Enable Jupiter-X features
synth.enable_jupiter_x_mode()

# Start audio processing
synth.start()
```

### Simple Performance
```python
# Note on (middle C, velocity 100)
synth.note_on(60, 100, channel=0)

# Wait for sound
time.sleep(2.0)

# Note off
synth.note_off(60, channel=0)
```

## Architecture Overview

### Synthesis Engines

#### Analog Engine
Classic subtractive synthesis with dual oscillators:
- **Oscillators**: Sawtooth, Square, Triangle, Sine, Noise
- **Filters**: 12dB/octave low-pass with resonance
- **Envelopes**: ADSR with velocity sensitivity
- **LFO**: Per-engine modulation with multiple destinations

#### Digital Engine
Advanced wavetable synthesis:
- **Wavetables**: 12 built-in + custom loading
- **Processing**: Bit crushing, sample rate reduction, wavefolding
- **Morphing**: Real-time wavetable interpolation
- **Formants**: Frequency shifting with resonance

#### FM Engine
6-operator FM synthesis:
- **Algorithms**: 32 classic DX7 algorithms
- **Feedback**: Global and per-operator feedback
- **Ratios**: Precise frequency ratios with detuning
- **Envelopes**: Individual operator envelopes

#### External Engine
Sample playback with advanced processing:
- **Playback Modes**: One-shot, Loop, Ping-pong, Granular
- **Time Stretching**: Independent pitch and time control
- **Granular**: Variable grain size and density
- **Filtering**: Multi-mode filter with envelope control

## Part Configuration

### Basic Part Setup
```python
# Configure part 0 for Jupiter-X Analog engine
synth.set_part_engine(0, 'analog')
synth.set_part_parameter(0, 'volume', 0.8)
synth.set_part_parameter(0, 'pan', 0.0)
```

### Engine-Specific Parameters
```python
# Analog engine configuration
synth.set_engine_parameter(0, 'analog', 'osc1_waveform', 'sawtooth')
synth.set_engine_parameter(0, 'analog', 'filter_cutoff', 0.5)
synth.set_engine_parameter(0, 'analog', 'filter_resonance', 0.3)

# Digital engine configuration
synth.set_engine_parameter(0, 'digital', 'wavetable', 'complex1')
synth.set_engine_parameter(0, 'digital', 'morph_amount', 0.7)

# FM engine configuration
synth.set_engine_parameter(0, 'fm', 'algorithm', 5)
synth.set_engine_parameter(0, 'fm', 'feedback', 0.2)
```

## Effects Processing

### XG Effects (GS Compatible)
```python
# Enable reverb
synth.set_effect_parameter('reverb', 'level', 0.4)
synth.set_effect_parameter('reverb', 'time', 2.0)

# Enable chorus
synth.set_effect_parameter('chorus', 'level', 0.3)
synth.set_effect_parameter('chorus', 'rate', 0.5)
```

### Jupiter-X Effects Enhancement
```python
# Enable Jupiter-X specific processing
synth.enable_jupiter_x_effects()

# Configure advanced effects
synth.set_jupiter_x_effect('distortion', 'drive', 0.6)
synth.set_jupiter_x_effect('phaser', 'rate', 0.3)
```

## Arpeggiator System

### Basic Arpeggiator Setup
```python
# Enable arpeggiator for part 0
synth.enable_arpeggiator(0, True)

# Set pattern and tempo
synth.set_arpeggiator_pattern(0, 5)  # Pattern 5
synth.set_arpeggiator_tempo(0, 128)  # 128 BPM

# Configure timing
synth.set_arpeggiator_gate_time(0, 0.8)  # 80% gate time
synth.set_arpeggiator_swing(0, 0.5)      # 50% swing
```

### Advanced Arpeggiator Features
```python
# 32 available patterns
patterns = synth.get_arpeggiator_patterns()
print(f"Available patterns: {len(patterns)}")

# Custom pattern creation
custom_pattern = synth.create_arpeggiator_pattern("My Pattern")
# Edit pattern grid...
synth.set_arpeggiator_pattern(0, custom_pattern.id)
```

## MPE (Microtonal Expression)

### MPE Setup
```python
# Enable MPE mode
synth.enable_mpe(True)

# Configure zones (default setup)
# Lower zone: channels 1-8 (master=0)
# Upper zone: channels 10-15 (master=9)

# Per-note pitch bend range (±48 semitones by default)
synth.set_mpe_pitch_bend_range(48.0)
```

### MPE Performance
```python
# MPE note with pitch bend
synth.mpe_note_on(channel=1, note=60, velocity=100, pitch_bend=12.0)

# Adjust timbre and pressure in real-time
synth.mpe_set_timbre(channel=1, note=60, timbre=0.8)
synth.mpe_set_pressure(channel=1, note=60, pressure=0.7)
```

## MIDI Control

### MIDI Mapping
```python
# Map CC 74 to filter cutoff
synth.map_midi_cc(74, 'filter_cutoff')

# Map NRPN to engine parameters
synth.map_nrpn(0x48, 0x00, 'analog_osc1_level')

# Save/load MIDI mappings
synth.save_midi_mappings('my_mappings.json')
synth.load_midi_mappings('my_mappings.json')
```

### Advanced MIDI Features
```python
# Polyphonic aftertouch
synth.enable_poly_aftertouch(True)

# High-resolution velocity curves
synth.set_velocity_curve('convex')  # linear, convex, concave, switch

# Aftertouch modes
synth.set_aftertouch_mode('poly')  # off, poly, channel, mpe
```

## Presets and Banks

### Preset Management
```python
# Save current state as preset
synth.save_preset('My Sound', 'Analog Leads')

# Load preset
synth.load_preset('My Sound', 'Analog Leads')

# Browse available presets
banks = synth.get_preset_banks()
for bank_name, presets in banks.items():
    print(f"Bank: {bank_name}")
    for preset in presets:
        print(f"  - {preset}")
```

### Preset Categories
- **Analog**: Classic subtractive synthesis sounds
- **Digital**: Wavetable and FM-based timbres
- **External**: Sample-based instruments
- **Effects**: Sound design and processing
- **Arpeggiated**: Sequence-based sounds
- **MPE**: Microtonal and expressive presets

## Performance Optimization

### Real-Time Monitoring
```python
# Get performance metrics
metrics = synth.get_performance_metrics()
print(f"CPU Usage: {metrics['cpu']['current']}%")
print(f"Memory Usage: {metrics['memory']['current']}%")
print(f"Active Voices: {metrics['voices']['current']}")

# Get optimization recommendations
recommendations = synth.get_optimization_recommendations()
for rec in recommendations:
    print(f"⚡ {rec}")
```

### Performance Tuning
```python
# Set performance targets
synth.set_performance_targets(
    max_cpu=70.0,      # Target 70% CPU usage
    max_memory=80.0,   # Target 80% memory usage
    max_latency=5.0    # Target 5ms latency
)

# Apply real-time optimizations
results = synth.optimize_for_realtime()
print(f"Optimizations applied: {results['optimizations_applied']}")
```

### Buffer and Latency Settings
```python
# Configure audio buffer size
synth.set_buffer_size(512)    # Lower latency (higher CPU)
synth.set_buffer_size(2048)   # Higher latency (lower CPU)

# Monitor latency
latency_stats = synth.get_latency_stats()
print(f"Average latency: {latency_stats['average']}ms")
```

## Troubleshooting

### Common Issues

#### Audio Dropouts (Xruns)
```
Symptoms: Audio glitches, pops, or silence
Solutions:
- Reduce buffer size in audio interface settings
- Lower polyphony limit
- Disable CPU-intensive effects
- Check system resource usage
```

#### High CPU Usage
```
Symptoms: System slowdown, high CPU percentage
Solutions:
- Reduce active voices/polyphony
- Disable complex effects (reverb, chorus)
- Use simpler synthesis engines
- Enable performance optimizations
```

#### Memory Issues
```
Symptoms: Out of memory errors, system slowdown
Solutions:
- Reduce sample library size
- Clear unused presets
- Restart synthesizer periodically
- Monitor memory usage trends
```

### Performance Benchmarks

#### Expected Performance (Recommended Hardware)
- **Polyphony**: 64+ voices sustained
- **CPU Usage**: <50% at 64 voices
- **Latency**: <5ms round-trip
- **Memory**: <500MB with full sample library

#### Performance Testing
```python
# Run performance benchmark
results = synth.run_performance_test(duration=30)
print(f"Average CPU: {results['cpu_average']}%")
print(f"Peak voices: {results['voices_peak']}")
print(f"Xruns detected: {results['xruns']}")
```

## Advanced Features

### Custom Wavetables
```python
# Load custom wavetable
wavetable_data = np.random.uniform(-1, 1, 2048)
synth.load_custom_wavetable(wavetable_data, 'my_wavetable')

# Use in digital engine
synth.set_engine_parameter(0, 'digital', 'wavetable', 'my_wavetable')
```

### Sample Management
```python
# Load sample for external engine
sample_data, sample_rate = load_audio_file('my_sample.wav')
synth.load_sample_for_engine(0, sample_data, sample_rate)

# Configure playback
synth.set_engine_parameter(0, 'external', 'playback_mode', 'loop')
synth.set_engine_parameter(0, 'external', 'start_point', 0.1)
synth.set_engine_parameter(0, 'external', 'end_point', 0.9)
```

### Custom Algorithms
```python
# Define custom FM algorithm
custom_algorithm = [
    (1, 0, 1.0),    # OP2 modulates OP1
    (2, 1, 0.5),    # OP3 modulates OP2
    (3, 2, 0.3),    # OP4 modulates OP3
]

synth.define_custom_fm_algorithm(99, custom_algorithm)
synth.set_engine_parameter(0, 'fm', 'algorithm', 99)
```

## API Reference

### Core Classes

#### JupiterXSynthesizer
Main synthesizer interface with all high-level controls.

#### JupiterXPart
Individual part configuration and engine management.

#### Synthesis Engines
- `JupiterXAnalogEngine`: Subtractive synthesis
- `JupiterXDigitalEngine`: Wavetable synthesis
- `JupiterXFMEngine`: FM synthesis
- `JupiterXExternalEngine`: Sample playback

### Key Methods

#### Initialization
- `JupiterXSynthesizer(sample_rate, buffer_size)`
- `enable_jupiter_x_mode()`
- `start()` / `stop()`

#### Note Control
- `note_on(note, velocity, channel=0)`
- `note_off(note, channel=0)`
- `all_notes_off(channel=-1)`

#### Parameter Control
- `set_parameter(name, value)`
- `get_parameter(name)`
- `set_part_parameter(part, name, value)`
- `set_engine_parameter(part, engine, name, value)`

#### Effects & Processing
- `set_effect_parameter(effect, param, value)`
- `enable_effect(effect, enable=True)`
- `set_reverb_type(type_index)`
- `set_chorus_type(type_index)`

#### Arpeggiator
- `enable_arpeggiator(part, enable=True)`
- `set_arpeggiator_pattern(part, pattern_id)`
- `set_arpeggiator_tempo(part, bpm)`

#### MPE
- `enable_mpe(enable=True)`
- `set_mpe_pitch_bend_range(semitones)`
- `mpe_note_on(channel, note, velocity, pitch_bend=0)`

#### Presets
- `save_preset(name, bank='default')`
- `load_preset(name, bank='default')`
- `get_preset_banks()`

#### Performance
- `get_performance_metrics()`
- `optimize_for_realtime()`
- `set_performance_targets(cpu, memory, latency)`

## Examples

### Complete Setup Example
```python
from synth.jupiter_x import JupiterXSynthesizer
import time

# Initialize with high-performance settings
synth = JupiterXSynthesizer(sample_rate=48000, buffer_size=256)
synth.enable_jupiter_x_mode()
synth.optimize_for_realtime()

# Configure part 0 with analog engine
synth.set_part_engine(0, 'analog')
synth.set_engine_parameter(0, 'analog', 'osc1_waveform', 'sawtooth')
synth.set_engine_parameter(0, 'analog', 'filter_cutoff', 0.6)
synth.set_engine_parameter(0, 'analog', 'filter_resonance', 0.4)

# Enable effects
synth.set_effect_parameter('reverb', 'level', 0.3)
synth.set_effect_parameter('chorus', 'level', 0.2)

# Enable arpeggiator
synth.enable_arpeggiator(0, True)
synth.set_arpeggiator_pattern(0, 1)  # Up pattern
synth.set_arpeggiator_tempo(0, 120)

# Start synthesis
synth.start()

# Play arpeggiated sequence
notes = [60, 64, 67, 72]  # C major arpeggio
for note in notes:
    synth.note_on(note, 100, channel=0)
    time.sleep(0.5)

# Clean shutdown
for note in notes:
    synth.note_off(note, channel=0)
synth.stop()
```

This comprehensive guide covers all aspects of Jupiter-X synthesizer usage, from basic setup to advanced performance optimization. For additional support, refer to the API documentation or community forums.
