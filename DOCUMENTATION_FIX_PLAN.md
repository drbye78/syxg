# Documentation Fix Plan - XG Synthesizer

## Executive Summary

This document identifies gaps, outdated content, and missing sections in the project documentation, and provides a comprehensive plan to fix these issues.

---

## Phase 1: Critical API Discrepancies (High Priority)

### Issue 1.1: Non-existent Methods in Documentation

The user guides reference many methods that don't exist in the actual API:

| Documentation Claims | Actual API | Fix Action |
|---------------------|------------|------------|
| `synth.generate_note_audio(note, velocity, duration)` | Doesn't exist | Add to API or update docs |
| `synth.render_midi_file(midi_file, output_file)` | Doesn't exist | Add to API or document CLI |
| `synth.set_engine_for_part(part, engine)` | Doesn't exist | Add to API or remove docs |
| `synth.configure_fm_operator()` | Doesn't exist | Add to API or remove docs |
| `synth.add_modulation_route()` | Doesn't exist | Add to API or remove docs |
| `synth.map_controller()` | Doesn't exist | Add to API or remove docs |
| `synth.get_audio()` | Doesn't exist | Use `generate_audio_block()` |
| `synth.configure_sf2_engine()` | Doesn't exist | Document actual API |
| `synth.disable_effects()` | Doesn't exist | Add or document alternatives |

### Issue 1.2: Correct API That Needs Documentation

The actual ModernXGSynthesizer API includes:

```python
# Working methods that need documentation:
synth.load_soundfont(sf2_path)
synth.set_channel_program(channel, bank, program)
synth.get_channel_info(channel)
synth.get_synthesizer_info()
synth.reset()
synth.cleanup()

# XG-specific methods
synth.set_xg_reverb_type(type)
synth.set_xg_chorus_type(type)
synth.set_xg_variation_type(type)
synth.set_drum_kit(channel, kit_number)
synth.apply_temperament(temperament_name)
synth.set_compatibility_mode(mode)
synth.set_receive_channel(part_id, channel)

# Audio generation
synth.generate_audio_block(block_size)
synth.generate_audio_block_sample_accurate()

# MIDI processing
synth.process_midi_message(message_bytes)
synth.send_midi_message_block(messages)

# XGML (via config_system)
synth.load_xgml_config(path)  # via config_system
synth.load_xgml_string(string)  # via config_system

# Timing/Playback
synth.rewind()
synth.set_current_time(time)
synth.get_current_time()
synth.get_total_duration()
```

---

## Phase 2: Missing Documentation (High Priority)

### Issue 2.1: No Documentation for Main CLI Tools

| Missing | Description |
|---------|-------------|
| `render_midi.py` | Main MIDI rendering CLI - no docs |
| `midi_to_xgml.py` | Conversion tool - no docs |
| `config.yaml` | Configuration file - no docs |

### Issue 2.2: No Documentation for Core Synthesizer

The main `Synthesizer` class (`synth/core/synthesizer.py`) has no dedicated documentation:
- No API reference
- No usage examples
- No relationship to ModernXGSynthesizer explained

### Issue 2.3: Test Documentation Missing

- No test documentation
- No guide on running tests
- No explanation of test structure

---

## Phase 3: Outdated Content (Medium Priority)

### Issue 3.1: Wrong Docker Image Reference

In `INSTALL.md`:
```yaml
# Current (WRONG - already fixed):
docker pull drbye78/xg-synthesizer:latest
```

### Issue 3.2: Example File Paths Don't Exist

Documentation references:
- `examples/simple_piano.xgdsl` - Need to verify exists
- `examples/tutorials/basic-synthesis.md` - Need to verify exists
- `examples/tutorials/advanced-effects.md` - Need to verify exists

### Issue 3.3: Broken Links

- `docs/user/configuration.md` referenced but may not exist
- `docs/developer/architecture.md` referenced but path may be wrong

---

## Phase 4: Structural Issues (Medium Priority)

### Issue 4.1: No Quick Reference Guide

Missing:
- One-page API quick reference
- Common use cases cheatsheet

### Issue 4.2: No Migration Guide

Missing:
- Guide for users migrating from older versions
- Breaking changes documentation

### Issue 4.3: Inconsistent Terminology

- "XGML" vs "XGDSL" used inconsistently
- "ModernXGSynthesizer" vs "Synthesizer" confusion

---

## Implementation Plan

### Priority 1: Fix Critical API Docs (Week 1)

| Task | Files to Update | Effort | Status |
|------|-----------------|--------|--------|
| Document actual ModernXGSynthesizer API | docs/api/modern-xg-synthesizer.md (new) | 2 days | ✅ DONE |
| Add working examples for audio generation | docs/user/getting-started.md | 1 day | ✅ DONE |
| Document CLI tools (render_midi, midi_to_xgml) | docs/tools/ (new) | 2 days | ✅ DONE |
| Fix XGML config examples | docs/XGML_README.md | 1 day | Pending |
| Fix user-guide.md API references | docs/user/user-guide.md | 1 day | ✅ DONE |

### Priority 2: Add Missing Docs (Week 2)

| Task | Files to Update | Effort |
|------|-----------------|--------|
| Document synth/core/synthesizer.py | docs/api/core-synthesizer.md (new) | 1 day |
| Document config.yaml | docs/configuration.md (new) | 1 day |
| Add test documentation | docs/testing.md (new) | 1 day |
| Fix broken links | All docs | 1 day |

### Priority 3: Fix Outdated Content (Week 3)

| Task | Files to Update | Effort |
|------|-----------------|--------|
| Fix Docker image reference | INSTALL.md | 15 min |
| Verify/create example files | examples/ | 1 day |
| Update terminology consistently | All docs | 2 days |

### Priority 4: Structural Improvements (Week 4)

| Task | Files to Update | Effort | Status |
|------|-----------------|--------|--------|
| Create quick reference guide | docs/quick-reference.md (new) | 1 day | ✅ DONE |
| Create migration guide | docs/migration.md (new) | 1 day | Pending |
| Reorganize docs structure | docs/ | 1 day | Pending |

---

## Files to Update

### High Priority
1. `docs/user/getting-started.md` - Fix code examples
2. `docs/user/user-guide.md` - Fix API references
3. `docs/api/overview.md` - Add ModernXGSynthesizer docs

### Medium Priority
4. `INSTALL.md` - Fix Docker image
5. `README.md` - Verify all links work

### Low Priority
6. `CONTRIBUTING.md` - Minor updates
7. `docs/user/troubleshooting.md` - Add new issues

---

## Success Criteria

After fixes:
- [ ] All code examples work with current API
- [ ] No broken links
- [ ] All CLI tools documented
- [ ] Docker image reference correct
- [ ] Terminology consistent
- [ ] Quick reference guide available

---

*Generated: 2026-02-20*
