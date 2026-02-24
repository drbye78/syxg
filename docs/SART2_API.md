# S.Art2 API Reference

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-22

---

## Overview

S.Art2 (Super Articulation 2) provides universal articulation control across ALL synthesis engines in Modern XG Synth. It wraps any `IRegion` implementation with expressive articulation capabilities controlled via NRPN/SYSEX messages or direct API calls.

---

## Core Classes

### **SArt2Region**

**Module:** `synth.xg.sart.sart2_region`

Universal articulation wrapper that adds S.Art2 control to any synthesis region.

#### Constructor

```python
SArt2Region(
    base_region: IRegion,
    sample_rate: int = 44100,
    enable_sample_modification: bool = True
)
```

**Parameters:**
- `base_region` - Any IRegion implementation (SF2Region, FMRegion, etc.)
- `sample_rate` - Audio sample rate in Hz (default: 44100)
- `enable_sample_modification` - Enable articulation sample processing (default: True)

**Example:**
```python
from synth.xg.sart.sart2_region import SArt2Region
from synth.partial.sf2_region import SF2Region

# Wrap SF2 region with S.Art2
base_region = SF2Region(descriptor, 44100, manager)
sart2_region = SArt2Region(base_region)
```

#### Methods

##### `set_articulation(articulation: str) -> None`

Set current articulation.

**Parameters:**
- `articulation` - Articulation name (e.g., 'legato', 'staccato', 'growl')

**Example:**
```python
region.set_articulation('legato')
```

##### `get_articulation() -> str`

Get current articulation name.

**Returns:** Articulation name string

**Example:**
```python
current = region.get_articulation()  # Returns 'legato'
```

##### `process_nrpn(msb: int, lsb: int) -> str`

Process NRPN message to set articulation.

**Parameters:**
- `msb` - NRPN MSB value (0-127)
- `lsb` - NRPN LSB value (0-127)

**Returns:** Articulation name that was set

**Example:**
```python
# MSB 1, LSB 1 = legato
articulation = region.process_nrpn(1, 1)
```

##### `process_sysex(sysex_data: bytes) -> Dict[str, Any]`

Process SYSEX message for articulation control.

**Parameters:**
- `sysex_data` - SYSEX byte data

**Returns:** SYSEX parsing result dictionary

**Example:**
```python
result = region.process_sysex(sysex_bytes)
if result['command'] == 'set_articulation':
    print(f"Articulation: {result['articulation']}")
```

##### `get_available_articulations() -> List[str]`

Get list of all available articulations.

**Returns:** List of articulation names

**Example:**
```python
articulations = region.get_available_articulations()
# ['normal', 'legato', 'staccato', 'growl', ...]
```

##### `get_articulation_params() -> Dict[str, Any]`

Get parameters for current articulation.

**Returns:** Parameter dictionary with articulation-specific values

**Example:**
```python
params = region.get_articulation_params()
# {'rate': 5.0, 'depth': 0.05} for vibrato
```

##### `set_articulation_param(param: str, value: Any) -> None`

Set parameter for current articulation.

**Parameters:**
- `param` - Parameter name (e.g., 'rate', 'depth', 'blend')
- `value` - Parameter value

**Example:**
```python
region.set_articulation_param('rate', 6.0)  # Faster vibrato
```

##### `generate_samples(block_size: int, modulation: Dict) -> np.ndarray`

Generate samples with S.Art2 articulation processing.

**Parameters:**
- `block_size` - Number of samples to generate
- `modulation` - Current modulation values

**Returns:** Stereo audio buffer (block_size * 2,) as float32

---

### **SArt2RegionFactory**

**Module:** `synth.xg.sart.sart2_region`

Factory for creating S.Art2-wrapped regions.

#### Constructor

```python
SArt2RegionFactory(sample_rate: int = 44100)
```

#### Methods

##### `create_sart2_region(base_region: IRegion) -> SArt2Region`

Wrap a base region with S.Art2 articulation.

**Parameters:**
- `base_region` - Any IRegion implementation

**Returns:** SArt2Region wrapper

**Example:**
```python
factory = SArt2RegionFactory(44100)
sart2_region = factory.create_sart2_region(base_region)
```

