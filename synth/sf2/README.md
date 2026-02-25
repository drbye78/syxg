# SF2 Synthesis Engine

SoundFont 2 (SF2) wavetable synthesis engine for the XG synthesizer system.

## Status: ⚠️ UNDER ACTIVE DEVELOPMENT

**Current State**: Mid-refactor with known critical bugs

**Target**: Full SF2 v2.04 specification compliance

**Last Updated**: 2026-02-25

---

## Overview

The SF2 engine implements professional-grade SoundFont 2 wavetable synthesis with:

- Full SF2 v2.04 specification compliance (target)
- Multi-zone preset support with velocity/key splitting
- Layered voices with crossfading
- Complete generator and modulator matrix
- High-performance sample caching and management
- Integration with XG synthesizer infrastructure

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ModernXGSynthesizer                       │
│                      (Host System)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      SF2Engine                               │
│  - Preset lookup and management                              │
│  - Region creation and matching                              │
│  - Sample data coordination                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   SF2SoundFontManager                        │
│  - Multi-file soundfont management                           │
│  - Sample caching and memory management                      │
│  - Zone caching for fast lookup                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    SF2SoundFont                              │
│  - Single soundfont file representation                      │
│  - Preset/Instrument/Zone hierarchy                          │
│  - Generator and modulator processing                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SF2Region → SF2Partial                          │
│  - Individual voice instantiation                            │
│  - Sample playback with interpolation                        │
│  - Envelope, filter, LFO processing                          │
│  - Effects sends (reverb, chorus, pan)                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Structure

```
synth/sf2/
├── sf2_soundfont_manager.py    # Multi-file management
├── sf2_soundfont.py            # Single soundfont representation
├── sf2_file_loader.py          # RIFF chunk parsing
├── sf2_data_model.py           # Preset/Instrument/Zone data model
├── sf2_constants.py            # SF2 generator/modulator constants
├── sf2_modulation_engine.py    # Modulation matrix processing
├── sf2_sample_processor.py     # Sample processing and mip-mapping
├── sf2_zone_cache.py           # Zone caching for performance
└── sf2_s90_s70.py              # Yamaha AWM integration (WIP)

synth/engine/
└── sf2_engine.py               # Main SF2 synthesis engine

synth/partial/
├── sf2_partial.py              # SF2 partial implementation
└── sf2_region.py               # SF2 region (lazy initialization)
```

## Known Issues

### Critical (P0) - Prevents Operation

1. **`__slots__` Mismatch** - `SF2Partial` crashes on instantiation
2. **Constructor Signature** - Wrong parameters passed to `SF2Partial`
3. **Missing Manager Methods** - `get_sample_info`, `get_sample_loop_info`, `get_zone` not implemented
4. **Parameter Structure Mismatch** - Region/Partial use incompatible structures
5. **Sample Chunk Path** - Standard SF2 layout not handled correctly
6. **Engine Returns Silence** - No preset/zone lookup in generate path

### High Priority (P1) - Incorrect Behavior

7. **Generator ID Mappings** - Multiple wrong generator IDs
8. **frequency_to_cents Formula** - Mathematically incorrect
9. **sampleID Generator** - Wrong generator ID used
10. **Modulation Engine API** - Missing methods
11. **Import Path Errors** - Wrong relative imports
12. **Zone Cache Dead Code** - Resources not freed on unload

### Medium Priority (P2) - Quality Issues

13. **Buffer Pool Leaks** - Memory not released
14. **Mip-Map Anti-Aliasing** - TODO not implemented
15. **AVL Tree Performance** - O(n) not O(log n)
16. **Loop Mode Support** - Mode 2 (backward) not implemented
17. **Stereo Sample Handling** - Shape detection incomplete

See `sf2_fix_plan.md` for detailed remediation plan.

## Usage

### Basic Usage

```python
from synth.engine.sf2_engine import SF2Engine

# Create engine with soundfont
engine = SF2Engine(
    sf2_file_path='path/to/soundfont.sf2',
    sample_rate=44100,
    block_size=1024,
    synth=synthesizer_instance
)

# Generate audio for a note
audio = engine.generate_samples(
    program=0,
    bank=0,
    note=60,
    velocity=100,
    block_size=1024,
    modulation={}
)
```

### Advanced Usage

```python
from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager

# Create manager with custom cache settings
manager = SF2SoundFontManager(
    cache_memory_mb=512,
    max_loaded_files=20
)

# Load multiple soundfonts
manager.load_soundfont('orchestra.sf2', priority=10)
manager.load_soundfont('piano.sf2', priority=5)

# Get program parameters
params = manager.get_program_parameters(
    bank=0,
    program=0,
    note=60,
    velocity=100
)

# Get sample data
sample_data = manager.get_sample_data(sample_id=42)
```

## SF2 Specification Compliance

### Implemented Features

