# Changelog

All notable changes to the XG Synthesizer project are documented here.

## [Unreleased]

### Fixed
- Exponential (dB-based) ADSR envelope curves replacing linear ramps
- Modulation envelope release starts from current level (not sustain level)
- Key tracking generators 31/32 (key_to_mod_env_hold, key_to_mod_env_decay) applied to modulation envelope
- LFO→filter modulation uses 4-sub-block interpolation for waveform accuracy
- Sustain pedal release from all envelope phases (was sustain-only)
- NRPN protocol changed to single-CC6 completion per MIDI spec
- XG CC73/74/76 ranges extended to exponential 0.001-41s per XG spec
- XG CC77/78 vibrato rate/depth extended to exponential ranges per XG spec
- XG CC79 vibrato delay now updates LFO object in addition to stored value
- Pitch envelope rendering implemented (per-sample delay→attack→hold→decay→sustain→release)
- Per-sample LFO→pan with constant-power sin/cos (replaced block-constant np.mean)
- 6 cumulative CC `+=` bugs changed to `=` (CC2, CC4, CC70, CC71, CC72, CC75)
- XG/GS part mode selection: drum bank constant unified (BANK_DRUM=127), _is_drum_mode bit 4 fix
- SF2 sample cache: Ordereddict NameError, mip-map cache key, data.copy() on get, 24-bit conversion dedup
- SF2 wavetable render loop vectorized (numpy array ops replacing per-sample Python loop)
- SF2 pitch bend unit corrected from cents to semitones
- mod wheel doubling removed (now applied once per block)
- Expression (CC11) wired into volume pipeline
- Pan changed to constant-power sin/cos
- Portamento per-sample vectorized glide
- Velocity curve selection (concave/convex/linear from SF2 gen 41)
- Parameter range clamping for all critical SF2 generators
- Instrument global zone inheritance plumbed through create_zone_engine
- Controllers dict populated from synth.channels at note_on time
- Double audio generation bug fixed (skip_generation flag)
- np.zeros in hot path replaced with BufferPool
- 28 method-level imports moved to module top
- 16 pre-existing ruff warnings fixed
- Jupiter-X arpeggiator crash (empty __all__) fixed

### Added
- XGChannelParameterManager connected via Channel._xg_param_manager
- 6 NRPN-derived values and 12 XG parameters flow through _collect_modulation_values()
- SF2PartModeIntegrator for XG/GS part mode routing
- Sysex handling in realtime.py → XGSynthesizerSystem.process_sysex()
- Part mode change callback in XGSynthesizerSystem
- S.Art2 SYSEX command system (8 sub-commands, 4 parsers, 3 builders, checksum)
- S.Art2 compatibility mode routing (XG_ARTICULATION_MAP / GS_ARTICULATION_MAP)
- ArticulationPreset with CATEGORY_ALIASES, velocity/key splits
- SF2SampleModifier with 28 articulation methods (pitch, envelope, modulation, noise)
- Scratch buffer system for zero-allocation DSP (Phase 3)
- S.Art2 parameter routing through modulation dict (Phase 2)
- 35 audio-quality DSP tests for modifiers (pitch accuracy, envelopes, boundaries)
- Stereo width control via modulation dict (previously always 1.0)

### Fixed
- S.Art2 modifiers.py: linear-interpolation resampling replacing nearest-neighbour
- S.Art2 modifiers.py: one-pole IIR filters replacing boxcar convolutions (5 methods)
- S.Art2 modifiers.py: apply_bend AM bug → real pitch shift
- S.Art2 modifiers.py: apply_harmonics derives freq from MIDI note (was hardcoded 440 Hz)
- S.Art2 modifiers.py: apply_trill sinusoidal (was square wave with clicks)
- S.Art2 modifiers.py: all np.zeros/ones/copy/empty replaced with scratch buffers
- S.Art2 sart2_region.py: generate_samples() applies modulation BEFORE base engine
- S.Art2 sart2_region.py: _apply_note_on_articulation handles 17 articulations (5 categories)
- S.Art2 sart2_region.py: _apply_articulation_to_modulation maps to all 12 gs_* keys
- S.Art2 controllers.py: SYSEX COMMANDS dict, 3 new parsers, 3 builders, _find_nrpn

## [2026-04-14] — Modular Restructure

### Added
- New modular architecture with synth/ as the core library package
- synth/AGENTS.md — hierarchical knowledge base for core library
- synth.hardware package (Jupiter-X integration)
- synth.io package (SF2 and MIDI file I/O)

### Fixed
- Broken imports: synth.core.* → synth.primitives/synth.synthesizers
- Broken imports: synth.engine.* → synth.engines.*
- Orphaned partial_generator_block.py removed
- __all__ added to constants modules
- Abstract classes converted to proper @abstractmethod
- Import sorting in __init__ files
- Python version updated to 3.11+ in docs

### Changed
- Package restructured: synth.engine → synth.engines, synth.core → synth.primitives
- pyproject.toml updated (py314→py313 for ruff compatibility)

## [2026-03-28] — Test Suite and Documentation

### Added
- Comprehensive test suite expansion
- AGENTS.md project guide for AI pair programmers
- Improving documentation structure and coverage

## [2026-03-23] — SF2 and XG/GS Feature Implementation

### Added
- Missing SF2 features implemented (region support, modulation)
- XG/GS feature gap closure
- Zone cache with range tree optimization
- MIDI message timestamp support

### Fixed
- MIDI message timestamp bug
- Linting, security, and test compliance issues (refactor pass)

## [2026-03-06] — SF2 Region Support

### Added
- SF2 region-based synthesis support
- Envelope test infrastructure

## [2026-03-03] — SF2 Engine Refactor

### Changed
- SF2 engine, channel, and effects refactored
- Test data files (sf2_presets.csv) removed
- .qwen config and dependabot.yml removed

### Fixed
- Various test and compliance issues resolved

## [2026-02-28] — Effects and Engine Refactor

### Changed
- Effects processing pipeline refactored
- Engine architecture improvements (FM, SF2)
- Voice and XG arpeggiator refactored
- Default audio format updated to MP3

### Fixed
- Debug output removed from production code

## [2026-02-27] — Vibexg Workstation

### Added
- **Vibexg** — Real-time XG MIDI workstation
- TUI control surface (Rich-based)
- MIDI input subsystem (keyboard, ports, network, file, stdin)
- Audio output subsystem (sounddevice, file rendering)
- Preset management system
- MIDI Learn functionality
- Style engine with auto-accompaniment
- Multi-format MIDI file rendering
- Network MIDI support (RTP-MIDI)

### Changed
- Project structure reorganized for vibexg integration
- MPE, sampling, sequencer, and style systems enhanced

## [2026-02-25] — Early Development

### Changed
- FM and SF2 engine refactoring
- Documentation cleanup and reorganization
- Initial modular architecture shaping

## [2025-09-01 through 2026-02-24] — Initial Development

Early development phase with iterative prototyping across:
- SF2 SoundFont loading and deferred parsing
- FM-X 8-operator synthesis engine
- SFZ v2 engine with modulation system
- XG/GS/MIDI protocol implementation
- Audio effects processing chain
- XGML configuration language
- S.Art2 (Super Articulation 2) system
- Style engine for auto-accompaniment
- Physical modeling and spectral engines
