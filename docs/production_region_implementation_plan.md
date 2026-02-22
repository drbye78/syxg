# Production-Grade Region Implementation Plan
## Replacing Stubs with Full Implementations

**Document Version:** 1.0  
**Date:** 2026-02-22  
**Status:** Planning Phase  
**Goal:** Replace all stub region implementations with production-grade solutions

---

## Executive Summary

The current architecture refactor introduced a unified region-based interface across all synthesis engines. While stub implementations allow the system to function, production-grade implementations are needed for:

1. **Engine-specific optimizations** - Each engine has unique capabilities
2. **Full parameter control** - Stubs don't expose engine-specific parameters
3. **Performance optimization** - Stubs use generic Region base class
4. **Feature completeness** - Some engine features inaccessible through stubs

This plan outlines the implementation of production-grade region classes for all 13 synthesis engines.

---

## Implementation Priority

### **P0: Critical (Core Synthesis Engines)**

| Engine | Priority | Reason | Effort |
|--------|----------|--------|--------|
| **WavetableRegion** | P0 | Most used after SF2/FM | High |
| **AdditiveRegion** | P0 | Core synthesis method | High |
| **PhysicalRegion** | P0 | Physical modeling core | Medium |

### **P1: Important (Specialized Engines)**

| Engine | Priority | Reason | Effort |
|--------|----------|--------|--------|
| **GranularRegion** | P1 | Time-stretching/pitch-shifting | High |
| **FDSPRegion** | P1 | Vocal synthesis | Medium |
| **ANRegion** | P1 | Analog modeling (Motif) | Medium |

### **P2: Enhancement (Advanced Features)**

| Engine | Priority | Reason | Effort |
|--------|----------|--------|--------|
| **SpectralRegion** | P2 | FFT-based processing | Very High |
| **AdvancedPhysicalRegion** | P2 | Advanced physical modeling | Very High |
| **ConvolutionReverbRegion** | P2 | IR-based reverb | Medium |

---

## Implementation Patterns

### **Pattern 1: Sample-Based Regions (SF2, SFZ, Wavetable)**

```python
class SampleBasedRegion(IRegion):
    """Base class for sample-based regions."""
    
    __slots__ = [
        'sample_cache', 'sample_id', 'loop_start', 'loop_end',
        'loop_mode', 'root_key', 'sample_position', 'phase_step'
    ]
    
    def _load_sample_data(self) -> Optional[np.ndarray]:
        """Load sample from cache with lazy loading."""
        if self.sample_id is None:
            return None
        
        # Use shared sample cache manager
        sample = self.sample_cache.get_sample(
            self.source_id,
            self.sample_id,
            loader=self._load_from_disk
        )
        
        if sample is not None:
            self.descriptor.is_sample_loaded = True
        
        return sample
    
    def _calculate_phase_step(self) -> float:
        """Calculate phase step based on note and tuning."""
        note_diff = self.current_note - self.root_key
        total_semitones = note_diff + self.coarse_tune + self.fine_tune / 100.0
        return 2.0 ** (total_semitones / 12.0)
    
    def _handle_looping(self, position: float, sample_length: int) -> float:
        """Handle SF2-style looping modes."""
        if self.loop_mode == 0:  # No loop
            if position >= sample_length:
                self.state = RegionState.RELEASING
                return sample_length - 1
        
        elif self.loop_mode == 1:  # Forward loop
            if position >= self.loop_end:
                loop_length = self.loop_end - self.loop_start
                if loop_length > 0:
                    excess = position - self.loop_end
                    return self.loop_start + (excess % loop_length)
        
        elif self.loop_mode == 3:  # Loop and continue
            # Implementation for loop-then-continue
            pass
        
        return position
```

### **Pattern 2: Algorithmic Regions (FM, Additive, Physical)**

