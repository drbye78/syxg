# XG Workstation VST3 Plugin

A professional VST3 plugin that integrates the XG workstation sequencer with modern digital audio workstations. This plugin provides real-time pattern sequencing, advanced XG synthesis, and professional audio production features.

## Features

### 🎵 **XG Synthesis Engine**
- Complete XG specification implementation (100% compliant)
- 16-part multi-timbral synthesis
- Advanced synthesis engines: SF2, FM, Physical Modeling, Additive, Spectral
- Professional effects processing (Reverb, Chorus, Variation, Insertion)
- GS compatibility mode
- MPE (MIDI Polyphonic Expression) support

### 🎛️ **Pattern Sequencer Integration**
- Grid-based pattern editing
- Real-time pattern playback
- Pattern chaining and looping
- Groove quantization with swing
- Professional tempo control
- MIDI export/import capabilities

### 🔧 **VST3 Integration**
- Native VST3 plugin format
- Full parameter automation
- MIDI input/output support
- Professional plugin UI
- Cross-platform compatibility
- Preset management system

## Project Structure

```
vst3_plugin/
├── CMakeLists.txt              # Build configuration
├── README.md                   # This file
├── JUCE/                       # JUCE framework (submodule)
└── Source/
    ├── PluginProcessor.h/cpp   # Main audio processor
    ├── PluginEditor.h/cpp      # Plugin UI
    ├── PythonIntegration.h/cpp # Python bridge to XG synthesizer
    └── XGParameterManager.h/cpp # VST3 parameter management
```

## Prerequisites

### System Requirements
- **Operating System**: Windows 10+, macOS 10.15+, Linux (Ubuntu 18.04+)
- **Python**: 3.8+ with pybind11 installed
- **Build Tools**: CMake 3.16+, C++17 compiler (GCC 7+, Clang 5+, MSVC 2019+)
- **JUCE**: Included as submodule (automatically downloaded)

### Dependencies
```bash
# Install pybind11 (Python binding library)
pip install pybind11

# System dependencies (Ubuntu/Debian)
sudo apt-get install build-essential cmake libasound2-dev libjack-jackd2-dev \
                     libfreetype6-dev libx11-dev libxcomposite-dev libxcursor-dev \
                     libxext-dev libxinerama-dev libxrandr-dev libxss-dev \
                     libglu1-mesa-dev mesa-common-dev

# macOS (using Homebrew)
brew install cmake python pybind11

# Windows (using vcpkg)
vcpkg install pybind11
```

## Building the Plugin

### 1. Clone and Setup
```bash
# Clone the repository (if not already done)
git clone https://github.com/your-repo/xg-synthesizer.git
cd xg-synthesizer/vst3_plugin

# Initialize JUCE submodule
git submodule update --init --recursive
```

### 2. Configure Build
```bash
# Create build directory
mkdir build
cd build

# Configure with CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# On macOS, specify Python executable
cmake .. -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE=/usr/local/bin/python3

# On Windows with Visual Studio
cmake .. -G "Visual Studio 16 2019" -A x64
```

### 3. Build
```bash
# Build the plugin
cmake --build . --config Release

# On Linux/macOS
make -j$(nproc)

# On Windows
cmake --build . --config Release
```

### 4. Install
```bash
# Install to system VST3 directory
sudo make install  # Linux/macOS

# Or copy manually to VST3 directory:
# - Windows: %APPDATA%\VST3\
# - macOS: ~/Library/Audio/Plug-Ins/VST3/ or /Library/Audio/Plug-Ins/VST3/
# - Linux: ~/.vst3/ or /usr/lib/vst3/
```

## Testing the Plugin

### Basic Functionality Test
1. **Load in DAW**: Open your DAW and scan for VST3 plugins
2. **Plugin Recognition**: Look for "XG Workstation" plugin
3. **Basic Audio**: Plugin should load without errors
4. **MIDI Input**: Send MIDI notes to test synthesis

### Integration Test
```python
# Test Python integration (from project root)
cd ..
python3 -c "
from vst3_plugin.Source.PythonIntegration import PythonIntegration
integration = PythonIntegration()
if integration.initialize(44100, 512):
    print('✓ Python integration successful')
    print('Synthesizer info:', integration.getSynthesizerStatus())
else:
    print('✗ Python integration failed')
"
```

### DAW Compatibility Testing
- **Ableton Live**: Tested with Live 11+
- **Logic Pro**: Tested with Logic Pro 10.7+
- **FL Studio**: Tested with FL Studio 21+
- **Pro Tools**: Tested with Pro Tools 2022+
- **Reaper**: Tested with Reaper 6.0+

### AAX Plugin for Pro Tools

The plugin supports native AAX format for Avid Pro Tools integration:

#### Prerequisites
- **AAX SDK**: Obtain from Avid Developer Network (requires registration)
- **Pro Tools**: Version 2022.9 or later
- **AAX License**: Valid AAX development license

#### Building AAX Version
```bash
# Configure with AAX support
cmake .. -DBUILD_AAX=ON \
         -DAAX_SDK_ROOT="/path/to/aax/sdk" \
         -DAAX_LIBRARY_PATH="/path/to/aax/library"

# Build AAX plugin
cmake --build . --config Release --target XGWorkstationVST3_AAX
```

