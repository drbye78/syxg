"""
SF2 SoundFont Manager

Single optimized SF2 implementation managing multiple soundfonts with complete feature set.
Handles ordering, blacklisting, remapping, and orchestrates all SF2 components.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any


class SF2SoundFontManager:
    """
    Single optimized SF2 SoundFont manager with complete feature set.

    Manages multiple SF2 files with ordering, blacklisting, remapping, and full
    SF2 specification compliance. Orchestrates all SF2 components for high-performance synthesis.
    """

    def __init__(self, cache_memory_mb: int = 256, max_loaded_files: int = 10):
        """
        Initialize SF2 SoundFont manager.

        Args:
            cache_memory_mb: Memory limit for sample caching across all files
            max_loaded_files: Maximum number of SF2 files to keep loaded
        """
        self.cache_memory_mb = cache_memory_mb
        self.max_loaded_files = max_loaded_files

        # File management
        self.loaded_files: dict[str, SF2SoundFont] = {}  # filepath -> soundfont
        self.file_order: list[str] = []  # File loading order for preset resolution
        self.file_blacklist: set[tuple[int, int]] = set()  # (bank, program) to blacklist
        self.file_remapping: dict[
            tuple[int, int], tuple[int, int]
        ] = {}  # (bank, program) -> (new_bank, new_program)

        # Core components
        self.sample_processor = None  # Will be initialized when first file is loaded
        self.zone_cache_manager = None
        self.modulation_engine = None

        # Statistics and performance tracking
        self.load_times: dict[str, float] = {}
        self.access_counts: dict[str, int] = {}
        self._lock = threading.RLock()

        # Initialize core components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize core SF2 components."""
        from .sf2_modulation_engine import SF2ModulationEngine
        from .sf2_sample_processor import SF2SampleProcessor
        from .sf2_zone_cache import SF2ZoneCacheManager

        self.sample_processor = SF2SampleProcessor(cache_memory_mb=self.cache_memory_mb)
        self.zone_cache_manager = SF2ZoneCacheManager()
        self.modulation_engine = SF2ModulationEngine()

    def load_soundfont(self, filepath: str, priority: int = 0) -> bool:
        """
        Load SF2 soundfont with priority ordering.

        Args:
            filepath: Path to SF2 file
            priority: Loading priority (higher = loaded first, used first for conflicts)

        Returns:
            True if loaded successfully
        """
        filepath = str(Path(filepath).resolve())

        with self._lock:
            # Check if already loaded
            if filepath in self.loaded_files:
                # Update access count and move to end of order
                self.access_counts[filepath] += 1
                if filepath in self.file_order:
                    self.file_order.remove(filepath)
                self.file_order.append(filepath)
                return True

            # Enforce maximum loaded files limit
            if len(self.loaded_files) >= self.max_loaded_files:
                self._evict_least_recently_used()

            # Load the soundfont
            start_time = time.time()

            try:
                from .sf2_soundfont import SF2SoundFont

                soundfont = SF2SoundFont(
                    filepath, self.sample_processor, self.zone_cache_manager, self.modulation_engine
                )

                if soundfont.load():
                    self.loaded_files[filepath] = soundfont
                    self.load_times[filepath] = time.time() - start_time
                    self.access_counts[filepath] = 1

                    # Insert into order based on priority
                    self._insert_file_by_priority(filepath, priority)

                    print(f"🎹 SF2: Loaded '{soundfont.name}' in {self.load_times[filepath]:.2f}s")
                    return True
                else:
                    print(f"❌ SF2: Failed to load '{filepath}'")
                    return False

            except Exception as e:
                print(f"❌ SF2: Error loading '{filepath}': {e}")
                return False

    def _insert_file_by_priority(self, filepath: str, priority: int) -> None:
        """
        Insert file into loading order based on priority.

        Args:
            filepath: File path
            priority: Priority level
        """
        # Remove if already in order
        if filepath in self.file_order:
            self.file_order.remove(filepath)

        # Find insertion point (higher priority = earlier in list)
        insert_pos = 0
        for i, existing_file in enumerate(self.file_order):
            existing_priority = getattr(self.loaded_files.get(existing_file), "priority", 0)
            if priority > existing_priority:
                insert_pos = i
                break
            insert_pos = i + 1

        self.file_order.insert(insert_pos, filepath)

        # Update soundfont priority
        if filepath in self.loaded_files:
            self.loaded_files[filepath].priority = priority

    def _evict_least_recently_used(self) -> None:
        """Evict least recently used soundfont to make room for new one."""
        if not self.file_order:
            return

        # Find file with lowest access count
        lru_file = min(self.file_order, key=lambda f: self.access_counts.get(f, 0))

        # Remove it
        if lru_file in self.loaded_files:
            self.loaded_files[lru_file].unload()
            del self.loaded_files[lru_file]

        if lru_file in self.load_times:
            del self.load_times[lru_file]

        if lru_file in self.access_counts:
            del self.access_counts[lru_file]

        self.file_order.remove(lru_file)

    def unload_soundfont(self, filepath: str) -> bool:
        """
        Unload a specific soundfont.

        Args:
            filepath: Path to SF2 file

        Returns:
            True if unloaded successfully
        """
        filepath = str(Path(filepath).resolve())

        with self._lock:
            if filepath not in self.loaded_files:
                return False

            self.loaded_files[filepath].unload()
            del self.loaded_files[filepath]

            if filepath in self.file_order:
                self.file_order.remove(filepath)

            if filepath in self.load_times:
                del self.load_times[filepath]

            if filepath in self.access_counts:
                del self.access_counts[filepath]

            return True

    def get_program_parameters(
        self, bank: int, program: int, note: int = 60, velocity: int = 100
    ) -> dict[str, Any] | None:
        """
        Get program parameters with remapping and blacklisting support.

        Args:
            bank: MIDI bank number
            program: MIDI program number
            note: MIDI note (for zone matching)
            velocity: MIDI velocity (for zone matching)

        Returns:
            Program parameters or None if not found/blacklisted
        """
        # Check blacklisting
        if (bank, program) in self.file_blacklist:
            return None

        # Check remapping
        original_bank, original_program = bank, program
        if (bank, program) in self.file_remapping:
            bank, program = self.file_remapping[(bank, program)]

        # Search through files in priority order
        with self._lock:
            for filepath in self.file_order:
                if filepath in self.loaded_files:
                    soundfont = self.loaded_files[filepath]
                    params = soundfont.get_program_parameters(bank, program, note, velocity)

                    if params:
                        # Update access statistics
                        self.access_counts[filepath] += 1

                        # Add metadata
                        params["source_file"] = filepath
                        params["original_bank"] = original_bank
                        params["original_program"] = original_program
                        params["remapped_bank"] = bank
                        params["remapped_program"] = program

                        return params

        return None

    # NOTE: get_sample_info / get_sample_loop_info / get_zone are defined later in this file
    # with unified implementations that support optional soundfont_path. The older versions
    # that were here have been removed to avoid duplicate, conflicting definitions.

    def get_available_programs(self) -> list[tuple[int, int, str]]:
        """
        Get all available programs across all loaded soundfonts.

        Returns:
            List of (bank, program, name) tuples
        """
        programs = []

        with self._lock:
            for filepath in self.file_order:
                if filepath in self.loaded_files:
                    soundfont = self.loaded_files[filepath]
                    file_programs = soundfont.get_available_programs()

                    # Filter out blacklisted programs
                    filtered_programs = [
                        (bank, prog, name)
                        for bank, prog, name in file_programs
                        if (bank, prog) not in self.file_blacklist
                    ]

                    programs.extend(filtered_programs)

        # Remove duplicates (later files override earlier ones with same bank/program)
        seen = set()
        unique_programs = []

        for bank, program, name in reversed(
            programs
        ):  # Process in reverse to prioritize later files
            key = (bank, program)
            if key not in seen:
                seen.add(key)
                unique_programs.append((bank, program, name))

        return list(reversed(unique_programs))  # Restore original order

    def blacklist_program(self, bank: int, program: int) -> None:
        """
        Blacklist a program so it won't be available.

        Args:
            bank: MIDI bank number
            program: MIDI program number
        """
        self.file_blacklist.add((bank, program))

    def unblacklist_program(self, bank: int, program: int) -> None:
        """
        Remove program from blacklist.

        Args:
            bank: MIDI bank number
            program: MIDI program number
        """
        self.file_blacklist.discard((bank, program))

    def remap_program(
        self, from_bank: int, from_program: int, to_bank: int, to_program: int
    ) -> None:
        """
        Remap a program to different bank/program numbers.

        Args:
            from_bank: Original MIDI bank number
            from_program: Original MIDI program number
            to_bank: Target MIDI bank number
            to_program: Target MIDI program number
        """
        self.file_remapping[(from_bank, from_program)] = (to_bank, to_program)

    def clear_remapping(self, bank: int, program: int) -> None:
        """
        Clear remapping for a program.

        Args:
            bank: MIDI bank number
            program: MIDI program number
        """
        key = (bank, program)
        if key in self.file_remapping:
            del self.file_remapping[key]

    def set_file_priority(self, filepath: str, priority: int) -> bool:
        """
        Set loading priority for a soundfont file.

        Args:
            filepath: Path to SF2 file
            priority: New priority level

        Returns:
            True if priority updated successfully
        """
        filepath = str(Path(filepath).resolve())

        with self._lock:
            if filepath not in self.loaded_files:
                return False

            self._insert_file_by_priority(filepath, priority)
            return True

    def get_sample_data(self, sample_id: int, soundfont_path: str | None = None) -> Any | None:
        """
        Get sample data with cross-file caching.

        Args:
            sample_id: Sample ID
            soundfont_path: Specific soundfont path (search all if None)

        Returns:
            Sample data or None if not found
        """
        with self._lock:
            if soundfont_path:
                # Get from specific soundfont
                soundfont_path = str(Path(soundfont_path).resolve())
                if soundfont_path in self.loaded_files:
                    return self.loaded_files[soundfont_path].get_sample_data(sample_id)
            else:
                # Search through all soundfonts in priority order
                for filepath in self.file_order:
                    if filepath in self.loaded_files:
                        sample_data = self.loaded_files[filepath].get_sample_data(sample_id)
                        if sample_data is not None:
                            return sample_data

        return None

    def get_sample_info(
        self, sample_id: int, soundfont_path: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get sample information (root key, name, sample rate, etc.).

        Args:
            sample_id: Sample ID
            soundfont_path: Specific soundfont path (search all if None)

        Returns:
            Sample info dictionary or None
        """
        with self._lock:
            # If a specific soundfont is requested, query only that one.
            if soundfont_path:
                sf_path = str(Path(soundfont_path).resolve())
                soundfont = self.loaded_files.get(sf_path)
                if soundfont and hasattr(soundfont, "get_sample_info"):
                    return soundfont.get_sample_info(sample_id)

            # Otherwise search through all loaded soundfonts in priority order.
            for filepath in self.file_order:
                soundfont = self.loaded_files.get(filepath)
                if not soundfont or not hasattr(soundfont, "get_sample_info"):
                    continue
                info = soundfont.get_sample_info(sample_id)
                if info:
                    return info

        return None

    def get_sample_loop_info(
        self, sample_id: int, soundfont_path: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get sample loop information.

        Args:
            sample_id: Sample ID
            soundfont_path: Specific soundfont path (search all if None)

        Returns:
            Loop info dictionary or None
        """
        with self._lock:
            # If a specific soundfont is requested, query only that one.
            if soundfont_path:
                sf_path = str(Path(soundfont_path).resolve())
                soundfont = self.loaded_files.get(sf_path)
                if soundfont and hasattr(soundfont, "get_sample_loop_info"):
                    return soundfont.get_sample_loop_info(sample_id)

            # Otherwise search through all loaded soundfonts in priority order.
            for filepath in self.file_order:
                soundfont = self.loaded_files.get(filepath)
                if not soundfont or not hasattr(soundfont, "get_sample_loop_info"):
                    continue
                info = soundfont.get_sample_loop_info(sample_id)
                if info:
                    return info

        return None

    def get_zone(self, region_id: int, bank: int = 0, program: int = 0) -> Any | None:
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
                soundfont = self.loaded_files.get(filepath)
                if not soundfont or not hasattr(soundfont, "get_zone"):
                    continue
                zone = soundfont.get_zone(bank, program, region_id)
                if zone:
                    return zone

        return None

    def update_controller(self, controller: int, value: int | float) -> None:
        """
        Update global controller value across all soundfonts.

        Args:
            controller: Controller number
            value: New value
        """
        if self.modulation_engine:
            self.modulation_engine.update_global_controller(controller, value)

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get comprehensive performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            stats = {
                "loaded_files": len(self.loaded_files),
                "file_order": self.file_order.copy(),
                "total_blacklisted": len(self.file_blacklist),
                "total_remapped": len(self.file_remapping),
                "file_stats": {},
                "memory_usage": self._get_memory_usage(),
                "cache_performance": {},
            }

            # Individual file statistics
            for filepath, soundfont in self.loaded_files.items():
                file_stats = {
                    "load_time": self.load_times.get(filepath, 0.0),
                    "access_count": self.access_counts.get(filepath, 0),
                    "program_count": len(soundfont.get_available_programs()),
                    "priority": getattr(soundfont, "priority", 0),
                }
                stats["file_stats"][filepath] = file_stats

            # Cache performance
            if self.sample_processor:
                stats["cache_performance"] = self.sample_processor.get_performance_stats()

            # Zone cache stats
            if self.zone_cache_manager:
                stats["zone_cache_stats"] = self.zone_cache_manager.get_performance_stats()

            return stats

    def _get_memory_usage(self) -> dict[str, Any]:
        """Get memory usage across all components."""
        memory_stats = {"total_mb": 0.0, "components": {}}

        # Sample processor memory
        if self.sample_processor:
            sample_stats = self.sample_processor.get_performance_stats()
            cache_stats = sample_stats.get("cache_stats", {})
            memory_stats["components"]["sample_cache"] = cache_stats.get("memory_usage_mb", 0.0)
            memory_stats["total_mb"] += memory_stats["components"]["sample_cache"]

        # Zone cache memory
        if self.zone_cache_manager:
            zone_stats = self.zone_cache_manager.get_memory_usage()
            memory_stats["components"]["zone_cache"] = (
                zone_stats.get("total_zones", 0) * 0.001
            )  # Rough estimate
            memory_stats["total_mb"] += memory_stats["components"]["zone_cache"]

        return memory_stats

    def clear_all_caches(self) -> None:
        """Clear all caches across all components."""
        with self._lock:
            if self.sample_processor:
                self.sample_processor.clear_cache()

            if self.zone_cache_manager:
                self.zone_cache_manager.clear_all_caches()

            if self.modulation_engine:
                self.modulation_engine.reset_all()

    def unload_all(self) -> None:
        """Unload all soundfonts and clear all data."""
        with self._lock:
            for soundfont in self.loaded_files.values():
                soundfont.unload()

            self.loaded_files.clear()
            self.file_order.clear()
            self.load_times.clear()
            self.access_counts.clear()

            self.clear_all_caches()

    def get_soundfont_info(
        self, filepath: str | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Get information about loaded soundfonts.

        Args:
            filepath: Specific file path, or None for all files

        Returns:
            Soundfont info dict, or list of all soundfont infos
        """
        with self._lock:
            if filepath:
                filepath = str(Path(filepath).resolve())
                if filepath in self.loaded_files:
                    return self.loaded_files[filepath].get_info()
                return {}
            else:
                return [sf.get_info() for sf in self.loaded_files.values()]

    def __len__(self) -> int:
        """Get number of loaded soundfonts."""
        return len(self.loaded_files)

    def __contains__(self, filepath: str) -> bool:
        """Check if a soundfont file is loaded."""
        return str(Path(filepath).resolve()) in self.loaded_files

    def __str__(self) -> str:
        """String representation."""
        with self._lock:
            return f"SF2SoundFontManager(loaded={len(self.loaded_files)}, order={self.file_order})"
