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
xg_dsl_version: "2.1"          # Required: Schema version (v2.1 adds advanced engine controls)
description: "Optional description"
timestamp: "2025-12-23T18:00:00Z"  # Optional: ISO timestamp

# Configuration sections
basic_messages: {...}          # Static MIDI messages
rpn_parameters: {...}          # Registered parameters
channel_parameters: {...}      # XG channel parameters
drum_parameters: {...}         # Drum kit parameters
system_exclusive: {...}        # SYSEX messages
effects: {...}                 # Effects configuration

# Modern Engine Configurations (v2.1)
fm_x_engine: {...}             # FM-X synthesis engine
sfz_engine: {...}              # SFZ sample playback engine
physical_engine: {...}         # Physical modeling engine
spectral_engine: {...}         # Spectral processing engine

# Advanced Features
arpeggiator_configuration: {...} # Yamaha Motif arpeggiator
microtonal_tuning: {...}       # Alternative tuning systems
modulation_matrix: {...}       # Advanced modulation routing

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

### Modern Synthesis Engines
XGML now supports multiple advanced synthesis engines for modern sound design:
```yaml
synthesis_engines:
  default_engine: "sfz"                    # Default engine for all parts
  part_engines:
    part_0: "fm"                           # FM synthesis for lead sounds
    part_1: "wavetable"                    # Wavetable for pads
    part_2: "physical"                     # Physical modeling for acoustic
    part_3: "spectral"                     # Spectral processing for effects
  engine_parameters:
    fm:
      algorithm: 1
      feedback: 0.3
    wavetable:
      table_size: 2048
      interpolation: "cubic"
```

### GS Compatibility Mode
Full GS (Roland General MIDI 2) compatibility with enhanced features:
```yaml
gs_configuration:
  enabled: true
  mode: "auto"                            # auto, gs, or xg
  system_effects:
    reverb_type: 4                        # GS reverb types 0-7
    chorus_type: 2                        # GS chorus types 0-7
  multi_part:
    voice_reserve: [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]  # Per-part voice allocation
```

### MPE (Microtonal Expression)
Complete MPE support for expressive microtonal control:
```yaml
mpe_configuration:
  enabled: true
  zones:
    - zone_id: 1
      lower_channel: 0
      upper_channel: 7
      pitch_bend_range: 48                # ±48 semitones
      timbre_cc: 74                       # CC74 for timbre
    - zone_id: 2
      lower_channel: 8
      upper_channel: 15
      pitch_bend_range: 24                # ±24 semitones
  global_settings:
    pressure_active: true                 # Per-note pressure
    slide_active: true                    # Slide control
    lift_active: true                     # Lift control
```

### Advanced Effects Processing
Professional-grade effects with detailed parameter control:
```yaml
effects_configuration:
  system_effects:
    reverb:
      type: 4                             # XG reverb type
      time: 2.5                           # Reverb time in seconds
      level: 0.8                          # Wet/dry mix
      hf_damping: 0.3                     # High frequency damping
    chorus:
      type: 1                             # XG chorus type
      rate: 0.5                           # Chorus rate in Hz
      depth: 0.6                          # Chorus depth
  variation_effects:
    type: 12                              # Delay effect
    parameters:
      delay_time: 300                     # Delay time in ms
      feedback: 0.4                       # Feedback amount
  master_processing:
    equalizer:
      type: 2                             # Jazz EQ preset
      bands:
        low: {gain: 2.0, frequency: 80}
        mid: {gain: -1.5, frequency: 1000, q: 1.4}
    limiter:
      threshold: -0.1                     # Limiter threshold
      release: 100                        # Release time in ms
```

### Arpeggiator System
Advanced Yamaha Motif-style arpeggiator with custom patterns:
```yaml
arpeggiator_configuration:
  enabled: true
  global_settings:
    tempo: 128                            # Arpeggiator tempo
    swing: 0.2                            # Swing amount
    gate_time: 0.9                        # Note gate time
  patterns:
    - id: "custom_up"
      name: "Custom Up Pattern"
      steps:
        - step: 0, note: 60, velocity: 100
        - step: 1, note: 64, velocity: 80
        - step: 2, note: 67, velocity: 90
      length: 3
      type: "up"
  channel_assignments:
    - channel: 0
      pattern_id: "custom_up"
      octave_range: 2
```

### Microtonal Tuning
Support for various temperaments and custom tunings:
```yaml
microtonal_tuning:
  temperament: "just"                     # just, pythagorean, meantone, etc.
  custom_tuning:
    notes:
      C: 0.0                              # Reference note
      C#: 3.9                             # Just major second
      D: -3.9                             # Just major second (different direction)
    octaves: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # Per-octave offsets
  global_offset: 0.0                      # Global tuning offset in cents
  a4_frequency: 442.0                     # A4 reference frequency
```

