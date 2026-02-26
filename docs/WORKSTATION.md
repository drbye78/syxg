# Vibexg - Vibe XG Real-Time MIDI Workstation

A professional real-time MIDI workstation emulator built around the XG Synthesizer, capable of receiving MIDI messages via multiple interfaces and rendering audio to audio interfaces or files.

## Features

### Multiple MIDI Input Interfaces
- **Computer Keyboard**: Use your computer keyboard as a MIDI controller (Z-M = C3-B3, Q-U = C4-B4)
- **Physical MIDI Ports**: Connect via USB MIDI interfaces using mido
- **Virtual MIDI Ports**: Inter-process MIDI communication
- **Network MIDI**: RTP-MIDI / AppleMIDI support with UDP socket handling
- **MIDI File Playback**: Real-time file playback with tempo control and looping
- **Stdin MIDI**: Scriptable MIDI input via JSON

### Enhanced Features (New)
- **Full MIDI Message Routing**: Complete conversion of all MIDI message types to synthesizer input
- **Preset Management**: Save/load complete workstation setups with pickle serialization
- **MIDI Learn**: Interactive CC mapping with linear/exponential/logarithmic curves
- **Style Engine Integration**: Auto-accompaniment with .sty/.sff file support
- **Demo Mode**: Built-in test patterns (scale, chords, arpeggio) for audio verification
- **File Audio Output**: Proper finalization and buffering for clean file rendering

### Audio Output Options
- **Real-time Audio**: Low-latency output via sounddevice to any audio interface
- **File Rendering**: Render directly to WAV, FLAC, OGG, MP3, AAC, or M4A
- **Silent Mode**: Process MIDI without audio output

### Professional Workstation Features
- **16 MIDI Channels**: Full multi-timbral support
- **XG/GS Compatibility**: Yamaha XG and Roland GS specification support
- **Real-time Effects**: Reverb, chorus, insertion effects
- **Recording & Playback**: Record MIDI performances, playback with tempo control
- **Metronome**: Built-in click track
- **TUI Control Surface**: Rich text-based interface with real-time visualization
- **Preset Management**: Save and recall complete setups
- **MIDI Learn**: Map hardware controllers to synth parameters

## Installation

### Prerequisites

```bash
# Install core requirements
pip install -r requirements.txt

# Install workstation-specific requirements (includes rtmidi for MIDI port support)
pip install -r requirements_workstation.txt
```

### MIDI Port Support

The workstation now uses the native `synth.midi` package for MIDI I/O operations. For physical MIDI port support, install rtmidi:

```bash
pip install rtmidi
```

**Note:** mido is no longer required - all MIDI functionality is now provided by the native `synth.midi` package.

## Quick Start

### Basic Usage (Keyboard Input + Real-time Audio)

```bash
python vibexg.py
```

This starts the workstation with:
- Computer keyboard as MIDI input
- Default audio output device
- Rich TUI interface

### With Specific MIDI Input

```bash
# List available MIDI ports
python vibexg.py --list-ports

# Use specific MIDI port
python vibexg.py --midi-input "mido_port:USB MIDI Device"

# Multiple inputs
python vibexg.py --midi-input keyboard --midi-input "mido_port:USB MIDI"
```

### File Output (Rendering)

```bash
# Render to WAV file
python vibexg.py --audio-output "file:output.wav"

# Render with MIDI file playback
python vibexg.py --midi-input "file:song.mid" --audio-output "file:output.flac"
```

### Headless Mode (No TUI)

```bash
python vibexg.py --no-tui
```

### Load Configuration

```bash
python vibexg.py --config workstation_config.yaml
```

## Command Line Options

