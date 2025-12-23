# 🔧 Troubleshooting Guide - XG Synthesizer

This guide helps you resolve common issues and problems when using the XG Synthesizer. If you can't find a solution here, check the [GitHub Issues](https://github.com/roger/syxg/issues) or ask on [GitHub Discussions](https://github.com/roger/syxg/discussions).

## 📋 Quick Reference

### Most Common Issues
1. [No audio output](#no-audio-output)
2. [Import errors](#import-errors)
3. [MIDI file issues](#midi-file-problems)
4. [Performance problems](#performance-issues)
5. [XGML parsing errors](#xgml-configuration-issues)

### Emergency Fixes
```bash
# Quick diagnostic
python -c "from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer; print('Import successful')"

# Test basic functionality
render-midi --help

# Check audio setup
python -c "import sounddevice as sd; print('Audio devices:', len(sd.query_devices()))"
```

## 🔇 Audio Issues

### No Audio Output

#### Symptom
No sound when rendering MIDI files or using real-time synthesis.

#### Solutions

**1. Check Audio Device Configuration**
```bash
# List available audio devices
python -c "
import sounddevice as sd
devices = sd.query_devices()
for i, dev in enumerate(devices):
    print(f'{i}: {dev['name']} (in: {dev['max_input_channels']}, out: {dev['max_output_channels']})')
"

# Test basic audio output
python -c "
import sounddevice as sd
import numpy as np
sd.play(np.sin(2 * np.pi * 440 * np.arange(44100) / 44100) * 0.1, 44100)
sd.wait()
"
```

**2. Check Real-time Settings**
```python
# Ensure proper real-time configuration
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=512,  # Smaller buffer for lower latency
    real_time=True
)
```

**3. Verify File Output**
```bash
# Check if files are being created
render-midi input.mid output.wav
ls -la output.wav

# Test file playback with different tools
ffplay output.wav    # FFmpeg
aplay output.wav     # ALSA (Linux)
afplay output.wav    # macOS
start output.wav     # Windows
```

**4. Environment Variables**
```bash
# Set audio backend explicitly
export SDL_AUDIODRIVER=alsa     # Linux
export AUDIODEV=hw:0,0          # Linux ALSA device
# or
export SDL_AUDIODRIVER=coreaudio # macOS
```

#### Advanced Debugging
```python
# Detailed audio diagnostics
import sounddevice as sd
import numpy as np

print("Default device info:")
print(sd.query_devices(sd.default.device))

print("Testing audio callback...")
def callback(outdata, frames, time, status):
    if status:
        print(f"Audio callback status: {status}")
    outdata[:] = np.random.randn(frames, 2) * 0.1

try:
    with sd.OutputStream(callback=callback, channels=2):
        input("Press Enter to stop...")
except Exception as e:
    print(f"Audio error: {e}")
```

### Audio Crackling or Distortion

#### Symptom
Intermittent crackling, popping, or distorted audio during playback.

#### Causes and Solutions

**1. Buffer Size Issues**
```python
# Increase buffer size for stability
synth = ModernXGSynthesizer(
    buffer_size=2048,  # Larger buffer reduces CPU load
    sample_rate=44100
)

# For real-time, find optimal buffer size
for buffer_size in [256, 512, 1024, 2048]:
    synth = ModernXGSynthesizer(buffer_size=buffer_size, real_time=True)
    # Test for crackling at each size
```

**2. Sample Rate Mismatch**
```python
# Ensure consistent sample rates
synth = ModernXGSynthesizer(sample_rate=44100)

# Check input file sample rate
import librosa
audio, sr = librosa.load('your_sample.wav')
print(f"Sample rate: {sr}")  # Should match synthesizer rate
```

**3. CPU Overload**
```python
# Monitor CPU usage
import psutil
import time

synth = ModernXGSynthesizer()
synth.load_xgml_config("complex_config.xgdsl")

for i in range(10):
    start = time.time()
    audio = synth.generate_audio(1024)
    end = time.time()
    cpu_percent = psutil.cpu_percent()
    print(f"Block {i}: {(end-start)*1000:.1f}ms, CPU: {cpu_percent}%")
```

**4. Memory Issues**
```python
# Check available memory
import psutil
memory = psutil.virtual_memory()
print(f"Available memory: {memory.available / 1024 / 1024:.1f} MB")

# Use memory-efficient settings
from synth.audio.sample_manager import PyAVSampleManager
sample_manager = PyAVSampleManager(max_cache_size_mb=256)  # Reduce cache
```

### Volume Issues

#### Symptom
Audio is too quiet, too loud, or clipping occurs.

#### Solutions

**1. Normalization Settings**
```python
# Enable/disable normalization
synth.render_midi_file(
    "input.mid",
    "output.wav",
    normalize=True,   # Prevent clipping
    peak_level=0.9    # Leave headroom
)
```

**2. Manual Level Adjustment**
```python
import numpy as np

# Adjust audio levels programmatically
audio = synth.generate_audio(44100)

# Normalize to prevent clipping
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = audio / max_val * 0.9  # 90% of max level

# Apply gain
gain_db = 6.0  # +6dB boost
gain_linear = 10 ** (gain_db / 20)
audio = audio * gain_linear
```

**3. XGML Volume Control**
```yaml
# Adjust volume in XGML
basic_messages:
  channels:
    channel_1:
      volume: 100      # 0-127, 100 = 0dB
      expression: 127  # Additional volume control

effects_configuration:
  master_processing:
    equalizer:
      bands:
        low: {gain: 3.0}  # Boost low end
```

## 🐍 Import and Installation Issues

### Import Errors

#### Symptom
`ImportError` or `ModuleNotFoundError` when importing XG Synthesizer modules.

#### Solutions

**1. Check Installation**
```bash
# Verify installation
pip list | grep xg

# Reinstall if needed
pip uninstall xg-synthesizer
pip install -e .
```

**2. Python Path Issues**
```python
# Check Python path
import sys
print("Python path:")
for path in sys.path:
    print(f"  {path}")

# Add current directory to path
import os
sys.path.insert(0, os.path.abspath('.'))
```

**3. Virtual Environment Issues**
```bash
# Check which Python is being used
which python
which python3

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Verify packages are in venv
pip list
```

**4. Dependency Conflicts**
```bash
# Check for conflicting packages
pip check

# Update problematic packages
pip install --upgrade numpy scipy

# Install in isolated environment
python -m venv clean_env
source clean_env/bin/activate
pip install -e .
```

### Version Compatibility

#### Symptom
Code works in one environment but fails in another.

#### Solutions

**1. Check Versions**
```python
# Check all relevant versions
import sys
print(f"Python: {sys.version}")

import numpy as np
print(f"NumPy: {np.__version__}")

import scipy
print(f"SciPy: {scipy.__version__}")

# Check XG Synthesizer version
from synth import __version__
print(f"XG Synthesizer: {__version__}")
```

**2. Environment Isolation**
```bash
# Create reproducible environment
python -m venv xg_env
source xg_env/bin/activate

# Install with specific versions
pip install numpy==1.21.0 scipy==1.7.0
pip install -e .
```

## 🎼 MIDI File Problems

### File Not Recognized

#### Symptom
MIDI file cannot be loaded or parsed.

#### Solutions

**1. Validate MIDI File**
```python
# Check MIDI file structure
import mido

try:
    mid = mido.MidiFile('your_file.mid')
    print(f"Format: {mid.type}")
    print(f"Tracks: {len(mid.tracks)}")
    print(f"TPB: {mid.ticks_per_beat}")

    for i, track in enumerate(mid.tracks):
        print(f"Track {i}: {len(track)} messages")
        for msg in track[:5]:  # First 5 messages
            print(f"  {msg}")

except Exception as e:
    print(f"MIDI error: {e}")
```

**2. Convert MIDI Format**
```python
# Convert between MIDI formats if needed
import mido

# Load and save as different format
mid = mido.MidiFile('input.mid')
mid.save('output.mid', format=mid.type)  # Preserve format
# or
mid.save('output_format0.mid', format=0)  # Convert to format 0
```

**3. Clean MIDI Data**
```python
# Remove problematic MIDI events
mid = mido.MidiFile('problematic.mid')

for track in mid.tracks:
    # Remove sysex and meta messages that might cause issues
    track[:] = [msg for msg in track
                if msg.type in ['note_on', 'note_off', 'control_change',
                               'program_change', 'pitch_bend']]

mid.save('clean.mid')
```

### Timing Issues

#### Symptom
MIDI playback has wrong tempo or timing.

#### Solutions

**1. Check Tempo Settings**
```python
# Analyze MIDI tempo
mid = mido.MidiFile('your_file.mid')

for track in mid.tracks:
    for msg in track:
        if msg.type == 'set_tempo':
            tempo_bpm = mido.tempo2bpm(msg.tempo)
            print(f"Tempo: {tempo_bpm} BPM")

# Set tempo explicitly
synth.set_tempo(120)  # 120 BPM
```

**2. Time Signature Issues**
```python
# Check time signature
for track in mid.tracks:
    for msg in track:
        if msg.type == 'time_signature':
            print(f"Time signature: {msg.numerator}/{msg.denominator}")
```

### Note Range Issues

#### Symptom
Some notes don't play or sound wrong.

#### Solutions

**1. Check Note Range**
```python
# Analyze note range in MIDI file
notes = []

for track in mid.tracks:
    for msg in track:
        if msg.type in ['note_on', 'note_off']:
            notes.append(msg.note)

if notes:
    print(f"Note range: {min(notes)} - {max(notes)}")
    print(f"Total notes: {len(notes)}")
```

**2. Transpose Notes**
```python
# Transpose MIDI notes
semitones = 12  # Up one octave

for track in mid.tracks:
    for msg in track:
        if msg.type in ['note_on', 'note_off']:
            msg.note = min(127, max(0, msg.note + semitones))

mid.save('transposed.mid')
```

## ⚙️ XGML Configuration Issues

### Parsing Errors

#### Symptom
XGML file fails to load with parsing errors.

#### Solutions

**1. Validate YAML Syntax**
```bash
# Use YAML validator
python -c "
import yaml
try:
    with open('your_config.xgdsl', 'r') as f:
        config = yaml.safe_load(f)
    print('YAML syntax is valid')
    print(f'Keys: {list(config.keys())}')
except yaml.YAMLError as e:
    print(f'YAML error: {e}')
"
```

**2. Check XGML Structure**
```python
# Validate XGML structure
from synth.xgml.parser import XGMLParser

parser = XGMLParser()
document = parser.parse_file('your_config.xgdsl')

if parser.has_errors():
    print("XGML Errors:")
    for error in parser.get_errors():
        print(f"  {error}")

if parser.has_warnings():
    print("XGML Warnings:")
    for warning in parser.get_warnings():
        print(f"  {warning}")
```

**3. Common XGML Mistakes**
```yaml
# ❌ Wrong: Missing required sections
xg_dsl_version: "2.1"
# No basic_messages section!

# ✅ Correct: Include required sections
xg_dsl_version: "2.1"
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
```

### Schema Validation Errors

#### Symptom
Configuration loads but doesn't work as expected.

#### Solutions

**1. Use Schema Validation**
```python
# Validate against XGML schema
import jsonschema
import yaml

# Load schema
with open('docs/xgml_schema.yaml', 'r') as f:
    schema = yaml.safe_load(f)

# Load and validate config
with open('your_config.xgdsl', 'r') as f:
    config = yaml.safe_load(f)

try:
    jsonschema.validate(config, schema)
    print("Configuration is valid")
except jsonschema.ValidationError as e:
    print(f"Schema validation error: {e.message}")
    print(f"Path: {e.absolute_path}")
```

**2. Parameter Range Checks**
```yaml
# Check parameter ranges
valid_ranges = {
    'volume': (0, 127),
    'pan': (-100, 100),
    'reverb_send': (0, 127),
    'chorus_send': (0, 127)
}

for param, (min_val, max_val) in valid_ranges.items():
    if param in config:
        value = config[param]
        if not (min_val <= value <= max_val):
            print(f"Parameter {param}={value} out of range [{min_val}, {max_val}]")
```

## 🚀 Performance Issues

### High CPU Usage

#### Symptom
Synthesizer uses too much CPU, causing system slowdown.

#### Solutions

**1. Optimize Settings**
```python
# Use performance-optimized settings
synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=2048,  # Larger buffer = less CPU interrupts
    max_polyphony=64,  # Limit simultaneous voices
    enable_optimization=True
)
```

**2. Profile Performance**
```python
import cProfile
import pstats

# Profile rendering
pr = cProfile.Profile()
pr.enable()

audio = synth.render_midi_file("input.mid", "output.wav")

pr.disable()
ps = pstats.Stats(pr).sort_stats('cumulative')
ps.print_stats(20)  # Top 20 time-consuming functions
```

**3. Use Efficient Engines**
```yaml
# Prefer CPU-efficient engines
synthesis_engines:
  default_engine: "sf2"    # Sample playback = low CPU
  part_engines:
    part_0: "sf2"          # Drums
    part_1: "additive"     # Simple bass
    # Avoid: FM-X for polyphonic parts
```

### Memory Issues

#### Symptom
Out of memory errors or excessive memory usage.

#### Solutions

**1. Monitor Memory Usage**
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Memory usage: {memory_mb:.1f} MB")
```

**2. Optimize Sample Loading**
```python
# Use memory-efficient sample management
from synth.audio.sample_manager import PyAVSampleManager

sample_manager = PyAVSampleManager(
    max_cache_size_mb=512,     # Limit cache size
    preload_priority=False,    # Don't preload all samples
    compression_enabled=True   # Compress cached samples
)

synth.set_sample_manager(sample_manager)
```

**3. Stream Large Files**
```python
# For very large MIDI files, process in chunks
chunk_size = 10 * 60  # 10 minutes

# Process file in segments
for start_time in range(0, total_duration, chunk_size):
    end_time = min(start_time + chunk_size, total_duration)

    # Render chunk
    audio_chunk = synth.render_time_range(
        midi_file="large_file.mid",
        start_time=start_time,
        end_time=end_time
    )

    # Save or process chunk
    # ...
```

### Latency Issues

#### Symptom
High latency in real-time playback.

#### Solutions

**1. Optimize Buffer Settings**
```python
# Find optimal buffer size for your system
for buffer_size in [64, 128, 256, 512, 1024]:
    synth = ModernXGSynthesizer(
        buffer_size=buffer_size,
        real_time=True
    )

    # Measure round-trip latency
    # Choose smallest buffer without xruns
```

**2. Use Appropriate Sample Rate**
```python
# Higher sample rates can reduce latency
synth = ModernXGSynthesizer(
    sample_rate=96000,  # Higher sample rate
    buffer_size=128     # Smaller buffer
)
```

## 🔧 Advanced Debugging

### Logging Configuration

```python
# Enable detailed logging
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xg_synth_debug.log'),
        logging.StreamHandler()
    ]
)

# Enable XG Synthesizer debug logging
logger = logging.getLogger('synth')
logger.setLevel(logging.DEBUG)
```

### Core Dump Analysis

```python
# Generate core dump on crash (Linux)
import os
os.environ['PYTHONFAULTHANDLER'] = '1'

# Or use faulthandler
import faulthandler
faulthandler.enable(file=open('crash.log', 'w'))
```

### Performance Profiling

```python
# Detailed performance profiling
import cProfile
import io
import pstats

pr = cProfile.Profile()
pr.enable()

# Your code here
audio = synth.generate_audio(44100)

pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats()
print(s.getvalue())
```

## 📞 Getting Help

### Before Asking for Help

**1. Gather Information**
```bash
# System information
uname -a                    # Linux
systeminfo                  # Windows
sw_vers                     # macOS

# Python environment
python --version
pip list

# XG Synthesizer info
python -c "from synth import __version__; print(__version__)"
```

**2. Minimal Test Case**
Create the smallest possible example that reproduces your issue:

```python
# minimal_test.py
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

synth = ModernXGSynthesizer()
audio = synth.generate_note_audio(60, 100, 1.0)  # C4, 1 second
print(f"Generated {len(audio)} samples")
```

### Community Support

- **GitHub Issues**: [Report bugs](https://github.com/roger/syxg/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/roger/syxg/discussions)
- **Stack Overflow**: Tag with `xg-synthesizer` and `python`

### Commercial Support

For commercial support, enterprise features, or custom development:
- Contact: [support@xg-synth.dev](mailto:support@xg-synth.dev)
- Enterprise licensing available

---

**🔧 This troubleshooting guide covers the most common XG Synthesizer issues. For additional help, don't hesitate to ask the community!**
