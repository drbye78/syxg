# Behavioral Synthesis Engine — Comprehensive Implementation Strategy

> Based on: `report_sna0.md` (critical audit), `report_sna2.md` (architecture roadmap), independent codebase analysis.
> Principle: Start small, validate end-to-end, then scale.
> No backward compatibility constraints. Architecture refactoring permitted.

## 1. What This Is (And Isn't)

**This is:** A hybrid PCM+model synthesis engine that extracts acoustic properties from SF2 samples at load time, plays PCM attack transients, then crossfades to physically-inspired modal resonators for infinitely variable sustain and release.

**This is NOT:** Roland SuperNATURAL. The rebrand from "SuperNATURAL-Acoustic alike" to "Behavioral Synthesis Engine" is non-negotiable.

## 2. Architecture

### 2.1 Current → Target

```
CURRENT (post-processing)                      TARGET (hybrid PCM+model)
─────────────────────────                      ──────────────────────────
SF2Region generates full sample                BehavioralVoice
  ↓                                                 ├── AttackRegion (PCM SF2, first 50-200ms)
AcousticBehaviorRegion (wrapper)                     ├── Crossfader (PCM→Model, 10-30ms)
  ├── velocity_timbre (1-pole LP)                    ├── ModalResonator (sustain phase)
  ├── sympathetic_resonance (modal bank)             ├── ExcitationModel (bow/breath/hammer/pluck)
  ├── performance_noise (white noise)                ├── BodyRadiationFilter (per-instrument)
  ├── damper_resonance (exp decay)                   ├── DamperModel (pedal-dependent)
  ├── ensemble_detune (linear pitch shift)           └── SympatheticResonanceBank (note-aware coupling)
  └── keyoff_noise (white noise burst)           ↓
                                              EffectsCoordinator (unchanged)
```

### 2.2 Key Design Decisions

**Decision 1: Build on SynthesisEngine, not alongside it.**
The behavioral engine extends `SynthesisEngine`. SF2 loading, preset management, engine registration, and voice lifecycle are reused unchanged.

**Decision 2: Start with one instrument, validate, then scale.**
Phase 1 targets **BOWED_STRINGS** (violin) only — 10-20 modal frequencies, a single excitation model (bow). Once validated end-to-end (attack→crossfade→sustain→release), scale to 18 instrument groups.

**Decision 3: Rename the existing acoustic layer.**
`synth/engines/acoustic/` → `synth/engines/behavioral/`. The existing 9 processors become **fallback processors** for instrument groups where full behavioral modeling is not yet implemented. They are not wasted — they provide a functional baseline while the hybrid pipeline is progressively rolled out.

**Decision 4: Sample segmentation runs at load time, not note-on time.**
When an SF2 is loaded, the sustain portion of each sample is analyzed to extract modal parameters. These are stored in a `BehavioralSampleCache` alongside the raw PCM data. At note-on time, the behavioral voice reads pre-computed modal parameters — no analysis on the audio thread.

**Decision 5: De-risk the riskiest component first.**
Sample auto-segmentation is the most uncertain component. Before building any synthesis infrastructure, validate that attack/sustain/release boundaries can be reliably detected without human annotation. If they cannot, fall back to a simpler scheme: fixed-duration attack (first 100ms of every sample as attack region) with configurable per-instrument thresholds.

## 3. Implementation Phases

### Phase 0 — Rebrand & Rename (0.5 hours)

Rename "SuperNATURAL" → "Behavioral Synthesis" across all documentation and code.

**Files to modify:**
- `synth/engines/acoustic/__init__.py` — module docstring
- `synth/engines/acoustic/acoustic_behavior_region.py` — class docstring and pipeline comments
- `synth/engines/acoustic/engine.py` — feature descriptor
- `synth/engines/acoustic/behavior_config.py` — docstring
- `synth/engines/acoustic/channel_context.py` — docstring
- `synth/engines/acoustic/processors/sympathetic_resonance.py` — docstring
- `synth/engines/acoustic/processors/velocity_timbre.py` — docstring
- `vibexg/cli.py` — CLI help text
- `README.md` — feature tables

**New terminology:**
- "SuperNATURAL-Acoustic alike" → "Behavioral Synthesis Engine"
- "SN-A" → "Hybrid PCM+Model"
- "Acoustic behavior layer" → "Behavioral synthesis layer"

