# 🔧 XG Synthesizer API Reference

This section provides comprehensive API documentation for the XG Synthesizer, including all public classes, methods, and functions.

## 📋 API Architecture

The XG Synthesizer API is organized into several key modules:

- **`synth.engine`** - Core synthesis engines and main synthesizer
- **`synth.xgml`** - XGML configuration language parser and translator
- **`synth.effects`** - Audio effects processing
- **`synth.midi`** - MIDI processing and file handling
- **`synth.audio`** - Audio I/O and sample management
- **`synth.core`** - Core utilities and base classes

## 🎹 Main Synthesizer API

### ModernXGSynthesizer

The main synthesizer class providing high-level control over all XG workstation synthesis features, including XG specification compliance, GS compatibility, MPE support, and advanced workstation capabilities.

#### Constructor

```python
ModernXGSynthesizer(
    sample_rate: int = 44100,
    max_channels: int = 32,
    xg_enabled: bool = True,
    gs_enabled: bool = True,
    mpe_enabled: bool = True,
    device_id: int = 0x10,
    gs_mode: str = 'auto',
    s90_mode: bool = False
)
```

**Parameters:**
- `sample_rate` (int): Audio sample rate in Hz (default: 44100)
- `max_channels` (int): Maximum MIDI channels (default: 32, expanded for S90/S70 compatibility)
- `xg_enabled` (bool): Enable XG specification features (default: True)
- `gs_enabled` (bool): Enable GS compatibility mode (default: True)
- `mpe_enabled` (bool): Enable MPE (Microtonal Pitch Expression) support (default: True)
- `device_id` (int): MIDI device ID for XG/GS/MPE (default: 0x10)
- `gs_mode` (str): GS/XG mode selection - 'xg', 'gs', or 'auto' (default: 'auto')
- `s90_mode` (bool): Enable S90/S70 workstation compatibility features (default: False)

#### Core Methods

##### Audio Generation

```python
def render_midi_file(
    self,
    midi_file: Union[str, Path],
    output_file: Union[str, Path],
    sample_rate: Optional[int] = None,
    normalize: bool = True,
    bit_depth: int = 16,
    metadata: Optional[Dict[str, str]] = None
) -> bool
```

Renders a MIDI file to audio.

**Parameters:**
- `midi_file` (str/Path): Input MIDI file path
- `output_file` (str/Path): Output audio file path
- `sample_rate` (int, optional): Output sample rate (uses instance rate if None)
- `normalize` (bool): Normalize audio to prevent clipping (default: True)
- `bit_depth` (int): Output bit depth (16 or 24, default: 16)
- `metadata` (dict, optional): Audio file metadata

**Returns:** bool - True if rendering succeeded

```python
def generate_audio(self, num_samples: int) -> np.ndarray
```

Generates audio samples for current MIDI state.

**Parameters:**
- `num_samples` (int): Number of samples to generate

**Returns:** numpy.ndarray - Stereo audio array of shape (num_samples, 2)

```python
def generate_note_audio(
    self,
    note: int,
    velocity: int,
    duration: float,
    channel: int = 0
) -> np.ndarray
```

Generates audio for a single note.

**Parameters:**
- `note` (int): MIDI note number (0-127)
- `velocity` (int): Note velocity (0-127)
- `duration` (float): Note duration in seconds
- `channel` (int): MIDI channel (0-15, default: 0)

**Returns:** numpy.ndarray - Stereo audio array

##### MIDI Control

```python
def note_on(self, channel: int, note: int, velocity: int) -> None
```

Triggers a note-on event.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `note` (int): MIDI note number (0-127)
- `velocity` (int): Note velocity (0-127)

```python
def note_off(self, channel: int, note: int, velocity: int = 64) -> None
```

Triggers a note-off event.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `note` (int): MIDI note number (0-127)
- `velocity` (int, optional): Note-off velocity (default: 64)

```python
def control_change(self, channel: int, controller: int, value: int) -> None
```

Sends a MIDI control change message.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `controller` (int): Controller number (0-127)
- `value` (int): Controller value (0-127)

```python
def pitch_bend(self, channel: int, value: int) -> None
```

Sends a MIDI pitch bend message.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `value` (int): Pitch bend value (-8192 to 8191)

