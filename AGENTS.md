# AGENTS.md - XG Synthesizer

## Build / Lint / Test

```bash
# Install
pip install -e ".[dev,audio,workstation]"

# Single test
pytest tests/test_voice_manager.py -v

# All tests
pytest tests/ -v

# Fast tests only
pytest tests/ -m "not slow"

# Coverage
pytest tests/ --cov=synth --cov-report=html

# Lint (must pass before committing)
black synth/ vibexg/
ruff check synth/ vibexg/
mypy synth/ vibexg/

# Run workstation
python -m vibexg
```

## Code Style

- **Formatter**: Black, line length 100
- **Linter**: Ruff + Flake8 (see `pyproject.toml` for rules)
- **Type Checking**: MyPy strict mode
- **Python**: 3.11+ required — use pattern matching, `Self`, `TypeAlias`

### Imports & Formatting
- `from __future__ import annotations` in every file
- Standard library → third-party → local, each group separated by blank line
- No unused imports (ruff F401)
- No `print()` in production — use `logging` module

### Types
- Strict mode: no `Any` without justification, no implicit `Optional`
- Use `X | None` not `Optional[X]`
- Dataclasses use `@dataclass(slots=True)`
- Never suppress type errors with `as any`, `@ts-ignore`, etc.

### Naming
- Classes: `PascalCase` (`ModernXGSynthesizer`, `SF2Engine`)
- Functions/methods: `snake_case` (`render_block`, `parse_bytes`)
- Constants: `UPPER_SNAKE_CASE` (`DEFAULT_SAMPLE_RATE`)
- Private: leading underscore (`_handle_midi_message`)

### Error Handling
- No bare `except:` — always `except Exception:`
- Use `logging.error/warning/info` — never `print()`
- No debug prints left in code
- Catch specific exceptions, not broad ones

### Threading
- **Never** allocate memory in audio paths
- Use `threading.Lock` for shared mutable state
- Use `threading.Event` for interruptible waits (not bare `time.sleep`)
- Use `threading.local()` for per-thread caches (not function attributes)
- Daemon threads for background workers

### Audio Path Rules
- Pre-allocated buffers only — no `np.zeros()`, `np.empty()` in hot paths
- Interleaved stereo: shape `(block_size, 2)`, dtype `np.float32`
- Numba: `@jit(nopython=True, fastmath=True, cache=True)`
- Process blocks, not individual samples

## Architecture

### Two Synthesizer Entrypoints (NOT duplicates)

| Class | File | Purpose |
|-------|------|---------|
| `ModernXGSynthesizer` | `synth/engine/modern_xg_synthesizer.py` | MIDI rendering — offline/batch |
| `Synthesizer` | `synth/synthesizers/realtime.py` | Real-time workstation — vibexg TUI |

### Key Directories
- `synth/` — Core library (engines, effects, voice management)
- `vibexg/` — Real-time workstation (CLI, TUI, MIDI I/O, managers)
- `vst3_plugin/` — JUCE + pybind11 bridge
- `tests/` — Test suite

### Vibexg Module Structure
- `workstation.py` — `XGWorkstation` main orchestrator
- `midi_inputs.py` — MIDI input interfaces (keyboard, port, network, file)
- `audio_outputs.py` — Audio output engines (sounddevice, file rendering)
- `managers.py` — PresetManager, MIDILearnManager, StyleEngineIntegration
- `types.py` — Dataclasses, enums, constants
- `tui.py` — Rich-based TUI control surface
- `cli.py` — Argument parsing, main entry point
- `backends/network.py` — RTP-MIDI handler

### Keyboard Input Pattern
`KeyboardListener` (in `synth/utils/keyboard.py`) uses `tty.setraw()` which consumes ALL keystrokes. Command keys must flow through `set_command_callback()`, not `input()`. The `input()` loop and raw keyboard listener cannot coexist.

## Code Rules (Hard)

1. **No duplicate method definitions** — second silently shadows first
2. **No bare `except:`** — use `except Exception:`
3. **No `print()`** — use `logging`
4. **No memory allocation in audio paths** — use buffer pool
5. **No debug prints** — remove before committing
6. **Validate buffer shapes** before `+=` operations
7. **Never use `pickle`** — use JSON for serialization (security risk)

## Common Tasks

### Adding a Synthesis Engine
1. Create class in `synth/engine/` implementing `SynthesisEngine`
2. Register in `ModernXGSynthesizer._register_engines()`
3. Add tests in `tests/`

### Adding a MIDI Input Type
1. Subclass `MIDIInputInterface` in `vibexg/midi_inputs.py`
2. Implement `_start_interface()` / `_stop_interface()`
3. Add case in `XGWorkstation._create_midi_interface()`
4. Add to `InputInterfaceType` enum in `vibexg/types.py`
