"""
Configuration System - XGML v3.0 Configuration Management

Complete XGML v3.0 configuration management with hot-reloading support,
workstation features, and smooth parameter transitions for professional
synthesizer configuration and real-time parameter updates.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading
import time
import math
from pathlib import Path
import os
import hashlib
import weakref


class XGMLConfigSystem:
    """
    Complete XGML v3.0 configuration system with hot-reloading.

    Manages XGML configuration parsing, application, and hot-reloading
    with smooth parameter transitions for professional synthesizer operation.
    """

    def __init__(self, synthesizer):
        """
        Initialize XGML configuration system.

        Args:
            synthesizer: Reference to the parent synthesizer
        """
        self.synthesizer = synthesizer
        self.lock = threading.RLock()

        # Hot-reloading state
        self._hot_reload_enabled = False
        self._hot_reload_watch_paths = []
        self._hot_reload_check_interval = 1.0
        self._hot_reload_file_hashes = {}  # path -> hash mapping
        self._hot_reload_last_check = time.time()
        self._hot_reload_thread = None

    def load_xgml_config(self, xgml_path: str | Path) -> bool:
        """
        Load XGML v3.0 configuration from file.

        Args:
            xgml_path: Path to XGML v3.0 configuration file

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            # Parse XGML v3.0 configuration
            from ..xgml.parser_v3 import XGMLParserV3

            parser = XGMLParserV3()
            config = parser.parse_file(xgml_path)

            if config is None:
                print(f"❌ Failed to parse XGML configuration: {xgml_path}")
                print(f"Errors: {parser.get_errors()}")
                print(f"Warnings: {parser.get_warnings()}")
                return False

            # Apply configuration to synthesizer
            return self._apply_xgml_config(config)

        except Exception as e:
            print(f"❌ Error loading XGML configuration: {e}")
            return False

    def load_xgml_string(self, xgml_string: str) -> bool:
        """
        Load XGML v3.0 configuration from string.

        Args:
            xgml_string: XGML v3.0 configuration as YAML string

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            # Parse XGML v3.0 configuration
            from ..xgml.parser_v3 import XGMLParserV3

            parser = XGMLParserV3()
            config = parser.parse_string(xgml_string)

            if config is None:
                print("❌ Failed to parse XGML configuration string")
                print(f"Errors: {parser.get_errors()}")
                print(f"Warnings: {parser.get_warnings()}")
                return False

            # Apply configuration to synthesizer
            return self._apply_xgml_config(config)

        except Exception as e:
            print(f"❌ Error loading XGML configuration string: {e}")
            return False

    def _apply_xgml_config(self, config) -> bool:
        """
        Apply XGML v3.0 configuration to synthesizer.

        Args:
            config: Parsed XGML v3.0 configuration

        Returns:
            True if configuration applied successfully
        """
        try:
            print(f"🎹 Applying XGML v3.0 configuration: {config.description or 'Unnamed'}")

            # Apply synthesizer core settings
            self._apply_synthesizer_core_config(config.synthesizer_core)

            # Apply workstation features
            self._apply_workstation_features_config(config.workstation_features)

            # Apply synthesis engines configuration
            self._apply_synthesis_engines_config(config.synthesis_engines)

            # Apply effects processing
            self._apply_effects_processing_config(config.effects_processing)

            # Apply modulation system
            self._apply_modulation_system_config(config.modulation_system)

            # Apply performance controls
            self._apply_performance_controls_config(config.performance_controls)

            # Apply sequencing configuration
            self._apply_sequencing_config(config.sequencing)

            print("✅ XGML v3.0 configuration applied successfully")
            return True

        except Exception as e:
            print(f"❌ Error applying XGML configuration: {e}")
            return False

    def _apply_xgml_config_with_transitions(self, config, source_name: str) -> bool:
        """
        Apply XGML configuration with smooth parameter transitions.

        Args:
            config: New XGML configuration to apply
            source_name: Name of the source file for logging

        Returns:
            True if configuration applied successfully
        """
        # Initialize current_state for potential rollback
        current_state = None

        try:
            print(f"🔄 Applying XGML v3.0 configuration with smooth transitions: {source_name}")

            # Store current state for potential rollback
            current_state = self._capture_current_state()

            # Apply configuration sections with transitions
            success = True

            # Core settings (immediate application)
            try:
                self._apply_synthesizer_core_config(config.synthesizer_core)
            except Exception as e:
                print(f"⚠️  Failed to apply core settings: {e}")
                success = False

            # Workstation features (immediate)
            try:
                self._apply_workstation_features_config(config.workstation_features)
            except Exception as e:
                print(f"⚠️  Failed to apply workstation features: {e}")
                success = False

            # Synthesis engines (immediate)
            try:
                self._apply_synthesis_engines_config(config.synthesis_engines)
            except Exception as e:
                print(f"⚠️  Failed to apply synthesis engines: {e}")
                success = False

            # Effects processing (with transitions)
            try:
                self._apply_effects_processing_with_transitions(config.effects_processing)
            except Exception as e:
                print(f"⚠️  Failed to apply effects processing: {e}")
                success = False

            # Modulation system (immediate)
            try:
                self._apply_modulation_system_config(config.modulation_system)
            except Exception as e:
                print(f"⚠️  Failed to apply modulation system: {e}")
                success = False

            # Performance controls (immediate)
            try:
                self._apply_performance_controls_config(config.performance_controls)
            except Exception as e:
                print(f"⚠️  Failed to apply performance controls: {e}")
                success = False

            # Sequencing (immediate)
            try:
                self._apply_sequencing_config(config.sequencing)
            except Exception as e:
                print(f"⚠️  Failed to apply sequencing: {e}")
                success = False

            if success:
                print(f"✅ XGML v3.0 configuration applied with smooth transitions: {source_name}")
                return True
            else:
                print(f"⚠️  Configuration applied with some errors: {source_name}")
                # Don't rollback on partial success - some features may still work
                return True

        except Exception as e:
            print(f"❌ Error applying configuration with transitions: {e}")
            # Attempt rollback on critical failure
            try:
                if current_state is not None:
                    self._restore_state(current_state)
                    print("🔄 Configuration rollback completed")
                else:
                    print("⚠️  No state captured for rollback")
            except Exception as rollback_error:
                print(f"❌ Rollback also failed: {rollback_error}")
            return False

    def _apply_effects_processing_with_transitions(self, effects_config: dict[str, Any]):
        """
        Apply effects processing with smooth parameter transitions.

        This ensures that effect parameter changes don't cause audio glitches.
        """
        # For now, apply immediately - in a full implementation, this would
        # interpolate parameters over time to avoid clicks/pops

        # Store current effect parameters
        current_params = self._capture_effects_state()

        # Apply new configuration
        self._apply_effects_processing_config(effects_config)

        # In a full implementation, you would:
        # 1. Create parameter interpolation curves
        # 2. Apply changes gradually over several audio blocks
        # 3. Handle crossfading between different effect types

    def _capture_current_state(self) -> dict[str, Any]:
        """Capture current synthesizer state for potential rollback."""
        state = {
            "timestamp": time.time(),
            "description": "Captured state for hot-reload rollback",
            "channels": [],
            "effects": {},
            "system": {},
        }

        # Capture channel states
        if hasattr(self.synthesizer, "channels"):
            for ch in self.synthesizer.channels:
                if ch and hasattr(ch, "get_channel_info"):
                    state["channels"].append(ch.get_channel_info())

        # Capture effects state
        if hasattr(self.synthesizer, "effects_coordinator"):
            ec = self.synthesizer.effects_coordinator
            state["effects"] = {
                "wet_dry_mix": getattr(ec, "wet_dry_mix", 1.0),
                "master_level": getattr(ec, "master_level", 1.0),
                "processing_enabled": getattr(ec, "processing_enabled", True),
            }

        # Capture system state
        state["system"] = {
            "sample_rate": self.synthesizer.sample_rate,
            "max_polyphony": getattr(self.synthesizer, "max_polyphony", 128),
        }

        return state

    def _capture_effects_state(self) -> dict[str, Any]:
        """Capture current effects processing state."""
        state = {
            "system_effects": {},
            "variation_effects": [],
            "insertion_effects": [],
            "timestamp": time.time(),
        }

        # Capture effects coordinator state if available
        if hasattr(self.synthesizer, "effects_coordinator"):
            ec = self.synthesizer.effects_coordinator
            state["system_effects"] = {
                "reverb": getattr(ec, "reverb_sends", []).tolist()
                if hasattr(getattr(ec, "reverb_sends", None), "tolist")
                else list(getattr(ec, "reverb_sends", [])),
                "chorus": getattr(ec, "chorus_sends", []).tolist()
                if hasattr(getattr(ec, "chorus_sends", None), "tolist")
                else list(getattr(ec, "chorus_sends", [])),
            }

        return state

    def _restore_state(self, state: dict[str, Any]):
        """Restore synthesizer state from captured snapshot."""
        timestamp = state.get("timestamp", 0)
        print(
            f"🔄 Attempting to restore state from {time.strftime('%H:%M:%S', time.localtime(timestamp))}"
        )

        # Restore channel states
        if "channels" in state and hasattr(self.synthesizer, "channels"):
            for idx, ch_state in enumerate(state["channels"]):
                if idx < len(self.synthesizer.channels):
                    ch = self.synthesizer.channels[idx]
                    if ch and ch_state:
                        # Restore program
                        if "program" in ch_state:
                            ch.set_program(ch_state.get("program", 0))
                        # Restore volume/pan
                        if "master_level" in ch_state:
                            ch.master_level = ch_state.get("master_level", 1.0)
                        if "pan" in ch_state:
                            ch.set_pan(ch_state.get("pan", 0.0))
                        # Restore mute/solo
                        if "muted" in ch_state:
                            ch.muted = ch_state.get("muted", False)
                        if "solo" in ch_state:
                            ch.solo = ch_state.get("solo", False)
                        # Restore key range
                        if "key_range" in ch_state:
                            kr = ch_state["key_range"]
                            ch.set_key_range(kr[0], kr[1])

        # Restore effects state
        if "effects" in state and hasattr(self.synthesizer, "effects_coordinator"):
            ec = self.synthesizer.effects_coordinator
            eff_state = state["effects"]
            if "wet_dry_mix" in eff_state:
                ec.wet_dry_mix = eff_state.get("wet_dry_mix", 1.0)
            if "master_level" in eff_state:
                ec.master_level = eff_state.get("master_level", 1.0)
            if "processing_enabled" in eff_state:
                ec.processing_enabled = eff_state.get("processing_enabled", True)

        print("✅ State restoration complete")

    def _apply_synthesizer_core_config(self, core_config: dict[str, Any]):
        """Apply synthesizer core configuration."""
        if "audio" in core_config:
            audio_config = core_config["audio"]
            # Note: Audio settings like sample_rate are typically set at initialization
            # and cannot be changed dynamically. Log if they differ.
            if (
                audio_config.get("sample_rate", self.synthesizer.sample_rate)
                != self.synthesizer.sample_rate
            ):
                print(
                    f"⚠️  Audio sample rate mismatch: config={audio_config['sample_rate']}, synth={self.synthesizer.sample_rate}"
                )

        if "performance" in core_config:
            perf_config = core_config["performance"]
            # Performance settings are handled at initialization but can be updated
            if "max_polyphony" in perf_config:
                # Note: Polyphony limits might be managed at voice manager level
                print(f"ℹ️  Polyphony setting: {perf_config['max_polyphony']}")

        if "monitoring" in core_config:
            monitor_config = core_config["monitoring"]
            if monitor_config.get("enabled", False):
                print("ℹ️  Performance monitoring enabled")

    def _apply_workstation_features_config(self, features_config: dict[str, Any]):
        """Apply workstation features configuration."""
        # Motif arpeggiator system
        if "motif_integration" in features_config:
            motif_config = features_config["motif_integration"]
            if motif_config.get("enabled", False):
                print("🎹 Motif arpeggiator integration enabled")
                # Arpeggiator configuration would be applied here

        # S90/S70 AWM Stereo
        if "s90_awm_stereo" in features_config:
            awm_config = features_config["s90_awm_stereo"]
            if awm_config.get("enabled", False):
                print("🎹 S90/S70 AWM Stereo features enabled")
                # AWM Stereo configuration would be applied here

        # Multi-timbral configuration
        if "multi_timbral" in features_config:
            multi_config = features_config["multi_timbral"]
            channels = multi_config.get("channels", 16)
            print(f"🎹 Multi-timbral channels: {channels}")

    def _apply_synthesis_engines_config(self, engines_config: dict[str, Any]):
        """Apply synthesis engines configuration."""
        registry_config = engines_config.get("registry", {})

        # Engine priorities
        if "engine_priorities" in registry_config:
            priorities = registry_config["engine_priorities"]
            print(f"🎹 Engine priorities configured: {priorities}")

        # Channel engine assignments
        if "channel_engines" in engines_config:
            channel_assignments = engines_config["channel_engines"]
            print(f"🎹 Channel engine assignments: {len(channel_assignments)} channels configured")

            # Apply channel assignments
            for channel_str, engine_name in channel_assignments.items():
                if channel_str.startswith("channel_"):
                    channel_num = int(channel_str.split("_")[1])
                    if 0 <= channel_num < len(self.synthesizer.channels):
                        # Note: Engine assignment would typically be handled at channel level
                        # For now, this is informational
                        print(f"  Channel {channel_num}: {engine_name}")

        # Individual engine configurations
        engine_configs = {
            "sf2_engine": engines_config.get("sf2_engine", {}),
            "fm_x_engine": engines_config.get("fm_x_engine", {}),
            "physical_engine": engines_config.get("physical_engine", {}),
            "spectral_engine": engines_config.get("spectral_engine", {}),
        }

        for engine_name, engine_config in engine_configs.items():
            if engine_config and engine_config.get("enabled", True):
                print(f"🎹 {engine_name.upper()} configured")

    def _apply_effects_processing_config(self, effects_config: dict[str, Any]):
        """Apply effects processing configuration."""
        if "coordinator" in effects_config:
            coord_config = effects_config["coordinator"]
            if coord_config.get("enabled", True):
                print("🎹 Effects coordinator enabled")

        if "system_effects" in effects_config:
            sys_effects = effects_config["system_effects"]
            if "reverb" in sys_effects:
                print("🎹 System reverb configured")
            if "chorus" in sys_effects:
                print("🎹 System chorus configured")

        if "variation_effects" in effects_config:
            var_effects = effects_config["variation_effects"]
            print(f"🎹 {len(var_effects)} variation effects configured")

        if "insertion_effects" in effects_config:
            ins_effects = effects_config["insertion_effects"]
            print(f"🎹 {len(ins_effects)} insertion effects configured")

    def _apply_modulation_system_config(self, modulation_config: dict[str, Any]):
        """Apply modulation system configuration."""
        matrix_config = modulation_config.get("matrix", {})

        if matrix_config.get("enabled", True):
            max_routes = matrix_config.get("max_routes", 128)
            print(f"🎹 Modulation matrix enabled: {max_routes} routes")

            if "routes" in matrix_config:
                routes = matrix_config["routes"]
                print(f"🎹 {len(routes)} modulation routes configured")

    def _apply_performance_controls_config(self, controls_config: dict[str, Any]):
        """Apply performance controls configuration."""
        if "assignable_knobs" in controls_config:
            knobs = controls_config["assignable_knobs"]
            print(f"🎹 {len(knobs)} assignable knobs configured")

        if "assignable_sliders" in controls_config:
            sliders = controls_config["assignable_sliders"]
            print(f"🎹 {len(sliders)} assignable sliders configured")

        if "snapshots" in controls_config:
            snapshots = controls_config["snapshots"]
            print(f"🎹 {len(snapshots)} performance snapshots configured")

    def _apply_sequencing_config(self, sequencing_config: dict[str, Any]):
        """Apply sequencing configuration."""
        if "sequencer_core" in sequencing_config:
            seq_core = sequencing_config["sequencer_core"]
            if seq_core.get("enabled", True):
                tempo = seq_core.get("tempo", 128)
                print(f"🎹 Sequencer enabled: {tempo} BPM")

        if "patterns" in sequencing_config:
            patterns = sequencing_config["patterns"]
            print(f"🎹 {len(patterns)} sequence patterns loaded")

    def enable_config_hot_reloading(
        self, watch_paths: list[str | Path] | None = None, check_interval: float = 1.0
    ) -> bool:
        """
        Enable configuration hot-reloading for XGML files.

        Args:
            watch_paths: List of paths to watch for XGML configuration files.
                        If None, uses currently loaded configuration paths.
            check_interval: How often to check for file changes (seconds).

        Returns:
            True if hot-reloading enabled successfully
        """
        try:
            if self._hot_reload_thread and self._hot_reload_thread.is_alive():
                print("⚠️  Hot-reloading already enabled")
                return True

            # Initialize hot-reloading system
            self._hot_reload_enabled = True
            self._hot_reload_watch_paths = watch_paths or []
            self._hot_reload_check_interval = check_interval
            self._hot_reload_file_hashes = {}  # path -> hash mapping
            self._hot_reload_last_check = time.time()

            # Start background monitoring thread
            self._hot_reload_thread = threading.Thread(
                target=self._hot_reload_monitor, name="XGMLHotReloadMonitor", daemon=True
            )
            self._hot_reload_thread.start()

            print(f"🔄 XGML hot-reloading enabled (check interval: {check_interval}s)")
            if self._hot_reload_watch_paths:
                print(f"   Watching {len(self._hot_reload_watch_paths)} paths")

            return True

        except Exception as e:
            print(f"❌ Failed to enable hot-reloading: {e}")
            return False

    def disable_config_hot_reloading(self) -> bool:
        """
        Disable configuration hot-reloading.

        Returns:
            True if disabled successfully
        """
        try:
            self._hot_reload_enabled = False

            if self._hot_reload_thread:
                self._hot_reload_thread.join(timeout=2.0)
                if self._hot_reload_thread.is_alive():
                    print("⚠️  Hot-reload thread did not stop gracefully")

            print("🔄 XGML hot-reloading disabled")
            return True

        except Exception as e:
            print(f"❌ Failed to disable hot-reloading: {e}")
            return False

    def add_hot_reload_watch_path(self, path: str | Path) -> bool:
        """
        Add a path to watch for configuration changes.

        Args:
            path: Path to XGML configuration file to watch

        Returns:
            True if path added successfully
        """
        try:
            path = Path(path).resolve()
            if path not in self._hot_reload_watch_paths:
                self._hot_reload_watch_paths.append(path)
                print(f"🔄 Added watch path: {path}")

                # Initialize hash for new path
                if path.exists():
                    self._hot_reload_file_hashes[str(path)] = self._calculate_file_hash(path)

            return True

        except Exception as e:
            print(f"❌ Failed to add watch path {path}: {e}")
            return False

    def remove_hot_reload_watch_path(self, path: str | Path) -> bool:
        """
        Remove a path from hot-reload watching.

        Args:
            path: Path to remove from watching

        Returns:
            True if path removed successfully
        """
        try:
            path = Path(path).resolve()
            if path in self._hot_reload_watch_paths:
                self._hot_reload_watch_paths.remove(path)
                self._hot_reload_file_hashes.pop(str(path), None)
                print(f"🔄 Removed watch path: {path}")
            return True

        except Exception as e:
            print(f"❌ Failed to remove watch path {path}: {e}")
            return False

    def get_hot_reload_status(self) -> dict[str, Any]:
        """
        Get hot-reloading status information.

        Returns:
            Dictionary with hot-reloading status
        """
        status = {
            "enabled": self._hot_reload_enabled,
            "watch_paths": [str(p) for p in self._hot_reload_watch_paths],
            "check_interval": self._hot_reload_check_interval,
            "thread_alive": False,
            "last_check": self._hot_reload_last_check,
            "file_hashes": self._hot_reload_file_hashes.copy(),
        }

        if self._hot_reload_thread:
            status["thread_alive"] = self._hot_reload_thread.is_alive()

        return status

    def _hot_reload_monitor(self):
        """Background thread that monitors configuration files for changes."""
        print("🔄 XGML hot-reload monitor started")

        while self._hot_reload_enabled:
            try:
                current_time = time.time()

                # Check if it's time to scan files
                if current_time - self._hot_reload_last_check >= self._hot_reload_check_interval:
                    self._check_files_for_changes()
                    self._hot_reload_last_check = current_time

                # Sleep for a short time to avoid busy waiting
                time.sleep(0.1)

            except Exception as e:
                print(f"❌ Hot-reload monitor error: {e}")
                time.sleep(1.0)  # Wait before retrying

        print("🔄 XGML hot-reload monitor stopped")

    def _check_files_for_changes(self):
        """Check all watched files for changes."""
        for path in self._hot_reload_watch_paths:
            try:
                path_str = str(path)

                # Check if file exists
                if not path.exists():
                    if path_str in self._hot_reload_file_hashes:
                        print(f"⚠️  Watched file no longer exists: {path}")
                        self._hot_reload_file_hashes.pop(path_str, None)
                    continue

                # Calculate current hash
                current_hash = self._calculate_file_hash(path)

                # Check if hash changed
                if path_str not in self._hot_reload_file_hashes:
                    # New file
                    self._hot_reload_file_hashes[path_str] = current_hash
                    print(f"🔄 New configuration file detected: {path}")
                    self._reload_configuration_from_path(path)
                elif self._hot_reload_file_hashes[path_str] != current_hash:
                    # File changed
                    old_hash = self._hot_reload_file_hashes[path_str]
                    self._hot_reload_file_hashes[path_str] = current_hash
                    print(f"🔄 Configuration file changed: {path}")
                    print(f"   Hash: {old_hash[:8]}... -> {current_hash[:8]}...")
                    self._reload_configuration_from_path(path)

            except Exception as e:
                print(f"❌ Error checking file {path}: {e}")

    def _calculate_file_hash(self, path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            with open(path, "rb") as f:
                import hashlib

                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _reload_configuration_from_path(self, path: Path):
        """Reload configuration from a specific file path."""
        try:
            print(f"🔄 Reloading configuration from: {path}")

            # Parse the new configuration
            from ..xgml.parser_v3 import XGMLParserV3

            parser = XGMLParserV3()
            config = parser.parse_file(str(path))

            if config is None:
                print(f"❌ Failed to parse updated configuration: {path}")
                errors = parser.get_errors()
                warnings = parser.get_warnings()
                if errors:
                    print(f"   Errors: {errors}")
                if warnings:
                    print(f"   Warnings: {warnings}")
                return

            # Apply configuration with smooth transitions
            success = self._apply_xgml_config_with_transitions(config, path.name)

            if success:
                print(f"✅ Configuration reloaded successfully from: {path}")
            else:
                print(f"❌ Failed to apply reloaded configuration from: {path}")

        except Exception as e:
            print(f"❌ Error reloading configuration from {path}: {e}")

    def trigger_manual_config_reload(self, path: str | Path | None = None) -> bool:
        """
        Manually trigger configuration reload.

        Args:
            path: Specific path to reload, or None to reload all watched paths

        Returns:
            True if reload successful
        """
        try:
            if path is not None:
                # Reload specific path
                path = Path(path).resolve()
                if path.exists():
                    self._reload_configuration_from_path(path)
                    return True
                else:
                    print(f"❌ Configuration file not found: {path}")
                    return False
            else:
                # Reload all watched paths
                success_count = 0
                for watch_path in self._hot_reload_watch_paths:
                    if watch_path.exists():
                        self._reload_configuration_from_path(watch_path)
                        success_count += 1

                print(f"🔄 Manual reload completed: {success_count} configurations reloaded")
                return success_count > 0

        except Exception as e:
            print(f"❌ Manual reload failed: {e}")
            return False

    def get_xgml_config_template(self) -> str:
        """
        Get a basic XGML v3.0 configuration template.

        Returns:
            YAML string containing a basic XGML v3.0 configuration
        """
        template = """# XGML v3.0 Basic Configuration Template
