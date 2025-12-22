"""
Enhanced SF2 Manager with Stereo Sample Support and Multi-Partial Presets

Extends the existing SF2 manager with advanced features:
- Stereo sample loading and playback
- Multi-partial preset architecture
- Enhanced region management
- Professional sample processing
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..audio.sample_manager import PyAVSampleManager, SFZSample
from .manager import SF2Manager


class EnhancedSF2Sample:
    """
    Enhanced SF2 sample with stereo support and professional features.

    Supports both mono and stereo SF2 samples with proper channel handling.
    """

    def __init__(self, sf2_sample_data: Any, sample_rate: int, is_stereo: bool = False):
        """
        Initialize enhanced SF2 sample.

        Args:
            sf2_sample_data: Raw SF2 sample data
            sample_rate: Sample rate in Hz
            is_stereo: Whether sample is stereo
        """
        self.sample_rate = sample_rate
        self.is_stereo = is_stereo
        self.original_link = getattr(sf2_sample_data, 'original_link', None)

        # Handle stereo SF2 samples (linked samples)
        if is_stereo and hasattr(sf2_sample_data, 'linked_sample'):
            # This is a stereo pair - left channel
            self.left_channel = sf2_sample_data.data
            self.right_channel = sf2_sample_data.linked_sample.data
            self.data = self.left_channel  # For compatibility
        else:
            # Mono sample
            self.data = sf2_sample_data.data
            self.left_channel = self.data
            self.right_channel = self.data

        # SF2-specific metadata
        self.loop_start = getattr(sf2_sample_data, 'loop_start', 0)
        self.loop_end = getattr(sf2_sample_data, 'loop_end', len(self.data))
        self.sample_type = getattr(sf2_sample_data, 'sample_type', 'mono')

        # Enhanced metadata
        self.root_key = getattr(sf2_sample_data, 'original_pitch', 60)
        self.fine_tune = getattr(sf2_sample_data, 'pitch_correction', 0)
        self.overriding_root_key = getattr(sf2_sample_data, 'overriding_root_key', -1)

    def get_channel_data(self, channel: int) -> Any:
        """Get data for specific channel (0=left, 1=right)."""
        if channel == 0:
            return self.left_channel
        elif channel == 1:
            return self.right_channel
        else:
            return self.left_channel  # Default to left

    def get_duration_seconds(self) -> float:
        """Get sample duration in seconds."""
        return len(self.data) / self.sample_rate

    def is_linked_sample(self) -> bool:
        """Check if this is part of a stereo pair."""
        return self.original_link is not None


class EnhancedSF2Region:
    """
    Enhanced SF2 region with multi-partial support and advanced features.

    Supports stereo samples, multiple partials per region, and advanced
    synthesis parameters beyond basic SF2 specification.
    """

    def __init__(self, zone_data: Any, sample_manager: PyAVSampleManager):
        """
        Initialize enhanced SF2 region.

        Args:
            zone_data: SF2 zone/preset zone data
            sample_manager: Sample manager for loading samples
        """
        self.zone_data = zone_data
        self.sample_manager = sample_manager

        # Basic SF2 region parameters
        self.key_range = (getattr(zone_data, 'key_range_low', 0),
                         getattr(zone_data, 'key_range_high', 127))
        self.velocity_range = (getattr(zone_data, 'vel_range_low', 0),
                              getattr(zone_data, 'vel_range_high', 127))

        # Sample information
        self.sample = None
        self.sample_path = getattr(zone_data, 'sample', None)

        # Load sample if available
        if hasattr(zone_data, 'sample') and zone_data.sample:
            try:
                # Check if it's an enhanced SF2 sample
                if hasattr(zone_data.sample, 'is_stereo'):
                    self.sample = zone_data.sample
                else:
                    # Create enhanced sample wrapper
                    is_stereo = hasattr(zone_data.sample, 'linked_sample') and zone_data.sample.linked_sample is not None
                    self.sample = EnhancedSF2Sample(zone_data.sample, zone_data.sample.sample_rate, is_stereo)
            except Exception as e:
                print(f"Warning: Failed to load SF2 sample: {e}")
                self.sample = None

        # SF2 synthesis parameters
        self.pan = getattr(zone_data, 'pan', 0) / 500.0  # SF2 pan is -500 to 500
        self.volume = getattr(zone_data, 'attenuation', 0)  # dB attenuation
        self.root_key = getattr(zone_data, 'root_key', 60)
        self.fine_tune = getattr(zone_data, 'fine_tune', 0)
        self.coarse_tune = getattr(zone_data, 'coarse_tune', 0)

        # Filter parameters
        self.filter_cutoff = getattr(zone_data, 'initial_filter_cutoff', 13500)
        self.filter_resonance = getattr(zone_data, 'initial_filter_resonance', 0)

        # Envelope parameters (SF2 style)
        self.vol_env_delay = getattr(zone_data, 'vol_env_delay', 0)
        self.vol_env_attack = getattr(zone_data, 'vol_env_attack', 0)
        self.vol_env_hold = getattr(zone_data, 'vol_env_hold', 0)
        self.vol_env_decay = getattr(zone_data, 'vol_env_decay', 0)
        self.vol_env_sustain = getattr(zone_data, 'vol_env_sustain', 1000)  # 0-1000
        self.vol_env_release = getattr(zone_data, 'vol_env_release', 0)

        # Filter envelope
        self.mod_env_delay = getattr(zone_data, 'mod_env_delay', 0)
        self.mod_env_attack = getattr(zone_data, 'mod_env_attack', 0)
        self.mod_env_hold = getattr(zone_data, 'mod_env_hold', 0)
        self.mod_env_decay = getattr(zone_data, 'mod_env_decay', 0)
        self.mod_env_sustain = getattr(zone_data, 'mod_env_sustain', 1000)
        self.mod_env_release = getattr(zone_data, 'mod_env_release', 0)

        # LFO parameters
        self.vib_lfo_freq = getattr(zone_data, 'vib_lfo_freq', 0)
        self.vib_lfo_delay = getattr(zone_data, 'vib_lfo_delay', 0)
        self.mod_lfo_freq = getattr(zone_data, 'mod_lfo_freq', 0)
        self.mod_lfo_delay = getattr(zone_data, 'mod_lfo_delay', 0)

        # Enhanced parameters (beyond SF2)
        self.modulation_matrix_routes = self._extract_modulation_routes(zone_data)

        # Multi-partial support
        self.partials = self._create_partials(zone_data)

    def _extract_modulation_routes(self, zone_data: Any) -> List[Dict[str, Any]]:
        """Extract modulation routes from SF2 zone data."""
        routes = []

        # Basic SF2 modulation routes
        if hasattr(zone_data, 'modulators'):
            for mod in zone_data.modulators:
                route = {
                    'source': self._map_sf2_modulator_source(mod.source),
                    'destination': self._map_sf2_modulator_dest(mod.destination),
                    'amount': mod.amount,
                    'transform': mod.transform_type
                }
                routes.append(route)

        return routes

    def _map_sf2_modulator_source(self, source: int) -> str:
        """Map SF2 modulator source to standard name."""
        # SF2 controller sources
        source_map = {
            0: 'none',
            2: 'velocity',
            3: 'key',
            10: 'pan',
            13: 'channel_pressure',
            14: 'pitch_bend',
            16: 'timbre',  # Brightness
            17: 'pitch',   # Coarse tune
            18: 'fine_tune',
            19: 'sample_volume',  # Initial volume
            20: 'sample_pan',     # Initial pan
        }
        return source_map.get(source, f'cc{source}')

    def _map_sf2_modulator_dest(self, dest: int) -> str:
        """Map SF2 modulator destination to standard name."""
        dest_map = {
            0: 'none',
            8: 'pan',
            9: 'key',
            10: 'vibrato',
            11: 'tremolo',
            15: 'volume',
            16: 'timbre',  # Brightness/filter
            17: 'pitch',
            18: 'fine_tune',
            19: 'sample_volume',
            20: 'sample_pan',
            21: 'loop_start',
            22: 'loop_end',
            23: 'filter_cutoff',
            24: 'filter_resonance',
        }
        return dest_map.get(dest, f'unknown_{dest}')

    def _create_partials(self, zone_data: Any) -> List[Any]:
        """Create partials for multi-partial support."""
        partials = []

        # Basic SF2 has one partial per zone
        # Enhanced version could support multiple partials
        partial = {
            'level': 1.0,
            'pan': self.pan,
            'coarse_tune': self.coarse_tune,
            'fine_tune': self.fine_tune,
            'root_key': self.root_key,
            'key_range': self.key_range,
            'velocity_range': self.velocity_range,
            'filter_cutoff': self.filter_cutoff,
            'filter_resonance': self.filter_resonance,
            'sample': self.sample
        }
        partials.append(partial)

        return partials

    def should_play_for_note(self, note: int, velocity: int) -> bool:
        """Check if region should play for given note and velocity."""
        return (self.key_range[0] <= note <= self.key_range[1] and
                self.velocity_range[0] <= velocity <= self.velocity_range[1])

    def get_pitch_ratio(self, note: int) -> float:
        """Calculate pitch ratio for given note."""
        # Use overriding root key if set, otherwise use sample root key
        root_key = self.root_key
        if hasattr(self, 'overriding_root_key') and self.overriding_root_key >= 0:
            root_key = self.overriding_root_key

        # Calculate semitone offset
        semitones = note - root_key + self.coarse_tune + (self.fine_tune / 100.0)

        # Convert to frequency ratio
        return 2.0 ** (semitones / 12.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert region to dictionary for processing."""
        return {
            'key_range': self.key_range,
            'velocity_range': self.velocity_range,
            'pan': self.pan,
            'volume': self.volume,
            'root_key': self.root_key,
            'fine_tune': self.fine_tune,
            'coarse_tune': self.coarse_tune,
            'filter_cutoff': self.filter_cutoff,
            'filter_resonance': self.filter_resonance,
            'has_sample': self.sample is not None,
            'is_stereo': self.sample.is_stereo if self.sample else False,
            'partials': self.partials,
            'modulation_routes': self.modulation_matrix_routes
        }