### Phase 1 — Sample Segmentation & Modal Analysis (De-Risk, 3 hours)

**Goal:** Validate that SF2 samples can be automatically segmented into attack/sustain/release regions and that modal parameters can be extracted from the sustain portion.

**New file:** `synth/engines/behavioral/sample_analyzer.py`

```python
class SampleSegmenter:
    """Detect attack/sustain/release boundaries in sample data."""
    
    def segment(self, sample: np.ndarray, sr: int) -> SampleSegments:
        """Return attack, sustain, release boundaries.
        
        Uses RMS energy envelope + threshold detection.
        Falls back to fixed-duration segmentation if detection fails.
        """
    
class ModalAnalyzer:
    """Extract modal parameters from sustain portion of sample."""
    
    def analyze(self, sustain: np.ndarray, sr: int) -> list[ModalParameter]:
        """Extract frequency, amplitude, decay rate for each mode.
        
        Uses FFT peak detection + sinusoidal modeling.
        """
```

**Validation criteria:**
- For 10 diverse SF2 samples (piano, violin, flute, trumpet, guitar), verify:
  1. Attack region contains the initial transient (visually inspect waveform)
  2. Sustain region is quasi-periodic (zero-crossing rate stable)
  3. Modal analysis produces at least 5 identifiable frequency peaks
  4. Fallback segmentation (first 100ms = attack) produces acceptable results when auto-detection fails

**If validation fails:** Use fixed-duration segmentation. The hybrid engine is still viable — the attack sample just has a fixed rather than adaptive length.

**Effort:** 3 hours.

### Phase 2 — Behavioral Voice Infrastructure (4 hours)

**Goal:** Build the `BehavioralVoice` class that orchestrates the PCM→Model transition.

**New file:** `synth/engines/behavioral/behavioral_voice.py`

**Architecture:**

```
BehavioralVoice (extends IRegion)
├── _attack_region: SF2Region     (PCM attack sample)
├── _modal_resonator: ModalResonator (physical model sustain)
├── _crossfader: Crossfader       (PCM→Model transition)
├── _excitation: ExcitationModel  (bow/breath/hammer/pluck)
└── _damper: DamperModel          (pedal-dependent damping)

note_on(velocity, note):
    _attack_region.note_on(velocity, note)  # Start PCM playback
    _crossfader.start_transition()          # Begin 30ms crossfade timer
    _excitation.trigger(velocity, note)     # Start model excitation
    _phase = ATTACK

generate_samples(block_size):
    if _phase == ATTACK:
        pcm = _attack_region.generate_samples(block_size)
        if _crossfader.is_complete():
            _phase = SUSTAIN
            return _modal_resonator.render(block_size, _excitation)
        return _crossfader.mix(pcm, _modal_resonator.render(block_size, _excitation))
    elif _phase == SUSTAIN:
        return _modal_resonator.render(block_size, _excitation)
    elif _phase == RELEASE:
        return _modal_resonator.render_release(block_size, _damper)
```

**Effort:** 4 hours.

### Phase 3 — Modal Resonator + Excitation Model (6 hours)

**Goal:** Implement the core physical modeling components for the first instrument (violin/bowed strings).

**Bowed String Excitation Model:**

```python
class BowedStringExcitation:
    """Bow-string interaction model using friction characteristic."""
    
    def __init__(self, sample_rate: int):
        self.bow_pressure = 0.5     # 0-1 (normalized bow force)
        self.bow_velocity = 0.3     # 0-1 (bow speed)
        self.bow_position = 0.5     # 0-1 (fraction of string length)
    
    def compute_excitation(self, note: int, velocity: int) -> np.ndarray:
        """Compute excitation signal for one block.
        
        Bow pressure controls harmonic richness.
        Bow velocity controls amplitude.
        Bow position controls harmonic balance (sul tasto ↔ sul ponticello).
        """
```

**Modal Resonator:**

