# 📚 **XGML v3.0 Example Configurations**

This comprehensive collection demonstrates XGML v3.0 usage across all feature levels, from basic children's piano to advanced workstation orchestras. Each example is fully functional and includes detailed explanations.

---

## 🎼 **Basic Examples (Children's Piano Level)**

### **Example 1.1: Minimal Piano**
```yaml
# The simplest possible XGML v3.0 configuration
# Works perfectly for basic piano playing
xg_dsl_version: "3.0"
```

*This single line creates a fully functional piano synthesizer with default settings.*

### **Example 1.2: Simple Piano with Reverb**
```yaml
# Basic piano with simple reverb
xg_dsl_version: "3.0"
description: "Simple piano for beginners"

effects_processing:
  system_effects:
    reverb:
      algorithm: "hall_1"
      parameters:
        time: 2.0
        level: 0.3
```

*Clean piano sound with subtle hall reverb - perfect for practice.*

### **Example 1.3: Children's Song Setup**
```yaml
# Optimized for children's piano lessons
xg_dsl_version: "3.0"
description: "Children's piano lessons"

synthesizer_core:
  performance:
    max_polyphony: 8  # Conservative for older computers

basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 85  # Comfortable listening level
```

---

## 🎹 **Intermediate Examples (Musician Level)**

### **Example 2.1: Jazz Trio**
```yaml
# Complete jazz combo setup
xg_dsl_version: "3.0"
description: "Jazz piano trio"

synthesis_engines:
  channel_engines:
    channel_0: "sf2"     # Piano
    channel_1: "sf2"     # Bass (if available)
    channel_2: "sfz"     # Drums

basic_messages:
  channels:
    channel_0:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      reverb_send: 30
    channel_1:
      program_change: "acoustic_bass"
      volume: 90
      pan: "left_20"
      reverb_send: 20
    channel_2:
      program_change: "jazz_drum_kit"
      volume: 95
      pan: "right_20"
      reverb_send: 15

effects_processing:
  system_effects:
    reverb:
      algorithm: "club"
      parameters:
        time: 1.8
        level: 0.4
        hf_damping: 0.2
```

### **Example 2.2: Rock Band**
```yaml
# Template-based rock band
template: "basic_rock_band"

# Customizations
synthesis_engines:
  sf2_engine:
    soundfont_path: "vintage_rock.sf2"

effects_processing:
  system_effects:
    reverb:
      algorithm: "room_1"
      parameters:
        time: 1.2
        level: 0.3
  variation_effects:
    - slot: 0
      type: 48  # Overdrive
      parameters:
        drive: 0.4
        tone: 0.7
```

### **Example 2.3: Classical Orchestra**
```yaml
# Template-based orchestra
template: "classical_orchestra"

# Fine-tune balance
basic_messages:
  channels:
    channel_0:  # Violins
      volume: 95
    channel_1:  # Violas
      volume: 85
    channel_2:  # Cellos
      volume: 90
    channel_3:  # Double bass
      volume: 80

effects_processing:
  system_effects:
    reverb:
      algorithm: "cathedral"
      parameters:
        time: 3.5
        level: 0.6
        diffusion: 0.8
```

---

## 🎛️ **Advanced Examples (Professional Level)**

