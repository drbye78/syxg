import numpy as np
from scipy.io import wavfile
from typing import List, Dict, Optional, Tuple, Union
import logging
import mido
from mido import MidiFile
import time
from dataclasses import dataclass
from enum import Enum


# Настройка логирования для production-like качества
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArticulationType(Enum):
    """Enumeration of supported articulation types."""
    NORMAL = "normal"
    LEGATO = "legato"
    STACCATO = "staccato"
    BEND = "bend"
    VIBRATO = "vibrato"
    BREATH = "breath"
    GLISS = "gliss"
    GROWL = "growl"
    FLUTTER = "flutter"
    TRILL = "trill"
    PIZZICATO = "pizzicato"
    GRACE = "grace"
    SHAKE = "shake"
    FALL = "fall"
    DOIT = "doit"
    TONGUE_SLAP = "tongue_slap"
    HARMONICS = "harmonics"
    HAMMER_ON = "hammer_on"
    PULL_OFF = "pull_off"
    KEY_OFF = "key_off"
    MARCATO = "marcato"
    DETACHE = "detache"
    SUL_PONTICELLO = "sul_ponticello"
    SCOOP = "scoop"
    RIP = "rip"
    PORTAMENTO = "portamento"
    SWELL = "swell"
    ACCENTED = "accented"
    BOW_UP = "bow_up"
    BOW_DOWN = "bow_down"
    COL_LEGNO = "col_legno"
    UP_BEND = "up_bend"
    DOWN_BEND = "down_bend"
    SMEAR = "smear"
    FLIP = "flip"
    STRAIGHT = "straight"


@dataclass
class ArticulationParams:
    """Parameters for articulation effects."""
    # Vibrato parameters
    vibrato_depth: float = 0.05
    vibrato_rate: float = 5.0
    
    # Bend parameters
    bend_amount: float = 0.02  # Fractional frequency change
    
    # Trill parameters
    trill_frequency: float = 5.0
    trill_semitone: float = 1.05946
    
    # Shake parameters
    shake_frequency: float = 8.0
    
    # Growl/flutter parameters
    growl_frequency: float = 20.0
    flutter_frequency: float = 10.0
    
    # Duration parameters
    grace_duration: float = 0.05
    slap_duration: float = 0.02
    hammer_duration: float = 0.01
    pull_duration: float = 0.01
    scoop_duration: float = 0.05
    flip_duration: float = 0.03
    
    # Noise parameters
    breath_noise_level: float = 0.1
    key_off_noise_level: float = 0.05
    col_legno_noise_level: float = 0.2


class YamahaNRPNMapper:
    """
    Маппинг NRPN сообщений Yamaha для S.Art2 артикуляций.
    Основан на документации Yamaha для Genos/PSR, где NRPN используются для переключения элементов артикуляции.
    """
    def __init__(self):
        self.nrpn_to_articulation: Dict[Tuple[int, int], str] = {
            # Общие (MSB 1: ART1/ART2/ART3-like)
            (1, 0): 'normal',
            (1, 1): 'legato',
            (1, 2): 'staccato',
            (1, 3): 'bend',
            (1, 4): 'vibrato',
            (1, 5): 'breath',
            (1, 6): 'gliss',
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
            # Духовые специфические (MSB 2)
            (2, 0): 'growl',
            (2, 1): 'flutter',
            (2, 2): 'tongue_slap',
            (2, 3): 'smear',
            (2, 4): 'flip',
            (2, 5): 'scoop',
            (2, 6): 'rip',
            # Струнные специфические (MSB 3)
            (3, 0): 'pizzicato',
            (3, 1): 'harmonics',
            (3, 2): 'sul_ponticello',
            (3, 3): 'bow_up',
            (3, 4): 'bow_down',
            (3, 5): 'col_legno',
            (3, 6): 'portamento',
            # Гитарные (MSB 4)
            (4, 0): 'hammer_on',
            (4, 1): 'pull_off',
            (4, 2): 'harmonics',
        }

    def get_articulation(self, msb: int, lsb: int) -> str:
        return self.nrpn_to_articulation.get((msb, lsb), 'normal')


