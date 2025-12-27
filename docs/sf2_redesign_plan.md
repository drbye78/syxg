# SF2 Lazy Loading Redesign Plan

## Overview
Redesign the `LazySF2SoundFont` and related classes to implement true lazy loading for large SoundFonts (1GB+), replacing the current flawed implementation with a production-quality, high-performance solution.

## Current Issues
1. **False Lazy Loading**: Preloads all critical chunks upfront, defeating the purpose of lazy loading.
2. **Memory Inefficiency**: Loads all zone data during initialization, which is inefficient for large files.
3. **Redundant Architecture**: Multiple overlapping classes complicate the design.
4. **Inefficient Sample Handling**: Does not properly handle 24-bit and stereo samples.
5. **Lack of Proper Caching**: Caching mechanism is not optimized for large soundfonts.

## New Architecture Goals
1. **True Lazy Loading**: Load data only when specifically requested.
2. **Memory Efficiency**: Minimal initial memory footprint, with on-demand loading.
3. **Fast Lookups**: O(1) index lookups without preloading data.
4. **Scalability**: Handle 1GB+ files without memory issues.
5. **Proper Sample Handling**: Support for 16-bit and 24-bit samples, mono and stereo.
6. **Efficient Caching**: Implement LRU caching for frequently used chunks and samples.

## Implementation Plan

### Phase 1: Core Index Refactoring
1. **Create LazyIndexBuilder Class**
   - Build offset-based indices without loading chunk data.
   - Store only file offsets and boundary information.
   - Enable O(1) preset/instrument boundary lookups.

2. **Replace PreloadedZoneIndex with LazyZoneIndex**
   - Remove data preloading from zone index.
   - Store only offset ranges for generators/modulators.
   - Load zone data on-demand during lookups.

3. **Implement OnDemandZoneLoader**
   - Load and process individual zones only when requested.
   - Cache processed zones with LRU eviction.
   - Handle memory limits and cleanup.

### Phase 2: Lazy Chunk Loading
4. **Refactor LazySF2SoundFont Initialization**
   - Remove `_preload_critical_chunks()` method.
   - Build chunk offset maps without loading data.
   - Implement lazy chunk data loading with caching.

5. **Create ChunkDataCache**
   - Cache loaded chunk data segments.
   - Implement memory-managed LRU cache.
   - Support partial chunk loading (ranges).

### Phase 3: Unified Preset/Instrument Handling
6. **Merge SF2LazyPreset and SF2OptimizedPreset**
   - Create single SF2Preset class with lazy loading.
   - Remove redundant selective processing logic.
   - Implement unified zone matching with on-demand loading.

7. **Refactor Zone Processing**
   - Simplify zone matching logic.
   - Remove complex selective processing.
   - Use efficient offset-based lookups.

### Phase 4: Memory Management & Optimization
8. **Add MemoryManager**
   - Global memory limits for SF2 loading.
   - LRU eviction policies for caches.
   - Background cleanup of unused data.

9. **Optimize Sample Loading**
   - Ensure samples are truly lazy-loaded.
   - Implement sample data caching with memory limits.
   - Support streaming for large samples.

### Phase 5: Testing & Validation
10. **Update Tests**
    - Test memory usage improvements.
    - Validate lazy loading behavior.
    - Performance benchmarks for large files.

11. **Integration Testing**
    - Test with 1GB+ SoundFonts.
    - Validate real-time performance.
    - Memory usage monitoring.

## Expected Outcomes
- **80-90% reduction** in initial memory footprint for large SF2 files.
- **Near-instant initialization** instead of loading all data upfront.
- **Maintained O(1) lookup performance** for presets/instruments.
- **Scalable to 1GB+ files** without memory issues.
- **Cleaner architecture** with unified classes and clear responsibilities.

## Success Criteria
- Initial memory usage < 10MB for any SF2 file size.
- Load time < 1 second for file scanning/indexing.
- No performance regression in zone lookups.
- Support for SoundFonts with 1000+ presets and 10000+ zones.

## Implementation Details

### LazyIndexBuilder
```python
class LazyIndexBuilder:
    """Build offset-based indices without loading chunk data."""
    
    def __init__(self, sf2_file):
        self.sf2_file = sf2_file
        self.preset_boundaries = {}
        self.instrument_boundaries = {}
        self.sample_boundaries = {}
    
    def build_preset_index(self):
        """Build preset index with only boundary information."""
        # Parse preset headers to get boundaries
        # Store only (bank, preset) -> (start_bag, end_bag)
        pass
    
    def build_instrument_index(self):
        """Build instrument index with only boundary information."""
        # Parse instrument headers to get boundaries
        # Store only instrument_index -> (start_bag, end_bag)
        pass
    
    def build_sample_index(self):
        """Build sample index with only boundary information."""
        # Parse sample headers to get boundaries
        # Store only sample_name -> (header_offset, data_offset)
        pass
```

### LazyZoneIndex
```python
class LazyZoneIndex:
    """Lazy zone index that loads data on-demand."""
    
    def __init__(self, sf2_file, chunk_name):
        self.sf2_file = sf2_file
        self.chunk_name = chunk_name
        self.bag_boundaries = []  # Store only boundaries, not data
    
    def get_matching_zones(self, start_bag, end_bag, note, velocity):
        """Load and process zones on-demand."""
        # Load only the required bag data
        # Process generators and modulators for matching zones
        pass
```

### OnDemandZoneLoader
```python
class OnDemandZoneLoader:
    """Load and process individual zones on-demand."""
    
    def __init__(self, sf2_file, max_cache_size):
        self.sf2_file = sf2_file
        self.zone_cache = LRUCache(max_cache_size)
    
    def load_zone(self, zone_id):
        """Load and process a single zone."""
        # Check cache first
        # Load from file if not cached
        # Process generators and modulators
        # Cache the result
        pass
```

### ChunkDataCache
```python
class ChunkDataCache:
    """Memory-managed LRU cache for chunk data."""
    
    def __init__(self, max_memory_mb):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.cache = OrderedDict()
    
    def get_chunk_data(self, chunk_name, offset, size):
        """Get chunk data from cache or load from file."""
        # Check cache
        # Load from file if not cached
        # Manage memory limits
        pass
```

### Unified SF2Preset
```python
class SF2Preset:
    """Unified preset class with lazy loading."""
    
    def __init__(self, sf2_file, name, bank, preset, bag_index):
        self.sf2_file = sf2_file
        self.name = name
        self.bank = bank
        self.preset = preset
        self.bag_index = bag_index
    
    def get_matching_zones(self, note, velocity):
        """Get zones that match the note/velocity."""
        # Use lazy zone loading
        # Return matching zones
        pass
```

## Next Steps
1. Implement the `LazyIndexBuilder` class.
2. Replace `PreloadedZoneIndex` with `LazyZoneIndex`.
3. Implement `OnDemandZoneLoader` for lazy zone loading.
4. Create `ChunkDataCache` for efficient chunk data caching.
5. Refactor `LazySF2SoundFont` to use the new architecture.
6. Test and validate the implementation with large soundfonts.
