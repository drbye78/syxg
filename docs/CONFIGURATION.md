# Configuration System Documentation

## Overview

The syxg synthesizer features a comprehensive unified configuration system that consolidates all runtime and musical settings into a single `config.yaml` file. This replaces the previous split configuration approach (config.yaml + synth_config.yaml).

## Architecture

### Components

1. **`config.yaml`** - Unified YAML configuration file containing all settings
2. **`ConfigManager`** (`synth/core/config_manager.py`) - Python class for loading and accessing configuration
3. **`ModernXGSynthesizer.configure_from_config()`** - Method that applies configuration to the synthesizer

### Configuration Loading

```
config.yaml → ConfigManager.load() → Synthesizer.configure_from_config()
```

The system searches for config.yaml in:
1. Explicit path provided
2. Current working directory
3. Project root directory

---

## Configuration File Structure

### Section 1: Audio Settings

```yaml
audio:
  sample_rate: 48000      # Audio sample rate in Hz (22050, 44100, 48000, 96000)
  bit_depth: 32           # Bit depth (16, 24, 32)
  block_size: 1024        # Processing block size in samples
  polyphony: 128          # Maximum voice polyphony
  volume: 0.8             # Master volume (0.0 - 1.0)
```

### Section 2: MIDI Settings

```yaml
midi:
  xg_enabled: true        # Enable XG mode
  gs_enabled: true       # Enable GS mode
  mpe_enabled: true       # Enable MPE (MIDI Polyphonic Expression)
  device_id: 16           # MIDI device ID (0-16)
```

### Section 3: Engine Priorities

```yaml
engines:
  default: "sf2"          # Default synthesis engine
  priority:
    sf2: 10              # SoundFont 2.0 - highest priority
    fm: 8                # FM synthesis
    wavetable: 7         # Wavetable synthesis
    physical: 5          # Physical modeling
    spectral: 3          # Spectral processing
```

**Available Engines:**
- `sf2` - SoundFont 2.0 sample playback
- `fm` - FM (Frequency Modulation) synthesis
- `wavetable` - Wavetable synthesis
- `physical` - Physical modeling
- `spectral` - Spectral processing
- `additive` - Additive synthesis
- `granular` - Granular synthesis
- `convolution` - Convolution reverb

### Section 4: Voice Management

```yaml
voices:
  max_polyphony: 128     # Maximum number of voices
  stealing_policy: "oldest_first"  # Voice stealing strategy
                          # Options: oldest_first, quietest, priority, round_robin
  reserve:               # Per-part voice reserve
    part_0: 8
    part_1: 8
    # ... up to part_15
```

### Section 5: SoundFont Configuration (Multiple SoundFonts)

The synthesizer supports loading multiple SoundFont files with advanced configuration options including **priority ordering**, **program blacklisting**, and **program remapping**.

#### Simple Single Path (Backwards Compatible)

```yaml
sf2_path: "/path/to/soundfont.sf2"  # Default SoundFont file (backwards compatible)
```

#### Multiple SoundFonts with Advanced Options

```yaml
soundfonts:
  # Primary soundfont - highest priority
  - path: "/path/to/primary.sf2"
    priority: 10                    # Higher = loaded first, used first for conflicts
    blacklist:                      # Programs to exclude from this soundfont
      - [0, 0]                     # bank 0, program 0 (Acoustic Grand Piano)
      - [0, 1]                     # bank 0, program 1 (Bright Acoustic Piano)
    remap: {}                      # Program remapping (see below)
  
  # Secondary soundfont - lower priority (fallback for blacklisted programs)
  - path: "/path/to/secondary.sf2"
    priority: 5
    blacklist: []
    remap:
      "0:0": "8:0"                 # Remap program 0 on bank 0 to bank 8 (drums)
      "0:1": "8:1"                 # Another remap example
  
  # Drum soundfont - high priority for drums
  - path: "/path/to/drums.sf2"
    priority: 8
    blacklist:
      - [128, 0]                   # Skip GM drum kit if not needed
    remap: {}
```

#### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `path` | string | Path to the SF2 file (required) |
| `priority` | integer | Loading priority (higher = loaded first, default: 0) |
| `blacklist` | list | List of `[bank, program]` pairs to exclude |
| `remap` | dict | Program remapping (`"from_bank:from_prog": "to_bank:to_prog"`) |

#### Blacklisting

Blacklisted programs will **not** be available from that soundfont. If a program is needed but blacklisted, the synthesizer will search the next soundfont in priority order.

```yaml
soundfonts:
  - path: "/path/to/piano.sf2"
    priority: 10
    blacklist:
      - [0, 0]    # Blacklist Acoustic Grand Piano
      - [0, 1]    # Blacklist Bright Acoustic Piano
      - [0, 6]    # Blacklist Electric Piano 1
```

#### Remapping

Program remapping redirects requests for one program to another. This is useful for:
- Routing drums to different banks
- Redirecting to alternate sounds
- Creating custom program assignments

```yaml
soundfonts:
  - path: "/path/to/drums.sf2"
    priority: 10
    blacklist: []
    remap:
      # Map GM drum program (bank 0, prog 0) to XG drums (bank 8, prog 0)
      "0:0": "8:0"
      # Map additional drum programs
      "0:1": "8:1"
      "0:2": "8:2"
```

#### Priority and Loading Order

When multiple soundfonts contain the same program:
1. Programs are resolved by **priority** (higher priority soundfonts checked first)
2. Within the same priority, programs are resolved by **loading order**
3. Blacklisted programs are skipped entirely

```yaml
soundfonts:
  # This will be checked first (priority 10)
  - path: "/path/to/custom_pianos.sf2"
    priority: 10
    blacklist: []
    remap: {}
  
  # This will be checked second (priority 5)
  - path: "/path/to/general_user.sf2"
    priority: 5
    blacklist: []
    remap: {}
  
  # This will be checked last (priority 0, default)
  - path: "/path/to/fallback.sf2"
    priority: 0
    blacklist: []
    remap: {}
```

#### Using Multiple SoundFonts via CLI

For simple soundfont loading via command line (without advanced options):

```bash
# Load multiple soundfonts (basic paths only)
python render_midi.py --sf2 /path/to/soundfont1.sf2 --sf2 /path/to/soundfont2.sf2 input.mid
```

For advanced options (priority, blacklist, remap), use the `soundfonts` section in config.yaml.

#### Program Bank Numbers

Standard MIDI bank numbers:
- **Bank 0** (MSB=0, LSB=0): General MIDI
- **Bank 8** (MSB=0, LSB=127): Drums
- **Bank 120** (MSB=0, LSB=120): SoundFX
- **Bank 121-127**: User-defined

---

### Section 6: Per-Part Configuration (16 parts)

Each of the 16 XG parts can be configured independently:

```yaml
parts:
  part_0:
    engine: "sf2"           # Synthesis engine for this part
    program: 0              # Program number (0-127)
    bank_msb: 0            # Bank MSB
    bank_lsb: 0            # Bank LSB
    volume: 100            # Part volume (0-127)
    pan: 64                # Pan position (0-127, 64=center)
    expression: 127         # Expression (0-127)
    reverb_send: 40         # Reverb send (0-127)
    chorus_send: 0         # Chorus send (0-127)
    variation_send: 0      # Variation send (0-127)
    
    # Filter settings
    filter:
      cutoff: 127          # Filter cutoff (0-127)
      resonance: 0         # Filter resonance (0-127)
      envelope:
        attack: 0          # EG attack (0-127)
        decay: 0           # EG decay (0-127)
        sustain: 127      # EG sustain (0-127)
        release: 0         # EG release (0-127)
        
    # LFO settings
    lfo:
      lfo1:
        waveform: "sine"   # sine, triangle, sawtooth, square
        speed: 64          # LFO speed (0-127)
        pitch_depth: 0      # Pitch modulation depth (0-127)
        filter_depth: 0     # Filter modulation depth (0-127)
        amplitude_depth: 0 # Amplitude modulation depth (0-127)
```

