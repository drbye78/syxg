# SF2 Synth Engine - Comprehensive Fix Plan

**Document Version**: 1.0  
**Created**: 2026-02-25  
**Status**: Approved for Implementation  
**Estimated Effort**: 60-80 hours  

---

## Executive Summary

The SF2 synthesis engine is an ambitious implementation targeting full SF2 v2.04 specification compliance. However, comprehensive code analysis has identified **25+ critical bugs** across the engine/region/partial stack that prevent functional audio synthesis.

This document provides a complete remediation plan including:
- Phased bug fixes organized by criticality
- Architecture improvements for maintainability  
- Comprehensive test suite creation
- Documentation updates
- Validation criteria for each phase

**Current Status**: Non-functional - multiple crash-on-start bugs prevent basic operation  
**Target Status**: Production-ready SF2 playback with full spec compliance

---

## Phase 0: Preparation & Infrastructure (4-6 hours)

### Objectives
- Set up development environment for SF2 testing
- Create test infrastructure
- Establish baseline metrics

### Tasks

#### 0.1: Test Infrastructure Setup (2 hours)
**Files to Create**:
- `synth/sf2/tests/__init__.py`
- `synth/sf2/tests/test_sf2_basics.py`
- `synth/sf2/tests/test_sf2_integration.py`
- `synth/sf2/tests/conftest.py`

**Test Fixtures Needed**:
```python
# Minimal valid SF2 file for testing (programmatic generation)
# Small real SF2 file (1-2 MB) for integration tests
# Mock soundfont manager for unit tests
```

**Acceptance Criteria**:
- [ ] pytest can discover and run SF2 tests
- [ ] Basic fixture infrastructure in place
- [ ] Test coverage reporting enabled for SF2 modules

#### 0.2: Development Environment (1 hour)
**Tasks**:
- Document SF2 spec version being targeted (2.04)
- Create reference SF2 file with known-good parameters
- Set up linting rules for SF2 modules

**Acceptance Criteria**:
- [ ] Reference SF2 file created with documented parameters
- [ ] Linting configuration includes SF2-specific rules
- [ ] Type checking enabled for all SF2 modules

#### 0.3: Baseline Assessment (1-2 hours)
**Tasks**:
- Run existing tests to document current failure state
- Create bug tracking spreadsheet
- Prioritize bugs by impact

**Deliverable**: Bug tracking document with severity ratings

---

## Phase 1: Critical Crash Fixes (P0) - 16-20 hours

**Goal**: Make SF2Partial instantiable and basic audio path functional

### 1.1: Fix `__slots__` Mismatch (2 hours)
**File**: `synth/partial/sf2_partial.py`

**Problem**: `__slots__` doesn't include all instance attributes

**Solution Options**:
```python
# Option A: Add all missing attributes to __slots__ (recommended)
__slots__ = [
    # ... existing slots ...
    'vib_lfo_buffer', 'mod_lfo_buffer', 'mod_env_buffer',
    'lfo_pitch_buffer', 'lfo_filter_buffer', 'lfo_volume_buffer', 'lfo_pan_buffer',
    '_pitch_mod_vector', '_filter_mod_vector', '_volume_mod_vector', '_pan_mod_vector',
    '_buffers_allocated', '_mod_env_state', '_vib_lfo_phase', '_mod_lfo_phase',
    '_channel_pan', '_reverb_send', '_chorus_send', '_pan_position',
    # ... etc (complete list below)
]

# Option B: Remove __slots__ entirely (simpler but less memory efficient)
# Remove __slots__ declaration completely
```

**Complete `__slots__` Fix**:
```python
__slots__ = [
    # Existing slots (lines 18-52)
    'synth', 'sample_data', 'phase_step', 'sample_position', 'pitch_ratio',
    'loop_mode', 'loop_start', 'loop_end', 'envelope', 'filter',
    'mod_lfo', 'vib_lfo', 'audio_buffer', 'work_buffer',
    'pitch_mod', 'filter_mod', 'volume_mod', 'active', 'params',
    
    # SF2 Generators - Effects
    'chorus_effects_send', 'reverb_effects_send',
    # Zone Control
    'key_range', 'vel_range', 'exclusive_class', 'sample_modes',
    # Advanced LFO
    'delay_mod_lfo', 'freq_mod_lfo', 'delay_vib_lfo', 'freq_vib_lfo',
    'vib_lfo_to_pan', 'mod_lfo_to_pan',
    # Modulation Envelope
    'mod_env_to_pitch', 'delay_mod_env', 'attack_mod_env', 'hold_mod_env',
    'decay_mod_env', 'sustain_mod_env', 'release_mod_env',
    # Envelope Sensitivity
    'keynum_to_mod_env_hold', 'keynum_to_mod_env_decay',
    'keynum_to_vol_env_hold', 'keynum_to_vol_env_decay',
    # Coarse Sample Addressing
    'start_addrs_coarse_offset', 'end_addrs_coarse_offset',
    'startloop_addrs_coarse_offset', 'endloop_addrs_coarse_offset',
    # Advanced Tuning
    'overriding_root_key', 'scale_tuning',
    # Volume Envelope
    'hold_vol_env',
    
    # MISSING SLOTS (causing crashes)
    # Buffer references
    'vib_lfo_buffer', 'mod_lfo_buffer', 'mod_env_buffer',
    'lfo_pitch_buffer', 'lfo_filter_buffer', 'lfo_volume_buffer', 'lfo_pan_buffer',
    
    # Performance optimization buffers
    '_pitch_mod_vector', '_filter_mod_vector', '_volume_mod_vector', '_pan_mod_vector',
    
    # Allocation state
    '_buffers_allocated',
    
    # LFO phase tracking
    '_vib_lfo_phase', '_mod_lfo_phase',
    
    # Envelope state
    '_mod_env_state',
    
    # Spatial processing
    '_channel_pan', '_reverb_send', '_chorus_send', '_pan_position',
    
    # Additional attributes used in methods
    'pan_mod', 'resonance_mod', 'lfo_rate_mod',
    'aftertouch_mod', 'breath_mod', 'modwheel_mod', 'foot_mod', 'expression_mod',
    'vib_lfo_to_pitch', 'mod_lfo_to_filter', 'mod_lfo_to_volume',
    'freq_mod_lfo', 'freq_vib_lfo', 'delay_mod_lfo', 'delay_vib_lfo',
    'mod_lfo_to_pan', 'vib_lfo_to_pan'
]
```

