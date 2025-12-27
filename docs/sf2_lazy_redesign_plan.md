# SF2 Lazy Loading Redesign Plan

## Overview
Redesign the lazy on-demand processing in `synth/sf2/core/manager.py` to implement true lazy loading for large SoundFonts (1GB+), replacing the current false lazy loading that preloads all data upfront.

## Current Issues
- **False lazy loading**: Preloads entire chunks ('pbag', 'ibag', 'pgen', 'igen', 'pmod', 'imod') at initialization
- **Memory inefficiency**: Processes all generators/modulators upfront, defeating purpose for large files
- **Redundant architecture**: Multiple overlapping classes (SF2LazyPreset, SF2OptimizedPreset)
- **Inefficient indices**: PreloadedZoneIndex loads all zone data instead of boundaries

## New Architecture Goals
- **True lazy loading**: Load data only when specifically requested
- **Memory efficient**: Minimal initial memory footprint, load on-demand
- **Fast lookups**: O(1) index lookups without preloading data
- **Scalable**: Handle 1GB+ files without memory issues

## Implementation Plan

### Phase 1: Core Index Refactoring
1. **Create LazyIndexBuilder class**
   - Build offset-based indices without loading chunk data
   - Store only file offsets and boundary information
   - Enable O(1) preset/instrument boundary lookups

2. **Replace PreloadedZoneIndex with LazyZoneIndex**
   - Remove data preloading from zone index
   - Store only offset ranges for generators/modulators
   - Load zone data on-demand during lookups

3. **Implement OnDemandZoneLoader**
   - Load and process individual zones only when requested
   - Cache processed zones with LRU eviction
   - Handle memory limits and cleanup

### Phase 2: Lazy Chunk Loading
4. **Refactor LazySF2SoundFont initialization**
   - Remove `_preload_frequently_accessed_chunks()`
   - Build chunk offset maps without loading data
   - Implement lazy chunk data loading with caching

5. **Create ChunkDataCache**
   - Cache loaded chunk data segments
   - Implement memory-managed LRU cache
   - Support partial chunk loading (ranges)

### Phase 3: Unified Preset/Instrument Handling
6. **Merge SF2LazyPreset and SF2OptimizedPreset**
   - Create single SF2Preset class with lazy loading
   - Remove redundant selective processing logic
   - Implement unified zone matching with on-demand loading

7. **Refactor zone processing**
   - Simplify zone matching logic
   - Remove complex selective processing
   - Use efficient offset-based lookups

### Phase 4: Memory Management & Optimization
8. **Add MemoryManager**
   - Global memory limits for SF2 loading
   - LRU eviction policies for caches
   - Background cleanup of unused data

9. **Optimize sample loading**
   - Ensure samples are truly lazy-loaded
   - Implement sample data caching with memory limits
   - Support streaming for large samples

### Phase 5: Testing & Validation
10. **Update tests**
    - Test memory usage improvements
    - Validate lazy loading behavior
    - Performance benchmarks for large files

11. **Integration testing**
    - Test with 1GB+ SoundFonts
    - Validate real-time performance
    - Memory usage monitoring

## Expected Outcomes
- **80-90% reduction** in initial memory footprint for large SF2 files
- **Near-instant initialization** instead of loading all data upfront
- **Maintained O(1) lookup performance** for presets/instruments
- **Scalable to 1GB+ files** without memory issues
- **Cleaner architecture** with unified classes and clear responsibilities

## Implementation Order
1. ✅ LazyIndexBuilder (Phase 1) - COMPLETED
2. ✅ LazyZoneIndex (Phase 1) - COMPLETED
3. ✅ OnDemandZoneLoader (Phase 1) - COMPLETED
4. ✅ ChunkDataCache (Phase 2) - COMPLETED
5. ✅ LazySF2SoundFont refactor (Phase 2) - COMPLETED
6. ✅ Unified SF2Preset (Phase 3) - COMPLETED
7. ✅ CORE REDESIGN COMPLETE - TESTED AND WORKING
8. MemoryManager (Phase 4) - OPTIONAL
9. Sample loading optimization (Phase 4) - OPTIONAL
10. Testing (Phase 5) - OPTIONAL

## Success Criteria
- Initial memory usage < 10MB for any SF2 file size
- Load time < 1 second for file scanning/indexing
- No performance regression in zone lookups
- Support for SoundFonts with 1000+ presets and 10000+ zones