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
        (1, 0): "normal",
        (1, 1): "legato",
        (1, 2): "staccato",
        (1, 3): "bend",
        (1, 4): "vibrato",
        (1, 5): "breath",
        (1, 6): "glissando",
        (1, 7): "growl",
        (1, 8): "flutter",
        (1, 9): "trill",
        (1, 10): "pizzicato",
        (1, 11): "grace",
        (1, 12): "shake",
        (1, 13): "fall",
        (1, 14): "doit",
        (1, 15): "tongue_slap",
        (1, 16): "harmonics",
        (1, 17): "hammer_on",
        (1, 18): "pull_off",
        (1, 19): "key_off",
        (1, 20): "marcato",
        (1, 21): "detache",
        (1, 22): "sul_ponticello",
        (1, 23): "scoop",
        (1, 24): "rip",
        (1, 25): "portamento",
        (1, 26): "swell",
        (1, 27): "accented",
        (1, 28): "bow_up",
        (1, 29): "bow_down",
        (1, 30): "col_legno",
        (1, 31): "up_bend",
        (1, 32): "down_bend",
        (1, 33): "smear",
        (1, 34): "flip",
        (1, 35): "straight",
        # Dynamics (MSB 2)
        (2, 0): "ppp",
        (2, 1): "pp",
        (2, 2): "p",
        (2, 3): "mp",
        (2, 4): "mf",
        (2, 5): "f",
        (2, 6): "ff",
        (2, 7): "fff",
        (2, 8): "crescendo",
        (2, 9): "diminuendo",
        (2, 10): "sfz",
        (2, 11): "rfz",
        # Wind techniques (MSB 3)
        (3, 0): "growl_wind",
        (3, 1): "flutter_wind",
        (3, 2): "tongue_slap_wind",
        (3, 3): "smear_wind",
        (3, 4): "flip_wind",
        (3, 5): "scoop_wind",
        (3, 6): "rip_wind",
        (3, 7): "double_tongue",
        (3, 8): "triple_tongue",
        # String techniques (MSB 4)
        (4, 0): "pizzicato_strings",
        (4, 1): "harmonics_strings",
        (4, 2): "sul_ponticello_strings",
        (4, 3): "bow_up_strings",
        (4, 4): "bow_down_strings",
        (4, 5): "col_legno_strings",
        (4, 6): "portamento_strings",
        (4, 7): "spiccato",
        (4, 8): "tremolando",
        # Guitar techniques (MSB 5) - Extended to 25 articulations
        (5, 0): "hammer_on_guitar",
        (5, 1): "pull_off_guitar",
        (5, 2): "harmonics_guitar",
        (5, 3): "palm_mute",
        (5, 4): "tap",
        (5, 5): "slide_up",
        (5, 6): "slide_down",
        (5, 7): "bend",
        # Additional guitar articulations
        (5, 8): "slide_up_short",
        (5, 9): "slide_up_long",
        (5, 10): "slide_down_short",
        (5, 11): "slide_down_long",
        (5, 12): "bend_quarter",
        (5, 13): "bend_half",
        (5, 14): "bend_full",
        (5, 15): "bend_1_5",
        (5, 16): "vibrato_shallow",
        (5, 17): "vibrato_deep",
        (5, 18): "vibrato_wide",
        (5, 19): "harmonic_natural_5th",
        (5, 20): "harmonic_natural_7th",
        (5, 21): "harmonic_artificial_3rd",
        (5, 22): "harmonic_artificial_5th",
        (5, 23): "palm_mute_light",
        (5, 24): "palm_mute_heavy",
        # Brass techniques (MSB 6) - Extended to 20 articulations
        (6, 0): "muted_brass",
        (6, 1): "cup_mute",
        (6, 2): "harmon_mute",
        (6, 3): "stopped",
        (6, 4): "scoop_brass",
        (6, 5): "lip_trill",
        # Additional brass articulations
        (6, 6): "shake_brass",
        (6, 7): "drop_brass",
        (6, 8): "doit_brass",
        (6, 9): "fall_brass",
        (6, 10): "scoop_brass_long",
        (6, 11): "plop_brass",
        (6, 12): "lift_brass",
        (6, 13): "smooth_fall_brass",
        (6, 14): "rough_fall_brass",
        (6, 15): "long_fall_brass",
        (6, 16): "straight_mute",
        (6, 17): "plunger_mute",
        (6, 18): "bucket_mute",
        (6, 19): "hat_mute",
        # Strings - Bow techniques (MSB 7) - 22 articulations
        (7, 0): "pizzicato_strings",
        (7, 1): "harmonics_strings",
        (7, 2): "sul_ponticello_strings",
        (7, 3): "bow_up_strings",
        (7, 4): "bow_down_strings",
        (7, 5): "col_legno_strings",
        (7, 6): "portamento_strings",
        (7, 7): "spiccato",
        (7, 8): "tremolando",
        (7, 9): "sautille",
        (7, 10): "martele",
        (7, 11): "ricochet",
        (7, 12): "flautando",
        (7, 13): "sul_g",
        (7, 14): "con_sordino",
        (7, 15): "senza_sordino",
        (7, 16): "tremolo",
        (7, 17): "tremolo_sordino",
        (7, 18): "portamento_fast",
        (7, 19): "portamento_slow",
        (7, 20): "sul_tasto",
        (7, 21): "punto",
        # Strings - Pluck techniques (MSB 8) - 15 articulations
        (8, 0): "pizzicato_snap",
        (8, 1): "pizzicato_left",
        (8, 2): "pizzicato_right",
        (8, 3): "pizzicato_chord",
        (8, 4): "barto_k",
        (8, 5): "gyro_pizz",
        (8, 6): "harmonic_pizz",
        (8, 7): "muted_pizz",
        (8, 8): "vibrato_pizz",
        (8, 9): "gliss_pizz",
        (8, 10): "thumb_pizz",
        (8, 11): "slap_pizz",
        (8, 12): "pop_pizz",
        (8, 13): "tap_pizz",
        (8, 14): "scratch_pizz",
        # Guitar techniques (MSB 9) - Extended to 25 articulations
        (9, 0): "slide_up_gtr",
        (9, 1): "slide_down_gtr",
        (9, 2): "bend_gtr",
        (9, 3): "bend_release_gtr",
        (9, 4): "pre_bend",
        (9, 5): "harmonics_natural",
        (9, 6): "harmonics_artificial",
        (9, 7): "harmonics_pinch",
        (9, 8): "tapping_gtr",
        (9, 9): "slap_gtr",
        (9, 10): "pop_gtr",
        (9, 11): "mute_gtr",
        (9, 12): "cut_noise",
        (9, 13): "fret_noise",
        (9, 14): "string_noise",
        (9, 15): "body_hit_gtr",
        (9, 16): "hammer_on_gtr",
        (9, 17): "pull_off_gtr",
        (9, 18): "vibrato_gtr",
        (9, 19): "wide_vibrato",
        (9, 20): "palm_mute_gtr",
        (9, 21): "harmonic_tap",
        (9, 22): "tremolo_gtr",
        (9, 23): "arpeggio_up",
        (9, 24): "arpeggio_down",
        # Vocal techniques (MSB 10) - 20 articulations
        (10, 0): "vocal_breath",
        (10, 1): "vocal_attack",
        (10, 2): "vocal_fry",
        (10, 3): "falsetto",
        (10, 4): "chest_voice",
        (10, 5): "head_voice",
        (10, 6): "mixed_voice",
        (10, 7): "whisper",
        (10, 8): "shout",
        (10, 9): "scream",
        (10, 10): "growl_vocal",
        (10, 11): "vibrato_vocal",
        (10, 12): "straight_tone",
        (10, 13): "scoop_vocal",
        (10, 14): "fall_vocal",
        (10, 15): "turn_vocal",
        (10, 16): "mordent_vocal",
        (10, 17): "trill_vocal",
        (10, 18): "glissando_vocal",
        (10, 19): "portamento_vocal",
        # Synth techniques (MSB 11) - 15 articulations
        (11, 0): "synth_attack",
        (11, 1): "synth_decay",
        (11, 2): "synth_sustain",
        (11, 3): "synth_release",
        (11, 4): "filter_sweep",
        (11, 5): "filter_snap",
        (11, 6): "lfo_sync",
        (11, 7): "lfo_free",
        (11, 8): "glide",
        (11, 9): "legato_synth",
        (11, 10): "staccato_synth",
        (11, 11): "trig_synth",
        (11, 12): "gate_synth",
        (11, 13): "accent_synth",
        (11, 14): "tie_synth",
        # Percussion techniques (MSB 12) - 20 articulations
        (12, 0): "perc_attack",
        (12, 1): "perc_decay",
        (12, 2): "rim_shot",
        (12, 3): "cross_stick",
        (12, 4): "buzz_roll",
        (12, 5): "press_roll",
        (12, 6): "flam",
        (12, 7): "drag",
        (12, 8): "ruff",
        (12, 9): "diddle",
        (12, 10): "bounce",
        (12, 11): "dead_stroke",
        (12, 12): "tap_perc",
        (12, 13): "slap_perc",
        (12, 14): "pop_perc",
        (12, 15): "mute_perc",
        (12, 16): "open_perc",
        (12, 17): "closed_perc",
        (12, 18): "choke_perc",
        (12, 19): "sustain_perc",
        # Ethnic techniques (MSB 13) - 18 articulations
        (13, 0): "ethnic_attack",
        (13, 1): "ethnic_decay",
        (13, 2): "bend_ethnic",
        (13, 3): "vibrato_ethnic",
        (13, 4): "tremolo_ethnic",
        (13, 5): "harmonic_ethnic",
        (13, 6): "percussive_ethnic",
        (13, 7): "breath_ethnic",
        (13, 8): "slide_ethnic",
        (13, 9): "gliss_ethnic",
        (13, 10): "trill_ethnic",
        (13, 11): "mordent_ethnic",
        (13, 12): "turn_ethnic",
        (13, 13): "grace_ethnic",
        (13, 14): "accent_ethnic",
        (13, 15): "staccato_ethnic",
        (13, 16): "tenuto_ethnic",
        (13, 17): "marcato_ethnic",
        # Effects techniques (MSB 14) - 12 articulations
        (14, 0): "fx_sweep_up",
        (14, 1): "fx_sweep_down",
        (14, 2): "fx_noise",
        (14, 3): "fx_hit",
        (14, 4): "fx_rise",
        (14, 5): "fx_fall",
        (14, 6): "fx_boom",
        (14, 7): "fx_crash",
        (14, 8): "fx_slam",
        (14, 9): "fx_scrape",
        (14, 10): "fx_click",
        (14, 11): "fx_pop",
        # Piano techniques (MSB 15) - 20 articulations
        (15, 0): "soft_pedal",
        (15, 1): "sustain_pedal",
        (15, 2): "sostenuto_pedal",
        (15, 3): "una_corda",
        (15, 4): "tre_corde",
        (15, 5): "key_off_early",
        (15, 6): "key_off_late",
        (15, 7): "key_off_noise",
        (15, 8): "duplex_scale",
        (15, 9): "string_resonance",
        (15, 10): "damper_noise",
        (15, 11): "hammer_noise",
        (15, 12): "pedal_up",
        (15, 13): "pedal_down",
        (15, 14): "soft_lift",
        (15, 15): "sustain_lift",
        (15, 16): "agoge",
        (15, 17): "portamento_piano",
        (15, 18): "legato_pedal",
        (15, 19): "mute_staccato",
        # Bass techniques (MSB 16) - 20 articulations
        (16, 0): "finger_style",
        (16, 1): "pick_style",
        (16, 2): "slap_bass",
        (16, 3): "pop_bass",
        (16, 4): "muted_bass",
        (16, 5): "open_string",
        (16, 6): "fret_noise_bass",
        (16, 7): "harmonic_bass",
        (16, 8): "glissando_bass",
        (16, 9): "slide_bass",
        (16, 10): "dead_note",
        (16, 11): "neck_position",
        (16, 12): "bridge_position",
        (16, 13): "pizzicato_bass",
        (16, 14): "tremolo_bass",
        (16, 15): "tap_bass",
        (16, 16): "raking",
        (16, 17): "semi_tone_harm",
        (16, 18): "pedal_point",
        (16, 19): "sub_bass",
        # Organ techniques (MSB 17) - 15 articulations
        (17, 0): "drawbar_organ",
        (17, 1): "percussive_organ",
        (17, 2): "click_organ",
        (17, 3): "rotary_organ",
        (17, 4): "leslie_slow",
        (17, 5): "leslie_fast",
        (17, 6): "vibrato_organ",
        (17, 7): "chorus_organ",
        (17, 8): "reverb_organ",
        (17, 9): " Organ_soft",
        (17, 10): "Organ_loud",
        (17, 11): "Organ_gospel",
        (17, 12): " Organ_jazzy",
        (17, 13): "Organ_rock",
        (17, 14): " Organ_full",
        # Ethnic World instruments (MSB 18) - 20 articulations
        (18, 0): "sitar_attack",
        (18, 1): "sitar_pluck",
        (18, 2): "sitar_bend",
        (18, 3): "tanpura_drone",
        (18, 4): "tabla_tom",
        (18, 5): "tabla_ti",
        (18, 6): "tabla_na",
        (18, 7): "tabla_ke",
        (18, 8): "dholak_roll",
        (18, 9): "dholak_tak",
        (18, 10): "didgeridoo_drone",
        (18, 11): "didgeridoo_rit",
        (18, 12): "berimbau_roll",
        (18, 13): "berimbau_clic",
        (18, 14): "kalimba_pluck",
        (18, 15): "kora_pluck",
        (18, 16): "guzheng_ply",
        (18, 17): "guzheng_gliss",
        (18, 18): "shakuhachi_breath",
        (18, 19): "shakuhachi_flip",
    }

    # Yamaha S.Art2 SYSEX manufacturer ID
    YAMAHA_SYSEX_ID = 0x43

    def __init__(self):
        """Initialize the articulation controller."""
        self.current_articulation = "normal"
        self.current_category = "common"
        self.nrpn_msb = 0
        self.nrpn_lsb = 0

        # Compatibility mode (sart2, xg, gs)
        self.compatibility_mode = "sart2"

        # Articulation parameters that can be controlled
        self.articulation_params: Dict[str, Any] = {
            "legato": {"blend": 0.5, "transition_time": 0.05},
            "staccato": {"note_length": 0.1},
            "vibrato": {"rate": 5.0, "depth": 0.05},
            "trill": {"interval": 2, "rate": 6.0},
            "bend": {"amount": 1.0, "direction": "up"},
            "pizzicato": {"decay_rate": 8.0},
            "glissando": {"target_interval": 7, "speed": 0.2},
            "growl": {"mod_freq": 25.0, "depth": 0.25},
            "flutter": {"mod_freq": 12.0, "depth": 0.15},
            "harmonics": {"harmonic": 2, "level": 0.35},
            "swell": {"attack": 0.1, "release": 0.2},
            "crescendo": {"target_level": 1.0, "duration": 1.0},
            "diminuendo": {"target_level": 0.1, "duration": 1.0},
        }

        # XG NRPN mapping (Yamaha XG standard)
        self.xg_nrpn_map: Dict[Tuple[int, int], str] = {
            # XG MSB 3 (Basic Parameters)
            (3, 16): "vibrato",  # Vibrato rate
            (3, 17): "vibrato",  # Vibrato depth
            (3, 18): "vibrato",  # Vibrato delay
            (3, 20): "filter",  # Brightness (filter cutoff)
            (3, 21): "envelope",  # Attack time
            (3, 22): "envelope",  # Decay time
            (3, 23): "envelope",  # Release time
            # XG MSB 4 (Controller Assignments)
            (4, 0): "normal",  # Default
            (4, 1): "legato",  # Legato
            (4, 2): "staccato",  # Staccato
            (4, 3): "marcato",  # Marcato
            (4, 4): "tenuto",  # Tenuto
        }

        # GS NRPN mapping (Roland GS standard)
        self.gs_nrpn_map: Dict[Tuple[int, int], str] = {
            # GS NRPN for articulation
            (1, 0): "normal",
            (1, 1): "legato",
            (1, 2): "staccato",
            (1, 3): "marcato",
            (1, 4): "tenuto",
            (1, 5): "pizzicato",
            (1, 6): "spiccato",
            (1, 7): "tremolo",
            # GS NRPN for drum instruments
            (2, 0): "normal",  # Drum instrument select
        }

        # Callback for articulation changes
        self._on_articulation_change: Optional[Callable[[str], None]] = None

        # Import NRPN parameter controller
        from .nrpn import NRPNParameterController

        self.param_controller = NRPNParameterController()

        # SYSEX command definitions (Genos2 compatible)
        self.SYSEX_COMMANDS = {
            0x10: "articulation_set",
            0x11: "articulation_param",
            0x12: "articulation_release",
            0x13: "articulation_query",
            0x14: "articulation_chain",
            0x15: "bulk_dump",
            0x16: "bulk_load",
            0x17: "system_config",
        }

    def set_compatibility_mode(self, mode: str) -> None:
        """
        Set compatibility mode.

        Args:
            mode: Compatibility mode ('sart2', 'xg', 'gs')
        """
        if mode in ("sart2", "xg", "gs"):
            self.compatibility_mode = mode

    def get_compatibility_mode(self) -> str:
        """Get current compatibility mode."""
        return self.compatibility_mode

    def process_nrpn(self, msb: int, lsb: int) -> str:
        """
        Process NRPN message and return articulation name.

        Supports S.Art2, XG, and GS NRPN mappings based on compatibility mode.

        Args:
            msb: NRPN MSB (parameter number high byte)
            lsb: NRPN LSB (parameter number low byte)

        Returns:
            Articulation name string
        """
        self.nrpn_msb = msb
        self.nrpn_lsb = lsb

        # Look up articulation based on compatibility mode
        if self.compatibility_mode == "xg":
            # Use XG NRPN mapping
            articulation = self.xg_nrpn_map.get((msb, lsb), "normal")
        elif self.compatibility_mode == "gs":
            # Use GS NRPN mapping
            articulation = self.gs_nrpn_map.get((msb, lsb), "normal")
        else:
            # Use S.Art2 NRPN mapping (default)
            articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")

        if articulation != self.current_articulation:
            self.current_articulation = articulation
            if self._on_articulation_change:
                self._on_articulation_change(articulation)
            logger.debug(
                f"Articulation changed to: {articulation} ({self.compatibility_mode})"
            )

        return articulation

    def process_sysex(self, sysex: bytes) -> Optional[Dict[str, Any]]:
        """
        Process Yamaha S.Art2 SYSEX message with full Genos2 compatibility.

        Supported SYSEX formats:

        1. Articulation Set (0x10):
           F0 43 10 4C 10 [channel] [art_msb] [art_lsb] F7

        2. Parameter Set (0x11):
           F0 43 10 4C 11 [channel] [param_msb] [param_lsb] [value_msb] [value_lsb] F7

        3. Articulation Release (0x12):
           F0 43 10 4C 12 [channel] F7

        4. Articulation Query (0x13):
           F0 43 10 4C 13 [channel] F7

        5. Articulation Chain (0x14):
           F0 43 10 4C 14 [channel] [count] [art1_msb] [art1_lsb] [dur1_msb] [dur1_lsb] ... F7

        6. Bulk Dump (0x15):
           F0 43 10 4C 15 [channel] [data...] [checksum] F7

        7. Bulk Load (0x16):
           F0 43 10 4C 16 [channel] [data...] [checksum] F7

        8. System Config (0x17):
           F0 43 10 4C 17 [channel] [config_msb] [config_lsb] [value] F7

        Args:
            sysex: SYSEX message bytes (including F0 and F7)

        Returns:
            Parsed command dict or None if not recognized
        """
        if len(sysex) < 8:
            return None

        # Validate SYSEX format
        if sysex[0] != 0xF0 or sysex[-1] != 0xF7:
            return None

        # Check Yamaha manufacturer ID (0x43)
        if sysex[1] != self.YAMAHA_SYSEX_ID:
            return None

        # Check for S.Art2 command (0x4C)
        if sysex[3] != 0x4C:
            return None

        # Get command type
        cmd = sysex[4]
        cmd_name = self.SYSEX_COMMANDS.get(cmd, "unknown")

        # Parse based on command type
        if cmd == 0x10:
            return self._parse_sysex_articulation_set(sysex)
        elif cmd == 0x11:
            return self._parse_sysex_parameter_set(sysex)
        elif cmd == 0x12:
            return self._parse_sysex_articulation_release(sysex)
        elif cmd == 0x13:
            return self._parse_sysex_articulation_query(sysex)
        elif cmd == 0x14:
            return self._parse_sysex_articulation_chain(sysex)
        elif cmd == 0x15:
            return self._parse_sysex_bulk_dump(sysex)
        elif cmd == 0x16:
            return self._parse_sysex_bulk_load(sysex)
        elif cmd == 0x17:
            return self._parse_sysex_system_config(sysex)
        else:
            return {"command": cmd_name, "raw_data": sysex.hex(), "length": len(sysex)}

    def _parse_sysex_articulation_set(self, sysex: bytes) -> Dict[str, Any]:
        """Parse articulation set SYSEX (0x10)."""
        if len(sysex) < 9:
            return {"error": "Invalid articulation set SYSEX"}

        channel = sysex[5] & 0x0F
        art_msb = sysex[6] & 0x7F
        art_lsb = sysex[7] & 0x7F

        articulation = self.NRPN_ARTICULATION_MAP.get((art_msb, art_lsb), "normal")

        # Set articulation
        self.process_nrpn(art_msb, art_lsb)

        return {
            "command": "set_articulation",
            "channel": channel,
            "articulation": articulation,
            "nrpn_msb": art_msb,
            "nrpn_lsb": art_lsb,
        }

    def _parse_sysex_parameter_set(self, sysex: bytes) -> Dict[str, Any]:
        """Parse parameter set SYSEX (0x11)."""
        if len(sysex) < 11:
            return {"error": "Invalid parameter set SYSEX"}

        channel = sysex[5] & 0x0F
        param_msb = sysex[6] & 0x7F
        param_lsb = sysex[7] & 0x7F
        value_msb = sysex[8] & 0x7F
        value_lsb = sysex[9] & 0x7F

        value = (value_msb << 7) | value_lsb

        # Process parameter
        param_result = self.param_controller.process_parameter_nrpn(
            param_msb, param_lsb, value
        )

        return {
            "command": "set_parameter",
            "channel": channel,
            "param_msb": param_msb,
            "param_lsb": param_lsb,
            "value": value,
            "param_info": param_result,
        }

    def _parse_sysex_articulation_release(self, sysex: bytes) -> Dict[str, Any]:
        """Parse articulation release SYSEX (0x12)."""
        channel = sysex[5] & 0x0F if len(sysex) > 5 else 0

        # Reset to normal articulation
        self.process_nrpn(1, 0)

        return {"command": "release_articulation", "channel": channel}

    def _parse_sysex_articulation_query(self, sysex: bytes) -> Dict[str, Any]:
        """Parse articulation query SYSEX (0x13)."""
        channel = sysex[5] & 0x0F if len(sysex) > 5 else 0

        # Get current articulation NRPN
        msb, lsb = self._find_nrpn_for_articulation(self.current_articulation)

        return {
            "command": "query_articulation",
            "channel": channel,
            "articulation": self.current_articulation,
            "nrpn_msb": msb,
            "nrpn_lsb": lsb,
        }

    def _parse_sysex_articulation_chain(self, sysex: bytes) -> Dict[str, Any]:
        """Parse articulation chain SYSEX (0x14)."""
        if len(sysex) < 8:
            return {"error": "Invalid articulation chain SYSEX"}

        channel = sysex[5] & 0x0F
        count = sysex[6]

        articulations = []
        offset = 7

        for i in range(count):
            if offset + 3 >= len(sysex):
                break

            art_msb = sysex[offset] & 0x7F
            art_lsb = sysex[offset + 1] & 0x7F
            dur_msb = sysex[offset + 2] & 0x7F
            dur_lsb = sysex[offset + 3] & 0x7F

            articulation = self.NRPN_ARTICULATION_MAP.get((art_msb, art_lsb), "normal")
            duration = ((dur_msb << 7) | dur_lsb) * 0.001  # Convert to seconds

            articulations.append(
                {
                    "articulation": articulation,
                    "duration": duration,
                    "nrpn_msb": art_msb,
                    "nrpn_lsb": art_lsb,
                }
            )

            offset += 4

        return {
            "command": "set_articulation_chain",
            "channel": channel,
            "count": count,
            "articulations": articulations,
        }

    def _parse_sysex_bulk_dump(self, sysex: bytes) -> Dict[str, Any]:
        """Parse bulk dump SYSEX (0x15)."""
        if len(sysex) < 10:
            return {"error": "Invalid bulk dump SYSEX"}

        channel = sysex[5] & 0x0F

        # Extract data (excluding F0, header, and checksum/F7)
        data = sysex[6:-2]
        checksum = sysex[-2]

        # Verify checksum
        calculated_checksum = self._calculate_sysex_checksum(sysex[1:-2])

        return {
            "command": "bulk_dump",
            "channel": channel,
            "data": data,
            "checksum": checksum,
            "checksum_valid": (checksum == calculated_checksum),
            "data_length": len(data),
        }

    def _parse_sysex_bulk_load(self, sysex: bytes) -> Dict[str, Any]:
        """Parse bulk load SYSEX (0x16)."""
        if len(sysex) < 10:
            return {"error": "Invalid bulk load SYSEX"}

        channel = sysex[5] & 0x0F

        # Extract data
        data = sysex[6:-2]
        checksum = sysex[-2]

        # Verify checksum
        calculated_checksum = self._calculate_sysex_checksum(sysex[1:-2])

        return {
            "command": "bulk_load",
            "channel": channel,
            "data": data,
            "checksum": checksum,
            "checksum_valid": (checksum == calculated_checksum),
            "data_length": len(data),
        }

    def _parse_sysex_system_config(self, sysex: bytes) -> Dict[str, Any]:
        """Parse system config SYSEX (0x17)."""
        if len(sysex) < 10:
            return {"error": "Invalid system config SYSEX"}

        channel = sysex[5] & 0x0F
        config_msb = sysex[6] & 0x7F
        config_lsb = sysex[7] & 0x7F
        value = sysex[8] & 0x7F

        return {
            "command": "system_config",
            "channel": channel,
            "config_msb": config_msb,
            "config_lsb": config_lsb,
            "value": value,
        }

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

    def get_articulation_params(
        self, articulation: Optional[str] = None
    ) -> Dict[str, Any]:
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
            "common": [(1, i) for i in range(36)],
            "dynamics": [(2, i) for i in range(12)],
            "wind": [(3, i) for i in range(10)],
            "strings": [(4, i) for i in range(10)],
            "guitar": [(5, i) for i in range(10)],
            "brass": [(6, i) for i in range(6)],
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
        self.current_articulation = "normal"
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        if self._on_articulation_change:
            self._on_articulation_change("normal")

    # =====================================================================
    # SYSEX HELPER METHODS (Genos2 Compatible)
    # =====================================================================

    def _calculate_sysex_checksum(self, data: bytes) -> int:
        """
        Calculate Yamaha SYSEX checksum.

        Yamaha checksum: invert lower 7 bits of sum

        Args:
            data: SYSEX data (excluding F0 and F7)

        Returns:
            Checksum byte (0-127)
        """
        checksum = sum(data) & 0x7F
        return (~checksum) & 0x7F

    def _find_nrpn_for_articulation(self, articulation: str) -> Tuple[int, int]:
        """Find NRPN MSB/LSB for an articulation name."""
        for (msb, lsb), art in self.NRPN_ARTICULATION_MAP.items():
            if art == articulation:
                return (msb, lsb)
        return (1, 0)  # Default to normal

    def build_sysex_articulation_set(
        self, channel: int, art_msb: int, art_lsb: int
    ) -> bytes:
        """
        Build SYSEX message for articulation set.

        Args:
            channel: MIDI channel (0-15)
            art_msb: Articulation MSB
            art_lsb: Articulation LSB

        Returns:
            SYSEX byte sequence
        """
        return bytes(
            [
                0xF0,
                0x43,
                0x10,
                0x4C,
                0x10,
                channel & 0x0F,
                art_msb & 0x7F,
                art_lsb & 0x7F,
                0xF7,
            ]
        )

    def build_sysex_parameter_set(
        self, channel: int, param_msb: int, param_lsb: int, value: int
    ) -> bytes:
        """
        Build SYSEX message for parameter set.

        Args:
            channel: MIDI channel
            param_msb: Parameter MSB
            param_lsb: Parameter LSB
            value: Parameter value (0-16383)

        Returns:
            SYSEX byte sequence
        """
        value = max(0, min(16383, value))
        return bytes(
            [
                0xF0,
                0x43,
                0x10,
                0x4C,
                0x11,
                channel & 0x0F,
                param_msb & 0x7F,
                param_lsb & 0x7F,
                (value >> 7) & 0x7F,
                value & 0x7F,
                0xF7,
            ]
        )

    def build_sysex_articulation_query(self, channel: int) -> bytes:
        """
        Build SYSEX message for articulation query.

        Args:
            channel: MIDI channel

        Returns:
            SYSEX byte sequence
        """
        return bytes([0xF0, 0x43, 0x10, 0x4C, 0x13, channel & 0x0F, 0xF7])


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
        params: Optional[Dict[str, Any]] = None,
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

        if articulation == "normal" or not articulation:
            return sample

        # Apply specific articulation
        method_name = f"apply_{articulation}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sample, params)

        # Default: return unchanged
        logger.debug(f"No specific handler for articulation: {articulation}")
        return sample

    def apply_legato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply legato articulation - smooth transitions."""
        blend = params.get("blend", 0.5)
        transition_time = params.get("transition_time", 0.05)

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
        note_length = params.get("note_length", 0.1)

        length_samples = int(note_length * self.sample_rate)
        if len(sample) > length_samples:
            # Truncate and apply decay
            sample = sample[:length_samples].copy()
            decay = np.exp(-np.linspace(0, 10, length_samples))
            sample *= decay

        return sample

    def apply_vibrato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply vibrato - pitch modulation."""
        rate = params.get("rate", 5.0)
        depth = params.get("depth", 0.05)

        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * np.sin(2 * np.pi * rate * t)

        # Apply frequency modulation
        phase = np.cumsum(2 * np.pi * mod)
        mod_sample = sample * np.cos(phase)

        return (sample + mod_sample * 0.3).astype(np.float32)

    def apply_trill(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply trill - rapid note alternation."""
        interval = params.get("interval", 2)  # semitones
        rate = params.get("rate", 6.0)

        t = np.arange(len(sample)) / self.sample_rate
        mod = np.sin(2 * np.pi * rate * t)

        # Alternating pitch
        SEMITONE_RATIO = 1.059463359
        freq_mult = SEMITONE_RATIO ** (interval * mod)

        return (sample * freq_mult).astype(np.float32)

    def apply_pizzicato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply pizzicato - plucked string character."""
        decay_rate = params.get("decay_rate", 8.0)

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
        target_interval = params.get("target_interval", 7)
        speed = params.get("speed", 0.2)

        SEMITONE_RATIO = 1.059463359
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / speed, 0, 1)

        freq_mult = SEMITONE_RATIO ** (target_interval * progress)

        return (sample * freq_mult).astype(np.float32)

    def apply_growl(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply growl - growling texture."""
        mod_freq = params.get("mod_freq", 25.0)
        depth = params.get("depth", 0.25)

        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))

        # Add noise modulation
        noise = np.random.normal(0, 0.1, len(sample))
        noise = np.convolve(noise, np.ones(50) / 50, mode="same")

        return (sample * mod + noise * 0.2).astype(np.float32)

    def apply_flutter(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply flutter tongue."""
        mod_freq = params.get("mod_freq", 12.0)
        depth = params.get("depth", 0.15)

        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))

        return (sample * mod).astype(np.float32)

    def apply_bend(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply pitch bend."""
        amount = params.get("amount", 1.0)
        direction = params.get("direction", "up")

        SEMITONE_RATIO = 1.059463359
        bend_amount = amount / 12.0  # Convert semitones to octave ratio

        if direction == "down":
            bend_amount = -bend_amount

        t = np.arange(len(sample)) / self.sample_rate
        progress = np.linspace(0, 1, len(sample))

        freq_mult = SEMITONE_RATIO ** (bend_amount * progress)

        return (sample * freq_mult).astype(np.float32)

    def apply_swell(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply swell - volume crescendo then decrescendo."""
        attack = params.get("attack", 0.1)
        release = params.get("release", 0.2)

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
        harmonic = params.get("harmonic", 2)
        level = params.get("level", 0.35)

        t = np.arange(len(sample)) / self.sample_rate
        # Assume base frequency around 440Hz
        base_freq = 440
        harmonic_wave = np.sin(2 * np.pi * base_freq * harmonic * t)

        return (sample + harmonic_wave * level).astype(np.float32)

    def apply_crescendo(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply crescendo - gradual volume increase."""
        target_level = params.get("target_level", 1.0)
        duration = params.get("duration", 1.0)

        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / duration, 0, 1)

        envelope = 0.3 + progress * (target_level - 0.3)

        return (sample * envelope).astype(np.float32)

    def apply_diminuendo(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply diminuendo - gradual volume decrease."""
        target_level = params.get("target_level", 0.1)
        duration = params.get("duration", 1.0)

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

    def apply_soft_pedal(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply soft pedal (una corda) - reduced volume, softer tone."""
        level = params.get("level", 0.7)
        brightness = params.get("brightness", 0.8)

        # Reduce overall level
        result = sample * level

        # Apply low-pass filter effect via simple smoothing
        if brightness < 1.0:
            kernel_size = int((1.0 - brightness) * 100) + 1
            kernel = np.ones(kernel_size) / kernel_size
            result = np.convolve(result, kernel, mode="same")

        return result.astype(np.float32)

    def apply_sustain_pedal(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply sustain pedal - extends release."""
        sustain_level = params.get("sustain_level", 0.8)
        release_rate = params.get("release_rate", 0.5)

        # Create sustain envelope
        envelope = np.ones(len(sample))

        # Gradual decay in sustained portion
        sustain_start = int(len(sample) * 0.3)
        for i in range(sustain_start, len(sample)):
            decay = np.exp(-(i - sustain_start) * release_rate / self.sample_rate)
            envelope[i] = sustain_level + (1 - sustain_level) * decay

        return (sample * envelope).astype(np.float32)

    def apply_hammer_on(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply hammer-on - quick pitch rise."""
        amount = params.get("amount", 2)  # semitones
        SEMITONE_RATIO = 1.059463359

        # Gradual pitch rise
        pitch_rise = np.linspace(0, amount, len(sample))
        freq_mult = SEMITONE_RATIO**pitch_rise

        t = np.arange(len(sample)) / self.sample_rate
        # Simple resampling approximation
        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        result = sample[indices]
        return result.astype(np.float32)

    def apply_pull_off(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply pull-off - quick pitch drop."""
        amount = params.get("amount", -2)  # semitones down
        SEMITONE_RATIO = 1.059463359

        # Gradual pitch drop
        pitch_drop = np.linspace(0, amount, len(sample))
        freq_mult = SEMITONE_RATIO**pitch_drop

        t = np.arange(len(sample)) / self.sample_rate
        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        result = sample[indices]
        return result.astype(np.float32)

    def apply_palm_mute(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply palm mute - dampened sound."""
        damp_factor = params.get("damp_factor", 0.5)

        # Quick decay envelope
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 10 * (1 - damp_factor))

        # Also add some noise for pick attack
        attack_samples = int(0.01 * self.sample_rate)
        attack = np.zeros(len(sample))
        if attack_samples > 0:
            noise = np.random.normal(0, 0.2, attack_samples)
            attack[:attack_samples] = noise

        return (sample * decay + attack * damp_factor * 0.3).astype(np.float32)

    def apply_tremolo(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply tremolo - fast volume modulation."""
        rate = params.get("rate", 6.0)  # Hz
        depth = params.get("depth", 0.5)

        t = np.arange(len(sample)) / self.sample_rate
        mod = 1.0 - depth * (1 + np.sin(2 * np.pi * rate * t)) / 2

        return (sample * mod).astype(np.float32)

    def apply_vibrato(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply vibrato - pitch modulation."""
        rate = params.get("rate", 5.0)  # Hz
        depth = params.get("depth", 0.5)  # cents
        SEMITONE_RATIO = 1.059463359

        cents = depth / 100.0
        t = np.arange(len(sample)) / self.sample_rate
        pitch_mod = cents * np.sin(2 * np.pi * rate * t)
        freq_mult = SEMITONE_RATIO**pitch_mod

        # Approximate resampling
        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_sub_bass(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply sub bass - add sub-bass frequency content."""
        # Add low frequency rumble
        t = np.arange(len(sample)) / self.sample_rate
        sub_freq = 40  # Hz
        sub_osc = np.sin(2 * np.pi * sub_freq * t) * 0.3

        # Low-pass filter approximation
        kernel = np.ones(50) / 50
        sample_smooth = np.convolve(sample, kernel, mode="same")

        return (sample_smooth + sub_osc).astype(np.float32)

    def apply_dead_note(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply dead note - muted percussive sound."""
        # Quick decay
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 30)

        # Add noise component
        noise = np.random.normal(0, 0.3, len(sample))
        noise = np.convolve(noise, np.ones(20) / 20, mode="same")

        result = sample * decay * 0.3 + noise * decay * 0.5
        return result.astype(np.float32)

    def apply_fret_noise(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Add fret noise - finger on frets."""
        noise_level = params.get("noise_level", 0.15)

        # Create noise bursts at note start
        attack_samples = int(0.02 * self.sample_rate)
        fret_noise = np.zeros(len(sample))

        # Initial fret noise
        fret_noise[:attack_samples] = np.random.normal(0, noise_level, attack_samples)

        # Combine with original sample
        return (sample + fret_noise).astype(np.float32)

    def apply_organ_click(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply organ click - percussive attack."""
        click_level = params.get("click_level", 0.2)
        click_width = params.get("click_width", 0.005)  # seconds

        # Add click at start
        click_samples = int(click_width * self.sample_rate)
        click = np.zeros(len(sample))

        # Initial click
        click[:click_samples] = np.random.normal(0, click_level, click_samples)

        # Quick decay
        t = np.arange(click_samples) / self.sample_rate
        click[:click_samples] *= np.exp(-t * 50)

        return (sample + click).astype(np.float32)

    def apply_ethnic_bend(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply ethnic-style pitch bend."""
        bend_amount = params.get("bend_amount", 0.5)  # semitones
        bend_speed = params.get("bend_speed", 0.3)

        SEMITONE_RATIO = 1.059463359

        # S-curve bend
        t = np.arange(len(sample)) / self.sample_rate
        progress = 1 - np.exp(-t * bend_speed * 10)
        bend = bend_amount * progress
        freq_mult = SEMITONE_RATIO**bend

        # Resample
        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_rim_shot(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply rim shot - hard attack with rim sound."""
        rim_level = params.get("rim_level", 0.6)

        # Sharp attack
        attack_samples = int(0.005 * self.sample_rate)
        attack = np.zeros(len(sample))
        attack[:attack_samples] = np.random.normal(0, rim_level, attack_samples)

        # Quick decay
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 20)

        return (sample * decay + attack).astype(np.float32)

    def apply_open_rim(self, sample: np.ndarray, params: Dict) -> np.ndarray:
        """Apply open rim shot - resonant."""
        ring_time = params.get("ring_time", 0.3)

        # Longer decay with some resonance
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * (3 / ring_time))

        return (sample * decay).astype(np.float32)


# Factory function
def create_articulation_controller() -> ArticulationController:
    """Create and return an ArticulationController instance."""
    return ArticulationController()


def create_sample_modifier(sample_rate: int = 44100) -> SF2SampleModifier:
    """Create and return an SF2SampleModifier instance."""
    return SF2SampleModifier(sample_rate=sample_rate)
