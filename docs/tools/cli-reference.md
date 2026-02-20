# CLI Tools Reference

This document provides reference documentation for the command-line interface (CLI) tools provided by XG Synthesizer.

---

## render_midi.py

The main CLI tool for converting MIDI and XGML files to audio.

### Basic Usage

```bash
# Render MIDI file to audio (default: OGG format)
render_midi.py input.mid

# Render with specific output format
render_midi.py input.mid output.wav

# Render XGML configuration file
render_midi.py config.xgml output.flac
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `input_files` | Input MIDI/XGML files (supports wildcards) | Required |
| `output` | Output file or directory | Auto-generated |
| `-c, --config` | Path to YAML configuration file | config.yaml |
| `--sf2` | SoundFont (.sf2) file paths | None |
| `--sample-rate` | Audio sample rate in Hz | 48000 |
| `--polyphony` | Maximum polyphony | 64 |
| `--volume` | Master volume (0.0 to 1.0) | 0.8 |
| `--format` | Output format (ogg, wav, mp3, flac, m4a, aac) | ogg |
| `--tempo` | Tempo ratio (1.0 = original) | 1.0 |
| `--silent` | Suppress console output | False |
| `--keyboard-abort` | Enable SPACE key to abort | False |
| `-r, --recursive` | Recurse into subdirectories | False |
| `--architecture` | Synthesizer architecture (legacy, voice) | legacy |
| `--synth` | Engine (modern, optimized) | modern |

### Examples

```bash
# Single file conversion
render_midi.py song.mid song.wav

# Multiple files with wildcards
render_midi.py *.mid output/

# With SoundFont
render_midi.py --sf2 piano.sf2 input.mid output.wav

# High-quality output
render_midi.py --sample-rate 96000 --format flac input.mid output.flac

# Recursive conversion
render_midi.py --recursive *.mid audio/

# With abort control
render_midi.py --keyboard-abort long_file.xgml output.ogg
```

---

## midi_to_xgml.py

Converts MIDI files to XGML (XG Markup Language) format.

### Basic Usage

```bash
# Convert MIDI to XGML
midi_to_xgml.py input.mid

# Specify output file
midi_to_xgml.py input.mid output.xgml

# Convert multiple files
midi_to_xgml.py *.mid --output-dir xgml/
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `input_files` | Input MIDI files (required) |
| `output` | Output XGML file or directory |
| `--output-dir, -d` | Output directory for multiple files |

### Output Format

The converter produces XGML files with:
- `basic_messages`: Program changes, controller settings
- `sequences`: Time-bound note events with timing

---

## Configuration File (config.yaml)

The `config.yaml` file controls synthesis parameters:

```yaml
# Sample rate (Hz)
sample_rate: 48000

# Chunk size in milliseconds
chunk_size_ms: 10.67

# Maximum polyphony
polyphony: 64

# Master volume (0.0 to 1.0)
volume: 0.8

# SoundFont files to load
sf2_files:
  - /path/to/piano.sf2
  - /path/to/strings.sf2
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `XG_SYNTH_SAMPLE_DIR` | Default sample directory |
| `XG_SYNTH_CACHE_DIR` | Cache directory |
| `XG_SYNTH_DEBUG` | Enable debug logging (1) |
| `XG_SYNTH_AUDIO_BACKEND` | Audio backend (portaudio) |

---

*Generated: 2026-02-20*
