# SF2Region MIDI Controller Implementation Plan

## Overview

This plan documents the implementation of full MIDI controller support in SF2Region, following the removal of the legacy VectorizedChannelRenderer/XGPartialGenerator path.

## Current State

SF2Region currently handles:
- CC1 (Mod Wheel) - partially
- CC10 (Pan) - yes
- CC71/72 - but **swapped** (bug)

SF2Region has slots for:
- `_breath_mod`, `_foot_mod`, `_expression_mod` - but these are read from the modulation dict, not from direct CC handling

## Missing Controllers to Implement

| CC | Name | Current Status | Implementation Priority |
|----|------|----------------|------------------------|
| 2 | Breath Controller | Slot exists, not applied | High |
| 4 | Foot Controller | Slot exists, not applied | High |
| 5 | Portamento Time | Not implemented | Medium |
| 8 | Balance | Not implemented | Medium |
| 11 | Expression | Slot exists, not applied | High |
| 64 | Sustain | Not directly handled | High |
| 65 | Portamento On/Off | Not implemented | Medium |
| 66 | Sostenuto | Not implemented | Medium |
| 67 | Soft Pedal | Not implemented | Medium |
| 68 | Legato | Not implemented | Medium |
| 69 | Hold 2 | Not implemented | Medium |
| 70 | Sound Controller 1 | Not implemented | Medium |
| 71 | Harmonic Content | **SWAPPED** - needs fix | High |
| 72 | Brightness | **SWAPPED** - needs fix | High |
| 73 | Release Time | Not implemented | High |
| 74 | Attack Time | Not implemented | High |
| 75 | Filter Cutoff | Not implemented | High |
| 76 | Decay Time | Not implemented | High |
| 77 | Vibrato Rate | Not implemented | Medium |
| 78 | Vibrato Depth | Not implemented | Medium |
| 79 | Vibrato Delay | Not implemented | Medium |
| 80 | GP Button 1 | Not implemented | Low |
| 81 | GP Button 2 | Not implemented | Low |
| 82 | GP Button 3 | Not implemented | Low |
| 83 | GP Button 4 | Not implemented | Low |
| 92 | Tremolo Depth | Not implemented | Medium |

---

## Phase 1: Infrastructure (Slots and Storage)

### 1.1 Add New __slots__

```python
# In __slots__ list, add:

# Portamento
"_portamento_active",
"_portamento_time",
"_portamento_note",

# Pedals
"_sustain_pedal",
"_sostenuto_pedal", 
"_soft_pedal",
"_legato_active",
"_hold2_pedal",

# XG Sound Controllers
"_sound_controller_1",

# Envelope/Vibrato XG (CC73-79)
"_xg_release_time",
"_xg_attack_time",
"_xg_filter_cutoff",
"_xg_decay_time",
"_xg_vibrato_rate",
"_xg_vibrato_depth",
"_xg_vibrato_delay",

# General Purpose Buttons
"_gp_button_1",
"_gp_button_2", 
"_gp_button_3",
"_gp_button_4",

# Tremolo (CC92)
"_tremolo_depth",

# Balance
"_balance",

# Previous note for portamento
"_last_note",
```

### 1.2 Initialize in __init__

```python
# Portamento
self._portamento_active = False
self._portamento_time = 0.0
self._portamento_note = None

# Pedals
self._sustain_pedal = False
self._sostenuto_pedal = False
self._soft_pedal = False
self._legato_active = False
self._hold2_pedal = False

# XG Controllers
self._sound_controller_1 = 0.0
self._xg_release_time = 0.0
self._xg_attack_time = 0.0
self._xg_filter_cutoff = 0.0
self._xg_decay_time = 0.0
self._xg_vibrato_rate = 0.0
self._xg_vibrato_depth = 0.0
self._xg_vibrato_delay = 0.0

# GP Buttons
self._gp_button_1 = 0.0
self._gp_button_2 = 0.0
self._gp_button_3 = 0.0
self._gp_button_4 = 0.0

# Tremolo
self._tremolo_depth = 0.0

# Balance
self._balance = 0.0

# Portamento state
self._last_note = None
```

---

## Phase 2: Main Controller Handler

