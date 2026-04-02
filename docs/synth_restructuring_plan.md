# Synth Package Restructuring Plan

## Executive Summary

This document outlines a comprehensive restructuring of the `synth` package to achieve:
- **Consistent module organization** with clear architectural boundaries
- **Concise files** targeting 200-400 lines per module
- **Clean dependency flow** with no circular imports
- **Improved testability** with focused, single-responsibility modules
- **Zero backward compatibility** constraints - complete clean-slate redesign

---

## Part 1: New Directory Structure

```
synth/
│
├── # ==================== Public API ====================
├── __init__.py                     # Top-level exports
│
├── # ==================== Core Types & Protocols ====================
├── types.py                        # Protocol definitions, TypedDicts, enums
│
├── # ==================== Core Audio Infrastructure ====================
├── core/
│   ├── __init__.py
│   ├── buffer_pool.py              # Zero-allocation buffer management
│   ├── envelope.py                 # ADSR envelope generators
│   ├── filter.py                   # Biquad, SVF, ladder filters
│   ├── oscillator.py               # Basic waveform oscillators
│   ├── panner.py                   # Stereo panning utilities
│   ├── lfo.py                      # LFO implementations (sine, triangle, etc.)
│   ├── noise.py                    # Noise generators (white, pink, brownian)
│   └── coefficient_manager.py      # Pre-computed coefficient tables
│
├── # ==================== Audio Processing Pipeline ====================
├── audio/
│   ├── __init__.py
│   ├── pipeline.py                 # Audio block processing pipeline
│   ├── mixer.py                    # Channel-to-stereo mixing
│   ├── limiter.py                  # Master limiting/dithering
│   ├── resampler.py                # Sample rate conversion
│   └── effects_chain.py            # Effects processing chain
│
├── # ==================== Voice Management ====================
├── voice/
│   ├── __init__.py
│   ├── voice.py                    # Voice data structure
│   ├── voice_manager.py            # Polyphony and voice stealing
│   ├── voice_allocator.py          # Allocation strategies (LRU, oldest, quietest)
│   └── voice_factory.py            # Voice creation from synthesis engines
│
├── # ==================== Channel Processing ====================
├── channel/
│   ├── __init__.py
│   ├── channel.py                  # Main channel data/behavior
│   ├── controllers.py              # CC/NRPN parameter processing
│   ├── drum_channel.py             # Drum-specific channel handling
│   ├── sends.py                    # Effect send level management
│   └── parameter_router.py         # Parameter update routing
│
├── # ==================== Synthesis Engines ====================
├── engines/
│   ├── __init__.py
│   ├── base.py                     # SynthesisEngine protocol/base class
│   ├── region.py                   # Region descriptor and interface
│   ├── preset_info.py              # Preset information structure
│   │
│   ├── # --- Sample-Based Synthesis ---
│   ├── sampler/
│   │   ├── __init__.py
│   │   ├── sf2_engine.py           # SoundFont 2 synthesis engine
│   │   ├── sf2_region.py           # SF2 region audio processing
│   │   ├── sf2_voice.py            # SF2 voice (note instance)
│   │   ├── sfz_engine.py           # SFZ synthesis engine
│   │   └── wav_engine.py           # WAV-based sample playback
│   │
│   ├── # --- FM Synthesis ---
│   ├── fm/
│   │   ├── __init__.py
│   │   ├── engine.py               # FM synthesis engine
│   │   ├── operator.py             # FM operator (carrier/modulator)
│   │   ├── algorithm.py            # FM algorithm definitions
│   │   ├── lfo.py                  # FM-specific LFO
│   │   ├── formant.py              # Formant filter support
│   │   └── sysex.py                # FM SysEx handling
│   │
│   ├── # --- Additive Synthesis ---
│   ├── additive/
│   │   ├── __init__.py
│   │   ├── engine.py               # Additive synthesis engine
│   │   ├── partial.py              # Additive partial oscillator
│   │   ├── harmonic.py             # Harmonic spectrum definitions
│   │   └── morphing.py             # Spectral morphing
│   │
│   ├── # --- Wavetable Synthesis ---
│   ├── wavetable/
│   │   ├── __init__.py
│   │   ├── engine.py               # Wavetable synthesis engine
│   │   ├── wavetable.py            # Wavetable data structure
│   │   ├── oscillator.py           # Wavetable oscillator
│   │   └── morphing.py             # Wavetable morphing
│   │
│   ├── # --- Granular Synthesis ---
│   ├── granular/
│   │   ├── __init__.py
│   │   ├── engine.py               # Granular synthesis engine
│   │   ├── grain.py                # Individual grain
│   │   └── cloud.py                # Grain cloud management
│   │
│   ├── # --- Physical Modeling ---
│   ├── physical/
│   │   ├── __init__.py
│   │   ├── an_engine.py            # Analog physical modeling engine
│   │   ├── waveguide.py            # Digital waveguide string
│   │   ├── resonator.py            # Modal resonator
│   │   ├── excitation.py           # Excitation models (pluck, bow, strike)
│   │   └── material.py             # Material properties (wood, metal, etc.)
│   │
│   ├── # --- Formant-Driven Synthesis (FDSP) ---
│   ├── fdsp/
│   │   ├── __init__.py
│   │   ├── engine.py               # FDSP synthesis engine
│   │   ├── phoneme.py              # Phoneme data
│   │   ├── vocal_db.py             # Vocal database
│   │   └── formant_bank.py         # Formant filter bank
│   │
│   └── # --- Spectral Synthesis ---
│   └── spectral/
│       ├── __init__.py
│       ├── engine.py               # Spectral synthesis engine
│       ├── fft_processor.py        # FFT analysis/synthesis
│       ├── filter.py               # Spectral filtering
│       └── vocoder.py              # Vocoder processing
│
├── # ==================== Effects Processing ====================
├── effects/
│   ├── __init__.py
│   ├── types.py                    # Effect type enums
│   ├── coordinator.py              # Effects pipeline orchestration
│   ├── registry.py                 # Effect type registration
│   ├── factory.py                  # Effect instance creation
│   ├── presets.py                  # XG effect preset definitions
│   │
│   ├── # --- System Effects (Reverb/Chorus) ---
│   ├── system/
│   │   ├── __init__.py
│   │   ├── reverb.py               # System reverb (hall/room/plate)
│   │   └── chorus.py               # System chorus
│   │
│   ├── # --- Variation Effects ---
│   ├── variation/
│   │   ├── __init__.py
│   │   ├── modulation.py           # Chorus, flanger, phaser
│   │   ├── delay.py                # Delay variations (LCR, echo, Pan)
│   │   ├── pitch.py                # Pitch shift, harmonizer, detune
│   │   └── special.py              # Vocoder, ERL, gate reverb
│   │
│   ├── # --- Insertion Effects ---
│   ├── insertion/
│   │   ├── __init__.py
│   │   ├── distortion.py           # Distortion, overdrive, fuzz
│   │   ├── dynamics.py             # Compressor, limiter, expander
│   │   ├── filter.py               # Auto-filter, wah, envelope filter
│   │   ├── modulation.py           # Phaser, flanger, rotary speaker
│   │   └── spatial.py              # Stereo imaging, auto-pan
│   │
│   └── # --- Equalization ---
│   └── eq/
│       ├── __init__.py
│       ├── channel_eq.py           # Per-channel 5-band EQ
│       └── master_eq.py            # Master equalizer
│
├── # ==================== MIDI Processing ====================
├── midi/
│   ├── __init__.py
│   ├── parser.py                   # MIDI message parsing
│   ├── processor.py                # MIDI message routing/processing
│   ├── nrpn.py                     # NRPN parameter handling
│   ├── sysex.py                    # SysEx message handling
│   ├── sysex_router.py             # SysEx routing to handlers
│   ├── capability_discovery.py     # MIDI 2.0/XG capability querying
│   └── timestamp.py                # Sample-accurate timing
│
├── # ==================== Modulation ====================
├── modulation/
│   ├── __init__.py
│   ├── matrix.py                   # Modulation matrix
│   ├── sources.py                  # Modulation sources (LFO, envelope, CC)
│   └── destinations.py             # Modulation destinations
│
├── # ==================== XG Specification ====================
├── xg/
│   ├── __init__.py
│   ├── system.py                   # XG system management
│   ├── channel.py                  # XG channel parameters
│   ├── drum_kit.py                 # XG drum kit definitions
│   ├── nrpn_params.py              # XG NRPN parameter map
│   ├── sysex.py                    # XG SysEx commands/responses
│   └── gs_compat.py                # GS compatibility layer
│
├── # ==================== MPE Support ====================
├── mpe/
│   ├── __init__.py
│   ├── zone.py                     # MPE zone management
│   ├── note.py                     # Per-note expression
│   └── processor.py                # MPE note handling
│
├── # ==================== Jupiter-X Emulation ====================
├── jupiter_x/
│   ├── __init__.py
│   ├── part.py                     # Part management
│   ├── sysex.py                    # SysEx protocol handling
│   ├── nrpn.py                     # NRPN protocol handling
│   └── params/
│       ├── __init__.py
│       ├── analog.py               # Analog engine parameters
│       ├── digital.py              # Digital engine parameters
│       ├── fm.py                   # FM engine parameters
│       └── external.py             # External engine parameters
│
├── # ==================== S90/S70 Emulation ====================
├── s90_s70/
│   ├── __init__.py
│   ├── awm_engine.py               # AWM stereo engine
│   ├── layer.py                    # Velocity crossfade layers
│   └── performance.py              # Performance features
│
├── # ==================== SF2 SoundFont Support ====================
├── sf2/
│   ├── __init__.py
│   ├── data_model.py               # SF2 data structures (zone, preset, etc.)
│   ├── file_loader.py              # Binary SF2 file loading
│   ├── soundfont.py                # SoundFont high-level abstraction
│   ├── manager.py                  # Multi-font management
│   ├── zone_cache.py               # Zone lookup acceleration
│   ├── sample_cache.py             # Sample data caching/mipmapping
│   ├── modulation.py               # SF2 modulation system
│   └── generator.py                # SF2 generator processors
│
├── # ==================== SART2 Articulation ====================
├── articulation/
│   ├── __init__.py
│   ├── engine.py                   # Articulation processing engine
│   ├── keyswitch.py                # Keyswitch articulations
│   ├── cc_controlled.py            # CC-controlled articulations
│   ├── legato.py                   # Legato transitions
│   └── presets.py                  # Articulation preset catalog
│
├── # ==================== Style/Auto-Accompaniment ====================
├── style/
│   ├── __init__.py
│   ├── engine.py                   # Auto-accompaniment engine
│   ├── chord_detection.py          # Chord recognition
│   ├── chord_voicings.py           # Chord voicing analysis
│   ├── style_layers.py             # Style layer management
│   └── phrase_generator.py         # Phrase generation
│
├── # ==================== Arpeggiator ====================
├── arpeggiator/
│   ├── __init__.py
│   ├── engine.py                   # Arpeggiator processing
│   └── patterns.py                 # Arpeggio pattern definitions
│
├── # ==================== Sampling/Audio I/O ====================
├── sampling/
│   ├── __init__.py
│   ├── loader.py                   # Audio file loading (WAV, FLAC, etc.)
│   ├── format.py                   # Audio format handling
│   └── converter.py                # Sample format conversion
│
├── # ==================== Sequencer ====================
├── sequencer/
│   ├── __init__.py
│   ├── sequencer.py                # MIDI sequencer
│   ├── timeline.py                 # Event scheduling
│   ├── pattern.py                  # Pattern data
│   └── player.py                   # Pattern playback
│
├── # ==================== GS Specification ====================
├── gs/
│   ├── __init__.py
│   ├── system.py                   # GS system management
│   ├── parameters.py               # GS NRPN parameters
│   ├── component_manager.py        # GS component integration
│   ├── tone.py                     # Tone management
│   └── drum_kit.py                 # GS drum kit handling
│
├── # ==================== SFZ Support ====================
├── sfz/
│   ├── __init__.py
│   ├── engine.py                   # SFZ synthesis engine
│   ├── parser.py                   # SFZ file parsing
│   ├── region.py                   # SFZ region definition
│   └── group.py                    # SFZ group management
│
├── # ==================== XGML Configuration ====================
├── xgml/
│   ├── __init__.py
│   ├── parser.py                   # YAML configuration parsing
│   ├── translator.py               # XGML to synthesizer configuration
│   ├── validator.py                # Schema validation
│   └── schema.py                   # XGML schema definitions
│
├── # ==================== Main Synthesizer ====================
├── synthesizer/
│   ├── __init__.py
│   ├── modern_xg.py                # ModernXGSynthesizer main class
│   ├── initialization.py           # Initialization helpers
│   ├── xg_subsystem.py             # XG subsystem management
│   ├── gs_subsystem.py             # GS subsystem management
│   ├── mpe_subsystem.py            # MPE subsystem management
│   ├── config_integration.py       # XGML/config integration
│   ├── arpeggiator_integration.py  # Arpeggiator integration
│   └── plugin_integration.py       # Plugin system integration
│
├── # ==================== Parser Protocols ====================
├── parsers/
│   ├── __init__.py
│   ├── sff2_protocol.py            # SFF2 MIDI protocol definitions
│   ├── sff2_message.py             # SFF2 message builder
│   ├── sff2_parser.py              # SFF2 message parser
│   └── sff2_bulk.py                # Bulk transfer handling
│
└── # ==================== Utilities ====================
└── utils/
    ├── __init__.py
    ├── timing.py                   # Timing utilities
    ├── validation.py               # Parameter validation
    └── performance.py              # Performance monitoring/profiling
```

