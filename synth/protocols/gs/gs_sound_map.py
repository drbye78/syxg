"""Roland GS instrument bank map — Capital Tones, Variation Tones, Drum Kits.

Maps (bank_msb, bank_lsb, program) → instrument_name per the
Roland GS specification. Used for instrument display and GS MIDI file playback.
"""

from __future__ import annotations

# ── Capital Tones (Bank MSB=0, Bank LSB=0) ──
# GS-compatible GM sound set, 128 programs
GS_CAPITAL_TONES: dict[int, str] = {
    0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano",
    2: "Electric Grand Piano", 3: "Honky-tonk Piano",
    4: "Electric Piano 1", 5: "Electric Piano 2",
    6: "Harpsichord", 7: "Clavinet",
    8: "Celesta", 9: "Glockenspiel",
    10: "Music Box", 11: "Vibraphone",
    12: "Marimba", 13: "Xylophone",
    14: "Tubular Bells", 15: "Dulcimer",
    16: "Drawbar Organ", 17: "Percussive Organ",
    18: "Rock Organ", 19: "Church Organ",
    20: "Reed Organ", 21: "Accordion",
    22: "Harmonica", 23: "Tango Accordion",
    24: "Nylon String Guitar", 25: "Steel String Guitar",
    26: "Jazz Guitar", 27: "Clean Electric Guitar",
    28: "Muted Electric Guitar", 29: "Overdriven Guitar",
    30: "Distortion Guitar", 31: "Guitar Harmonics",
    32: "Acoustic Bass", 33: "Fingered Electric Bass",
    34: "Picked Electric Bass", 35: "Fretless Bass",
    36: "Slap Bass 1", 37: "Slap Bass 2",
    38: "Synth Bass 1", 39: "Synth Bass 2",
    40: "Violin", 41: "Viola",
    42: "Cello", 43: "Contrabass",
    44: "Tremolo Strings", 45: "Pizzicato Strings",
    46: "Orchestral Harp", 47: "Timpani",
    48: "String Ensemble 1", 49: "String Ensemble 2",
    50: "Synth Strings 1", 51: "Synth Strings 2",
    52: "Choir Aahs", 53: "Voice Oohs",
    54: "Synth Voice", 55: "Orchestra Hit",
    56: "Trumpet", 57: "Trombone",
    58: "Tuba", 59: "Muted Trumpet",
    60: "French Horn", 61: "Brass Section",
    62: "Synth Brass 1", 63: "Synth Brass 2",
    64: "Soprano Sax", 65: "Alto Sax",
    66: "Tenor Sax", 67: "Baritone Sax",
    68: "Oboe", 69: "English Horn",
    70: "Bassoon", 71: "Clarinet",
    72: "Piccolo", 73: "Flute",
    74: "Recorder", 75: "Pan Flute",
    76: "Blown Bottle", 77: "Shakuhachi",
    78: "Whistle", 79: "Ocarina",
    80: "Lead 1 (Square)", 81: "Lead 2 (Sawtooth)",
    82: "Lead 3 (Calliope)", 83: "Lead 4 (Chiff)",
    84: "Lead 5 (Charang)", 85: "Lead 6 (Voice)",
    86: "Lead 7 (Fifths)", 87: "Lead 8 (Bass + Lead)",
    88: "Pad 1 (New Age)", 89: "Pad 2 (Warm)",
    90: "Pad 3 (Polysynth)", 91: "Pad 4 (Choir)",
    92: "Pad 5 (Bowed)", 93: "Pad 6 (Metallic)",
    94: "Pad 7 (Halo)", 95: "Pad 8 (Sweep)",
    96: "FX 1 (Rain)", 97: "FX 2 (Soundtrack)",
    98: "FX 3 (Crystal)", 99: "FX 4 (Atmosphere)",
    100: "FX 5 (Brightness)", 101: "FX 6 (Goblins)",
    102: "FX 7 (Echoes)", 103: "FX 8 (Sci-Fi)",
    104: "Sitar", 105: "Banjo",
    106: "Shamisen", 107: "Koto",
    108: "Kalimba", 109: "Bagpipe",
    110: "Fiddle", 111: "Shanai",
    112: "Tinkle Bell", 113: "Agogo",
    114: "Steel Drums", 115: "Woodblock",
    116: "Taiko Drum", 117: "Melodic Tom",
    118: "Synth Drum", 119: "Reverse Cymbal",
    120: "Guitar Fret Noise", 121: "Breath Noise",
    122: "Seashore", 123: "Bird Tweet",
    124: "Telephone Ring", 125: "Helicopter",
    126: "Applause", 127: "Gunshot",
}

# ── GS Drum Kits (Bank MSB=127) ──
GS_DRUM_KITS: dict[int, str] = {
    0: "Standard Kit 1",
    1: "Standard Kit 2",
    8: "Room Kit",
    16: "Power Kit",
    24: "Electronic Kit",
    25: "TR-808 Kit",
    32: "Jazz Kit",
    40: "Brush Kit",
    48: "Orchestra Kit",
    56: "SFX Kit",
}


def get_gs_instrument_name(bank_msb: int, bank_lsb: int, program: int) -> str:
    """Return instrument name for a GS bank/program combination.

    Args:
        bank_msb: Bank Select MSB (0-127)
        bank_lsb: Bank Select LSB (0-127)
        program: Program Change number (0-127)

    Returns:
        Human-readable instrument name string.
    """
    if bank_msb == 127:
        name = GS_DRUM_KITS.get(program)
        if name:
            return name
        return f"GS Drum Kit {program}"
    elif bank_msb == 0 and bank_lsb == 0:
        name = GS_CAPITAL_TONES.get(program)
        if name:
            return name
        return f"GM Program {program}"
    else:
        # Variation tones — return descriptive name with bank info
        return f"GS Variation {bank_lsb}/{program}"
