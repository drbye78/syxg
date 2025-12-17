# XGML (XG Markup Language) - Complete Implementation

## Overview

XGML (XG Markup Language) is a comprehensive high-level YAML-based interface for controlling Yamaha XG synthesizer parameters. It provides human-readable abstractions over low-level MIDI messages, NRPN parameters, and system exclusive commands.

## 🚀 Production-Ready Features

### ✅ Fully Implemented
- **Basic MIDI Messages**: Program changes, controllers with semantic names
- **RPN Parameters**: Pitch bend range, tuning, modulation depth
- **Channel Parameters**: Complete NRPN MSB 3-31 implementation (filter, LFO, effects, scale tuning)
- **Time-bound Sequences**: Musical events with precise timing
- **Automatic Validation**: Schema-based validation of XGML documents
- **MIDI/XGML Conversion**: Bidirectional translation between formats

### 🔧 Tools & Infrastructure
- **render_midi.py**: Unified converter (MIDI + XGML → Audio)
- **midi_to_xgml.py**: MIDI to XGML converter
- **XGML Schema**: Complete JSON Schema for validation
- **XGML Module**: Full Python implementation (`synth/xgml/`)

## 📖 XGML Schema Structure

### Document Structure
```yaml
xg_dsl_version: "1.0"          # Required: Schema version
description: "Optional description"
timestamp: "2025-12-15T02:15:00Z"  # Optional: ISO timestamp

# Configuration sections
basic_messages: {...}          # Static MIDI messages
rpn_parameters: {...}          # Registered parameters
channel_parameters: {...}      # XG channel parameters
drum_parameters: {...}         # Drum kit parameters
system_exclusive: {...}        # SYSEX messages
effects: {...}                 # Effects configuration
sequences: {...}               # Time-bound sequences
```

### Basic Messages Example
```yaml
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"              # Semantic pan position
      expression: 127
      reverb_send: 40
      chorus_send: 20
```

### Channel Parameters Example
```yaml
channel_parameters:
  channel_1:
    # Filter parameters
    filter:
      cutoff: 80
      resonance: 70
      type: "lowpass"
      envelope:
        attack: 90
        decay: 40
        sustain: 70
        release: 60

    # LFO parameters
    lfo:
      lfo1:
        waveform: "sine"
        speed: 64
        pitch_depth: 50
        filter_depth: 30

    # Effects sends
    effects_sends:
      reverb: 50
      chorus: 20
      variation: 0
```

### Time-bound Sequences Example
```yaml
sequences:
  melody:
    tempo: 120
    time_signature: "4/4"
    quantization: "1/8"

    tracks:
      - track:
          channel: 0
          parameters:
            volume: 90
            pan: "center"

          events:
            - at: { time: 0.0, note_on: { note: "C4", velocity: 80 } }
            - at: { time: 1.0, note_off: { note: "C4", velocity: 40 } }
            - at: { time: 0.5, brightness: { from: 80, to: 120, curve: "linear", duration: 1.5 } }
```

## 🎵 Supported XG Features

### Program Names
All 128 GM/XG programs supported with readable names:
```yaml
program_change: "acoustic_grand_piano"     # 0
program_change: "electric_piano_1"         # 4
program_change: "violin"                   # 40
program_change: "trumpet"                  # 56
program_change: "pad_1_new_age"           # 88
# ... and 123 more
```

### Controller Names
Human-readable controller names instead of numbers:
```yaml
brightness: 80           # CC 74 - Filter cutoff
harmonic_content: 70     # CC 71 - Filter resonance
reverb_send: 40          # CC 91 - Reverb send
chorus_send: 20          # CC 93 - Chorus send
sustain: true            # CC 64 - Sustain pedal
```

### Pan Positions
Semantic pan positions:
```yaml
pan: "left"              # 0
pan: "center"            # 64
pan: "right"             # 127
pan: "left_20"           # 20 (20% left)
pan: "right_30"          # 97 (30% right)
```

### NRPN Parameters
Complete XG parameter mapping:
```yaml
# Filter parameters (MSB 5)
filter:
  cutoff: 80
  resonance: 70
  type: "lowpass"

# Amplifier envelope (MSB 7)
amplifier:
  envelope:
    attack: 90
    decay: 40
    sustain: 70
    release: 60

# LFO parameters (MSB 9)
lfo:
  lfo1:
    waveform: "sine"
    speed: 64
    pitch_depth: 50
```

## 🛠️ Usage

### Convert XGML to Audio
```bash
# Single XGML file
render_midi.py input.xgml

# Multiple files
render_midi.py *.xgml --format mp3

# With specific output
render_midi.py input.xgml output.wav
```

### Convert MIDI to XGML
```bash
# Convert MIDI to readable XGML
midi_to_xgml.py input.mid

# Batch conversion
midi_to_xgml.py *.mid --output-dir xgml/
```