### Advanced Modulation Matrix
Comprehensive modulation routing system:
```yaml
modulation_matrix:
  sources: ["lfo1", "lfo2", "envelope", "velocity", "aftertouch", "timbre", "slide"]
  destinations: ["pitch", "volume", "pan", "filter_cutoff", "filter_resonance", "timbre"]
  routes:
    - source: "velocity"
      destination: "filter_cutoff"
      amount: 0.7
      curve: "exponential"
    - source: "lfo1"
      destination: "pitch"
      amount: -0.2
      bipolar: true
    - source: "timbre"
      destination: "volume"
      amount: 0.5
      channel: 0                          # Per-channel modulation
```

## 🎚️ Advanced Engine Configurations (XGML v2.1)

XGML v2.1 introduces comprehensive support for advanced synthesis engines with deep parameter control.

### FM-X Engine Configuration
Complete control over Yamaha FM-X synthesis with 8 operators, algorithms, and modulation:

```yaml
fm_x_engine:
  enabled: true
  algorithm: 1                            # FM algorithm (0-87)
  algorithm_name: "Basic FM"
  master_volume: 0.8                      # Master volume (0.0-1.0)
  pitch_bend_range: 2                     # Pitch bend range in semitones

  # 8 FM operators with full control
  operators:
    op_0:                                 # Carrier operator
      enabled: true
      frequency_ratio: 1.0                # Frequency ratio
      detune_cents: 0                     # Detune in cents (-100 to 100)
      feedback_level: 0                   # Feedback (0-7)
      waveform: "sine"                    # sine, triangle, sawtooth, square

      # 8-stage envelope with loop support
      envelope:
        levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]  # 8 levels
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]  # 8 rates
        loop_start: -1                     # Loop start stage (-1 = no loop)
        loop_end: -1                       # Loop end stage

      # Operator scaling
      scaling:
        key_depth: 0                      # Key scaling depth (0-7)
        velocity_sensitivity: 0           # Velocity sensitivity (0-7)
        key_curve: "linear"               # linear, exp, log

      # Formant synthesis for vocals
      formant_synthesis:
        enabled: false
        vowel: "a"                        # a, e, i, o, u, or custom
        custom_formant:
          frequency: 700                  # Formant frequency in Hz
          bandwidth: 50                   # Bandwidth in Hz
          gain: 2.0                       # Gain multiplier

      # Per-operator LFO
      lfo_modulation:
        depth: 0.0                        # LFO depth (0.0-1.0)
        waveform: "sine"                  # sine, triangle, sawtooth, square, random
        speed: 1.0                        # Speed in Hz

    op_1:                                 # Modulator operator
      enabled: true
      frequency_ratio: 0.5
      feedback_level: 2
      # ... additional operators 2-7

  # LFO system (3 global LFOs)
  lfos:
    lfo_0:
      enabled: true
      waveform: "sine"
      frequency: 1.0                      # Hz
      depth: 1.0
      phase: 0.0                          # degrees
      assignable: true                    # Can be used in modulation matrix

  # Ring modulation connections
  ring_modulation:
    - [0, 1]                             # Operator 0 ring modulates operator 1

  # Advanced modulation matrix (128 assignments)
  modulation_matrix:
    - source: "lfo0"
      destination: "pitch"
      amount: 0.5
      bipolar: true                       # Bipolar modulation
    - source: "velocity"
      destination: "amplitude"
      amount: 0.7
      curve: "exponential"

  # Effects sends
  effects_sends:
    reverb: 0.3
    chorus: 0.2
    delay: 0.1
```

### SFZ Engine Configuration
Professional sample playback with region overrides and modulation:

```yaml
sfz_engine:
  enabled: true
  instrument_path: "piano.sfz"            # SFZ instrument file path

  # Global SFZ parameters
  global_parameters:
    volume: 0.0                          # Volume in dB (-144 to 6)
    pan: 0.0                             # Pan (-100 to 100)
    tune: 0                              # Tuning offset in cents (-100 to 100)
    transpose: 0                         # Transposition in semitones (-127 to 127)

  # Region parameter overrides
  region_overrides:
    - lokey: 36                          # Low key limit
      hikey: 72                          # High key limit
      lovel: 1                           # Low velocity
      hivel: 127                         # High velocity
      sample: "piano_C4.wav"              # Override sample file
      volume: 6.0                         # Volume in dB
      pan: -10.0                         # Pan position
      tune: 1200                         # Tuning in cents (+1 octave)
      pitch_keycenter: 60                # Pitch key center
      cutoff: 8000.0                     # Filter cutoff
      resonance: 2.0                     # Filter resonance
      ampeg_attack: 0.01                 # Amp envelope attack
      ampeg_decay: 0.3                   # Amp envelope decay
      ampeg_sustain: 0.8                 # Amp envelope sustain
      ampeg_release: 1.0                 # Amp envelope release
      loop_mode: "loop_continuous"       # Sample loop mode
      round_robin: 1                     # Round robin group

  # Modulation assignments
  modulation_assignments:
    - source: "cc1"                      # Mod wheel
      destination: "volume"
      amount: 50.0                       # -100 to 100
      curve: "linear"                    # linear, concave, convex, switch
    - source: "velocity"
      destination: "cutoff"
      amount: 70.0
      curve: "concave"

  # Sample preloading configuration
  sample_preload:
    enabled: true
    max_samples: 100                     # Maximum samples to preload
    priority_regions:
      - "C4-C6"                          # Priority key ranges
```

