# XG Synthesizer

High-performance MIDI XG (eXtended General MIDI) synthesizer implemented in Python with optimized vectorized processing. This synthesizer provides full XG specification compliance with performance optimizations using NumPy and Numba.

## Features

- Full XG specification compliance
- Vectorized audio processing for maximum performance
- Support for SoundFont (.sf2) files
- Advanced system effects (reverb, chorus, variation, equalizer)
- Insertion effects per channel
- Optimized for real-time MIDI rendering
- 8 partials per note (extended from XG standard of 4)
- Comprehensive modulation matrix

## Requirements

- Python 3.8+
- NumPy for vectorized operations
- SciPy for optimized signal processing (when available)
- SoundFont (SF2) file for samples

## Installation

To install the XG synthesizer and its dependencies:

```bash
pip install -r requirements.txt
```

Or install directly from the repository:

```bash
pip install .
```

For development mode:

```bash
pip install -e .[dev]
```

## Usage

To convert a MIDI file to audio:

```bash
python render_midi.py input.mid
```

With custom SoundFont and parameters:

```bash
python render_midi.py --sf2 path/to/soundfont.sf2 --sample-rate 48000 input.mid output.wav
```

More options can be viewed with:

```bash
python render_midi.py --help
```

## Performance Optimizations

The synthesizer includes several performance optimizations:

- Vectorized equalizer processing using scipy's lfilter when available
- Pre-allocated memory pools for audio buffers
- Numba JIT compilation for critical audio processing loops
- Zero-allocation audio processing where possible
- Efficient block-based processing for MIDI events

## Configuration

The synthesizer can be configured using the `config.yaml` file:

- `sample_rate`: Audio output sample rate (default: 48000 Hz)
- `chunk_size_ms`: Processing chunk size in milliseconds (default: 512 samples / 48000 Hz)
- `max_polyphony`: Maximum simultaneous voices (default: 512)
- `volume`: Master volume level (default: 0.8)
- `sf2_files`: List of SoundFont files to load

## Architecture

- `synth/engine/`: Core synthesizer engine with vectorized processing
- `synth/effects/`: System and insertion effects processing
- `synth/xg/`: XG specification implementation
- `synth/sf2/`: SoundFont file processing
- `synth/core/`: Core synthesis components (oscillators, envelopes, filters)
- `synth/midi/`: MIDI parsing and processing