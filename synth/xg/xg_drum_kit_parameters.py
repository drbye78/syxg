"""
XG Drum Kit Individual Note Parameters

This module implements XG-compliant individual drum note parameter control.
Provides access to per-drum parameters like level, pan, assign, tuning, and sends.

XG Drum Parameter Map (NRPN MSB 40-41):
- MSB 40 LSB 0-127: Level (0-127)
- MSB 40 LSB 0-127: Pan (-63 to +63, centered on 64)
- MSB 40 LSB 0-127: Assign (0=note-off, 1=poly, 2=mono)
- MSB 40 LSB 0-127: Coarse Tune (-24 to +24 semitones)
- MSB 40 LSB 0-127: Fine Tune (-50 to +50 cents)
- MSB 40 LSB 0-127: Filter Cutoff (0-127)
- MSB 40 LSB 0-127: Filter Resonance (0-127)
- MSB 40 LSB 0-127: Attack Time (0-127)
- MSB 40 LSB 0-127: Decay Time (0-127)
- MSB 41 LSB 0-127: Reverb Send (0-127)
- MSB 41 LSB 0-127: Chorus Send (0-127)

Copyright (c) 2025
"""

from typing import Dict, List, Tuple, Optional, NamedTuple, Any
import numpy as np
import threading


class XGDrumNoteParameters(NamedTuple):
    """XG Drum Note Parameter Structure"""
    level: int = 100          # 0-127 - Note level/volume
    pan: int = 64            # 0-127 - Pan position (64=center)
    assign: int = 1          # 0=note-off, 1=poly, 2=mono
    coarse_tune: int = 64    # 0-127 - Coarse tune (64=0 semitones)
    fine_tune: int = 64      # 0-127 - Fine tune (64=0 cents)
    filter_cutoff: int = 64  # 0-127 - Filter cutoff
    filter_resonance: int = 64  # 0-127 - Filter resonance
    attack_time: int = 64    # 0-127 - Envelope attack time
    decay_time: int = 64     # 0-127 - Envelope decay time
    reverb_send: int = 0     # 0-127 - Reverb send level
    chorus_send: int = 0     # 0-127 - Chorus send level


