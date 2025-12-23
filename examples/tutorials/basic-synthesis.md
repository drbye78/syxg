# 🎼 Basic Synthesis Tutorial - XG Synthesizer

Welcome to your first XG Synthesizer tutorial! This guide will walk you through creating your first synthesized sounds using the XG Synthesizer's powerful synthesis engines.

## 🎯 Tutorial Goals

By the end of this tutorial, you will:
- Understand the basic concepts of synthesis
- Create simple sounds using different synthesis engines
- Control parameters to shape your sound
- Save and reuse your configurations

## 📋 Prerequisites

- XG Synthesizer installed (see [Installation Guide](../../INSTALL.md))
- Basic understanding of MIDI (notes, velocity, channels)
- A MIDI file or keyboard for testing

## 🎵 Lesson 1: Your First Sound - Simple Waveforms

Let's start with the most basic synthesis: generating pure waveforms.

### Step 1: Create a Basic Configuration

Create a new file called `my_first_sound.xgdsl`:

```yaml
# My First XG Synthesizer Sound
xg_dsl_version: "2.1"
description: "Basic sine wave sound for learning"

# Use additive synthesis for pure waveforms
synthesis_engines:
  default_engine: "additive"

# Simple piano-like settings
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
```

### Step 2: Generate Your First Audio

```bash
# Render a simple melody
echo "Creating a test MIDI note..."
python3 -c "
import mido
mid = mido.MidiFile()
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.Message('note_on', note=60, velocity=100, time=0))
track.append(mido.Message('note_off', note=60, velocity=64, time=1920))  # 1 second at 120 BPM
mid.save('test_note.mid')
"

# Render with your configuration
render-midi test_note.mid first_sound.wav --config my_first_sound.xgdsl
```

### Step 3: Listen and Analyze

```bash
# Play the sound
aplay first_sound.wav  # Linux
afplay first_sound.wav # macOS
start first_sound.wav  # Windows

# Analyze the waveform (optional)
python3 -c "
import librosa
import matplotlib.pyplot as plt

audio, sr = librosa.load('first_sound.wav')
plt.figure(figsize=(10, 4))
plt.plot(audio[:1000])  # First 1000 samples
plt.title('Your First Synthesized Sound')
plt.show()
"
```

**What you should hear:** A clean, pure tone. This is the fundamental building block of synthesis!

## 🎹 Lesson 2: Additive Synthesis - Building Complex Tones

Additive synthesis creates complex sounds by adding multiple sine waves together.

### Step 1: Understanding Harmonics

Every sound can be broken down into harmonics:
- **Fundamental**: The base frequency (C4 = 261.63 Hz)
- **2nd Harmonic**: 2x fundamental (523.25 Hz)
- **3rd Harmonic**: 3x fundamental (784.88 Hz)
- And so on...

### Step 2: Create a Sawtooth Wave

A sawtooth wave contains all harmonics with decreasing amplitudes:

```yaml
# sawtooth_wave.xgdsl
xg_dsl_version: "2.1"
description: "Sawtooth wave using additive synthesis"

synthesis_engines:
  default_engine: "additive"

# Configure additive synthesis
additive_engine:
  enabled: true
  num_partials: 16
  harmonic_structure: "sawtooth"  # All harmonics, amplitude = 1/n

  # Fine-tune the harmonics
  partials:
    - harmonic: 1, amplitude: 1.0, phase: 0.0    # Fundamental
    - harmonic: 2, amplitude: 0.5, phase: 0.0    # Octave
    - harmonic: 3, amplitude: 0.33, phase: 0.0   # Fifth
    - harmonic: 4, amplitude: 0.25, phase: 0.0   # Two octaves
    # ... continues with 1/n amplitude
```

### Step 3: Experiment with Different Waveforms

#### Square Wave (Odd Harmonics Only)
```yaml
additive_engine:
  enabled: true
  harmonic_structure: "square"  # Only odd harmonics: 1, 3, 5, 7...
  num_partials: 8
```