**Testing**:
```python
def test_sf2_partial_instantiation():
    """SF2Partial should be instantiable without AttributeError"""
    params = create_minimal_params()
    synth = create_mock_synth()
    
    # Should not raise AttributeError
    partial = SF2Partial(params, synth)
    assert partial is not None
```

**Acceptance Criteria**:
- [ ] `SF2Partial` instantiates without errors
- [ ] All attributes in `__init__` are in `__slots__`
- [ ] No `AttributeError` during basic attribute access

---

### 1.2: Fix Constructor Signature Mismatch (2 hours)
**File**: `synth/partial/sf2_region.py`

**Problem**: Line 255 passes `sample_rate` where `ModernXGSynthesizer` expected

**Current Code**:
```python
partial = SF2Partial(partial_params, self.sample_rate)  # WRONG
```

**Fix**:
```python
# SF2Region needs access to synth instance, not just sample_rate
def __init__(
    self,
    descriptor: RegionDescriptor,
    sample_rate: int = 44100,
    soundfont_manager: Optional[Any] = None,
    synth: Optional['ModernXGSynthesizer'] = None  # ADD THIS
):
    super().__init__(descriptor, sample_rate)
    self.synth = synth  # Store synth reference
    # ... rest of init
```

**Then in `_create_partial`**:
```python
def _create_partial(self) -> Optional[Any]:
    # ...
    partial = SF2Partial(partial_params, self.synth)  # CORRECT
```

**Update `SF2Engine.create_region`**:
```python
def create_region(self, descriptor: 'RegionDescriptor', sample_rate: int) -> 'IRegion':
    from ..partial.sf2_region import SF2Region
    # Pass synth instance to region
    return SF2Region(descriptor, sample_rate, self.soundfont_manager, synth=self.synth)
```

**Testing**:
```python
def test_sf2_region_creates_partial():
    """SF2Region should create SF2Partial with correct constructor"""
    region = create_test_region()
    region.note_on(100, 60)
    
    # Should not raise TypeError
    partial = region._create_partial()
    assert partial is not None
```

**Acceptance Criteria**:
- [ ] `SF2Region._create_partial()` doesn't crash
- [ ] `SF2Partial` receives `ModernXGSynthesizer` instance
- [ ] All region creation paths work correctly

---

### 1.3: Implement Missing SoundFont Manager Methods (4 hours)
**File**: `synth/sf2/sf2_soundfont_manager.py`

**Problem**: Three methods called but not implemented

**Implementation**:

```python
def get_sample_info(self, sample_id: int, soundfont_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get sample information (root key, loop points, etc.).
    
    Args:
        sample_id: Sample ID
        soundfont_path: Specific soundfont path (search all if None)
    
    Returns:
        Sample info dictionary or None
    """
    with self._lock:
        for filepath in self.file_order:
            if filepath in self.loaded_files:
                soundfont = self.loaded_files[filepath]
                if hasattr(soundfont, 'get_sample_info'):
                    info = soundfont.get_sample_info(sample_id)
                    if info:
                        return info
    return None


def get_sample_loop_info(self, sample_id: int, soundfont_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get sample loop information.
    
    Args:
        sample_id: Sample ID
        soundfont_path: Specific soundfont path (search all if None)
    
    Returns:
        Loop info dictionary or None
    """
    with self._lock:
        for filepath in self.file_order:
            if filepath in self.loaded_files:
                soundfont = self.loaded_files[filepath]
                if hasattr(soundfont, 'get_sample_loop_info'):
                    info = soundfont.get_sample_loop_info(sample_id)
                    if info:
                        return info
    return None


def get_zone(self, region_id: int, bank: int = 0, program: int = 0) -> Optional[Any]:
    """
    Get SF2Zone by region ID for a specific preset.
    
    Args:
        region_id: Zone/region identifier
        bank: MIDI bank number
        program: MIDI program number
    
    Returns:
        SF2Zone instance or None
    """
    with self._lock:
        for filepath in self.file_order:
            if filepath in self.loaded_files:
                soundfont = self.loaded_files[filepath]
                if hasattr(soundfont, 'get_zone'):
                    zone = soundfont.get_zone(bank, program, region_id)
                    if zone:
                        return zone
    return None
```

**Also implement in `SF2SoundFont`** (`synth/sf2/sf2_soundfont.py`):