---

## Part 2: Module Size Targets

### File Size Distribution Goals

| Category | Target Lines | Count | Description |
|----------|-------------|-------|-------------|
| Core Infrastructure | 150-300 | ~15 | Buffer pool, envelope, filter, etc. |
| Synthesis Engines | 200-400 | ~40 | Engine + operators/components |
| Effects Processors | 150-350 | ~35 | Individual effect implementations |
| MIDI/SysEx Handlers | 100-250 | ~20 | Protocol-specific handlers |
| Main Classes | 200-500 | ~10 | Orchestrators/facades |
| Type Definitions | 100-250 | ~8 | Enums, protocols, TypedDicts |
| Configuration | 150-300 | ~10 | XGML, parameters |
| **Total** | | **~140** | |

### Before vs After Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Total modules | ~65 | ~140 | +75 logical modules |
| Avg file size | ~650 lines | ~250 lines | -62% |
| Max file size | ~2474 lines | ~500 lines | -80% |
| Files >1000 lines | 20 | 0 | 100% reduction |
| Files 500-999 lines | ~35 | ~10 | -71% |
| Files <500 lines | ~10 | ~130 | +1200% |

---

## Part 3: Migration Strategy

### Phase 0: Preparation (Week 1)

```
Day 1-2: Create new package structure
Day 3-4: Set up build configuration
Day 5: Create migration test scripts
```

