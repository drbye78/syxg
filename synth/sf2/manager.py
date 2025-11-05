"""
XG Synthesizer SF2 Manager

Handles SoundFont 2.0 file management and integration.
"""

from typing import List, Dict, Tuple, Optional, Union, Any
from ..core.constants import DEFAULT_CONFIG
from .core import WavetableManager


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
                self.sf2_manager = WavetableManager(sf2_paths, param_cache=self.param_cache)

                # Apply existing configurations
                for sf2_path in sf2_paths:
                    if sf2_path in self.bank_blacklists:
                        self.sf2_manager.set_bank_blacklist(sf2_path, self.bank_blacklists[sf2_path])
                    if sf2_path in self.preset_blacklists:
                        self.sf2_manager.set_preset_blacklist(sf2_path, self.preset_blacklists[sf2_path])
                    if sf2_path in self.bank_mappings:
                        self.sf2_manager.set_bank_mapping(sf2_path, self.bank_mappings[sf2_path])

                return True
            else:
                self.sf2_manager = None
                return False

        except Exception as e:
            print(f"Error setting SF2 files: {e}")
            self.sf2_manager = None
            return False

    def get_manager(self) -> Optional[WavetableManager]:
        """
        Get the underlying SF2 manager instance.

        Returns:
            WavetableManager instance or None
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
        Get program parameters for XG synthesizer.

        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)

        Returns:
            Program parameters dictionary or None if not found
        """
        if not self.sf2_manager:
            return None

        try:
            return self.sf2_manager.get_program_parameters(program, bank)
        except Exception as e:
            print(f"Error getting program parameters: {e}")
            return None

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
