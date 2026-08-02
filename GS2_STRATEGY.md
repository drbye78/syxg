# GS2 Remediation Strategy — Implement Features, Preserve Claims

> Prerequisite: `/mnt/c/Work/report_gs2.md` — 13 claims verified, 7 true, 5 overstated, 2 stale.
> Principle: **Implement missing features, don't remove claims.**
> No backward compatibility constraints.

## 1. Issues Inventory

| # | Issue | Severity | File | Action |
|---|---|---|---|---|
| **F1** | JV-2080 MFX: 42 types with identical stub parameters `{0:64,1:64,2:64,3:64}` | **Critical** | `jv2080_component_manager.py:757` | Implement per-type parameter definitions |
| **F2** | VCM effects: marketed as "Virtual Circuit Modeling" but uses standard DSP (tanh, polynomial) | **High** | `jupiter_x_vcm_effects.py` | Add nonlinear saturation stages + rebrand claims |
| **F3** | Plugin engines: all 5 `generate_samples()` return `None` (stubs) | **Critical** | `plugins/jupiter_x/*_extensions.py` | Implement actual audio processing |
| **F4** | GS drum composite noise: SC-8850 noise params absent | **Medium** | `gs_sysex_handler.py:drum_key_param_map` | Add noise component parameters |
| **F5** | GS instrument bank map: no Roland GS sound name dictionary | **Medium** | New file | Add GS sound map data |
| **F6** | Jupiter-X midi_controller: 120 lines, no CC mapping | **Medium** | `jupiter_x/midi_controller.py` | Add CC→parameter dispatch table |
| **F7** | No GS-specific CC handler | **Low** | `gs_sysex_handler.py` | Add CC dispatch for GS-mode parameters |

### What the Review Got Wrong (No Action Needed)

- §2.2 GS routing placeholder — already wired in GS Phase 3
- §2.3 SC-8850 Temporary Area — already expanded in GS Phase 5
- §5.1 "Dual NRPN overlap" — only 1 parameter overlaps all 3 stacks (not worth merging)
- "Jupiter-X in README" — the README never claims this
- "GS NRPN 3,517 entries" — loop-generated, 31 unique params

---

## 2. Implementation Plan

### Phase 1 — JV-2080 MFX Parameter Definitions (F1)

**Goal:** Replace the `{0:64,1:64,2:64,3:64}` stub with per-type parameter definitions for all 42 MFX types.

**File:** `synth/protocols/gs/jv2080_component_manager.py`

**New data structure:**

```python
# Per-MFX-type parameter definitions (name, min, max, default)
JV2080_MFX_PARAMETERS: dict[int, list[tuple[str, int, int, int]]] = {
    0: [  # THRU (bypass)
        ("level", 0, 127, 127),
    ],
    1: [  # Stereo EQ
        ("low_gain", 0, 30, 15),      # -15 to +15 dB
        ("low_freq", 0, 127, 64),      # 200Hz, 400Hz
        ("mid1_gain", 0, 30, 15),
        ("mid1_freq", 0, 127, 64),
        ("mid1_q", 0, 127, 64),
        ("mid2_gain", 0, 30, 15),
        ("mid2_freq", 0, 127, 64),
        ("mid2_q", 0, 127, 64),
        ("high_gain", 0, 30, 15),
        ("high_freq", 0, 127, 64),
        ("level", 0, 127, 127),
    ],
    6: [  # Overdrive
        ("drive", 0, 127, 64),
        ("tone", 0, 127, 64),
        ("level", 0, 127, 127),
        ("amp_type", 0, 3, 0),         # Small/Built-In/2-Stack/3-Stack
    ],
    10: [ # Phaser
        ("rate", 0, 127, 64),
        ("depth", 0, 127, 64),
        ("manual", 0, 127, 64),
        ("resonance", 0, 127, 64),
        ("mix", 0, 127, 64),
        ("level", 0, 127, 127),
    ],
    23: [ # Pitch Shifter
        ("coarse", 0, 24, 12),          # -12 to +12 semitones
        ("fine", 0, 100, 50),           # -50 to +50 cents
        ("delay", 0, 127, 64),
        ("feedback", 0, 127, 64),
        ("pan", 0, 127, 64),
        ("level", 0, 127, 127),
    ],
    26: [ # Delay
        ("delay_left", 0, 127, 64),
        ("delay_right", 0, 127, 64),
        ("feedback", 0, 127, 64),
        ("damping", 0, 127, 64),
        ("pan", 0, 127, 64),
        ("level", 0, 127, 127),
    ],
    33: [ # Reverb
        ("type", 0, 5, 0),              # Room/Hall/Plate/Spring/Gate/Reverse
        ("time", 0, 127, 64),
        ("pre_delay", 0, 127, 0),
        ("damping", 0, 127, 64),
        ("diffusion", 0, 127, 64),
        ("level", 0, 127, 127),
    ],
    # ... all 42 types with their JV-2080 spec parameter sets
}
```