```python
class AlgorithmicRegion(IRegion):
    """Base class for algorithmic synthesis regions."""
    
    __slots__ = [
        'operators', 'algorithm', 'modulation_matrix',
        'key_scaling', 'velocity_scaling', 'output_level'
    ]
    
    def _apply_key_scaling(self, params: Dict) -> Dict:
        """Apply key-based parameter scaling."""
        if not self.key_scaling:
            return params
        
        # Calculate scaling factor based on note position
        key_center = self.key_scaling.get('center', 60)
        key_offset = self.current_note - key_center
        depth = self.key_scaling.get('depth', 0)
        
        # Apply to operator amplitudes, envelope rates, etc.
        scaled = params.copy()
        scale_factor = 1.0 + (key_offset / 127.0) * (depth / 7.0)
        
        if 'amplitude' in scaled:
            scaled['amplitude'] *= scale_factor
        
        return scaled
    
    def _apply_velocity_scaling(self, params: Dict) -> Dict:
        """Apply velocity-based parameter scaling."""
        if not self.velocity_scaling:
            return params
        
        # Calculate scaling factor based on velocity
        sensitivity = self.velocity_scaling.get('sensitivity', 0)
        vel_factor = (self.current_velocity / 127.0) ** (sensitivity / 7.0)
        
        scaled = params.copy()
        if 'amplitude' in scaled:
            scaled['amplitude'] *= vel_factor
        
        return scaled
```

### **Pattern 3: Grain-Based Regions (Granular)**

```python
class GrainBasedRegion(IRegion):
    """Base class for granular synthesis regions."""
    
    __slots__ = [
        'grain_clouds', 'source_buffer', 'grain_params',
        'time_stretch', 'pitch_shift', 'density'
    ]
    
    def _trigger_grain_cloud(self, cloud_id: int) -> None:
        """Trigger a grain cloud with current parameters."""
        if cloud_id >= len(self.grain_clouds):
            return
        
        cloud = self.grain_clouds[cloud_id]
        
        # Set cloud parameters
        cloud.set_parameters({
            'density': self.density,
            'duration_ms': self.grain_params.get('duration', 50),
            'position': self._calculate_grain_position(),
            'pitch_shift': self.pitch_shift,
            'pan_spread': self.grain_params.get('pan_spread', 0.5)
        })
        
        # Trigger cloud
        cloud.trigger()
    
    def _calculate_grain_position(self) -> float:
        """Calculate grain position in source buffer."""
        # Implementation depends on playback mode
        # - Normal: linear progression
        # - Random: random positions
        # - Granular cloud: positions around center point
        pass
```

---

## Detailed Implementation Plans

### **1. WavetableRegion (P0 - High Priority)**

**File:** `synth/partial/wavetable_region.py`

**Features:**
- Wavetable scanning with morphing
- Multi-oscillator support (up to 8 oscillators)
- Unison detuning
- Real-time wavetable position modulation
- Filter with envelope modulation

**Implementation:**
```python
class WavetableRegion(IRegion):
    __slots__ = [
        'wavetable_bank', 'oscillators', 'wavetable_position',
        'morph_speed', 'unison_voices', 'detune_amount',
        'filter_cutoff', 'filter_resonance'
    ]
    
    def _create_partial(self) -> Optional[Any]:
        """Create wavetable oscillator bank."""
        # Get current wavetable from bank
        wavetable_name = self.descriptor.algorithm_params.get('wavetable', 'default')
        wavetable = self.wavetable_bank.get_wavetable(wavetable_name)
        
        if wavetable is None:
            return None
        
        # Create oscillator bank
        params = {
            'wavetable': wavetable,
            'frequency': self._calculate_frequency(),
            'wavetable_position': self.wavetable_position,
            'morph_speed': self.morph_speed,
            'unison_voices': self.unison_voices,
            'detune_amount': self.detune_amount,
            'filter_cutoff': self.filter_cutoff,
            'filter_resonance': self.filter_resonance
        }
        
        from ..partial.wavetable_partial import WavetablePartial
        return WavetablePartial(params, self.sample_rate)
```

**Estimated Effort:** 2-3 days  
**Test Coverage:** 15+ tests  
**Dependencies:** WavetablePartial, WavetableBank

---

### **2. AdditiveRegion (P0 - High Priority)**

**File:** `synth/partial/additive_region.py`

