# SF2 Synthesis Engine - Documentation Index

**Last Updated**: 2026-02-25  
**Status**: Under Active Development  

---

## Quick Navigation

### 📋 For Implementers
Start here if you're fixing the SF2 engine:
1. **[SF2_REMEDIATION_SUMMARY.md](../partial/SF2_REMEDIATION_SUMMARY.md)** - Project overview and checklist
2. **[sf2_fix_plan.md](../partial/sf2_fix_plan.md)** - Detailed fix instructions with code examples
3. **[Test Suite](./tests/)** - Run tests to validate fixes

### 🔍 For Analysts
Start here if you're assessing the SF2 engine:
1. **[SF2_SPEC_COMPLIANCE.md](./SF2_SPEC_COMPLIANCE.md)** - Specification compliance report
2. **[sf2_report_01.md](../partial/sf2_report_01.md)** - Initial bug assessment
3. **[sf2_assessment.md](../sf2_assessment.md)** - Architecture assessment

### 📖 For Users
Start here if you're using the SF2 engine:
1. **[README.md](./README.md)** - Overview, usage examples, known issues
2. **[sf2_fix_plan.md](../partial/sf2_fix_plan.md)** - Roadmap and timeline
3. **[SF2_REMEDIATION_SUMMARY.md](../partial/SF2_REMEDIATION_SUMMARY.md)** - Current status

---

## Document Directory

### Core Documentation

| Document | Location | Purpose | Audience |
|----------|----------|---------|----------|
| **README** | `synth/sf2/README.md` | Overview and usage | All users |
| **Spec Compliance** | `synth/sf2/SF2_SPEC_COMPLIANCE.md` | SF2 spec assessment | Developers, QA |
| **Fix Plan** | `synth/partial/sf2_fix_plan.md` | Implementation guide | Developers |
| **Remediation Summary** | `synth/partial/SF2_REMEDIATION_SUMMARY.md` | Project overview | PM, Developers |

### Assessment Reports

| Document | Location | Focus | Date |
|----------|----------|-------|------|
| **Initial Assessment** | `synth/partial/sf2_report_01.md` | Bug identification | 2026-02-25 |
| **Architecture Assessment** | `synth/sf2_assessment.md` | Code quality review | 2026-02-25 |
| **Compliance Report** | `synth/sf2/SF2_SPEC_COMPLIANCE.md` | Spec compliance | 2026-02-25 |

### Test Documentation

| File | Location | Purpose |
|------|----------|---------|
| **Test Fixtures** | `synth/sf2/tests/conftest.py` | Pytest fixtures and mocks |
| **Basic Tests** | `synth/sf2/tests/test_sf2_basics.py` | Core functionality tests |
| **Generator Tests** | `synth/sf2/tests/test_generator_mappings.py` | Generator ID validation |
| **Integration Tests** | `synth/sf2/tests/test_integration.py` | End-to-end pipeline tests |

---

## Bug Tracking

### Critical Bugs (P0) - 6 Issues

| ID | Bug | Document | Status |
|----|-----|----------|--------|
| P0-1 | `__slots__` mismatch | sf2_fix_plan.md §1.1 | ⏳ Pending |
| P0-2 | Constructor signature | sf2_fix_plan.md §1.2 | ⏳ Pending |
| P0-3 | Missing manager methods | sf2_fix_plan.md §1.3 | ⏳ Pending |
| P0-4 | Parameter structure mismatch | sf2_fix_plan.md §1.4 | ⏳ Pending |
| P0-5 | Sample chunk path bug | sf2_fix_plan.md §1.5 | ⏳ Pending |
| P0-6 | Engine returns silence | sf2_fix_plan.md §1.6 | ⏳ Pending |

### High Priority (P1) - 6 Issues

| ID | Bug | Document | Status |
|----|-----|----------|--------|
| P1-1 | Generator ID mappings | sf2_fix_plan.md §2.1 | ⏳ Pending |
| P1-2 | frequency_to_cents formula | sf2_fix_plan.md §2.2 | ⏳ Pending |
| P1-3 | sampleID generator | sf2_fix_plan.md §2.3 | ⏳ Pending |
| P1-4 | Modulation engine API | sf2_fix_plan.md §2.4 | ⏳ Pending |
| P1-5 | Import path errors | sf2_fix_plan.md §2.5 | ⏳ Pending |
| P1-6 | Zone cache dead code | sf2_fix_plan.md §2.6 | ⏳ Pending |

