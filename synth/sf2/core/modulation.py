"""
SF2 Modulation System

Real-time modulation matrix implementation for SF2 SoundFont processing.
Provides comprehensive modulation routing from sources to destinations.
"""

from typing import Dict, List, Any, Optional
from .types import SF2Modulator


class SF2ModulationMatrix:
    """
    SF2 Modulation Matrix Implementation

    Provides comprehensive modulation routing based on SF2 modulators.
    Supports continuous controllers, envelopes, LFOs, and other modulation sources.
    """

    def __init__(self):
        # Modulation sources (SF2 controller sources)
        self.sources = {
            0: 'none',           # No source
            2: 'note_on_velocity',  # Note-on velocity
            3: 'note_on_key',       # Note-on key number
            10: 'poly_pressure',    # Polyphonic pressure
            13: 'channel_pressure', # Channel pressure
            14: 'pitch_wheel',      # Pitch wheel
            16: 'pitch_wheel_sens', # Pitch wheel sensitivity
        }

        # Add CC sources (17-127 for CC 0-110)
        for cc in range(110):
            self.sources[17 + cc] = f'cc_{cc}'

        # Modulation destinations (SF2 generator indices)
        self.destinations = {
            7: 'pan',              # Pan
            15: 'attack_vol_env',  # Attack volume envelope
            16: 'hold_vol_env',    # Hold volume envelope
            17: 'decay_vol_env',   # Decay volume envelope
            19: 'sustain_vol_env', # Sustain volume envelope
            21: 'release_vol_env', # Release volume envelope
            25: 'delay_mod_lfo',   # Delay modulation LFO
            26: 'freq_mod_lfo',    # Frequency modulation LFO
            27: 'mod_lfo_to_pitch', # Mod LFO to pitch
            28: 'mod_lfo_to_filter', # Mod LFO to filter cutoff
            29: 'mod_lfo_to_volume', # Mod LFO to volume
            30: 'delay_vib_lfo',   # Delay vibrato LFO
            31: 'freq_vib_lfo',    # Frequency vibrato LFO
            32: 'vib_lfo_to_pitch', # Vib LFO to pitch
            34: 'initial_filter_fc', # Initial filter cutoff
            35: 'initial_filter_q',  # Initial filter Q
            43: 'instrument',      # Instrument selection
            44: 'reserved',        # Reserved
            45: 'key_range',       # Key range
            46: 'vel_range',       # Velocity range
            47: 'startloop_addrs_coarse_offset', # Loop start coarse offset
            48: 'keynum',          # Key number
            49: 'velocity',        # Velocity
            50: 'endloop_addrs_coarse_offset', # Loop end coarse offset
            51: 'coarse_tune',     # Coarse tune
            52: 'fine_tune',       # Fine tune
            53: 'sample_id',       # Sample ID
            54: 'sample_modes',    # Sample modes
            56: 'scale_tuning',    # Scale tuning
            57: 'exclusive_class', # Exclusive class
            58: 'overriding_root_key', # Overriding root key
        }

        # Active modulation connections
        self.modulations: List[Dict[str, Any]] = []

    def add_modulator(self, modulator: SF2Modulator):
        """Add a modulator to the modulation matrix."""
        source = self.sources.get(modulator.src_operator, f'unknown_{modulator.src_operator}')
        destination = self.destinations.get(modulator.dest_operator, f'unknown_{modulator.dest_operator}')

        modulation = {
            'source': source,
            'destination': destination,
            'amount': modulator.mod_amount,
            'src_amount': modulator.amt_src_operator,
            'transform': modulator.mod_trans_operator,
            'bipolar': bool(modulator.mod_trans_operator & 0x02),  # Bit 1 = bipolar
            'active': True
        }

        self.modulations.append(modulation)

    def get_modulation_amount(self, destination: str, source_value: float = 0.0) -> float:
        """Get the total modulation amount for a destination parameter."""
        total_amount = 0.0

        for mod in self.modulations:
            if mod['destination'] == destination and mod['active']:
                # Apply modulation amount (simplified - would need proper source processing)
                amount = mod['amount'] / 32768.0  # Normalize from SF2 range
                if mod['bipolar']:
                    amount = (amount * 2.0) - 1.0  # Convert to bipolar

                total_amount += amount * source_value

        return total_amount

    def update_modulation_sources(self, midi_cc: Dict[int, float], velocity: float,
                                 key: int, pitch_wheel: float):
        """Update modulation sources with current MIDI values."""
        # This would be called each synthesis block to update modulation sources
        # Implementation would update source values for modulation calculations
        pass

    def clear_modulations(self):
        """Clear all modulation connections."""
        self.modulations.clear()

    def get_active_modulations(self) -> List[Dict[str, Any]]:
        """Get list of active modulation connections."""
        return [mod for mod in self.modulations if mod['active']]

    def disable_modulation(self, index: int):
        """Disable a modulation connection by index."""
        if 0 <= index < len(self.modulations):
            self.modulations[index]['active'] = False

    def enable_modulation(self, index: int):
        """Enable a modulation connection by index."""
        if 0 <= index < len(self.modulations):
            self.modulations[index]['active'] = True
