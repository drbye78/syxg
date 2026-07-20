# Electronic Music XG DSL Example

```yaml
xg_dsl_version: "1.0"
description: "Electronic music production with advanced XG modulation and effects"
timestamp: "2025-12-14T10:45:28Z"

# Basic MIDI Messages
basic_messages:
  channels:
    channel_1:  # Lead Synth
      program_change: "synth_lead_1"
      bank_select:
        msb: 64
        lsb: 0
      control_changes:
        volume: 110
        pan: "center"
        expression: 127
        modulation: 100
        sustain: false
    
    channel_2:  # Pad Synth
      program_change: "synth_pad_1"
      bank_select:
        msb: 64
        lsb: 0
      control_changes:
        volume: 90
        pan: "left_30"
        expression: 127
        modulation: 80
        sustain: false
    
    channel_3:  # Bass Synth
      program_change: "synth_bass_1"
      bank_select:
        msb: 64
        lsb: 0
      control_changes:
        volume: 120
        pan: "center"
        expression: 127
        modulation: 60
        sustain: false
    
    channel_4:  # Arpeggiated Synth
      program_change: "synth_calliope"
      bank_select:
        msb: 64
        lsb: 0
      control_changes:
        volume: 85
        pan: "right_30"
        expression: 127
        modulation: 90
        sustain: false
    
    channel_9:  # Electronic Drums
      program_change: "electronic_drum_kit"
      bank_select:
        msb: 127
        lsb: 0
      control_changes:
        volume: 115
        pan: "center"
        expression: 127

# RPN Parameters
rpn_parameters:
  global:
    pitch_bend_range: 12    # Wide range for electronic music
    fine_tuning: 0
    coarse_tuning: 0
    modulation_depth: 127   # Maximum modulation depth
  
  channel_1:
    pitch_bend_range: 24    # Maximum lead synth expression
  
  channel_2:
    pitch_bend_range: 7     # Moderate pad range
  
  channel_3:
    pitch_bend_range: 12    # Wide bass range

# Channel Parameters (MSB 3-31)
channel_parameters:
  channel_1:  # Lead Synth
    # Basic Channel Parameters (MSB 3)
    volume:
      coarse: 110
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
      bend_range: 24        # Maximum expression range
      portamento:
        enabled: true       # Glide between notes
        time: 40            # Moderate glide time
        mode: "full"        # Full portamento
    
    # Filter Parameters (MSB 5-6)
    filter:
      cutoff: 95             # Very bright for leads
      resonance: 85          # High resonance for sweeps
      type: "lowpass"
      envelope:
        attack: 20           # Fast attack
        decay: 60            # Moderate decay
        sustain: 80          # High sustain
        release: 40          # Quick release
    
    # Amplifier Envelope (MSB 7-8)
    amplifier:
      envelope:
        attack: 10           # Very fast attack
        decay: 50            # Moderate decay
        sustain: 90          # High sustain
        release: 30          # Quick release
      velocity_sensitivity: 40  # Lower velocity sensitivity
      key_scaling: 30        # Minimal key scaling
    
    # LFO Parameters (MSB 9-10)
    lfo:
      lfo1:
        waveform: "sine"
        speed: 80            # Fast vibrato
        delay: 0
        fade_time: 0
        pitch_depth: 100     # Deep vibrato
        filter_depth: 50
        amp_depth: 20
      lfo2:
        waveform: "triangle"
        speed: 120           # Very fast modulation
        delay: 5
        fade_time: 10
        pitch_depth: 30
        filter_depth: 80     # Heavy filter modulation
        amp_depth: 40        # Tremolo effect
    
    # Effects Send (MSB 11-12)
    effects_sends:
      reverb: 30             # Minimal reverb for clarity
      chorus: 60             # Rich chorus for width
      variation: 80          # Heavy variation processing
      dry_level: 100
      insertion:
        part_l: 120
        part_r: 120
        connection: "system"
    
    # Controller Assignments (MSB 15-16)
    controller_assignments:
      mod_wheel: "filter_modulation"  # Mod wheel controls filter
      foot_controller: "pitch_modulation"
      aftertouch: "amp_modulation"    # Aftertouch controls dynamics
      breath_controller: "pitch_modulation"
      general_buttons:
        gp1: "filter_type"
        gp2: "distortion"
        gp3: "lfo_speed"
        gp4: "preset_load"

  channel_2:  # Pad Synth
    volume:
      coarse: 90
      fine: 64
    pan:
      coarse: "left_30"
      fine: 64
    expression:
      coarse: 127
      fine: 64
    
    pitch:
      coarse: 64
      fine: 64
      bend_range: 7
      portamento:
        enabled: false
        time: 0
        mode: "fingered"
    
    filter:
      cutoff: 60             # Warmer pad sound
      resonance: 40          # Moderate resonance
      type: "lowpass"
      envelope:
        attack: 80           # Slow attack for pads
        decay: 70
        sustain: 95          # Very high sustain
        release: 100         # Long release
    
    amplifier:
      envelope:
        attack: 80           # Slow attack
        decay: 70
        sustain: 95          # Maximum sustain
        release: 100         # Long release
      velocity_sensitivity: 20  # Low velocity sensitivity
      key_scaling: 10        # Minimal key scaling
    
    lfo:
      lfo1:
        waveform: "sine"
        speed: 30            # Slow pad vibrato
        delay: 2000          # 2 second delay
        fade_time: 4000      # 4 second fade
        pitch_depth: 15      # Subtle pad vibrato
        filter_depth: 10
        amp_depth: 0
      lfo2:
        waveform: "triangle"
        speed: 15            # Very slow modulation
        delay: 5000          # 5 second delay
        fade_time: 8000      # 8 second fade
        pitch_depth: 5
        filter_depth: 20     # Slow filter sweep
        amp_depth: 0
    
    effects_sends:
      reverb: 80             # Lots of reverb for pads
      chorus: 70             # Rich chorus
      variation: 40          # Moderate variation
      dry_level: 80
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    controller_assignments:
      mod_wheel: "pitch_modulation"
      foot_controller: "filter_modulation"
      aftertouch: "filter_modulation"
      breath_controller: "amp_modulation"

  channel_3:  # Bass Synth
    volume:
      coarse: 120            # High bass volume
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
      bend_range: 12         # Wide bass range
      portamento:
        enabled: true       # Bass glide
        time: 20            # Fast glide
        mode: "full"
    
    filter:
      cutoff: 40             # Dark bass
      resonance: 95          # Maximum resonance
      type: "lowpass"
      envelope:
        attack: 30           # Fast bass attack
        decay: 80            # Long decay
        sustain: 70          # Good sustain
        release: 60          # Moderate release
    
    amplifier:
      envelope:
        attack: 25           # Fast attack
        decay: 75
        sustain: 80          # High sustain
        release: 50          # Quick release
      velocity_sensitivity: 80  # High velocity sensitivity
      key_scaling: 85        # Strong key scaling
    
    lfo:
      lfo1:
        waveform: "sawtooth"
        speed: 60            # Fast bass vibrato
        delay: 0
        fade_time: 0
        pitch_depth: 40      # Deep bass vibrato
        filter_depth: 30
        amp_depth: 15
      lfo2:
        waveform: "square"
        speed: 40            # Square wave modulation
        delay: 0
        fade_time: 0
        pitch_depth: 20
        filter_depth: 60     # Heavy filter mod
        amp_depth: 25        # Bass tremolo
    
    effects_sends:
      reverb: 15             # Minimal reverb
      chorus: 30             # Subtle chorus
      variation: 90          # Heavy variation processing
      dry_level: 110
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    controller_assignments:
      mod_wheel: "filter_modulation"
      foot_controller: "amp_modulation"
      aftertouch: "pitch_modulation"
      breath_controller: "filter_modulation"

  channel_4:  # Arpeggiated Synth
    volume:
      coarse: 85
      fine: 64
    pan:
      coarse: "right_30"
      fine: 64
    expression:
      coarse: 127
      fine: 64
    
    pitch:
      coarse: 64
      fine: 64
      bend_range: 2          # Minimal range for arps
      portamento:
        enabled: false
        time: 0
        mode: "fingered"
    
    filter:
      cutoff: 100            # Very bright for arps
      resonance: 70          # Good resonance
      type: "bandpass"       # Bandpass for arps
      envelope:
        attack: 5            # Instant attack
        decay: 40            # Quick decay
        sustain: 60          # Moderate sustain
        release: 20          # Quick release
    
    amplifier:
      envelope:
        attack: 5            # Instant attack
        decay: 35            # Quick decay
        sustain: 50          # Moderate sustain
        release: 15          # Very quick release
      velocity_sensitivity: 70  # Good velocity sensitivity
      key_scaling: 50        # Moderate key scaling
    
    lfo:
      lfo1:
        waveform: "triangle"
        speed: 200           # Very fast for arps
        delay: 0
        fade_time: 0
        pitch_depth: 5       # Minimal pitch mod
        filter_depth: 90     # Heavy filter mod
        amp_depth: 30        # Fast tremolo
      lfo2:
        waveform: "sine"
        speed: 150           # Fast secondary LFO
        delay: 0
        fade_time: 0
        pitch_depth: 10
        filter_depth: 70
        amp_depth: 20
    
    effects_sends:
      reverb: 50             # Moderate reverb
      chorus: 80             # Rich chorus for arps
      variation: 60          # Good variation
      dry_level: 90
      insertion:
        part_l: 127
        part_r: 127
        connection: "system"
    
    controller_assignments:
      mod_wheel: "lfo_speed"
      foot_controller: "filter_cutoff"
      aftertouch: "amp_modulation"
      breath_controller: "lfo_depth"

# Drum Parameters (MSB 40-41)
drum_parameters:
  drum_channel: 9
  pattern_configurations:
    electronic_drums:
      # Kick (MIDI note 36)
      36:  # Electronic Kick
        level: 120           # Very loud kick
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 64
        filter_cutoff: 30    # Very dark kick
        filter_resonance: 95 # Maximum resonance
        attack_time: 100     # Instant attack
        decay_time: 20       # Very quick decay
        reverb_send: 5       # Minimal reverb
        chorus_send: 0
      
      # Snare (MIDI note 38)
      38:  # Electronic Snare
        level: 110
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 64
        filter_cutoff: 85    # Bright snare
        filter_resonance: 90 # High resonance
        attack_time: 95      # Fast attack
        decay_time: 25       # Quick decay
        reverb_send: 15
        chorus_send: 20      # Snare chorus
      
      # Hi-hat closed (MIDI note 42)
      42:  # Electronic Hi-hat
        level: 95
        pan: "right_40"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 70        # Sharp hi-hat
        filter_cutoff: 120   # Maximum brightness
        filter_resonance: 80 # High resonance
        attack_time: 100     # Instant attack
        decay_time: 10       # Very quick
        reverb_send: 5
        chorus_send: 10
      
      # Hi-hat open (MIDI note 46)
      46:  # Electronic Open Hat
        level: 90
        pan: "right_40"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 68
        filter_cutoff: 118
        filter_resonance: 75
        attack_time: 100
        decay_time: 40       # Medium decay for open
        reverb_send: 10
        chorus_send: 15
      
      # Crash (MIDI note 49)
      49:  # Electronic Crash
        level: 85
        pan: "left_40"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 62
        filter_cutoff: 95    # Bright crash
        filter_resonance: 85 # High resonance
        attack_time: 90      # Fast attack
        decay_time: 60       # Long decay
        reverb_send: 60      # Lots of reverb
        chorus_send: 30
      
      # Ride (MIDI note 51)
      51:  # Electronic Ride
        level: 80
        pan: "right_50"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 66
        filter_cutoff: 90
        filter_resonance: 75
        attack_time: 85
        decay_time: 90       # Long decay
        reverb_send: 50
        chorus_send: 25
      
      # Clap (MIDI note 40)
      40:  # Electronic Clap
        level: 100
        pan: "center"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 64
        filter_cutoff: 80
        filter_resonance: 85
        attack_time: 100
        decay_time: 35       # Clap-like decay
        reverb_send: 25
        chorus_send: 30
      
      # Tom (MIDI note 47)
      47:  # Electronic Tom
        level: 90
        pan: "left_20"
        assign: "poly"
        coarse_tune: 64
        fine_tune: 70        # Slightly sharp tom
        filter_cutoff: 70
        filter_resonance: 80
        attack_time: 90
        decay_time: 50       # Medium decay
        reverb_send: 20
        chorus_send: 15

# System Exclusive Messages
system_exclusive:
  manufacturer: "yamaha"
  model: "xg"
  device_id: 0
  commands:
    - command: "parameter_change"
      address: 0x100010
      values:
        reverb_type: "hall_3"
        chorus_type: "flanger_1"
        master_volume: 127
        reverb_time: 2.5
        chorus_depth: 0.8

# Modulation Routing with Advanced Patterns
modulation_routing:
  channel_1:  # Lead Synth Complex Modulation
    routes:
      # Basic routes
      - source: "lfo1"
        destination: "pitch"
        amount: 100         # Deep vibrato
        polarity: "positive"
      - source: "lfo2"
        destination: "filter_cutoff"
        amount: 80          # Heavy filter mod
        polarity: "positive"
      - source: "mod_wheel"
        destination: "lfo1_depth"
        amount: 1.0         # Full mod wheel control
        polarity: "positive"
      - source: "aftertouch"
        destination: "amp"
        amount: 0.7         # Aftertouch dynamics
        polarity: "positive"
      - source: "velocity"
        destination: "filter_resonance"
        amount: 0.6
        velocity_sensitivity: 0.5
    
    # Advanced modulation patterns
    modulation_patterns:
      filter_sweep:
        - source: "lfo2"
          destination: "filter_cutoff"
          amount: [0, 25, 50, 75, 100, 75, 50, 25, 0]  # Sweep pattern
          time_points: [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
          loop: true
      
      vibrato_enhancement:
        - source: "aftertouch"
          destination: "lfo1_depth"
          amount: [0, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0]
          time_points: [0, 1, 2, 3, 4, 5, 6, 7, 8]
          loop: true
  
  channel_2:  # Pad Synth Atmospheric Modulation
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 15          # Subtle pad vibrato
        polarity: "positive"
      - source: "lfo2"
        destination: "filter_cutoff"
        amount: 20          # Slow filter movement
        polarity: "positive"
      - source: "breath_controller"
        destination: "amp"
        amount: 0.8         # Breath dynamics
        polarity: "positive"
      - source: "mod_wheel"
        destination: "lfo1_speed"
        amount: 0.5         # Mod wheel controls speed
        polarity: "positive"
    
    modulation_patterns:
      pad_swell:
        - source: "expression"
          destination: "amp"
          amount: [0, 0.3, 0.6, 0.8, 1.0, 0.8, 0.6, 0.3, 0]
          time_points: [0, 2, 4, 6, 8, 10, 12, 14, 16]
          loop: true
  
  channel_3:  # Bass Synth Aggressive Modulation
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 40          # Deep bass vibrato
        polarity: "positive"
      - source: "lfo2"
        destination: "filter_cutoff"
        amount: 60          # Heavy filter mod
        polarity: "positive"
      - source: "foot_controller"
        destination: "amp"
        amount: 0.9         # Foot controls dynamics
        polarity: "positive"
      - source: "mod_wheel"
        destination: "filter_resonance"
        amount: 0.8         # Mod wheel controls resonance
        polarity: "positive"
      - source: "velocity"
        destination: "pitch"
        amount: 0.3         # Velocity affects pitch
        velocity_sensitivity: 0.7
  
  channel_4:  # Arp Synth Fast Modulation
    routes:
      - source: "lfo1"
        destination: "filter_cutoff"
        amount: 90          # Very heavy filter mod
        polarity: "positive"
      - source: "lfo2"
        destination: "amp"
        amount: 30          # Fast tremolo
        polarity: "positive"
      - source: "mod_wheel"
        destination: "lfo1_speed"
        amount: 1.0         # Mod wheel controls speed
        polarity: "positive"
      - source: "aftertouch"
        destination: "filter_resonance"
        amount: 0.6         # Aftertouch controls resonance
        polarity: "positive"

# Effect Parameters
effects:
  system_effects:
    reverb:
      type: "hall_3"        # Large hall for space
      time: 2.5             # Long reverb time
      hf_damp: 0.4          # Moderate high frequency damping
      feedback: 0.6         # High feedback for space
      level: 0.4            # Moderate reverb level
      pre_delay: 0.030      # 30ms pre-delay
      room_size: 0.9        # Large room size
      diffusion: 0.8        # High diffusion
    
    chorus:
      type: "flanger_1"     # Flanger for intensity
      lfo_rate: 1.5         # Fast LFO rate
      lfo_depth: 0.8        # Deep modulation
      feedback: 0.6         # High feedback
      send_level: 0.4       # Good send level
      delay_time: 0.040     # 40ms delay
      phase_difference: 90  # Standard phase difference
  
  variation_effects:
    channel_1:  # Lead variation
      type: "distortion"
      parameters:
        drive: 0.7          # High drive
        level: 0.8          # High level
        tone: 0.6           # Mid tone
        pre_eq: 0.3         # Low pre EQ
        post_eq: 0.7        # High post EQ
        send_level: 0.6     # High send level
    
    channel_2:  # Pad variation
      type: "reverb"
      parameters:
        time: 4.0           # Very long reverb
        hf_damp: 0.2        # Low damping for brightness
        feedback: 0.8       # High feedback
        level: 0.5          # High level
        pre_delay: 0.050    # 50ms pre-delay
        send_level: 0.7     # High send level
    
    channel_3:  # Bass variation
      type: "auto_wah"
      parameters:
        cutoff_frequency: 1200  # High cutoff for bass
        resonance: 0.9          # Very high resonance
        modulation_rate: 3.0    # Fast rate
        depth: 0.8              # Deep depth
        send_level: 0.5         # Good send level
    
    channel_4:  # Arp variation
      type: "delay_lcr"
      parameters:
        left_delay: 0.125   # 125ms left
        center_delay: 0.250 # 250ms center
        right_delay: 0.375  # 375ms right
        feedback: 0.5       # 50% feedback
        send_level: 0.4     # Good send level

# Preset Configurations
presets:
  instruments:
    electronic_lead:
      channel_1:
        program: "synth_lead_1"
        bank_select:
          msb: 64
          lsb: 0
        filter:
          cutoff: 95
          resonance: 85
        amplifier:
          envelope:
            attack: 10
            decay: 50
            sustain: 90
            release: 30
        pitch:
          bend_range: 24
        lfo:
          lfo1:
            speed: 80
            pitch_depth: 100
          lfo2:
            speed: 120
            filter_depth: 80
        effects_sends:
          reverb: 30
          chorus: 60
          variation: 80
    
    atmospheric_pad:
      channel_2:
        program: "synth_pad_1"
        bank_select:
          msb: 64
          lsb: 0
        filter:
          cutoff: 60
          resonance: 40
        amplifier:
          envelope:
            attack: 80
            decay: 70
            sustain: 95
            release: 100
        lfo:
          lfo1:
            speed: 30
            delay: 2000
            pitch_depth: 15
        effects_sends:
          reverb: 80
          chorus: 70
          variation: 40
    
    aggressive_bass:
      channel_3:
        program: "synth_bass_1"
        bank_select:
          msb: 64
          lsb: 0
        filter:
          cutoff: 40
          resonance: 95
        amplifier:
          envelope:
            attack: 25
            decay: 75
            sustain: 80
            release: 50
        pitch:
          bend_range: 12
        lfo:
          lfo1:
            speed: 60
            pitch_depth: 40
          lfo2:
            speed: 40
            filter_depth: 60
        effects_sends:
          reverb: 15
          chorus: 30
          variation: 90
    
    bright_arp:
      channel_4:
        program: "synth_calliope"
        bank_select:
          msb: 64
          lsb: 0
        filter:
          cutoff: 100
          resonance: 70
          type: "bandpass"
        amplifier:
          envelope:
            attack: 5
            decay: 35
            sustain: 50
            release: 15
        lfo:
          lfo1:
            speed: 200
            filter_depth: 90
          lfo2:
            speed: 150
            amp_depth: 20
        effects_sends:
          reverb: 50
          chorus: 80
          variation: 60
  
  arrangements:
    electronic_trance:
      channel_1: "electronic_lead"
      channel_2: "atmospheric_pad"
      channel_3: "aggressive_bass"
      channel_4: "bright_arp"
      channel_9: "electronic_drums"
      effects:
        system_effects:
          reverb:
            type: "hall_3"
            time: 3.0
            level: 0.5
          chorus:
            type: "flanger_1"
            lfo_depth: 0.9
            send_level: 0.5

# Advanced Configuration Features
advanced_features:
  macros:
    create_trance_lead:
      - type: "set_modulation"
        source: "lfo1"
        destination: "pitch"
        amount: 100
      - type: "set_modulation"
        source: "lfo2"
        destination: "filter_cutoff"
        amount: 90
      - type: "set_controller_assignment"
        controller: "mod_wheel"
        assignment: "filter_modulation"
      - type: "set_effects_sends"
        reverb: 40
        chorus: 70
        variation: 90
    
    create_ambient_pad:
      - type: "set_filter"
        cutoff: 50
        resonance: 30
      - type: "set_lfo"
        lfo1:
          speed: 20
          delay: 3000
          fade_time: 5000
      - type: "set_effects_sends"
        reverb: 100
        chorus: 80
        variation: 50
  
  sequences:
    arpeggiator_pattern:
      - type: "note_sequence"
        channel: 4
        notes: ["C4", "E4", "G4", "B4", "C5", "B4", "G4", "E4"]
        velocity: 80
        duration: 0.125      # Fast arpeggio
        timing: 0.0
      - type: "control_change_sequence"
        channel: 4
        controller: "modulation"
        values: [0, 50, 100, 50, 0, 50, 100, 50]
        timing: 0.0
        duration: 1.0
        loop: true
  
  conditional_logic:
    velocity_filter_response:
      - condition: "velocity > 100"
        action: "set_filter_cutoff"
        value: 120
        target: "all_channels"
      - condition: "velocity < 50"
        action: "set_filter_cutoff"
        value: 40
        target: "all_channels"
      - condition: "velocity >= 50 and velocity <= 100"
        action: "set_filter_cutoff"
        value: 80
        target: "all_channels"
  
  automation:
    filter_sweep_lead:
      - parameter: "filter_cutoff"
        curve: "sine"
        start_value: 30
        end_value: 120
        duration: 16.0       # 16-beat sweep
        loop: true
        target: "channel_1"
    
    pad_evolution:
      - parameter: "lfo1_depth"
        curve: "exponential"
        start_value: 0
        end_value: 50
        duration: 32.0       # 32-beat evolution
        delay: 8.0           # Start after 8 beats
        target: "channel_2"
    
    bass_pressure:
      - parameter: "filter_resonance"
        curve: "linear"
        start_value: 60
        end_value: 95
        duration: 0.5        # Quick punch
        trigger: "note_on"
        target: "channel_3"
    
    arp_intensity:
      - parameter: "lfo1_speed"
        curve: "sine"
        start_value: 100
        end_value: 300
        duration: 8.0        # 8-beat intensity change
        loop: true
        target: "channel_4"