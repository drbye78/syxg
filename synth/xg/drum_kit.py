"""
XG Drum Kit implementation for XG synthesizer.
Contains all standard XG drum kits and parameters.
"""

from typing import Dict, List, Tuple, Optional, Any


class XGDrumKit:
    """XG Drum Kit implementation with all standard kits and parameters"""

    # XG Drum Kit Types
    STANDARD = 0
    ROOM = 8
    POWER = 16
    ELECTRONIC = 24
    ANALOG = 25
    JAZZ = 32
    BRUSH = 40
    ORCHESTRA = 48
    SFX = 56
    CM64 = 57
    CM32 = 58

    # Complete XG drum map with all kits
    XG_DRUM_KITS = {
        STANDARD: {
            35: {"name": "Acoustic Bass Drum", "tune": 0, "level": 100, "pan": 0, "reverb": 20, "chorus": 0},
            36: {"name": "Bass Drum 1", "tune": 0, "level": 100, "pan": 0, "reverb": 20, "chorus": 0},
            37: {"name": "Side Stick", "tune": 0, "level": 80, "pan": -20, "reverb": 10, "chorus": 0},
            38: {"name": "Acoustic Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 15, "chorus": 0},
            39: {"name": "Hand Clap", "tune": 0, "level": 90, "pan": 0, "reverb": 25, "chorus": 5},
            40: {"name": "Electric Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 15, "chorus": 0},
            41: {"name": "Low Floor Tom", "tune": -8, "level": 90, "pan": 30, "reverb": 20, "chorus": 0},
            42: {"name": "Closed Hi Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 10, "chorus": 0},
            43: {"name": "High Floor Tom", "tune": -4, "level": 90, "pan": -30, "reverb": 20, "chorus": 0},
            44: {"name": "Pedal Hi-Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 10, "chorus": 0},
            45: {"name": "Low Tom", "tune": -12, "level": 90, "pan": 40, "reverb": 20, "chorus": 0},
            46: {"name": "Open Hi-Hat", "tune": 0, "level": 85, "pan": 0, "reverb": 15, "chorus": 0},
            47: {"name": "Low-Mid Tom", "tune": -8, "level": 90, "pan": 20, "reverb": 20, "chorus": 0},
            48: {"name": "Hi-Mid Tom", "tune": -4, "level": 90, "pan": -20, "reverb": 20, "chorus": 0},
            49: {"name": "Crash Cymbal 1", "tune": 0, "level": 100, "pan": -40, "reverb": 30, "chorus": 10},
            50: {"name": "High Tom", "tune": 0, "level": 90, "pan": -40, "reverb": 20, "chorus": 0},
            51: {"name": "Ride Cymbal 1", "tune": 0, "level": 95, "pan": 40, "reverb": 25, "chorus": 5},
            52: {"name": "Chinese Cymbal", "tune": 0, "level": 100, "pan": 50, "reverb": 35, "chorus": 15},
            53: {"name": "Ride Bell", "tune": 12, "level": 85, "pan": 40, "reverb": 20, "chorus": 5},
            54: {"name": "Tambourine", "tune": 0, "level": 80, "pan": 0, "reverb": 15, "chorus": 10},
            55: {"name": "Splash Cymbal", "tune": 0, "level": 95, "pan": 30, "reverb": 30, "chorus": 10},
            56: {"name": "Cowbell", "tune": 0, "level": 85, "pan": 0, "reverb": 10, "chorus": 0},
            57: {"name": "Crash Cymbal 2", "tune": 0, "level": 100, "pan": 40, "reverb": 30, "chorus": 10},
            58: {"name": "Vibra Slap", "tune": 0, "level": 80, "pan": 0, "reverb": 20, "chorus": 5},
            59: {"name": "Ride Cymbal 2", "tune": 0, "level": 95, "pan": -40, "reverb": 25, "chorus": 5},
            60: {"name": "High Bongo", "tune": 0, "level": 90, "pan": -20, "reverb": 15, "chorus": 5},
            61: {"name": "Low Bongo", "tune": -4, "level": 90, "pan": 20, "reverb": 15, "chorus": 5},
            62: {"name": "Mute High Conga", "tune": 0, "level": 85, "pan": -30, "reverb": 15, "chorus": 5},
            63: {"name": "Open High Conga", "tune": 0, "level": 90, "pan": -30, "reverb": 20, "chorus": 5},
            64: {"name": "Low Conga", "tune": -8, "level": 90, "pan": 30, "reverb": 20, "chorus": 5},
            65: {"name": "High Timbale", "tune": 0, "level": 90, "pan": -40, "reverb": 15, "chorus": 0},
            66: {"name": "Low Timbale", "tune": -8, "level": 90, "pan": 40, "reverb": 15, "chorus": 0},
            67: {"name": "High Agogo", "tune": 0, "level": 85, "pan": -20, "reverb": 10, "chorus": 0},
            68: {"name": "Low Agogo", "tune": -12, "level": 85, "pan": 20, "reverb": 10, "chorus": 0},
            69: {"name": "Cabasa", "tune": 0, "level": 80, "pan": 0, "reverb": 15, "chorus": 10},
            70: {"name": "Maracas", "tune": 0, "level": 80, "pan": 0, "reverb": 15, "chorus": 10},
            71: {"name": "Short Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 5, "chorus": 0},
            72: {"name": "Long Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 5, "chorus": 0},
            73: {"name": "Short Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 10, "chorus": 0},
            74: {"name": "Long Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 10, "chorus": 0},
            75: {"name": "Claves", "tune": 0, "level": 85, "pan": 0, "reverb": 10, "chorus": 0},
            76: {"name": "High Wood Block", "tune": 12, "level": 80, "pan": -20, "reverb": 10, "chorus": 0},
            77: {"name": "Low Wood Block", "tune": 0, "level": 80, "pan": 20, "reverb": 10, "chorus": 0},
            78: {"name": "Mute Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 15, "chorus": 5},
            79: {"name": "Open Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 15, "chorus": 5},
            80: {"name": "Mute Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 20, "chorus": 15},
            81: {"name": "Open Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 20, "chorus": 15}
        },

        # Room kit (similar to Standard but with different reverb/chorus settings)
        ROOM: {
            35: {"name": "Acoustic Bass Drum", "tune": 0, "level": 100, "pan": 0, "reverb": 40, "chorus": 5},
            36: {"name": "Bass Drum 1", "tune": 0, "level": 100, "pan": 0, "reverb": 40, "chorus": 5},
            37: {"name": "Side Stick", "tune": 0, "level": 80, "pan": -20, "reverb": 30, "chorus": 0},
            38: {"name": "Acoustic Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 35, "chorus": 5},
            39: {"name": "Hand Clap", "tune": 0, "level": 90, "pan": 0, "reverb": 45, "chorus": 10},
            40: {"name": "Electric Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 35, "chorus": 5},
            41: {"name": "Low Floor Tom", "tune": -8, "level": 90, "pan": 30, "reverb": 40, "chorus": 5},
            42: {"name": "Closed Hi Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 30, "chorus": 0},
            43: {"name": "High Floor Tom", "tune": -4, "level": 90, "pan": -30, "reverb": 40, "chorus": 5},
            44: {"name": "Pedal Hi-Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 30, "chorus": 0},
            45: {"name": "Low Tom", "tune": -12, "level": 90, "pan": 40, "reverb": 40, "chorus": 5},
            46: {"name": "Open Hi-Hat", "tune": 0, "level": 85, "pan": 0, "reverb": 35, "chorus": 5},
            47: {"name": "Low-Mid Tom", "tune": -8, "level": 90, "pan": 20, "reverb": 40, "chorus": 5},
            48: {"name": "Hi-Mid Tom", "tune": -4, "level": 90, "pan": -20, "reverb": 40, "chorus": 5},
            49: {"name": "Crash Cymbal 1", "tune": 0, "level": 100, "pan": -40, "reverb": 50, "chorus": 15},
            50: {"name": "High Tom", "tune": 0, "level": 90, "pan": -40, "reverb": 40, "chorus": 5},
            51: {"name": "Ride Cymbal 1", "tune": 0, "level": 95, "pan": 40, "reverb": 45, "chorus": 10},
            52: {"name": "Chinese Cymbal", "tune": 0, "level": 100, "pan": 50, "reverb": 55, "chorus": 20},
            53: {"name": "Ride Bell", "tune": 12, "level": 85, "pan": 40, "reverb": 40, "chorus": 10},
            54: {"name": "Tambourine", "tune": 0, "level": 80, "pan": 0, "reverb": 35, "chorus": 15},
            55: {"name": "Splash Cymbal", "tune": 0, "level": 95, "pan": 30, "reverb": 50, "chorus": 15},
            56: {"name": "Cowbell", "tune": 0, "level": 85, "pan": 0, "reverb": 30, "chorus": 5},
            57: {"name": "Crash Cymbal 2", "tune": 0, "level": 100, "pan": 40, "reverb": 50, "chorus": 15},
            58: {"name": "Vibra Slap", "tune": 0, "level": 80, "pan": 0, "reverb": 40, "chorus": 10},
            59: {"name": "Ride Cymbal 2", "tune": 0, "level": 95, "pan": -40, "reverb": 45, "chorus": 10},
            60: {"name": "High Bongo", "tune": 0, "level": 90, "pan": -20, "reverb": 35, "chorus": 10},
            61: {"name": "Low Bongo", "tune": -4, "level": 90, "pan": 20, "reverb": 35, "chorus": 10},
            62: {"name": "Mute High Conga", "tune": 0, "level": 85, "pan": -30, "reverb": 35, "chorus": 10},
            63: {"name": "Open High Conga", "tune": 0, "level": 90, "pan": -30, "reverb": 40, "chorus": 10},
            64: {"name": "Low Conga", "tune": -8, "level": 90, "pan": 30, "reverb": 40, "chorus": 10},
            65: {"name": "High Timbale", "tune": 0, "level": 90, "pan": -40, "reverb": 35, "chorus": 5},
            66: {"name": "Low Timbale", "tune": -8, "level": 90, "pan": 40, "reverb": 35, "chorus": 5},
            67: {"name": "High Agogo", "tune": 0, "level": 85, "pan": -20, "reverb": 30, "chorus": 5},
            68: {"name": "Low Agogo", "tune": -12, "level": 85, "pan": 20, "reverb": 30, "chorus": 5},
            69: {"name": "Cabasa", "tune": 0, "level": 80, "pan": 0, "reverb": 35, "chorus": 15},
            70: {"name": "Maracas", "tune": 0, "level": 80, "pan": 0, "reverb": 35, "chorus": 15},
            71: {"name": "Short Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 25, "chorus": 5},
            72: {"name": "Long Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 25, "chorus": 5},
            73: {"name": "Short Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 30, "chorus": 5},
            74: {"name": "Long Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 30, "chorus": 5},
            75: {"name": "Claves", "tune": 0, "level": 85, "pan": 0, "reverb": 30, "chorus": 5},
            76: {"name": "High Wood Block", "tune": 12, "level": 80, "pan": -20, "reverb": 30, "chorus": 5},
            77: {"name": "Low Wood Block", "tune": 0, "level": 80, "pan": 20, "reverb": 30, "chorus": 5},
            78: {"name": "Mute Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 35, "chorus": 10},
            79: {"name": "Open Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 35, "chorus": 10},
            80: {"name": "Mute Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 40, "chorus": 20},
            81: {"name": "Open Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 40, "chorus": 20}
        },

        # Power kit (more aggressive settings)
        POWER: {
            35: {"name": "Acoustic Bass Drum", "tune": 0, "level": 110, "pan": 0, "reverb": 15, "chorus": 0},
            36: {"name": "Bass Drum 1", "tune": 0, "level": 110, "pan": 0, "reverb": 15, "chorus": 0},
            37: {"name": "Side Stick", "tune": 0, "level": 85, "pan": -20, "reverb": 5, "chorus": 0},
            38: {"name": "Acoustic Snare", "tune": 0, "level": 110, "pan": 0, "reverb": 10, "chorus": 0},
            39: {"name": "Hand Clap", "tune": 0, "level": 95, "pan": 0, "reverb": 20, "chorus": 0},
            40: {"name": "Electric Snare", "tune": 0, "level": 110, "pan": 0, "reverb": 10, "chorus": 0},
            41: {"name": "Low Floor Tom", "tune": -8, "level": 100, "pan": 30, "reverb": 15, "chorus": 0},
            42: {"name": "Closed Hi Hat", "tune": 0, "level": 90, "pan": 0, "reverb": 5, "chorus": 0},
            43: {"name": "High Floor Tom", "tune": -4, "level": 100, "pan": -30, "reverb": 15, "chorus": 0},
            44: {"name": "Pedal Hi-Hat", "tune": 0, "level": 90, "pan": 0, "reverb": 5, "chorus": 0},
            45: {"name": "Low Tom", "tune": -12, "level": 100, "pan": 40, "reverb": 15, "chorus": 0},
            46: {"name": "Open Hi-Hat", "tune": 0, "level": 95, "pan": 0, "reverb": 10, "chorus": 0},
            47: {"name": "Low-Mid Tom", "tune": -8, "level": 100, "pan": 20, "reverb": 15, "chorus": 0},
            48: {"name": "Hi-Mid Tom", "tune": -4, "level": 100, "pan": -20, "reverb": 15, "chorus": 0},
            49: {"name": "Crash Cymbal 1", "tune": 0, "level": 115, "pan": -40, "reverb": 25, "chorus": 5},
            50: {"name": "High Tom", "tune": 0, "level": 100, "pan": -40, "reverb": 15, "chorus": 0},
            51: {"name": "Ride Cymbal 1", "tune": 0, "level": 105, "pan": 40, "reverb": 20, "chorus": 0},
            52: {"name": "Chinese Cymbal", "tune": 0, "level": 115, "pan": 50, "reverb": 30, "chorus": 10},
            53: {"name": "Ride Bell", "tune": 12, "level": 95, "pan": 40, "reverb": 15, "chorus": 0},
            54: {"name": "Tambourine", "tune": 0, "level": 90, "pan": 0, "reverb": 10, "chorus": 5},
            55: {"name": "Splash Cymbal", "tune": 0, "level": 105, "pan": 30, "reverb": 25, "chorus": 5},
            56: {"name": "Cowbell", "tune": 0, "level": 95, "pan": 0, "reverb": 5, "chorus": 0},
            57: {"name": "Crash Cymbal 2", "tune": 0, "level": 115, "pan": 40, "reverb": 25, "chorus": 5},
            58: {"name": "Vibra Slap", "tune": 0, "level": 90, "pan": 0, "reverb": 15, "chorus": 0},
            59: {"name": "Ride Cymbal 2", "tune": 0, "level": 105, "pan": -40, "reverb": 20, "chorus": 0},
            60: {"name": "High Bongo", "tune": 0, "level": 100, "pan": -20, "reverb": 10, "chorus": 0},
            61: {"name": "Low Bongo", "tune": -4, "level": 100, "pan": 20, "reverb": 10, "chorus": 0},
            62: {"name": "Mute High Conga", "tune": 0, "level": 95, "pan": -30, "reverb": 10, "chorus": 0},
            63: {"name": "Open High Conga", "tune": 0, "level": 100, "pan": -30, "reverb": 15, "chorus": 0},
            64: {"name": "Low Conga", "tune": -8, "level": 100, "pan": 30, "reverb": 15, "chorus": 0},
            65: {"name": "High Timbale", "tune": 0, "level": 100, "pan": -40, "reverb": 10, "chorus": 0},
            66: {"name": "Low Timbale", "tune": -8, "level": 100, "pan": 40, "reverb": 10, "chorus": 0},
            67: {"name": "High Agogo", "tune": 0, "level": 95, "pan": -20, "reverb": 5, "chorus": 0},
            68: {"name": "Low Agogo", "tune": -12, "level": 95, "pan": 20, "reverb": 5, "chorus": 0},
            69: {"name": "Cabasa", "tune": 0, "level": 90, "pan": 0, "reverb": 10, "chorus": 5},
            70: {"name": "Maracas", "tune": 0, "level": 90, "pan": 0, "reverb": 10, "chorus": 5},
            71: {"name": "Short Whistle", "tune": 0, "level": 85, "pan": 0, "reverb": 0, "chorus": 0},
            72: {"name": "Long Whistle", "tune": 0, "level": 85, "pan": 0, "reverb": 0, "chorus": 0},
            73: {"name": "Short Guiro", "tune": 0, "level": 90, "pan": 0, "reverb": 5, "chorus": 0},
            74: {"name": "Long Guiro", "tune": 0, "level": 90, "pan": 0, "reverb": 5, "chorus": 0},
            75: {"name": "Claves", "tune": 0, "level": 95, "pan": 0, "reverb": 5, "chorus": 0},
            76: {"name": "High Wood Block", "tune": 12, "level": 90, "pan": -20, "reverb": 5, "chorus": 0},
            77: {"name": "Low Wood Block", "tune": 0, "level": 90, "pan": 20, "reverb": 5, "chorus": 0},
            78: {"name": "Mute Cuica", "tune": 0, "level": 90, "pan": 0, "reverb": 10, "chorus": 0},
            79: {"name": "Open Cuica", "tune": 0, "level": 90, "pan": 0, "reverb": 10, "chorus": 0},
            80: {"name": "Mute Triangle", "tune": 0, "level": 85, "pan": 0, "reverb": 15, "chorus": 10},
            81: {"name": "Open Triangle", "tune": 0, "level": 85, "pan": 0, "reverb": 15, "chorus": 10}
        },

        # Electronic kit
        ELECTRONIC: {
            35: {"name": "Electric Bass Drum", "tune": 0, "level": 100, "pan": 0, "reverb": 10, "chorus": 0},
            36: {"name": "Electric Bass Drum", "tune": 0, "level": 100, "pan": 0, "reverb": 10, "chorus": 0},
            37: {"name": "Electric Stick", "tune": 0, "level": 80, "pan": -20, "reverb": 5, "chorus": 0},
            38: {"name": "Electric Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 8, "chorus": 0},
            39: {"name": "Hand Clap", "tune": 0, "level": 90, "pan": 0, "reverb": 15, "chorus": 0},
            40: {"name": "Electric Snare", "tune": 0, "level": 100, "pan": 0, "reverb": 8, "chorus": 0},
            41: {"name": "Electric Low Tom", "tune": -8, "level": 90, "pan": 30, "reverb": 10, "chorus": 0},
            42: {"name": "Closed Hi Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 5, "chorus": 0},
            43: {"name": "Electric High Tom", "tune": -4, "level": 90, "pan": -30, "reverb": 10, "chorus": 0},
            44: {"name": "Pedal Hi-Hat", "tune": 0, "level": 80, "pan": 0, "reverb": 5, "chorus": 0},
            45: {"name": "Electric Low Tom", "tune": -12, "level": 90, "pan": 40, "reverb": 10, "chorus": 0},
            46: {"name": "Open Hi-Hat", "tune": 0, "level": 85, "pan": 0, "reverb": 8, "chorus": 0},
            47: {"name": "Electric Mid Tom", "tune": -8, "level": 90, "pan": 20, "reverb": 10, "chorus": 0},
            48: {"name": "Electric Mid Tom", "tune": -4, "level": 90, "pan": -20, "reverb": 10, "chorus": 0},
            49: {"name": "Reverse Cymbal", "tune": 0, "level": 100, "pan": -40, "reverb": 20, "chorus": 5},
            50: {"name": "Electric High Tom", "tune": 0, "level": 90, "pan": -40, "reverb": 10, "chorus": 0},
            51: {"name": "Ride Cymbal", "tune": 0, "level": 95, "pan": 40, "reverb": 15, "chorus": 0},
            52: {"name": "Chinese Cymbal", "tune": 0, "level": 100, "pan": 50, "reverb": 25, "chorus": 10},
            53: {"name": "Ride Bell", "tune": 12, "level": 85, "pan": 40, "reverb": 12, "chorus": 0},
            54: {"name": "Tambourine", "tune": 0, "level": 80, "pan": 0, "reverb": 10, "chorus": 5},
            55: {"name": "Splash Cymbal", "tune": 0, "level": 95, "pan": 30, "reverb": 20, "chorus": 5},
            56: {"name": "Cowbell", "tune": 0, "level": 85, "pan": 0, "reverb": 5, "chorus": 0},
            57: {"name": "Crash Cymbal", "tune": 0, "level": 100, "pan": 40, "reverb": 20, "chorus": 5},
            58: {"name": "Vibra Slap", "tune": 0, "level": 80, "pan": 0, "reverb": 12, "chorus": 0},
            59: {"name": "Ride Cymbal", "tune": 0, "level": 95, "pan": -40, "reverb": 15, "chorus": 0},
            60: {"name": "High Bongo", "tune": 0, "level": 90, "pan": -20, "reverb": 8, "chorus": 0},
            61: {"name": "Low Bongo", "tune": -4, "level": 90, "pan": 20, "reverb": 8, "chorus": 0},
            62: {"name": "Mute High Conga", "tune": 0, "level": 85, "pan": -30, "reverb": 8, "chorus": 0},
            63: {"name": "Open High Conga", "tune": 0, "level": 90, "pan": -30, "reverb": 12, "chorus": 0},
            64: {"name": "Low Conga", "tune": -8, "level": 90, "pan": 30, "reverb": 12, "chorus": 0},
            65: {"name": "High Timbale", "tune": 0, "level": 90, "pan": -40, "reverb": 8, "chorus": 0},
            66: {"name": "Low Timbale", "tune": -8, "level": 90, "pan": 40, "reverb": 8, "chorus": 0},
            67: {"name": "High Agogo", "tune": 0, "level": 85, "pan": -20, "reverb": 5, "chorus": 0},
            68: {"name": "Low Agogo", "tune": -12, "level": 85, "pan": 20, "reverb": 5, "chorus": 0},
            69: {"name": "Cabasa", "tune": 0, "level": 80, "pan": 0, "reverb": 8, "chorus": 5},
            70: {"name": "Maracas", "tune": 0, "level": 80, "pan": 0, "reverb": 8, "chorus": 5},
            71: {"name": "Short Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 0, "chorus": 0},
            72: {"name": "Long Whistle", "tune": 0, "level": 75, "pan": 0, "reverb": 0, "chorus": 0},
            73: {"name": "Short Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 5, "chorus": 0},
            74: {"name": "Long Guiro", "tune": 0, "level": 80, "pan": 0, "reverb": 5, "chorus": 0},
            75: {"name": "Claves", "tune": 0, "level": 85, "pan": 0, "reverb": 5, "chorus": 0},
            76: {"name": "High Wood Block", "tune": 12, "level": 80, "pan": -20, "reverb": 5, "chorus": 0},
            77: {"name": "Low Wood Block", "tune": 0, "level": 80, "pan": 20, "reverb": 5, "chorus": 0},
            78: {"name": "Mute Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 8, "chorus": 0},
            79: {"name": "Open Cuica", "tune": 0, "level": 80, "pan": 0, "reverb": 8, "chorus": 0},
            80: {"name": "Mute Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 12, "chorus": 8},
            81: {"name": "Open Triangle", "tune": 0, "level": 75, "pan": 0, "reverb": 12, "chorus": 8}
        }
    }

    def __init__(self, kit_type=STANDARD):
        """
        Initialize XG Drum Kit

        Args:
            kit_type: Type of drum kit (STANDARD, ROOM, POWER, etc.)
        """
        self.kit_type = kit_type
        self.kit_data = self.XG_DRUM_KITS.get(kit_type, self.XG_DRUM_KITS[self.STANDARD]).copy()

    def get_instrument(self, note: int) -> Optional[Dict[str, Any]]:
        """
        Get instrument data for a specific note

        Args:
            note: MIDI note number

        Returns:
            Dictionary with instrument parameters or None
        """
        return self.kit_data.get(note)

    def set_kit_type(self, kit_type: int):
        """
        Change drum kit type

        Args:
            kit_type: New kit type
        """
        if kit_type in self.XG_DRUM_KITS:
            self.kit_type = kit_type
            self.kit_data = self.XG_DRUM_KITS[kit_type].copy()

    def get_kit_name(self) -> str:
        """
        Get human-readable kit name

        Returns:
            Kit name string
        """
        kit_names = {
            self.STANDARD: "Standard",
            self.ROOM: "Room",
            self.POWER: "Power",
            self.ELECTRONIC: "Electronic",
            self.ANALOG: "Analog",
            self.JAZZ: "Jazz",
            self.BRUSH: "Brush",
            self.ORCHESTRA: "Orchestra",
            self.SFX: "SFX",
            self.CM64: "CM-64",
            self.CM32: "CM-32"
        }
        return kit_names.get(self.kit_type, "Unknown")

    @staticmethod
    def get_available_kits() -> List[Tuple[int, str]]:
        """
        Get list of available drum kits

        Returns:
            List of (kit_id, kit_name) tuples
        """
        return [
            (XGDrumKit.STANDARD, "Standard"),
            (XGDrumKit.ROOM, "Room"),
            (XGDrumKit.POWER, "Power"),
            (XGDrumKit.ELECTRONIC, "Electronic"),
            (XGDrumKit.ANALOG, "Analog"),
            (XGDrumKit.JAZZ, "Jazz"),
            (XGDrumKit.BRUSH, "Brush"),
            (XGDrumKit.ORCHESTRA, "Orchestra"),
            (XGDrumKit.SFX, "SFX"),
            (XGDrumKit.CM64, "CM-64"),
            (XGDrumKit.CM32, "CM-32")
        ]