```
usage: vibexg.py [-h] [--config CONFIG] [--midi-input TYPE[:NAME]] ...
                            [--audio-output TYPE[:PATH]] [--sample-rate SR]
                            [--buffer-size BS] [--no-tui] [--demo PATTERN]
                            [--verbose] [--list-ports]

Vibexg - Vibe XG Real-Time MIDI Workstation

options:
  -h, --help            show this help message and exit
  --config, -c CONFIG   Configuration file path (default: config.yaml)
  --midi-input, -i TYPE[:NAME]
                        MIDI input interface:
                        - keyboard: Computer keyboard
                        - mido_port:NAME: Physical MIDI port
                        - virtual_port: Virtual MIDI port
                        - network_midi:host=IP,port=PORT: Network MIDI (RTP-MIDI)
                        - file:PATH: MIDI file playback
                        - stdin: JSON MIDI from stdin
  --audio-output, -o TYPE[:PATH]
                        Audio output:
                        - sounddevice: Default audio output
                        - sounddevice:DEVICE: Specific device
                        - file:PATH: Render to file
                        - none: No audio output
  --sample-rate, -sr    Audio sample rate (default: 44100)
  --buffer-size, -bs    Audio buffer size (default: 512)
  --no-tui              Disable TUI (text user interface)
  --demo PATTERN        Run demo pattern (scale, chords, arpeggio)
  --verbose, -v         Verbose output
  --list-ports          List available MIDI ports
```

## TUI Controls

When running with TUI enabled:

| Key | Function |
|-----|----------|
| R | Toggle recording |
| P | Playback recorded events |
| S | Stop playback/metronome |
| M | Toggle metronome |
| + | Increase tempo (+5 BPM) |
| - | Decrease tempo (-5 BPM) |
| V | Change volume |
| D | Run demo pattern |
| Q | Quit |
| H | Show help |

## Enhanced Features

### MIDI Message Routing

All MIDI message types are now fully routed to the synthesizer:

```python
from vibexg import midimessage_to_bytes, MIDIMessage

# Note On/Off
msg = MIDIMessage(type='note_on', channel=0, data={'note': 60, 'velocity': 80})
bytes_out = midimessage_to_bytes(msg)  # 0x90 0x3C 0x50

# Control Change
msg = MIDIMessage(type='control_change', channel=0, data={'controller': 74, 'value': 100})
bytes_out = midimessage_to_bytes(msg)  # 0xB0 0x4A 0x64

# Program Change
msg = MIDIMessage(type='program_change', channel=0, data={'program': 25})
bytes_out = midimessage_to_bytes(msg)  # 0xC0 0x19

# Pitch Bend (14-bit value)
msg = MIDIMessage(type='pitch_bend', channel=0, data={'value': 8192})  # Center
bytes_out = midimessage_to_bytes(msg)  # 0xE0 0x00 0x40

# SysEx
msg = MIDIMessage(type='sysex', data={'raw_data': [0x41, 0x10, 0x42]})
bytes_out = midimessage_to_bytes(msg)  # 0xF0 0x41 0x10 0x42 0xF7
```

### Preset Management

Save and load complete workstation setups:

```python
from vibexg import PresetManager

pm = PresetManager('presets')

# Create and save preset
preset = pm.create_preset('My Setup')
preset.master_volume = 0.75
preset.tempo = 110.0
preset.programs = {0: 1, 1: 5}  # Channel programs
pm.save_preset(preset)

# Load preset
loaded = pm.load_preset('my_preset.preset')

# Export as JSON
pm.export_preset_json(preset, 'my_setup.json')
```

### MIDI Learn

Map hardware controller CCs to synthesizer parameters:

```python
from vibexg import MIDILearnManager

midi_learn = MIDILearnManager(synthesizer)

# Add mapping with exponential curve (filter cutoff)
midi_learn.add_mapping(
    cc_number=74,
    target_param='filter.cutoff',
    channel=0,
    min_val=100,
    max_val=10000,
    curve='exp'  # linear, exp, log
)

# Add mapping with invert
midi_learn.add_mapping(
    cc_number=72,
    target_param='filter.resonance',
    channel=0,
    min_val=0,
    max_val=127,
    invert=True  # Invert control direction
)

# Process incoming CC
midi_learn.process_cc(74, 64, channel=0)  # Maps to filter.cutoff
```

