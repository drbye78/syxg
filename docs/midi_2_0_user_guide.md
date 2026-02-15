# MIDI 2.0 User Guide for XG Synthesizer

This guide explains how to use the advanced MIDI 2.0 features in the XG Synthesizer, including 32-bit parameter control, per-note controllers, MPE+ extensions, and XG effects integration.

## Table of Contents
1. [Introduction to MIDI 2.0 in XG](#introduction-to-midi-20-in-xg)
2. [Setting Up MIDI 2.0](#setting-up-midi-20)
3. [32-bit Parameter Control](#32-bit-parameter-control)
4. [Per-Note Controllers](#per-note-controllers)
5. [MPE+ Extensions](#mpe-extensions)
6. [XG Effects with MIDI 2.0](#xg-effects-with-midi-20)
7. [Profile Configuration](#profile-configuration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Introduction to MIDI 2.0 in XG

MIDI 2.0 brings revolutionary improvements to the XG Synthesizer with:

- **32-bit Parameter Resolution**: 4.2 billion possible values vs 127 in MIDI 1.0
- **Per-Note Controllers**: Individual control of parameters per note
- **MPE+ Extensions**: Enhanced MPE with 32-bit resolution
- **Profile Configuration**: Automatic device capability negotiation
- **Enhanced Effects**: Professional-grade effects with high-resolution control

### Key Improvements Over MIDI 1.0

1. **Ultra-Precise Control**: 32-bit resolution eliminates quantization artifacts
2. **Expressive Performance**: Per-note controllers enable unprecedented expressiveness
3. **Automatic Compatibility**: Profile negotiation ensures optimal device compatibility
4. **Future-Proof**: Architecture ready for upcoming MIDI specifications

## Setting Up MIDI 2.0

### Prerequisites
- MIDI 2.0 compatible hardware or software
- XG Synthesizer with MIDI 2.0 support enabled
- Understanding of basic MIDI concepts

### Enabling MIDI 2.0 Support
MIDI 2.0 support is enabled by default in the XG Synthesizer. To verify it's active:

```python
from synth.synthesizer import XGSynthesizer

synth = XGSynthesizer()
print(f"MIDI 2.0 enabled: {synth.midi_2_enabled}")
print(f"32-bit parameter support: {synth.supports_32bit_parameters}")
print(f"Per-note controller support: {synth.supports_per_note_controllers}")
```

### Basic MIDI 2.0 Message Sending
Sending MIDI 2.0 messages is similar to MIDI 1.0 but with higher resolution:

```python
# Standard MIDI 1.0 (7-bit resolution)
synth.send_midi_message([0x90, 60, 100])  # Note On, C4, velocity 100

# MIDI 2.0 with 32-bit resolution (using UMP format)
from synth.midi.ump_packets import MIDI2ChannelVoicePacket

# Create a MIDI 2.0 Note On with full 32-bit velocity resolution
note_on_packet = MIDI2ChannelVoicePacket(
    ump_type=0x2,  # MIDI 2.0 Channel Voice
    group=0,
    message_type=0x9,  # Note On
    channel=0,
    data_word_1=(60 << 24) | (0x7F << 16),  # Note 60, unused
    data_word_2=(0x7FFFFFFF << 0)  # Maximum 32-bit velocity
)

# Send the packet
synth.send_ump_packet(note_on_packet)
```

## 32-bit Parameter Control

### Understanding 32-bit Resolution
MIDI 2.0 introduces 32-bit parameter resolution, providing over 4 billion possible values compared to MIDI 1.0's 128 values. This enables:

- Ultra-smooth parameter transitions
- Precise control over synthesis parameters
- Elimination of quantization artifacts
- Professional-grade parameter automation

### Setting 32-bit Parameters
You can set 32-bit parameters using the AdvancedParameterController:

```python
from synth.midi.advanced_parameter_control import AdvancedParameterController

param_controller = AdvancedParameterController()

# Set a parameter with 32-bit resolution
param_controller.set_parameter_value('filter_cutoff', 0.7532, resolution='32bit')

# Set a parameter with explicit 32-bit value
param_controller.set_parameter_value('resonance', 0x7FFFFFFF, resolution='32bit_raw')
```

### Parameter Mapping
Create sophisticated parameter mappings between controllers and synthesis parameters:

```python
# Map mod wheel to filter cutoff with custom curve
mapping_id = param_controller.add_parameter_mapping(
    source='mod_wheel',
    destination='filter_cutoff',
    min_value=0.1,      # Minimum filter cutoff
    max_value=0.9,      # Maximum filter cutoff
    curve='exponential', # Exponential response curve
    sensitivity=0.8      # Sensitivity factor
)

# Remove the mapping later if needed
param_controller.remove_parameter_mapping(mapping_id)
```

### Working with Controller Values
The system automatically handles conversion between different resolutions:

```python
# Set a 7-bit controller value (MIDI 1.0)
param_controller.set_parameter_value('mod_wheel', 64, resolution='7bit')
# The system internally converts to 32-bit equivalent

# Set a 14-bit controller value (MIDI 1.0 with LSB)
param_controller.set_parameter_value('pitch_bend_range', 8192, resolution='14bit')
# The system internally converts to 32-bit equivalent

# Set a 32-bit controller value (MIDI 2.0 native)
param_controller.set_parameter_value('timbre', 0x3F7F0000, resolution='32bit')
```

## Per-Note Controllers

### Introduction to Per-Note Control
Per-note controllers allow individual control of parameters for each note being played, enabling unprecedented expressiveness:

- Individual pitch bend per note
- Per-note pressure and timbre
- Note-specific effects parameters
- Polyphonic aftertouch with 32-bit resolution

### Setting Per-Note Parameters
Use the per-note parameter system to control individual notes:

```python
# Set per-note expression for specific notes
for note in [60, 62, 64, 65, 67, 69, 71, 72]:  # C major scale
    # Higher notes get more expression
    expression_value = 0.5 + (note - 60) * 0.05
    param_controller.set_per_note_parameter(
        note=note,
        param_name='expression',
        value=min(expression_value, 1.0),  # Clamp to 1.0 max
        resolution='32bit'
    )

# Set per-note timbre for each note in a chord
chord_notes = [60, 64, 67, 71]  # C major 7th chord
for i, note in enumerate(chord_notes):
    # Different timbre for each note in the chord
    timbre_value = 0.3 + i * 0.2
    param_controller.set_per_note_parameter(
        note=note,
        param_name='timbre',
        value=timbre_value,
        resolution='32bit'
    )
```

### Per-Note Pitch Bend
MIDI 2.0 supports per-note pitch bend for expressive polyphonic performance:

```python
# Apply different pitch bends to different notes
param_controller.set_per_note_parameter(60, 'per_note_pitch_bend', 2.0)  # 2 semitones up
param_controller.set_per_note_parameter(64, 'per_note_pitch_bend', -1.5)  # 1.5 semitones down
param_controller.set_per_note_parameter(67, 'per_note_pitch_bend', 0.5)  # 0.5 semitones up
```

### Per-Note Effects Control
Control effects parameters on a per-note basis:

```python
# Apply different reverb sends to different notes
for note in [60, 62, 64]:
    # Higher notes get more reverb
    reverb_send = 0.2 + (note - 60) * 0.1
    param_controller.set_per_note_parameter(
        note=note,
        param_name='reverb_send',
        value=reverb_send,
        resolution='32bit'
    )

# Set per-note chorus depth
param_controller.set_per_note_parameter(72, 'chorus_depth', 0.8, resolution='32bit')
```

## MPE+ Extensions

### Understanding MPE+
MPE+ (MIDI Polyphonic Expression Plus) extends the standard MPE specification with additional capabilities:

- Enhanced per-note parameter control
- 32-bit resolution for all MPE parameters
- Advanced channel mapping options
- Integration with XG effects

### Enabling MPE+ Mode
Activate MPE+ mode for expressive polyphonic performance:

```python
from synth.channel.channel import Channel

# Get a channel instance
channel = synth.get_channel(0)

# Enable MPE+ mode
channel.enable_mpe_plus(
    master_channel=15,           # Channel 16 controls global parameters
    first_note_channel=1,        # Channels 1-14 for note data
    last_note_channel=14,
    layout='horizontal'          # Horizontal ribbon layout (pitch = X, pressure = Y)
)

# You can also use vertical layout (pitch = Y, pressure = X)
channel.enable_mpe_plus(
    master_channel=15,
    first_note_channel=1,
    last_note_channel=14,
    layout='vertical'
)
```

### MPE+ Performance Techniques
Once MPE+ is enabled, you can perform expressive techniques:

```python
# Send MPE+ compatible messages
# Note on with initial pressure
synth.send_midi_message([0x91, 60, 100])  # Channel 1 (note channel)

# Apply per-note pitch bend (channel 1)
synth.send_midi_message([0xE1, 0x00, 0x40])  # Center pitch bend on channel 1

# Apply per-note pressure (channel 1)
synth.send_midi_message([0xD1, 96])  # Channel pressure on channel 1

# Apply per-note timbre (channel 1)
synth.send_midi_message([0xB1, 74, 80])  # CC74 (timbre) on channel 1
```

### MPE+ Parameter Control
Control MPE+ parameters with 32-bit resolution:

```python
# Set MPE+ specific parameters
mpe_params = {
    'pitch_range_semitones': 24,      # Pitch bend range per note
    'pressure_sensitivity': 0.8,      # How much pressure affects timbre
    'timbre_sensitivity': 0.6,        # How much CC74 affects timbre
    'slide_time': 0.1                 # Time for smooth parameter transitions
}

for param, value in mpe_params.items():
    channel.set_mpe_per_note_parameter(param, value, resolution='32bit')
```

## XG Effects with MIDI 2.0

### XG Effects Overview
The XG Effects system integrates with MIDI 2.0 to provide:

- 32-bit parameter resolution for all XG effects
- Per-note effect parameter control
- Advanced XG effect types with MIDI 2.0 support
- Profile-based effect configuration

### Setting XG Effect Parameters
Control XG effects with ultra-high resolution:

```python
from synth.effects.midi_2_effects_processor import XGMIDI2EffectsProcessor

effects = XGMIDI2EffectsProcessor(sample_rate=48000)

# Set reverb time with 32-bit precision
effects.set_xg_parameter(
    parameter_address=0x000001,  # REV TIME
    value=3.456789,  # Precise value with many decimal places
    resolution_bits=32
)

# Set chorus rate with 32-bit precision
effects.set_xg_parameter(
    parameter_address=0x000105,  # CHO RATE
    value=0.876543,
    resolution_bits=32
)
```

### Per-Note XG Effects
Apply different effects to different notes:

```python
# Set per-note reverb send
for note in [60, 62, 64, 65]:
    # Higher notes get more reverb
    reverb_send = 0.1 + (note - 60) * 0.03
    effects.set_per_note_effect_parameter(
        note=note,
        effect_id=effects.system_reverb_id,
        param_name='send_level',
        value=reverb_send
    )

# Set per-note chorus depth
effects.set_per_note_effect_parameter(
    note=72,
    effect_id=effects.system_chorus_id,
    param_name='depth',
    value=0.75
)
```

### XG Effect Types
The system supports numerous XG effect types with MIDI 2.0 resolution:

```python
# System Effects (applied globally)
effects.set_xg_parameter(0x000000, 5, resolution_bits=32)  # Set reverb type to Hall 1
effects.set_xg_parameter(0x000100, 2, resolution_bits=32)  # Set chorus type to Chorus 2

# Variation Effects (multi-function)
effects.set_xg_parameter(0x000200, 15, resolution_bits=32)  # Set variation type

# Insertion Effects (per-part)
insert_id = effects.create_effect(MIDI2EffectType.DELAY_STEREO_32BIT)
effects.set_effect_parameter(insert_id, 'time', 0.5, resolution_bits=32)
effects.set_effect_parameter(insert_id, 'feedback', 0.3, resolution_bits=32)
effects.enable_effect(insert_id)
```

## Profile Configuration

### Profile Negotiation
MIDI 2.0 includes profile negotiation for optimal device compatibility:

```python
from synth.midi.profile_configurator import ProfileConfigurationSystem

profiler = ProfileConfigurationSystem()

# Negotiate the best profile for your application
negotiated_profile, capabilities = profiler.negotiate_profile(
    port=0,
    requested_profile=MIDIProfile.GENERAL_MIDI_2
)

print(f"Negotiated profile: {negotiated_profile}")
print(f"Capabilities: {capabilities}")
```

### Capability Discovery
Discover what features a device supports:

```python
# Discover device capabilities
from synth.midi.capability_discovery import CapabilityDiscoverySystem

discoverer = CapabilityDiscoverySystem()
device_id = "my_midi_device"
capabilities = discoverer.discover_device_capabilities(device_id)

print(f"Max polyphony: {capabilities.get('max_polyphony', 0)}")
print(f"32-bit support: {capabilities.get('supports_32bit_resolution', False)}")
print(f"Per-note controllers: {capabilities.get('supports_per_note_controllers', False)}")
print(f"MPE support: {capabilities.get('supports_mpe', False)}")
print(f"Supported message types: {capabilities.get('supported_message_types', set())}")

# Check for specific XG features
if capabilities.get('xg_support', False):
    print("XG features available")
    print(f"XG effects: {capabilities.get('xg_effects_count', 0)}")
    print(f"XG voices: {capabilities.get('xg_voices', 0)}")
```

### Profile-Specific Behavior
Configure your application based on the negotiated profile:

```python
if negotiated_profile == MIDIProfile.GENERAL_MIDI_2:
    # Use GM2 features
    use_32bit_parameters = True
    enable_per_note_controllers = True
    max_polyphony = 64
elif negotiated_profile == MIDIProfile.XG_FULL:
    # Use XG-specific features
    use_32bit_parameters = True
    enable_per_note_controllers = True
    enable_xg_effects = True
    max_polyphony = 128
elif negotiated_profile == MIDIProfile.MPE_STANDARD:
    # Configure for MPE
    use_32bit_parameters = True
    enable_mpe_mode = True
    max_polyphony = 15  # MPE typically uses 15 note channels + 1 master
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
negotiated_profile, capabilities = profile_configurator.negotiate_profile(
    port=0, 
    requested_profile=MIDIProfile.GENERAL_MIDI_2
)
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: 32-bit Parameters Not Working
**Symptoms**: Parameters seem to behave like 7-bit values
**Solution**: Verify that MIDI 2.0 mode is enabled and that you're sending UMP packets or using the 32-bit parameter methods:

```python
# Check if 32-bit support is enabled
print(f"32-bit support: {synth.supports_32bit_parameters}")

# Use the correct method with explicit resolution
param_controller.set_parameter_value('filter_cutoff', 0.75, resolution='32bit')
```

#### Issue: Per-Note Controllers Not Responding
**Symptoms**: Per-note parameters don't seem to affect individual notes
**Solution**: Ensure that per-note controller support is enabled and that you're setting parameters for the correct notes:

```python
# Verify per-note support
print(f"Per-note support: {synth.supports_per_note_controllers}")

# Set per-note parameters correctly
param_controller.set_per_note_parameter(note=60, param_name='expression', value=0.8)
```

#### Issue: MPE+ Not Working
**Symptoms**: MPE+ features don't respond as expected
**Solution**: Check that MPE+ mode is properly enabled and that you're sending messages on the correct channels:

```python
# Enable MPE+ with proper channel configuration
channel.enable_mpe_plus(
    master_channel=15,      # Usually channel 16 (0-indexed as 15)
    first_note_channel=0,   # Usually channel 1 (0-indexed as 0)
    last_note_channel=14    # Usually channel 15 (0-indexed as 14)
)

# Send messages on the correct channels
synth.send_midi_message([0x90, 60, 100])  # Note on channel 1 (0-indexed)
synth.send_midi_message([0xE0, 0x00, 0x40])  # Pitch bend on master channel (15)
```

#### Issue: XG Effects Not Processing MIDI 2.0
**Symptoms**: XG effects don't respond to 32-bit parameters
**Solution**: Ensure that XG mode is enabled and that you're using the XG-specific parameter methods:

```python
# Verify XG mode is enabled
print(f"XG enabled: {synth.xg_enabled}")

# Use XG-specific parameter setting
effects.set_xg_parameter(0x000001, 3.0, resolution_bits=32)  # REV TIME
```

### Performance Tips

1. **Use Parameter Caching**: For frequently changing parameters, consider caching to reduce computation overhead.

2. **Batch Parameter Updates**: When updating multiple parameters, batch them together for better performance.

3. **Optimize Per-Note Usage**: While per-note controllers are powerful, use them judiciously as they require more processing power.

4. **Profile Appropriately**: Use the appropriate MIDI profile for your application to optimize resource usage.

### Debugging MIDI 2.0 Messages

To debug MIDI 2.0 messages, you can inspect the UMP packets:

```python
from synth.midi.ump_packets import UMPParser

parser = UMPParser()
raw_data = b'\x20\x00\x90\x3C\x40\x00\x00\x00'  # Example UMP packet
packets = parser.parse_packet_stream(raw_data)

for packet in packets:
    print(f"UMP Type: {packet.ump_type:X}")
    print(f"Group: {packet.group}")
    print(f"Message Type: {packet.message_type:X}")
    print(f"Channel: {packet.channel}")
```

This user guide provides comprehensive information on using the MIDI 2.0 features in the XG Synthesizer, from basic setup to advanced techniques. The implementation provides professional-grade MIDI 2.0 support with full backward compatibility to MIDI 1.0, XG, and GS formats.