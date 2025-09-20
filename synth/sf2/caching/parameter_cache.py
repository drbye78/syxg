from typing import Dict, Any

class ParameterCache:
    """Optimized cache for SF2 parameter merging operations"""
    
    def __init__(self):
        self._cache = {}
        self._hit_count = 0
        self._miss_count = 0
        
    def get_cached_params(self, preset_params: Dict, instrument_params: Dict) -> Dict:
        """Get cached merged parameters or compute and cache them"""
        cache_key = self._make_cache_key(preset_params, instrument_params)
        if cache_key in self._cache:
            self._hit_count += 1
            return self._cache[cache_key].copy()
            
        self._miss_count += 1
        merged = self._merge_params(preset_params, instrument_params)
        self._cache[cache_key] = merged.copy()
        return merged
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hit_count + self._miss_count
        return {
            'hits': self._hit_count,
            'misses': self._miss_count,
            'hit_rate': self._hit_count / total if total > 0 else 0,
            'cache_size': len(self._cache)
        }
        
    def _make_cache_key(self, preset_params: Dict, instrument_params: Dict):
        """Create a hashable cache key from parameters"""
        return (
            self._make_hashable(preset_params), 
            self._make_hashable(instrument_params)
        )
        
    def _make_hashable(self, obj):
        """Convert objects to hashable types"""
        if isinstance(obj, dict):
            return frozenset((k, self._make_hashable(v)) for k, v in obj.items())
        elif isinstance(obj, list):
            return tuple(self._make_hashable(item) for item in obj)
        return obj
        
    def _merge_params(self, preset: Dict, instrument: Dict) -> Dict:
        """Merge preset and instrument parameters"""
        merged = preset.copy()
        for key, value in instrument.items():
            if key not in merged:
                merged[key] = value
            elif key == 'modulators':
                merged[key] = self._merge_lists(merged.get(key), value)
            elif key == 'zones':
                merged[key] = self._merge_lists(merged.get(key), value)
            else:
                merged[key] = value
        return merged
        
    def _merge_lists(self, existing, new):
        """Merge two lists, handling None cases"""
        if existing is None:
            existing = []
        if not isinstance(existing, list):
            existing = [existing]
        if isinstance(new, list):
            existing.extend(new)
        else:
            existing.append(new)
        return existing