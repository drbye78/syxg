"""
Voice Factory - Refactored with preset-first approach.

Part of the unified region-based synthesis architecture.
VoiceFactory creates Voice objects with preset definitions.
Region instantiation happens at note-on time, not at Voice creation.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

from ..engine.synthesis_engine import SynthesisEngine
from ..engine.synthesis_engine import SynthesisEngineRegistry
from ..engine.preset_info import PresetInfo
from .voice import Voice

logger = logging.getLogger(__name__)


class VoiceFactory:
    """
    Refactored VoiceFactory with preset-first approach.
    
    Creates Voice with preset definition (not pre-loaded regions).
    Region instantiation happens at note-on time.
    
    This is the KEY factory that enables:
    - Fast program changes (no sample loading)
    - Lazy region creation (only when needed)
    - Multi-zone preset support (key/velocity splits)
    
    Attributes:
        engine_registry: Registry of available synthesis engines
        synth: Optional synthesizer reference for infrastructure access
    """
    
    __slots__ = ['engine_registry', 'synth', '_preset_cache']
    
    def __init__(
        self, 
        engine_registry: SynthesisEngineRegistry,
        synth: Optional[Any] = None
    ):
        """
        Initialize voice factory.
        
        Args:
            engine_registry: Registry of available synthesis engines
            synth: Optional ModernXGSynthesizer instance
        """
        self.engine_registry = engine_registry
        self.synth = synth
        
        # Optional cache of preset info for faster access
        self._preset_cache: Dict[Tuple[int, int], PresetInfo] = {}
    
    def create_voice(
        self, 
        bank: int, 
        program: int, 
        channel: int,
        sample_rate: int
    ) -> Optional[Voice]:
        """
        Create Voice for preset.
        
        Gets preset info with ALL region descriptors.
        Does NOT create region instances (lazy initialization).
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
            channel: MIDI channel number
            sample_rate: Audio sample rate
        
        Returns:
            Voice instance or None if preset not found
        """
        # Try engines in priority order
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if not engine:
                continue
            
            try:
                # Get preset info (lightweight, no samples loaded)
                preset_info = self._get_preset_info_cached(
                    engine, bank, program
                )
                
                if preset_info:
                    # Create voice with preset definition
                    return Voice(
                        preset_info=preset_info,
                        engine=engine,
                        channel=channel,
                        sample_rate=sample_rate
                    )
                    
            except Exception as e:
                logger.warning(
                    f"Engine {engine_type} failed to create voice for "
                    f"program {program}/bank {bank}: {e}"
                )
                # Try next engine
        
        logger.warning(
            f"No engine can handle program {program} in bank {bank}"
        )
        return None
    
    def _get_preset_info_cached(
        self, 
        engine: SynthesisEngine, 
        bank: int, 
        program: int
    ) -> Optional[PresetInfo]:
        """
        Get preset info with caching.
        
        Args:
            engine: Synthesis engine
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            PresetInfo or None
        """
        cache_key = (bank, program, engine.get_engine_type())
        
        if cache_key in self._preset_cache:
            return self._preset_cache[cache_key]
        
        try:
            preset_info = engine.get_preset_info(bank, program)
            if preset_info:
                self._preset_cache[cache_key] = preset_info
            return preset_info
        except Exception as e:
            logger.error(f"Failed to get preset info: {e}")
            return None
    
    def get_preset_info(
        self, 
        bank: int, 
        program: int
    ) -> Optional[PresetInfo]:
        """
        Get preset info without creating voice.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            PresetInfo or None if not found
        """
        # Check cache first
        for engine_type in self.engine_registry.get_priority_order():
            cache_key = (bank, program, engine_type)
            if cache_key in self._preset_cache:
                return self._preset_cache[cache_key]
        
        # Try engines in priority order
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if not engine:
                continue
            
            try:
                preset_info = engine.get_preset_info(bank, program)
                if preset_info:
                    cache_key = (bank, program, engine_type)
                    self._preset_cache[cache_key] = preset_info
                    return preset_info
            except Exception:
                continue
        
        return None
    
    def get_available_programs(self) -> List[Tuple[int, int, str, str]]:
        """
        Get all available programs across all engines.
        
        Returns:
            List of (bank, program, name, engine_type) tuples
        """
        programs = []
        
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if not engine:
                continue
            
            # Try engine-specific method
            if hasattr(engine, 'get_available_programs'):
                try:
                    engine_programs = engine.get_available_programs()
                    programs.extend(engine_programs)
                except Exception as e:
                    logger.warning(
                        f"Engine {engine_type} failed to get programs: {e}"
                    )
        
        return programs
    
    def get_program_info(
        self, 
        bank: int, 
        program: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about a program.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            Dictionary with program information or None
        """
        preset_info = self.get_preset_info(bank, program)
        if not preset_info:
            return None
        
        return {
            'bank': bank,
            'program': program,
            'name': preset_info.name,
            'engine_type': preset_info.engine_type,
            'region_count': preset_info.get_region_count(),
            'has_key_splits': preset_info.has_key_splits(),
            'has_velocity_splits': preset_info.has_velocity_splits(),
            'key_range': preset_info.get_key_range(),
            'velocity_range': preset_info.get_velocity_range()
        }
    
    def preload_preset(
        self, 
        bank: int, 
        program: int
    ) -> bool:
        """
        Preload preset info into cache.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            True if preset was loaded successfully
        """
        preset_info = self.get_preset_info(bank, program)
        return preset_info is not None
    
    def clear_cache(self) -> None:
        """Clear preset info cache."""
        self._preset_cache.clear()
    
    def get_engine_for_program(
        self, 
        bank: int, 
        program: int
    ) -> Optional[str]:
        """
        Get the engine type that handles a program.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            Engine type string or None
        """
        preset_info = self.get_preset_info(bank, program)
        if preset_info:
            return preset_info.engine_type
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get voice factory statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'cached_presets': len(self._preset_cache),
            'available_engines': len(self.engine_registry.get_priority_order())
        }
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"VoiceFactory(cached_presets={len(self._preset_cache)}, "
            f"engines={len(self.engine_registry.get_priority_order())})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()


# Convenience function for creating voice factory
def create_voice_factory(
    engine_registry: SynthesisEngineRegistry,
    synth: Optional[Any] = None
) -> VoiceFactory:
    """
    Create and configure a voice factory.
    
    Args:
        engine_registry: Synthesis engine registry
        synth: Optional synthesizer reference
    
    Returns:
        Configured VoiceFactory instance
    """
    return VoiceFactory(engine_registry, synth)