**Features:**
- Harmonic spectrum control (up to 128 partials)
- Real-time spectral morphing
- Bandwidth optimization
- Individual partial envelopes
- Brightness and spread control

**Implementation:**
```python
class AdditiveRegion(IRegion):
    __slots__ = [
        'spectrum', 'target_spectrum', 'morph_factor',
        'max_partials', 'brightness', 'spread',
        'bandwidth_limit'
    ]
    
    def _create_partial(self) -> Optional[Any]:
        """Create additive synthesis partial bank."""
        # Get spectrum type from descriptor
        spectrum_type = self.descriptor.algorithm_params.get('spectrum_type', 'sawtooth')
        
        # Create spectrum
        spectrum = HarmonicSpectrum(spectrum_type)
        if spectrum_type == 'sawtooth':
            spectrum.create_sawtooth(self.max_partials)
        elif spectrum_type == 'square':
            spectrum.create_square(self.max_partials)
        elif spectrum_type == 'triangle':
            spectrum.create_triangle(self.max_partials)
        
        # Apply brightness scaling
        self._apply_brightness(spectrum)
        
        params = {
            'spectrum': spectrum,
            'max_partials': self.max_partials,
            'brightness': self.brightness,
            'spread': self.spread,
            'bandwidth_limit': self.bandwidth_limit
        }
        
        from ..partial.additive_partial import AdditivePartial
        return AdditivePartial(params, self.sample_rate)
```

**Estimated Effort:** 2-3 days  
**Test Coverage:** 15+ tests  
**Dependencies:** HarmonicSpectrum, AdditivePartial

---

### **3. PhysicalRegion (P0 - Medium Priority)**

**File:** `synth/partial/physical_region.py`

**Features:**
- Digital waveguide synthesis
- Karplus-Strong plucked string
- Physical parameter control (tension, damping, material)
- Multiple physical models (string, tube, membrane)

**Implementation:**
```python
class PhysicalRegion(IRegion):
    __slots__ = [
        'model_type', 'waveguide', 'excitation_type',
        'tension', 'damping', 'material', 'body_size'
    ]
    
    MODEL_TYPES = ['string', 'tube', 'membrane', 'plate']
    EXCITATION_TYPES = ['pluck', 'strike', 'blow', 'bow']
    
    def _create_partial(self) -> Optional[Any]:
        """Create physical modeling partial."""
        model_type = self.descriptor.algorithm_params.get('model_type', 'string')
        
        if model_type == 'string':
            # Karplus-Strong string model
            from ..core.waveguide import DigitalWaveguide
            waveguide = DigitalWaveguide(self.sample_rate)
            waveguide.set_frequency(self._calculate_frequency())
            waveguide.set_parameters({
                'tension': self.tension,
                'damping': self.damping,
                'body_size': self.body_size
            })
            
            params = {
                'waveguide': waveguide,
                'excitation_type': self.excitation_type,
                'model_type': model_type
            }
            
            from ..partial.physical_partial import PhysicalPartial
            return PhysicalPartial(params, self.sample_rate)
```

**Estimated Effort:** 2 days  
**Test Coverage:** 12+ tests  
**Dependencies:** DigitalWaveguide, PhysicalPartial

---

### **4. GranularRegion (P1 - High Priority)**

**File:** `synth/partial/granular_region.py`

**Features:**
- Multiple grain clouds (up to 8)
- Time-stretching without pitch change
- Pitch-shifting without time change
- Grain parameter randomization
- Source buffer management

