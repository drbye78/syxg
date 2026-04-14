# Vibexg Documentation

Welcome to the Vibexg documentation!

## Vibexg - Vibe XG Real-Time MIDI Workstation

Vibexg is a professional real-time MIDI workstation emulator built around the XG Synthesizer.

### Key Features

- **Multiple MIDI Inputs**: Keyboard, physical ports, virtual ports, network, file, stdin
- **Real-time Audio**: SoundDevice output or file rendering
- **Preset Management**: Save and recall complete setups
- **MIDI Learn**: Map hardware controllers to parameters
- **Style Engine**: Auto-accompaniment support
- **TUI Interface**: Rich text-based control surface
- **Demo Mode**: Built-in test patterns

## Documentation Sections

```{toctree}
:maxdepth: 2
:caption: User Guide

user/getting-started
user/installation
user/quick-start
user/midi-inputs
user/audio-outputs
user/presets
user/midi-learn
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/vibexg
api/workstation
api/managers
api/types
api/midi_inputs
api/audio_outputs
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

dev/architecture
dev/contributing
dev/testing
```

```{toctree}
:maxdepth: 1
:caption: Examples

examples/basic_usage
examples/preset_management
examples/midi_learn_setup
```

## Quick Example

```python
from vibexg import XGWorkstation, PresetManager

# Create workstation
ws = XGWorkstation({'sample_rate': 44100, 'buffer_size': 512})

# Create and save preset
pm = PresetManager('presets')
preset = pm.create_preset('My Setup')
preset.master_volume = 0.75
pm.save_preset(preset)

# Start workstation
ws.start()
```

## Installation

```bash
# Install vibexg
pip install -e .

# For MIDI port support
pip install rtmidi

# For real-time audio
pip install sounddevice
```

## Command Line Usage

```bash
# Run with keyboard input
python -m vibexg --midi-input keyboard

# List MIDI ports
python -m vibexg --list-ports

# Run demo
python -m vibexg --demo scale
```

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
