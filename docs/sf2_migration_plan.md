# SF2Region Feature Migration Plan
## Bringing SF2Partial Features to the Main Synthesis Pipeline

---

## 1. Executive Summary

This document outlines the implementation plan to migrate features from `SF2Partial` (currently unused) to `SF2Region` (the active synthesis implementation). The goal is to achieve full SF2 v2.04 specification compliance with sample-accurate envelope processing, complete LFO modulation, modulation matrix integration, and MIDI controller support.

---

## 2. Feature Comparison Matrix

### 2.1 Amplitude Envelope

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| ADSR stages (Delay, Attack, Hold, Decay, Sustain, Release) | ⚠️ Partial | ✅ Full | **Missing: Hold in envelope processing** |
| Sample-accurate timing | ❌ No | ✅ Yes | **Must implement** |
| Velocity-sensitive attack | ❌ No | ✅ Yes | Must implement |
| Key scaling (hold/decay) | ❌ No | ✅ Yes | Must implement |
| Release phase on note_off | ⚠️ Basic | ✅ Full | Needs improvement |
| Envelope delay generator (gen 8) | ❌ Disabled (line 393) | ✅ Full | Must enable |
| Hold generator (gen 10) | ❌ Not applied | ✅ Full | Must implement |

### 2.2 Modulation Envelope

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| ADSR envelope creation | ✅ Yes (line 416-425) | ✅ Full | **Envelope exists but NOT triggered** |
| Trigger on note_on | ❌ No | ✅ Yes | **Must implement** |
| Release on note_off | ❌ No | ✅ Yes | Must implement |
| Sample-accurate processing | ❌ No | ✅ Full | Must implement |
| Modulation to pitch (gen 20) | ⚠️ Extracted | ✅ Applied | Must apply to output |
| Modulation to filter (gen 44) | ⚠️ Extracted | ✅ Applied | Must apply to output |
| Modulation to volume (custom) | ⚠️ Extracted | ✅ Applied | Must apply to output |
| Modulation to pan (custom) | ⚠️ Extracted | ✅ Applied | Must apply to output |
| Key scaling (gen 31, 32) | ⚠️ Extracted | ✅ Applied | Must implement |

### 2.3 LFO System

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Mod LFO object | ❌ No | ✅ Yes | **Must implement** |
| Vib LFO object | ❌ No | ✅ Yes | **Must implement** |
| Mod LFO delay (gen 21) | ⚠️ Extracted | ✅ Applied | Must instantiate LFO |
| Mod LFO frequency (gen 22) | ⚠️ Extracted | ✅ Applied | Must instantiate LFO |
| Vib LFO delay (gen 26) | ⚠️ Extracted | ✅ Applied | Must instantiate LFO |
| Vib LFO frequency (gen 27) | ⚠️ Extracted | ✅ Applied | Must instantiate LFO |
| Vib LFO → pitch (gen 28) | ❌ No | ✅ Full | **Must implement** |
| Mod LFO → pitch (gen 25) | ❌ No | ✅ Full | **Must implement** |
| Mod LFO → filter (gen 24) | ❌ No | ✅ Full | **Must implement** |
| Mod LFO → volume (gen 23) | ❌ No | ✅ Full | **Must implement** |
| Mod LFO → pan (gen 42) | ❌ No | ✅ Full | Must implement |
| Vib LFO → pan (gen 37) | ❌ No | ✅ Full | Must implement |
| Per-sample LFO modulation | ❌ No | ✅ Full | Must implement |
| LFO waveform selection | ❌ No | ✅ Sine only | Should add waveforms |

### 2.4 Filter Processing

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Filter creation | ✅ Basic | ✅ Full | Adequate |
| Base cutoff from gen 29 | ✅ Yes | ✅ Yes | OK |
| Base resonance from gen 30 | ✅ Yes | ✅ Yes | OK |
| LFO → filter modulation | ❌ No | ✅ Full | Must implement |
| Mod env → filter modulation | ❌ No | ✅ Full | Must implement |
| Global modulation → filter | ❌ Ignored | ✅ Full | Must implement |

### 2.5 Modulation Matrix Integration

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Receives modulation dict | ⚠️ Parameter ignored | ✅ Full | **Must use modulation** |
| Global pitch modulation | ❌ No | ✅ Full | Must implement |
| Global filter cutoff | ❌ No | ✅ Full | Must implement |
| Global volume | ❌ No | ✅ Full | Must implement |
| Provides modulation outputs | ❌ No | ✅ Yes | Must implement |
| Controller aftertouch | ❌ No | ✅ Full | Must implement |
| Controller breath | ❌ No | ✅ Full | Must implement |
| Controller modwheel | ❌ No | ✅ Full | Must implement |
| Controller foot | ❌ No | ✅ Full | Must implement |
| Controller expression | ❌ No | ✅ Full | Must implement |