### **Example 3.1: SF2 Professional Piano**
```yaml
# Professional piano with full SF2 control
xg_dsl_version: "3.0"
description: "Professional concert grand piano"

synthesis_engines:
  registry:
    default_engine: "sf2"
    engine_priorities:
      sf2: 100

  channel_engines:
    channel_0: "sf2"

  sf2_engine:
    enabled: true
    soundfont_path: "steinway_concert_grand.sf2"
    bank: 0
    program: 0
    velocity_curve: "concave"
    tuning: 0.0

    # S90/S70 AWM Stereo features
    awm_stereo:
      enabled: true
      stereo_width: 1.2
      compression_ratio: 1.0

    # Zone-specific overrides for expression
    zone_overrides:
      - preset: [0, 0]
        instrument: 0
        generators:
          8: 200   # Increase volume slightly
          29: 100  # Boost filter cutoff
          30: 20   # Add subtle resonance
        modulators:
          - src: 1    # CC1 (Mod wheel)
            dest: 29  # Filter cutoff
            amount: 1200  # 1 octave range

effects_processing:
  system_effects:
    reverb:
      algorithm: "concert_hall"
      parameters:
        time: 2.8
        level: 0.5
        hf_damping: 0.1
        pre_delay: 0.05
        early_reflections: 0.3
    chorus:
      algorithm: "ensemble"
      parameters:
        rate: 0.4
        depth: 0.3
        feedback: 0.1
        mix: 0.2

  master_processing:
    equalizer:
      bands:
        - frequency: 80.0
          gain: 1.0
          q: 0.8
          type: "low_shelf"
        - frequency: 3000.0
          gain: -0.5
          q: 1.2
          type: "peaking"
    limiter:
      threshold: -0.5
      ratio: 8.0
      attack: 0.5
      release: 50.0
```

### **Example 3.2: Physical Modeling Strings**
```yaml
# Physically modeled string quartet
xg_dsl_version: "3.0"
description: "Physical modeling string quartet"

synthesis_engines:
  channel_engines:
    channel_0: "physical"  # Violin 1
    channel_1: "physical"  # Violin 2
    channel_2: "physical"  # Viola
    channel_3: "physical"  # Cello

  physical_engine:
    enabled: true
    model_type: "string"

    # Violin 1 - E string
    violin_1_parameters:
      length: 0.325        # Violin string length
      tension: 65.0        # String tension
      mass_per_length: 0.0008
      stiffness: 0.05      # Inharmonicity
      damping: 0.0005      # Sustain control
      pluck_position: 0.12 # Bridge pickup position

    # Violin 2 - A string
    violin_2_parameters:
      length: 0.325
      tension: 55.0
      mass_per_length: 0.0009
      stiffness: 0.06
      damping: 0.0006
      pluck_position: 0.15

    # Viola - C string
    viola_parameters:
      length: 0.38
      tension: 48.0
      mass_per_length: 0.0012
      stiffness: 0.08
      damping: 0.0008
      pluck_position: 0.18

    # Cello - A string
    cello_parameters:
      length: 0.695
      tension: 85.0
      mass_per_length: 0.0021
      stiffness: 0.12
      damping: 0.0012
      pluck_position: 0.22

basic_messages:
  channels:
    channel_0: {program_change: "violin", volume: 85, pan: "left_30"}
    channel_1: {program_change: "violin", volume: 80, pan: "left_10"}
    channel_2: {program_change: "viola", volume: 88, pan: "right_10"}
    channel_3: {program_change: "cello", volume: 95, pan: "right_30"}

effects_processing:
  system_effects:
    reverb:
      algorithm: "chamber"
      parameters:
        time: 1.6
        level: 0.4
        diffusion: 0.9
        pre_delay: 0.03
```