```python
def get_sample_info(self, sample_id: int) -> Optional[Dict[str, Any]]:
    """Get sample info from file loader"""
    if not self._is_loaded or not self.file_loader:
        return None
    
    if hasattr(self.file_loader, 'parse_sample_header_at_index'):
        header = self.file_loader.parse_sample_header_at_index(sample_id)
        if header:
            return {
                'name': header.get('name', ''),
                'original_pitch': header.get('original_pitch', 60),
                'pitch_correction': header.get('pitch_correction', 0),
                'sample_rate': header.get('sample_rate', 44100),
                'start': header.get('start', 0),
                'end': header.get('end', 0),
            }
    return None


def get_sample_loop_info(self, sample_id: int) -> Optional[Dict[str, Any]]:
    """Get loop info from sample header"""
    if not self._is_loaded or not self.file_loader:
        return None
    
    header = self.get_sample_info(sample_id)
    if header:
        return {
            'start': header.get('start', 0),
            'end': header.get('end', 0),
            'mode': 0  # Would need to extract from sample header
        }
    return None


def get_zone(self, bank: int, program: int, zone_id: int) -> Optional['SF2Zone']:
    """Get zone from preset"""
    preset = self._get_or_load_preset(bank, program)
    if not preset:
        return None
    
    if zone_id < len(preset.zones):
        return preset.zones[zone_id]
    return None
```

**Testing**:
```python
def test_soundfont_manager_methods():
    """SoundFont manager should have required methods"""
    manager = SF2SoundFontManager()
    
    # Methods should exist
    assert hasattr(manager, 'get_sample_info')
    assert hasattr(manager, 'get_sample_loop_info')
    assert hasattr(manager, 'get_zone')
    
    # Should return None gracefully when no soundfonts loaded
    assert manager.get_sample_info(0) is None
    assert manager.get_sample_loop_info(0) is None
    assert manager.get_zone(0) is None
```

**Acceptance Criteria**:
- [ ] All three methods exist and are callable
- [ ] Methods return `None` gracefully when data unavailable
- [ ] Methods return correct data when soundfonts loaded
- [ ] No `AttributeError` in `SF2Region` when calling these methods

---

### 1.4: Fix Parameter Structure Mismatch (4 hours)
**Files**: `synth/partial/sf2_region.py`, `synth/partial/sf2_partial.py`

**Problem**: Region creates flat structure, Partial expects nested structure

**Solution**: Standardize on nested structure (matches SF2 spec organization)

**Update `SF2Region._build_partial_params_from_generators()`**:

```python
def _build_partial_params_from_generators(self) -> Dict[str, Any]:
    """Build partial parameters from SF2 generators with correct nested structure."""
    
    params = {
        # Sample data
        'sample_data': self._sample_data,
        'note': self.current_note,
        'velocity': self.current_velocity,
        'original_pitch': self._root_key,
        
        # Loop info (nested)
        'loop': {
            'mode': self._get_generator_value(51, 0),  # sampleMode
            'start': self._loop_start,
            'end': self._loop_end
        },
        
        # Volume envelope (nested)
        'amp_envelope': {
            'delay': self._timecents_to_seconds(self._get_generator_value(8, -12000)),
            'attack': self._timecents_to_seconds(self._get_generator_value(9, -12000)),
            'hold': self._timecents_to_seconds(self._get_generator_value(10, -12000)),
            'decay': self._timecents_to_seconds(self._get_generator_value(11, -12000)),
            'sustain': self._get_generator_value(12, 0) / 1000.0,
            'release': self._timecents_to_seconds(self._get_generator_value(13, -12000))
        },
        
        # Modulation envelope (nested)
        'mod_envelope': {
            'delay': self._timecents_to_seconds(self._get_generator_value(14, -12000)),
            'attack': self._timecents_to_seconds(self._get_generator_value(15, -12000)),
            'hold': self._timecents_to_seconds(self._get_generator_value(16, -12000)),
            'decay': self._timecents_to_seconds(self._get_generator_value(17, -12000)),
            'sustain': self._get_generator_value(18, 0) / 1000.0,
            'release': self._timecents_to_seconds(self._get_generator_value(19, -12000)),
            'to_pitch': self._get_generator_value(20, 0) / 1200.0
        },
        
        # Mod LFO (nested)
        'mod_lfo': {
            'delay': self._timecents_to_seconds(self._get_generator_value(21, -12000)),
            'frequency': self._cents_to_frequency(self._get_generator_value(22, 0)),
            'to_volume': self._get_generator_value(23, 0) / 960.0,
            'to_filter': self._get_generator_value(24, 0) / 1200.0,
            'to_pitch': self._get_generator_value(25, 0) / 1200.0
        },
        
        # Vib LFO (nested)
        'vib_lfo': {
            'delay': self._timecents_to_seconds(self._get_generator_value(26, -12000)),
            'frequency': self._cents_to_frequency(self._get_generator_value(27, 0)),
            'to_pitch': self._get_generator_value(28, 0) / 1200.0
        },
        
        # Filter (nested)
        'filter': {
            'cutoff': self._cents_to_frequency(self._get_generator_value(29, 13500)),
            'resonance': self._get_generator_value(30, 0) / 10.0,
            'type': 'lowpass'
        },
        
        # Effects (nested)
        'effects': {
            'reverb_send': self._get_generator_value(32, 0) / 1000.0,
            'chorus_send': self._get_generator_value(33, 0) / 1000.0,
            'pan': self._get_generator_value(34, 0) / 500.0
        },
        
        # Pitch modulation (nested)
        'pitch_modulation': {
            'coarse_tune': self._get_generator_value(48, 0),
            'fine_tune': self._get_generator_value(49, 0) / 100.0,
            'scale_tuning': self._get_generator_value(52, 100) / 100.0
        },
        
        # Key tracking
        'key_tracking': {
            'to_mod_env_hold': self._get_generator_value(35, 0),
            'to_mod_env_decay': self._get_generator_value(36, 0),
            'to_vol_env_hold': self._get_generator_value(37, 0),
            'to_vol_env_decay': self._get_generator_value(38, 0)
        },
        
        # Modulators list
        'modulators': self._modulators
    }
    
    return params
```

**Update `SF2Partial._load_sf2_parameters()`** to handle both structures (backward compatibility):

