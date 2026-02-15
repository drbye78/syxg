"""
NRPN Mapper for Yamaha S.Art2 articulations and Genos2 voice bank mapping.
"""

from typing import Dict, Tuple, Optional


def midi_note_to_frequency(note: int) -> float:
    """Convert MIDI note number to frequency (A4 = 440Hz at note 69)."""
    SEMITONE_RATIO = 1.059463359
    return 440.0 * (SEMITONE_RATIO ** (note - 69))


class YamahaNRPNMapper:
    """
    Enhanced NRPN mapper for Yamaha S.Art2 articulations.
    Properly handles MSB/LSB combinations without duplicates.
    """
    
    def __init__(self):
        # Use a more specific key structure to avoid duplicates
        # Format: (msb, lsb, category) -> articulation_name
        self.nrpn_to_articulation: Dict[Tuple[int, int, str], str] = {
            # Common articulations (MSB 1)
            (1, 0, 'common'): 'normal',
            (1, 1, 'common'): 'legato',
            (1, 2, 'common'): 'staccato',
            (1, 3, 'common'): 'bend',
            (1, 4, 'common'): 'vibrato',
            (1, 5, 'common'): 'breath',
            (1, 6, 'common'): 'glissando',
            (1, 7, 'common'): 'growl',
            (1, 8, 'common'): 'flutter',
            (1, 9, 'common'): 'trill',
            (1, 10, 'common'): 'pizzicato',
            (1, 11, 'common'): 'grace',
            (1, 12, 'common'): 'shake',
            (1, 13, 'common'): 'fall',
            (1, 14, 'common'): 'doit',
            (1, 15, 'common'): 'tongue_slap',
            (1, 16, 'common'): 'harmonics',
            (1, 17, 'common'): 'hammer_on',
            (1, 18, 'common'): 'pull_off',
            (1, 19, 'common'): 'key_off',
            (1, 20, 'common'): 'marcato',
            (1, 21, 'common'): 'detache',
            (1, 22, 'common'): 'sul_ponticello',
            (1, 23, 'common'): 'scoop',
            (1, 24, 'common'): 'rip',
            (1, 25, 'common'): 'portamento',
            (1, 26, 'common'): 'swell',
            (1, 27, 'common'): 'accented',
            (1, 28, 'common'): 'bow_up',
            (1, 29, 'common'): 'bow_down',
            (1, 30, 'common'): 'col_legno',
            (1, 31, 'common'): 'up_bend',
            (1, 32, 'common'): 'down_bend',
            (1, 33, 'common'): 'smear',
            (1, 34, 'common'): 'flip',
            (1, 35, 'common'): 'straight',
            
            # Wind-specific (MSB 2)
            (2, 0, 'wind'): 'growl_wind',
            (2, 1, 'wind'): 'flutter_wind',
            (2, 2, 'wind'): 'tongue_slap_wind',
            (2, 3, 'wind'): 'smear_wind',
            (2, 4, 'wind'): 'flip_wind',
            (2, 5, 'wind'): 'scoop_wind',
            (2, 6, 'wind'): 'rip_wind',
            
            # Strings-specific (MSB 3)
            (3, 0, 'strings'): 'pizzicato_strings',
            (3, 1, 'strings'): 'harmonics_strings',
            (3, 2, 'strings'): 'sul_ponticello_strings',
            (3, 3, 'strings'): 'bow_up_strings',
            (3, 4, 'strings'): 'bow_down_strings',
            (3, 5, 'strings'): 'col_legno_strings',
            (3, 6, 'strings'): 'portamento_strings',
            
            # Guitar-specific (MSB 4)
            (4, 0, 'guitar'): 'hammer_on_guitar',
            (4, 1, 'guitar'): 'pull_off_guitar',
            (4, 2, 'guitar'): 'harmonics_guitar',
        }
        
        # Simplified lookup for backward compatibility
        self._simplified_map: Dict[Tuple[int, int], str] = {}
        for (msb, lsb, _), art in self.nrpn_to_articulation.items():
            key = (msb, lsb)
            # Only add if not already present (common articulations take priority)
            if key not in self._simplified_map:
                self._simplified_map[key] = art
    
    def get_articulation(self, msb: int, lsb: int, category: str = 'common') -> str:
        """Get articulation from NRPN MSB/LSB values."""
        # Validate input range
        msb = max(0, min(127, msb))
        lsb = max(0, min(127, lsb))
        
        # Try category-specific lookup first
        key = (msb, lsb, category)
        if key in self.nrpn_to_articulation:
            return self.nrpn_to_articulation[key]
        
        # Fall back to simplified map
        return self._simplified_map.get((msb, lsb), 'normal')