### **Example 3.3: Spectral Processing Effects**
```yaml
# Advanced spectral processing workstation
xg_dsl_version: "3.0"
description: "Spectral processing effects unit"

synthesis_engines:
  channel_engines:
    channel_0: "spectral"
    channel_1: "spectral"

  spectral_engine:
    enabled: true
    mode: "morph"

    fft_settings:
      fft_size: 2048
      hop_size: 512
      window_type: "hann"
      overlap_factor: 0.75

    # Spectral morphing between two sources
    morphing:
      enabled: true
      source_a: "voice_female.wav"
      source_b: "voice_male.wav"
      morph_position: 0.0  # Start with female voice
      morph_mode: "perceptual"
      frequency_bands: 24

    # Real-time spectral filtering
    filtering:
      filter_type: "parametric"
      cutoff_frequency: 1000.0
      bandwidth: 1.0
      gain: 0.0

    # Phase vocoder for pitch/time manipulation
    phase_vocoder:
      enabled: true
      pitch_scale: 1.0
      time_scale: 1.0
      preserve_transients: true

    # Transient processing
    transient_processing:
      enabled: true
      attack_gain: 1.2
      sustain_gain: 0.9
      onset_threshold: 0.15

performance_controls:
  assignable_knobs:
    knob_1:
      name: "Morph Position"
      parameter: "synthesis_engines.spectral_engine.morphing.morph_position"
      range: [0.0, 1.0]
      curve: "linear"
      default: 0.5
    knob_2:
      name: "Pitch Shift"
      parameter: "synthesis_engines.spectral_engine.phase_vocoder.pitch_scale"
      range: [0.5, 2.0]
      curve: "exponential"
      default: 1.0
    knob_3:
      name: "Filter Frequency"
      parameter: "synthesis_engines.spectral_engine.filtering.cutoff_frequency"
      range: [100.0, 8000.0]
      curve: "exponential"
      default: 1000.0
    knob_4:
      name: "Time Stretch"
      parameter: "synthesis_engines.spectral_engine.phase_vocoder.time_scale"
      range: [0.5, 2.0]
      curve: "exponential"
      default: 1.0

  snapshots:
    - name: "Female Voice"
      parameters:
        synthesis_engines.spectral_engine.morphing.morph_position: 0.0
    - name: "Male Voice"
      parameters:
        synthesis_engines.spectral_engine.morphing.morph_position: 1.0
    - name: "Robotic"
      parameters:
        synthesis_engines.spectral_engine.phase_vocoder.pitch_scale: 1.5
        synthesis_engines.spectral_engine.filtering.gain: -6.0
```

---

## 🎼 **Workstation Examples (Complete Systems)**

### **Example 4.1: Motif-Style Workstation**
```yaml
# Complete Motif-style workstation
xg_dsl_version: "3.0"
description: "Motif XS-style workstation setup"

workstation_features:
  motif_integration:
    enabled: true
    arpeggiator_system:
      global_settings:
        tempo: 128
        swing: 0.1
        gate_time: 0.9
        velocity_rate: 100
      arpeggiators:
        - id: 0
          pattern: "up_down_oct"
          octave_range: 2
          assigned_channels: [0, 1, 2, 3]
          hold_enabled: true
        - id: 1
          pattern: "chord_major"
          assigned_channels: [4, 5]
        - id: 2
          pattern: "bass_line"
          assigned_channels: [6]

  multi_timbral:
    channels: 16
    voice_reserve:
      channel_0: 32  # Piano
      channel_1: 24  # Strings
      channel_2: 16  # Brass
      channel_3: 16  # Woodwinds
      channel_4: 12  # Guitar
      channel_5: 12  # Bass
      channel_6: 8   # Arp bass
      channel_7: 8   # Pad
      channel_8: 8   # FX 1
      channel_9: 24  # Drums
      channel_10: 8  # Percussion
      channel_11: 8  # SFX
      channel_12: 8  # Voice
      channel_13: 8  # Synth lead
      channel_14: 8  # Synth pad
      channel_15: 8  # FX 2

  xg_effects:
    system_effects:
      reverb:
        type: 4
        time: 2.5
        level: 0.8
        hf_damping: 0.3
      chorus:
        type: 1
        rate: 0.5
        depth: 0.6
        feedback: 0.3

synthesis_engines:
  channel_engines:
    channel_0: "sf2"      # Piano
    channel_1: "physical" # Strings
    channel_2: "fm"       # Brass
    channel_3: "fm"       # Woodwinds
    channel_4: "sf2"      # Guitar
    channel_5: "sf2"      # Bass
    channel_6: "fm"       # Arp bass
    channel_7: "spectral" # Pad
    channel_8: "spectral" # FX 1
    channel_9: "sfz"      # Drums

modulation_system:
  matrix:
    sources:
      lfo1: {waveform: "sine", frequency: 0.5, depth: 1.0}
      envelope1: {attack: 0.01, decay: 0.3, sustain: 0.7, release: 0.5}
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 0.1
        bipolar: true
      - source: "envelope1"
        destination: "filter_cutoff"
        amount: 800.0

performance_controls:
  assignable_knobs:
    knob_1: {name: "Reverb Time", parameter: "workstation_features.xg_effects.system_effects.reverb.time", range: [0.1, 10.0], curve: "exponential"}
    knob_2: {name: "Chorus Depth", parameter: "workstation_features.xg_effects.system_effects.chorus.depth", range: [0.0, 1.0], curve: "linear"}
    knob_3: {name: "Arp Tempo", parameter: "workstation_features.motif_integration.arpeggiator_system.global_settings.tempo", range: [60.0, 200.0], curve: "linear"}
    knob_4: {name: "Filter Cutoff", parameter: "global_filter_cutoff", range: [20.0, 8000.0], curve: "exponential"}

  snapshots:
    - name: "Piano Solo"
      parameters: {channel_0_volume: 100, channel_1_volume: 0, channel_9_volume: 20}
    - name: "Full Band"
      parameters: {channel_0_volume: 90, channel_1_volume: 80, channel_9_volume: 100}
    - name: "Strings Only"
      parameters: {channel_0_volume: 0, channel_1_volume: 100, channel_9_volume: 0}
```