##### Configuration

```python
def load_xgml_config(self, config_path: Union[str, Path]) -> bool
```

Loads XGML configuration from file.

**Parameters:**
- `config_path` (str/Path): Path to XGML configuration file

**Returns:** bool - True if loading succeeded

```python
def load_xgml_string(self, config_string: str) -> bool
```

Loads XGML configuration from string.

**Parameters:**
- `config_string` (str): XGML configuration as YAML string

**Returns:** bool - True if loading succeeded

```python
def set_engine_for_part(self, part: int, engine: str) -> bool
```

Sets the synthesis engine for a specific part.

**Parameters:**
- `part` (int): Part number (0-15)
- `engine` (str): Engine name ("sf2", "sfz", "fm", etc.)

**Returns:** bool - True if engine was set successfully

##### SoundFont Management

```python
def load_soundfont(self, sf2_path: Union[str, Path], bank: int = 0) -> bool
```

Loads a SoundFont 2.0 file.

**Parameters:**
- `sf2_path` (str/Path): Path to SoundFont file
- `bank` (int): Bank number to load presets into (default: 0)

**Returns:** bool - True if loading succeeded

```python
def select_preset(self, bank: int, program: int, channel: int = 0) -> None
```

Selects a preset for a MIDI channel.

**Parameters:**
- `bank` (int): Bank number (0-127)
- `program` (int): Program number (0-127)
- `channel` (int): MIDI channel (0-15, default: 0)

##### Effects Control

```python
def set_reverb_parameters(self, **params) -> None
```

Sets system reverb parameters.

**Parameters:**
- `type` (int): Reverb type (0-12)
- `time` (float): Reverb time in seconds
- `level` (float): Wet/dry mix (0.0-1.0)
- Additional parameters vary by reverb type

```python
def set_chorus_parameters(self, **params) -> None
```

Sets system chorus parameters.

**Parameters:**
- `type` (int): Chorus type (0-5)
- `rate` (float): LFO rate in Hz
- `depth` (float): Modulation depth (0.0-1.0)
- `feedback` (float): Feedback amount (-1.0 to 1.0)

##### Advanced Audio Processing

```python
def generate_audio_block(self, block_size: Optional[int] = None) -> np.ndarray
```

Generates audio block with buffered MIDI message processing support.

**Parameters:**
- `block_size` (int, optional): Samples to generate (uses default if None)

**Returns:** numpy.ndarray - Stereo audio array

```python
def generate_audio_block_sample_accurate(self) -> np.ndarray
```

Generates audio block with true sample-perfect MIDI message processing.

**Returns:** numpy.ndarray - Stereo audio array

```python
def send_midi_message_block(self, messages: List[Any]) -> None
```

Send block of MIDI messages for buffered processing.

**Parameters:**
- `messages` (List): MIDI message list

##### XG System Methods

```python
def set_xg_reverb_type(self, reverb_type: int) -> bool
```

Set XG reverb type.

**Parameters:**
- `reverb_type` (int): Reverb type (0-12)

**Returns:** bool - Success status

```python
def set_xg_chorus_type(self, chorus_type: int) -> bool
```

Set XG chorus type.

**Parameters:**
- `chorus_type` (int): Chorus type (0-17)

**Returns:** bool - Success status

```python
def set_xg_variation_type(self, variation_type: int) -> bool
```

Set XG variation type.

**Parameters:**
- `variation_type` (int): Variation type (0-45)

**Returns:** bool - Success status

```python
def set_drum_kit(self, channel: int, kit_number: int) -> bool
```

Set drum kit for channel.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `kit_number` (int): Drum kit number

**Returns:** bool - Success status

```python
def apply_temperament(self, temperament_name: str) -> bool
```

Apply musical temperament.

**Parameters:**
- `temperament_name` (str): Temperament name

**Returns:** bool - Success status

```python
def get_xg_compliance_report(self) -> Dict[str, Any]
```

Get XG compliance report.

**Returns:** dict - Compliance information

##### GS System Methods

```python
def set_gs_mode(self, mode: str) -> None
```

Set GS/XG mode.

**Parameters:**
- `mode` (str): Mode ('xg', 'gs', 'auto')

