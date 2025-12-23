# 🚀 Installation Guide - XG Synthesizer

This guide covers installing and setting up the XG Synthesizer on different platforms.

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB
- **Disk Space**: 1GB for installation + sample storage
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)

### Recommended Requirements
- **Python**: 3.9 or higher
- **RAM**: 8GB or more
- **Disk Space**: 10GB+ SSD for optimal performance
- **CPU**: Multi-core processor with AVX2 support

### Optional Dependencies
- **Audio Processing**: FFmpeg for additional audio format support
- **Performance**: Numba for JIT compilation acceleration
- **Visualization**: Matplotlib for audio analysis plots

## 🐧 Linux Installation

### Ubuntu/Debian

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install audio libraries (optional but recommended)
sudo apt install ffmpeg libsndfile1 -y

# Install PortAudio for real-time audio (optional)
sudo apt install portaudio19-dev -y

# Clone and install XG Synthesizer
git clone https://github.com/roger/syxg.git
cd syxg
pip3 install -e .
```

### CentOS/RHEL/Fedora

```bash
# Install Python
sudo dnf install python3 python3-pip -y  # Fedora/CentOS 8+
# OR
sudo yum install python3 python3-pip -y  # CentOS 7

# Install audio libraries
sudo dnf install ffmpeg ffmpeg-devel -y

# Clone and install
git clone https://github.com/roger/syxg.git
cd syxg
pip3 install -e .
```

### Arch Linux

```bash
# Install Python and audio libraries
sudo pacman -S python python-pip ffmpeg

# Clone and install
git clone https://github.com/roger/syxg.git
cd syxg
pip install -e .
```

## 🍎 macOS Installation

### Using Homebrew (Recommended)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.9

# Install audio libraries
brew install ffmpeg

# Clone and install XG Synthesizer
git clone https://github.com/roger/syxg.git
cd syxg
pip3 install -e .
```

### Using MacPorts

```bash
# Install MacPorts from https://www.macports.org/

# Install Python and audio libraries
sudo port install python39 py39-pip ffmpeg

# Clone and install
git clone https://github.com/roger/syxg.git
cd syxg
pip-3.9 install -e .
```

## 🪟 Windows Installation

### Method 1: Using Python from python.org (Recommended)

1. **Download Python**
   - Go to https://www.python.org/downloads/
   - Download Python 3.9 or later
   - Run the installer
   - **Important**: Check "Add Python to PATH" during installation

2. **Install Git**
   - Download from https://git-scm.com/download/win
   - Install with default settings

3. **Install FFmpeg (Optional but recommended)**
   - Download from https://ffmpeg.org/download.html#builds
   - Add to system PATH

4. **Install XG Synthesizer**
   ```cmd
   git clone https://github.com/roger/syxg.git
   cd syxg
   pip install -e .
   ```

### Method 2: Using Anaconda/Miniconda

```cmd
# Install Miniconda from https://docs.conda.io/en/latest/miniconda.html

# Create environment
conda create -n xg-synth python=3.9
conda activate xg-synth

# Clone and install
git clone https://github.com/roger/syxg.git
cd syxg
pip install -e .
```

## 🐳 Docker Installation

### Using Pre-built Image

```bash
# Pull the image
docker pull roger/xg-synthesizer:latest

# Run container
docker run -it --rm \
  -v $(pwd):/workspace \
  roger/xg-synthesizer:latest \
  render-midi input.mid output.wav
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/roger/syxg.git
cd syxg

# Build Docker image
docker build -t xg-synthesizer .

# Run container
docker run -it --rm \
  -v $(pwd):/workspace \
  xg-synthesizer \
  render-midi input.mid output.wav
```

## 📦 Advanced Installation Options

### Development Installation

```bash
# Clone repository
git clone https://github.com/roger/syxg.git
cd syxg

# Install with development dependencies
pip install -e ".[dev]"

# Install with all optional dependencies
pip install -e ".[dev,audio,performance,visualization]"

# Run tests to verify installation
pytest
```

### Optional Dependencies

```bash
# Audio processing (recommended)
pip install -e ".[audio]"
# Includes: pydub, librosa, soundfile, av

# Performance optimization
pip install -e ".[performance]"
# Includes: numba

# Visualization tools
pip install -e ".[visualization]"
# Includes: matplotlib, seaborn
```

