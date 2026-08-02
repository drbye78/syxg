# Behavioral Synthesis Engine — Overview

**Package:** `synth/engines/acoustic/` (3,400+ lines)  
**Status:** Production-grade hybrid PCM+Model synthesis covering 18 instrument groups

## Architecture

The Behavioral Synthesis Engine extends sample-based playback (SF2/SFZ) with physically-inspired modal resonance and waveguide synthesis for infinitely variable sustain and release.

### Hybrid Voice Pipeline

```
BehavioralVoice
├── Phase 1: ATTACK — PCM burst from SF2 sample (50-200ms)
│     └── VelocityLayerSelector crossfades between velocity layers
├── Phase 2: CROSSFADE — PCM→Model transition (30ms)
│     ├── Phase-locked: model oscillators initialized from PCM FFT
│     └── Energy-matched: model onset scaled to PCM tail energy
├── Phase 3: SUSTAIN — physically-inspired synthesis
│     ├── Modal resonator (damped harmonic oscillator bank)
│     ├── Spectral sustain (attack spectrum filtering, universal fallback)
│     └── 7 Numba-JIT waveguide instruments
└── Phase 4: RELEASE — model decay + PCM key-off sample overlay
      └── Continuous damper model (0.0-1.0, not binary)
```

### Three Synthesis Paths

| Path | Instruments | Technology |
|---|---|---|
| **Modal resonator** | Piano, guitar, mallets, harp | Damped harmonic oscillators via velocity Verlet integration |
| **Spectral sustain** | Choir, ethnic, accordion, organ, pads | Pink noise shaped by attack spectrum, per-instrument decay |
| **Waveguide** | Bowed strings, brass, woodwinds | Numba-JIT digital waveguides with nonlinear excitation |

## Waveguide Instruments (7 types)

| # | Instrument | Excitation Model | Bore Type |
|---|---|---|---|
| 1 | Bowed string | Stick-slip friction | String (N = sr/f0) |
| 2 | Brass | Lip mass-spring | Conical |
| 3 | Flute | Air jet edge-tone + LCG turbulence | Open-hole |
| 4 | Recorder | Fipple edge (deterministic) | Open-hole |
| 5 | Clarinet | Single-reed | Cylindrical |
| 6 | Saxophone | Single-reed | Conical |
| 7 | Oboe | Double-reed | Conical |

## Advanced Features

| Feature | Module | Description |
|---|---|---|
| **Continuous articulation** | `continuous_articulation.py` | 5 dimensions: staccato/legato, sul tasto/ponticello, pp/ff, normal/marcato, vibrato. Smoothstep interpolation over configurable transition times |
| **Phrase analysis** | `phrase_analyzer.py` | Boundary detection (>500ms gap), dynamic contour, apex anticipation, rubato timing |
| **Velocity crossfade** | `velocity_crossfade.py` | 1-N velocity layers with equal-power sin/cos blending |
| **Formant-preserving shift** | `formant_shifter.py` | Phase vocoder with spectral envelope separation |
| **Note-aware resonance** | `sympathetic_resonance.py` | Only undamped held notes resonate through harmonic proximity coupling |
| **Gesture detection** | `auto_detect/engine.py` | 7 gestures: legato, glissando, velocity, duration, sforzando, repetition, crescendo |

## Integration

```python
from synth.engines.acoustic.behavioral_voice import BehavioralVoice
from synth.engines.acoustic.waveguide import BowedStringWaveguide, ClarinetWaveguide
from synth.engines.acoustic.continuous_articulation import ContinuousArticulation
from synth.engines.acoustic.phrase_analyzer import PhraseAnalyzer

# Hybrid voice with velocity layers
voice = BehavioralVoice(sample_rate=44100)
voice.note_on(60, 100, attack_data, modes, release_data=key_off_sample)

# Waveguide instrument
bowed = BowedStringWaveguide(44100)
bowed.set_note(60)
bowed.bow_pressure = 0.5  # Continuous control

# Continuous articulation morphing
art = ContinuousArticulation()
art.set("staccato_legato", 0.8, transition=0.1)  # Morph to legato over 100ms
```

## Performance

All waveguide instruments use Numba `@njit(cache=True)` for near-C performance. At 44.1kHz with 256-sample blocks:
- 4-voice bowed string ensemble: ~1.2ms CPU
- 8-voice clarinet section: ~0.8ms CPU
- 16-voice modal resonator: ~0.5ms CPU

Total: ~2.5ms for a full behavioral orchestra within the 5.8ms block budget.