#### Tasks:
1. Create new directory tree under `synth_v2/`
2. Update `pyproject.toml` to support parallel package structure temporarily
3. Create migration validation script to verify API compatibility
4. Document all public API endpoints that vibexg and VST3 plugin depend on

#### Deliverables:
- [ ] New empty directory structure
- [ ] Migration test script
- [ ] API dependency map

### Phase 1: Core Infrastructure Migration (Week 1-2)

```
Priority: CRITICAL
Risk: LOW (these are self-contained)
Test coverage: Unit tests only
```

**Order of migration:**
1. `synth/types.py` → foundation for everything
2. `synth/core/buffer_pool.py` → zero-alloc buffers
3. `synth/core/envelope.py` → ADSR
4. `synth/core/filter.py` → filters
5. `synth/core/oscillator.py` → oscillators
6. `synth/core/panner.py` → panning
7. `synth/core/lfo.py` → LFOs
8. `synth/core/noise.py` → noise generators
9. `synth/core/coefficient_manager.py` → coefficients

**Migration steps for each module:**
```python
# 1. Create new file with same public API
# 2. Copy implementation (may split if >400 lines)
# 3. Write focused unit tests
# 4. Run existing tests to verify no regression
# 5. Update import references in other modules
```

**Test impact:**
- Existing tests in `tests/test_envelope.py`, `tests/test_utils.py` update paths
- No behavioral changes expected

