# XG MIDI DSL - Comprehensive Specification

## Table of Contents

1. [Overview](#overview)
2. [Document Structure](#document-structure)
3. [Basic MIDI Messages](#basic-midi-messages)
4. [MIDI Controllers](#midi-controllers)
5. [RPN Parameters](#rpn-parameters)
6. [XG Channel Parameters (NRPN)](#xg-channel-parameters-nrpn)
7. [XG Drum Parameters](#xg-drum-parameters)
8. [Effect Parameters](#effect-parameters)
9. [Time-Bound Message Sequences](#time-bound-message-sequences)
10. [System Exclusive Messages](#system-exclusive-messages)
11. [Advanced Features](#advanced-features)
12. [Complete Examples](#complete-examples)

## Overview

The XG MIDI DSL (Domain-Specific Language) provides a high-level, human-readable YAML-based interface for controlling Yamaha XG synthesizer parameters. It hides the complexity of numerical MIDI IDs, NRPN messages, and binary data while providing intuitive textual abstractions. The language friendly name is "XG Markup Language" or "XGML". The supposed filename extension is `.xgml`.

### Core Design Principles

1. **Intuitive Naming**: All parameters use descriptive, human-readable names
2. **Semantic Abstractions**: High-level concepts instead of raw parameter values
3. **Channel Organization**: Messages grouped by MIDI channel
4. **Timestamp Grouping**: Events at the same time grouped together
5. **Infrastructure Integration**: Direct mapping to existing XG classes
6. **Validation**: Automatic parameter range checking
7. **Dense Format**: Concise and readable YAML structure

## Document Structure

```yaml
xg_dsl_version: "1.0"
description: "XG synthesizer configuration"
timestamp: "2025-12-14T10:45:28Z"

# Static configuration sections
basic_messages:
  channels: {...}

rpn_parameters: {...}

channel_parameters: {...}

drum_parameters: {...}

system_exclusive: {...}

modulation_routing: {...}

effects: {...}

presets: {...}

advanced_features: {...}

# Time-bound sequences
sequences: {...}
```

## Basic MIDI Messages

### Channel Voice Messages

#### Program Changes
```yaml
program_change: "acoustic_grand_piano"  # Program name or MIDI number
bank_msb: 0                            # CC 0 (0-127)
bank_lsb: 0                            # CC 32 (0-127)
```

**Supported Program Names:**
- Pianos: `acoustic_grand_piano`, `bright_acoustic_piano`, `electric_grand_piano`, `honky_tonk_piano`, `electric_piano_1`, `electric_piano_2`, `harpsichord`, `clavinet`
- Chromatic Percussion: `celesta`, `glockenspiel`, `music_box`, `vibraphone`, `marimba`, `xylophone`, `tubular_bells`, `dulcimer`
- Organs: `drawbar_organ`, `percussive_organ`, `rock_organ`, `church_organ`, `reed_organ`, `accordion`, `harmonica`, `tango_accordion`
- Guitars: `nylon_string_guitar`, `steel_string_guitar`, `electric_jazz_guitar`, `electric_clean_guitar`, `electric_muted_guitar`, `overdriven_guitar`, `distortion_guitar`, `guitar_harmonics`
- Bass: `acoustic_bass`, `electric_bass_finger`, `electric_bass_pick`, `fretless_bass`, `slap_bass_1`, `slap_bass_2`, `synth_bass_1`, `synth_bass_2`
- Strings: `violin`, `viola`, `cello`, `contrabass`, `tremolo_strings`, `pizzicato_strings`, `orchestral_harp`, `timpani`
- Ensemble: `string_ensemble_1`, `string_ensemble_2`, `synth_strings_1`, `synth_strings_2`, `choir_aahs`, `voice_oohs`, `synth_voice`, `orchestra_hit`
- Brass: `trumpet`, `trombone`, `tuba`, `muted_trumpet`, `french_horn`, `brass_section`, `synth_brass_1`, `synth_brass_2`
- Reed: `soprano_sax`, `alto_sax`, `tenor_sax`, `baritone_sax`, `oboe`, `english_horn`, `bassoon`, `clarinet`
- Pipe: `piccolo`, `flute`, `recorder`, `pan_flute`, `blown_bottle`, `shakuhachi`, `whistle`, `ocarina`
- Synth Lead: `lead_1_square`, `lead_2_sawtooth`, `lead_3_calliope`, `lead_4_chiff`, `lead_5_charang`, `lead_6_voice`, `lead_7_fifths`, `lead_8_bass_lead`
- Synth Pad: `pad_1_new_age`, `pad_2_warm`, `pad_3_polysynth`, `pad_4_choir`, `pad_5_bowed`, `pad_6_metallic`, `pad_7_halo`, `pad_8_sweep`
- Synth Effects: `fx_1_rain`, `fx_2_soundtrack`, `fx_3_crystal`, `fx_4_atmosphere`, `fx_5_brightness`, `fx_6_goblins`, `fx_7_echoes`, `fx_8_sci_fi`
- Ethnic: `sitar`, `banjo`, `shamisen`, `koto`, `kalimba`, `bag_pipe`, `fiddle`, `shanai`
- Percussion: `tinkle_bell`, `agogo`, `steel_drums`, `woodblock`, `taiko_drum`, `melodic_tom`, `synth_drum`, `reverse_cymbal`
- Sound Effects: `guitar_fret_noise`, `breath_noise`, `seashore`, `bird_tweet`, `telephone_ring`, `helicopter`, `applause`, `gunshot`

#### Note Messages
```yaml
# Note On (for time-bound sequences)
note_on:
  note: "C4"                    # Note name or MIDI number (0-127)
  velocity: 80                  # 1-127
  duration: 2.0                 # Auto note_off after duration (seconds)
  articulation: "legato"        # legato, staccato, accent, tenuto

# Note Off (for time-bound sequences)  
note_off:
  note: "C4"                    # Note name or MIDI number
  velocity: 40                  # Note off velocity (0-127)

# Drum notes (for time-bound sequences)
kick: { note: 36, velocity: 100, duration: 0.5 }
snare: { note: 38, velocity: 95, duration: 0.3 }
hihat_closed: { note: 42, velocity: 70, duration: 0.25 }
hihat_open: { note: 46, velocity: 85, duration: 0.5 }
crash: { note: 49, velocity: 90, duration: 1.0 }
ride: { note: 51, velocity: 85, duration: 0.8 }
tom: { note: 45, velocity: 80, duration: 0.4 }
```

**Note Name Format:**
- Natural notes: `C`, `D`, `E`, `F`, `G`, `A`, `B`
- Sharp/flat notes: `C#`/`Db`, `D#`/`Eb`, `F#`/`Gb`, `G#`/`Ab`, `A#`/`Bb`
- Octaves: `C0` to `G8` (MIDI notes 0-127)

#### Pitch Bend
```yaml
# Simple pitch bend
pitch_bend: 2000                # -8192 to +8191

# Pitch bend with curve (for time-bound sequences)
pitch_bend:
  value: 2000                   # End value
  curve: "linear"               # linear, exponential, sine_wave, triangle
  duration: 1.0                 # Time to reach value
```

#### Aftertouch
```yaml
# Channel pressure (monophonic aftertouch)
channel_pressure: 64            # 0-127

# Polyphonic aftertouch (for time-bound sequences)
polyphonic_pressure:
  note: "C4"                    # Note name or MIDI number
  value: 50                     # 0-127
```

## MIDI Controllers

### Standard MIDI Controllers (CC 0-119)

| Controller | Name | Range | Description |
|------------|------|-------|-------------|
| 0 | bank_msb | 0-127 | Bank Select MSB |
| 1 | modulation | 0-127 | Modulation Wheel |
| 2 | breath_controller | 0-127 | Breath Control |
| 3 | undefined | 0-127 | Undefined |
| 4 | foot_controller | 0-127 | Foot Pedal |
| 5 | portamento_time | 0-127 | Portamento Time |
| 6 | data_entry_msb | 0-127 | Data Entry MSB |
| 7 | volume | 0-127 | Channel Volume |
| 8 | balance | 0-127 | Balance |
| 9 | undefined | 0-127 | Undefined |
| 10 | pan | 0-127 | Pan Position |
| 11 | expression | 0-127 | Expression Controller |
| 12 | effect_control_1 | 0-127 | Effect Control 1 |
| 13 | effect_control_2 | 0-127 | Effect Control 2 |
| 14-15 | undefined | 0-127 | Undefined |
| 16-19 | general_purpose_1-4 | 0-127 | General Purpose Controllers 1-4 |
| 20-31 | undefined | 0-127 | Undefined |
| 32 | bank_lsb | 0-127 | Bank Select LSB |
| 33 | modulation_lsb | 0-127 | Modulation Wheel LSB |
| 34 | breath_controller_lsb | 0-127 | Breath Control LSB |
| 35 | undefined_lsb | 0-127 | Undefined LSB |
| 36 | foot_controller_lsb | 0-127 | Foot Pedal LSB |
| 37 | portamento_time_lsb | 0-127 | Portamento Time LSB |
| 38 | data_entry_lsb | 0-127 | Data Entry LSB |
| 39 | volume_lsb | 0-127 | Channel Volume LSB |
| 40 | balance_lsb | 0-127 | Balance LSB |
| 41 | undefined_lsb | 0-127 | Undefined LSB |
| 42 | pan_lsb | 0-127 | Pan Position LSB |
| 43 | expression_lsb | 0-127 | Expression Controller LSB |
| 44 | effect_control_1_lsb | 0-127 | Effect Control 1 LSB |
| 45 | effect_control_2_lsb | 0-127 | Effect Control 2 LSB |
| 46-63 | undefined | 0-127 | Undefined |
| 64 | sustain | true/false | Damper Pedal (Sustain) |
| 65 | portamento | true/false | Portamento On/Off |
| 66 | sostenuto | true/false | Sostenuto Pedal |
| 67 | soft_pedal | true/false | Soft Pedal |
| 68 | legato_foot | true/false | Legato Foot Switch |
| 69 | hold_2 | true/false | Hold 2 |
| 70 | sound_variation | 0-127 | Sound Variation |
| 71 | harmonic_content | 0-127 | Harmonic Content (XG Filter Resonance) |
| 72 | release_time | 0-127 | Release Time (XG Filter Release) |
| 73 | attack_time | 0-127 | Attack Time (XG Filter Attack) |
| 74 | brightness | 0-127 | Brightness (XG Filter Cutoff) |
| 75 | decay_time | 0-127 | Decay Time (XG Filter Decay) |
| 76 | vibrato_rate | 0-127 | Vibrato Rate |
| 77 | vibrato_depth | 0-127 | Vibrato Depth |
| 78 | vibrato_delay | 0-127 | Vibrato Delay |
| 79 | undefined | 0-127 | Undefined |
| 80-83 | general_purpose_5-8 | 0-127 | General Purpose Controllers 5-8 |
| 84 | portamento_control | 0-127 | Portamento Control |
| 85-90 | undefined | 0-127 | Undefined |
| 91 | reverb_send | 0-127 | Reverb Send Level |
| 92 | tremor | 0-127 | Tremor |
| 93 | chorus_send | 0-127 | Chorus Send Level |
| 94 | variation_send | 0-127 | Variation Send Level |
| 95 | phenylalanine | 0-127 | Phenylalanine (XG External Data) |
| 96 | data_increment | 0-127 | Data Increment |
| 97 | data_decrement | 0-127 | Data Decrement |
| 98 | nrpn_lsb | 0-127 | Non-Registered Parameter Number LSB |
| 99 | nrpn_msb | 0-127 | Non-Registered Parameter Number MSB |
| 100 | rpn_lsb | 0-127 | Registered Parameter Number LSB |
| 101 | rpn_msb | 0-127 | Registered Parameter Number MSB |
| 102-119 | undefined | 0-127 | Undefined |

### XG-Specific Controllers

```yaml
# XG Sound Controllers (CC 71-78)
brightness: 64                 # CC 74 - Filter cutoff modulation
harmonic_content: 64           # CC 71 - Filter resonance modulation
release_time: 64               # CC 72 - Filter release time
attack_time: 64                # CC 73 - Filter attack time
decay_time: 64                 # CC 75 - Filter decay time
vibrato_rate: 64               # CC 76 - LFO vibrato rate
vibrato_depth: 64              # CC 77 - LFO vibrato depth
vibrato_delay: 64              # CC 78 - LFO vibrato delay

# XG Effect Sends (CC 91, 93-95)
reverb_send: 40                # CC 91 - Reverb send level
chorus_send: 20                # CC 93 - Chorus send level  
variation_send: 0              # CC 94 - Variation send level
external_data: 0               # CC 95 - External data

# XG General Purpose Controllers
sound_variation: 64            # CC 70 - Sound variation
tremor: 64                     # CC 92 - Tremor intensity
```

### Pan Position Values
```yaml
pan: "center"                  # 64
pan: "left"                    # 0
pan: "right"                   # 127
pan: "left_20"                 # 20 (20% left)
pan: "right_30"                # 97 (30% right)
pan: 64                        # Direct numerical value
```

### Boolean Controllers
```yaml
sustain: false                 # CC 64 - Sustain pedal
sustain: true                  # CC 64 - Sustain pedal
portamento: false              # CC 65 - Portamento on/off
sostenuto: false               # CC 67 - Sostenuto pedal
soft_pedal: false              # CC 67 - Soft pedal
legato_foot: false             # CC 68 - Legato foot switch
hold_2: false                  # CC 69 - Hold 2 pedal
```

## RPN Parameters

### Standard RPN Parameters (MSB 0)

| RPN (MSB, LSB) | Parameter Name | Range | Description |
|----------------|----------------|-------|-------------|
| (0, 0) | pitch_bend_range | 0-24 | Pitch Bend Sensitivity (semitones) |
| (0, 1) | fine_tuning | -100 to +100 | Fine Tuning (cents) |
| (0, 2) | coarse_tuning | -24 to +24 | Coarse Tuning (semitones) |
| (0, 3) | tuning_program_select | 0-127 | Tuning Program Select |
| (0, 4) | tuning_bank_select | 0-127 | Tuning Bank Select |
| (0, 5) | modulation_depth_range | 0-127 | Modulation Depth Range |

### RPN Usage

```yaml
# In static configuration
rpn_parameters:
  global:
    pitch_bend_range: 2        # RPN 0,0 (semitones)
    fine_tuning: -5            # RPN 0,1 (cents, signed)
    coarse_tuning: 0           # RPN 0,2 (semitones, signed)
    modulation_depth_range: 100 # RPN 0,5 (0-127)
    
  channel_1:
    pitch_bend_range: 7        # Extended range for expressive playing

# In time-bound sequences
rpn_parameters:                # Applied at time 0
  pitch_bend_range: 2
  fine_tuning: -5
  coarse_tuning: 0
  modulation_depth_range: 100
```

## XG Channel Parameters (NRPN)

### MSB 3: Basic Channel Parameters

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | volume_coarse | 0-127 | Volume Coarse (MSB) |
| 1 | volume_fine | 0-127 | Volume Fine (LSB) |
| 2 | pan_coarse | 0-127 | Pan Coarse (MSB) |
| 3 | pan_fine | 0-127 | Pan Fine (LSB) |
| 4 | expression_coarse | 0-127 | Expression Coarse (MSB) |
| 5 | expression_fine | 0-127 | Expression Fine (LSB) |
| 6 | modulation_depth | 0-127 | Modulation Depth |
| 7 | modulation_speed | 0-127 | Modulation Speed |

### MSB 4: Pitch & Tuning Parameters

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | pitch_coarse | 0-127 | Pitch Coarse (-12 to +12 semitones) |
| 1 | pitch_fine | 0-127 | Pitch Fine (-100 to +100 cents) |
| 2 | pitch_bend_range | 0-12 | Pitch Bend Range (semitones) |
| 3 | portamento_mode | 0-1 | Portamento Mode (OFF/ON) |
| 4 | portamento_time | 0-127 | Portamento Time |
| 5 | pitch_balance | 0-127 | Pitch Balance |

### MSB 5-6: Filter Parameters

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 5 | 0 | filter_cutoff | 0-127 | Filter Cutoff (-9600 to +9600 cents) |
| 5 | 1 | filter_resonance | 0-127 | Filter Resonance |
| 5 | 2 | filter_attack | 0-127 | Filter Envelope Attack |
| 5 | 3 | filter_decay | 0-127 | Filter Envelope Decay |
| 5 | 4 | filter_sustain | 0-127 | Filter Envelope Sustain |
| 5 | 5 | filter_release | 0-127 | Filter Envelope Release |
| 5 | 6 | brightness | 0-127 | Brightness |
| 5 | 7 | filter_type | 0-3 | Filter Type (0=LPF, 1=HPF, 2=BPF, 3=BRF) |
| 6 | 0 | filter_cutoff_lsb | 0-127 | Filter Cutoff LSB |
| 6 | 1 | filter_resonance_lsb | 0-127 | Filter Resonance LSB |
| 6 | 2 | filter_attack_lsb | 0-127 | Filter Envelope Attack LSB |
| 6 | 3 | filter_decay_lsb | 0-127 | Filter Envelope Decay LSB |
| 6 | 4 | filter_sustain_lsb | 0-127 | Filter Envelope Sustain LSB |
| 6 | 5 | filter_release_lsb | 0-127 | Filter Envelope Release LSB |
| 6 | 6 | brightness_lsb | 0-127 | Brightness LSB |
| 6 | 7 | filter_type | 0-3 | Filter Type |

### MSB 7-8: Amplifier Envelope

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 7 | 0 | amp_attack | 0-127 | Amplifier Envelope Attack |
| 7 | 1 | amp_decay | 0-127 | Amplifier Envelope Decay |
| 7 | 2 | amp_sustain | 0-127 | Amplifier Envelope Sustain |
| 7 | 3 | amp_release | 0-127 | Amplifier Envelope Release |
| 7 | 4 | amp_velocity_sense | 0-127 | Amplifier Velocity Sensitivity |
| 7 | 5 | amp_key_scaling | 0-127 | Amplifier Key Scaling |
| 8 | 0 | amp_attack_lsb | 0-127 | Amplifier Envelope Attack LSB |
| 8 | 1 | amp_decay_lsb | 0-127 | Amplifier Envelope Decay LSB |
| 8 | 2 | amp_sustain_lsb | 0-127 | Amplifier Envelope Sustain LSB |
| 8 | 3 | amp_release_lsb | 0-127 | Amplifier Envelope Release LSB |
| 8 | 4 | amp_velocity_sense_lsb | 0-127 | Amplifier Velocity Sensitivity LSB |
| 8 | 5 | amp_key_scaling_lsb | 0-127 | Amplifier Key Scaling LSB |

### MSB 9-10: LFO Parameters

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 9 | 0 | lfo1_waveform | 0-3 | LFO1 Waveform (0=Triangle, 1=SAW, 2=Square, 3=Sine) |
| 9 | 1 | lfo1_speed | 0-127 | LFO1 Speed |
| 9 | 2 | lfo1_delay | 0-127 | LFO1 Delay |
| 9 | 3 | lfo1_fade_time | 0-127 | LFO1 Fade Time |
| 9 | 4 | lfo1_pitch_depth | 0-127 | LFO1 Pitch Depth |
| 9 | 5 | lfo1_filter_depth | 0-127 | LFO1 Filter Depth |
| 9 | 6 | lfo1_amp_depth | 0-127 | LFO1 Amplitude Depth |
| 9 | 7 | lfo1_pitch_control | 0-127 | LFO1 Pitch Control |
| 10 | 0 | lfo2_waveform | 0-3 | LFO2 Waveform |
| 10 | 1 | lfo2_speed | 0-127 | LFO2 Speed |
| 10 | 2 | lfo2_delay | 0-127 | LFO2 Delay |
| 10 | 3 | lfo2_fade_time | 0-127 | LFO2 Fade Time |
| 10 | 4 | lfo2_pitch_depth | 0-127 | LFO2 Pitch Depth |
| 10 | 5 | lfo2_filter_depth | 0-127 | LFO2 Filter Depth |
| 10 | 6 | lfo2_amp_depth | 0-127 | LFO2 Amplitude Depth |
| 10 | 7 | lfo2_pitch_control | 0-127 | LFO2 Pitch Control |

### MSB 11-12: Effects Send

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 11 | 0 | reverb_send | 0-127 | Reverb Send Level |
| 11 | 1 | chorus_send | 0-127 | Chorus Send Level |
| 11 | 2 | variation_send | 0-127 | Variation Send Level |
| 11 | 3 | dry_level | 0-127 | Dry Level |
| 11 | 4 | insertion_part_l | 0-127 | Insertion Part L |
| 11 | 5 | insertion_part_r | 0-127 | Insertion Part R |
| 11 | 6 | insertion_connection | 0-1 | Insertion Connection (0=System, 1=Insertion) |
| 11 | 7 | send_chorus_to_reverb | 0-1 | Send Chorus to Reverb |
| 12 | 0 | reverb_send_lsb | 0-127 | Reverb Send Level LSB |
| 12 | 1 | chorus_send_lsb | 0-127 | Chorus Send Level LSB |
| 12 | 2 | variation_send_lsb | 0-127 | Variation Send Level LSB |
| 12 | 3 | dry_level_lsb | 0-127 | Dry Level LSB |
| 12 | 4 | insertion_part_l_lsb | 0-127 | Insertion Part L LSB |
| 12 | 5 | insertion_part_r_lsb | 0-127 | Insertion Part R LSB |
| 12 | 6 | insertion_connection | 0-1 | Insertion Connection |
| 12 | 7 | send_chorus_to_reverb | 0-1 | Send Chorus to Reverb |

### MSB 13: Pitch Envelope

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | pitch_attack | 0-127 | Pitch Envelope Attack |
| 1 | pitch_decay | 0-127 | Pitch Envelope Decay |
| 2 | pitch_sustain | 0-127 | Pitch Envelope Sustain |
| 3 | pitch_release | 0-127 | Pitch Envelope Release |
| 4 | pitch_attack_level | 0-127 | Pitch Envelope Attack Level |
| 5 | pitch_decay_level | 0-127 | Pitch Envelope Decay Level |
| 6 | pitch_sustain_level | 0-127 | Pitch Envelope Sustain Level |
| 7 | pitch_release_level | 0-127 | Pitch Envelope Release Level |

### MSB 14: Pitch LFO

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | pitch_lfo_waveform | 0-3 | Pitch LFO Waveform |
| 1 | pitch_lfo_speed | 0-127 | Pitch LFO Speed |
| 2 | pitch_lfo_delay | 0-127 | Pitch LFO Delay |
| 3 | pitch_lfo_fade_time | 0-127 | Pitch LFO Fade Time |
| 4 | pitch_lfo_pitch_depth | 0-127 | Pitch LFO Pitch Depth |

### MSB 15-16: Controller Assignments

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 15 | 0 | mod_wheel_assign | 0-12 | Mod Wheel Assignment |
| 15 | 1 | foot_controller_assign | 0-12 | Foot Controller Assignment |
| 15 | 2 | aftertouch_assign | 0-12 | Aftertouch Assignment |
| 15 | 3 | breath_controller_assign | 0-12 | Breath Controller Assignment |
| 15 | 4 | general1_assign | 0-12 | General Purpose Button 1 Assignment |
| 16 | 0 | general2_assign | 0-12 | General Purpose Button 2 Assignment |
| 16 | 1 | general3_assign | 0-12 | General Purpose Button 3 Assignment |
| 16 | 2 | general4_assign | 0-12 | General Purpose Button 4 Assignment |
| 16 | 3 | ribbon_assign | 0-12 | Ribbon Controller Assignment |

**Controller Assignment Values:**
- 0: OFF, 1: MOD, 2: VOL, 3: PAN, 4: EXP, 5: REV, 6: CHO, 7: VAR, 8: PAN, 9: FLT, 10: POR, 11: PIT, 12: AMB

### MSB 17-18: Scale Tuning

| MSB | LSB | Parameter Name | Range | Description |
|-----|-----|----------------|-------|-------------|
| 17 | 0 | scale_tune_c | 0-127 | Scale Tuning C (-64 to +63 cents) |
| 17 | 1 | scale_tune_csharp | 0-127 | Scale Tuning C# |
| 17 | 2 | scale_tune_d | 0-127 | Scale Tuning D |
| 17 | 3 | scale_tune_dsharp | 0-127 | Scale Tuning D# |
| 17 | 4 | scale_tune_e | 0-127 | Scale Tuning E |
| 17 | 5 | scale_tune_f | 0-127 | Scale Tuning F |
| 17 | 6 | scale_tune_fsharp | 0-127 | Scale Tuning F# |
| 18 | 0 | scale_tune_g | 0-127 | Scale Tuning G |
| 18 | 1 | scale_tune_gsharp | 0-127 | Scale Tuning G# |
| 18 | 2 | scale_tune_a | 0-127 | Scale Tuning A |
| 18 | 3 | scale_tune_asharp | 0-127 | Scale Tuning A# |
| 18 | 4 | scale_tune_b | 0-127 | Scale Tuning B |
| 18 | 5 | octave_tune | 0-127 | Octave Tuning (-64 to +63 cents per octave) |

### MSB 19: Velocity Response

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | velocity_curve | 0-9 | Velocity Curve (0-9) |
| 1 | velocity_offset | 0-127 | Velocity Offset |
| 2 | velocity_range | 0-127 | Velocity Range |
| 3 | velocity_curve_offset | 0-127 | Velocity Curve Offset |
| 4 | velocity_curve_range | 0-127 | Velocity Curve Range |

### XG Channel Parameter Usage

```yaml
# In static configuration
channel_parameters:
  channel_1:
    # Basic Channel Parameters (MSB 3)
    volume:
      coarse: 100              # LSB 0
      fine: 64                 # LSB 1
    pan:
      coarse: "center"         # LSB 2
      fine: 64                 # LSB 3
    expression:
      coarse: 127              # LSB 4
      fine: 64                 # LSB 5
    
    # Filter Parameters (MSB 5-6)
    filter:
      cutoff: 80               # MSB 5 LSB 0
      resonance: 70            # MSB 6 LSB 1
      type: "lowpass"          # MSB 6 LSB 7 (0=LPF, 1=HPF, 2=BPF, 3=BRF)
      envelope:
        attack: 90             # MSB 5 LSB 2
        decay: 40              # MSB 5 LSB 3
        sustain: 70            # MSB 5 LSB 4
        release: 60            # MSB 5 LSB 5
    
    # Amplifier Envelope (MSB 7-8)
    amplifier:
      envelope:
        attack: 90             # MSB 7 LSB 0
        decay: 40              # MSB 7 LSB 1
        sustain: 70            # MSB 7 LSB 2
        release: 60            # MSB 7 LSB 3
      velocity_sensitivity: 80 # MSB 7 LSB 4
      key_scaling: 50          # MSB 7 LSB 5
    
    # LFO Parameters (MSB 9-10)
    lfo:
      lfo1:
        waveform: "sine"       # MSB 9 LSB 0 (0=Triangle, 1=SAW, 2=Square, 3=Sine)
        speed: 64              # MSB 9 LSB 1
        delay: 0               # MSB 9 LSB 2
        fade_time: 0           # MSB 9 LSB 3
        pitch_depth: 50        # MSB 9 LSB 4
        filter_depth: 30       # MSB 9 LSB 5
        amp_depth: 20          # MSB 9 LSB 6
      lfo2:
        waveform: "triangle"   # MSB 10 LSB 0
        speed: 32              # MSB 10 LSB 1
        delay: 10              # MSB 10 LSB 2
        fade_time: 5           # MSB 10 LSB 3
        pitch_depth: 20        # MSB 10 LSB 4
        filter_depth: 30       # MSB 10 LSB 5
        amp_depth: 0           # MSB 10 LSB 6
    
    # Effects Send (MSB 11-12)
    effects_sends:
      reverb: 50               # MSB 11 LSB 0
      chorus: 20               # MSB 11 LSB 1
      variation: 0             # MSB 11 LSB 2
      dry_level: 127           # MSB 11 LSB 3
      insertion:
        part_l: 127            # MSB 11 LSB 4
        part_r: 127            # MSB 11 LSB 5
        connection: "system"   # MSB 11 LSB 6 (0=System, 1=Insertion)
    
    # Controller Assignments (MSB 15-16)
    controller_assignments:
      mod_wheel: "pitch_modulation"    # MSB 15 LSB 0
      foot_controller: "filter_modulation" # MSB 15 LSB 1
      aftertouch: "amp_modulation"     # MSB 15 LSB 2
      breath_controller: "pitch_modulation" # MSB 15 LSB 3
      general_buttons:
        gp1: "filter_type"             # MSB 15 LSB 4
        gp2: "effect_bypass"           # MSB 16 LSB 0
        gp3: "modulation_source"       # MSB 16 LSB 1
        gp4: "performance_preset"      # MSB 16 LSB 2
    
    # Scale Tuning (MSB 17-18)
    scale_tuning:
      notes:
        c: 64                    # MSB 17 LSB 0 (-64 to +63 cents)
        csharp: 66               # MSB 17 LSB 1 (+2 cents)
        d: 64                    # MSB 17 LSB 2
        dsharp: 62               # MSB 17 LSB 3 (-2 cents)
        e: 64                    # MSB 17 LSB 4
        f: 64                    # MSB 17 LSB 5
        fsharp: 64               # MSB 17 LSB 6
        g: 64                    # MSB 18 LSB 0
        gsharp: 64               # MSB 18 LSB 1
        a: 64                    # MSB 18 LSB 2
        asharp: 64               # MSB 18 LSB 3
        b: 64                    # MSB 18 LSB 4
      octave_tune: 64            # MSB 18 LSB 5 (-64 to +63 cents per octave)

# In time-bound sequences (simplified syntax)
parameters:                     # Applied at time 0
  volume: 100                   # MSB 3 LSB 0
  pan: "center"                 # MSB 3 LSB 2
  expression: 127               # MSB 3 LSB 4
  filter_cutoff: 80             # MSB 5 LSB 0
  filter_resonance: 70          # MSB 6 LSB 1
  amp_attack: 90                # MSB 7 LSB 0
  amp_decay: 40                 # MSB 7 LSB 1
  amp_sustain: 70               # MSB 7 LSB 2
  amp_release: 60               # MSB 7 LSB 3
  lfo1_speed: 64                # MSB 9 LSB 1
  lfo1_waveform: "sine"         # MSB 9 LSB 0
  reverb_send: 50               # MSB 11 LSB 0
  chorus_send: 20               # MSB 11 LSB 1
  variation_send: 0             # MSB 11 LSB 2
```

## XG Drum Parameters

### MSB 40: Basic Drum Parameters

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | drum_level | 0-127 | Drum Note Level |
| 1 | drum_pan | 0-127 | Drum Note Pan |
| 2 | drum_assign | 0-2 | Drum Note Assign (0=note-off, 1=poly, 2=mono) |
| 3 | drum_coarse_tune | 0-127 | Drum Note Coarse Tune |
| 4 | drum_fine_tune | 0-127 | Drum Note Fine Tune |
| 5 | drum_filter_cutoff | 0-127 | Drum Note Filter Cutoff |
| 6 | drum_filter_resonance | 0-127 | Drum Note Filter Resonance |
| 7 | drum_attack_time | 0-127 | Drum Note Attack Time |
| 8 | drum_decay_time | 0-127 | Drum Note Decay Time |

### MSB 41: Drum Effect Sends

| LSB | Parameter Name | Range | Description |
|-----|----------------|-------|-------------|
| 0 | drum_reverb_send | 0-127 | Drum Note Reverb Send |
| 1 | drum_chorus_send | 0-127 | Drum Note Chorus Send |

### Standard Drum Kit Notes

| Note | Drum Name | Typical Usage |
|------|-----------|---------------|
| 35 | Acoustic Bass Drum | Kick drum |
| 36 | Bass Drum 1 | Kick drum |
| 37 | Side Stick | Rim shot |
| 38 | Acoustic Snare | Snare drum |
| 39 | Hand Clap | Hand clap |
| 40 | Electric Snare | Electronic snare |
| 41 | Low Floor Tom | Low tom |
| 42 | Closed Hi-Hat | Hi-hat (closed) |
| 43 | High Floor Tom | High tom |
| 44 | Pedal Hi-Hat | Hi-hat (pedal) |
| 45 | Low Tom | Mid-low tom |
| 46 | Open Hi-Hat | Hi-hat (open) |
| 47 | Low-Mid Tom | Mid tom |
| 48 | High-Mid Tom | Mid-high tom |
| 49 | Crash Cymbal 1 | Crash cymbal |
| 50 | High Tom | High tom |
| 51 | Ride Cymbal 1 | Ride cymbal |
| 52 | Chinese Cymbal | China cymbal |
| 53 | Ride Bell | Ride bell |
| 54 | Tambourine | Tambourine |
| 55 | Splash Cymbal | Splash cymbal |
| 56 | Cowbell | Cowbell |
| 57 | Crash Cymbal 2 | Crash cymbal 2 |
| 58 | Vibraslap | Vibraslap |
| 59 | Ride Cymbal 2 | Ride cymbal 2 |
| 60 | High Bongo | High bongo |
| 61 | Low Bongo | Low bongo |
| 62 | Mute High Conga | Muted high conga |
| 63 | Open High Conga | Open high conga |
| 64 | Low Conga | Low conga |
| 65 | High Timbale | High timbale |
| 66 | Low Timbale | Low timbale |
| 67 | High Agogo | High agogo |
| 68 | Low Agogo | Low agogo |
| 69 | Cabasa | Cabasa |
| 70 | Maracas | Maracas |
| 71 | Short Whistle | Short whistle |
| 72 | Long Whistle | Long whistle |
| 73 | Short Guiro | Short guiro |
| 74 | Long Guiro | Long guiro |
| 75 | Claves | Claves |
| 76 | High Wood Block | High wood block |
| 77 | Low Wood Block | Low wood block |
| 78 | Mute Cuica | Muted cuica |
| 79 | Open Cuica | Open cuica |
| 80 | Mute Triangle | Muted triangle |
| 81 | Open Triangle | Open triangle |
| 82 | Shaker | Shaker |
| 83 | Jingle Bell | Jingle bell |
| 84 | Bell Tree | Bell tree |
| 85 | Castanets | Castanets |
| 86 | Mute Surdo | Muted surdo |
| 87 | Open Surdo | Open surdo |

### XG Drum Parameter Usage

```yaml
# In static configuration
drum_parameters:
  drum_channel: 9              # MIDI channel 10
  drum_notes:
    36:                        # Kick drum
      level: 100               # MSB 40 LSB 0
      pan: "center"            # MSB 40 LSB 1
      assign: "poly"           # MSB 40 LSB 2 (0=note-off, 1=poly, 2=mono)
      coarse_tune: 64          # MSB 40 LSB 3 (64=center, ±24 semitones)
      fine_tune: 64            # MSB 40 LSB 4 (64=center, ±50 cents)
      filter_cutoff: 50        # MSB 40 LSB 5
      filter_resonance: 60     # MSB 40 LSB 6
      attack_time: 90          # MSB 40 LSB 7
      decay_time: 30           # MSB 40 LSB 8
      reverb_send: 25          # MSB 41 LSB 0
      chorus_send: 0           # MSB 41 LSB 1
    
    38:                        # Snare drum
      level: 95
      pan: "center"
      assign: "poly"
      coarse_tune: 64
      fine_tune: 67            # +3 cents for definition
      filter_cutoff: 80        # Brighter
      filter_resonance: 70     # More resonant
      attack_time: 80          # Faster attack
      decay_time: 50           # Shorter decay
      reverb_send: 30
      chorus_send: 10
    
    42:                        # Hi-hat closed
      level: 80
      pan: "right"             # Pan to right
      assign: "poly"
      coarse_tune: 64
      fine_tune: 64
      filter_cutoff: 96        # Very bright
      filter_resonance: 85     # High resonance
      attack_time: 90          # Instant attack
      decay_time: 30           # Quick decay
      reverb_send: 10
      chorus_send: 5
    
    46:                        # Hi-hat open
      level: 85
      pan: "right"
      assign: "poly"
      coarse_tune: 64
      fine_tune: 64
      filter_cutoff: 94
      filter_resonance: 80
      attack_time: 90
      decay_time: 60           # Longer decay for open hat
      reverb_send: 15
      chorus_send: 8
    
    49:                        # Crash cymbal
      level: 80
      pan: "left_40"
      assign: "poly"
      coarse_tune: 64
      fine_tune: 63
      filter_cutoff: 88
      filter_resonance: 75
      attack_time: 80
      decay_time: 70           # Medium decay
      reverb_send: 50
      chorus_send: 25
    
    51:                        # Ride cymbal
      level: 75
      pan: "right_40"
      assign: "poly"
      coarse_tune: 64
      fine_tune: 65
      filter_cutoff: 85
      filter_resonance: 70
      attack_time: 75
      decay_time: 80           # Long decay for ride
      reverb_send: 45
      chorus_send: 20
  
  # Pattern-based configuration
  pattern_configurations:
    jazz_drums:
      kick:
        level: 90
        reverb_send: 25
      snare:
        level: 100
        reverb_send: 35
      hi_hat:
        level: 75
        filter_cutoff: 90
    
    rock_drums:
      kick:
        level: 110
        filter_resonance: 80
      snare:
        level: 105
        reverb_send: 40
      crash:
        level: 90
        reverb_send: 50

# In time-bound sequences (simplified)
- track:
    channel: 9                 # Drum channel
    parameters:
      volume: 105
      bank_msb: 126
      bank_lsb: 0
    
    events:
      - at:
          time: 0.0
          program_change: "standard_drum_kit"
          kick: { note: 36, velocity: 100, duration: 0.5 }
          snare: { note: 38, velocity: 95, duration: 0.3 }
          hihat_closed: { note: 42, velocity: 70, duration: 0.25 }
```

## Effect Parameters

### System Effects (Reverb)

| Parameter | Range | Description |
|-----------|-------|-------------|
| type | string | Reverb type (hall_1, hall_2, hall_3, hall_4, room_1, room_2, room_3, room_4, stage_1, stage_2, stage_3, stage_4, plate) |
| time | 0.1-5.0 seconds | Reverb time |
| hf_damp | 0.0-1.0 | High frequency damping |
| feedback | 0.0-0.95 | Reverberation feedback |
| level | 0.0-1.0 | Wet level |
| pre_delay | 0.0-0.1 seconds | Pre-delay time |
| room_size | 0.0-1.0 | Room size |
| diffusion | 0.0-1.0 | Diffusion |

### System Effects (Chorus)

| Parameter | Range | Description |
|-----------|-------|-------------|
| type | string | Chorus type (chorus_1, chorus_2, celeste_1, celeste_2, flanger_1, flanger_2) |
| lfo_rate | 0.125-8.0 Hz | LFO rate |
| lfo_depth | 0.0-1.0 | LFO depth |
| feedback | -1.0 to 1.0 | Feedback |
| send_level | 0.0-1.0 | Send level |
| delay_time | 0.005-0.050 seconds | Delay time |
| phase_difference | 0-180 degrees | Phase difference |

### Variation Effects (MSB 3, LSB 0-14)

XG Variation Effects provide 15 different effect types that can be applied per-part. Each effect has specific parameters controlled via NRPN MSB 3.

#### Chorus Effects (Types 0-3)
| Type | Description | Parameters |
|------|-------------|------------|
| chorus_1 | Standard chorus | rate: 0.5Hz, depth: 0.5, feedback: 0.0, delay: 0.025s, phase_diff: 90° |
| chorus_2 | Deeper chorus | rate: 1.0Hz, depth: 0.7, feedback: 0.2, delay: 0.030s, phase_diff: 90° |
| chorus_3 | Slow chorus | rate: 0.3Hz, depth: 0.6, feedback: 0.0, delay: 0.035s, phase_diff: 90° |
| chorus_4 | Fast chorus | rate: 1.5Hz, depth: 0.4, feedback: 0.1, delay: 0.020s, phase_diff: 90° |

#### Celeste Effects (Types 4-5)
| Type | Description | Parameters |
|------|-------------|------------|
| celeste_1 | Standard celeste | rate: 0.3Hz, depth: 0.4, feedback: -0.3, delay: 0.025s, phase_diff: 180° |
| celeste_2 | Deep celeste | rate: 0.4Hz, depth: 0.6, feedback: -0.4, delay: 0.030s, phase_diff: 180° |

#### Flanger Effects (Types 6-7)
| Type | Description | Parameters |
|------|-------------|------------|
| flanger_1 | Standard flanger | rate: 0.1Hz, depth: 0.7, feedback: 0.7, delay: 0.001s, phase_diff: 0° |
| flanger_2 | Deep flanger | rate: 0.2Hz, depth: 0.9, feedback: 0.9, delay: 0.002s, phase_diff: 0° |

#### Phaser Effects (Types 8-9)
| Type | Description | Parameters |
|------|-------------|------------|
| phaser_1 | 4-stage phaser | rate: 0.5Hz, depth: 0.6, feedback: 0.5, stages: 4, manual: 0.5 |
| phaser_2 | 8-stage phaser | rate: 1.0Hz, depth: 0.8, feedback: 0.7, stages: 8, manual: 0.3 |

#### Auto Wah (Type 10)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| cutoff_frequency | 50-5000Hz | 1000Hz | Center frequency |
| resonance | 0.0-1.0 | 0.8 | Filter resonance |
| modulation_rate | 0.1-10.0Hz | 2.5Hz | LFO rate |
| depth | 0.0-1.0 | 0.6 | Modulation depth |
| manual | 0.0-1.0 | 0.5 | Manual frequency control |

#### Rotary Speaker (Type 11)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-10.0Hz | 0.5Hz | Rotation speed |
| depth | 0.0-1.0 | 0.7 | Modulation depth |
| feedback | 0.0-1.0 | 0.3 | Internal feedback |
| drive | 0.0-1.0 | 0.5 | Overdrive amount |
| horn_balance | 0.0-1.0 | 0.5 | Horn/rotor balance |

#### Tremolo (Type 12)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-10.0Hz | 4.0Hz | Modulation rate |
| depth | 0.0-1.0 | 0.5 | Modulation depth |
| waveform | sine/triangle/square | sine | LFO waveform |
| phase | 0-360° | 0° | LFO phase offset |

#### Delay LCR (Type 13)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| left_delay | 0.001-2.0s | 0.250s | Left channel delay |
| center_delay | 0.001-2.0s | 0.125s | Center channel delay |
| right_delay | 0.001-2.0s | 0.375s | Right channel delay |
| feedback | 0.0-0.95 | 0.3 | Feedback amount |
| hf_damp | 0.0-1.0 | 0.5 | High-frequency damping |
| level | 0.0-1.0 | 0.3 | Wet level |

#### Delay LR (Type 14)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| left_delay | 0.001-2.0s | 0.250s | Left channel delay |
| right_delay | 0.001-2.0s | 0.300s | Right channel delay |
| feedback | 0.0-0.95 | 0.35 | Feedback amount |
| hf_damp | 0.0-1.0 | 0.5 | High-frequency damping |
| level | 0.0-1.0 | 0.3 | Wet level |

### Insertion Effects (3 per Part)

XG provides 3 insertion effect slots per part, each capable of running any of the 12 insertion effect types. Insertion effects are processed in the signal chain before variation effects.

#### Distortion (Type 0)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| drive | 0.0-1.0 | 0.5 | Distortion amount |
| level | 0.0-1.0 | 0.8 | Output level |
| tone | 0.0-1.0 | 0.5 | Tone control (brightness) |
| presence | 0.0-1.0 | 0.3 | High-frequency enhancement |

#### Compressor (Type 1)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| threshold | -40 to 0 dB | -12 dB | Compression threshold |
| ratio | 1:1 to 20:1 | 4:1 | Compression ratio |
| attack | 0.001-0.1s | 0.01s | Attack time |
| release | 0.01-1.0s | 0.1s | Release time |
| gain | -20 to +20 dB | 3 dB | Makeup gain |
| knee | 0-20 dB | 2 dB | Soft knee width |

#### 6-Band EQ (Type 2)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| low_gain | -20 to +20 dB | 0 dB | Low band gain |
| low_freq | 20-400 Hz | 80 Hz | Low band frequency |
| low_mid_gain | -20 to +20 dB | 0 dB | Low-mid band gain |
| low_mid_freq | 100-1000 Hz | 250 Hz | Low-mid band frequency |
| mid_gain | -20 to +20 dB | 0 dB | Mid band gain |
| mid_freq | 200-5000 Hz | 1000 Hz | Mid band frequency |
| high_mid_gain | -20 to +20 dB | 0 dB | High-mid band gain |
| high_mid_freq | 500-10000 Hz | 3000 Hz | High-mid band frequency |
| high_gain | -20 to +20 dB | 0 dB | High band gain |
| high_freq | 1000-20000 Hz | 8000 Hz | High band frequency |

#### Delay (Type 3)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| delay_time | 0.001-2.0s | 0.3s | Delay time |
| feedback | 0.0-0.95 | 0.4 | Feedback amount |
| level | 0.0-1.0 | 0.5 | Wet level |
| hf_damp | 0.0-1.0 | 0.3 | High-frequency damping |
| pan | -1.0 to 1.0 | 0.0 | Delay pan position |

#### Chorus (Type 4)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-10.0 Hz | 0.8 Hz | LFO rate |
| depth | 0.0-1.0 | 0.5 | Modulation depth |
| feedback | -0.95 to 0.95 | 0.2 | Feedback amount |
| level | 0.0-1.0 | 0.4 | Wet level |
| delay_time | 0.005-0.05s | 0.025s | Base delay time |
| phase_diff | 0-180° | 90° | Stereo phase difference |

#### Flanger (Type 5)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.05-5.0 Hz | 0.2 Hz | LFO rate |
| depth | 0.0-1.0 | 0.7 | Modulation depth |
| feedback | -0.95 to 0.95 | 0.6 | Feedback amount |
| level | 0.0-1.0 | 0.5 | Wet level |
| delay_time | 0.0001-0.01s | 0.001s | Base delay time |
| manual | 0.0-1.0 | 0.5 | Manual delay offset |

#### Phaser (Type 6)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-5.0 Hz | 0.8 Hz | LFO rate |
| depth | 0.0-1.0 | 0.6 | Modulation depth |
| feedback | -0.95 to 0.95 | 0.5 | Feedback amount |
| level | 0.0-1.0 | 0.4 | Wet level |
| stages | 2-12 | 4 | Number of all-pass stages |
| manual | 0.0-1.0 | 0.5 | Manual frequency control |

#### Auto Wah (Type 7)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| cutoff_frequency | 50-5000 Hz | 1000 Hz | Center frequency |
| resonance | 0.0-1.0 | 0.8 | Filter resonance |
| modulation_rate | 0.1-10.0 Hz | 2.5 Hz | LFO rate |
| depth | 0.0-1.0 | 0.6 | Modulation depth |
| level | 0.0-1.0 | 0.5 | Wet level |
| manual | 0.0-1.0 | 0.5 | Manual frequency control |

#### Tremolo (Type 8)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-10.0 Hz | 4.0 Hz | Modulation rate |
| depth | 0.0-1.0 | 0.5 | Modulation depth |
| waveform | sine/triangle/square | sine | LFO waveform |
| level | 0.0-1.0 | 0.5 | Wet level |
| phase | 0-360° | 0° | LFO phase offset |

#### Rotary Speaker (Type 9)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| rate | 0.1-10.0 Hz | 0.5 Hz | Rotation speed |
| depth | 0.0-1.0 | 0.7 | Modulation depth |
| feedback | 0.0-1.0 | 0.3 | Internal feedback |
| level | 0.0-1.0 | 0.5 | Wet level |
| drive | 0.0-1.0 | 0.5 | Overdrive amount |
| horn_balance | 0.0-1.0 | 0.5 | Horn/rotor balance |

#### Guitar Amp Simulator (Type 10)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| drive | 0.0-1.0 | 0.6 | Preamp drive |
| amp_type | fender/jmarshall/vox/acoustic | fender | Amplifier model |
| tone | 0.0-1.0 | 0.5 | Tone control |
| presence | 0.0-1.0 | 0.3 | Presence control |
| level | 0.0-1.0 | 0.8 | Output level |
| cab_type | open/closed | open | Cabinet type |

#### Limiter (Type 11)
| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| threshold | -40 to 0 dB | -6 dB | Limiting threshold |
| ratio | 1:1 to ∞:1 | ∞:1 | Limiting ratio |
| attack | 0.001-0.1s | 0.001s | Attack time |
| release | 0.01-1.0s | 0.05s | Release time |
| gain | -20 to +20 dB | 0 dB | Makeup gain |
| knee | 0-20 dB | 0 dB | Soft knee width |

### Effect Parameter Usage

```yaml
# In static configuration
effects:
  # System Effects (shared across all parts)
  system_effects:
    reverb:
      type: "hall_2"          # hall_1, hall_2, hall_3, hall_4, room_1-4, stage_1-4, plate
      time: 1.8               # seconds (0.1-5.0)
      hf_damp: 0.4            # 0.0-1.0 (high frequency damping)
      feedback: 0.5           # 0.0-0.95 (reverberation feedback)
      level: 0.3              # 0.0-1.0 (wet level)
      pre_delay: 0.02         # seconds (0.0-0.1)
      room_size: 0.8          # 0.0-1.0
      diffusion: 0.7          # 0.0-1.0
    
    chorus:
      type: "chorus_2"        # chorus_1-2, celeste_1-2, flanger_1-2
      lfo_rate: 1.0           # Hz (0.125-8.0)
      lfo_depth: 0.7          # 0.0-1.0
      feedback: 0.2           # -1.0 to 1.0
      send_level: 0.3         # 0.0-1.0
      delay_time: 0.025       # seconds (0.005-0.050)
      phase_difference: 90    # degrees (0-180)
  
  # Variation Effects (per-part)
  variation_effects:
    part_1:
      type: "auto_wah"        # Type 10: Auto Wah
      parameters:
        cutoff_frequency: 1000  # Hz (50-5000)
        resonance: 0.8          # 0.0-1.0
        modulation_rate: 2.5    # Hz (0.1-10.0)
        depth: 0.6              # 0.0-1.0
        manual: 0.5             # 0.0-1.0
        send_level: 0.4         # 0.0-1.0

    part_2:
      type: "phaser_1"          # Type 8: 4-stage phaser
      parameters:
        rate: 0.8               # Hz (0.1-5.0)
        depth: 0.5              # 0.0-1.0
        feedback: 0.7           # -0.95 to 0.95
        stages: 4               # 2-12
        manual: 0.5             # 0.0-1.0
        send_level: 0.3         # 0.0-1.0

    part_3:
      type: "delay_lcr"         # Type 13: LCR Delay
      parameters:
        left_delay: 0.250       # seconds (0.001-2.0)
        center_delay: 0.125     # seconds (0.001-2.0)
        right_delay: 0.375      # seconds (0.001-2.0)
        feedback: 0.3           # 0.0-0.95
        hf_damp: 0.5            # 0.0-1.0
        level: 0.2              # 0.0-1.0

    part_4:
      type: "rotary_speaker"    # Type 11: Rotary Speaker
      parameters:
        rate: 0.5               # Hz (0.1-10.0)
        depth: 0.7              # 0.0-1.0
        feedback: 0.3           # 0.0-1.0
        drive: 0.5              # 0.0-1.0
        horn_balance: 0.5       # 0.0-1.0
        send_level: 0.6         # 0.0-1.0
  
  # Insertion Effects (3 per part)
  insertion_effects:
    part_1:
      insertion_1:
        type: "distortion"      # Type 0: Distortion
        parameters:
          drive: 0.6            # 0.0-1.0
          level: 0.8            # 0.0-1.0
          tone: 0.5             # 0.0-1.0
          presence: 0.3         # 0.0-1.0
      insertion_2:
        type: "compressor"      # Type 1: Compressor
        parameters:
          threshold: -12        # dB (-40 to 0)
          ratio: 4              # 1:1 to 20:1
          attack: 0.01          # seconds (0.001-0.1)
          release: 0.1          # seconds (0.01-1.0)
          gain: 3               # dB (-20 to +20)
          knee: 2               # dB (0-20)
      insertion_3:
        type: "6band_eq"        # Type 2: 6-Band EQ
        parameters:
          low_gain: 2           # dB (-20 to +20)
          low_freq: 80          # Hz (20-400)
          low_mid_gain: 1       # dB (-20 to +20)
          low_mid_freq: 250     # Hz (100-1000)
          mid_gain: 0           # dB (-20 to +20)
          mid_freq: 1000        # Hz (200-5000)
          high_mid_gain: -1     # dB (-20 to +20)
          high_mid_freq: 3000   # Hz (500-10000)
          high_gain: -2         # dB (-20 to +20)
          high_freq: 8000       # Hz (1000-20000)

    part_2:
      insertion_1:
        type: "chorus"          # Type 4: Chorus
        parameters:
          rate: 0.8             # Hz (0.1-10.0)
          depth: 0.5            # 0.0-1.0
          feedback: 0.2         # -0.95 to 0.95
          level: 0.4            # 0.0-1.0
          delay_time: 0.025     # seconds (0.005-0.05)
          phase_diff: 90        # degrees (0-180)
      insertion_2:
        type: "phaser"          # Type 6: Phaser
        parameters:
          rate: 0.8             # Hz (0.1-5.0)
          depth: 0.6            # 0.0-1.0
          feedback: 0.5         # -0.95 to 0.95
          level: 0.4            # 0.0-1.0
          stages: 4             # 2-12
          manual: 0.5           # 0.0-1.0
      insertion_3:
        type: "limiter"         # Type 11: Limiter
        parameters:
          threshold: -6         # dB (-40 to 0)
          ratio: 1000           # ∞:1 limiting
          attack: 0.001         # seconds (0.001-0.1)
          release: 0.05         # seconds (0.01-1.0)
          gain: 0               # dB (-20 to +20)
          knee: 0               # dB (0-20)

    part_3:
      insertion_1:
        type: "guitar_amp"      # Type 10: Guitar Amp Simulator
        parameters:
          drive: 0.6            # 0.0-1.0
          amp_type: "fender"    # fender/jmarshall/vox/acoustic
          tone: 0.5             # 0.0-1.0
          presence: 0.3         # 0.0-1.0
          level: 0.8            # 0.0-1.0
          cab_type: "open"      # open/closed
      insertion_2:
        type: "delay"           # Type 3: Delay
        parameters:
          delay_time: 0.3       # seconds (0.001-2.0)
          feedback: 0.4         # 0.0-0.95
          level: 0.5            # 0.0-1.0
          hf_damp: 0.3          # 0.0-1.0
          pan: 0.0              # -1.0 to 1.0
      insertion_3:
        type: "tremolo"         # Type 8: Tremolo
        parameters:
          rate: 4.0             # Hz (0.1-10.0)
          depth: 0.5            # 0.0-1.0
          waveform: "sine"      # sine/triangle/square
          level: 0.5            # 0.0-1.0
          phase: 0              # degrees (0-360)

# In time-bound sequences
- track:
    channel: 1
    events:
      - at:
          time: 0.0
          # Change system effects
          system_exclusive:
            manufacturer: "yamaha"
            model: "xg"
            command: "parameter_change"
            address: 0x100010
            values:
              reverb_type: "hall_2"
              chorus_type: "chorus_2"
              master_volume: 127
              reverb_time: 1.8
              chorus_depth: 0.7

### Effect Parameter Control via NRPN

XG effects are controlled via NRPN messages. Each effect type has specific parameter mappings:

#### System Effects NRPN (MSB 1-2)
- **MSB 1**: System Reverb Parameters
  - LSB 0: Reverb Type (0-12)
  - LSB 2: Reverb Time (0-127)
  - LSB 4: HF Damp (0-127)
  - LSB 6: Feedback (0-127)

- **MSB 2**: System Chorus Parameters
  - LSB 0: Chorus Type (0-5)
  - LSB 2: LFO Rate (0-127)
  - LSB 4: LFO Depth (0-127)
  - LSB 6: Feedback (0-127)

#### Variation Effects NRPN (MSB 3)
- **LSB 0**: Variation Type Selection (0-14)
- **LSB 1**: Parameter 1 (Rate/Time) - varies by effect type
- **LSB 2**: Parameter 2 (Depth) - 0-127
- **LSB 3**: Parameter 3 (Feedback) - 0-127, signed for some effects
- **LSB 4**: Parameter 4 (Sensitivity/Q) - varies by effect type

#### Insertion Effects NRPN (MSB 4-6)
- **MSB 4**: Insertion Effect 1 Parameters
- **MSB 5**: Insertion Effect 2 Parameters
- **MSB 6**: Insertion Effect 3 Parameters
  - LSB 0: Effect Type (0-11)
  - LSB 1-32: Effect-specific parameters (varies by type)

```yaml
# Example: Controlling variation effect parameters via NRPN
channel_parameters:
  channel_1:
    # Set variation effect to Auto Wah (type 10)
    variation_type: 10

    # Auto Wah parameters
    variation_param_1: 64    # Cutoff frequency (MSB 3 LSB 1)
    variation_param_2: 102   # Resonance (MSB 3 LSB 2)
    variation_param_3: 76    # Modulation rate (MSB 3 LSB 3)
    variation_param_4: 77    # Depth (MSB 3 LSB 4)
```
```

## Time-Bound Message Sequences

### Basic Structure

```yaml
sequences:
  sequence_name:
    tempo: 120                 # BPM for this sequence
    time_signature: "4/4"      # Musical time signature
    start_time: 0.0           # Sequence start time
    quantization: "1/8"       # Note timing quantization
    
    # Track definitions
    - track:
        channel: 1            # MIDI channel (1-16)
        
        # Default parameters applied at time 0
        parameters:
          volume: 100
          pan: "center"
          expression: 127
          # ... other parameters
        
        # Time-stamped events
        events:
          - at:
              time: 0.0       # Start time in seconds
              # MIDI messages for this timestamp
              program_change: "acoustic_grand_piano"
              volume: 90
              pan: "center"
              note_on: { note: "C4", velocity: 80, duration: 2.0 }
              filter_cutoff: 80
              
          - at:
              time: 1.0
              modulation: { from: 0, to: 100, curve: "exponential", duration: 1.5 }
              pitch_bend: 2000
              
          - at:
              time: 2.0
              note_off: { note: "C4", velocity: 40 }
              system_exclusive:
                manufacturer: "yamaha"
                model: "xg"
                command: "parameter_change"
                address: 0x100010
                values:
                  reverb_type: "hall_2"
```

### Timing Formats

```yaml
# Absolute time (seconds)
time: 0.0                     # Start
time: 1.5                     # 1.5 seconds
time: 3.25                    # 3.25 seconds

# Musical time (measure:beat:tick)
time: "0:0:0"                 # Start of piece
time: "1:2:240"               # Measure 1, beat 2, tick 240
time: "2:1:120"               # Measure 2, beat 1, tick 120

# Relative time
time: "+1.0"                  # 1 second after previous message
time: "-0.5"                  # 0.5 seconds before previous message
time: "++0.25"                # 0.25 seconds after last ++ marker

# Tempo-relative
time: "tempo:1.0"             # 1 tempo unit (quarter note)
time: "tempo:0.5"             # Half a quarter note (eighth note)

# Named markers
time: "mark:verse_start"      # Reference to named marker
```

### Curve Interpolation Types

```yaml
# Linear interpolation
curve: "linear"

# Exponential interpolation
curve: "exponential"

# Waveform curves
curve: "sine_wave"           # Sine wave oscillation
  amplitude: 20              # Value swing amount
  frequency: 1.0             # Cycles per second
  phase: 0.0                 # Starting phase (0-360 degrees)
  
curve: "triangle_wave"       # Triangle wave
  amplitude: 15
  frequency: 0.5
  
curve: "sawtooth"            # Sawtooth wave
  amplitude: 25
  frequency: 2.0
  
curve: "square_wave"         # Square wave
  amplitude: 30
  frequency: 0.8

# Envelope curves
curve: "adsr"                # ADSR envelope
  attack: 0.1                # Attack time (seconds)
  decay: 0.3                 # Decay time
  sustain: 0.7               # Sustain level (0.0-1.0)
  release: 0.5               # Release time
  
curve: "ar"                  # Attack-Release envelope
  attack: 0.2
  release: 0.8
  
curve: "one_shot"            # One-shot envelope
  attack: 0.05
  decay: 0.95
  peak: 1.0

# Musical curves
curve: "crescendo"           # Gradual increase
curve: "diminuendo"          # Gradual decrease
curve: "vibrato"             # Vibrato-like oscillation
  rate: 5.0                  # Vibrato rate in Hz
  depth: 10                  # Vibrato depth
  
curve: "tremolo"             # Amplitude modulation
  rate: 4.0
  depth: 0.5                 # 0.0-1.0
  
curve: "glissando"           # Glide between values
  curve_type: "linear"       # Interpolation for the glide
```

### Advanced Message Types

```yaml
# Chord messages
chord:
  notes: ["C4", "E4", "G4", "B4"]  # Note names or numbers
  velocity: 80
  duration: 2.0
  voicing: "spread"                 # spread, close, drop2, drop3
  articulation: "legato"

# Scale-based patterns
scale_run:
  scale: "major"                     # Scale type
  key: "C"                           # Musical key
  start_note: "C4"                   # Starting note
  direction: "ascending"             # ascending, descending
  octave_range: [4, 6]               # Octave range
  rhythm: "eighths"                  # Note duration pattern
  duration: 4.0                      # Total duration

# Drum patterns
drum_pattern:
  pattern: "basic_rock"              # Pre-defined pattern
  tempo_factor: 1.0                  # Timing multiplier
  velocity_factor: 1.0               # Velocity multiplier
  humanize: 0.01                     # Timing variation

# Conditional messages
filter_cutoff:
  if: "previous_velocity > 100"
  then: 96                          # Bright for loud notes
  else: 64                          # Natural for soft notes
  curve: "instant"

# Modulation mapping
modulation_mapping:
  source: "mod_wheel"
  destination: "lfo1_depth"
  amount: 1.0
  curve: "complementary"            # Inverse relationship
```

## System Exclusive Messages

### XG System Exclusive Structure

```yaml
system_exclusive:
  manufacturer: "yamaha"        # or 0x43
  model: "xg"                   # or 0x4C
  device_id: 0                  # 0-127
  commands:
    - command: "bulk_dump"      # bulk_dump, parameter_change, request
      address: 0x100000         # XG system area address
      data_size: 256            # For bulk dump
      data: [0x10, 0x00, 0x10, 0x20]  # Raw data bytes
      
    - command: "parameter_change"
      address: 0x100010         # System parameters address
      values:
        reverb_type: "hall_1"   # XG parameter values
        chorus_type: "chorus_1"
        master_volume: 127
        reverb_time: 1.2
        chorus_depth: 0.5
        
    - command: "request"
      address: 0x100000         # Address to request data from
      size: 256                 # Size of data to request
```

### XG System Exclusive Addresses

| Address Range | Function |
|---------------|----------|
| 0x100000-0x10001F | System Parameters |
| 0x100020-0x10003F | System Effect 1 (Reverb) |
| 0x100040-0x10005F | System Effect 2 (Chorus) |
| 0x100060-0x10007F | System Effect 3 (Variation) |
| 0x100080-0x1000FF | System Effect Common |
| 0x100100-0x1001FF | Part Parameters (16 parts) |
| 0x200000-0x2000FF | Drum Kit Parameters |
| 0x200100-0x2001FF | Drum Kit Common |

### XG System Parameters

| Address | Parameter | Values |
|---------|-----------|--------|
| 0x100010 | Reverb Type | 0-7 (hall_1, hall_2, hall_3, hall_4, room_1, room_2, room_3, room_4, stage_1, stage_2, stage_3, stage_4, plate) |
| 0x100011 | Chorus Type | 0-7 (chorus_1, chorus_2, celeste_1, celeste_2, flanger_1, flanger_2) |
| 0x100012 | Variation Type | 0-15 (various effect types) |
| 0x100013 | Master Volume | 0-127 |
| 0x100014 | Master Key Shift | 0-24 (semitones, 12=center) |
| 0x100015 | Master Pitch Shift | -24 to +24 (semitones) |

### System Exclusive Usage

```yaml
# In static configuration
system_exclusive:
  manufacturer: "yamaha"
  model: "xg"
  device_id: 0
  commands:
    - command: "bulk_dump"
      address: 0x100000     # XG system area
      data_size: 256
    - command: "parameter_change"
      address: 0x100010     # System parameters
      values:
        reverb_type: "hall_1"
        chorus_type: "chorus_1"
        master_volume: 127

# In time-bound sequences
- track:
    channel: 1
    events:
      - at:
          time: 2.0
          system_exclusive:
            manufacturer: "yamaha"
            model: "xg"
            command: "parameter_change"
            address: 0x100010
            values:
              reverb_type: "hall_2"
              chorus_type: "chorus_2"
              master_volume: 120
              reverb_time: 1.8
              chorus_depth: 0.7
```

## Advanced Features

### Modulation Routing

```yaml
modulation_routing:
  channel_1:
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 50          # cents
        polarity: "positive"
      - source: "lfo2"
        destination: "filter_cutoff"
        amount: 30
        polarity: "positive"
      - source: "velocity"
        destination: "amplitude"
        amount: 0.8
        velocity_sensitivity: 0.5
      - source: "mod_wheel"
        destination: "lfo1_depth"
        amount: 1.0
        polarity: "positive"
      - source: "aftertouch"
        destination: "filter_cutoff"
        amount: 0.6
        polarity: "positive"
    
    # Advanced modulation patterns
    modulation_patterns:
      vibrato_sweep:
        - source: "lfo1"
          destination: "pitch"
          amount: [0, 25, 50, 25, 0]  # Time-based sweep
          time_points: [0, 1, 2, 3, 4]  # seconds
      
      filter_sweep:
        - source: "lfo2"
          destination: "filter_cutoff"
          amount: [0, 50, 0, -50, 0]  # Bidirectional sweep
          time_points: [0, 0.5, 1, 1.5, 2]
```

### Performance Macros

```yaml
advanced_features:
  macros:
    create_vibrato_channel:
      - type: "create_channel"
        channel: 16
        program: "vibrato_synth"
      - type: "set_modulation"
        source: "lfo1"
        destination: "pitch"
        amount: 100
      - type: "set_controller_assignment"
        controller: "mod_wheel"
        assignment: "lfo_depth"
    
    create_ambient_pad:
      - type: "create_channel"
        channel: 17
        program: "synth_pad"
      - type: "set_filter"
        cutoff: 40
        resonance: 30
      - type: "set_lfo"
        lfo1:
          speed: 15
          delay: 2000
          fade_time: 3000
      - type: "set_effects_sends"
        reverb: 80
        chorus: 50
        variation: 30

  # MIDI sequence generation
  sequences:
    chord_progression:
      - type: "note_sequence"
        channel: 1
        notes: ["C4", "E4", "G4", "C5"]
        velocity: 80
        duration: 2.0
        timing: 0.0
      - type: "control_change_sequence"
        channel: 1
        controller: "modulation"
        values: [0, 25, 50, 75, 100, 75, 50, 25, 0]
        timing: 0.0
        duration: 4.0
  
  # Conditional logic
  conditional_logic:
    velocity_sensitive_filter:
      - condition: "velocity > 100"
        action: "set_filter_cutoff"
        value: 90
      - condition: "velocity < 50"
        action: "set_filter_cutoff"
        value: 40
      - condition: "velocity >= 50 and velocity <= 100"
        action: "set_filter_cutoff"
        value: 65
  
  # Automation curves
  automation:
    filter_sweep:
      - parameter: "filter_cutoff"
        curve: "linear"
        start_value: 30
        end_value: 100
        duration: 4.0
        loop: true
    
    volume_fade:
      - parameter: "volume"
        curve: "exponential"
        start_value: 0
        end_value: 100
        duration: 2.0
        delay: 1.0
```

### Preset Configurations

```yaml
presets:
  # Instrument-specific presets
  instruments:
    bright_piano:
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
    
    warm_strings:
      channel_2:
        program: "string_ensemble_1"
        filter:
          cutoff: 60
          resonance: 40
        amplifier:
          envelope:
            attack: 80
            decay: 60
            sustain: 85
            release: 70
        lfo:
          lfo1:
            speed: 40
            pitch_depth: 5
            delay: 20
        effects_sends:
          reverb: 70
          chorus: 30
          variation: 20
    
    aggressive_bass:
      channel_3:
        program: "electric_bass_finger"
        filter:
          cutoff: 50
          resonance: 90
        amplifier:
          envelope:
            attack: 70
            decay: 50
            sustain: 60
            release: 40
        pitch:
          bend_range: 12
        effects_sends:
          reverb: 20
          chorus: 10
          variation: 40
  
  # Complete arrangement presets
  arrangements:
    jazz_combo:
      channel_1: "bright_piano"
      channel_2: "warm_strings"
      channel_3: "aggressive_bass"
      channel_9: "jazz_drums"
      effects:
        system_effects:
          reverb:
            type: "room_2"
            time: 1.2
            level: 0.4
          chorus:
            type: "chorus_2"
            lfo_depth: 0.5
            send_level: 0.3
    
    rock_band:
      channel_1: "bright_piano"
      channel_3: "aggressive_bass"
      channel_9: "rock_drums"
      effects:
        system_effects:
          reverb:
            type: "hall_3"
            time: 2.5
            level: 0.5
          chorus:
            type: "flanger_1"
            lfo_depth: 0.8
            send_level: 0.2
        variation_effects:
          channel_1:
            type: "distortion"
            parameters:
              drive: 0.7
              level: 0.8
```

## Complete Examples

### Basic Piano Setup

```yaml
xg_dsl_version: "1.0"
description: "Basic piano configuration"

basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      control_changes:
        volume: 100
        pan: "center"
        expression: 127

channel_parameters:
  channel_1:
    filter:
      cutoff: 80
      resonance: 60
    amplifier:
      envelope:
        attack: 90
        decay: 40
        sustain: 70
        release: 60
    effects_sends:
      reverb: 50
      chorus: 20

modulation_routing:
  channel_1:
    routes:
      - source: "lfo1"
        destination: "pitch"
        amount: 10
      - source: "velocity"
        destination: "amplitude"
        amount: 0.8
```

### Jazz Combo with Time-Bound Sequences

```yaml
xg_dsl_version: "1.0"
description: "Jazz combo arrangement with time-bound sequences"
tempo: 140
time_signature: "4/4"

sequences:
  jazz_combo:
    - track:
        channel: 1              # Piano
        parameters:
          volume: 100
          pan: "center"
          filter_cutoff: 80
          reverb_send: 50
          chorus_send: 20
          
        events:
          - at:
              time: 0.0
              program_change: "acoustic_grand_piano"
              chord:
                notes: ["C4", "E4", "G4", "B4"]
                velocity: 80
                duration: 2.0
                voicing: "spread"
              modulation: { from: 0, to: 75, curve: "exponential", duration: 1.5 }
              
          - at:
              time: 1.0
              filter_cutoff: { from: 80, to: 96, curve: "sine_wave", duration: 2.0, amplitude: 16 }
              
          - at:
              time: 2.0
              chord:
                notes: ["A3", "C4", "E4", "G4"]
                velocity: 75
                duration: 2.0
                
          - at:
              time: 4.0
              system_exclusive:
                manufacturer: "yamaha"
                model: "xg"
                command: "parameter_change"
                address: 0x100010
                values:
                  reverb_type: "room_2"
                  chorus_type: "chorus_2"
                  
    - track:
        channel: 9              # Drums
        parameters:
          volume: 105
          bank_msb: 126
          
        events:
          - at:
              time: 0.0
              program_change: "standard_drum_kit"
              kick: { note: 36, velocity: 100, duration: 0.5 }
              snare: { note: 38, velocity: 95, duration: 0.3 }
              hihat_closed: { note: 42, velocity: 70, duration: 0.25 }
              
          - at:
              time: 1.0
              snare: { note: 38, velocity: 100, accent: true }
              
          - at:
              time: 3.75
              hihat_open: { note: 46, velocity: 85, duration: 0.5 }
```

### Electronic Music Production

```yaml
xg_dsl_version: "1.0"
description: "Electronic music with advanced synthesis"
tempo: 128
time_signature: "4/4"

sequences:
  electronic_track:
    - track:
        channel: 1              # Lead synth
        parameters:
          volume: 90
          pan: "center"
          filter_cutoff: 60
          filter_resonance: 80
          filter_type: "lowpass"
          amp_attack: 30
          amp_decay: 60
          amp_sustain: 70
          amp_release: 40
          lfo1_speed: 40
          lfo1_waveform: "sawtooth"
          lfo1_pitch_depth: 30
          reverb_send: 30
          chorus_send: 50
          
        events:
          - at:
              time: 0.0
              program_change: "lead_2_sawtooth"
              # Opening arpeggio
              note_on: { note: "C4", velocity: 100, duration: 0.5 }
              note_on: { note: "E4", velocity: 95, duration: 0.5, delay: 0.125 }
              note_on: { note: "G4", velocity: 90, duration: 0.5, delay: 0.25 }
              note_on: { note: "B4", velocity: 85, duration: 1.0, delay: 0.375 }
              
          - at:
              time: 1.0
              # Filter sweep with LFO
              filter_cutoff: { from: 60, to: 100, curve: "sine_wave", duration: 4.0, amplitude: 40, frequency: 0.5 }
              lfo1_pitch_depth: { from: 30, to: 80, curve: "exponential", duration: 2.0 }
              
          - at:
              time: 2.0
              # Modulation wheel control
              modulation: { from: 0, to: 127, curve: "linear", duration: 1.0 }
              
          - at:
              time: 4.0
              # Change effects
              system_exclusive:
                manufacturer: "yamaha"
                model: "xg"
                command: "parameter_change"
                address: 0x100010
                values:
                  reverb_type: "hall_3"
                  chorus_type: "flanger_1"
                  master_volume: 127
```

## XG Effects Architecture Overview

### Signal Flow
```
Input → Insertion Effects (3 slots) → Variation Effect → System Effects → Output
       ↓                              ↓                    ↓
   Per-Part Processing           Per-Part Processing   Shared Processing
```

### Effects Categories

#### System Effects (Shared Across All Parts)
- **Reverb**: 13 types (Hall 1-4, Room 1-4, Stage 1-4, Plate)
- **Chorus**: 6 types (Chorus 1-2, Celeste 1-2, Flanger 1-2)
- Controlled via NRPN MSB 1-2

#### Variation Effects (Per-Part, 15 Types)
- **Chorus/Celeste**: 6 types for modulation effects
- **Flanger/Phaser**: 4 types for filtering effects
- **Auto Wah**: Envelope-followed filter sweep
- **Rotary Speaker**: Classic rotating speaker simulation
- **Tremolo**: Amplitude modulation
- **Delay LCR/LR**: Stereo delay effects
- Controlled via NRPN MSB 3

#### Insertion Effects (Per-Part, 3 Slots × 12 Types)
- **Distortion**: 4 parameters (drive, level, tone, presence)
- **Dynamics**: Compressor (6 params), Limiter (6 params)
- **EQ**: 6-band parametric equalizer (10 params)
- **Delay**: Mono delay with feedback (5 params)
- **Modulation**: Chorus, Flanger, Phaser, Tremolo (4-6 params each)
- **Specialized**: Auto Wah, Rotary Speaker, Guitar Amp (5-6 params each)
- Controlled via NRPN MSB 4-6

### Parameter Control Methods

#### Static Configuration (YAML)
```yaml
effects:
  system_effects:
    reverb:
      type: "hall_2"
      time: 1.8
      hf_damp: 0.4
    chorus:
      type: "chorus_2"
      lfo_rate: 1.0

  variation_effects:
    part_1:
      type: "auto_wah"
      parameters:
        cutoff_frequency: 1000
        resonance: 0.8

  insertion_effects:
    part_1:
      insertion_1:
        type: "distortion"
        parameters:
          drive: 0.6
          tone: 0.5
```

#### Dynamic Control (NRPN Messages)
- System Effects: NRPN MSB 1-2
- Variation Effects: NRPN MSB 3
- Insertion Effects: NRPN MSB 4-6
- Real-time parameter changes during performance

#### Time-Bound Sequences
```yaml
sequences:
  - track:
      channel: 1
      events:
        - at:
            time: 2.0
            system_exclusive:
              manufacturer: "yamaha"
              model: "xg"
              command: "parameter_change"
              address: 0x100012  # Variation type
              values:
                variation_type: 10  # Auto Wah
```

### XG Effects Feature Set

✅ **Complete Implementation**:
- 2 System Effects × 19 total types
- 15 Variation Effects with full parameter control
- 12 Insertion Effects × 3 slots per part
- 200+ individual effect parameters
- NRPN-based real-time control
- Full MIDI XG specification compliance

This comprehensive specification provides complete coverage of all MIDI controllers, RPNs, NRPNs, drum parameters, effect parameters, and constructs supported by the XG MIDI DSL. The language provides an intuitive, human-readable interface while maintaining full compatibility with the sophisticated XG synthesizer infrastructure.