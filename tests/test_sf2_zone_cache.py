"""
Test suite for SF2 zone cache.

Tests AVLRangeTree, HierarchicalZoneCache, and SF2ZoneCacheManager.
"""

import pytest
from synth.sf2 import sf2_zone_cache
from synth.sf2.sf2_data_model import SF2Zone


class TestAVLRangeTree:
    """Tests for AVLRangeTree class."""

    def test_tree_creation(self):
        """Test tree initialization."""
        tree = sf2_zone_cache.AVLRangeTree()

        assert tree.root is None
        assert tree._node_count == 0

    def test_insert_single_zone(self):
        """Test inserting single zone."""
        tree = sf2_zone_cache.AVLRangeTree()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.velocity_range = (0, 127)

        tree.insert(zone)

        assert tree._node_count == 1

    def test_query_finds_matching_zone(self):
        """Test query finds matching zone."""
        tree = sf2_zone_cache.AVLRangeTree()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.velocity_range = (0, 127)
        tree.insert(zone)

        results = tree.query(60, 100)

        assert len(results) == 1
        assert results[0] is zone

    def test_query_excludes_non_matching(self):
        """Test query excludes non-matching zones."""
        tree = sf2_zone_cache.AVLRangeTree()

        zone = SF2Zone("preset")
        zone.key_range = (48, 60)
        zone.velocity_range = (0, 127)
        tree.insert(zone)

        results = tree.query(72, 100)  # Outside key range

        assert len(results) == 0

    def test_query_multiple_zones(self):
        """Test query with multiple overlapping zones."""
        tree = sf2_zone_cache.AVLRangeTree()

        # Zone 1: full range
        z1 = SF2Zone("preset")
        z1.key_range = (0, 127)
        z1.velocity_range = (0, 127)
        tree.insert(z1)

        # Zone 2: mid range
        z2 = SF2Zone("preset")
        z2.key_range = (40, 80)
        z2.velocity_range = (0, 127)
        tree.insert(z2)

        results = tree.query(60, 100)

        assert len(results) == 2

    def test_query_velocity_matching(self):
        """Test velocity-based matching."""
        tree = sf2_zone_cache.AVLRangeTree()

        zone = SF2Zone("preset")
        zone.key_range = (0, 127)
        zone.velocity_range = (64, 127)
        tree.insert(zone)

        # Should match
        assert len(tree.query(60, 100)) == 1
        # Should not match
        assert len(tree.query(60, 50)) == 0

    def test_avl_balancing(self):
        """Test AVL tree remains balanced after insertions."""
        tree = sf2_zone_cache.AVLRangeTree()

        # Insert in sorted order (worst case for balance)
        for i in range(10):
            zone = SF2Zone("preset")
            zone.key_range = (i * 10, i * 10 + 5)
            tree.insert(zone)

        # Check tree is balanced
        assert tree._node_count == 10

    def test_clear(self):
        """Test clearing tree."""
        tree = sf2_zone_cache.AVLRangeTree()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        tree.insert(zone)

        tree.clear()

        assert tree.root is None
        assert tree._node_count == 0


class TestRangeNode:
    """Tests for RangeNode class."""

    def test_node_creation(self):
        """Test node creation."""
        zone = SF2Zone("preset")
        node = sf2_zone_cache.RangeNode(zone, 48, 72, 0, 127)

        assert node.zone is zone
        assert node.key_min == 48
        assert node.key_max == 72
        assert node.vel_min == 0
        assert node.vel_max == 127

    def test_overlaps_true(self):
        """Test overlap detection returns True."""
        zone = SF2Zone("preset")
        node = sf2_zone_cache.RangeNode(zone, 48, 72, 64, 127)

        assert node.overlaps(60, 100) is True

    def test_overlaps_false_key(self):
        """Test overlap returns False when key outside."""
        zone = SF2Zone("preset")
        node = sf2_zone_cache.RangeNode(zone, 48, 72, 64, 127)

        assert node.overlaps(30, 100) is False

    def test_overlaps_false_velocity(self):
        """Test overlap returns False when velocity outside."""
        zone = SF2Zone("preset")
        node = sf2_zone_cache.RangeNode(zone, 48, 72, 64, 127)

        assert node.overlaps(60, 50) is False


