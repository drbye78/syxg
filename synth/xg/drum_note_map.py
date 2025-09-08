"""
Drum note mapping for XG synthesizer.
Maps MIDI notes to drum instrument names.
"""

from typing import Dict, Optional


class DrumNoteMap:
    """Класс для отображения MIDI нот на барабанные инструменты в соответствии с XG стандартом"""

    # Стандартная карта барабанов XG
    XG_DRUM_MAP = {
        35: "Acoustic Bass Drum",
        36: "Bass Drum 1",
        37: "Side Stick",
        38: "Acoustic Snare",
        39: "Hand Clap",
        40: "Electric Snare",
        41: "Low Floor Tom",
        42: "Closed Hi Hat",
        43: "High Floor Tom",
        44: "Pedal Hi-Hat",
        45: "Low Tom",
        46: "Open Hi-Hat",
        47: "Low-Mid Tom",
        48: "Hi-Mid Tom",
        49: "Crash Cymbal 1",
        50: "High Tom",
        51: "Ride Cymbal 1",
        52: "Chinese Cymbal",
        53: "Ride Bell",
        54: "Tambourine",
        55: "Splash Cymbal",
        56: "Cowbell",
        57: "Crash Cymbal 2",
        58: "Vibra Slap",
        59: "Ride Cymbal 2",
        60: "High Bongo",
        61: "Low Bongo",
        62: "Mute High Conga",
        63: "Open High Conga",
        64: "Low Conga",
        65: "High Timbale",
        66: "Low Timbale",
        67: "High Agogo",
        68: "Low Agogo",
        69: "Cabasa",
        70: "Maracas",
        71: "Short Whistle",
        72: "Long Whistle",
        73: "Short Guiro",
        74: "Long Guiro",
        75: "Claves",
        76: "High Wood Block",
        77: "Low Wood Block",
        78: "Mute Cuica",
        79: "Open Cuica",
        80: "Mute Triangle",
        81: "Open Triangle"
    }

    def __init__(self, drum_map=None):
        """
        Инициализация карты барабанов

        Args:
            drum_map: пользовательская карта барабанов (словарь note -> имя)
        """
        if drum_map is None:
            self.drum_map = self.XG_DRUM_MAP.copy()
        else:
            self.drum_map = drum_map

    def get_instrument_name(self, note):
        """
        Получение имени инструмента по MIDI ноте

        Args:
            note: MIDI нота (0-127)

        Returns:
            имя барабанного инструмента или None
        """
        return self.drum_map.get(note, None)

    def is_drum_note(self, note):
        """
        Проверка, является ли нота барабанным инструментом

        Args:
            note: MIDI нота (0-127)

        Returns:
            True, если это барабанный инструмент, иначе False
        """
        return note in self.drum_map