### Phase 2: Voice & Channel Migration (Week 2-3)

```
Priority: HIGH
Risk: MEDIUM (integrates with engines)
Test coverage: Unit + integration tests
```

**Order:**
1. `synth/voice/voice.py`
2. `synth/voice/voice_factory.py`
3. `synth/voice/voice_allocator.py`
4. `synth/voice/voice_manager.py`
5. `synth/channel/channel.py`
6. `synth/channel/controllers.py` (split from channel.py)
7. `synth/channel/drum_channel.py` (extracted)
8. `synth/channel/sends.py` (extracted)

**Test impact:**
- `tests/test_voice_manager.py` - update imports
- `tests/test_voice_management.py` - update imports
- `tests/test_voice_management_comprehensive.py` - update imports
- New tests needed for split modules

### Phase 3: SF2 SoundFont Migration (Week 3-4)

```
Priority: HIGH
Risk: MEDIUM (complex data model)
Test coverage: Comprehensive existing tests
```

**Order:**
1. `synth/sf2/data_model.py`
2. `synth/sf2/file_loader.py`
3. `synth/sf2/soundfont.py`
4. `synth/sf2/manager.py`
5. `synth/sf2/zone_cache.py`
6. `synth/sf2/sample_cache.py`
7. `synth/sf2/modulation.py`
8. `synth/sf2/generator.py`
9. `synth/engines/sampler/sf2_engine.py`
10. `synth/engines/sampler/sf2_region.py`
11. `synth/engines/sampler/sf2_voice.py`

