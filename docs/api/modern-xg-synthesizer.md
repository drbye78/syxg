# ModernXGSynthesizer API Reference

Complete API reference for the ModernXGSynthesizer class.

## Constructor

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| sample_rate | int | 44100 | Audio sample rate in Hz |
| max_channels | int | 32 | Maximum MIDI channels |
| xg_enabled | bool | True | Enable XG features |
| gs_enabled | bool | True | Enable GS features |
| mpe_enabled | bool | True | Enable MPE features |
| device_id | int | 0x10 | XG/GS device ID |
| gs_mode | str | 'auto' | Mode: 'xg', 'gs', or 'auto' |
| s90_mode | bool | False | S90/S70 compatibility |

## Core Methods

### Audio Generation

#### `generate_audio_block(block_size: int) -> np.ndarray`
Generate audio block with buffered MIDI message processing.

```python
audio = synth.generate_audio_block(1024)
# Returns: np.ndarray with shape (block_size, 2)
```

#### `generate_audio_block_sample_accurate() -> np.ndarray`
Generate audio with true sample-perfect MIDI timing.

```python
audio = synth.generate_audio_block_sample_accurate()
```

### MIDI Processing

#### `process_midi_message(message_bytes: bytes)`
Process raw MIDI message bytes.

```python
import mido
msg = mido.Message('note_on', channel=0, note=60, velocity=100)
synth.process_midi_message(msg.bytes())
```

#### `send_midi_message_block(messages: List)`
Send block of MIDI messages for buffered processing.

```python
messages = [msg1, msg2, msg3]  # List of MIDIMessage objects
synth.send_midi_message_block(messages)
```

### Program Control

#### `set_channel_program(channel: int, bank: int, program: int)`
Set program for a channel.

```python
synth.set_channel_program(channel=0, bank=0, program=0)  # Acoustic Piano
```

#### `load_soundfont(sf2_path: str)`
Load SoundFont file.

```python
synth.load_soundfont("path/to/piano.sf2")
```

### Information

#### `get_synthesizer_info() -> Dict`
Get comprehensive synthesizer information.

```python
info = synth.get_synthesizer_info()
# Returns: {
#   'sample_rate': 44100,
#   'max_channels': 32,
#   'engines': {...},
#   'effects_enabled': True,
#   'performance': {...}
# }
```

#### `get_channel_info(channel: int) -> Optional[Dict]`
Get information about a specific channel.

```python
info = synth.get_channel_info(0)
```

### Playback Control

#### `rewind()`
Reset playback position to beginning.

```python
synth.rewind()
```

#### `set_current_time(time: float)`
Set current playback time in seconds.

```python
synth.set_current_time(5.0)  # Jump to 5 seconds
```

#### `get_current_time() -> float`
Get current playback time.

```python
current = synth.get_current_time()
```

#### `get_total_duration() -> float`
Get total duration of buffered sequence.

```python
duration = synth.get_total_duration()
```

### Control

#### `reset()`
Reset synthesizer to default state.

```python
synth.reset()
```

#### `cleanup()`
Clean up all resources.

```python
synth.cleanup()
```

## XG-Specific Methods

### Effects

```python
synth.set_xg_reverb_type(type: int)
synth.set_xg_chorus_type(type: int)
synth.set_xg_variation_type(type: int)
```

### Drum Kits

```python
synth.set_drum_kit(channel: int, kit_number: int)
```

### Tuning

```python
synth.apply_temperament(temperament_name: str)
synth.set_compatibility_mode(mode: str)
```

### Channel Routing

```python
synth.set_receive_channel(part_id: int, midi_channel: int)
synth.get_receive_channel(part_id: int) -> Optional[int]
synth.get_parts_for_midi_channel(midi_channel: int) -> List[int]
synth.reset_receive_channels()
```

## MPE Methods

```python
synth.set_mpe_enabled(enabled: bool)
synth.get_mpe_info() -> Dict
synth.reset_mpe()
```

## GS Methods

```python
synth.set_gs_mode(mode: str)
synth.get_gs_system_info() -> Dict
synth.set_gs_part_parameter(part_number: int, param_id: int, value: int) -> bool
synth.reset_gs_system()
```

## Configuration

### Hot Reloading

```python
synth.enable_config_hot_reloading(watch_paths, check_interval) -> bool
synth.disable_config_hot_reloading() -> bool
synth.add_hot_reload_watch_path(path) -> bool
synth.remove_hot_reload_watch_path(path) -> bool
synth.get_hot_reload_status() -> Dict
synth.trigger_manual_config_reload(path) -> bool
```

### XGML Configuration

```python
synth.load_xgml_config(path: Union[str, Path]) -> bool
synth.load_xgml_string(xgml_string: str) -> bool
synth.get_xgml_config_template() -> str
synth.create_xgml_config_from_current_state() -> Optional[str]
```

## Constants

### Sample Rates
- 22050 Hz
- 44100 Hz (default)
- 48000 Hz
- 96000 Hz

### Engine Names
- 'sf2' - SoundFont 2.0
- 'sfz' - SFZ format
- 'fm' - FM synthesis
- 'additive' - Additive synthesis
- 'wavetable' - Wavetable synthesis
- 'physical' - Physical modeling
- 'granular' - Granular synthesis
- 'spectral' - Spectral processing

---

*Generated: 2026-02-20*
