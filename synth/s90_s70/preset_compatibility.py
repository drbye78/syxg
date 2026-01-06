"""
S90/S70 Preset Compatibility

Handles authentic preset compatibility, parameter mapping,
and behavior for S90/S70 synthesizer presets.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import json
import os


class S90S70PresetBank:
    """Represents a bank of S90/S70 presets"""

    def __init__(self, bank_name: str, bank_id: int, max_presets: int = 128):
        """
        Initialize preset bank.

        Args:
            bank_name: Name of the bank
            bank_id: Bank identifier
            max_presets: Maximum number of presets in bank
        """
        self.bank_name = bank_name
        self.bank_id = bank_id
        self.max_presets = max_presets
        self.presets: Dict[int, Dict[str, Any]] = {}

    def add_preset(self, preset_number: int, preset_data: Dict[str, Any]) -> bool:
        """Add preset to bank"""
        if 0 <= preset_number < self.max_presets:
            self.presets[preset_number] = preset_data.copy()
            return True
        return False

    def get_preset(self, preset_number: int) -> Optional[Dict[str, Any]]:
        """Get preset from bank"""
        return self.presets.get(preset_number)

    def clear_preset(self, preset_number: int) -> bool:
        """Clear preset from bank"""
        if preset_number in self.presets:
            del self.presets[preset_number]
            return True
        return False

    def get_bank_info(self) -> Dict[str, Any]:
        """Get bank information"""
        return {
            'name': self.bank_name,
            'id': self.bank_id,
            'max_presets': self.max_presets,
            'used_presets': len(self.presets),
            'preset_numbers': sorted(self.presets.keys())
        }


class S90S70PresetCompatibility:
    """
    S90/S70 Preset Compatibility Manager

    Provides authentic preset handling, parameter mapping, and
    compatibility features for S90/S70 synthesizers.
    """

    def __init__(self):
        """Initialize preset compatibility manager"""
        self.banks: Dict[str, S90S70PresetBank] = {}
        self.current_bank = 'USER'
        self.current_preset = 0

        # Initialize standard banks
        self._init_standard_banks()

        # Parameter mapping tables
        self._init_parameter_mappings()

        # Preset compatibility rules
        self._init_compatibility_rules()

    def _init_standard_banks(self):
        """Initialize standard S90/S70 preset banks"""

        # User bank
        self.banks['USER'] = S90S70PresetBank("User", 0, 128)

        # Preset banks (A-H, total 8 banks × 128 presets = 1024)
        for bank_char in 'ABCDEFGH':
            bank_name = f"Preset {bank_char}"
            bank_id = ord(bank_char) - ord('A') + 1
            self.banks[bank_char] = S90S70PresetBank(bank_name, bank_id, 128)

        # Drum banks (for S90/S70 drum kits)
        for i in range(1, 3):  # 2 drum banks
            bank_name = f"Drum {i}"
            self.banks[f'DRUM{i}'] = S90S70PresetBank(bank_name, 10 + i, 32)

    def _init_parameter_mappings(self):
        """Initialize parameter mapping tables for preset compatibility"""

        # S90/S70 parameter structure mapping
        self.parameter_structure = {
            'common': {
                'name': str,
                'category': str,
                'volume': (0, 127),
                'pan': (-64, 63),
                'priority': ['low', 'normal', 'high'],
                'assign_mode': ['mono', 'poly'],
                'portamento': (0, 127),
                'pitch_bend_range': (0, 12)  # semitones
            },
            'awm': {
                'element_switch': [bool, bool],  # 2 elements
                'element_level': [(0, 127), (0, 127)],
                'element_pan': [(-64, 63), (-64, 63)],
                'element_coarse_tune': [(-24, 24), (-24, 24)],
                'element_fine_tune': [(-64, 63), (-64, 63)],
                'filter_type': ['lpf', 'hpf', 'bpf', 'brf'],
                'filter_cutoff': (0, 127),
                'filter_resonance': (0, 127),
                'filter_attack': (0, 127),
                'filter_decay': (0, 127),
                'filter_sustain': (0, 127),
                'filter_release': (0, 127),
                'amplitude_attack': (0, 127),
                'amplitude_decay': (0, 127),
                'amplitude_sustain': (0, 127),
                'amplitude_release': (0, 127)
            },
            'an': {  # S90 only
                'oscillator_waveform': ['saw', 'square', 'triangle', 'sine', 'noise'],
                'oscillator_level': (0, 127),
                'oscillator_coarse_tune': (-24, 24),
                'oscillator_fine_tune': (-64, 63),
                'filter_cutoff': (0, 127),
                'filter_resonance': (0, 127),
                'filter_envelope_amount': (-64, 63),
                'amplitude_attack': (0, 127),
                'amplitude_decay': (0, 127),
                'amplitude_sustain': (0, 127),
                'amplitude_release': (0, 127)
            },
            'fdsp': {
                'phoneme': str,
                'formant_shift': (0, 127),
                'tilt': (-64, 63),
                'vibrato_rate': (0, 127),
                'vibrato_depth': (0, 127),
                'breath_level': (0, 127),
                'excitation_type': ['pulse', 'noise', 'mixed']
            },
            'effects': {
                'insertion_effect_type': (0, 17),
                'insertion_effect_param1': (0, 127),
                'insertion_effect_param2': (0, 127),
                'insertion_effect_param3': (0, 127),
                'insertion_effect_param4': (0, 127),
                'reverb_send': (0, 127),
                'chorus_send': (0, 127),
                'variation_send': (0, 127)
            }
        }

        # Compatibility mapping between different synth models
        self.compatibility_mappings = {
            'motif_xs': {
                'awm_filter_cutoff': 'awm.filter.cutoff',
                'awm_filter_resonance': 'awm.filter.resonance',
                'an_oscillator_waveform': 'an.oscillator.waveform',
                'fdsp_phoneme': 'fdsp.phoneme'
            },
            'motif_xf': {
                'awm_filter_cutoff': 'awm.filter.cutoff',
                'awm_filter_resonance': 'awm.filter.resonance',
                'an_oscillator_waveform': 'an.oscillator.waveform',
                'fdsp_phoneme': 'fdsp.phoneme',
                'flash_memory_support': True
            },
            'reface_dx': {
                'awm_filter_cutoff': 'filter.cutoff',
                'awm_filter_resonance': 'filter.resonance',
                'dx7_compatibility': True
            }
        }

    def _init_compatibility_rules(self):
        """Initialize compatibility rules for different synth models"""

        self.compatibility_rules = {
            'parameter_clamping': {
                # Some parameters have different ranges between models
                'filter_resonance_s70': (0, 100),  # S70 has less resonance range
                'filter_resonance_s90': (0, 127),  # S90 has full range
                'an_detune_s90es': (-1200, 1200),  # S90ES has wider detune range
            },
            'feature_support': {
                'an_engine': ['S90', 'S90ES'],  # Only S90 series has AN engine
                'fdsp_engine': ['S70', 'S90', 'S90ES'],  # All models have FDSP
                'insertion_effects': ['S70', 'S90', 'S90ES'],  # All have insertion effects
                'user_flash_memory': ['S90ES'],  # Only S90ES has flash memory
            },
            'voice_mode_restrictions': {
                'dual_awm_elements': ['S70', 'S90', 'S90ES'],  # All support dual elements
                'single_an_voice': ['S90', 'S90ES'],  # Only S90 series
                'fdsp_only': ['S70', 'S90', 'S90ES'],  # All support FDSP
                'drum_kits': ['S70', 'S90', 'S90ES'],  # All support drum kits
            }
        }

    def set_current_bank(self, bank_name: str) -> bool:
        """
        Set current preset bank.

        Args:
            bank_name: Bank name ('USER', 'A', 'B', etc.)

        Returns:
            True if bank exists
        """
        if bank_name in self.banks:
            self.current_bank = bank_name
            return True
        return False

    def get_current_bank(self) -> str:
        """Get current bank name"""
        return self.current_bank

    def save_preset(self, preset_number: int, preset_data: Dict[str, Any],
                   bank_name: Optional[str] = None) -> bool:
        """
        Save preset to bank.

        Args:
            preset_number: Preset number (0-127)
            preset_data: Preset parameter data
            bank_name: Bank name (uses current if None)

        Returns:
            True if saved successfully
        """
        bank = bank_name or self.current_bank
        if bank not in self.banks:
            return False

        # Validate preset data structure
        if not self._validate_preset_structure(preset_data):
            return False

        # Apply compatibility transformations
        compatible_data = self._apply_compatibility_transforms(preset_data)

        return self.banks[bank].add_preset(preset_number, compatible_data)

    def load_preset(self, preset_number: int, bank_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load preset from bank.

        Args:
            preset_number: Preset number (0-127)
            bank_name: Bank name (uses current if None)

        Returns:
            Preset data or None if not found
        """
        bank = bank_name or self.current_bank
        if bank not in self.banks:
            return None

        preset_data = self.banks[bank].get_preset(preset_number)
        if not preset_data:
            return None

        # Apply current hardware compatibility
        return self._apply_hardware_compatibility(preset_data)

    def delete_preset(self, preset_number: int, bank_name: Optional[str] = None) -> bool:
        """
        Delete preset from bank.

        Args:
            preset_number: Preset number (0-127)
            bank_name: Bank name (uses current if None)

        Returns:
            True if deleted successfully
        """
        bank = bank_name or self.current_bank
        if bank not in self.banks:
            return False

        return self.banks[bank].clear_preset(preset_number)

    def copy_preset(self, source_bank: str, source_preset: int,
                   dest_bank: str, dest_preset: int) -> bool:
        """
        Copy preset between banks.

        Args:
            source_bank: Source bank name
            source_preset: Source preset number
            dest_bank: Destination bank name
            dest_preset: Destination preset number

        Returns:
            True if copied successfully
        """
        if source_bank not in self.banks or dest_bank not in self.banks:
            return False

        preset_data = self.banks[source_bank].get_preset(source_preset)
        if not preset_data:
            return False

        return self.banks[dest_bank].add_preset(dest_preset, preset_data.copy())

    def get_bank_info(self, bank_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get information about a bank"""
        bank = bank_name or self.current_bank
        if bank not in self.banks:
            return None

        return self.banks[bank].get_bank_info()

    def get_all_bank_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all banks"""
        return {name: bank.get_bank_info() for name, bank in self.banks.items()}

    def export_bank_to_file(self, bank_name: str, filename: str) -> bool:
        """
        Export bank to JSON file.

        Args:
            bank_name: Bank to export
            filename: Output filename

        Returns:
            True if exported successfully
        """
        if bank_name not in self.banks:
            return False

        bank = self.banks[bank_name]
        export_data = {
            'bank_info': bank.get_bank_info(),
            'presets': bank.presets.copy()
        }

        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception:
            return False

    def import_bank_from_file(self, filename: str, target_bank: str) -> bool:
        """
        Import bank from JSON file.

        Args:
            filename: Input filename
            target_bank: Target bank name

        Returns:
            True if imported successfully
        """
        if target_bank not in self.banks:
            return False

        try:
            with open(filename, 'r') as f:
                import_data = json.load(f)

            bank = self.banks[target_bank]

            # Import presets
            presets = import_data.get('presets', {})
            for preset_num, preset_data in presets.items():
                if isinstance(preset_num, str):
                    preset_num = int(preset_num)
                bank.add_preset(preset_num, preset_data)

            return True
        except Exception:
            return False

    def _validate_preset_structure(self, preset_data: Dict[str, Any]) -> bool:
        """
        Validate preset data structure against S90/S70 specifications.

        Args:
            preset_data: Preset data to validate

        Returns:
            True if structure is valid
        """
        # Check required common parameters
        required_common = ['name', 'category']
        for param in required_common:
            if param not in preset_data:
                return False

        # Validate parameter ranges
        for section, params in self.parameter_structure.items():
            if section in preset_data:
                section_data = preset_data[section]
                for param_name, param_spec in params.items():
                    if param_name in section_data:
                        value = section_data[param_name]
                        if not self._validate_parameter_value(value, param_spec):
                            return False

        return True

    def _validate_parameter_value(self, value: Any, spec: Any) -> bool:
        """Validate a parameter value against its specification"""
        if isinstance(spec, tuple) and len(spec) == 2:
            # Range specification (min, max)
            min_val, max_val = spec
            return isinstance(value, (int, float)) and min_val <= value <= max_val
        elif isinstance(spec, list):
            # List of allowed values
            return value in spec
        elif isinstance(spec, type):
            # Type specification
            return isinstance(value, spec)
        elif isinstance(spec, list) and all(isinstance(item, tuple) for item in spec):
            # Multiple ranges (for multi-element parameters)
            if not isinstance(value, list) or len(value) != len(spec):
                return False
            return all(self._validate_parameter_value(v, s) for v, s in zip(value, spec))

        return True

    def _apply_compatibility_transforms(self, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply compatibility transformations to preset data.

        Args:
            preset_data: Original preset data

        Returns:
            Transformed preset data
        """
        # Make a copy to avoid modifying original
        transformed = preset_data.copy()

        # Apply parameter range clamping based on current hardware
        for section_name, section_data in transformed.items():
            if isinstance(section_data, dict):
                for param_name, param_value in section_data.items():
                    # Check for hardware-specific clamping
                    clamped_value = self._apply_parameter_clamping(param_name, param_value)
                    if clamped_value != param_value:
                        section_data[param_name] = clamped_value

        return transformed

    def _apply_hardware_compatibility(self, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply hardware compatibility transformations for loading.

        Args:
            preset_data: Preset data

        Returns:
            Hardware-compatible preset data
        """
        # For now, return as-is (could add hardware-specific adjustments later)
        return preset_data.copy()

    def _apply_parameter_clamping(self, param_name: str, param_value: Any) -> Any:
        """
        Apply parameter clamping based on hardware limitations.

        Args:
            param_name: Parameter name
            param_value: Parameter value

        Returns:
            Clamped parameter value
        """
        # Hardware-specific parameter clamping rules
        clamping_rules = {
            'awm_filter_resonance': {
                'S70': (0, 100),  # S70 has reduced resonance range
                'S90': (0, 127),  # S90 has full range
                'S90ES': (0, 127)
            },
            'an_oscillator_detune': {
                'S90': (-7, 7),    # S90 has ±7 semitone range
                'S90ES': (-12, 12) # S90ES has ±12 semitone range
            }
        }

        if param_name in clamping_rules:
            # Apply clamping based on current hardware (placeholder for now)
            # In a full implementation, this would check the current hardware profile
            return param_value

        return param_value

    def create_default_preset(self, preset_type: str = 'awm') -> Dict[str, Any]:
        """
        Create a default preset of specified type.

        Args:
            preset_type: Type of preset ('awm', 'an', 'fdsp')

        Returns:
            Default preset data
        """
        base_preset = {
            'common': {
                'name': f'Default {preset_type.upper()}',
                'category': preset_type.upper(),
                'volume': 100,
                'pan': 0,
                'priority': 'normal',
                'assign_mode': 'poly',
                'portamento': 0,
                'pitch_bend_range': 2
            },
            'effects': {
                'insertion_effect_type': 0,
                'insertion_effect_param1': 64,
                'insertion_effect_param2': 64,
                'insertion_effect_param3': 64,
                'insertion_effect_param4': 64,
                'reverb_send': 40,
                'chorus_send': 0,
                'variation_send': 0
            }
        }

        if preset_type == 'awm':
            base_preset['awm'] = {
                'element_switch': [True, False],
                'element_level': [127, 0],
                'element_pan': [0, 0],
                'element_coarse_tune': [0, 0],
                'element_fine_tune': [0, 0],
                'filter_type': 'lpf',
                'filter_cutoff': 64,
                'filter_resonance': 0,
                'filter_attack': 0,
                'filter_decay': 64,
                'filter_sustain': 64,
                'filter_release': 32,
                'amplitude_attack': 0,
                'amplitude_decay': 64,
                'amplitude_sustain': 64,
                'amplitude_release': 32
            }
        elif preset_type == 'an':
            base_preset['an'] = {
                'oscillator_waveform': 'saw',
                'oscillator_level': 127,
                'oscillator_coarse_tune': 0,
                'oscillator_fine_tune': 0,
                'filter_cutoff': 64,
                'filter_resonance': 32,
                'filter_envelope_amount': 32,
                'amplitude_attack': 0,
                'amplitude_decay': 64,
                'amplitude_sustain': 64,
                'amplitude_release': 32
            }
        elif preset_type == 'fdsp':
            base_preset['fdsp'] = {
                'phoneme': 'ə',
                'formant_shift': 64,
                'tilt': 0,
                'vibrato_rate': 64,
                'vibrato_depth': 0,
                'breath_level': 0,
                'excitation_type': 'pulse'
            }

        return base_preset

    def get_preset_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded presets"""
        total_presets = 0
        bank_usage = {}

        for bank_name, bank in self.banks.items():
            used_presets = len(bank.presets)
            total_presets += used_presets
            bank_usage[bank_name] = {
                'used': used_presets,
                'total': bank.max_presets,
                'percentage': (used_presets / bank.max_presets) * 100
            }

        return {
            'total_presets': total_presets,
            'bank_usage': bank_usage,
            'memory_usage_estimate_mb': total_presets * 0.1  # Rough estimate
        }

    def set_xg_system(self, xg_system) -> bool:
        """
        Set reference to XG system for compatibility operations.

        Args:
            xg_system: XG system instance

        Returns:
            True if set successfully
        """
        self.xg_system = xg_system
        return True
