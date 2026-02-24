# S.Art2 SYSEX Format Specification

**Version:** 1.0  
**Package:** `synth.xg.sart`  
**Date:** 2026-02-23

---

## Table of Contents

1. [SYSEX Basics](#sysex-basics)
2. [S.Art2 SYSEX Format](#sart2-sysex-format)
3. [Command Reference](#command-reference)
4. [Checksum Calculation](#checksum-calculation)
5. [Examples](#examples)

---

## SYSEX Basics

### **What is SYSEX?**

SYSEX (System Exclusive) is a MIDI message type that allows manufacturers to define custom messages for their devices.

### **SYSEX Message Format**

```
F0 [Manufacturer ID] [Device ID] [Data...] F7
│  │                 │           │       └─ End of SYSEX
│  │                 │           └──────── Data bytes
│  │                 └──────────────────── Device ID
│  └────────────────────────────────────── Manufacturer ID
└───────────────────────────────────────── Start of SYSEX
```

### **Yamaha SYSEX Format**

```
F0 43 [Device ID] 4C [Command] [Data...] F7
│  │  │           │   │
│  │  │           │   └─ S.Art2 Command
│  │  │           └───── S.Art2 ID (0x4C)
│  │  └───────────────── Device ID (0x10 = Channel 1)
│  └──────────────────── Yamaha ID (0x43)
└─────────────────────── Start of SYSEX
```

---

## S.Art2 SYSEX Format

### **Standard Format**

```
F0 43 10 4C [CMD] [CHANNEL] [DATA...] [CHECKSUM] F7
```

| Byte | Name | Range | Description |
|------|------|-------|-------------|
| 0 | F0 | 0xF0 | Start of SYSEX |
| 1 | Manufacturer | 0x43 | Yamaha |
| 2 | Device ID | 0x00-0x0F | Device/Channel |
| 3 | Model ID | 0x4C | S.Art2 |
| 4 | Command | 0x10-0x17 | Command type |
| 5 | Channel | 0x00-0x0F | MIDI channel |
| 6...n | Data | 0x00-0x7F | Command data |
| n+1 | Checksum | 0x00-0x7F | Yamaha checksum |
| n+2 | F7 | 0xF7 | End of SYSEX |

---

## Command Reference

### **0x10: Articulation Set**

Set articulation for a channel.

**Format:**
```
F0 43 10 4C 10 [CHANNEL] [ART_MSB] [ART_LSB] [CHECKSUM] F7
```

| Byte | Name | Description |
|------|------|-------------|
| 6 | ART_MSB | Articulation MSB |
| 7 | ART_LSB | Articulation LSB |

**Example: Set legato on channel 1**
```
F0 43 10 4C 10 00 01 01 4E F7
```

**Python:**
```python
from synth.xg.sart import ArticulationController

controller = ArticulationController()
sysex = controller.build_sysex_articulation_set(
    channel=0,
    art_msb=1,
    art_lsb=1  # legato
)
```

---

### **0x11: Articulation Parameter**

Set articulation parameter.

**Format:**
```
F0 43 10 4C 11 [CHANNEL] [PARAM_MSB] [PARAM_LSB] [VALUE_MSB] [VALUE_LSB] [CHECKSUM] F7
```

| Byte | Name | Description |
|------|------|-------------|
| 6 | PARAM_MSB | Parameter MSB |
| 7 | PARAM_LSB | Parameter LSB |
| 8 | VALUE_MSB | Value MSB (0-127) |
| 9 | VALUE_LSB | Value LSB (0-127) |

**Value Calculation:**
```python
value = (VALUE_MSB << 7) | VALUE_LSB  # Range: 0-16383
```

**Example: Set vibrato rate to 0.5 Hz on channel 1**
```
F0 43 10 4C 11 00 00 00 40 00 3E F7
           │  │  │  │  │  │
           │  │  │  │  │  └─ Checksum
           │  │  │  │  └──── VALUE_LSB = 0
           │  │  │  └─────── VALUE_MSB = 64 (0x40)
           │  │  └────────── PARAM_LSB = 0
           │  └───────────── PARAM_MSB = 0
           └──────────────── CHANNEL = 0
```

**Python:**
```python
sysex = controller.build_sysex_parameter_set(
    channel=0,
    param_msb=0,
    param_lsb=0,
    value=8192  # 0.5 Hz
)
```

---

### **0x12: Articulation Release**

Release articulation (reset to normal).

**Format:**
```
F0 43 10 4C 12 [CHANNEL] [CHECKSUM] F7
```

**Example: Release articulation on channel 1**
```
F0 43 10 4C 12 00 6B F7
```

**Python:**
```python
sysex = bytes([0xF0, 0x43, 0x10, 0x4C, 0x12, 0x00, checksum, 0xF7])
```

---

### **0x13: Articulation Query**

Query current articulation.

**Format:**
```
F0 43 10 4C 13 [CHANNEL] [CHECKSUM] F7
```

**Response:**
```
F0 43 10 4C 13 [CHANNEL] [ART_MSB] [ART_LSB] [CHECKSUM] F7
```

**Example: Query articulation on channel 1**
```
Request:  F0 43 10 4C 13 00 6C F7
Response: F0 43 10 4C 13 00 01 01 4E F7  # legato
```

**Python:**
```python
sysex = controller.build_sysex_articulation_query(channel=0)
```

---

### **0x14: Articulation Chain**

Set articulation chain with timing.

**Format:**
```
F0 43 10 4C 14 [CHANNEL] [COUNT] [ART1_MSB] [ART1_LSB] [DUR1_MSB] [DUR1_LSB] ... [CHECKSUM] F7
```

| Byte | Name | Description |
|------|------|-------------|
| 6 | COUNT | Number of articulations (1-127) |
| 7...n | Articulations | [ART_MSB] [ART_LSB] [DUR_MSB] [DUR_LSB] per articulation |

**Duration Calculation:**
```python
duration_ms = (DUR_MSB << 7) | DUR_LSB  # Range: 0-16383 ms
duration_sec = duration_ms / 1000.0
```

**Example: Chain legato (500ms) → staccato (300ms) on channel 1**
```
F0 43 10 4C 14 00 02 01 01 01 F4 01 02 01 2C XX F7
           │  │  │  │  │  │  │  │  │  │  │  │
           │  │  │  │  │  │  │  │  │  │  │  └─ Checksum
           │  │  │  │  │  │  │  │  │  │  └──── DUR_LSB (staccato)
           │  │  │  │  │  │  │  │  │  └─────── DUR_MSB (staccato)
           │  │  │  │  │  │  │  │  └────────── ART_LSB (staccato)
           │  │  │  │  │  │  │  └───────────── ART_MSB (staccato)
           │  │  │  │  │  │  └──────────────── DUR_LSB (legato)
           │  │  │  │  │  └─────────────────── DUR_MSB (legato)
           │  │  │  │  └────────────────────── ART_LSB (legato)
           │  │  │  └───────────────────────── ART_MSB (legato)
           │  │  └──────────────────────────── COUNT = 2
           │  └─────────────────────────────── CHANNEL = 0
```

**Python:**
```python
chain = [
    ('legato', 0.5),    # 500ms
    ('staccato', 0.3)   # 300ms
]
sysex = controller.build_sysex_articulation_chain(channel=0, chain=chain)
```

---

### **0x15: Bulk Dump**

Dump articulation presets.

**Format:**
```
F0 43 10 4C 15 [CHANNEL] [DATA...] [CHECKSUM] F7
```

**Data Format:**
```
[PRESET_COUNT] [PRESET1_DATA] [PRESET2_DATA] ...
```

**Example: Dump presets on channel 1**
```
F0 43 10 4C 15 00 [DATA...] [CHECKSUM] F7
```

**Python:**
```python
# Build bulk dump
sysex = controller.build_sysex_bulk_dump(channel=0, articulations=['legato', 'staccato'])
```

---

### **0x16: Bulk Load**

Load articulation presets.

**Format:**
```
F0 43 10 4C 16 [CHANNEL] [DATA...] [CHECKSUM] F7
```

**Example: Load presets on channel 1**
```
F0 43 10 4C 16 00 [DATA...] [CHECKSUM] F7
```

**Python:**
```python
sysex = controller.build_sysex_bulk_load(channel=0, articulations=['legato', 'staccato'])
```

---

### **0x17: System Config**

Set system configuration.

**Format:**
```
F0 43 10 4C 17 [CHANNEL] [CONFIG_MSB] [CONFIG_LSB] [VALUE] [CHECKSUM] F7
```

| Byte | Name | Description |
|------|------|-------------|
| 6 | CONFIG_MSB | Configuration MSB |
| 7 | CONFIG_LSB | Configuration LSB |
| 8 | VALUE | Configuration value (0-127) |

**Example: Set system config on channel 1**
```
F0 43 10 4C 17 00 00 00 40 XX F7
```

**Python:**
```python
sysex = controller.build_sysex_system_config(
    channel=0,
    config_msb=0,
    config_lsb=0,
    value=64
)
```

---

## Checksum Calculation

### **Yamaha SYSEX Checksum**

```python
def calculate_checksum(data: bytes) -> int:
    """
    Calculate Yamaha SYSEX checksum.
    
    Yamaha checksum: invert lower 7 bits of sum
    
    Args:
        data: SYSEX data (excluding F0 and F7)
    
    Returns:
        Checksum byte (0-127)
    """
    checksum = sum(data) & 0x7F
    return (~checksum) & 0x7F
```

### **Example Calculation**

**Data:** `43 10 4C 10 00 01 01` (Articulation Set, legato, channel 1)

```python
data = bytes([0x43, 0x10, 0x4C, 0x10, 0x00, 0x01, 0x01])
checksum = calculate_checksum(data)
# checksum = 0x4E
```

**Full SYSEX:**
```
F0 43 10 4C 10 00 01 01 4E F7
```

---

## Examples

### **Python Examples**

```python
from synth.xg.sart import ArticulationController

controller = ArticulationController()

# 1. Set articulation
sysex = controller.build_sysex_articulation_set(
    channel=0,
    art_msb=1,
    art_lsb=1  # legato
)
# Result: F0 43 10 4C 10 00 01 01 4E F7

# 2. Set parameter
sysex = controller.build_sysex_parameter_set(
    channel=0,
    param_msb=0,
    param_lsb=0,
    value=8192  # vibrato rate 0.5 Hz
)
# Result: F0 43 10 4C 11 00 00 00 40 00 3E F7

# 3. Articulation chain
chain = [
    ('legato', 0.5),
    ('staccato', 0.3),
    ('marcato', 0.2)
]
sysex = controller.build_sysex_articulation_chain(channel=0, chain=chain)

# 4. Bulk dump
sysex = controller.build_sysex_bulk_dump(
    channel=0,
    articulations=['legato', 'staccato', 'marcato']
)

# 5. Process SYSEX
result = controller.process_sysex(sysex_bytes)
print(result['command'])  # 'set_articulation'
```

### **MIDI Monitor Examples**

**Set legato on channel 1:**
```
TX: F0 43 10 4C 10 00 01 01 4E F7
```

**Set staccato on channel 2:**
```
TX: F0 43 10 4C 10 01 01 02 4D F7
```

**Set vibrato rate on channel 1:**
```
TX: F0 43 10 4C 11 00 00 00 40 00 3E F7
```

**Articulation chain:**
```
TX: F0 43 10 4C 14 00 02 01 01 01 F4 01 02 01 2C XX F7
```

---

## See Also

- [`SART2_API_REFERENCE.md`](SART2_API_REFERENCE.md) - Complete API reference
- [`SART2_NRPN_GUIDE.md`](SART2_NRPN_GUIDE.md) - NRPN mapping guide
- [`SART2_SWITCHING_GUIDE.md`](SART2_SWITCHING_GUIDE.md) - Velocity/Key switching guide

---

**End of SYSEX Format Specification**
