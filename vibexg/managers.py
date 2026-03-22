"""
Vibexg Managers - Management classes for presets, MIDI learn, and style engine

This module provides:
- PresetManager: Save/load preset configurations
- MIDILearnManager: MIDI CC to parameter mapping
- StyleEngineIntegration: Auto-accompaniment style engine integration
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import pickle
import time
from pathlib import Path
from typing import Any

from synth.core.synthesizer import Synthesizer

from .types import PresetData

logger = logging.getLogger(__name__)

# Style engine imports (optional)
try:
    from synth.style import Style, StyleLoader
    from synth.style.style_player import StylePlayer

    STYLE_ENGINE_AVAILABLE = True
except ImportError:
    STYLE_ENGINE_AVAILABLE = False
    StylePlayer = None
    StyleLoader = None
    Style = None
    logger.info("Style engine not available - auto-accompaniment disabled")


class PresetManager:
    """
    Manages preset save/load operations.

    Provides functionality to save, load, list, and delete preset
    configurations. Presets are stored as pickle files for full
    fidelity, with optional JSON export for human readability.
    """

    def __init__(self, preset_dir: str = "presets"):
        """
        Initialize the preset manager.

        Args:
            preset_dir: Directory to store preset files (default: "presets")
        """
        self.preset_dir = Path(preset_dir)
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        self.current_preset: PresetData | None = None
        self.preset_history: list[PresetData] = []

    def create_preset(self, name: str = "New Preset") -> PresetData:
        """
        Create a new preset.

        Args:
            name: Name for the new preset

        Returns:
            New PresetData instance
        """
        preset = PresetData(name=name)
        self.current_preset = preset
        return preset

    def save_preset(self, preset: PresetData | None = None, filename: str | None = None) -> Path:
        """
        Save preset to file.

        Args:
            preset: Preset to save (uses current_preset if None)
            filename: Optional filename (auto-generated if None)

        Returns:
            Path to saved file

        Raises:
            ValueError: If no preset is provided and current_preset is None
        """
        if preset is None:
            preset = self.current_preset

        if preset is None:
            raise ValueError("No preset to save")

        preset.modified_at = time.time()

        if filename is None:
            # Generate filename from preset name
            safe_name = hashlib.md5(preset.name.encode()).hexdigest()[:12]
            filename = f"{safe_name}.preset"

        filepath = self.preset_dir / filename

        with open(filepath, "wb") as f:
            pickle.dump(self._preset_to_dict(preset), f)

        logger.info(f"Preset saved: {filepath}")
        return filepath

    def load_preset(self, filename: str) -> PresetData | None:
        """
        Load preset from file.

        Args:
            filename: Path or name of preset file to load

        Returns:
            Loaded PresetData or None if not found
        """
        filepath = Path(filename)

        if not filepath.exists():
            # Try in preset directory
            filepath = self.preset_dir / filename
            if not filepath.exists():
                logger.error(f"Preset not found: {filename}")
                return None

        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)

            preset = self._dict_to_preset(data)
            self.current_preset = preset
            self.preset_history.append(preset)

            logger.info(f"Preset loaded: {preset.name}")
            return preset

        except Exception as e:
            logger.error(f"Failed to load preset: {e}")
            return None

    def list_presets(self) -> list[Path]:
        """
        List all available presets.

        Returns:
            List of Path objects for preset files
        """
        return list(self.preset_dir.glob("*.preset"))

    def delete_preset(self, filename: str) -> bool:
        """
        Delete a preset.

        Args:
            filename: Name of preset file to delete

        Returns:
            True if deleted, False if not found
        """
        filepath = self.preset_dir / filename
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Preset deleted: {filename}")
            return True
        return False

    def export_preset_json(self, preset: PresetData | None = None, filename: str = None) -> Path:
        """
        Export preset as JSON for human readability.

        Args:
            preset: Preset to export (uses current_preset if None)
            filename: Output filename (auto-generated if None)

        Returns:
            Path to exported JSON file

        Raises:
            ValueError: If no preset is provided and current_preset is None
        """
        if preset is None:
            preset = self.current_preset

        if preset is None:
            raise ValueError("No preset to export")

        if filename is None:
            filename = f"{preset.name.replace(' ', '_')}.json"

        filepath = Path(filename)

        # Convert to dict and make timestamps readable
        data = self._preset_to_dict(preset)
        data["created_at"] = time.ctime(data["created_at"])
        data["modified_at"] = time.ctime(data["modified_at"])

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Preset exported: {filepath}")
        return filepath

    def _preset_to_dict(self, preset: PresetData) -> dict[str, Any]:
        """Convert PresetData to dictionary."""
        return {
            "name": preset.name,
            "programs": preset.programs,
            "volumes": preset.volumes,
            "pans": preset.pans,
            "reverb_sends": preset.reverb_sends,
            "chorus_sends": preset.chorus_sends,
            "master_volume": preset.master_volume,
            "tempo": preset.tempo,
            "effects_config": preset.effects_config,
            "midi_learn_mappings": preset.midi_learn_mappings,
            "created_at": preset.created_at,
            "modified_at": preset.modified_at,
        }

    def _dict_to_preset(self, data: dict[str, Any]) -> PresetData:
        """Convert dictionary to PresetData."""
        return PresetData(
            name=data.get("name", "Init"),
            programs=data.get("programs", {}),
            volumes=data.get("volumes", {}),
            pans=data.get("pans", {}),
            reverb_sends=data.get("reverb_sends", {}),
            chorus_sends=data.get("chorus_sends", {}),
            master_volume=data.get("master_volume", 0.8),
            tempo=data.get("tempo", 120.0),
            effects_config=data.get("effects_config", {}),
            midi_learn_mappings=data.get("midi_learn_mappings", []),
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time()),
        )


class MIDILearnManager:
    """
    Manages MIDI CC to parameter mappings.

    Provides functionality to map MIDI Continuous Controller (CC)
    messages to synthesizer parameters, enabling real-time hardware
    control of software parameters.
    """

    def __init__(self, synthesizer: Synthesizer):
        """
        Initialize the MIDI Learn manager.

        Args:
            synthesizer: Synthesizer instance to control
        """
        self.synthesizer = synthesizer
        self.mappings: dict[int, dict[str, Any]] = {}  # cc_number -> mapping
        self.learning_mode = False
        self.last_cc_received: int | None = None
        self.last_cc_value: int | None = None

    def add_mapping(
        self,
        cc_number: int,
        target_param: str,
        channel: int = 0,
        min_val: int = 0,
        max_val: int = 127,
        curve: str = "linear",
        invert: bool = False,
    ):
        """
        Add a MIDI CC to parameter mapping.

        Args:
            cc_number: MIDI CC number (0-127)
            target_param: Parameter path (e.g., "filter.cutoff")
            channel: MIDI channel (0-15, or -1 for all channels)
            min_val: Minimum mapped value
            max_val: Maximum mapped value
            curve: Mapping curve ('linear', 'exp', 'log')
            invert: Whether to invert the mapping
        """
        self.mappings[cc_number] = {
            "cc": cc_number,
            "target": target_param,
            "channel": channel,
            "min": min_val,
            "max": max_val,
            "curve": curve,
            "invert": invert,
        }
        logger.info(f"MIDI Learn: CC{cc_number} -> {target_param}")

    def remove_mapping(self, cc_number: int):
        """
        Remove a MIDI CC mapping.

        Args:
            cc_number: CC number to remove
        """
        if cc_number in self.mappings:
            del self.mappings[cc_number]
            logger.info(f"MIDI Learn: CC{cc_number} mapping removed")

    def clear_mappings(self):
        """Clear all mappings."""
        self.mappings.clear()
        logger.info("MIDI Learn: All mappings cleared")

    def process_cc(self, cc_number: int, value: int, channel: int = 0):
        """
        Process incoming CC and route to mapped parameter.

        Args:
            cc_number: MIDI CC number received
            value: CC value (0-127)
            channel: MIDI channel the CC was received on
        """
        if cc_number not in self.mappings:
            return

        mapping = self.mappings[cc_number]

        # Check channel match
        if mapping["channel"] != channel and mapping["channel"] != -1:
            return

        # Apply mapping
        min_val = mapping["min"]
        max_val = mapping["max"]

        if mapping["invert"]:
            value = max_val - (value - min_val) + min_val

        # Apply curve
        if mapping["curve"] == "linear":
            mapped_value = min_val + (value / 127.0) * (max_val - min_val)
        elif mapping["curve"] == "exp":
            # Exponential curve for filter cutoff, etc.
            normalized = value / 127.0
            mapped_value = min_val + (normalized**2) * (max_val - min_val)
        elif mapping["curve"] == "log":
            # Logarithmic curve for attack/decay times
            normalized = value / 127.0
            if normalized > 0:
                mapped_value = min_val + math.log(normalized * 9 + 1) / math.log(10) * (
                    max_val - min_val
                )
            else:
                mapped_value = min_val
        else:
            mapped_value = value

        # Route to synthesizer parameter
        self._set_parameter(mapping["target"], int(mapped_value), channel)

    def _set_parameter(self, param: str, value: int, channel: int):
        """
        Set synthesizer parameter.

        Args:
            param: Parameter path (e.g., "filter.cutoff")
            value: Parameter value
            channel: MIDI channel
        """
        # Parse parameter path (e.g., "filter.cutoff", "amplitude.attack")
        parts = param.split(".")

        if len(parts) == 2:
            section, param_name = parts

            # Route to appropriate synthesizer component
            if section == "filter":
                self._set_filter_param(param_name, value, channel)
            elif section == "amplitude":
                self._set_amplitude_param(param_name, value, channel)
            elif section == "effects":
                self._set_effects_param(param_name, value, channel)
            elif section == "master":
                self._set_master_param(param_name, value)

    def _set_filter_param(self, param_name: str, value: int, channel: int):
        """Set filter parameter."""
        logger.debug(f"Filter {param_name} = {value} on channel {channel}")

    def _set_amplitude_param(self, param_name: str, value: int, channel: int):
        """Set amplitude parameter."""
        logger.debug(f"Amplitude {param_name} = {value} on channel {channel}")

    def _set_effects_param(self, param_name: str, value: int, channel: int):
        """Set effects parameter."""
        logger.debug(f"Effects {param_name} = {value} on channel {channel}")

    def _set_master_param(self, param_name: str, value: int):
        """Set master parameter."""
        logger.debug(f"Master {param_name} = {value}")

    def get_mappings(self) -> dict[int, dict[str, Any]]:
        """
        Get all mappings.

        Returns:
            Copy of all CC mappings
        """
        return self.mappings.copy()

    def export_mappings(self) -> dict[str, Any]:
        """
        Export mappings as dictionary.

        Returns:
            Dictionary containing mappings and learning mode state
        """
        return {"mappings": list(self.mappings.values()), "learning_mode": self.learning_mode}

    def import_mappings(self, data: dict[str, Any]):
        """
        Import mappings from dictionary.

        Args:
            data: Dictionary containing mappings and learning mode
        """
        self.mappings = {m["cc"]: m for m in data.get("mappings", [])}
        self.learning_mode = data.get("learning_mode", False)


class StyleEngineIntegration:
    """
    Integrates style engine for auto-accompaniment.

    Provides functionality to load and play backing styles for
    auto-accompaniment features, similar to commercial keyboards.
    """

    def __init__(self, synthesizer: Synthesizer):
        """
        Initialize the style engine integration.

        Args:
            synthesizer: Synthesizer instance to control
        """
        self.synthesizer = synthesizer
        self.style_player: StylePlayer | None = None
        self.style_loader: StyleLoader | None = None
        self.loaded_styles: dict[int, Style] = {}  # channel -> style
        self.style_paths: list[Path] = []

    def initialize(self, style_paths: list[str] = None) -> bool:
        """
        Initialize style engine.

        Args:
            style_paths: List of directories to search for style files

        Returns:
            True if initialization successful, False otherwise
        """
        if not STYLE_ENGINE_AVAILABLE:
            logger.warning("Style engine not available")
            return False

        try:
            self.style_loader = StyleLoader()
            self.style_player = StylePlayer(self.synthesizer)

            if style_paths:
                for path in style_paths:
                    self.add_style_path(Path(path))

            logger.info("Style engine initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize style engine: {e}")
            return False

    def add_style_path(self, path: Path):
        """
        Add a style search path.

        Args:
            path: Directory path to add to style search paths
        """
        if path.exists() and path.is_dir():
            self.style_paths.append(path)
            logger.info(f"Style path added: {path}")

    def load_style(self, style_name: str, channel: int = 0) -> bool:
        """
        Load a style file.

        Args:
            style_name: Name of style to load (without extension)
            channel: MIDI channel to assign style to

        Returns:
            True if style loaded successfully, False otherwise
        """
        if self.style_loader is None:
            return False

        # Search for style file
        for style_path in self.style_paths:
            # Try different extensions
            for ext in [".sty", ".sff", ".sf2"]:
                style_file = style_path / f"{style_name}{ext}"
                if style_file.exists():
                    try:
                        style = self.style_loader.load_style(str(style_file))
                        self.loaded_styles[channel] = style
                        logger.info(f"Style loaded: {style_name} on channel {channel}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to load style {style_name}: {e}")

        logger.warning(f"Style not found: {style_name}")
        return False

    def unload_style(self, channel: int = 0):
        """
        Unload style from channel.

        Args:
            channel: Channel to unload style from
        """
        if channel in self.loaded_styles:
            del self.loaded_styles[channel]
            logger.info(f"Style unloaded from channel {channel}")

    def start_style(self, channel: int = 0):
        """
        Start style playback.

        Args:
            channel: Channel with style to start
        """
        if channel in self.loaded_styles and self.style_player:
            self.style_player.set_style(self.loaded_styles[channel])
            self.style_player.start()
            logger.info(f"Style started on channel {channel}")

    def stop_style(self, channel: int = 0):
        """
        Stop style playback.

        Args:
            channel: Channel to stop (ignored, stops all)
        """
        if self.style_player:
            self.style_player.stop()

    def set_tempo(self, tempo: float):
        """
        Set style tempo.

        Args:
            tempo: Tempo in BPM
        """
        if self.style_player:
            self.style_player.set_tempo(tempo)

    def set_section(self, section: str, channel: int = 0):
        """
        Change style section (intro, main, fill, ending).

        Args:
            section: Section name to switch to
            channel: Channel with style to change
        """
        if self.style_player:
            self.style_player.set_section(section)

    def get_loaded_styles(self) -> dict[int, str]:
        """
        Get loaded styles.

        Returns:
            Dictionary mapping channels to style names
        """
        return dict.fromkeys(self.loaded_styles.keys(), "Style")