```python
class ModalResonator:
    """Parallel bank of damped harmonic oscillators.
    
    Each mode: f_n = n * f0 * sqrt(1 + B * n^2)  (inharmonic string)
               decay_n = decay_rate * f_n^2        (high frequencies decay faster)
    """
    
    def __init__(self, modes: list[ModalParameter], sample_rate: int):
        # 10-20 modes for a bowed string
        self._modes = modes
    
    def render(self, block_size: int, excitation: ExcitationModel) -> np.ndarray:
        """Render one block of modal synthesis output."""
        out = np.zeros((block_size, 2), dtype=np.float32)
        for mode in self._modes:
            # Damped harmonic oscillator
            # x'' + 2*decay*x' + w^2*x = excitation
            # Discretized as: state += excitation - decay*velocity - w^2*position
            ...
        return out
```

**Effort:** 6 hours.

### Phase 4 — Integration (5 hours)

**Goal:** Wire BehavioralVoice into the synthesis pipeline.

**Steps:**
1. Create `BehavioralSynthesisEngine(SynthesisEngine)` — overrides `_create_base_region()` to return `BehavioralVoice` when instrument group has behavioral model
2. Register in `EngineRegistry` with priority 10 (above SF2)
3. `ChannelAcousticContext` → `ChannelBehavioralContext`:
   - Add `GestureState` (pre-existing: our auto-detection already tracks legato/interval/velocity/duration)
   - Wire sympathetic resonance to undamped held notes only (note-aware coupling)
4. Route through `EffectsCoordinator` unchanged
5. Add behavioral NRPN parameters to `XGChannelParameterManager` (per sna2 §5.1):

**Behavioral NRPN Parameter Map (MSB 17 — previously reserved):**

| NRPN MSB | NRPN LSB | Parameter | Range | Default | Description |
|---|---|---|---|---|---|
| **17** | 0 | `behavioral_excitation_pressure` | 0–127 | 64 | Bow pressure / breath intensity / hammer force |
| **17** | 1 | `behavioral_excitation_position` | 0–127 | 64 | Bow position / embouchure / pluck point (sul tasto ↔ sul ponticello) |
| **17** | 2 | `behavioral_vibrato_rate` | 0–127 | 64 | Behavioral vibrato rate (modulates excitation, not LFO) |
| **17** | 3 | `behavioral_vibrato_depth` | 0–127 | 0 | Behavioral vibrato depth |
| **17** | 4 | `behavioral_portamento_time` | 0–127 | 0 | Behavioral glide time (model-level pitch interpolation) |
| **17** | 5 | `behavioral_brightness` | 0–127 | 64 | Harmonic content / spectral tilt |
| **17** | 6 | `behavioral_damper_position` | 0–127 | 0 | Continuous damper/pedal position (0=fully damped, 127=fully open) |
| **17** | 7 | `behavioral_sympathetic_resonance` | 0–127 | 64 | Sympathetic resonance intensity |
| **17** | 8 | `behavioral_body_resonance` | 0–127 | 64 | Instrument body radiation level |
| **17** | 9 | `behavioral_attack_length` | 0–127 | 64 | PCM→Model crossfade duration (0=immediate model, 127=longest PCM) |
| **17** | 10 | `behavioral_noise_level` | 0–127 | 32 | Mechanical/breath noise intensity |
| **17** | 11 | `behavioral_ensemble_width` | 0–127 | 0 | Section spread (0=solo, 127=full section) |

**XGControllerAssignments mapping (pre-existing MSB 15-16):**

These behavioral parameters are map targets for the existing 12 controller assignment slots:
- Slot 0 default: CC1 (mod wheel) → `behavioral_excitation_pressure`
- Slot 1 default: CC2 (breath) → `behavioral_excitation_pressure` (wind instruments)
- Slot 2 default: CC4 (foot) → `behavioral_damper_position`
- Slot 3 default: CC11 (expression) → `behavioral_brightness`
- Slot 4 default: CC71 (harmonic content) → `behavioral_vibrato_depth`
- Slot 5 default: CC74 (brightness) → `behavioral_brightness`

This reuses the existing controller assignment infrastructure (12 slots, 6 curves, range scaling) without modification.

6. Validation: end-to-end test — SF2 violin sample → BehavioralVoice → modal sustain → EffectsCoordinator → audible output

**Effort:** 5 hours.

### Phase 5 — Scale to Instrument Groups (8 hours)

**Goal:** Expand from violin (1 group) to all 18 instrument groups with excitation models.

**Per-group excitation types:**

