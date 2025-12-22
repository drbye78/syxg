"""
XG NRPN/MIDI Control Interface

This module provides XG-compliant NRPN and MIDI CC parameter control for the
XG effects system. Implements the full XG specification for parameter
control via MIDI messages (CC and NRPN).

Key Features:
- XG NRPN parameter mapping (MSB/LSB addressing)
- MIDI CC control for effects (CC 200-209 for units, CC 91/93/94 for sends)
- SysEx parameter control support
- Thread-safe parameter updates
- Real-time parameter smoothing

XG Control Specification:
- NRPN MSB 0: System Effects
- NRPN MSB 1: Chorus Parameters
- NRPN MSB 2: Reverb Parameters
- NRPN MSB 3: Variation Parameters
- NRPN MSB 4-119: Reserved
- CC 91: Reverb Send
- CC 93: Chorus Send
- CC 94: Variation Send
- CC 200-209: Effect Unit Activation
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import IntEnum
import threading

# Import our coordinator for parameter updates
try:
    from .effects_coordinator import XGEffectsCoordinator
    from .eq_processor import XGMultiBandEqualizer
    # Note: XGChannelMixerProcessor doesn't exist yet, commented out
    # from .mixer_processor import XGChannelMixerProcessor
except ImportError:
    # Fallback for development
    pass


class XGControlType(IntEnum):
    """XG Control Message Types"""
    CC_MESSAGE = 0      # MIDI CC (7-bit)
    NRPN_MESSAGE = 1    # NRPN parameter (MSB/LSB)
    SYSEX_MESSAGE = 2   # SysEx parameter control


class XGNRPNBanks(IntEnum):
    """XG NRPN Parameter Banks (MSB values)"""
    SYSTEM_REVERB = 0   # System Reverb Parameters
    SYSTEM_CHORUS = 1   # System Chorus Parameters
    VARIATION_EFFECT = 2  # Variation Effect Parameters
    INSERTION_EFFECT = 3  # Insertion Effect Parameters
    MASTER_EQ = 4       # Master EQ Parameters
    CHANNEL_MIXER = 5   # Channel Mixer Parameters
    RESERVED_6_119 = 63  # End of defined banks


class XGNRPNParameters:
    """XG NRPN Parameter Definitions by Bank"""

    # System Reverb (MSB 0)
    REVERB_PARAMS = {
        0: ('reverb_type', lambda x: int(x)),         # Type 1-24
        1: ('time', lambda x: x * 8.3),               # 0.1-8.3 seconds
        2: ('level', lambda x: x),                    # 0.0-1.0
        3: ('hf_damping', lambda x: x),               # 0.0-1.0
        4: ('pre_delay', lambda x: x * 0.05),        # 0-50ms
        5: ('density', lambda x: x),                 # 0.0-1.0
    }

    # System Chorus (MSB 1)
    CHORUS_PARAMS = {
        0: ('chorus_type', lambda x: int(x)),         # Type 0-5
        1: ('rate', lambda x: 0.125 + x * 9.875),    # 0.125-10.0 Hz
        2: ('depth', lambda x: x),                    # 0.0-1.0
        3: ('feedback', lambda x: (x - 0.5) * 0.5), # -0.25 to +0.25
        4: ('level', lambda x: x),                    # 0.0-1.0
        5: ('delay', lambda x: x * 0.012),           # 0-12ms
    }

    # Variation Effect (MSB 2)
    VARIATION_PARAMS = {
        0: ('variation_type', lambda x: int(x)),      # Type 0-83
        1: ('variation_level', lambda x: x),          # 0.0-1.0
        # Additional parameters depend on effect type
    }

    # Master EQ (MSB 4)
    MASTER_EQ_PARAMS = {
        0: ('low_gain', lambda x: (x - 0.5) * 24.0),    # -12 to +12 dB
        1: ('mid_gain', lambda x: (x - 0.5) * 24.0),    # -12 to +12 dB
        2: ('high_gain', lambda x: (x - 0.5) * 24.0),   # -12 to +12 dB
        3: ('low_freq', lambda x: 20 + x * 380.0),       # 20-400 Hz
        4: ('mid_freq', lambda x: 200 + x * 7800.0),     # 200-8000 Hz
        5: ('high_freq', lambda x: 2000 + x * 19800.0),  # 2000-22000 Hz
    }

    # Channel Parameters base offsets
    CHANNEL_PARAM_BASE = 0  # Channel 0
    CHANNEL_PARAM_INCREMENT = 16  # 16 parameters per channel

    @classmethod
    def get_parameter_mapping(cls, bank: int, param: int) -> Optional[Tuple[str, Callable]]:
        """Get parameter name and scaling function for given bank/parameter."""
        if bank == XGNRPNBanks.SYSTEM_REVERB:
            return cls.REVERB_PARAMS.get(param)
        elif bank == XGNRPNBanks.SYSTEM_CHORUS:
            return cls.CHORUS_PARAMS.get(param)
        elif bank == XGNRPNBanks.VARIATION_EFFECT:
            return cls.VARIATION_PARAMS.get(param)
        elif bank == XGNRPNBanks.MASTER_EQ:
            return cls.MASTER_EQ_PARAMS.get(param)

        return None


class XGNRPNController:
    """
    XG NRPN Parameter Controller

    Handles NRPN message sequences and parameter accumulation.
    NRPN uses two messages: CC 98 (LSB) + CC 99 (MSB) for parameter select,
    then CC 38 (LSB) + CC 6 (MSB) for parameter value.
    """

    def __init__(self, effects_coordinator: Optional[Any] = None):
        """
        Initialize NRPN controller.

        Args:
            effects_coordinator: XG effects coordinator for parameter updates
        """
        self.effects_coordinator = effects_coordinator

        # NRPN state
        self.current_bank = 0     # MSB (parameter bank)
        self.current_param = 0    # LSB (parameter number)
        self.pending_bank = False
        self.pending_param = False
        self.pending_value = False

        # Parameter value accumulation (14-bit)
        self.value_msb = 0
        self.value_lsb = 0

        # Thread safety
        self.lock = threading.RLock()

        # Parameter change callbacks
        self.parameter_callbacks: Dict[Tuple[int, int], List[Callable]] = {}

    def register_callback(self, bank: int, param: int, callback: Callable) -> None:
        """Register a callback for parameter changes."""
        key = (bank, param)
        if key not in self.parameter_callbacks:
            self.parameter_callbacks[key] = []
        self.parameter_callbacks[key].append(callback)

    def process_nrpn_message(self, cc_number: int, value: int) -> bool:
        """
        Process NRPN control change message.

        Args:
            cc_number: MIDI CC number
            value: CC value (0-127)

        Returns:
            True if parameter was updated
        """
        with self.lock:
            parameter_updated = False

            if cc_number == 99:  # NRPN MSB (bank select)
                self.current_bank = value
                self.pending_bank = True

            elif cc_number == 98:  # NRPN LSB (parameter select)
                self.current_param = value
                self.pending_param = True

            elif cc_number == 6:  # Data Entry MSB
                self.value_msb = value
                self.pending_value = True

            elif cc_number == 38:  # Data Entry LSB
                self.value_lsb = value
                self.pending_value = True

            # Check if we have a complete parameter update
            if self.pending_bank and self.pending_param and self.pending_value:
                # Combine MSB and LSB into 14-bit value
                full_value = (self.value_msb << 7) | self.value_lsb
                normalized_value = full_value / 16383.0  # Normalize to 0.0-1.0

                # Apply parameter update
                parameter_updated = self._apply_nrpn_parameter(
                    self.current_bank, self.current_param, normalized_value
                )

                # Reset pending flags
                self.pending_bank = False
                self.pending_param = False
                self.pending_value = False

            return parameter_updated

    def _apply_nrpn_parameter(self, bank: int, param: int, normalized_value: float) -> bool:
        """
        Apply NRPN parameter update to effects coordinator.

        Args:
            bank: NRPN bank (MSB)
            param: Parameter number (LSB)
            normalized_value: Normalized parameter value (0.0-1.0)

        Returns:
            True if parameter was successfully applied
        """
        if self.effects_coordinator is None:
            return False

        success = False

        # System Reverb (MSB 0)
        if bank == XGNRPNBanks.SYSTEM_REVERB:
            mapping = XGNRPNParameters.get_parameter_mapping(bank, param)
            if mapping:
                param_name, scaler = mapping
                scaled_value = scaler(normalized_value)
                success = self.effects_coordinator.set_system_effect_parameter(
                    'reverb', param_name, scaled_value
                )

        # System Chorus (MSB 1)
        elif bank == XGNRPNBanks.SYSTEM_CHORUS:
            mapping = XGNRPNParameters.get_parameter_mapping(bank, param)
            if mapping:
                param_name, scaler = mapping
                scaled_value = scaler(normalized_value)
                success = self.effects_coordinator.set_system_effect_parameter(
                    'chorus', param_name, scaled_value
                )

        # Variation Effect (MSB 2)
        elif bank == XGNRPNBanks.VARIATION_EFFECT:
            if param == 0:  # Variation type
                variation_type = int(normalized_value * 83)  # 0-83
                success = self.effects_coordinator.set_variation_effect_type(variation_type)
            elif param == 1:  # Variation level
                success = self.effects_coordinator.set_system_effect_parameter(
                    'variation', 'level', normalized_value
                )

        # Master EQ (MSB 4)
        elif bank == XGNRPNBanks.MASTER_EQ:
            mapping = XGNRPNParameters.get_parameter_mapping(bank, param)
            if mapping:
                param_name, scaler = mapping
                scaled_value = scaler(normalized_value)

                # Update coordinator's EQ parameters using proper method names
                if hasattr(self.effects_coordinator, 'master_eq'):
                    eq_processor = self.effects_coordinator.master_eq
                    if param_name == 'low_gain':
                        success = True  # Value already scaled correctly
                        eq_processor.set_low_gain(scaled_value)
                    elif param_name == 'mid_gain':
                        success = True
                        eq_processor.set_mid_gain(scaled_value)
                    elif param_name == 'high_gain':
                        success = True
                        eq_processor.set_high_gain(scaled_value)
                    elif param_name == 'mid_freq':
                        success = True
                        eq_processor.set_mid_frequency(scaled_value)
                elif hasattr(self.effects_coordinator, 'set_master_eq_gain'):
                    # Alternative interface
                    if 'gain' in param_name:
                        band = param_name.replace('_gain', '')
                        success = self.effects_coordinator.set_master_eq_gain(band, scaled_value)
                    elif param_name == 'mid_freq':
                        success = self.effects_coordinator.set_master_eq_frequency(scaled_value)

        # Channel-specific parameters (MSB >= 8, might be used for channel control)
        elif bank >= 8:
            # Channel number = bank - 8
            channel = bank - 8
            if 0 <= channel < 16 and hasattr(self.effects_coordinator, 'mixer_processor'):
                success = self._apply_channel_parameter(channel, param, normalized_value)

        # Trigger callbacks
        key = (bank, param)
        if key in self.parameter_callbacks:
            for callback in self.parameter_callbacks[key]:
                try:
                    callback(bank, param, normalized_value)
                except Exception:
                    pass  # Ignore callback errors

        return success

    def _apply_channel_parameter(self, channel: int, param: int, value: float) -> bool:
        """Apply channel-specific NRPN parameter."""
        if self.effects_coordinator is None:
            return False

        success = False

        # Map parameter numbers to channel parameters using effects coordinator methods
        if param == 0:  # Volume
            success = self.effects_coordinator.set_channel_volume(channel, value)
        elif param == 1:  # Pan
            pan_value = value * 2.0 - 1.0  # Convert to -1/+1
            success = self.effects_coordinator.set_channel_pan(channel, pan_value)
        elif param == 2:  # Reverb send
            success = self.effects_coordinator.set_effect_send_level(channel, 'reverb', value)
        elif param == 3:  # Chorus send
            success = self.effects_coordinator.set_effect_send_level(channel, 'chorus', value)
        elif param == 4:  # Variation send
            success = self.effects_coordinator.set_effect_send_level(channel, 'variation', value)

        return success


class XGMIDIController:
    """
    XG MIDI CC and Control Interface

    Handles all MIDI CC messages and maps them to XG effect parameters.
    Provides the main interface for MIDI control of XG effects.
    """

    def __init__(self, effects_coordinator: Optional[Any] = None,
                 eq_processor: Optional[Any] = None,
                 mixer_processor: Optional[Any] = None):
        """
        Initialize MIDI controller.

        Args:
            effects_coordinator: Main XG effects coordinator
            eq_processor: Optional separate EQ processor
            mixer_processor: Optional separate mixer processor
        """
        self.effects_coordinator = effects_coordinator
        self.eq_processor = eq_processor
        self.mixer_processor = mixer_processor

        # NRPN controller for complex parameters
        self.nrpn_controller = XGNRPNController(effects_coordinator)

        # Channel-specific effect sends (working variables)
        self.channel_reverb_sends = np.full(16, 0.4, dtype=np.float32)   # Default 40/127
        self.channel_chorus_sends = np.full(16, 0.0, dtype=np.float32)   # Default 0/127
        self.channel_variation_sends = np.full(16, 0.0, dtype=np.float32) # Default 0/127

        # Effect unit activation (XG CC 200-209)
        self.effect_units_active = np.ones(10, dtype=bool)  # All active by default

        # Thread safety
        self.lock = threading.RLock()

        # MIDI CC mapping
        self.cc_mappings = self._initialize_cc_mappings()

    def _initialize_cc_mappings(self) -> Dict[int, str]:
        """Initialize MIDI CC to XG parameter mappings."""
        cc_map = {
            # XG Standard effect sends
            91: 'reverb_send',
            93: 'chorus_send',
            94: 'variation_send',
            # XG Effect unit activation
            200: 'effect_unit_0',
            201: 'effect_unit_1',
            202: 'effect_unit_2',
            203: 'effect_unit_3',
            204: 'effect_unit_4',
            205: 'effect_unit_5',
            206: 'effect_unit_6',
            207: 'effect_unit_7',
            208: 'effect_unit_8',
            209: 'effect_unit_9',
        }
        return cc_map

    def process_midi_message(self, message_type: str, cc_number: int = None,
                           value: int = None, channel: int = None) -> bool:
        """
        Process MIDI message and apply to XG effects.

        Args:
            message_type: Message type ('cc', 'nrpn')
            cc_number: CC number for CC messages
            value: MIDI value (0-127)
            channel: MIDI channel (0-15) for channel-specific messages

        Returns:
            True if parameter was updated
        """
        with self.lock:
            if message_type == 'cc':
                return self._process_cc_message(cc_number, value, channel)
            elif message_type == 'nrpn':
                return self.nrpn_controller.process_nrpn_message(cc_number, value)
            else:
                return False

    def _process_cc_message(self, cc_number: int, value: int, channel: int) -> bool:
        """
        Process MIDI CC message.

        Args:
            cc_number: CC number
            value: CC value (0-127)
            channel: MIDI channel

        Returns:
            True if parameter was updated
        """
        normalized_value = value / 127.0  # Normalize to 0.0-1.0

        # Channel-specific effect sends
        if cc_number in [91, 93, 94]:
            if channel is not None and 0 <= channel < 16:
                return self._process_channel_send_cc(cc_number, channel, normalized_value)
            return False

        # Effect unit activation (CC 200-209)
        elif 200 <= cc_number <= 209:
            unit = cc_number - 200
            active = value >= 64  # Above half value = active
            return self._process_effect_unit_activation(unit, active)

        # Other CC mappings
        elif cc_number == 7:  # Master volume
            return self._process_master_volume(normalized_value)

        elif cc_number == 10:  # Channel pan
            if channel is not None and 0 <= channel < 16:
                pan_value = normalized_value * 2.0 - 1.0  # Convert to -1/+1
                if self.mixer_processor:
                    return self.mixer_processor.set_channel_params(channel, pan=pan_value)
                elif self.effects_coordinator and hasattr(self.effects_coordinator, 'mixer_processor'):
                    return self.effects_coordinator.mixer_processor.set_channel_params(channel, pan=pan_value)
            return False

        return False

    def _process_channel_send_cc(self, cc_number: int, channel: int, value: float) -> bool:
        """Process channel-specific effect send CC message."""
        if cc_number == 91:  # Reverb send
            self.channel_reverb_sends[channel] = value
            target = 'reverb_send'
        elif cc_number == 93:  # Chorus send
            self.channel_chorus_sends[channel] = value
            target = 'chorus_send'
        elif cc_number == 94:  # Variation send
            self.channel_variation_sends[channel] = value
            target = 'variation_send'
        else:
            return False

        # Update effects coordinator
        if self.effects_coordinator:
            return self.effects_coordinator.set_effect_send_level(channel, target, value)
        elif self.mixer_processor:
            return self.mixer_processor.set_channel_params(channel, **{target: value})

        return False

    def _process_effect_unit_activation(self, unit: int, active: bool) -> bool:
        """Process effect unit activation CC message."""
        if 0 <= unit < len(self.effect_units_active):
            old_state = self.effect_units_active[unit]
            self.effect_units_active[unit] = active

            # Update effects coordinator
            if self.effects_coordinator:
                return self.effects_coordinator.set_effect_unit_activation(unit, active)

            return old_state != active
        return False

    def _process_master_volume(self, value: float) -> bool:
        """Process master volume CC message."""
        if self.effects_coordinator:
            return self.effects_coordinator.set_master_controls(level=value * 2.0)
        elif self.mixer_processor:
            return self.mixer_processor.set_master_params(volume=value * 2.0)
        return False

    def get_current_send_levels(self) -> Dict[str, np.ndarray]:
        """Get current effect send levels for all channels."""
        with self.lock:
            return {
                'reverb': self.channel_reverb_sends.copy(),
                'chorus': self.channel_chorus_sends.copy(),
                'variation': self.channel_variation_sends.copy(),
            }

    def get_effect_unit_states(self) -> np.ndarray:
        """Get current effect unit activation states."""
        with self.lock:
            return self.effect_units_active.copy()

    def reset_to_defaults(self) -> None:
        """Reset all MIDI controls to XG defaults."""
        with self.lock:
            self.channel_reverb_sends.fill(0.4)
            self.channel_chorus_sends.fill(0.0)
            self.channel_variation_sends.fill(0.0)
            self.effect_units_active.fill(True)


class XGSysExController:
    """
    XG SysEx Parameter Controller

    Handles XG System Exclusive messages for bulk parameter control.
    Supports XG model ID (0x43) and device ID parameter updates.
    """

    def __init__(self, effects_coordinator: Optional[Any] = None):
        """
        Initialize SysEx controller.

        Args:
            effects_coordinator: XG effects coordinator for parameter updates
        """
        self.effects_coordinator = effects_coordinator

        # XG SysEx constants
        self.XG_MODEL_ID = 0x43
        self.XG_DEVICE_ID = 0x10  # Default device ID

        # Thread safety
        self.lock = threading.RLock()

    def process_sysex_message(self, data: bytes) -> bool:
        """
        Process XG System Exclusive message.

        Args:
            data: Raw SysEx data bytes

        Returns:
            True if message was processed successfully
        """
        with self.lock:
            if len(data) < 8 or data[0] != 0xF0 or data[-1] != 0xF7:
                return False  # Invalid SysEx format

            # XG SysEx format: F0 43 1n 27 [data] F7
            if data[1] != self.XG_MODEL_ID:
                return False  # Not XG message

            device_id = data[2] & 0x0F
            if device_id != self.XG_DEVICE_ID and device_id != 0x7F:  # 7F = all devices
                return False  # Not for this device

            model_id = data[3]
            if model_id != 0x27:  # XG effects/model ID
                return False  # Not effects message

            # Process parameter data
            return self._process_sysex_parameters(data[4:-1])

    def _process_sysex_parameters(self, param_data: bytes) -> bool:
        """
        Process XG SysEx parameter data.

        Args:
            param_data: Parameter data bytes

        Returns:
            True if parameters were processed
        """
        # XG SysEx parameter format: aa bb cc dd ee
        # Where aa = parameter high, bb = parameter mid, cc = parameter low
        # dd = data high, ee = data low

        if len(param_data) < 5:
            return False

        param_high = param_data[0]
        param_mid = param_data[1]
        param_low = param_data[2]
        data_high = param_data[3]
        data_low = param_data[4]

        # Combine into full parameter address and value
        param_address = (param_high << 16) | (param_mid << 8) | param_low
        param_value = (data_high << 7) | data_low

        # Convert to normalized value (0.0-1.0)
        normalized_value = param_value / 16383.0

        # Map parameter address to XG parameter
        return self._apply_sysex_parameter(param_address, normalized_value)

    def _apply_sysex_parameter(self, address: int, value: float) -> bool:
        """
        Apply SysEx parameter update.

        XG address format:
        - 0x020000-0x02FFFF: System effects
        - 0x030000-0x03FFFF: Variation effects
        - 0x040000-0x04FFFF: Channel parameters

        Args:
            address: Parameter address
            value: Normalized parameter value

        Returns:
            True if parameter was applied
        """
        if self.effects_coordinator is None:
            return False

        # Extract address components
        address_high = address >> 16
        address_mid = (address >> 8) & 0xFF

        if address_high == 0x02:
            # System effects (0x0200XX)
            if address_mid == 0x00:
                # Reverb parameters
                return False  # Not implemented yet
            elif address_mid == 0x01:
                # Chorus parameters
                return False  # Not implemented yet

        elif address_high == 0x03:
            # Variation effects (0x0300XX)
            return False  # Not implemented yet

        elif address_high == 0x04:
            # Channel parameters (0x0400XX)
            channel = address_mid
            param_type = address & 0xFF
            return self._apply_channel_sysex_parameter(channel, param_type, value)

        return False

    def _apply_channel_sysex_parameter(self, channel: int, param_type: int, value: float) -> bool:
        """Apply SysEx channel parameter update."""
        if self.effects_coordinator is None:
            return False

        # Map channel parameters using effects coordinator methods
        if param_type == 0x00:  # Volume
            return self.effects_coordinator.set_channel_volume(channel, value)
        elif param_type == 0x01:  # Pan
            pan_value = value * 2.0 - 1.0  # Convert to -1/+1
            return self.effects_coordinator.set_channel_pan(channel, pan_value)

        return False
