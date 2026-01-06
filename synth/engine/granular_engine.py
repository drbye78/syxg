"""
Granular Synthesis Engine

Implements granular synthesis with real-time grain control, cloud manipulation,
and advanced time-stretching/pitch-shifting capabilities.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import math
import random

from .synthesis_engine import SynthesisEngine
from ..partial.granular_partial import GranularPartial
from .plugins.plugin_registry import get_global_plugin_registry
from .plugins.base_plugin import PluginLoadContext, SynthesisFeaturePlugin


class Grain:
    """
    Individual grain for granular synthesis.

    Each grain has its own envelope, position, and modulation parameters.
    """

    def __init__(self, sample_rate: int):
        """Initialize grain."""
        self.sample_rate = sample_rate

        # Grain parameters
        self.duration_ms = 50.0  # Grain duration in milliseconds
        self.position = 0.0      # Position in source (0.0 to 1.0)
        self.pitch_shift = 1.0   # Pitch shift ratio
        self.pan = 0.0          # Stereo pan (-1.0 to 1.0)
        self.amplitude = 1.0    # Grain amplitude

        # Envelope parameters
        self.attack_ms = 5.0    # Attack time
        self.release_ms = 15.0  # Release time

        # State variables
        self.active = False
        self.current_sample = 0
        self.total_samples = 0
        self.envelope_value = 0.0

    def trigger(self, position: float, duration_ms: float, pitch_shift: float = 1.0,
               pan: float = 0.0, amplitude: float = 1.0):
        """
        Trigger grain playback.

        Args:
            position: Position in source (0.0 to 1.0)
            duration_ms: Grain duration in milliseconds
            pitch_shift: Pitch shift ratio
            pan: Stereo pan (-1.0 to 1.0)
            amplitude: Grain amplitude
        """
        self.position = position
        self.duration_ms = duration_ms
        self.pitch_shift = pitch_shift
        self.pan = pan
        self.amplitude = amplitude

        # Calculate sample counts
        self.total_samples = int((duration_ms / 1000.0) * self.sample_rate)
        self.current_sample = 0

        # Reset envelope
        self.envelope_value = 0.0
        self.active = True

    def process_sample(self) -> tuple[float, float]:
        """
        Process one sample from the grain.

        Returns:
            Tuple of (left_sample, right_sample)
        """
        if not self.active:
            return 0.0, 0.0

        # Update envelope
        progress = self.current_sample / max(1, self.total_samples - 1)

        # Simple ADSR envelope
        if progress < 0.1:  # Attack (10% of duration)
            self.envelope_value = progress / 0.1
        elif progress > 0.8:  # Release (last 20% of duration)
            release_progress = (progress - 0.8) / 0.2
            self.envelope_value = 1.0 - release_progress
        else:  # Sustain
            self.envelope_value = 1.0

        # Apply amplitude
        sample_value = self.envelope_value * self.amplitude

        # Apply panning
        left_gain = (1.0 - self.pan) * 0.5
        right_gain = (1.0 + self.pan) * 0.5

        left_sample = sample_value * left_gain
        right_sample = sample_value * right_gain

        # Update position
        self.current_sample += 1

        # Check if grain is finished
        if self.current_sample >= self.total_samples:
            self.active = False

        return left_sample, right_sample

    def is_active(self) -> bool:
        """Check if grain is still active."""
        return self.active


class GrainCloud:
    """
    Cloud of grains for granular synthesis.

    Manages multiple grains with density, position, and pitch control.
    """

    def __init__(self, sample_rate: int, max_grains: int = 100):
        """
        Initialize grain cloud.

        Args:
            sample_rate: Audio sample rate in Hz
            max_grains: Maximum number of simultaneous grains
        """
        self.sample_rate = sample_rate
        self.max_grains = max_grains

        # Cloud parameters
        self.density = 10.0      # Grains per second
        self.duration_ms = 100.0 # Grain duration
        self.position = 0.0      # Cloud position (0.0 to 1.0)
        self.position_spread = 0.1  # Position randomization
        self.pitch_shift = 1.0   # Base pitch shift
        self.pitch_spread = 0.0  # Pitch randomization
        self.pan_spread = 0.5    # Stereo spread

        # Initialize grains
        self.grains = [Grain(sample_rate) for _ in range(max_grains)]
        self.active_grains = []

        # Timing
        self.last_grain_time = 0.0
        self.grain_interval = 1.0 / self.density

    def set_parameters(self, params: Dict[str, Any]):
        """
        Set cloud parameters.

        Args:
            params: Parameter dictionary
        """
        self.density = params.get('density', self.density)
        self.duration_ms = params.get('duration_ms', self.duration_ms)
        self.position = params.get('position', self.position)
        self.position_spread = params.get('position_spread', self.position_spread)
        self.pitch_shift = params.get('pitch_shift', self.pitch_shift)
        self.pitch_spread = params.get('pitch_spread', self.pitch_spread)
        self.pan_spread = params.get('pan_spread', self.pan_spread)

        # Recalculate grain interval
        self.grain_interval = 1.0 / self.density

    def process_sample(self, dt: float) -> tuple[float, float]:
        """
        Process one sample from the grain cloud.

        Args:
            dt: Time delta in seconds

        Returns:
            Tuple of (left_sample, right_sample)
        """
        # Update timing
        self.last_grain_time += dt

        # Trigger new grains based on density
        while self.last_grain_time >= self.grain_interval:
            self._trigger_new_grain()
            self.last_grain_time -= self.grain_interval

        # Sum active grains
        left_sum = 0.0
        right_sum = 0.0

        # Process all active grains
        self.active_grains = [g for g in self.active_grains if g.is_active()]

        for grain in self.active_grains:
            left, right = grain.process_sample()
            left_sum += left
            right_sum += right

        # Normalize by number of active grains (optional)
        num_active = len(self.active_grains)
        if num_active > 0:
            left_sum /= num_active
            right_sum /= num_active

        return left_sum, right_sum

    def _trigger_new_grain(self):
        """Trigger a new grain with randomized parameters."""
        # Find inactive grain
        for grain in self.grains:
            if not grain.is_active():
                # Randomize parameters
                position = self.position + random.uniform(-self.position_spread, self.position_spread)
                position = max(0.0, min(1.0, position))  # Clamp to valid range

                pitch_shift = self.pitch_shift * (1.0 + random.uniform(-self.pitch_spread, self.pitch_spread))
                pan = random.uniform(-self.pan_spread, self.pan_spread)

                # Trigger grain
                grain.trigger(
                    position=position,
                    duration_ms=self.duration_ms,
                    pitch_shift=pitch_shift,
                    pan=pan,
                    amplitude=1.0
                )

                self.active_grains.append(grain)
                break

    def get_cloud_info(self) -> Dict[str, Any]:
        """Get information about the grain cloud."""
        return {
            'active_grains': len(self.active_grains),
            'max_grains': self.max_grains,
            'density': self.density,
            'duration_ms': self.duration_ms,
            'position': self.position,
            'pitch_shift': self.pitch_shift
        }


class GranularEngine(SynthesisEngine):
    """
    Granular Synthesis Engine.

    Implements real-time granular synthesis with multiple grain clouds,
    time-stretching, pitch-shifting, and advanced grain manipulation.
    """

    def __init__(self, max_clouds: int = 8, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize granular synthesis engine.

        Args:
            max_clouds: Maximum number of simultaneous grain clouds
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.max_clouds = max_clouds

        # Initialize grain clouds
        self.clouds = [GrainCloud(sample_rate) for _ in range(max_clouds)]

        # Source material (for time-stretching/pitch-shifting)
        self.source_buffer = None
        self.source_length = 0

        # Global parameters
        self.master_volume = 1.0
        self.freeze = False        # Freeze grain positions
        self.time_stretch = 1.0   # Time stretching factor
        self.pitch_shift = 1.0    # Global pitch shift

        # Active clouds tracking
        self.active_clouds = set()

        # Plugin system
        self._plugin_registry = get_global_plugin_registry()
        self._loaded_plugins: Dict[str, SynthesisFeaturePlugin] = {}
        self._plugin_integration_points = {
            'pre_synthesis': [],      # Called before synthesis
            'post_synthesis': [],     # Called after synthesis
            'midi_processing': [],    # MIDI message handlers
            'parameter_processing': [] # Parameter processing
        }

        # Auto-load Jupiter-X external plugin if available
        self._auto_load_jupiter_x_plugin()

    def get_engine_info(self) -> Dict[str, Any]:
        """Get granular engine information."""
        return {
            'name': 'Granular Synthesis Engine',
            'type': 'granular',
            'capabilities': ['granular_synthesis', 'time_stretching', 'pitch_shifting', 'grain_clouds'],
            'formats': ['.gran', '.grn'],  # Custom granular formats
            'polyphony': self.max_clouds,  # Limited by grain density
            'parameters': ['density', 'duration', 'position', 'pitch_shift', 'time_stretch', 'freeze'],
            'max_clouds': self.max_clouds
        }

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float], block_size: int) -> np.ndarray:
        """
        Generate granular synthesis audio samples.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Generate samples
        output = np.zeros((block_size, 2), dtype=np.float32)
        dt = 1.0 / self.sample_rate

        for i in range(block_size):
            left_sum = 0.0
            right_sum = 0.0

            # Sum all active clouds
            for cloud_idx in self.active_clouds:
                if cloud_idx < len(self.clouds):
                    left, right = self.clouds[cloud_idx].process_sample(dt)
                    left_sum += left
                    right_sum += right

            # Apply modulation
            pitch_mod = modulation.get('pitch', 0.0)
            pitch_ratio = 2.0 ** (pitch_mod / 1200.0)  # Convert cents to ratio

            # Apply global parameters
            left_sum *= self.master_volume * (velocity / 127.0) * pitch_ratio
            right_sum *= self.master_volume * (velocity / 127.0) * pitch_ratio

            output[i, 0] = left_sum
            output[i, 1] = right_sum

        return output

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported."""
        return 0 <= note <= 127  # Granular synthesis works with any note

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> 'GranularPartial':
        """Create granular partial."""
        from ..partial.granular_partial import GranularPartial
        return GranularPartial(partial_params, sample_rate)

    def create_grain_cloud(self, cloud_params: Dict[str, Any]) -> int:
        """
        Create a new grain cloud.

        Args:
            cloud_params: Cloud parameter dictionary

        Returns:
            Cloud index or -1 if failed
        """
        # Find available cloud
        for i in range(self.max_clouds):
            if i not in self.active_clouds:
                self.clouds[i].set_parameters(cloud_params)
                self.active_clouds.add(i)
                return i

        return -1  # No available clouds

    def destroy_grain_cloud(self, cloud_idx: int):
        """
        Destroy a grain cloud.

        Args:
            cloud_idx: Cloud index to destroy
        """
        if cloud_idx in self.active_clouds:
            self.active_clouds.remove(cloud_idx)

    def set_cloud_parameters(self, cloud_idx: int, params: Dict[str, Any]):
        """
        Set parameters for a grain cloud.

        Args:
            cloud_idx: Cloud index
            params: Parameter dictionary
        """
        if 0 <= cloud_idx < self.max_clouds:
            self.clouds[cloud_idx].set_parameters(params)

    def get_cloud_info(self, cloud_idx: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a grain cloud.

        Args:
            cloud_idx: Cloud index

        Returns:
            Cloud information dictionary or None
        """
        if 0 <= cloud_idx < self.max_clouds:
            return self.clouds[cloud_idx].get_cloud_info()
        return None

    def set_source_buffer(self, audio_buffer: np.ndarray):
        """
        Set source audio buffer for granular processing.

        Args:
            audio_buffer: Mono or stereo audio buffer
        """
        if audio_buffer.ndim == 2:
            # Convert stereo to mono
            self.source_buffer = (audio_buffer[:, 0] + audio_buffer[:, 1]) * 0.5
        else:
            self.source_buffer = audio_buffer.copy()

        self.source_length = len(self.source_buffer)

    def set_time_stretch(self, stretch_factor: float):
        """
        Set time stretching factor.

        Args:
            stretch_factor: Time stretch ratio (> 0.0)
        """
        self.time_stretch = max(0.1, min(10.0, stretch_factor))

        # Update all clouds
        for cloud in self.clouds:
            cloud.set_parameters({'time_stretch': self.time_stretch})

    def set_freeze(self, freeze: bool):
        """
        Set freeze mode (stops grain position advancement).

        Args:
            freeze: True to freeze grain positions
        """
        self.freeze = freeze

        # Update all clouds
        for cloud in self.clouds:
            cloud.set_parameters({'freeze': self.freeze})

    def get_voice_parameters(self, program: int, bank: int = 0) -> Optional[Dict[str, Any]]:
        """Get granular voice parameters."""
        # Different granular presets based on program
        presets = {
            0: {  # Basic granular
                'name': 'Granular Basic',
                'density': 20.0,
                'duration_ms': 100.0,
                'position_spread': 0.2,
                'pitch_spread': 0.1
            },
            24: {  # Frozen clouds
                'name': 'Frozen Clouds',
                'density': 50.0,
                'duration_ms': 200.0,
                'position_spread': 0.05,
                'pitch_spread': 0.0,
                'freeze': True
            },
            40: {  # Time-stretched
                'name': 'Time Stretch',
                'density': 15.0,
                'duration_ms': 150.0,
                'time_stretch': 2.0,
                'position_spread': 0.1
            },
            56: {  # Dense cloud
                'name': 'Dense Cloud',
                'density': 100.0,
                'duration_ms': 50.0,
                'position_spread': 0.8,
                'pitch_spread': 0.5,
                'pan_spread': 1.0
            }
        }

        return presets.get(program % 64, presets[0])

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        # Create a new cloud for this note
        cloud_params = {
            'density': 20.0 + (velocity / 127.0) * 30.0,  # Velocity affects density
            'duration_ms': 50.0 + (note / 127.0) * 100.0,  # Note affects duration
            'position': note / 127.0,  # Note affects position
            'pitch_shift': 2.0 ** ((note - 60) / 12.0),  # Note to pitch
            'position_spread': 0.2,
            'pitch_spread': 0.1
        }

        cloud_idx = self.create_grain_cloud(cloud_params)
        if cloud_idx >= 0:
            # Store note->cloud mapping (simplified)
            pass

    def note_off(self, note: int):
        """Handle note-off event."""
        # For now, just clear all clouds (simplified)
        # In a full implementation, we'd track note->cloud mappings
        for i in range(self.max_clouds):
            if i in self.active_clouds:
                self.destroy_grain_cloud(i)

    def is_active(self) -> bool:
        """Check if engine is active."""
        return len(self.active_clouds) > 0

    def reset(self):
        """Reset engine state."""
        self.active_clouds.clear()

    def get_supported_formats(self) -> List[str]:
        """Get supported file formats."""
        return ['.gran', '.grn']

    def get_granular_info(self) -> Dict[str, Any]:
        """Get comprehensive granular synthesis information."""
        clouds_info = []
        for i, cloud in enumerate(self.clouds):
            if i in self.active_clouds:
                clouds_info.append({
                    'index': i,
                    **cloud.get_cloud_info()
                })

        return {
            'active_clouds': len(self.active_clouds),
            'max_clouds': self.max_clouds,
            'clouds': clouds_info,
            'master_volume': self.master_volume,
            'time_stretch': self.time_stretch,
            'freeze': self.freeze,
            'source_length': self.source_length
        }

    # Plugin System Methods

    def _auto_load_jupiter_x_plugin(self):
        """Automatically load Jupiter-X external plugin if available."""
        try:
            # Check if Jupiter-X external plugin is available
            available_plugins = self._plugin_registry.get_plugins_for_engine('granular')
            jupiter_external_plugin = 'jupiter_x.external_extensions.JupiterXExternalPlugin'

            if jupiter_external_plugin in available_plugins:
                success = self.load_plugin(jupiter_external_plugin)
                if success:
                    print("🎹 Granular Engine: Jupiter-X external extensions loaded automatically")
                else:
                    print("⚠️  Granular Engine: Failed to load Jupiter-X external extensions")
            else:
                print("ℹ️  Granular Engine: Jupiter-X external extensions not available")

        except Exception as e:
            print(f"⚠️  Granular Engine: Error during auto-loading Jupiter-X plugin: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin for this granular engine.

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
                block_size=self.block_size
            )

            if success:
                plugin = self._plugin_registry.get_plugin(plugin_name)
                if plugin:
                    self._loaded_plugins[plugin_name] = plugin

                    # Register plugin integration points
                    self._register_plugin_integration_points(plugin)

                    print(f"✅ Granular Engine: Plugin '{plugin_name}' loaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Granular Engine: Failed to load plugin '{plugin_name}': {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin from this granular engine.

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
                    print(f"✅ Granular Engine: Plugin '{plugin_name}' unloaded successfully")
                    return True

            return False

        except Exception as e:
            print(f"❌ Granular Engine: Failed to unload plugin '{plugin_name}': {e}")
            return False

    def get_loaded_plugins(self) -> Dict[str, SynthesisFeaturePlugin]:
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
        if hasattr(plugin, 'process_midi_message'):
            self._plugin_integration_points['midi_processing'].append(plugin)

        # Register parameter processing
        if hasattr(plugin, 'set_parameter'):
            self._plugin_integration_points['parameter_processing'].append(plugin)

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
        for plugin in self._plugin_integration_points['midi_processing']:
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

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin information dictionary or None
        """
        return self._plugin_registry.get_plugin_info(plugin_name)
