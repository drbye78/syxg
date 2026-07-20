# Jazz Combo XG DSL Example

```yaml
xg_dsl_version: "1.0"
description: "Complete jazz combo arrangement with full XG parameter control"
timestamp: "2025-12-14T10:45:28Z"

# Basic MIDI Messages
basic_messages:
  channels:
    channel_1:  # Piano
      program_change: "acoustic_grand_piano"
      bank_select:
        msb: 0
        lsb: 0
      control_changes:
        volume: 100
        pan: "center"
        expression: 127
        modulation: 50
        sustain: false
    
    channel_2:  # Saxophone
      program_change: "tenor_sax"
      bank_select:
        msb: 64
        lsb: 0
      control_changes:
        volume: 95
        pan: "left_20"
        expression: 120
        modulation: 75
        sustain: false
    
    channel_3:  # Bass
      program_change: "electric_bass_finger"
      bank_select:
        msb: 0
        lsb: 0
      control_changes:
        volume: 110
        pan: "center"
        expression: 127
        modulation: 30
        sustain: false
    
    channel_9:  # Drums
      program_change: "standard_drum_kit"
      bank_select:
        msb: 126
        lsb: 0
      control_changes:
        volume: 105
        pan: "center"
        expression: 127

# RPN Parameters
rpn_parameters:
  global:
    pitch_bend_range: 2
    fine_tuning: 0
    coarse_tuning: 0
    modulation_depth: 100
  
  channel_1:
    pitch_bend_range: 7      # Extended range for piano expression
  
  channel_2:
    pitch_bend_range: 5      # Sax expression range
    fine_tuning: -3          # Slight detune for character

# Channel Parameters (MSB 3-31)
channel_parameters:
  channel_1:  # Piano
    # Basic Channel Parameters (MSB 3)
    volume:
      coarse: 100
      fine: 64
    pan:
      coarse: "center"
      fine: 64
    expression:
      coarse: 127
      fine: 64
    
    # Pitch & Tuning (MSB 4)
    pitch:
      coarse: 64
      fine: 64
      bend_range: 7
      portamento:
        enabled: false
        time: 0
        mode: "fingered"
    
    # Filter Parameters (MSB 5-6)
    filter:
      cutoff: 80             # Bright piano
      resonance: 60
      type: "lowpass"
      envelope:
        attack: 64
        decay: 64
        sustain: 64
        release: 64
    
    # Amplifier Envelope (MSB 7-8)
    amplifier:
      envelope:
        attack: 90           # Fast piano attack
        decay: 40            # Quick decay
        sustain: 70          # Good sustain
        release: 60          # Natural release
      velocity_sensitivity: 80  # High velocity sensitivity
      key_scaling: 50        # Moderate key scaling
    
    # LFO Parameters (MSB 9-10)
    lfo:
      lfo1:
        waveform: "sine"
        speed: 20            # Slow vibrato
        delay: 0
        fade_time: 0
        pitch_depth: 10      # Subtle vibrato
        filter_depth: 0
        amp_depth: 0
      lfo2:
        waveform: "triangle"
        speed: 40
        delay: 10
        fade_time: 5
        pitch_depth: 5
        filter_depth: 15
        amp_depth: 0
    
    # Effects Send (MSB 11-12)
    effects_sends:
      reverb: 50             # Moderate reverb
      chorus: 20             # Subtle chorus
      variation: 0
      dry_level: 127
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    # Controller Assignments (MSB 15-16)
    controller_assignments:
      mod_wheel: "pitch_modulation"
      foot_controller: "filter_modulation"
      aftertouch: "amp_modulation"
      breath_controller: "pitch_modulation"
      general_buttons:
        gp1: "filter_type"
        gp2: "effect_bypass"
        gp3: "modulation_source"
        gp4: "performance_preset"

  channel_2:  # Saxophone
    volume:
      coarse: 95
      fine: 64
    pan:
      coarse: "left_20"
      fine: 64
    expression:
      coarse: 120
      fine: 64
    
    pitch:
      coarse: 64
      fine: 61              # -3 cents
      bend_range: 5
      portamento:
        enabled: false
        time: 0
        mode: "fingered"
    
    filter:
      cutoff: 85             # Brighter for sax
      resonance: 45
      type: "lowpass"
      envelope:
        attack: 70
        decay: 50
        sustain: 75
        release: 80
    
    amplifier:
      envelope:
        attack: 70           # Reed attack
        decay: 50
        sustain: 85          # Long sustain
        release: 70
      velocity_sensitivity: 70
      key_scaling: 60
    
    lfo:
      lfo1:
        waveform: "sine"
        speed: 45            # Moderate vibrato
        delay: 0
        fade_time: 0
        pitch_depth: 30      # Expressive vibrato
        filter_depth: 10
        amp_depth: 5
      lfo2:
        waveform: "triangle"
        speed: 60
        delay: 5
        fade_time: 10
        pitch_depth: 15
        filter_depth: 25
        amp_depth: 10
    
    effects_sends:
      reverb: 65             # More reverb for sax
      chorus: 35             # Chorus for warmth
      variation: 15          # Subtle variation
      dry_level: 100
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    controller_assignments:
      mod_wheel: "pitch_modulation"
      foot_controller: "filter_modulation"
      aftertouch: "filter_modulation"  # Aftertouch affects filter
      breath_controller: "amp_modulation"  # Breath controls dynamics

  channel_3:  # Bass
    volume:
      coarse: 110            # Higher bass volume
      fine: 64
    pan:
      coarse: "center"
      fine: 64
    expression:
      coarse: 127
      fine: 64
    
    pitch:
      coarse: 64
      fine: 64
      bend_range: 12         # Extended bass range
      portamento:
        enabled: false
        time: 0
        mode: "fingered"
    
    filter:
      cutoff: 50             # Darker bass
      resonance: 90          # High resonance for attack
      type: "lowpass"
      envelope:
        attack: 80
        decay: 60
        sustain: 60
        release: 70
    
    amplifier:
      envelope:
        attack: 75           # Quick bass attack
        decay: 55
        sustain: 65
        release: 65
      velocity_sensitivity: 60
      key_scaling: 70        # Strong key scaling
    
    lfo:
      lfo1:
        waveform: "sine"
        speed: 30            # Slow bass vibrato
        delay: 0
        fade_time: 0
        pitch_depth: 15      # Subtle bass vibrato
        filter_depth: 5
        amp_depth: 0
      lfo2:
        waveform: "sawtooth"
        speed: 25
        delay: 0
        fade_time: 0
        pitch_depth: 5
        filter_depth: 20     # Filter modulation for bass
        amp_depth: 0
    
    effects_sends:
      reverb: 20             # Minimal reverb for bass
      chorus: 10             # Subtle chorus
      variation: 40          # More variation for bass effects
      dry_level: 120
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    controller_assignments:
      mod_wheel: "pitch_modulation"
      foot_controller: "amp_modulation"  # Foot controls dynamics
      aftertouch: "filter_modulation"
      breath_controller: "pitch_modulation"
      general_buttons:
        gp1: "filter_type"
        gp2: "effect_bypass"
        gp3: "portamento"
        gp4: "performance_preset"

# Drum Parameters (MSB 40-41)
drum_parameters:
  drum_channel: 9
  pattern_configurations:
    jazz_drums:
      # Kick (MIDI note 36)
      36:  # Kick
        level: 90
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 64
        filter_cutoff: 50    # Darker kick
        filter_resonance: 60
        attack_time: 90      # Fast attack
        decay_time: 30       # Quick decay
        reverb_send: 25
        chorus_send: 0
      
      # Snare (MIDI note 38)
      38:  # Snare
        level: 100
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 67        # +3 cents for definition
        filter_cutoff: 75    # Bright snare
        filter_resonance: 80 # High resonance
        attack_time: 85      # Fast attack
        decay_time: 45       # Medium decay
        reverb_send: 35
        chorus_send: 15      # Snare chorus
      
      # Hi-hat closed (MIDI note 42)
      42:  # Hi-hat closed
        level: 80
        pan: "right_30"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 70        # Slightly sharp
        filter_cutoff: 96    # Very bright
        filter_resonance: 85 # High resonance
        attack_time: 95      # Instant attack
        decay_time: 20       # Quick decay
        reverb_send: 10
        chorus_send: 5
      
      # Hi-hat open (MIDI note 46)
      46:  # Hi-hat open
        level: 85
        pan: "right_30"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 68
        filter_cutoff: 94
        filter_resonance: 80
        attack_time: 90
        decay_time: 60       # Longer decay for open hat
        reverb_send: 15
        chorus_send: 8
      
      # Ride cymbal (MIDI note 51)
      51:  # Ride
        level: 75
        pan: "right_40"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 65
        filter_cutoff: 85
        filter_resonance: 70
        attack_time: 75
        decay_time: 80       # Long decay for ride
        reverb_send: 45
        chorus_send: 20
      
      # Crash cymbal (MIDI note 49)
      49:  # Crash
        level: 80
        pan: "left_40"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 63
        filter_cutoff: 88
        filter_resonance: 75
        attack_time: 80
        decay_time: 70       # Medium decay
        reverb_send: 50
        chorus_send: 25
      
      # Piano key (MIDI note 60 - C4 for comping)
      60:  # Piano key
        level: 60
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 64
        filter_cutoff: 70
        filter_resonance: 50
        attack_time: 70
        decay_time: 50
        reverb_send: 20
        chorus_send: 10

# System Exclusive Messages
system_exclusive:
  manufacturer: "yamaha"
  model: "xg"
  device_id: 0
  commands:
    - command: "parameter_change"
      address: 0x100010
      values:
        reverb_type: "room_2"
        chorus_type: "chorus_2"
        master_volume: 127
        reverb_time: 1.2
        chorus_depth: 0.5

# Modulation Routing
modulation_routing:
  channel_1:  # Piano modulation
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 10          # Subtle piano vibrato
        polarity: "positive"
      - source: "velocity"
        destination: "amplitude"
        amount: 0.8
        velocity_sensitivity: 0.6
      - source: "mod_wheel"
        destination: "lfo1_depth"
        amount: 1.0
        polarity: "positive"
      - source: "aftertouch"
        destination: "filter_cutoff"
        amount: 0.4
        polarity: "positive"
      - source: "brightness"
        destination: "filter_cutoff"
        amount: 0.7
        polarity: "positive"
  
  channel_2:  # Sax modulation
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 30          # Expressive sax vibrato
        polarity: "positive"
      - source: "breath_controller"
        destination: "amp"
        amount: 0.9
        polarity: "positive"
      - source: "aftertouch"
        destination: "filter_cutoff"
        amount: 0.6
        polarity: "positive"
      - source: "mod_wheel"
        destination: "lfo1_depth"
        amount: 0.8
        polarity: "positive"
      - source: "velocity"
        destination: "amplitude"
        amount: 0.7
        velocity_sensitivity: 0.5
  
  channel_3:  # Bass modulation
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 15          # Subtle bass vibrato
        polarity: "positive"
      - source: "foot_controller"
        destination: "amp"
        amount: 0.8
        polarity: "positive"
      - source: "aftertouch"
        destination: "filter_cutoff"
        amount: 0.5
        polarity: "positive"
      - source: "mod_wheel"
        destination: "filter_cutoff"
        amount: 0.6
        polarity: "positive"
      - source: "velocity"
        destination: "amplitude"
        amount: 0.6
        velocity_sensitivity: 0.4

# Effect Parameters
effects:
  system_effects:
    reverb:
      type: "room_2"        # Small room for jazz
      time: 1.2             # Moderate reverb time
      hf_damp: 0.3          # Slight high frequency damping
      feedback: 0.4         # Moderate feedback
      level: 0.35           # Moderate reverb level
      pre_delay: 0.015      # Short pre-delay
      room_size: 0.6        # Medium room size
      diffusion: 0.7        # Good diffusion
    
    chorus:
      type: "chorus_2"      # Chorus type 2
      lfo_rate: 0.8         # Moderate LFO rate
      lfo_depth: 0.5        # Moderate depth
      feedback: 0.2         # Low feedback
      send_level: 0.3       # Moderate send level
      delay_time: 0.030     # 30ms delay
      phase_difference: 90  # Standard phase difference
  
  variation_effects:
    channel_1:  # Piano variation
      type: "delay_lcr"
      parameters:
        left_delay: 0.250    # 250ms left delay
        center_delay: 0.125  # 125ms center delay
        right_delay: 0.375   # 375ms right delay
        feedback: 0.3        # 30% feedback
        send_level: 0.2      # 20% send level
    
    channel_2:  # Sax variation
      type: "phaser_1"
      parameters:
        rate: 0.6            # Slow phaser rate
        depth: 0.4           # Moderate depth
        feedback: 0.5        # 50% feedback
        stages: 4            # 4 phaser stages
        send_level: 0.25     # 25% send level
    
    channel_3:  # Bass variation
      type: "auto_wah"
      parameters:
        cutoff_frequency: 800  # Hz
        resonance: 0.7         # High resonance
        modulation_rate: 2.0   # Moderate rate
        depth: 0.6             # Good depth
        send_level: 0.3        # 30% send level

# Preset Configurations
presets:
  instruments:
    jazz_piano:
      channel_1:
        program: "acoustic_grand_piano"
        filter:
          cutoff: 80
          resonance: 60
        amplifier:
          envelope:
            attack: 90
            decay: 40
            sustain: 70
            release: 60
        lfo:
          lfo1:
            speed: 20
            pitch_depth: 10
        effects_sends:
          reverb: 50
          chorus: 20
    
    expressive_sax:
      channel_2:
        program: "tenor_sax"
        bank_select:
          msb: 64
          lsb: 0
        filter:
          cutoff: 85
          resonance: 45
        amplifier:
          envelope:
            attack: 70
            decay: 50
            sustain: 85
            release: 70
        lfo:
          lfo1:
            speed: 45
            pitch_depth: 30
        effects_sends:
          reverb: 65
          chorus: 35
    
    punchy_bass:
      channel_3:
        program: "electric_bass_finger"
        filter:
          cutoff: 50
          resonance: 90
        amplifier:
          envelope:
            attack: 75
            decay: 55
            sustain: 65
            release: 65
        pitch:
          bend_range: 12
        effects_sends:
          reverb: 20
          chorus: 10

# Advanced Configuration Features
advanced_features:
  macros:
    create_jazz_piano_vibrato:
      - type: "set_modulation"
        source: "lfo1"
        destination: "pitch"
        amount: 25
      - type: "set_controller_assignment"
        controller: "mod_wheel"
        assignment: "lfo_depth"
      - type: "set_effects_sends"
        reverb: 60
        chorus: 25
  
  sequences:
    jazz_comping:
      - type: "note_sequence"
        channel: 1
        notes: ["C4", "E4", "G4", "B4", "C5", "G4", "E4", "C4"]
        velocity: 80
        duration: 0.5
        timing: 0.0
      - type: "control_change_sequence"
        channel: 1
        controller: "modulation"
        values: [0, 25, 50, 75, 100, 75, 50, 25, 0]
        timing: 0.0
        duration: 4.0
  
  conditional_logic:
    saxophone_breath_control:
      - condition: "breath_controller > 80"
        action: "set_filter_cutoff"
        value: 95
      - condition: "breath_controller < 30"
        action: "set_filter_cutoff"
        value: 70
      - condition: "breath_controller >= 30 and breath_controller <= 80"
        action: "set_filter_cutoff"
        value: 85
  
  automation:
    piano_filter_sweep:
      - parameter: "filter_cutoff"
        curve: "sine"
        start_value: 60
        end_value: 90
        duration: 8.0
        loop: true
    
    bass_punch_emphasis:
      - parameter: "filter_resonance"
        curve: "exponential"
        start_value: 60
        end_value: 95
        duration: 0.1
        delay: 0.0
        trigger: "note_on"