```python
def get_gs_system_info(self) -> Dict[str, Any]
```

Get GS system information.

**Returns:** dict - GS system status

```python
def set_gs_part_parameter(self, part_number: int, param_id: int, value: int) -> bool
```

Set GS part parameter.

**Parameters:**
- `part_number` (int): Part number (0-15)
- `param_id` (int): Parameter ID
- `value` (int): Parameter value

**Returns:** bool - Success status

```python
def reset_gs_system(self) -> None
```

Reset GS system to defaults.

##### MPE System Methods

```python
def get_mpe_info(self) -> Dict[str, Any]
```

Get MPE system information.

**Returns:** dict - MPE status and zones

```python
def set_mpe_enabled(self, enabled: bool) -> None
```

Enable or disable MPE.

**Parameters:**
- `enabled` (bool): MPE enabled state

```python
def reset_mpe(self) -> None
```

Reset MPE system.

##### XGML v3.0 Integration

```python
def load_xgml_config(self, xgml_path: Union[str, Path]) -> bool
```

Load XGML v3.0 configuration from file.

**Parameters:**
- `xgml_path` (str/Path): XGML file path

**Returns:** bool - Success status

```python
def load_xgml_string(self, xgml_string: str) -> bool
```

Load XGML v3.0 configuration from string.

**Parameters:**
- `xgml_string` (str): XGML YAML string

**Returns:** bool - Success status

```python
def enable_config_hot_reloading(self, watch_paths: Optional[List[Union[str, Path]]] = None, check_interval: float = 1.0) -> bool
```

Enable configuration hot-reloading.

**Parameters:**
- `watch_paths` (List, optional): Paths to watch
- `check_interval` (float): Check interval in seconds

**Returns:** bool - Success status

```python
def disable_config_hot_reloading(self) -> bool
```

Disable configuration hot-reloading.

**Returns:** bool - Success status

```python
def get_hot_reload_status(self) -> Dict[str, Any]
```

Get hot-reloading status.

**Returns:** dict - Reload status information

```python
def trigger_manual_config_reload(self, path: Optional[Union[str, Path]] = None) -> bool
```

Manually trigger configuration reload.

**Parameters:**
- `path` (str/Path, optional): Specific path to reload

**Returns:** bool - Success status

##### Engine & Sound Management

```python
def load_soundfont(self, sf2_path: str) -> None
```

Load SoundFont file.

**Parameters:**
- `sf2_path` (str): SoundFont file path

```python
def set_channel_program(self, channel: int, bank: int, program: int) -> None
```

Set program for MIDI channel.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `bank` (int): Bank number (0-127)
- `program` (int): Program number (0-127)

```python
def get_channel_info(self, channel: int) -> Optional[Dict[str, Any]]
```

Get channel information.

**Parameters:**
- `channel` (int): MIDI channel (0-15)

**Returns:** dict - Channel information or None

```python
def get_synthesizer_info(self) -> Dict[str, Any]
```

Get comprehensive synthesizer information.

**Returns:** dict - System information

##### System Management

```python
def reset(self) -> None
```

Reset synthesizer to clean state.

```python
def cleanup(self) -> None
```

Clean up all resources.

```python
def set_master_volume(self, volume: float) -> None
```

Set master volume.

**Parameters:**
- `volume` (float): Volume (0.0-1.0)

```python
def finalize_audio_logging(self) -> None
```

Finalize audio logging.

##### Receive Channel Management

```python
def set_receive_channel(self, part_id: int, midi_channel: int) -> bool
```

Set XG receive channel for part.

**Parameters:**
- `part_id` (int): XG part ID (0-15)
- `midi_channel` (int): MIDI channel (0-15, 254=OFF, 255=ALL)

**Returns:** bool - Success status

```python
def get_receive_channel(self, part_id: int) -> Optional[int]
```

Get XG receive channel for part.

**Parameters:**
- `part_id` (int): XG part ID (0-15)

**Returns:** int - MIDI channel or None

```python
def get_parts_for_midi_channel(self, midi_channel: int) -> List[int]
```

Get parts receiving from MIDI channel.

**Parameters:**
- `midi_channel` (int): MIDI channel (0-15)

**Returns:** List[int] - Part IDs

```python
def reset_receive_channels(self) -> None
```