```python
def _load_sf2_parameters(self):
    """Load SF2 parameters with support for both flat and nested structures."""
    
    # Get sample data
    sample_data = self.params.get('sample_data')
    if sample_data is not None and len(sample_data) > 0:
        self.sample_data = np.asarray(sample_data, dtype=np.float32)
        self._load_loop_info()
        self._load_pitch_info()
    
    # Load envelope parameters (try nested first, then flat)
    if 'amp_envelope' in self.params:
        amp_env = self.params['amp_envelope']
        self.envelope.update_parameters(
            delay=amp_env.get('delay', 0.0),
            attack=amp_env.get('attack', 0.01),
            hold=amp_env.get('hold', 0.0),
            decay=amp_env.get('decay', 0.3),
            sustain=amp_env.get('sustain', 0.7),
            release=amp_env.get('release', 0.5)
        )
    else:
        # Fallback to flat structure
        self.envelope.update_parameters(
            delay=self.params.get('amp_delay', 0.0),
            attack=self.params.get('amp_attack', 0.01),
            hold=self.params.get('amp_hold', 0.0),
            decay=self.params.get('amp_decay', 0.3),
            sustain=self.params.get('amp_sustain', 0.7),
            release=self.params.get('amp_release', 0.5)
        )
    
    # Load filter parameters
    if 'filter' in self.params:
        filter_params = self.params['filter']
        self.filter.set_parameters(
            cutoff=filter_params.get('cutoff', 20000.0),
            resonance=filter_params.get('resonance', 0.0),
            filter_type=filter_params.get('type', 'lowpass')
        )
    else:
        self.filter.set_parameters(
            cutoff=self.params.get('filter_cutoff', 20000.0),
            resonance=self.params.get('filter_resonance', 0.0),
            filter_type='lowpass'
        )
    
    # Load LFO parameters (similar pattern)
    # ... etc for all nested structures
```

**Testing**:
```python
def test_parameter_structure_compatibility():
    """SF2Partial should accept both nested and flat parameter structures"""
    
    # Test nested structure
    nested_params = create_nested_params()
    partial1 = SF2Partial(nested_params, synth)
    assert partial1.envelope is not None
    
    # Test flat structure (backward compatibility)
    flat_params = create_flat_params()
    partial2 = SF2Partial(flat_params, synth)
    assert partial2.filter is not None
```

**Acceptance Criteria**:
- [ ] `SF2Region` produces correctly nested parameter structure
- [ ] `SF2Partial` accepts nested structure
- [ ] `SF2Partial` maintains backward compatibility with flat structure
- [ ] All generator values correctly transferred to partial

---

### 1.5: Fix Sample Data Chunk Path (3 hours)
**File**: `synth/sf2/sf2_file_loader.py`

**Problem**: Standard SF2 has `LIST sdta → smpl/sm24`, but code looks for top-level `smpl`

**Fix in `_parse_riff_structure_lazy()`**:

```python
if list_type == 'sdta':
    # Parse nested chunks within LIST sdta to find smpl and sm24
    sdta_start = self._file_handle.tell()
    list_data_size = actual_chunk_size
    
    # Parse nested chunks
    nested_pos = 0
    while nested_pos < list_data_size - 8:
        self._file_handle.seek(sdta_start + nested_pos)
        nested_header = self._file_handle.read(8)
        if len(nested_header) < 8:
            break
        
        nested_id, nested_size = struct.unpack("<4sI", nested_header)
        nested_id_str = nested_id.decode("ascii", errors="ignore")
        
        if nested_id_str in ['smpl', 'sm24']:
            # Store location of sample data chunks
            chunk_start = sdta_start + nested_pos + 8
            self.sample_data_chunks[nested_id_str] = (chunk_start, nested_size)
        
        # Skip to next chunk
        self._file_handle.seek(nested_size, 1)
        if nested_size % 2 == 1:
            self._file_handle.seek(1, 1)
        
        nested_pos += 8 + nested_size
        if nested_size % 2 == 1:
            nested_pos += 1
```

**Fix in `get_sample_data()`**:

```python
def get_sample_data(self, sample_id: int) -> Optional[np.ndarray]:
    """Get sample data with correct chunk path handling."""
    
    # Try direct chunk access first (for non-standard layout)
    if 'smpl' in self.sample_data_chunks:
        return self._read_16bit_sample_data_from_file(...)
    
    # Try LIST_sdta path (standard layout)
    if 'LIST_sdta' in self.sample_data_chunks:
        # Parse sdta to find smpl offset
        sdta_offset, sdta_size = self.sample_data_chunks['LIST_sdta']
        smpl_offset = self._find_smpl_in_sdta(sdta_offset, sdta_size)
        if smpl_offset:
            return self._read_16bit_sample_data_from_file(...)
    
    return None
```

**Add helper method**:

```python
def _find_smpl_in_sdta(self, sdta_offset: int, sdta_size: int) -> Optional[int]:
    """Find smpl chunk offset within LIST sdta."""
    # Parse sdta structure to locate smpl chunk
    # Return offset or None
```

**Testing**:
```python
def test_standard_sf2_layout():
    """Should load samples from standard LIST sdta layout"""
    loader = SF2FileLoader('test_standard.sf2')
    loader.load_file()
    
    # Should find smpl chunk
    assert 'smpl' in loader.sample_data_chunks or 'LIST_sdta' in loader.sample_data_chunks
    
    # Should load sample data
    data = loader.get_sample_data(0)
    assert data is not None
    assert len(data) > 0
```

**Acceptance Criteria**:
- [ ] Standard SF2 files with `LIST sdta` layout load correctly
- [ ] Non-standard SF2 files with top-level `smpl` still work
- [ ] 24-bit samples load from `sm24` chunk
- [ ] Sample data matches header specifications

