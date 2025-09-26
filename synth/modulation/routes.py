"""
Modulation routes for XG synthesizer.
Defines modulation route configuration and processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class ModulationRoute:
    """Modulation route in the modulation matrix"""
    def __init__(self, source, destination, amount=0.0, polarity=1.0,
                 velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Initialization of modulation route

        Args:
            source: modulation source (from ModulationSource)
            destination: modulation destination (from ModulationDestination)
            amount: modulation depth (0.0-1.0)
            polarity: polarity (1.0 or -1.0)
            velocity_sensitivity: velocity sensitivity (0.0-1.0)
            key_scaling: note height dependency (-1.0-1.0)
        """
        self.source = source
        self.destination = destination
        self.amount = amount
        self.polarity = polarity
        self.velocity_sensitivity = velocity_sensitivity
        self.key_scaling = key_scaling

    def get_modulation_value(self, source_value, velocity, note):
        """
        Getting modulation value for this route

        Args:
            source_value: current source value
            velocity: key press velocity (0-127)
            note: MIDI note (0-127)

        Returns:
            modulation value
        """
        # Applying polarity
        value = source_value * self.polarity * self.amount

        # Applying velocity sensitivity
        if self.velocity_sensitivity != 0.0:
            velocity_factor = (velocity / 127.0) ** (1.0 + self.velocity_sensitivity)
            value *= velocity_factor

        # Applying key scaling
        if self.key_scaling != 0.0:
            # Note normalization (60 = C3)
            note_factor = (note - 60) / 60.0
            key_factor = 1.0 + note_factor * self.key_scaling
            value *= max(0.1, key_factor)

        return value
