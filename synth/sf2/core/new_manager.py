#!/usr/bin/env python3
"""
SF2 Complete Redesign - Core Infrastructure

This module implements the completely redesigned SF2 file management system
with true lazy loading, efficient memory management, and full SF2 specification
support.
"""

import struct
import threading
from typing import Dict, List, Tuple, Optional, Any
from collections import OrderedDict
import numpy as np


class LRUCache:
    """Memory-managed LRU cache for SF2 data."""
    
    def __init__(self, max_size: int = 100, max_memory_mb: int = 50):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.current_memory = 0
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self.lock:
            if key not in self.cache:
                return None
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: Any, memory_size: int = 0) -> None:
        """Put item into cache."""
        with self.lock:
            # Remove if already exists
            if key in self.cache:
                old_value = self.cache[key]
                self.current_memory -= self._get_memory_size(old_value)
                del self.cache[key]
            
            # Add new item
            self.cache[key] = value
            self.current_memory += memory_size
            
            # Evict if necessary
            self._evict_if_needed()
    
    def _get_memory_size(self, value: Any) -> int:
        """Estimate memory size of cached item."""
        if isinstance(value, np.ndarray):
            return value.nbytes
        elif isinstance(value, (list, dict)):
            return len(str(value))  # Rough estimate
        else:
            return len(str(value))
    
    def _evict_if_needed(self) -> None:
        """Evict items if cache is too large."""
        while len(self.cache) > self.max_size or self.current_memory > self.max_memory:
            # Remove least recently used
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0