### Installing from PyPI (Future)

```bash
# When available on PyPI
pip install xg-synthesizer

# With optional dependencies
pip install xg-synthesizer[audio,performance]
```

## ⚙️ Configuration

### Environment Variables

```bash
# Set sample directory
export XG_SYNTH_SAMPLE_DIR="/path/to/samples"

# Set cache directory
export XG_SYNTH_CACHE_DIR="/tmp/xg_cache"

# Enable debug logging
export XG_SYNTH_DEBUG=1

# Set audio backend
export XG_SYNTH_AUDIO_BACKEND="portaudio"
```

### Configuration Files

Create `~/.xg_synth/config.yaml`:

```yaml
# XG Synthesizer Configuration
sample_directories:
  - "/usr/share/sounds/sf2"
  - "~/samples"

cache:
  directory: "~/.cache/xg_synth"
  max_size_mb: 1024

audio:
  backend: "portaudio"
  sample_rate: 44100
  buffer_size: 1024

synthesis:
  default_engine: "sf2"
  max_polyphony: 256
  real_time: true
```

## 🧪 Testing Installation

### Basic Functionality Test

```python
# test_installation.py
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
import numpy as np

# Create synthesizer
synth = ModernXGSynthesizer()

# Generate test tone
audio = synth.generate_test_tone(frequency=440, duration=1.0)

# Save to file
import soundfile as sf
sf.write('test_tone.wav', audio, 44100)

print("✅ XG Synthesizer installed successfully!")
print(f"Generated {len(audio)} samples")
```

Run the test:
```bash
python test_installation.py
```

### Render MIDI Test

```bash
# Create a simple MIDI file for testing
echo "MIDI test file would go here" > test.mid

# Render with default settings
render-midi test.mid test_output.wav

# Check if output was created
ls -la test_output.wav
```

## 🔧 Troubleshooting

### Common Installation Issues

#### Python Version Issues
```bash
# Check Python version
python --version
python3 --version

# Use specific Python version
python3.9 -m pip install -e .
```

#### Permission Errors
```bash
# Install without root (Linux/macOS)
pip install --user -e .

# Or use virtual environment
python -m venv xg_env
source xg_env/bin/activate  # Linux/macOS
# xg_env\Scripts\activate    # Windows
pip install -e .
```

#### Missing Audio Libraries
```bash
# Linux
sudo apt install libportaudio2 portaudio19-dev

# macOS
brew install portaudio

# Windows - install from conda
conda install portaudio
```

#### FFmpeg Issues
```bash
# Check FFmpeg installation
ffmpeg -version

# Install FFmpeg
# Linux: sudo apt install ffmpeg
# macOS: brew install ffmpeg
# Windows: Download from https://ffmpeg.org/
```

### Performance Issues

#### High CPU Usage
```python
# Enable performance optimizations
import os
os.environ['NUMBA_DISABLE_JIT'] = '0'  # Enable JIT compilation

# Use optimized settings
synth = ModernXGSynthesizer(
    sample_rate=44100,
    buffer_size=2048,  # Larger buffer for less CPU
    enable_optimization=True
)
```

#### Memory Issues
```python
# Reduce sample cache size
from synth.audio.sample_manager import PyAVSampleManager
sample_manager = PyAVSampleManager(max_cache_size_mb=512)
```

### Audio Device Issues

#### No Audio Output
```bash
# List available audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Set specific device
export AUDIODEV=hw:0,0  # Linux
# or
export SDL_AUDIODRIVER=alsa  # Linux
```

## 📚 Next Steps

### Quick Start
1. **Test Installation**: Run the test script above
2. **Load Examples**: Check `examples/` directory
3. **Read Documentation**: Start with `docs/user/getting-started.md`

### Learning Resources
- **[User Guide](docs/user/user-guide.md)** - Complete usage guide
- **[XGML Reference](docs/XGML_README.md)** - Configuration language
- **[Examples](examples/)** - Working configurations
- **[API Reference](docs/api/)** - Developer documentation

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/roger/syxg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/roger/syxg/discussions)
- **Documentation**: [Full Docs](docs/)

---

**🎹 Installation complete! You're now ready to create professional audio with the XG Synthesizer.**