**Update `_get_default_parameters`:**

```python
def _get_default_parameters(self, mfx_type: int) -> dict[int, int]:
    """Get default parameters for MFX type per JV-2080 specification."""
    mfx_params = JV2080_MFX_PARAMETERS.get(mfx_type)
    if mfx_params is None:
        return {0: 64, 1: 64, 2: 64, 3: 64}
    return {i: param[3] for i, param in enumerate(mfx_params)}
```

**Update `get_parameter_name`:** Add method to return human-readable parameter names for SysEx editor display.

**Effort:** 6 hours. Most time is data entry for 42 effect types.

---

### Phase 2 — VCM Effects: Add Saturation Stages (F2)

**Goal:** Add genuine analog-style saturation to the VCM effects processor so the "Virtual Circuit Modeling" claim is substantiated by actual nonlinear DSP.

**File:** `synth/hardware/jupiter_x/jupiter_x_vcm_effects.py`

**What to add — 3 nonlinear saturation stages:**

```python
class VCMDistortionStage:
    """Soft-clipping saturation with asymmetric transfer curve (tube-like)."""
    
    def __init__(self, drive: float = 0.5, bias: float = 0.0):
        self.drive = drive
        self.bias = bias
    
    def process_sample(self, x: float) -> float:
        # Asymmetric tanh with drive and bias for tube-like warmth
        s = (x + self.bias) * (1.0 + self.drive * 3.0)
        return np.tanh(s) / (1.0 + self.drive * 0.3)

class VCMWarmthFilter:
    """Pre/post emphasis filter mimicking analog circuit frequency response."""
    
    def __init__(self, sample_rate: int):
        # Simple shelving filter for analog warmth
        self.lp_state = 0.0
        self.hp_state = 0.0
        self.cutoff = 12000.0  # Gentle high-end roll-off
    
    def process_sample(self, x: float) -> float:
        alpha = 1.0 / (1.0 + 2 * np.pi * self.cutoff / self.sample_rate)
        self.lp_state += alpha * (x - self.lp_state)
        return self.lp_state
```

**Rebrand claims:**
- Update class docstrings: "VCM-inspired digital effects with nonlinear saturation stages"
- Add comment: "Uses tanh-based soft clipping and asymmetric bias for tube-like warmth. Not bit-accurate to Roland VCM hardware, which uses proprietary component-level models."

**Effort:** 3 hours.

---

### Phase 3 — Plugin Engine Audio Processing (F3)

**Goal:** Implement actual audio processing in the 5 plugin engine `generate_samples()` methods. Each plugin adds its characteristic processing to the base engine output.

**Files:** All 5 files in `synth/engines/plugins/jupiter_x/`

**Per-plugin implementation:**

