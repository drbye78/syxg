# 🎹 XG Synthesizer - High-Performance MIDI Synthesis Engine

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-green.svg)](#)
[![Documentation](https://img.shields.io/badge/docs-complete-blue.svg)](#)

A **high-performance, vectorized XG (eXtended General MIDI) synthesizer** implemented in pure Python, featuring advanced synthesis engines, professional effects processing, and comprehensive MIDI control.

## ✨ Features

### 🎵 **Advanced Synthesis Engines**
- **SF2/SoundFont 2.0** - Professional sample playback with velocity layers
- **SFZ** - Modern sample format with real-time modulation
- **FM-X** - 8-operator FM synthesis with 88 algorithms
- **Additive** - Harmonic synthesis with custom spectra
- **Wavetable** - Dynamic wavetable synthesis
- **Physical Modeling** - Waveguide and modal synthesis
- **Granular** - Advanced granular processing
- **Spectral** - FFT-based spectral processing

### 🎛️ **Professional Effects Processing**
- **System Effects**: Reverb, Chorus, Delay with XG specifications
- **Variation Effects**: 62+ effect types including phaser, flanger, distortion
- **Insertion Effects**: Per-channel processing with 17 effect types
- **Master Processing**: 5-band EQ, stereo enhancement, limiter

### 🎚️ **Advanced Control Systems**
- **XGML v2.1** - Human-readable YAML configuration language
- **MPE Support** - Microtonal expression with per-note control
- **GS Compatibility** - Roland GS mode with JV-2080 enhancements
- **Arpeggiator** - Yamaha Motif-style pattern generation
- **Modulation Matrix** - 128 assignable modulation routings

### 🚀 **Performance & Architecture**
- **Vectorized Processing** - SIMD-optimized audio generation
- **Real-time Synthesis** - Low-latency performance (<5ms)
- **Multi-format Support** - WAV, AIFF, FLAC, OGG, MP3 samples
- **Cross-platform** - Windows, macOS, Linux support
- **Extensible Design** - Plugin architecture for custom engines

## 🚀 Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/roger/syxg.git
cd syxg
pip install -e .

# Or install with all optional dependencies
pip install -e ".[audio,performance,visualization]"
```

### Basic Usage

```python
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

# Create synthesizer
synth = ModernXGSynthesizer(sample_rate=44100)

# Load XGML configuration
synth.load_xgml_config("examples/simple_piano.xgdsl")

# Generate audio from MIDI
synth.render_midi_file("input.mid", "output.wav")
```

### Command Line

```bash
# Render MIDI file to audio
render-midi input.mid output.wav

# Convert MIDI to XGML
midi-to-xgml input.mid > config.xgdsl

# Render with custom XGML
render-midi --config my_config.xgdsl input.mid output.wav
```

## 📖 Documentation

### 📚 **User Guides**
- **[Getting Started](docs/user/getting-started.md)** - Quick start guide
- **[User Manual](docs/user/user-guide.md)** - Complete usage guide
- **[XGML Reference](docs/XGML_README.md)** - XGML v2.1 specification
- **[Configuration](docs/user/configuration.md)** - All configuration options

### 🔧 **Engine Documentation**
- **[FM-X Engine](docs/engines/fm-engine.md)** - 8-operator FM synthesis
- **[SFZ Engine](docs/engines/sfz-engine.md)** - Modern sample playback
- **[Physical Modeling](docs/engines/physical-engine.md)** - Waveguide synthesis
- **[Spectral Processing](docs/engines/spectral-engine.md)** - FFT-based effects

### 💻 **Developer Resources**
- **[API Reference](docs/api/overview.md)** - Complete API documentation
- **[Architecture](docs/developer/architecture.md)** - System design
- **[Contributing](CONTRIBUTING.md)** - Development guidelines

### 🎓 **Examples & Tutorials**
- **[Basic Synthesis](examples/tutorials/basic-synthesis.md)** - Simple patches
- **[Advanced Effects](examples/tutorials/advanced-effects.md)** - Professional processing
- **[Orchestral Setup](examples/projects/orchestral-setup.xgdsl)** - Complete orchestra

## 🎼 XGML Configuration Example

```yaml
# XGML v2.1 Configuration
xg_dsl_version: "2.1"
description: "Professional piano with FM-X bass"

# Basic MIDI setup
basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      reverb_send: 40

# Advanced FM-X engine for bass
fm_x_engine:
  enabled: true
  algorithm: 1
  operators:
    op_0:
      frequency_ratio: 1.0
      envelope:
        levels: [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
        rates: [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
      scaling:
        key_depth: 0
        velocity_sensitivity: 0

# Professional effects
effects_configuration:
  system_effects:
    reverb:
      type: 4
      time: 2.5
      level: 0.8
  master_processing:
    equalizer:
      type: "jazz"
      bands:
        low: {gain: 2.0, frequency: 80}
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    XG Synthesizer Engine                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Synthesis Engines                    │    │
│  │  ┌─────────┬─────────┬─────────┬─────────┐        │    │
│  │  │  SF2    │  SFZ    │  FM-X   │Physical │        │    │
│  │  │ Engine  │ Engine  │ Engine  │Modeling│        │    │
│  │  └─────────┴─────────┴─────────┴─────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Effects Processing                   │    │
│  │  ┌─────────┬─────────┬─────────┬─────────┐        │    │
│  │  │ System  │Variation│Insertion│ Master  │        │    │
│  │  │Effects  │Effects  │Effects  │Processing│      │    │
│  │  └─────────┴─────────┴─────────┴─────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Control Systems                      │    │
│  │  ┌─────────┬─────────┬─────────┬─────────┐        │    │
│  │  │  MIDI   │  XGML   │  MPE    │Arpeggiator│      │    │
│  │  │ Parser  │ Parser  │ Manager │  Engine  │      │    │
│  │  └─────────┴─────────┴─────────┴─────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Audio Output                         │    │
│  │  ┌─────────┬─────────┬─────────┬─────────┐        │    │
│  │  │Vectorized│Optimized│ Multi-  │ Format  │      │    │
│  │  │Processing│Coefficients│format  │Support │      │    │
│  │  └─────────┴─────────┴─────────┴─────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Key Components

### **Synthesis Engines**
- **SF2Engine**: SoundFont 2.0 playback with velocity layers and crossfading
- **SFZEngine**: Modern SFZ format with real-time modulation
- **FMEngine**: 8-operator FM synthesis with 88 algorithms
- **PhysicalEngine**: Waveguide and modal synthesis
- **SpectralEngine**: FFT-based processing and morphing

### **Control Systems**
- **XGML Parser/Translator**: Human-readable YAML to MIDI conversion
- **MPE Manager**: Per-note expression control
- **Arpeggiator Engine**: Pattern-based note generation
- **Modulation Matrix**: Advanced parameter routing

### **Effects Processing**
- **System Effects**: Reverb, chorus, delay (XG specification)
- **Variation Effects**: 62+ effect types
- **Insertion Effects**: Per-channel processing
- **Master Section**: EQ, stereo enhancement, limiting

## 📊 Performance

- **Latency**: <5ms end-to-end
- **Polyphony**: 256+ voices (depending on engine)
- **CPU Usage**: Optimized vectorized processing
- **Memory**: Efficient sample management with caching
- **Real-time**: Suitable for live performance

## 🔧 System Requirements

### Minimum Requirements
- **Python**: 3.8+
- **RAM**: 4GB
- **Disk**: 1GB for samples and temporary files
- **OS**: Windows 10+, macOS 10.15+, Linux (Ubuntu 18.04+)

### Recommended Requirements
- **Python**: 3.9+
- **RAM**: 8GB+
- **Disk**: SSD with 10GB+ free space
- **CPU**: Multi-core processor with AVX2 support

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone repository
git clone https://github.com/roger/syxg.git
cd syxg

# Install development dependencies
pip install -e ".[dev,audio,performance]"

# Run tests
pytest

# Run linting
flake8 synth/
black synth/
```

### Code Style
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **Pytest** for testing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Yamaha Corporation** - For the XG specification and inspiration
- **SoundFont Technical Committee** - For the SF2 specification
- **SFZ Format Community** - For modern sample standards
- **Open Source Community** - For the libraries that make this possible

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/roger/syxg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/roger/syxg/discussions)
- **Documentation**: [Full Documentation](docs/)

---

**🎹 Transform your MIDI files into professional audio with the power of modern synthesis engines and XGML configuration.**