#### Triangle Wave (Odd Harmonics with 1/n²)
```yaml
additive_engine:
  enabled: true
  harmonic_structure: "triangle"  # Odd harmonics with 1/n² amplitude
  num_partials: 6
```

#### Custom Harmonic Series
```yaml
additive_engine:
  enabled: true
  partials:
    - harmonic: 1, amplitude: 1.0, phase: 0.0     # Fundamental
    - harmonic: 2, amplitude: 0.3, phase: 1.57    # Octave (90° phase)
    - harmonic: 3, amplitude: 0.2, phase: 0.0     # Fifth
    - harmonic: 4, amplitude: 0.1, phase: 3.14    # Two octaves (180° phase)
    - harmonic: 5, amplitude: 0.05, phase: 0.0    # Major third
```

### Step 4: Render and Compare

```bash
# Render different waveforms
render-midi test_note.mid sawtooth.wav --config sawtooth_wave.xgdsl
render-midi test_note.mid square.wav --config square_wave.xgdsl
render-midi test_note.mid triangle.wav --config triangle_wave.xgdsl

# Listen to the differences
# Each waveform has a distinct character and harmonic content
```

**Learning Points:**
- Different waveforms have unique harmonic spectra
- Sawtooth: Bright, rich sound with all harmonics
- Square: Hollow, nasal quality with odd harmonics only
- Triangle: Softer, flute-like with fewer harmonics

## 🎛️ Lesson 3: FM Synthesis - Dynamic Timbre Control

FM (Frequency Modulation) synthesis creates complex sounds by modulating one oscillator with another.

### Step 1: Simple FM Configuration

```yaml
# simple_fm.xgdsl
xg_dsl_version: "2.1"
description: "Simple FM bell sound"

synthesis_engines:
  default_engine: "fm"

fm_x_engine:
  enabled: true
  algorithm: 0                    # Simple FM: Op0 modulates Op1
  master_volume: 0.8

  operators:
    op_0:                         # Modulator
      frequency_ratio: 1.0        # Same frequency as carrier
      feedback_level: 2           # Some feedback for brightness
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    op_1:                         # Carrier
      frequency_ratio: 1.0        # Fundamental frequency
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Step 2: Understanding FM Parameters

**Frequency Ratio**: Determines the modulation frequency relative to the carrier
- Ratio = 1.0: Same frequency (harmonic modulation)
- Ratio = 2.0: One octave higher
- Ratio = 0.5: One octave lower

**Feedback**: Self-modulation of the modulator
- Creates additional harmonics and brightness
- Values 0-7 (0 = no feedback, 7 = maximum)

**Envelope**: Controls how the modulation evolves over time
- Fast attack + fast decay = percussive bell sounds
- Slow attack + long decay = evolving pads

### Step 3: Create Different FM Sounds

#### Bell Sound
```yaml
fm_x_engine:
  algorithm: 0
  operators:
    op_0:                         # Bright, fast modulator
      frequency_ratio: 1.4        # Inharmonic ratio
      feedback_level: 6           # Lots of feedback
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.03, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    op_1:                         # Ringing carrier
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.08, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

#### Bass Sound
```yaml
fm_x_engine:
  algorithm: 1                   # Stacked FM
  operators:
    op_0:                        # Sub-bass fundamental
      frequency_ratio: 0.5
      envelope:
        levels: [0.0, 1.0, 0.8, 0.3, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0, 0.0]
    op_1:                        # Body enhancer
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 0.7, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.1, 0.3, 0.5, 0.0, 0.0, 0.0, 0.0]
    op_2:                        # Bite/high end
      frequency_ratio: 2.0
      envelope:
        levels: [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Step 4: Experiment with FM

```bash
# Render different FM sounds
render-midi test_note.mid fm_bell.wav --config bell_fm.xgdsl
render-midi test_note.mid fm_bass.wav --config bass_fm.xgdsl