**Engine Options per Part:**
- `sf2` - SoundFont sample playback
- `fm` - FM synthesis
- `wavetable` - Wavetable synthesis
- `physical` - Physical modeling
- `spectral` - Spectral processing

---

### Section 7: FM Engine Configuration

Full FM synthesis parameters for parts using the FM engine:

```yaml
fm:
  algorithm: 1             # FM algorithm (1-88)
  algorithm_name: "basic" # Algorithm name
  
  master_volume: 0.8       # FM master volume (0.0-1.0)
  pitch_bend_range: 2      # Pitch bend range in semitones
  
  # 8 Operators
  operators:
    op_0:
      enabled: true
      frequency_ratio: 1.0    # Frequency ratio (0.5-32.0)
      detune_cents: 0          # Detune (-100 to +100 cents)
      feedback_level: 0        # Feedback (0-7)
      waveform: "sine"         # sine, triangle, sawtooth, square
      envelope:
        levels: [0, 100, 70, 70, 0, 0, 0, 0]  # 8 levels
        rates: [10, 30, 0, 50, 0, 0, 0, 0]    # 8 rates
      key_scaling_depth: 0     # Key scaling (0-7)
      velocity_sensitivity: 0  # Velocity sensitivity (0-7)
      scaling_curve: "linear"  # linear, exp, log
    
    # Operators op_1 through op_7...
    
  # 3 Global LFOs
  lfos:
    lfo_1:
      enabled: true
      frequency: 1.0          # Hz (0.01-20)
      waveform: "sine"
      depth: 0.5              # 0.0-1.0
      phase: 0.0              # degrees
      
  # Modulation Matrix
  modulation:
    - source: "lfo1"
      destination: "pitch"
      amount: 0.5
      bipolar: true
    - source: "velocity"
      destination: "amplitude"
      amount: 0.7
      
  # Effects sends
  effects_sends:
    reverb: 0.3
    chorus: 0.2
    delay: 0.0
```

---

### Section 8: Effects Configuration

```yaml
effects:
  reverb:
    enabled: true
    type: 4              # XG reverb type (0-127)
    time: 2.5             # Reverb time in seconds
    level: 0.8            # Wet/dry mix (0-1)
    hf_damping: 0.3       # High frequency damping (0-1)
  
  chorus:
    enabled: true
    type: 1              # XG chorus type (0-7)
    rate: 0.5             # Rate in Hz
    depth: 0.6            # Depth (0-1)
    feedback: 0.5         # Feedback (0-1)
  
  variation:
    enabled: true
    type: 12             # Variation effect type (0-127)
    parameters:
      delay_time: 300     # Delay time in ms
      feedback: 0.4       # Feedback amount
      level: 0.5          # Wet/dry mix
  
  eq:
    enabled: false
    low_gain: 0.0        # dB
    low_frequency: 100   # Hz
    mid_gain: 0.0        # dB
    mid_frequency: 1000  # Hz
    mid_q: 1.0
    high_gain: 0.0       # dB
    high_frequency: 8000 # Hz
  
  compressor:
    enabled: false
    threshold: -20.0      # dB
    ratio: 4.0           # Compression ratio
    attack: 10.0         # ms
    release: 100.0       # ms
    makeup_gain: 0.0     # dB
  
  limiter:
    enabled: true
    threshold: -0.5      # dB
    release: 0.1         # seconds
```

---

### Section 9: Arpeggiator Configuration

```yaml
arpeggiator:
  enabled: false
  tempo: 120             # BPM (40-240)
  swing: 0.0             # Swing amount (-1 to 1)
  gate_time: 0.9         # Note gate time (0-1)
  velocity: 100          # Output velocity (1-127)
  octave_range: 2        # Octave range (1-8)
  
  # Per-channel pattern assignments
  channel_patterns:
    channel_0: "up"
    channel_1: "down"
    channel_2: "up_down"
    channel_3: "random"
```