---

### 1.6: Fix SF2Engine.generate_samples() (3 hours)
**File**: `synth/engine/sf2_engine.py`

**Problem**: Method doesn't look up SF2 presets, always returns silence

**Complete Rewrite**:

```python
def generate_samples(
    self,
    program: int,
    bank: int,
    note: int,
    velocity: int,
    block_size: int,
    modulation: Dict
) -> np.ndarray:
    """
    Generate SF2 samples with proper preset/zone lookup.
    
    Args:
        program: MIDI program number
        bank: MIDI bank number
        note: MIDI note number
        velocity: MIDI velocity
        block_size: Number of samples to generate
        modulation: Global modulation values
    
    Returns:
        Stereo audio buffer (block_size * 2,) as float32
    """
    # Get preset info with all regions
    preset_info = self.get_preset_info(bank, program)
    if not preset_info:
        logger.warning(f"SF2 preset not found: {bank}:{program}")
        return np.zeros(block_size * 2, dtype=np.float32)
    
    # Find matching regions for this note/velocity
    matching_regions = []
    for descriptor in preset_info.region_descriptors:
        if descriptor.should_play_for_note(note, velocity):
            matching_regions.append(descriptor)
    
    if not matching_regions:
        logger.debug(f"No SF2 regions match note {note} vel {velocity}")
        return np.zeros(block_size * 2, dtype=np.float32)
    
    # Create and initialize regions for all matching descriptors
    audio_output = np.zeros(block_size * 2, dtype=np.float32)
    
    for descriptor in matching_regions:
        try:
            # Create region
            region = self.create_region(descriptor, self.sample_rate)
            
            # Load sample data
            if not self.load_sample_for_region(region):
                logger.warning(f"Failed to load sample for region {descriptor.region_id}")
                continue
            
            # Trigger note
            if not region.note_on(velocity, note):
                continue
            
            # Generate samples
            region_audio = region.generate_samples(block_size, modulation)
            
            # Mix into output (simple sum for now, should apply gain)
            audio_output += region_audio
            
        except Exception as e:
            logger.error(f"Error generating SF2 samples: {e}")
            continue
    
    return audio_output
```

**Testing**:
```python
def test_sf2_engine_generates_audio():
    """SF2Engine should generate audio, not silence"""
    engine = SF2Engine(sf2_file='test.sf2')
    
    audio = engine.generate_samples(
        program=0, bank=0, note=60, velocity=100,
        block_size=1024, modulation={}
    )
    
    # Should not be all zeros
    assert not np.all(audio == 0.0)
    assert len(audio) == 2048  # block_size * 2
```

**Acceptance Criteria**:
- [ ] Engine looks up presets by bank/program
- [ ] Engine finds matching regions for note/velocity
- [ ] Engine loads sample data for regions
- [ ] Engine generates non-silent audio output
- [ ] Multiple regions layer correctly

---

## Phase 2: High Priority Fixes (P1) - 14-18 hours

**Goal**: Audio plays with correct parameters matching SF2 specification

### 2.1: Fix Generator ID Mappings (4 hours)
**Files**: `synth/partial/sf2_partial.py`, `synth/sf2/sf2_constants.py`

**Create Reference Mapping Table**:

```python
# Correct SF2 Generator IDs per SF2 2.04 specification
CORRECT_SF2_GENERATORS = {
    # Volume Envelope
    8: 'volEnvDelay',
    9: 'volEnvAttack',
    10: 'volEnvHold',
    11: 'volEnvDecay',
    12: 'volEnvSustain',
    13: 'volEnvRelease',
    
    # Modulation Envelope
    14: 'modEnvDelay',
    15: 'modEnvAttack',
    16: 'modEnvHold',
    17: 'modEnvDecay',
    18: 'modEnvSustain',
    19: 'modEnvRelease',
    20: 'modEnvToPitch',
    
    # Mod LFO
    21: 'modLfoDelay',
    22: 'modLfoFreq',
    23: 'modLfoToVol',
    24: 'modLfoToFilter',
    25: 'modLfoToPitch',
    
    # Vib LFO
    26: 'vibLfoDelay',
    27: 'vibLfoFreq',
    28: 'vibLfoToPitch',
    
    # Filter
    29: 'initialFilterFc',
    30: 'initialFilterQ',
    
    # Effects
    31: 'unused1',
    32: 'reverbEffectsSend',
    33: 'chorusEffectsSend',
    34: 'pan',
    
    # Key Tracking
    35: 'keynumToModEnvHold',
    36: 'keynumToModEnvDecay',
    37: 'keynumToVolEnvHold',
    38: 'keynumToVolEnvDecay',
    
    # Instrument Controls
    41: 'instrumentControls',
    42: 'keyRange',
    43: 'velRange',
    
    # Loop Addresses
    44: 'startloopAddrsCoarse',
    45: 'endloopAddrsCoarse',
    46: 'startAddrsCoarse',
    47: 'endAddrsCoarse',
    
    # Sample Information
    50: 'sampleID',
    51: 'sampleModes',
    52: 'scaleTuning',
    53: 'exclusiveClass',
    
    # Fine Sample Addresses
    54: 'startAddrsOffset',
    55: 'endAddrsOffset',
    56: 'startloopAddrsOffset',
    57: 'endloopAddrsOffset',
}
```

**Fix `SF2Partial._load_sf2_generator_values()`**:

```python
def _load_sf2_generator_values(self):
    """Load SF2 generator values with CORRECT generator IDs."""
    
    generators = self.params.get('generators', {})
    
    # Effects (CORRECT IDs: 32, 33)
    self.chorus_effects_send = generators.get(33, 0) / 1000.0
    self.reverb_effects_send = generators.get(32, 0) / 1000.0
    
    # Key/Vel ranges (CORRECT IDs: 42, 43)
    self.key_range = self._parse_key_range(generators.get(42, (0, 127)))
    self.vel_range = self._parse_vel_range(generators.get(43, (0, 127)))
    
    # Sample modes and exclusive class (CORRECT IDs: 51, 53)
    self.sample_modes = generators.get(51, 0)
    self.exclusive_class = generators.get(53, 0)
    
    # Mod envelope to pitch (CORRECT ID: 20)
    self.mod_env_to_pitch = generators.get(20, 0) / 1200.0
    
    # Mod envelope times (CORRECT IDs: 14-19)
    self.delay_mod_env = self._convert_time_cent(14, generators.get(14, -12000))
    self.attack_mod_env = self._convert_time_cent(15, generators.get(15, -12000))
    self.hold_mod_env = self._convert_time_cent(16, generators.get(16, -12000))
    self.decay_mod_env = self._convert_time_cent(17, generators.get(17, -12000))
    self.sustain_mod_env = generators.get(18, 0) / 1000.0
    self.release_mod_env = self._convert_time_cent(19, generators.get(19, -12000))
    
    # ... continue fixing all generator mappings
```

**Update `SF2_GENERATORS` constant** in `sf2_constants.py`:

```python
SF2_GENERATORS = {
    # ... verify all entries against spec ...
    32: {"name": "reverbEffectsSend", "description": "Reverb send level", "default": 0},
    33: {"name": "chorusEffectsSend", "description": "Chorus send level", "default": 0},
    42: {"name": "keyRange", "description": "MIDI key range", "default": (0, 127)},
    43: {"name": "velRange", "description": "Velocity range", "default": (0, 127)},
    50: {"name": "sampleID", "description": "Sample index", "default": 0},
    51: {"name": "sampleModes", "description": "Sample loop modes", "default": 0},
    53: {"name": "exclusiveClass", "description": "Exclusive class", "default": 0},
    # ... etc
}
```

**Testing**:
```python
def test_generator_id_mappings():
    """Generator IDs should match SF2 2.04 specification"""
    
    # Test reverb/chorus
    params = create_params_with_generators({32: 500, 33: 300})
    partial = SF2Partial(params, synth)
    
    assert partial.reverb_effects_send == 0.5  # 500/1000
    assert partial.chorus_effects_send == 0.3  # 300/1000
    
    # Test sample ID
    params = create_params_with_generators({50: 42})
    # Should use sample index 42, not 53
```

**Acceptance Criteria**:
- [ ] All generator IDs match SF2 2.04 spec
- [ ] `SF2_GENERATORS` constant is accurate
- [ ] Generator values map to correct parameters
- [ ] No warnings about unknown generator IDs

---

### 2.2: Fix `frequency_to_cents` Formula (1 hour)
**File**: `synth/sf2/sf2_constants.py`

**Current (WRONG)**:
```python
def frequency_to_cents(frequency: float, base_freq: float = 440.0) -> int:
    ratio = frequency / base_freq
    return int(1200.0 * (ratio ** (1.0 / 2.0)).real)  # WRONG: sqrt instead of log2
```

**Fix**:
```python
def frequency_to_cents(frequency: float, base_freq: float = 440.0) -> int:
    """
    Convert frequency to cents using correct logarithmic formula.
    
    Args:
        frequency: Frequency in Hz
        base_freq: Reference frequency (default 440.0 Hz = A4)
    
    Returns:
        Cents value (integer)
    """
    import math
    
    if frequency <= 0 or base_freq <= 0:
        return 0
    
    ratio = frequency / base_freq
    # Correct formula: 1200 * log2(ratio)
    return int(1200.0 * math.log2(ratio))
```

**Also verify `cents_to_frequency`**:

```python
def cents_to_frequency(cents: int, base_freq: float = 440.0) -> float:
    """Convert cents to frequency (inverse of frequency_to_cents)."""
    return base_freq * (2.0 ** (cents / 1200.0))
```

**Testing**:
```python
def test_frequency_cents_conversion():
    """Frequency/cents conversion should be mathematically correct"""
    
    # 440 Hz = 0 cents (reference)
    assert frequency_to_cents(440.0) == 0
    
    # 880 Hz = 1200 cents (one octave up)
    assert frequency_to_cents(880.0) == 1200
    
    # 220 Hz = -1200 cents (one octave down)
    assert frequency_to_cents(220.0) == -1200
    
    # Round-trip should be identity
    for freq in [220, 440, 880, 1760]:
        cents = frequency_to_cents(freq)
        recovered = cents_to_frequency(cents)
        assert abs(recovered - freq) < 0.1  # Allow small floating point error
```

**Acceptance Criteria**:
- [ ] `frequency_to_cents` uses correct logarithmic formula
- [ ] Round-trip conversion is identity
- [ ] Edge cases (zero, negative) handled gracefully
- [ ] All tests pass

---

### 2.3: Fix `sampleID` Generator in Data Model (2 hours)
**File**: `synth/sf2/sf2_data_model.py`

**Current (WRONG)**:
```python
elif gen_type == 53:  # sampleID (instrument level)
    self.sample_id = gen_amount
```

**Fix**:
```python
elif gen_type == 50:  # sampleID (instrument level) - CORRECT ID
    self.sample_id = gen_amount
elif gen_type == 53:  # exclusiveClass
    self.exclusive_class = gen_amount
```

**Also update any other references**:

```bash
# Search for all uses of generator 53
grep -rn "gen_type.*53" synth/sf2/
grep -rn "generator.*53" synth/sf2/
```