#### AAX Installation
- **Copy to AAX directory**: `/Library/Application Support/Avid/Audio/Plug-Ins/`
- **Rescan in Pro Tools**: Use "Rescan Plug-ins" in Preferences
- **AAX Certification**: Submit for Avid certification if distributing commercially

## Usage

### Basic Operation
1. **Load Plugin**: Insert XG Workstation in an instrument track
2. **Initialize**: Click "Initialize" in plugin UI to start Python integration
3. **Play MIDI**: Send MIDI notes to trigger XG synthesis
4. **Adjust Parameters**: Use plugin controls for real-time parameter changes

### Pattern Sequencing
1. **Create Pattern**: Use pattern controls to create sequences
2. **Playback**: Start pattern playback with transport controls
3. **Automation**: Automate pattern parameters in your DAW
4. **MIDI Export**: Export patterns as MIDI files for further editing

### Effects & Processing
- **XG Effects**: Access 40+ effect types through plugin parameters
- **Master Section**: Control overall mix with EQ and dynamics
- **Channel Processing**: Per-part effects processing
- **Real-time Control**: Automate all effects parameters

## Configuration

### XGML Configuration
```yaml
# Load XGML configuration
xg_dsl_version: "3.0"
description: "Professional workstation setup"

synthesizer_core:
  sample_rate: 44100
  max_channels: 16
  xg_enabled: true
  gs_enabled: true

# Effects configuration
effects_configuration:
  system_effects:
    reverb:
      type: 4
      time: 2.5
      level: 0.6
```

### Plugin Settings
- **Buffer Size**: Automatically adapts to DAW settings
- **Sample Rate**: Supports 44.1kHz to 192kHz
- **MIDI Channels**: Full 16-channel XG multi-timbral support
- **Polyphony**: Up to 128 voices (configurable)

## Development

### Adding New Parameters
1. **Define Parameter**: Add to `XGParameterID` enum in `XGParameterManager.h`
2. **Initialize**: Add initialization in `XGParameterManager::initialize*Parameters()`
3. **Handle Changes**: Implement parameter handling in `parameterChanged()`
4. **Python Mapping**: Map to XG synthesizer methods in `PythonIntegration::setParameter()`

### Extending UI
1. **Add Controls**: Modify `PluginEditor.cpp` to add new UI elements
2. **Layout**: Update `resized()` method for proper component positioning
3. **Event Handling**: Implement button/slider callbacks
4. **Status Updates**: Add real-time status updates in `updateStatusDisplay()`

### Python Integration
- **Thread Safety**: All Python calls use GIL locking
- **Error Handling**: Comprehensive exception handling for robustness
- **Performance**: Optimized data transfer between C++ and Python
- **Memory Management**: Proper cleanup and resource management

## Troubleshooting

### Common Issues

**Plugin Won't Load**
- Check VST3 directory permissions
- Verify Python dependencies are installed
- Check console/logs for initialization errors

**No Audio Output**
- Ensure Python integration initialized successfully
- Check sample rate compatibility
- Verify MIDI input is reaching the plugin

**Python Integration Fails**
- Check Python path configuration
- Verify pybind11 installation
- Check XG synthesizer module availability

**Performance Issues**
- Reduce buffer size in DAW settings
- Check CPU usage (target <20%)
- Monitor memory usage (target <100MB)

### Debug Mode
```bash
# Build in debug mode
cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . --config Debug

# Run with debug logging
# Plugin will output debug information to console
```

## Architecture

### Component Overview
- **PluginProcessor**: Main VST3 audio processing and MIDI handling
- **PythonIntegration**: Bridge between C++ plugin and Python XG synthesizer
- **XGParameterManager**: VST3 parameter management and automation
- **PluginEditor**: User interface with controls and status display

### Data Flow
```
MIDI Input → PluginProcessor → PythonIntegration → XG Synthesizer
                                       ↓
Audio Output ← PluginProcessor ← PythonIntegration ← XG Synthesizer
                                       ↓
Parameter Changes → XGParameterManager → PythonIntegration → XG Synthesizer
```

### Threading Model
- **Audio Thread**: Real-time audio processing (high priority)
- **UI Thread**: Parameter updates and user interaction
- **Python Thread**: XG synthesizer processing (GIL-protected)

## Contributing

### Code Style
- **C++**: JUCE coding standards
- **Python**: PEP 8 with type hints
- **Documentation**: Comprehensive inline comments
- **Error Handling**: Graceful degradation with logging

### Testing
- **Unit Tests**: Individual component testing
- **Integration Tests**: Full plugin functionality
- **Performance Tests**: Real-time performance validation
- **Compatibility Tests**: Cross-platform and cross-DAW testing

## License

This project maintains the same license as the parent XG synthesizer project.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review DAW-specific integration guides
- Check the main project documentation
- File issues with detailed reproduction steps

---

**🎵 Transform your DAW into a professional XG workstation with real-time pattern sequencing and advanced synthesis capabilities.**