### 2.6 MIDI Controllers

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Pitch bend | ❌ No | ✅ Full | Must implement |
| Channel pressure | ❌ No | ✅ Full | Must implement |
| Polyphonic pressure | ❌ No | ✅ Full | Must implement |
| CC1 (Mod wheel) | ❌ No | ✅ Full | Must implement |
| CC2 (Breath) | ❌ No | ✅ Full | Must implement |
| CC7 (Volume) | ❌ No | ✅ Full | Must implement |
| CC10 (Pan) | ❌ No | ✅ Full | Must implement |
| CC11 (Expression) | ❌ No | ✅ Full | Must implement |
| CC64 (Sustain) | ❌ No | ✅ Full | Must implement |

### 2.7 Spatial Processing

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Pan from gen 34 | ⚠️ Not applied | ✅ Full | **Must implement** |
| Reverb send (gen 32) | ⚠️ Extracted | ✅ Full | Must send to effects |
| Chorus send (gen 33) | ⚠️ Extracted | ✅ Full | Must send to effects |
| Stereo width | ❌ No | ✅ Full | Optional |

### 2.8 Additional Advanced Features

| Feature | SF2Region | SF2Partial | Status |
|---------|-----------|------------|--------|
| Multiple LFO waveforms | ❌ Sine only | ❌ Sine only | **Must implement** |
| VCF key tracking (gen 31) | ❌ No | ❌ No | Must implement |
| Filter types (gen 36) | ❌ Lowpass only | ❌ No | Must implement |
| Velocity curves (gen 41) | ❌ Linear only | ❌ No | Must implement |
| Loop crossfade (gen 45) | ❌ No | ❌ No | Must implement |
| Pitch envelope (gen 54-59) | ❌ No | ❌ No | Must implement |
| High-quality resampling | ❌ Linear only | ❌ No | Should implement |
| Reverse playback (gen 57) | ❌ No | ❌ No | Must implement |
| Drum/one-shot mode | ❌ No | ❌ No | Must implement |
| Voice stealing | ⚠️ Basic | ❌ No | Improve |
| Microtuning | ❌ No | ❌ No | Optional |
| Insertion effects routing | ❌ No | ❌ No | Optional |
| Stereo width | ❌ No | ❌ No | Optional |

---

## 3. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Add Required Slots to SF2Region

```python
# Add to __slots__ in SF2Region
"_active",                           # Voice active state
"_mod_lfo",                          # Modulation LFO
"_vib_lfo",                          # Vibrato LFO  
"_mod_env_state",                   # Modulation envelope state
"_mod_env_buffer",                  # Modulation envelope buffer
"_vib_lfo_buffer",                  # Vib LFO buffer
"_mod_lfo_buffer",                  # Mod LFO buffer

# Pitch modulation
"_pitch_mod",                       # Current pitch modulation
"_base_phase_step",                 # Phase step without modulation

# Filter modulation
"_filter_mod",                      # Current filter cutoff modulation

# Volume/pan
"_volume_mod",                      # Current volume modulation
"_pan_position",                    # Current pan position

# Modulation sources
"_aftertouch_mod",
"_breath_mod",
"_modwheel_mod",
"_foot_mod",
"_expression_mod",

# LFO parameters (from generators)
"_delay_mod_lfo",
"_freq_mod_lfo",
"_delay_vib_lfo",
"_freq_vib_lfo",

# LFO modulation depths
"_vib_lfo_to_pitch",
"_mod_lfo_to_pitch",
"_mod_lfo_to_filter",
"_mod_lfo_to_volume",
"_vib_lfo_to_pan",
"_mod_lfo_to_pan",

# Mod env modulation depths
"_mod_env_to_pitch",
"_mod_env_to_filter",
"_mod_env_to_volume",
"_mod_env_to_pan",

# Mod env parameters
"_delay_mod_env",
"_attack_mod_env",
"_hold_mod_env",
"_decay_mod_env",
"_sustain_mod_env",
"_release_mod_env",

# Key tracking
"_keynum_to_mod_env_hold",
"_keynum_to_mod_env_decay",
"_keynum_to_vol_env_hold",
"_keynum_to_vol_env_decay",

# Effects sends
"_reverb_send",
"_chorus_send",
```

#### 1.2 Initialize LFO Objects in SF2Region

