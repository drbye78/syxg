"""
Voice factory for XG synthesizer.

Provides factory pattern for creating Voice instances using appropriate synthesis engines.
"""

from typing import Optional, TYPE_CHECKING
from .voice import Voice
from ..engine.synthesis_engine import SynthesisEngineRegistry

if TYPE_CHECKING:
    from ..voice.voice_manager import VoiceManager
    from ..engine.modern_xg_synthesizer import ModernXGSynthesizer


class VoiceFactory:
    """
    Factory for creating Voice instances with global voice management integration.

    Uses synthesis engine registry to determine appropriate engine for each voice
    and creates Voice objects with proper synthesis engine integration and
    unified voice allocation, stealing, and polyphony management.
    """

    def __init__(self, engine_registry: SynthesisEngineRegistry,
                 voice_manager: Optional['VoiceManager'] = None,
                 synth: Optional['ModernXGSynthesizer'] = None):
        """
        Initialize voice factory with global integration.

        Args:
            engine_registry: Registry of available synthesis engines
            voice_manager: Global voice manager for allocation coordination
            synth: ModernXGSynthesizer instance for infrastructure access
        """
        self.engine_registry = engine_registry
        self.voice_manager = voice_manager
        self.synth = synth

    def create_voice(self, bank: int, program: int, channel: int, sample_rate: int) -> Voice:
        """
        Create a voice for the specified program/bank combination.

        Args:
            bank: MIDI bank number (0-16383)
            program: MIDI program number (0-127)
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz

        Returns:
            Voice instance configured for the program/bank

        Raises:
            RuntimeError: If no synthesis engines are registered
        """
        # Try engines in priority order to find one that can handle this program/bank
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if engine:
                try:
                    # Get voice parameters from the engine
                    voice_params = engine.get_voice_parameters(program, bank)
                    if voice_params:
                        # Create voice instance
                        voice = Voice(engine, voice_params, channel, sample_rate)
                        return voice
                except Exception:
                    # Engine can't handle this program/bank, try next engine
                    continue

        # Fallback: use default engine (SF2) with default parameters
        sf2_engine = self.engine_registry.get_engine('sf2')
        if sf2_engine:
            voice_params = sf2_engine.get_voice_parameters(program, bank) or sf2_engine.get_default_partial_params()
            voice = Voice(sf2_engine, voice_params, channel, sample_rate)
            return voice

        raise RuntimeError("No synthesis engines available for voice creation")

    def create_voice_with_engine(self, engine_type: str, voice_params: dict,
                                channel: int, sample_rate: int) -> Voice:
        """
        Create a voice with a specific synthesis engine.

        Args:
            engine_type: Type of synthesis engine to use
            voice_params: Voice parameter dictionary
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz

        Returns:
            Voice instance using the specified engine

        Raises:
            KeyError: If engine type is not registered
        """
        engine = self.engine_registry.get_engine(engine_type)
        voice = Voice(engine, voice_params, channel, sample_rate)
        return voice

    def get_available_engines_for_program(self, bank: int, program: int) -> list:
        """
        Get list of engine types that can handle a program/bank combination.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            List of engine type strings that support this program/bank
        """
        available_engines = []

        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if engine:
                try:
                    # Try to get voice parameters - if successful, engine supports it
                    params = engine.get_voice_parameters(program, bank)
                    if params is not None:
                        available_engines.append(engine_type)
                except Exception:
                    # Engine doesn't support this program/bank, try next engine
                    continue

        return available_engines

    def preload_voice(self, bank: int, program: int, channel: int, sample_rate: int) -> Voice:
        """
        Preload a voice for faster access.

        Args:
            bank: MIDI bank number
            program: MIDI program number
            channel: MIDI channel number
            sample_rate: Audio sample rate

        Returns:
            Preloaded Voice instance
        """
        voice = self.create_voice(bank, program, channel, sample_rate)

        # Preload any engine-specific resources (if available)
        # Engines may implement preloading in future versions

        return voice

    def get_voice_info(self, bank: int, program: int) -> Optional[dict]:
        """
        Get information about a voice without creating it.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            Voice information dictionary or None if not available
        """
        # Try each engine in priority order
        for engine_type in self.engine_registry.get_priority_order():
            engine = self.engine_registry.get_engine(engine_type)
            if engine:
                try:
                    voice_params = engine.get_voice_parameters(program, bank)
                    if voice_params:
                        return {
                            'bank': bank,
                            'program': program,
                            'name': voice_params.get('name', f'Program {program}'),
                            'engine_type': engine.get_engine_type(),
                            'key_range': (voice_params.get('key_range_low', 0),
                                        voice_params.get('key_range_high', 127)),
                            'num_partials': len(voice_params.get('partials', []))
                        }
                except Exception:
                    continue

        return None

    def create_sf2_voice(self, partial_params: dict, channel: int) -> Optional[Voice]:
        """
        Create an SF2 voice with global voice management integration.

        This method creates SF2 voices that participate in the unified voice
        allocation system instead of using isolated SF2 voice management.

        Args:
            partial_params: SF2 partial parameters from zone processing
            channel: MIDI channel number (0-15)

        Returns:
            SF2 Voice instance with global voice management, or None if allocation fails
        """
        if not self.synth or not self.voice_manager:
            # Fallback to regular voice creation if no global integration
            sf2_engine = self.engine_registry.get_engine('sf2')
            if sf2_engine:
                voice_params = {'name': 'SF2 Voice', 'partials': [partial_params]}
                return Voice(sf2_engine, voice_params, channel, sf2_engine.sample_rate)
            return None

        # Create SF2 voice with global voice management
        try:
            # Use SF2 manager's voice creation method
            sf2_manager = getattr(self.synth, 'sf2_manager', None)
            if sf2_manager and hasattr(sf2_manager, 'create_sf2_voice'):
                voice = sf2_manager.create_sf2_voice(partial_params, self.voice_manager, self.synth)
                return voice
        except Exception as e:
            print(f"Failed to create SF2 voice with global management: {e}")

        # Fallback to regular voice creation
        sf2_engine = self.engine_registry.get_engine('sf2')
        if sf2_engine:
            voice_params = {'name': 'SF2 Voice', 'partials': [partial_params]}
            return Voice(sf2_engine, voice_params, channel, sf2_engine.sample_rate)

        return None