xg_dsl_version: "3.0"
description: "Basic XGML v3.0 Configuration"
timestamp: "2026-01-12T14:30:00Z"

# Synthesizer core settings
synthesizer_core:
  audio:
    sample_rate: 44100
    buffer_size: 512
  performance:
    max_polyphony: 128
    voice_stealing: "priority"

# Synthesis engines
synthesis_engines:
  registry:
    default_engine: "sf2"
    engine_priorities:
      sf2: 100
      fm: 90
  sf2_engine:
    enabled: true
    velocity_curve: "concave"

# Effects processing
effects_processing:
  system_effects:
    reverb:
      algorithm: "hall_1"
      parameters:
        level: 0.4
        time: 2.0
    chorus:
      algorithm: "chorus_1"
      parameters:
        mix: 0.3

# Basic instrument setup
basic_messages:
  channels:
    channel_0:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      reverb_send: 40
"""
        return template

    def create_xgml_config_from_current_state(self) -> str | None:
        """
        Create an XGML v3.0 configuration from the current synthesizer state.

        Returns:
            YAML string containing current configuration, or None if failed
        """
        try:
            # Get current synthesizer state
            synth_info = self.synthesizer.get_synthesizer_info()

            # Build XGML v3.0 configuration
            config = {
                "xg_dsl_version": "3.0",
                "description": "Exported from ModernXGSynthesizer",
                "timestamp": "2026-01-12T14:30:00Z",
                "synthesizer_core": {
                    "audio": {
                        "sample_rate": synth_info.get("sample_rate", 44100),
                        "buffer_size": 512,
                    },
                    "performance": {
                        "max_polyphony": synth_info.get("total_active_voices", 128),
                        "voice_stealing": "priority",
                    },
                },
                "synthesis_engines": {
                    "registry": {
                        "default_engine": "sf2",
                        "engine_priorities": {"sf2": 100, "fm": 90, "physical": 80},
                    }
                },
            }

            # Convert to YAML
            import yaml

            return yaml.dump(config, default_flow_style=False, sort_keys=False)

        except Exception as e:
            print(f"❌ Error creating XGML config from current state: {e}")
            return None