class MemoryManager:
    """Global memory management for SF2 loading."""
    
    def __init__(self, max_memory_mb: int = 512):
        """
        Initialize memory manager.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.current_memory = 0
        self.caches: Dict[str, LRUCache] = {}
        self.lock = threading.Lock()
    
    def create_cache(self, name: str, max_size: int = 100, max_memory_mb: int = 50) -> LRUCache:
        """Create a new LRU cache."""
        with self.lock:
            cache = LRUCache(max_size, max_memory_mb)
            self.caches[name] = cache
            return cache
    
    def get_cache(self, name: str) -> Optional[LRUCache]:
        """Get an existing cache."""
        return self.caches.get(name)
    
    def cleanup(self) -> None:
        """Clean up unused memory."""
        with self.lock:
            for cache in self.caches.values():
                cache.clear()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self.lock:
            total_cached = sum(len(cache.cache) for cache in self.caches.values())
            total_memory = sum(cache.current_memory for cache in self.caches.values())
            
            return {
                'total_cached_items': total_cached,
                'total_memory_bytes': total_memory,
                'total_memory_mb': total_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory / (1024 * 1024),
                'memory_utilization': (total_memory / self.max_memory) * 100 if self.max_memory > 0 else 0.0
            }


class LazyIndexSystem:
    """Offset-based indexing without data loading."""
    
    def __init__(self, manager: 'SF2FileManager'):
        """
        Initialize index system.
        
        Args:
            manager: SF2FileManager instance
        """
        self.manager = manager
        self.preset_indices: Dict[Tuple[int, int], Tuple[int, int]] = {}  # (bank, preset) -> (start_bag, end_bag)
        self.instrument_indices: Dict[int, Tuple[int, int]] = {}  # instrument_id -> (start_bag, end_bag)
        self.sample_indices: Dict[int, Tuple[int, int]] = {}  # sample_id -> (header_offset, data_offset)
        self.chunk_offsets: Dict[str, Tuple[int, int]] = {}  # chunk_name -> (offset, size)
        self.file_size: int = 0
    
    def build_indices(self) -> None:
        """Build all indices by scanning file structure."""
        self._scan_file_structure()
        self._build_preset_index()
        self._build_instrument_index()
        self._build_sample_index()
    
    def _scan_file_structure(self) -> None:
        """Scan RIFF structure and record chunk offsets."""
        with self.manager.file_lock:
            if self.manager.file_handle is None:
                raise RuntimeError("File not opened")
            
            # Verify RIFF header
            if self.manager.file_handle.read(4) != b'RIFF':
                raise ValueError("Not a valid RIFF file")
            
            # Read file size
            self.file_size = int.from_bytes(self.manager.file_handle.read(4), byteorder='little') + 8
            
            # Verify SF2 format
            if self.manager.file_handle.read(4) != b'sfbk':
                raise ValueError("Not a valid SF2 file")
            
            # Parse chunks
            while self.manager.file_handle.tell() < self.file_size:
                chunk_id = self.manager.file_handle.read(4)
                if len(chunk_id) < 4:
                    break
                
                chunk_size = int.from_bytes(self.manager.file_handle.read(4), byteorder='little')
                offset = self.manager.file_handle.tell()
                chunk_id_str = chunk_id.decode('ascii', errors='ignore')
                
                # Handle LIST chunks
                if chunk_id_str == 'LIST':
                    list_type = self.manager.file_handle.read(4).decode('ascii', errors='ignore')
                    actual_data_offset = self.manager.file_handle.tell()
                    actual_data_size = chunk_size - 4
                    
                    self.chunk_offsets[f'LIST_{list_type}'] = (actual_data_offset, actual_data_size)
                    
                    # Parse subchunks
                    end_of_list = actual_data_offset + actual_data_size
                    while self.manager.file_handle.tell() < end_of_list:
                        subchunk_id = self.manager.file_handle.read(4)
                        if len(subchunk_id) < 4:
                            break
                        
                        subchunk_size = int.from_bytes(self.manager.file_handle.read(4), byteorder='little')
                        subchunk_offset = self.manager.file_handle.tell()
                        subchunk_id_str = subchunk_id.decode('ascii', errors='ignore')
                        
                        self.chunk_offsets[subchunk_id_str] = (subchunk_offset, subchunk_size)
                        self.manager.file_handle.seek(subchunk_size, 1)
                else:
                    # Regular chunk
                    self.chunk_offsets[chunk_id_str] = (offset, chunk_size)
                    self.manager.file_handle.seek(chunk_size, 1)
    
    def _build_preset_index(self) -> None:
        """Build preset index with boundaries only."""
        if 'phdr' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['phdr']
        
        with self.manager.file_lock:
            self.manager.file_handle.seek(offset)
            
            # SF2 Preset Header structure (38 bytes)
            count = size // 38
            
            for i in range(count - 1):  # Last entry is terminator
                # Read preset header to get bank, preset, and bag index
                header_data = self.manager.file_handle.read(38)
                if len(header_data) < 26:
                    continue
                
                # Unpack: preset_num at offset 20, bank_num at offset 22, bag_ndx at offset 24
                preset_num, bank_num, bag_ndx = struct.unpack('<HHH', header_data[20:26])
                self.preset_indices[(bank_num, preset_num)] = (bag_ndx, bag_ndx + 1)  # Will adjust boundaries later
    
    def _build_instrument_index(self) -> None:
        """Build instrument index with boundaries only."""
        if 'inst' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['inst']
        
        with self.manager.file_lock:
            self.manager.file_handle.seek(offset)
            
            # SF2 Instrument Header structure (22 bytes)
            count = size // 22
            
            for i in range(count - 1):  # Last entry is terminator
                # Read instrument header to get bag index
                header_data = self.manager.file_handle.read(22)
                if len(header_data) < 22:
                    continue
                
                # Unpack bag index at offset 20
                bag_ndx = struct.unpack('<H', header_data[20:22])[0]
                self.instrument_indices[i] = (bag_ndx, bag_ndx + 1)  # Will adjust boundaries later
    
    def _build_sample_index(self) -> None:
        """Build sample index with boundaries only."""
        if 'shdr' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['shdr']
        sample_data_offset = self.chunk_offsets.get('smpl', (0, 0))[0]
        
        with self.manager.file_lock:
            self.manager.file_handle.seek(offset)
            
            # SF2 Sample Header structure (46 bytes)
            count = size // 46
            
            # Determine bit depth by reading first sample header
            bytes_per_sample = 2  # Default to 16-bit
            if count > 1:
                first_header_pos = self.manager.file_handle.tell()
                first_header = self.manager.file_handle.read(46)
                if len(first_header) >= 46:
                    sample_type = struct.unpack('<H', first_header[44:46])[0]
                    is_24bit = bool(sample_type & 0x8000)
                    bytes_per_sample = 3 if is_24bit else 2
                self.manager.file_handle.seek(first_header_pos)
            
            for i in range(count - 1):  # Last entry is terminator
                sample_offset = self.manager.file_handle.tell()
                # Read sample header to get start offset
                header_data = self.manager.file_handle.read(46)
                if len(header_data) < 24:
                    continue
                
                # Unpack start offset (4 bytes at offset 20)
                start = struct.unpack('<I', header_data[20:24])[0]
                data_offset = sample_data_offset + start * bytes_per_sample
                self.sample_indices[i] = (sample_offset, data_offset)
    
    def get_preset_boundaries(self, bank: int, preset: int) -> Tuple[int, int]:
        """Get preset boundaries."""
        return self.preset_indices.get((bank, preset), (0, 0))
    
    def get_instrument_boundaries(self, instrument_id: int) -> Tuple[int, int]:
        """Get instrument boundaries."""
        return self.instrument_indices.get(instrument_id, (0, 0))
    
    def get_sample_offsets(self, sample_id: int) -> Tuple[int, int]:
        """Get sample offsets."""
        return self.sample_indices.get(sample_id, (0, 0))
    
    def get_chunk_offset(self, chunk_name: str) -> Tuple[int, int]:
        """Get chunk offset and size."""
        return self.chunk_offsets.get(chunk_name, (0, 0))


class SF2FileManager:
    """Central manager for SF2 file operations."""
    
    def __init__(self, filename: str):
        """
        Initialize SF2 file manager.
        
        Args:
            filename: Path to SF2 file
        """
        self.filename = filename
        self.file_handle: Optional[Any] = None
        self.file_lock = threading.Lock()
        self.memory_manager = MemoryManager()
        self.index_system = LazyIndexSystem(self)
        self.loader: Optional[OnDemandLoader] = None
        self.is_initialized = False
    
    def initialize(self) -> None:
        """Initialize file and build indices."""
        try:
            with self.file_lock:
                self.file_handle = open(self.filename, 'rb')
            
            # Build indices
            self.index_system.build_indices()
            
            # Initialize loader
            self.loader = OnDemandLoader(self)
            
            self.is_initialized = True
            
        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Failed to initialize SF2 file {self.filename}: {e}")
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass
            self.file_handle = None
        
        self.is_initialized = False
    
    def __del__(self):
        """Destructor to clean up resources."""
        self._cleanup()
    
    def get_preset(self, bank: int, preset: int) -> Optional['SF2Preset']:
        """Get preset with lazy loading."""
        if not self.is_initialized:
            return None
        return self.loader.load_preset(bank, preset)
    
    def get_instrument(self, instrument_id: int) -> Optional['SF2Instrument']:
        """Get instrument with lazy loading."""
        if not self.is_initialized:
            return None
        return self.loader.load_instrument(instrument_id)
    
    def get_sample(self, sample_id: int) -> Optional[np.ndarray]:
        """Get sample data with lazy loading."""
        if not self.is_initialized:
            return None
        return self.loader.load_sample(sample_id)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return self.memory_manager.get_memory_stats()


class OnDemandLoader:
    """Lazy loading of chunks, zones, and samples."""
    
    def __init__(self, manager: SF2FileManager):
        """
        Initialize on-demand loader.
        
        Args:
            manager: SF2FileManager instance
        """
        self.manager = manager
        self.zone_cache = manager.memory_manager.create_cache('zones', max_size=200, max_memory_mb=100)
        self.sample_cache = manager.memory_manager.create_cache('samples', max_size=100, max_memory_mb=256)
        self.chunk_cache = manager.memory_manager.create_cache('chunks', max_size=50, max_memory_mb=50)
    
    def load_preset(self, bank: int, preset: int) -> Optional['SF2Preset']:
        """Load preset with lazy zone loading."""
        boundaries = self.manager.index_system.get_preset_boundaries(bank, preset)
        if boundaries == (0, 0):
            return None
        
        zones = self._load_zones('preset', boundaries)
        return SF2Preset(bank, preset, zones)
    
    def load_instrument(self, instrument_id: int) -> Optional['SF2Instrument']:
        """Load instrument with lazy zone loading."""
        boundaries = self.manager.index_system.get_instrument_boundaries(instrument_id)
        if boundaries == (0, 0):
            return None
        
        zones = self._load_zones('instrument', boundaries)
        return SF2Instrument(instrument_id, zones)
    
    def load_sample(self, sample_id: int) -> Optional[np.ndarray]:
        """Load sample data with proper bit depth and channel handling."""
        # Check cache first
        cache_key = f"sample_{sample_id}"
        cached_sample = self.sample_cache.get(cache_key)
        if cached_sample is not None:
            return cached_sample
        
        # Load from file
        header_offset, data_offset = self.manager.index_system.get_sample_offsets(sample_id)
        if header_offset == 0 or data_offset == 0:
            return None
        
        with self.manager.file_lock:
            if self.manager.file_handle is None:
                return None
            
            # Read sample header to get parameters
            self.manager.file_handle.seek(header_offset)
            header_data = self.manager.file_handle.read(46)
            if len(header_data) < 46:
                return None
            
            # Parse sample header
            name_bytes = header_data[:20]
            start, end = struct.unpack('<II', header_data[20:28])
            sample_rate = struct.unpack('<I', header_data[36:40])[0]
            original_pitch = header_data[40]  # int8
            pitch_correction = header_data[41]  # int8
            sample_type = struct.unpack('<H', header_data[44:46])[0]
            
            # Determine sample format
            is_stereo = bool(sample_type & 0x0001)
            is_24bit = bool(sample_type & 0x8000)
            
            sample_count = end - start
            
            # Read sample data
            self.manager.file_handle.seek(data_offset)
            if is_24bit:
                bytes_per_sample = 3
                if is_stereo:
                    bytes_per_sample *= 2
                sample_bytes = self.manager.file_handle.read(sample_count * bytes_per_sample)
                sample_data = self._convert_24bit_sample(sample_bytes, sample_count, is_stereo)
            else:
                bytes_per_sample = 2
                if is_stereo:
                    bytes_per_sample *= 2
                sample_bytes = self.manager.file_handle.read(sample_count * bytes_per_sample)
                sample_data = self._convert_16bit_sample(sample_bytes, sample_count, is_stereo)
            
            # Cache the sample
            memory_size = sample_data.nbytes
            self.sample_cache.put(cache_key, sample_data, memory_size)
            
            return sample_data
    
    def _convert_24bit_sample(self, sample_bytes: bytes, sample_count: int, is_stereo: bool) -> np.ndarray:
        """Convert 24-bit sample to float32."""
        if is_stereo:
            stereo_data = np.zeros((sample_count, 2), dtype=np.float32)
            for i in range(sample_count):
                # Left channel
                left_bytes = sample_bytes[i*6:i*6+3]
                if len(left_bytes) == 3:
                    left_int = int.from_bytes(left_bytes, byteorder='little', signed=True)
                    if left_int & 0x800000:
                        left_int |= 0xFF000000
                    stereo_data[i, 0] = left_int / 8388608.0
                
                # Right channel
                right_bytes = sample_bytes[i*6+3:i*6+6]
                if len(right_bytes) == 3:
                    right_int = int.from_bytes(right_bytes, byteorder='little', signed=True)
                    if right_int & 0x800000:
                        right_int |= 0xFF000000
                    stereo_data[i, 1] = right_int / 8388608.0
            return stereo_data
        else:
            sample_data = np.zeros(sample_count, dtype=np.float32)
            for i in range(sample_count):
                sample_24bit = sample_bytes[i*3:(i+1)*3]
                if len(sample_24bit) == 3:
                    sample_int = int.from_bytes(sample_24bit, byteorder='little', signed=True)
                    if sample_int & 0x800000:
                        sample_int |= 0xFF000000
                    sample_data[i] = sample_int / 8388608.0
            return sample_data
    
    def _convert_16bit_sample(self, sample_bytes: bytes, sample_count: int, is_stereo: bool) -> np.ndarray:
        """Convert 16-bit sample to float32."""
        if is_stereo:
            stereo_data = np.frombuffer(sample_bytes, dtype=np.int16)
            stereo_data = stereo_data.reshape(-1, 2).astype(np.float32) / 32768.0
            return stereo_data
        else:
            return np.frombuffer(sample_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    
    def _load_zones(self, zone_type: str, boundaries: Tuple[int, int]) -> List['SF2Zone']:
        """Load zones within specified boundaries."""
        zones = []
        
        # Get bag data for the specified range
        bag_chunk = 'pbag' if zone_type == 'preset' else 'ibag'
        bag_data = self._load_bag_data(bag_chunk, boundaries[0], boundaries[1])
        
        # Load generators and modulators
        gen_chunk = 'pgen' if zone_type == 'preset' else 'igen'
        mod_chunk = 'pmod' if zone_type == 'preset' else 'imod'
        
        gen_data = self._load_generator_data(gen_chunk)
        mod_data = self._load_modulator_data(mod_chunk)
        
        # Process each zone
        for i, (gen_start, mod_start) in enumerate(bag_data):
            zone_id = boundaries[0] + i
            cache_key = f"{zone_type}_zone_{zone_id}"
            
            # Check cache
            cached_zone = self.zone_cache.get(cache_key)
            if cached_zone is not None:
                zones.append(cached_zone)
                continue
            
            # Calculate boundaries
            gen_end = bag_data[i+1][0] if i+1 < len(bag_data) else len(gen_data)
            mod_end = bag_data[i+1][1] if i+1 < len(bag_data) else len(mod_data)
            
            # Create and process zone
            zone = self._create_zone(zone_type, gen_data, mod_data, gen_start, gen_end, mod_start, mod_end)
            
            # Cache the zone
            memory_size = len(str(zone.to_dict()))  # Rough estimate
            self.zone_cache.put(cache_key, zone, memory_size)
            
            zones.append(zone)
        
        return zones
    
    def _load_bag_data(self, chunk_name: str, start_bag: int, end_bag: int) -> List[Tuple[int, int]]:
        """Load bag data for specified range."""
        if chunk_name not in self.manager.index_system.chunk_offsets:
            return []
        
        offset, size = self.manager.index_system.get_chunk_offset(chunk_name)
        
        # Check cache
        cache_key = f"bag_{chunk_name}_{start_bag}_{end_bag}"
        cached_data = self.chunk_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Load from file
        bag_data = []
        
        with self.manager.file_lock:
            if self.manager.file_handle is None:
                return []
            
            # Each bag entry is 4 bytes: gen_ndx (2), mod_ndx (2)
            entry_size = 4
            count = (end_bag - start_bag)
            
            for i in range(count):
                bag_offset = offset + (start_bag + i) * entry_size
                self.manager.file_handle.seek(bag_offset)
                entry_data = self.manager.file_handle.read(entry_size)
                if len(entry_data) < entry_size:
                    break
                
                gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
                bag_data.append((gen_ndx, mod_ndx))
        
        # Cache the data
        memory_size = len(bag_data) * entry_size
        self.chunk_cache.put(cache_key, bag_data, memory_size)
        
        return bag_data
    
    def _load_generator_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """Load generator data."""
        if chunk_name not in self.manager.index_system.chunk_offsets:
            return []
        
        # Check cache
        cache_key = f"gen_{chunk_name}"
        cached_data = self.chunk_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Load from file
        offset, size = self.manager.index_system.get_chunk_offset(chunk_name)
        gen_data = []
        
        with self.manager.file_lock:
            if self.manager.file_handle is None:
                return []
            
            # Each generator entry is 4 bytes: gen_type (2), gen_amount (2, signed)
            entry_size = 4
            count = size // entry_size
            
            for i in range(count):
                gen_offset = offset + i * entry_size
                self.manager.file_handle.seek(gen_offset)
                entry_data = self.manager.file_handle.read(entry_size)
                if len(entry_data) < entry_size:
                    break
                
                gen_type, gen_amount = struct.unpack('<Hh', entry_data)
                gen_data.append((gen_type, gen_amount))
        
        # Cache the data
        memory_size = len(gen_data) * entry_size
        self.chunk_cache.put(cache_key, gen_data, memory_size)
        
        return gen_data
    
    def _load_modulator_data(self, chunk_name: str) -> List[Dict[str, int]]:
        """Load modulator data."""
        if chunk_name not in self.manager.index_system.chunk_offsets:
            return []
        
        # Check cache
        cache_key = f"mod_{chunk_name}"
        cached_data = self.chunk_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Load from file
        offset, size = self.manager.index_system.get_chunk_offset(chunk_name)
        mod_data = []
        
        with self.manager.file_lock:
            if self.manager.file_handle is None:
                return []
            
            # Each modulator entry is 10 bytes
            entry_size = 10
            count = size // entry_size
            
            for i in range(count):
                mod_offset = offset + i * entry_size
                self.manager.file_handle.seek(mod_offset)
                entry_data = self.manager.file_handle.read(entry_size)
                if len(entry_data) < entry_size:
                    break
                
                # Parse modulator structure
                src_oper = struct.unpack('<H', entry_data[0:2])[0]
                dest_oper = struct.unpack('<H', entry_data[2:4])[0]
                mod_amount = struct.unpack('<h', entry_data[4:6])[0]
                amt_src_oper = struct.unpack('<H', entry_data[6:8])[0]
                mod_trans_oper = struct.unpack('<H', entry_data[8:10])[0]
                
                modulator = {
                    'src_operator': src_oper,
                    'dest_operator': dest_oper,
                    'mod_amount': mod_amount,
                    'amt_src_operator': amt_src_oper,
                    'mod_trans_operator': mod_trans_oper
                }
                mod_data.append(modulator)
        
        # Cache the data
        memory_size = len(mod_data) * entry_size
        self.chunk_cache.put(cache_key, mod_data, memory_size)
        
        return mod_data
    
    def _create_zone(self, zone_type: str, gen_data: List[Tuple[int, int]], 
                     mod_data: List[Dict[str, int]], gen_start: int, gen_end: int,
                     mod_start: int, mod_end: int) -> 'SF2Zone':
        """Create and process a single zone."""
        zone = SF2Zone()
        
        # Process generators
        for gen_idx in range(gen_start, min(gen_end, len(gen_data))):
            gen_type, gen_amount = gen_data[gen_idx]
            zone.add_generator(gen_type, gen_amount)
        
        # Process modulators
        for mod_idx in range(mod_start, min(mod_end, len(mod_data))):
            modulator = mod_data[mod_idx]
            zone.add_modulator(modulator)
        
        # Validate and finalize zone
        zone.finalize()
        
        return zone


# Data Model Classes

class SF2Zone:
    """Unified zone class with full SF2 support."""
    
    def __init__(self):
        self.generators: Dict[int, int] = {}
        self.modulators: List[Dict[str, int]] = []
        self.sample_id: int = -1
        self.key_range: Tuple[int, int] = (0, 127)
        self.velocity_range: Tuple[int, int] = (0, 127)
        self.is_global: bool = False
    
    def add_generator(self, gen_type: int, gen_amount: int) -> None:
        """Add a generator to the zone."""
        self.generators[gen_type] = gen_amount
        
        # Handle special generators
        if gen_type == 42:  # keyRange
            self.key_range = (gen_amount & 0xFF, (gen_amount >> 8) & 0xFF)
        elif gen_type == 43:  # velRange
            self.velocity_range = (gen_amount & 0xFF, (gen_amount >> 8) & 0xFF)
        elif gen_type == 53:  # sampleID
            self.sample_id = gen_amount
    
    def add_modulator(self, modulator: Dict[str, int]) -> None:
        """Add a modulator to the zone."""
        self.modulators.append(modulator)
    
    def matches(self, note: int, velocity: int) -> bool:
        """Check if zone matches note and velocity."""
        return (self.key_range[0] <= note <= self.key_range[1] and
                self.velocity_range[0] <= velocity <= self.velocity_range[1])
    
    def finalize(self) -> None:
        """Finalize zone processing."""
        # Determine if this is a global zone
        self.is_global = (self.sample_id == -1 and
                         self.key_range == (0, 127) and
                         self.velocity_range == (0, 127))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary."""
        return {
            'generators': self.generators.copy(),
            'modulators': self.modulators.copy(),
            'sample_id': self.sample_id,
            'key_range': self.key_range,
            'velocity_range': self.velocity_range,
            'is_global': self.is_global
        }