```python
def _init_lfos(self) -> None:
    """Initialize LFO objects from SF2 generators."""
    from ..core.oscillator import UltraFastXGLFO
    
    # Get LFO parameters from generators
    mod_lfo_delay = self._timecents_to_seconds(
        self._get_generator_value(21, -12000)
    )
    mod_lfo_freq = self._cents_to_frequency(
        self._get_generator_value(22, 0)
    )
    
    vib_lfo_delay = self._timecents_to_seconds(
        self._get_generator_value(26, -12000)
    )
    vib_lfo_freq = self._cents_to_frequency(
        self._get_generator_value(27, 0)
    )
    
    # Create LFO objects
    self._mod_lfo = UltraFastXGLFO(
        id=0,
        sample_rate=self.sample_rate,
        block_size=1024
    )
    self._mod_lfo.set_parameters(
        waveform="sine",
        rate=mod_lfo_freq,
        depth=1.0,
        delay=mod_lfo_delay
    )
    
    self._vib_lfo = UltraFastXGLFO(
        id=1,
        sample_rate=self.sample_rate,
        block_size=1024
    )
    self._vib_lfo.set_parameters(
        waveform="sine",
        rate=vib_lfo_freq,
        depth=1.0,
        delay=vib_lfo_delay
    )
    
    # Load LFO modulation depths from generators
    self._vib_lfo_to_pitch = self._get_generator_value(28, 0) / 100.0
    self._mod_lfo_to_pitch = self._get_generator_value(25, 0) / 100.0
    self._mod_lfo_to_filter = self._get_generator_value(24, 0) / 1200.0
    self._mod_lfo_to_volume = self._get_generator_value(23, 0) / 10.0
    self._vib_lfo_to_pan = self._get_generator_value(37, 0) / 10.0
    self._mod_lfo_to_pan = self._get_generator_value(42, 0) / 10.0
```

### Phase 2: Envelope Processing (Week 1-2)

#### 2.1 Fix Amplitude Envelope

**Current issue**: Delay generator is disabled, Hold not applied

```python
def _init_envelopes(self) -> None:
    """Initialize envelopes from SF2 generator parameters."""
    from ..core.envelope import UltraFastADSREnvelope
    
    # FIX: Enable delay from generator 8
    delay = self._timecents_to_seconds(self._get_generator_value(8, -12000))
    attack = self._timecents_to_seconds(self._get_generator_value(9, -12000))
    hold = self._timecents_to_seconds(self._get_generator_value(10, -12000))  # FIX: Was missing
    decay = self._timecents_to_seconds(self._get_generator_value(11, -12000))
    sustain = self._get_generator_value(12, 0) / 1000.0
    release = self._timecents_to_seconds(self._get_generator_value(13, -12000))
    
    self._envelopes["amp_env"] = UltraFastADSREnvelope(
        delay=delay,
        attack=attack,
        hold=hold,
        decay=decay,
        sustain=sustain,
        release=release,
        sample_rate=self.sample_rate,
    )
```

#### 2.2 Implement Modulation Envelope

```python
def _init_modulation_envelope(self) -> None:
    """Initialize modulation envelope state."""
    self._mod_env_state = {
        "stage": "idle",
        "level": 0.0,
        "stage_time": 0.0,
    }
    
    # Load modulation envelope parameters
    self._delay_mod_env = self._timecents_to_seconds(
        self._get_generator_value(14, -12000)
    )
    self._attack_mod_env = self._timecents_to_seconds(
        self._get_generator_value(15, -12000)
    )
    self._hold_mod_env = self._timecents_to_seconds(
        self._get_generator_value(16, -12000)
    )
    self._decay_mod_env = self._timecents_to_seconds(
        self._get_generator_value(17, -12000)
    )
    self._sustain_mod_env = self._get_generator_value(18, 0) / 1000.0
    self._release_mod_env = self._timecents_to_seconds(
        self._get_generator_value(19, -12000)
    )
    
    # Load modulation depths
    self._mod_env_to_pitch = self._get_generator_value(20, 0) / 1200.0
    # gen 44 = modEnvToFilterFc
    self._mod_env_to_filter = self._get_generator_value(44, 0) / 1200.0
    # Custom: modEnvToVolume
    self._mod_env_to_volume = 0.0
    # Custom: modEnvToPan
    self._mod_env_to_pan = 0.0
    
    # Load key tracking
    self._keynum_to_mod_env_hold = self._get_generator_value(31, 0) / 100.0
    self._keynum_to_mod_env_decay = self._get_generator_value(32, 0) / 100.0

def _trigger_modulation_envelope(self) -> None:
    """Trigger modulation envelope attack."""
    if self._mod_env_state:
        self._mod_env_state["stage"] = "attack"
        self._mod_env_state["level"] = 0.0
        self._mod_env_state["stage_time"] = 0.0

def _release_modulation_envelope(self) -> None:
    """Trigger modulation envelope release."""
    if self._mod_env_state:
        self._mod_env_state["stage"] = "release"

def _generate_modulation_envelope_block(self, block_size: int) -> np.ndarray:
    """Generate modulation envelope block sample-by-sample."""
    output = np.zeros(block_size, dtype=np.float32)
    
    for i in range(block_size):
        output[i] = self._calculate_modulation_envelope_sample()
        self._update_modulation_envelope_state()
    
    return output
```