# Try different velocities
python3 -c "
import mido
mid = mido.MidiFile()
track = mido.MidiTrack()
mid.tracks.append(track)
# Soft note
track.append(mido.Message('note_on', note=60, velocity=50, time=0))
track.append(mido.Message('note_off', note=60, velocity=64, time=1920))
# Loud note
track.append(mido.Message('note_on', note=60, velocity=120, time=1920))
track.append(mido.Message('note_off', note=60, velocity=64, time=1920))
mid.save('velocity_test.mid')
"

render-midi velocity_test.mid velocity_fm.wav --config simple_fm.xgdsl
```

## 🎚️ Lesson 4: Sample Playback with SFZ

Learn to use pre-recorded samples with SFZ format.

### Step 1: Basic SFZ Setup

First, you'll need some sample files. For this tutorial, you can use any WAV files:

```
samples/
├── piano_C4.wav
├── piano_D4.wav
├── piano_E4.wav
└── piano_F4.wav
```

### Step 2: Create SFZ Instrument

Create `piano.sfz`:

```
<global>
volume=0

<group>
key=60          // C4
lovel=1 hivel=127
sample=piano_C4.wav

<group>
key=62          // D4
lovel=1 hivel=127
sample=piano_D4.wav

<group>
key=64          // E4
lovel=1 hivel=127
sample=piano_E4.wav

<group>
key=65          // F4
lovel=1 hivel=127
sample=piano_F4.wav
```

### Step 3: XGML Configuration for SFZ

```yaml
# sfz_piano.xgdsl
xg_dsl_version: "2.1"
description: "SFZ sample-based piano"

synthesis_engines:
  default_engine: "sfz"

sfz_engine:
  enabled: true
  instrument_path: "piano.sfz"

  global_parameters:
    volume: 6.0                  # dB boost for samples
    pan: 0.0
    tune: 0

  # Optional: Override specific regions
  region_overrides:
    - lokey: 60, hikey: 60       # C4
      volume: 3.0
      tune: 1200                 # +1 octave if needed
```

### Step 4: Render Sample-Based Audio

```bash
# Create a melody using the sample range
python3 -c "
import mido
mid = mido.MidiFile()
track = mido.MidiTrack()
mid.tracks.append(track)
# Simple melody: C4 D4 E4 C4
notes = [60, 62, 64, 60]
time = 0
for note in notes:
    track.append(mido.Message('note_on', note=note, velocity=100, time=time))
    time = 960  # Quarter note at 120 BPM
    track.append(mido.Message('note_off', note=note, velocity=64, time=time))
    time = 0
mid.save('sample_melody.mid')
"

# Render with SFZ samples
render-midi sample_melody.mid piano_samples.wav --config sfz_piano.xgdsl
```

## 🎛️ Lesson 5: Effects Processing

Add professional effects to enhance your sounds.

### Step 1: Basic Reverb

```yaml
# with_reverb.xgdsl
xg_dsl_version: "2.1"
description: "Sound with reverb effect"

# Your sound configuration here...

effects_configuration:
  system_effects:
    reverb:
      type: 4                    # Hall 1
      time: 2.0                  # Reverb time in seconds
      level: 0.7                 # Wet/dry mix
      hf_damping: 0.3            # High frequency damping
```

### Step 2: Chorus Effect

```yaml
effects_configuration:
  system_effects:
    chorus:
      type: 1                    # Chorus 1
      rate: 0.5                  # LFO rate in Hz
      depth: 0.6                 # Modulation depth
      feedback: 0.3              # Feedback amount
```

### Step 3: Multiple Effects

```yaml
effects_configuration:
  system_effects:
    reverb:
      type: 4
      time: 1.5
      level: 0.5
    chorus:
      type: 1
      rate: 0.3
      depth: 0.4

  variation_effects:
    type: 12                     # Delay LCR
    parameters:
      delay_time: 300            # Delay time in ms
      feedback: 0.3
      level: 0.4
