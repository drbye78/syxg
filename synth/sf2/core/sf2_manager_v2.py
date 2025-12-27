#!/usr/bin/env python3
"""
SF2 Manager V2 - Simplified Redesign

This module implements a simplified but production-quality SF2 file
management system with true lazy loading and efficient memory management.
"""

import struct
import threading
from typing import Dict, List, Tuple, Optional, Any
from collections import OrderedDict
import numpy as np


class SimpleLRUCache:
    """Simple LRU cache for SF2 data."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """Put item into cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            self.cache[key] = value
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear cache."""
        with self.lock:
            self.cache.clear()


class SF2IndexSystem:
    """Offset-based indexing for SF2 files."""
    
    def __init__(self, manager: 'SF2FileManagerV2'):
        self.manager = manager
        self.preset_indices: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.instrument_indices: Dict[int, Tuple[int, int]] = {}
        self.sample_indices: Dict[int, Tuple[int, int]] = {}
        self.chunk_offsets: Dict[str, Tuple[int, int]] = {}
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
            f = self.manager.file_handle
            if f is None:
                raise RuntimeError("File not opened")
            
            # Verify RIFF header
            if f.read(4) != b'RIFF':
                raise ValueError("Not a valid RIFF file")
            
            # Read file size
            self.file_size = int.from_bytes(f.read(4), 'little') + 8
            
            # Verify SF2 format
            if f.read(4) != b'sfbk':
                raise ValueError("Not a valid SF2 file")
            
            # Parse chunks
            while f.tell() < self.file_size:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break
                
                chunk_size = int.from_bytes(f.read(4), 'little')
                offset = f.tell()
                chunk_id_str = chunk_id.decode('ascii', 'ignore')
                
                # Handle LIST chunks
                if chunk_id_str == 'LIST':
                    list_type = f.read(4).decode('ascii', 'ignore')
                    actual_data_offset = f.tell()
                    actual_data_size = chunk_size - 4
                    
                    self.chunk_offsets[f'LIST_{list_type}'] = (
                        actual_data_offset, actual_data_size
                    )
                    
                    # Parse subchunks
                    end_of_list = actual_data_offset + actual_data_size
                    while f.tell() < end_of_list:
                        subchunk_id = f.read(4)
                        if len(subchunk_id) < 4:
                            break
                        
                        subchunk_size = int.from_bytes(f.read(4), 'little')
                        subchunk_offset = f.tell()
                        subchunk_id_str = subchunk_id.decode('ascii', 'ignore')
                        
                        self.chunk_offsets[subchunk_id_str] = (
                            subchunk_offset, subchunk_size
                        )
                        f.seek(subchunk_size, 1)
                else:
                    # Regular chunk
                    self.chunk_offsets[chunk_id_str] = (offset, chunk_size)
                    f.seek(chunk_size, 1)
    
    def _build_preset_index(self) -> None:
        """Build preset index with boundaries."""
        if 'phdr' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['phdr']
        
        with self.manager.file_lock:
            f = self.manager.file_handle
            if f is None:
                return
            f.seek(offset)
            
            # SF2 Preset Header structure (38 bytes)
            count = size // 38
            
            for i in range(count - 1):
                header_data = f.read(38)
                if len(header_data) < 26:
                    continue
                
                # Unpack preset info
                preset_num, bank_num, bag_ndx = struct.unpack(
                    '<HHH', header_data[20:26]
                )
                self.preset_indices[(bank_num, preset_num)] = (
                    bag_ndx, bag_ndx + 1
                )
    
    def _build_instrument_index(self) -> None:
        """Build instrument index with boundaries."""
        if 'inst' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['inst']
        
        with self.manager.file_lock:
            f = self.manager.file_handle
            if f is None:
                return
            f.seek(offset)
            
            # SF2 Instrument Header structure (22 bytes)
            count = size // 22
            
            for i in range(count - 1):
                header_data = f.read(22)
                if len(header_data) < 22:
                    continue
                
                # Unpack instrument bag index
                bag_ndx = struct.unpack('<H', header_data[20:22])[0]
                self.instrument_indices[i] = (bag_ndx, bag_ndx + 1)
    
    def _build_sample_index(self) -> None:
        """Build sample index with boundaries."""
        if 'shdr' not in self.chunk_offsets:
            return
        
        offset, size = self.chunk_offsets['shdr']
        sample_data_offset = self.chunk_offsets.get('smpl', (0, 0))[0]
        
        with self.manager.file_lock:
            f = self.manager.file_handle
            if f is None:
                return
            f.seek(offset)
            
            # SF2 Sample Header structure (46 bytes)
            count = size // 46
            
            # Determine bit depth
            bytes_per_sample = 2
            if count > 1:
                first_header_pos = f.tell()
                first_header = f.read(46)
                if len(first_header) >= 46:
                    sample_type = struct.unpack('<H', first_header[44:46])[0]
                    is_24bit = bool(sample_type & 0x8000)
                    bytes_per_sample = 3 if is_24bit else 2
                f.seek(first_header_pos)
            
            for i in range(count - 1):
                sample_offset = f.tell()
                header_data = f.read(46)
                if len(header_data) < 24:
                    continue
                
                # Unpack sample start offset
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


class SF2FileManagerV2:
    """Central manager for SF2 file operations."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.file_handle = None
        self.file_lock = threading.Lock()
        self.index_system = SF2IndexSystem(self)
        self.zone_cache = SimpleLRUCache(max_size=200)
        self.sample_cache = SimpleLRUCache(max_size=100)
        self.is_initialized = False
    
    def initialize(self) -> None:
        """Initialize file and build indices."""
        try:
            with self.file_lock:
                self.file_handle = open(self.filename, 'rb')
            
            self.index_system.build_indices()
            self.is_initialized = True
            
        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Failed to initialize SF2 file: {e}")
    
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
        
        boundaries = self.index_system.get_preset_boundaries(bank, preset)
        if boundaries == (0, 0):
            return None
        
        zones = self._load_zones('preset', boundaries)
        return SF2Preset(bank, preset, zones)
    
    def get_instrument(self, instrument_id: int) -> Optional['SF2Instrument']:
        """Get instrument with lazy loading."""
        if not self.is_initialized:
            return None
        
        boundaries = self.index_system.get_instrument_boundaries(instrument_id)
        if boundaries == (0, 0):
            return None
        
        zones = self._load_zones('instrument', boundaries)
        return SF2Instrument(instrument_id, zones)
    
    def get_sample(self, sample_id: int) -> Optional[np.ndarray]:
        """Get sample data with lazy loading."""
        if not self.is_initialized:
            return None
        
        # Check cache first
        cache_key = f"sample_{sample_id}"
        cached_sample = self.sample_cache.get(cache_key)
        if cached_sample is not None:
            return cached_sample
        
        # Load from file
        header_offset, data_offset = self.index_system.get_sample_offsets(sample_id)
        if header_offset == 0 or data_offset == 0:
            return None
        
        with self.file_lock:
            if self.file_handle is None:
                return None
            
            # Read sample header
            self.file_handle.seek(header_offset)
            header_data = self.file_handle.read(46)
            if len(header_data) < 46:
                return None
            
            # Parse sample header
            start, end = struct.unpack('<II', header_data[20:28])
            sample_type = struct.unpack('<H', header_data[44:46])[0]
            
            # Determine sample format
            is_stereo = bool(sample_type & 0x0001)
            is_24bit = bool(sample_type & 0x8000)
            
            sample_count = end - start
            
            # Read sample data
            self.file_handle.seek(data_offset)
            if is_24bit:
                bytes_per_sample = 3
                if is_stereo:
                    bytes_per_sample *= 2
                sample_bytes = self.file_handle.read(
                    sample_count * bytes_per_sample
                )
                sample_data = self._convert_24bit_sample(
                    sample_bytes, sample_count, is_stereo
                )
            else:
                bytes_per_sample = 2
                if is_stereo:
                    bytes_per_sample *= 2
                sample_bytes = self.file_handle.read(
                    sample_count * bytes_per_sample
                )
                sample_data = self._convert_16bit_sample(
                    sample_bytes, sample_count, is_stereo
                )
            
            # Cache the sample
            self.sample_cache.put(cache_key, sample_data)
            return sample_data
    
    def _convert_24bit_sample(
        self, sample_bytes: bytes, sample_count: int, is_stereo: bool
    ) -> np.ndarray:
        """Convert 24-bit sample to float32."""
        if is_stereo:
            stereo_data = np.zeros((sample_count, 2), dtype=np.float32)
            for i in range(sample_count):
                # Left channel
                left_bytes = sample_bytes[i*6:i*6+3]
                if len(left_bytes) == 3:
                    left_int = int.from_bytes(left_bytes, 'little', signed=True)
                    if left_int & 0x800000:
                        left_int |= 0xFF000000
                    stereo_data[i, 0] = left_int / 8388608.0
                
                # Right channel
                right_bytes = sample_bytes[i*6+3:i*6+6]
                if len(right_bytes) == 3:
                    right_int = int.from_bytes(right_bytes, 'little', signed=True)
                    if right_int & 0x800000:
                        right_int |= 0xFF000000
                    stereo_data[i, 1] = right_int / 8388608.0
            return stereo_data
        else:
            sample_data = np.zeros(sample_count, dtype=np.float32)
            for i in range(sample_count):
                sample_24bit = sample_bytes[i*3:(i+1)*3]
                if len(sample_24bit) == 3:
                    sample_int = int.from_bytes(sample_24bit, 'little', signed=True)
                    if sample_int & 0x800000:
                        sample_int |= 0xFF000000
                    sample_data[i] = sample_int / 8388608.0
            return sample_data
    
    def _convert_16bit_sample(
        self, sample_bytes: bytes, sample_count: int, is_stereo: bool
    ) -> np.ndarray:
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
        
        # Get bag data
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
            zone = self._create_zone(
                zone_type, gen_data, mod_data, gen_start, gen_end, mod_start, mod_end
            )
            
            # Cache the zone
            self.zone_cache.put(cache_key, zone)
            zones.append(zone)
        
        return zones
    
    def _load_bag_data(self, chunk_name: str, start_bag: int, end_bag: int) -> List[Tuple[int, int]]:
        """Load bag data for specified range."""
        if chunk_name not in self.index_system.chunk_offsets:
            return []
        
        offset, size = self.index_system.get_chunk_offset(chunk_name)
        bag_data = []
        
        with self.file_lock:
            if self.file_handle is None:
                return []
            
            # Each bag entry is 4 bytes: gen_ndx (2), mod_ndx (2)
            entry_size = 4
            count = end_bag - start_bag
            
            for i in range(count):
                bag_offset = offset + (start_bag + i) * entry_size
                self.file_handle.seek(bag_offset)
                entry_data = self.file_handle.read(entry_size)
                if len(entry_data) < entry_size:
                    break
                
                gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
                bag_data.append((gen_ndx, mod_ndx))
        
        return bag_data
    
    def _load_generator_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """Load generator data."""
        if chunk_name not in self.index_system.chunk_offsets:
            return []
        
        offset, size = self.index_system.get_chunk_offset(chunk_name)
        gen_data = []
        
        with self.file_lock:
            if self.file_handle is None:
                return []
            
            # Each generator entry is 4 bytes
            entry_size = 4
            count = size // entry_size
            
            for i in range(count):
                gen_offset = offset + i * entry_size
                self.file_handle.seek(gen_offset)
                entry_data = self.file_handle.read(entry_size)
                if len(entry_data) < entry_size:
                    break
                
                gen_type, gen_amount = struct.unpack('<Hh', entry_data)
                gen_data.append((gen_type, gen_amount))
        
        return gen_data
    
    def _load_modulator_data(self, chunk_name: str) -> List[Dict[str, int]]:
        """Load modulator data."""
        if chunk_name not in self.index_system.chunk_offsets:
            return []
        
        offset, size = self.index_system.get_chunk_offset(chunk_name)
        mod_data = []
        
        with self.file_lock:
            if self.file_handle is None:
                return []
            
            # Each modulator entry is 10 bytes
            entry_size = 10
            count = size // entry_size
            
            for i in range(count):
                mod_offset = offset + i * entry_size
                self.file_handle.seek(mod_offset)
                entry_data = self.file_handle.read(entry_size)
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
        
        # Finalize zone
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
        self.is_global = (
            self.sample_id == -1 and
            self.key_range == (0, 127) and
            self.velocity_range == (0, 127)
        )
    
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

class SF2ManagerV2:
    """Main SF2 manager API."""
    
    def __init__(self):
        self.file_managers: Dict[str, SF2FileManagerV2] = {}
        self.lock = threading.Lock()
    
    def load_file(self, filename: str) -> bool:
        """Load SF2 file."""
        try:
            manager = SF2FileManagerV2(filename)
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


# Backward compatibility
class LazySF2SoundFont:
    """Backward compatibility wrapper."""
    
    def __init__(self, filename: str, manager: SF2ManagerV2):
        self.filename = filename
        self.manager = manager
        self.sf2_manager = SF2FileManagerV2(filename)
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