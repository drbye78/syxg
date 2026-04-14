# MIDI 2.0 API Reference

This document provides comprehensive API documentation for the MIDI 2.0 features implemented in the XG Synthesizer.

## Table of Contents
1. [Universal MIDI Packet (UMP) System](#ump-system)
2. [32-bit Parameter Control](#32-bit-parameter-control)
3. [Per-Note Controllers](#per-note-controllers)
4. [MPE+ Extensions](#mpe-extensions)
5. [XG Effects Integration](#xg-effects-integration)
6. [Profile Configuration System](#profile-configuration-system)
7. [Capability Discovery](#capability-discovery)

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

### XGMIDI2EffectsProcessor Class

Manages XG-specific effects with MIDI 2.0 parameter resolution.

#### Methods

**`set_xg_parameter(parameter_address: int, value: int, resolution_bits: int = 32)`**
- **Description**: Sets an XG parameter with specified resolution
- **Parameters**:
  - `parameter_address`: XG parameter address
  - `value`: Parameter value
  - `resolution_bits`: Parameter resolution (7, 14, or 32)
- **Example**:
```python
effects_processor.set_xg_parameter(0x000000, 5, resolution_bits=32)  # Set reverb type
```

**`set_per_note_effect_parameter(note: int, effect_id: int, param_name: str, value: float)`**
- **Description**: Sets a per-note effect parameter
- **Parameters**:
  - `note`: MIDI note number
  - `effect_id`: Effect identifier
  - `param_name`: Parameter name
  - `value`: Parameter value (0.0-1.0)

**`create_effect(effect_type: MIDI2EffectType) -> Optional[int]`**
- **Description**: Creates a new effect instance
- **Parameters**:
  - `effect_type`: Type of effect to create
- **Returns**: Effect ID or None if creation failed

**`enable_effect(effect_id: int) -> bool`**
- **Description**: Enables an effect
- **Parameters**:
  - `effect_id`: Effect identifier
- **Returns**: True if effect was enabled successfully

**`set_effect_parameter(effect_id: int, param_name: str, value: float, resolution_bits: int = 32)`**
- **Description**: Sets an effect parameter with specified resolution
- **Parameters**:
  - `effect_id`: Effect identifier
  - `param_name`: Parameter name
  - `value`: Parameter value (0.0-1.0)
  - `resolution_bits`: Parameter resolution
- **Example**:
```python
effects_processor.set_effect_parameter(reverb_id, 'time', 2.5, resolution_bits=32)
```

### XG Effect Types

The system supports various XG effect types with MIDI 2.0 resolution:

#### System Effects
- `REVERB_HALL_32BIT`, `REVERB_ROOM_32BIT`, `REVERB_PLATE_32BIT`, `REVERB_CHAMBER_32BIT`, `REVERB_SPRING_32BIT`, `REVERB_CONVOLUTION_32BIT`
- `CHORUS_STANDARD_32BIT`, `CHORUS_FLANGER_32BIT`, `CHORUS_CELESTE_32BIT`, `CHORUS_DIMENSION_32BIT`, `CHORUS_ENSEMBLE_32BIT`
- `DELAY_STEREO_32BIT`, `DELAY_MULTI_TAP_32BIT`, `DELAY_CROSS_32BIT`, `DELAY_MODULATED_32BIT`, `DELAY_ANALOG_32BIT`, `DELAY_DIGITAL_32BIT`

#### Per-Note Effects
- `PER_NOTE_REVERB_SEND_32BIT`, `PER_NOTE_CHORUS_SEND_32BIT`, `PER_NOTE_DELAY_SEND_32BIT`, `PER_NOTE_DISTORTION_SEND_32BIT`
- `PER_NOTE_FILTER_CUTOFF_32BIT`, `PER_NOTE_FILTER_RESONANCE_32BIT`, `PER_NOTE_PAN_32BIT`, `PER_NOTE_WIDTH_32BIT`

#### Advanced Effects
- `PITCH_SHIFTER_32BIT`, `HARMONIZER_32BIT`, `VOCODER_32BIT`, `RING_MODULATOR_32BIT`, `CONVOLUTION_REVERB_32BIT`

## Profile Configuration System

### ProfileConfigurationSystem Class

Manages MIDI 2.0 profile configuration and capability discovery.

#### Methods

**`negotiate_profile(port: int, requested_profile: MIDIProfile) -> Tuple[MIDIProfile, Dict[str, Any]]`**
- **Description**: Negotiates a profile for a port with fallback capabilities
- **Parameters**:
  - `port`: MIDI port number
  - `requested_profile`: Profile requested by client
- **Returns**: Tuple of (negotiated_profile, capabilities_dict)

**`set_port_profile(port: int, profile: MIDIProfile) -> bool`**
- **Description**: Sets a specific profile for a port
- **Parameters**:
  - `port`: MIDI port number
  - `profile`: Profile to assign
- **Returns**: True if profile was set successfully

**`get_port_profile(port: int) -> Optional[MIDIProfile]`**
- **Description**: Gets the profile assigned to a port
- **Parameters**:
  - `port`: MIDI port number
- **Returns**: Profile assigned to the port or None

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

## Capability Discovery

### CapabilityDiscoverySystem Class

Discovers and reports device capabilities with comprehensive interrogation.

#### Methods

**`discover_device_capabilities(device_id: str, device_type: str = 'auto') -> Dict[CapabilityType, Any]`**
- **Description**: Discovers capabilities of a MIDI device
- **Parameters**:
  - `device_id`: Unique identifier for the device
  - `device_type`: Type of device ('xg', 'gm', 'gs', 'mpe', 'auto')
- **Returns**: Dictionary of discovered capabilities

**`get_device_summary(device_id: str) -> Dict[str, Any]`**
- **Description**: Gets a summary of device capabilities
- **Parameters**:
  - `device_id`: Device identifier
- **Returns**: Summary dictionary of key capabilities

**`query_capability(device_id: str, capability_type: CapabilityType) -> Optional[Any]`**
- **Description**: Queries a specific capability of a device
- **Parameters**:
  - `device_id`: Device identifier
  - `capability_type`: Type of capability to query
- **Returns**: Capability value or None if not supported/discovered

### CapabilityType Enum

Defines types of capabilities that can be discovered:

```python
class CapabilityType(IntEnum):
    MIDI_VERSION = 0x01
    MAX_CHANNELS = 0x02
    MAX_POLYPHONY = 0x03
    PARAMETER_RESOLUTION = 0x04
    PER_NOTE_CONTROLLERS = 0x05
    MPE_SUPPORT = 0x06
    SYSEX_7_SUPPORT = 0x07
    PROPERTY_EXCHANGE = 0x08
    PROFILE_CONFIG = 0x09
    UMP_STREAMS = 0x0A
    JITTER_REDUCTION = 0x0B
    MIXED_DATA_SETS = 0x0C
    SUPPORTED_MESSAGES = 0x0D
    EFFECTS_CAPABILITIES = 0x0E
    # ... additional capability types
```

## Constants and Enums

### Parameter Resolution Options

The system supports multiple parameter resolution options:

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
controller.set_parameter_value('filter_cutoff', 0.7, resolution_bits=32)

# Good: Use the parameter resolution enum
from synth.midi.types import ParameterResolution
controller.set_parameter_value('resonance', 0.5, resolution=ParameterResolution.MIDI_2_32_BIT)
```

### Per-Note Control
Take advantage of per-note controllers for expressive performance:

```python
# Set per-note expression for individual control
for note in [60, 62, 64, 65, 67]:  # C, D, E, F, G
    controller.set_per_note_parameter(note, 'expression', 0.8 + (note % 5) * 0.05, resolution_bits=32)
```

### MPE+ Mode
Use MPE+ for expressive polyphonic performance:

```python
# Enable MPE+ for expressive control
channel.enable_mpe_plus(
    master_channel=15,           # Channel 16 controls global parameters
    first_note_channel=1,        # Channels 1-15 for note data
    last_note_channel=15,
    layout='horizontal'          # Horizontal ribbon layout
)
```

### Profile Configuration
Always negotiate profiles for optimal compatibility:

```python
# Negotiate the best profile for your needs
negotiated_profile, capabilities = profile_configurator.negotiate_profile(
    port=0, 
    requested_profile=MIDIProfile.GENERAL_MIDI_2
)
```

This API reference provides comprehensive documentation for all MIDI 2.0 features implemented in the XG Synthesizer, enabling developers to leverage the full power of MIDI 2.0 in their applications.