| Group | Excitation | Modes | Complexity |
|---|---|---|---|
| BOWED_STRINGS | Bow friction | 10-20 | Reference implementation (Phase 3) |
| ACOUSTIC_PIANO | Hammer strike | 50-200 per note (3 strings × 66 partials) | Highest — note-aware sympathetic + damper |
| ACOUSTIC_GUITAR | Pluck/strum | 10-30 | Similar to bowed but plucked excitation |
| BRASS | Lip buzz | 10-20 | Bore standing wave model |
| REEDS_WOODWINDS | Reed vibration | 10-20 | Similar to brass with reed nonlinearity |
| FLUTE (treated as REEDS_WOODWINDS) | Air jet | 10-15 | Edge tone excitation |
| ACOUSTIC_BASS | Pluck/finger | 8-15 | Similar to guitar, lower frequencies |
| ORGAN | Continuous tone | 5-15 (harmonic drawbar) | Sustained excitation, no decay |
| CHOIR | Glottal pulse | 5-8 (vocal formants) | Formant filter bank |
| *Remaining 9 groups* | Fallback to existing acoustic processors | N/A | Existing DSP as safety net |

**Scaling strategy:** Implement in order of decreasing instrument popularity (bowed strings → piano → guitar → brass → woodwinds). Groups without excitation models fall back to the existing acoustic processors (Phase 0 rename preserved them as fallback).

**Effort:** 8 hours.

### Phase 6 — Quality Improvements (4 hours)

**Improvements identified in the audit:**
1. **Ensemble detune aliasing fix:** Replace linear interpolation with cubic (reuse `PitchModProcessor._resample` from S.Art2)
2. **Colored performance noise:** Replace `np.random.uniform` with pink noise (1/f spectrum) for mechanical noise
3. **Note-aware sympathetic resonance:** Only resonate undamped strings matching held note harmonics (not all modes for all held notes)
4. **Continuous damper model:** Replace binary sustain pedal with pedal position (0-127)

**Effort:** 4 hours.

## 4. Original Design Insights (Not from Audit Reports)

These are architectural observations derived from deeply analyzing the entire codebase across all our remediation work — patterns that apply specifically to building a mature behavioral engine.

### 4.1 Phase-Lock the PCM→Model Crossfade or It Won't Work

The naïve approach — play PCM attack, start model oscillator, crossfade linearly — will produce comb filtering at every transition because the model's initial phase will be random relative to the PCM signal's phase at the crossfade start.

**Solution: Phase-lock the model to the PCM signal.** At the crossfade boundary (t=0), read the PCM signal's phase for each modal frequency via short-time FFT. Initialize each modal oscillator with that phase so the first model sample is phase-continuous with the last PCM sample.

```python
def start_crossfade(self, pcm_buffer: np.ndarray):
    """Phase-lock model oscillators to PCM signal at crossfade boundary."""
    window = pcm_buffer[-512:]  # Last 512 samples of PCM attack
    spectrum = np.fft.rfft(window * np.hanning(512))
    for mode in self._modes:
        # Find the nearest FFT bin to this modal frequency
        bin_idx = int(mode.frequency * 512 / self.sample_rate)
        if bin_idx < len(spectrum):
            phase = np.angle(spectrum[bin_idx])
            mode.set_phase(phase)  # Initialize oscillator phase
```

This is the single highest-impact implementation detail. Without it, every PCM→Model transition will have an audible "click" or "swirl." With it, the transition is seamless. This technique is not mentioned in either audit report but is standard practice in hybrid synthesizers (Korg MOSS, Yamaha VL, Roland V-Synth).

### 4.2 Modal Parameters Must Be Note-Indexed, Not Sample-Indexed

The sample analyzer extracts modal parameters from the sustain portion of a single sample. But C4 on violin has different modes than C6 — the body resonance shifts with pitch, and the string length changes. A single modal profile per sample is wrong for polyphonic instruments.

**Solution: Extract per-note modal parameters during SF2 loading.** When loading a soundfont, analyze every unique sample's sustain region. Store modal parameters indexed by MIDI note number in a `NoteModalCache`:

```python
class NoteModalCache:
    """Modal parameters indexed by MIDI note number."""
    _cache: dict[int, list[ModalParameter]] = {}  # note → [mode1, mode2, ...]
    
    def __init__(self, sample_data: dict[int, np.ndarray], sr: int):
        for note, samples in sample_data.items():
            modes = ModalAnalyzer().analyze(samples[0].sustain, sr)
            self._cache[note] = modes
    
    def get_modes(self, note: int) -> list[ModalParameter]:
        """Return pre-computed modal params for this note. Interpolate between nearest cached notes."""
        if note in self._cache:
            return self._cache[note]
        # Interpolate between nearest cached notes
        nearest_below = max(k for k in self._cache if k <= note)
        nearest_above = min(k for k in self._cache if k >= note)
        return self._interpolate_modes(nearest_below, nearest_above, note)
```

This is architecturally similar to SF2's existing velocity-layer system — we already have note-range-to-sample mapping in `RegionDescriptor`. The modal cache extends it with note-range-to-modal-profile mapping.

### 4.3 The Existing Auto-Detection IS Gesture Detection

`report_sna0.md` claims "No behavioral gesture detection" exists. This is **stale** — our S.Art2 auto-detection engine (`synth/engines/auto_detect/engine.py`) already detects:

- **Legato** (note overlap → `attack_skip`) — directly reusable for behavioral synthesis: legato notes use a different excitation envelope (no re-attack)
- **Interval glissando** (octave+ → glissando articulation) — behavioral equivalent: engage portamento model
- **Velocity switching** (velocity → articulation mapping) — behavioral equivalent: velocity → excitation intensity + attack length
- **Duration-based release** (held <80ms → staccato release) — behavioral equivalent: short notes skip sustain, go PCM attack → immediate release

**What's missing:** Wire these existing detections to behavioral voice parameters. The detection infrastructure is built; the behavioral engine just needs to consume it.

```python
# In BehavioralVoice.note_on():
detection = self.auto_detect.on_note_on(note, velocity, group, held_notes, preset)
if detection.attack_skip:
    self._attack_length = 0  # Skip PCM attack, go directly to model
if detection.articulation == "glissando":
    self._excitation.engage_portamento(detection.glissando_interval)
```

### 4.4 The Damper Model Is the Architectural Linchpin

The existing `damper_resonance.py` (36 lines, exponential decay impulse) is the weakest processor in the current acoustic layer. The behavioral damper model is the most architecturally significant upgrade because it connects three subsystems:

1. **Voice lifecycle:** When a voice transitions to RELEASE, the damper model computes per-frequency damping coefficients based on pedal position and note duration
2. **Sympathetic resonance:** Undamped strings (pedal up, note held) continue to resonate — but only at frequencies matching held notes. The damper model determines which modes are "undamped"
3. **Cross-note coupling:** When one voice releases while others sustain, the damper model feeds the releasing voice's residual energy into the sympathetic resonance bank

```python
class ContinuousDamperModel:
    """Models frequency-dependent string damping based on pedal position."""
    
    def __init__(self, sample_rate: int):
        self.pedal_position = 0.0  # 0.0 (fully damped) to 1.0 (fully open)
    
    def get_damping_coefficient(self, frequency: float, is_held: bool) -> float:
        """Return damping coefficient for a specific frequency.
        
        - Pedal fully down (0.0): all frequencies damp quickly → short release
        - Pedal half (0.5): low frequencies damp slowly, high frequencies damp fast
        - Pedal fully up (1.0): no damping on held notes → infinite sustain
        - Is_held=True: no damping regardless of pedal (player's finger on key)
        """
        if is_held:
            return 0.0  # Undamped — finger is holding the note
        base_damping = 1.0 - self.pedal_position  # 1.0→0.0 as pedal goes up
        # High frequencies damp faster (string inharmonicity + air resistance)
        freq_factor = min(1.0, frequency / 8000.0)
        return base_damping * (0.3 + 0.7 * freq_factor)
```

### 4.5 The 18 "Instrument Groups" Are Too Coarse for Modal Profiles

The current `InstrumentGroup` enum has 18 entries. For parameter configuration DSP, this is fine. For modal resonance, it's insufficient. A violin (body resonance ~200-500Hz primary modes) and a cello (body resonance ~100-300Hz) are both `BOWED_STRINGS` but have fundamentally different body radiation characteristics.

**Solution: Add `InstrumentSubCategory` that maps to modal profiles.**