### 2.1 Add control_change() Method

```python
def control_change(self, controller: int, value: int) -> None:
    """
    Handle MIDI control change message.
    
    Args:
        controller: CC number (0-127)
        value: CC value (0-127)
    """
    normalized = value / 127.0
    
    if controller == 1:  # Modulation Wheel
        self._modwheel_mod = normalized
    elif controller == 2:  # Breath Controller
        self._breath_mod = normalized
        self._apply_breath_controller(normalized)
    elif controller == 4:  # Foot Controller
        self._foot_mod = normalized
        self._apply_foot_controller(normalized)
    elif controller == 5:  # Portamento Time
        self._portamento_time = self._calculate_portamento_time(value)
    elif controller == 7:  # Volume (handled by channel)
        pass
    elif controller == 8:  # Balance
        self._balance = (value - 64) / 64.0  # -1.0 to 1.0
    elif controller == 10:  # Pan (already handled)
        self._pan_position = (value - 64) / 64.0
    elif controller == 11:  # Expression
        self._expression_mod = normalized
    elif controller == 64:  # Sustain
        self._sustain_pedal = value >= 64
        self._handle_sustain_pedal(value >= 64)
    elif controller == 65:  # Portamento On/Off
        self._portamento_active = value >= 64
    elif controller == 66:  # Sostenuto
        self._sostenuto_pedal = value >= 64
        self._handle_sostenuto_pedal(value >= 64)
    elif controller == 67:  # Soft Pedal
        self._soft_pedal = value >= 64
        self._apply_soft_pedal(normalized)
    elif controller == 68:  # Legato
        self._legato_active = value >= 64
    elif controller == 69:  # Hold 2
        self._hold2_pedal = value >= 64
        self._handle_hold2_pedal(value >= 64)
    elif controller == 70:  # Sound Controller 1
        self._sound_controller_1 = normalized
        self._apply_sound_controller_1(normalized)
    elif controller == 71:  # Harmonic Content (FIX SWAP)
        # XG Spec: CC71 = Harmonic Content (filter resonance)
        self._apply_harmonic_content(normalized)
    elif controller == 72:  # Brightness (FIX SWAP)
        # XG Spec: CC72 = Brightness (filter cutoff)
        self._apply_brightness(normalized)
    elif controller == 73:  # Release Time
        self._xg_release_time = normalized
        self._apply_xg_release_time(normalized)
    elif controller == 74:  # Attack Time
        self._xg_attack_time = normalized
        self._apply_xg_attack_time(normalized)
    elif controller == 75:  # Filter Cutoff
        self._xg_filter_cutoff = normalized
        self._apply_xg_filter_cutoff(normalized)
    elif controller == 76:  # Decay Time
        self._xg_decay_time = normalized
        self._apply_xg_decay_time(normalized)
    elif controller == 77:  # Vibrato Rate
        self._xg_vibrato_rate = normalized
        self._apply_xg_vibrato_rate(normalized)
    elif controller == 78:  # Vibrato Depth
        self._xg_vibrato_depth = normalized
        self._apply_xg_vibrato_depth(normalized)
    elif controller == 79:  # Vibrato Delay
        self._xg_vibrato_delay = normalized
        self._apply_xg_vibrato_delay(normalized)
    elif controller == 80:  # GP Button 1
        self._gp_button_1 = normalized
    elif controller == 81:  # GP Button 2
        self._gp_button_2 = normalized
    elif controller == 82:  # GP Button 3
        self._gp_button_3 = normalized
    elif controller == 83:  # GP Button 4
        self._gp_button_4 = normalized
    elif controller == 91:  # Reverb Send
        self._reverb_send = normalized
    elif controller == 92:  # Tremolo Depth
        self._tremolo_depth = normalized
        self._apply_tremolo_depth(normalized)
    elif controller == 93:  # Chorus Send
        self._chorus_send = normalized
```

---

## Phase 3: Individual Controller Handlers

### 3.1 Portamento (CC5, CC65)

