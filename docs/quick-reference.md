# XG Synthesizer Quick Reference

Quick reference guide for common tasks.

---

## Quick Start

```python
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
import mido
import soundfile as sf

# Create synthesizer
synth = ModernXGSynthesizer(sample_rate=44100)

# Set piano program
synth.set_channel_program(channel=0, bank=0, program=0)

# Play note (MIDI message)
msg_on = mido.Message('note_on', channel=0, note=60, velocity=100)
synth.process_midi_message(msg_on.bytes())

# Generate audio
audio = synth.generate_audio_block(1024)

# Stop note
msg_off = mido.Message('note_off', channel=0, note=60)
synth.process_midi_message(msg_off.bytes())

# Save
sf.write('output.wav', audio, 44100)
```

---

## Common Tasks

### Load SoundFont
```python
synth.load_soundfont("piano.sf2")
synth.set_channel_program(0, 0, 0)
```

### Render MIDI File
```bash
python render_midi.py input.mid output.wav
```

### Convert MIDI to XGML
```bash
python midi_to_xgml.py input.mid output.xgml
```

### Set Effects
```python
synth.set_xg_reverb_type(4)  # Hall reverb
synth.set_xg_chorus_type(1)  # Chorus 1
```

---

## MIDI Messages

| Message | Bytes | Example |
|---------|-------|---------|
| Note On | 9x nn vv | `mido.Message('note_on', note=60, velocity=100)` |
| Note Off | 8x nn vv | `mido.Message('note_off', note=60)` |
| CC | Bx cc vv | `mido.Message('control_change', control=7, value=100)` |
| Program | Cx pp | `mido.Message('program_change', program=0)` |
| Pitch Bend | Ex ll hh | `mido.Message('pitch_bend', value=8192)` |

---

## Program Numbers

| Program | Number |
|---------|--------|
| Acoustic Grand Piano | 0 |
| Electric Piano 1 | 4 |
| Acoustic Guitar | 24 |
| Electric Bass | 33 |
| String Ensemble | 48 |
| Trumpet | 56 |
| Flute | 73 |

---

## CLI Commands

```bash
# Render MIDI
render_midi.py input.mid output.wav

# With options
render_midi.py --sample-rate 48000 --format flac input.mid output.flac

# Batch
render_midi.py *.mid output/

# Convert to XGML
midi_to_xgml.py song.mid
```

---

## XGML Example

```yaml
xg_dsl_version: "2.1"
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      reverb_send: 40
```

---

*Generated: 2026-02-20*
