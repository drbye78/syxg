# S.Art2 Velocity/Key Switching Guide

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-23

---

## Table of Contents

1. [Overview](#overview)
2. [Velocity Switching](#velocity-switching)
3. [Key Switching](#key-switching)
4. [Combined Switching](#combined-switching)
5. [Articulation Presets](#articulation-presets)
6. [Examples](#examples)

---

## Overview

S.Art2 supports two types of automatic articulation switching:

1. **Velocity Switching** - Different articulations based on playing velocity
2. **Key Switching** - Different articulations based on note position

These can be used independently or combined for maximum expressiveness.

### **Quick Start**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(base_region)

# Velocity switching
region.set_velocity_articulation(0, 64, 'pizzicato')
region.set_velocity_articulation(65, 100, 'staccato')
region.set_velocity_articulation(101, 127, 'marcato')

# Key switching
region.set_key_articulation(0, 47, 'bass')
region.set_key_articulation(48, 83, 'mid')
region.set_key_articulation(84, 127, 'treble')

# Automatic switching during play
region.note_on(velocity=50, note=60)   # → pizzicato
region.note_on(velocity=100, note=60)  # → staccato
region.note_on(velocity=120, note=36)  # → bass + marcato
```

---

## Velocity Switching

### **How It Works**

Velocity switching assigns different articulations to different velocity ranges. This mimics how real instruments produce different sounds based on playing intensity.

### **Setting Velocity Articulations**

```python
region.set_velocity_articulation(
    vel_low=0,
    vel_high=64,
    articulation='pizzicato',
    note_length=0.5,
    decay=0.2
)
```

**Parameters:**
- `vel_low` - Low velocity bound (0-127)
- `vel_high` - High velocity bound (0-127)
- `articulation` - Articulation name
- `**params` - Articulation parameters

### **Velocity Ranges**

| Range | Name | Typical Use |
|-------|------|-------------|
| 0-64 | Soft | Piano, gentle playing |
| 65-100 | Medium | Mezzo-forte, normal playing |
| 101-127 | Loud | Forte, accented playing |

### **Example: Piano Velocity Switching**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(piano_region)

# Three velocity layers
region.set_velocity_articulation(
    0, 64, 'staccato',
    note_length=0.5,
    volume=0.7
)
region.set_velocity_articulation(
    65, 100, 'normal',
    note_length=1.0,
    volume=0.85
)
region.set_velocity_articulation(
    101, 127, 'marcato',
    accent=1.2,
    volume=1.0
)

# Play with different velocities
region.note_on(velocity=50, note=60)   # → staccato
region.note_on(velocity=80, note=60)   # → normal
region.note_on(velocity=120, note=60)  # → marcato
```

### **Example: Guitar Velocity Switching**

```python
region = SArt2Region(guitar_region)

# Velocity-based guitar techniques
region.set_velocity_articulation(0, 64, 'palm_mute_gtr', mute=0.7)
region.set_velocity_articulation(65, 100, 'normal')
region.set_velocity_articulation(101, 127, 'accented', accent=1.2)
```

### **Example: Saxophone Velocity Switching**

```python
region = SArt2Region(sax_region)

# Velocity-based saxophone techniques
region.set_velocity_articulation(0, 64, 'sub_tone_sax', breath=0.3)
region.set_velocity_articulation(65, 100, 'normal')
region.set_velocity_articulation(101, 127, 'growl_wind', growl=0.5)
```

### **Clearing Velocity Articulations**

```python
region.clear_velocity_articulations()
```

---

## Key Switching

### **How It Works**

Key switching assigns different articulations to different key ranges. This is useful for instruments that have different playing techniques in different registers.

### **Setting Key Articulations**

```python
region.set_key_articulation(
    key_low=0,
    key_high=47,
    articulation='pizzicato_strings',
    decay=0.2
)
```

**Parameters:**
- `key_low` - Low key bound (0-127)
- `key_high` - High key bound (0-127)
- `articulation` - Articulation name
- `**params` - Articulation parameters

### **Key Ranges**

| Range | Notes | Name | Typical Use |
|-------|-------|------|-------------|
| 0-47 | C0-B2 | Bass | Low register |
| 48-83 | C3-B4 | Mid | Middle register |
| 84-127 | C5-C7 | Treble | High register |

### **Example: Violin Key Switching**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(violin_region)

# Different techniques for different registers
region.set_key_articulation(
    0, 47, 'pizzicato_strings',
    decay=0.2
)
region.set_key_articulation(
    48, 83, 'legato',
    attack=0.05
)
region.set_key_articulation(
    84, 127, 'spiccato',
    accent=1.1
)

# Play in different registers
region.note_on(velocity=100, note=36)  # C2 → pizzicato
region.note_on(velocity=100, note=60)  # C4 → legato
region.note_on(velocity=100, note=96)  # C7 → spiccato
```

### **Example: Strings Ensemble Key Switching**

```python
region = SArt2Region(strings_region)

# Key-based string techniques
region.set_key_articulation(0, 47, 'pizzicato_strings')
region.set_key_articulation(48, 83, 'legato')
region.set_key_articulation(84, 127, 'tremolando')
```

### **Clearing Key Articulations**

```python
region.clear_key_articulations()
```

---

## Combined Switching

### **How It Works**

Velocity and key switching can be combined. The switching priority is:

1. **Key splits** (checked first)
2. **Velocity splits** (checked second)
3. **Default articulation** (fallback)

### **Example: Combined Piano**

```python
region = SArt2Region(piano_region)

# Key splits (bass/treble)
region.set_key_articulation(0, 47, 'bass_normal')
region.set_key_articulation(48, 127, 'treble_normal')

# Velocity splits (within each key range)
region.set_velocity_articulation(0, 64, 'staccato')
region.set_velocity_articulation(65, 100, 'normal')
region.set_velocity_articulation(101, 127, 'marcato')

# Combined switching
region.note_on(velocity=50, note=36)   # Bass + staccato
region.note_on(velocity=100, note=60)  # Treble + normal
region.note_on(velocity=120, note=96)  # Treble + marcato
```

### **Example: Advanced Guitar**

```python
region = SArt2Region(guitar_region)

# Key splits for different string ranges
region.set_key_articulation(0, 52, 'bass_strings', mute=0.5)
region.set_key_articulation(53, 127, 'treble_strings')

# Velocity splits for playing techniques
region.set_velocity_articulation(0, 64, 'palm_mute_gtr')
region.set_velocity_articulation(65, 100, 'normal')
region.set_velocity_articulation(101, 127, 'bend_gtr', bend_amount=0.5)

# Combined
region.note_on(velocity=50, note=40)   # Bass + palm mute
region.note_on(velocity=100, note=72)  # Treble + normal
region.note_on(velocity=120, note=84)  # Treble + bend
```

---

## Articulation Presets

### **Using ArticulationPreset**

```python
from synth.xg.sart.articulation_preset import ArticulationPreset

# Create preset
preset = ArticulationPreset(
    name='Grand Piano',
    program=0,
    bank=0,
    default_articulation='normal'
)

# Add velocity splits
preset.add_velocity_split(
    0, 64, 'staccato',
    note_length=0.5
)
preset.add_velocity_split(65, 100, 'normal')
preset.add_velocity_split(
    101, 127, 'marcato',
    accent=1.2
)

# Add key splits
preset.add_key_split(
    0, 47, 'bass_normal',
    volume=0.8
)
preset.add_key_split(48, 127, 'treble_normal')

# Get articulation for note/velocity
art, params = preset.get_articulation(note=60, velocity=100)
# Returns: ('normal', {})
```

### **Loading Presets in ModernXGSynthesizer**

```python
from synth import ModernXGSynthesizer

synth = ModernXGSynthesizer()

# Load preset for channel
success = synth.load_articulation_preset(
    channel=0,
    bank=0,
    program=0
)

# Preset is automatically applied to notes
synth.channels[0].note_on(note=60, velocity=100)
```

### **Built-in Presets**

The following presets are included:

| Program | Name | Category | Velocity Splits | Key Splits |
|---------|------|----------|-----------------|------------|
| 0 | Grand Piano | piano | 3 | 0 |
| 4 | Electric Piano | piano | 2 | 0 |
| 40 | Violin | strings | 2 | 2 |
| 48 | Strings Ensemble | strings | 3 | 0 |
| 24 | Acoustic Guitar | guitar | 3 | 0 |
| 26 | Electric Guitar | guitar | 3 | 0 |
| 65 | Alto Sax | wind | 3 | 0 |
| 56 | Trumpet | wind | 3 | 0 |
| 52 | Choir Aahs | vocal | 3 | 0 |
| 81 | Saw Lead | synth | 2 | 0 |

---

## Examples

### **Example 1: Multi-Velocity Piano**

```python
from synth import ModernXGSynthesizer

synth = ModernXGSynthesizer()

# Load piano preset (has velocity splits)
synth.load_articulation_preset(channel=0, bank=0, program=0)

# Play with different velocities
for velocity in [40, 70, 110]:
    synth.channels[0].note_on(note=60, velocity=velocity)
    # velocity=40 → staccato
    # velocity=70 → normal
    # velocity=110 → marcato
```

### **Example 2: Key-Switched Strings**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(strings_region)

# Set key splits
region.set_key_articulation(0, 47, 'pizzicato_strings')
region.set_key_articulation(48, 83, 'legato')
region.set_key_articulation(84, 127, 'spiccato')

# Play scale
for note in [36, 48, 60, 72, 84, 96]:
    region.note_on(velocity=100, note=note)
    # note=36 → pizzicato
    # note=48-83 → legato
    # note=84+ → spiccato
```

### **Example 3: Combined Guitar**

```python
from synth.xg.sart.articulation_preset import ArticulationPreset

# Create guitar preset
preset = ArticulationPreset(
    name='Electric Guitar',
    program=26,
    bank=0
)

# Key splits
preset.add_key_split(0, 52, 'bass_strings', mute=0.5)
preset.add_key_split(53, 127, 'treble_strings')

# Velocity splits
preset.add_velocity_split(0, 64, 'palm_mute_gtr')
preset.add_velocity_split(65, 100, 'normal')
preset.add_velocity_split(101, 127, 'bend_gtr', bend_amount=0.5)

# Load preset
synth.load_articulation_preset(channel=0, bank=0, program=26)
```

### **Example 4: Custom Velocity Curves**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(region)

# Fine-grained velocity control
region.set_velocity_articulation(0, 30, 'ppp', volume=0.3)
region.set_velocity_articulation(31, 50, 'pp', volume=0.4)
region.set_velocity_articulation(51, 70, 'p', volume=0.5)
region.set_velocity_articulation(71, 90, 'mp', volume=0.6)
region.set_velocity_articulation(91, 110, 'mf', volume=0.75)
region.set_velocity_articulation(111, 120, 'f', volume=0.9)
region.set_velocity_articulation(121, 127, 'ff', volume=1.0)
```

---

## Tips and Best Practices

### **1. Use Meaningful Velocity Ranges**

```python
# Good: Clear velocity boundaries
region.set_velocity_articulation(0, 64, 'soft')
region.set_velocity_articulation(65, 100, 'medium')
region.set_velocity_articulation(101, 127, 'loud')

# Bad: Overlapping ranges (last one wins)
region.set_velocity_articulation(0, 80, 'soft')
region.set_velocity_articulation(60, 127, 'loud')  # Overlaps!
```

### **2. Use Instrument-Appropriate Splits**

```python
# Piano: Velocity-based dynamics
region.set_velocity_articulation(0, 64, 'staccato')
region.set_velocity_articulation(65, 127, 'legato')

# Strings: Key-based techniques
region.set_key_articulation(0, 47, 'pizzicato')
region.set_key_articulation(48, 127, 'legato')

# Guitar: Combined
region.set_key_articulation(0, 52, 'bass')
region.set_key_articulation(53, 127, 'treble')
region.set_velocity_articulation(0, 64, 'palm_mute')
region.set_velocity_articulation(65, 127, 'normal')
```

### **3. Test All Velocity/Key Ranges**

```python
# Test all velocity ranges
for vel in [30, 64, 65, 100, 101, 127]:
    region.note_on(velocity=vel, note=60)
    print(f'Vel {vel}: {region.get_articulation()}')

# Test all key ranges
for note in [24, 47, 48, 83, 84, 108]:
    region.note_on(velocity=100, note=note)
    print(f'Note {note}: {region.get_articulation()}')
```

### **4. Use Presets for Consistency**

```python
# Create reusable preset
preset = ArticulationPreset(
    name='My Piano',
    program=0,
    bank=0
)
preset.add_velocity_split(0, 64, 'staccato')
preset.add_velocity_split(65, 127, 'legato')

# Save preset
manager = ArticulationPresetManager()
manager.add_preset(preset)
manager.save_to_file('my_presets.json')

# Load preset later
manager.load_from_file('my_presets.json')
```

---

## See Also

- [`SART2_API_REFERENCE.md`](SART2_API_REFERENCE.md) - Complete API reference
- [`SART2_NRPN_GUIDE.md`](SART2_NRPN_GUIDE.md) - NRPN mapping guide
- [`SART2_SYSEX_SPEC.md`](SART2_SYSEX_SPEC.md) - SYSEX format specification

---

**End of Velocity/Key Switching Guide**