**Available Patterns:**
- `up` - Ascending
- `down` - Descending
- `up_down` - Ascending then descending
- `random` - Random order

---

### Section 10: MPE Configuration

```yaml
mpe:
  enabled: true
  
  # MPE Zones
  zones:
    - zone_id: 1
      enabled: true
      lower_channel: 0      # Lower MIDI channel
      upper_channel: 7      # Upper MIDI channel
      pitch_bend_range: 48 # Pitch bend range (+/- semitones)
      timbre_cc: 74        # Timbre controller CC
      pressure_active: true # Per-note pressure
      slide_active: true    # Slide control
      lift_active: true     # Lift control
  
  # Global MPE settings
  global:
    per_note_pitch: true
    per_note_timbre: true
    per_note_pressure: true
```

---

### Section 11: Tuning Configuration

```yaml
tuning:
  temperament: "equal"    # equal, just, pythagorean, meantone, werckmeister, kirnberger, custom
  a4_frequency: 440.0   # A4 reference frequency in Hz
  global_offset: 0.0     # Global tuning offset in cents
  
  # Custom tuning (if temperament is "custom")
  custom_tuning:
    enabled: false
    notes:
      C: 0.0
      C_sharp: 0.0
      D: 0.0
      # ... all 12 notes
```

---

## Layered Configuration

The configuration system supports **layered configuration** via file includes. This allows you to:
- Split configuration into multiple files
- Reuse common configurations
- Override specific sections without modifying the base config

### How It Works

Add an `includes` key in your config.yaml to include other YAML files:

```yaml
# Main config.yaml
includes:
  - effects.yaml
  - parts/piano.yaml
  - tuning/just.yaml
```

The system will:
1. Load the main config.yaml
2. Process each included file in order
3. **Later includes override earlier ones** (precedence)
4. Nested includes are processed recursively

### Merge Rules

- **Dictionaries**: Deep merged (nested values merged)
- **Lists**: Replaced (not appended)
- **None values**: Remove the key from base config

### Example: Modular Configuration

Create a directory structure:
```
config/
  config.yaml       # Main config with includes
  effects.yaml      # Shared effects settings
  parts/
    piano.yaml      # Piano part
    bass.yaml       # Bass part
  tuning/
    equal.yaml     # Equal temperament
    just.yaml      # Just intonation
```

**config.yaml**:
```yaml
audio:
  sample_rate: 48000

includes:
  - effects.yaml
  - parts/piano.yaml
  - tuning/equal.yaml
```

**effects.yaml**:
```yaml
effects:
  reverb:
    enabled: true
    type: 4
    time: 2.0
  chorus:
    enabled: true
    type: 1
```

**parts/piano.yaml**:
```yaml
parts:
  part_0:
    engine: "sf2"
    program: 0
    volume: 100
    reverb_send: 40
```

### Override Example

Override specific values from included files:

```yaml
# config.yaml
includes:
  - effects.yaml    # Includes base effects
  - warm_reverb.yaml  # Overrides reverb settings

# warm_reverb.yaml
effects:
  reverb:
    type: 7         # Different reverb type
    time: 3.0       # Longer reverb
    level: 0.9       # More reverb
```

### Including External Presets

You can include complete preset files:

```yaml
# Include external FM patch
includes:
  - fm_patches/bright_lead.yaml

# Override just the part that uses it
parts:
  part_1:
    volume: 80
    pan: 32
```

### Relative Paths

Included file paths are resolved relative to the **including file's directory**:

```
config/
  config.yaml         # includes: parts/piano.yaml
  parts/
    piano.yaml        # includes: ../common.yaml (resolved to config/common.yaml)
```

### Debugging Includes

Check which files were included:

```python
config = ConfigManager('config.yaml')
config.load()

print(config.get_include_stack())  # List of all loaded files
print(config.get_includes())      # Includes defined in main config
```

### Using None to Remove Keys

Use `null` in YAML to remove keys from base config:

```yaml
# Remove chorus from base config
includes:
  - no_chorus.yaml

# no_chorus.yaml
effects:
  chorus: null
```

---

## Using the Configuration System

### Basic Usage

The configuration is automatically loaded when using `render_midi.py`:

```bash
python render_midi.py input.mid output.wav
```

The synthesizer automatically loads `config.yaml` from the current directory.

### Custom Configuration Path

Specify a custom config file:

```bash
python render_midi.py -c /path/to/custom_config.yaml input.mid
```

### Programmatic Usage

```python
from synth.core.config_manager import ConfigManager
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

# Load configuration
config = ConfigManager('/path/to/config.yaml')
config.load()

# Create synthesizer
synth = ModernXGSynthesizer(sample_rate=48000)

# Apply configuration
synth.configure_from_config(config)
```

### ConfigManager API

```python
# Get configuration values
sample_rate = config.get_sample_rate()
polyphony = config.get_polyphony()
volume = config.get_volume()

# Get MIDI settings
xg_enabled = config.get_xg_enabled()
gs_enabled = config.get_gs_enabled()
mpe_enabled = config.get_mpe_enabled()

# Get engine priorities
priorities = config.get_engine_priorities()

# Get part configuration
part0 = config.get_part_config(0)
part5 = config.get_part_config(5)

# Get FM configuration
fm_config = config.get_fm_config()
operators = config.get_fm_operators()

# Get effects configuration
reverb = config.get_reverb_config()
chorus = config.get_chorus_config()

# Get arpeggiator config
arp_enabled = config.get_arpeggiator_enabled()
arp_tempo = config.get_arpeggiator_tempo()

# Get MPE config
mpe_enabled = config.get_mpe_enabled()
mpe_zones = config.get_mpe_zones()

# Get tuning
temperament = config.get_temperament()
a4_freq = config.get_a4_frequency()
```

---

## Examples

### Example 1: FM Synthesis Setup

```yaml
audio:
  sample_rate: 48000
  polyphony: 64

midi:
  xg_enabled: true
  gs_enabled: false
  mpe_enabled: false

parts:
  part_0:
    engine: "fm"
    program: 0
    volume: 100
    pan: 64
    reverb_send: 30

fm:
  algorithm: 5
  operators:
    op_0:
      frequency_ratio: 1.0
      feedback_level: 3
    op_1:
      frequency_ratio: 2.0

effects:
  reverb:
    type: 4
    time: 1.5
    level: 0.6
```

### Example 2: Multi-Engine Setup

```yaml
parts:
  part_0:
    engine: "sf2"
    program: 0    # Acoustic Grand Piano
    volume: 100
    
  part_1:
    engine: "fm"
    program: 0
    volume: 80
    
  part_2:
    engine: "wavetable"
    program: 5
    volume: 90
    
  part_8:
    engine: "sf2"
    program: 0    # Drums
    volume: 110
    reverb_send: 50
```

### Example 3: MPE Expressive Setup

```yaml
midi:
  xg_enabled: true
  mpe_enabled: true

mpe:
  enabled: true
  zones:
    - zone_id: 1
      lower_channel: 0
      upper_channel: 7
      pitch_bend_range: 48
      pressure_active: true
      slide_active: true

tuning:
  temperament: "just"
  a4_frequency: 432.0
```

---

## Best Practices

1. **Keep config.yaml in project root** - The system automatically finds it there
2. **Use descriptive comments** - Document your custom configurations
3. **Start with defaults** - Modify only what you need
4. **Test incrementally** - Make small changes and test frequently
5. **Version control** - Track config changes in git

---

## Troubleshooting

### Config not loading
- Verify `config.yaml` exists in the correct location
- Check YAML syntax (use a validator)
- Ensure file permissions allow reading

### Settings not applied
- Verify the synth engine supports the setting
- Check that required dependencies are installed
- Ensure config values are within valid ranges

### Performance issues
- Reduce `polyphony` if experiencing CPU overload
- Increase `block_size` for better performance (at cost of latency)
- Disable unused effects in the `effects` section