Reset receive channels to XG defaults.

```python
def get_receive_channel_mapping(self) -> Dict[str, Any]
```

Get receive channel mapping status.

**Returns:** dict - Channel mapping information

#### Attributes

```python
sample_rate: int        # Current sample rate in Hz (read-only after initialization)
max_channels: int       # Maximum MIDI channels (32 for S90/S70 compatibility)
xg_enabled: bool        # XG system enabled (read-only after initialization)
gs_enabled: bool        # GS system enabled (read-only after initialization)
mpe_enabled: bool       # MPE system enabled (read-only after initialization)
device_id: int          # MIDI device ID (0x10, read-only after initialization)
gs_mode: str            # GS/XG mode ('auto', 'xg', 'gs')
s90_mode: bool          # S90/S70 compatibility mode (read-only after initialization)
```

## 🎼 XGML API

### XGMLParser

Parses XGML YAML documents into structured configuration objects.

#### Constructor

```python
XGMLParser()
```

#### Methods

```python
def parse_file(self, file_path: Union[str, Path]) -> Optional[XGMLDocument]
```

Parses XGML from file.

**Parameters:**
- `file_path` (str/Path): Path to XGML file

**Returns:** XGMLDocument or None if parsing failed

```python
def parse_string(self, yaml_string: str) -> Optional[XGMLDocument]
```

Parses XGML from string.

**Parameters:**
- `yaml_string` (str): XGML content as YAML string

**Returns:** XGMLDocument or None if parsing failed

```python
def get_errors(self) -> List[str]
```

Returns parsing error messages.

**Returns:** List[str] - Error messages

```python
def get_warnings(self) -> List[str]
```

Returns parsing warning messages.

**Returns:** List[str] - Warning messages

### XGMLDocument

Represents a parsed XGML document.

#### Methods

```python
def has_section(self, section_name: str) -> bool
```

Checks if document contains a specific section.

**Parameters:**
- `section_name` (str): Section name to check

**Returns:** bool - True if section exists

```python
def get_section(self, section_name: str) -> Optional[Any]
```

Retrieves a configuration section.

**Parameters:**
- `section_name` (str): Section name to retrieve

**Returns:** Section data or None if not found

```python
def get_sections(self) -> List[str]
```

Returns list of all available sections.

**Returns:** List[str] - Section names

#### Properties

```python
version: str  # XGML version (e.g., "2.1")
description: str  # Optional document description
timestamp: Optional[str]  # ISO timestamp
```

### XGMLToMIDITranslator

Translates XGML documents to MIDI message sequences.

#### Constructor

```python
XGMLToMIDITranslator()
```

#### Methods

```python
def translate_document(self, xgml_document: XGMLDocument) -> List[MIDIMessage]
```

Translates complete XGML document to MIDI messages.

**Parameters:**
- `xgml_document` (XGMLDocument): Parsed XGML document

**Returns:** List[MIDIMessage] - MIDI message sequence

```python
def get_errors(self) -> List[str]
```

Returns translation error messages.

**Returns:** List[str] - Error messages

```python
def get_warnings(self) -> List[str]
```

Returns translation warning messages.

**Returns:** List[str] - Warning messages

## 🎛️ Effects API

### EffectsCoordinator

Manages audio effects processing chain.

#### Constructor

```python
EffectsCoordinator(sample_rate: int = 44100)
```

**Parameters:**
- `sample_rate` (int): Audio sample rate in Hz

#### Methods

```python
def add_system_reverb(self, **params) -> None
```

Adds XG system reverb effect.

**Parameters:** Reverb parameters (type, time, level, etc.)

```python
def add_system_chorus(self, **params) -> None
```

Adds XG system chorus effect.

**Parameters:** Chorus parameters (type, rate, depth, etc.)

```python
def add_variation_effect(self, effect_type: int, **params) -> None
```

Adds XG variation effect.

**Parameters:**
- `effect_type` (int): Variation effect type (0-62)
- `**params`: Effect-specific parameters

```python
def add_insertion_effect(self, channel: int, slot: int, effect_type: int, **params) -> None
```

Adds per-channel insertion effect.

