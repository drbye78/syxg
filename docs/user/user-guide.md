# 📖 XG Synthesizer User Guide

This comprehensive guide covers all features and capabilities of the XG Synthesizer, from basic usage to advanced synthesis techniques.

## 🎯 Overview

The XG Synthesizer is a high-performance, vectorized MIDI synthesis engine that transforms MIDI files into professional-quality audio using multiple advanced synthesis techniques.

### Key Features

- **8 Synthesis Engines**: SF2, SFZ, FM-X, Additive, Wavetable, Physical Modeling, Granular, Spectral
- **Professional Effects**: XG-compatible reverb, chorus, delay, EQ, and dynamics processing
- **Advanced Control**: XGML configuration language, MPE support, arpeggiator, modulation matrix
- **Real-time Performance**: <5ms latency with optimized vectorized processing
- **Cross-platform**: Windows, macOS, Linux with identical functionality

## 🚀 Quick Start

If you're new to XG Synthesizer, start with the [Getting Started Guide](getting-started.md).

## 🎼 Synthesis Engines

### Overview

XG Synthesizer supports 8 different synthesis engines, each optimized for specific sound design tasks:

| Engine | Best For | Polyphony | CPU Usage |
|--------|----------|-----------|-----------|
| **SF2** | General MIDI, sampled instruments | 256+ | Low |
| **SFZ** | Professional sample libraries | 256+ | Low |
| **FM-X** | Bells, pads, leads, bass | 64 | Medium |
| **Additive** | Rich harmonics, evolving sounds | 32 | High |
| **Wavetable** | Dynamic timbres, evolving textures | 128 | Medium |
| **Physical** | Acoustic instruments, realism | 16 | High |
| **Granular** | Textures, ambient, experimental | 64 | High |
| **Spectral** | Vocals, processing, morphing | 32 | High |

### Engine Selection and Configuration

#### Basic Engine Selection

The ModernXGSynthesizer uses engines internally based on XG part configuration.
Engines are registered automatically. Use XGML configuration to select engines:

```python
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

# Create synthesizer - engines are auto-registered
synth = ModernXGSynthesizer(
    sample_rate=44100,
    xg_enabled=True,
    gs_enabled=True
)

# List available engines
info = synth.get_synthesizer_info()
print("Available engines:", info.get('engines', {}))
```

#### XGML Engine Configuration

```yaml
# engine_selection.xgdsl
xg_dsl_version: "2.1"

synthesis_engines:
  default_engine: "fm"          # Default for all parts
  part_engines:
    part_0: "fm"                # FM synthesis for leads
    part_1: "sfz"               # Sample playback for drums
    part_2: "physical"          # Physical modeling for acoustic
    part_3: "spectral"          # Spectral processing for effects

  engine_parameters:
    fm:
      algorithm: 1
      feedback: 0.3
    sfz:
      preload_samples: true
      max_polyphony: 128
```

### SF2 (SoundFont 2.0) Engine

Professional sample playback with velocity layers and crossfading.

```python
# Load SoundFont
synth.load_soundfont("path/to/soundfont.sf2")

# Configure preset using channel program
synth.set_channel_program(channel=0, bank=0, program=0)  # Piano

# Get channel info
info = synth.get_channel_info(0)
print(f"Channel 0 program: {info.get('program', 'N/A')}")
```

### SFZ Engine

Modern sample format with real-time modulation and region overrides.

```yaml
# SFZ configuration
sfz_engine:
  enabled: true
  instrument_path: "piano.sfz"

  global_parameters:
    volume: 0.0
    pan: 0.0
    tune: 0

  region_overrides:
    - lokey: 36, hikey: 72
      sample: "piano_C4.wav"
      volume: 6.0
      cutoff: 8000.0
      ampeg_attack: 0.01

  modulation_assignments:
    - source: "cc1"
      destination: "volume"
      amount: 50.0
      curve: "linear"
```

### FM-X Engine

8-operator FM synthesis with 88 algorithms and advanced modulation.