**Testing**:
```python
def test_sample_id_generator():
    """sampleID generator (50) should set sample_id correctly"""
    
    zone = SF2Zone('instrument')
    zone.add_generator(50, 42)  # sampleID = 42
    
    assert zone.sample_id == 42
    
    # Generator 53 should set exclusiveClass, not sample_id
    zone2 = SF2Zone('instrument')
    zone2.add_generator(53, 5)  # exclusiveClass = 5
    
    assert zone2.exclusive_class == 5
    assert zone2.sample_id is None  # Not set
```

**Acceptance Criteria**:
- [ ] Generator 50 sets `sample_id`
- [ ] Generator 53 sets `exclusive_class`
- [ ] All zone creation uses correct generator IDs

---

### 2.4: Fix Modulation Engine API (3 hours)
**File**: `synth/sf2/sf2_modulation_engine.py`

**Problem**: `SF2SoundFont` calls `create_zone_engine()` which doesn't exist

**Option A: Implement Missing API** (Recommended if modulation is needed):

```python
class SF2ModulationEngine:
    """SF2 modulation engine with zone engine support."""
    
    def create_zone_engine(
        self,
        zone_id: str,
        instrument_gens: Dict[int, int],
        instrument_mods: List[Dict],
        preset_gens: Dict[int, int],
        preset_mods: List[Dict]
    ) -> 'SF2ZoneEngine':
        """
        Create zone engine for modulation processing.
        
        Args:
            zone_id: Zone identifier
            instrument_gens: Instrument-level generators
            instrument_mods: Instrument-level modulators
            preset_gens: Preset-level generators (global)
            preset_mods: Preset-level modulators
        
        Returns:
            SF2ZoneEngine instance
        """
        return SF2ZoneEngine(
            zone_id, instrument_gens, instrument_mods,
            preset_gens, preset_mods
        )
```

**Create `SF2ZoneEngine` class**:

```python
class SF2ZoneEngine:
    """Zone-specific modulation engine."""
    
    def __init__(
        self,
        zone_id: str,
        instrument_gens: Dict[int, int],
        instrument_mods: List[Dict],
        preset_gens: Dict[int, int],
        preset_mods: List[Dict]
    ):
        self.zone_id = zone_id
        self.instrument_gens = instrument_gens
        self.instrument_mods = instrument_mods
        self.preset_gens = preset_gens
        self.preset_mods = preset_mods
        
        # Merge generators (instrument overrides preset)
        self.merged_gens = preset_gens.copy()
        self.merged_gens.update(instrument_gens)
    
    def get_modulated_parameters(
        self,
        note: int,
        velocity: int,
        controllers: Optional[Dict[int, float]] = None
    ) -> Dict[str, float]:
        """
        Get modulated parameters for given note/velocity.
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
            controllers: Optional controller values
        
        Returns:
            Dictionary of modulated parameter values
        """
        params = {}
        
        # Apply generators
        for gen_type, value in self.merged_gens.items():
            param_name = SF2_GENERATORS.get(gen_type, {}).get('name', f'gen_{gen_type}')
            params[param_name] = value
        
        # Apply modulators
        # ... modulation matrix processing ...
        
        return params
```

**Option B: Remove Unused Code** (Simpler if modulation not yet needed):

Comment out or remove the modulation engine calls in `SF2SoundFont._process_zones_to_parameters()`:

```python
# TEMPORARILY DISABLED - Modulation engine not yet implemented
# zone_engine = self.modulation_engine.create_zone_engine(...)
# params = zone_engine.get_modulated_parameters(note, velocity)

# Use direct generator values instead
params = self._extract_generators_from_zone(zone, note, velocity)
```

**Recommendation**: Start with Option B to unblock audio path, then implement Option A in Phase 3.

**Acceptance Criteria**:
- [ ] No `AttributeError` when processing zones
- [ ] Modulation processing either works or is gracefully disabled
- [ ] Clear TODO comments for future implementation

---

### 2.5: Fix Import Path Errors (1 hour)
**File**: `synth/engine/sf2_engine.py`

**Current (WRONG)**:
```python
# Line 452
from .partial.sf2_region import SF2Region  # Wrong relative path
```

**Fix**:
```python
from ..partial.sf2_region import SF2Region  # Correct: go up to synth/, then down to partial/
```

**Audit all imports**:

```bash
# Find all potentially wrong imports
grep -rn "from \.partial" synth/engine/
grep -rn "from \.sf2" synth/partial/
```

**Testing**:
```python
def test_sf2_engine_imports():
    """SF2Engine should import without errors"""
    
    # Should not raise ImportError
    from synth.engine.sf2_engine import SF2Engine
    assert SF2Engine is not None
```

**Acceptance Criteria**:
- [ ] All imports use correct relative paths
- [ ] Module imports without errors
- [ ] No circular import issues

---

### 2.6: Fix Zone Cache Unload Dead Code (2 hours)
**File**: `synth/sf2/sf2_soundfont.py`

**Current (Dead Code)**:
```python
def unload(self) -> None:
    with self._lock:
        self.presets.clear()  # Cleared before iteration!
        self.instruments.clear()
        
        # This never executes - presets already cleared
        if self.zone_cache_manager:
            zones_to_remove = []
            for preset_key in self.presets.keys():  # EMPTY!
                ...
```

**Fix**:
```python
def unload(self) -> None:
    """Unload soundfont and clear all associated caches."""
    with self._lock:
        # Collect keys BEFORE clearing
        preset_keys = list(self.presets.keys())
        instrument_indices = list(self.instruments.keys())
        
        # Clear zone caches for this soundfont
        if self.zone_cache_manager:
            # Remove preset zones
            for bank, program in preset_keys:
                try:
                    self.zone_cache_manager.remove_preset_zones(bank, program)
                except AttributeError:
                    pass  # Method may not exist yet
        
        # Now clear local caches
        self.presets.clear()
        self.instruments.clear()
        self.samples.clear()
        
        self._is_loaded = False
```