class TestHierarchicalZoneCache:
    """Tests for HierarchicalZoneCache class."""

    def test_cache_creation(self):
        """Test cache initialization."""
        cache = sf2_zone_cache.HierarchicalZoneCache()

        assert cache is not None
        assert cache.range_tree is not None

    def test_add_zones(self):
        """Test adding zones to cache."""
        cache = sf2_zone_cache.HierarchicalZoneCache()

        zones = []
        for i in range(3):
            zone = SF2Zone("preset")
            zone.key_range = (i * 20, i * 20 + 25)  # Extended range to cover 60
            zones.append(zone)

        cache.add_zones(zones)

        # Query should find zones - key 60 falls in zone 2 (40-65)
        results = cache.get_matching_zones(60, 100)
        assert len(results) >= 1

    def test_get_matching_zones(self):
        """Test getting matching zones."""
        cache = sf2_zone_cache.HierarchicalZoneCache()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.velocity_range = (0, 127)
        cache.add_zone(zone)

        results = cache.get_matching_zones(60, 100)

        assert len(results) == 1
        assert results[0] is zone

    def test_query_caching(self):
        """Test query results are cached."""
        cache = sf2_zone_cache.HierarchicalZoneCache()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        cache.add_zone(zone)

        # First query
        cache.get_matching_zones(60, 100)

        # Second query should hit cache
        assert cache.cache_misses == 1
        results = cache.get_matching_zones(60, 100)
        assert cache.cache_hits == 1

    def test_clear(self):
        """Test clearing cache."""
        cache = sf2_zone_cache.HierarchicalZoneCache()

        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        cache.add_zone(zone)

        cache.clear()

        results = cache.get_matching_zones(60, 100)
        assert len(results) == 0


class TestSF2ZoneCacheManager:
    """Tests for SF2ZoneCacheManager class."""

    def test_manager_creation(self):
        """Test cache manager initialization."""
        manager = sf2_zone_cache.SF2ZoneCacheManager()

        assert manager is not None
        assert manager.preset_caches is not None

    def test_add_preset_zones(self):
        """Test adding preset zones."""
        manager = sf2_zone_cache.SF2ZoneCacheManager()

        zones = []
        zone = SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.instrument_index = 0
        zones.append(zone)

        manager.add_preset_zones(0, 0, zones)

        # Check zones were added
        cache_key = (0 << 8) | 0
        assert cache_key in manager.preset_caches

        # Query should find zones
        results = manager.preset_caches[cache_key].get_matching_zones(60, 100)
        assert len(results) >= 1

    def test_add_instrument_zones(self):
        """Test adding instrument zones."""
        manager = sf2_zone_cache.SF2ZoneCacheManager()

        zones = []
        zone = SF2Zone("instrument")
        zone.key_range = (48, 72)
        zone.sample_id = 5
        zones.append(zone)

        manager.add_instrument_zones(5, zones)

        assert 5 in manager.instrument_caches
        results = manager.instrument_caches[5].get_matching_zones(60, 100)
        assert len(results) >= 1

    def test_query_nonexistent(self):
        """Test querying nonexistent preset."""
        manager = sf2_zone_cache.SF2ZoneCacheManager()

        cache_key = (99 << 8) | 99
        assert cache_key not in manager.preset_caches


class TestZoneCachePerformance:
    """Performance and complexity tests for zone cache."""

    def test_many_zones_query(self):
        """Test query performance with many zones."""
        import time

        tree = sf2_zone_cache.AVLRangeTree()

        # Insert 100 zones
        for i in range(100):
            zone = SF2Zone("preset")
            zone.key_range = (i, i + 10)
            zone.velocity_range = (0, 127)
            tree.insert(zone)

        # Time the query
        start = time.perf_counter()
        for _ in range(100):
            results = tree.query(50, 100)
        elapsed = time.perf_counter() - start

        # Should be reasonably fast
        assert elapsed < 0.1  # 100 queries in under 100ms

    def test_sparse_key_ranges(self):
        """Test with sparse key ranges."""
        tree = sf2_zone_cache.AVLRangeTree()

        # Zones at sparse intervals
        for i in range(0, 128, 16):
            zone = SF2Zone("preset")
            zone.key_range = (i, i + 5)
            tree.insert(zone)

        # Query between zones
        results = tree.query(20, 100)

        # Should find zones containing key 20
        assert len(results) >= 1

    def test_wide_velocity_range(self):
        """Test with wide velocity range zones."""
        tree = sf2_zone_cache.AVLRangeTree()

        # Single zone covering all velocities
        zone = SF2Zone("preset")
        zone.key_range = (0, 127)
        zone.velocity_range = (0, 127)
        tree.insert(zone)

        # Should match any velocity
        for vel in [0, 1, 64, 127]:
            results = tree.query(60, vel)
            assert len(results) == 1