| Plugin | What It Does | DSP |
|---|---|---|
| `analog_extensions.py` | Subtractive synthesis enhancements: multi-mode filter sweep, oscillator drift | Modulated biquad filter, slow random phase offset |
| `digital_extensions.py` | Bit-crush, sample-rate reduction, digital lo-fi effects | Quantization + decimation on output |
| `fm_extensions.py` | Additional FM operator modulations, feedback path | Operator feedback with configurable ratio |
| `external_extensions.py` | Granular processing, time-stretch, glitch effects | Grain windowing, pitch randomization |
| `an_extensions.py` | Analog-style saturation, sub-oscillator mix | `tanh` saturation, octave-down mixer |

**Common pattern for `generate_samples()`:**

```python
def generate_samples(self, block_size: int, modulation: dict) -> np.ndarray | None:
    """Apply plugin-specific processing to base engine output."""
    if self._base_engine is None:
        return None
    
    # Get base engine output
    base = self._base_engine.generate_samples(block_size, modulation)
    if base is None:
        return None
    
    # Apply plugin processing
    match self._mode:
        case "bypass":
            return base
        case "filter_sweep":
            return self._apply_filter_sweep(base, block_size)
        case "saturation":
            return self._apply_saturation(base)
        # ... per-plugin modes
    
    return base
```

**Effort:** 8 hours. 5 files × ~1.5h each.

---

### Phase 4 — GS Drum Composite Noise (F4)

**Goal:** Add SC-8850 noise component parameters to the GS drum key parameter map.

**File:** `synth/protocols/gs/gs_sysex_handler.py`

**Changes:**

1. Extend `drum_key_param_map` (line 349) from 7 to 10 entries:

```python
self.drum_key_param_map = {
    0x00: "pitch_offset",
    0x01: "level",
    0x02: "pan",
    0x03: "reverb_send",
    0x04: "chorus_send",
    0x05: "key_group",
    0x06: "mute_group",
    # SC-8850 Composite Noise parameters
    0x07: "noise_pitch",      # Noise component pitch offset
    0x08: "noise_level",      # Noise component level
    0x09: "noise_pan",        # Noise component pan position
}
```

2. Add noise parameter handling in `_handle_drum_key_param()`: forward noise params through the drum setup system like other drum key parameters.

3. Add the composite noise parameters to `XGDrumSetupParameters` or the drum manager so they flow to the audio engine.

**Effort:** 2 hours.

---

### Phase 5 — GS Instrument Bank Map (F5)

**Goal:** Add a Roland GS sound name dictionary for proper instrument display.

**New file:** `synth/protocols/gs/gs_sound_map.py`

**Structure:**

```python
# Roland GS Capital Tone map (Bank 0, Program 0-127 ≈ GM)
GS_CAPITAL_TONES = {
    0: "Acoustic Grand Piano",
    1: "Bright Acoustic Piano",
    2: "Electric Grand Piano",
    # ... 128 GM-compatible names
}

# Roland GS Variation Tones (Bank 1-127)
GS_VARIATION_TONES = {
    1: {  # Bank 1 variations
        0: "Piano 1w",
        1: "Piano 1d",
        # ...
    },
    # ... per-bank variation names
}

# Roland GS Drum Kits (Bank 127)
GS_DRUM_KITS = {
    0: "Standard Kit 1",
    1: "Standard Kit 2",
    8: "Room Kit",
    16: "Power Kit",
    24: "Electronic Kit",
    25: "TR-808 Kit",
    32: "Jazz Kit",
    40: "Brush Kit",
    48: "Orchestra Kit",
}


def get_gs_instrument_name(bank_msb: int, bank_lsb: int, program: int) -> str:
    """Return instrument name for a GS bank/program combination."""
    if bank_msb == 127:
        return GS_DRUM_KITS.get(program, f"GS Drum Kit {program}")
    elif bank_msb == 0 and bank_lsb == 0:
        return GS_CAPITAL_TONES.get(program, f"GM {program}")
    else:
        variations = GS_VARIATION_TONES.get(bank_lsb, {})
        return variations.get(program, f"GS Var {bank_lsb}/{program}")
```

**Effort:** 2 hours. Mostly data entry.

---