class ImprovedKarplusStrongSynthesizer:
    """
    Improved Karplus-Strong string synthesis with realistic physical modeling.
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        
    def generate(self, 
                 freq: float, 
                 duration: float, 
                 velocity: int = 100,
                 feedback: float = 0.996,
                 damping: float = 0.001,
                 pluck_position: float = 0.1) -> np.ndarray:
        """
        Generate a string sound using improved Karplus-Strong algorithm.
        
        Args:
            freq: Fundamental frequency
            duration: Duration in seconds
            velocity: MIDI velocity (0-127)
            feedback: Feedback coefficient (0-1)
            damping: Damping factor for high frequencies
            pluck_position: Position along string where plucked (0-1)
            
        Returns:
            Generated audio signal as numpy array
        """
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        if not 0 <= feedback <= 1:
            raise ValueError("Feedback must be between 0 and 1")
        if not 0 <= pluck_position <= 1:
            raise ValueError("Pluck position must be between 0 and 1")
            
        n_samples = int(self.sample_rate * duration)
        period = int(self.sample_rate / freq)
        
        # Validate period to prevent division by zero
        if period <= 1:
            period = 2
            
        # Initialize delay line with noise burst at pluck position
        delay_line_length = max(period, 2)
        delay_line = np.zeros(delay_line_length)
        
        # Create pluck with proper position and shape
        pluck_start = int(pluck_position * delay_line_length)
        pluck_width = max(1, int(0.1 * delay_line_length))
        
        # Generate initial excitation (pluck)
        excitation_length = min(pluck_width * 2, delay_line_length)
        excitation_pos = max(0, pluck_start - pluck_width // 2)
        excitation_end = min(excitation_pos + excitation_length, delay_line_length)
        
        if excitation_end > excitation_pos:
            # Create a triangular pluck shape
            excitation_range = excitation_end - excitation_pos
            triangle_pluck = np.concatenate([
                np.linspace(0, 1, excitation_range // 2),
                np.linspace(1, 0, excitation_range - excitation_range // 2)
            ])
            if len(triangle_pluck) > excitation_range:
                triangle_pluck = triangle_pluck[:excitation_range]
                
            delay_line[excitation_pos:excitation_pos + len(triangle_pluck)] = (
                triangle_pluck * (velocity / 127.0)
            )
        
        # Generate output with improved filtering
        output = np.zeros(n_samples)
        read_idx = 0
        write_idx = 0
        
        for i in range(n_samples):
            # Read from delay line
            sample = delay_line[read_idx]
            output[i] = sample
            
            # Apply feedback with damping
            delayed_sample = delay_line[write_idx]
            new_sample = feedback * (sample + delayed_sample * (1 - damping))
            
            # Write to delay line
            delay_line[write_idx] = new_sample
            
            # Update indices
            read_idx = (read_idx + 1) % delay_line_length
            write_idx = (write_idx + 1) % delay_line_length
            
        return output


class SuperArticulation2Synthesizer:
    """
    Класс для симуляции Super Articulation 2 (S.Art2) технологии Yamaha.
    Поддерживает расширенный список инструментов и артикуляций.
    Интеграция с MIDI: чтение файлов, real-time input, NRPN для артикуляций.
    Синтез: FM для духовых, Karplus-Strong для струнных.
    """
    def __init__(
        self,
        instrument: str = 'saxophone',
        sample_rate: int = 44100,
        base_feedback: float = 0.98,
        vibrato_depth: float = 0.05,
        vibrato_rate: float = 5.0,
    ):
        self.instrument = instrument.lower()
        self.sample_rate = sample_rate
        self.base_feedback = base_feedback
        self.vibrato_depth = vibrato_depth
        self.vibrato_rate = vibrato_rate
        self.nrpn_mapper = YamahaNRPNMapper()
        self.current_articulation = 'normal'
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.instrument_params = self._get_instrument_params()
        self.articulation_params = ArticulationParams(
            vibrato_depth=vibrato_depth,
            vibrato_rate=vibrato_rate
        )
        self.ks_synthesizer = ImprovedKarplusStrongSynthesizer(sample_rate=sample_rate)
        self._validate_params()

    def _get_instrument_params(self) -> Dict[str, Dict]:
        """Параметры для инструментов (расширенный список)."""
        return {
            'saxophone': {'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 5.0, 'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.7, 'release_time': 0.2, 'feedback': 0.98},
            'trumpet': {'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 4.0, 'attack_time': 0.03, 'decay_time': 0.08, 'sustain_level': 0.8, 'release_time': 0.15, 'feedback': 0.98},
            'clarinet': {'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 3.0, 'attack_time': 0.07, 'decay_time': 0.12, 'sustain_level': 0.6, 'release_time': 0.25, 'feedback': 0.98},
            'flute': {'synthesis_method': 'fm', 'mod_ratio': 1.2, 'mod_index_max': 2.5, 'attack_time': 0.06, 'decay_time': 0.09, 'sustain_level': 0.75, 'release_time': 0.18, 'feedback': 0.98},
            'oboe': {'synthesis_method': 'fm', 'mod_ratio': 1.8, 'mod_index_max': 4.5, 'attack_time': 0.08, 'decay_time': 0.11, 'sustain_level': 0.65, 'release_time': 0.22, 'feedback': 0.98},
            'trombone': {'synthesis_method': 'fm', 'mod_ratio': 2.5, 'mod_index_max': 3.5, 'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.85, 'release_time': 0.2, 'feedback': 0.98},
            'french_horn': {'synthesis_method': 'fm', 'mod_ratio': 2.2, 'mod_index_max': 4.2, 'attack_time': 0.06, 'decay_time': 0.12, 'sustain_level': 0.8, 'release_time': 0.25, 'feedback': 0.98},
            'bassoon': {'synthesis_method': 'fm', 'mod_ratio': 0.8, 'mod_index_max': 4.8, 'attack_time': 0.09, 'decay_time': 0.15, 'sustain_level': 0.6, 'release_time': 0.3, 'feedback': 0.98},
            'tenor_sax': {'synthesis_method': 'fm', 'mod_ratio': 1.6, 'mod_index_max': 5.5, 'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.75, 'release_time': 0.2, 'feedback': 0.98},
            'alto_sax': {'synthesis_method': 'fm', 'mod_ratio': 1.4, 'mod_index_max': 5.0, 'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.72, 'release_time': 0.2, 'feedback': 0.98},
            'violin': {'synthesis_method': 'ks', 'feedback': 0.995, 'attack_time': 0.1, 'decay_time': 0.15, 'sustain_level': 0.5, 'release_time': 0.3, 'damping': 0.002, 'pluck_position': 0.1},
            'cello': {'synthesis_method': 'ks', 'feedback': 0.99, 'attack_time': 0.12, 'decay_time': 0.18, 'sustain_level': 0.4, 'release_time': 0.35, 'damping': 0.003, 'pluck_position': 0.15},
            'guitar': {'synthesis_method': 'ks', 'feedback': 0.996, 'attack_time': 0.02, 'decay_time': 0.05, 'sustain_level': 0.6, 'release_time': 0.1, 'damping': 0.001, 'pluck_position': 0.2},
            'bass_guitar': {'synthesis_method': 'ks', 'feedback': 0.985, 'attack_time': 0.03, 'decay_time': 0.07, 'sustain_level': 0.55, 'release_time': 0.15, 'damping': 0.002, 'pluck_position': 0.25},
            'harp': {'synthesis_method': 'ks', 'feedback': 0.997, 'attack_time': 0.01, 'decay_time': 0.04, 'sustain_level': 0.3, 'release_time': 0.4, 'damping': 0.0005, 'pluck_position': 0.1},
            'viola': {'synthesis_method': 'ks', 'feedback': 0.993, 'attack_time': 0.11, 'decay_time': 0.16, 'sustain_level': 0.48, 'release_time': 0.32, 'damping': 0.002, 'pluck_position': 0.12},
            'contrabass': {'synthesis_method': 'ks', 'feedback': 0.988, 'attack_time': 0.14, 'decay_time': 0.2, 'sustain_level': 0.45, 'release_time': 0.4, 'damping': 0.003, 'pluck_position': 0.18},
            'electric_guitar': {'synthesis_method': 'ks', 'feedback': 0.992, 'attack_time': 0.015, 'decay_time': 0.06, 'sustain_level': 0.7, 'release_time': 0.12, 'damping': 0.0015, 'pluck_position': 0.22},
            'marimba': {'synthesis_method': 'ks', 'feedback': 0.98, 'attack_time': 0.01, 'decay_time': 0.08, 'sustain_level': 0.25, 'release_time': 0.6, 'damping': 0.005, 'pluck_position': 0.05},
            'strings_ensemble': {'synthesis_method': 'ks', 'feedback': 0.996, 'attack_time': 0.15, 'decay_time': 0.2, 'sustain_level': 0.65, 'release_time': 0.35, 'damping': 0.001, 'pluck_position': 0.1},
        }

    def _validate_params(self) -> None:
        if self.instrument not in self.instrument_params:
            raise ValueError(f"Unsupported instrument: {self.instrument}. Supported: {list(self.instrument_params.keys())}")
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")
        if not 0 < self.base_feedback < 1:
            raise ValueError("Base feedback must be between 0 and 1.")
        logger.info(f"Initialized S.Art2 synthesizer for {self.instrument} at {self.sample_rate} Hz.")

    def _generate_fm_tone(self, freq: float, duration: float, velocity: int, params: Dict) -> np.ndarray:
        """Generate FM synthesized tone."""
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        if duration <= 0:
            raise ValueError("Duration must be positive")
            
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        mod_index = velocity / 127.0 * params['mod_index_max']
        modulator = np.sin(2 * np.pi * freq * params['mod_ratio'] * t)
        carrier = np.sin(2 * np.pi * freq * t + mod_index * modulator)
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        return carrier * envelope * (velocity / 127.0)

    def _generate_ks_tone(self, freq: float, duration: float, velocity: int, params: Dict) -> np.ndarray:
        """Generate Karplus-Strong synthesized tone with improved algorithm."""
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        if duration <= 0:
            raise ValueError("Duration must be positive")
            
        # Extract KS-specific parameters
        feedback = params.get('feedback', self.base_feedback)
        damping = params.get('damping', 0.001)
        pluck_position = params.get('pluck_position', 0.1)
        
        # Generate the base tone using improved KS algorithm
        samples = self.ks_synthesizer.generate(
            freq=freq,
            duration=duration,
            velocity=velocity,
            feedback=feedback,
            damping=damping,
            pluck_position=pluck_position
        )
        
        # Apply ADSR envelope
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        samples *= envelope[:len(samples)]
        
        # Normalize to prevent clipping
        max_amplitude = np.max(np.abs(samples)) if np.max(np.abs(samples)) != 0 else 1
        if max_amplitude > 1.0:
            samples /= max_amplitude
            
        return samples * (velocity / 127.0)

    def _generate_adsr_envelope(self, duration: float, velocity: int, params: Dict) -> np.ndarray:
        """Generate ADSR envelope with velocity-dependent attack."""
        if duration <= 0:
            raise ValueError("Duration must be positive")
        if velocity < 0 or velocity > 127:
            raise ValueError("Velocity must be between 0 and 127")
            
        total_samples = int(self.sample_rate * duration)
        attack_time = params['attack_time'] if velocity > 80 else params['attack_time'] * 1.5
        decay_time = params['decay_time']
        release_time = params['release_time']
        sustain_level = params['sustain_level']

        attack_samples = int(attack_time * self.sample_rate)
        decay_samples = int(decay_time * self.sample_rate)
        release_samples = int(release_time * self.sample_rate)

        # Ensure we don't exceed total samples
        attack_samples = min(attack_samples, total_samples)
        decay_samples = min(decay_samples, total_samples - attack_samples)
        release_samples = min(release_samples, total_samples - attack_samples - decay_samples)

        envelope = np.zeros(total_samples)
        
        # Attack phase
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay phase
        sustain_start = attack_samples + decay_samples
        if decay_samples > 0:
            envelope[attack_samples:sustain_start] = np.linspace(1, sustain_level, decay_samples)
        
        # Sustain phase
        sustain_end = total_samples - release_samples
        if sustain_end > sustain_start:
            envelope[sustain_start:sustain_end] = sustain_level
        
        # Release phase
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(sustain_level, 0, release_samples)
            
        return envelope

    def _generate_base_tone(self, freq: float, duration: float, velocity: int = 100) -> np.ndarray:
        """Generate base tone using appropriate synthesis method."""
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        if velocity < 0 or velocity > 127:
            raise ValueError("Velocity must be between 0 and 127")
            
        params = self.instrument_params[self.instrument]
        if params['synthesis_method'] == 'fm':
            return self._generate_fm_tone(freq, duration, velocity, params)
        elif params['synthesis_method'] == 'ks':
            return self._generate_ks_tone(freq, duration, velocity, params)
        else:
            raise ValueError(f"Unknown synthesis method: {params['synthesis_method']}")

    def _apply_articulation(self, waveform: np.ndarray, articulation: str, freq: float) -> np.ndarray:
        """Apply articulation effect to waveform with improved quality."""
        if len(waveform) == 0:
            return waveform
            
        # Validate inputs
        if freq <= 0:
            raise ValueError("Frequency must be positive")
        if not isinstance(articulation, str):
            raise TypeError("Articulation must be a string")
            
        t = np.arange(len(waveform)) / self.sample_rate
        
        # Convert articulation string to enum for validation
        try:
            articulation_type = ArticulationType(articulation.lower())
        except ValueError:
            logger.warning(f"Unknown articulation: {articulation}, using 'normal'")
            articulation_type = ArticulationType.NORMAL
            
        # Apply articulation based on type
        if articulation_type in [ArticulationType.NORMAL, ArticulationType.STRAIGHT]:
            return waveform
        elif articulation_type == ArticulationType.STACCATO:
            decay_env = np.exp(-t / 0.2)
            return waveform * decay_env
        elif articulation_type == ArticulationType.LEGATO:
            # Legato is typically handled in sequences, not individual notes
            return waveform
        elif articulation_type in [ArticulationType.BEND, ArticulationType.UP_BEND]:
            bend_amount = 1.0 + self.articulation_params.bend_amount
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.DOWN_BEND:
            bend_amount = 1.0 - self.articulation_params.bend_amount
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.VIBRATO:
            vibrato = self.articulation_params.vibrato_depth * np.sin(
                2 * np.pi * self.articulation_params.vibrato_rate * t
            )
            return waveform * (1 + vibrato)
        elif articulation_type == ArticulationType.BREATH:
            # Add filtered noise to simulate breathiness
            noise = self.articulation_params.breath_noise_level * np.random.normal(0, 1, len(waveform))
            # Apply low-pass filter simulation
            kernel_size = 100
            if len(noise) >= kernel_size:
                window = np.ones(kernel_size) / kernel_size
                filtered_noise = np.convolve(noise, window, mode='same')
            else:
                filtered_noise = noise
            return waveform + filtered_noise
        elif articulation_type in [ArticulationType.GLISS, ArticulationType.PORTAMENTO]:
            gliss_amount = 1.05
            freq_slide = np.linspace(freq, freq * gliss_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return waveform * np.sin(phase)
        elif articulation_type == ArticulationType.GROWL:
            growl_freq = self.articulation_params.growl_frequency
            growl = 0.2 * (1 + np.sin(2 * np.pi * growl_freq * t))
            return waveform * growl
        elif articulation_type == ArticulationType.FLUTTER:
            flutter_freq = self.articulation_params.flutter_frequency
            flutter = 0.1 * (1 + np.sin(2 * np.pi * flutter_freq * t))
            return waveform * flutter
        elif articulation_type == ArticulationType.TRILL:
            trill_semitone = self.articulation_params.trill_semitone
            trill_freq = self.articulation_params.trill_frequency
            trill_mod = np.sin(2 * np.pi * trill_freq * t)
            freq_mod = freq * (1 + 0.01 * trill_mod * (trill_semitone - 1))
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.PIZZICATO:
            decay_env = np.exp(-t / 0.1)
            return waveform * decay_env
        elif articulation_type == ArticulationType.GRACE:
            grace_duration = self.articulation_params.grace_duration
            grace_samples = int(grace_duration * self.sample_rate)
            if grace_samples >= len(waveform):
                return waveform  # Grace note too long, return original
                
            grace_freq = freq * 1.05946
            grace_wave = np.sin(2 * np.pi * grace_freq * t[:grace_samples])
            grace_env = np.linspace(0, 1, grace_samples // 2)
            grace_env = np.concatenate((grace_env, grace_env[::-1]))
            result = waveform.copy()
            result[:grace_samples] += grace_wave * grace_env * 0.5
            return result
        elif articulation_type == ArticulationType.SHAKE:
            shake_freq = self.articulation_params.shake_frequency
            shake_mod = np.sin(2 * np.pi * shake_freq * t)
            freq_mod = freq * (1 + 0.02 * shake_mod)
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.FALL:
            fall_amount = 0.95
            freq_slide = np.linspace(freq, freq * fall_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.DOIT:
            doit_amount = 1.05
            half_len = len(waveform) // 2
            freq_slide = np.linspace(freq, freq * doit_amount, half_len)
            freq_slide = np.concatenate((freq_slide, np.full(len(waveform) - half_len, freq * doit_amount)))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.TONGUE_SLAP:
            slap_duration = self.articulation_params.slap_duration
            slap_samples = int(slap_duration * self.sample_rate)
            if slap_samples >= len(waveform):
                return waveform  # Slap too long, return original
                
            slap_noise = 0.3 * np.random.normal(0, 1, slap_samples)
            result = waveform.copy()
            result[:slap_samples] += slap_noise
            return result
        elif articulation_type == ArticulationType.HARMONICS:
            harmonic_mult = 2.0
            harmonic_wave = np.sin(2 * np.pi * freq * harmonic_mult * t)
            return waveform + 0.3 * harmonic_wave
        elif articulation_type == ArticulationType.HAMMER_ON:
            hammer_duration = self.articulation_params.hammer_duration
            hammer_samples = int(hammer_duration * self.sample_rate)
            if hammer_samples * 2 >= len(waveform):
                return waveform  # Hammer too long, return original
                
            result = waveform.copy()
            hammer_env = np.linspace(0, 1, hammer_samples)
            result[hammer_samples:hammer_samples*2] *= (1 + 0.2 * hammer_env)
            return result
        elif articulation_type == ArticulationType.PULL_OFF:
            pull_duration = self.articulation_params.pull_duration
            pull_samples = int(pull_duration * self.sample_rate)
            if pull_samples >= len(waveform):
                return waveform  # Pull-off too long, return original
                
            result = waveform.copy()
            pull_env = np.linspace(1, 0, pull_samples)
            result[-pull_samples:] *= pull_env
            return result
        elif articulation_type == ArticulationType.KEY_OFF:
            off_noise = self.articulation_params.key_off_noise_level * np.random.normal(0, 1, len(waveform) // 10)
            if len(off_noise) >= len(waveform):
                return waveform  # Noise too long, return original
                
            result = waveform.copy()
            result[-len(off_noise):] += off_noise
            return result
        elif articulation_type == ArticulationType.MARCATO:
            marcato_env = np.exp(-t / 0.15) * 1.2
            return waveform * marcato_env
        elif articulation_type == ArticulationType.DETACHE:
            result = waveform.copy()
            detach_len = min(int(0.1 * self.sample_rate), len(result))
            if detach_len > 0:
                result[-detach_len:] *= np.linspace(1, 0, detach_len)
            return result
        elif articulation_type == ArticulationType.SUL_PONTICELLO:
            pont_noise = 0.15 * np.random.normal(0, 1, len(waveform))
            # High-pass filter simulation
            high_pass = np.diff(pont_noise, prepend=pont_noise[0])
            return waveform + high_pass
        elif articulation_type == ArticulationType.SCOOP:
            scoop_duration = self.articulation_params.scoop_duration
            scoop_samples = min(int(scoop_duration * self.sample_rate), len(waveform) // 4)
            if scoop_samples <= 0:
                return waveform  # Scoop too short, return original
                
            scoop_amount = 0.98
            freq_slide = np.linspace(freq * scoop_amount, freq, scoop_samples)
            remaining_samples = len(waveform) - scoop_samples
            freq_slide = np.concatenate((freq_slide, np.full(remaining_samples, freq)))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.RIP:
            rip_amount = 1.05
            quarter_len = min(len(waveform) // 4, int(0.1 * self.sample_rate))
            if quarter_len <= 0:
                return waveform  # Rip too short, return original
                
            freq_slide_up = np.linspace(freq, freq * rip_amount, quarter_len)
            freq_slide_down = freq_slide_up[::-1]
            freq_constant = np.full(len(waveform) - 2 * quarter_len, freq * rip_amount)
            
            freq_slide = np.concatenate((freq_slide_up, freq_constant, freq_slide_down))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            return np.sin(phase) * np.abs(waveform)  # Preserve amplitude envelope
        elif articulation_type == ArticulationType.SWELL:
            if len(t) > 1:
                swell_env = np.sin(np.pi * t / max(t) if max(t) > 0 else 1)
                return waveform * swell_env * 1.2
            else:
                return waveform
        elif articulation_type == ArticulationType.ACCENTED:
            acc_env = np.exp(-t / 0.1) * 1.5
            return waveform * acc_env
        elif articulation_type == ArticulationType.BOW_UP:
            bow_env = np.linspace(0.8, 1.2, len(waveform))
            return waveform * bow_env
        elif articulation_type == ArticulationType.BOW_DOWN:
            bow_env = np.linspace(1.2, 0.8, len(waveform))
            return waveform * bow_env
        elif articulation_type == ArticulationType.COL_LEGNO:
            legno_noise = self.articulation_params.col_legno_noise_level * np.random.normal(0, 1, len(waveform))
            decay_env = np.exp(-t / 0.3)
            return (waveform + legno_noise) * decay_env
        elif articulation_type == ArticulationType.SMEAR:
            smear_freq = 15.0
            smear_mod = 0.1 * np.sin(2 * np.pi * smear_freq * t)
            return waveform * (1 + smear_mod)
        elif articulation_type == ArticulationType.FLIP:
            flip_duration = self.articulation_params.flip_duration
            flip_samples = min(int(flip_duration * self.sample_rate), len(waveform) // 4)
            if flip_samples <= 0:
                return waveform  # Flip too short, return original
                
            flip_freq = freq * 1.05946 * 2
            flip_wave = np.sin(2 * np.pi * flip_freq * t[:flip_samples])
            flip_env = np.linspace(0, 1, flip_samples // 2)
            flip_env = np.concatenate((flip_env[::-1], flip_env))
            if len(flip_env) > len(flip_wave):
                flip_env = flip_env[:len(flip_wave)]
            elif len(flip_env) < len(flip_wave):
                flip_env = np.pad(flip_env, (0, len(flip_wave) - len(flip_env)), mode='constant')
                
            result = waveform.copy()
            result[:flip_samples] += flip_wave * flip_env * 0.4
            return result
        else:
            # Default to normal articulation for unknown types
            return waveform

    def synthesize_note(self, freq: float, duration: float, velocity: int = 100, articulation: Optional[str] = None) -> np.ndarray:
        """Synthesize a single note with specified parameters."""
        articulation = articulation or self.current_articulation
        
        try:
            base = self._generate_base_tone(freq, duration, velocity)
            articulated = self._apply_articulation(base, articulation, freq)
            
            # Normalize to prevent clipping
            max_amplitude = np.max(np.abs(articulated)) if np.max(np.abs(articulated)) != 0 else 1
            if max_amplitude > 1.0:
                articulated /= max_amplitude
                
            return articulated.astype(np.float32)
        except Exception as e:
            logger.error(f"Error synthesizing note: {e}")
            raise

    def synthesize_note_sequence(self, notes: List[Dict[str, float]], overlap: float = 0.05) -> np.ndarray:
        """Synthesize a sequence of notes with proper transitions."""
        if not notes:
            return np.array([])
            
        audio = np.array([])
        prev_articulation = None

        for note in notes:
            if 'freq' not in note or 'duration' not in note:
                logger.warning(f"Skipping invalid note: {note}")
                continue
                
            articulation = note.get('articulation', self.current_articulation)
            velocity = note.get('velocity', 100)
            
            note_audio = self.synthesize_note(note['freq'], note['duration'], velocity, articulation)

            if prev_articulation == 'legato' and len(audio) > 0:
                overlap_samples = int(overlap * self.sample_rate)
                if overlap_samples > 0 and overlap_samples < len(audio) and overlap_samples < len(note_audio):
                    fade_out = np.linspace(1, 0, overlap_samples)
                    fade_in = np.linspace(0, 1, overlap_samples)
                    audio[-overlap_samples:] *= fade_out
                    note_audio[:overlap_samples] *= fade_in
                    audio[-overlap_samples:] += note_audio[:overlap_samples]
                    audio = np.concatenate((audio, note_audio[overlap_samples:]))
            else:
                audio = np.concatenate((audio, note_audio))

            prev_articulation = articulation

        return audio

    def save_to_wav(self, audio: np.ndarray, filename: str) -> None:
        """Save audio to WAV file."""
        try:
            # Ensure audio is in the right format for WAV
            if audio.dtype != np.int16:
                # Normalize to [-1, 1] then convert to int16
                audio_normalized = audio / np.max(np.abs(audio)) if np.max(np.abs(audio)) != 0 else audio
                audio_int16 = (audio_normalized * 32767).astype(np.int16)
            else:
                audio_int16 = audio
                
            wavfile.write(filename, self.sample_rate, audio_int16)
            logger.info(f"Saved audio to {filename}")
        except Exception as e:
            logger.error(f"Error saving WAV: {e}")
            raise

    # MIDI Интеграция
    def process_midi_file(self, midi_path: str, output_wav: str = 'output.wav', tempo: int = 120) -> None:
        """
        Обработка MIDI-файла: синтез аудио с учетом NRPN, note_on/off, velocity.
        """
        mid = MidiFile(midi_path)
        audio = np.array([])
        active_notes: Dict[int, Tuple[float, float, int, str]] = {}  # note: (start_time, freq, velocity, articulation)
        current_time = 0.0
        ticks_per_beat = mid.ticks_per_beat
        tempo_microseconds = tempo  # Микросекунд на бит (default 120 BPM -> 500000 us/beat)

        for track in mid.tracks:
            for msg in track:
                delta_time_sec = mido.tick2second(msg.time, ticks_per_beat, tempo_microseconds)
                current_time += delta_time_sec

                if msg.type == 'set_tempo':
                    tempo_microseconds = msg.tempo

                if msg.type == 'control_change':
                    if msg.control == 99:  # NRPN MSB
                        self.nrpn_msb = msg.value
                    elif msg.control == 98:  # NRPN LSB
                        self.nrpn_lsb = msg.value
                        self.current_articulation = self.nrpn_mapper.get_articulation(self.nrpn_msb, self.nrpn_lsb)
                        logger.info(f"NRPN: Articulation set to {self.current_articulation}")

                if msg.type == 'note_on' and msg.velocity > 0:
                    freq = mido.midifreq(msg.note)
                    active_notes[msg.note] = (current_time, freq, msg.velocity, self.current_articulation)

                if (msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)) and msg.note in active_notes:
                    start_time, freq, velocity, art = active_notes.pop(msg.note)
                    duration = current_time - start_time
                    note_audio = self.synthesize_note(freq, duration, velocity, art)
                    # Добавляем в аудио на позиции start_time
                    start_sample = int(start_time * self.sample_rate)
                    if len(audio) < start_sample + len(note_audio):
                        audio = np.pad(audio, (0, start_sample + len(note_audio) - len(audio)))
                    audio[start_sample:start_sample + len(note_audio)] += note_audio

        self.save_to_wav(audio, output_wav)

    def listen_midi_real_time(self, port_name: Optional[str] = None, output_device: Optional[str] = None) -> None:
        """
        Real-time прослушивание MIDI-ввода: реагирует на note_on/off, NRPN.
        Для вывода аудио можно интегрировать с audio backend (например, sounddevice), но здесь симулируем лог/синтез.
        """
        if port_name is None:
            available_ports = mido.get_input_names()
            if not available_ports:
                raise ValueError("No MIDI input ports available.")
            port_name = available_ports[0]

        logger.info(f"Listening on MIDI port: {port_name}")

        with mido.open_input(port_name) as inport:
            active_notes: Dict[int, float] = {}  # note: start_time
            while True:  # Бесконечный цикл для real-time
                for msg in inport.iter_pending():
                    current_time = time.time()

                    if msg.type == 'control_change':
                        if msg.control == 99:
                            self.nrpn_msb = msg.value
                        elif msg.control == 98:
                            self.nrpn_lsb = msg.value
                            self.current_articulation = self.nrpn_mapper.get_articulation(self.nrpn_msb, self.nrpn_lsb)
                            logger.info(f"Real-time NRPN: Articulation {self.current_articulation}")

                    if msg.type == 'note_on' and msg.velocity > 0:
                        active_notes[msg.note] = current_time
                        logger.info(f"Note ON: {msg.note}, velocity {msg.velocity}, art {self.current_articulation}")
                        # Здесь можно играть звук в реальном времени (например, через PyAudio или sounddevice)

                    if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        if msg.note in active_notes:
                            start_time = active_notes.pop(msg.note)
                            duration = current_time - start_time
                            freq = mido.midifreq(msg.note)
                            note_audio = self.synthesize_note(freq, duration, msg.velocity)
                            # Сохранить или сыграть note_audio в реальном времени
                            self.save_to_wav(note_audio, f'note_{msg.note}.wav')  # Пример сохранения
                            logger.info(f"Note OFF: {msg.note}, duration {duration:.2f}s")

                time.sleep(0.01)  # Чтобы не нагружать CPU


# Example usage
if __name__ == "__main__":
    synth = SuperArticulation2Synthesizer(instrument='tenor_sax')

    # Синтез последовательности
    notes = [
        {'freq': 440.0, 'duration': 1.0, 'articulation': 'growl', 'velocity': 90},
        {'freq': 493.88, 'duration': 1.0, 'articulation': 'gliss', 'velocity': 100},
    ]
    audio = synth.synthesize_note_sequence(notes)
    synth.save_to_wav(audio, 'example.wav')

    # MIDI файл
    # synth.process_midi_file('example.mid', 'midi_render.wav')

    # Real-time
    # synth.listen_midi_real_time()