### Demo Mode

Test audio output with built-in patterns:

```bash
# Run scale demo
python vibexg.py --demo scale

# Run chords demo
python vibexg.py --demo chords

# Run arpeggio demo
python vibexg.py --demo arpeggio
```

Or programmatically:

```python
ws = XGWorkstation()
ws.start()
ws.run_demo('scale')  # Plays C major scale
time.sleep(5)
ws.stop()
```

### Network MIDI (RTP-MIDI)

Connect to remote MIDI devices over network:

```bash
# Start network MIDI server
python vibexg.py --midi-input "network_midi:host=0.0.0.0,port=5004"

# Connect from another device (AppleMIDI/RTP-MIDI compatible)
```

Configuration:
```yaml
midi_inputs:
  - type: network_midi
    name: "Network MIDI"
    options:
      host: "192.168.1.100"
      port: 5004
```

### Style Engine Integration

Auto-accompaniment with style files:

```python
from vibexg import StyleEngineIntegration

style_engine = StyleEngineIntegration(synthesizer)
style_engine.initialize(['styles/'])

# Load and play style
style_engine.load_style('8Beat', channel=0)
style_engine.start_style(channel=0)
style_engine.set_tempo(120)
```

## Configuration File

Create a `workstation_config.yaml` for persistent settings:

```yaml
# Audio settings
audio:
  sample_rate: 44100
  buffer_size: 512
  master_volume: 0.8

# MIDI inputs
midi_inputs:
  - type: keyboard
    name: "Computer Keyboard"
    enabled: true
    transpose: 0

  - type: mido_port
    name: "USB MIDI"
    port_name: "USB MIDI Device"
    enabled: true

# Audio output
audio_output:
  type: sounddevice
  # device_name: "USB Audio Interface"
  sample_rate: 44100
  buffer_size: 512

# Synthesizer
synthesizer:
  max_polyphony: 128
  xg_enabled: true
  gs_enabled: true

# Effects
effects:
  master_reverb:
    enabled: true
    type: hall
    level: 0.3
  master_chorus:
    enabled: true
    type: chorus1
    level: 0.2
```

## MIDI Input Interface Examples

### Computer Keyboard

Maps keyboard keys to MIDI notes:
- **Z to M**: C3 to B3 (white keys)
- **Q to U**: C4 to B4 (black keys on upper row)
- Velocity fixed at 80

```bash
python vibexg.py --midi-input keyboard
```

### Physical MIDI Port

```bash
# List ports first
python vibexg.py --list-ports

# Use specific port
python vibexg.py --midi-input "mido_port:Launchkey MIDI"
```

### MIDI File Playback

```bash
# Play MIDI file in real-time
python vibexg.py --midi-input "file:song.mid"

# With tempo adjustment
python vibexg.py --midi-input "file:song.mid:0.8" --audio-output "file:output.wav"
```

### Scriptable Input (Stdin)

Send JSON MIDI messages via stdin:

```bash
echo '{"type": "note_on", "channel": 0, "data": {"note": 60, "velocity": 80}}' | \
  python vibexg.py --midi-input stdin
```

### Network MIDI (RTP-MIDI)

```yaml
# In config file
midi_inputs:
  - type: network_midi
    name: "Network MIDI"
    host: "192.168.1.100"
    port: 5004
```

## Audio Output Examples

### Real-time to Default Device

```bash
python vibexg.py --audio-output sounddevice
```

### Real-time to Specific Device

```bash
# List devices (Python)
python -c "import sounddevice as sd; print(sd.query_devices())"

# Use specific device
python vibexg.py --audio-output "sounddevice:USB Audio Codec"
```

### Render to File