### Medium Priority (P2) - 7 Issues

| ID | Bug | Document | Status |
|----|-----|----------|--------|
| P2-1 | Buffer pool memory leaks | sf2_fix_plan.md §3.1 | ⏳ Pending |
| P2-2 | Mip-map anti-aliasing | sf2_fix_plan.md §3.2 | ⏳ Pending |
| P2-3 | AVL tree performance | sf2_fix_plan.md §3.3 | ⏳ Pending |
| P2-4 | Loop mode support | sf2_fix_plan.md §3.4 | ⏳ Pending |
| P2-5 | Timecents conversion | sf2_fix_plan.md §3.5 | ⏳ Pending |
| P2-6 | Input validation | sf2_fix_plan.md §3.6 | ⏳ Pending |
| P2-7 | Stereo sample handling | sf2_fix_plan.md §3.7 | ⏳ Pending |

**Total Bugs Identified**: 25+  
**Total Fix Effort**: 60-80 hours

---

## Code Structure

### SF2 Module Files

```
synth/sf2/
├── README.md                      # Module overview
├── SF2_SPEC_COMPLIANCE.md         # Spec compliance report
├── sf2_soundfont_manager.py       # Multi-file management
├── sf2_soundfont.py               # Single soundfont
├── sf2_file_loader.py             # RIFF parsing
├── sf2_data_model.py              # Data structures
├── sf2_constants.py               # Generator/modulator constants
├── sf2_modulation_engine.py       # Modulation matrix
├── sf2_sample_processor.py        # Sample processing
├── sf2_zone_cache.py              # Zone caching
├── sf2_s90_s70.py                 # Yamaha AWM (WIP)
└── tests/
    ├── conftest.py                # Test fixtures
    ├── test_sf2_basics.py         # Basic tests
    ├── test_generator_mappings.py # Generator tests
    └── test_integration.py        # Integration tests
```

### Related Engine Files

```
synth/engine/
└── sf2_engine.py                  # Main SF2 engine

synth/partial/
├── sf2_partial.py                 # SF2 partial
├── sf2_region.py                  # SF2 region
├── sf2_fix_plan.md                # Fix plan
└── SF2_REMEDIATION_SUMMARY.md     # Project summary

synth/
└── sf2_assessment.md              # Architecture assessment
```

---

## Testing Guide

### Running Tests

```bash
# All SF2 tests
pytest synth/sf2/tests/ -v

# With coverage
pytest synth/sf2/tests/ --cov=synth/sf2 --cov-report=html

# Specific test file
pytest synth/sf2/tests/test_sf2_basics.py -v

# Specific test category
pytest synth/sf2/tests/test_generator_mappings.py -v
pytest synth/sf2/tests/test_integration.py -v
```

### Test Coverage Goals

| Phase | Target | Current |
|-------|--------|---------|
| Phase 1 (P0 fixes) | > 60% | < 30% |
| Phase 2 (P1 fixes) | > 75% | - |
| Phase 3 (Complete) | > 80% | - |

---

## Implementation Roadmap

### Phase 1: Critical Fixes (16-20 hours)
**Goal**: Make SF2 engine functional

- [ ] Fix `__slots__` mismatch
- [ ] Fix constructor signature
- [ ] Implement missing manager methods
- [ ] Fix parameter structure mismatch
- [ ] Fix sample chunk path
- [ ] Fix engine generate path

**Exit Criteria**: SF2Partial instantiates, engine generates non-silent audio

### Phase 2: High Priority (14-18 hours)
**Goal**: Audio plays with correct parameters

- [ ] Fix generator ID mappings
- [ ] Fix frequency_to_cents formula
- [ ] Fix sampleID generator
- [ ] Fix modulation engine API
- [ ] Fix import paths
- [ ] Fix zone cache unload

**Exit Criteria**: Generator mappings match SF2 2.04 spec

### Phase 3: Medium Priority (12-16 hours)
**Goal**: Quality and performance improvements

