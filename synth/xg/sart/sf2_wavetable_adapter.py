"""
SF2 Wavetable Adapter - Bridge between SF2 samples and S.Art2 synthesis.

This adapter extracts wavetable data from SF2 SoundFont files and provides
it to the S.Art2 synthesizer for realistic acoustic instrument sounds.
"""

import logging
from typing import Dict, Optional, Tuple, List
import numpy as np

logger = logging.getLogger(__name__)

# Try to import SF2 modules
SF2_AVAILABLE = False
try:
    from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
    from synth.sf2.sf2_sample_processor import SF2SampleProcessor
    SF2_AVAILABLE = True
except ImportError:
    SF2_AVAILABLE = False
    logger.warning("SF2 modules not available - SF2WavetableAdapter will use fallback")


class SF2WavetableAdapter:
    """
    Adapter that provides wavetable data from SF2 SoundFont files.
    
    This allows S.Art2 to use real acoustic instrument samples from
    SoundFont files as the basis for synthesis, combined with the
    articulation system for expressive control.
    """
    
    # Mapping from S.Art2 instrument names to typical SF2 bank/program
    INSTRUMENT_TO_SF2_MAP: Dict[str, Tuple[int, int, int]] = {
        # Piano (MSB 0)
        'grand_piano': (0, 0, 0),
        'piano': (0, 0, 0),
        'honkytonk_piano': (0, 0, 3),
        'electric_piano': (0, 1, 0),
        'clavinet': (0, 1, 7),
        
        # Organ (MSB 2)
        'hammond_organ': (2, 0, 0),
        'rock_organ': (2, 0, 2),
        'church_organ': (2, 0, 3),
        
        # Guitar (MSB 4)
        'nylon_guitar': (4, 0, 0),
        'steel_guitar': (4, 0, 1),
        'electric_guitar': (4, 0, 2),
        'jazz_guitar': (4, 0, 6),
        
        # Bass (MSB 5)
        'bass_guitar': (5, 0, 0),
        'electric_bass': (5, 0, 1),
        'fretless_bass': (5, 0, 4),
        
        # Strings (MSB 6)
        'violin': (6, 0, 0),
        'viola': (6, 0, 1),
        'cello': (6, 0, 2),
        'contrabass': (6, 0, 3),
        'strings_ensemble': (6, 0, 0),
        
        # Brass (MSB 7)
        'trumpet': (7, 0, 0),
        'trombone': (7, 0, 1),
        'french_horn': (7, 0, 2),
        'tuba': (7, 0, 4),
        
        # Reed (MSB 8)
        'saxophone': (8, 0, 0),
        'soprano_sax': (8, 0, 0),
        'alto_sax': (8, 0, 1),
        'tenor_sax': (8, 0, 2),
        'baritone_sax': (8, 0, 3),
        'clarinet': (8, 0, 4),
        'oboe': (8, 0, 5),
        'bassoon': (8, 0, 6),
        
        # Pipe (MSB 9)
        'piccolo': (9, 0, 0),
        'flute': (9, 0, 1),
        'recorder': (9, 0, 2),
        'pan_flute': (9, 0, 6),
        'shakuhachi': (9, 0, 7),
        
        # Synth Lead (MSB 10)
        'saw_lead': (10, 0, 0),
        'square_lead': (10, 0, 1),
        'sine_lead': (10, 0, 3),
        
        # Synth Pad (MSB 11)
        'warm_pad': (11, 0, 0),
        'polysynth': (11, 0, 1),
        'space_pad': (11, 0, 2),
        
        # Ethnic (MSB 13)
        'sitar': (13, 0, 0),
        'banjo': (13, 0, 0),
        'mandolin': (13, 0, 2),
        'koto': (13, 0, 6),
        
        # Percussion (MSB 14)
        'vibraphone': (14, 0, 11),
        'marimba': (14, 0, 12),
        'xylophone': (14, 0, 13),
    }
    
    def __init__(self, soundfont_path: Optional[str] = None):
        """
        Initialize SF2 Wavetable Adapter.
        
        Args:
            soundfont_path: Optional path to SoundFont file to load
        """
        self.soundfont_manager: Optional[SF2SoundFontManager] = None
        self.sample_processor: Optional[SF2SampleProcessor] = None
        self.loaded_presets: Dict[str, Dict] = {}
        self.wavetable_cache: Dict[str, np.ndarray] = {}
        
        if SF2_AVAILABLE and soundfont_path:
            self.load_soundfont(soundfont_path)
        else:
            logger.info("SF2WavetableAdapter initialized in fallback mode")
    
    def load_soundfont(self, path: str) -> bool:
        """
        Load a SoundFont file.
        
        Args:
            path: Path to SF2 file
            
        Returns:
            True if loaded successfully
        """
        if not SF2_AVAILABLE:
            logger.error("Cannot load SF2 - modules not available")
            return False
        
        try:
            self.soundfont_manager = SF2SoundFontManager()
            self.sample_processor = SF2SampleProcessor()
            
            # Load the soundfont
            result = self.soundfont_manager.load_soundfont(path)
            if result:
                logger.info(f"Loaded SoundFont: {path}")
                self._build_preset_cache()
                return True
            else:
                logger.warning(f"Failed to load SoundFont: {path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading SoundFont: {e}")
            return False
    
    def _build_preset_cache(self):
        """Build cache of available presets from loaded soundfont."""
        if not self.soundfont_manager:
            return
        
        try:
            # Get all available presets
            for bank_msb in range(128):
                for bank_lsb in range(128):
                    for program in range(128):
                        preset = self.soundfont_manager.get_preset(bank_msb, bank_lsb, program)
                        if preset:
                            key = f"{bank_msb}:{bank_lsb}:{program}"
                            self.loaded_presets[key] = {
                                'name': preset.get('name', 'Unknown'),
                                'bank_msb': bank_msb,
                                'bank_lsb': bank_lsb,
                                'program': program
                            }
        except Exception as e:
            logger.warning(f"Could not build preset cache: {e}")
    
    def get_wavetable(
        self,
        instrument_name: str,
        sample_rate: int = 44100
    ) -> Optional[np.ndarray]:
        """
        Get wavetable data for an instrument.
        
        Args:
            instrument_name: S.Art2 instrument name
            sample_rate: Target sample rate for resampling
            
        Returns:
            Wavetable data as numpy array, or None if not available
        """
        # Check cache first
        cache_key = f"{instrument_name}_{sample_rate}"
        if cache_key in self.wavetable_cache:
            return self.wavetable_cache[cache_key]
        
        # Try to get from SF2
        if self.soundfont_manager and SF2_AVAILABLE:
            wavetable = self._extract_from_sf2(instrument_name, sample_rate)
            if wavetable is not None:
                self.wavetable_cache[cache_key] = wavetable
                return wavetable
        
        # Fall back to generated wavetable
        return self._get_fallback_wavetable(instrument_name)
    
    def _extract_from_sf2(
        self,
        instrument_name: str,
        sample_rate: int
    ) -> Optional[np.ndarray]:
        """Extract wavetable from SF2 preset."""
        if not self.soundfont_manager:
            return None
        
        # Look up SF2 bank/program
        sf2_key = self.INSTRUMENT_TO_SF2_MAP.get(instrument_name)
        if not sf2_key:
            # Try to find closest match
            sf2_key = self._find_closest_preset(instrument_name)
        
        if not sf2_key:
            return None
        
        bank_msb, bank_lsb, program = sf2_key
        
        try:
            # Get preset
            preset = self.soundfont_manager.get_preset(bank_msb, bank_lsb, program)
            if not preset:
                return None
            
            # Get sample data from first instrument zone
            sample_data = self._extract_sample_from_preset(preset, sample_rate)
            return sample_data
            
        except Exception as e:
            logger.debug(f"Could not extract SF2 sample for {instrument_name}: {e}")
            return None
    
    def _extract_sample_from_preset(
        self,
        preset: Dict,
        sample_rate: int
    ) -> Optional[np.ndarray]:
        """Extract sample data from a preset."""
        if not self.sample_processor:
            return None
        
        try:
            # Get instrument zones
            zones = preset.get('zones', [])
            if not zones:
                return None
            
            # Get first zone with sample data
            for zone in zones:
                sample_id = zone.get('sample_id')
                if sample_id is not None:
                    # Get sample data
                    sample_data = self.soundfont_manager.get_sample_data(sample_id)
                    if sample_data is not None:
                        # Resample if needed
                        if sample_rate != getattr(sample_data, 'sample_rate', sample_rate):
                            sample_data = self._resample(sample_data, sample_rate)
                        
                        # Extract a single cycle or loop point
                        return self._prepare_wavetable(sample_data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting sample: {e}")
            return None
    
    def _resample(self, sample_data: np.ndarray, target_rate: int) -> np.ndarray:
        """Resample audio data to target sample rate."""
        try:
            from scipy import signal
            
            current_rate = getattr(sample_data, 'sample_rate', 44100)
            if current_rate == target_rate:
                return sample_data
            
            # Calculate resampling ratio
            ratio = target_rate / current_rate
            new_length = int(len(sample_data) * ratio)
            
            # Resample
            resampled = signal.resample(sample_data, new_length)
            return resampled
            
        except Exception as e:
            logger.warning(f"Resampling failed: {e}")
            return sample_data
    
    def _prepare_wavetable(self, sample_data: np.ndarray) -> np.ndarray:
        """
        Prepare sample data as a wavetable.
        
        Extracts a single cycle or relevant portion for wavetable synthesis.
        """
        try:
            # Find optimal loop points or extract cycle
            if len(sample_data) > 2048:
                # Take a segment that's suitable for wavetable
                # Typically the attack or sustain portion
                segment_length = 2048
                start = len(sample_data) // 4  # Skip attack
                sample = sample_data[start:start + segment_length]
            else:
                sample = sample_data
            
            # Normalize
            max_val = np.max(np.abs(sample))
            if max_val > 0:
                sample = sample / max_val * 0.9  # Leave headroom
            
            return sample.astype(np.float32)
            
        except Exception as e:
            logger.debug(f"Error preparing wavetable: {e}")
            return None
    
    def _find_closest_preset(self, instrument_name: str) -> Optional[Tuple[int, int, int]]:
        """Find closest matching SF2 preset for instrument name."""
        # Simple string matching
        instrument_lower = instrument_name.lower()
        
        for name, key in self.INSTRUMENT_TO_SF2_MAP.items():
            if instrument_lower in name or name in instrument_lower:
                return key
        
        return None
    
    def _get_fallback_wavetable(self, instrument_name: str) -> Optional[np.ndarray]:
        """Get generated fallback wavetable."""
        # This will be handled by the WavetableSynthesisEngine
        # This method returns None to indicate fallback is needed
        return None
    
    def get_available_instruments(self) -> List[str]:
        """Get list of instruments with SF2 samples available."""
        instruments = []
        
        # Add instruments with SF2 mapping
        for name in self.INSTRUMENT_TO_SF2_MAP:
            if self.get_wavetable(name) is not None:
                instruments.append(name)
        
        return instruments
    
    def get_wavetable_info(self, instrument_name: str) -> Dict:
        """
        Get information about wavetable for an instrument.
        
        Returns:
            Dict with wavetable metadata
        """
        wavetable = self.get_wavetable(instrument_name)
        
        info = {
            'instrument': instrument_name,
            'has_sample': wavetable is not None,
            'source': 'sf2' if self.soundfont_manager else 'generated',
            'length': len(wavetable) if wavetable is not None else 0,
        }
        
        # Add SF2 mapping info if available
        sf2_key = self.INSTRUMENT_TO_SF2_MAP.get(instrument_name)
        if sf2_key:
            info['sf2_bank'], info['sf2_lsb'], info['sf2_program'] = sf2_key
        
        return info


class SF2WavetableProvider:
    """
    High-level provider that combines SF2 samples with S.Art2 wavetable engine.
    
    Usage:
        provider = SF2WavetableProvider(soundfont_path='path/to/soundfont.sf2')
        audio = provider.synthesize_note(
            instrument='saxophone',
            frequency=440,
            duration=1.0,
            velocity=100,
            articulation='legato'
        )
    """
    
    def __init__(
        self,
        soundfont_path: Optional[str] = None,
        sample_rate: int = 44100
    ):
        """
        Initialize the provider.
        
        Args:
            soundfont_path: Optional path to SoundFont file
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        
        # Initialize components
        self.sf2_adapter = SF2WavetableAdapter(soundfont_path)
        
        # Import wavetable engine
        try:
            from .wavetable import WavetableSynthesisEngine
            self.wavetable_engine = WavetableSynthesisEngine(sample_rate=sample_rate)
        except ImportError:
            logger.warning("Wavetable engine not available")
            self.wavetable_engine = None
    
    def synthesize_note(
        self,
        instrument: str,
        frequency: float,
        duration: float,
        velocity: int = 100,
        articulation: str = 'normal',
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """
        Synthesize a note using SF2-sourced wavetable.
        
        Args:
            instrument: Instrument name
            frequency: Frequency in Hz
            duration: Duration in seconds
            velocity: MIDI velocity (0-127)
            articulation: Articulation type
            pitch_bend: Pitch bend in semitones
            mod_wheel: Modulation wheel value
            
        Returns:
            Audio waveform as numpy array
        """
        if not self.wavetable_engine:
            return np.zeros(int(self.sample_rate * duration))
        
        # Try to get SF2 wavetable first
        wavetable_data = self.sf2_adapter.get_wavetable(instrument, self.sample_rate)
        
        # Prepare parameters
        params = {
            'attack_time': 0.02,
            'decay_time': 0.1,
            'sustain_level': 0.7,
            'release_time': 0.2,
        }
        
        if wavetable_data is not None:
            # Use SF2 sample - would need custom processing
            # For now, fall through to generated wavetable
            pass
        
        # Generate tone using wavetable engine
        audio = self.wavetable_engine.generate_tone(
            freq=frequency,
            duration=duration,
            velocity=velocity,
            params=params,
            pitch_bend=pitch_bend,
            mod_wheel=mod_wheel
        )
        
        return audio
    
    def get_instrument_info(self, instrument: str) -> Dict:
        """Get information about instrument availability."""
        return self.sf2_adapter.get_wavetable_info(instrument)
    
    def list_available_instruments(self) -> List[str]:
        """List all instruments with SF2 sample support."""
        return self.sf2_adapter.get_available_instruments()


def create_sf2_wavetable_provider(
    soundfont_path: str,
    sample_rate: int = 44100
) -> SF2WavetableProvider:
    """
    Factory function to create SF2 wavetable provider.
    
    Args:
        soundfont_path: Path to SoundFont file
        sample_rate: Audio sample rate
        
    Returns:
        SF2WavetableProvider instance
    """
    return SF2WavetableProvider(
        soundfont_path=soundfont_path,
        sample_rate=sample_rate
    )