```yaml
fm_x_engine:
  enabled: true
  algorithm: 1                    # Algorithm selection (0-87)
  master_volume: 0.8

  operators:
    op_0:                         # Carrier operator
      frequency_ratio: 1.0
      feedback_level: 0
      envelope:
        levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
      scaling:
        key_depth: 0
        velocity_sensitivity: 0

  lfos:
    lfo_0:
      waveform: "sine"
      frequency: 1.0
      depth: 1.0

  modulation_matrix:
    - source: "lfo0"
      destination: "pitch"
      amount: 0.5
      bipolar: true
```

### Physical Modeling Engine

Waveguide synthesis and modal resonance for realistic acoustics.

```yaml
physical_engine:
  enabled: true
  model_type: "string"

  string_parameters:
    length: 0.65               # Physical dimensions
    tension: 150.0
    stiffness: 0.1
    damping: 0.001
    pluck_position: 0.1
    pickup_position: 0.2

  global_parameters:
    sample_rate: 44100
    oversampling: 2
```

### Spectral Processing Engine

FFT-based spectral processing with morphing and filtering.

```yaml
spectral_engine:
  enabled: true
  mode: "morph"

  fft_settings:
    fft_size: 2048
    window_type: "hann"

  morphing:
    source_a: "sound1.wav"
    source_b: "sound2.wav"
    morph_position: 0.5

  filtering:
    filter_type: "lowpass"
    cutoff_frequency: 1000.0
```

## 🎛️ Effects Processing

### System Effects

XG-compatible system effects applied globally:

```yaml
effects_configuration:
  system_effects:
    reverb:
      type: 4                # Hall 1
      time: 2.5              # Reverb time in seconds
      level: 0.8             # Wet/dry mix
      hf_damping: 0.3        # High frequency damping
      diffusion: 0.7         # Diffusion amount

    chorus:
      type: 1                # Chorus 1
      rate: 0.5              # LFO rate in Hz
      depth: 0.6             # Modulation depth
      feedback: 0.3          # Feedback amount
```

### Variation Effects

62+ effect types for creative processing:

```yaml
variation_effects:
  type: 12                   # Delay LCR
  parameters:
    delay_time: 300          # Delay time in ms
    feedback: 0.4            # Feedback amount
    level: 0.7               # Effect level
```

### Insertion Effects

Per-channel effects processing:

```yaml
insertion_effects:
  - channel: 0
    slot: 0
    type: 1                  # Stereo EQ
    parameters:
      low_gain: 2.0
      high_gain: -1.0
    bypass: false
```

### Master Processing

Final output processing chain:

```yaml
master_processing:
  equalizer:
    type: "jazz"             # Jazz EQ preset
    bands:
      low: {gain: 2.0, frequency: 80}
      mid: {gain: -1.5, frequency: 1000, q: 1.4}
      high: {gain: 0.5, frequency: 8000}

  limiter:
    threshold: -0.1          # Limiter threshold
    release: 100             # Release time in ms

  stereo_enhancement:
    width: 1.2               # Stereo width
```

## 🎚️ Advanced Control Systems

### XGML Configuration Language

Human-readable YAML-based configuration:

#### Basic MIDI Messages
```yaml
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      reverb_send: 40
      chorus_send: 20
```

#### RPN Parameters
```yaml
rpn_parameters:
  global:
    pitch_bend_range: 12      # ±12 semitones
    fine_tuning: 0            # 0 cents
  channel_1:
    pitch_bend_range: 24      # ±24 semitones
```

#### Channel Parameters
```yaml
channel_parameters:
  channel_1:
    filter:
      cutoff: 80
      resonance: 70
      envelope:
        attack: 90
        decay: 40
        sustain: 70
        release: 60
    lfo:
      lfo1:
        speed: 64
        pitch_depth: 50
```

### MPE (Microtonal Expression)

Per-note expression control:

```yaml
mpe_configuration:
  enabled: true
  zones:
    - zone_id: 1
      lower_channel: 0
      upper_channel: 7
      pitch_bend_range: 48    # ±48 semitones
      timbre_cc: 74           # Timbre control CC
  global_settings:
    pressure_active: true     # Per-note pressure
    slide_active: true        # Slide control
    lift_active: true         # Lift control
```

### Arpeggiator System

Pattern-based note generation:

```yaml
arpeggiator_configuration:
  enabled: true
  global_settings:
    tempo: 128
    swing: 0.2
    gate_time: 0.9

  patterns:
    - id: "up_pattern"
      name: "Simple Up"
      steps:
        - step: 0, note: 60, velocity: 100
        - step: 1, note: 64, velocity: 80
        - step: 2, note: 67, velocity: 90
      length: 3

  channel_assignments:
    - channel: 0
      pattern_id: "up_pattern"
      octave_range: 2
```

### Modulation Matrix

Advanced parameter routing:

```yaml
modulation_matrix:
  routes:
    - source: "velocity"
      destination: "filter_cutoff"
      amount: 0.7
      curve: "exponential"
    - source: "lfo1"
      destination: "pitch"
      amount: -0.2
      bipolar: true
    - source: "aftertouch"
      destination: "volume"
      amount: 0.5
```

## 🎹 MIDI Processing

### MIDI File Support

- **Format**: Standard MIDI File (SMF) format 0 and 1
- **Resolution**: 96-1920 PPQ supported
- **Tempo**: 30-300 BPM
- **Channels**: 1-16 (full XG specification)
- **Controllers**: All CC 0-127 supported

### Real-time MIDI

```python
# Real-time MIDI processing
import mido
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

synth = ModernXGSynthesizer(
    sample_rate=44100,
    xg_enabled=True,
    gs_enabled=True
)

# Set a program
synth.set_channel_program(channel=0, bank=0, program=0)

# MIDI event handling
def midi_callback(message):
    # Convert mido message to bytes and process
    synth.process_midi_message(message.bytes())

# Connect to MIDI input
midi_input = mido.open_input()
midi_input.callback = midi_callback
```

### MIDI Controllers

All standard controllers supported:

```python
# Controller mapping
controllers = {
    1: "modulation",          # CC 1
    7: "volume",              # CC 7
    10: "pan",                # CC 10
    11: "expression",         # CC 11
    64: "sustain",            # CC 64
    71: "harmonic_content",   # CC 71 - Filter resonance
    72: "release_time",       # CC 72
    73: "attack_time",        # CC 73
    74: "brightness"          # CC 74 - Filter cutoff
}
```

## 🔄 Audio Rendering

### Basic Rendering

```python
# Render MIDI file to audio
synth.render_midi_file(
    midi_file="input.mid",
    output_file="output.wav",
    sample_rate=44100,
    normalize=True
)
```

### Advanced Rendering Options

```python
# High-quality rendering
synth.render_midi_file(
    midi_file="input.mid",
    output_file="output.flac",
    sample_rate=96000,        # High sample rate
    bit_depth=24,             # High bit depth
    normalize=True,
    dither=True,              # Dither for bit depth reduction
    metadata={                # Add metadata
        "title": "My Composition",
        "artist": "Composer Name",
        "genre": "Classical"
    }
)
```

### Batch Processing

```python
import glob

# Process all MIDI files in directory
midi_files = glob.glob("midi_files/*.mid")
for midi_file in midi_files:
    output_file = midi_file.replace('.mid', '.wav')
    synth.render_midi_file(midi_file, output_file)
    print(f"Rendered {midi_file} -> {output_file}")
```

### Real-time Audio

```python
# Real-time audio output
import sounddevice as sd

synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=512,          # Low latency
    real_time=True
)

# Audio callback for real-time playback
def audio_callback(outdata, frames, time, status):
    if status:
        print(f"Audio callback status: {status}")

    # Generate audio for current MIDI state
    audio = synth.generate_audio(frames)
    outdata[:] = audio.reshape(-1, 2)  # Stereo

# Start real-time audio
with sd.OutputStream(
    samplerate=44100,
    channels=2,
    callback=audio_callback,
    blocksize=512
):
    print("Real-time audio started. Press Ctrl+C to stop.")
    input()  # Wait for user input
```

## ⚙️ Configuration and Optimization

### Performance Tuning

```python
# Optimized for performance
synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=2048,         # Larger buffer = less CPU
    max_polyphony=128,        # Limit polyphony
    enable_optimization=True, # Use optimized code paths
    num_threads=4             # Multi-threading
)
```

### Memory Management