```python
@dataclass
class InstrumentModalProfile:
    group: InstrumentGroup
    sub_category: str          # "violin", "cello", "trumpet", "flute", etc.
    body_modes: list[float]    # Primary body resonance frequencies (Hz)
    body_q: list[float]        # Q factors per mode
    radiation_pattern: str     # "dipole" (strings), "monopole" (brass), "plane" (flute)
    excitation_type: str       # "bow", "breath", "hammer", "pluck", "strike"
    num_strings: int           # For sympathetic resonance coupling (1=mono, 3=piano)

# Map SF2 program numbers to sub-categories
PROGRAM_TO_PROFILE: dict[int, InstrumentModalProfile] = {
    40: InstrumentModalProfile(..., sub_category="violin", ...),
    42: InstrumentModalProfile(..., sub_category="cello", ...),
    # ... 
}
```

Extract `program_to_group()` from the existing `behavior_config.py` and expand it to `program_to_profile()`. This is data, not code — ~18 entries per group, ~300 total.

### 4.6 The Reuse Architecture Avoids the "Two-Pipeline" Problem

Throughout our remediation work, we found the same anti-pattern: two subsystems doing the same thing with different code paths (SF2SampleModifier vs acoustic processors, XG SysEx router vs channel parameters). The behavioral engine must avoid this.

**The rule: behavioral voices and PCM voices share the same pipeline.** The `EffectsCoordinator` doesn't know whether a buffer came from PCM or behavioral synthesis. The `VoiceManager` steals voices the same way regardless. The `BufferPool` allocates buffers identically. The only difference is inside `BehavioralVoice.generate_samples()` — everything downstream is identical.

This means `BehavioralSynthesisEngine` overrides exactly one method (`_create_base_region()`) and inherits everything else from `SynthesisEngine`. This is the lesson from our S.Art2 refactoring: extend, don't duplicate.



### New files (7)

```
synth/engines/behavioral/sample_analyzer.py      — P1: SampleSegmenter + ModalAnalyzer
synth/engines/behavioral/behavioral_voice.py      — P2: Hybrid PCM+Model voice
synth/engines/behavioral/modal_resonator.py       — P3: Modal resonator bank
synth/engines/behavioral/excitation.py            — P3: Excitation models per instrument
synth/engines/behavioral/crossfader.py            — P2: PCM→Model crossfade
synth/engines/behavioral/damper_model.py          — P4: Pedal-dependent damping
synth/engines/behavioral/body_radiation.py        — P3: Per-instrument radiation filter
```

### Renamed directory

```
synth/engines/acoustic/ → synth/engines/behavioral/
```

### Modified files (8)

```
synth/engines/behavioral/engine.py               — Feature descriptor, rename
synth/engines/behavioral/behavior_config.py       — Expand InstrumentBehaviorProfile
synth/engines/behavioral/channel_context.py       — Add GestureState
synth/engines/behavioral/acoustic_behavior_region.py — Rename class, update pipeline
synth/engines/synthesis_engine.py                 — Register behavioral engine
synth/engines/engine_registry.py                  — Add "behavioral" engine entry
synth/protocols/xg/xg_channel_parameter_manager.py — Add behavioral NRPN parameters
README.md                                        — Update claims, remove "SuperNATURAL"
```

### Deleted files (0)

The existing acoustic processors are preserved as fallbacks — not deleted.

## 5. Effort Estimate

| Phase | Hours | Risk |
|---|---|---|
| P0 — Rebrand & rename | 0.5 | Low |
| P1 — Sample segmentation (de-risk) | 3 | High — auto-segmentation is uncertain |
| P2 — Behavioral voice infrastructure | 4 | Medium |
| P3 — Modal resonator + excitation | 6 | Medium |
| P4 — Integration (incl. NRPN mapping) | 6 | Medium |
| P5 — Scale to instrument groups | 8 | Medium |
| P6 — Quality improvements | 4 | Low |
| **Total** | **31.5** | |

## 6. What This Strategy Does NOT Do

- **Does not claim SuperNATURAL compatibility** — the rebrand eliminates that claim entirely.
- **Does not model all 88 piano notes with 200+ modes each** — piano modeling is scoped to Phase 5 with the understanding that full implementation is a separate project.
- **Does not implement SN-S (synth) or SN-D (drums)** — acoustic instruments only.
- **Does not replace the S.Art2 articulation system** — behavioral synthesis operates at the voice level; articulations remain at the engine level.
- **Does not delete the existing acoustic processors** — they become fallback processors for unmodeled instrument groups.
