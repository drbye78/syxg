# 🚀 Getting Started with XG Synthesizer

Welcome to the XG Synthesizer! This guide will help you get up and running quickly with professional MIDI synthesis.

## 📋 Prerequisites

Before you begin, make sure you have:

1. **Python 3.11+** installed
2. **XG Synthesizer** installed (see [Installation Guide](../../INSTALL.md))
3. **Basic MIDI file** for testing (or use our examples)

## 🎵 Your First Synthesis

### Step 1: Basic MIDI Rendering

Let's start by rendering a MIDI file to audio:

```bash
# Navigate to the project directory
cd xg-synthesizer

# Render a MIDI file (replace 'input.mid' with your MIDI file)
render-midi examples/simple_piano.xgdsl output.wav

# Listen to the result
# On Linux/macOS: aplay output.wav or afplay output.wav
# On Windows: start output.wav
```

### Step 2: Python API Usage

Here's how to use the XG Synthesizer programmatically:

```python
#!/usr/bin/env python3
"""
Basic XG Synthesizer usage example
"""

from synth.synthesizers.rendering import ModernXGSynthesizer
import numpy as np

def main():
    # Create synthesizer instance
    synth = ModernXGSynthesizer(
        sample_rate=44100,      # Audio sample rate
        xg_enabled=True,        # Enable XG features
        gs_enabled=True,        # Enable GS features
        mpe_enabled=False       # Disable MPE
    )

    # Load SoundFont (optional)
    # synth.load_soundfont("path/to/soundfont.sf2")

    # Set channel program (bank, program)
    synth.set_channel_program(channel=0, bank=0, program=0)  # Acoustic Grand Piano

    # Method 1: Generate audio block programmatically
    print("Generating audio block...")
    block_size = 1024
    audio = synth.generate_audio_block(block_size)
    # audio shape: (block_size, 2) for stereo

    # Method 2: Process MIDI messages and generate audio
    print("Processing MIDI...")
    # Send a note on message (example using mido)
    import mido
    msg = mido.Message('note_on', channel=0, note=60, velocity=100)
    synth.process_midi_message(msg.bytes())
    
    # Generate audio after MIDI input
    audio = synth.generate_audio_block(block_size)

    # Save the generated audio
    import soundfile as sf
    sf.write('test_note.wav', audio, synth.sample_rate)
    print("✅ Audio generated successfully!")

if __name__ == "__main__":
    main()
```

### Step 3: Real-time Synthesis

For real-time playback, use MIDI message processing:

```python
#!/usr/bin/env python3
"""
Real-time XG Synthesizer example
"""

from synth.synthesizers.rendering import ModernXGSynthesizer
import time
import mido

def main():
    # Create synthesizer with real-time settings
    synth = ModernXGSynthesizer(
        sample_rate=44100,
        xg_enabled=True,
        gs_enabled=True,
        mpe_enabled=False
    )

    # Set channel program
    synth.set_channel_program(channel=0, bank=0, program=0)  # Piano

    # Play a sequence of notes using MIDI messages
    notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale

    print("🎹 Playing C major scale...")

    for note in notes:
        # Note on - send MIDI message
        msg = mido.Message('note_on', channel=0, note=note, velocity=100)
        synth.process_midi_message(msg.bytes())
        time.sleep(0.5)  # Hold for 500ms

        # Note off
        msg = mido.Message('note_off', channel=0, note=note, velocity=64)
        synth.process_midi_message(msg.bytes())
        time.sleep(0.1)  # Brief pause between notes

    # Generate final audio block
    audio = synth.generate_audio_block(1024)
    
    # Save output
    import soundfile as sf
    sf.write('scale_output.wav', audio, synth.sample_rate)
    print("✅ Scale playback complete!")

if __name__ == "__main__":
    main()
```

## 🎼 XGML Configuration Basics

XGML (XG Markup Language) is our human-readable configuration format. Here's a basic setup:

```yaml
# basic_piano.xgdsl
xg_dsl_version: "2.1"
description: "Simple acoustic piano setup"

basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      reverb_send: 40
      chorus_send: 20
```

### Loading XGML Configurations

```python
# Load from file
synth.load_xgml_config("my_config.xgdsl")

# Load from string
xgml_config = """
xg_dsl_version: "2.1"
basic_messages:
  channels:
    channel_1:
      program_change: "electric_piano_1"
      volume: 110
"""

synth.load_xgml_string(xgml_config)
```

## 🎛️ Common Configuration Examples

### 1. Multi-instrument Setup

