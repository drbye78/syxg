# S.Art2 Subsystem — Overview

**Package:** `synth/protocols/xg/sart/` + `synth/engines/articulation/`

## Architecture

The S.Art2 (Super Articulation 2) subsystem provides universal articulation control across all synthesis engines. It operates in two tiers:

### Tier 1 — Core Articulation (`synth/protocols/xg/sart/`)
- **SArt2Region** — IRegion wrapper providing NRPN dispatch and articulation state
- **ArticulationController** — NRPN/SYSEX message processing (333 mapped names)
- **YamahaNRPNMapper** — bidirectional NRPN↔articulation lookup (17 categories)
- **ArticulationPreset** — per-program articulation configs with velocity/key splits

### Tier 2 — Unified Engine (`synth/engines/articulation/`)
- **ArticulationEngine** — data-driven, stereo-native, registry-driven dispatch
- **12 modular DSP processors**: PitchMod, Envelope, AmplitudeMod, Filter, Noise, Transient, Formant, Rotary, Harmonics, Pedal, Composite
- **ARTICULATION_REGISTRY** — 317-entry dispatch table (254 DSP, 10 voice-level, 11 dynamics, 42 documented STUBs)

## Integration

```
SynthesisEngine.create_region()
  → base_region (SF2/FM/Additive/etc.)
    → SArt2Region wrapping
      → AcousticBehaviorRegion (cross-note behavior)
        → ArticulationEngine.apply() (sample-level DSP)
```

## New Subsystems

| Subsystem | Location | Purpose |
|---|---|---|
| **AutoDetectionEngine** | `synth/engines/auto_detect/` | 7 gesture types: legato, glissando, velocity, duration, sforzando, repetition, crescendo |
| **VoiceFeatureController** | `synth/engines/voice_features/` | Trigger modes (trig/gate/tie/legato), glide/portamento, LFO sync, filter envelope |
| **ArtButtonManager** | `synth/engines/art_buttons/` | 3-slot per-voice assignable articulation triggers |
| **ArticulationNoteSequencer** | `synth/engines/note_sequencing/` | Grace notes, agoge, raking, double/triple tongue |
| **ContinuousArticulation** | `synth/engines/acoustic/` | 5D morphing: staccato/legato, sul tasto/ponticello, pp/ff, normal/marcato, vibrato |
| **PhraseAnalyzer** | `synth/engines/acoustic/` | Boundary detection, apex anticipation, rubato timing, dynamic contour |

## Import Path

```python
from synth.protocols.xg.sart import SArt2Region, ArticulationController
from synth.engines.articulation import ArticulationEngine, ArticulationContext
from synth.engines.auto_detect import AutoDetectionEngine
from synth.engines.voice_features import VoiceFeatureController
from synth.engines.art_buttons import ArtButtonManager
```
