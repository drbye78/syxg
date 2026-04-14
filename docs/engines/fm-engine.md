# 🎹 FM-X Synthesis Engine

The FM-X (Frequency Modulation eXtended) synthesis engine implements advanced 8-operator FM synthesis with 88 algorithms, comprehensive modulation, and professional sound design capabilities.

## 🎼 Overview

FM-X synthesis uses frequency modulation where one oscillator (carrier) is modulated by another oscillator (modulator). The XG Synthesizer's FM-X engine extends traditional FM with:

- **8 Operators**: Individual oscillators with full control
- **88 Algorithms**: Complex routing configurations
- **Advanced Envelopes**: 8-stage envelopes with loop points
- **Ring Modulation**: Additional modulation between operators
- **Formant Synthesis**: Vocal formant capabilities
- **Comprehensive LFOs**: 3 assignable LFOs with multiple waveforms
- **Modulation Matrix**: 128 assignable modulation routings

## 🏗️ Architecture

### Operators

Each FM-X operator contains:

- **Oscillator**: Sine, triangle, sawtooth, or square wave
- **Frequency Control**: Ratio-based frequency setting
- **Detuning**: Fine frequency adjustment (±100 cents)
- **Feedback**: Self-modulation amount (0-7 levels)
- **8-Stage Envelope**: Attack, Decay, Sustain, Release with loop points
- **Scaling**: Key and velocity sensitivity adjustments

### Algorithms

FM-X provides 88 predefined algorithms that determine how operators modulate each other:

| Algorithm | Description | Operators Used |
|-----------|-------------|----------------|
| 0 | Simple FM (1→2) | 2 |
| 1 | Stacked FM (1→2→3) | 3 |
| 8 | Ring Modulation Pairs | 4 |
| 32 | Complex 6-operator | 6 |
| 63 | Full 8-operator | 8 |

### Modulation System

#### LFOs (Low Frequency Oscillators)
- **3 Global LFOs**: Assignable to any modulation destination
- **Waveforms**: Sine, triangle, sawtooth, square, random
- **Frequency Range**: 0.01 Hz to 20 Hz
- **Phase Control**: 0-360° phase offset

#### Modulation Matrix
- **128 Assignable Slots**: Connect sources to destinations
- **Sources**: LFOs, velocity, aftertouch, controllers, note number
- **Destinations**: Pitch, volume, filter, LFO parameters
- **Bipolar Control**: Positive/negative modulation amounts

## 🎛️ Configuration

### Basic FM-X Setup

```yaml
# Basic FM-X configuration
fm_x_engine:
  enabled: true
  algorithm: 0                    # Simple FM algorithm
  master_volume: 0.8

  operators:
    op_0:                         # Modulator
      frequency_ratio: 1.0
      feedback_level: 2
      envelope:
        levels: [0.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]

    op_1:                         # Carrier
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0, 0.0]
```

### Advanced Configuration

```yaml
fm_x_engine:
  enabled: true
  algorithm: 32                  # Complex 6-operator algorithm
  master_volume: 0.9
  pitch_bend_range: 2            # ±2 semitones

  # Full operator configuration
  operators:
    op_0:
      enabled: true
      frequency_ratio: 0.5        # Fundamental frequency / 2
      detune_cents: -10           # Slight detuning
      feedback_level: 1
      waveform: "sine"
      envelope:
        levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        loop_start: -1            # No envelope looping
      scaling:
        key_depth: 0
        velocity_sensitivity: 1

    # Additional operators 1-5 with similar configuration...

  # LFO configuration
  lfos:
    lfo_0:
      enabled: true
      waveform: "sine"
      frequency: 1.0
      depth: 1.0
      phase: 0.0
      assignable: true

    lfo_1:
      enabled: true
      waveform: "triangle"
      frequency: 0.5
      depth: 0.8

  # Ring modulation between operators
  ring_modulation:
    - [0, 2]                     # Operator 0 ring modulates operator 2
    - [1, 3]                     # Operator 1 ring modulates operator 3

  # Advanced modulation matrix
  modulation_matrix:
    - source: "lfo0"
      destination: "pitch"
      amount: 0.3
      bipolar: true
    - source: "velocity"
      destination: "amplitude"
      amount: 0.7
    - source: "aftertouch"
      destination: "filter_cutoff"
      amount: -0.5

  # Effects integration
  effects_sends:
    reverb: 0.2
    chorus: 0.3
    delay: 0.1
```

## 🎵 Sound Design Techniques

### Creating Bell Sounds