### Phase 3: LFO Processing (Week 2)

#### 3.1 Generate LFO Signals

```python
def _generate_lfo_signals(self, block_size: int) -> None:
    """Generate LFO modulation signals for the block."""
    # Ensure buffers exist
    if self._mod_lfo_buffer is None:
        self._mod_lfo_buffer = np.zeros(block_size, dtype=np.float32)
    if self._vib_lfo_buffer is None:
        self._vib_lfo_buffer = np.zeros(block_size, dtype=np.float32)
    
    # Generate mod LFO
    if self._mod_lfo:
        mod_result = self._mod_lfo.generate_block(block_size)
        if isinstance(mod_result, np.ndarray):
            self._mod_lfo_buffer[:] = mod_result
        else:
            self._mod_lfo_buffer[:] = mod_result
    
    # Generate vib LFO
    if self._vib_lfo:
        vib_result = self._vib_lfo.generate_block(block_size)
        if isinstance(vib_result, np.ndarray):
            self._vib_lfo_buffer[:] = vib_result
        else:
            self._vib_lfo_buffer[:] = vib_result

def _calculate_sample_pitch_modulation(self, sample_index: int) -> float:
    """Calculate total pitch modulation for a specific sample."""
    total = self._pitch_mod
    
    # Add vibrato LFO modulation
    if self._vib_lfo_buffer is not None and sample_index < len(self._vib_lfo_buffer):
        total += self._vib_lfo_buffer[sample_index] * self._vib_lfo_to_pitch
    
    # Add modulation LFO modulation
    if self._mod_lfo_buffer is not None and sample_index < len(self._mod_lfo_buffer):
        total += self._mod_lfo_buffer[sample_index] * self._mod_lfo_to_pitch
    
    # Add modulation envelope modulation
    if self._mod_env_buffer is not None and sample_index < len(self._mod_env_buffer):
        total += self._mod_env_buffer[sample_index] * self._mod_env_to_pitch
    
    return total
```

### Phase 4: Modulation Matrix Integration (Week 2-3)

#### 4.1 Apply Global Modulation

```python
def _apply_global_modulation(self, modulation: dict[str, float]) -> None:
    """Apply modulation from modulation matrix."""
    # Pitch modulation
    self._pitch_mod = modulation.get("pitch", 0.0)
    
    # Filter modulation (in octaves)
    self._filter_mod = modulation.get("filter_cutoff", 0.0)
    
    # Volume modulation
    self._volume_mod = modulation.get("volume", 1.0)
    
    # Pan modulation
    self._pan_mod = modulation.get("pan", 0.0)
    
    # Controller sources
    self._aftertouch_mod = modulation.get("aftertouch", 0.0)
    self._breath_mod = modulation.get("breath", 0.0)
    self._modwheel_mod = modulation.get("modwheel", 0.0)
    self._foot_mod = modulation.get("foot", 0.0)
    self._expression_mod = modulation.get("expression", 0.0)
    
    # Apply controller effects
    if self._modwheel_mod != 0.0:
        # Mod wheel affects vibrato depth
        self._vib_lfo_to_pitch *= (1.0 + self._modwheel_mod)
        # Mod wheel affects filter
        self._filter_mod += self._modwheel_mod * 1.5
    
    if self._aftertouch_mod != 0.0:
        self._volume_mod *= (1.0 + self._aftertouch_mod * 0.5)
        self._filter_mod += self._aftertouch_mod * 2.0
```

#### 4.2 Provide Modulation Outputs

```python
def get_modulation_outputs(self) -> dict[str, float]:
    """Provide SF2 modulation sources to global modulation matrix."""
    outputs = {}
    
    if self._vib_lfo_buffer is not None and len(self._vib_lfo_buffer) > 0:
        outputs["sf2_vibrato_lfo"] = float(self._vib_lfo_buffer[-1])
    
    if self._mod_lfo_buffer is not None and len(self._mod_lfo_buffer) > 0:
        outputs["sf2_modulation_lfo"] = float(self._mod_lfo_buffer[-1])
    
    if self._mod_env_buffer is not None and len(self._mod_env_buffer) > 0:
        outputs["sf2_modulation_env"] = float(self._mod_env_buffer[-1])
    
    if hasattr(self, "_envelopes") and "amp_env" in self._envelopes:
        env = self._envelopes["amp_env"]
        if hasattr(env, "get_current_level"):
            outputs["sf2_amplitude_env"] = float(env.get_current_level())
    
    return outputs
```

### Phase 5: MIDI Controller Support (Week 3)

#### 5.1 Note On/Off Enhancement