**Add missing methods to `SF2ZoneCacheManager`** (`synth/sf2/sf2_zone_cache.py`):

```python
def remove_preset_zones(self, bank: int, program: int) -> None:
    """Remove cached zones for a preset."""
    key = (bank, program)
    if key in self.preset_cache:
        del self.preset_cache[key]


def remove_instrument_zones(self, instrument_index: int) -> None:
    """Remove cached zones for an instrument."""
    if instrument_index in self.instrument_cache:
        del self.instrument_cache[instrument_index]
```

**Testing**:
```python
def test_soundfont_unload_clears_cache():
    """Unloading soundfont should clear zone caches"""
    
    manager = SF2SoundFontManager()
    manager.load_soundfont('test.sf2')
    
    # Access preset to cache zones
    params = manager.get_program_parameters(0, 0, 60, 100)
    assert params is not None
    
    # Unload
    soundfont = manager.loaded_files['test.sf2']
    soundfont.unload()
    
    # Cache should be cleared
    assert len(soundfont.presets) == 0
```

**Acceptance Criteria**:
- [ ] Zone caches cleared on unload
- [ ] No resource leaks
- [ ] Memory freed correctly

---

## Phase 3: Medium Priority Fixes (P2) - 12-16 hours

**Goal**: Performance, resource management, and audio quality improvements

### 3.1: Fix Buffer Pool Memory Leaks (3 hours)
### 3.2: Enable Mip-Map Anti-Aliasing (3 hours)
### 3.3: Fix AVL Tree Performance (2 hours)
### 3.4: Complete Loop Mode Support (2 hours)
### 3.5: Fix Timecents Conversion Edge Cases (1 hour)
### 3.6: Add Input Validation (2 hours)
### 3.7: Fix Stereo Sample Handling (2 hours)

---

## Phase 4: Architecture Improvements - 16-20 hours

### 4.1: Create ZoneEngine Object (6 hours)
### 4.2: Implement Proper Voice Layering (4 hours)
### 4.3: Add Render-Ready API (4 hours)
### 4.4: Consolidate Conversion Functions (2 hours)

---

## Phase 5: Testing & Documentation - 12-16 hours

### 5.1: Complete Test Suite (8 hours)
### 5.2: Update Documentation (4 hours)
### 5.3: Create SF2 Compliance Report (2 hours)

---

## Test Suite Structure

```
synth/sf2/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_sf2_basics.py       # Unit tests for core components
├── test_sf2_file_loader.py  # File parsing tests
├── test_sf2_soundfont.py    # SoundFont loading tests
├── test_sf2_partial.py      # Partial creation and rendering
├── test_sf2_region.py       # Region matching and rendering
├── test_sf2_engine.py       # Engine integration tests
├── test_generator_mappings.py # Generator ID validation
├── test_modulation.py       # Modulation engine tests
└── test_integration.py      # Full pipeline tests
```

---

## Documentation Updates

### Files to Create/Update:
1. `synth/sf2/README.md` - SF2 module overview
2. `synth/sf2/SF2_SPEC_COMPLIANCE.md` - Specification compliance status
3. `synth/sf2/ARCHITECTURE.md` - Architecture documentation
4. `synth/sf2/CHANGELOG.md` - Change history
5. Update main `README.md` with SF2 status

---

## Validation Criteria

### Phase 1 Completion:
- [ ] All P0 tests pass
- [ ] SF2Partial instantiates without errors
- [ ] Basic audio path functional (non-silent output)
- [ ] No crash-on-start bugs

### Phase 2 Completion:
- [ ] All P1 tests pass
- [ ] Generator mappings verified against spec
- [ ] Parameter structures consistent
- [ ] Audio matches SF2 file parameters

### Phase 3 Completion:
- [ ] All P2 tests pass
- [ ] No memory leaks in extended playback
- [ ] Anti-aliasing functional
- [ ] Performance meets targets

### Phase 4 Completion:
- [ ] Architecture improvements implemented
- [ ] ZoneEngine functional
- [ ] Voice layering works correctly
- [ ] API is clean and documented

### Phase 5 Completion:
- [ ] Test coverage > 80% for SF2 modules
- [ ] All documentation updated
- [ ] Compliance report complete
- [ ] Ready for production use

---

## Risk Mitigation

### High-Risk Areas:
1. **Sample I/O** - Test with multiple SF2 files
2. **Modulation** - Start simple, add complexity gradually
3. **Performance** - Profile early and often
4. **Spec Compliance** - Validate against reference implementation

### Rollback Plan:
- Maintain working branch at each phase completion
- Feature flags for incomplete functionality
- Fallback to simple rendering path if complex path fails

---

## Success Metrics

### Functional:
- Audio renders without crashes
- Parameters match SF2 file specifications
- All loop modes work correctly
- Modulation functional

### Performance:
- < 10ms latency at 44.1kHz/512 block size
- < 5% CPU usage for 64-voice polyphony
- No memory leaks in 1-hour stress test

### Quality:
- > 80% test coverage
- Zero critical bugs
- Documentation complete

---

## Appendix A: Complete `__slots__` Fix

[Full `__slots__` declaration as shown in section 1.1]

---

## Appendix B: Generator ID Reference Table

[Complete SF2 2.04 generator mapping table]

---

## Appendix C: Test SF2 File Specification

[Minimal SF2 file structure for testing]

---

**End of Document**
