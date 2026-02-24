"""
SF2 Zone Cache with Range Tree Optimization

Provides O(log n) lookups for zone matching based on key/velocity ranges.
Optimized for real-time synthesis with thousands of zones.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import math
from collections import defaultdict
from .sf2_data_model import SF2Zone


class RangeNode:
    """
    Node in the range tree for efficient 2D range queries.

    Stores key and velocity ranges for fast zone matching.
    """

    def __init__(
        self, zone: SF2Zone, key_min: int, key_max: int, vel_min: int, vel_max: int
    ):
        """
        Initialize range node.

        Args:
            zone: SF2 zone this node represents
            key_min: Minimum key range
            key_max: Maximum key range
            vel_min: Minimum velocity range
            vel_max: Maximum velocity range
        """
        self.zone = zone
        self.key_min = key_min
        self.key_max = key_max
        self.vel_min = vel_min
        self.vel_max = vel_max

        # Tree structure
        self.left: Optional["RangeNode"] = None
        self.right: Optional["RangeNode"] = None
        self.height = 1

    def overlaps(self, key: int, velocity: int) -> bool:
        """
        Check if this node's range overlaps with the given key/velocity.

        Args:
            key: MIDI key (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            True if ranges overlap
        """
        return (
            self.key_min <= key <= self.key_max
            and self.vel_min <= velocity <= self.vel_max
        )


class AVLRangeTree:
    """
    AVL-balanced range tree for efficient 2D range queries.

    Provides O(log n) lookup time for zone matching based on key/velocity ranges.
    """

    def __init__(self):
        """Initialize empty range tree."""
        self.root: Optional[RangeNode] = None
        self._node_count = 0

    def insert(self, zone: SF2Zone) -> None:
        """
        Insert a zone into the range tree.

        Args:
            zone: SF2 zone to insert
        """
        self.root = self._insert_recursive(self.root, zone)
        self._node_count += 1

    def _insert_recursive(self, node: Optional[RangeNode], zone: SF2Zone) -> RangeNode:
        """Recursive insertion with AVL balancing."""
        if node is None:
            return RangeNode(
                zone,
                zone.key_range[0],
                zone.key_range[1],
                zone.velocity_range[0],
                zone.velocity_range[1],
            )

        # Compare by key range start for ordering
        if zone.key_range[0] < node.key_min:
            node.left = self._insert_recursive(node.left, zone)
        else:
            node.right = self._insert_recursive(node.right, zone)

        # Update height
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))

        # Balance the tree
        balance = self._get_balance(node)

        # Left Left Case
        if balance > 1 and node.left and zone.key_range[0] < node.left.key_min:
            return self._right_rotate(node)

        # Right Right Case
        if balance < -1 and node.right and zone.key_range[0] > node.right.key_min:
            return self._left_rotate(node)

        # Left Right Case
        if balance > 1 and node.left and zone.key_range[0] > node.left.key_min:
            node.left = self._left_rotate(node.left)
            return self._right_rotate(node)

        # Right Left Case
        if balance < -1 and node.right and zone.key_range[0] < node.right.key_min:
            node.right = self._right_rotate(node.right)
            return self._left_rotate(node)

        return node

    def query(self, key: int, velocity: int) -> List[SF2Zone]:
        """
        Query zones that match the given key/velocity.

        Args:
            key: MIDI key (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones
        """
        result = []
        self._query_recursive(self.root, key, velocity, result)
        return result

    def _query_recursive(
        self, node: Optional[RangeNode], key: int, velocity: int, result: List[SF2Zone]
    ) -> None:
        """Recursive range query with proper pruning."""
        if node is None:
            return

        # Check current node
        if node.overlaps(key, velocity):
            result.append(node.zone)

        # Prune: only search left subtree if key is within left subtree's range
        if node.left and key >= node.left.key_min:
            self._query_recursive(node.left, key, velocity, result)

        # Prune: only search right subtree if key is within right subtree's range
        if node.right and key <= node.right.key_max:
            self._query_recursive(node.right, key, velocity, result)

    def clear(self) -> None:
        """Clear the tree."""
        self.root = None
        self._node_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get tree statistics.

        Returns:
            Dictionary with tree statistics
        """
        return {
            "node_count": self._node_count,
            "height": self._get_height(self.root),
            "is_balanced": self._is_balanced(),
        }

    def _get_height(self, node: Optional[RangeNode]) -> int:
        """Get node height."""
        return node.height if node else 0

    def _get_balance(self, node: Optional[RangeNode]) -> int:
        """Get balance factor."""
        if node is None:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)

    def _left_rotate(self, z: RangeNode) -> RangeNode:
        """Left rotation for AVL balancing."""
        y = z.right
        T2 = y.left

        y.left = z
        z.right = T2

        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

    def _right_rotate(self, z: RangeNode) -> RangeNode:
        """Right rotation for AVL balancing."""
        y = z.left
        T3 = y.right

        y.right = z
        z.left = T3

        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))

        return y

    def _is_balanced(self) -> bool:
        """Check if tree is balanced."""
        return abs(self._get_balance(self.root)) <= 1


