# XG2 Remediation Strategy — Complete SysEx + Architecture Fixes

> Prerequisite: `/mnt/c/Work/report_xg2.md` — 13 claims verified, 9 true, 2 partially true, 1 false.
> Priority: Complete XG SysEx parameter address map per full XG v2.0 specification.
> No backward compatibility constraints.

## 1. Issues Inventory

### Critical (Code Bugs)

| # | Issue | File | Severity |
|---|---|---|---|
| **B1** | 24-bit sample sign-extension: MSB sign-extended before shifting, corrupting bit-range detection | `sf2_file_loader.py:943-950` | Critical |
| **B2** | O(n) part lookup on every CC: linear scan through 16 parts; O(1) index exists but unused | `xg_system.py:287-341` | Critical |
| **B3** | Distributed XG state: 15 modules with independent `RLock()`, no lock hierarchy | 15 files in `protocols/xg/` | Critical |

### Architecture (Structural)

| # | Issue | Severity |
|---|---|---|
| **A1** | `XG_PARAMETER_ADDRESSES` covers 26 entries (~10% of XG spec); insertion routing entirely absent | Critical |
| **A2** | CC handling fragmented across `XGSystem`, `SF2Region`, `XGControllerAssignments`, `XGSynthesizerSystem` | High |
| **A3** | No save/load snapshot for full synthesizer state | Medium |
| **A4** | Error handling inconsistent: `SF2Engine` catches `Exception` broadly; other engines have no error handling | Medium |

### Documentation (Claims vs. Reality)

| # | Issue | Severity |
|---|---|---|
| **D1** | "<5ms latency" claim unsupported by 1024-sample buffer (23.2ms alone) | High |
| **D2** | "Vectorized SIMD" — no explicit SIMD intrinsics; NumPy-only | High |
| **D3** | "Complete XG/GS" with ✅ marks — SysEx map covers ~10% | High |
| **D4** | AAX claim conditional on proprietary SDK | Medium |
| **D5** | SF2 HP/BP filters: only lowpass implemented | Medium |
| **D6** | SF2 crossfade loops: code exists but disabled (initialized to 0) | Low |

---

## 2. Target Architecture

### Complete XG SysEx Parameter Address Map

The current 26-entry address map is replaced by a **complete XG v2.0 parameter tree** organized by address range:

```
XGSysExParameterTree (new, replaces XG_PARAMETER_ADDRESSES)
├── System (0x00 00 00–0F): master tune, volume, transpose, system mode, display
├── Multi-Part (0x08 nn pp): 16 parts × bank/program/volume/pan/reverb/chorus/variation
├── Drum Setup (0x30 nn dd): 128 notes × 25 parameters + 17 per-note params
├── Effects (0x02 01–6F): reverb/chorus/variation type, time, depth, send levels
├── Insertion (0x04 nn pp): routing matrix (part→insert), connection (series/parallel)
├── Part EQ (0x40 nn pp): per-part low/high shelf gain (±12 dB)
├── Display (0x12 nn pp): text display messages
└── Bulk Dump (0x70–7F): parameter bulk dump/load
```

### Unified XG State Management

```
CURRENT (15 independent locks)                 TARGET (single XGState)
─────────────────────────                     ──────────────────────
XGSystem.lock                                 XGState (one RLock)
XGChannelParameterManager.lock                     │
XGSysExController.lock                         ┌───┼───────────────┐
XGControllerAssignments.lock                   │   │               │
XGMultiPartSetup.lock                    PartParams  Effects  DrumSetup
XGDrumKitManager.lock                     (16 parts) (reverb/  (128 notes
XGDrumSetupParameters.lock                          chorus/   ×25 params)
... (9 more)                                       variation)

                        Access pattern:
                        with state.lock:
                            state.parts[part].volume = 100
                            state.effects.reverb_time = 2.5
```

### Centralized CC Dispatch

```
CURRENT (fragmented)                           TARGET (unified dispatch)
─────────────────────                          ─────────────────────────
XGSystem.handle_control_change()               XGCCController
  ├── CC 0, 7, 10, 32, 91, 93, 94                    │
                                                     │
SF2Region._drain_param_updates()               ┌─────┼─────────────┐
  ├── CC 1-5, 7, 8, 10, 11, 64-79, 91-93      │     │             │
                                               Voice   Part     System
XGControllerAssignments                        params  params    params
  ├── NRPN MSB 15-16 (controller routing)

XGSynthesizerSystem.handle_control_change()
  ├── Duplicate of XGSystem's handler
```