```python
# Configure sample caching
from synth.audio.sample_manager import PyAVSampleManager

sample_manager = PyAVSampleManager(
    max_cache_size_mb=1024,   # 1GB cache
    preload_priority=True,    # Preload important samples
    compression_enabled=True  # Compress cached samples
)

synth.set_sample_manager(sample_manager)
```

### CPU Optimization

```python
# Enable all optimizations
import os
os.environ['NUMBA_DISABLE_JIT'] = '0'        # Enable JIT compilation
os.environ['XG_SYNTH_VECTORIZE'] = '1'      # Enable vectorization
os.environ['XG_SYNTH_OPENMP'] = '1'         # Enable OpenMP

synth = ModernXGSynthesizer(
    enable_simd=True,          # SIMD instructions
    enable_openmp=True,        # OpenMP parallelization
    cache_fft=True            # Cache FFT computations
)
```

## 🎵 Sound Design Techniques

### Layering Sounds

```yaml
# Layer multiple engines
synthesis_engines:
  part_engines:
    part_0: "sf2"            # Sampled piano
    part_1: "fm"             # FM enhancement
    part_2: "additive"       # Harmonic enhancement

fm_x_engine:
  enabled: true
  algorithm: 32             # Simple enhancement

additive_engine:
  enabled: true
  partials: 8               # 8 harmonics
  harmonic_distribution: "stretched"
```

### Creating Custom Sounds

```python
# Programmatic sound design
def create_custom_sound():
    # Configure FM algorithm
    synth.configure_fm_operator(0, {
        'frequency_ratio': 1.0,
        'envelope': {'attack': 0.1, 'decay': 0.3, 'sustain': 0.8, 'release': 1.0}
    })

    # Add chorus effect
    synth.set_effect_parameter('chorus', 'rate', 0.5)
    synth.set_effect_parameter('chorus', 'depth', 0.6)

    # Set modulation
    synth.add_modulation_route('velocity', 'filter_cutoff', 0.7)

create_custom_sound()
```

### Real-time Control

```python
# Real-time parameter control
def setup_real_time_control():
    # Map CC controllers to parameters
    synth.map_controller(1, 'modulation', 'lfo_depth')      # CC1 -> LFO depth
    synth.map_controller(7, 'volume', 'master_volume')      # CC7 -> Volume
    synth.map_controller(74, 'brightness', 'filter_cutoff') # CC74 -> Filter

    # Set modulation matrix
    synth.add_modulation_route('aftertouch', 'timbre', 0.8)

setup_real_time_control()
```

## 🔧 Troubleshooting

### Audio Issues

#### No Sound Output
```bash
# Check audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test basic audio
python -c "import sounddevice as sd; sd.play([0.1, 0.2], 44100); sd.wait()"
```

#### High Latency
```python
# Reduce latency
synth = ModernXGSynthesizer(
    buffer_size=128,          # Smaller buffer
    sample_rate=44100,
    real_time=True
)
```

### Performance Issues

#### High CPU Usage
```python
# Optimize settings
synth.set_max_polyphony(64)   # Reduce polyphony
synth.disable_effects()       # Disable effects if not needed
synth.set_sample_rate(22050)  # Lower sample rate for preview
```

#### Memory Problems
```python
# Reduce memory usage
sample_manager = PyAVSampleManager(max_cache_size_mb=256)
synth.set_sample_manager(sample_manager)
synth.disable_sample_preloading()
```

### Configuration Issues

#### XGML Validation Errors
```python
# Validate XGML before loading
from synth.xgml.parser import XGMLParser

parser = XGMLParser()
document = parser.parse_file("config.xgdsl")

if parser.has_errors():
    for error in parser.get_errors():
        print(f"Error: {error}")

if parser.has_warnings():
    for warning in parser.get_warnings():
        print(f"Warning: {warning}")
```

## 📚 Advanced Topics

### Custom Engine Development

```python
from synth.engine.synthesis_engine import SynthesisEngine

class CustomEngine(SynthesisEngine):
    def __init__(self, sample_rate=44100):
        super().__init__(sample_rate)
        self.custom_parameter = 0.5

    def generate_samples(self, note, velocity, modulation, block_size):
        # Custom synthesis algorithm
        # Return numpy array of shape (block_size, 2)
        pass

# Register custom engine
synth.register_engine('custom', CustomEngine)
synth.set_engine_for_part(0, 'custom')
```

