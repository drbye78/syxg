# MIDI 2.0 User Guide for XG Synthesizer

This guide explains how to use the MIDI 2.0 features in the XG Synthesizer, including 32-bit parameter resolution, per-note controllers, MPE+ extensions, and UMP packet handling.

## Table of Contents

1. [Introduction to MIDI 2.0 in XG](#1-introduction-to-midi-20-in-xg)
2. [Enabling MIDI 2.0](#2-enabling-midi-20)
3. [Sending MIDI 2.0 Messages](#3-sending-midi-20-messages)
4. [Receiving MIDI 2.0 Messages](#4-receiving-midi-20-messages)
5. [Per-Note Controllers](#5-per-note-controllers)
6. [MPE+ Extensions](#6-mpe-extensions)
7. [Channel-Level 32-bit Control](#7-channel-level-32-bit-control)
8. [Troubleshooting](#8-troubleshooting)
9. [UMP Group Routing](#9-ump-group-routing)

---

## 1. Introduction to MIDI 2.0 in XG

MIDI 2.0 brings higher precision and greater expressiveness to the XG Synthesizer. The implementation focuses on the Universal MIDI Packet (UMP) transport and higher-resolution parameter control.

### Key Features

- **32-bit Parameter Resolution**: Over 4 billion possible values (vs 127 in MIDI 1.0) for controllers, pitch bend, and pressure
- **16-bit Note Velocity**: 0-65535 range instead of 0-127 for finer dynamic control
- **Per-Note Controllers**: Individual CC74 (timbre), CC75 (slide), CC76 (lift) per note with 24-bit precision
- **MPE+**: MPE with 32-bit precision for pitch bend and controllers
- **Backward Compatibility**: Full MIDI 1.0 support; conversion utilities bridge both worlds

### What MIDI 2.0 Is Not

The XG Synthesizer implements the core MIDI 2.0 channel voice and stream (per-note) message types. The following MIDI 2.0 features are **not** implemented:
- Capability Discovery (CI — Protocol Negotiation)
- Profile Configuration
- MIDI 2.0 Property Exchange
- MIDI 2.0 Effects processors (separate from the existing XG effects system)

---

## 2. Enabling MIDI 2.0

MIDI 2.0 support is **disabled by default** (`midi_2_enabled=False`). Enable it at construction time:

### Offline Synthesizer (ModernXGSynthesizer)

```python
from synth.synthesizers.rendering import ModernXGSynthesizer

synth = ModernXGSynthesizer(
    sample_rate=44100,
    midi_2_enabled=True,  # Enable MIDI 2.0 features
    xg_enabled=True,
    mpe_enabled=True,
)
print(f"MIDI 2.0 enabled: {synth.midi_2_enabled}")  # True
```

### Real-Time Synthesizer (Synthesizer)

```python
from synth.synthesizers.realtime import Synthesizer

synth = Synthesizer(
    sample_rate=44100,
    buffer_size=1024,
    midi_2_enabled=True,  # Enable MIDI 2.0 features
)
print(f"MIDI 2.0 enabled: {synth.midi_2_enabled}")  # True
```

### Checking Current State

```python
# Both synthesizers expose the property
is_enabled = synth.midi_2_enabled
```

---

## 3. Sending MIDI 2.0 Messages

MIDI 2.0 messages are constructed as UMP (Universal MIDI Packet) objects, serialized to bytes, and sent through the MIDI processing pipeline.

### 3.1 Using the MIDI1ToMIDI2Converter (Recommended)

The simplest way to create MIDI 2.0 messages is to start from MIDI 1.0 values and convert them:

```python
from synth.io.midi.ump_packets import MIDI1ToMIDI2Converter

# Note On: convert standard MIDI 1.0 values
packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
    status_byte=0x90,  # Note On, channel 0
    data1=60,           # Middle C
    data2=100           # Velocity 100 (scaled to 16-bit automatically)
)

# Get bytes for processing
ump_bytes = packet.to_bytes()
```

### 3.2 Direct MIDI2ChannelVoicePacket Construction

For full control over 32-bit data words:

```python
from synth.io.midi.ump_packets import MIDI2ChannelVoicePacket, UMPGroup

# Note On with explicit 16-bit velocity
note = 60
velocity_16bit = 50000  # 0-65535 (vs 0-127 in MIDI 1.0)

packet = MIDI2ChannelVoicePacket(
    group=UMPGroup(0),
    channel=0,
    message_type=0x9,     # Note On
    data_word_1=note,      # Note number in lower 16 bits
    data_word_2=(velocity_16bit & 0xFFFF) << 16  # Velocity in upper 16 bits
)
```

### 3.3 Control Change with 32-bit Value

```python
# Send CC7 (Volume) with 32-bit precision
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0xB,
    (7 & 0x7F) << 9,         # Controller number at bits 15-9
    2147483647                # 32-bit value (~50%)
)

# Process through the synthesizer
synth.process_midi_message(packet.to_bytes())
```

### 3.4 Pitch Bend with 32-bit Value

```python
# 32-bit pitch bend: 0=full down, 0x7FFFFFFF=center, 0xFFFFFFFF=full up
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0xE,
    0,                        # Unused
    0x7FFFFFFF                # Center position
)

synth.process_midi_message(packet.to_bytes())

# Full up
packet = MIDI2ChannelVoicePacket(UMPGroup(0), 0, 0xE, 0, 0xFFFFFFFF)
synth.process_midi_message(packet.to_bytes())
```

### 3.5 Channel Pressure with 32-bit Value

```python
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0xD,
    0,                        # Unused
    0x40000000                # ~25% pressure
)
synth.process_midi_message(packet.to_bytes())
```

### 3.6 Poly Pressure with 32-bit Value

```python
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0xA,
    60,                       # Note number
    0x60000000                # ~37.5% pressure
)
synth.process_midi_message(packet.to_bytes())
```

### 3.7 How Messages Flow Through the System

```
MIDI2ChannelVoicePacket
    → .to_bytes()
    → synth.process_midi_message(bytes)
    → MIDIMessageProcessor.process_midi_message()
    → RealtimeParser.parse_bytes()  (auto-detects UMP)
    → MIDIMessage with is_midi2=True
    → Channel control_change()/pitch_bend()/etc.
```

---

## 4. Receiving MIDI 2.0 Messages

When UMP bytes are processed through `RealtimeParser`, they become `MIDIMessage` objects with additional precision-specific data keys.

### 4.1 Using RealtimeParser Directly

```python
from synth.io.midi.realtime import RealtimeParser
from synth.io.midi.ump_packets import MIDI2ChannelVoicePacket, UMPGroup

parser = RealtimeParser()

# Create and parse a MIDI 2.0 message
packet = MIDI2ChannelVoicePacket(UMPGroup(0), 0, 0x9, 60, (50000 << 16))
messages = parser.parse_bytes(packet.to_bytes())

for msg in messages:
    # The is_midi2 flag identifies MIDI 2.0 sources
    if msg.data.get("is_midi2"):
        print(f"MIDI 2.0 {msg.type} on channel {msg.channel}")
        print(f"  Note: {msg.data['note']}")
        print(f"  16-bit velocity: {msg.data['velocity_16bit']}")
```

### 4.2 Detecting MIDI 2.0 Messages

All MIDI 2.0-originated messages contain `"is_midi2": True` in their data dictionary:

```python
for msg in messages:
    if msg.data.get("is_midi2"):
        # This message came from a MIDI 2.0 source
        handle_midi2_message(msg)
    else:
        # Standard MIDI 1.0 message
        handle_midi1_message(msg)
```

### 4.3 Accessing Extended Precision Values

| Message Type | MIDI 2.0 Key | Range | Example |
|-------------|-------------|-------|---------|
| `note_on` / `note_off` | `velocity_16bit` | 0-65535 | `msg.data["velocity_16bit"]` |
| `control_change` | `value_32bit` | 0-4294967295 | `msg.data["value_32bit"]` |
| `pitch_bend` | `pitch_32bit` | 0-4294967295 | `msg.data["pitch_32bit"]` |
| `channel_pressure` | `pressure_32bit` | 0-4294967295 | `msg.data["pressure_32bit"]` |
| `poly_pressure` | `pressure_32bit` | 0-4294967295 | `msg.data["pressure_32bit"]` |
| `midi2_per_note_controller` | `value_24bit` | 0-16777215 | `msg.data["value_24bit"]` |

**Example — inspecting all MIDI 2.0 data:**

```python
def dump_midi2_data(msg):
    """Print all MIDI 2.0 extended data from a message."""
    if not msg.data.get("is_midi2"):
        return

    for key in ("velocity_16bit", "value_32bit", "pitch_32bit",
                 "pressure_32bit", "value_24bit"):
        if key in msg.data:
            print(f"  {key}: {msg.data[key]}")
```

### 4.4 MIDI 2.0 Through the Synthesizer

When processing MIDI messages through `synth.process_midi_message()`, the system automatically detects UMP format and converts it. The `Channel` class internally stores both 7-bit and 32-bit values:

```python
# After sending a MIDI 2.0 CC message:
channel = synth.channels[0]
print(channel.controllers[7])           # 7-bit value (0-127)
print(channel.controllers_32bit[7])     # 32-bit value (0-4294967295)
```

---

## 5. Per-Note Controllers

MIDI 2.0 introduces per-note controllers that carry MIDI controller values for a specific note with 24-bit precision (0-16777215).

### 5.1 Creating Per-Note Controller Messages

```python
from synth.io.midi.ump_packets import PerNoteControllerUMP, UMPGroup

# Per-note timbre (CC74) on note 60 at 50%
pnc = PerNoteControllerUMP(
    group=UMPGroup(0),
    channel=0,
    note=60,
    controller_index=74,     # Timbre
    value=8388607             # 50% in 24-bit range (0-16777215)
)

# Per-note slide (CC75) on note 62 at 25%
pnc_slide = PerNoteControllerUMP(
    UMPGroup(0), 0, 62, 75, 4194303
)

# Per-note lift (CC76) on note 64 at 75%
pnc_lift = PerNoteControllerUMP(
    UMPGroup(0), 0, 64, 76, 12582911
)
```

### 5.2 Controller Index Mapping

| CC | Name | MPE Role | 24-bit Value Meaning |
|----|------|----------|---------------------|
| 74 | Timbre | Filter/brightness control | 0 = dark, 16777215 = bright |
| 75 | Slide | Pitch glide amount | 0 = no slide, 16777215 = max slide |
| 76 | Lift | Release envelope | 0 = short release, 16777215 = long release |

### 5.3 Parsing Per-Note Controllers

`RealtimeParser` converts `PerNoteControllerUMP` to `MIDIMessage` with type `"midi2_per_note_controller"`:

```python
parser = RealtimeParser()

pnc = PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 8388607)
messages = parser.parse_bytes(pnc.to_bytes())

for msg in messages:
    if msg.type == "midi2_per_note_controller":
        note = msg.data["note"]             # 60
        controller = msg.data["controller"]  # 74
        value = msg.data["value"]            # 8388607 (24-bit)
        value_24bit = msg.data["value_24bit"]  # 8388607

        print(f"Note {note}: CC{controller} = {value_24bit}")
```

### 5.4 Processing Per-Note Controllers in MPE

When MPE is enabled, per-note controllers are processed through the MPE system for expressive control:

```python
# Assuming synth has mpe_system with MPE enabled
synth.mpe_system.process_per_note_controller(
    channel=0,
    note=60,
    controller=74,      # Timbre
    value_24bit=8388607  # 50%
)
```

This will update the `MPENote` object's `.timbre` attribute (normalized to 0.0-1.0).

### 5.5 Practical Use — Expressive Chord

```python
from synth.io.midi.ump_packets import PerNoteControllerUMP, UMPGroup

# Process per-note controllers through the synth
def send_per_note_controller(synth, channel, note, cc, value_24bit):
    pnc = PerNoteControllerUMP(UMPGroup(0), channel, note, cc, value_24bit)
    synth.process_midi_message(pnc.to_bytes())

# C major chord with varying timbre per note
notes = [60, 64, 67]
for i, note in enumerate(notes):
    # Each note gets different timbre
    timbre = int((i + 1) * 4194303)  # 25%, 50%, 75%
    send_per_note_controller(synth, 0, note, 74, timbre)
```

### 5.6 Per-Note Management

MIDI 2.0 Per-Note Management messages (`PerNoteManagementUMP`, UMP type 0xF, stream status 0x1) let you **explicitly assign or remove notes** from MPE zones. This gives direct control over per-note behavior without relying on dynamic zone assignment.

```python
from synth.io.midi.ump_packets import PerNoteManagementUMP, UMPGroup

# Assign note 72 to the MPE zone on channel 7
pnm = PerNoteManagementUMP(
    group=UMPGroup(0),
    channel=7,
    note=72,
    assign=True,
)

# Process through the synthesizer's MPE system
synth.mpe_system.process_per_note_management(channel=7, note=72, assign=True)

# When assign=False, the note is removed from the zone
synth.mpe_system.process_per_note_management(channel=7, note=72, assign=False)
```

**Use cases:**
- **Assign**: Pre-assign notes to specific MPE member channels before they arrive, enabling one-note-per-channel expressive control.
- **Remove**: Release a note from MPE management, returning it to standard channel behavior.

**Data keys** (via `midi2_per_note_management` MIDIMessage):

| Key | Type | Description |
|-----|------|-------------|
| `note` | `int` | Note number |
| `assign` | `bool` | `True` = assign, `False` = remove |
| `midi_group` | `UMPGroup` | UMP group of the message |

---

## 6. MPE+ Extensions

MPE+ is a MIDI 2.0 extension to standard MPE that provides 32-bit precision for pitch bend, controllers, and per-note processing.

### 6.1 Enabling MPE+

```python
from synth.engines.systems.mpe_system import MPESystem

mpe_system = MPESystem(synthesizer=synth, max_channels=32)

# MPE is enabled by default
print(mpe_system.mpe_enabled)        # True

# Enable MPE+ for high-precision mode
mpe_system.set_mpe_plus_enabled(True)
print(mpe_system.mpe_plus_enabled)   # True
```

### 6.2 32-bit Pitch Bend in MPE+

```python
# Standard MPE (14-bit pitch bend)
mpe_system.process_pitch_bend(0, 8192)   # Center

# MPE+ (32-bit pitch bend) — finer granularity
mpe_system.process_pitch_bend_32bit(0, 0x7FFFFFFF)  # Center
mpe_system.process_pitch_bend_32bit(0, 0xFFFFFFFF)   # Maximum up
mpe_system.process_pitch_bend_32bit(0, 0x00000000)   # Maximum down
```

The 32-bit value is internally normalized to a -1.0 to +1.0 range, then multiplied by the zone's pitch bend range in semitones.

### 6.3 32-bit MPE Controllers

```python
# CC74 (timbre) with 32-bit precision
mpe_system.process_mpe_controller_32bit(1, 74, 4294967295)  # Full timbre

# CC75 (slide) with 32-bit precision
mpe_system.process_mpe_controller_32bit(1, 75, 0)           # No slide

# CC76 (lift) with 32-bit precision
mpe_system.process_mpe_controller_32bit(1, 76, 2147483647)  # 50% lift
```

### 6.4 Per-Note Controller Integration

MPE+ integrates with the per-note controller system for individual note expression:

```python
# Set per-note timbre on an active MPE note
mpe_system.process_per_note_controller(
    channel=1,           # MPE member channel
    note=60,
    controller=74,       # Timbre
    value_24bit=8388607  # 50%
)

# Check the MPE note's timbre value
notes = mpe_system.get_active_mpe_notes(channel=1)
for note in notes:
    if note.note_number == 60:
        print(f"Timbre: {note.timbre}")  # ~0.5 (normalized from 24-bit)
```

### 6.5 MPE System State

```python
# Get overall MPE status
info = mpe_system.get_mpe_info()
print(f"MPE enabled: {info['enabled']}")
print(f"Active zones: {info['zones']}")
print(f"Active notes: {info['active_notes']}")
print(f"MPE+ enabled: {mpe_system.mpe_plus_enabled}")

# Get active notes for a specific channel
notes = mpe_system.get_active_mpe_notes(channel=0)
for mpe_note in notes:
    print(f"Note {mpe_note.note_number}: "
          f"pitch_bend={mpe_note.pitch_bend:.2f}, "
          f"timbre={mpe_note.timbre:.2f}, "
          f"slide={mpe_note.slide:.2f}, "
          f"lift={mpe_note.lift:.2f}")
```

---

## 7. Channel-Level 32-bit Control

The `Channel` class stores both 7-bit (MIDI 1.0) and 32-bit (MIDI 2.0) values for controllers, pitch bend, and pressure.

### 7.1 32-bit Controllers

```python
# Access the channel from the synthesizer
channel = synth.channels[0]  # ModernXGSynthesizer

# MIDI 2.0: pass is_32bit=True
channel.control_change(7, 4294967295, is_32bit=True)    # Volume: 100%
channel.control_change(10, 0x7FFFFFFF, is_32bit=True)   # Pan: center
channel.control_change(11, 3221225472, is_32bit=True)   # Expression: ~75%

# Both representations are stored
print(f"7-bit volume:  {channel.controllers[7]}")          # 127
print(f"32-bit volume: {channel.controllers_32bit[7]}")    # 4294967295

# Normalize to float for modulation
normalized = channel._normalize_32bit_value(channel.controllers_32bit[7])
print(f"Normalized: {normalized:.3f}")  # 1.000
```

### 7.2 32-bit Pitch Bend

```python
# MIDI 2.0: pass pitch_32bit parameter
channel.pitch_bend(0, 0, pitch_32bit=0x7FFFFFFF)  # Center
channel.pitch_bend(0, 0, pitch_32bit=0)            # Full down
channel.pitch_bend(0, 0, pitch_32bit=0xFFFFFFFF)   # Full up

# Access the stored values
print(channel.pitch_bend_value)    # 32-bit value
print(channel.pitch_bend_32bit)    # Same 32-bit value
```

### 7.3 32-bit Channel Pressure

```python
# MIDI 2.0 channel pressure
channel.set_channel_pressure_32bit(2147483647)
print(f"7-bit pressure: {channel.channel_pressure}")        # ~63
print(f"32-bit pressure: {channel.channel_pressure_32bit}") # 2147483647
```

### 7.4 32-bit Poly Pressure

```python
# MIDI 2.0 per-note pressure
channel.key_pressure(60, 0, pressure_32bit=4294967295)
print(channel.key_pressure_values[60])             # 127
print(channel.key_pressure_32bit_values[60])       # 4294967295
```

### 7.5 Verification — Checking 32-bit State

```python
# Inspect all 32-bit controllers on a channel
print("32-bit controllers:")
for cc, value in channel.controllers_32bit.items():
    normalized = channel._normalize_32bit_value(value)
    print(f"  CC{cc:3d}: {value:10d} ({normalized:.3f})")

print(f"Pitch bend (32-bit): {channel.pitch_bend_32bit}")
print(f"Channel pressure (32-bit): {channel.channel_pressure_32bit}")
```

---

## 8. Troubleshooting

### 8.1 MIDI 2.0 Not Enabled

**Symptom:** Higher precision values have no effect; everything behaves like MIDI 1.0.

**Solution:** Ensure `midi_2_enabled=True` at construction time:

```python
synth = ModernXGSynthesizer(midi_2_enabled=True)
print(f"MIDI 2.0 enabled: {synth.midi_2_enabled}")  # Must be True
```

### 8.2 UMP Bytes Not Being Recognized

**Symptom:** `RealtimeParser.parse_bytes()` returns empty or unexpected messages from UMP bytes.

**Solution:** Verify the bytes start with a valid UMP type nibble (0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, or 0xF):

```python
from synth.io.midi.ump_packets import UMPParser

# Verify bytes are parseable
packets = UMPParser.parse_packet_stream(your_bytes)
if not packets:
    print("Not valid UMP data")

# Check first nibble
first_byte = your_bytes[0]
ump_type = (first_byte >> 4) & 0xF
print(f"UMP type: 0x{ump_type:X}")
```

### 8.3 Per-Note Controllers Not Affecting Sound

**Symptom:** Sending `PerNoteControllerUMP` messages doesn't change the audio output.

**Solution:** Ensure MPE is enabled and the target note is active:

```python
# Verify MPE state
print(f"MPE enabled: {synth.mpe_system.mpe_enabled}")
print(f"Active MPE notes: {len(synth.mpe_system.get_active_mpe_notes())}")

# Per-note controllers only affect notes currently managed by MPE
# Send a note on first, then the per-note controller
from synth.io.midi.ump_packets import MIDI1ToMIDI2Converter
note_on = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x90, 60, 100)
synth.process_midi_message(note_on.to_bytes())

# Now send the per-note controller
pnc = PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 8388607)
synth.process_midi_message(pnc.to_bytes())
```

### 8.4 MIDI 2.0 Conversion Loses Precision

**Symptom:** Round-trip conversion (MIDI 1.0 → 2.0 → 1.0) produces slightly different values.

**Explanation:** This is expected. The conversion scales between ranges:

- 7-bit (0-127) ↔ 16-bit (0-65535): uses integer scaling `* 65535 / 127`
- 7-bit (0-127) ↔ 32-bit (0-4294967295): uses integer scaling `* 0xFFFFFFFF / 127`
- 14-bit (0-16383) ↔ 32-bit (0-0xFFFFFFFF): uses integer scaling

Rounding errors can occur: velocity 100 → 16-bit 33024 → 7-bit 99 (not 100). This is within acceptable tolerance.

### 8.5 MPE+ Methods vs Standard MPE Methods

**Symptom:** Calling `set_mpe_plus_enabled(True)` doesn't seem to change behavior.

**Explanation:** MPE+ methods (`process_pitch_bend_32bit`, `process_mpe_controller_32bit`) are independent of the `mpe_plus_enabled` flag. The flag is for informational/configuration purposes. The 32-bit methods always work with 32-bit precision regardless of the flag state. Standard methods (`process_pitch_bend`, `process_mpe_controller`) always use 14-bit/7-bit values.

### 8.6 Import Paths

Ensure you use the correct import paths:

```python
# ✅ Correct imports
from synth.io.midi.ump_packets import (
    MIDI2ChannelVoicePacket,
    MIDI1ChannelVoicePacket,
    PerNoteControllerUMP,
    SysExUMP,
    UMPParser,
    MIDI1ToMIDI2Converter,
    UMPGroup,
)
from synth.io.midi.realtime import RealtimeParser
from synth.io.midi.message import MIDIMessage
from synth.engines.systems.mpe_system import MPESystem
from synth.mpe.mpe_manager import MPEManager, MPENote
from synth.processing.channel import Channel
from synth.synthesizers.rendering import ModernXGSynthesizer
from synth.synthesizers.realtime import Synthesizer

# ❌ Incorrect — these modules do not exist
# from synth.midi.ump_packets import ...   # Wrong
# from synth.io.midi.advanced_parameter_control import ...  # Does not exist
# from synth.io.midi.capability_discovery import ...        # Does not exist
# from synth.io.midi.profile_configurator import ...        # Does not exist
```

### 8.7 Validation — Import Check

Run this to verify your environment has all the MIDI 2.0 APIs:

```bash
python -c "
from synth.io.midi.ump_packets import (
    MIDI2ChannelVoicePacket, MIDI1ToMIDI2Converter,
    PerNoteControllerUMP, UMPGroup, UMPParser,
    MIDI1ChannelVoicePacket, SysExUMP, UMPMessageType,
)
from synth.io.midi.realtime import RealtimeParser
from synth.io.midi.message import MIDIMessage
from synth.engines.systems.mpe_system import MPESystem
print('All MIDI 2.0 imports OK')
"
```

---

## 9. UMP Group Routing

UMP Groups allow a single UMP stream to carry up to 16 independent groups of 16 MIDI channels, for a total of 256 logical channels. This is equivalent to having multiple MIDI ports over a single cable.

### 9.1 How Groups Work

Each UMP packet carries a 4-bit group identifier (0-15) in its header. The group is automatically extracted by `RealtimeParser` when parsing UMP data.

```python
# Group 0, channel 5 — standard first port
packet_g0 = MIDI2ChannelVoicePacket(
    UMPGroup(0), channel=5, message_type=0x9,
    data_word_1=60, data_word_2=100 << 16,
)

# Group 1, channel 5 — second port
packet_g1 = MIDI2ChannelVoicePacket(
    UMPGroup(1), channel=5, message_type=0x9,
    data_word_1=72, data_word_2=80 << 16,
)
```

### 9.2 MIDI Message Data

Every UMP message parsed by `RealtimeParser` includes the group in its data dictionary as `midi_group`, while `channel` stays as the raw group-relative value (0-15):

```python
parser = RealtimeParser()

# Parse a message from group 3, channel 7
pnc = PerNoteControllerUMP(UMPGroup(3), channel=7, note=60, controller_index=74, value=8388607)
messages = parser.parse_bytes(pnc.to_bytes())

for msg in messages:
    print(f"Channel: {msg.channel}")          # 7 (raw within group)
    print(f"Group: {msg.data['midi_group']}") # UMPGroup(3)
```

### 9.3 Synthesizer Channel Mapping

The synthesizer maps groups to its flat channel array:

```
synth_channel = midi_group × 16 + midi_channel
```

| UMP Group | MIDI Channel | Synth Channel | Result |
|-----------|-------------|---------------|--------|
| 0 | 0 | 0 | First channel, first group |
| 0 | 15 | 15 | Last channel, first group |
| 1 | 0 | 16 | First channel, second group |
| 1 | 5 | 21 | Channel 5, second group |
| 3 | 7 | 55 | Channel 7, group 3 |

### 9.4 Enabling Multi-Group Support

Configure the synthesizer with enough channels for your groups. Each group requires 16 consecutive channels:

```python
# Two groups (32 channels)
synth = ModernXGSynthesizer(max_channels=32, midi_2_enabled=True)

# Four groups (64 channels)
synth = Synthesizer(max_channels=64, midi_2_enabled=True)
```

The flat channel number is used only for direct synthesizer channel access. XG receive-channel routing and MPE zone management continue to use the raw group-relative channel (0-15) and are unaffected by group offset.

---

### Conversion from MIDI 1.0 to MIDI 2.0

| MIDI 1.0 | MIDI 2.0 Equivalent |
|----------|---------------------|
| `[0x90, 60, 100]` | `MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x90, 60, 100).to_bytes()` |
| `[0xB0, 7, 80]` | `MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xB0, 7, 80).to_bytes()` |
| `[0xE0, 0x00, 0x40]` | `MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xE0, 0x00, 0x40).to_bytes()` |

### Range Comparison

| Parameter | MIDI 1.0 | MIDI 2.0 | Improvement |
|-----------|----------|----------|-------------|
| Velocity | 0-127 (7-bit) | 0-65535 (16-bit) | 512x |
| Controller | 0-127 (7-bit) | 0-4294967295 (32-bit) | 33Mx |
| Pitch Bend | 0-16383 (14-bit) | 0-4294967295 (32-bit) | 262Kx |
| Pressure | 0-127 (7-bit) | 0-4294967295 (32-bit) | 33Mx |
| Per-Note CC | N/A | 0-16777215 (24-bit) | New |

---

## Copyright

This user guide documents the MIDI 2.0 implementation in the XG Synthesizer. Features and APIs are subject to change as the implementation evolves.