class Genos2VoiceBank:
    """
    Yamaha Genos2 Voice Bank Mapping.
    Maps Bank Select (MSB/LSB) + Program Change to instrument names.
    Based on Yamaha XG/GM standard with Genos2-specific additions.
    """
    
    # Bank MSB numbers (CC 0)
    BANK_PIANO = 0
    BANK_E_PIANO = 1
    BANK_ORGAN = 2
    BANK_ACCORDION = 3
    BANK_GUITAR = 4
    BANK_BASS = 5
    BANK_STRINGS = 6
    BANK_BRASS = 7
    BANK_REED = 8
    BANK_PIPE = 9
    BANK_SYNTH_LEAD = 10
    BANK_SYNTH_PAD = 11
    BANK_SYNTH_EFFECT = 12
    BANK_WORLd = 13
    BANK_PERCUSSION = 14
    BANK_SFX = 15
    BANK_SART_SOLO = 16      # S.Art2 Solo instruments
    BANK_SART_ENSEMBLE = 17  # S.Art2 Ensemble
    BANK_LIVE = 18            # Live! sounds
    BANK_SWEET = 19          # Sweet! sounds
    BANK_COOL = 20           # Cool! sounds
    
    # Voice bank mapping: (MSB, LSB, Program) -> instrument_name
    # Maps Yamaha Genos2 voice numbers to internal instrument names
    VOICE_MAP: Dict[Tuple[int, int, int], str] = {
        # === PIANO (MSB 0) ===
        (0, 0, 0): 'grand_piano',
        (0, 0, 1): 'grand_piano',
        (0, 0, 2): 'piano',
        (0, 0, 3): 'honkytonk_piano',
        (0, 0, 4): 'electric_piano',
        (0, 0, 5): 'electric_piano',
        (0, 0, 6): 'electric_piano',
        (0, 0, 7): 'clavinet',
        
        # === E.PIANO (MSB 1) ===
        (1, 0, 0): 'electric_piano',
        (1, 0, 1): 'electric_piano',
        (1, 0, 2): 'electric_piano',
        (1, 0, 3): 'electric_piano',
        
        # === ORGAN (MSB 2) ===
        (2, 0, 0): 'hammond_organ',
        (2, 0, 1): 'rock_organ',
        (2, 0, 2): 'church_organ',
        (2, 0, 3): 'reed_organ',
        (2, 0, 4): 'hammond_organ',
        
        # === S.ART2 SOLO (MSB 16) - Genos2 Super Articulation Solo ===
        (16, 0, 0): 'saxophone',
        (16, 0, 1): 'tenor_sax',
        (16, 0, 2): 'alto_sax',
        (16, 0, 3): 'soprano_sax',
        (16, 0, 4): 'baritone_sax',
        (16, 0, 5): 'trumpet',
        (16, 0, 6): 'trombone',
        (16, 0, 7): 'flugelhorn',
        (16, 0, 8): 'french_horn',
        (16, 0, 9): 'tuba',
        (16, 0, 10): 'flute',
        (16, 0, 11): 'clarinet',
        (16, 0, 12): 'oboe',
        (16, 0, 13): 'bassoon',
        (16, 0, 14): 'piccolo',
        (16, 0, 15): 'recorder',
        (16, 0, 16): 'violin',
        (16, 0, 17): 'viola',
        (16, 0, 18): 'cello',
        (16, 0, 19): 'contrabass',
        (16, 0, 20): 'guitar',
        (16, 0, 21): 'nylon_guitar',
        (16, 0, 22): 'steel_guitar',
        (16, 0, 23): 'electric_guitar',
        (16, 0, 24): 'bass_guitar',
        
        # === S.ART2 ENSEMBLE (MSB 17) ===
        (17, 0, 0): 'strings_ensemble',
        (17, 0, 1): 'violin_section',
        (17, 0, 2): 'brass_section',
        
        # === GUITAR (MSB 4) ===
        (4, 0, 0): 'nylon_guitar',
        (4, 0, 1): 'steel_guitar',
        (4, 0, 2): 'electric_guitar',
        (4, 0, 3): 'clean_guitar',
        (4, 0, 4): 'overdrive_guitar',
        (4, 0, 5): 'distortion_guitar',
        (4, 0, 6): 'guitar',
        (4, 0, 7): 'jazz_guitar',
        
        # === BASS (MSB 5) ===
        (5, 0, 0): 'bass_guitar',
        (5, 0, 1): 'electric_bass',
        (5, 0, 2): 'fretless_bass',
        (5, 0, 3): 'slap_bass',
        (5, 0, 4): 'synth_bass',
        
        # === STRINGS (MSB 6) ===
        (6, 0, 0): 'strings_ensemble',
        (6, 0, 1): 'violin_section',
        (6, 0, 2): 'violin',
        (6, 0, 3): 'viola',
        (6, 0, 4): 'cello',
        (6, 0, 5): 'contrabass',
        (6, 0, 6): 'pizzicato_strings',
        (6, 0, 7): 'synth_strings',
        
        # === BRASS (MSB 7) ===
        (7, 0, 0): 'trumpet',
        (7, 0, 1): 'trombone',
        (7, 0, 2): 'french_horn',
        (7, 0, 3): 'tuba',
        (7, 0, 4): 'brass_section',
        (7, 0, 5): 'synth_brass_1',
        
        # === REED (MSB 8) ===
        (8, 0, 0): 'saxophone',
        (8, 0, 1): 'clarinet',
        (8, 0, 2): 'oboe',
        (8, 0, 3): 'bassoon',
        (8, 0, 4): 'english_horn',
        
        # === PIPE (MSB 9) ===
        (9, 0, 0): 'flute',
        (9, 0, 1): 'piccolo',
        (9, 0, 2): 'recorder',
        (9, 0, 3): 'pan_flute',
        (9, 0, 4): 'shakuhachi',
        (9, 0, 5): 'ocarina',
        
        # === SYNTH LEAD (MSB 10) ===
        (10, 0, 0): 'saw_lead',
        (10, 0, 1): 'square_lead',
        (10, 0, 2): 'sine_lead',
        (10, 0, 3): 'classic_lead',
        (10, 0, 4): 'unison_lead',
        
        # === SYNTH PAD (MSB 11) ===
        (11, 0, 0): 'warm_pad',
        (11, 0, 1): 'polysynth',
        (11, 0, 2): 'space_pad',
        (11, 0, 3): 'halo_pad',
        (11, 0, 4): 'metal_pad',
        
        # === ETHNIC/WORLD (MSB 13) ===
        (13, 0, 0): 'sitar',
        (13, 0, 1): 'banjo',
        (13, 0, 2): 'mandolin',
        (13, 0, 3): 'bouzouki',
        (13, 0, 4): 'erhu',
        (13, 0, 5): 'shamisen',
        (13, 0, 6): 'koto',
        (13, 0, 7): 'kalimba',
        (13, 0, 8): 'bansuri',
        (13, 0, 9): 'bagpipe',
        
        # === PERCUSSION (MSB 14) ===
        (14, 0, 0): 'vibraphone',
        (14, 0, 1): 'marimba',
        (14, 0, 2): 'xylophone',
        (14, 0, 3): 'glockenspiel',
        (14, 0, 4): 'celesta',
        (14, 0, 5): 'tubular_bells',
        
        # === LIVE! (MSB 18) ===
        (18, 0, 0): 'grand_piano',
        (18, 0, 1): 'saxophone',
        (18, 0, 2): 'trumpet',
        (18, 0, 3): 'violin',
        (18, 0, 4): 'guitar',
    }
    
    @classmethod
    def get_instrument(cls, msb: int, lsb: int, program: int) -> Optional[str]:
        """Get instrument name from bank MSB, LSB, and program number."""
        key = (msb, lsb, program)
        return cls.VOICE_MAP.get(key)
    
    @classmethod
    def get_bank_info(cls, msb: int) -> str:
        """Get bank name from MSB number."""
        bank_names = {
            0: "Piano",
            1: "E.Piano",
            2: "Organ",
            3: "Accordion",
            4: "Guitar",
            5: "Bass",
            6: "Strings",
            7: "Brass",
            8: "Reed",
            9: "Pipe",
            10: "Synth Lead",
            11: "Synth Pad",
            12: "Synth Effect",
            13: "World",
            14: "Percussion",
            15: "SFX",
            16: "S.Art2 Solo",
            17: "S.Art2 Ensemble",
            18: "Live!",
            19: "Sweet!",
            20: "Cool!",
        }
        return bank_names.get(msb, f"Bank {msb}")