```bash
# WAV format
python vibexg.py --audio-output "file:output.wav"

# FLAC format
python vibexg.py --audio-output "file:output.flac"

# With MIDI file input
python vibexg.py --midi-input "file:song.mid" --audio-output "file:rendered.ogg"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    XG Workstation                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Keyboard   │  │  MIDI Ports  │  │  File/Net    │      │
│  │    Input     │  │    Input     │  │    Input     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │  MIDI Parser    │                        │
│                  │  (Realtime)     │                        │
│                  └────────┬────────┘                        │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│  ┌──────▼──────┐  ┌───────▼────────┐ ┌─────▼──────┐       │
│  │  Recording  │  │   Synthesizer  │ │  Metronome │       │
│  │   Engine    │  │    (XG Core)   │ │   Engine   │       │
│  └─────────────┘  └───────┬────────┘ └────────────┘       │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│  ┌──────▼──────┐  ┌───────▼────────┐ ┌─────▼──────┐       │
│  │ SoundDevice │  │  File Renderer │  │    TUI     │       │
│  │   Output    │  │     Output     │  │  Control   │       │
│  └─────────────┘  └────────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Performance Tuning

### Low Latency Setup

```yaml
audio:
  sample_rate: 48000      # Higher sample rate = lower latency
  buffer_size: 256        # Smaller buffer = lower latency (more CPU)
  block_size: 512

advanced:
  audio_thread_priority: realtime
  preallocate_buffers: true
```

### High Quality Setup

```yaml
audio:
  sample_rate: 44100
  buffer_size: 1024       # Larger buffer = more stable (higher latency)
  block_size: 2048

synthesizer:
  max_polyphony: 256
```

### Troubleshooting

#### Audio Crackling/Dropouts

1. Increase buffer size: `--buffer-size 1024`
2. Lower sample rate: `--sample-rate 44100`
3. Reduce polyphony in config
4. Close other audio applications

#### MIDI Input Not Working

1. Check available ports: `--list-ports`
2. Verify exact port name (case-sensitive)
3. Ensure mido is installed: `pip install mido`
4. Check MIDI device permissions (Linux: add user to `audio` group)

#### High CPU Usage

1. Reduce max_polyphony in config
2. Disable unused effects
3. Increase buffer size
4. Use optimized SoundFonts

## API Usage

The workstation can also be used programmatically:

```python
from vibexg import XGWorkstation, MIDIInputConfig, AudioOutputConfig
from synth.midi import MIDIMessage

# Create workstation
workstation = XGWorkstation()

# Add MIDI input
keyboard_config = MIDIInputConfig(
    interface_type='keyboard',
    name='Keyboard',
    transpose=0
)
workstation.add_midi_input(keyboard_config)

# Configure audio output
audio_config = AudioOutputConfig(
    output_type='sounddevice',
    sample_rate=44100,
    buffer_size=512
)
workstation.set_audio_output(audio_config)

# Start
workstation.start()

# Send MIDI programmatically
note_on = MIDIMessage(
    type='note_on',
    channel=0,
    data={'note': 60, 'velocity': 80},
    timestamp=time.time()
)
workstation.send_midi(note_on)

# Stop
workstation.stop()
```

## Examples

### Live Performance Setup

```bash
# Keyboard + USB MIDI controller + real-time audio
python vibexg.py \
  --midi-input keyboard \
  --midi-input "mido_port:Launchkey MIDI" \
  --audio-output "sounddevice:USB Audio Interface"
```

### MIDI File Rendering

```bash
# Render MIDI file to high-quality FLAC
python vibexg.py \
  --midi-input "file:composition.mid" \
  --audio-output "file:composition.flac" \
  --sample-rate 48000 \
  --buffer-size 2048
```

### Interactive Practice Session

```bash
# Load song, enable metronome, record practice
python vibexg.py \
  --midi-input "file:backing_track.mid" \
  --config practice_config.yaml
```

### Network MIDI Session

```bash
# Receive MIDI from remote computer over network
python vibexg.py \
  --midi-input network_midi \
  --audio-output sounddevice \
  --config network_config.yaml
```

## License

MIT License - See LICENSE file for details.

## Contributing

See CONTRIBUTING.md for guidelines on contributing to this project.
