"""
XG Synthesizer SF2 Manager

Handles SoundFont 2.0 file management and integration.
"""

from typing import List, Dict, Tuple, Optional, Union, Any
from .core.sf2_manager_v2 import SF2ManagerV2 as CoreSF2Manager


class SF2Manager:
    """
    Manages SoundFont 2.0 files and provides interface to the synthesizer.

    Provides functionality for:
    - SF2 file loading and management
    - Bank and preset blacklisting
    - Bank mapping
    - Program parameter retrieval
    - Drum parameter retrieval
    - Sample data access
    """

    def __init__(self, param_cache=None, drum_manager=None):
        """
        Initialize SF2 manager.

        Args:
            param_cache: Optional parameter cache for performance optimization
            drum_manager: Optional XG drum manager for parameter integration
        """
        self.param_cache = param_cache
        self.drum_manager = drum_manager  # Reference to XG drum manager
        self.sf2_manager = None
        self.bank_blacklists = {}
        self.preset_blacklists = {}
        self.bank_mappings = {}

    def set_sf2_files(self, sf2_paths: List[str], selective_parsing: bool = True) -> bool:
        """
        Set list of SF2 files to use.

        Args:
            sf2_paths: List of paths to SF2 files
            selective_parsing: Whether to use selective parsing for performance optimization

        Returns:
            True if successful, False otherwise
        """
        try:
            self.sf2_paths = sf2_paths.copy()

            # Create SF2 manager if we have valid paths
            if sf2_paths:
                self.sf2_manager = CoreSF2Manager()

                # Enable progressive loading for large SoundFonts
                self.sf2_manager.enable_lazy_loading()

                # Note: Mip-map cache removed in new implementation
                # for simplicity and memory efficiency

                # Load the SF2 files
                for sf2_path in sf2_paths:
                    if not self.sf2_manager.load_sf2_file(sf2_path):
                        print(f"Failed to load SF2 file: {sf2_path}")
                        return False

                # Note: The new modular SF2 system doesn't use the old bank/preset blacklists
                # and mappings. These would need to be reimplemented if still needed.

                return True
            else:
                self.sf2_manager = None
                return False

        except Exception as e:
            print(f"Error setting SF2 files: {e}")
            self.sf2_manager = None
            return False

    def load_sf2_file(self, filename: str) -> bool:
        """
        Load a single SF2 file.

        Args:
            filename: Path to SF2 file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create SF2 manager if not already created
            if not self.sf2_manager:
                self.sf2_manager = CoreSF2Manager()
                self.sf2_manager.enable_lazy_loading()
                self.sf2_manager.mip_map_cache = MipMapCache(max_memory_mb=128)

            # Load the SF2 file
            return self.sf2_manager.load_sf2_file(filename)

        except Exception as e:
            print(f"Error loading SF2 file {filename}: {e}")
            return False

    def get_manager(self) -> Optional[CoreSF2Manager]:
        """
        Get the underlying SF2 manager instance.

        Returns:
            CoreSF2Manager instance or None
        """
        return self.sf2_manager

    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Set bank blacklist for specified SF2 file.

        Args:
            sf2_path: Path to SF2 file
            bank_list: List of bank numbers to exclude
        """
        self.bank_blacklists[sf2_path] = bank_list.copy()
        if self.sf2_manager:
            self.sf2_manager.set_bank_blacklist(sf2_path, bank_list)

    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Set preset blacklist for specified SF2 file.

        Args:
            sf2_path: Path to SF2 file
            preset_list: List of (bank, program) tuples to exclude
        """
        self.preset_blacklists[sf2_path] = preset_list.copy()
        if self.sf2_manager:
            self.sf2_manager.set_preset_blacklist(sf2_path, preset_list)

    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Set MIDI bank to SF2 bank mapping for specified file.

        Args:
            sf2_path: Path to SF2 file
            bank_mapping: Dictionary mapping midi_bank -> sf2_bank
        """
        self.bank_mappings[sf2_path] = bank_mapping.copy()
        if self.sf2_manager:
            self.sf2_manager.set_bank_mapping(sf2_path, bank_mapping)

    def get_program_parameters(self, program: int, bank: int = 0) -> Optional[Dict[str, Any]]:
        """
        Get program parameters for XG synthesizer with enhanced error handling and fallback.

        This method provides production-grade parameter retrieval with:
        - Comprehensive error handling and logging
        - Parameter validation and range checking
        - Fallback to default parameters when SF2 data is unavailable
        - Integration with XG parameter system

        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)

        Returns:
            Program parameters dictionary with guaranteed structure, or None only on critical errors
        """
        # Validate input parameters
        if not (0 <= program <= 127):
            print(f"[SF2] Invalid program number: {program} (must be 0-127)")
            return None

        if not (0 <= bank <= 16383):
            print(f"[SF2] Invalid bank number: {bank} (must be 0-16383)")
            return None

        # If no SF2 manager is available, return default XG program parameters
        if not self.sf2_manager:
            return self._get_default_xg_program_parameters(program, bank)

        try:
            # Attempt to get SF2 parameters
            sf2_params = self.sf2_manager.get_program_parameters(program, bank)

            if sf2_params is None:
                # SF2 doesn't have this program, fall back to XG defaults
                print(f"[SF2] Program {program} not found in SF2, using XG defaults")
                return self._get_default_xg_program_parameters(program, bank)

            # Validate and enhance SF2 parameters with XG compliance
            enhanced_params = self._enhance_sf2_params_with_xg(sf2_params, program, bank)

            # Ensure all required XG parameters are present
            enhanced_params = self._ensure_xg_parameter_completeness(enhanced_params, program, bank)

            return enhanced_params

        except Exception as e:
            print(f"[SF2] Error getting program parameters for program {program}, bank {bank}: {e}")
            # On error, fall back to default XG parameters instead of returning None
            print(f"[SF2] Falling back to default XG parameters due to error")
            return self._get_default_xg_program_parameters(program, bank)

    def _get_default_xg_program_parameters(self, program: int, bank: int) -> Dict[str, Any]:
        """
        Get default XG program parameters when SF2 data is unavailable.

        XG provides default parameters for all 128 programs across 16 banks,
        ensuring the synthesizer always has valid parameters to work with.

        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)

        Returns:
            Complete XG program parameter dictionary
        """
        # XG program categories (approximate)
        program_categories = {
            range(0, 8): "Piano",
            range(8, 16): "Chromatic Percussion",
            range(16, 24): "Organ",
            range(24, 32): "Guitar",
            range(32, 40): "Bass",
            range(40, 48): "Strings",
            range(48, 56): "Ensemble",
            range(56, 64): "Brass",
            range(64, 72): "Reed",
            range(72, 80): "Pipe",
            range(80, 88): "Synth Lead",
            range(88, 96): "Synth Pad",
            range(96, 104): "Synth Effects",
            range(104, 112): "Ethnic",
            range(112, 120): "Percussive",
            range(120, 128): "Sound Effects"
        }

        # Determine program category
        category = "Unknown"
        for prog_range, cat_name in program_categories.items():
            if program in prog_range:
                category = cat_name
                break

        # XG default parameters based on program category
        base_params = {
            "program": program,
            "bank": bank,
            "category": category,
            "name": f"XG {category} {program % 8 + 1}",

            # Amplitude envelope (XG defaults)
            "amp_envelope": {
                "attack": 0.0,      # Instant attack
                "decay": 0.0,       # No decay
                "sustain": 1.0,     # Full sustain
                "release": 0.5,     # Medium release
                "hold": 0.0         # No hold
            },

            # Filter (XG defaults - neutral)
            "filter": {
                "type": "lowpass_2p",
                "cutoff": 20000.0,    # Full range
                "resonance": 0.0,     # No resonance
                "key_track": 0.0      # No key tracking
            },

            # Pitch envelope (XG defaults - neutral)
            "pitch_envelope": {
                "attack": 0.0,
                "decay": 0.0,
                "sustain": 0.0,
                "release": 0.0
            },

            # LFO parameters (XG defaults)
            "lfo": {
                "speed": 1.0,       # 1 Hz
                "depth": 0.0,       # No modulation
                "waveform": "triangle",
                "sync": False
            },

            # Portamento (XG defaults)
            "portamento": {
                "time": 0.0,        # Instant
                "mode": "linear"
            },

            # XG voice parameters
            "xg_params": {
                "element_switch": 127,     # All elements on
                "velocity_sensitivity": 64, # Medium sensitivity
                "velocity_curve": 0,       # Curve 1
                "level": 100,              # Full level
                "pan": 64,                 # Center
                "reverb_send": 40,         # Medium reverb
                "chorus_send": 0,          # No chorus
                "variation_send": 0,       # No variation
                "filter_cutoff_offset": 64, # No offset
                "filter_resonance_offset": 64, # No offset
                "attack_offset": 64,       # No offset
                "decay_offset": 64,        # No offset
                "release_offset": 64,      # No offset
                "detune": 0,               # No detuning
                "fine_tune": 0,            # No fine tuning
                "coarse_tune": 0,          # No coarse tuning
                "pitch_bend_range": 2,     # 2 semitones
                "portamento_switch": 0,    # Off
                "portamento_time": 0,      # Instant
                "mono_mode": 0,            # Polyphonic
                "assign_mode": 0,          # Poly1
                "voice_reserve": 0,        # No reserve
            },

            # Partials structure (simplified - single partial for basic XG compatibility)
            "partials": [
                {
                    "partial_id": 0,
                    "sample_path": None,  # No sample - use oscillator
                    "oscillator_type": "sine",
                    "amplitude": 1.0,
                    "pan": 0.0,
                    "tuning_coarse": 0,
                    "tuning_fine": 0.0,
                    "filter_cutoff": 20000.0,
                    "filter_resonance": 0.0,
                    "amp_envelope": {
                        "attack": 0.0,
                        "decay": 0.0,
                        "sustain": 1.0,
                        "release": 0.5
                    }
                }
            ],

            # Empty modulation matrix (XG default)
            "modulation_matrix": [],

            # Metadata
            "source": "XG_Default",
            "sf2_path": None,
            "is_drum": False
        }

        # Apply category-specific defaults
        if category == "Piano":
            base_params["filter"]["cutoff"] = 8000.0  # Soften high frequencies
            base_params["amp_envelope"]["attack"] = 0.002  # Slight attack
        elif category == "Organ":
            base_params["lfo"]["depth"] = 0.3  # Add some tremolo
            base_params["lfo"]["speed"] = 6.0  # Fast tremolo
        elif category == "Strings":
            base_params["filter"]["cutoff"] = 12000.0
            base_params["amp_envelope"]["attack"] = 0.1  # Slower attack
        elif category == "Brass":
            base_params["amp_envelope"]["attack"] = 0.05
            base_params["filter"]["cutoff"] = 6000.0
        elif category == "Synth Lead":
            base_params["filter"]["resonance"] = 0.2
            base_params["filter"]["cutoff"] = 4000.0
        elif category == "Synth Pad":
            base_params["amp_envelope"]["attack"] = 0.3
            base_params["filter"]["cutoff"] = 3000.0
        elif category == "Percussive":
            base_params["amp_envelope"]["attack"] = 0.0
            base_params["amp_envelope"]["decay"] = 0.3
            base_params["amp_envelope"]["sustain"] = 0.0
            base_params["amp_envelope"]["release"] = 0.1

        return base_params

    def _enhance_sf2_params_with_xg(self, sf2_params: Dict[str, Any], program: int, bank: int) -> Dict[str, Any]:
        """
        Enhance SF2 parameters with XG compliance and additional features.

        Args:
            sf2_params: Raw SF2 parameters
            program: Program number
            bank: Bank number

        Returns:
            Enhanced parameter dictionary with XG compliance
        """
        enhanced = sf2_params.copy()

        # Ensure XG parameter structure exists
        if "xg_params" not in enhanced:
            enhanced["xg_params"] = {
                "element_switch": 127,
                "velocity_sensitivity": 64,
                "velocity_curve": 0,
                "level": 100,
                "pan": 64,
                "reverb_send": 40,
                "chorus_send": 0,
                "variation_send": 0,
                "filter_cutoff_offset": 64,
                "filter_resonance_offset": 64,
                "attack_offset": 64,
                "decay_offset": 64,
                "release_offset": 64,
                "detune": 0,
                "fine_tune": 0,
                "coarse_tune": 0,
                "pitch_bend_range": 2,
                "portamento_switch": 0,
                "portamento_time": 0,
                "mono_mode": 0,
                "assign_mode": 0,
                "voice_reserve": 0,
            }

        # Add metadata
        enhanced["program"] = program
        enhanced["bank"] = bank
        enhanced["source"] = "SF2_Enhanced"
        enhanced["is_drum"] = bank == 128

        return enhanced

    def _ensure_xg_parameter_completeness(self, params: Dict[str, Any], program: int, bank: int) -> Dict[str, Any]:
        """
        Ensure all required XG parameters are present with valid values.

        Args:
            params: Parameter dictionary to validate
            program: Program number
            bank: Bank number

        Returns:
            Parameter dictionary with all required XG parameters
        """
        # Required top-level keys
        required_keys = [
            "program", "bank", "name", "amp_envelope", "filter",
            "pitch_envelope", "lfo", "portamento", "xg_params", "partials"
        ]

        for key in required_keys:
            if key not in params:
                print(f"[SF2] Missing required parameter '{key}' for program {program}, providing default")

                if key == "program":
                    params[key] = program
                elif key == "bank":
                    params[key] = bank
                elif key == "name":
                    params[key] = f"Program {program}"
                elif key == "amp_envelope":
                    params[key] = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.5}
                elif key == "filter":
                    params[key] = {"type": "lowpass_2p", "cutoff": 20000.0, "resonance": 0.0}
                elif key == "pitch_envelope":
                    params[key] = {"attack": 0.0, "decay": 0.0, "sustain": 0.0, "release": 0.0}
                elif key == "lfo":
                    params[key] = {"speed": 1.0, "depth": 0.0, "waveform": "triangle"}
                elif key == "portamento":
                    params[key] = {"time": 0.0, "mode": "linear"}
                elif key == "xg_params":
                    params[key] = self._get_default_xg_program_parameters(program, bank)["xg_params"]
                elif key == "partials":
                    params[key] = [{"partial_id": 0, "amplitude": 1.0, "pan": 0.0}]

        return params

    def get_drum_parameters(self, note: int, program: int = 0, bank: int = 128) -> Optional[Dict[str, Any]]:
        """
        Get drum parameters for XG synthesizer.

        Args:
            note: MIDI note number (0-127)
            program: Program number (0-127)
            bank: Bank number (usually 128 for drums)

        Returns:
            Drum parameters dictionary or None if not found
        """
        if not self.sf2_manager:
            return None

        try:
            # Get base SF2 parameters
            sf2_params = self.sf2_manager.get_drum_parameters(note, program, bank)
            if sf2_params is None:
                return None

            # If we have a drum manager, integrate XG drum parameters
            if self.drum_manager is not None:
                # Get XG drum parameters for this note (using channel 9 as default drum channel)
                xg_params = self.drum_manager.get_drum_parameters_for_note(9, note)
                
                # Merge XG parameters with SF2 parameters
                if xg_params:
                    # Apply level parameter
                    if "level" in xg_params:
                        # Adjust amplitude envelope sustain level or overall level
                        if "amp_envelope" in sf2_params:
                            # Scale sustain level by XG level parameter (0.0-1.0)
                            xg_level = xg_params["level"]
                            # Preserve original sustain but scale by XG level
                            orig_sustain = sf2_params["amp_envelope"].get("sustain", 0.7)
                            sf2_params["amp_envelope"]["sustain"] = max(0.0, min(1.0, orig_sustain * xg_level))
                    
                    # Apply pan parameter
                    if "pan" in xg_params and "partials" in sf2_params:
                        # Adjust partial panning
                        xg_pan = xg_params["pan"]  # -1.0 to +1.0
                        for partial in sf2_params["partials"]:
                            # Replace existing pan with XG pan (more direct control)
                            partial["pan"] = max(-1.0, min(1.0, xg_pan))
                    
                    # Apply filter parameters
                    if "filter_cutoff" in xg_params and "filter" in sf2_params:
                        # Adjust filter cutoff frequency
                        xg_cutoff = xg_params["filter_cutoff"]  # Hz
                        sf2_params["filter"]["cutoff"] = max(20.0, min(20000.0, xg_cutoff))
                    
                    if "filter_resonance" in xg_params and "filter" in sf2_params:
                        # Adjust filter resonance
                        xg_resonance = xg_params["filter_resonance"]  # 0.0-1.0
                        sf2_params["filter"]["resonance"] = max(0.0, min(1.0, xg_resonance))
                    
                    # Apply envelope parameters
                    if "eg_attack" in xg_params and "amp_envelope" in sf2_params:
                        # Adjust envelope attack time
                        xg_attack = xg_params["eg_attack"]  # seconds
                        sf2_params["amp_envelope"]["attack"] = max(0.001, min(10.0, xg_attack))
                    
                    if "eg_decay1" in xg_params and "amp_envelope" in sf2_params:
                        # Adjust envelope decay time
                        xg_decay = xg_params["eg_decay1"]  # seconds
                        sf2_params["amp_envelope"]["decay"] = max(0.001, min(10.0, xg_decay))
                    
                    if "eg_release" in xg_params and "amp_envelope" in sf2_params:
                        # Adjust envelope release time
                        xg_release = xg_params["eg_release"]  # seconds
                        sf2_params["amp_envelope"]["release"] = max(0.001, min(10.0, xg_release))
                    
                    # Apply pitch parameters (tune coarse/fine would be applied in audio generation)
                    # These affect the playback pitch but are handled in the audio engine

            return sf2_params
            
        except Exception as e:
            print(f"Error getting drum parameters: {e}")
            return None

    def get_partial_table(self, note: int, program: int, partial_id: int,
                         velocity: int, bank: int = 0) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Get sample data for a partial.

        Args:
            note: MIDI note number (0-127)
            program: Program number (0-127)
            partial_id: Partial ID within the program
            velocity: Velocity value (0-127)
            bank: Bank number (0-16383)

        Returns:
            Sample data or None if not found
        """
        if not self.sf2_manager:
            return None

        try:
            return self.sf2_manager.get_partial_table(note, program, partial_id, velocity, bank)
        except Exception as e:
            print(f"Error getting partial table: {e}")
            return None

    def get_available_presets(self) -> List[Tuple[int, int, str]]:
        """
        Get list of available presets.

        Returns:
            List of tuples (bank, program, name)
        """
        if not self.sf2_manager:
            return []

        try:
            return self.sf2_manager.get_available_presets()
        except Exception as e:
            print(f"Error getting available presets: {e}")
            return []

    def get_modulation_matrix(self, program: int, bank: int = 0) -> List[Dict[str, Any]]:
        """
        Get modulation matrix for a program.

        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)

        Returns:
            List of modulation routes
        """
        if not self.sf2_manager:
            return []

        try:
            return self.sf2_manager.get_modulation_matrix(program, bank)
        except Exception as e:
            print(f"Error getting modulation matrix: {e}")
            return []

    def preload_program(self, program: int, bank: int = 0):
        """
        Preload program data for faster access.

        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)
        """
        if not self.sf2_manager:
            return

        try:
            self.sf2_manager.preload_program(program, bank)
        except Exception as e:
            print(f"Error preloading program: {e}")

    def clear_cache(self):
        """
        Clear sample cache to free memory.
        """
        if self.sf2_manager:
            try:
                self.sf2_manager.clear_cache()
            except Exception as e:
                print(f"Error clearing cache: {e}")

    def is_drum_bank(self, bank: int) -> bool:
        """
        Check if a bank is a drum bank.

        Args:
            bank: Bank number

        Returns:
            True if drum bank, False otherwise
        """
        if not self.sf2_manager:
            return bank == 128  # Default drum bank

        try:
            return self.sf2_manager.is_drum_bank(bank)
        except Exception:
            return bank == 128

    def get_sf2_info(self) -> Dict[str, Any]:
        """
        Get information about loaded SF2 files.

        Returns:
            Dictionary with SF2 information
        """
        info = {
            "sf2_paths": self.sf2_paths.copy(),
            "bank_blacklists": {k: v.copy() for k, v in self.bank_blacklists.items()},
            "preset_blacklists": {k: v.copy() for k, v in self.preset_blacklists.items()},
            "bank_mappings": {k: v.copy() for k, v in self.bank_mappings.items()},
            "manager_loaded": self.sf2_manager is not None
        }

        if self.sf2_manager:
            try:
                # Add available presets count
                presets = self.sf2_manager.get_available_presets()
                info["available_presets_count"] = len(presets)
            except Exception:
                info["available_presets_count"] = 0

        return info