**Parameters:**
- `channel` (int): MIDI channel (0-15)
- `slot` (int): Insertion slot (0-2)
- `effect_type` (int): Insertion effect type (0-17)
- `**params`: Effect-specific parameters

```python
def process_audio(self, audio: np.ndarray) -> np.ndarray
```

Processes audio through effects chain.

**Parameters:**
- `audio` (numpy.ndarray): Stereo audio array

**Returns:** numpy.ndarray - Processed audio

## 🎵 MIDI API

### MIDI Processing

```python
from synth.midi.parser import MIDIMessage, MIDIParser

# Create MIDI parser
parser = MIDIParser()

# Parse MIDI file
messages = parser.parse_file("input.mid")

# Process messages
for msg in messages:
    print(f"{msg.time}: {msg.type} on channel {msg.channel}")
```

### MIDIMessage

Represents a MIDI message.

#### Properties

```python
type: str  # Message type ("note_on", "note_off", "control_change", etc.)
channel: int  # MIDI channel (0-15)
time: float  # Timestamp in seconds
note: Optional[int]  # Note number (0-127) for note messages
velocity: Optional[int]  # Velocity (0-127) for note messages
controller: Optional[int]  # Controller number for CC messages
value: Optional[int]  # Controller value for CC messages
program: Optional[int]  # Program number for program change
```

## 🔊 Audio API

### Sample Management

```python
from synth.audio.sample_manager import PyAVSampleManager

# Create sample manager
manager = PyAVSampleManager(max_cache_size_mb=512)

# Load sample
sample = manager.load_sample("audio_file.wav")

# Get sample info
print(f"Sample rate: {sample.sample_rate}")
print(f"Channels: {sample.channels}")
print(f"Duration: {sample.duration}s")
```

### Audio Conversion

```python
from synth.audio.converter import AudioConverter

# Create converter
converter = AudioConverter()

# Convert audio format
converter.convert_audio(
    input_file="input.flac",
    output_file="output.wav",
    sample_rate=44100,
    bit_depth=16
)
```

## 🎚️ Engine APIs

### SynthesisEngine (Base Class)

All synthesis engines inherit from this base class.

#### Methods

```python
def generate_samples(
    self,
    note: int,
    velocity: int,
    modulation: Dict[str, float],
    block_size: int
) -> np.ndarray
```

Generates audio samples for a note.

**Parameters:**
- `note` (int): MIDI note number
- `velocity` (int): Note velocity
- `modulation` (dict): Current modulation values
- `block_size` (int): Samples to generate

**Returns:** numpy.ndarray - Audio samples

```python
def note_on(self, note: int, velocity: int) -> None
```

Handles note-on event.

```python
def note_off(self, note: int) -> None
```

Handles note-off event.

```python
def is_active(self) -> bool
```

Returns whether engine has active voices.

**Returns:** bool - True if voices are active

### SF2Engine

SoundFont 2.0 synthesis engine.

#### Constructor

```python
SF2Engine(sample_rate: int = 44100, max_polyphony: int = 256)
```

#### Methods

```python
def load_soundfont(self, sf2_path: Union[str, Path]) -> bool
```

Loads SoundFont file.

```python
def select_preset(self, bank: int, program: int) -> None
```

Selects preset for playback.

### SFZEngine

SFZ sample format engine.

#### Constructor

```python
SFZEngine(sample_rate: int = 44100, max_polyphony: int = 256)
```

#### Methods

```python
def load_instrument(self, sfz_path: Union[str, Path]) -> bool
```

Loads SFZ instrument.

```python
def set_global_parameter(self, param: str, value: Any) -> None
```

Sets global SFZ parameter.

### FMEngine

FM synthesis engine.

#### Constructor

```python
FMEngine(sample_rate: int = 44100, num_operators: int = 8)
```

#### Methods

```python
def set_algorithm(self, algorithm: int) -> None
```

Sets FM algorithm (0-87).

```python
def configure_operator(self, op_index: int, **params) -> None
```

Configures FM operator parameters.

### PhysicalEngine

Physical modeling synthesis engine.

#### Constructor

```python
PhysicalEngine(sample_rate: int = 44100, model_type: str = "string")
```

#### Methods

```python
def set_model_parameters(self, **params) -> None
```

Sets physical model parameters.

### SpectralEngine