```python
def _calculate_portamento_time(self, value: int) -> float:
    """Calculate portamento time from CC value."""
    # XG formula: 0-64 = 0-1s, 64-127 = 1-8s (logarithmic)
    if value < 64:
        return value / 64.0  # 0-1 second
    else:
        return 1.0 + (value - 64) / 63.0 * 7.0  # 1-8 seconds

def _apply_portamento(self, note: int) -> None:
    """Apply portamento glide to target note."""
    if self._portamento_active and self._last_note is not None:
        # Calculate pitch delta
        pitch_delta = (note - self._last_note) / 12.0
        # Glide will be applied in sample generation
```

### 3.2 Pedals (CC64, CC66, CC67, CC69)

```python
def _handle_sustain_pedal(self, active: bool) -> None:
    """Handle sustain pedal (CC64)."""
    if active:
        # Sustain: keep envelope in sustain state
        pass  # Envelope continues at sustain level
    else:
        # Release
        if hasattr(self, '_amp_envelope'):
            self._amp_envelope.start_release()

def _handle_sostenuto_pedal(self, active: bool) -> CC66:
    """Handle sostenuto pedal - only sustains currently playing notes."""
    # Unlike sustain, this only holds notes that were playing when pedal was pressed
    pass

def _apply_soft_pedal(self, depth: float) -> None:
    """Apply soft pedal (CC67) - reduce volume by up to -40%."""
    volume_reduction = 1.0 - (depth * 0.4)  # -40% at max
    self._volume_mod *= volume_reduction
```

### 3.3 XG Envelope/Vibrato (CC73-79)

```python
def _apply_xg_release_time(self, normalized: float) -> None:
    """CC73: XG Release Time - modify amp envelope release."""
    # Formula: 0 = -∞, 1 = +72dB range
    if hasattr(self, '_amp_envelope'):
        release_time = 0.001 + normalized * 4.999  # 1ms to 5s
        self._amp_envelope.release = release_time

def _apply_xg_attack_time(self, normalized: float) -> None:
    """CC74: XG Attack Time - modify amp envelope attack."""
    if hasattr(self, '_amp_envelope'):
        attack_time = 0.001 + normalized * 9.999  # 1ms to 10s
        self._amp_envelope.attack = attack_time

def _apply_xg_decay_time(self, normalized: float) -> None:
    """CC76: XG Decay Time - modify amp envelope decay."""
    if hasattr(self, '_amp_envelope'):
        decay_time = 0.01 + normalized * 4.99  # 10ms to 5s
        self._amp_envelope.decay = decay_time

def _apply_xg_filter_cutoff(self, normalized: float) -> None:
    """CC75: XG Filter Cutoff - modify filter cutoff."""
    # +1 octave per 32 values, centered
    cutoff_mod = (normalized - 0.5) * 2.0  # -1 to +1
    self._filter_mod += cutoff_mod * 2.0  # ±2 octaves

def _apply_harmonic_content(self, normalized: float) -> None:
    """CC71: XG Harmonic Content - modify filter resonance."""
    # Higher = more resonance
    base_resonance = getattr(self, '_filter_resonance', 0.7)
    self._filter_resonance = base_resonance * (0.5 + normalized)

def _apply_brightness(self, normalized: float) -> None:
    """CC72: XG Brightness - modify filter cutoff."""
    # Higher = brighter (higher cutoff)
    base_cutoff = getattr(self, '_filter_cutoff', 1000.0)
    self._filter_cutoff = base_cutoff * (0.5 + normalized * 2.0)

def _apply_xg_vibrato_rate(self, normalized: float) -> None:
    """CC77: XG Vibrato Rate - modify vib LFO rate."""
    if self._vib_lfo:
        rate = 0.5 + normalized * 8.0  # 0.5Hz to 8.5Hz
        self._vib_lfo.set_frequency(rate)

def _apply_xg_vibrato_depth(self, normalized: float) -> None:
    """CC78: XG Vibrato Depth - modify vib LFO depth."""
    self._vib_lfo_to_pitch = normalized * 1.0  # Up to 1 semitone

def _apply_xg_vibrato_delay(self, normalized: float) -> None:
    """CC79: XG Vibrato Delay - modify vib LFO delay."""
    self._delay_vib_lfo = normalized * 2.0  # 0-2 seconds delay
```

### 3.4 Tremolo (CC92)

