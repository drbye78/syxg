# S.Art2 API Reference

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-23

---

## Table of Contents

1. [Overview](#overview)
2. [Core Classes](#core-classes)
3. [Articulation Types](#articulation-types)
4. [NRPN Reference](#nrpn-reference)
5. [SYSEX Reference](#sysex-reference)
6. [Examples](#examples)

---

## Overview

S.Art2 (Super Articulation 2) provides universal articulation control across ALL synthesis engines in Modern XG Synth. It wraps any `IRegion` implementation with articulation control capabilities via NRPN/SYSEX messages.

### **Key Features**

- **275+ Articulations** - Comprehensive articulation library
- **NRPN Support** - Real-time articulation switching
- **SYSEX Support** - Bulk articulation operations
- **Velocity Switching** - Articulation per velocity range
- **Key Switching** - Articulation per key range
- **Preset System** - Program-specific articulation configurations

### **Quick Start**

```python
from synth import ModernXGSynthesizer

# Create synthesizer (S.Art2 enabled by default)
synth = ModernXGSynthesizer()

# Set articulation via API
synth.set_channel_articulation(0, 'legato')

# Set articulation via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)  # legato

# Load articulation preset
synth.load_articulation_preset(channel=0, bank=0, program=0)
```

---

## Core Classes

### **ArticulationController**

**Module:** `synth.xg.sart.articulation_controller`

Main controller for articulation management.

```python
from synth.xg.sart import ArticulationController

controller = ArticulationController()

# Set articulation
controller.set_articulation('legato')

# Get articulation
art = controller.get_articulation()  # 'legato'

# Process NRPN
controller.process_nrpn(msb=1, lsb=1)  # Sets 'legato'

# Process SYSEX
result = controller.process_sysex(sysex_bytes)

# Get available articulations
arts = controller.get_available_articulations()
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `set_articulation()` | `articulation: str` | `None` | Set current articulation |
| `get_articulation()` | - | `str` | Get current articulation |
| `process_nrpn()` | `msb: int, lsb: int` | `str` | Process NRPN message |
| `process_sysex()` | `sysex: bytes` | `Dict` | Process SYSEX message |
| `get_available_articulations()` | - | `List[str]` | Get all articulations |
| `get_articulation_params()` | - | `Dict` | Get current parameters |
| `set_articulation_param()` | `param: str, value: Any` | `None` | Set parameter |
| `build_sysex_articulation_set()` | `channel: int, art_msb: int, art_lsb: int` | `bytes` | Build SYSEX |
| `build_sysex_parameter_set()` | `channel: int, param_msb: int, param_lsb: int, value: int` | `bytes` | Build SYSEX |

---

### **YamahaNRPNMapper**

**Module:** `synth.xg.sart.nrpn`

NRPN to articulation mapper with category support.

```python
from synth.xg.sart import YamahaNRPNMapper

mapper = YamahaNRPNMapper()

# Get articulation from NRPN
art = mapper.get_articulation(msb=1, lsb=1)  # 'legato'

# Get NRPN for articulation
msb, lsb = mapper.get_nrpn_for_articulation('legato')  # (1, 1)

# Search articulations
results = mapper.search_articulations('vibrato')

# Get category info
count = mapper.get_category_count('common')  # 50+
categories = mapper.get_all_categories()  # 13 categories
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_articulation()` | `msb: int, lsb: int, category: str` | `str` | Get articulation |
| `get_nrpn_for_articulation()` | `articulation: str, category: str` | `Tuple[int, int]` | Reverse lookup |
| `search_articulations()` | `pattern: str` | `List[Tuple]` | Search |
| `get_category_for_msb()` | `msb: int` | `str` | Get category |
| `get_msb_for_category()` | `category: str` | `int` | Get MSB |
| `get_articulation_count()` | - | `int` | Total count |
| `get_category_count()` | `category: str` | `int` | Category count |

---

### **NRPNParameterController**

**Module:** `synth.xg.sart.nrpn`

Controller for articulation parameter NRPN messages.

```python
from synth.xg.sart import NRPNParameterController

ctrl = NRPNParameterController()

# Process parameter NRPN
result = ctrl.process_parameter_nrpn(param_msb=0, param_lsb=0, value=64)
# {'articulation': 'vibrato', 'param_name': 'rate', 'value': 0.64}

# Get NRPN for parameter
nrpn = ctrl.get_nrpn_for_parameter('vibrato', 'rate')  # (0, 0)

# Split/combine values
msb, lsb = ctrl.split_parameter_value(8192)  # (64, 0)
value = ctrl.build_parameter_value(64, 0)  # 8192
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `process_parameter_nrpn()` | `param_msb: int, param_lsb: int, value: int` | `Dict` | Process NRPN |
| `get_nrpn_for_parameter()` | `articulation: str, param_name: str` | `Tuple[int, int]` | Reverse lookup |
| `split_parameter_value()` | `value: int` | `Tuple[int, int]` | Split to MSB/LSB |
| `build_parameter_value()` | `msb: int, lsb: int` | `int` | Combine values |
| `get_parameter_range()` | `param_msb: int, param_lsb: int` | `Dict` | Get range |
| `get_all_parameters()` | - | `List[Dict]` | All parameters |

---

### **SArt2Region**

**Module:** `synth.xg.sart.sart2_region`

S.Art2 wrapper for any `IRegion` implementation.

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(base_region)

# Set articulation
region.set_articulation('legato')

# Set velocity articulation
region.set_velocity_articulation(0, 64, 'pizzicato')
region.set_velocity_articulation(65, 127, 'staccato')

# Set key articulation
region.set_key_articulation(0, 47, 'bass')
region.set_key_articulation(48, 127, 'treble')

# Note-on with automatic switching
region.note_on(velocity=100, note=60)
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `set_articulation()` | `articulation: str` | `None` | Set articulation |
| `get_articulation()` | - | `str` | Get articulation |
| `set_velocity_articulation()` | `vel_low: int, vel_high: int, art: str` | `None` | Set velocity split |
| `set_key_articulation()` | `key_low: int, key_high: int, art: str` | `None` | Set key split |
| `note_on()` | `velocity: int, note: int` | `bool` | Trigger note |
| `generate_samples()` | `block_size: int, modulation: Dict` | `np.ndarray` | Generate audio |

---

### **ArticulationPreset**

**Module:** `synth.xg.sart.articulation_preset`

Articulation preset for a program.

```python
from synth.xg.sart.articulation_preset import ArticulationPreset

preset = ArticulationPreset(
    name='Grand Piano',
    program=0,
    bank=0,
    default_articulation='normal'
)

# Add velocity splits
preset.add_velocity_split(0, 64, 'staccato', note_length=0.5)
preset.add_velocity_split(65, 100, 'normal')
preset.add_velocity_split(101, 127, 'marcato', accent=1.2)

# Get articulation for note/velocity
art, params = preset.get_articulation(note=60, velocity=100)
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add_velocity_split()` | `vel_low: int, vel_high: int, art: str, **params` | `None` | Add split |
| `add_key_split()` | `key_low: int, key_high: int, art: str, **params` | `None` | Add split |
| `get_articulation()` | `note: int, velocity: int` | `Tuple[str, Dict]` | Get articulation |
| `to_dict()` | - | `Dict` | Convert to dict |
| `to_json()` | `indent: int` | `str` | Convert to JSON |
| `from_dict()` | `data: Dict` | `ArticulationPreset` | Create from dict |
| `from_json()` | `json_str: str` | `ArticulationPreset` | Create from JSON |

---

### **ArticulationPresetManager**

**Module:** `synth.xg.sart.articulation_preset`

Manager for articulation presets.

```python
from synth.xg.sart.articulation_preset import ArticulationPresetManager

manager = ArticulationPresetManager()

# Add preset
manager.add_preset(preset)

# Get preset
preset = manager.get_preset(bank=0, program=0)

# Get by category
presets = manager.get_presets_by_category('piano')

# Save/load
manager.save_to_file('presets.json')
manager.load_from_file('presets.json')
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add_preset()` | `preset: ArticulationPreset` | `None` | Add preset |
| `get_preset()` | `bank: int, program: int` | `ArticulationPreset` | Get preset |
| `get_presets_by_category()` | `category: str` | `List[ArticulationPreset]` | Get by category |
| `remove_preset()` | `bank: int, program: int` | `bool` | Remove preset |
| `save_to_file()` | `filepath: str` | `None` | Save to file |
| `load_from_file()` | `filepath: str` | `int` | Load from file |
| `get_preset_count()` | - | `int` | Get count |

---

## Articulation Types

### **Common Articulations (MSB 1)**

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
| ... | ... | ... |

### **Dynamics (MSB 2)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | ppp | Pianississimo |
| 1 | pp | Pianissimo |
| 2 | p | Piano |
| 3 | mp | Mezzo-piano |
| 4 | mf | Mezzo-forte |
| 5 | f | Forte |
| 6 | ff | Fortissimo |
| 7 | fff | Fortississimo |
| 8 | crescendo | Gradually louder |
| 9 | diminuendo | Gradually softer |

### **Guitar (MSB 8)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | slide_up_gtr | Slide up |
| 1 | slide_down_gtr | Slide down |
| 2 | bend_gtr | String bend |
| 3 | bend_release_gtr | Bend release |
| 4 | pre_bend | Pre-bend |
| 5 | harmonics_natural | Natural harmonics |
| 6 | harmonics_artificial | Artificial harmonics |
| 7 | harmonics_pinch | Pinch harmonics |
| 8 | tapping_gtr | Tapping |
| 9 | slap_gtr | Slap |
| 10 | pop_gtr | Pop |
| ... | ... | ... |

---

## NRPN Reference

### **Standard NRPN Format**

```
CC 99 (NRPN MSB) = Parameter MSB
CC 98 (NRPN LSB) = Parameter LSB
CC 6 (Data MSB)  = Value MSB (0-127)
CC 38 (Data LSB) = Value LSB (0-127)

Value = (MSB << 7) | LSB  (0-16383)
```

### **Articulation NRPN (MSB 1-13)**

| MSB | Category | LSB Range | Parameters |
|-----|----------|-----------|------------|
| 1 | Common | 0-49 | articulation |
| 2 | Dynamics | 0-14 | articulation |
| 3 | Wind - Sax | 0-24 | articulation |
| 4 | Wind - Brass | 0-19 | articulation |
| 5 | Wind - Woodwind | 0-17 | articulation |
| 6 | Strings - Bow | 0-21 | articulation |
| 7 | Strings - Pluck | 0-14 | articulation |
| 8 | Guitar | 0-24 | articulation |
| 9 | Vocal | 0-19 | articulation |
| 10 | Synth | 0-14 | articulation |
| 11 | Percussion | 0-19 | articulation |
| 12 | Ethnic | 0-17 | articulation |
| 13 | Effects | 0-11 | articulation |

### **Parameter NRPN (MSB 0-10)**

| MSB | LSB | Articulation | Parameter | Range |
|-----|-----|--------------|-----------|-------|
| 0 | 0 | vibrato | rate | 0.0-1.27 Hz |
| 0 | 1 | vibrato | depth | 0.0-16.38 |
| 1 | 0 | legato | blend | 0.0-1.638 |
| 1 | 1 | legato | transition_time | 0.0-0.16 sec |
| 2 | 0 | growl | mod_freq | 0-127 Hz |
| ... | ... | ... | ... | ... |

---

## SYSEX Reference

### **SYSEX Format**

```
F0 43 10 4C [cmd] [data...] F7
│  │  │  │   │
│  │  │  │   └─ Command
│  │  │  └──── S.Art2 ID (0x4C)
│  │  └─────── Device ID (0x10)
│  └────────── Yamaha ID (0x43)
└───────────── Start of SYSEX
```

### **Command Types**

| Cmd | Name | Format | Description |
|-----|------|--------|-------------|
| 0x10 | articulation_set | `F0 43 10 4C 10 [ch] [art_msb] [art_lsb] F7` | Set articulation |
| 0x11 | articulation_param | `F0 43 10 4C 11 [ch] [param_msb] [param_lsb] [val_msb] [val_lsb] F7` | Set parameter |
| 0x12 | articulation_release | `F0 43 10 4C 12 [ch] F7` | Release articulation |
| 0x13 | articulation_query | `F0 43 10 4C 13 [ch] F7` | Query articulation |
| 0x14 | articulation_chain | `F0 43 10 4C 14 [ch] [count] [art1_msb] [art1_lsb] [dur1_msb] [dur1_lsb] ... F7` | Set chain |
| 0x15 | bulk_dump | `F0 43 10 4C 15 [ch] [data...] [checksum] F7` | Bulk dump |
| 0x16 | bulk_load | `F0 43 10 4C 16 [ch] [data...] [checksum] F7` | Bulk load |
| 0x17 | system_config | `F0 43 10 4C 17 [ch] [config_msb] [config_lsb] [value] F7` | System config |

### **Checksum Calculation**

```python
def calculate_checksum(data: bytes) -> int:
    """Calculate Yamaha SYSEX checksum."""
    checksum = sum(data) & 0x7F
    return (~checksum) & 0x7F
```

---

## Examples

### **Basic Articulation Control**

```python
from synth import ModernXGSynthesizer

synth = ModernXGSynthesizer()

# Set articulation
synth.set_channel_articulation(0, 'legato')

# Get articulation
art = synth.get_channel_articulation(0)  # 'legato'

# Get available articulations
arts = synth.get_available_articulations()
```

### **NRPN Control**

```python
# Set legato via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)

# Set staccato via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=2, value=0)
```

### **Velocity Switching**

```python
from synth.xg.sart import SArt2Region

region = SArt2Region(base_region)

# Set velocity articulations
region.set_velocity_articulation(0, 64, 'pizzicato')
region.set_velocity_articulation(65, 100, 'staccato')
region.set_velocity_articulation(101, 127, 'marcato')

# Automatic switching
region.note_on(velocity=50, note=60)  # → pizzicato
region.note_on(velocity=80, note=60)  # → staccato
region.note_on(velocity=120, note=60) # → marcato
```

### **Key Switching**

```python
# Set key articulations
region.set_key_articulation(0, 47, 'pizzicato_strings')
region.set_key_articulation(48, 83, 'spiccato')
region.set_key_articulation(84, 127, 'tremolando')

# Automatic switching
region.note_on(velocity=100, note=36)  # C2 → pizzicato_strings
region.note_on(velocity=100, note=60)  # C4 → spiccato
region.note_on(velocity=100, note=96)  # C7 → tremolando
```

### **Articulation Presets**

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
preset.add_velocity_split(0, 64, 'staccato', note_length=0.5)
preset.add_velocity_split(65, 100, 'normal')
preset.add_velocity_split(101, 127, 'marcato', accent=1.2)

# Load preset
synth.load_articulation_preset(channel=0, bank=0, program=0)
```

### **SYSEX Operations**

```python
from synth.xg.sart import ArticulationController

controller = ArticulationController()

# Build articulation set SYSEX
sysex = controller.build_sysex_articulation_set(
    channel=0,
    art_msb=1,
    art_lsb=1  # legato
)

# Build parameter set SYSEX
sysex = controller.build_sysex_parameter_set(
    channel=0,
    param_msb=0,
    param_lsb=0,
    value=8192  # vibrato rate 0.5
)

# Process SYSEX
result = controller.process_sysex(sysex_bytes)
```

---

## See Also

- [`SART2_NRPN_GUIDE.md`](SART2_NRPN_GUIDE.md) - Complete NRPN mapping reference
- [`SART2_SYSEX_SPEC.md`](SART2_SYSEX_SPEC.md) - SYSEX format specification
- [`SART2_SWITCHING_GUIDE.md`](SART2_SWITCHING_GUIDE.md) - Velocity/Key switching guide
- [`SART2_GENOS2_COMPATIBILITY.md`](SART2_GENOS2_COMPATIBILITY.md) - Genos2 compatibility guide

---

**End of API Reference**