### Physical Modeling Engine Configuration
Waveguide synthesis and modal resonance for realistic acoustics:

```yaml
physical_engine:
  enabled: true
  model_type: "string"                   # string, woodwind, brass, percussion

  # String physical modeling
  string_parameters:
    length: 0.65                         # String length in meters
    tension: 150.0                       # Tension in Newtons
    stiffness: 0.1                       # Stiffness coefficient (0.0-1.0)
    damping: 0.001                       # Damping coefficient
    pluck_position: 0.1                  # Pluck position (0.0-1.0)
    pickup_position: 0.2                 # Pickup position (0.0-1.0)
    termination_impedance: 500.0         # Bridge impedance

  # Woodwind physical modeling
  woodwind_parameters:
    bore_length: 0.3                     # Bore length in meters
    bore_radius: 0.005                   # Bore radius in meters
    reed_stiffness: 5.0                  # Reed stiffness coefficient
    reed_mass: 0.001                     # Reed mass in kg
    breath_pressure: 2000.0              # Breath pressure in Pascals
    embouchure_position: 0.3             # Embouchure position (0.0-1.0)

  # Brass physical modeling
  brass_parameters:
    bell_radius: 0.03                    # Bell radius in meters
    bell_length: 0.2                     # Bell length in meters
    mouthpiece_radius: 0.008             # Mouthpiece radius in meters
    lip_tension: 8.0                     # Lip tension coefficient
    lip_mass: 0.002                      # Lip mass in kg
    air_pressure: 50000.0                # Air pressure in Pascals

  # Percussion physical modeling
  percussion_parameters:
    material: "wood"                     # wood, metal, membrane, glass, plastic
    geometry: "circular"                 # circular, rectangular, triangular
    dimensions: [0.3, 0.3]               # Dimensions in meters
    thickness: 0.005                     # Material thickness in meters
    youngs_modulus: 1.1e10               # Young's modulus in Pa
    poissons_ratio: 0.3                  # Poisson's ratio
    damping_ratio: 0.001                 # Damping ratio

  # Waveguide synthesis
  waveguide_parameters:
    delay_length: 500                    # Delay length in samples
    reflection_coefficients: [0.5, 0.3, 0.1]  # Reflection coefficients
    loss_factor: 0.99                    # Energy loss per reflection
    dispersion_enabled: false            # Enable dispersion
    dispersion_coefficients: [1.0, 0.99, 0.98]  # Dispersion filter coeffs

  # Global parameters
  global_parameters:
    sample_rate: 44100                   # Physical modeling sample rate
    oversampling: 2                      # Oversampling factor
    stability_threshold: 1.0             # Numerical stability threshold
    max_iterations: 100                  # Maximum convergence iterations
```

### Spectral Processing Engine Configuration
FFT-based spectral processing with morphing and filtering:

```yaml
spectral_engine:
  enabled: true
  mode: "morph"                         # filter, morph, freeze, shift, stretch

  # FFT analysis settings
  fft_settings:
    fft_size: 2048                      # FFT size (power of 2)
    hop_size: 512                       # Hop size in samples
    window_type: "hann"                 # hann, hamming, blackman, kaiser
    overlap_factor: 0.5                 # Overlap factor (0.125-1.0)

  # Spectral processing parameters
  spectral_parameters:
    formant_shift: 1.0                  # Formant shift ratio (0.1-10.0)
    pitch_shift: 1.0                    # Pitch shift ratio (0.1-4.0)
    spectral_tilt: 0.0                  # Spectral tilt in dB (-24 to 24)
    brightness_boost: 0.0               # High frequency boost in dB
    freeze_position: 0.0                # Freeze position (0.0-1.0)
    freeze_enabled: false               # Enable spectral freeze
    bin_shift_amount: 0                 # Spectral bin shift (-100 to 100)

  # Spectral morphing
  morphing:
    enabled: true
    source_a: "sound1.wav"              # Source A audio file
    source_b: "sound2.wav"              # Source B audio file
    morph_position: 0.5                 # Morph position (0=A, 1=B)
    morph_rate: 1.0                     # Morph rate in Hz
    crossfade_curve: "equal_power"      # linear, equal_power, exponential

  # Spectral filtering
  filtering:
    filter_type: "lowpass"              # lowpass, highpass, bandpass, bandstop
    cutoff_frequency: 1000.0            # Cutoff in Hz
    bandwidth: 1.0                      # Bandwidth in octaves
    gain: 0.0                           # Gain in dB
    order: 2                            # Filter order
    q: 0.707                           # Q factor

  # Time stretching
  time_stretching:
    enabled: false
    stretch_factor: 1.0                 # Time stretch factor (0.1-10.0)
    preserve_pitch: true                # Preserve pitch during stretching
    quality: "standard"                 # fast, standard, high, ultra

  # Output processing
  output_processing:
    dry_wet_mix: 1.0                    # Dry/wet mix (0=dry, 1=wet)
    output_gain: 0.0                    # Output gain in dB
    stereo_spread: 0.0                  # Stereo spread amount (0.0-1.0)
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
