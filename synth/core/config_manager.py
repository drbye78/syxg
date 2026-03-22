"""
Unified Configuration Manager for syxg synthesizer

Loads and manages the unified config.yaml file which supports:
- Runtime/Audio engine settings
- XGML-style musical configuration (parts, effects, arpeggiator, MPE, tuning)
- Layered configuration via YAML file includes
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

import yaml


class IncludeLoader(yaml.SafeLoader):
    """Custom YAML loader with support for file includes"""

    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0] if hasattr(stream, "name") else os.getcwd()
        super().__init__(stream)


def include_constructor(loader: IncludeLoader, node: yaml.Node) -> Any:
    """Construct included YAML file"""
    # Get the file path from the node
    if isinstance(node, yaml.ScalarNode):
        include_path = loader.construct_scalar(node)
    else:
        raise yaml.constructor.ConstructorError(
            "while constructing a Python object",
            node.start_mark,
            f"expected include path as scalar, got {node.id}",
            node.start_mark,
        )

    # Resolve relative paths
    if not os.path.isabs(include_path):
        include_path = os.path.join(loader._root, include_path)

    # Load the included file
    if os.path.exists(include_path):
        with open(include_path) as f:
            # Recursively process includes in the included file
            return yaml.load(f, IncludeLoader)
    else:
        print(f"Warning: Included file not found: {include_path}")
        return {}


# Register the custom tag
yaml.add_constructor("!include", include_constructor, Loader=IncludeLoader)


class ConfigManager:
    """
    Configuration Manager for loading and accessing unified config.yaml
    Supports layered configuration via file includes.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize ConfigManager

        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self._loaded = False
        self._include_stack: list[str] = []  # Track included files for debugging

    def load(self, config_path: str | None = None) -> bool:
        """
        Load configuration from YAML file with support for layered includes.

        The configuration system supports:
        - Direct configuration in the main file
        - Includes via 'includes' key listing files to include
        - Nested includes (recursively processed)

        Include precedence: Later files override earlier ones.

        Args:
            config_path: Optional path to config file

        Returns:
            True if loaded successfully
        """
        path = config_path or self.config_path

        # First check if the explicit path exists
        if path and os.path.exists(path):
            loaded_path = path
        else:
            # Try additional locations
            search_paths = [
                os.path.join(os.getcwd(), path),
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml"
                ),
                "/mnt/c/Work/guga/syxg/config.yaml",
            ]

            loaded_path = None
            for search_path in search_paths:
                if search_path and os.path.exists(search_path):
                    loaded_path = search_path
                    break

        if not loaded_path:
            print("Warning: Config file not found, using defaults")
            self._set_defaults()
            return False

        try:
            # Load base configuration
            with open(loaded_path) as f:
                base_config = yaml.safe_load(f) or {}

            # Process layered includes
            self.config = self._merge_includes(base_config, loaded_path)
            self.config_path = loaded_path
            self._loaded = True
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            self._set_defaults()
            return False

    def _merge_includes(self, config: dict[str, Any], base_path: str) -> dict[str, Any]:
        """
        Recursively merge included configuration files.

        The 'includes' key in a config file lists additional YAML files to include.
        Later includes override earlier ones. Nested includes are processed recursively.

        Args:
            config: Current configuration dictionary
            base_path: Path to the config file (for resolving relative includes)

        Returns:
            Merged configuration dictionary
        """
        # Get the directory of the base config file
        base_dir = os.path.dirname(os.path.abspath(base_path))

        # Check for includes
        includes = config.pop("includes", None)

        # Start with the current config
        merged_config = deepcopy(config)

        if includes:
            # Process each included file
            if isinstance(includes, str):
                includes = [includes]

            for include_file in includes:
                # Resolve relative paths
                if not os.path.isabs(include_file):
                    include_path = os.path.join(base_dir, include_file)
                else:
                    include_path = include_file

                if os.path.exists(include_path):
                    # Avoid circular includes
                    if include_path in self._include_stack:
                        print(f"Warning: Circular include detected: {include_path}")
                        continue

                    # Track included file
                    self._include_stack.append(include_path)

                    try:
                        # Load included config
                        with open(include_path) as f:
                            included_config = yaml.safe_load(f) or {}

                        # Recursively process nested includes
                        included_config = self._merge_includes(included_config, include_path)

                        # Merge with precedence (later overrides earlier)
                        merged_config = self._deep_merge(merged_config, included_config)
                    finally:
                        # Remove from stack after processing
                        self._include_stack.pop()
                else:
                    print(f"Warning: Included file not found: {include_path}")

        return merged_config

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries.
        Values in 'override' take precedence over 'base'.

        Special handling:
        - Lists are replaced (not appended)
        - None values in override trigger key removal from base

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = deepcopy(base)

        for key, value in override.items():
            if value is None:
                # None triggers removal
                if key in result:
                    del result[key]
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = deepcopy(value)

        return result

    def _set_defaults(self):
        """Set default configuration values"""
        self.config = {
            "audio": {
                "sample_rate": 48000,
                "bit_depth": 32,
                "block_size": 1024,
                "polyphony": 128,
                "volume": 0.8,
            },
            "midi": {"xg_enabled": True, "gs_enabled": True, "mpe_enabled": True, "device_id": 16},
            "engines": {
                "default": "sf2",
                "priority": {"sf2": 10, "fm": 8, "wavetable": 7, "physical": 5, "spectral": 3},
            },
            "voices": {"max_polyphony": 128, "stealing_policy": "oldest_first"},
            "sf2_path": "",
            "parts": {},
            "fm": {},
            "effects": {},
            "arpeggiator": {},
            "mpe": {},
            "tuning": {},
        }

    # ============================================================
    # Runtime / Audio Settings
    # ============================================================

    def get_audio_config(self) -> dict[str, Any]:
        """Get audio configuration section"""
        return self.config.get("audio", {})

    def get_sample_rate(self) -> int:
        """Get sample rate"""
        return self.get_audio_config().get("sample_rate", 48000)

    def get_bit_depth(self) -> int:
        """Get bit depth"""
        return self.get_audio_config().get("bit_depth", 32)

    def get_block_size(self) -> int:
        """Get block size"""
        return self.get_audio_config().get("block_size", 1024)

    def get_polyphony(self) -> int:
        """Get polyphony limit"""
        return self.get_audio_config().get("polyphony", 128)

    def get_volume(self) -> float:
        """Get master volume"""
        return self.get_audio_config().get("volume", 0.8)

    # ============================================================
    # MIDI Settings
    # ============================================================

    def get_midi_config(self) -> dict[str, Any]:
        """Get MIDI configuration section"""
        return self.config.get("midi", {})

    def get_xg_enabled(self) -> bool:
        """Get XG enabled status"""
        return self.get_midi_config().get("xg_enabled", True)

    def get_gs_enabled(self) -> bool:
        """Get GS enabled status"""
        return self.get_midi_config().get("gs_enabled", True)

    def get_mpe_enabled(self) -> bool:
        """Get MPE enabled status"""
        return self.get_midi_config().get("mpe_enabled", True)

    def get_device_id(self) -> int:
        """Get MIDI device ID"""
        return self.get_midi_config().get("device_id", 16)

    # ============================================================
    # Engine Settings
    # ============================================================

    def get_engines_config(self) -> dict[str, Any]:
        """Get engines configuration section"""
        return self.config.get("engines", {})

    def get_default_engine(self) -> str:
        """Get default synthesis engine"""
        return self.get_engines_config().get("default", "sf2")

    def get_engine_priorities(self) -> dict[str, int]:
        """Get engine priority dictionary"""
        return self.get_engines_config().get("priority", {})

    # ============================================================
    # Voice Management
    # ============================================================

    def get_voices_config(self) -> dict[str, Any]:
        """Get voices configuration section"""
        return self.config.get("voices", {})

    def get_max_polyphony(self) -> int:
        """Get maximum polyphony"""
        return self.get_voices_config().get("max_polyphony", 128)

    def get_stealing_policy(self) -> str:
        """Get voice stealing policy"""
        return self.get_voices_config().get("stealing_policy", "oldest_first")

    def get_voice_reserve(self) -> dict[str, int]:
        """Get per-part voice reserve"""
        voices = self.get_voices_config()
        reserve = {}
        for i in range(16):
            key = f"part_{i}"
            if key in voices:
                reserve[i] = voices[key]
            else:
                reserve[i] = 8
        return reserve

    # ============================================================
    # SoundFont Configuration (Multiple SoundFonts)
    # ============================================================

    def get_sf2_path(self) -> str:
        """Get default SoundFont path (legacy single path, for backwards compatibility)"""
        return self.config.get("sf2_path", "")

    def get_soundfonts(self) -> list[dict[str, Any]]:
        """
        Get list of configured soundfonts with their configurations.

        Each soundfont can have:
        - path: Path to the SF2 file
        - priority: Loading priority (higher = loaded first)
        - blacklist: List of (bank, program) tuples to blacklist
        - remap: Dict of (bank, program) -> (target_bank, target_program) mappings

        Returns:
            List of soundfont configuration dictionaries with properly parsed blacklist and remap
        """
        soundfonts = self.config.get("soundfonts", [])

        # Convert legacy single sf2_path to soundfonts list if present
        if not soundfonts:
            legacy_path = self.config.get("sf2_path", "")
            if legacy_path:
                return [{"path": legacy_path, "priority": 0, "blacklist": [], "remap": {}}]

        # Parse each soundfont configuration
        result = []
        for sf in soundfonts:
            if isinstance(sf, dict):
                parsed = {
                    "path": sf.get("path", ""),
                    "priority": sf.get("priority", 0),
                    "blacklist": [],
                    "remap": {},
                }

                # Parse blacklist entries
                blacklist = sf.get("blacklist", [])
                if isinstance(blacklist, list):
                    for item in blacklist:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            parsed["blacklist"].append((int(item[0]), int(item[1])))
                        elif isinstance(item, str):
                            # Handle "bank:program" string format
                            if ":" in item:
                                try:
                                    bank, prog = item.split(":")
                                    parsed["blacklist"].append((int(bank), int(prog)))
                                except (ValueError, IndexError):
                                    pass

                # Parse remap entries
                remap = sf.get("remap", {})
                if isinstance(remap, dict):
                    for key, value in remap.items():
                        # Parse key (from_bank:from_prog)
                        if isinstance(key, str) and ":" in key:
                            try:
                                from_bank, from_prog = key.split(":")
                                from_bank = int(from_bank)
                                from_prog = int(from_prog)

                                # Parse value (to_bank:to_prog)
                                if isinstance(value, str) and ":" in value:
                                    to_bank, to_prog = value.split(":")
                                    parsed["remap"][(from_bank, from_prog)] = (
                                        int(to_bank),
                                        int(to_prog),
                                    )
                                elif isinstance(value, (list, tuple)) and len(value) >= 2:
                                    parsed["remap"][(from_bank, from_prog)] = (
                                        int(value[0]),
                                        int(value[1]),
                                    )
                            except (ValueError, IndexError):
                                pass

                result.append(parsed)
            elif isinstance(sf, str):
                # Simple path string
                result.append({"path": sf, "priority": 0, "blacklist": [], "remap": {}})

        return result

    def _parse_soundfont_config(self, sf_config: Any) -> dict[str, Any]:
        """
        Parse a soundfont configuration entry (supports both string and dict formats).

        Args:
            sf_config: Either a string path or a dict with configuration

        Returns:
            Parsed soundfont configuration dictionary
        """
        if isinstance(sf_config, str):
            # Simple path string
            return {"path": sf_config, "priority": 0, "blacklist": [], "remap": {}}
        elif isinstance(sf_config, dict):
            result = {
                "path": sf_config.get("path", ""),
                "priority": sf_config.get("priority", 0),
                "blacklist": [],
                "remap": {},
            }

            # Parse blacklist
            blacklist = sf_config.get("blacklist", [])
            if isinstance(blacklist, list):
                for item in blacklist:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        result["blacklist"].append((int(item[0]), int(item[1])))
                    elif isinstance(item, str) and ":" in item:
                        try:
                            bank, prog = item.split(":")
                            result["blacklist"].append((int(bank), int(prog)))
                        except (ValueError, IndexError):
                            pass

            # Parse remap
            remap = sf_config.get("remap", {})
            if isinstance(remap, dict):
                for key, value in remap.items():
                    if isinstance(key, str) and ":" in key:
                        try:
                            from_bank, from_prog = key.split(":")
                            if isinstance(value, (list, tuple)) and len(value) >= 2:
                                result["remap"][(int(from_bank), int(from_prog))] = (
                                    int(value[0]),
                                    int(value[1]),
                                )
                            elif isinstance(value, str) and ":" in value:
                                to_bank, to_prog = value.split(":")
                                result["remap"][(int(from_bank), int(from_prog))] = (
                                    int(to_bank),
                                    int(to_prog),
                                )
                        except (ValueError, IndexError):
                            pass

            return result

        return {"path": "", "priority": 0, "blacklist": [], "remap": {}}

    # ============================================================
    # Per-Part Configuration
    # ============================================================

    def get_parts_config(self) -> dict[str, Any]:
        """Get parts configuration section"""
        return self.config.get("parts", {})

    def get_part_config(self, part_num: int) -> dict[str, Any]:
        """
        Get configuration for a specific part

        Args:
            part_num: Part number (0-15)

        Returns:
            Part configuration dictionary
        """
        parts = self.get_parts_config()
        key = f"part_{part_num}"
        return parts.get(key, {})

    def get_all_parts(self) -> list[dict[str, Any]]:
        """
        Get all part configurations as a list

        Returns:
            List of 16 part configurations
        """
        return [self.get_part_config(i) for i in range(16)]

    # ============================================================
    # FM Engine Configuration
    # ============================================================

    def get_fm_config(self) -> dict[str, Any]:
        """Get FM engine configuration section"""
        return self.config.get("fm", {})

    def get_fm_algorithm(self) -> int:
        """Get FM algorithm number"""
        return self.get_fm_config().get("algorithm", 1)

    def get_fm_operators(self) -> list[dict[str, Any]]:
        """Get FM operator configurations"""
        fm = self.get_fm_config()
        operators = fm.get("operators", {})
        return [operators.get(f"op_{i}", {}) for i in range(8)]

    def get_fm_lfos(self) -> list[dict[str, Any]]:
        """Get FM LFO configurations"""
        fm = self.get_fm_config()
        lfos = fm.get("lfos", {})
        return [lfos.get("lfo_1", {}), lfos.get("lfo_2", {}), lfos.get("lfo_3", {})]

    def get_fm_modulation(self) -> list[dict[str, Any]]:
        """Get FM modulation matrix"""
        return self.get_fm_config().get("modulation", [])

    # ============================================================
    # Effects Configuration
    # ============================================================

    def get_effects_config(self) -> dict[str, Any]:
        """Get effects configuration section"""
        return self.config.get("effects", {})

    def get_reverb_config(self) -> dict[str, Any]:
        """Get reverb configuration"""
        return self.get_effects_config().get("reverb", {})

    def get_chorus_config(self) -> dict[str, Any]:
        """Get chorus configuration"""
        return self.get_effects_config().get("chorus", {})

    def get_variation_config(self) -> dict[str, Any]:
        """Get variation effect configuration"""
        return self.get_effects_config().get("variation", {})

    def get_eq_config(self) -> dict[str, Any]:
        """Get EQ configuration"""
        return self.get_effects_config().get("eq", {})

    def get_compressor_config(self) -> dict[str, Any]:
        """Get compressor configuration"""
        return self.get_effects_config().get("compressor", {})

    def get_limiter_config(self) -> dict[str, Any]:
        """Get limiter configuration"""
        return self.get_effects_config().get("limiter", {})

    # ============================================================
    # Arpeggiator Configuration
    # ============================================================

    def get_arpeggiator_config(self) -> dict[str, Any]:
        """Get arpeggiator configuration section"""
        return self.config.get("arpeggiator", {})

    def get_arpeggiator_enabled(self) -> bool:
        """Get arpeggiator enabled status"""
        return self.get_arpeggiator_config().get("enabled", False)

    def get_arpeggiator_tempo(self) -> int:
        """Get arpeggiator tempo"""
        return self.get_arpeggiator_config().get("tempo", 120)

    # ============================================================
    # MPE Configuration
    # ============================================================

    def get_mpe_config(self) -> dict[str, Any]:
        """Get MPE configuration section"""
        return self.config.get("mpe", {})

    def get_mpe_enabled(self) -> bool:
        """Get MPE enabled status"""
        return self.get_mpe_config().get("enabled", True)

    def get_mpe_zones(self) -> list[dict[str, Any]]:
        """Get MPE zone configurations"""
        return self.get_mpe_config().get("zones", [])

    # ============================================================
    # Tuning Configuration
    # ============================================================

    def get_tuning_config(self) -> dict[str, Any]:
        """Get tuning configuration section"""
        return self.config.get("tuning", {})

    def get_temperament(self) -> str:
        """Get temperament type"""
        return self.get_tuning_config().get("temperament", "equal")

    def get_a4_frequency(self) -> float:
        """Get A4 reference frequency"""
        return self.get_tuning_config().get("a4_frequency", 440.0)

    # ============================================================
    # Include Information
    # ============================================================

    def get_include_stack(self) -> list[str]:
        """Get list of included configuration files"""
        return self._include_stack.copy()

    def get_includes(self) -> list[str]:
        """Get list of includes defined in current config"""
        return self.config.get("includes", [])

    # ============================================================
    # Full Config Access
    # ============================================================

    def get_full_config(self) -> dict[str, Any]:
        """Get full configuration dictionary"""
        return self.config

    def is_loaded(self) -> bool:
        """Check if configuration was loaded"""
        return self._loaded


# Global config manager instance
_config_manager: ConfigManager | None = None


def get_config_manager(config_path: str = "config.yaml") -> ConfigManager:
    """
    Get global ConfigManager instance

    Args:
        config_path: Path to config file

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
        _config_manager.load()
    return _config_manager


def load_config(config_path: str = "config.yaml") -> ConfigManager:
    """
    Load configuration from file

    Args:
        config_path: Path to config file

    Returns:
        ConfigManager instance
    """
    manager = ConfigManager(config_path)
    manager.load()
    return manager