### **Example 4.2: S90/S70 Professional Setup**
```yaml
# S90/S70 professional keyboard setup
xg_dsl_version: "3.0"
description: "S90/S70 professional keyboard workstation"

workstation_features:
  s90_awm_stereo:
    enabled: true
    global_mixing:
      stereo_width: 1.3
      compression_ratio: 1.5
      limiter_threshold: -0.2
    velocity_layers:
      preset_0_0:  # Piano
        - min_velocity: 0, max_velocity: 43, sample: "pp_soft.wav", volume: -6.0
        - min_velocity: 44, max_velocity: 87, sample: "mf_medium.wav", volume: 0.0
        - min_velocity: 88, max_velocity: 127, sample: "ff_hard.wav", volume: 4.0
      preset_0_40: # Strings
        - min_velocity: 0, max_velocity: 63, sample: "sustain_soft.wav"
        - min_velocity: 64, max_velocity: 127, sample: "sustain_loud.wav"
    stereo_pairs:
      piano_samples:
        left: "piano_L.wav"
        right: "piano_R.wav"
        width: 1.4
      string_samples:
        left: "strings_L.wav"
        right: "strings_R.wav"
        width: 1.2

  multi_timbral:
    channels: 16
    voice_reserve:
      channel_0: 64   # Main sound (high priority)
      channel_1: 32   # Layer sound
      channel_2: 24   # Split sound
      channel_3: 16   # Arpeggiator destination

  xg_effects:
    system_effects:
      reverb: {type: 5, time: 2.2, level: 0.7, hf_damping: 0.2}
      chorus: {type: 2, rate: 0.4, depth: 0.5, feedback: 0.2}
    variation_effects:
      - slot: 0, type: 12, parameters: {rate: 0.3, depth: 0.6}  # Chorus
      - slot: 1, type: 48, parameters: {drive: 0.2, tone: 0.8}  # Overdrive

synthesis_engines:
  channel_engines:
    channel_0: "sf2"     # Main AWM stereo sound
    channel_1: "sf2"     # Layer (dual sound mode)
    channel_2: "physical" # Split (left hand)
    channel_3: "fm"      # Arpeggiator destination

  sf2_engine:
    soundfont_path: "s90_samples.sf2"
    awm_stereo:
      enabled: true
      stereo_width: 1.5

effects_processing:
  system_effects:
    reverb: {algorithm: "stage", time: 2.0, level: 0.6}
  master_processing:
    equalizer:
      bands:
        - {frequency: 100, gain: 2.0, type: "low_shelf"}
        - {frequency: 5000, gain: -1.0, type: "high_shelf"}
    stereo_enhancer: {width: 1.1}
    limiter: {threshold: -0.1, ratio: 6.0}

performance_controls:
  assignable_knobs:
    knob_1: {name: "Reverb Time", parameter: "effects_processing.system_effects.reverb.parameters.time", range: [0.5, 8.0]}
    knob_2: {name: "Chorus Send", parameter: "effects_processing.system_effects.chorus.parameters.mix", range: [0.0, 1.0]}
    knob_3: {name: "Stereo Width", parameter: "workstation_features.s90_awm_stereo.global_mixing.stereo_width", range: [0.5, 2.0]}
    knob_4: {name: "Layer Balance", parameter: "channel_1_volume", range: [0, 127]}

  snapshots:
    - name: "Clean Piano"
      parameters: {workstation_features.s90_awm_stereo.global_mixing.compression_ratio: 1.0}
    - name: "Compressed Piano"
      parameters: {workstation_features.s90_awm_stereo.global_mixing.compression_ratio: 3.0}
    - name: "Wide Stereo"
      parameters: {workstation_features.s90_awm_stereo.global_mixing.stereo_width: 1.8}
```

