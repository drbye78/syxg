"""
XG RPN (Registered Parameter Number) Controller

This module implements XG-compliant RPN parameter support alongside NRPN.
RPN parameters provide alternative access to commonly used MIDI controls.

XG RPN Parameter Map:
- RPN 0,0: Pitch Bend Range - Pitch bend sensitivity in semitones
- RPN 0,1: Fine Tuning - Fine tuning adjustment in cents
- RPN 0,2: Coarse Tuning - Coarse tuning adjustment in semitones
- RPN 0,3: Tuning Program Select - Select tuning program
- RPN 0,4: Tuning Bank Select - Select tuning bank
- RPN 0,5: Modulation Depth Range - Mod wheel sensitivity

Copyright (c) 2025
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading


class XGRPNController:
    """
    XG RPN Parameter Controller

    Handles RPN (Registered Parameter Numbers) for XG-compliant MIDI control.
    RPN parameters provide standardized access to common MIDI functions,
    complementing the more extensive NRPN parameter set.
    """

    # XG RPN Parameter Definitions
    RPN_PARAMETERS = {
        (0, 0): {
            'name': 'Pitch Bend Range',
            'description': 'Pitch bend sensitivity in semitones (default: 2)',
            'range': (0, 24),
            'default': 2,
            'unit': 'semitones'
        },
        (0, 1): {
            'name': 'Fine Tuning',
            'description': 'Fine tuning adjustment in cents (±100 cents)',
            'range': (-100, 100),
            'default': 0,
            'unit': 'cents'
        },
        (0, 2): {
            'name': 'Coarse Tuning',
            'description': 'Coarse tuning adjustment in semitones (±24 semitones)',
            'range': (-24, 24),
            'default': 0,
            'unit': 'semitones'
        },
        (0, 3): {
            'name': 'Tuning Program Select',
            'description': 'Select tuning program (0-127)',
            'range': (0, 127),
            'default': 0,
            'unit': None
        },
        (0, 4): {
            'name': 'Tuning Bank Select',
            'description': 'Select tuning bank (0-127)',
            'range': (0, 127),
            'default': 0,
            'unit': None
        },
        (0, 5): {
            'name': 'Modulation Depth Range',
            'description': 'Mod wheel sensitivity range (0-127)',
            'range': (0, 127),
            'default': 127,
            'unit': None
        }
    }

    def __init__(self):
        """
        Initialize XG RPN Controller
        """
        # RPN state tracking
        self.rpn_msb = 0  # RPN MSB (CC 101)
        self.rpn_lsb = 0  # RPN LSB (CC 100)
        self.rpn_active = False  # RPN sequence in progress
        self.data_msb = 0  # Data Entry MSB received
        self.data_msb_received = False  # Track if Data MSB has been received

        # Current parameter values
        self.parameter_values = {}
        self._initialize_default_values()

        # Thread safety
        self.lock = threading.RLock()

    def _initialize_default_values(self):
        """Initialize RPN parameters to XG defaults"""
        for rpn_key, param_info in self.RPN_PARAMETERS.items():
            self.parameter_values[rpn_key] = param_info['default']

    def handle_rpn_message(self, controller: int, value: int) -> tuple[int, int] | None:
        """
        Handle RPN MIDI message sequence

        Args:
            controller: MIDI controller number (100=RPN LSB, 101=RPN MSB, 6=Data MSB, 38=Data LSB)
            value: Controller value (0-127)

        Returns:
            Tuple of (rpn_msb, rpn_lsb) if parameter was set, None otherwise
        """
        with self.lock:
            if controller == 101:  # RPN MSB - Start RPN sequence
                self.rpn_msb = value
                self.rpn_active = True
                self.data_msb_received = False
                return None  # Don't process as parameter yet
            elif controller == 100:  # RPN LSB
                self.rpn_lsb = value
                self.rpn_active = True
                self.data_msb_received = False
                return None  # Don't process as parameter yet
            elif controller == 6:  # Data Entry MSB
                if self.rpn_active:
                    self.data_msb = value
                    self.data_msb_received = True
                    return None  # Don't process as parameter yet
            elif controller == 38:  # Data Entry LSB - Complete RPN sequence
                if self.rpn_active and self.data_msb_received:
                    data_lsb = value
                    # Complete RPN message received
                    parameter_set = self._process_rpn_complete(self.rpn_msb, self.rpn_lsb,
                                                             self.data_msb, data_lsb)
                    # Reset RPN state
                    self.rpn_active = False
                    self.data_msb_received = False

                    if parameter_set:
                        return (self.rpn_msb, self.rpn_lsb)

            return None

    def _process_rpn_complete(self, rpn_msb: int, rpn_lsb: int,
                            data_msb: int, data_lsb: int) -> bool:
        """
        Process completed RPN message

        Args:
            rpn_msb: RPN MSB (0-127)
            rpn_lsb: RPN LSB (0-127)
            data_msb: Data entry MSB (0-127)
            data_lsb: Data entry LSB (0-127)

        Returns:
            True if parameter was processed, False otherwise
        """
        rpn_key = (rpn_msb, rpn_lsb)

        if rpn_key not in self.RPN_PARAMETERS:
            return False

        # RPN data is typically only from Data Entry MSB
        # Data Entry LSB may be used for fine control in some cases
        parameter_value = data_msb

        # Validate and clamp parameter value
        param_info = self.RPN_PARAMETERS[rpn_key]
        min_val, max_val = param_info['range']

        if param_info['name'] == 'Fine Tuning':
            # Fine tuning is signed: 0-63 = -100 to -1, 64=0, 65-127 = 1 to 100
            if data_msb < 64:
                parameter_value = data_msb - 64  # -64 to -1
            else:
                parameter_value = data_msb - 64  # 0 to 63
        elif param_info['name'] == 'Coarse Tuning':
            # Coarse tuning is signed: 0-63 = -24 to -1, 64=0, 65-127 = 1 to 63
            if data_msb < 64:
                parameter_value = data_msb - 64  # -64 to -1, but clamp to -24
            else:
                parameter_value = data_msb - 64  # 0 to 63

        # Clamp to valid range
        parameter_value = max(min_val, min(max_val, parameter_value))
        self.parameter_values[rpn_key] = parameter_value

        return True

    def get_rpn_parameter(self, rpn_msb: int, rpn_lsb: int) -> int | None:
        """
        Get current value of an RPN parameter

        Args:
            rpn_msb: RPN MSB (0-127)
            rpn_lsb: RPN LSB (0-127)

        Returns:
            Parameter value or None if parameter doesn't exist
        """
        rpn_key = (rpn_msb, rpn_lsb)
        return self.parameter_values.get(rpn_key)

    def get_all_rpn_parameters(self) -> dict[tuple[int, int], int]:
        """
        Get all current RPN parameter values

        Returns:
            Dictionary mapping (rpn_msb, rpn_lsb) to parameter values
        """
        return self.parameter_values.copy()

    def set_rpn_parameter(self, rpn_msb: int, rpn_lsb: int, value: int) -> bool:
        """
        Set an RPN parameter value programmatically

        Args:
            rpn_msb: RPN MSB (0-127)
            rpn_lsb: RPN LSB (0-127)
            value: Parameter value

        Returns:
            True if parameter was set, False otherwise
        """
        rpn_key = (rpn_msb, rpn_lsb)

        if rpn_key not in self.RPN_PARAMETERS:
            return False

        # Validate and clamp value
        param_info = self.RPN_PARAMETERS[rpn_key]
        min_val, max_val = param_info['range']
        clamped_value = max(min_val, min(max_val, value))

        with self.lock:
            self.parameter_values[rpn_key] = clamped_value

        return True

    def reset_rpn_parameters(self):
        """Reset all RPN parameters to their XG default values"""
        with self.lock:
            self._initialize_default_values()

    def get_rpn_parameter_info(self, rpn_msb: int, rpn_lsb: int) -> dict[str, Any] | None:
        """
        Get information about an RPN parameter

        Args:
            rpn_msb: RPN MSB (0-127)
            rpn_lsb: RPN LSB (0-127)

        Returns:
            Parameter information dictionary or None if parameter doesn't exist
        """
        rpn_key = (rpn_msb, rpn_lsb)
        if rpn_key not in self.RPN_PARAMETERS:
            return None

        info = self.RPN_PARAMETERS[rpn_key].copy()
        info['current_value'] = self.parameter_values.get(rpn_key, info['default'])
        return info

    def list_all_rpn_parameters(self) -> dict[tuple[int, int], dict[str, Any]]:
        """
        List all available RPN parameters with their information

        Returns:
            Dictionary mapping RPN keys to parameter information
        """
        result = {}
        for rpn_key, param_info in self.RPN_PARAMETERS.items():
            info = param_info.copy()
            info['current_value'] = self.parameter_values.get(rpn_key, info['default'])
            result[rpn_key] = info

        return result

    def export_rpn_state(self) -> dict[str, Any]:
        """
        Export complete RPN controller state for debugging/serialization

        Returns:
            Dictionary containing all RPN state information
        """
        return {
            'parameter_values': self.parameter_values.copy(),
            'rpn_state': {
                'rpn_msb': self.rpn_msb,
                'rpn_lsb': self.rpn_lsb,
                'rpn_active': self.rpn_active,
                'data_msb': self.data_msb,
                'data_msb_received': self.data_msb_received
            },
            'available_parameters': list(self.RPN_PARAMETERS.keys())
        }

    # XG-Specific RPN Parameter Applications

    def apply_pitch_bend_range(self, channel_renderer) -> None:
        """
        Apply pitch bend range RPN parameter to a channel renderer

        Args:
            channel_renderer: VectorizedChannelRenderer instance
        """
        pitch_range = self.get_rpn_parameter(0, 0)
        if pitch_range is not None:
            channel_renderer.pitch_bend_range = pitch_range

    def apply_tuning_parameters(self, channel_renderer) -> None:
        """
        Apply fine/coarse tuning RPN parameters to a channel renderer

        Args:
            channel_renderer: VectorizedChannelRenderer instance
        """
        fine_tune = self.get_rpn_parameter(0, 1)
        coarse_tune = self.get_rpn_parameter(0, 2)

        if fine_tune is not None:
            channel_renderer.fine_tune_rpn = fine_tune / 100.0  # Convert to ratio

        if coarse_tune is not None:
            channel_renderer.coarse_tune_rpn = 2.0 ** (coarse_tune / 12.0)  # Convert to frequency ratio

    def apply_modulation_range(self, channel_renderer) -> None:
        """
        Apply modulation depth range RPN parameter to a channel renderer

        Args:
            channel_renderer: VectorizedChannelRenderer instance
        """
        mod_range = self.get_rpn_parameter(0, 5)
        if mod_range is not None:
            # Scale mod wheel sensitivity 0-127
            channel_renderer.mod_wheel_range_rpn = mod_range / 127.0

    def apply_tuning_program(self, channel_renderer) -> None:
        """
        Apply tuning program/bank selection to channel renderer

        Args:
            channel_renderer: VectorizedChannelRenderer instance
        """
        program = self.get_rpn_parameter(0, 3)
        bank = self.get_rpn_parameter(0, 4)

        # This would typically interface with a tuning table system
        # For now, just store the values
        if program is not None:
            channel_renderer.tuning_program_rpn = program
        if bank is not None:
            channel_renderer.tuning_bank_rpn = bank

    def apply_all_rpn_parameters(self, channel_renderer) -> None:
        """
        Apply all current RPN parameters to a channel renderer

        Args:
            channel_renderer: VectorizedChannelRenderer instance
        """
        self.apply_pitch_bend_range(channel_renderer)
        self.apply_tuning_parameters(channel_renderer)
        self.apply_modulation_range(channel_renderer)
        self.apply_tuning_program(channel_renderer)