**Test impact:**
- `tests/test_sf2_data_model.py` - update paths
- `tests/test_sf2_file_loader.py` - update paths
- `tests/test_sf2_integration.py` - update paths
- `tests/test_sf2_modulation_engine.py` - update paths
- `tests/test_sf2_parsing_validation.py` - update paths
- `tests/test_sf2_region_architecture.py` - update paths
- `tests/test_sf2_zone_cache.py` - update paths

### Phase 4: Synthesis Engines Migration (Week 4-6)

```
Priority: HIGH
Risk: MEDIUM-HIGH (core audio generation)
Test coverage: Engine-specific tests
```

**FM Engine:**
1. `synth/engines/base.py`
2. `synth/engines/region.py`
3. `synth/engines/fm/engine.py`
4. `synth/engines/fm/operator.py`
5. `synth/engines/fm/algorithm.py`
6. `synth/engines/fm/lfo.py`
7. `synth/engines/fm/formant.py`
8. `synth/engines/fm/sysex.py`

**Other engines (parallel work):**
- Wavetable engine → `engines/wavetable/`
- Additive engine → `engines/additive/`
- Granular engine → `engines/granular/`
- Physical engine → `engines/physical/`
- FDSP engine → `engines/fdsp/`
- Spectral engine → `engines/spectral/`
- Sampler engine → `engines/sampler/`

**Test impact:**
- Multiple test files need import path updates
- New tests for split modules

### Phase 5: Effects Migration (Week 6-7)

```
Priority: HIGH
Risk: MEDIUM (many effect types)
Test coverage: Effect-specific tests
```

**Order:**
1. `synth/effects/types.py`
2. `synth/effects/registry.py`
3. `synth/effects/factory.py`
4. `synth/effects/coordinator.py`
5. `synth/effects/presets.py`
6. `synth/effects/system/reverb.py`
7. `synth/effects/system/chorus.py`
8. `synth/effects/variation/modulation.py`
9. `synth/effects/variation/delay.py`
10. `synth/effects/variation/pitch.py`
11. `synth/effects/variation/special.py`
12. `synth/effects/insertion/distortion.py`
13. `synth/effects/insertion/dynamics.py`
14. `synth/effects/insertion/filter.py`
15. `synth/effects/insertion/modulation.py`
16. `synth/effects/insertion/spatial.py`
17. `synth/effects/eq/channel_eq.py`
18. `synth/effects/eq/master_eq.py`

**Test impact:**
- `tests/test_effects_integration.py` - update paths
- `tests/test_effects_chaining.py` - update paths
- `tests/test_xg_effects_routing.py` - update paths

### Phase 6: MIDI & XG Migration (Week 7-8)

```
Priority: HIGH
Risk: MEDIUM (external protocol)
```

**Order:**
1. `synth/midi/parser.py`
2. `synth/midi/processor.py`
3. `synth/midi/nrpn.py`
4. `synth/midi/sysex.py`
5. `synth/midi/sysex_router.py`
6. `synth/midi/capability_discovery.py`
7. `synth/midi/timestamp.py`
8. `synth/xg/system.py`
9. `synth/xg/channel.py`
10. `synth/xg/drum_kit.py`
11. `synth/xg/nrpn_params.py`
12. `synth/xg/sysex.py`
13. `synth/xg/gs_compat.py`

**Test impact:**
- `tests/test_midi_processing.py` - update paths
- `tests/test_nrpn_rpn_processing.py` - update paths
- `tests/test_xg_*.py` files (many) - update paths
- `tests/test_gs_sysex.py` - update paths

### Phase 7: Specialized Features Migration (Week 8-9)

