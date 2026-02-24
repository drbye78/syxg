# Comprehensive Test Suite Plan for synth/sf2 Package

## Overview
Create a thorough test suite covering all major functionality of the SF2 package, organized into logical test modules.

## Test Modules Structure

### 1. test_sf2_constants.py
Tests for SF2 constants, generators, and conversion functions.

- [ ] Test all SF2_GENERATORS have correct indices
- [ ] Test frequency_to_cents conversion accuracy
- [ ] Test cents_to_frequency conversion
- [ ] Test timecents_to_seconds conversion
- [ ] Test SF2_MODULATOR_SOURCES completeness
- [ ] Test SF2_MODULATOR_DESTINATIONS completeness

### 2. test_sf2_data_model.py
Tests for core data structures.

- [ ] Test SF2Zone creation and generator handling
- [ ] Test SF2Zone key/velocity range matching
- [ ] Test SF2Zone.sample_id extraction (gen 50)
- [ ] Test SF2Instrument zone management
- [ ] Test SF2Preset zone management
- [ ] Test SF2Sample properties
- [ ] Test RangeTree zone insertion and query
- [ ] Test RangeTree AVL balancing

### 3. test_sf2_file_loader.py
Tests for SF2 file parsing.

- [ ] Test SF2 header verification
- [ ] Test RIFF chunk parsing
- [ ] Test LIST sdta nested chunk parsing (smpl/sm24)
- [ ] Test INFO metadata extraction
- [ ] Test pdta chunk parsing (presets, instruments, samples)
- [ ] Test on-demand sample data retrieval
- [ ] Test 16-bit sample data reading
- [ ] Test 24-bit sample data reconstruction
- [ ] Test lazy loading doesn't load sample data into memory

### 4. test_sf2_modulation_engine.py
Tests for modulation and generator processing.

- [ ] Test SF2GeneratorProcessor initialization
- [ ] Test all 60+ generators mapped correctly
- [ ] Test volume envelope parameter generation
- [ ] Test modulation envelope parameter generation
- [ ] Test LFO parameter generation
- [ ] Test filter parameter generation
- [ ] Test loop parameter mapping (gens 44-47)
- [ ] Test SF2ModulationEngine controller states
- [ ] Test SF2ZoneEngine per-zone modulation
- [ ] Test modulator source processing

### 5. test_sf2_soundfont.py
Tests for SF2SoundFont class.

- [ ] Test soundfont loading
- [ ] Test preset parsing
- [ ] Test instrument parsing
- [ ] Test zone generation from bags
- [ ] Test sample loading
- [ ] Test get_program_parameters
- [ ] Test key/velocity zone matching
- [ ] Test multi-layered zones
- [ ] Test zone cache population
- [ ] Test unload functionality

### 6. test_sf2_soundfont_manager.py
Tests for SF2SoundFontManager class.

- [ ] Test soundfont loading
- [ ] Test multiple soundfont priority
- [ ] Test bank/program lookup
- [ ] Test sample data retrieval across soundfonts
- [ ] Test soundfont unloading
- [ ] Test memory management

### 7. test_sf2_zone_cache.py
Tests for zone caching and lookups.

- [ ] Test AVLRangeTree insertion
- [ ] Test AVLRangeTree query performance
- [ ] Test AVLRangeTree rebalancing
- [ ] Test HierarchicalZoneCache operations
- [ ] Test SF2ZoneCacheManager operations

### 8. test_sf2_sample_processor.py
Tests for sample processing.

- [ ] Test mip-map generation
- [ ] Test sample rate conversion
- [ ] Test stereo/mono handling

### 9. test_sf2_integration.py
Integration tests with real soundfonts.

- [ ] Test loading ref.sf2
- [ ] Test preset lookup (bank 0, program 0)
- [ ] Test note triggering
- [ ] Test velocity layers
- [ ] Test key splits
- [ ] Test loop handling

### 10. test_sf2_e2e.py
End-to-end tests.

- [ ] Test full soundfont loading to playback
- [ ] Test parameter generation from generators
- [ ] Test modulator application
- [ ] Test sample data flow

## Test Data
- Primary: tests/ref.sf2 (377MB) - general purpose
- Secondary: tests/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2 (377MB) - GM/GS/XG
- Tertiary: tests/yamaha tyros 4_just_t4_fixed.sf2 (502MB) - Yamaha-specific

## Test Execution Strategy

1. **Unit tests**: Fast, use mocked data where possible
2. **Integration tests**: Use smallest soundfont (ref.sf2)
3. **Full tests**: Use all soundfonts, skip if loading takes too long
4. **Performance tests**: Measure zone lookup times, sample loading

## Fixtures Needed

```python
@pytest.fixture
def ref_sf2_path():
    """Path to ref.sf2"""
    
@pytest.fixture
def sf2_manager(ref_sf2_path):
    """Pre-loaded manager"""
    
@pytest.fixture
def small_sf2_path(tmp_path):
    """Create minimal test SF2"""
```

## Coverage Goals
- Target: 80%+ code coverage
- Critical paths: 95%+ coverage
- All public APIs tested
- Edge cases: empty zones, invalid ranges, boundary conditions