### Phase 6 — Jupiter-X CC Mapping (F6) + GS CC Handler (F7)

**Goal:** Add CC→parameter dispatch to `midi_controller.py` and add GS-specific CC handling.

**File F6:** `synth/hardware/jupiter_x/midi_controller.py`

```python
# CC → parameter dispatch table
_JUPITER_X_CC_MAP = {
    1: ("modulation", "mod_wheel"),
    7: ("part", "volume"),
    10: ("part", "pan"),
    11: ("part", "expression"),
    64: ("part", "sustain"),
    71: ("part", "filter_resonance"),
    74: ("part", "filter_cutoff"),
    # ... complete Jupiter-X CC set
}

def _handle_cc(self, channel: int, controller: int, value: int):
    mapping = self._cc_map.get(controller)
    if mapping is None:
        return
    scope, param = mapping
    if scope == "part":
        part = self._get_part_for_channel(channel)
        if part:
            part.set_parameter(param, value / 127.0)
    elif scope == "system":
        self.component_manager.set_system_parameter(param, value)
```

**File F7:** `synth/protocols/gs/gs_sysex_handler.py`

Add a GS CC handler that forwards standard CCs through the GS parameter system when in GS mode:

```python
def handle_gs_cc(self, channel: int, controller: int, value: int) -> bool:
    """Handle MIDI CC in GS mode."""
    part_num = channel  # GS uses direct channel mapping
    if controller == 7:  # Volume
        self.set_channel_parameter(channel, "volume", value)
        return True
    elif controller == 10:  # Pan
        self.set_channel_parameter(channel, "pan", value)
        return True
    # ... other GS CCs
    return False
```

**Effort:** 3 hours (2h for Jupiter-X + 1h for GS).

---

## 3. File-Level Change Summary

### New files (1)

```
synth/protocols/gs/gs_sound_map.py              — Roland GS instrument name map
```

### Files to MODIFY (7)

```
synth/protocols/gs/jv2080_component_manager.py   — P1: 42 per-type MFX parameter definitions
synth/hardware/jupiter_x/jupiter_x_vcm_effects.py — P2: 3 saturation stages + rebrand docstring
synth/engines/plugins/jupiter_x/analog_extensions.py — P3: implement generate_samples()
synth/engines/plugins/jupiter_x/digital_extensions.py — P3: implement generate_samples()
synth/engines/plugins/jupiter_x/fm_extensions.py — P3: implement generate_samples()
synth/engines/plugins/jupiter_x/external_extensions.py — P3: implement generate_samples()
synth/engines/plugins/jupiter_x/an_extensions.py — P3: implement generate_samples()
synth/protocols/gs/gs_sysex_handler.py           — P4: drum noise params + P7: GS CC handler
synth/hardware/jupiter_x/midi_controller.py       — P6: CC→parameter dispatch table
```

---

## 4. Effort Estimate

| Phase | Hours | Risk |
|---|---|---|
| P1 — JV-2080 MFX parameter definitions | 6 | Medium (data entry for 42 types) |
| P2 — VCM saturation stages | 3 | Low |
| P3 — Plugin engine audio processing | 8 | High (5 independent implementations) |
| P4 — GS drum composite noise | 2 | Low |
| P5 — GS instrument bank map | 2 | Low (data entry) |
| P6 — Jupiter-X CC mapping | 2 | Low |
| P7 — GS CC handler | 1 | Low |
| **Total** | **24** | |

---

## 5. What This Strategy Does NOT Do

- **Does not remove VCM claims** — adds saturation stages to substantiate them.
- **Does not merge NRPN stacks** — overlap is minimal (1 parameter across all 3).
- **Does not add SC-8850 full Temporary Area** — only adds the drum composite noise parameters that are documented as missing.
- **Does not implement bit-accurate Roland VCM hardware models** — adds tanh-based saturation that is "inspired by" VCM, not a replica.
- **Does not add Jupiter-X hardware reference validation** — the Jupiter-X emulation remains best-effort reverse engineering.
