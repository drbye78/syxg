# SF2 On-Demand Parsing Optimization

## Summary of Changes

I've refactored the SF2 implementation to calculate file positions of mandatory chunks ('pbag', 'pmod', 'pgen', 'ibag', 'imod', 'igen') during initial parsing of the SF2 structure and reuse them without scanning LIST chunks.

## Key Improvements

### 1. Enhanced Chunk Position Calculation
- Modified `_locate_sf2_chunks()` to include a new `_locate_pdta_subchunks()` method
- During initial parsing, the positions of all mandatory subchunks in the 'pdta' section are stored
- This eliminates the need to scan through LIST chunks during on-demand parsing

### 2. Optimized Selective Parsing Methods
- Updated `_parse_pdta_presets_selective()` to directly access stored chunk positions
- Updated `_parse_pdta_instruments_selective()` to directly access stored chunk positions
- Removed unnecessary scanning of LIST chunks during selective parsing

### 3. Improved Performance
- Reduced file I/O operations during on-demand parsing
- Eliminated redundant chunk scanning
- Faster access to mandatory chunk data

## Technical Details

### New Method: `_locate_pdta_subchunks()`
```python
def _locate_pdta_subchunks(self, pdta_position: int, pdta_size: int):
    """Находит позиции обязательных подчанков в pdta для оптимизации on-demand парсинга"""
    # ...
    # Сохраняем позиции обязательных подчанков
    if subchunk_id in [b'pbag', b'pmod', b'pgen', b'ibag', b'imod', b'igen']:
        # Сохраняем позицию начала данных подчанка
        self.chunk_positions[subchunk_id.decode('ascii')] = self.file.tell()
```

### Optimized Selective Parsing
The selective parsing methods now directly access the stored positions:
```python
# Парсим pbag данные напрямую по сохраненной позиции
if 'pbag' in self.chunk_positions:
    pbag_pos = self.chunk_positions['pbag']
    # Переходим к pbag и парсим данные
```

## Benefits

1. **Reduced File Operations**: No need to scan through LIST chunks during on-demand parsing
2. **Faster Access**: Direct access to mandatory chunk positions
3. **Better Performance**: Improved overall parsing performance
4. **Maintained Compatibility**: All existing APIs remain unchanged