**Implementation:**
```python
class GranularRegion(IRegion):
    __slots__ = [
        'grain_clouds', 'source_buffer', 'source_length',
        'time_stretch', 'pitch_shift', 'grain_density',
        'grain_duration', 'position_spread'
    ]
    
    def _create_partial(self) -> Optional[Any]:
        """Create granular synthesis cloud bank."""
        # Load source buffer if needed
        if self.source_buffer is None:
            self.source_buffer = self._load_source_buffer()
        
        # Create grain clouds
        clouds = []
        for i in range(self.descriptor.algorithm_params.get('max_clouds', 4)):
            cloud = GrainCloud(self.sample_rate, max_grains=100)
            cloud.set_parameters({
                'density': self.grain_density,
                'duration_ms': self.grain_duration,
                'position': self._calculate_cloud_position(i),
                'pitch_shift': self.pitch_shift,
                'time_stretch': self.time_stretch
            })
            clouds.append(cloud)
        
        params = {
            'clouds': clouds,
            'source_buffer': self.source_buffer,
            'time_stretch': self.time_stretch,
            'pitch_shift': self.pitch_shift
        }
        
        from ..partial.granular_partial import GranularPartial
        return GranularPartial(params, self.sample_rate)
```

**Estimated Effort:** 3-4 days  
**Test Coverage:** 18+ tests  
**Dependencies:** GrainCloud, GranularPartial

---

### **5. FDSPRegion (P1 - Medium Priority)**

**File:** `synth/partial/fdsp_region.py`

**Features:**
- Formant synthesis with phoneme transitions
- Vocal tract modeling
- Breath noise control
- Vibrato with rate/depth control
- Multiple excitation types

**Implementation:**
```python
class FDSPRegion(IRegion):
    __slots__ = [
        'fdsp_engine', 'phoneme', 'target_phoneme',
        'transition_progress', 'formant_shift',
        'vibrato_rate', 'vibrato_depth', 'breath_level'
    ]
    
    PHONEMES = ['a', 'e', 'i', 'o', 'u', 'ə', 'N', 'M', 'L', 'R']
    
    def _create_partial(self) -> Optional[Any]:
        """Create FDSP vocal synthesis partial."""
        # Create dedicated FDSP engine for this region
        fdsp = FDSPEngine(self.sample_rate)
        
        # Set initial phoneme
        phoneme_name = self.descriptor.algorithm_params.get('phoneme', 'ə')
        fdsp.set_phoneme(phoneme_name)
        
        # Set vocal parameters
        fdsp.set_parameters({
            'pitch': self._calculate_frequency(),
            'formant_shift': self.formant_shift,
            'tilt': self.descriptor.algorithm_params.get('tilt', 0.5),
            'vibrato_rate': self.vibrato_rate,
            'vibrato_depth': self.vibrato_depth,
            'breath_level': self.breath_level
        })
        
        params = {
            'fdsp_engine': fdsp,
            'phoneme': phoneme_name,
            'excitation_type': self.descriptor.algorithm_params.get('excitation', 'vocal')
        }
        
        from ..partial.fdsp_partial import FDSPPartial
        return FDSPPartial(params, self.sample_rate)
```

**Estimated Effort:** 2 days  
**Test Coverage:** 12+ tests  
**Dependencies:** FDSPEngine, FDSPPartial

---

### **6. ANRegion (P1 - Medium Priority)**

**File:** `synth/partial/an_region.py`

**Features:**
- Analog physical modeling (Motif AN)
- RP-PR (Resonant Peak - Physical Resonance) synthesis
- String/pipe/membrane models
- Real-time parameter control

**Implementation:**
```python
class ANRegion(IRegion):
    __slots__ = [
        'an_engine', 'model_type', 'resonator_params',
        'exciter_params', 'coupling_params'
    ]
    
    def _create_partial(self) -> Optional[Any]:
        """Create AN physical modeling partial."""
        # Create AN engine instance
        from ..jupiter_x.an_engine import ANPhysicalModel
        an_model = ANPhysicalModel(self.sample_rate)
        
        # Set model type (string, pipe, membrane, etc.)
        model_type = self.descriptor.algorithm_params.get('model_type', 'string')
        an_model.set_model_type(model_type)
        
        # Configure resonator
        an_model.set_resonator_parameters({
            'frequency': self._calculate_frequency(),
            'tension': self.resonator_params.get('tension', 0.5),
            'damping': self.resonator_params.get('damping', 0.5),
            'body_size': self.resonator_params.get('body_size', 0.5)
        })
        
        # Configure exciter
        an_model.set_exciter_parameters(self.exciter_params)
        
        params = {
            'an_model': an_model,
            'model_type': model_type
        }
        
        from ..partial.an_partial import ANPartial
        return ANPartial(params, self.sample_rate)
```