class HierarchicalZoneCache:
    """
    Hierarchical zone cache with multiple lookup strategies.

    Combines range tree for fast lookups with hash-based caching for repeated queries.
    """

    def __init__(self):
        """Initialize hierarchical cache."""
        self.range_tree = AVLRangeTree()
        self.query_cache: Dict[Tuple[int, int], List[SF2Zone]] = {}
        self.max_cache_size = 1000  # Maximum cached queries
        self.cache_hits = 0
        self.cache_misses = 0

    def add_zone(self, zone: SF2Zone) -> None:
        """
        Add zone to the cache.

        Args:
            zone: Zone to add
        """
        self.range_tree.insert(zone)
        # Clear query cache when zones change
        self.query_cache.clear()

    def add_zones(self, zones: List[SF2Zone]) -> None:
        """
        Add multiple zones efficiently.

        Args:
            zones: List of zones to add
        """
        for zone in zones:
            self.range_tree.insert(zone)
        # Clear query cache when zones change
        self.query_cache.clear()

    def get_matching_zones(self, key: int, velocity: int) -> List[SF2Zone]:
        """
        Get zones matching the given key/velocity with caching.

        Args:
            key: MIDI key (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones
        """
        cache_key = (key, velocity)

        # Check query cache first
        if cache_key in self.query_cache:
            self.cache_hits += 1
            return self.query_cache[cache_key].copy()

        # Perform range query
        self.cache_misses += 1
        zones = self.range_tree.query(key, velocity)

        # Cache result if cache not too large
        if len(self.query_cache) < self.max_cache_size:
            self.query_cache[cache_key] = zones.copy()

        return zones

    def clear(self) -> None:
        """Clear all caches."""
        self.range_tree.clear()
        self.query_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_queries = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_queries * 100) if total_queries > 0 else 0.0

        tree_stats = self.range_tree.get_stats()

        return {
            "tree_stats": tree_stats,
            "query_cache_size": len(self.query_cache),
            "max_cache_size": self.max_cache_size,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_queries": total_queries,
            "hit_rate_percent": round(hit_rate, 2),
        }


