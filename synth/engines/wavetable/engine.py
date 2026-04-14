"""Wavetable synthesis engine."""

from __future__ import annotations
from typing import Any
import numpy as np
from ...io.audio.sample_manager import PyAVSampleManager
from ...processing.partial import SynthesisPartial
from ...processing.partial.region import Region
from ..plugins.base_plugin import SynthesisFeaturePlugin
from ..plugins.plugin_registry import get_global_plugin_registry
from ..synthesis_engine import SynthesisEngine
from .wavetable import Wavetable
from .oscillator import WavetableOscillator
from .bank import WavetableBank
from .partial import WavetablePartial
from .region import WavetableRegion


class WavetableEngine(SynthesisEngine):
    """
    Wavetable Synthesis Engine

    Provides efficient wavetable-based synthesis with real-time morphing,
    multiple oscillators, and advanced modulation capabilities.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024, max_oscillators: int = 64):
        """
        Initialize wavetable synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            max_oscillators: Maximum number of simultaneous oscillators
        """
        super().__init__(sample_rate, block_size)

        # Core components
        self.wavetable_bank = WavetableBank()
        self.oscillators = [WavetableOscillator(sample_rate) for _ in range(max_oscillators)]
        self.sample_manager = PyAVSampleManager()

        # Engine state
        self.active_oscillators: list[int] = []  # Indices of active oscillators
        self.current_wavetable = "sine"  # Default wavetable

        # Initialize with basic wavetables
        self._initialize_basic_wavetables()

        # Plugin system
        self._plugin_registry = get_global_plugin_registry()
        self._loaded_plugins: dict[str, SynthesisFeaturePlugin] = {}
        self._plugin_integration_points = {
            "pre_synthesis": [],  # Called before synthesis
            "post_synthesis": [],  # Called after synthesis
            "midi_processing": [],  # MIDI message handlers
            "parameter_processing": [],  # Parameter processing
        }

        # Auto-load Jupiter-X digital plugin if available
        self._auto_load_jupiter_x_plugin()

    def _initialize_basic_wavetables(self):
        """Initialize engine with basic mathematical wavetables."""
        basic_waveforms = ["sine", "triangle", "square", "sawtooth"]

        for waveform in basic_waveforms:
            self.wavetable_bank.create_wavetable_from_waveform(waveform, waveform, size=2048)

        # Set default wavetable for all oscillators
        default_wt = self.wavetable_bank.get_wavetable("sine")
        if default_wt:
            for osc in self.oscillators:
                osc.set_wavetable(default_wt)

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return "wavetable"

    def load_wavetable(self, file_path: str, name: str) -> bool:
        """
        Load wavetable from audio file.

        Args:
            file_path: Path to audio file
            name: Name for the wavetable

        Returns:
            True if loaded successfully
        """
        return self.wavetable_bank.load_wavetable_from_file(file_path, name, self.sample_manager)

    def create_wavetable(self, waveform_type: str, name: str, size: int = 2048) -> bool:
        """
        Create mathematical wavetable.

        Args:
            waveform_type: Type of waveform
            name: Name for the wavetable
            size: Wavetable size

        Returns:
            True if created successfully
        """
        return self.wavetable_bank.create_wavetable_from_waveform(waveform_type, name, size)

    def set_wavetable(self, name: str):
        """
        Set current wavetable for new notes.

        Args:
            name: Name of wavetable to use
        """
        wavetable = self.wavetable_bank.get_wavetable(name)
        if wavetable:
            self.current_wavetable = name
            # Update all oscillators to use this wavetable
            for osc in self.oscillators:
                osc.set_wavetable(wavetable)

    def create_morph_group(self, group_name: str, wavetable_names: list[str]):
        """Create a wavetable morph group."""
        self.wavetable_bank.create_morph_group(group_name, wavetable_names)

    def get_morph_group(self, group_name: str) -> list[str]:
        """Get wavetable names in morph group."""
        return self.wavetable_bank.get_morph_group(group_name)

    def get_regions_for_note(
        self, note: int, velocity: int, program: int = 0, bank: int = 0
    ) -> list[Any]:
        """
        Get regions for note (wavetable engine creates regions dynamically).

        Returns:
            List containing a proper WavetableRegion
        """
        # Create proper region parameters
        region_params = {
            "note": note,
            "velocity": velocity,
            "wavetable": self.current_wavetable,
            "key_range_low": note,
            "key_range_high": note,
            "velocity_range_low": velocity,
            "velocity_range_high": velocity,
        }

        # Return proper WavetableRegion instance
        return [WavetableRegion(region_params, self.wavetable_bank)]

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int) -> SynthesisPartial:
        """
        Create wavetable partial for synthesis.

        Args:
            partial_params: Parameters for the partial
            sample_rate: Audio sample rate

        Returns:
            Configured WavetablePartial
        """
        return WavetablePartial(partial_params, sample_rate, self.wavetable_bank)

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples using wavetable synthesis.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Find or allocate oscillator for this note
        oscillator = self._find_or_allocate_oscillator(note)

        if not oscillator:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Configure oscillator
        oscillator.set_note(note, velocity)

        # Apply modulation
        freq_mod = modulation.get("pitch", 0.0) / 1200.0  # Convert cents to ratio
        amp_mod = modulation.get("volume", 0.0)
        wt_pos = modulation.get("timbre", 0.0)  # Use timbre for wavetable position

        oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

        # Generate samples
        mono_audio = oscillator.generate_samples(block_size)

        # Convert to stereo
        stereo_audio = np.column_stack([mono_audio, mono_audio])

        # Apply additional processing
        stereo_audio = self._apply_modulation(stereo_audio, modulation, block_size)

        return stereo_audio

    def _find_or_allocate_oscillator(self, note: int) -> WavetableOscillator | None:
        """Find existing oscillator for note or allocate new one."""
        # First, check if we already have an oscillator for this note
        for idx in self.active_oscillators:
            if self.oscillators[idx].note == note and self.oscillators[idx].is_active():
                return self.oscillators[idx]

        # Find free oscillator
        for i, osc in enumerate(self.oscillators):
            if not osc.is_active():
                # Set current wavetable
                wavetable = self.wavetable_bank.get_wavetable(self.current_wavetable)
                if wavetable:
                    osc.set_wavetable(wavetable)

                if i not in self.active_oscillators:
                    self.active_oscillators.append(i)

                return osc

        # No free oscillators
        return None

    def _apply_modulation(
        self, audio: np.ndarray, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """Apply additional modulation effects to generated audio."""
        # Pan modulation
        if "pan" in modulation:
            pan = np.clip(modulation["pan"], -1.0, 1.0)
            left_gain = 1.0 - max(0.0, pan)
            right_gain = 1.0 - max(0.0, -pan)
            audio[:, 0] *= left_gain
            audio[:, 1] *= right_gain

        # Filter modulation (simple lowpass)
        if "cutoff" in modulation:
            cutoff_norm = np.clip(modulation["cutoff"] / 20000.0, 0.0, 1.0)
            # Simple smoothing filter based on cutoff
            alpha = 0.1 + cutoff_norm * 0.8  # Higher cutoff = less smoothing

            # Apply simple lowpass per channel
            for ch in range(2):
                for i in range(1, block_size):
                    audio[i, ch] = alpha * audio[i, ch] + (1 - alpha) * audio[i - 1, ch]

        return audio

    def is_note_supported(self, note: int) -> bool:
        """Check if note is supported (all notes supported in wavetable synthesis)."""
        return 0 <= note <= 127

    def get_supported_formats(self) -> list[str]:
        """Get supported file formats for wavetable loading."""
        return [".wav", ".aiff", ".flac", ".ogg"]

    def get_engine_info(self) -> dict[str, Any]:
        """Get comprehensive engine information."""
        bank_stats = self.wavetable_bank.get_stats()

        return {
            "name": "Wavetable Synthesis Engine",
            "type": "wavetable",
            "version": "1.0",
            "capabilities": [
                "wavetable_synthesis",
                "real_time_morphing",
                "mathematical_waveforms",
                "frequency_modulation",
                "amplitude_modulation",
                "multi_oscillator",
                "unison_detuning",
                "wavetable_scanning",
            ],
            "formats": self.get_supported_formats(),
            "max_oscillators": len(self.oscillators),
            "active_oscillators": len(self.active_oscillators),
            "wavetable_bank": bank_stats,
            "parameters": [
                "wavetable",
                "frequency",
                "amplitude",
                "pan",
                "cutoff",
                "pitch_mod",
                "amp_mod",
                "timbre_mod",
            ],
            "modulation_sources": ["velocity", "key", "cc1-cc127", "pitch_bend", "aftertouch"],
            "modulation_destinations": [
                "frequency",
                "amplitude",
                "pan",
                "cutoff",
                "wavetable_position",
            ],
        }

    # ========== REGION-BASED ARCHITECTURE IMPLEMENTATION ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get wavetable preset information with proper region descriptors.

        Args:
            bank: Preset bank number (0-127)
            program: Preset program number (0-127)

        Returns:
            PresetInfo with region descriptors for wavetable synthesis
        """
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor

        # Wavetable engine uses wavetable synthesis with morphing
        # Programs define wavetable configurations and morphing settings
        preset_name = f"Wavetable {bank}:{program}"

        # Get wavetable name from preset bank
        wavetable_name = self.get_wavetable_preset_name(bank, program)
        if not wavetable_name:
            wavetable_name = "default"

        # Create region descriptors for wavetable synthesis
        # Wavetable supports polyphonic playback with full keyboard range
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type=self.get_engine_type(),
            key_range=(0, 127),
            velocity_range=(0, 127),
            algorithm_params={
                "wavetable_name": wavetable_name,
                "wavetable_position": 0.0,  # Start position in wavetable
                "wavetable_morph": 0.0,  # Morph between wavetables
                "oscillator_count": 2,  # Dual oscillator wavetable synthesis
                "unison_detune": 0.0,  # Unison detuning
                "filter_type": "lowpass",
                "filter_cutoff": 2000.0,  # Hz
                "filter_resonance": 0.5,
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=preset_name,
            engine_type=self.get_engine_type(),
            region_descriptors=[descriptor],
            is_monophonic=False,
            category="wavetable_synthesis",
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """
        Get all region descriptors for wavetable preset.

        Args:
            bank: Preset bank number
            program: Preset program number

        Returns:
            List of RegionDescriptor objects
        """
        preset_info = self.get_preset_info(bank, program)
        return preset_info.region_descriptors if preset_info else []

    def create_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create wavetable region instance from descriptor.

        Args:
            descriptor: Region descriptor with wavetable parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance for wavetable synthesis
        """
        from ..processing.partial.wavetable_region import WavetableRegion

        # Create wavetable region with proper initialization
        region = WavetableRegion(descriptor, sample_rate)

        # Initialize the region (loads wavetable data, creates oscillators)
        if not region.initialize():
            raise RuntimeError("Failed to initialize Wavetable region")

        return region

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load wavetable data for region.

        Args:
            region: Region to load wavetable for

        Returns:
            True if wavetable loaded successfully
        """
        # Wavetable data is loaded during region initialization
        # This method ensures the wavetable is properly loaded
        if hasattr(region, "load_wavetable"):
            return region.load_wavetable()
        return region._initialized if hasattr(region, "_initialized") else False

    def get_available_wavetables(self) -> list[str]:
        """Get list of available wavetable names."""
        return self.wavetable_bank.list_wavetables()

    def get_wavetable_info(self, name: str) -> dict[str, Any] | None:
        """Get information about a specific wavetable."""
        wavetable = self.wavetable_bank.get_wavetable(name)
        if not wavetable:
            return None

        return {
            "name": wavetable.name,
            "length": wavetable.length,
            "sample_rate": wavetable.sample_rate,
            "duration_ms": (wavetable.length / wavetable.sample_rate) * 1000,
        }

    def reset(self) -> None:
        """Reset engine to clean state."""
        for osc in self.oscillators:
            osc.reset()
        self.active_oscillators.clear()

    def cleanup(self) -> None:
        """Clean up engine resources."""
        self.reset()
        self.wavetable_bank.wavetables.clear()

    def __str__(self) -> str:
        """String representation."""
        info = self.get_engine_info()
        return (
            f"WavetableEngine(oscillators={info['max_oscillators']}, "
            f"active={info['active_oscillators']}, "
            f"wavetables={info['wavetable_bank']['total_wavetables']})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    # Plugin System Methods

    def _auto_load_jupiter_x_plugin(self):
        """Automatically load Jupiter-X digital plugin if available."""
        try:
            # Check if Jupiter-X digital plugin is available
            available_plugins = self._plugin_registry.get_plugins_for_engine("wavetable")
            jupiter_digital_plugin = "jupiter_x.digital_extensions.JupiterXDigitalPlugin"

            if jupiter_digital_plugin in available_plugins:
                success = self.load_plugin(jupiter_digital_plugin)
                if success:
                    print("🎹 Wavetable Engine: Jupiter-X digital extensions loaded automatically")
                else:
                    print("⚠️  Wavetable Engine: Failed to load Jupiter-X digital extensions")
            else:
                print("ℹ️  Wavetable Engine: Jupiter-X digital extensions not available")

        except Exception as e:
            print(f"⚠️  Wavetable Engine: Error during auto-loading Jupiter-X plugin: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin for this wavetable engine.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Load plugin using registry
            success = self._plugin_registry.load_plugin(
                plugin_name,
                engine_instance=self,
                sample_rate=self.sample_rate,
                block_size=self.block_size,
            )

            if success:
                plugin = self._plugin_registry.get_plugin(plugin_name)
                if plugin:
                    self._loaded_plugins[plugin_name] = plugin

                    # Register plugin integration points
                    self._register_plugin_integration_points(plugin)

                    print(f"✅ Wavetable Engine: Plugin '{plugin_name}' loaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Wavetable Engine: Failed to load plugin '{plugin_name}': {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin from this wavetable engine.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if plugin_name in self._loaded_plugins:
                plugin = self._loaded_plugins[plugin_name]

                # Unregister plugin integration points
                self._unregister_plugin_integration_points(plugin)

                # Unload from registry
                success = self._plugin_registry.unload_plugin(plugin_name)

                if success:
                    del self._loaded_plugins[plugin_name]
                    print(f"✅ Wavetable Engine: Plugin '{plugin_name}' unloaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Wavetable Engine: Failed to unload plugin '{plugin_name}': {e}")
            return False

    def get_loaded_plugins(self) -> dict[str, SynthesisFeaturePlugin]:
        """Get all plugins loaded for this engine."""
        return self._loaded_plugins.copy()

    def _register_plugin_integration_points(self, plugin: SynthesisFeaturePlugin):
        """
        Register plugin integration points.

        Args:
            plugin: Plugin to register
        """
        # Register modulation sources
        modulation_sources = plugin.get_modulation_sources()
        for source_name, source_func in modulation_sources.items():
            # Add to engine's modulation sources (would need modulation system)
            pass

        # Register modulation destinations
        modulation_destinations = plugin.get_modulation_destinations()
        for dest_name, dest_func in modulation_destinations.items():
            # Add to engine's modulation destinations
            pass

        # Register MIDI processing
        if hasattr(plugin, "process_midi_message"):
            self._plugin_integration_points["midi_processing"].append(plugin)

        # Register parameter processing
        if hasattr(plugin, "set_parameter"):
            self._plugin_integration_points["parameter_processing"].append(plugin)

    def _unregister_plugin_integration_points(self, plugin: SynthesisFeaturePlugin):
        """
        Unregister plugin integration points.

        Args:
            plugin: Plugin to unregister
        """
        # Remove from integration points
        for point_name, plugins in self._plugin_integration_points.items():
            if plugin in plugins:
                plugins.remove(plugin)

    def process_plugin_midi(self, status: int, data1: int, data2: int) -> bool:
        """
        Process MIDI message through loaded plugins.

        Args:
            status: MIDI status byte
            data1: MIDI data byte 1
            data2: MIDI data byte 2

        Returns:
            True if any plugin handled the message
        """
        handled = False
        for plugin in self._plugin_integration_points["midi_processing"]:
            if plugin.process_midi_message(status, data1, data2):
                handled = True

        return handled

    def set_plugin_parameter(self, plugin_name: str, param_name: str, value: Any) -> bool:
        """
        Set parameter on a loaded plugin.

        Args:
            plugin_name: Name of the plugin
            param_name: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set
        """
        if plugin_name in self._loaded_plugins:
            plugin = self._loaded_plugins[plugin_name]
            return plugin.set_parameter(param_name, value)
        return False

    def get_plugin_parameter(self, plugin_name: str, param_name: str) -> Any:
        """
        Get parameter value from a loaded plugin.

        Args:
            plugin_name: Name of the plugin
            param_name: Parameter name

        Returns:
            Parameter value or None if not found
        """
        if plugin_name in self._loaded_plugins:
            plugin = self._loaded_plugins[plugin_name]
            params = plugin.get_parameters()
            return params.get(param_name)
        return None

    def _create_base_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create Wavetable base region without S.Art2 wrapper.

        Args:
            descriptor: Region descriptor with wavetable parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            WavetableRegion instance
        """
        from ..processing.partial.wavetable_region import WavetableRegion

        return WavetableRegion(descriptor, sample_rate)

    def get_plugin_info(self, plugin_name: str) -> dict[str, Any] | None:
        """
        Get information about a loaded plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin information dictionary or None
        """
        return self._plugin_registry.get_plugin_info(plugin_name)