class XGDrumKitParameters:
    """
    XG Drum Kit Individual Note Parameters

    Manages per-drum parameters for XG drum kits. Each drum note (0-127)
    has individual parameters that can be controlled via NRPN MSB 40-41.
    """

    # XG Drum Parameter Types (NRPN LSB values)
    PARAM_LEVEL = 0
    PARAM_PAN = 1
    PARAM_ASSIGN = 2
    PARAM_COARSE_TUNE = 3
    PARAM_FINE_TUNE = 4
    PARAM_FILTER_CUTOFF = 5
    PARAM_FILTER_RESONANCE = 6
    PARAM_ATTACK_TIME = 7
    PARAM_DECAY_TIME = 8
    PARAM_REVERB_SEND = 9    # NRPN MSB 41
    PARAM_CHORUS_SEND = 10   # NRPN MSB 41

    # XG Drum Parameter Definitions with proper ranges and defaults
    DRUM_PARAM_DEFS = {
        PARAM_LEVEL: {
            'name': 'Level',
            'range': (0, 127),
            'default': 100,
            'description': 'Note level/volume (0=silent, 127=full)'
        },
        PARAM_PAN: {
            'name': 'Pan',
            'range': (0, 127),
            'default': 64,
            'description': 'Pan position (0=hard left, 64=center, 127=hard right)'
        },
        PARAM_ASSIGN: {
            'name': 'Assign',
            'range': (0, 2),
            'default': 1,
            'description': 'Voice assignment (0=note-off, 1=poly, 2=mono)'
        },
        PARAM_COARSE_TUNE: {
            'name': 'Coarse Tune',
            'range': (0, 127),
            'default': 64,
            'description': 'Coarse tuning in semitones (±24 semitones from 64)'
        },
        PARAM_FINE_TUNE: {
            'name': 'Fine Tune',
            'range': (0, 127),
            'default': 64,
            'description': 'Fine tuning in cents (±50 cents from 64)'
        },
        PARAM_FILTER_CUTOFF: {
            'name': 'Filter Cutoff',
            'range': (0, 127),
            'default': 64,
            'description': 'Filter cutoff frequency'
        },
        PARAM_FILTER_RESONANCE: {
            'name': 'Filter Resonance',
            'range': (0, 127),
            'default': 64,
            'description': 'Filter resonance amount'
        },
        PARAM_ATTACK_TIME: {
            'name': 'Attack Time',
            'range': (0, 127),
            'default': 64,
            'description': 'Envelope attack time'
        },
        PARAM_DECAY_TIME: {
            'name': 'Decay Time',
            'range': (0, 127),
            'default': 64,
            'description': 'Envelope decay time'
        },
        PARAM_REVERB_SEND: {
            'name': 'Reverb Send',
            'range': (0, 127),
            'default': 0,
            'description': 'Reverb send level'
        },
        PARAM_CHORUS_SEND: {
            'name': 'Chorus Send',
            'range': (0, 127),
            'default': 0,
            'description': 'Chorus send level'
        }
    }

    def __init__(self, max_drums: int = 128):
        """
        Initialize XG Drum Kit Parameters

        Args:
            max_drums: Maximum number of drum notes to support (default: 128 for full GM)
        """
        self.max_drums = max_drums

        # Parameter storage: dict of drum_note -> XGDrumNoteParameters
        self.drum_parameters: Dict[int, XGDrumNoteParameters] = {}

        # NRPN state tracking for drum parameters
        self.current_drum_note = 0  # Which drum note we are editing (0-127)
        self.nrpn_active = False

        # Initialize all drum notes with defaults
        self._initialize_default_parameters()

        # Thread safety
        self.lock = threading.RLock()

    def _initialize_default_parameters(self):
        """Initialize all drum notes with XG default parameters"""
        for drum_note in range(self.max_drums):
            self.drum_parameters[drum_note] = XGDrumNoteParameters()

    def handle_xg_drum_nrpn(self, nrpn_msb: int, nrpn_lsb: int,
                           data_msb: int, data_lsb: int) -> bool:
        """
        Handle XG Drum Kit NRPN parameters (MSB 40-41)

        Args:
            nrpn_msb: NRPN MSB (40=drum params 0-8, 41=drum params 9-10)
            nrpn_lsb: NRPN LSB - drum note number (0-127)
            data_msb: Data entry MSB - parameter type/value
            data_lsb: Data entry LSB - unused

        Returns:
            True if parameter was handled, False otherwise
        """
        if nrpn_msb not in [40, 41]:
            return False

        with self.lock:
            drum_note = nrpn_lsb  # LSB = drum note number (0-127)

            if nrpn_msb == 40:
                # MSB 40: Basic drum parameters (0-8)
                param_type = data_msb
                param_value = data_lsb  # Usually unused for drum params

                return self._set_drum_parameter(drum_note, param_type, param_value)

            elif nrpn_msb == 41:
                # MSB 41: Effect send parameters (9-10)
                if data_msb == 0:
                    # Reverb send
                    return self._set_drum_parameter(drum_note, self.PARAM_REVERB_SEND, data_lsb)
                elif data_msb == 1:
                    # Chorus send
                    return self._set_drum_parameter(drum_note, self.PARAM_CHORUS_SEND, data_lsb)

        return False

    def _set_drum_parameter(self, drum_note: int, param_type: int, value: int) -> bool:
        """
        Set a specific drum parameter for a drum note

        Args:
            drum_note: Drum note number (0-127)
            param_type: Parameter type (0-10)
            value: Parameter value (0-127)

        Returns:
            True if parameter was set, False otherwise
        """
        if drum_note >= self.max_drums or param_type not in self.DRUM_PARAM_DEFS:
            return False

        # Get current parameters for this drum note
        current_params = self.drum_parameters.get(drum_note, XGDrumNoteParameters())

        # Validate and clamp the value
        param_def = self.DRUM_PARAM_DEFS[param_type]
        min_val, max_val = param_def['range']
        clamped_value = max(min_val, min(max_val, value))

        # Create new parameter tuple with updated value
        if param_type == self.PARAM_LEVEL:
            new_params = current_params._replace(level=clamped_value)
        elif param_type == self.PARAM_PAN:
            new_params = current_params._replace(pan=clamped_value)
        elif param_type == self.PARAM_ASSIGN:
            new_params = current_params._replace(assign=clamped_value)
        elif param_type == self.PARAM_COARSE_TUNE:
            new_params = current_params._replace(coarse_tune=clamped_value)
        elif param_type == self.PARAM_FINE_TUNE:
            new_params = current_params._replace(fine_tune=clamped_value)
        elif param_type == self.PARAM_FILTER_CUTOFF:
            new_params = current_params._replace(filter_cutoff=clamped_value)
        elif param_type == self.PARAM_FILTER_RESONANCE:
            new_params = current_params._replace(filter_resonance=clamped_value)
        elif param_type == self.PARAM_ATTACK_TIME:
            new_params = current_params._replace(attack_time=clamped_value)
        elif param_type == self.PARAM_DECAY_TIME:
            new_params = current_params._replace(decay_time=clamped_value)
        elif param_type == self.PARAM_REVERB_SEND:
            new_params = current_params._replace(reverb_send=clamped_value)
        elif param_type == self.PARAM_CHORUS_SEND:
            new_params = current_params._replace(chorus_send=clamped_value)
        else:
            return False  # Unknown parameter type

        # Update the parameter storage
        self.drum_parameters[drum_note] = new_params
        return True

    def get_drum_parameter(self, drum_note: int, param_type: int) -> Optional[int]:
        """
        Get a specific drum parameter value

        Args:
            drum_note: Drum note number (0-127)
            param_type: Parameter type (0-10)

        Returns:
            Parameter value or None if not found
        """
        if drum_note >= self.max_drums:
            return None

        params = self.drum_parameters.get(drum_note)
        if params is None:
            return None

        # Extract the specific parameter
        if param_type == self.PARAM_LEVEL:
            return params.level
        elif param_type == self.PARAM_PAN:
            return params.pan
        elif param_type == self.PARAM_ASSIGN:
            return params.assign
        elif param_type == self.PARAM_COARSE_TUNE:
            return params.coarse_tune
        elif param_type == self.PARAM_FINE_TUNE:
            return params.fine_tune
        elif param_type == self.PARAM_FILTER_CUTOFF:
            return params.filter_cutoff
        elif param_type == self.PARAM_FILTER_RESONANCE:
            return params.filter_resonance
        elif param_type == self.PARAM_ATTACK_TIME:
            return params.attack_time
        elif param_type == self.PARAM_DECAY_TIME:
            return params.decay_time
        elif param_type == self.PARAM_REVERB_SEND:
            return params.reverb_send
        elif param_type == self.PARAM_CHORUS_SEND:
            return params.chorus_send

        return None

    def get_drum_parameters(self, drum_note: int) -> Optional[XGDrumNoteParameters]:
        """
        Get all parameters for a specific drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            XGDrumNoteParameters tuple or None if not found
        """
        if drum_note >= self.max_drums:
            return None
        return self.drum_parameters.get(drum_note)

    def set_drum_parameters(self, drum_note: int, parameters: XGDrumNoteParameters) -> bool:
        """
        Set all parameters for a specific drum note

        Args:
            drum_note: Drum note number (0-127)
            parameters: XGDrumNoteParameters to set

        Returns:
            True if parameters were set, False otherwise
        """
        if drum_note >= self.max_drums:
            return False

        with self.lock:
            self.drum_parameters[drum_note] = parameters
        return True

    def reset_drum_parameters(self, drum_note: int) -> bool:
        """
        Reset a drum note to XG default parameters

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            True if reset succeeded, False otherwise
        """
        if drum_note >= self.max_drums:
            return False

        with self.lock:
            self.drum_parameters[drum_note] = XGDrumNoteParameters()
        return True

    def reset_all_drum_parameters(self):
        """Reset all drum notes to XG default parameters"""
        with self.lock:
            self._initialize_default_parameters()

    def export_drum_kit_state(self, kit_number: int = 0) -> Dict[str, Any]:
        """
        Export complete drum kit state for serialization

        Args:
            kit_number: Kit number (for future multi-kit support)

        Returns:
            Dictionary containing all drum parameters
        """
        with self.lock:
            return {
                'kit_number': kit_number,
                'max_drums': self.max_drums,
                'drum_parameters': {
                    drum_note: params._asdict()
                    for drum_note, params in self.drum_parameters.items()
                    if params != XGDrumNoteParameters()  # Only export non-default values
                }
            }

    def import_drum_kit_state(self, state: Dict[str, Any]) -> bool:
        """
        Import drum kit state from dictionary

        Args:
            state: Drum kit state dictionary

        Returns:
            True if import succeeded, False otherwise
        """
        try:
            with self.lock:
                self.max_drums = state.get('max_drums', 128)
                drum_params_data = state.get('drum_parameters', {})

                # Reset to defaults first
                self._initialize_default_parameters()

                # Import individual drum parameters
                for drum_note_str, params_dict in drum_params_data.items():
                    drum_note = int(drum_note_str)
                    if drum_note < self.max_drums:
                        params = XGDrumNoteParameters(**params_dict)
                        self.drum_parameters[drum_note] = params

            return True
        except Exception:
            return False

    # XG Drum Parameter Translation Methods

    def get_drum_level_scale(self, drum_note: int) -> float:
        """
        Get level scaling factor for a drum note (0.0-1.0)

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Level scaling factor (0.0=silent, 1.0=full level)
        """
        level = self.get_drum_parameter(drum_note, self.PARAM_LEVEL)
        return (level or 100) / 127.0

    def get_drum_pan_position(self, drum_note: int) -> float:
        """
        Get pan position for a drum note (-1.0 to 1.0)

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Pan position (-1.0=left, 0.0=center, 1.0=right)
        """
        pan = self.get_drum_parameter(drum_note, self.PARAM_PAN)
        centered_pan = (pan or 64) - 64  # -64 to +63
        return centered_pan / 63.0

    def get_drum_tuning_ratio(self, drum_note: int) -> float:
        """
        Get overall tuning ratio for a drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Frequency ratio for tuning adjustment
        """
        coarse_tune = self.get_drum_parameter(drum_note, self.PARAM_COARSE_TUNE)
        fine_tune = self.get_drum_parameter(drum_note, self.PARAM_FINE_TUNE)

        # Coarse tuning: 64 = center, each step = 1 semitone
        coarse_semitones = (coarse_tune or 64) - 64
        coarse_ratio = 2.0 ** (coarse_semitones / 12.0)

        # Fine tuning: 64 = center, range ±50 cents
        fine_cents = ((fine_tune or 64) - 64) * (50.0 / 64.0)
        fine_ratio = 2.0 ** (fine_cents / 1200.0)

        return coarse_ratio * fine_ratio

    def get_drum_assign_mode(self, drum_note: int) -> int:
        """
        Get voice assignment mode for a drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Assign mode (0=note-off, 1=poly, 2=mono)
        """
        return self.get_drum_parameter(drum_note, self.PARAM_ASSIGN) or 1

    def get_drum_filter_params(self, drum_note: int) -> Tuple[float, float]:
        """
        Get filter parameters for a drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Tuple of (cutoff_ratio, resonance_ratio) both 0.0-1.0
        """
        cutoff = self.get_drum_parameter(drum_note, self.PARAM_FILTER_CUTOFF)
        resonance = self.get_drum_parameter(drum_note, self.PARAM_FILTER_RESONANCE)

        cutoff_ratio = (cutoff or 64) / 127.0
        resonance_ratio = (resonance or 64) / 127.0

        return (cutoff_ratio, resonance_ratio)

    def get_drum_envelope_params(self, drum_note: int) -> Tuple[float, float]:
        """
        Get envelope parameters for a drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Tuple of (attack_time_ratio, decay_time_ratio) both 0.0-1.0
        """
        attack = self.get_drum_parameter(drum_note, self.PARAM_ATTACK_TIME)
        decay = self.get_drum_parameter(drum_note, self.PARAM_DECAY_TIME)

        attack_ratio = (attack or 64) / 127.0
        decay_ratio = (decay or 64) / 127.0

        return (attack_ratio, decay_ratio)

    def get_drum_effect_sends(self, drum_note: int) -> Tuple[float, float]:
        """
        Get effect send levels for a drum note

        Args:
            drum_note: Drum note number (0-127)

        Returns:
            Tuple of (reverb_send, chorus_send) both 0.0-1.0
        """
        reverb = self.get_drum_parameter(drum_note, self.PARAM_REVERB_SEND)
        chorus = self.get_drum_parameter(drum_note, self.PARAM_CHORUS_SEND)

        reverb_ratio = (reverb or 0) / 127.0
        chorus_ratio = (chorus or 0) / 127.0

        return (reverb_ratio, chorus_ratio)

    def apply_xg_drum_parameters(self, drum_note: int, partial_generator) -> None:
        """
        Apply XG drum parameters to a partial generator instance

        This method translates XG drum NRPN parameters into partial generator settings.

        Args:
            drum_note: Drum note number (0-127)
            partial_generator: XGPartialGenerator instance to modify
        """
        if drum_note >= self.max_drums:
            return

        # Get all drum parameters for this note
        params = self.get_drum_parameters(drum_note)
        if params is None:
            return

        # Apply level scaling
        level_scale = params.level / 127.0
        if hasattr(partial_generator, 'level'):
            partial_generator.level *= level_scale

        # Apply pan position
        if hasattr(partial_generator, '_pan'):
            pan_pos = (params.pan - 64) / 63.0  # -1.0 to 1.0
            partial_generator._pan = pan_pos

        # Apply tuning
        if hasattr(partial_generator, '_calculate_base_frequency'):
            tuning_ratio = self.get_drum_tuning_ratio(drum_note)
            if hasattr(partial_generator, 'coarse_tune'):
                # Adjust coarse tune based on param
                coarse_offset = (params.coarse_tune - 64) / 12.0  # semitones
                partial_generator.coarse_tune += coarse_offset

        # Apply filter parameters
        if hasattr(partial_generator, 'filter_cutoff'):
            cutoff_ratio, resonance_ratio = self.get_drum_filter_params(drum_note)
            partial_generator.filter_cutoff *= cutoff_ratio

        if hasattr(partial_generator, 'filter_resonance'):
            _, resonance_ratio = self.get_drum_filter_params(drum_note)
            partial_generator.filter_resonance *= resonance_ratio

        # Apply envelope parameters
        if hasattr(partial_generator, 'amp_attack_time'):
            attack_ratio, decay_ratio = self.get_drum_envelope_params(drum_note)
            partial_generator.amp_attack_time *= attack_ratio
            partial_generator.amp_decay_time *= decay_ratio

        # Apply effect sends (would be handled by effects manager)
        # The sends are stored here and would be used during mixing

    def list_modified_drums(self) -> List[Tuple[int, XGDrumNoteParameters]]:
        """
        List all drum notes that have parameters different from XG defaults

        Returns:
            List of (drum_note, parameters) tuples for modified drums
        """
        modified_drums = []
        default_params = XGDrumNoteParameters()

        for drum_note, params in self.drum_parameters.items():
            if params != default_params:
                modified_drums.append((drum_note, params))

        return modified_drums

    def get_parameter_info(self, param_type: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a drum parameter type

        Args:
            param_type: Parameter type (0-10)

        Returns:
            Parameter information dictionary or None
        """
        return self.DRUM_PARAM_DEFS.get(param_type)

    def list_all_parameter_types(self) -> Dict[int, Dict[str, Any]]:
        """
        List all available drum parameter types with their information

        Returns:
            Dictionary mapping parameter types to their definitions
        """
        return self.DRUM_PARAM_DEFS.copy()
