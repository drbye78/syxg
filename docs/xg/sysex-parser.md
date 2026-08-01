# XG SysEx Parser — Spec-Correct Implementation

**File:** `synth/io/midi/xg_sysex_parser.py`
**Class:** `XGSysexParser`

## Format

Real Yamaha XG SysEx uses a **3-byte address format** (not a "command byte"):

```
F0 43 1n 4C aa aa aa [dd ...] cc F7
     │  │  │  └─ 3-byte address (high, mid, low)
     │  │  └──── Model ID (0x4C = XG)
     │  └─────── Device ID (0x1n, n=0-15)
     └────────── Manufacturer ID (0x43 = Yamaha)
```

## Address Routing

| Address Pattern | Destination |
|---|---|
| `0x00 0x00 xx` | System parameters (master tune, volume, XG on/off) |
| `0x08 nn pp` | Part `nn` parameter `pp` |
| `0x30 nn dd` | Drum setup note `nn` parameter `dd` |

## Checksum

```
checksum = 128 - (sum(address) + sum(data)) % 128
```

Covers address + data only — NOT manufacturer, device, or model ID.

## Usage

```python
from synth.io.midi.xg_sysex_parser import XGSysexParser

parser = XGSysexParser(device_id=0x10)

# Build XG System On message
msg = parser.build_xg((0x00, 0x00, 0x7F))
# → F0 43 10 4C 00 00 7F 7F F7

# Parse and validate
parsed = parser.parse(msg)
assert parsed.is_valid
assert parsed.address == (0x00, 0x00, 0x7F)
```