### MIDI Scripting

```python
# Advanced MIDI processing
def process_midi_events(events):
    processed = []

    for event in events:
        if event.type == 'note_on':
            # Apply custom processing
            event.velocity = min(127, event.velocity * 1.2)  # Boost velocity

            # Add pitch bend
            bend_event = MIDIMessage(
                type='pitch_bend',
                channel=event.channel,
                value=256,  # Slight bend up
                time=event.time
            )
            processed.append(bend_event)

        processed.append(event)

    return processed
```

### Effect Chain Customization

```python
# Custom effect routing
def setup_custom_effects():
    # Bypass system effects
    synth.disable_system_effects()

    # Create custom effect chain
    synth.add_effect_to_chain('compressor', slot=0)
    synth.add_effect_to_chain('eq', slot=1)
    synth.add_effect_to_chain('reverb', slot=2)

    # Configure effect parameters
    synth.set_effect_parameter('compressor', 'ratio', 4.0)
    synth.set_effect_parameter('compressor', 'threshold', -12.0)

setup_custom_effects()
```

## 🔗 Integration Examples

### DAW Integration

```python
# VST/AU plugin interface (future)
class XGSynthPlugin:
    def __init__(self):
        self.synth = ModernXGSynthesizer(real_time=True)

    def process_block(self, inputs, outputs, block_size):
        # Process MIDI events
        midi_events = self.get_midi_events()
        for event in midi_events:
            self.process_midi_event(event)

        # Generate audio
        audio = self.synth.generate_audio(block_size)
        outputs[0][:] = audio[:, 0]  # Left channel
        outputs[1][:] = audio[:, 1]  # Right channel
```

### Web Integration

```python
# WebAssembly/Web Audio API (future)
import asyncio
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

async def web_audio_integration():
    synth = ModernXGSynthesizer(sample_rate=44100)

    # Web Audio API integration
    audio_context = await get_audio_context()

    # Create script processor node
    processor = audio_context.createScriptProcessor(2048, 0, 2)

    processor.onaudioprocess = lambda event:
        # Generate audio
        audio = synth.generate_audio(2048)

        # Copy to output buffers
        event.outputBuffer.getChannelData(0)[:] = audio[:, 0]
        event.outputBuffer.getChannelData(1)[:] = audio[:, 1]

    # Connect to audio graph
    processor.connect(audio_context.destination)
```

## 📊 Monitoring and Analysis

### Performance Monitoring

```python
# Enable performance monitoring
synth.enable_performance_monitoring()

# Get performance stats
stats = synth.get_performance_stats()
print(f"CPU Usage: {stats['cpu_percent']}%")
print(f"Memory Usage: {stats['memory_mb']} MB")
print(f"Active Voices: {stats['active_voices']}")
print(f"Average Latency: {stats['latency_ms']} ms")
```

### Audio Analysis

```python
# Enable audio analysis
synth.enable_audio_analysis()

# Get analysis data
analysis = synth.get_audio_analysis()
print(f"RMS Level: {analysis['rms_level']}")
print(f"Peak Level: {analysis['peak_level']}")
print(f"Spectral Centroid: {analysis['spectral_centroid']}")
print(f"Zero Crossing Rate: {analysis['zero_crossing_rate']}")
```

## 🎯 Best Practices

### Sound Design
1. **Start Simple**: Begin with basic patches and gradually add complexity
2. **Use Layering**: Combine multiple engines for rich sounds
3. **Balance Levels**: Use automation to control dynamics
4. **Optimize CPU**: Use appropriate polyphony limits

### Performance
1. **Buffer Size**: Balance latency vs. CPU usage
2. **Sample Rate**: Use 44100Hz for most applications
3. **Polyphony**: Set appropriate limits for your system
4. **Caching**: Enable sample caching for better performance

### Production
1. **Version Control**: Keep XGML files in version control
2. **Documentation**: Comment complex configurations
3. **Backup**: Regularly backup custom samples and configurations
4. **Testing**: Test renders at multiple quality levels

---

**🎹 This guide covers the complete XG Synthesizer feature set. For specific topics, see the [API Reference](../api/) and [Engine Documentation](../engines/).**
