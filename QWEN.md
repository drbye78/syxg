# XG Synthesizer Project

## Project Overview

This project is a complete MIDI to MP3 converter with a built-in XG-compatible software synthesizer. It's designed to convert MIDI files into high-quality audio by rendering them using a sophisticated synthesis engine that supports the Yamaha XG standard.

### Core Components

1.  **XG Synthesizer (`xg_synthesizer.py`)**: The main synthesis engine, implementing the Yamaha XG standard. It manages multiple "Tone Generators", handles all standard MIDI messages (including SysEx), generates audio in blocks, and applies effects.
2.  **Tone Generator (`tg.py`)**: Responsible for generating audio for individual notes. It supports advanced features like multiple LFOs, an ADSR envelope, a resonant filter, a modulation matrix, and the "Partial Structure" concept from XG for complex timbres. It uses wavetable data provided by the `Sf2WavetableManager`.
3.  **SoundFont Wavetable Manager (`sf2.py`)**: Loads and parses SoundFont 2.0 (.sf2) files to provide wavetable data, envelopes, filters, and modulation information to the Tone Generators. It supports loading multiple SF2 files, blacklists for banks/presets, and bank mapping. It implements lazy loading and caching of samples. **Enhanced to correctly handle generators and modulators as part of preset definition according to the SoundFont standard.**
4.  **Effect Manager (`fx.py`)**: Implements a wide range of audio effects in line with the XG standard, including Reverb, Chorus, Insertion Effects (per channel), and Variation Effects (global). It handles effect parameters via NRPN, SysEx, and a direct API.
5.  **MIDI to MP3 Converter (`midi_to_mp3.py`)**: The main command-line utility script. It uses `mido` to parse MIDI files and the `XGSynthesizer` to generate audio, which is then saved as WAV and optionally converted to MP3 using `pydub`.
6.  **Configuration (`config.yaml`)**: A YAML file for configuring the synthesizer's audio settings (sample rate, block size, polyphony) and specifying SoundFont files to load.

## Building and Running

1.  **Dependencies**: Ensure you have Python 3.x installed. Install the required Python packages:
    ```bash
    pip install mido pydub pyyaml numpy
    ```
2.  **SoundFonts**: You need at least one SoundFont (.sf2) file. Update the `config.yaml` file to point to your SF2 file(s).
3.  **Running the Converter**:
    ```bash
    python midi_to_mp3.py input.mid output.mp3
    ```
    You can also specify options directly on the command line:
    ```bash
    python midi_to_mp3.py --sf2 my_soundfont.sf2 --sample-rate 48000 input.mid output.mp3
    ```
    Run `python midi_to_mp3.py -h` for a full list of options.

## Development Conventions

*   **Language**: Python 3.x
*   **File Encoding**: UTF-8
*   **Typing**: Heavy use of Python type hints (`typing` module) for clarity and robustness.
*   **Style**: Follows PEP 8 style guidelines (use a linter like `flake8`).
*   **Structure**:
    *   Each major component is in its own file (`xg_synthesizer.py`, `tg.py`, `sf2.py`, `fx.py`).
    *   The main entry point is `midi_to_mp3.py`.
    *   Configuration is externalized in `config.yaml`.
*   **MIDI Compatibility**: Strives for full compatibility with the Yamaha XG standard, including handling of SysEx, NRPN, and specific controller messages.
*   **Modularity**: Components are designed to be relatively independent. The `XGSynthesizer` orchestrates `Sf2WavetableManager`, `XGToneGenerator`s, and `XGEffectManager`.
*   **Performance**: Uses NumPy for audio processing and implements caching (`Sf2WavetableManager`) to handle large SoundFonts efficiently.
*   **SoundFont Standard Compliance**: The `Sf2WavetableManager` now correctly implements the SoundFont 2.0 standard for handling preset-level generators and modulators, allowing presets to define default values that instruments can override.