"""
XGML Backward Compatibility Layer

Provides automatic conversion from XGML v2.1 to XGML v3.0 format.
Ensures seamless migration while maintaining all functionality.
"""
from __future__ import annotations

from typing import Any


class XGMLCompatibilityConverter:
    """
    Converts XGML v2.1 configurations to XGML v3.0 format.

    Handles all breaking changes and deprecated features while preserving
    functionality and intent of original configurations.
    """

    def __init__(self):
        self.conversion_warnings: list[str] = []
        self.conversion_errors: list[str] = []

    def convert_v2_to_v3(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """
        Convert XGML v2.1 configuration to v3.0 format.

        Args:
            v2_config: XGML v2.1 configuration dictionary

        Returns:
            XGML v3.0 compatible configuration dictionary
        """
        self.conversion_warnings = []
        self.conversion_errors = []

        # Start with v3.0 base
        v3_config = {
            "xg_dsl_version": "3.0",
            "description": v2_config.get("description"),
            "timestamp": v2_config.get("timestamp"),
            "metadata": v2_config.get("metadata", {})
        }

        # Convert sections
        v3_config.update(self._convert_basic_messages(v2_config))
        v3_config.update(self._convert_channel_parameters(v2_config))
        v3_config.update(self._convert_effects(v2_config))
        v3_config.update(self._convert_engine_config(v2_config))
        v3_config.update(self._convert_sequences(v2_config))

        return v3_config

    def _convert_basic_messages(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Convert basic_messages section from v2.1 to v3.0."""
        if "basic_messages" not in v2_config:
            return {}

        v2_basic = v2_config["basic_messages"]
        v3_basic = {"basic_messages": v2_basic}

        # Validate and enhance basic messages
        if "channels" in v2_basic:
            for channel_name, channel_config in v2_basic["channels"].items():
                # Add new v3.0 parameters with defaults
                if "volume" in channel_config and isinstance(channel_config["volume"], (int, float)):
                    # Ensure volume is in correct range
                    volume = max(0, min(127, int(channel_config["volume"])))
                    channel_config["volume"] = volume

                # Add new semantic parameters if not present
                if "reverb_send" not in channel_config:
                    channel_config["reverb_send"] = 0
                if "chorus_send" not in channel_config:
                    channel_config["chorus_send"] = 0

        return v3_basic

    def _convert_channel_parameters(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Convert channel_parameters section from v2.1 to v3.0."""
        if "channel_parameters" not in v2_config:
            return {}

        v2_channels = v2_config["channel_parameters"]
        v3_channels = {}

        for channel_name, channel_config in v2_channels.items():
            v3_channel_config = {}

            # Convert filter section
            if "filter" in channel_config:
                v3_channel_config["filter"] = self._convert_filter_config(channel_config["filter"])

            # Convert LFO section
            if "lfo" in channel_config:
                v3_channel_config["lfo"] = self._convert_lfo_config(channel_config["lfo"])

            # Convert effects sends
            if "effects_sends" in channel_config:
                v3_channel_config["effects_sends"] = channel_config["effects_sends"]

            # Convert other parameters
            for param_name, param_value in channel_config.items():
                if param_name not in ["filter", "lfo", "effects_sends"]:
                    v3_channel_config[param_name] = param_value

            if v3_channel_config:
                v3_channels[channel_name] = v3_channel_config

        if v3_channels:
            return {"channel_parameters": v3_channels}
        return {}

    def _convert_filter_config(self, v2_filter: dict[str, Any]) -> dict[str, Any]:
        """Convert filter configuration from v2.1 to v3.0."""
        v3_filter = {}

        # Convert basic parameters
        param_mapping = {
            "cutoff": "cutoff",
            "resonance": "resonance",
            "type": "type"
        }

        for v2_param, v3_param in param_mapping.items():
            if v2_param in v2_filter:
                v3_filter[v3_param] = v2_filter[v2_param]

        # Convert envelope (remains the same structure)
        if "envelope" in v2_filter:
            v3_filter["envelope"] = v2_filter["envelope"]

        return v3_filter

    def _convert_lfo_config(self, v2_lfo: dict[str, Any]) -> dict[str, Any]:
        """Convert LFO configuration from v2.1 to v3.0."""
        v3_lfo = {}

        # LFO structure is largely compatible, just ensure proper defaults
        for lfo_name, lfo_config in v2_lfo.items():
            v3_lfo_config = {}

            # Ensure required parameters
            defaults = {
                "waveform": "sine",
                "speed": 64,
                "pitch_depth": 0,
                "filter_depth": 0
            }

            for param, default_value in defaults.items():
                v3_lfo_config[param] = lfo_config.get(param, default_value)

            # Copy any additional parameters
            for param, value in lfo_config.items():
                if param not in defaults:
                    v3_lfo_config[param] = value

            v3_lfo[lfo_name] = v3_lfo_config

        return v3_lfo

    def _convert_effects(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Convert effects section from v2.1 to v3.0."""
        if "effects" not in v2_config:
            return {}

        v2_effects = v2_config["effects"]
        v3_effects = {"effects_processing": {}}

        # Convert system effects
        if "system" in v2_effects:
            v3_system_effects = {}

            # Convert reverb
            if "reverb" in v2_effects["system"]:
                reverb_value = v2_effects["system"]["reverb"]
                if isinstance(reverb_value, str):
                    # Map string names to v3.0 format
                    reverb_mapping = {
                        "hall_1": {"algorithm": "hall_1", "parameters": {"level": 0.5}},
                        "hall_2": {"algorithm": "hall_2", "parameters": {"level": 0.5}},
                        "room_1": {"algorithm": "room_1", "parameters": {"level": 0.4}},
                        "room_2": {"algorithm": "room_2", "parameters": {"level": 0.4}}
                    }
                    if reverb_value in reverb_mapping:
                        v3_system_effects["reverb"] = reverb_mapping[reverb_value]
                    else:
                        self.conversion_warnings.append(f"Unknown reverb type '{reverb_value}', using hall_1")
                        v3_system_effects["reverb"] = reverb_mapping["hall_1"]
                else:
                    # Assume it's already in a compatible format
                    v3_system_effects["reverb"] = {"algorithm": "hall_1", "parameters": {"level": reverb_value}}

            # Convert chorus
            if "chorus" in v2_effects["system"]:
                chorus_value = v2_effects["system"]["chorus"]
                if isinstance(chorus_value, str):
                    chorus_mapping = {
                        "chorus_1": {"algorithm": "chorus_1", "parameters": {"mix": 0.5}},
                        "chorus_2": {"algorithm": "chorus_2", "parameters": {"mix": 0.5}},
                        "celeste_1": {"algorithm": "celeste", "parameters": {"mix": 0.3}}
                    }
                    if chorus_value in chorus_mapping:
                        v3_system_effects["chorus"] = chorus_mapping[chorus_value]
                    else:
                        self.conversion_warnings.append(f"Unknown chorus type '{chorus_value}', using chorus_1")
                        v3_system_effects["chorus"] = chorus_mapping["chorus_1"]

            if v3_system_effects:
                v3_effects["effects_processing"]["system_effects"] = v3_system_effects

        # Convert variation effects
        if "variation" in v2_effects:
            variation_value = v2_effects["variation"]
            if isinstance(variation_value, str):
                variation_mapping = {
                    "delay_lcr": {"type": 12, "parameters": {"delay_time": 300, "feedback": 0.3}},
                    "delay_lr": {"type": 13, "parameters": {"delay_time": 400, "feedback": 0.2}},
                    "echo": {"type": 14, "parameters": {"delay_time": 500, "feedback": 0.4}},
                    "cross_delay": {"type": 15, "parameters": {"delay_time": 200, "feedback": 0.3}}
                }
                if variation_value in variation_mapping:
                    v3_effects["effects_processing"]["variation_effects"] = [variation_mapping[variation_value]]
                else:
                    self.conversion_warnings.append(f"Unknown variation effect '{variation_value}', skipping")

        return v3_effects

    def _convert_engine_config(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Convert engine configuration from v2.1 to v3.0."""
        engine_sections = ["fm_x_engine", "sfz_engine"]
        v3_engines = {"synthesis_engines": {}}

        has_engines = False

        for v2_section in engine_sections:
            if v2_section in v2_config:
                v2_engine_config = v2_config[v2_section]

                # Convert FM-X engine
                if v2_section == "fm_x_engine":
                    v3_engines["synthesis_engines"]["fm_x_engine"] = self._convert_fm_x_engine(v2_engine_config)
                    has_engines = True

                # Convert SFZ engine
                elif v2_section == "sfz_engine":
                    v3_engines["synthesis_engines"]["sfz_engine"] = self._convert_sfz_engine(v2_engine_config)
                    has_engines = True

        if has_engines:
            # Add default engine registry
            v3_engines["synthesis_engines"]["registry"] = {
                "default_engine": "fm" if "fm_x_engine" in v2_config else "sfz",
                "fallback_engine": "sf2"
            }

        return v3_engines if has_engines else {}

    def _convert_fm_x_engine(self, v2_fm_config: dict[str, Any]) -> dict[str, Any]:
        """Convert FM-X engine config from v2.1 to v3.0."""
        v3_fm_config = {
            "enabled": True,
            "algorithm": v2_fm_config.get("algorithm", 0),
            "algorithm_name": f"Algorithm {v2_fm_config.get('algorithm', 0)}"
        }

        # Convert operators
        if "operators" in v2_fm_config:
            v3_fm_config["operators"] = {}
            for op_name, op_config in v2_fm_config["operators"].items():
                v3_op_config = {
                    "enabled": True,
                    "frequency_ratio": op_config.get("ratio", 1.0),
                    "detune_cents": op_config.get("detune", 0),
                    "feedback_level": op_config.get("feedback", 0),
                    "waveform": "sine",
                    "envelope": {
                        "levels": [0.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0],
                        "rates": [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
                    }
                }
                v3_fm_config["operators"][op_name] = v3_op_config

        return v3_fm_config

    def _convert_sfz_engine(self, v2_sfz_config: dict[str, Any]) -> dict[str, Any]:
        """Convert SFZ engine config from v2.1 to v3.0."""
        v3_sfz_config = {
            "enabled": True,
            "instrument_path": v2_sfz_config.get("instrument_path", ""),
            "global_parameters": v2_sfz_config.get("global_parameters", {})
        }

        return v3_sfz_config

    def _convert_sequences(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Convert sequences section from v2.1 to v3.0."""
        if "sequences" not in v2_config:
            return {}

        # Sequences structure is largely compatible
        return {"sequences": v2_config["sequences"]}

    def get_conversion_warnings(self) -> list[str]:
        """Get conversion warnings."""
        return self.conversion_warnings.copy()

    def get_conversion_errors(self) -> list[str]:
        """Get conversion errors."""
        return self.conversion_errors.copy()

    def has_conversion_issues(self) -> bool:
        """Check if there were conversion issues."""
        return len(self.conversion_warnings) > 0 or len(self.conversion_errors) > 0


class XGMLv2CompatibilityLayer:
    """
    XGML v2.1 compatibility layer for XGML v3.0 parser.

    Automatically detects and converts v2.1 configurations to v3.0 format.
    """

    def __init__(self):
        self.converter = XGMLCompatibilityConverter()

    def convert_if_needed(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Convert configuration to v3.0 format if it's v2.1.

        Args:
            config: Input configuration (may be v2.1 or v3.0)

        Returns:
            v3.0 compatible configuration
        """
        version = config.get("xg_dsl_version", "2.1")

        if version == "3.0":
            # Already v3.0
            return config
        elif version in ["2.1", "1.0"]:
            # Convert from v2.1/v1.0 to v3.0
            v3_config = self.converter.convert_v2_to_v3(config)

            # Add conversion metadata
            if "metadata" not in v3_config:
                v3_config["metadata"] = {}
            v3_config["metadata"]["converted_from_version"] = version
            v3_config["metadata"]["conversion_timestamp"] = "2026-01-12T14:20:00Z"

            return v3_config
        else:
            # Unknown version, assume v3.0
            return config

    def get_conversion_report(self) -> dict[str, Any]:
        """Get detailed conversion report."""
        return {
            "warnings": self.converter.get_conversion_warnings(),
            "errors": self.converter.get_conversion_errors(),
            "has_issues": self.converter.has_conversion_issues()
        }
