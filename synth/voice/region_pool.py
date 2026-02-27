"""
Region Pool - Object pooling for region instances.

Part of the unified region-based synthesis architecture.
RegionPool reduces allocation overhead by reusing region objects
instead of creating new instances for every note-on event.
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
from dataclasses import dataclass, field
import threading
import logging

from ..engine.region_descriptor import RegionDescriptor

# Forward reference to avoid circular import
if __name__ == '__annotations__':
    from ..partial.region import IRegion

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PoolStats:
    """Statistics for a region pool."""
    region_type: str
    pooled_count: int = 0
    created_count: int = 0
    reused_count: int = 0
    max_pooled: int = 0
    
    @property
    def reuse_ratio(self) -> float:
        """Calculate reuse ratio (0.0 to 1.0)."""
        total = self.created_count + self.reused_count
        return self.reused_count / total if total > 0 else 0.0


class RegionPool:
    """
    Object pool for region instances.
    
    Reduces allocation overhead by reusing region objects.
    Maintains separate pools per region type (SF2, FM, Additive, etc.).
    
    Attributes:
        max_pooled_per_type: Maximum regions to pool per type
    """
    
    def __init__(self, max_pooled_per_type: int = 64):
        """
        Initialize region pool.
        
        Args:
            max_pooled_per_type: Maximum number of regions to keep pooled per type
        """
        self.max_pooled_per_type = max_pooled_per_type
        
        # Pool per region type: type_name -> [regions]
        self._pools: dict[str, list[Any]] = {}
        
        # Statistics per type
        self._stats: dict[str, PoolStats] = {}
        
        # Lock for thread safety
        self._lock = threading.RLock()
    
    def acquire(
        self, 
        region_type: str,
        factory: Callable[[], Any],
        descriptor: RegionDescriptor | None = None
    ) -> Any:
        """
        Acquire region from pool or create new.
        
        Args:
            region_type: Type identifier (e.g., 'sf2', 'fm', 'additive')
            factory: Factory function to create new region
            descriptor: Optional descriptor to initialize region with
        
        Returns:
            Region instance (ready to use)
        """
        with self._lock:
            if region_type not in self._pools:
                self._pools[region_type] = []
                self._stats[region_type] = PoolStats(region_type=region_type)
            
            pool = self._pools[region_type]
            stats = self._stats[region_type]
            
            if pool:
                # Reuse from pool
                region = pool.pop()
                stats.reused_count += 1
                
                # Reset region state if it has a reset method
                if hasattr(region, 'reset'):
                    region.reset()
                
                # Update descriptor if provided
                if descriptor is not None and hasattr(region, 'descriptor'):
                    region.descriptor = descriptor
                
                return region
            else:
                # Create new
                region = factory()
                stats.created_count += 1
                stats.max_pooled = max(stats.max_pooled, 1)
                return region
    
    def release(self, region: Any) -> None:
        """
        Release region back to pool.
        
        Args:
            region: Region to release
        """
        if region is None:
            return
        
        # Get region type from descriptor
        if not hasattr(region, 'descriptor'):
            # Cannot pool region without descriptor
            return
        
        region_type = region.descriptor.engine_type
        
        with self._lock:
            if region_type not in self._pools:
                self._pools[region_type] = []
                self._stats[region_type] = PoolStats(region_type=region_type)
            
            pool = self._pools[region_type]
            stats = self._stats[region_type]
            
            if len(pool) < self.max_pooled_per_type:
                # Reset and pool
                if hasattr(region, 'reset'):
                    region.reset()
                pool.append(region)
                stats.pooled_count = len(pool)
            # else: let it be garbage collected
    
    def release_all(self, regions: list[Any]) -> None:
        """
        Release multiple regions back to pool.
        
        Args:
            regions: List of regions to release
        """
        for region in regions:
            self.release(region)
    
    def clear(self) -> None:
        """Clear all pooled regions."""
        with self._lock:
            for pool in self._pools.values():
                for region in pool:
                    if hasattr(region, 'dispose'):
                        try:
                            region.dispose()
                        except Exception as e:
                            logger.warning(f"Error disposing region: {e}")
            
            self._pools.clear()
            self._stats.clear()
    
    def get_stats(self) -> dict[str, PoolStats]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary of statistics per region type
        """
        with self._lock:
            return self._stats.copy()
    
    def get_total_stats(self) -> dict[str, Any]:
        """
        Get aggregated statistics across all region types.
        
        Returns:
            Dictionary with total statistics
        """
        with self._lock:
            total_created = sum(s.created_count for s in self._stats.values())
            total_reused = sum(s.reused_count for s in self._stats.values())
            total_pooled = sum(s.pooled_count for s in self._stats.values())
            
            total = total_created + total_reused
            reuse_ratio = total_reused / total if total > 0 else 0.0
            
            return {
                'total_pooled': total_pooled,
                'total_created': total_created,
                'total_reused': total_reused,
                'reuse_ratio': reuse_ratio,
                'types': len(self._stats)
            }
    
    def trim_pool(self, region_type: str, max_size: int) -> int:
        """
        Trim a specific pool to a maximum size.
        
        Args:
            region_type: Type of region to trim
            max_size: Maximum pool size
        
        Returns:
            Number of regions removed
        """
        with self._lock:
            if region_type not in self._pools:
                return 0
            
            pool = self._pools[region_type]
            removed = 0
            
            while len(pool) > max_size:
                region = pool.pop()
                if hasattr(region, 'dispose'):
                    try:
                        region.dispose()
                    except Exception:
                        pass
                removed += 1
            
            if region_type in self._stats:
                self._stats[region_type].pooled_count = len(pool)
            
            return removed
    
    def trim_all(self, max_size: int) -> int:
        """
        Trim all pools to a maximum size.
        
        Args:
            max_size: Maximum pool size per type
        
        Returns:
            Total number of regions removed
        """
        total_removed = 0
        with self._lock:
            for region_type in list(self._pools.keys()):
                total_removed += self.trim_pool(region_type, max_size)
        return total_removed
    
    def get_pooled_count(self, region_type: str) -> int:
        """
        Get number of pooled regions for a type.
        
        Args:
            region_type: Type identifier
        
        Returns:
            Number of pooled regions
        """
        with self._lock:
            if region_type not in self._pools:
                return 0
            return len(self._pools[region_type])
    
    def get_total_pooled(self) -> int:
        """
        Get total number of pooled regions.
        
        Returns:
            Total pooled regions across all types
        """
        with self._lock:
            return sum(len(pool) for pool in self._pools.values())
    
    def __len__(self) -> int:
        """Get total number of pooled regions."""
        return self.get_total_pooled()
    
    def __str__(self) -> str:
        """String representation."""
        stats = self.get_total_stats()
        return (
            f"RegionPool(pooled={stats['total_pooled']}, "
            f"created={stats['total_created']}, "
            f"reused={stats['total_reused']}, "
            f"reuse_ratio={stats['reuse_ratio']:.1%})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()


# Global region pool instance (lazy initialized)
_global_pool: RegionPool | None = None
_global_pool_lock = threading.Lock()


def get_global_region_pool(max_pooled_per_type: int = 64) -> RegionPool:
    """
    Get or create global region pool instance.
    
    Args:
        max_pooled_per_type: Maximum regions to pool per type
    
    Returns:
        Global RegionPool instance
    """
    global _global_pool
    
    if _global_pool is None:
        with _global_pool_lock:
            if _global_pool is None:
                _global_pool = RegionPool(max_pooled_per_type)
    
    return _global_pool


def reset_global_region_pool() -> None:
    """Reset global region pool (for testing)."""
    global _global_pool
    with _global_pool_lock:
        if _global_pool is not None:
            _global_pool.clear()
            _global_pool = None
