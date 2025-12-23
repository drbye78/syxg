"""
Yamaha Arpeggiator NRPN Controller

NRPN parameter control for Yamaha Motif arpeggiator parameters.
Implements 14-bit parameter resolution for precise arpeggiator control.

Copyright (c) 2025
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
import threading


class YamahaArpeggiatorNRPNController:
    """
    Yamaha Arpeggiator NRPN Parameter Controller

    Handles NRPN (Non-Registered Parameter Number) messages for arpeggiator
    control with 14-bit parameter resolution. Provides precise control over
    all arpeggiator parameters following Yamaha Motif specifications.

    NRPN Address Space:
    - MSB 0x18-0x2F: Parts 0-15 (0x18 = Part 0, 0x19 = Part 1, etc.)
    - LSB 0x40-0x7F: Arpeggiator Parameters
    """

    def __init__(self, arpeggiator_engine):
        """
        Initialize NRPN controller.

        Args:
            arpeggiator_engine: YamahaArpeggiatorEngine instance
        """
        self.arpeggiator_engine = arpeggiator_engine
        self.lock = threading.RLock()

        # NRPN State
        self.active_nrpn = False
        self.current_msb = 0     # NRPN MSB (0-127)
        self.current_lsb = 0     # NRPN LSB (0-127)
        self.data_msb = 0        # Data MSB (0-127)
        self.data_msb_received = False

        # Parameter Map - Complete arpeggiator NRPN address space
        self.parameter_map = self._build_parameter_map()

        print("🎹 Yamaha Arpeggiator NRPN Controller: Initialized")

    def _build_parameter_map(self) -> Dict[Tuple[int, int], Dict[str, Any]]:
        """
        Build comprehensive NRPN parameter map for arpeggiator control.

        Yamaha Arpeggiator NRPN Address Space:
        MSB (0x18-0x2F): Parts 0-15
        LSB (0x40-0x7F): Arpeggiator Parameters
        """
        param_map = {}

        # Arpeggiator parameters for each part (MSB 0x18-0x2F = Parts 0-15)
        arp_params = {
            0x40: {'name': 'arp_switch', 'range': (0, 1), 'default': 0, 'unit': 'on/off'},
            0x41: {'name': 'pattern_msb', 'range': (0, 127), 'default': 0, 'unit': 'pattern'},
            0x42: {'name': 'pattern_lsb', 'range': (0, 127), 'default': 0, 'unit': 'pattern'},
            0x43: {'name': 'hold_mode', 'range': (0, 1), 'default': 0, 'unit': 'on/off'},
            0x44: {'name': 'velocity_mode', 'range': (0, 2), 'default': 0, 'unit': 'mode'},
            0x45: {'name': 'octave_range', 'range': (1, 4), 'default': 1, 'unit': 'octaves'},
            0x46: {'name': 'gate_time', 'range': (0, 127), 'default': 102, 'unit': 'time'},  # 80% = 102
            0x47: {'name': 'swing_amount', 'range': (0, 127), 'default': 64, 'unit': 'swing'},  # 50% = 64
            0x48: {'name': 'velocity_rate', 'range': (0, 127), 'default': 100, 'unit': 'rate'},
            0x49: {'name': 'accent_velocity', 'range': (1, 127), 'default': 127, 'unit': 'velocity'},
            0x4A: {'name': 'arp_tempo', 'range': (60, 200), 'default': 120, 'unit': 'bpm'},
            0x4B: {'name': 'pattern_length', 'range': (1, 16), 'default': 1, 'unit': 'beats'},
            0x4C: {'name': 'key_mode', 'range': (0, 2), 'default': 0, 'unit': 'mode'},  # 0=Sort, 1=Thru, 2=Direct
            0x4D: {'name': 'voice_assign_mode', 'range': (0, 1), 'default': 0, 'unit': 'mode'},  # 0=Mono, 1=Poly
            0x4E: {'name': 'motif_retrigger', 'range': (0, 1), 'default': 0, 'unit': 'on/off'},
            0x4F: {'name': 'arp_zone_lower', 'range': (0, 127), 'default': 0, 'unit': 'note'},
            0x50: {'name': 'arp_zone_upper', 'range': (0, 127), 'default': 127, 'unit': 'note'},
            0x51: {'name': 'arp_zone_switch', 'range': (0, 1), 'default': 0, 'unit': 'on/off'},
            0x52: {'name': 'chord_detect_mode', 'range': (0, 1), 'default': 1, 'unit': 'on/off'},
            0x53: {'name': 'arp_unit_multiplier', 'range': (1, 8), 'default': 1, 'unit': 'multiplier'},
            0x54: {'name': 'arp_swing_offset', 'range': (-64, 63), 'default': 0, 'unit': 'offset'},
            0x55: {'name': 'arp_velocity_offset', 'range': (-64, 63), 'default': 0, 'unit': 'offset'},
            0x56: {'name': 'arp_gate_offset', 'range': (-64, 63), 'default': 0, 'unit': 'offset'},
            # Additional parameters can be added here
        }

        # Create parameter map for all 16 parts
        for part_offset in range(16):
            msb = 0x18 + part_offset  # 0x18 = Part 0, 0x19 = Part 1, etc.
            for lsb, param_info in arp_params.items():
                param_map[(msb, lsb)] = {
                    'name': f"part_{part_offset}_{param_info['name']}",
                    'part': part_offset,
                    'param_name': param_info['name'],
                    **param_info
                }

        return param_map

    def process_nrpn_message(self, controller: int, value: int) -> bool:
        """
        Process NRPN-related controller messages.

        Args:
            controller: MIDI controller number
            value: Controller value (0-127)

        Returns:
            True if NRPN message was processed
        """
        with self.lock:
            if controller == 98:  # NRPN LSB
                self.current_lsb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 99:  # NRPN MSB
                self.current_msb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 6:  # Data Entry MSB
                if self.active_nrpn:
                    if not self.data_msb_received:
                        self.data_msb = value
                        self.data_msb_received = True
                    else:
                        # Complete NRPN message received
                        data_value = (self.data_msb << 7) | value
                        success = self._process_nrpn_data(data_value)
                        self.active_nrpn = False
                        self.data_msb_received = False
                        return success

            elif controller == 96:  # Data Increment
                if self.active_nrpn:
                    # Increment current parameter value
                    current_value = self.get_current_parameter_value()
                    if current_value is not None:
                        max_val = self._get_parameter_max_value()
                        new_value = min(current_value + 1, max_val)
                        return self._process_nrpn_data(new_value)

            elif controller == 97:  # Data Decrement
                if self.active_nrpn:
                    # Decrement current parameter value
                    current_value = self.get_current_parameter_value()
                    if current_value is not None:
                        min_val = self._get_parameter_min_value()
                        new_value = max(current_value - 1, min_val)
                        return self._process_nrpn_data(new_value)

        return False

    def _process_nrpn_data(self, data_value: int) -> bool:
        """
        Process complete NRPN data value.

        Args:
            data_value: 14-bit NRPN data value (0-16383)

        Returns:
            True if parameter was processed successfully
        """
        # Convert 14-bit value to appropriate range
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.parameter_map.get(param_key)

        if not param_info:
            print(f"⚠️  Unknown arpeggiator NRPN parameter: {param_key}")
            return False

        # Convert 14-bit value to parameter range
        param_range = param_info['range']
        param_min, param_max = param_range

        if param_max > 127:
            # 14-bit parameter (tempo, etc.)
            param_value = data_value
        else:
            # 7-bit parameter - use MSB only
            param_value = data_value >> 7

        # Clamp to valid range
        param_value = max(param_min, min(param_max, param_value))

        # Process parameter based on type
        param_name = param_info['param_name']
        part = param_info['part']

        return self._set_arpeggiator_parameter(part, param_name, param_value)

    def _set_arpeggiator_parameter(self, part: int, param_name: str, value: Any) -> bool:
        """Set arpeggiator parameter for a specific part."""
        # Convert parameter names to engine parameter names
        param_mapping = {
            'arp_switch': 'enabled',
            'hold_mode': 'hold_mode',
            'velocity_mode': 'velocity_mode',
            'octave_range': 'octave_range',
            'gate_time': 'gate_time',
            'swing_amount': 'swing_amount',
            'arp_tempo': 'bpm',
            'velocity_rate': 'fixed_velocity',  # Approximation
            'accent_velocity': 'fixed_velocity',  # Approximation
        }

        engine_param = param_mapping.get(param_name, param_name)

        # Special handling for pattern selection
        if param_name in ['pattern_msb', 'pattern_lsb']:
            return self._handle_pattern_selection(part, param_name, value)

        # Set parameter in arpeggiator engine
        return self.arpeggiator_engine.set_arpeggiator_parameter(part, engine_param, value)

    def _handle_pattern_selection(self, part: int, param_type: str, value: int) -> bool:
        """Handle pattern selection (MSB/LSB combination)."""
        # This would need to store MSB/LSB and combine them
        # For now, use the value directly as pattern ID
        pattern_id = value  # Simplified - should combine MSB/LSB
        return self.arpeggiator_engine.set_pattern(part, pattern_id)

    def get_current_parameter_value(self) -> Optional[int]:
        """Get current parameter value for data increment/decrement."""
        if not self.active_nrpn:
            return None

        param_key = (self.current_msb, self.current_lsb)
        param_info = self.parameter_map.get(param_key)

        if not param_info:
            return None

        # Get current value from arpeggiator engine
        part = param_info['part']
        param_name = param_info['param_name']

        # Convert to engine parameter name
        param_mapping = {
            'arp_switch': 'enabled',
            'hold_mode': 'hold_mode',
            'velocity_mode': 'velocity_mode',
            'octave_range': 'octave_range',
            'gate_time': 'gate_time',
            'swing_amount': 'swing_amount',
            'arp_tempo': 'bpm',
        }

        engine_param = param_mapping.get(param_name, param_name)
        status = self.arpeggiator_engine.get_arpeggiator_status(part)

        if status and engine_param in status:
            value = status[engine_param]
            # Convert back to NRPN range
            param_range = param_info['range']
            param_min, param_max = param_range

            if param_max <= 127:
                # 7-bit parameter
                return int((value - param_min) / (param_max - param_min) * 16383)
            else:
                # 14-bit parameter
                return int(value)

        return None

    def _get_parameter_max_value(self) -> int:
        """Get maximum value for current parameter."""
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.parameter_map.get(param_key)
        if param_info:
            return param_info['range'][1]
        return 127

    def _get_parameter_min_value(self) -> int:
        """Get minimum value for current parameter."""
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.parameter_map.get(param_key)
        if param_info:
            return param_info['range'][0]
        return 0

    def get_parameter_info(self, msb: int, lsb: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific NRPN parameter."""
        param_key = (msb, lsb)
        return self.parameter_map.get(param_key)

    def list_parameters(self, part: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all NRPN parameters, optionally filtered by part.

        Args:
            part: Part number to filter by (None = all parts)

        Returns:
            List of parameter information dictionaries
        """
        parameters = []

        for (msb, lsb), param_info in self.parameter_map.items():
            if part is None or param_info['part'] == part:
                parameters.append({
                    'address': f'{msb:02X}:{lsb:02X}',
                    'msb': msb,
                    'lsb': lsb,
                    'part': param_info['part'],
                    **param_info
                })

        return parameters

    def get_nrpn_status(self) -> Dict[str, Any]:
        """Get current NRPN controller status."""
        with self.lock:
            return {
                'active': self.active_nrpn,
                'current_msb': self.current_msb,
                'current_lsb': self.current_lsb,
                'data_msb_received': self.data_msb_received,
                'data_msb': self.data_msb,
                'current_parameter': self.get_parameter_info(self.current_msb, self.current_lsb)
            }

    def reset_nrpn_state(self):
        """Reset NRPN controller state."""
        with self.lock:
            self.active_nrpn = False
            self.current_msb = 0
            self.current_lsb = 0
            self.data_msb = 0
            self.data_msb_received = False

    def create_nrpn_message(self, msb: int, lsb: int, value: int, channel: int = 0) -> List[bytes]:
        """
        Create NRPN message sequence for a parameter.

        Args:
            msb: NRPN MSB
            lsb: NRPN LSB
            value: 14-bit parameter value
            channel: MIDI channel

        Returns:
            List of MIDI message bytes
        """
        messages = []

        # NRPN LSB
        messages.append(bytes([0xB0 | channel, 98, lsb]))

        # NRPN MSB
        messages.append(bytes([0xB0 | channel, 99, msb]))

        # Data Entry MSB
        data_msb = (value >> 7) & 0x7F
        messages.append(bytes([0xB0 | channel, 6, data_msb]))

        # Data Entry LSB
        data_lsb = value & 0x7F
        messages.append(bytes([0xB0 | channel, 38, data_lsb]))

        return messages

    def __str__(self) -> str:
        """String representation."""
        status = self.get_nrpn_status()
        active = "Active" if status['active'] else "Inactive"
        return f"YamahaArpeggiatorNRPNController({active}, params={len(self.parameter_map)})"

    def __repr__(self) -> str:
        return self.__str__()