```yaml
# multi_instrument.xgdsl
xg_dsl_version: "2.1"
description: "Piano + strings ensemble"

basic_messages:
  channels:
    channel_1:  # Piano
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "left_20"

    channel_2:  # Strings
      program_change: "string_ensemble_1"
      volume: 80
      pan: "right_20"
      reverb_send: 60
```

### 2. Effects Processing

```yaml
# with_effects.xgdsl
xg_dsl_version: "2.1"
description: "Instrument with effects"

basic_messages:
  channels:
    channel_1:
      program_change: "electric_guitar_clean"
      volume: 100

effects_configuration:
  system_effects:
    reverb:
      type: 4
      time: 2.0
      level: 0.7
    chorus:
      type: 1
      rate: 0.5
      depth: 0.6
```

### 3. Advanced Engine Selection

```yaml
# advanced_engines.xgdsl
xg_dsl_version: "2.1"
description: "Using advanced synthesis engines"

synthesis_engines:
  default_engine: "fm"
  part_engines:
    part_0: "fm"      # FM synthesis for leads
    part_1: "sfz"     # Sample playback for drums
    part_2: "physical" # Physical modeling for acoustic

# Configure FM engine
fm_x_engine:
  enabled: true
  algorithm: 1
  operators:
    op_0:
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
```

## 🎹 MIDI File Preparation

### Creating MIDI Files

You can create MIDI files using:

1. **Digital Audio Workstations (DAW)**:
   - Logic Pro, Ableton Live, FL Studio, Reaper
   - Export as Standard MIDI File (.mid)

2. **Online Tools**:
   - MIDI editors, piano roll interfaces
   - Simple melody creation tools

3. **Programming**:
   ```python
   from midiutil import MIDIFile

   # Create MIDI file
   midi = MIDIFile(1)  # One track
   midi.addTrackName(0, 0, "XG Synth Track")
   midi.addTempo(0, 0, 120)

   # Add notes
   midi.addNote(0, 0, 60, 0, 1, 100)    # C4
   midi.addNote(0, 0, 64, 1, 1, 100)    # E4
   midi.addNote(0, 0, 67, 2, 1, 100)    # G4

   # Save file
   with open("chord.mid", "wb") as f:
       midi.writeFile(f)
   ```

### MIDI File Requirements

- **Format**: Standard MIDI File (SMF) format 0 or 1
- **Resolution**: 96-1920 PPQ (pulses per quarter note)
- **Tempo**: 60-200 BPM recommended
- **Channels**: 1-16 (XG standard)
- **Notes**: 0-127 (C-2 to G8)

## 🔧 Troubleshooting

### Common Issues

#### 1. No Audio Output
```bash
# Check audio setup
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test basic audio
python -c "import sounddevice as sd; sd.play([0.1, 0.2, 0.1, -0.1], 44100); sd.wait()"
```

#### 2. Import Errors
```bash
# Check installation
pip list | grep xg

# Reinstall if needed
pip install -e .
```

#### 3. MIDI File Issues
```bash
# Validate MIDI file
python -c "
import mido
mid = mido.MidiFile('your_file.mid')
print(f'Tracks: {len(mid.tracks)}')
print(f'Tempo: {mid.ticks_per_beat} TPB')
for msg in mid.tracks[0][:10]:
    print(msg)
"
```

#### 4. Performance Issues
```python
# Optimize settings
synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=2048,  # Larger buffer = less CPU
    enable_optimization=True
)
```

### Getting Help

- **Documentation**: Check [User Guide](user-guide.md) and [XGML Reference](../../XGML_README.md)
- **Examples**: Browse `examples/` directory for working code
- **Issues**: Report bugs on [GitHub Issues](https://github.com/drbye78/syxg/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/drbye78/syxg/discussions)

## 🎯 Next Steps

Now that you have the basics working, try these advanced features:

1. **Experiment with XGML**: Create custom instrument configurations
2. **Try Different Engines**: Switch between SF2, FM, SFZ, and Physical modeling
3. **Add Effects**: Apply reverb, chorus, and other processing
4. **Real-time Control**: Use MIDI controllers for live performance
5. **Batch Processing**: Render multiple MIDI files automatically

### Learning Path

1. **[User Guide](user-guide.md)** - Complete feature overview
2. **[XGML Reference](../../XGML_README.md)** - Configuration language
3. **[Engine Documentation](../../engines/)** - Synthesis engine details
4. **[API Reference](../../api/)** - Developer documentation
5. **[Examples](../../examples/)** - Working code samples

---

**🎹 Happy synthesizing! Transform your MIDI into professional audio with the XG Synthesizer.**