class SF2ZoneCacheManager:
    """
    Manager for multiple zone caches (preset and instrument level).

    Provides efficient caching and lookup for all zones in an SF2 file.
    """

    def __init__(self):
        """Initialize zone cache manager."""
        self.preset_caches: Dict[
            int, HierarchicalZoneCache
        ] = {}  # bank_program -> cache
        self.instrument_caches: Dict[
            int, HierarchicalZoneCache
        ] = {}  # instrument_index -> cache
        self.global_preset_cache: Optional[HierarchicalZoneCache] = None
        self.global_instrument_cache: Optional[HierarchicalZoneCache] = None

    def add_preset_zones(self, bank: int, program: int, zones: List[SF2Zone]) -> None:
        """
        Add zones for a specific preset.

        Args:
            bank: MIDI bank number
            program: MIDI program number
            zones: List of zones for this preset
        """
        cache_key = (bank << 8) | program  # Combine bank and program
        cache = HierarchicalZoneCache()
        cache.add_zones(zones)
        self.preset_caches[cache_key] = cache

    def add_instrument_zones(self, instrument_index: int, zones: List[SF2Zone]) -> None:
        """
        Add zones for a specific instrument.

        Args:
            instrument_index: Instrument index
            zones: List of zones for this instrument
        """
        cache = HierarchicalZoneCache()
        cache.add_zones(zones)
        self.instrument_caches[instrument_index] = cache

    def add_global_preset_zones(self, zones: List[SF2Zone]) -> None:
        """
        Add global preset zones that apply to all presets.

        Args:
            zones: Global preset zones
        """
        self.global_preset_cache = HierarchicalZoneCache()
        self.global_preset_cache.add_zones(zones)

    def add_global_instrument_zones(self, zones: List[SF2Zone]) -> None:
        """
        Add global instrument zones that apply to all instruments.

        Args:
            zones: Global instrument zones
        """
        self.global_instrument_cache = HierarchicalZoneCache()
        self.global_instrument_cache.add_zones(zones)

    def get_preset_zones(
        self, bank: int, program: int, key: int, velocity: int
    ) -> List[SF2Zone]:
        """
        Get zones for a preset that match the given key/velocity.

        Args:
            bank: MIDI bank number
            program: MIDI program number
            key: MIDI key (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones
        """
        zones = []

        # Add global preset zones
        if self.global_preset_cache:
            zones.extend(self.global_preset_cache.get_matching_zones(key, velocity))

        # Add specific preset zones
        cache_key = (bank << 8) | program
        if cache_key in self.preset_caches:
            zones.extend(
                self.preset_caches[cache_key].get_matching_zones(key, velocity)
            )

        return zones

    def get_instrument_zones(
        self, instrument_index: int, key: int, velocity: int
    ) -> List[SF2Zone]:
        """
        Get zones for an instrument that match the given key/velocity.

        Args:
            instrument_index: Instrument index
            key: MIDI key (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones
        """
        zones = []

        # Add global instrument zones
        if self.global_instrument_cache:
            zones.extend(self.global_instrument_cache.get_matching_zones(key, velocity))

        # Add specific instrument zones
        if instrument_index in self.instrument_caches:
            zones.extend(
                self.instrument_caches[instrument_index].get_matching_zones(
                    key, velocity
                )
            )

        return zones

    def preload_hot_zones(
        self, common_keys: List[int] = None, common_velocities: List[int] = None
    ) -> None:
        """
        Preload cache for commonly used key/velocity combinations.

        Args:
            common_keys: List of commonly used keys (default: C major scale)
            common_velocities: List of commonly used velocities (default: forte range)
        """
        if common_keys is None:
            # C major scale
            common_keys = [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72]

        if common_velocities is None:
            # Forte range
            common_velocities = [80, 90, 100, 110, 120, 127]

        # Preload cache for all combinations
        for cache in self.preset_caches.values():
            for key in common_keys:
                for vel in common_velocities:
                    cache.get_matching_zones(key, vel)

        for cache in self.instrument_caches.values():
            for key in common_keys:
                for vel in common_velocities:
                    cache.get_matching_zones(key, vel)

    def clear_all_caches(self) -> None:
        """Clear all zone caches."""
        for cache in self.preset_caches.values():
            cache.clear()
        for cache in self.instrument_caches.values():
            cache.clear()

        if self.global_preset_cache:
            self.global_preset_cache.clear()
        if self.global_instrument_cache:
            self.global_instrument_cache.clear()

        self.preset_caches.clear()
        self.instrument_caches.clear()

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        preset_cache_count = len(self.preset_caches)
        instrument_cache_count = len(self.instrument_caches)

        total_preset_zones = sum(
            cache.range_tree._node_count for cache in self.preset_caches.values()
        )
        total_instrument_zones = sum(
            cache.range_tree._node_count for cache in self.instrument_caches.values()
        )

        global_preset_zones = (
            self.global_preset_cache.range_tree._node_count
            if self.global_preset_cache
            else 0
        )
        global_instrument_zones = (
            self.global_instrument_cache.range_tree._node_count
            if self.global_instrument_cache
            else 0
        )

        return {
            "preset_caches": preset_cache_count,
            "instrument_caches": instrument_cache_count,
            "total_preset_zones": total_preset_zones,
            "total_instrument_zones": total_instrument_zones,
            "global_preset_zones": global_preset_zones,
            "global_instrument_zones": global_instrument_zones,
            "total_zones": total_preset_zones
            + total_instrument_zones
            + global_preset_zones
            + global_instrument_zones,
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for all caches.

        Returns:
            Dictionary with performance metrics
        """
        stats = {
            "preset_cache_stats": {},
            "instrument_cache_stats": {},
            "global_preset_stats": None,
            "global_instrument_stats": None,
        }

        # Collect stats from preset caches
        for cache_key, cache in self.preset_caches.items():
            bank = cache_key >> 8
            program = cache_key & 0xFF
            stats["preset_cache_stats"][f"{bank}:{program}"] = cache.get_stats()

        # Collect stats from instrument caches
        for inst_idx, cache in self.instrument_caches.items():
            stats["instrument_cache_stats"][str(inst_idx)] = cache.get_stats()

        # Global cache stats
        if self.global_preset_cache:
            stats["global_preset_stats"] = self.global_preset_cache.get_stats()
        if self.global_instrument_cache:
            stats["global_instrument_stats"] = self.global_instrument_cache.get_stats()

        return stats