##### `create_from_engine(descriptor: RegionDescriptor, engine: SynthesisEngine) -> SArt2Region`

Create S.Art2 region from descriptor using engine.

**Parameters:**
- `descriptor` - Region descriptor
- `engine` - Synthesis engine to create base region

**Returns:** SArt2Region wrapper

**Example:**
```python
region = factory.create_from_engine(descriptor, sf2_engine)
```

---

### **ArticulationController**

**Module:** `synth.xg.sart.articulation_controller`

Controller for articulation mapping and parameter management.

#### Methods

##### `set_articulation(articulation: str) -> None`

Set current articulation.

##### `get_articulation() -> str`

Get current articulation name.

##### `process_nrpn(msb: int, lsb: int) -> str`

Process NRPN message to set articulation.

##### `parse_sysex(sysex_data: bytes) -> Dict[str, Any]`

Parse SYSEX message for articulation control.

##### `get_articulation_params() -> Dict[str, Any]`

Get parameters for current articulation.

---

### **YamahaNRPNMapper**

**Module:** `synth.xg.sart.nrpn`

NRPN mapper for Yamaha S.Art2 articulations.

#### Methods

##### `get_articulation(msb: int, lsb: int, category: str = 'common') -> str`

Get articulation from NRPN MSB/LSB values.

**Parameters:**
- `msb` - NRPN MSB value
- `lsb` - NRPN LSB value
- `category` - Articulation category ('common', 'wind', 'strings', etc.)

**Returns:** Articulation name

**Example:**
```python
mapper = YamahaNRPNMapper()
articulation = mapper.get_articulation(1, 1)  # Returns 'legato'
```

---

## ModernXGSynthesizer Integration

### **NRPN Processing**

```python
synth.process_nrpn(channel: int, msb: int, lsb: int, value: int) -> None
```

Process NRPN message for S.Art2 articulation control.

**Example:**
```python
# Set legato on channel 0
synth.process_nrpn(0, 1, 1, 0)
```

### **SYSEX Processing**

```python
synth.process_sysex(data: bytes) -> None
```

Process SYSEX message for S.Art2 articulation.

### **Channel Articulation**

```python
synth.set_channel_articulation(channel: int, articulation: str) -> None
synth.get_channel_articulation(channel: int) -> str
```

**Example:**
```python
synth.set_channel_articulation(0, 'staccato')
current = synth.get_channel_articulation(0)
```

### **Available Articulations**

```python
synth.get_available_articulations() -> list
```

---

## Articulation Reference

### **Common Articulations (MSB 1)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | normal | Default articulation |
| 1 | legato | Smooth note transitions |
| 2 | staccato | Short, detached notes |
| 3 | bend | Pitch bend effect |
| 4 | vibrato | Vibrato modulation |
| 5 | breath | Breath controller effect |
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
| 17 | hammer_on | Hammer-on (guitar) |
| 18 | pull_off | Pull-off (guitar) |
| 19 | key_off | Key-off noise |
| 20 | marcato | Marcato (accented) |
| 21 | detache | Detaché |
| 22 | sul_ponticello | Sul ponticello (strings) |
| 23 | scoop | Scoop effect |
| 24 | rip | Rip effect |
| 25 | portamento | Portamento slide |
| 26 | swell | Swell effect |
| 27 | accented | Accented note |
| 28 | bow_up | Up-bow (strings) |
| 29 | bow_down | Down-bow (strings) |
| 30 | col_legno | Col legno (strings) |
| 31 | up_bend | Upward bend |
| 32 | down_bend | Downward bend |
| 33 | smear | Smear effect |
| 34 | flip | Flip effect |
| 35 | straight | Straight (no vibrato) |

### **Dynamics (MSB 2)**

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

### **Wind-Specific (MSB 3)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | growl_wind | Wind growl |
| 1 | flutter_wind | Flutter tongue |
| 2 | tongue_slap_wind | Tongue slap |
| 3 | smear_wind | Smear |
| 4 | flip_wind | Flip |
| 5 | scoop_wind | Scoop |
| 6 | rip_wind | Rip |
| 7 | double_tongue | Double tonguing |
| 8 | triple_tongue | Triple tonguing |