- [x] RIFF chunk parsing
- [x] Preset/Instrument/Zone hierarchy
- [x] Generator extraction (partial)
- [x] Sample loading (16-bit, 24-bit)
- [x] Loop modes (forward, no loop)
- [x] Basic modulation matrix
- [x] Effects sends

### In Progress

- [ ] Full generator inheritance (preset → instrument → zone)
- [ ] Complete modulator matrix
- [ ] All 60+ generators
- [ ] Proper velocity crossfading
- [ ] Multi-layer voice handling
- [ ] Mip-map anti-aliasing

### Not Yet Implemented

- [ ] SF2 v3.0 extensions
- [ ] Custom sample formats
- [ ] Real-time parameter modulation
- [ ] Advanced articulation switching

## Testing

### Run Tests

```bash
# Run all SF2 tests
pytest synth/sf2/tests/ -v

# Run with coverage
pytest synth/sf2/tests/ --cov=synth/sf2 --cov-report=html

# Run specific test category
pytest synth/sf2/tests/test_sf2_basics.py -v
pytest synth/sf2/tests/test_generator_mappings.py -v
pytest synth/sf2/tests/test_integration.py -v
```

### Test Coverage Goals

- Phase 1 (P0 fixes): > 60% coverage
- Phase 2 (P1 fixes): > 75% coverage
- Phase 3 (Complete): > 85% coverage

## Performance

### Targets

| Metric | Target | Current |
|--------|--------|---------|
| Latency (1024 samples) | < 10ms | TBD |
| CPU (64 voices) | < 5% | TBD |
| Memory (per voice) | < 1MB | TBD |
| Sample load time | < 100ms | TBD |

### Optimization Strategies

- Pooled buffers (zero allocation in hot path)
- Mip-map anti-aliasing for high-pitch playback
- Zone caching with AVL range trees
- Lazy sample loading
- LRU sample cache

## File Format Support

### Supported

- SF2 v2.04 (primary target)
- 16-bit PCM samples
- 24-bit PCM samples (via sm24 chunk)
- Standard RIFF layout

### Not Supported

- SFZ format
- Preset files (.sf3)
- Compressed samples

## Integration Points

### XG Synthesizer

The SF2 engine integrates with `ModernXGSynthesizer`:

- Voice management and polyphony
- Effects processing (reverb, chorus, variation)
- MIDI controller handling
- Modulation matrix integration

### Required Infrastructure

```python
# SF2Engine requires these from synth:
synth.sample_rate      # Audio sample rate
synth.block_size       # Processing block size
synth.memory_pool      # Buffer pool for zero allocation
synth.envelope_pool    # Envelope object pool
synth.filter_pool      # Filter object pool
synth.partial_lfo_pool # LFO object pool
```

## Development Roadmap

### Phase 1: Critical Fixes (P0) - 16-20 hours
- [ ] Fix `__slots__` mismatch
- [ ] Fix constructor signature
- [ ] Implement missing manager methods
- [ ] Fix parameter structure mismatch
- [ ] Fix sample chunk path
- [ ] Fix engine generate path

### Phase 2: High Priority (P1) - 14-18 hours
- [ ] Fix generator ID mappings
- [ ] Fix frequency_to_cents formula
- [ ] Fix sampleID generator
- [ ] Fix modulation engine API
- [ ] Fix import paths
- [ ] Fix zone cache unload

### Phase 3: Medium Priority (P2) - 12-16 hours
- [ ] Fix buffer pool memory leaks
- [ ] Enable mip-map anti-aliasing
- [ ] Fix AVL tree performance
- [ ] Complete loop mode support
- [ ] Add input validation

### Phase 4: Architecture - 16-20 hours
- [ ] Create ZoneEngine object
- [ ] Implement voice layering
- [ ] Add render-ready API
- [ ] Consolidate conversions

### Phase 5: Testing & Docs - 12-16 hours
- [ ] Complete test suite
- [ ] Update documentation
- [ ] Create compliance report

Total Estimated Effort: **60-80 hours**

## Contributing

### Before Contributing

1. Read `sf2_fix_plan.md` for current priorities
2. Check existing issues for known bugs
3. Run test suite before making changes
4. Ensure test coverage for new code

### Code Style

- Follow existing code conventions
- Use type hints for all functions
- Add docstrings to all public methods
- Include unit tests for new functionality

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes with tests
3. Run full test suite
4. Update documentation
5. Submit PR with description of changes

## References

### SF2 Specification

- [SoundFont 2.04 Specification](https://github.com/soundfonts2/soundfonts2-specifications)
- [RIFF File Format](https://www.w3.org/TR/NOTE-wavedrm.html)

### Related Documentation

- `sf2_fix_plan.md` - Comprehensive fix plan
- `sf2_report_01.md` - Initial bug assessment
- `sf2_assessment.md` - Architecture assessment

## License

Same as parent project (see LICENSE in root directory)

## Authors

See git history for contributor list

## Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: See docs/ directory
- SF2-specific: See synth/sf2/README.md

---

**Last Updated**: 2026-02-25  
**Document Version**: 1.0  
**Status**: Under Active Development