```
Priority: MEDIUM
Risk: LOW-MEDIUM (self-contained features)
```

**MPE:**
1. `synth/mpe/zone.py`
2. `synth/mpe/note.py`
3. `synth/mpe/processor.py`

**Jupiter-X:**
4. `synth/jupiter_x/part.py`
5. `synth/jupiter_x/sysex.py`
6. `synth/jupiter_x/nrpn.py`
7. `synth/jupiter_x/params/analog.py`
8. `synth/jupiter_x/params/digital.py`
9. `synth/jupiter_x/params/fm.py`
10. `synth/jupiter_x/params/external.py`

**S90/S70:**
11. `synth/s90_s70/awm_engine.py`
12. `synth/s90_s70/layer.py`
13. `synth/s90_s70/performance.py`

**SART2 Articulation:**
14. `synth/articulation/engine.py`
15. `synth/articulation/keyswitch.py`
16. `synth/articulation/cc_controlled.py`
17. `synth/articulation/legato.py`
18. `synth/articulation/presets.py`

**Test impact:**
- `tests/test_mpe_*.py` files - update paths
- `tests/test_sart2_*.py` files - update paths
- Jupiter-X specific tests

### Phase 8: Main Synthesizer Migration (Week 9-10)

```
Priority: CRITICAL
Risk: HIGH (integrates everything)
Test coverage: Full integration tests
```

**Order:**
1. `synth/synthesizer/modern_xg.py` (main facade ~400 lines)
2. `synth/synthesizer/initialization.py`
3. `synth/synthesizer/xg_subsystem.py`
4. `synth/synthesizer/gs_subsystem.py`
5. `synth/synthesizer/mpe_subsystem.py`
6. `synth/synthesizer/config_integration.py`
7. `synth/synthesizer/arpeggiator_integration.py`
8. `synth/synthesizer/plugin_integration.py`

**Key refactoring for `modern_xg.py`:**
```python
# Before: 1974 lines, everything in one class
# After: ~400 lines, delegates to subsystems

class ModernXGSynthesizer:
    def __init__(self, sample_rate, block_size, ...):
        self._core = CoreSubsystem(...)
        self._xg = XGSubsystem(...)
        self._gs = GSSubsystem(...)
        self._mpe = MPESubsystem(...)
        self._engines = EngineManager(...)
        self._effects = EffectsCoordinator(...)
        # ... delegate, don't implement
```

**Test impact:**
- This is the critical integration test point
- All integration tests run here
- `tests/test_managers.py` - update paths

### Phase 9: Auxiliary Modules (Week 10-11)

```
Priority: MEDIUM
Risk: LOW
```

**Remaining modules:**
1. `synth/arpeggiator/engine.py`
2. `synth/arpeggiator/patterns.py`
3. `synth/style/engine.py`
4. `synth/style/chord_detection.py`
5. `synth/style/chord_voicings.py`
6. `synth/style/style_layers.py`
7. `synth/style/phrase_generator.py`
8. `synth/sampling/loader.py`
9. `synth/sampling/format.py`
10. `synth/sampling/converter.py`
11. `synth/sequencer/sequencer.py`
12. `synth/sequencer/timeline.py`
13. `synth/sequencer/pattern.py`
14. `synth/sequencer/player.py`
15. `synth/sfz/engine.py`
16. `synth/sfz/parser.py`
17. `synth/sfz/region.py`
18. `synth/gs/system.py`
19. `synth/gs/parameters.py`
20. `synth/gs/component_manager.py`
21. `synth/gs/tone.py`
22. `synth/gs/drum_kit.py`
23. `synth/xgml/parser.py`
24. `synth/xgml/translator.py`
25. `synth/xgml/validator.py`
26. `synth/xgml/schema.py`
27. `synth/parsers/sff2_protocol.py`
28. `synth/parsers/sff2_message.py`
29. `synth/parsers/sff2_parser.py`
30. `synth/parsers/sff2_bulk.py`
31. `synth/utils/timing.py`
32. `synth/utils/validation.py`
33. `synth/utils/performance.py`

### Phase 10: Switchover & Cleanup (Week 11-12)

```
Priority: CRITICAL
Risk: HIGH (deployment)
```

**Tasks:**
1. Update `synth/__init__.py` to export from new structure
2. Update `vibexg/` imports to new structure
3. Update VST3 plugin imports
4. Run full test suite
5. Remove old file structure
6. Update documentation
7. Update `AGENTS.md`