```yaml
# Bell using high feedback and inharmonic ratios
fm_x_engine:
  algorithm: 0
  operators:
    op_0:                         # Modulator with high feedback
      frequency_ratio: 1.4        # Inharmonic ratio
      feedback_level: 7           # Maximum feedback
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    op_1:                         # Carrier
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Brass Sounds

```yaml
# Brass using multiple operators and breath control
fm_x_engine:
  algorithm: 8                   # Parallel carriers
  operators:
    op_0:                        # Fundamental
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.8, 0.3, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]

    op_1:                        # Octave
      frequency_ratio: 2.0
      envelope:
        levels: [0.0, 0.5, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]

  modulation_matrix:
    - source: "breath"
      destination: "amplitude"
      amount: 0.8
```

### Vocal Formants

```yaml
# Vocal synthesis using formant operators
fm_x_engine:
  algorithm: 0
  operators:
    op_0:                        # Carrier with formant
      frequency_ratio: 1.0
      formant_synthesis:
        enabled: true
        vowel: "a"               # /ɑ/ formant
      envelope:
        levels: [0.0, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0]

    op_1:                        # Modulator
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

## 🔧 API Usage

### Programmatic Control

```python
from synth.engine.fm_engine import FMEngine

# Create FM engine
fm_engine = FMEngine(sample_rate=44100, num_operators=8)

# Set algorithm
fm_engine.set_algorithm(0)  # Simple FM

# Configure operators
fm_engine.configure_operator(0, {
    'frequency_ratio': 1.0,
    'feedback_level': 2,
    'envelope': {
        'levels': [0.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0],
        'rates': [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    }
})

fm_engine.configure_operator(1, {
    'frequency_ratio': 1.0,
    'envelope': {
        'levels': [0.0, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0],
        'rates': [0.01, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0, 0.0]
    }
})

# Generate audio
audio = fm_engine.generate_samples(
    note=60,           # C4
    velocity=100,
    modulation={},
    block_size=1024
)
```

### Real-time Performance

```python
# Real-time FM synthesis
fm_engine.note_on(60, 100)     # Play C4

# Generate audio blocks
for i in range(100):           # 100 audio blocks
    audio_block = fm_engine.generate_samples(60, 100, {}, 512)
    # Send to audio output...

fm_engine.note_off(60)         # Stop note
```

## 📊 Technical Specifications

### Operator Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `frequency_ratio` | 0.1 - 32.0 | Frequency multiplier |
| `detune_cents` | -100 - 100 | Fine tuning in cents |
| `feedback_level` | 0 - 7 | Self-modulation amount |
| `waveform` | sine/triangle/sawtooth/square | Oscillator shape |

### Envelope Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `levels[8]` | 0.0 - 1.0 | 8 envelope levels |
| `rates[8]` | 0.0 - 10.0 | 8 envelope rates (seconds) |
| `loop_start` | -1, 0-7 | Envelope loop start (-1 = no loop) |
| `loop_end` | -1, 0-7 | Envelope loop end (-1 = no loop) |

### Scaling Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `key_depth` | 0 - 7 | Key scaling sensitivity |
| `velocity_sensitivity` | 0 - 7 | Velocity sensitivity |
| `key_curve` | linear/exp/log | Key scaling curve |

### LFO Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `frequency` | 0.01 - 20.0 Hz | LFO speed |
| `depth` | 0.0 - 1.0 | LFO amplitude |
| `phase` | 0.0 - 360.0° | Phase offset |
| `waveform` | sine/triangle/sawtooth/square/random | LFO shape |

### Modulation Matrix

| Source | Destination | Range | Description |
|--------|-------------|-------|-------------|
| `lfo0-2` | `pitch/volume/amplitude/frequency/feedback` | -1.0 - 1.0 | LFO modulation |
| `velocity` | All destinations | -1.0 - 1.0 | Velocity modulation |
| `aftertouch` | All destinations | -1.0 - 1.0 | Aftertouch modulation |
| Controllers | All destinations | -1.0 - 1.0 | MIDI CC modulation |

## 🎛️ Advanced Features

### Algorithm Variations

```python
# Algorithm 0: Simple FM
# Op0 (Modulator) → Op1 (Carrier)

# Algorithm 1: Stacked FM
# Op0 → Op1 → Op2

# Algorithm 8: Ring Modulation Pairs
# Op0 ↔ Op1, Op2 ↔ Op3

# Algorithm 32: Complex routing
# Op0 → Op1, Op1 → Op3, Op2 → Op4, etc.
```

### Envelope Looping

```yaml
# Looping envelope for evolving sounds
envelope:
  levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
  rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
  loop_start: 2                 # Loop from sustain stage
  loop_end: 3                   # Back to sustain level
```

### Ring Modulation

```yaml
# Ring modulation between operators
ring_modulation:
  - [0, 1]                      # Op0 * Op1
  - [2, 3]                      # Op2 * Op3 (additional harmonics)

# Symmetric ring modulation
operators:
  op_0:
    ring_modulation:
      enabled: true
      partner_operator: 1
      symmetric: true            # Both directions
```