---

## 🎵 **Modulation & Control Examples**

### **Example 5.1: Advanced Modulation Matrix**
```yaml
# Complex modulation routing
xg_dsl_version: "3.0"
description: "Advanced modulation example"

modulation_system:
  matrix:
    sources:
      lfo1: {waveform: "sine", frequency: 0.1, depth: 1.0, bipolar: true}
      lfo2: {waveform: "triangle", frequency: 0.25, depth: 1.0}
      lfo3: {waveform: "random", frequency: 2.0, depth: 1.0}
      envelope1: {attack: 0.001, decay: 0.1, sustain: 0.8, release: 0.2}
      envelope2: {attack: 0.05, decay: 0.5, sustain: 0.3, release: 1.0}
      velocity: {curve: "exponential", bipolar: false}
      aftertouch: {curve: "linear", bipolar: false}
      timbre: {cc: 74, curve: "linear", bipolar: true}
      slide: {cc: 65, curve: "switch", bipolar: false}

    destinations:
      pitch: {range: [-24, 24], bipolar: true}
      volume: {range: [-60, 0], bipolar: false}
      pan: {range: [-100, 100], bipolar: true}
      filter_cutoff: {range: [-12000, 12000], bipolar: true}
      filter_resonance: {range: [0, 40], bipolar: false}
      reverb_send: {range: [0, 127], bipolar: false}
      chorus_send: {range: [0, 127], bipolar: false}
      delay_send: {range: [0, 127], bipolar: false}
      distortion_drive: {range: [0, 1], bipolar: false}
      phaser_rate: {range: [0.1, 10], bipolar: false}

    routes:
      # Vibrato
      - id: "vibrato"
        source: "lfo1"
        destination: "pitch"
        amount: 0.05
        bipolar: true
        smoothing: 0.01

      # Filter sweep envelope
      - id: "filter_sweep"
        source: "envelope1"
        destination: "filter_cutoff"
        amount: 2400.0
        curve: "exponential"

      # Tremolo
      - id: "tremolo"
        source: "lfo2"
        destination: "volume"
        amount: -0.3
        bipolar: true

      # Auto-pan
      - id: "auto_pan"
        source: "lfo3"
        destination: "pan"
        amount: 0.8
        bipolar: true

      # Velocity-controlled filter
      - id: "velocity_filter"
        source: "velocity"
        destination: "filter_cutoff"
        amount: 1200.0
        curve: "exponential"

      # Aftertouch-controlled reverb
      - id: "aftertouch_reverb"
        source: "aftertouch"
        destination: "reverb_send"
        amount: 64.0

      # MPE timbre to filter resonance
      - id: "mpe_timbre_filter"
        source: "timbre"
        destination: "filter_resonance"
        amount: 20.0
        bipolar: true

  # Modulation presets
  presets:
    - name: "Classic Vibrato"
      routes:
        - {source: "lfo1", destination: "pitch", amount: 0.03, bipolar: true}
    - name: "Slow Filter Sweep"
      routes:
        - {source: "envelope2", destination: "filter_cutoff", amount: 1200.0}
    - name: "Heavy Tremolo"
      routes:
        - {source: "lfo2", destination: "volume", amount: -0.6, bipolar: true}
```