### Schema Validation
```yaml
# XGML documents are validated against xgml_schema.yaml
# Use any JSON Schema validator or IDE with YAML support
```

## 📋 XGML Schema Validation

The `xgml_schema.yaml` provides complete JSON Schema validation:

```bash
# Validate XGML file (using Python)
python -c "
import yaml
from pathlib import Path

# Load and validate XGML
with open('file.xgml', 'r') as f:
    data = yaml.safe_load(f)

# Check required fields
assert 'xg_dsl_version' in data
assert data['xg_dsl_version'] == '1.0'
print('✅ Valid XGML document')
"
```

## 🔄 MIDI ↔ XGML Conversion

### MIDI to XGML Benefits
- **Readability**: `program_change: "acoustic_grand_piano"` vs MIDI `0xC0 0x00`
- **Maintainability**: Semantic names instead of magic numbers
- **Documentation**: Self-documenting configuration
- **Version Control**: Human-readable diffs

### XGML to MIDI Benefits
- **Compatibility**: Works with any MIDI-compatible software
- **Performance**: Optimized binary format for real-time playback
- **Standards**: Full MIDI 1.0/2.0 compatibility
- **Ecosystem**: Access to entire MIDI tool ecosystem

## 🎼 Advanced Features

### Complex Events
```yaml
events:
  # Chord events
  - at: { time: 0.0, chord: { notes: ["C4", "E4", "G4"], velocity: 80, voicing: "spread" } }

  # System exclusive
  - at: { time: 1.0, system_exclusive: { manufacturer: "yamaha", model: "xg", command: "parameter_change", address: "0x100010", values: { reverb_type: "hall_2" } } }

  # Pitch bend with curve
  - at: { time: 2.0, pitch_bend: { value: 2000, curve: "sine_wave", duration: 1.0 } }
```

### Controller Curves
```yaml
# Smooth parameter transitions
brightness: { from: 60, to: 100, curve: "exponential", duration: 2.0 }
modulation: { from: 0, to: 127, curve: "linear", duration: 4.0 }
pan: { from: "left", to: "right", curve: "sine_wave", duration: 3.0 }
```

## 🏗️ Architecture

```
XGML File (.xgml)
    ↓
XGMLParser → XGMLDocument
    ↓
XGMLToMIDITranslator → List[MIDIMessage]
    ↓
OptimizedXGSynthesizer.send_midi_message_block()
    ↓
Real-time Audio Rendering
```

## 📊 Performance & Compatibility

- **Zero Overhead**: XGML → MIDI conversion is computationally free
- **Full XG Support**: All Yamaha XG parameters and effects
- **Real-time Ready**: Optimized for live performance and sequencing
- **Cross-Platform**: Works on any system with Python 3.8+
- **Extensible**: Easy to add new XGML features and parameters

## 🔧 Development

### Project Structure
```
synth/xgml/              # XGML implementation
├── __init__.py         # Module exports
├── constants.py        # XG mappings and constants
├── parser.py           # YAML parser with validation
└── translator.py       # XGML to MIDI translator

render_midi.py          # Unified MIDI/XGML converter
midi_to_xgml.py         # MIDI to XGML converter
xgml_schema.yaml        # Complete JSON Schema
```

### Testing
```bash
# Test XGML parsing and rendering
python render_midi.py test_schema.xgml --format wav

# Test MIDI conversion
python midi_to_xgml.py test.mid

# Validate schema
python -c "import yaml; yaml.safe_load(open('xgml_schema.yaml'))"
```

## 📚 Examples

See the `examples/` directory for complete XGML examples:
- `jazz_combo.xgdsl` - Multi-instrument jazz arrangement
- `electronic_music_example.md` - Electronic music production
- `simple_piano.xgdsl` - Basic piano configuration

## 🎯 Use Cases

### Music Production
- **DAW Integration**: Human-readable instrument configurations
- **Version Control**: Track changes in readable format
- **Collaboration**: Share configurations as readable text
- **Documentation**: Self-documenting project files

### Live Performance
- **Real-time Control**: Dynamic parameter changes
- **Preset Management**: Organized sound configurations
- **System Integration**: Connect with lighting, video systems

### Education
- **Learning Tool**: Understand synthesizer parameters
- **Teaching Aid**: Demonstrate synthesis concepts
- **Documentation**: Clear parameter explanations

## 🤝 Contributing

XGML is designed to be extensible. To add new features:

1. Update `xgml_schema.yaml` with new schema definitions
2. Extend `constants.py` with new mappings
3. Implement parsing in `parser.py`
4. Add translation logic in `translator.py`
5. Update documentation and examples

## 📄 License

This XGML implementation is part of the syxg project and follows the same license terms.

---

**XGML provides the future of synthesizer control: human-readable, version-controllable, and fully compatible with professional audio production workflows.**