**Estimated Effort:** 2-3 days  
**Test Coverage:** 12+ tests  
**Dependencies:** ANPhysicalModel, ANPartial

---

### **7. SpectralRegion (P2 - Very High Priority)**

**File:** `synth/partial/spectral_region.py`

**Features:**
- FFT-based spectral processing
- Real-time spectral morphing
- Harmonic enhancement
- Spectral filtering
- Freeze/morph effects

**Estimated Effort:** 4-5 days  
**Test Coverage:** 20+ tests  
**Dependencies:** FFTProcessor, SpectralPartial

---

### **8. AdvancedPhysicalRegion (P2 - Very High Priority)**

**File:** `synth/partial/advanced_physical_region.py`

**Features:**
- Advanced physical modeling
- Multi-body coupling
- Non-linear behavior
- Environmental modeling

**Estimated Effort:** 5-6 days  
**Test Coverage:** 20+ tests  
**Dependencies:** AdvancedPhysicalModel

---

### **9. ConvolutionReverbRegion (P2 - Medium Priority)**

**File:** `synth/partial/convolution_reverb_region.py`

**Features:**
- Impulse response loading
- Convolution processing
- Wet/dry mixing
- Pre-delay control
- High-frequency damping

**Estimated Effort:** 2 days  
**Test Coverage:** 10+ tests  
**Dependencies:** ConvolutionProcessor

---

## Testing Strategy

### **Unit Tests (Per Region Type)**

```python
class TestWavetableRegion:
    def test_wavetable_region_creation(self):
        """Test region creation with wavetable."""
        pass
    
    def test_wavetable_morphing(self):
        """Test real-time wavetable morphing."""
        pass
    
    def test_unison_detuning(self):
        """Test unison voice detuning."""
        pass
    
    def test_filter_modulation(self):
        """Test filter envelope modulation."""
        pass
    
    # 10+ more tests...
```

### **Integration Tests**

```python
class TestEngineIntegration:
    def test_all_engines_create_regions(self):
        """Test all engines can create regions."""
        pass
    
    def test_multi_engine_preset(self):
        """Test preset using multiple engines."""
        pass
    
    # 5+ more tests...
```

---

## Implementation Timeline

### **Phase 1: Core Engines (Week 1-2)**
- WavetableRegion (2-3 days)
- AdditiveRegion (2-3 days)
- PhysicalRegion (2 days)
- **Total: 6-8 days**

### **Phase 2: Specialized Engines (Week 3-4)**
- GranularRegion (3-4 days)
- FDSPRegion (2 days)
- ANRegion (2-3 days)
- **Total: 7-9 days**

### **Phase 3: Advanced Engines (Week 5-7)**
- SpectralRegion (4-5 days)
- AdvancedPhysicalRegion (5-6 days)
- ConvolutionReverbRegion (2 days)
- **Total: 11-13 days**

### **Phase 4: Testing & Optimization (Week 8)**
- Unit test completion
- Integration testing
- Performance optimization
- **Total: 5 days**

**Grand Total: 29-35 days (6-7 weeks)**

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| **Test Coverage** | >90% for all region types |
| **Performance** | <1ms region creation time |
| **Memory Usage** | <100MB for typical multi-zone preset |
| **CPU Usage** | <10% per active region (typical preset) |
| **Feature Parity** | 100% of stub features + engine-specific features |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance regression** | Medium | High | Continuous benchmarking |
| **Memory leaks** | Low | High | Automated testing, valgrind |
| **Feature incompleteness** | Low | Medium | Regular testing with real presets |
| **Integration issues** | Medium | Medium | Incremental integration testing |

---

## Next Steps

1. **Approve plan** - Review and approve implementation priorities
2. **Set up test infrastructure** - Prepare testing environment
3. **Begin Phase 1** - Start with WavetableRegion implementation
4. **Weekly reviews** - Review progress and adjust priorities
5. **Continuous integration** - Run tests on every commit

---

**End of Plan**
