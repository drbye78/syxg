# synth/ - Core Synthesis Library

## OVERVIEW
Core synthesis engine, DSP primitives, and XG/GS protocol implementations. Does NOT include the vibexg workstation.

## STRUCTURE
| Subdir | Purpose |
|--------|---------|
| `engines/` | Synthesis engine implementations (SF2, FM, FM-X, Physical, Wavetable, Granular, Spectral, Additive) |
| `processing/` | Audio/MIDI processing pipeline (channel, voice, partial, effects, modulation) |
| `protocols/xg/` | XG specification (S.Art2, arpeggiator, drum kit, effects) |
| `protocols/gs/` | GS specification (JV-2080, GS reset, NRPN) |
| `primitives/` | DSP building blocks (BufferPool, Envelope, Filter, Oscillator, Panner) |
| `hardware/` | Hardware emulation (Jupiter-X, S90/S70 FDSP) |
| `io/` | File I/O (MIDI, Audio, SF2, SFZ parsers) |
| `sampling/` | Sample loading, pitch/time stretching, sample library |
| `synthesizers/` | Top-level orchestrators (ModernXGSynthesizer offline, Synthesizer realtime) |
| `style/` | Auto-accompaniment .sty/.sff engine |
| `sequencer/` | Pattern sequencer, groove quantization, MIDI file handler |

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Add new synthesis engine | `engines/` - subclass `SynthesisEngine` base class |
| Add XG parameter | `protocols/xg/xg_system_parameters.py` |
| Add S.Art2 articulation | `protocols/xg/sart/articulation_controller.py` |
| Add effect type | `processing/effects/` - follow coordinator pattern |
| Add MIDI parser | `io/midi/` - implement `MIDIMessage` handlers |
| Add sample format support | `sampling/sample_formats.py` |
| Buffer allocation | `primitives/buffer_pool.py` - never allocate in audio path |
| Voice management | `processing/voice/voice_manager.py` |

## CONVENTIONS
- **Engine registration**: Add to `engine_registry.py` via `SynthesisEngineRegistry.register()`
- **Parameter routing**: Use `engines/parameter_router.py` for engine-agnostic parameter mapping
- **Effects chain**: Subclass `XGEffectsCoordinator` for new effect categories
- **MIDI messages**: Use Python 3.11+ `match`/`case` for message dispatch
- **Audio buffers**: Always `(block_size, 2)` stereo interleaved, `np.float32`

## ANTI-PATTERNS
- **NEVER** create new `SynthesisEngine` subclasses in `synthesizers/` - engines belong in `engines/`
- **NEVER** hardcode synthesis logic in `protocols/` - routing goes through `parameter_router.py`
- **NEVER** allocate `np.zeros()` or `np.empty()` in audio render paths - use `BufferPool`
- **NEVER** put UI/TUI code in `synth/` - belongs in `vibexg/` package