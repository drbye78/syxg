# AGENTS.md - XG Synthesizer

## Build / Lint / Test

```bash
# Install all (dev + audio + workstation)
uv sync --group dev --group audio --group workstation

# Run workstation
python -m vibexg

# Single test
pytest tests/test_voice_manager.py -v

# Fast tests only (skips @pytest.mark.slow)
pytest tests/ -m "not slow"

# All tests (parallel by default via -n auto)
pytest tests/ -v

# Coverage (HTML report)
pytest tests/ --cov=synth --cov-report=html

# Lint / format / typecheck (must pass before commit)
ruff check synth/ vibexg/
black --check --diff synth/ vibexg/
mypy synth/ vibexg/

# Auto-fix
black synth/ vibexg/ && ruff check --fix synth/ vibexg/

# Pre-commit hooks (configured in .pre-commit-config.yaml)
pre-commit run --all-files
```

## Code Conventions

- **Formatter**: Black, line length 100
- **Linter**: Ruff (select E, W, F, I, B, C4, UP, RUF in pyproject.toml)
- **Type checking**: MyPy strict mode (no `Any` without justification, no implicit `Optional`)
- **Python**: `>=3.12` required; `.python-version` may be higher (currently 3.14)

### File-level
- `from __future__ import annotations` at top of every `.py` file
- Imports: stdlib → third-party → local, blank-line separated
- No `print()` — use `logging`

### Types & data classes
- `X | None` (not `Optional[X]`)
- `@dataclass(slots=True)` for new data classes
- No `pickle` — use JSON

### Audio path rules
- Pre-allocated buffers only — no `np.zeros()`/`np.empty()` in hot paths
- Interleaved stereo: shape `(block_size, 2)`, dtype `np.float32`
- Validate buffer shapes before `+=`
- Numba: `@jit(nopython=True, fastmath=True, cache=True)`

### Threading
- `threading.Event` for interruptible waits (not bare `time.sleep`)
- `threading.local()` for per-thread caches
- Daemon threads for background workers

## Architecture

### Two synthesizer entrypoints (NOT duplicates)

| Class | File | Purpose |
|-------|------|---------|
| `ModernXGSynthesizer` | `synth/synthesizers/rendering.py` | MIDI rendering — offline/batch |
| `Synthesizer` | `synth/synthesizers/realtime.py` | Real-time workstation — vibexg TUI |

### Key directories
- `synth/` — Core library (engines, processing, protocols, primitives). See `synth/AGENTS.md` for subpackage map.
- `vibexg/` — Real-time workstation (XGWorkstation, CLI, TUI, MIDI I/O, managers)
- `vst3_plugin/` — JUCE submodule + pybind11 bridge
- `tests/` — Test suite (101+ files; pytest markers: `slow`, `integration`, `unit`)

### CLI entry points (from pyproject.toml `[project.scripts]`)
- `render-midi` → `render_midi:main` (uses ModernXGSynthesizer)
- `vibexg` → `vibexg.cli:main` (real-time workstation)

### Vibexg module map
- `workstation.py` — `XGWorkstation` orchestrator
- `midi_inputs.py` — MIDI input interfaces (keyboard, mido port, virtual, network, file, stdin)
- `audio_outputs.py` — Audio output engines (sounddevice, file render)
- `cli.py` / `tui.py` — Entrypoint and Rich-based TUI
- `managers.py` — PresetManager, MIDILearnManager, StyleEngineIntegration

### Keyboard input quirk
`KeyboardListener` in `synth/utils/keyboard.py` uses `tty.setraw()` which consumes ALL keystrokes. Command keys must flow through `set_command_callback()`, not `input()`. The `input()` loop and raw keyboard listener cannot coexist.

## Hard Rules (violations fail review)
1. No duplicate method definitions (second silently shadows first)
2. No bare `except:` — always `except Exception:`
3. No memory allocation in audio paths — use BufferPool
4. Validate buffer shapes before `+=` operations
5. No `pickle` — JSON only

## Common Tasks

### Add a synthesis engine
1. Create class in `synth/engines/` implementing `SynthesisEngine`
2. Register in `engine_registry.py` via `SynthesisEngineRegistry.register()`
3. Add tests in `tests/`

### Add a MIDI input type
1. Subclass `MIDIInputInterface` in `vibexg/midi_inputs.py`
2. Implement `_start_interface()` / `_stop_interface()`
3. Add case in `XGWorkstation._create_midi_interface()`
4. Add to `InputInterfaceType` enum in `vibexg/types.py`

## State of the repo
- **Package manager**: `uv` (uv.lock committed)
- **CI**: Not configured (`.github/workflows/` exists but empty)
- **Environment**: Virtual env is `/.venv/` at repo root
- **VST3 plugin**: Requires JUCE submodule (`git submodule update --init vst3_plugin/JUCE`)
- **Configuration**: `config.yaml` (root) for synth engine; `vibexg_config.yaml` for workstation