### **Example 5.2: Real-Time Performance Controls**
```yaml
# Complete performance control setup
xg_dsl_version: "3.0"
description: "Live performance workstation"

performance_controls:
  assignable_knobs:
    knob_1:
      name: "Master Volume"
      parameter: "synthesizer_core.master_volume"
      range: [-60.0, 12.0]
      curve: "linear"
      default: 0.0
      midi_cc: 7
      smoothing: 0.05

    knob_2:
      name: "Reverb Mix"
      parameter: "effects_processing.system_effects.reverb.parameters.level"
      range: [0.0, 1.0]
      curve: "linear"
      default: 0.3
      midi_cc: 91
      smoothing: 0.02

    knob_3:
      name: "Filter Cutoff"
      parameter: "global_filter_cutoff"
      range: [20.0, 8000.0]
      curve: "exponential"
      default: 1000.0
      midi_cc: 74
      smoothing: 0.01

    knob_4:
      name: "LFO Speed"
      parameter: "modulation_system.matrix.sources.lfo1.frequency"
      range: [0.01, 10.0]
      curve: "exponential"
      default: 1.0
      midi_cc: 76
      smoothing: 0.1

  assignable_sliders:
    slider_1:
      name: "Expression"
      parameter: "global_expression"
      range: [0, 127]
      curve: "linear"
      default: 100
      midi_cc: 11
      smoothing: 0.02

    slider_2:
      name: "Variation Send"
      parameter: "effects_processing.variation_effects[0].parameters.mix"
      range: [0.0, 1.0]
      curve: "linear"
      default: 0.5
      midi_cc: 93
      smoothing: 0.03

  snapshots:
    - name: "Clean Sound"
      description: "Clean, dry sound with no effects"
      parameters:
        effects_processing.system_effects.reverb.parameters.level: 0.0
        effects_processing.system_effects.chorus.parameters.mix: 0.0
        effects_processing.variation_effects[0].parameters.mix: 0.0
        modulation_system.matrix.routes[0].enabled: false

    - name: "Hall Sound"
      description: "Concert hall with reverb and chorus"
      parameters:
        effects_processing.system_effects.reverb.parameters.algorithm: "hall_2"
        effects_processing.system_effects.reverb.parameters.time: 3.0
        effects_processing.system_effects.reverb.parameters.level: 0.7
        effects_processing.system_effects.chorus.parameters.mix: 0.4

    - name: "Effect Heavy"
      description: "Heavy effects with modulation"
      parameters:
        effects_processing.system_effects.reverb.parameters.level: 0.8
        effects_processing.system_effects.chorus.parameters.depth: 0.8
        effects_processing.variation_effects[0].parameters.drive: 0.6
        modulation_system.matrix.routes[0].enabled: true
        modulation_system.matrix.routes[0].amount: 0.8

    - name: "Intimate"
      description: "Close-miked, dry sound"
      parameters:
        effects_processing.system_effects.reverb.parameters.level: 0.1
        effects_processing.master_processing.equalizer.bands[0].gain: 3.0
        effects_processing.master_processing.equalizer.bands[2].gain: 2.0

  automation:
    enabled: true
    midi_cc_learning: true
    parameter_feedback: true
    snapshot_transition_time: 0.5
    snapshot_interpolation: "exponential"
```

---

## 🎼 **Sequencing Examples**

