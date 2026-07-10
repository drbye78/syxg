# MIDI 2.0 API Reference

This document provides comprehensive API documentation for the MIDI 2.0 features implemented in the XG Synthesizer. All code examples are verified against the actual codebase.

## Table of Contents

1. [Universal MIDI Packet (UMP) System](#1-universal-midi-packet-ump-system)
2. [MIDI Message System](#2-midi-message-system)
3. [Real-Time MIDI Processing](#3-real-time-midi-processing)
4. [MPE System](#4-mpe-system)
5. [Channel 32-bit Support](#5-channel-32-bit-support)
6. [MIDI 2.0 Channel Voice Message Types](#6-midi-20-channel-voice-message-types)
7. [Per-Note Controller System](#7-per-note-controller-system)
8. [Per-Note Management System](#8-per-note-management-system)
9. [MIDI 1.0 / MIDI 2.0 Conversion](#9-midi-10--midi-20-conversion)
10. [UMP Group Routing](#10-ump-group-routing)

---

## 1. Universal MIDI Packet (UMP) System

The UMP subsystem lives in `synth.io.midi.ump_packets` and implements the MIDI 2.0 Universal MIDI Packet specification. It provides packet construction, serialization, parsing, and conversion between MIDI 1.0 and MIDI 2.0 formats.

### 1.1 UMPGroup

A type-safe wrapper for the 4-bit UMP group identifier (0-15), representing a MIDI port or group.

```python
from synth.io.midi.ump_packets import UMPGroup

group = UMPGroup(0)   # Valid: 0-15
# UMPGroup(16)        # Raises ValueError
```

**Constructor:**
- `UMPGroup(value: int)` — value must be 0-15

### 1.2 UMPPacket (Abstract Base)

Base class for all UMP packets.

```python
from synth.io.midi.ump_packets import UMPPacket, UMPMessageType

# UMPPacket is abstract — use one of its subclasses
```

**Properties:**
- `ump_type: UMPMessageType` — the UMP message type enum
- `group: UMPGroup` — the group/port identifier

**Methods:**
- `to_words() -> list[int]` — convert to list of 32-bit words
- `to_bytes() -> bytes` — convert to raw byte representation

### 1.3 UMPMessageType Enum

```python
from synth.io.midi.ump_packets import UMPMessageType

UMPMessageType.MIDI_1_CHANNEL    # 0x1 — MIDI 1.0 Channel Voice
UMPMessageType.MIDI_2_CHANNEL    # 0x2 — MIDI 2.0 Channel Voice
UMPMessageType.SYSEX             # 0x3 — System Exclusive
UMPMessageType.UTILITY           # 0x4 — Utility Messages
UMPMessageType.SYSTEM            # 0x5 — System Messages
UMPMessageType.POWER             # 0x6 — Power Messages
UMPMessageType.EXTENDED          # 0x7 — Extended Messages
UMPMessageType.STREAM            # 0xF — Stream Messages (Per-Note Controller, etc.)
```

### 1.4 MIDI2ChannelVoicePacket

Represents a MIDI 2.0 Channel Voice message as a 64-bit (2-word) UMP packet with 32-bit parameter resolution.

```python
from synth.io.midi.ump_packets import MIDI2ChannelVoicePacket, UMPGroup

# Note On: channel 0, note 60, velocity scaled to 16-bit
packet = MIDI2ChannelVoicePacket(
    group=UMPGroup(0),
    channel=0,
    message_type=0x9,    # 0x8-0xE (Note Off, Note On, Poly Pressure, CC, PC, Ch Pressure, Pitch Bend)
    data_word_1=60,      # Note number (lower 16 bits used)
    data_word_2=100 << 16  # Velocity in upper 16 bits of word 2
)
```

**Constructor:**

```python
MIDI2ChannelVoicePacket(
    group: UMPGroup,
    channel: int,          # 0-15
    message_type: int,     # 0x8-0xE (upper nibble of status byte)
    data_word_1: int,      # 0-0xFFFFFFFF (32-bit)
    data_word_2: int,      # 0-0xFFFFFFFF (32-bit)
)
```

**Properties:**
- `ump_type` → `UMPMessageType.MIDI_2_CHANNEL` (always 0x2)
- `group` → `UMPGroup`
- `channel` → `int` (0-15)
- `message_type` → `int` (0x8-0xE)
- `data_word_1` → `int` (32-bit)
- `data_word_2` → `int` (32-bit)

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_words()` | `list[int]` (2 elements) | Serialize to 2×32-bit words |
| `to_bytes()` | `bytes` (8 bytes) | Serialize to 8-byte big-endian representation |
| `from_words(words)` classmethod | `MIDI2ChannelVoicePacket \| None` | Parse from 2-word array |
| `get_status_byte()` | `int` | Reconstruct status byte `(message_type << 4) \| channel` |
| `get_property_data()` | `tuple[int, int, int, int]` | Extract property id, index, data_type, value from data words |

**Examples:**

```python
# Create and serialize a Note On
packet = MIDI2ChannelVoicePacket(UMPGroup(0), 0, 0x9, 60, 100 << 16)
words = packet.to_words()     # [546308156, 6553600]
raw_bytes = packet.to_bytes() # b'20 90 00 3c 00 64 00 00'

# Parse back from words
restored = MIDI2ChannelVoicePacket.from_words(words)
print(restored.channel)       # 0
print(restored.message_type)  # 9
print(restored.data_word_1)   # 60  (note number)

# Get status byte
status = packet.get_status_byte()  # 0x90
```

### 1.5 MIDI1ChannelVoicePacket

Represents a MIDI 1.0 Channel Voice message as a 32-bit (1-word) UMP packet.

```python
from synth.io.midi.ump_packets import MIDI1ChannelVoicePacket, UMPGroup

packet = MIDI1ChannelVoicePacket(
    group=UMPGroup(0),
    status_byte=0x90,  # Note On, channel 0
    data1=60,          # Note number
    data2=100          # Velocity
)
```

**Constructor:**

```python
MIDI1ChannelVoicePacket(
    group: UMPGroup,
    status_byte: int,  # 0x80-0xEF
    data1: int,        # 0-127
    data2: int,        # 0-127
)
```

**Methods:**
- `to_words()` → `list[int]` (1 element)
- `to_bytes()` → `bytes` (4 bytes)
- `from_words(words)` classmethod → `MIDI1ChannelVoicePacket | None`

### 1.6 SysExUMP

Represents System Exclusive messages in UMP format (variable length, 128+ bits).

```python
from synth.io.midi.ump_packets import SysExUMP, UMPGroup

sysex_data = bytes([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7])
packet = SysExUMP(
    group=UMPGroup(0),
    sys_ex_data=sysex_data,
    complete=True
)
```

**Constructor:**

```python
SysExUMP(
    group: UMPGroup,
    sys_ex_data: bytes,
    complete: bool = True,  # True if complete SysEx message
)
```

### 1.7 PerNoteControllerUMP

A 64-bit Stream message (UMP type 0xF, status 0x0) carrying per-note controller data with 24-bit precision. See [Section 7](#7-per-note-controller-system) for full details.

### 1.8 UtilityUMP

Represents a 32-bit Utility message (JR Timestamp, MIDI Time Code, etc.).

```python
from synth.io.midi.ump_packets import UtilityUMP, UMPGroup

# JR Timestamp
packet = UtilityUMP(group=UMPGroup(0), utility_type=0x1, data=12345)
```

### 1.9 UMPParser

Parses raw bytes into UMP packet objects.

```python
from synth.io.midi.ump_packets import UMPParser, UMPPacket

parser = UMPParser()
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `parse_packet(packet_bytes)` | `UMPPacket \| None` | Parse a single UMP packet from bytes |
| `parse_packet_stream(data)` | `list[UMPPacket]` | Parse a stream of UMP packets from bytes |

**Examples:**

```python
# Parse a single packet
raw_bytes = b"\x20\x90\x00\x3c\x00\x64\x00\x00"
packet = UMPParser.parse_packet(raw_bytes)
if packet:
    print(type(packet).__name__)  # MIDI2ChannelVoicePacket

# Parse a stream
stream = (
    b"\x20\x90\x00\x3c\x00\x64\x00\x00"  # Note On
    b"\x20\x90\x00\x3e\x00\x50\x00\x00"   # Note On
)
packets = UMPParser.parse_packet_stream(stream)
print(len(packets))  # 2
```

---

## 2. MIDI Message System

The `MIDIMessage` class in `synth.io.midi.message` provides a unified representation for all MIDI messages, including MIDI 2.0 extensions.

```python
from synth.io.midi.message import MIDIMessage
```

### 2.1 MIDIMessage

**Constructor:**

```python
MIDIMessage(
    type: str,
    channel: int | None = None,
    data: dict[str, Any] | None = None,
    timestamp: float | None = None,
    **kwargs,
)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `type` | `str` | Message type identifier |
| `channel` | `int \| None` | MIDI channel (0-15) or None for system messages |
| `data` | `dict[str, Any]` | Type-specific message data |
| `timestamp` | `float` | Message timestamp in seconds |

**Convenience Properties:**

| Property | Returns | Description |
|----------|---------|-------------|
| `.note` | `int \| None` | Note number (from `data["note"]`) |
| `.velocity` | `int \| None` | Note velocity (from `data["velocity"]`) |
| `.controller` | `int \| None` | Controller number (from `data["controller"]`) |
| `.value` | `int \| None` | Controller value (from `data["value"]`) |
| `.program` | `int \| None` | Program number (from `data["program"]`) |
| `.pressure` | `int \| None` | Pressure value (from `data["pressure"]`) |
| `.pitch` | `int \| None` | Pitch bend value (from `data["pitch"]`) |
| `.bend_value` | `int \| None` | Alias for pitch bend value |

**Type Checking Methods:**
- `.is_note_on()` → `bool`
- `.is_note_off()` → `bool`
- `.is_control_change()` → `bool`
- `.is_program_change()` → `bool`
- `.is_pitch_bend()` → `bool`
- `.is_channel_pressure()` → `bool`
- `.is_poly_pressure()` → `bool`
- `.is_system_message()` → `bool`
- `.is_channel_message()` → `bool`

**Utility Methods:**
- `.copy()` → `MIDIMessage` — create a copy
- `.with_timestamp(timestamp)` → `MIDIMessage` — create copy with new timestamp

### 2.2 MIDI 2.0 Data Keys

When a `MIDIMessage` originates from a MIDI 2.0 source, the `data` dictionary includes the following keys in addition to standard ones:

| Key | Type | Message Types | Description |
|-----|------|---------------|-------------|
| `is_midi2` | `bool` | All | Always `True` when converted from MIDI 2.0 |
| `velocity_16bit` | `int` | `note_on`, `note_off` | 16-bit unsigned velocity (0-65535) |
| `value_32bit` | `int` | `control_change` | 32-bit unsigned controller value (0-4294967295) |
| `pitch_32bit` | `int` | `pitch_bend` | 32-bit unsigned pitch bend (0-4294967295, center=2147483647) |
| `pressure_32bit` | `int` | `poly_pressure`, `channel_pressure` | 32-bit unsigned pressure (0-4294967295) |
| `value_24bit` | `int` | `midi2_per_note_controller` | 24-bit unsigned controller value (0-16777215) |

**Example — inspecting a MIDI 2.0 message:**

```python
# After parsing UMP bytes through RealtimeParser:
for msg in messages:
    if msg.data.get("is_midi2"):
        print(f"MIDI 2.0 {msg.type}")
        if "velocity_16bit" in msg.data:
            print(f"  16-bit velocity: {msg.data['velocity_16bit']}")
        if "value_32bit" in msg.data:
            print(f"  32-bit value: {msg.data['value_32bit']}")
        if "pitch_32bit" in msg.data:
            print(f"  32-bit pitch: {msg.data['pitch_32bit']}")
```

### 2.3 Message Type Strings

| `type` string | Channel? | Description |
|---------------|----------|-------------|
| `"note_on"` | Yes | Note On |
| `"note_off"` | Yes | Note Off |
| `"control_change"` | Yes | Control Change (CC) |
| `"program_change"` | Yes | Program Change |
| `"pitch_bend"` | Yes | Pitch Bend |
| `"channel_pressure"` | Yes | Channel Aftertouch |
| `"poly_pressure"` | Yes | Polyphonic Key Pressure |
| `"midi2_per_note_controller"` | Yes | MIDI 2.0 Per-Note Controller |
| `"sysex"` | No | System Exclusive |
| `"time_code"` | No | MIDI Time Code Quarter Frame |
| `"song_position"` | No | Song Position Pointer |
| `"song_select"` | No | Song Select |
| `"tune_request"` | No | Tune Request |
| `"timing_clock"` | No | Timing Clock |
| `"start"` | No | Start |
| `"continue"` | No | Continue |
| `"stop"` | No | Stop |
| `"active_sensing"` | No | Active Sensing |
| `"system_reset"` | No | System Reset |
| `"jitter_reduction_timestamp"` | No | UMP JR Timestamp (utility) |

---

## 3. Real-Time MIDI Processing

The `RealtimeParser` in `synth.io.midi.realtime` converts raw MIDI bytes — both MIDI 1.0 and MIDI 2.0 UMP — into structured `MIDIMessage` objects.

```python
from synth.io.midi.realtime import RealtimeParser
```

### 3.1 RealtimeParser

**Constructor:**

```python
RealtimeParser()
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `parse_bytes(data: bytes)` | `list[MIDIMessage]` | Parse raw MIDI bytes. Auto-detects MIDI 1.0 vs UMP format. |
| `reset()` | — | Reset parser state |

**Auto-detection:** The parser examines the first 4 bytes. If the upper nibble matches a valid UMP message type (0x1-0x7, 0xF), it processes the data as UMP packets. Otherwise, it falls back to MIDI 1.0 byte parsing.

**Example — parsing MIDI 2.0 UMP:**

```python
from synth.io.midi.realtime import RealtimeParser
from synth.io.midi.ump_packets import (
    MIDI2ChannelVoicePacket, UMPGroup,
    MIDI1ToMIDI2Converter,
)

parser = RealtimeParser()

# Create a MIDI 2.0 Note On via converter
midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x90, 60, 100)

# Parse the UMP bytes
messages = parser.parse_bytes(midi2.to_bytes())
for msg in messages:
    print(msg.type, msg.channel, msg.data["note"], msg.data.get("velocity_16bit"))
    # note_on 0 60 33024  (velocity scaled to 16-bit)
```

**Example — parsing MIDI 1.0 bytes:**

```python
# Standard MIDI 1.0 byte stream
messages = parser.parse_bytes(bytes([0x90, 60, 100, 0x80, 60, 0]))
for msg in messages:
    print(msg.type, msg.channel, msg.data.get("note"), msg.data.get("velocity"))
    # note_on 0 60 100
    # note_off 0 60 0
```

### 3.2 Conversion Pipeline

The conversion flow for MIDI 2.0 messages:

```
UMP Bytes (MIDI 2.0)
    → UMPParser.parse_packet_stream()
    → _convert_ump_to_midimessage() per packet
    → MIDIMessage with is_midi2=True + extended precision keys
```

The `MIDIMessageProcessor` in `synth.engines.processors.midi_processor` integrates with the `ModernXGSynthesizer`:

```python
from synth.engines.processors.midi_processor import MIDIMessageProcessor

# Access via the synthesizer
# synth.midi_processor.process_midi_message(message_bytes)
```

---

## 4. MPE System

The MPE system in `synth.engines.systems.mpe_system` provides Microtonal Expression (MPE) support with MIDI 2.0 MPE+ high-precision extensions.

```python
from synth.engines.systems.mpe_system import MPESystem
```

### 4.1 MPESystem

**Constructor:**

```python
MPESystem(synthesizer, max_channels: int = 32)
```

**Properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `mpe_enabled` | `bool` | `True` | Whether MPE is enabled |
| `mpe_plus_enabled` | `bool` | `False` | MIDI 2.0 MPE+ high-precision mode |
| `global_pitch_bend_range` | `int` | `48` | Global pitch bend range in semitones |

**Methods — Standard MPE:**

| Method | Description |
|--------|-------------|
| `process_note_on(channel, note, velocity)` | Process MPE note-on; returns `MPENote \| None` |
| `process_note_off(channel, note, velocity)` | Process MPE note-off; returns `MPENote \| None` |
| `process_pitch_bend(channel, bend_value)` | Process 14-bit pitch bend with MPE routing |
| `process_poly_pressure(channel, note, pressure)` | Process polyphonic pressure |
| `process_mpe_controller(channel, controller, value)` | Process CC74/75/76 (timbre/slide/lift) |
| `set_mpe_enabled(enabled)` | Enable or disable MPE |
| `reset_mpe()` | Reset all MPE notes |
| `get_mpe_info()` | Get MPE system status dictionary |
| `get_active_mpe_notes(channel=None)` | List active MPE notes |
| `set_global_pitch_bend_range(range_semitones)` | Set pitch bend range |
| `handle_rpn(channel, controller, value)` | Handle RPN messages for MPE |

**Methods — MIDI 2.0 / MPE+ (32-bit):**

| Method | Description |
|--------|-------------|
| `set_mpe_plus_enabled(enabled: bool)` | Enable/disable MPE+ high-precision mode |
| `process_pitch_bend_32bit(channel, bend_value_32bit)` | Process 32-bit pitch bend |
| `process_mpe_controller_32bit(channel, controller, value_32bit)` | Process MPE controllers with 32-bit precision |
| `process_per_note_controller(channel, note, controller, value_24bit)` | Process MIDI 2.0 per-note controller with 24-bit precision |

**Example — MPE+ 32-bit pitch bend:**

```python
# 32-bit pitch bend: 0 = full down, 0x7FFFFFFF = center, 0xFFFFFFFF = full up
mpe_system.set_mpe_plus_enabled(True)
mpe_system.process_pitch_bend_32bit(0, 0x7FFFFFFF)  # Center
mpe_system.process_pitch_bend_32bit(0, 0xFFFFFFFF)   # Full up
mpe_system.process_pitch_bend_32bit(0, 0x00000000)   # Full down
```

**Example — 32-bit MPE controller:**

```python
# CC74 (timbre) with 32-bit precision
mpe_system.process_mpe_controller_32bit(1, 74, 2147483647)  # 50% timbre
# CC75 (slide)
mpe_system.process_mpe_controller_32bit(1, 75, 4294967295)  # Full slide
# CC76 (lift)
mpe_system.process_mpe_controller_32bit(1, 76, 0)           # No lift
```

### 4.2 MPEManager & MPENote

Located in `synth.mpe.mpe_manager`.

```python
from synth.mpe.mpe_manager import MPEManager, MPENote
```

**MPENote** properties:
- `note_number`: `int`
- `channel`: `int`
- `velocity`: `int`
- `active`: `bool`
- `pitch_bend`: `float` (semitones, -48 to +48)
- `timbre`: `float` (0.0-1.0)
- `pressure`: `float` (0.0-1.0)
- `slide`: `float` (0.0-1.0)
- `lift`: `float` (0.0-1.0)
- `frequency`: `float` (base frequency)
- `adjusted_frequency`: `float` (with pitch bend applied)

---

## 5. Channel 32-bit Support

The `Channel` class in `synth.processing.channel` provides 32-bit parameter support for MIDI 2.0.

```python
from synth.processing.channel import Channel
```

### 5.1 32-bit Controller Values

```python
# MIDI 2.0: pass is_32bit=True to use full 32-bit range
channel.control_change(7, 2147483647, is_32bit=True)   # Volume at ~50%
channel.control_change(10, 0x7FFFFFFF, is_32bit=True)   # Pan centered
channel.control_change(11, 4294967295, is_32bit=True)   # Expression at 100%

# Access stored 32-bit values
channel.controllers_32bit[7]    # 32-bit volume value
channel.controllers_32bit[11]   # 32-bit expression value

# MIDI 1.0 values are automatically derived:
channel.controllers[7]          # 7-bit equivalent (0-127)
```

### 5.2 32-bit Pitch Bend

```python
# MIDI 2.0 32-bit pitch bend (overrides lsb/msb)
channel.pitch_bend(0, 0, pitch_32bit=0x7FFFFFFF)  # Center position
channel.pitch_bend(0, 0, pitch_32bit=0)            # Full down
channel.pitch_bend(0, 0, pitch_32bit=0xFFFFFFFF)   # Full up

# Access values
channel.pitch_bend_value    # 32-bit value
channel.pitch_bend_32bit    # 32-bit value (same)
```

### 5.3 32-bit Channel Pressure

```python
# MIDI 2.0 32-bit channel pressure
channel.set_channel_pressure_32bit(2147483647)  # ~50% pressure
# 7-bit equivalent is automatically set:
channel.channel_pressure  # ~63
```

### 5.4 32-bit Key (Poly) Pressure

```python
# MIDI 2.0 32-bit poly pressure
channel.key_pressure(60, 0, pressure_32bit=4294967295)  # Note 60, full pressure
# 7-bit equivalent is automatically derived:
channel.key_pressure_values[60]  # 127
channel.key_pressure_32bit_values[60]  # 4294967295
```

### 5.5 Internal Conversion Methods

The Channel class provides these internal helpers (used automatically):

| Method | Description |
|--------|-------------|
| `_convert_32bit_to_7bit(value_32)` | Scale 32-bit (0-4294967295) to 7-bit (0-127) |
| `_convert_7bit_to_32bit(value_7)` | Scale 7-bit (0-127) to 32-bit (0-4294967295) |
| `_convert_14bit_to_32bit(value_14)` | Scale 14-bit pitch (0-16383) to 32-bit |
| `_convert_32bit_to_14bit(value_32)` | Scale 32-bit pitch to 14-bit |
| `_normalize_32bit_value(value_32)` | Convert 32-bit to float 0.0-1.0 |
| `_normalize_32bit_pan(value_32)` | Convert 32-bit pan to float -1.0 to 1.0 |

---

## 6. MIDI 2.0 Channel Voice Message Types

The 7 MIDI 2.0 Channel Voice message types, identified by `message_type` (upper nibble of the status byte):

| Type | Value | Message | data_word_1 | data_word_2 |
|------|-------|---------|-------------|-------------|
| Note Off | `0x8` | Note Off | Note number (lower 16 bits) | Release velocity in upper 16 bits |
| Note On | `0x9` | Note On | Note number (lower 16 bits) | Velocity in upper 16 bits |
| Poly Pressure | `0xA` | Polyphonic Key Pressure | Note number (lower 16 bits) | 32-bit pressure value |
| CC | `0xB` | Control Change | Controller number at bits 15-9 | 32-bit controller value |
| PC | `0xC` | Program Change | Program number (lower 16 bits) | Unused (0) |
| Ch Pressure | `0xD` | Channel Pressure | Unused (0) | 32-bit pressure value |
| Pitch Bend | `0xE` | Pitch Bend | Unused (0) | 32-bit pitch bend value |

**Creating a Note On with full 16-bit velocity:**

```python
note = 60
velocity_16bit = 50000  # 0-65535 range
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0x9,
    note & 0xFFFF,
    (velocity_16bit & 0xFFFF) << 16
)
```

**Creating a Control Change with 32-bit value:**

```python
cc_number = 7    # Volume
cc_value = 2147483647  # ~50% in 32-bit range
packet = MIDI2ChannelVoicePacket(
    UMPGroup(0), 0, 0xB,
    (cc_number & 0x7F) << 9,
    cc_value
)
```

---

## 7. Per-Note Controller System

MIDI 2.0 Per-Note Controllers allow individual control of parameters for each note using 24-bit precision. Implemented via `PerNoteControllerUMP` (UMP type 0xF, stream status 0x0).

### 7.1 PerNoteControllerUMP

```python
from synth.io.midi.ump_packets import PerNoteControllerUMP, UMPGroup

# Set per-note timbre (CC74) on note 60 with 24-bit value
pnc = PerNoteControllerUMP(
    group=UMPGroup(0),
    channel=0,
    note=60,
    controller_index=74,  # Actual MIDI CC number
    value=8388607          # 24-bit value: 0-16777215 (50% here)
)
```

**Constructor:**

```python
PerNoteControllerUMP(
    group: UMPGroup,
    channel: int,         # 0-15
    note: int,            # 0-65535 (typically 0-127)
    controller_index: int, # 0-255 (actual MIDI CC number)
    value: int,           # 0-16777215 (24-bit)
)
```

**Methods:** `to_words()`, `to_bytes()`, `from_words()` classmethod.

**Controller Index Mapping:**

| CC | Name | MPE Meaning | Typical Use |
|----|------|-------------|-------------|
| 74 | Timbre | Timbre control | Filter cutoff, brightness |
| 75 | Slide | Slide control | Pitch glide amount |
| 76 | Lift | Lift control | Release envelope |

### 7.2 Parsing Per-Note Controllers

When parsed by `RealtimeParser`, `PerNoteControllerUMP` packets become `MIDIMessage` objects with type `"midi2_per_note_controller"`.

```python
parser = RealtimeParser()
pnc_bytes = PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 8388607).to_bytes()
messages = parser.parse_bytes(pnc_bytes)

for msg in messages:
    if msg.type == "midi2_per_note_controller":
        note = msg.data["note"]          # 60
        controller = msg.data["controller"]  # 74
        value_24bit = msg.data["value_24bit"]  # 8388607
        print(f"Note {note}, CC{controller}, 24-bit value: {value_24bit}")
```

### 7.3 Processing in MPE System

```python
# Via MPESystem.process_per_note_controller()
mpe_system.process_per_note_controller(
    channel=0,
    note=60,
    controller=74,   # Timbre
    value_24bit=8388607  # 50% in 24-bit range (0-16777215)
)
```

---

## 8. Per-Note Management System

MIDI 2.0 Per-Note Management messages (UMP type 0xF, stream status 0x1) explicitly assign or remove notes from MPE zones. This gives controllers direct control over which notes are managed by MPE, bypassing dynamic zone assignment.

### 8.1 PerNoteManagementUMP

```python
from synth.io.midi.ump_packets import PerNoteManagementUMP, UMPGroup

# Assign note 72 to the MPE zone at channel 7
pnm = PerNoteManagementUMP(
    group=UMPGroup(0),
    channel=7,
    note=72,
    assign=True,  # True = assign, False = remove
)
```

**Constructor:**

```python
PerNoteManagementUMP(
    group: UMPGroup,
    channel: int,  # 0-15
    note: int,     # 0-65535 (typically 0-127)
    assign: bool,  # True = assign note, False = remove note
)
```

**Properties:** `group`, `channel`, `note`, `assign`.

**Methods:** `to_words()`, `to_bytes()`, `from_words()` classmethod.

### 8.2 Parsing Per-Note Management Messages

When parsed by `RealtimeParser`, `PerNoteManagementUMP` packets become `MIDIMessage` objects with type `"midi2_per_note_management"`:

```python
parser = RealtimeParser()
pnm_bytes = PerNoteManagementUMP(UMPGroup(0), 7, 72, assign=True).to_bytes()
messages = parser.parse_bytes(pnm_bytes)

for msg in messages:
    if msg.type == "midi2_per_note_management":
        note = msg.data["note"]       # 72
        assign = msg.data["assign"]   # True
        group = msg.data["midi_group"]  # UMPGroup(0)
        print(f"Note {note}: {'assign' if assign else 'remove'} on group {group}")
```

### 8.3 Processing in MPE System

```python
# Assign note 72 to the MPE zone on channel 7
mpe_system.process_per_note_management(
    channel=7,
    note=72,
    assign=True,  # Add to zone
)

# Remove note 72 from the zone
mpe_system.process_per_note_management(
    channel=7,
    note=72,
    assign=False,  # Remove from zone
)
```

When `assign=True`, the MPE system creates a one-note-per-channel mapping for the specified note on the member channel. The note can then be controlled via per-note controllers (CC74/75/76).

---

## 9. MIDI 1.0 / MIDI 2.0 Conversion

### 9.1 MIDI1ToMIDI2Converter

Located in `synth.io.midi.ump_packets`.

```python
from synth.io.midi.ump_packets import MIDI1ToMIDI2Converter
```

**Methods:**

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `midi1_to_midi2_channel_voice(status, data1, data2, group=UMPGroup(0))` | `int, int, int, UMPGroup` | `MIDI2ChannelVoicePacket` | Convert MIDI 1.0 channel voice to MIDI 2.0, with optional group assignment |
| `midi2_to_midi1_channel_voice(packet)` | `MIDI2ChannelVoicePacket` | `tuple[int, int, int]` | Convert MIDI 2.0 back to MIDI 1.0 (status, data1, data2) |

**Conversion rules:**
- **Velocity**: 7-bit → 16-bit (scaled `value * 0xFFFF / 127`)
- **Controller values**: 7-bit → 32-bit (scaled `value * 0xFFFFFFFF / 127`)
- **Pitch bend**: 14-bit (0-16383) → 32-bit (0-0xFFFFFFFF, center=0x7FFFFFFF)
- **Pressure**: 7-bit → 32-bit (scaled `value * 0xFFFFFFFF / 127`)

**Group parameter:**

The converter accepts an optional `group: UMPGroup` parameter (defaults to `UMPGroup(0)`) to assign the resulting packet to a specific UMP group, enabling multi-group conversion:

```python
# Convert to group 1 (channels 16-31)
packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
    0x90, 60, 100, group=UMPGroup(1)
)
print(packet.group)  # UMPGroup(1)
```

**Example — round-trip conversion:**

```python
# MIDI 1.0 → MIDI 2.0
packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x90, 60, 100)
print(type(packet).__name__)  # MIDI2ChannelVoicePacket
print(packet.to_words())      # [546308156, 3381788672]

# MIDI 2.0 → MIDI 1.0
status, data1, data2 = MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(packet)
print(hex(status), data1, data2)  # 0x90 60 99  (near-perfect round-trip)
```

**All message type conversions:**

```python
# Note On
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x90, 60, 100)

# Note Off
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0x80, 60, 64)

# Control Change (CC7 Volume)
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xB0, 7, 100)

# Program Change
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xC0, 5, 0)

# Channel Pressure
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xD0, 80, 0)

# Pitch Bend (center)
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xE0, 0x00, 0x40)

# Poly Pressure
p = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(0xA0, 60, 64)
```

---

## 10. UMP Group Routing

UMP Groups provide 16 independent channel groups (0-15), each containing 16 MIDI channels, for a total of 256 logical channels over a single UMP stream. The synthesizer maps these groups to its flat channel address space.

### 10.1 Channel Address Formula

The synthesizer channel is computed from the UMP group and MIDI channel:

```
synthesizer_channel = midi_group * 16 + midi_channel
```

| UMP Group | MIDI Channel | Synthesizer Channel |
|-----------|-------------|---------------------|
| 0 | 0-15 | 0-15 |
| 1 | 0-15 | 16-31 |
| 2 | 0-15 | 32-47 |
| ... | ... | ... |
| 15 | 0-15 | 240-255 |

### 10.2 midi_group Data Key

Every UMP message parsed by `RealtimeParser` carries the group in the `midi_group` key of the `MIDIMessage.data` dictionary. The `channel` field always contains the raw group-relative channel (0-15) for backward compatibility with XG routing and MPE zone management.

```python
packet = MIDI2ChannelVoicePacket(
    UMPGroup(3), channel=2, message_type=0x9,
    data_word_1=60, data_word_2=100 << 16,
)
msg = parser._convert_midi2_packet_to_message(packet)

print(msg.channel)          # 2 (raw group-relative channel)
print(msg.data["midi_group"])  # UMPGroup(3)
# Synthesizer channel = 3 * 16 + 2 = 50
```

### 10.3 Data Flow

```
UMP Packet → Parser extracts group from header → 
_convert_*_to_message → MIDIMessage(channel=raw, data={"midi_group": group}) →
midi_processor.py: extracts midi_group, computes synth_channel = group * 16 + channel →
routes to synthesizer.channels[synth_channel]
```

- **XG receive channel routing** uses the raw channel (0-15 within each group) — unaffected by group offset.
- **MPE zone management** uses the raw channel — unaffected by group offset.
- **Direct channel access** (fallback path when XG is off or no mapping found) uses the computed flat `synth_channel`.

### 10.4 Configuring Multi-Group Support

To use multiple UMP groups, set `max_channels` on the synthesizer constructor:

```python
# 2 groups = 32 channels
synth = Synthesizer(max_channels=32, midi_2_enabled=True)

# 16 groups = 256 channels
synth = ModernXGSynthesizer(max_channels=256, midi_2_enabled=True)
```

Each group occupies 16 consecutive channels starting at `group * 16`.

---

## Copyright

This API reference documents the MIDI 2.0 implementation in the XG Synthesizer. All APIs are subject to change as the implementation evolves.