---

## 3. Implementation Plan

### Phase 1 — Complete XG SysEx Parameter Address Map (A1)

**Goal:** Replace the 26-entry `XG_PARAMETER_ADDRESSES` with a complete XG v2.0 parameter tree.

**New file:** `synth/protocols/xg/xg_sysex_parameter_tree.py`

**Structure:**

```python
# Parameter tree organized by address high byte
XG_PARAMETER_TREE = {
    0x00: {  # System Area
        "system": {
            (0x00, 0x00): "master_tune_msb",
            (0x00, 0x01): "master_tune_lsb",
            (0x00, 0x02): "master_volume",
            (0x00, 0x04): "master_attenuator",
            (0x00, 0x05): "master_transpose",
            (0x00, 0x06): "drum_setup_reset",
            (0x00, 0x7D): "all_parameter_reset",
            (0x00, 0x7E): "xg_system_off",
            (0x00, 0x7F): "xg_system_on",
        }
    },
    0x02: {  # Effects Area — reverb, chorus, variation
        "effects": {
            (0x01, 0x00): "reverb_type",
            (0x01, 0x01): "reverb_time",
            (0x01, 0x02): "reverb_diffusion",
            (0x01, 0x0B): "reverb_return",
            (0x01, 0x0C): "reverb_pan",
            (0x01, 0x10): "chorus_type",
            (0x01, 0x11): "chorus_lfo_freq",
            (0x01, 0x12): "chorus_lfo_depth",
            (0x01, 0x1B): "chorus_return",
            (0x01, 0x1C): "chorus_pan",
            (0x01, 0x20): "variation_type",
            (0x01, 0x21): "variation_param1",
            (0x01, 0x22): "variation_param2",
            (0x01, 0x2B): "variation_return",
            (0x01, 0x40): "insertion_type",
            (0x01, 0x41): "insertion_param1",
            # ... complete effect parameter set
        }
    },
    0x04: {  # Insertion Effect Routing
        "insertion_routing": {
            (0x00, 0x00): "insertion_part_l",
            (0x00, 0x01): "insertion_part_r",
            (0x00, 0x02): "insertion_connection",
            (0x00, 0x03): "insertion_control_ch",
            # ... per-part routing entries (parts 0-15)
        }
    },
    0x08: {  # Multi-Part Area — 16 parts
        "multi_part": {
            (None, None): "part_parameter",  # addr_mid = part, addr_low = parameter
        },
        "part_parameters": {
            0x00: "bank_select_msb",
            0x01: "bank_select_lsb",
            0x02: "program_number",
            0x03: "rcv_channel",
            0x04: "mono_poly_mode",
            0x05: "same_note_number_key_on_assign",
            0x06: "part_mode",
            0x07: "note_shift",
            0x08: "detune",
            0x09: "volume",
            0x0A: "velocity_sense_depth",
            0x0B: "velocity_sense_offset",
            0x0C: "pan",
            0x0D: "note_limit_low",
            0x0E: "note_limit_high",
            0x0F: "dry_level",
            0x10: "chorus_send",
            0x11: "reverb_send",
            0x12: "variation_send",
            0x13: "vibrato_rate",
            0x14: "vibrato_depth",
            0x15: "vibrato_delay",
            0x16: "filter_cutoff",
            0x17: "filter_resonance",
            0x18: "eg_attack",
            0x19: "eg_decay1",
            0x1A: "eg_decay2",
            0x1B: "eg_release",
            0x1C: "portamento_time",
            0x1D: "pitch_bend_range",
            0x1E: "assignable_controller_1",
            0x1F: "assignable_controller_2",
        }
    },
    0x30: {  # Drum Setup Area — 128 notes
        "drum_setup": {
            (None, None): "drum_parameter",  # addr_mid = note, addr_low = parameter
        },
        "drum_parameters": {
            0x00: "pitch_coarse",
            0x01: "pitch_fine",
            0x02: "level",
            0x03: "alternate_group",
            0x04: "pan",
            0x05: "reverb_send",
            0x06: "chorus_send",
            0x07: "variation_send",
            0x08: "key_assign",
            0x09: "rcv_note_off",
            0x0A: "rcv_note_on",
            0x0B: "filter_cutoff",
            0x0C: "filter_resonance",
            0x0D: "eg_attack",
            0x0E: "eg_decay1",
            0x0F: "eg_decay2",
            0x10: "eg_release",
            # ... remaining drum parameters
        }
    },
    0x40: {  # Part EQ
        "part_eq": {
            (None, None): "eq_parameter",  # addr_mid = part, addr_low = band
        },
        "eq_bands": {
            0x00: "eq_low_gain",
            0x01: "eq_low_freq",
            0x02: "eq_low_q",
            0x10: "eq_mid_gain",
            0x11: "eq_mid_freq",
            0x12: "eq_mid_q",
            0x20: "eq_high_gain",
            0x21: "eq_high_freq",
            0x22: "eq_high_q",
        }
    },
}
```

