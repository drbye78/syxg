# SYXG Project Overview

This project implements a comprehensive MIDI XG-compatible synthesizer in Python. It consists of three main modules:

1.  **`fx.py`**: Implements a complete XG effects manager with support for system effects (reverb, chorus), insertion effects, and variation effects.
2.  **`sf2.py`**: Provides a SoundFont 2.0 wavetable manager for loading and managing samples from SF2 files.
3.  **`tg.py`**: Contains the core tone generator implementing the XG standard with support for partial structures, multiple LFOs, modulation matrix, and full MIDI controller/RPN/NRPN/SysEx handling.

## Key Features

### Tone Generation (`tg.py`)

*   **Partial Structure**: Implements the XG concept of "Partial Structure", allowing complex timbres composed of multiple "partials".
*   **Multi-LFO Support**: Up to 3 LFOs per voice with customizable waveforms, rates, depths, and delays.
*   **Advanced Envelopes**: ADSR envelopes for amplitude, filter, and pitch with velocity sensitivity and key scaling.
*   **Resonant Filter**: Configurable lowpass, bandpass, and highpass filters with resonance and key following.
*   **Modulation Matrix**: A 16-slot modulation matrix supporting various sources (LFOs, envelopes, controllers) and destinations (pitch, filter, amplitude, etc.).
*   **Full MIDI Compatibility**: Handles Note On/Off, Controller Change, Pitch Bend, Aftertouch (Channel and Key), Program Change, RPN, NRPN, and SysEx messages according to the XG standard.
*   **XG-Specific Features**: Supports SAME NOTE KEY ON ASSIGN, portamento, vibrato, tremolo, detune, scale tuning, and drum mode with standard XG drum note mapping.
*   **Stereo Processing**: Includes stereo panning and width control.

### Effects (`fx.py`)

*   **Insertion Effects**: Per-channel effects like Distortion, Overdrive, Compressor, Phaser, Flanger, etc.
*   **System Effects**: Reverb and Chorus with multiple types and parameters.
*   **Variation Effects**: A wide range of effects including delays, modulation effects, and spectral processors.
*   **Equalizer**: 3-band parametric equalizer.
*   **Routing and Mixing**: Configurable effect routing and send levels.
*   **MIDI Control**: Full control via NRPN and SysEx messages as per XG specification.

### Wavetable Management (`sf2.py`)

*   **SoundFont 2.0 Parsing**: Reads and parses SF2 files, including presets, instruments, zones, generators, modulators, and samples.
*   **Lazy Loading and Caching**: Loads samples on demand and caches them for performance.
*   **Modulator Interpretation**: Interprets SF2 modulators and converts them to a format usable by the tone generator's modulation matrix.
*   **Parameter Conversion**: Converts SF2 generator parameters to the tone generator's internal representation.

## Building and Running

This project is written in Python and requires no compilation.

### Dependencies

The project uses standard Python libraries and `numpy`. You can install numpy using pip:

```bash
pip install numpy
```

### Running

The project consists of modules that would typically be imported and used by a main application or sequencer. There are no standalone executable scripts provided in these files.

Example usage would involve:

1.  Creating a `Sf2WavetableManager` instance to load a SoundFont file.
2.  Creating an `XGToneGenerator` instance, passing the wavetable manager.
3.  Sending MIDI messages (Note On/Off, controllers, etc.) to the tone generator.
4.  Calling the tone generator's `generate_sample()` method in a loop to produce audio output.
5.  Feeding the audio output through the `XGEffectManager` for effects processing.

### Testing

No specific test files or commands are included in the provided codebase.

## Development Conventions

*   **Code Style**: The code follows PEP 8 style guidelines, using descriptive variable and function names.
*   **Documentation**: Classes and functions are documented with detailed docstrings explaining their purpose, arguments, and return values.
*   **Modularity**: The code is well-organized into distinct modules (`fx.py`, `sf2.py`, `tg.py`) with clear responsibilities.
*   **XG Compliance**: Implementation closely follows the Yamaha XG specification for parameters, NRPN/RPN mappings, and behavior.