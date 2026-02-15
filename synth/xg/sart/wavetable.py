"""
Wavetable Synthesis Engine for S.Art2.

Provides realistic acoustic instrument tones using pre-computed wavetables
that can be morphed and blended for expressive performance.
"""

import numpy as np
from typing import Dict, Tuple, Optional


class WavetableSynthesisEngine:
    """
    Wavetable synthesis engine with pre-defined wavetables for acoustic instruments.
    Supports morphing between wavetables and various waveform generation methods.
    """
    
    # Wavetable size (power of 2)
    TABLE_SIZE = 2048
    
    # Pre-defined wavetables for different instrument categories
    WAVETABLES: Dict[str, np.ndarray] = {}
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._generate_all_wavetables()
    
    def _generate_sine_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate pure sine wave."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        return np.sin(t).astype(np.float32)
    
    def _generate_triangle_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate triangle wave."""
        t = np.linspace(-1, 1, n_samples, False)
        # Triangle is 2*|sawtooth| - 1
        return (2 * np.abs(2 * t / np.pi - np.floor(t / np.pi + 0.5)) - 1).astype(np.float32)
    
    def _generate_sawtooth_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate sawtooth wave."""
        t = np.linspace(-1, 1, n_samples, False)
        return (t / np.abs(t) * (2 * (t / np.pi - np.floor(t / np.pi + 0.5)))).astype(np.float32)
    
    def _generate_square_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate square wave."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        return np.sign(np.sin(t)).astype(np.float32)
    
    def _generate_pulse_wave(self, duty: float = 0.5, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate pulse wave with variable duty cycle."""
        t = np.linspace(0, 1, n_samples, False)
        return (t < duty).astype(np.float32) * 2 - 1
    
    def _generate_acoustic_piano(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate acoustic piano-like waveform (rich harmonics)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Fundamental + harmonics with decreasing amplitude
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 12):  # 11 harmonics
            amplitude = 1.0 / (h ** 1.5)  # Piano-like harmonic decay
            wave += amplitude * np.sin(h * t)
        
        # Normalize
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_organ_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate organ-like waveform (additive synthesis)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Organ typically has fundamental + odd harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in [1, 2, 3, 4, 6, 8, 10]:  # Typical organ drawbar set
            amplitude = 1.0 / h
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_soft_string(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate soft string-like waveform."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Soft strings have fewer high harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 6):
            amplitude = 1.0 / (h ** 2.5)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_bright_string(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate bright string-like waveform."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Bright strings have more harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 10):
            amplitude = 1.0 / h
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_clarinet_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate clarinet-like waveform (odd harmonics)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Clarinet: fundamental + odd harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 10, 2):
            amplitude = 1.0 / h
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_sax_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate saxophone-like waveform (rich, warm)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Sax: fundamental + harmonics with specific envelope
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 15):
            amplitude = 1.0 / (h ** 1.2)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_brass_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate brass-like waveform (bright, bold)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Brass: fundamental + strong harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 12):
            amplitude = 1.0 / (h ** 1.3)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_flute_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate flute-like waveform (pure, soft)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Flute: mostly fundamental + slight harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in [1, 2, 3, 5]:
            amplitude = 1.0 / (h ** 3)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_violin_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate violin-like waveform."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Violin: complex harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 16):
            amplitude = 1.0 / (h ** 1.8)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_guitar_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate guitar-like waveform (plucked string)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Guitar: plucked string characteristics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 14):
            amplitude = 1.0 / (h ** 1.7)
            # Add slight phase variation
            wave += amplitude * np.sin(h * t + h * 0.1)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_bass_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate bass-like waveform (warm, round)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Bass: fundamental + low harmonics
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 8):
            amplitude = 1.0 / (h ** 1.5)
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_pad_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate pad-like waveform (smooth, rich)."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Pad: multiple detuned oscillators
        wave = np.zeros(n_samples, dtype=np.float32)
        for h in range(1, 6):
            amplitude = 1.0 / h
            wave += amplitude * np.sin(h * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_bell_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate bell-like waveform."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Bell: inharmonic partials
        bell_ratios = [1.0, 2.4, 3.8, 5.25, 6.5, 8.2]
        wave = np.zeros(n_samples, dtype=np.float32)
        for i, ratio in enumerate(bell_ratios):
            amplitude = 1.0 / (i + 1) ** 2
            wave += amplitude * np.sin(ratio * t)
        
        wave /= np.max(np.abs(wave))
        return wave
    
    def _generate_chorus_wave(self, n_samples: int = TABLE_SIZE) -> np.ndarray:
        """Generate chorus effect waveform."""
        t = np.linspace(0, 2 * np.pi, n_samples, False)
        
        # Slight frequency modulation for chorus effect
        mod = 0.02 * np.sin(t * 0.5)
        wave = np.sin(t * (1 + mod))
        
        return wave.astype(np.float32)
    
    def _generate_all_wavetables(self):
        """Generate and store all wavetables."""
        self.WAVETABLES = {
            # Basic waveforms
            'sine': self._generate_sine_wave(),
            'triangle': self._generate_triangle_wave(),
            'sawtooth': self._generate_sawtooth_wave(),
            'square': self._generate_square_wave(),
            'pulse': self._generate_pulse_wave(),
            
            # Acoustic instrument waveforms
            'piano': self._generate_acoustic_piano(),
            'organ': self._generate_organ_wave(),
            'soft_string': self._generate_soft_string(),
            'bright_string': self._generate_bright_string(),
            'clarinet': self._generate_clarinet_wave(),
            'saxophone': self._generate_sax_wave(),
            'brass': self._generate_brass_wave(),
            'flute': self._generate_flute_wave(),
            'violin': self._generate_violin_wave(),
            'guitar': self._generate_guitar_wave(),
            'bass': self._generate_bass_wave(),
            'pad': self._generate_pad_wave(),
            'bell': self._generate_bell_wave(),
            'chorus': self._generate_chorus_wave(),
            
            # Aliases for common instruments
            'grand_piano': self._generate_acoustic_piano(),
            'nylon_guitar': self._generate_guitar_wave(),
            'steel_guitar': self._generate_guitar_wave(),
            'electric_guitar': self._generate_guitar_wave(),
            'electric_bass': self._generate_bass_wave(),
            'violin_section': self._generate_bright_string(),
            'strings_ensemble': self._generate_soft_string(),
            'trumpet': self._generate_brass_wave(),
            'trombone': self._generate_brass_wave(),
            'french_horn': self._generate_brass_wave(),
            'tuba': self._generate_brass_wave(),
            'oboe': self._generate_clarinet_wave(),
            'english_horn': self._generate_clarinet_wave(),
            'bassoon': self._generate_clarinet_wave(),
            'piccolo': self._generate_flute_wave(),
            'recorder': self._generate_flute_wave(),
            'pan_flute': self._generate_flute_wave(),
            'shakuhachi': self._generate_flute_wave(),
            'oboe': self._generate_clarinet_wave(),
            'clarinet': self._generate_clarinet_wave(),
            'bass_clarinet': self._generate_clarinet_wave(),
            
            # Synth categories
            'warm_pad': self._generate_pad_wave(),
            'polysynth': self._generate_pad_wave(),
            'space_pad': self._generate_pad_wave(),
            'metal_pad': self._generate_bell_wave(),
            'halo_pad': self._generate_chorus_wave(),
            'saw_lead': self._generate_sawtooth_wave(),
            'square_lead': self._generate_square_wave(),
            'sine_lead': self._generate_sine_wave(),
            'classic_lead': self._generate_square_wave(),
            'synth_brass_1': self._generate_brass_wave(),
            'synth_brass_2': self._generate_brass_wave(),
            'synth_strings': self._generate_soft_string(),
            'synth_bass': self._generate_bass_wave(),
            'synth_bass_1': self._generate_bass_wave(),
            'synth_bass_2': self._generate_bass_wave(),
            'synth_drum': self._generate_bass_wave(),
            'sweep_pad': self._generate_chorus_wave(),
            'rain': self._generate_chorus_wave(),
            'soundtrack': self._generate_pad_wave(),
            'crystal': self._generate_bell_wave(),
            'atmosphere': self._generate_chorus_wave(),
            
            # Ethnc/world
            'sitar': self._generate_guitar_wave(),
            'oud': self._generate_guitar_wave(),
            'bouzouki': self._generate_guitar_wave(),
            'erhu': self._generate_violin_wave(),
            'shamisen': self._generate_guitar_wave(),
            'koto': self._generate_guitar_wave(),
            'kalimba': self._generate_bell_wave(),
            'bansuri': self._generate_flute_wave(),
            'bagpipe': self._generate_pad_wave(),
            'ocarina': self._generate_flute_wave(),
            
            # Percussion
            'vibraphone': self._generate_bell_wave(),
            'marimba': self._generate_bell_wave(),
            'xylophone': self._generate_bell_wave(),
            'glockenspiel': self._generate_bell_wave(),
            'celesta': self._generate_bell_wave(),
            'tubular_bells': self._generate_bell_wave(),
            'carillon': self._generate_bell_wave(),
        }
    
    def get_wavetable(self, wavetable_type: str) -> np.ndarray:
        """Get a specific wavetable by name."""
        if wavetable_type in self.WAVETABLES:
            return self.WAVETABLES[wavetable_type]
        
        # Try to find closest match
        for key in self.WAVETABLES:
            if wavetable_type.lower() in key.lower():
                return self.WAVETABLES[key]
        
        # Default to sine
        return self.WAVETABLES['sine']
    
    def morph_wavetables(
        self,
        type1: str,
        type2: str,
        morph_position: float
    ) -> np.ndarray:
        """
        Morph between two wavetables.
        
        Args:
            type1: First wavetable name
            type2: Second wavetable name  
            morph_position: Position between 0 (type1) and 1 (type2)
        
        Returns:
            Morphed wavetable
        """
        wt1 = self.get_wavetable(type1)
        wt2 = self.get_wavetable(type2)
        
        # Ensure same size
        if len(wt1) != len(wt2):
            min_len = min(len(wt1), len(wt2))
            wt1 = wt1[:min_len]
            wt2 = wt2[:min_len]
        
        # Linear interpolation
        morph_position = max(0, min(1, morph_position))
        morphed = (1 - morph_position) * wt1 + morph_position * wt2
        
        # Normalize
        max_val = np.max(np.abs(morphed))
        if max_val > 0:
            morphed /= max_val
        
        return morphed.astype(np.float32)
    
    def generate_tone(
        self,
        freq: float,
        duration: float,
        velocity: int,
        params: Dict,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """
        Generate a tone using wavetable synthesis.
        
        Args:
            freq: Frequency in Hz
            duration: Duration in seconds
            velocity: MIDI velocity (0-127)
            params: Instrument parameters including wavetable_type
            pitch_bend: Pitch bend in semitones
            mod_wheel: Modulation wheel value (0-1)
        
        Returns:
            Generated audio waveform
        """
        SEMITONE_RATIO = 1.059463359
        
        # Apply pitch bend
        if pitch_bend != 0.0:
            freq = freq * (SEMITONE_RATIO ** pitch_bend)
        
        # Get wavetable
        wavetable_type = params.get('wavetable_type', 'sine')
        wavetable = self.get_wavetable(wavetable_type)
        
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Calculate playback rate for the wavetable
        # wavetable_freq = sample_rate / table_size * freq_ratio
        table_freq = self.sample_rate / len(wavetable)
        freq_ratio = freq / table_freq
        
        # Generate phase indices
        phase_increment = freq_ratio
        phase = np.cumsum(np.full(n_samples, phase_increment))
        phase = phase % len(wavetable)
        
        # Linear interpolation between wavetable samples
        phase_low = phase.astype(np.int32)
        phase_high = (phase_low + 1) % len(wavetable)
        frac = phase - phase_low
        
        audio = (1 - frac) * wavetable[phase_low] + frac * wavetable[phase_high]
        
        # Apply ADSR envelope
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        audio *= envelope[:n_samples] if len(envelope) > n_samples else np.pad(
            envelope, (0, n_samples - len(envelope))
        )
        
        # Apply velocity
        audio *= (velocity / 127.0)
        
        # Apply mod wheel (subtle vibrato)
        if mod_wheel > 0:
            vibrato = 0.01 * mod_wheel * np.sin(2 * np.pi * 5 * t)
            audio *= (1 + vibrato)
        
        return audio.astype(np.float32)
    
    def _generate_adsr_envelope(
        self,
        duration: float,
        velocity: int,
        params: Dict
    ) -> np.ndarray:
        """Generate ADSR envelope."""
        total_samples = int(self.sample_rate * duration)
        
        if total_samples <= 0:
            return np.array([])
        
        attack_time = params.get('attack_time', 0.01)
        decay_time = params.get('decay_time', 0.1)
        sustain_level = params.get('sustain_level', 0.7)
        release_time = params.get('release_time', 0.2)
        
        # Scale based on velocity
        attack_time *= (1.5 if velocity < 80 else 1.0)
        
        attack_samples = min(int(attack_time * self.sample_rate), total_samples // 2)
        decay_samples = min(int(decay_time * self.sample_rate), total_samples - attack_samples)
        release_samples = min(int(release_time * self.sample_rate), total_samples - attack_samples - decay_samples)
        
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples
        if sustain_samples < 0:
            release_samples = total_samples - attack_samples - decay_samples
            sustain_samples = 0
        
        envelope = np.zeros(total_samples)
        
        # Attack
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay
        decay_start = attack_samples
        decay_end = decay_start + decay_samples
        if decay_samples > 0:
            envelope[decay_start:decay_end] = np.linspace(1, sustain_level, decay_samples)
        
        # Sustain
        sustain_end = decay_end + sustain_samples
        if sustain_samples > 0:
            envelope[decay_end:sustain_end] = sustain_level
        
        # Release
        if release_samples > 0 and sustain_end < total_samples:
            envelope[sustain_end:] = np.linspace(sustain_level, 0, 
                                                   min(total_samples - sustain_end, release_samples))
        
        return envelope


# Map instrument names to recommended wavetables
INSTRUMENT_WAVETABLE_MAP: Dict[str, str] = {
    # Pianos
    'piano': 'piano',
    'grand_piano': 'piano',
    'stage_piano': 'piano',
    'electric_piano': 'organ',
    'honkytonk_piano': 'piano',
    'clavinet': 'sawtooth',
    
    # Organs
    'hammond_organ': 'organ',
    'perc_organ': 'organ',
    'rock_organ': 'organ',
    'church_organ': 'organ',
    'reed_organ': 'organ',
    
    # Strings
    'violin': 'violin',
    'viola': 'violin',
    'cello': 'violin',
    'contrabass': 'bass',
    'violin_section': 'bright_string',
    'strings_ensemble': 'soft_string',
    'pizzicato_strings': 'guitar',
    'synth_strings': 'soft_string',
    'slow_strings': 'soft_string',
    '60s_strings': 'soft_string',
    
    # Guitars
    'nylon_guitar': 'guitar',
    'steel_guitar': 'guitar',
    'electric_guitar': 'guitar',
    'clean_guitar': 'guitar',
    'overdrive_guitar': 'guitar',
    'distortion_guitar': 'sawtooth',
    'jazz_guitar': 'guitar',
    'muted_guitar': 'guitar',
    'pedal_steel_guitar': 'guitar',
    'synth_guitar': 'sawtooth',
    
    # Basses
    'bass_guitar': 'bass',
    'electric_bass': 'bass',
    'fretless_bass': 'bass',
    'slap_bass': 'bass',
    'synth_bass': 'bass',
    'synth_bass_1': 'bass',
    'synth_bass_2': 'bass',
    
    # Brass
    'trumpet': 'brass',
    'piccolo_trumpet': 'brass',
    'flugelhorn': 'brass',
    'french_horn': 'brass',
    'trombone': 'brass',
    'euphonium': 'brass',
    'tuba': 'brass',
    'brass_section': 'brass',
    'synth_brass_1': 'brass',
    'synth_brass_2': 'brass',
    
    # Woodwinds
    'piccolo': 'flute',
    'flute': 'flute',
    'alto_flute': 'flute',
    'bass_flute': 'flute',
    'oboe': 'clarinet',
    'english_horn': 'clarinet',
    'clarinet': 'clarinet',
    'bass_clarinet': 'clarinet',
    'bassoon': 'clarinet',
    'contrabassoon': 'clarinet',
    'recorder': 'flute',
    'pan_flute': 'flute',
    'shakuhachi': 'flute',
    
    # Saxes
    'soprano_sax': 'saxophone',
    'alto_sax': 'saxophone',
    'tenor_sax': 'saxophone',
    'baritone_sax': 'saxophone',
    'saxophone': 'saxophone',
    
    # Synth Leads
    'saw_lead': 'sawtooth',
    'square_lead': 'square',
    'sine_lead': 'sine',
    'classic_lead': 'square',
    'doc_lead': 'sawtooth',
    'unison_lead': 'sawtooth',
    'four_op_lead': 'sawtooth',
    'chisel_lead': 'square',
    
    # Synth Pads
    'warm_pad': 'pad',
    'polysynth': 'pad',
    'space_pad': 'pad',
    'bow_pad': 'soft_string',
    'metal_pad': 'bell',
    'halo_pad': 'chorus',
    'sweep_pad': 'chorus',
    'rain': 'chorus',
    'soundtrack': 'pad',
    'crystal': 'bell',
    'atmosphere': 'chorus',
    'bright': 'sawtooth',
    
    # Chromatic Percussion
    'vibraphone': 'bell',
    'marimba': 'bell',
    'xylophone': 'bell',
    'glockenspiel': 'bell',
    'celesta': 'bell',
    'tubular_bells': 'bell',
    'carillon': 'bell',
    'dulcimer': 'bell',
    'santur': 'bell',
    
    # Ethnic/World
    'sitar': 'guitar',
    'oud': 'guitar',
    'bouzouki': 'guitar',
    'erhu': 'violin',
    'shamisen': 'guitar',
    'koto': 'guitar',
    'taiko': 'bell',
    'shamisen_JP': 'guitar',
    'kalimba': 'bell',
    'bansuri': 'flute',
    'bagpipe': 'pad',
    'ocarina': 'flute',
    
    # Percussive
    'taiko_drum': 'bell',
    'melodic_tom': 'bell',
    'synth_drum': 'bass',
    'reverse_cymbal': 'chorus',
    
    # Additional
    'harp': 'bell',
    'mandolin': 'guitar',
    'ukulele': 'guitar',
    'banjo': 'guitar',
}


def get_wavetable_for_instrument(instrument_name: str) -> str:
    """Get the recommended wavetable for an instrument."""
    return INSTRUMENT_WAVETABLE_MAP.get(instrument_name, 'sine')