```python
def note_on(self, velocity: int, note: int) -> bool:
    """Trigger note-on with full controller processing."""
    if not self._matches_note_velocity(note, velocity):
        return False
    
    if not super().note_on(velocity, note):
        return False
    
    # Reset playback position
    self._sample_position = 0.0
    self._active = True
    
    # Apply key tracking to envelopes
    self._apply_key_tracking(note)
    
    # Trigger amplitude envelope
    if "amp_env" in self._envelopes:
        self._envelopes["amp_env"].note_on(velocity, note)
    
    # Trigger modulation envelope
    self._trigger_modulation_envelope()
    
    # Reset LFO phases
    if self._mod_lfo:
        self._mod_lfo.reset()
    if self._vib_lfo:
        self._vib_lfo.reset()
    
    return True

def note_off(self) -> bool:
    """Trigger note-off with envelope release."""
    # Trigger amplitude envelope release
    if "amp_env" in self._envelopes:
        self._envelopes["amp_env"].note_off()
    
    # Trigger modulation envelope release
    self._release_modulation_envelope()
    
    self.state = RegionState.RELEASING
    return True
```

### Phase 6: Spatial Processing (Week 3)

#### 6.1 Panning and Effects Sends

```python
def _apply_spatial_processing(self, block_size: int) -> np.ndarray:
    """Apply panning and effects sends."""
    output = self._output_buffer[:block_size * 2]
    
    # Get pan from generator 34
    pan = self._get_generator_value(34, 0) / 500.0
    pan += getattr(self, "_pan_mod", 0.0)
    
    # Apply LFO pan modulation
    if self._vib_lfo_to_pan != 0.0 and self._vib_lfo_buffer is not None:
        pan += self._vib_lfo_buffer[:block_size].mean() * self._vib_lfo_to_pan
    if self._mod_lfo_to_pan != 0.0 and self._mod_lfo_buffer is not None:
        pan += self._mod_lfo_buffer[:block_size].mean() * self._mod_lfo_to_pan
    
    # Apply pan
    pan = max(-1.0, min(1.0, pan))
    
    if pan != 0.0:
        if pan < 0:  # Pan left
            left_gain = 1.0 + pan
            right_gain = 1.0
        else:  # Pan right
            left_gain = 1.0 - pan
            right_gain = 1.0
        
        output[::2] *= left_gain
        output[1::2] *= right_gain
    
    # Apply volume modulation
    if self._volume_mod != 1.0:
        output *= self._volume_mod
    
    # Store effects sends for global effects processor
    self._reverb_send = self._get_generator_value(32, 0) / 1000.0
    self._chorus_send = self._get_generator_value(33, 0) / 1000.0
    
    return output
```

### Phase 7: Complete generate_samples Rewrite (Week 3-4)

```python
def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
    """Generate samples with full SF2 modulation processing."""
    if self._sample_data is None or not self._initialized:
        if self._sample_data is None:
            loaded = self._load_sample_data()
            if loaded is None:
                return np.zeros(block_size * 2, dtype=np.float32)
        if not self._initialized:
            if not self.initialize():
                return np.zeros(block_size * 2, dtype=np.float32)
    
    output = self._output_buffer
    if output is None or len(output) < block_size * 2:
        output = np.zeros(block_size * 2, dtype=np.float32)
    
    # 1. Apply global modulation from modulation matrix
    self._apply_global_modulation(modulation)
    
    # 2. Generate LFO signals
    self._generate_lfo_signals(block_size)
    
    # 3. Generate modulation envelope
    self._mod_env_buffer = self._generate_modulation_envelope_block(block_size)
    
    # 4. Generate wavetable samples with PER-SAMPLE pitch modulation
    self._generate_samples_with_mipmap_and_modulation(output, block_size)
    
    # 5. Apply amplitude envelope
    self._apply_amplitude_envelope(output, block_size)
    
    # 6. Apply filter with modulation
    self._apply_filter_with_modulation(output, block_size)
    
    # 7. Apply tremolo and auto-pan
    self._apply_tremolo_and_pan(output, block_size)
    
    # 8. Apply final spatial processing
    self._apply_spatial_processing(output, block_size)
    
    return output[:block_size * 2].copy()
```

---

## 4. Priority Implementation Order

### Critical (Must Implement)
1. ✅ Add active state management
2. ✅ Initialize LFO objects
3. ✅ Trigger modulation envelope on note_on
4. ✅ Apply pitch modulation from LFO/env
5. ✅ Apply filter modulation from LFO/env
6. ✅ Apply global modulation dictionary

### Important (Should Implement)
7. ✅ Apply global modulation to amplitude
8. ✅ Implement panning from generator 34
9. ✅ Apply tremolo (LFO → volume)
10. ✅ Apply auto-pan (LFO → pan)
11. ✅ Apply modulation envelope release

