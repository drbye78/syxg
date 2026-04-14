# XG Synthesizer Test Suite

Comprehensive test suite for the modern XG synthesizer with SF2 engine.

## Overview

This test suite validates every step of the modern XG synthesizer audio rendering pipeline that employs the SF2 synthesis engine. The tests cover all operations from voice setup through final audio output, ensuring proper panning, volume amplification, effects processing, and XG specification compliance.

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── run_tests.py                   # Test runner script
├── README.md                      # This file
├── utils/                         # Test utilities
│   ├── __init__.py
│   ├── audio_utils.py             # Audio testing functions
│   ├── midi_utils.py              # MIDI message creation
│   └── test_data_generator.py     # Test data generation
├── test_sf2_zone_selection.py     # SF2 zone selection tests
├── test_voice_synthesis.py        # Voice synthesis tests
├── test_envelope_processing.py    # Envelope processing tests
├── test_lfo_filter_processing.py  # LFO and filter tests
├── test_panning_volume.py         # Panning and volume tests
├── test_voice_integration.py      # Voice integration tests
├── test_channel_integration.py    # Channel integration tests
├── test_effects_integration.py    # Effects integration tests
├── test_pipeline_e2e.py           # End-to-end pipeline tests
└── test_performance.py            # Performance tests
```

## Test Categories

### 1. Unit Tests (Phase 1)
Tests for individual SF2 synthesis components:
- **SF2 Zone Selection**: Key/velocity range matching, zone inheritance, layering
- **Voice Synthesis**: Mono/stereo playback, loop modes, pitch shifting, interpolation
- **Envelope Processing**: ADSR stages, key follow, velocity sensitivity
- **LFO Processing**: Waveforms, rate modulation, delay, vibrato depth
- **Filter Processing**: Filter types, cutoff modulation, resonance, key follow
- **Panning/Volume**: Constant power panning, volume amplification

### 2. Integration Tests (Phase 2)
Tests for component interactions:
- **Voice Integration**: Note on/off, voice stealing, priority, cleanup
- **Channel Integration**: Volume/pan, effects routing, controller processing
- **Effects Integration**: Reverb types, chorus types, insertion effects

### 3. System Tests (Phase 3)
End-to-end pipeline tests:
- **Full Note Rendering**: Complete audio generation pipeline
- **Polyphonic Rendering**: Multiple simultaneous voices
- **Multi-Channel Rendering**: Multiple MIDI channels
- **Drum Channel Rendering**: Percussion sounds
- **Effects Chain Rendering**: Complete effects processing

### 4. Performance Tests (Phase 4)
Performance and stability tests:
- **Maximum Polyphony**: Voice limit testing
- **Block Processing Latency**: Processing speed
- **Memory Usage**: Memory consumption
- **CPU Usage**: Processing efficiency
- **Long-Running Stability**: Extended operation testing

## Running Tests

### Quick Start

```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py --verbose

# Run with coverage
python tests/run_tests.py --coverage
```

### Run Specific Test Categories

```bash
# Run only unit tests
python tests/run_tests.py --unit

# Run only integration tests
python tests/run_tests.py --integration

# Run only system tests
python tests/run_tests.py --system

# Run only performance tests
python tests/run_tests.py --performance
```

### Run Specific Test Files

```bash
# Run SF2 zone selection tests
python tests/run_tests.py --test-file tests/test_sf2_zone_selection.py

# Run voice synthesis tests
python tests/run_tests.py --test-file tests/test_voice_synthesis.py

# Run envelope processing tests
python tests/run_tests.py --test-file tests/test_envelope_processing.py
```

### Advanced Options

```bash
# Run tests in parallel
python tests/run_tests.py --parallel

# Include slow tests
python tests/run_tests.py --include-slow

# Run only tests requiring SF2 files
python tests/run_tests.py --requires-sf2

# Run with coverage and verbose output
python tests/run_tests.py --coverage --verbose
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/

# Run with markers
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m system
pytest tests/ -m performance

# Run specific test file
pytest tests/test_sf2_zone_selection.py

# Run with coverage
pytest tests/ --cov=synth --cov-report=html

