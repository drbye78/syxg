"""
Articulation Controller - NRPN/SYSEX Handler for S.Art2-style articulations.

This module provides the bridge between MIDI NRPN/SYSEX messages and
articulation control for SF2 sample playback.
"""

import logging
from typing import Dict, Tuple, Optional, Any, Callable
import numpy as np

logger = logging.getLogger(__name__)


class ArticulationController:
    """
    Controller that maps NRPN/SYSEX messages to S.Art2-style articulations.
    
    Provides articulation control for sample-based synthesis (SF2) by converting
    MIDI control messages into articulation parameters.
    
    Usage:
        controller = ArticulationController()
        controller.process_nrpn(1, 0)  # Sets 'normal'
        controller.process_nrpn(1, 1)  # Sets 'legato'
    """
    
    # NRPN MSB=1 for common articulations
    NRPN_ARTICULATION_MAP: Dict[Tuple[int, int], str] = {
        # Common articulations (MSB 1)
        (1, 0): 'normal',
        (1, 1): 'legato',
        (1, 2): 'staccato',
        (1, 3): 'bend',
        (1, 4): 'vibrato',
        (1, 5): 'breath',
        (1, 6): 'glissando',
        (1, 7): 'growl',
        (1, 8): 'flutter',
        (1, 9): 'trill',
        (1, 10): 'pizzicato',
        (1, 11): 'grace',
        (1, 12): 'shake',
        (1, 13): 'fall',
        (1, 14): 'doit',
        (1, 15): 'tongue_slap',
        (1, 16): 'harmonics',
        (1, 17): 'hammer_on',
        (1, 18): 'pull_off',
        (1, 19): 'key_off',
        (1, 20): 'marcato',
        (1, 21): 'detache',
        (1, 22): 'sul_ponticello',
        (1, 23): 'scoop',
        (1, 24): 'rip',
        (1, 25): 'portamento',
        (1, 26): 'swell',
        (1, 27): 'accented',
        (1, 28): 'bow_up',
        (1, 29): 'bow_down',
        (1, 30): 'col_legno',
        (1, 31): 'up_bend',
        (1, 32): 'down_bend',
        (1, 33): 'smear',
        (1, 34): 'flip',
        (1, 35): 'straight',
        
        # Dynamics (MSB 2)
        (2, 0): 'ppp',
        (2, 1): 'pp',
        (2, 2): 'p',
        (2, 3): 'mp',
        (2, 4): 'mf',
        (2, 5): 'f',
        (2, 6): 'ff',
        (2, 7): 'fff',
        (2, 8): 'crescendo',
        (2, 9): 'diminuendo',
        (2, 10): 'sfz',
        (2, 11): 'rfz',
        
        # Wind techniques (MSB 3)
        (3, 0): 'growl_wind',
        (3, 1): 'flutter_wind',
        (3, 2): 'tongue_slap_wind',
        (3, 3): 'smear_wind',
        (3, 4): 'flip_wind',
        (3, 5): 'scoop_wind',
        (3, 6): 'rip_wind',
        (3, 7): 'double_tongue',
        (3, 8): 'triple_tongue',
        
        # String techniques (MSB 4)
        (4, 0): 'pizzicato_strings',
        (4, 1): 'harmonics_strings',
        (4, 2): 'sul_ponticello_strings',
        (4, 3): 'bow_up_strings',
        (4, 4): 'bow_down_strings',
        (4, 5): 'col_legno_strings',
        (4, 6): 'portamento_strings',
        (4, 7): 'spiccato',
        (4, 8): 'tremolando',
        
        # Guitar techniques (MSB 5)
        (5, 0): 'hammer_on_guitar',
        (5, 1): 'pull_off_guitar',
        (5, 2): 'harmonics_guitar',
        (5, 3): 'palm_mute',
        (5, 4): 'tap',
        (5, 5): 'slide_up',
        (5, 6): 'slide_down',
        (5, 7): 'bend',
        
        # Brass techniques (MSB 6)
        (6, 0): 'muted_brass',
        (6, 1): 'cup_mute',
        (6, 2): 'harmon_mute',
        (6, 3): 'stopped',
        (6, 4): 'scoop_brass',
        (6, 5): 'lip_trill',
    }
    
    # Yamaha S.Art2 SYSEX manufacturer ID
    YAMAHA_SYSEX_ID = 0x43
    
    def __init__(self):
        """Initialize the articulation controller."""
        self.current_articulation = 'normal'
        self.current_category = 'common'
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        
        # Articulation parameters that can be controlled
        self.articulation_params: Dict[str, Any] = {
            'legato': {'blend': 0.5, 'transition_time': 0.05},
            'staccato': {'note_length': 0.1},
            'vibrato': {'rate': 5.0, 'depth': 0.05},
            'trill': {'interval': 2, 'rate': 6.0},
            'bend': {'amount': 1.0, 'direction': 'up'},
            'pizzicato': {'decay_rate': 8.0},
            'glissando': {'target_interval': 7, 'speed': 0.2},
            'growl': {'mod_freq': 25.0, 'depth': 0.25},
            'flutter': {'mod_freq': 12.0, 'depth': 0.15},
            'harmonics': {'harmonic': 2, 'level': 0.35},
            'swell': {'attack': 0.1, 'release': 0.2},
            'crescendo': {'target_level': 1.0, 'duration': 1.0},
            'diminuendo': {'target_level': 0.1, 'duration': 1.0},
        }
        
        # Callback for articulation changes
        self._on_articulation_change: Optional[Callable[[str], None]] = None
    
    def process_nrpn(self, msb: int, lsb: int) -> str:
        """
        Process NRPN message and return articulation name.
        
        Args:
            msb: NRPN MSB (parameter number high byte)
            lsb: NRPN LSB (parameter number low byte)
            
        Returns:
            Articulation name string
        """
        self.nrpn_msb = msb
        self.nrpn_lsb = lsb
        
        # Look up articulation
        articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), 'normal')
        
        if articulation != self.current_articulation:
            self.current_articulation = articulation
            if self._on_articulation_change:
                self._on_articulation_change(articulation)
            logger.debug(f"Articulation changed to: {articulation}")
        
        return articulation
    
    def process_sysex(self, sysex: bytes) -> Optional[Dict[str, Any]]:
        """
        Process Yamaha S.Art2 SYSEX message.
        
        SYSEX format: F0 43 [device] 4C [sub] [type] [data] ... F7
        
        Args:
            sysex: SYSEX message bytes
            
        Returns:
            Parsed command dict or None if not recognized
        """
        if len(sysex) < 6:
            return None
        
        # Check Yamaha manufacturer ID
        if sysex[1] != self.YAMAHA_SYSEX_ID:
            return None
        
        # Check for S.Art2 command (0x4C)
        if sysex[3] != 0x4C:
            return None
        
        sub = sysex[4]  # Sub status
        cmd_type = sysex[5] if len(sysex) > 5 else 0
        
        result = {
            'command': 'unknown',
            'sub': sub,
            'type': cmd_type,
        }
        
        # S.Art2 specific commands
        if sub == 0x10:  # Articulation set
            if len(sysex) >= 8:
                art_msb = sysex[6]
                art_lsb = sysex[7]
                articulation = self.process_nrpn(art_msb, art_lsb)
                result['command'] = 'set_articulation'
                result['articulation'] = articulation
        
        elif sub == 0x11:  # Articulation parameter
            if len(sysex) >= 10:
                param_msb = sysex[6]
                param_lsb = sysex[7]
                value_msb = sysex[8]
                value_lsb = sysex[9]
                result['command'] = 'set_parameter'
                result['param_msb'] = param_msb
                result['param_lsb'] = param_lsb
                result['value'] = (value_msb << 7) | value_lsb
        
        elif sub == 0x12:  # Articulation release
            result['command'] = 'release_articulation'
        
        elif sub == 0x13:  # Query current articulation
            result['command'] = 'query_articulation'
            result['articulation'] = self.current_articulation
        
        return result
    
    def build_sysex_response(self, articulation: str) -> bytes:
        """
        Build SYSEX response for current articulation.
        
        Args:
            articulation: Articulation name
            
        Returns:
            SYSEX bytes
        """
        # F0 43 10 4C 13 [art_msb] [art_lsb] F7
        # Find NRPN for articulation
        art_msb, art_lsb = self._find_nrpn_for_articulation(articulation)
        
        sysex = bytes([0xF0, 0x43, 0x10, 0x4C, 0x13, art_msb, art_lsb, 0xF7])
        return sysex
    
    def _find_nrpn_for_articulation(self, articulation: str) -> Tuple[int, int]:
        """Find NRPN MSB/LSB for an articulation name."""
        for (msb, lsb), art in self.NRPN_ARTICULATION_MAP.items():
            if art == articulation:
                return (msb, lsb)
        return (1, 0)  # Default to 'normal'
    
    def set_articulation(self, articulation: str) -> None:
        """
        Directly set articulation by name.
        
        Args:
            articulation: Articulation name
        """
        if articulation in self.get_available_articulations():
            self.current_articulation = articulation
            if self._on_articulation_change:
                self._on_articulation_change(articulation)
            logger.debug(f"Articulation set to: {articulation}")
        else:
            logger.warning(f"Unknown articulation: {articulation}")
    
    def get_articulation(self) -> str:
        """Get current articulation name."""
        return self.current_articulation
    
    def get_articulation_params(self, articulation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get parameters for an articulation.
        
        Args:
            articulation: Articulation name (uses current if None)
            
        Returns:
            Parameter dictionary
        """
        art = articulation or self.current_articulation
        return self.articulation_params.get(art, {})
    
    def set_articulation_param(self, param: str, value: Any) -> None:
        """
        Set parameter for current articulation.
        
        Args:
            param: Parameter name
            value: Parameter value
        """
        if self.current_articulation not in self.articulation_params:
            self.articulation_params[self.current_articulation] = {}
        self.articulation_params[self.current_articulation][param] = value
    
    def get_available_articulations(self) -> list:
        """Get list of all available articulations."""
        return list(set(self.NRPN_ARTICULATION_MAP.values()))
    
    def get_articulations_by_category(self, category: str) -> list:
        """Get articulations for a specific category."""
        category_map = {
            'common': [(1, i) for i in range(36)],
            'dynamics': [(2, i) for i in range(12)],
            'wind': [(3, i) for i in range(10)],
            'strings': [(4, i) for i in range(10)],
            'guitar': [(5, i) for i in range(10)],
            'brass': [(6, i) for i in range(6)],
        }
        
        nrpn_list = category_map.get(category, [])
        articulations = []
        for msb, lsb in nrpn_list:
            art = self.NRPN_ARTICULATION_MAP.get((msb, lsb))
            if art:
                articulations.append(art)
        return articulations
    
    def on_articulation_change(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for articulation changes.
        
        Args:
            callback: Function to call when articulation changes
        """
        self._on_articulation_change = callback
    
    def reset(self) -> None:
        """Reset to default articulation."""
        self.current_articulation = 'normal'
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        if self._on_articulation_change:
            self._on_articulation_change('normal')


class SF2SampleModifier:
    """
    Modifier that applies articulations to SF2 sample playback.
    
    Provides real-time sample manipulation for S.Art2-style articulations
    on SoundFont samples.
    
    Usage:
        modifier = SF2SampleModifier()
        modified = modifier.apply_articulation(sample, 'legato')
    """
    
    def __init__(self, sample_rate: int = 44100):
        """Initialize the sample modifier."""
        self.sample_rate = sample_rate
    
    def apply_articulation(
        self,
        sample: np.ndarray,
        articulation: str,
        params: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Apply articulation to sample data.
        
        Args:
            sample: Input sample array
            articulation: Articulation name
            params: Optional articulation parameters
            
        Returns:
            Modified sample array
        """
        params = params or {}
        
        if articulation == 'normal' or not articulation:
            return sample
        
        # Apply specific articulation
        method_name = f'apply_{articulation}'
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sample, params)
        
        # Default: return unchanged
        logger.debug(f"No specific handler for articulation: {articulation}")
        return sample
    
    def apply_legato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply legato articulation - smooth transitions."""
        blend = params.get('blend', 0.5)
        transition_time = params.get('transition_time', 0.05)
        
        # Apply crossfade at note boundaries
        transition_samples = int(transition_time * self.sample_rate)
        if len(sample) > transition_samples * 2:
            fade_in = np.linspace(0, 1, transition_samples)
            fade_out = np.linspace(1, 0, transition_samples)
            
            # Smooth the attack
            sample[:transition_samples] *= fade_in
            
            # Smooth the release
            sample[-transition_samples:] *= fade_out
        
        return sample
    
    def apply_staccato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply staccato - shortened notes."""
        note_length = params.get('note_length', 0.1)
        
        length_samples = int(note_length * self.sample_rate)
        if len(sample) > length_samples:
            # Truncate and apply decay
            sample = sample[:length_samples].copy()
            decay = np.exp(-np.linspace(0, 10, length_samples))
            sample *= decay
        
        return sample
    
    def apply_vibrato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply vibrato - pitch modulation."""
        rate = params.get('rate', 5.0)
        depth = params.get('depth', 0.05)
        
        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * np.sin(2 * np.pi * rate * t)
        
        # Apply frequency modulation
        phase = np.cumsum(2 * np.pi * mod)
        mod_sample = sample * np.cos(phase)
        
        return (sample + mod_sample * 0.3).astype(np.float32)
    
    def apply_trill(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply trill - rapid note alternation."""
        interval = params.get('interval', 2)  # semitones
        rate = params.get('rate', 6.0)
        
        t = np.arange(len(sample)) / self.sample_rate
        mod = np.sin(2 * np.pi * rate * t)
        
        # Alternating pitch
        SEMITONE_RATIO = 1.059463359
        freq_mult = SEMITONE_RATIO ** (interval * mod)
        
        return (sample * freq_mult).astype(np.float32)
    
    def apply_pizzicato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply pizzicato - plucked string character."""
        decay_rate = params.get('decay_rate', 8.0)
        
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-decay_rate * t)
        
        # Add slight brightness
        from scipy.signal import hilbert
        try:
            analytic = hilbert(sample)
            envelope = np.abs(analytic)
            bright_sample = sample + analytic * 0.1
            return (bright_sample * decay).astype(np.float32)
        except:
            return (sample * decay).astype(np.float32)
    
    def apply_glissando(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply glissando - slide between notes."""
        target_interval = params.get('target_interval', 7)
        speed = params.get('speed', 0.2)
        
        SEMITONE_RATIO = 1.059463359
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / speed, 0, 1)
        
        freq_mult = SEMITONE_RATIO ** (target_interval * progress)
        
        return (sample * freq_mult).astype(np.float32)
    
    def apply_growl(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply growl - growling texture."""
        mod_freq = params.get('mod_freq', 25.0)
        depth = params.get('depth', 0.25)
        
        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))
        
        # Add noise modulation
        noise = np.random.normal(0, 0.1, len(sample))
        noise = np.convolve(noise, np.ones(50)/50, mode='same')
        
        return (sample * mod + noise * 0.2).astype(np.float32)
    
    def apply_flutter(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply flutter tongue."""
        mod_freq = params.get('mod_freq', 12.0)
        depth = params.get('depth', 0.15)
        
        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))
        
        return (sample * mod).astype(np.float32)
    
    def apply_bend(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply pitch bend."""
        amount = params.get('amount', 1.0)
        direction = params.get('direction', 'up')
        
        SEMITONE_RATIO = 1.059463359
        bend_amount = amount / 12.0  # Convert semitones to octave ratio
        
        if direction == 'down':
            bend_amount = -bend_amount
        
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.linspace(0, 1, len(sample))
        
        freq_mult = SEMITONE_RATIO ** (bend_amount * progress)
        
        return (sample * freq_mult).astype(np.float32)
    
    def apply_swell(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply swell - volume crescendo then decrescendo."""
        attack = params.get('attack', 0.1)
        release = params.get('release', 0.2)
        
        t = np.arange(len(sample)) / self.sample_rate
        duration = len(sample) / self.sample_rate
        
        # Attack phase
        attack_samples = int(attack * self.sample_rate)
        release_samples = int(release * self.sample_rate)
        
        envelope = np.ones(len(sample))
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(1, 0, release_samples)
        
        return (sample * envelope).astype(np.float32)
    
    def apply_harmonics(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply harmonics - add harmonic content."""
        harmonic = params.get('harmonic', 2)
        level = params.get('level', 0.35)
        
        t = np.arange(len(sample)) / self.sample_rate
        # Assume base frequency around 440Hz
        base_freq = 440
        harmonic_wave = np.sin(2 * np.pi * base_freq * harmonic * t)
        
        return (sample + harmonic_wave * level).astype(np.float32)
    
    def apply_crescendo(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply crescendo - gradual volume increase."""
        target_level = params.get('target_level', 1.0)
        duration = params.get('duration', 1.0)
        
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / duration, 0, 1)
        
        envelope = 0.3 + progress * (target_level - 0.3)
        
        return (sample * envelope).astype(np.float32)
    
    def apply_diminuendo(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply diminuendo - gradual volume decrease."""
        target_level = params.get('target_level', 0.1)
        duration = params.get('duration', 1.0)
        
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / duration, 0, 1)
        
        envelope = 1.0 - progress * (1.0 - target_level)
        
        return (sample * envelope).astype(np.float32)
    
    def apply_marcato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply marcato - accented, strong attack."""
        t = np.arange(len(sample)) / self.sample_rate
        
        # Strong attack
        attack_samples = int(0.02 * self.sample_rate)
        envelope = np.ones(len(sample))
        envelope[:attack_samples] = np.linspace(0, 1.5, attack_samples)
        
        # Quick decay
        decay = np.exp(-t * 8)
        
        return (sample * envelope * decay).astype(np.float32)


# Factory function
def create_articulation_controller() -> ArticulationController:
    """Create and return an ArticulationController instance."""
    return ArticulationController()


def create_sample_modifier(sample_rate: int = 44100) -> SF2SampleModifier:
    """Create and return an SF2SampleModifier instance."""
    return SF2SampleModifier(sample_rate=sample_rate)
