# MIDI 2.0 API Reference

This document provides comprehensive API documentation for the MIDI 2.0 features implemented in the XG Synthesizer.

## Table of Contents
1. [Universal MIDI Packet (UMP) System](#ump-system)
2. [32-bit Parameter Control](#32-bit-parameter-control)
3. [Per-Note Controllers](#per-note-controllers)
4. [MPE+ Extensions](#mpe-extensions)
5. [XG Effects Integration](#xg-effects-integration)
6. [Profile Configuration System](#profile-configuration-system)

## UMP System

### UMPParser Class

The `UMPParser` class handles parsing of Universal MIDI Packets according to the MIDI 2.0 specification.

#### Methods

**`parse_packet_stream(data: bytes) -> List[UMPPacket]`**
- **Description**: Parses a stream of UMP packets from raw bytes
- **Parameters**: 
  - `data`: Raw bytes containing UMP packets
- **Returns**: List of parsed UMP packet objects
- **Example**:
```python
parser = UMPParser()
packets = parser.parse_packet_stream(raw_data)
```

**`create_packet(ump_type: int, group: int, message_type: int, channel: int, data_word_1: int, data_word_2: int) -> UMPPacket`**
- **Description**: Creates a UMP packet with specified parameters
- **Parameters**:
  - `ump_type`: UMP type (0x2 for MIDI 2.0 Channel Voice)
  - `group`: Group number (0-15)
  - `message_type`: MIDI message type (0x8-0xE)
  - `channel`: MIDI channel (0-15)
  - `data_word_1`: First 32-bit data word
  - `data_word_2`: Second 32-bit data word
- **Returns**: Constructed UMPPacket object

### MIDI2ChannelVoicePacket Class

Represents a MIDI 2.0 Channel Voice message with 32-bit parameter resolution.

#### Properties
- `ump_type`: UMP packet type (0x2 for MIDI 2.0 Channel Voice)
- `group`: Group number (0-15)
- `message_type`: MIDI message type (0x8-0xE)
- `channel`: MIDI channel (0-15)
- `data_word_1`: First 32-bit data word
- `data_word_2`: Second 32-bit data word

#### Methods

**`get_note() -> int`**
- **Description**: Gets the note number from the packet
- **Returns**: MIDI note number (0-127)

**`get_velocity() -> int`**
- **Description**: Gets the velocity from the packet
- **Returns**: Velocity value (0-127 for MIDI 1.0 compatibility, full 32-bit for MIDI 2.0)

**`get_pitch_bend_value() -> int`**
- **Description**: Gets the pitch bend value from the packet
- **Returns**: 32-bit pitch bend value

## 32-bit Parameter Control

### AdvancedParameterController Class

Manages 32-bit parameter control with per-note capabilities.

#### Methods

**`set_parameter_value(name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets a parameter value with specified resolution
- **Parameters**:
  - `name`: Parameter name
  - `value`: Parameter value (0.0-1.0 normalized)
  - `resolution`: Parameter resolution ('7bit', '14bit', '32bit')
- **Example**:
```python
controller.set_parameter_value('filter_cutoff', 0.7, resolution='32bit')
```

**`get_parameter_value(name: str) -> float`**
- **Description**: Gets the current value of a parameter
- **Parameters**:
  - `name`: Parameter name
- **Returns**: Current parameter value (0.0-1.0)

**`set_per_note_parameter(note: int, param_name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets a per-note parameter value
- **Parameters**:
  - `note`: MIDI note number (0-127)
  - `param_name`: Parameter name
  - `value`: Parameter value (0.0-1.0)
  - `resolution`: Parameter resolution
- **Example**:
```python
controller.set_per_note_parameter(60, 'expression', 0.8, resolution='32bit')
```

**`get_per_note_parameter(note: int, param_name: str) -> float`**
- **Description**: Gets a per-note parameter value
- **Parameters**:
  - `note`: MIDI note number
  - `param_name`: Parameter name
- **Returns**: Parameter value for the specified note

**`add_parameter_mapping(source: str, destination: str, curve: str = 'linear', sensitivity: float = 1.0)`**
- **Description**: Adds a parameter mapping from source to destination
- **Parameters**:
  - `source`: Source parameter name
  - `destination`: Destination parameter name
  - `curve`: Response curve ('linear', 'log', 'exp', 'sine', 'cosine')
  - `sensitivity`: Sensitivity multiplier
- **Returns**: Mapping ID
- **Example**:
```python
mapping_id = controller.add_parameter_mapping('mod_wheel', 'filter_cutoff', curve='linear', sensitivity=0.5)
```

## Per-Note Controllers

### Per-Note Controller Support

The system supports per-note controllers for expressive MIDI 2.0 performance:

#### Available Per-Note Parameters
- `per_note_pitch_bend`: Per-note pitch bend (±24 semitones)
- `per_note_mod_wheel`: Per-note modulation wheel
- `per_note_expression`: Per-note expression
- `per_note_brightness`: Per-note brightness/filter cutoff
- `per_note_harmonic_content`: Per-note harmonic content
- `per_note_pan`: Per-note pan position
- `per_note_pressure`: Per-note pressure (aftertouch)
- `per_note_timbre`: Per-note timbre
- `per_note_custom_1`: Custom per-note parameter 1
- `per_note_custom_2`: Custom per-note parameter 2

#### Methods

**`set_per_note_controller(note: int, controller_name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets a per-note controller value
- **Parameters**:
  - `note`: MIDI note number
  - `controller_name`: Name of the per-note controller
  - `value`: Controller value (0.0-1.0)
  - `resolution`: Controller resolution
- **Example**:
```python
channel.set_per_note_controller(60, 'per_note_expression', 0.9, resolution='32bit')
```

## MPE+ Extensions

### MPE+ Configuration

The system supports MPE+ (MIDI Polyphonic Expression Plus) extensions with enhanced per-note control.

#### Methods

**`enable_mpe_plus(master_channel: int = 0, first_note_channel: int = 1, last_note_channel: int = 15, layout: str = 'horizontal')`**
- **Description**: Enables MPE+ mode for the channel
- **Parameters**:
  - `master_channel`: Channel controlling global parameters (pitch bend, pressure)
  - `first_note_channel`: First channel for note data
  - `last_note_channel`: Last channel for note data
  - `layout`: Channel layout ('horizontal' or 'vertical')
- **Example**:
```python
channel.enable_mpe_plus(master_channel=15, first_note_channel=1, last_note_channel=14, layout='horizontal')
```

**`disable_mpe_plus()`**
- **Description**: Disables MPE+ mode for the channel

**`process_mpe_note_on(note: int, velocity: int, channel_offset: int = 0)`**
- **Description**: Processes an MPE+ note-on event
- **Parameters**:
  - `note`: MIDI note number
  - `velocity`: Note velocity
  - `channel_offset`: Channel offset for MPE+ processing

**`process_mpe_note_off(note: int, velocity: int = 64, channel_offset: int = 0)`**
- **Description**: Processes an MPE+ note-off event
- **Parameters**:
  - `note`: MIDI note number
  - `velocity`: Note-off velocity
  - `channel_offset`: Channel offset for MPE+ processing

## XG Effects Integration

### XGMIDIEffectsProcessor Class

Manages XG-specific effects with MIDI 2.0 parameter resolution.

#### Methods

**`set_xg_parameter(effect_slot: str, param_name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets an XG effect parameter with specified resolution
- **Parameters**:
  - `effect_slot`: Effect slot identifier ('system_reverb', 'variation', 'insertion_N')
  - `param_name`: Parameter name
  - `value`: Parameter value (0.0-1.0)
  - `resolution`: Parameter resolution
- **Example**:
```python
effects_processor.set_xg_parameter('system_reverb', 'time', 3.5, resolution='32bit')
```

**`set_per_note_xg_parameter(note: int, effect_slot: str, param_name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets a per-note XG effect parameter
- **Parameters**:
  - `note`: MIDI note number
  - `effect_slot`: Effect slot identifier
  - `param_name`: Parameter name
  - `value`: Parameter value
  - `resolution`: Parameter resolution

**`add_insertion_effect(effect_type: XGEffectType) -> int`**
- **Description**: Adds an insertion effect to the chain
- **Parameters**:
  - `effect_type`: Type of insertion effect to add
- **Returns**: Index of the added effect

**`process_audio_with_xg_effects(audio_input: np.ndarray, part: int = 0, note: int = None) -> np.ndarray`**
- **Description**: Processes audio through the XG effects chain
- **Parameters**:
  - `audio_input`: Input audio as numpy array
  - `part`: Part number for part-specific processing
  - `note`: Note number for per-note processing
- **Returns**: Processed audio as numpy array

### XG Effect Types

The system supports various XG effect types:

#### System Effects
- `REVERB_PLATE`, `REVERB_HALL`, `REVERB_ROOM`, `REVERB_STUDIO`, `REVERB_GATED`, `REVERB_REVERSE`, `REVERB_SHORT`, `REVERB_LONG`
- `CHORUS_STANDARD`, `CHORUS_FLANGER`, `CHORUS_CELESTE`, `CHORUS_DETUNE`, `CHORUS_DIMENSION`

#### Variation Effects
- `VARIATION_MULTI_CHORUS`, `VARIATION_STEREO_DELAY`, `VARIATION_TREMOLO`, `VARIATION_AUTO_PANNER`, `VARIATION_PHASER`, `VARIATION_FLANGER`, `VARIATION_ROTARY_SPEAKER`, `VARIATION_DISTORTION`, `VARIATION_COMPRESSOR`, `VARIATION_GATE`, `VARIATION_EQ`, `VARIATION_FILTER`, `VARIATION_OCTAVE`, `VARIATION_PITCH_SHIFTER`, `VARIATION_FEEDBACK_DELAY`, `VARIATION_LOFI`

#### Insertion Effects
- `INSERT_DUAL_DELAY`, `INSERT_STEREO_DELAY`, `INSERT_MULTI_TAP_DELAY`, `INSERT_CROSS_DELAY`, `INSERT_MOD_DELAY`, `INSERT_STEREO_CHORUS`, `INSERT_MONO_CHORUS`, `INSERT_MULTI_CHORUS`, `INSERT_STEREO_FLANGER`, `INSERT_MONO_FLANGER`, `INSERT_STEREO_PHASER`, `INSERT_MONO_PHASER`, `INSERT_STEREO_TREMOLO`, `INSERT_MONO_TREMOLO`, `INSERT_AUTO_PANNER`, `INSERT_ROTARY_SPEAKER`, `INSERT_DISTORTION`, `INSERT_OVERDRIVE`, `INSERT_AMP_SIMULATOR`, `INSERT_COMPRESSOR`, `INSERT_LIMITER`, `INSERT_GATE`, `INSERT_EXPANDER`, `INSERT_EQ_3_BAND`, `INSERT_EQ_5_BAND`, `INSERT_EQ_7_BAND`, `INSERT_EQ_15_BAND`, `INSERT_EQ_PARAMETRIC`, `INSERT_FILTER_LOW_PASS`, `INSERT_FILTER_HIGH_PASS`, `INSERT_FILTER_BAND_PASS`, `INSERT_FILTER_NOTCH`, `INSERT_FILTER_FORMANT`, `INSERT_FILTER_WOW_FLUTTER`, `INSERT_PITCH_SHIFTER`, `INSERT_MONO_TO_STEREO`, `INSERT_SIX_BAND_EQ`, `INSERT_DRIVE`, `INSERT_TALK_MODULATOR`, `INSERT_ENSEMBLE`, `INSERT_HARMONIZER`, `INSERT_ACOUSTIC_SIMULATOR`, `INSERT_CROSSOVER`, `INSERT_LOFI`, `INSERT_VOCODER`, `INSERT_GRANULAR`, `INSERT_SPECTRAL`, `INSERT_CONVOLUTION_REVERB`

## Profile Configuration System

### ProfileConfigurationSystem Class

Manages MIDI 2.0 profile configuration and capability discovery.

#### Methods

**`negotiate_profile(port: int, requested_profile: MIDIProfile) -> MIDIProfile`**
- **Description**: Negotiates a profile for a port with fallback capabilities
- **Parameters**:
  - `port`: MIDI port number
  - `requested_profile`: Profile requested by client
- **Returns**: Negotiated profile (may differ from requested)

**`discover_capabilities(port: int, device_identifier: str = "") -> Dict[str, Any]`**
- **Description**: Discovers comprehensive device capabilities
- **Parameters**:
  - `port`: MIDI port number
  - `device_identifier`: Optional device identifier for specific discovery
- **Returns**: Dictionary containing comprehensive device capabilities

**`get_profile_capabilities(profile: MIDIProfile) -> ProfileCapabilities`**
- **Description**: Gets capabilities for a specific profile
- **Parameters**:
  - `profile`: MIDI profile
- **Returns**: Profile capabilities object

### ProfileCapabilities Class

Describes the capabilities of a MIDI profile.

#### Properties
- `profile_id`: Profile identifier
- `max_channels`: Maximum supported channels
- `max_polyphony`: Maximum supported polyphony
- `supports_32bit_resolution`: Whether 32-bit resolution is supported
- `supports_per_note_controllers`: Whether per-note controllers are supported
- `supports_mpe`: Whether MPE is supported
- `supports_sysex_7`: Whether 7-bit sysex is supported
- `supports_property_exchange`: Whether property exchange is supported
- `supported_message_types`: Set of supported message types

## Voice Instance with MIDI 2.0 Support

### VoiceInstance Class

Enhanced voice instance with MIDI 2.0 features.

#### Methods

**`set_per_note_parameter(note: int, param_name: str, value: float)`**
- **Description**: Sets a per-note parameter for this voice
- **Parameters**:
  - `note`: MIDI note number
  - `param_name`: Parameter name
  - `value`: Parameter value

**`get_per_note_parameter(note: int, param_name: str) -> float`**
- **Description**: Gets a per-note parameter value
- **Parameters**:
  - `note`: MIDI note number
  - `param_name`: Parameter name
- **Returns**: Parameter value

**`update_per_note_modulation(modulation_updates: Dict[str, float])`**
- **Description**: Updates per-note modulation parameters
- **Parameters**:
  - `modulation_updates`: Dictionary of modulation parameter updates

## Channel with MIDI 2.0 Support

### Channel Class

Enhanced channel with full MIDI 2.0 support.

#### Methods

**`control_change(controller: int, value: int, is_32bit: bool = False)`**
- **Description**: Handles control change with 32-bit support
- **Parameters**:
  - `controller`: Controller number (0-127)
  - `value`: Controller value
  - `is_32bit`: Whether this is a 32-bit value

**`pitch_bend(lsb: int, msb: int, pitch_32bit: int = None)`**
- **Description**: Handles pitch bend with 32-bit support
- **Parameters**:
  - `lsb`: Pitch bend LSB (0-127) for MIDI 1.0
  - `msb`: Pitch bend MSB (0-127) for MIDI 1.0
  - `pitch_32bit`: 32-bit pitch bend value for MIDI 2.0 (optional)

**`key_pressure(note: int, pressure: int, pressure_32bit: int = None)`**
- **Description**: Handles polyphonic key pressure with 32-bit support
- **Parameters**:
  - `note`: MIDI note number (0-127)
  - `pressure`: 7-bit pressure value (0-127) for MIDI 1.0
  - `pressure_32bit`: 32-bit pressure value for MIDI 2.0 (optional)

## File Parser with MIDI 2.0 Support

### FileParser Class

Enhanced MIDI file parser with UMP support.

#### Methods

**`parse_file(filename: str) -> List[MIDIMessage]`**
- **Description**: Parses a MIDI file with support for both SMF and UMP formats
- **Parameters**:
  - `filename`: Path to MIDI file (.mid or .ump)
- **Returns**: List of parsed MIDIMessage objects

**`discover_capabilities(filename: str) -> Dict[str, Any]`**
- **Description**: Discovers capabilities from a MIDI file
- **Parameters**:
  - `filename`: Path to MIDI file
- **Returns**: Dictionary of file capabilities

## Real-time Parser with MIDI 2.0 Support

### RealtimeParser Class

Enhanced real-time MIDI parser with UMP support.

#### Methods

**`parse_bytes(data: bytes) -> List[MIDIMessage]`**
- **Description**: Parses raw MIDI bytes with support for both MIDI 1.0 and MIDI 2.0 UMP formats
- **Parameters**:
  - `data`: Raw MIDI byte data
- **Returns**: List of parsed MIDIMessage objects

## Effects with MIDI 2.0 Support

### MIDIEffectsProcessor Class

Advanced effects processor with MIDI 2.0 support.

#### Methods

**`set_per_note_parameter(note: int, effect_type: EffectType, param_name: str, value: float, resolution: str = '32bit')`**
- **Description**: Sets a per-note parameter for an effect
- **Parameters**:
  - `note`: MIDI note number
  - `effect_type`: Type of effect
  - `param_name`: Parameter name
  - `value`: Parameter value
  - `resolution`: Parameter resolution

**`get_per_note_parameter(note: int, effect_type: EffectType, param_name: str) -> float`**
- **Description**: Gets a per-note parameter value for an effect
- **Parameters**:
  - `note`: MIDI note number
  - `effect_type`: Type of effect
  - `param_name`: Parameter name
- **Returns**: Parameter value

## Constants and Enums

### MIDIProfile Enum

Defines MIDI 2.0 profile types:

```python
class MIDIProfile(IntEnum):
    # Basic Profiles
    GENERAL_MIDI_1 = 0x0000
    GENERAL_MIDI_2 = 0x0001
    XG_FULL = 0x0002
    GS_STANDARD = 0x0003
    
    # Advanced Profiles
    MPE_STANDARD = 0x0010
    DAW_CONTROL = 0x0011
    STUDIO_SET = 0x0012
    SYNTHESIZER = 0x0013
    SOUND_MODULE = 0x0014
    CONTROLLER = 0x0015
    PLAYER = 0x0016
    TONE_GENERATOR = 0x0017
```

### ParameterResolution Enum

Defines parameter resolution types:

```python
class ParameterResolution(IntEnum):
    MIDI_1_7_BIT = 7      # Standard MIDI 1.0 (7-bit)
    MIDI_1_14_BIT = 14    # MIDI 1.0 with LSB (14-bit)
    MIDI_2_32_BIT = 32    # MIDI 2.0 (32-bit)
    MIDI_2_64_BIT = 64    # MIDI 2.0 extended (64-bit)
```

## Best Practices

### Using 32-bit Parameters
When working with 32-bit parameters, always specify the resolution:

```python
# Good: Explicitly specify 32-bit resolution
controller.set_parameter_value('filter_cutoff', 0.7, resolution='32bit')

# Good: Use the parameter resolution enum
from synth.midi.types import ParameterResolution
controller.set_parameter_value('resonance', 0.5, resolution=ParameterResolution.MIDI_2_32_BIT)
```

### Per-Note Control
Take advantage of per-note controllers for expressive performance:

```python
# Set per-note expression for individual control
for note in [60, 62, 64, 65, 67]:  # C, D, E, F, G
    controller.set_per_note_parameter(note, 'expression', 0.8 + (note % 5) * 0.05)
```

### MPE+ Mode
Use MPE+ for expressive polyphonic performance:

```python
# Enable MPE+ for expressive control
channel.enable_mpe_plus(
    master_channel=15,           # Channel 16 controls global parameters
    first_note_channel=1,        # Channels 1-14 for note data
    last_note_channel=14,
    layout='horizontal'          # Horizontal ribbon layout
)
```

### Profile Configuration
Always negotiate profiles for optimal compatibility:

```python
# Negotiate the best profile for your needs
negotiated_profile = profile_configurator.negotiate_profile(
    port=0, 
    requested_profile=MIDIProfile.GENERAL_MIDI_2
)
```

This API reference provides comprehensive documentation for all MIDI 2.0 features implemented in the XG Synthesizer, enabling developers to leverage the full power of MIDI 2.0 in their applications.