- [ ] Fix buffer pool memory leaks
- [ ] Enable mip-map anti-aliasing
- [ ] Fix AVL tree performance
- [ ] Complete loop mode support
- [ ] Fix timecents conversion
- [ ] Add input validation
- [ ] Fix stereo sample handling

**Exit Criteria**: No memory leaks, anti-aliasing functional

### Phase 4: Architecture (16-20 hours)
**Goal**: Clean, maintainable architecture

- [ ] Create ZoneEngine object
- [ ] Implement voice layering
- [ ] Add render-ready API
- [ ] Consolidate conversion functions

**Exit Criteria**: Proper generator inheritance, clean API

### Phase 5: Testing & Documentation (12-16 hours)
**Goal**: Production-ready quality

- [ ] Complete test suite
- [ ] Update documentation
- [ ] Create compliance report

**Exit Criteria**: > 80% test coverage, documentation complete

---

## SF2 Specification Quick Reference

### Generator IDs (Critical)

| ID | Name | Description |
|----|------|-------------|
| 8-13 | Volume Envelope | Delay, Attack, Hold, Decay, Sustain, Release |
| 14-20 | Mod Envelope | Delay, Attack, Hold, Decay, Sustain, Release, toPitch |
| 21-25 | Mod LFO | Delay, Freq, toVol, toFilter, toPitch |
| 26-28 | Vib LFO | Delay, Freq, toPitch |
| 29-30 | Filter | Cutoff, Resonance |
| 32-34 | Effects | Reverb, Chorus, Pan |
| 42-43 | Ranges | KeyRange, VelRange |
| 48-49 | Pitch | CoarseTune, FineTune |
| 50-53 | Sample | SampleID, SampleModes, ScaleTuning, ExclusiveClass |

**Full List**: See `SF2_SPEC_COMPLIANCE.md` §3.2

### File Structure

```
RIFF sfbk
├── INFO (metadata)
├── SDTA (sample data)
│   ├── smpl (16-bit)
│   └── sm24 (24-bit extension)
└── PDTA (preset data)
    ├── phdr → pbag → pmod/pgen (presets)
    ├── inst → ibag → imod/igen (instruments)
    └── shdr (sample headers)
```

**Details**: See `sf2_file_loader.py` and `SF2_SPEC_COMPLIANCE.md` §1

---

## Glossary

| Term | Definition |
|------|------------|
| **SF2** | SoundFont 2 - sample-based synthesis format |
| **Preset** | MIDI bank/program assignment with zones |
| **Instrument** | Collection of zones with generators |
| **Zone** | Sample + parameters for specific key/velocity range |
| **Generator** | SF2 parameter (60+ types defined in spec) |
| **Modulator** | Source→destination modulation pair |
| **Region** | Lazy-initialized voice descriptor |
| **Partial** | Active voice instance |
| **Mip-map** | Downsampled versions for anti-aliasing |

---

## Contact & Support

### Documentation Issues
- Missing information? → Create issue in GitHub
- Incorrect information? → Submit PR with correction
- Questions? → Check README or create discussion

### Code Issues
- Bug found? → Check bug tracking section
- Fix completed? → Update checklist and run tests
- New bug found? → Add to assessment report

### Getting Help
1. Check relevant documentation above
2. Search existing issues/discussions
3. Create new issue with details
4. Reference specific documents in issue

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-25 | 1.0 | Initial documentation created |
| - | - | - |

---

## Quick Links

### Essential Reading
- [Remediation Summary](../partial/SF2_REMEDIATION_SUMMARY.md) - Start here
- [Fix Plan](../partial/sf2_fix_plan.md) - Implementation guide
- [README](./README.md) - Usage and overview

### Detailed Analysis
- [Spec Compliance](./SF2_SPEC_COMPLIANCE.md) - Full compliance report
- [Bug Report 1](../partial/sf2_report_01.md) - Initial assessment
- [Bug Report 2](../sf2_assessment.md) - Architecture review

### Testing
- [Test Suite](./tests/) - All test files
- [Fixtures](./tests/conftest.py) - Test helpers and mocks

---

**Index Status**: Complete  
**Next Update**: After Phase 1 completion  
**Maintainer**: SF2 Development Team