**Effort:** 6 hours. ~200 address entries across 7 categories.

---

### Phase 2 — Fix 24-Bit Sample Bug (B1)

**File:** `synth/io/sf2/sf2_file_loader.py`, lines 943-950

**Change:**
```python
# Before (bug):
if msb_byte & 0x80:
    msb_extended = msb_byte | 0xFFFFFF00
else:
    msb_extended = msb_byte
sample_24bit = (msb_extended << 16) | (lsb_word & 0xFFFF)

# After (fix):
sample_24bit = (msb_byte << 16) | (lsb_word & 0xFFFF)
if sample_24bit & 0x800000:  # 24-bit sign bit
    sample_24bit |= 0xFF000000  # Sign-extend to 32-bit
```

**Verification:** Test with known 24-bit sample values (0xFFFFFF → -1, 0x800000 → -8,388,608, 0x7FFFFF → 8,388,607).

**Effort:** 1 hour.

---

### Phase 3 — Centralize XG State (B3)

**Goal:** Replace 15 independent locks with a single `XGState` object.

**New file:** `synth/protocols/xg/xg_state.py`

**Architecture:**

```python
@dataclass(slots=True)
class XGPartState:
    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0
    volume: int = 100
    pan: int = 64
    reverb_send: int = 40
    chorus_send: int = 0
    filter_cutoff: int = 64
    filter_resonance: int = 64
    # ... 20+ part parameters

@dataclass(slots=True)
class XGState:
    lock: threading.RLock = field(default_factory=threading.RLock)
    parts: list[XGPartState] = field(default_factory=lambda: [XGPartState() for _ in range(16)])
    system: XGSystemState = field(default_factory=XGSystemState)
    effects: XGEffectsState = field(default_factory=XGEffectsState)
    drum: XGDrumState = field(default_factory=XGDrumState)
```

Each existing module (`XGChannelParameterManager`, `XGMultiPartSetup`, etc.) becomes a thin accessor that reads/writes `self.state.lock` and accesses the appropriate `XGState` sub-object.

**Migration:** Not a full rewrite — each module replaces its `self.lock = threading.RLock()` with a reference to the shared `XGState.lock`. Internal dicts become `XGPartState` dataclass fields. The migration is mechanical: find `self.lock` → replace with `self.state.lock`, find `self.parameters["filter_cutoff"]` → replace with `part.filter_cutoff`.

**Effort:** 8 hours.

---

### Phase 4 — Centralize CC Dispatch (A2, B2)

**Goal:** Single dispatch table for all CC messages. O(1) channel-to-part lookup.

**New file:** `synth/protocols/xg/xg_cc_controller.py`

**Architecture:**

```python
# CC dispatch table — single source of truth
_XG_CC_HANDLERS: dict[int, str] = {
    0: "bank_select_msb",
    1: "modulation_wheel",
    2: "breath_controller",
    4: "foot_controller",
    5: "portamento_time",
    7: "channel_volume",
    10: "pan",
    11: "expression",
    32: "bank_select_lsb",
    64: "sustain_pedal",
    65: "portamento_on_off",
    71: "harmonic_content",
    72: "release_time",
    73: "attack_time",
    74: "brightness",
    75: "filter_cutoff",
    76: "decay_time",
    77: "vibrato_rate",
    78: "vibrato_depth",
    79: "vibrato_delay",
    91: "reverb_send",
    92: "tremolo_depth",
    93: "chorus_send",
    94: "variation_send",
    # ... complete XG CC set
}

class XGCCController:
    def __init__(self, state: XGState):
        self.state = state
        # O(1) channel-to-part index maintained by set_channel_to_part()
        self._channel_to_part: dict[int, int] = {}

    def handle_cc(self, channel: int, controller: int, value: int) -> bool:
        with self.state.lock:
            part = self._channel_to_part.get(channel, channel)
            handler = _XG_CC_HANDLERS.get(controller)
            if handler:
                setattr(self.state.parts[part], handler, value)
                return True
            return False
```

