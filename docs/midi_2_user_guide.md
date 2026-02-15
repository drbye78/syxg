# MIDI 2.0 User Guide for XG Synthesizer

This guide explains how to use the advanced MIDI 2.0 features in the XG Synthesizer, including 32-bit parameter control, per-note controllers, MPE+ extensions, and XG effects integration.

## Table of Contents
1. [Getting Started with MIDI 2.0](#getting-started-with-midi-20)
2. [32-bit Parameter Control](#32-bit-parameter-control)
3. [Per-Note Controllers](#per-note-controllers)
4. [MPE+ Extensions](#mpe-extensions)
5. [XG Effects with MIDI 2.0](#xg-effects-with-midi-20)
6. [Profile Configuration](#profile-configuration)
7. [Troubleshooting](#troubleshooting)

## Getting Started with MIDI 2.0

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
    channel.set_mpe_parameter(param, value, resolution='32bit')
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
from synth.effects.xg_effects_integration import XGMIDIEffectsProcessor

effects = XGMIDIEffectsProcessor(sample_rate=48000)

# Set reverb time with 32-bit precision
effects.set_xg_parameter(
    effect_slot='system_reverb',
    param_name='time',
    value=3.456789,  # Precise value with many decimal places
    resolution='32bit'
)

# Set chorus rate with 32-bit precision
effects.set_xg_parameter(
    effect_slot='system_chorus',
    param_name='rate',
    value=0.876543,
    resolution='32bit'
)
```

### Per-Note XG Effects
Apply different effects to different notes:

```python
# Set per-note reverb send
for note in [60, 62, 64, 65]:
    # Higher notes get more reverb
    reverb_send = 0.1 + (note - 60) * 0.03
    effects.set_per_note_xg_parameter(
        note=note,
        effect_slot='system_reverb',
        param_name='send_level',
        value=reverb_send,
        resolution='32bit'
    )

# Set per-note chorus depth
effects.set_per_note_xg_parameter(
    note=72,
    effect_slot='system_chorus',
    param_name='depth',
    value=0.75,
    resolution='32bit'
)
```

### XG Effect Types
The system supports numerous XG effect types with MIDI 2.0 resolution:

```python
# System Effects (applied globally)
effects.set_xg_parameter('system_reverb', 'type', XGEffectType.REVERB_HALL.value)
effects.set_xg_parameter('system_chorus', 'type', XGEffectType.CHORUS_STANDARD.value)

# Variation Effects (multi-function)
effects.set_xg_parameter('variation', 'type', XGEffectType.VARIATION_MULTI_CHORUS.value)

# Insertion Effects (per-part)
insert_idx = effects.add_insertion_effect(XGEffectType.INSERT_DUAL_DELAY)
effects.set_xg_parameter(f'insertion_{insert_idx}', 'param1', 0.5, resolution='32bit')
```

## Profile Configuration

### Profile Negotiation
MIDI 2.0 includes profile negotiation for optimal device compatibility:

```python
from synth.midi.profile_configurator import ProfileConfigurationSystem

profiler = ProfileConfigurationSystem()

# Negotiate the best profile for your application
negotiated_profile = profiler.negotiate_profile(
    port=0,
    requested_profile=MIDIProfile.GENERAL_MIDI_2
)

print(f"Negotiated profile: {negotiated_profile}")
```

### Capability Discovery
Discover what features a device supports:

```python
# Discover device capabilities
capabilities = profiler.discover_capabilities(port=0)

print(f"Max polyphony: {capabilities['max_polyphony']}")
print(f"32-bit support: {capabilities['supports_32bit_resolution']}")
print(f"Per-note controllers: {capabilities['supports_per_note_controllers']}")
print(f"MPE support: {capabilities['supports_mpe']}")
print(f"Supported message types: {capabilities['supported_message_types']}")

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
effects.set_xg_parameter('system_reverb', 'time', 3.0, resolution='32bit')
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

## Advanced Topics

### Creating Custom Parameter Mappings
Develop sophisticated parameter mapping systems for expressive performance:

```python
# Create a complex modulation matrix
mod_matrix = {
    'mod_wheel': {
        'filter_cutoff': {'amount': 0.3, 'curve': 'linear'},
        'oscillator_detune': {'amount': 0.1, 'curve': 'exponential'},
        'lfo_rate': {'amount': 0.2, 'curve': 'sine'}
    },
    'breath_controller': {
        'amplitude': {'amount': 0.8, 'curve': 'linear'},
        'filter_resonance': {'amount': 0.4, 'curve': 'logarithmic'}
    },
    'expression': {
        'overall_level': {'amount': 1.0, 'curve': 'cubic'}
    }
}

# Apply the modulation matrix
for source, destinations in mod_matrix.items():
    for dest, params in destinations.items():
        param_controller.add_parameter_mapping(
            source=source,
            destination=dest,
            sensitivity=params['amount'],
            curve=params['curve']
        )
```

### Integration with DAWs
When integrating with Digital Audio Workstations, consider these MIDI 2.0 best practices:

```python
# Handle DAW transport and timing
def on_transport_play():
    # Sync to DAW transport
    synth.set_sync_mode('daw_transport')

def on_tempo_change(tempo_bpm):
    # Update internal timing to match DAW
    synth.set_tempo(tempo_bpm)

def on_time_signature_change(numerator, denominator):
    # Update timing to match DAW
    synth.set_time_signature(numerator, denominator)
```

This user guide provides comprehensive information on using the MIDI 2.0 features in the XG Synthesizer, from basic setup to advanced techniques. The implementation provides professional-grade MIDI 2.0 support with full backward compatibility to MIDI 1.0.