Spectral processing engine.

#### Constructor

```python
SpectralEngine(sample_rate: int = 44100, mode: str = "filter")
```

#### Methods

```python
def set_fft_parameters(self, fft_size: int, hop_size: int) -> None
```

Configures FFT analysis parameters.

```python
def set_spectral_parameters(self, **params) -> None
```

Sets spectral processing parameters.

## 🛠️ Utility APIs

### Configuration Management

```python
from synth.core.config import XGConfig

# Load configuration
config = XGConfig.load_from_file("~/.xg_synth/config.yaml")

# Get settings
sample_rate = config.get("audio.sample_rate", 44100)
max_polyphony = config.get("synthesis.max_polyphony", 256)

# Save configuration
config.save_to_file("~/.xg_synth/config.yaml")
```

### Performance Monitoring

```python
from synth.core.performance import PerformanceMonitor

# Create monitor
monitor = PerformanceMonitor()

# Enable monitoring
monitor.start()

# Get stats
stats = monitor.get_stats()
print(f"CPU: {stats['cpu_percent']}%")
print(f"Memory: {stats['memory_mb']} MB")
print(f"Latency: {stats['avg_latency_ms']} ms")

# Stop monitoring
monitor.stop()
```

### Logging

```python
import logging
from synth.core.logging import setup_logging

# Setup logging
setup_logging(level=logging.DEBUG, log_file="xg_synth.log")

# Use logger
logger = logging.getLogger("xg_synth")
logger.info("Synthesizer initialized")
logger.debug("Sample rate: 44100 Hz")
```

## 📊 Data Types

### Audio Formats

```python
# Audio buffer
audio: np.ndarray  # Shape: (num_samples, num_channels), dtype: float32

# Sample data
sample = {
    "data": np.ndarray,      # Audio data
    "sample_rate": int,      # Sample rate in Hz
    "channels": int,         # Number of channels
    "bit_depth": int,        # Bit depth
    "duration": float        # Duration in seconds
}
```

### MIDI Events

```python
# MIDI message types
midi_message = {
    "type": str,             # "note_on", "note_off", "control_change", etc.
    "channel": int,          # MIDI channel (0-15)
    "time": float,           # Timestamp in seconds
    # Type-specific fields
    "note": int,             # For note messages (0-127)
    "velocity": int,         # For note messages (0-127)
    "controller": int,       # For CC messages (0-127)
    "value": int,            # For CC messages (0-127)
    "program": int           # For program change (0-127)
}
```

### XGML Configuration

```python
# XGML document structure
xgml_document = {
    "xg_dsl_version": str,       # Version (e.g., "2.1")
    "description": str,          # Optional description
    "timestamp": str,            # ISO timestamp
    # Configuration sections
    "basic_messages": dict,      # MIDI messages
    "effects_configuration": dict,  # Effects setup
    "fm_x_engine": dict,         # FM-X configuration
    "sfz_engine": dict,          # SFZ configuration
    # ... other sections
}
```

## 🚨 Error Handling

### Exception Types

```python
from synth.core.exceptions import (
    XGError,                    # Base exception
    AudioError,                 # Audio processing errors
    MIDIError,                  # MIDI processing errors
    XGMLError,                  # XGML parsing errors
    EngineError,                # Synthesis engine errors
    ConfigurationError          # Configuration errors
)

try:
    synth.render_midi_file("input.mid", "output.wav")
except AudioError as e:
    print(f"Audio error: {e}")
except MIDIError as e:
    print(f"MIDI error: {e}")
except XGError as e:
    print(f"XG error: {e}")
```

### Error Checking

```python
# Check for errors after operations
if not synth.render_midi_file("input.mid", "output.wav"):
    errors = synth.get_errors()
    for error in errors:
        print(f"Error: {error}")

# XGML parsing errors
parser = XGMLParser()
document = parser.parse_file("config.xgdsl")

if parser.has_errors():
    for error in parser.get_errors():
        print(f"Parse error: {error}")

if parser.has_warnings():
    for warning in parser.get_warnings():
        print(f"Parse warning: {warning}")
```

---

**🔧 This API reference covers the complete XG Synthesizer public interface. For examples and tutorials, see the [Examples](../examples/) section.**