class MultiPartialSF2Preset:
    """
    Enhanced SF2 preset with multiple partials per note.

    Supports complex preset architectures where multiple samples/regions
    can be combined for rich, layered instrument sounds.
    """

    def __init__(self, preset_data: Any, sample_manager: PyAVSampleManager):
        """
        Initialize multi-partial SF2 preset.

        Args:
            preset_data: SF2 preset data
            sample_manager: Sample manager for loading samples
        """
        self.name = getattr(preset_data, 'name', 'Unnamed Preset')
        self.bank = getattr(preset_data, 'bank', 0)
        self.program = getattr(preset_data, 'program', 0)

        # Global preset parameters
        self.global_volume = 0.0  # dB
        self.global_pan = 0.0
        self.global_coarse_tune = 0
        self.global_fine_tune = 0

        # Multi-partial architecture
        self.partials = self._build_partial_hierarchy(preset_data, sample_manager)

        # Region cache for performance
        self.region_cache: Dict[Tuple[int, int], List[EnhancedSF2Region]] = {}

    def _build_partial_hierarchy(self, preset_data: Any, sample_manager: PyAVSampleManager) -> List[Dict[str, Any]]:
        """Build partial hierarchy from SF2 preset zones."""
        partials = []

        # Group zones by instrument (SF2 partial concept)
        instrument_groups = self._group_zones_by_instrument(preset_data.zones)

        for instrument_name, zones in instrument_groups.items():
            partial = {
                'name': instrument_name,
                'level': 1.0,
                'pan': 0.0,
                'coarse_tune': 0,
                'fine_tune': 0,
                'regions': []
            }

            # Create regions for this partial
            for zone in zones:
                region = EnhancedSF2Region(zone, sample_manager)
                partial['regions'].append(region)

            partials.append(partial)

        return partials

    def _group_zones_by_instrument(self, zones: List[Any]) -> Dict[str, List[Any]]:
        """Group preset zones by instrument."""
        groups = {}

        for zone in zones:
            # Use instrument name as grouping key
            if hasattr(zone, 'instrument') and zone.instrument:
                inst_name = zone.instrument.name
            else:
                inst_name = 'default'

            if inst_name not in groups:
                groups[inst_name] = []
            groups[inst_name].append(zone)

        return groups

    def get_regions_for_note(self, note: int, velocity: int) -> List[EnhancedSF2Region]:
        """
        Get all regions that should play for a given note/velocity.

        Returns regions from all partials that match the note/velocity criteria.
        """
        # Check cache first
        cache_key = (note, velocity)
        if cache_key in self.region_cache:
            return self.region_cache[cache_key]

        regions = []

        # Collect regions from all partials
        for partial in self.partials:
            for region in partial['regions']:
                if region.should_play_for_note(note, velocity):
                    regions.append(region)

        # Cache the result
        self.region_cache[cache_key] = regions
        return regions

    def get_preset_info(self) -> Dict[str, Any]:
        """Get comprehensive preset information."""
        total_regions = sum(len(partial['regions']) for partial in self.partials)
        stereo_regions = sum(
            len([r for r in partial['regions'] if r.sample and r.sample.is_stereo])
            for partial in self.partials
        )

        return {
            'name': self.name,
            'bank': self.bank,
            'program': self.program,
            'partials': len(self.partials),
            'total_regions': total_regions,
            'stereo_regions': stereo_regions,
            'mono_regions': total_regions - stereo_regions,
            'has_modulation': any(
                any(region.modulation_matrix_routes for region in partial['regions'])
                for partial in self.partials
            )
        }


