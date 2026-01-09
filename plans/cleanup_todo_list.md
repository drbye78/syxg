# Synth Package Cleanup - Todo List

## High Priority: Remove Duplicate/Obsolete Files

### 1. Remove SF2 Duplicates
- [ ] Delete `synth/sf2/core/sf2_manager_v2.py`
- [ ] Delete `synth/sf2/core/soundfont.py`
- [ ] Delete `synth/sf2/manager.py`
- [ ] Delete `synth/sf2/enhanced_sf2_manager.py`
- [ ] Verify imports are updated after deletions
- [ ] Run tests to ensure no breakage

### 2. Update Import Statements
- [ ] Check `synth/sf2/__init__.py` for exports
- [ ] Check `synth/sf2/core/__init__.py` for exports
- [ ] Update any files importing from deleted modules
- [ ] Add aliases for backward compatibility if needed

## Medium Priority: Refactoring

### 3. Consolidate Synthesizer Features
- [ ] Review `optimized_xg_synthesizer.py` for unique features
- [ ] Merge performance logging into `modern_xg_synthesizer.py`
- [ ] Update `optimized_xg_synthesizer.py` to use `modern_xg_synthesizer.py` or mark as deprecated

### 4. Extract VCM Effects
- [ ] Create `synth/effects/vcm_effects.py`
- [ ] Move VCM effect functions from `effects_coordinator.py`
- [ ] Update imports in `effects_coordinator.py`

### 5. Consolidate Arpeggiator Implementations
- [ ] Audit arpeggiator files in `synth/jupiter_x/`
- [ ] Audit arpeggiator files in `synth/xg/`
- [ ] Create unified arpeggiator or mark duplicates as deprecated

## Low Priority: Documentation

### 6. Update Documentation
- [ ] Update README.md with current architecture
- [ ] Update `synth/__init__.py` if needed
- [ ] Create architecture diagram in `docs/`

## Testing

### 7. Verification
- [ ] Run existing test suite
- [ ] Verify SF2 loading still works
- [ ] Verify effects processing still works
- [ ] Verify synthesizer initialization still works