# Run in parallel
pytest tests/ -n auto
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.system`: System tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow tests (excluded by default)
- `@pytest.mark.requires_sf2`: Tests requiring SF2 files

## Test Fixtures

The test suite provides shared fixtures in `conftest.py`:

- `sample_rate`: Audio sample rate (44100 Hz)
- `block_size`: Audio block size (1024 samples)
- `sf2_engine`: SF2 engine instance
- `midi_parser`: MIDI file parser
- `test_frequencies`: Standard test frequencies
- `test_notes`: Standard MIDI notes
- `test_velocities`: Standard velocities
- `test_controllers`: MIDI controller numbers
- `envelope_params`: Default envelope parameters
- `lfo_params`: Default LFO parameters
- `filter_params`: Default filter parameters

## Test Utilities

### Audio Utilities (`utils/audio_utils.py`)

- `generate_test_frequency()`: Generate test sine waves
- `generate_white_noise()`: Generate white noise
- `calculate_rms()`: Calculate RMS level
- `calculate_peak()`: Calculate peak level
- `detect_clipping()`: Detect clipping in audio
- `compare_audio_buffers()`: Compare audio buffers
- `apply_window()`: Apply window function
- `calculate_snr()`: Calculate signal-to-noise ratio
- `calculate_thd()`: Calculate total harmonic distortion
- `stereo_to_mono()`: Convert stereo to mono
- `mono_to_stereo()`: Convert mono to stereo
- `pan_stereo()`: Apply panning with constant power law
- `apply_volume()`: Apply volume scaling

### MIDI Utilities (`utils/midi_utils.py`)

- `create_note_on_message()`: Create Note On message
- `create_note_off_message()`: Create Note Off message
- `create_control_change_message()`: Create CC message
- `create_program_change_message()`: Create PC message
- `create_pitch_bend_message()`: Create Pitch Bend message
- `create_sysex_message()`: Create SysEx message
- `create_note_sequence()`: Create note sequence
- `create_chord()`: Create chord
- `create_scale()`: Create musical scale

### Test Data Generator (`utils/test_data_generator.py`)

- `generate_sf2_test_data()`: Generate test SF2 data
- `generate_midi_test_sequence()`: Generate MIDI sequences
- `generate_reference_audio()`: Generate reference audio
- `generate_controller_sequence()`: Generate CC sequences
- `generate_pitch_bend_sequence()`: Generate pitch bend sequences
- `generate_velocity_curve()`: Generate velocity curves
- `generate_key_range_test()`: Generate key range tests
- `generate_velocity_range_test()`: Generate velocity range tests
- `generate_polyphony_test()`: Generate polyphony tests

## Expected Test Results

### Unit Tests
- All unit tests should pass
- Code coverage should be > 80% for tested components

### Integration Tests
- All integration tests should pass
- Voice allocation and channel processing should work correctly

### System Tests
- End-to-end pipeline should generate valid audio
- No clipping or distortion in output

### Performance Tests
- Voice allocation: < 1ms per voice
- Block processing: < 5ms per block
- Memory usage: < 512MB
- CPU usage: < 50% at 64 voices

## Troubleshooting

### Tests Fail to Import

If tests fail to import synth modules, ensure you're running from the project root:

```bash
cd /mnt/c/work/guga/syxg
python tests/run_tests.py
```

### SF2 File Not Found

Some tests require SF2 files. If SF2 files are not available, those tests will be skipped. To run SF2-dependent tests, ensure SF2 files are in the `tests/data/` directory.

### Performance Issues

If performance tests fail, check:
- System load (other processes)
- Available memory
- CPU throttling

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Use shared fixtures from `conftest.py`
4. Add test utilities to `utils/` if needed
5. Update this README if adding new test categories

## Test Coverage

To generate a coverage report:

```bash
python tests/run_tests.py --coverage
```

This will generate:
- Terminal coverage report
- XML coverage report (for CI/CD)
- HTML coverage report in `htmlcov/` directory

## CI/CD Integration

The test suite is designed for CI/CD integration:

```yaml
# GitHub Actions example
- name: Run tests
  run: python tests/run_tests.py --coverage --verbose

- name: Upload coverage
  uses: codecov/codecov-action@v2
  with:
    file: ./coverage.xml
```

## Performance Benchmarks

Expected performance on modern hardware:

| Test | Target | Notes |
|------|--------|-------|
| Voice Allocation | < 1ms | Per voice |
| Block Processing | < 5ms | Per block (1024 samples) |
| Memory Usage | < 512MB | With 64 voices loaded |
| CPU Usage | < 50% | At 64 voices, 44.1kHz |

## License

This test suite is part of the XG Synthesizer project.