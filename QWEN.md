# XG Synthesizer Project

## Project Overview

This project is a complete MIDI to OGG converter with a built-in XG-compatible software synthesizer. It's designed to convert MIDI files into high-quality audio by rendering them using a sophisticated synthesis engine that supports the Yamaha XG standard.

The synthesizer features a channel-based architecture using persistent `XGChannelRenderer` instances for improved performance and resource management. It also supports multi-port MIDI rendering, allowing you to handle multiple simultaneous MIDI streams.

### Core Components

1.  **XG Synthesizer (`xg_synthesizer.py`)**: The main synthesis engine, implementing the Yamaha XG standard. It manages multiple "Channel Renderers", handles all standard MIDI messages (including SysEx), generates audio in blocks, and applies effects. Supports multiple MIDI ports for handling multiple simultaneous MIDI streams.
2.  **Channel Renderer (`tg.py`)**: Contains the `XGChannelRenderer` class which is a persistent per-channel renderer that manages notes for its channel. It supports advanced features like multiple LFOs, an ADSR envelope, a resonant filter, a modulation matrix, and the "Partial Structure" concept from XG for complex timbres. It uses wavetable data provided by the `Sf2WavetableManager`.
3.  **SoundFont Wavetable Manager (`sf2.py`)**: Loads and parses SoundFont 2.0 (.sf2) files to provide wavetable data, envelopes, filters, and modulation information to the Channel Renderers. It supports loading multiple SF2 files, blacklists for banks/presets, and bank mapping. It implements lazy loading and caching of samples. **Enhanced to correctly handle generators and modulators as part of preset definition according to the SoundFont standard.**
4.  **Effect Manager (`fx.py`)**: Implements a wide range of audio effects in line with the XG standard, including Reverb, Chorus, Insertion Effects (per channel), and Variation Effects (global). It handles effect parameters via NRPN, SysEx, and a direct API.
5.  **MIDI to OGG Converter (`midi_to_ogg.py`)**: The main command-line utility script. It uses `mido` to parse MIDI files and the `XGSynthesizer` to generate audio, which is then saved as OGG using `opuslib`.
6.  **Configuration (`config.yaml`)**: A YAML file for configuring the synthesizer's audio settings (sample rate, block size, polyphony) and specifying SoundFont files to load.

## Building and Running

1.  **Dependencies**: Ensure you have Python 3.x installed. Install the required Python packages:
    ```bash
    pip install mido pyyaml numpy opuslib
    ```
2.  **SoundFonts**: You need at least one SoundFont (.sf2) file. Update the `config.yaml` file to point to your SF2 file(s).
3.  **Running the Converter**:
    ```bash
    python midi_to_ogg.py input.mid output.ogg
    ```
    You can also specify options directly on the command line:
    ```bash
    python midi_to_ogg.py --sf2 my_soundfont.sf2 --sample-rate 48000 input.mid output.ogg
    ```
    Run `python midi_to_ogg.py -h` for a full list of options.

## Development Conventions

*   **Language**: Python 3.x
*   **File Encoding**: UTF-8
*   **Typing**: Heavy use of Python type hints (`typing` module) for clarity and robustness.
*   **Style**: Follows PEP 8 style guidelines (use a linter like `flake8`).
*   **Structure**:
    *   Each major component is in its own file (`xg_synthesizer.py`, `tg.py`, `sf2.py`, `fx.py`).
    *   The main entry point is `midi_to_ogg.py`.
    *   Configuration is externalized in `config.yaml`.
*   **MIDI Compatibility**: Strives for full compatibility with the Yamaha XG standard, including handling of SysEx, NRPN, and specific controller messages.
*   **Modularity**: Components are designed to be relatively independent. The `XGSynthesizer` orchestrates `Sf2WavetableManager`, `XGChannelRenderer`s, and `XGEffectManager`.
*   **Performance**: Uses NumPy for audio processing and implements caching (`Sf2WavetableManager`) to handle large SoundFonts efficiently. Uses a channel-based architecture with persistent renderers for improved performance. Supports multi-port MIDI rendering for handling multiple simultaneous MIDI streams.
*   **SoundFont Standard Compliance**: The `Sf2WavetableManager` correctly implements the SoundFont 2.0 standard for handling preset-level generators and modulators, allowing presets to define default values that instruments can override.

## Current Implementation Status

The project currently implements:
- Full MIDI XG synthesizer with Channel Renderers and Effects Manager
- Support for SoundFont 2.0 files with proper handling of generators and modulators
- Multiple LFOs, modulation matrix, and Partial Structure concepts
- System and Insertion Effects with NRPN/SysEx control
- Drum note mapping and parameter control
- Channel-based architecture with persistent renderers for improved performance
- Multi-port MIDI rendering support

## Multi-Port MIDI Rendering

The XG Synthesizer now supports multi-port MIDI rendering:

- **Configurable Ports**: Specify the number of MIDI ports when creating the synthesizer (default is 2)
- **Scalable Channels**: Each port supports 16 MIDI channels, so 2 ports = 32 channels, 4 ports = 64 channels, etc.
- **Independent Processing**: Each port's channels are processed independently
- **Port-Specific Messages**: Send MIDI messages to specific ports using the `send_midi_message_to_port()` method
- **Drum Channel Per Port**: Each port has its own drum channel (channel 10, 0-indexed as channel 9)

## Planned Enhancements

We're currently working on implementing full MIDI XG part mode selection and control, including:
- Part-specific effects processing
- Part EQ controls
- Enhanced NRPN parameter handling for part-specific settings
- Improved SysEx message processing for XG parameters

These enhancements will allow for more detailed control over individual MIDI parts/channels, enabling users to set unique effects and EQ settings for each part of their composition.