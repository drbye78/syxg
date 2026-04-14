# S.Art2 NRPN Mapping Guide

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-23

---

## Table of Contents

1. [NRPN Basics](#nrpn-basics)
2. [Articulation NRPN (MSB 1-13)](#articulation-nrpn-msb-1-13)
3. [Parameter NRPN (MSB 0-10)](#parameter-nrpn-msb-0-10)
4. [Complete Mapping Table](#complete-mapping-table)
5. [Examples](#examples)

---

## NRPN Basics

### **What is NRPN?**

NRPN (Non-Registered Parameter Number) is a MIDI message type that allows control of synthesizer parameters beyond standard MIDI controllers.

### **NRPN Message Format**

```
CC 99 (NRPN MSB) = Parameter Number MSB (0-127)
CC 98 (NRPN LSB) = Parameter Number LSB (0-127)
CC 6 (Data MSB)  = Value MSB (0-127)
CC 38 (Data LSB) = Value LSB (0-127)
```

### **Value Calculation**

```python
# Combine MSB/LSB to get 14-bit value
value = (msb << 7) | lsb  # Range: 0-16383

# Split value to MSB/LSB
msb = value >> 7
lsb = value & 0x7F
```

### **NRPN Message Sequence**

```
1. Send NRPN MSB (CC 99)
2. Send NRPN LSB (CC 98)
3. Send Data MSB (CC 6) - optional
4. Send Data LSB (CC 38) - optional
```

**Example: Set legato (MSB 1, LSB 1)**

```python
# MIDI messages
send_cc(99, 1)   # NRPN MSB = 1
send_cc(98, 1)   # NRPN LSB = 1
send_cc(6, 0)    # Data MSB = 0 (optional)
send_cc(38, 0)   # Data LSB = 0 (optional)
```

---

## Articulation NRPN (MSB 1-13)

### **MSB 1: Common Articulations (50 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | normal | Default articulation |
| 1 | legato | Smooth transitions |
| 2 | staccato | Short, detached |
| 3 | bend | Pitch bend |
| 4 | vibrato | Vibrato modulation |
| 5 | breath | Breath controller |
| 6 | glissando | Glissando slide |
| 7 | growl | Growl effect |
| 8 | flutter | Flutter tongue |
| 9 | trill | Trill effect |
| 10 | pizzicato | Plucked strings |
| 11 | grace | Grace note |
| 12 | shake | Shake effect |
| 13 | fall | Fall effect |
| 14 | doit | Doit (rise) effect |
| 15 | tongue_slap | Tongue slap |
| 16 | harmonics | Harmonics |
| 17 | hammer_on | Hammer-on |
| 18 | pull_off | Pull-off |
| 19 | key_off | Key-off noise |
| 20 | marcato | Marcato (accented) |
| 21 | detache | Detaché |
| 22 | sul_ponticello | Sul ponticello |
| 23 | scoop | Scoop effect |
| 24 | rip | Rip effect |
| 25 | portamento | Portamento slide |
| 26 | swell | Swell effect |
| 27 | accented | Accented |
| 28 | bow_up | Up-bow |
| 29 | bow_down | Down-bow |
| 30 | col_legno | Col legno |
| 31 | up_bend | Upward bend |
| 32 | down_bend | Downward bend |
| 33 | smear | Smear effect |
| 34 | flip | Flip effect |
| 35 | straight | Straight (no vibrato) |
| 36 | tenuto | Tenuto |
| 37 | non_vibrato | Non vibrato |
| 38 | molto_vibrato | Molto vibrato |
| 39 | sub_tone | Sub-tone |
| 40 | air_noise | Air noise |
| 41 | key_click | Key click |
| 42 | attack_noise | Attack noise |
| 43 | release_noise | Release noise |
| 44 | finger_noise | Finger noise |
| 45 | bow_noise | Bow noise |
| 46 | fret_noise | Fret noise |
| 47 | slide_noise | Slide noise |
| 48 | body_hit | Body hit |
| 49 | mute | Mute |

### **MSB 2: Dynamics (15 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | ppp | Pianississimo (very very soft) |
| 1 | pp | Pianissimo (very soft) |
| 2 | p | Piano (soft) |
| 3 | mp | Mezzo-piano (moderately soft) |
| 4 | mf | Mezzo-forte (moderately loud) |
| 5 | f | Forte (loud) |
| 6 | ff | Fortissimo (very loud) |
| 7 | fff | Fortississimo (very very loud) |
| 8 | crescendo | Gradually louder |
| 9 | diminuendo | Gradually softer |
| 10 | sfz | Sforzando (sudden accent) |
| 11 | rfz | Rinforzando (reinforced) |
| 12 | fp | Forte-piano |
| 13 | rf | Rinforzando |
| 14 | sfp | Sforzando-piano |

### **MSB 3: Wind - Saxophone (25 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | growl_wind | Growl (wind) |
| 1 | flutter_wind | Flutter tongue (wind) |
| 2 | tongue_slap_wind | Tongue slap (wind) |
| 3 | smear_wind | Smear (wind) |
| 4 | flip_wind | Flip (wind) |
| 5 | scoop_wind | Scoop (wind) |
| 6 | rip_wind | Rip (wind) |
| 7 | double_tongue | Double tonguing |
| 8 | triple_tongue | Triple tonguing |
| 9 | sub_tone_sax | Sub-tone (sax) |
| 10 | key_click_sax | Key click (sax) |
| 11 | breath_noise_sax | Breath noise (sax) |
| 12 | lip_trill_sax | Lip trill (sax) |
| 13 | bend_up_sax | Bend up (sax) |
| 14 | bend_down_sax | Bend down (sax) |
| 15 | glissando_up_sax | Glissando up (sax) |
| 16 | glissando_down_sax | Glissando down (sax) |
| 17 | fall_sax | Fall (sax) |
| 18 | doit_sax | Doit (sax) |
| 19 | plop_sax | Plop (sax) |
| 20 | lift_sax | Lift (sax) |
| 21 | smooth_fall_sax | Smooth fall (sax) |
| 22 | rough_fall_sax | Rough fall (sax) |
| 23 | long_fall_sax | Long fall (sax) |
| 24 | bite_sax | Bite (sax) |

### **MSB 4: Wind - Brass (20 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | muted_brass | Muted brass |
| 1 | cup_mute | Cup mute |
| 2 | harmon_mute | Harmon mute |
| 3 | stopped | Stopped |
| 4 | scoop_brass | Scoop (brass) |
| 5 | lip_trill | Lip trill |
| 6 | shake_brass | Shake (brass) |
| 7 | drop_brass | Drop (brass) |
| 8 | doit_brass | Doit (brass) |
| 9 | fall_brass | Fall (brass) |
| 10 | scoop_brass_long | Scoop long (brass) |
| 11 | plop_brass | Plop (brass) |
| 12 | lift_brass | Lift (brass) |
| 13 | smooth_fall_brass | Smooth fall (brass) |
| 14 | rough_fall_brass | Rough fall (brass) |
| 15 | long_fall_brass | Long fall (brass) |
| 16 | straight_mute | Straight mute |
| 17 | plunger_mute | Plunger mute |
| 18 | bucket_mute | Bucket mute |
| 19 | hat_mute | Hat mute |

### **MSB 5: Wind - Woodwind (18 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | hammer_on_guitar | Hammer-on (guitar) |
| 1 | pull_off_guitar | Pull-off (guitar) |
| 2 | harmonics_guitar | Harmonics (guitar) |
| 3 | palm_mute | Palm mute |
| 4 | tap | Tap |
| 5 | slide_up | Slide up |
| 6 | slide_down | Slide down |
| 7 | bend | Bend |
| 8 | flutter_tongue | Flutter tongue |
| 9 | double_tongue_ww | Double tonguing (ww) |
| 10 | triple_tongue_ww | Triple tonguing (ww) |
| 11 | key_click_ww | Key click (ww) |
| 12 | breath_ww | Breath (ww) |
| 13 | air_ww | Air (ww) |
| 14 | overblow | Overblow |
| 15 | harmonic_ww | Harmonic (ww) |
| 16 | pizzicato_ww | Pizzicato (ww) |
| 17 | staccato_ww | Staccato (ww) |

### **MSB 6: Strings - Bow (22 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | pizzicato_strings | Pizzicato strings |
| 1 | harmonics_strings | Harmonics strings |
| 2 | sul_ponticello_strings | Sul ponticello strings |
| 3 | bow_up_strings | Up-bow strings |
| 4 | bow_down_strings | Down-bow strings |
| 5 | col_legno_strings | Col legno strings |
| 6 | portamento_strings | Portamento strings |
| 7 | spiccato | Spiccato |
| 8 | tremolando | Tremolando |
| 9 | sautille | Sautillé |
| 10 | martele | Martelé |
| 11 | ricochet | Ricochet |
| 12 | flautando | Flautando |
| 13 | sul_g | Sul G |
| 14 | con_sordino | Con sordino |
| 15 | senza_sordino | Senza sordino |
| 16 | tremolo | Tremolo |
| 17 | tremolo_sordino | Tremolo sordino |
| 18 | portamento_fast | Portamento fast |
| 19 | portamento_slow | Portamento slow |
| 20 | sul_tasto | Sul tasto |
| 21 | punto | Punto |

### **MSB 7: Strings - Pluck (15 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | pizzicato_snap | Pizzicato snap |
| 1 | pizzicato_left | Pizzicato left hand |
| 2 | pizzicato_right | Pizzicato right hand |
| 3 | pizzicato_chord | Pizzicato chord |
| 4 | barto_k | Bartók pizzicato |
| 5 | gyro_pizz | Gyro pizzicato |
| 6 | harmonic_pizz | Harmonic pizzicato |
| 7 | muted_pizz | Muted pizzicato |
| 8 | vibrato_pizz | Vibrato pizzicato |
| 9 | gliss_pizz | Glissando pizzicato |
| 10 | thumb_pizz | Thumb pizzicato |
| 11 | slap_pizz | Slap pizzicato |
| 12 | pop_pizz | Pop pizzicato |
| 13 | tap_pizz | Tap pizzicato |
| 14 | scratch_pizz | Scratch pizzicato |

### **MSB 8: Guitar (25 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | slide_up_gtr | Slide up (guitar) |
| 1 | slide_down_gtr | Slide down (guitar) |
| 2 | bend_gtr | Bend (guitar) |
| 3 | bend_release_gtr | Bend release (guitar) |
| 4 | pre_bend | Pre-bend |
| 5 | harmonics_natural | Natural harmonics |
| 6 | harmonics_artificial | Artificial harmonics |
| 7 | harmonics_pinch | Pinch harmonics |
| 8 | tapping_gtr | Tapping (guitar) |
| 9 | slap_gtr | Slap (guitar) |
| 10 | pop_gtr | Pop (guitar) |
| 11 | mute_gtr | Mute (guitar) |
| 12 | cut_noise | Cut noise |
| 13 | fret_noise | Fret noise |
| 14 | string_noise | String noise |
| 15 | body_hit_gtr | Body hit (guitar) |
| 16 | hammer_on_gtr | Hammer-on (guitar) |
| 17 | pull_off_gtr | Pull-off (guitar) |
| 18 | vibrato_gtr | Vibrato (guitar) |
| 19 | wide_vibrato | Wide vibrato |
| 20 | palm_mute_gtr | Palm mute (guitar) |
| 21 | harmonic_tap | Harmonic tap |
| 22 | tremolo_gtr | Tremolo (guitar) |
| 23 | arpeggio_up | Arpeggio up |
| 24 | arpeggio_down | Arpeggio down |

### **MSB 9: Vocal (20 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | vocal_breath | Vocal breath |
| 1 | vocal_attack | Vocal attack |
| 2 | vocal_fry | Vocal fry |
| 3 | falsetto | Falsetto |
| 4 | chest_voice | Chest voice |
| 5 | head_voice | Head voice |
| 6 | mixed_voice | Mixed voice |
| 7 | whisper | Whisper |
| 8 | shout | Shout |
| 9 | scream | Scream |
| 10 | growl_vocal | Growl (vocal) |
| 11 | vibrato_vocal | Vibrato (vocal) |
| 12 | straight_tone | Straight tone |
| 13 | scoop_vocal | Scoop (vocal) |
| 14 | fall_vocal | Fall (vocal) |
| 15 | turn_vocal | Turn (vocal) |
| 16 | mordent_vocal | Mordent (vocal) |
| 17 | trill_vocal | Trill (vocal) |
| 18 | glissando_vocal | Glissando (vocal) |
| 19 | portamento_vocal | Portamento (vocal) |

### **MSB 10: Synth (15 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | synth_attack | Synth attack |
| 1 | synth_decay | Synth decay |
| 2 | synth_sustain | Synth sustain |
| 3 | synth_release | Synth release |
| 4 | filter_sweep | Filter sweep |
| 5 | filter_snap | Filter snap |
| 6 | lfo_sync | LFO sync |
| 7 | lfo_free | LFO free |
| 8 | glide | Glide |
| 9 | legato_synth | Legato (synth) |
| 10 | staccato_synth | Staccato (synth) |
| 11 | trig_synth | Trigger (synth) |
| 12 | gate_synth | Gate (synth) |
| 13 | accent_synth | Accent (synth) |
| 14 | tie_synth | Tie (synth) |

### **MSB 11: Percussion (20 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | perc_attack | Percussion attack |
| 1 | perc_decay | Percussion decay |
| 2 | rim_shot | Rim shot |
| 3 | cross_stick | Cross stick |
| 4 | buzz_roll | Buzz roll |
| 5 | press_roll | Press roll |
| 6 | flam | Flam |
| 7 | drag | Drag |
| 8 | ruff | Ruff |
| 9 | diddle | Diddle |
| 10 | bounce | Bounce |
| 11 | dead_stroke | Dead stroke |
| 12 | tap_perc | Tap (percussion) |
| 13 | slap_perc | Slap (percussion) |
| 14 | pop_perc | Pop (percussion) |
| 15 | mute_perc | Mute (percussion) |
| 16 | open_perc | Open (percussion) |
| 17 | closed_perc | Closed (percussion) |
| 18 | choke_perc | Choke (percussion) |
| 19 | sustain_perc | Sustain (percussion) |

### **MSB 12: Ethnic (18 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | ethnic_attack | Ethnic attack |
| 1 | ethnic_decay | Ethnic decay |
| 2 | bend_ethnic | Bend (ethnic) |
| 3 | vibrato_ethnic | Vibrato (ethnic) |
| 4 | tremolo_ethnic | Tremolo (ethnic) |
| 5 | harmonic_ethnic | Harmonic (ethnic) |
| 6 | percussive_ethnic | Percussive (ethnic) |
| 7 | breath_ethnic | Breath (ethnic) |
| 8 | slide_ethnic | Slide (ethnic) |
| 9 | gliss_ethnic | Glissando (ethnic) |
| 10 | trill_ethnic | Trill (ethnic) |
| 11 | mordent_ethnic | Mordent (ethnic) |
| 12 | turn_ethnic | Turn (ethnic) |
| 13 | grace_ethnic | Grace (ethnic) |
| 14 | accent_ethnic | Accent (ethnic) |
| 15 | staccato_ethnic | Staccato (ethnic) |
| 16 | tenuto_ethnic | Tenuto (ethnic) |
| 17 | marcato_ethnic | Marcato (ethnic) |

### **MSB 13: Effects (12 articulations)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | fx_sweep_up | FX sweep up |
| 1 | fx_sweep_down | FX sweep down |
| 2 | fx_noise | FX noise |
| 3 | fx_hit | FX hit |
| 4 | fx_rise | FX rise |
| 5 | fx_fall | FX fall |
| 6 | fx_boom | FX boom |
| 7 | fx_crash | FX crash |
| 8 | fx_slam | FX slam |
| 9 | fx_scrape | FX scrape |
| 10 | fx_click | FX click |
| 11 | fx_pop | FX pop |

---

## Parameter NRPN (MSB 0-10)

### **MSB 0: Vibrato Parameters**

| LSB | Parameter | Range | Description |
|-----|-----------|-------|-------------|
| 0 | rate | 0.0-1.27 Hz | Vibrato rate |
| 1 | depth | 0.0-16.38 | Vibrato depth |
| 2 | delay | 0.0-16.38 sec | Vibrato delay |

### **MSB 1: Legato Parameters**

| LSB | Parameter | Range | Description |
|-----|-----------|-------|-------------|
| 0 | blend | 0.0-1.638 | Legato blend |
| 1 | transition_time | 0.0-0.16 sec | Transition time |

### **MSB 2: Growl Parameters**

| LSB | Parameter | Range | Description |
|-----|-----------|-------|-------------|
| 0 | mod_freq | 0-127 Hz | Modulation frequency |
| 1 | depth | 0.0-1.638 | Growl depth |

---

## Complete Mapping Table

See [`SART2_API_REFERENCE.md`](SART2_API_REFERENCE.md) for complete mapping table.

---

## Examples

### **Python Example**

```python
from synth import ModernXGSynthesizer

synth = ModernXGSynthesizer()

# Set legato via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)

# Set staccato via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=2, value=0)

# Set vibrato rate via parameter NRPN
synth.process_nrpn(channel=0, msb=0, lsb=0, value=64)  # 0.64 Hz
```

### **MIDI Message Example**

```
# Set legato (MSB 1, LSB 1)
B0 63 01  ; CC 99 (NRPN MSB) = 1
B0 62 01  ; CC 98 (NRPN LSB) = 1
B0 06 00  ; CC 6 (Data MSB) = 0
B0 26 00  ; CC 38 (Data LSB) = 0

# Set staccato (MSB 1, LSB 2)
B0 63 01  ; CC 99 (NRPN MSB) = 1
B0 62 02  ; CC 98 (NRPN LSB) = 2
B0 06 00  ; CC 6 (Data MSB) = 0
B0 26 00  ; CC 38 (Data LSB) = 0
```

---

## See Also

- [`SART2_API_REFERENCE.md`](SART2_API_REFERENCE.md) - Complete API reference
- [`SART2_SYSEX_SPEC.md`](SART2_SYSEX_SPEC.md) - SYSEX format specification
- [`SART2_SWITCHING_GUIDE.md`](SART2_SWITCHING_GUIDE.md) - Velocity/Key switching guide

---

**End of NRPN Mapping Guide**