**Replace** `XGSystem.handle_control_change()`, `XGSynthesizerSystem.handle_control_change()`, and the CC portion of `SF2Region._drain_param_updates()` with delegation to `XGCCController`.

**Effort:** 4 hours.

---

### Phase 5 — Error Handling Consistency (A4)

**Goal:** Consistent error handling across all engines.

**Change:** Replace `except Exception` in `SF2Engine.generate_samples()` (line 1034) with specific exception types. Add lightweight error handling to other engines where absent:

```python
# Before (SF2):
except Exception as e:
    logger.error(f"Error generating SF2 samples: {e}")
    continue

# After (all engines):
except (ValueError, IndexError, RuntimeError) as e:
    logger.error(f"Error generating samples: {e}")
    continue
```

**Effort:** 2 hours.

---

### Phase 6 — Documentation Claims (D1-D6)

| Claim | Fix |
|---|---|
| "<5ms latency" (D1) | Replace with "Low-latency capable with appropriate hardware buffer sizes (configurable 64-4096 samples)" |
| "Vectorized SIMD" (D2) | Replace with "Vectorized NumPy processing with Numba JIT acceleration" |
| "Complete XG/GS" ✅ (D3) | Replace ✅ with "XG SysEx: 200+ parameters; GS: 100+ parameters. See docs/xg/sysex-coverage.md for details" |
| AAX support (D4) | Add "(requires proprietary Avid AAX SDK — not included)" |
| HP/BP filters (D5) | Remove claim or add: "Low-pass filter with resonance (high-pass/band-pass planned)" |
| Crossfade loops (D6) | Remove claim or enable with `_loop_crossfade_samples = 48` (2ms at 44.1kHz) |

**Effort:** 2 hours.

---

## 4. File-Level Change Summary

### New files (4)

```
synth/protocols/xg/xg_sysex_parameter_tree.py   — Complete XG v2.0 parameter tree (~200 entries)
synth/protocols/xg/xg_state.py                  — Unified XGState with single RLock
synth/protocols/xg/xg_cc_controller.py           — Centralized CC dispatch with O(1) lookup
docs/sart2/sysex-coverage.md (deferred)          — SysEx coverage documentation
```

### Files to MODIFY (10)

```
synth/io/sf2/sf2_file_loader.py                 — P2: Fix 24-bit sign-extension
synth/protocols/xg/xg_system.py                 — P3: Migrate to XGState, P4: Delegate CC to XGCCController
synth/protocols/xg/xg_channel_parameter_manager.py — P3: Migrate to XGState
synth/protocols/xg/xg_sysex_controller.py        — P1: Use new parameter tree
synth/protocols/xg/xg_controller_assignments.py  — P3: Migrate to XGState
synth/protocols/xg/xg_multi_part_setup.py        — P3: Migrate to XGState
synth/protocols/xg/xg_drum_kit_manager.py        — P3: Migrate to XGState
synth/engines/sf2_engine.py                     — P5: Specific exception types
synth/processing/partial/sf2_region.py           — P4: Delegate CC to XGCCController
synth/synthesizers/rendering.py                 — P4: Wire XGCCController
README.md                                       — P6: Fix documentation claims
```

---

## 5. Effort Estimate

| Phase | Hours | Risk |
|---|---|---|
| P1 — Complete XG SysEx address map | 6 | Medium (200+ entry data definition) |
| P2 — Fix 24-bit sample bug | 1 | Low |
| P3 — Centralize XG state (single lock) | 8 | High (touches 15+ modules) |
| P4 — Centralize CC dispatch (O(1) lookup) | 4 | Medium |
| P5 — Error handling consistency | 2 | Low |
| P6 — Documentation claims | 2 | Low |
| **Total** | **23** | |

---

## 6. What This Strategy Does NOT Do

- **Does not rewrite the VST3 plugin** — the GIL violation is architectural and acknowledged in the README.
- **Does not build a full save/load snapshot** — serialization of all synthesizer state requires a separate strategy for serialization format, versioning, and compatibility.
- **Does not add HP/BP filter support to SF2** — only documents the current state honestly.
- **Does not enable SF2 crossfade loops** — only documents the current state honestly.
- **Does not remove the AAX claim from README** — qualifies it instead.