---

## Part 4: Test Suite Migration

### Test File Path Updates

| Current Test File | Changes Required |
|------------------|------------------|
| `tests/test_voice_manager.py` | Update synth.voice imports |
| `tests/test_voice_management.py` | Update synth.voice imports |
| `tests/test_voice_management_comprehensive.py` | Update synth.voice imports |
| `tests/test_voice_integration.py` | Update synth.voice/vengine imports |
| `tests/test_sf2_*.py` (8 files) | Update synth.sf2 imports |
| `tests/test_effects_*.py` (3 files) | Update synth.effects imports |
| `tests/test_midi_*.py` (4 files) | Update synth.midi imports |
| `tests/test_xg_*.py` (12 files) | Update synth.xg imports |
| `tests/test_gs_sysex.py` | Update synth.gs imports |
| `tests/test_nrpn_rpn_processing.py` | Update synth.midi imports |
| `tests/test_mpe_*.py` (3 files) | Update synth.mpe imports |
| `tests/test_sart2_*.py` (6 files) | Update synth.articulation imports |
| `tests/test_envelope.py` | Update synth.core imports |
| `tests/test_envelope_processing.py` | Update synth.core imports |
| `tests/test_modulation_matrix.py` | Update synth.modulation imports |
| `tests/test_managers.py` | Update synth.synthesizer imports |
| `tests/test_config_*.py` (3 files) | Update synth.xgml imports |
| `tests/test_region_architecture.py` | Update synth.engines imports |
| `tests/test_production_*.py` (2 files) | Update synth.effects imports |
| `tests/test_comprehensive_sf2_region.py` | Update synth.engines.sampler imports |

**Total test files to update: ~60**

### New Tests to Add

| Module | New Tests Needed |
|--------|-----------------|
| `engines/fm/` | `tests/fm/test_operator.py`, `tests/fm/test_algorithm.py` |
| `engines/physical/` | `tests/physical/test_waveguide.py`, `tests/physical/test_resonator.py` |
| `effects/insertion/` | `tests/effects/insertion/test_distortion.py`, `test_dynamics.py` |
| `effects/variation/` | `tests/effects/variation/test_modulation.py`, `test_delay.py` |
| `effects/system/` | `tests/effects/system/test_reverb.py`, `test_chorus.py` |
| `synth/sf2/` | `tests/sf2/test_modulation.py`, `test_generator.py` |
| `channel/` | `tests/channel/test_controllers.py`, `test_sends.py` |
| `xg/` | `tests/xg/test_channel.py`, `test_drum_kit.py` |
| `jupiter_x/` | `tests/jupiter_x/test_sysex.py`, `test_nrpn.py` |
| `midi/` | `tests/midi/test_sysex_router.py`, `test_timestamp.py` |

**New test files to add: ~20**

### Test Coverage Goals

| Category | Current | Target |
|----------|---------|--------|
| Overall line coverage | ~65% | ~80% |
| Core infrastructure | ~75% | ~95% |
| Synthesis engines | ~60% | ~85% |
| Effects | ~55% | ~80% |
| MIDI/XG | ~70% | ~90% |
| Integration | ~50% | ~75% |

---

## Part 5: VST3 Plugin Migration

### Current Dependencies

The VST3 plugin typically depends on:
```
synth.synthesizer.ModernXGSynthesizer  # Main class
synth.core.buffer_pool                 # Audio buffers
synth.types                            # Type definitions
```

### Migration Steps

1. **Update import paths in VST3 source:**
```cpp
// Before (Python bindings)
import synth.synthesizer

// After
from synth.synthesizer import ModernXGSynthesizer
```

2. **Public API stability:**
- Ensure `ModernXGSynthesizer` public interface remains unchanged
- All methods like `generate_audio_block()`, `process_midi_message()` etc. preserve signatures

3. **VST3 plugin C++ changes:**
- No C++ changes needed if Python API is stable
- Only Python-side imports change

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| API breakage in ModernXGSynthesizer | Low | Preserve public interface |
| Buffer format changes | Very Low | No buffer format changes |
| MIDI processing changes | Low | Internal refactoring only |
| Performance regression | Medium | Benchmark before/after |

---

## Part 6: vibexg Integration Migration

### Files to Update