### **Strings-Specific (MSB 4)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | pizzicato_strings | Pizzicato |
| 1 | harmonics_strings | Harmonics |
| 2 | sul_ponticello_strings | Sul ponticello |
| 3 | bow_up_strings | Up-bow |
| 4 | bow_down_strings | Down-bow |
| 5 | col_legno_strings | Col legno |
| 6 | portamento_strings | Portamento |
| 7 | spiccato | Spiccato |
| 8 | tremolando | Tremolando |

### **Guitar-Specific (MSB 5)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | hammer_on_guitar | Hammer-on |
| 1 | pull_off_guitar | Pull-off |
| 2 | harmonics_guitar | Harmonics |
| 3 | palm_mute | Palm mute |
| 4 | tap | Tapping |
| 5 | slide_up | Slide up |
| 6 | slide_down | Slide down |
| 7 | bend | String bend |

### **Brass-Specific (MSB 6)**

| LSB | Articulation | Description |
|-----|--------------|-------------|
| 0 | muted_brass | Muted |
| 1 | cup_mute | Cup mute |
| 2 | harmon_mute | Harmon mute |
| 3 | stopped | Stopped |
| 4 | scoop_brass | Scoop |
| 5 | lip_trill | Lip trill |

---

## Articulation Parameters

Each articulation has specific parameters that control its behavior:

### **legato**
```python
{
    'blend': 0.5,           # Crossfade blend (0.0-1.0)
    'transition_time': 0.05 # Transition time in seconds
}
```

### **staccato**
```python
{
    'note_length': 0.1  # Note length multiplier (0.0-1.0)
}
```

### **vibrato**
```python
{
    'rate': 5.0,   # Vibrato rate in Hz
    'depth': 0.05  # Vibrato depth (frequency modulation)
}
```

### **trill**
```python
{
    'interval': 2,     # Semitone interval
    'rate': 6.0        # Trill rate in Hz
}
```

### **growl**
```python
{
    'mod_freq': 25.0,  # Modulation frequency in Hz
    'depth': 0.25      # Modulation depth
}
```

### **pizzicato**
```python
{
    'decay_rate': 8.0  # Decay rate (higher = shorter)
}
```

### **crescendo**
```python
{
    'target_level': 1.0,  # Target volume level
    'duration': 1.0       # Duration in seconds
}
```

---

## Usage Examples

### **Basic Usage**

```python
from synth import ModernXGSynthesizer

# Create synthesizer
synth = ModernXGSynthesizer()
synth.load_soundfont('piano.sf2')

# Set articulation
synth.set_channel_articulation(0, 'legato')

# Play note
synth.channels[0].note_on(60, 100)
```

### **NRPN Control**

```python
# Real-time articulation switching via NRPN
synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)  # legato
synth.process_nrpn(channel=0, msb=1, lsb=2, value=0)  # staccato
synth.process_nrpn(channel=0, msb=1, lsb=7, value=0)  # growl
```

### **Direct Region Control**

```python
from synth.xg.sart.sart2_region import SArt2Region

# Get region
region = synth.channels[0].current_voice.get_regions_for_note(60, 100)[0]

# Set articulation directly
region.set_articulation('vibrato')

# Set parameters
region.set_articulation_param('rate', 6.0)
region.set_articulation_param('depth', 0.08)
```

### **Articulation List**

```python
# Get all available articulations
articulations = synth.get_available_articulations()

for art in articulations:
    print(f"- {art}")
```

---

## Performance Notes

- **Overhead:** S.Art2 adds <5% CPU overhead
- **Latency:** <0.1ms additional latency
- **Memory:** ~10KB per SArt2Region instance
- **Thread Safety:** All methods are thread-safe

---

## See Also

- [`SART2_USER_GUIDE.md`](SART2_USER_GUIDE.md) - User guide with tutorials
- [`SART2_MIGRATION.md`](SART2_MIGRATION.md) - Migration guide
- [`synth/xg/sart/`](../synth/xg/sart/) - Package source code