```

### Step 4: Compare With and Without Effects

```bash
# Render without effects
render-midi test_note.mid dry_sound.wav --config simple_fm.xgdsl

# Render with effects
render-midi test_note.mid wet_sound.wav --config with_effects.xgdsl

# Listen to both versions
```

## 🎼 Lesson 6: Complete Arrangement

Combine everything you've learned into a complete piece.

### Step 1: Multi-track Configuration

```yaml
# complete_song.xgdsl
xg_dsl_version: "2.1"
description: "Complete multi-track arrangement"

synthesis_engines:
  default_engine: "fm"
  part_engines:
    part_0: "fm"                 # Lead melody
    part_1: "additive"           # Bass line
    part_2: "sfz"                # Drums (if you have samples)

# Lead sound (FM)
fm_x_engine:
  enabled: true
  algorithm: 0
  operators:
    op_0:                        # Bright lead
      frequency_ratio: 1.0
      feedback_level: 3
      envelope:
        levels: [0.0, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]
    op_1:
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0]
        rates: [0.001, 0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]

# Bass sound (Additive)
additive_engine:
  enabled: true
  harmonic_structure: "triangle"
  num_partials: 8

# Effects for the mix
effects_configuration:
  system_effects:
    reverb:
      type: 4
      time: 2.5
      level: 0.6
    chorus:
      type: 1
      rate: 0.4
      depth: 0.5

  master_processing:
    equalizer:
      type: "jazz"
      bands:
        low: {gain: 2.0, frequency: 80}
        high: {gain: -1.0, frequency: 10000}
```

### Step 2: Create Multi-track MIDI

```python
# create_multitrack_midi.py
import mido

mid = mido.MidiFile()
lead_track = mido.MidiTrack()
bass_track = mido.MidiTrack()

mid.tracks.extend([lead_track, bass_track])

# Lead melody (channel 0)
lead_notes = [72, 74, 76, 77, 79, 81, 83, 84]  # C major scale
time = 0
for note in lead_notes:
    lead_track.append(mido.Message('note_on', channel=0, note=note, velocity=100, time=time))
    time = 480  # Eighth note
    lead_track.append(mido.Message('note_off', channel=0, note=note, velocity=64, time=time))
    time = 0

# Bass line (channel 1)
bass_notes = [48, 50, 52, 53, 55, 57, 59, 60]  # C major bass
time = 0
for note in bass_notes:
    bass_track.append(mido.Message('note_on', channel=1, note=note, velocity=90, time=time))
    time = 960  # Quarter note
    bass_track.append(mido.Message('note_off', channel=1, note=note, velocity=64, time=time))
    time = 0

mid.save('multitrack.mid')
```

### Step 3: Render Your Complete Arrangement

```bash
render-midi multitrack.mid complete_song.wav --config complete_song.xgdsl
```

## 🎯 Next Steps

Congratulations! You've learned the fundamentals of synthesis with XG Synthesizer. Here are some next steps:

### Advanced Topics
- **Physical Modeling**: Waveguide synthesis for acoustic instruments
- **Spectral Processing**: FFT-based effects and transformations
- **Arpeggiator**: Pattern-based note generation
- **MPE Support**: Per-note expression control
- **XGML Scripting**: Dynamic parameter control

### Experimentation Ideas
- Create your own custom waveforms using additive synthesis
- Design unique FM algorithms for new timbres
- Combine multiple synthesis engines in creative ways
- Experiment with effects chains and processing

### Resources
- **[User Guide](../../user/user-guide.md)**: Complete feature reference
- **[XGML Reference](../../XGML_README.md)**: Configuration language guide
- **[API Documentation](../../api/overview.md)**: Developer resources
- **[Engine Guides](../../engines/)**: Detailed synthesis engine documentation

---

**🎼 You've completed the Basic Synthesis Tutorial! You now understand the fundamental concepts of digital synthesis and can create your own sounds with the XG Synthesizer.**