| File | Expected Changes |
|------|-----------------|
| `vibexg/cli.py` | Import path updates |
| `vibexg/workstation.py` | Import path updates |
| `vibexg/audio_outputs.py` | Import path updates |
| `vibexg/backends/*.py` | Import path updates |

### Migration Script

```python
#!/usr/bin/env python3
"""
Migration script to update imports from old to new structure.
Run this after Phase 10 is complete.
"""

import os
import re
from pathlib import Path

# Import path mappings
IMPORT_MAPPINGS = {
    # Old -> New mappings
    r'from synth\.engine\.modern_xg_synthesizer import': 'from synth.synthesizer import',
    r'from synth\.engine\.sf2_engine import': 'from synth.engines.sampler import',
    r'from synth\.engine\.fm_engine import': 'from synth.engines.fm import',
    r'from synth\.channel\.channel import': 'from synth.channel import',
    r'from synth\.effects\.effects_coordinator import': 'from synth.effects import',
    # ... add all mappings
}

def migrate_imports(root_dir: Path):
    for py_file in root_dir.rglob('*.py'):
        content = py_file.read_text()
        new_content = content
        for old, new in IMPORT_MAPPINGS.items():
            new_content = re.sub(old, new, new_content)
        if new_content != content:
            py_file.write_text(new_content)
            print(f"Updated: {py_file}")

if __name__ == '__main__':
    migrate_imports(Path(__file__).parent)
    print("Migration complete!")
```

---

## Part 7: Detailed Implementation Timeline

```
Week 1:  Phase 0 + Phase 1 (Core Infrastructure)
Week 2:  Phase 1 (cont.) + Phase 2 (Voice/Channel)
Week 3:  Phase 2 (cont.) + Phase 3 (SF2)
Week 4:  Phase 3 (cont.) + Phase 4 (Engines - SF2/SMPL)
Week 5:  Phase 4 (cont.) - FM/Additive/Wavetable
Week 6:  Phase 4 (cont.) - Other engines + Phase 5 start
Week 7:  Phase 5 (Effects) + Phase 6 (MIDI/XG)
Week 8:  Phase 6 (cont.) + Phase 7 (Specialized)
Week 9:  Phase 7 (cont.) + Phase 8 start
Week 10: Phase 8 (Main Synthesizer)
Week 11: Phase 9 (Auxiliary) + Phase 10 prep
Week 12: Phase 10 (Switchover) + Cleanup
```

---

## Part 8: Risk Mitigation

### Rollback Strategy

1. **Git branch per phase**: Each phase gets its own branch
2. **Continuous integration**: Tests run on every commit
3. **Preserve old structure**: Keep old files until switchover
4. **Feature flags**: Use `XG_USE_V1_STRUCTURE` env var if needed temporarily

### Performance Validation

```python
# Performance regression check
import time
import numpy as np

def benchmark_audio_block():
    synth = ModernXGSynthesizer(sample_rate=44100, block_size=1024)
    times = []
    for _ in range(100):
        start = time.perf_counter()
        synth.generate_audio_block()
        times.append(time.perf_counter() - start)
    return np.mean(times) * 1000  # ms

old_performance = 2.34  # Baseline from current implementation
new_performance = benchmark_audio_block()
assert new_performance <= old_performance * 1.10  # Within 10% tolerance
```

---

## Part 9: AGENTS.md Updates

After migration, `AGENTS.md` should be updated with new structure:

```markdown
## Project Structure (New)

```
synth/
├── core/           # Audio infrastructure
├── engines/        # Synthesis engines (sampler, fm, additive, etc.)
├── effects/        # Effects processing (system, variation, insertion)
├── channel/        # MIDI channel processing
├── voice/          # Voice management
├── midi/           # MIDI protocol handling
├── xg/             # XG specification
├── sf2/            # SoundFont support
├── synthesizer/    # Main synthesizer class
└── ...
```
```

---

## Summary

This restructuring will:
1. **Reduce average file size by 62%** (650 → 250 lines)
2. **Eliminate all files >1000 lines** (20 files currently)
3. **Increase module count to ~140** for better organization
4. **Improve test coverage** from ~65% to ~80%
5. **Maintain API stability** for VST3 plugin and vibexg
6. **Clear architectural boundaries** between subsystems
7. **Zero circular dependencies** with strict layer ordering

Estimated effort: **12 weeks** for comprehensive migration with safety checks.