### **Example 6.1: Pattern-Based Sequencing**
```yaml
# Advanced pattern-based sequencing
xg_dsl_version: "3.0"
description: "Pattern-based drum sequencing"

sequencing:
  sequencer_core:
    enabled: true
    resolution: 960
    tempo: 128
    time_signature: "4/4"
    swing: 0.1

  patterns:
    - name: "four_on_floor"
      type: "drum"
      steps: 16
      notes:
        36: [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]  # Kick
        38: [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]  # Snare
        42: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]  # Hi-hat
        46: [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]  # Open hat

    - name: "syncopated_beat"
      type: "drum"
      steps: 16
      notes:
        36: [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]
        38: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0]
        42: [0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1]

    - name: "arpeggio_pattern"
      type: "arpeggiator"
      notes: [60, 64, 67, 72, 76, 79, 84]  # C major arpeggio
      duration: 0.25
      velocity: [100, 90, 95, 85, 90, 80, 85]
      humanize: 0.05

  real_time_control:
    pattern_chain: ["four_on_floor", "syncopated_beat", "four_on_floor", "arpeggio_pattern"]
    transition_smoothing: 0.2
    pattern_sync: "bar"
    tempo_following: true

  workstation_sync:
    motif_arpeggiator: true
    external_clock: true
    midi_clock_out: true

  advanced:
    probability: true
    groove_quantization: true
    microtiming: true
```

---

## 📋 **Configuration Templates**

### **Built-in Templates**

#### **Children's Piano**
```yaml
template: "childrens_piano"
# Automatically configures:
# - Simple piano sound
# - Conservative polyphony (8 voices)
# - Basic reverb
# - Easy controls
```

#### **Professional Orchestra**
```yaml
template: "professional_orchestra"
# Automatically configures:
# - 16-channel multi-timbral setup
# - Physical modeling strings
# - SF2 brass and woodwinds
# - Concert hall reverb
# - Proper voice allocation
```

#### **Electronic Workstation**
```yaml
template: "electronic_workstation"
# Automatically configures:
# - FM synthesis engines
# - Spectral processing
# - Workstation effects
# - Performance controls
# - Arpeggiator patterns
```

### **Custom Template Creation**
```yaml
# Save current configuration as template
template_definition:
  name: "my_custom_template"
  description: "My custom sound setup"
  category: "hybrid"
  extends: "basic_rock_band"  # Optional base template

  # Template-specific overrides
  synthesizer_core:
    performance:
      max_polyphony: 256

  effects_processing:
    system_effects:
      reverb:
        algorithm: "plate"
        time: 2.0
```

---

## 🔧 **Validation Examples**

### **Configuration Validation**
```bash
# Validate XGML v3.0 configuration
xgml_validate config.xgml --schema v3.0

# Check for common issues
xgml_validate config.xgml --check-best-practices

# Auto-fix common problems
xgml_validate config.xgml --fix
```

### **Performance Analysis**
```bash
# Analyze configuration performance
xgml_analyze config.xgml --performance

# Check memory usage
xgml_analyze config.xgml --memory

# Validate real-time capability
xgml_analyze config.xgml --realtime
```

---

## 🎯 **Best Practices Examples**

### **Progressive Enhancement Pattern**
```yaml
# Start simple, add complexity gradually
xg_dsl_version: "3.0"

# Level 1: Basic sound
basic_messages:
  channels:
    channel_1: {program_change: "acoustic_grand_piano"}

# Level 2: Add effects (when needed)
effects_processing:
  system_effects:
    reverb: {algorithm: "hall_1", level: 0.3}

# Level 3: Add modulation (for expression)
modulation_system:
  matrix:
    routes:
      - source: "velocity"
        destination: "volume"
        amount: 0.7

# Level 4: Full workstation (for professionals)
workstation_features:
  multi_timbral: {channels: 16}
synthesis_engines:
  channel_engines: {channel_0: "sf2"}
```

### **Modular Configuration Pattern**
```yaml
# Break complex configurations into logical modules
xg_dsl_version: "3.0"

# Sound design module
synthesis_engines: {...}
basic_messages: {...}

# Spatial processing module
effects_processing:
  system_effects: {...}
  master_processing: {...}

# Control module
modulation_system: {...}
performance_controls: {...}

# Sequencing module
sequencing: {...}
workstation_features: {...}
```

---

**🎼 This comprehensive XGML v3.0 examples library demonstrates the full power of the modern synthesizer configuration language, from simple children's piano to advanced workstation orchestras, while maintaining the simplicity that makes XGML accessible to users of all skill levels.**
