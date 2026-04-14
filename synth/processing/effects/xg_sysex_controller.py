"""
XG SYSEX Controller - Complete XG System Exclusive Control

Implements XG SYSEX (System Exclusive) message handling for bulk parameter
control, effect configuration dumps, and advanced XG features.

XG SYSEX Format: F0 43 [dev] 4C [cmd] [data] F7
- Manufacturer: 43 (Yamaha)
- Model: 4C (XG)
- Device ID: 0-127 (usually 0 for all devices)
- Command: Various XG commands
- Data: Command-specific data
- End: F7

Copyright (c) 2025 XG Synthesis Core
"""

from __future__ import annotations

from enum import IntEnum


class XGSYSEXCommand(IntEnum):
    """XG SYSEX Command Codes"""

    BULK_DUMP = 0x00  # Bulk parameter dump
    PARAMETER_CHANGE = 0x01  # Individual parameter change
    DUMP_REQUEST = 0x02  # Request dump
    RECEIVE_CHANNEL = 0x08  # Receive channel assignment
    EFFECT_SETUP = 0x10  # Effect setup/configuration
    PRESET_DUMP = 0x20  # Effect preset dump
    SYSTEM_INFO = 0x30  # System information


class XGSYSEXController:
    """
    XG SYSEX Controller - Complete System Exclusive Message Handling

    Handles all XG SYSEX messages for bulk parameter control and advanced
    effect configuration. Supports effect presets, parameter dumps, and
    system configuration.
    """

    def __init__(self, effects_coordinator, nrpn_controller=None):
        """
        Initialize XG SYSEX controller.

        Args:
            effects_coordinator: XGEffectsCoordinator instance
            nrpn_controller: XGNRPNController instance (optional)
        """
        self.coordinator = effects_coordinator
        self.nrpn_controller = nrpn_controller

        # SYSEX state
        self.device_id = 0x7F  # Default to all devices (0x7F)

        # Registered SYSEX handlers
        self._register_sysex_handlers()

    def _register_sysex_handlers(self):
        """Register SYSEX command handlers."""
        self.sysex_handlers = {
            XGSYSEXCommand.BULK_DUMP: self._handle_bulk_dump,
            XGSYSEXCommand.PARAMETER_CHANGE: self._handle_parameter_change,
            XGSYSEXCommand.DUMP_REQUEST: self._handle_dump_request,
            XGSYSEXCommand.RECEIVE_CHANNEL: self._handle_receive_channel,
            XGSYSEXCommand.EFFECT_SETUP: self._handle_effect_setup,
            XGSYSEXCommand.PRESET_DUMP: self._handle_preset_dump,
            XGSYSEXCommand.SYSTEM_INFO: self._handle_system_info,
        }

    def process_sysex(self, data: list[int]) -> list[int] | None:
        """
        Process XG SYSEX message.

        Args:
            data: SYSEX data bytes (excluding F0/F7)

        Returns:
            Response SYSEX data if applicable, None otherwise
        """
        if len(data) < 4:
            return None  # Invalid XG SYSEX message

        # Parse XG SYSEX header
        manufacturer = data[0]
        model = data[1]
        device_id = data[2]
        command = data[3]

        # Validate XG SYSEX format
        if manufacturer != 0x43 or model != 0x4C:
            return None  # Not an XG SYSEX message

        # Check device ID (0x7F = all devices, or specific device)
        if device_id != 0x7F and device_id != self.device_id:
            return None  # Not for this device

        # Extract command data
        command_data = data[4:] if len(data) > 4 else []

        # Find and execute handler
        try:
            cmd_enum = XGSYSEXCommand(command)
            if cmd_enum in self.sysex_handlers:
                return self.sysex_handlers[cmd_enum](command_data)
        except ValueError:
            pass  # Invalid command, continue to unknown command message

        # Unknown command
        print(f"XG SYSEX: Unknown command 0x{command:02X}")
        return None

    def _handle_bulk_dump(self, data: list[int]) -> list[int] | None:
        """
        Handle bulk parameter dump SYSEX (F0 43 [dev] 4C 00 [data] F7).

        Applies multiple effect parameters in a single message.
        Format: [effect_type] [param_count] [param_data...]
        """
        if len(data) < 2:
            return None

        effect_type = data[0]
        param_count = data[1]

        if len(data) < 2 + param_count * 4:
            return None  # Insufficient data

        applied_params = 0
        for i in range(param_count):
            offset = 2 + i * 4
            param_id = data[offset]
            param_value = (data[offset + 1] << 7) | data[offset + 2]  # 14-bit value
            param_type = data[offset + 3]

            # Apply parameter based on effect type
            if self._apply_bulk_parameter(effect_type, param_id, param_value, param_type):
                applied_params += 1

        print(
            f"XG SYSEX: Applied {applied_params}/{param_count} bulk parameters for effect type {effect_type}"
        )
        return None  # No response needed

    def _handle_parameter_change(self, data: list[int]) -> list[int] | None:
        """
        Handle individual parameter change SYSEX (F0 43 [dev] 4C 01 [data] F7).

        Format: [effect_type] [param_id] [value_msb] [value_lsb] [param_type]
        """
        if len(data) < 5:
            return None

        effect_type = data[0]
        param_id = data[1]
        param_value = (data[2] << 7) | data[3]  # 14-bit value
        param_type = data[4]

        if self._apply_bulk_parameter(effect_type, param_id, param_value, param_type):
            print(
                f"XG SYSEX: Applied parameter {param_id} = {param_value} for effect type {effect_type}"
            )
        else:
            print(f"XG SYSEX: Failed to apply parameter {param_id} for effect type {effect_type}")

        return None

    def _handle_dump_request(self, data: list[int]) -> list[int] | None:
        """
        Handle dump request SYSEX (F0 43 [dev] 4C 02 [data] F7).

        Returns current effect configuration as SYSEX bulk dump.
        Format: [effect_type] (0xFF = all effects)
        """
        if len(data) < 1:
            return None

        effect_type = data[0]

        if effect_type == 0xFF:
            # Request all effects dump
            return self._create_full_effects_dump()
        else:
            # Request specific effect dump
            return self._create_effect_dump(effect_type)

    def _handle_receive_channel(self, data: list[int]) -> list[int] | None:
        """
        Handle receive channel assignment SYSEX (F0 43 [dev] 4C 08 [part] [channel] F7).

        This was previously handled in the synthesizer, but included here for completeness.
        """
        if len(data) < 2:
            return None

        part_id = data[0]
        midi_channel = data[1]

        # This would typically update channel routing tables
        print(f"XG SYSEX: Receive channel assignment - Part {part_id} -> MIDI CH {midi_channel}")
        return None

    def _handle_effect_setup(self, data: list[int]) -> list[int] | None:
        """
        Handle effect setup/configuration SYSEX (F0 43 [dev] 4C 10 [data] F7).

        Advanced effect configuration commands.
        """
        if len(data) < 1:
            return None

        setup_command = data[0]
        setup_data = data[1:]

        if setup_command == 0x00:  # Enable/disable effects
            return self._handle_effect_enable_disable(setup_data)
        elif setup_command == 0x01:  # Effect chain configuration
            return self._handle_effect_chain_config(setup_data)
        elif setup_command == 0x02:  # Global effect settings
            return self._handle_global_effect_settings(setup_data)

        print(f"XG SYSEX: Unknown effect setup command 0x{setup_command:02X}")
        return None

    def _handle_preset_dump(self, data: list[int]) -> list[int] | None:
        """
        Handle effect preset dump SYSEX (F0 43 [dev] 4C 20 [preset_id] [data] F7).

        Saves or loads effect presets.
        """
        if len(data) < 1:
            return None

        preset_id = data[0]
        preset_data = data[1:]

        if len(preset_data) == 0:
            # Request preset dump
            return self._create_preset_dump(preset_id)
        else:
            # Apply preset data
            return self._apply_preset_dump(preset_id, preset_data)

    def _handle_system_info(self, data: list[int]) -> list[int] | None:
        """
        Handle system information request SYSEX (F0 43 [dev] 4C 30 [info_type] F7).

        Returns system information and capabilities.
        """
        if len(data) < 1:
            return None

        info_type = data[0]

        if info_type == 0x00:  # System capabilities
            return self._create_system_capabilities()
        elif info_type == 0x01:  # Effect status
            return self._create_effect_status()
        elif info_type == 0x02:  # Firmware version
            return self._create_firmware_info()

        return None

    # ===== BULK PARAMETER APPLICATION =====

    def _apply_bulk_parameter(
        self, effect_type: int, param_id: int, param_value: int, param_type: int, part: int = 0
    ) -> bool:
        """
        Apply a bulk parameter to the appropriate effect.

        Args:
            effect_type: Effect type (0=reverb, 1=chorus, etc.)
            param_id: Parameter ID
            param_value: Parameter value (0-16383 for 14-bit)
            param_type: Parameter type/subtype
            part: Part number (0-15), defaults to 0

        Returns:
            True if parameter was applied successfully
        """
        try:
            # Convert 14-bit value to 7-bit for coordinator methods
            value_7bit = param_value >> 7  # Take MSB only

            if effect_type == 0:  # System Reverb
                return self._apply_reverb_parameter(param_id, value_7bit)
            elif effect_type == 1:  # System Chorus
                return self._apply_chorus_parameter(param_id, value_7bit)
            elif effect_type == 2:  # System Variation
                return self._apply_variation_parameter(param_id, value_7bit)
            elif effect_type == 3:  # Master EQ
                return self._apply_eq_parameter(param_id, value_7bit)
            elif effect_type >= 4 and effect_type <= 6:  # Insertion Effects
                slot = effect_type - 4  # 0-2 for insertion slots
                return self._apply_insertion_parameter(part, slot, param_id, value_7bit)

            return False

        except Exception as e:
            print(f"XG SYSEX: Error applying bulk parameter: {e}")
            return False

    def _apply_reverb_parameter(self, param_id: int, value: int) -> bool:
        """Apply reverb parameter via coordinator."""
        param_map = {
            0: ("reverb", "type"),
            1: ("reverb", "time"),
            2: ("reverb", "level"),
            3: ("reverb", "pre_delay"),
            4: ("reverb", "hf_damping"),
            5: ("reverb", "density"),
            6: ("reverb", "early_level"),
            7: ("reverb", "tail_level"),
        }

        if param_id in param_map:
            effect, param = param_map[param_id]
            return self.coordinator.set_system_effect_parameter(effect, param, value)

        return False

    def _apply_chorus_parameter(self, param_id: int, value: int) -> bool:
        """Apply chorus parameter via coordinator."""
        param_map = {
            0: ("chorus", "type"),
            1: ("chorus", "rate"),
            2: ("chorus", "depth"),
            3: ("chorus", "feedback"),
            4: ("chorus", "level"),
        }

        if param_id in param_map:
            effect, param = param_map[param_id]
            return self.coordinator.set_system_effect_parameter(effect, param, value)

        return False

    def _apply_variation_parameter(self, param_id: int, value: int) -> bool:
        """Apply variation parameter via coordinator."""
        if param_id == 0:  # Type
            return self.coordinator.set_variation_effect_type(value)
        return False

    def _apply_eq_parameter(self, param_id: int, value: int) -> bool:
        """Apply EQ parameter via coordinator."""
        if param_id == 0:  # Type
            return self.coordinator.set_master_eq_type(value)
        return False

    def _apply_insertion_parameter(self, part: int, slot: int, param_id: int, value: int) -> bool:
        """Apply insertion effect parameter via coordinator."""
        # For now, just apply to coordinator (would need expansion for full insertion control)
        if param_id == 0:  # Effect type
            return self.coordinator.set_channel_insertion_effect(part, slot, value)
        return False

    # ===== SYSEX RESPONSE CREATION =====

    def _create_full_effects_dump(self) -> list[int]:
        """Create a full effects configuration dump."""
        # This would create a comprehensive dump of all effect parameters
        # For now, return a basic response
        dump_data = [
            0x00,  # Bulk dump command
            0x00,  # All effects
            0x01,  # Version
            0x00,  # Reserved
        ]
        return [0x43, 0x4C, self.device_id, 0x00] + dump_data

    def _create_effect_dump(self, effect_type: int) -> list[int]:
        """Create a dump for a specific effect type."""
        # Get current state from coordinator
        state = self.coordinator.get_current_state()

        dump_data = [effect_type]

        if effect_type == 0:  # Reverb
            reverb = state.get("reverb_params", {})
            dump_data.extend(
                [
                    8,  # 8 parameters
                    0,
                    reverb.get("type", 1) >> 7,
                    reverb.get("type", 1) & 0x7F,
                    0,  # Type
                    1,
                    reverb.get("time", 64) >> 7,
                    reverb.get("time", 64) & 0x7F,
                    0,  # Time
                    2,
                    reverb.get("level", 64) >> 7,
                    reverb.get("level", 64) & 0x7F,
                    0,  # Level
                    3,
                    reverb.get("pre_delay", 0) >> 7,
                    reverb.get("pre_delay", 0) & 0x7F,
                    0,  # Pre-delay
                    4,
                    reverb.get("hf_damping", 32) >> 7,
                    reverb.get("hf_damping", 32) & 0x7F,
                    0,  # HF Damping
                    5,
                    reverb.get("density", 64) >> 7,
                    reverb.get("density", 64) & 0x7F,
                    0,  # Density
                    6,
                    reverb.get("early_level", 64) >> 7,
                    reverb.get("early_level", 64) & 0x7F,
                    0,  # Early Level
                    7,
                    reverb.get("tail_level", 64) >> 7,
                    reverb.get("tail_level", 64) & 0x7F,
                    0,  # Tail Level
                ]
            )

        return [0x43, 0x4C, self.device_id, 0x00] + dump_data

    def _create_preset_dump(self, preset_id: int) -> list[int]:
        """Create a preset dump response."""
        # Build preset data from coordinator state
        dump_data = [preset_id, 0x00]  # Preset ID

        # Add reverb parameters if available
        if hasattr(self.coordinator, "system_effects") and self.coordinator.system_effects:
            reverb = self.coordinator.system_effects
            dump_data.extend(
                [
                    reverb.get("reverb_type", 1),
                    reverb.get("reverb_time", 64),
                    reverb.get("reverb_level", 64),
                ]
            )
        else:
            dump_data.extend([1, 64, 64])  # Default values

        return [0x43, 0x4C, self.device_id, 0x20] + dump_data

    def _apply_preset_dump(self, preset_id: int, data: list[int]) -> list[int] | None:
        """Apply a preset dump (would save preset configuration)."""
        print(f"XG SYSEX: Received preset {preset_id} dump ({len(data)} bytes)")
        return None

    def _create_system_capabilities(self) -> list[int]:
        """Create system capabilities response."""
        caps_data = [
            0x01,  # Version
            0x10,  # Max parts (16)
            0x04,  # Effect types supported (reverb, chorus, variation, eq)
            0x80,  # Max presets (128)
        ]
        return [0x43, 0x4C, self.device_id, 0x30] + caps_data

    def _create_effect_status(self) -> list[int]:
        """Create current effect status response."""
        state = self.coordinator.get_current_state()
        status_data = [
            state.get("processing_enabled", False),
            len(state.get("effect_units_active", [])),
            0x00,  # Reserved
        ]
        return [0x43, 0x4C, self.device_id, 0x30] + status_data

    def _create_firmware_info(self) -> list[int]:
        """Create firmware version information."""
        version_data = [
            0x02,
            0x00,
            0x00,  # Version 2.0.0
            0x58,
            0x47,  # "XG" identifier
        ]
        return [0x43, 0x4C, self.device_id, 0x30] + version_data

    # ===== UTILITY METHODS =====

    def set_device_id(self, device_id: int):
        """Set the device ID for SYSEX filtering."""
        self.device_id = device_id & 0x7F

    def get_supported_commands(self) -> list[int]:
        """Get list of supported SYSEX commands."""
        return list(self.sysex_handlers.keys())

    def create_sysex_message(self, command: int, data: list[int]) -> list[int]:
        """
        Create a properly formatted XG SYSEX message.

        Args:
            command: XG SYSEX command
            data: Command data

        Returns:
            Complete SYSEX message including F0/F7
        """
        message = [0xF0, 0x43, self.device_id, 0x4C, command] + data + [0xF7]
        return message

    # ===== IMPLEMENTED SYSEX EFFECT CONTROL METHODS =====

    def _handle_effect_enable_disable(self, data: list[int]) -> list[int] | None:
        """
        Handle effect enable/disable commands (F0 43 [dev] 4C 10 00 [data] F7).

        Format: [command] [effect_unit] [enable_flag]
        - command: 0x00 (enable/disable)
        - effect_unit: 0-9 (XG effect units CC 200-209)
        - enable_flag: 0=disable, 1=enable
        """
        if len(data) < 3:
            return None

        command = data[0]
        effect_unit = data[1]
        enable_flag = data[2]

        if command != 0x00:
            return None

        if 0 <= effect_unit <= 9:
            enabled = enable_flag != 0
            if self.coordinator.set_effect_unit_activation(effect_unit, enabled):
                print(f"XG SYSEX: Effect unit {effect_unit} {'enabled' if enabled else 'disabled'}")
                return None

        print(f"XG SYSEX: Invalid effect unit {effect_unit} or enable flag {enable_flag}")
        return None

    def _handle_effect_chain_config(self, data: list[int]) -> list[int] | None:
        """
        Handle effect chain configuration (F0 43 [dev] 4C 10 01 [data] F7).

        Format: [command] [chain_type] [param_count] [params...]
        - command: 0x01 (chain config)
        - chain_type: 0=insertion, 1=variation, 2=system
        - param_count: number of parameters
        - params: parameter data
        """
        if len(data) < 3:
            return None

        command = data[0]
        chain_type = data[1]
        param_count = data[2]

        if command != 0x01 or len(data) < 3 + param_count:
            return None

        params = data[3 : 3 + param_count]

        if chain_type == 0:  # Insertion chain
            # Configure insertion effect routing
            if len(params) >= 2:
                channel = params[0]
                effect_type = params[1]
                if self.coordinator.set_channel_insertion_effect(channel, 0, effect_type):
                    print(
                        f"XG SYSEX: Set insertion effect for channel {channel} to type {effect_type}"
                    )
                    return None

        elif chain_type == 1:  # Variation chain
            # Configure variation effect type
            if len(params) >= 1:
                variation_type = params[0]
                if self.coordinator.set_variation_effect_type(variation_type):
                    print(f"XG SYSEX: Set variation effect to type {variation_type}")
                    return None

        elif chain_type == 2:  # System chain
            # Configure system effect parameters
            if len(params) >= 3:
                effect_type = params[0]  # 0=reverb, 1=chorus
                param_id = params[1]
                param_value = params[2]

                effect_name = "reverb" if effect_type == 0 else "chorus"
                param_names = {
                    0: ("reverb", "type") if effect_type == 0 else ("chorus", "type"),
                    1: ("reverb", "time") if effect_type == 0 else ("chorus", "rate"),
                    2: ("reverb", "level") if effect_type == 0 else ("chorus", "depth"),
                    3: ("reverb", "hf_damping") if effect_type == 0 else ("chorus", "feedback"),
                }

                if param_id in param_names:
                    effect, param = param_names[param_id]
                    if self.coordinator.set_system_effect_parameter(effect, param, param_value):
                        print(f"XG SYSEX: Set {effect} {param} to {param_value}")
                        return None

        print(f"XG SYSEX: Unknown chain configuration type {chain_type}")
        return None

    def _handle_global_effect_settings(self, data: list[int]) -> list[int] | None:
        """
        Handle global effect settings (F0 43 [dev] 4C 10 02 [data] F7).

        Format: [command] [setting_type] [value_msb] [value_lsb]
        - command: 0x02 (global settings)
        - setting_type: 0=master level, 1=wet/dry mix, 2=processing enable
        - value: 14-bit parameter value
        """
        if len(data) < 4:
            return None

        command = data[0]
        setting_type = data[1]
        value_msb = data[2]
        value_lsb = data[3]
        value_14bit = (value_msb << 7) | value_lsb
        value_norm = value_14bit / 16383.0  # Normalize to 0.0-1.0

        if command != 0x02:
            return None

        if setting_type == 0:  # Master level
            master_level = value_norm * 2.0  # 0-2.0 range
            if self.coordinator.set_master_controls(level=master_level):
                print(f"XG SYSEX: Set master level to {master_level:.2f}")
                return None

        elif setting_type == 1:  # Wet/dry mix
            wet_dry_mix = value_norm
            if self.coordinator.set_master_controls(wet_dry=wet_dry_mix):
                print(f"XG SYSEX: Set wet/dry mix to {wet_dry_mix:.2f}")
                return None

        elif setting_type == 2:  # Processing enable/disable
            enabled = value_14bit > 0
            # Note: Coordinator doesn't have a direct enable/disable method
            # This would need to be implemented at a higher level
            print(
                f"XG SYSEX: Processing {'enabled' if enabled else 'disabled'} (not yet implemented)"
            )
            return None

        elif setting_type == 3:  # Master EQ type
            eq_type = min(4, int(value_norm * 5))  # 0-4 range
            if self.coordinator.set_master_eq_type(eq_type):
                print(f"XG SYSEX: Set master EQ type to {eq_type}")
                return None

        print(f"XG SYSEX: Unknown global setting type {setting_type}")
        return None