class EnhancedSF2Manager:
    """
    Enhanced SF2 Manager with stereo support and multi-partial presets.

    Extends the base SF2 manager with advanced features:
    - Stereo sample loading and playback
    - Multi-partial preset architecture
    - Enhanced region management
    - Professional sample processing
    """

    def __init__(self, sample_manager: Optional[PyAVSampleManager] = None):
        """
        Initialize enhanced SF2 manager.

        Args:
            sample_manager: PyAV sample manager (created if None)
        """
        self.sample_manager = sample_manager or PyAVSampleManager()
        self.base_manager = SF2Manager()

        # Enhanced features
        self.loaded_presets: Dict[str, MultiPartialSF2Preset] = {}
        self.sample_cache: Dict[str, EnhancedSF2Sample] = {}

        # Statistics
        self.load_stats = {
            'total_presets': 0,
            'stereo_samples': 0,
            'mono_samples': 0,
            'multi_partial_presets': 0
        }

    def load_sf2_file(self, sf2_path: str) -> bool:
        """
        Load SF2 file with enhanced features.

        Args:
            sf2_path: Path to SF2 file

        Returns:
            True if loaded successfully
        """
        try:
            # Load with base manager first
            if not self.base_manager.load_sf2_file(sf2_path):
                return False

            # Enhance samples with stereo support
            self._enhance_samples()

            # Create multi-partial presets
            self._create_enhanced_presets()

            # Update statistics
            self._update_load_stats()

            print(f"🎹 Enhanced SF2: Loaded '{Path(sf2_path).name}' with stereo and multi-partial support")
            return True

        except Exception as e:
            print(f"Error loading enhanced SF2 file '{sf2_path}': {e}")
            return False

    def _enhance_samples(self):
        """Enhance SF2 samples with stereo support."""
        for sample_name, sample_data in self.base_manager.samples.items():
            # Check if sample has a linked sample (stereo)
            is_stereo = hasattr(sample_data, 'linked_sample') and sample_data.linked_sample is not None

            # Create enhanced sample
            enhanced_sample = EnhancedSF2Sample(sample_data, sample_data.sample_rate, is_stereo)
            self.sample_cache[sample_name] = enhanced_sample

    def _create_enhanced_presets(self):
        """Create multi-partial presets from SF2 data."""
        for preset_data in self.base_manager.presets:
            preset_key = f"{preset_data.bank}:{preset_data.program}"

            # Create enhanced preset
            enhanced_preset = MultiPartialSF2Preset(preset_data, self.sample_manager)
            self.loaded_presets[preset_key] = enhanced_preset

    def _update_load_stats(self):
        """Update loading statistics."""
        self.load_stats['total_presets'] = len(self.loaded_presets)
        self.load_stats['stereo_samples'] = sum(
            1 for sample in self.sample_cache.values() if sample.is_stereo
        )
        self.load_stats['mono_samples'] = len(self.sample_cache) - self.load_stats['stereo_samples']
        self.load_stats['multi_partial_presets'] = sum(
            1 for preset in self.loaded_presets.values()
            if len(preset.partials) > 1
        )

    def get_enhanced_preset(self, bank: int, program: int) -> Optional[MultiPartialSF2Preset]:
        """Get enhanced preset for bank/program."""
        preset_key = f"{bank}:{program}"
        return self.loaded_presets.get(preset_key)

    def get_program_parameters(self, program: int, bank: int = 0) -> Optional[Dict[str, Any]]:
        """Get program parameters with enhanced features."""
        # Try enhanced preset first
        enhanced_preset = self.get_enhanced_preset(bank, program)
        if enhanced_preset:
            return {
                'name': enhanced_preset.name,
                'bank': bank,
                'program': program,
                'is_multi_partial': len(enhanced_preset.partials) > 1,
                'total_regions': sum(len(p['regions']) for p in enhanced_preset.partials),
                'has_stereo_samples': any(
                    any(r.sample and r.sample.is_stereo for r in p['regions'])
                    for p in enhanced_preset.partials
                )
            }

        # Fall back to base manager
        return self.base_manager.get_program_parameters(program, bank)

    def get_available_presets(self) -> List[Tuple[int, int, str]]:
        """Get list of available presets with enhanced info."""
        presets = []

        # Add enhanced presets
        for preset_key, preset in self.loaded_presets.items():
            bank, program = map(int, preset_key.split(':'))
            info = preset.get_preset_info()
            display_name = f"{preset.name} ({info['partials']}p, {info['total_regions']}r)"
            if info['stereo_regions'] > 0:
                display_name += f" [{info['stereo_regions']}st]"
            presets.append((bank, program, display_name))

        # Add any base manager presets not covered
        base_presets = self.base_manager.get_available_presets()
        enhanced_keys = set(self.loaded_presets.keys())

        for bank, program, name in base_presets:
            preset_key = f"{bank}:{program}"
            if preset_key not in enhanced_keys:
                presets.append((bank, program, f"{name} (basic)"))

        return sorted(presets, key=lambda x: (x[0], x[1]))

    def get_load_stats(self) -> Dict[str, Any]:
        """Get loading statistics."""
        return self.load_stats.copy()

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        sample_memory = sum(
            sample.get_memory_usage_mb() for sample in self.sample_cache.values()
        )

        return {
            'sample_cache_mb': sample_memory,
            'loaded_presets': len(self.loaded_presets),
            'cached_samples': len(self.sample_cache),
            'pyav_cache': self.sample_manager.get_cache_stats()
        }

    def unload_sf2_file(self):
        """Unload current SF2 file and clear enhanced data."""
        self.base_manager.unload_sf2_file()
        self.loaded_presets.clear()
        self.sample_cache.clear()
        self.load_stats = {k: 0 for k in self.load_stats.keys()}

    def __str__(self) -> str:
        """String representation."""
        stats = self.get_load_stats()
        return (f"EnhancedSF2Manager(presets={stats['total_presets']}, "
                f"samples={stats['stereo_samples'] + stats['mono_samples']} "
                f"({stats['stereo_samples']}st/{stats['mono_samples']}mono))")