### Nice to Have (Included in Enhanced Plan)
12. ✅ MIDI controller sensitivity (Phase 5)
13. ✅ Multiple LFO waveforms (Phase 8.1)
14. ✅ Stereo width processing (Phase 8.14)
15. ✅ VCF key tracking (Phase 8.2)
16. ✅ Filter types beyond lowpass (Phase 8.3)
17. ✅ Velocity curves (Phase 8.4)
18. ✅ Crossfade loops (Phase 8.5)
19. ✅ Pitch envelope (Phase 8.6)
20. ✅ Sample rate conversion (Phase 8.7)
21. ✅ Reverse playback (Phase 8.8)
22. ✅ Drum-specific processing (Phase 8.10)
23. ✅ Voice stealing enhancements (Phase 8.11)
24. ✅ Microtuning (Phase 8.12)
25. ✅ Insertion effects routing (Phase 8.13)

---

## 5. Testing Plan

### Unit Tests
- Test envelope stage progression
- Test LFO phase accumulation
- Test pitch modulation calculation

### Integration Tests
- Test note_on triggers correct envelope stages
- Test modulation matrix integration
- Test panning with stereo output

### Golden Tests
- Compare output with reference SF2 player
- Test with various SoundFont presets

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Performance impact of per-sample processing | Use vectorized numpy operations |
| Buffer memory overhead | Reuse existing buffers where possible |
| LFO/Envelope timing accuracy | Use sample-accurate accumulator |
| Backward compatibility | Add feature flags |

---

## 7. Files to Modify

1. `synth/partial/sf2_region.py` - Main implementation
2. `synth/engine/sf2_engine.py` - May need updates to pass modulation
3. `tests/sf2/test_modulation.py` - New test file

## 8. Additional Advanced Features

### 8.1 Multiple LFO Waveforms

SF2 spec supports multiple LFO waveforms beyond sine:

| Waveform | SF2 ID | Description |
|----------|--------|-------------|
| Sine | 0 | Smooth modulation |
| Triangle | 1 | Softer harmonics |
| Square | 2 | On/off effect |
| Sawtooth | 3 | Brighter harmonics |
| Sample & Hold | 4 | Random stepped modulation |

```python
# SF2 Generator 43: lfoWaveform
# 0=sine, 1=triangle, 2=square, 3=sawtooth, 4=sampleHold

WAVEFORM_MAP = {
    0: "sine",
    1: "triangle", 
    2: "square",
    3: "sawtooth",
    4: "sample_hold",
}

def _init_lfo_waveform(self) -> None:
    """Initialize LFO with SF2 waveform."""
    waveform_gen = self._get_generator_value(43, 0)
    waveform = WAVEFORM_MAP.get(waveform_gen, "sine")
    
    if self._mod_lfo:
        self._mod_lfo.set_parameters(waveform=waveform)
    if self._vib_lfo:
        self._vib_lfo.set_parameters(waveform=waveform)
```

### 8.2 VCF Key Tracking

Filter cutoff follows keyboard pitch:

| Generator | Name | Range |
|-----------|------|-------|
| 31 | vcfKeyTrack | -1200 to +1200 cents |

```python
def _apply_vcf_key_tracking(self, note: int) -> None:
    """Apply VCF key tracking."""
    key_track = self._get_generator_value(31, 0)  # cents
    note_offset = note - 60  # relative to middle C
    cutoff_offset = key_track * note_offset / 100.0  # convert to semitones
    
    self._filter_key_track_mod = cutoff_offset
```

### 8.3 Additional Filter Types

SF2 supports multiple filter types beyond lowpass:

| Type | SF2 Value | Description |
|------|-----------|-------------|
| Lowpass | 0 | Default |
| Highpass | 1 | Removes low frequencies |
| Bandpass | 2 | Removes highs and lows |
| Notch | 3 | Removes middle frequencies |
| Peaking EQ | 4 | Boosts/cuts middle |

```python
FILTER_TYPE_MAP = {
    0: "lowpass",
    1: "highpass", 
    2: "bandpass",
    3: "notch",
    4: "peaking",
}

def _init_filter_type(self) -> None:
    """Initialize filter with SF2 type."""
    filter_type_gen = self._get_generator_value(36, 0)  # filterType
    filter_type = FILTER_TYPE_MAP.get(filter_type_gen, "lowpass")
    
    if "filter" in self._filters:
        self._filters["filter"].set_parameters(filter_type=filter_type)
```

### 8.4 Velocity Curves

Custom velocity response beyond linear 0-127:

```python
# SF2 Generator 41: velCurve
# 0=linear, 1=exponential, 2=squared, 3=sqrt, 4=step

VELOCITY_CURVES = {
    0: lambda v: v / 127.0,                           # Linear
    1: lambda v: (v / 127.0) ** 2,                    # Exponential  
    2: lambda v: (v / 127.0) ** 0.5,                  # Square root
    3: lambda v: 1.0 if v > 64 else 0.0,              # Step
}

def _apply_velocity_curve(self, velocity: int) -> float:
    """Apply SF2 velocity curve."""
    curve_type = self._get_generator_value(41, 0)
    curve_func = VELOCITY_CURVES.get(curve_type, VELOCITY_CURVES[0])
    return curve_func(velocity)
```

### 8.5 Crossfade Loops

Smooth loop transitions to prevent clicking:

```python
# SF2 Generator 45: loopCrossfade
# 0-32768 samples for crossfade

def _handle_loop_with_crossfade(self, position: float, loop_start: int, 
                                loop_end: int, crossfade_len: int) -> float:
    """Handle loop with crossfade for smooth transitions."""
    if position >= loop_end - crossfade_len:
        # In crossfade zone - apply envelope
        fade_position = (loop_end - position) / crossfade_len
        # Crossfade envelope (smooth in/out)
        crossfade_gain = 0.5 * (1.0 + np.cos(np.pi * fade_position))
        self._loop_crossfade_gain = crossfade_gain
    
    if position >= loop_end:
        # Wrap to loop start
        excess = position - loop_end
        position = loop_start + excess
    
    return position
```

### 8.6 Pitch Envelope

Dedicated pitch envelope (separate from modulation envelope):

| Generator | Name | Description |
|-----------|------|-------------|
| 54 | pitchEnvDelay | Pitch env delay |
| 55 | pitchEnvAttack | Pitch env attack |
| 56 | pitchEnvHold | Pitch env hold |
| 57 | pitchEnvDecay | Pitch env decay |
| 58 | pitchEnvSustain | Pitch env sustain level |
| 59 | pitchEnvRelease | Pitch env release |

```python
def _init_pitch_envelope(self) -> None:
    """Initialize pitch envelope (separate from mod envelope)."""
    self._pitch_env_delay = self._timecents_to_seconds(
        self._get_generator_value(54, -12000)
    )
    self._pitch_env_attack = self._timecents_to_seconds(
        self._get_generator_value(55, -12000)
    )
    self._pitch_env_decay = self._timecents_to_seconds(
        self._get_generator_value(57, -12000)
    )
    self._pitch_env_sustain = self._get_generator_value(58, 0) / 100.0
    self._pitch_env_release = self._timecents_to_seconds(
        self._get_generator_value(59, -12000)
    )
    
    # Pitch env depth (gen 52)
    self._pitch_env_depth = self._get_generator_value(52, 0) / 100.0
```

### 8.7 High-Quality Sample Rate Conversion

Better resampling for non-native sample rates:

```python
class HighQualityResampler:
    """Multi-stage resampling for best quality."""
    
    def __init__(self, source_rate: int, target_rate: int):
        self.source_rate = source_rate
        self.target_rate = target_rate
        
        # Calculate resampling ratio
        if target_rate > source_rate:
            # Upsample first, then decimate
            self.up_ratio = target_rate // source_rate
            self.down_ratio = 1
        else:
            # Decimate directly
            self.up_ratio = 1
            self.down_ratio = source_rate // target_rate
    
    def resample(self, samples: np.ndarray) -> np.ndarray:
        """Apply high-quality resampling."""
        if self.up_ratio > 1:
            # Linear interpolation for upsampling
            samples = self._interpolate(samples, self.up_ratio)
        
        if self.down_ratio > 1:
            # Apply lowpass filter before decimation
            samples = self._lowpass_filter(samples)
            samples = samples[::self.down_ratio]
        
        return samples
```

### 8.8 Reverse Sample Playback

Play samples in reverse direction:

```python
# SF2 Generator 57: samplePlaybackMode
# 0=normal, 1=reverse

def _generate_samples_reverse(self, output: np.ndarray, block_size: int) -> None:
    """Generate samples in reverse playback."""
    reverse_mode = self._get_generator_value(57, 0)
    
    if reverse_mode == 1:  # Reverse
        for i in range(block_size):
            pos = self._sample_position
            pos_int = int(pos)
            frac = pos - pos_int
            
            # Interpolate backwards
            s1 = self._sample_data[pos_int]
            s2 = self._sample_data[min(pos_int + 1, len(self._sample_data) - 1)]
            output[i] = s1 + frac * (s2 - s1)
            
            # Move backwards
            self._sample_position -= self._phase_step
            self._handle_sf2_looping(self._sample_position, len(self._sample_data))
```

### 8.10 Drum/One-Shot Processing

One-shot samples for drums don't use release envelope:

```python
def _init_drum_mode(self) -> None:
    """Initialize drum/one-shot mode."""
    # Gen 57: sampleModes
    # 0=mono, 1=mono+right, 2=mono+left, 3=mono+both, 4=loop, 5=?
    sample_mode = self._get_generator_value(51, 0)
    
    # One-shot mode (no looping, plays through)
    self._is_drum_mode = sample_mode in [0, 1, 2, 3]
    
    if self._is_drum_mode:
        # Don't use release envelope for drums
        if "amp_env" in self._envelopes:
            self._envelopes["amp_env"].set_parameters(release=0.0)
```

### 8.11 Voice Stealing Enhancements

Better handling of polyphony:

```python
def _calculate_voice_priority(self, note: int, velocity: int, 
                                note_age: float) -> float:
    """Calculate voice priority for stealing."""
    # Lower priority = first to steal
    
    # Prefer lower velocity (quieter notes steal first)
    velocity_factor = (127 - velocity) / 127.0 * 0.3
    
    # Prefer older notes
    age_factor = note_age / 10.0  # normalize to 0-1 range
    
    # Prefer lower notes
    note_factor = (127 - note) / 127.0 * 0.2
    
    return velocity_factor + age_factor + note_factor
```

### 8.12 Microtuning Support

Alternative tuning systems:

```python
# SF2 Generator 58: overridingRootKey (can be used for microtuning)
# Gen 59: tuning (custom extension)

def _apply_microtuning(self, note: int) -> float:
    """Apply microtuning offset."""
    # Get microtuning from generator or use default
    microtuning = self._get_generator_value(59, 0)  # cents offset
    
    # Apply to base pitch
    base_pitch = note * 100.0  # in cents
    tuned_pitch = base_pitch + microtuning
    
    # Convert back to ratio
    return 2.0 ** (tuned_pitch / 1200.0)
```

### 8.13 Insertion Effects Routing

Route SF2 output through insertion effects:

```python
def _route_to_insertion_effects(self, block_size: int) -> np.ndarray:
    """Route audio through insertion effects."""
    output = self._output_buffer[:block_size * 2]
    
    # Check for insertion effect routing
    insertion_effect = self._get_generator_value(46, 0)  # custom
    
    if insertion_effect > 0:
        # Route to insertion effect bus
        # This would connect to the global effects chain
        self._insertion_bus = getattr(self, "_insertion_bus", None)
        if self._insertion_bus is not None:
            self._insertion_bus.write(output)
    
    return output
```

### 8.14 Stereo Width Processing

Control stereo width beyond simple panning:

```python
# Generator 45: stereoMode (extension)
# Generator 46: width (extension)

def _apply_stereo_width(self, output: np.ndarray, block_size: int) -> None:
    """Apply stereo width processing."""
    width = self._get_generator_value(46, 100)  # 100 = normal width
    
    if width != 100:
        width_factor = width / 100.0
        
        for i in range(block_size):
            left = output[i * 2]
            right = output[i * 2 + 1]
            
            # Mid/Side processing
            mid = (left + right) * 0.5
            side = (left - right) * 0.5 * width_factor
            
            # Back to stereo
            output[i * 2] = mid + side
            output[i * 2 + 1] = mid - side
```

---

## 9. Enhanced Implementation Phases

| Phase | Features | Duration |
|-------|----------|----------|
| Phase 1-7 | Core migration (SF2Partial → SF2Region) | Weeks 1-4 |
| **Phase 8** | **Advanced Features** | **Weeks 4-8** |
| 8.1 | Multiple LFO waveforms | Week 4 |
| 8.2 | VCF key tracking | Week 4 |
| 8.3 | Additional filter types | Week 5 |
| 8.4 | Velocity curves | Week 5 |
| 8.5 | Crossfade loops | Week 5 |
| 8.6 | Pitch envelope | Week 6 |
| 8.7 | Sample rate conversion | Week 6 |
| 8.8 | Reverse playback | Week 6 |
| 8.10 | Drum processing | Week 7 |
| 8.11 | Voice stealing | Week 7 |
| 8.12 | Microtuning | Week 7 |
| 8.13 | Insertion effects | Week 8 |
| 8.14 | Stereo width | Week 8 |

---

## 10. Updated Success Criteria

- [ ] All 60+ SF2 generators processed
- [ ] Sample-accurate envelope timing
- [ ] Per-sample LFO modulation applied
- [ ] Modulation matrix input/output functional
- [ ] MIDI controllers affect sound
- [ ] Panning and effects sends work
- [ ] **Multiple LFO waveforms supported**
- [ ] **VCF key tracking functional**
- [ ] **All filter types implemented**
- [ ] **Velocity curves working**
- [ ] **Smooth loop crossfades**
- [ ] **Pitch envelope processing**
- [ ] **High-quality resampling**
- [ ] **Reverse playback**
- [ ] **Drum/one-shot mode**
- [ ] **Microtuning support**
- [ ] **Stereo width processing**
- [ ] No regression in existing functionality
