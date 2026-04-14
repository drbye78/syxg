# S.Art2 User Guide

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-22

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Articulation Basics](#articulation-basics)
4. [NRPN Control](#nrpn-control)
5. [SYSEX Control](#sysex-control)
6. [Instrument-Specific Techniques](#instrument-specific-techniques)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

### **What is S.Art2?**

S.Art2 (Super Articulation 2) is an articulation control system that adds expressive performance techniques to ANY synthesis engine. It's inspired by Yamaha's S.Art2 technology used in Genos and PSR workstations.

### **Key Features**

- ✅ **35+ Articulations** - Legato, staccato, growl, vibrato, and more
- ✅ **Universal Support** - Works with SF2, FM, Additive, Wavetable, Physical, etc.
- ✅ **Real-Time Control** - NRPN/SYSEX messages for live performance
- ✅ **Instrument-Specific** - Wind, strings, guitar, brass techniques
- ✅ **Dynamic Control** - ppp to fff with crescendo/diminuendo

### **How It Works**

```
┌─────────────────────────────────────────┐
│          S.Art2 Wrapper Layer           │
│  ┌─────────────────────────────────┐    │
│  │  Articulation Controller        │    │
│  │  • NRPN/SYSEX processing        │    │
│  │  • Parameter mapping            │    │
│  │  • Sample modification          │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────────┐    │
│  │  Base Region (any engine)       │    │
│  │  • SF2Region                    │    │
│  │  • FMRegion                     │    │
│  │  • AdditiveRegion               │    │
│  │  • etc.                         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

S.Art2 wraps any synthesis region and adds articulation processing on top.

---

## Quick Start

### **1. Create Synthesizer**

```python
from synth import ModernXGSynthesizer

# S.Art2 is enabled by default!
synth = ModernXGSynthesizer()
synth.load_soundfont('piano.sf2')
```

### **2. Set Articulation**

```python
# Method 1: Direct API
synth.set_channel_articulation(0, 'legato')

# Method 2: NRPN (MIDI)
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)
```

### **3. Play Notes**

```python
# Notes now play with articulation
synth.channels[0].note_on(60, 100)  # C4 with legato
```

### **4. Change Articulation**

```python
# Switch articulation during performance
synth.set_channel_articulation(0, 'staccato')
synth.channels[0].note_on(72, 100)  # C5 with staccato
```

---

## Articulation Basics

### **Common Articulations**

| Articulation | Description | Use Case |
|--------------|-------------|----------|
| **normal** | Default sound | General purpose |
| **legato** | Smooth transitions | Legato passages |
| **staccato** | Short, detached | Staccato passages |
| **vibrato** | Pitch modulation | Expressive solos |
| **growl** | Rough texture | Jazz/rock winds |
| **pizzicato** | Plucked strings | String pizzicato |
| **harmonics** | Harmonic overtones | Ethereal sounds |
| **portamento** | Pitch glide | Smooth slides |

### **Setting Articulations**

```python
# By name
synth.set_channel_articulation(0, 'legato')

# By NRPN
synth.process_nrpn(0, 1, 1, 0)  # MSB 1, LSB 1 = legato

# Get current articulation
current = synth.get_channel_articulation(0)
print(f"Current: {current}")  # 'legato'
```

### **Getting Available Articulations**

```python
articulations = synth.get_available_articulations()

print("Available articulations:")
for art in articulations:
    print(f"  - {art}")
```

---

## NRPN Control

### **What is NRPN?**

NRPN (Non-Registered Parameter Number) is a MIDI message type that allows control of synthesizer parameters. S.Art2 uses NRPN for real-time articulation switching.

### **NRPN Message Format**

```
CC 99 (NRPN MSB) = Articulation MSB
CC 98 (NRPN LSB) = Articulation LSB
CC 6 (Data MSB)  = Value (usually 0)
```

### **Common NRPN Mappings**

| MSB | LSB | Articulation |
|-----|-----|--------------|
| 1 | 0 | normal |
| 1 | 1 | legato |
| 1 | 2 | staccato |
| 1 | 4 | vibrato |
| 1 | 7 | growl |
| 1 | 10 | pizzicato |
| 2 | 0 | ppp (very soft) |
| 2 | 5 | f (loud) |

### **Using NRPN**

```python
# Via ModernXGSynthesizer
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)

# Via MIDI (external controller)
# Send CC 99=1, CC 98=1, CC 6=0
```

### **NRPN by Category**

```python
# Common (MSB 1)
synth.process_nrpn(0, 1, 1, 0)  # legato
synth.process_nrpn(0, 1, 2, 0)  # staccato

# Dynamics (MSB 2)
synth.process_nrpn(0, 2, 0, 0)  # ppp
synth.process_nrpn(0, 2, 5, 0)  # f

# Wind (MSB 3)
synth.process_nrpn(0, 3, 0, 0)  # growl_wind
synth.process_nrpn(0, 3, 1, 0)  # flutter_wind

# Strings (MSB 4)
synth.process_nrpn(0, 4, 0, 0)  # pizzicato_strings
synth.process_nrpn(0, 4, 1, 0)  # harmonics_strings

# Guitar (MSB 5)
synth.process_nrpn(0, 5, 0, 0)  # hammer_on_guitar
synth.process_nrpn(0, 5, 3, 0)  # palm_mute
```

---

## SYSEX Control

### **What is SYSEX?**

SYSEX (System Exclusive) messages provide advanced control with parameter settings. Use SYSEX for complex articulation configurations.

### **SYSEX Format**

```
F0 43 10 4C 13 [art_msb] [art_lsb] F7
│  │  │  │  │    │        │       └─ End of SYSEX
│  │  │  │  │    │        └─ Articulation LSB
│  │  │  │  │    └─ Articulation MSB
│  │  │  │  └─ S.Art2 command (0x13 = set articulation)
│  │  │  └─ Sub-status
│  │  └─ Device ID (0x10)
│  └─ Yamaha manufacturer ID (0x43)
└─ Start of SYSEX
```

### **Using SYSEX**

```python
# Build SYSEX for legato
sysex = bytes([0xF0, 0x43, 0x10, 0x4C, 0x13, 0x01, 0x01, 0xF7])

# Process SYSEX
synth.process_sysex(sysex)
```

---

## Instrument-Specific Techniques

### **Wind Instruments**

```python
# Saxophone techniques
synth.set_channel_articulation(0, 'growl_wind')    # Jazz growl
synth.set_channel_articulation(0, 'flutter_wind')  # Flutter tongue
synth.set_channel_articulation(0, 'double_tongue') # Double tonguing

# Trumpet techniques
synth.set_channel_articulation(0, 'muted_brass')   # With mute
synth.set_channel_articulation(0, 'lip_trill')     # Lip trill
```

### **String Instruments**

```python
# Violin techniques
synth.set_channel_articulation(0, 'pizzicato_strings')  # Plucked
synth.set_channel_articulation(0, 'harmonics_strings')  # Harmonics
synth.set_channel_articulation(0, 'spiccato')           # Spiccato
synth.set_channel_articulation(0, 'tremolando')         # Tremolo

# Cello techniques
synth.set_channel_articulation(0, 'bow_up_strings')     # Up-bow
synth.set_channel_articulation(0, 'bow_down_strings')   # Down-bow
```

### **Guitar Techniques**

```python
# Electric guitar
synth.set_channel_articulation(0, 'hammer_on_guitar')   # Hammer-on
synth.set_channel_articulation(0, 'pull_off_guitar')    # Pull-off
synth.set_channel_articulation(0, 'palm_mute')          # Palm mute
synth.set_channel_articulation(0, 'tap')                # Tapping
synth.set_channel_articulation(0, 'slide_up')           # Slide up
```

### **Dynamics**

```python
# Volume levels
synth.set_channel_articulation(0, 'ppp')   # Very very soft
synth.set_channel_articulation(0, 'p')     # Soft
synth.set_channel_articulation(0, 'mf')    # Moderately loud
synth.set_channel_articulation(0, 'f')     # Loud
synth.set_channel_articulation(0, 'fff')   # Very very loud

# Dynamic changes
synth.set_channel_articulation(0, 'crescendo')   # Gradually louder
synth.set_channel_articulation(0, 'diminuendo')  # Gradually softer
```

---

## Advanced Usage

### **Articulation Parameters**

```python
# Get region
region = synth.channels[0].current_voice.get_regions_for_note(60, 100)[0]

# Set vibrato parameters
region.set_articulation('vibrato')
region.set_articulation_param('rate', 6.0)   # Faster vibrato
region.set_articulation_param('depth', 0.08) # Deeper vibrato

# Set legato parameters
region.set_articulation('legato')
region.set_articulation_param('blend', 0.7)        # More crossfade
region.set_articulation_param('transition_time', 0.08)  # Slower transition
```

### **Articulation Chaining**

```python
# Chain articulations for complex expressions
synth.set_channel_articulation(0, 'crescendo')
time.sleep(1.0)  # Wait for crescendo
synth.set_channel_articulation(0, 'vibrato')  # Add vibrato
```

### **Per-Voice Articulation**

```python
# Different articulations for different notes
voice = synth.channels[0].current_voice

# Get regions for specific note/velocity
regions = voice.get_regions_for_note(60, 100)

# Set articulation per region
for region in regions:
    region.set_articulation('legato')
```

### **Custom Articulations**

```python
# Add custom articulation
from synth.xg.sart import ArticulationController

controller = ArticulationController()
controller.articulation_params['my_custom_art'] = {
    'rate': 8.0,
    'depth': 0.15,
    'attack': 0.02
}

# Use custom articulation
synth.set_channel_articulation(0, 'my_custom_art')
```

---

## Troubleshooting

### **Articulation Not Working**

**Problem:** Articulation changes have no effect.

**Solutions:**
1. Check that S.Art2 is enabled:
   ```python
   print(f"S.Art2 enabled: {synth.sart2_factory is not None}")
   ```

2. Verify articulation name:
   ```python
   available = synth.get_available_articulations()
   print(f"Available: {available}")
   ```

3. Check region type:
   ```python
   region = synth.channels[0].current_voice.get_regions_for_note(60, 100)[0]
   print(f"Region type: {type(region).__name__}")
   print(f"S.Art2 enabled: {hasattr(region, 'set_articulation')}")
   ```

### **NRPN Not Working**

**Problem:** NRPN messages don't change articulation.

**Solutions:**
1. Verify NRPN mapper:
   ```python
   from synth.xg.sart import YamahaNRPNMapper
   mapper = YamahaNRPNMapper()
   art = mapper.get_articulation(1, 1)
   print(f"NRPN (1,1) = {art}")  # Should be 'legato'
   ```

2. Check NRPN processing:
   ```python
   synth.process_nrpn(0, 1, 1, 0)
   print(f"Articulation: {synth.get_channel_articulation(0)}")
   ```

### **Performance Issues**

**Problem:** High CPU usage with S.Art2.

**Solutions:**
1. Disable sample modification if not needed:
   ```python
   from synth.xg.sart.sart2_region import SArt2Region
   region = SArt2Region(base_region, enable_sample_modification=False)
   ```

2. Reduce articulation complexity:
   ```python
   # Use simpler articulations
   region.set_articulation('normal')  # No processing
   ```

---

## See Also

- [`SART2_API.md`](SART2_API.md) - Complete API reference
- [`SART2_MIGRATION.md`](SART2_MIGRATION.md) - Migration guide
- [`synth/xg/sart/`](../synth/xg/sart/) - Package source code

---

## Quick Reference Card

### **Common Articulations**

```
normal    - Default sound
legato    - Smooth transitions
staccato  - Short, detached
vibrato   - Pitch modulation
growl     - Rough texture
pizzicato - Plucked strings
```

### **NRPN Quick Reference**

```
MSB 1, LSB 0  → normal
MSB 1, LSB 1  → legato
MSB 1, LSB 2  → staccato
MSB 1, LSB 4  → vibrato
MSB 1, LSB 7  → growl
MSB 2, LSB 0  → ppp (soft)
MSB 2, LSB 5  → f (loud)
```

### **API Quick Reference**

```python
# Set articulation
synth.set_channel_articulation(channel, 'legato')

# Get articulation
art = synth.get_channel_articulation(channel)

# Process NRPN
synth.process_nrpn(channel, msb, lsb, value)

# Get available
arts = synth.get_available_articulations()
```