```python
def _apply_tremolo_depth(self, normalized: float) -> None:
    """CC92: Tremolo Depth - amplitude LFO depth."""
    self._mod_lfo_to_volume = normalized
```

### 3.5 Other Handlers

```python
def _apply_breath_controller(self, normalized: float) -> None:
    """CC2: Breath Controller - typically controls filter."""
    self._filter_mod += normalized * 1.0
    self._breath_mod = normalized

def _apply_foot_controller(self, normalized: float) -> None:
    """CC4: Foot Controller - typically controls vibrato or volume."""
    self._foot_mod = normalized
    self._vib_lfo_to_pitch += normalized * 0.5

def _apply_sound_controller_1(self, normalized: float) -> CC70:
    """CC70: Sound Controller 1 - XG variation."""
    # Can be mapped to various parameters, default to filter
    self._filter_mod += (normalized - 0.5) * 1.0
```

---

## Phase 4: Integration with Note On/Off

### 4.1 Update note_on

```python
def note_on(self, note: int, velocity: int) -> None:
    # Existing code...
    
    # Handle portamento
    if self._portamento_active and self._last_note is not None:
        self._portamento_note = self._last_note
        self._portamento_target = note
        # Enable portamento glide in pitch
    
    self._last_note = note
```

### 4.2 Update note_off

```python
def note_off(self, velocity: int) -> None:
    # Handle sostenuto - don't release if held by sostenuto
    if self._sostenuto_pedal:
        # Mark as held but don't start release
        self._held_by_sostenuto = True
    else:
        # Normal release
        self._start_amp_envelope_release()
    
    # Handle hold2
    if self._hold2_pedal:
        self._held_by_hold2 = True
```

---

## Phase 5: Sample Generation Integration

### 5.1 Apply Controllers in generate_samples

```python
def generate_samples(...) -> np.ndarray:
    # Existing modulation...
    
    # Apply tremolo (CC92)
    if self._tremolo_depth > 0 and self._mod_lfo_buffer is not None:
        tremolo_mod = 1.0 - self._tremolo_depth * (1.0 - self._mod_lfo_buffer)
        output *= tremolo_mod
    
    # Apply balance (CC8)
    if self._balance != 0.0:
        # Apply stereo balance
        output = self._apply_stereo_balance(output, self._balance)
    
    # Apply soft pedal
    if self._soft_pedal:
        output *= 0.6  # -40% volume reduction
    
    # Apply portamento glide
    if self._portamento_note is not None:
        # Apply pitch glide
        pass
```

---

## Implementation Order

1. **Phase 1**: Add slots and initialize
2. **Phase 2**: Add main control_change() method with switch statement
3. **Phase 3**: Implement individual controller handlers
4. **Phase 4**: Integrate with note_on/note_off
5. **Phase 5**: Integrate with sample generation
6. **Testing**: Add unit tests for each controller

---

## Testing Plan

```python
def test_portamento_time():
    region = SF2Region(...)
    region.control_change(5, 64)  # 50% = ~0.5s
    assert region._portamento_time == pytest.approx(0.5, rel=0.1)

def test_portamento_on():
    region = SF2Region(...)
    region.control_change(65, 127)  # On
    assert region._portamento_active == True

def test_sustain_pedal():
    region = SF2Region(...)
    region.control_change(64, 127)  # On
    assert region._sustain_pedal == True

def test_xg_release_time():
    region = SF2Region(...)
    region.control_change(73, 64)  # 50%
    # Check amp envelope release modified

def test_cc71_harmonic_content():
    """Verify CC71 controls harmonic content (not brightness)."""
    region = SF2Region(...)
    region.control_change(71, 127)  # Max
    # Should increase resonance

def test_cc72_brightness():
    """Verify CC72 controls brightness (not harmonic content)."""
    region = SF2Region(...)
    region.control_change(72, 127)  # Max
    # Should increase filter cutoff

def test_tremolo():
    region = SF2Region(...)
    region.control_change(92, 64)  # 50%
    assert region._tremolo_depth == 0.5
```

---

## Backward Compatibility

- Default controller values match GM/XG spec
- Unimplemented CCs are ignored (no change to behavior)
- Existing SF2 generators take precedence over CC overrides