class SF2Preset:
    """Unified preset class."""
    
    def __init__(self, bank: int, preset: int, zones: List[SF2Zone]):
        self.bank = bank
        self.preset = preset
        self.zones = zones
    
    def get_matching_zones(self, note: int, velocity: int) -> List[SF2Zone]:
        """Get zones matching note and velocity."""
        return [zone for zone in self.zones if zone.matches(note, velocity)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary."""
        return {
            'bank': self.bank,
            'preset': self.preset,
            'zones': [zone.to_dict() for zone in self.zones]
        }


class SF2Instrument:
    """Unified instrument class."""
    
    def __init__(self, instrument_id: int, zones: List[SF2Zone]):
        self.instrument_id = instrument_id
        self.zones = zones
    
    def get_matching_zones(self, note: int, velocity: int) -> List[SF2Zone]:
        """Get zones matching note and velocity."""
        return [zone for zone in self.zones if zone.matches(note, velocity)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert instrument to dictionary."""
        return {
            'instrument_id': self.instrument_id,
            'zones': [zone.to_dict() for zone in self.zones]
        }


# Main API

class SF2Manager:
    """Main SF2 manager API."""
    
    def __init__(self):
        self.file_managers: Dict[str, SF2FileManager] = {}
        self.lock = threading.Lock()
    
    def load_file(self, filename: str) -> bool:
        """Load SF2 file."""
        try:
            manager = SF2FileManager(filename)
            manager.initialize()
            
            with self.lock:
                self.file_managers[filename] = manager
            
            return True
        except Exception as e:
            print(f"Error loading SF2 file {filename}: {e}")
            return False
    
    def get_preset(self, filename: str, bank: int, preset: int) -> Optional[SF2Preset]:
        """Get preset from file."""
        with self.lock:
            manager = self.file_managers.get(filename)
            if manager:
                return manager.get_preset(bank, preset)
        return None
    
    def get_instrument(self, filename: str, instrument_id: int) -> Optional[SF2Instrument]:
        """Get instrument from file."""
        with self.lock:
            manager = self.file_managers.get(filename)
            if manager:
                return manager.get_instrument(instrument_id)
        return None
    
    def get_sample(self, filename: str, sample_id: int) -> Optional[np.ndarray]:
        """Get sample from file."""
        with self.lock:
            manager = self.file_managers.get(filename)
            if manager:
                return manager.get_sample(sample_id)
        return None
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        stats = {
            'files': {},
            'total': {
                'cached_items': 0,
                'memory_mb': 0.0
            }
        }
        
        with self.lock:
            for filename, manager in self.file_managers.items():
                file_stats = manager.get_memory_stats()
                stats['files'][filename] = file_stats
                stats['total']['cached_items'] += file_stats['total_cached_items']
                stats['total']['memory_mb'] += file_stats['total_memory_mb']
        
        return stats


# For backward compatibility with existing code
class LazySF2SoundFont:
    """Backward compatibility wrapper."""
    
    def __init__(self, filename: str, manager: SF2Manager):
        self.filename = filename
        self.manager = manager
        self.sf2_manager = SF2FileManager(filename)
        self.sf2_manager.initialize()
    
    def get_preset_lazy(self, bank: int, preset: int) -> Optional[SF2Preset]:
        """Get preset with lazy loading."""
        return self.sf2_manager.get_preset(bank, preset)
    
    def get_instrument_lazy(self, instrument_id: int) -> Optional[SF2Instrument]:
        """Get instrument with lazy loading."""
        return self.sf2_manager.get_instrument(instrument_id)
    
    def get_sample_data_lazy(self, sample_id: int) -> Optional[np.ndarray]:
        """Get sample data with lazy loading."""
        return self.sf2_manager.get_sample(sample_id)