### Custom Formants

```yaml
# Custom vocal formants
formant_synthesis:
  enabled: true
  custom_formant:
    frequency: 800              # Formant frequency in Hz
    bandwidth: 100              # Formant bandwidth in Hz
    gain: 2.5                   # Resonance gain
```

## 🔄 Integration with XG Synthesizer

### XGML Configuration

```yaml
# Complete XGML with FM-X
xg_dsl_version: "2.1"

synthesis_engines:
  default_engine: "fm"
  part_engines:
    part_0: "fm"

fm_x_engine:
  # Full FM-X configuration as above...

basic_messages:
  channels:
    channel_1:
      program_change: "custom_fm_sound"
```

### Python Integration

```python
from synth.synthesizers.rendering import ModernXGSynthesizer

# Create synthesizer with FM-X
synth = ModernXGSynthesizer(default_engine="fm")

# Load XGML with FM-X configuration
synth.load_xgml_config("fm_x_patch.xgdsl")

# Render MIDI with FM synthesis
synth.render_midi_file("input.mid", "fm_output.wav")
```

## 🎵 Performance Considerations

### CPU Usage
- **Simple Algorithms**: Low CPU (algorithms 0-8)
- **Complex Algorithms**: Higher CPU (algorithms 32+)
- **8 Operators**: Maximum CPU usage
- **Envelope Looping**: Additional CPU for envelope processing

### Memory Usage
- **Algorithm Storage**: Minimal memory footprint
- **Operator States**: Per-voice memory allocation
- **Modulation Matrix**: Small memory overhead

### Optimization Tips
```python
# Use simpler algorithms for polyphonic patches
fm_engine.set_algorithm(0)      # Simple FM instead of complex

# Reduce operator count for CPU-intensive applications
fm_engine = FMEngine(num_operators=4)

# Disable unused features
# Remove envelope looping for static sounds
# Use simple waveforms instead of formants
```

## 🔧 Troubleshooting

### Common Issues

#### No Sound Output
- **Check Algorithm**: Ensure algorithm uses output operators
- **Verify Envelopes**: Make sure carrier envelopes have sustain > 0
- **Operator Levels**: Confirm modulation amounts are appropriate

#### Unstable Sounds
- **Feedback Levels**: Reduce feedback (0-3 recommended)
- **Frequency Ratios**: Use ratios < 16 to avoid aliasing
- **Envelope Rates**: Avoid very fast rates (< 0.001)

#### CPU Overload
- **Reduce Operators**: Use 4-6 operators instead of 8
- **Simplify Algorithm**: Choose simpler routing (algorithms 0-15)
- **Disable Features**: Turn off unused LFOs and modulation

## 📚 Examples

### Bell Sound

```yaml
fm_x_engine:
  algorithm: 0
  operators:
    op_0:                        # Bright modulator
      frequency_ratio: 1.0
      feedback_level: 6
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    op_1:                        # Ringing carrier
      frequency_ratio: 2.0
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Bass Sound

```yaml
fm_x_engine:
  algorithm: 1
  operators:
    op_0:                        # Sub-bass
      frequency_ratio: 0.5
      envelope:
        levels: [0.0, 1.0, 0.8, 0.2, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0]
    op_1:                        # Body
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 0.7, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0]
    op_2:                        # Bite
      frequency_ratio: 2.0
      envelope:
        levels: [0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Pad Sound

```yaml
fm_x_engine:
  algorithm: 32                 # Complex algorithm
  operators:
    op_0:                       # Slow attack pad
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 0.0, 0.8, 0.8, 0.0, 0.0, 0.0, 0.0]
        rates: [0.5, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]
        loop_start: 2           # Loop sustain section
        loop_end: 3
    # Additional operators for complex pad sound...
```

## 🎯 Best Practices

### Sound Design
1. **Start Simple**: Use algorithm 0 for initial experiments
2. **Balance Levels**: Keep modulation amounts between 0.1-1.0
3. **Use Feedback Sparingly**: Levels 0-3 for most sounds
4. **Experiment with Ratios**: Inharmonic ratios create interesting timbres

### Performance
1. **Choose Appropriate Algorithms**: Match complexity to needs
2. **Optimize Operator Count**: Use minimum operators required
3. **Monitor CPU**: Use simpler settings for polyphonic patches
4. **Cache Settings**: Reuse configurations for similar sounds

### Production
1. **Version Control**: Keep XGML files in git
2. **Documentation**: Comment complex modulation routings
3. **Backup**: Save working configurations
4. **Testing**: Verify sounds across velocity ranges

---

**🎹 FM-X synthesis provides professional-grade frequency modulation with unparalleled flexibility. From classic DX7-style sounds to modern experimental timbres, FM-X delivers the power of frequency modulation for any sound design task.**
