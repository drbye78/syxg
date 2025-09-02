# SF2 SoundFont Chunk Storage Refactoring

## Changes Implemented

### 1. Consolidated Chunk Storage
- Replaced separate `chunk_positions` and `chunk_sizes` dictionaries with a single `chunk_info` dictionary
- The new dictionary stores tuples in the format `(position, size)` for each chunk
- This simplifies the data structure and reduces memory overhead

### 2. Updated Chunk Location Logic
- Modified `_locate_sf2_chunks()` to store chunk information as tuples
- Modified `_locate_pdta_subchunks()` to store subchunk information as tuples
- Both methods now use the unified `chunk_info` dictionary

### 3. Updated All References
- Updated all methods that previously accessed `chunk_positions` and `chunk_sizes` 
- Methods now unpack the tuple values: `position, size = self.chunk_info['chunk_name']`
- This includes selective parsing methods, calculation methods, and data parsing methods

## Key Benefits

1. **Simplified Data Structure**:
   - Single dictionary instead of two separate dictionaries
   - Related data (position and size) stored together as tuples
   - Cleaner and more maintainable code

2. **Improved Performance**:
   - Reduced memory usage by eliminating duplicate keys
   - Faster access times due to better data locality
   - Eliminated need to check two separate dictionaries

3. **Better Code Organization**:
   - More intuitive data access patterns
   - Reduced code duplication
   - Easier to extend or modify in the future

## Technical Details

### New Data Structure
```python
# Before
self.chunk_positions = {}  # {'pbag': 12345}
self.chunk_sizes = {}      # {'pbag': 1024}

# After  
self.chunk_info = {}       # {'pbag': (12345, 1024)}
```

### Usage Pattern
```python
# Before
pbag_pos = self.chunk_positions['pbag']
pbag_size = self.chunk_sizes['pbag']

# After
pbag_pos, pbag_size = self.chunk_info['pbag']
```

### Updated Methods
- `_locate_sf2_chunks()`
- `_locate_pdta_subchunks()`
- `_parse_preset_headers()`
- `_parse_pdta_presets_selective()`
- `_parse_pdta_instruments_selective()`
- `_parse_preset_instruments()`
- `_calculate_preset_generator_indices()`
- `_calculate_preset_modulator_indices()`
- `_calculate_instrument_generator_indices()`
- `_calculate_instrument_modulator_indices()`
- `_parse_all_presets_data()`
- `_parse_all_instruments_data()`
- `get_sample_header()`