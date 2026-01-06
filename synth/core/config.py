"""
Synthesizer Configuration Management

Central configuration system for synthesizer settings, hardware profiles,
performance presets, and system parameters.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AudioConfig:
    """Audio system configuration"""
    sample_rate: int = 44100
    buffer_size: int = 1024
    channels: int = 2
    bit_depth: int = 24
    device_name: Optional[str] = None
    latency_ms: float = 10.0


@dataclass
class EngineConfig:
    """Synthesis engine configuration"""
    default_engine_priority: Optional[Dict[str, int]] = None
    max_voices_per_engine: Optional[Dict[str, int]] = None
    engine_enabled: Optional[Dict[str, bool]] = None

    def __post_init__(self):
        if self.default_engine_priority is None:
            self.default_engine_priority = {
                'fdsp': 10, 'an': 9, 'sf2': 8, 'xg': 7,
                'fm': 6, 'wavetable': 5, 'additive': 4
            }
        if self.max_voices_per_engine is None:
            self.max_voices_per_engine = {
                'fdsp': 32, 'an': 32, 'sf2': 64, 'xg': 64,
                'fm': 32, 'wavetable': 32, 'additive': 32
            }
        if self.engine_enabled is None:
            self.engine_enabled = {
                'fdsp': True, 'an': True, 'sf2': True, 'xg': True,
                'fm': True, 'wavetable': True, 'additive': True
            }


@dataclass
class MemoryConfig:
    """Memory management configuration"""
    sample_cache_mb: int = 512
    preset_cache_mb: int = 64
    max_loaded_samples: int = 1000
    max_loaded_presets: int = 100
    garbage_collection_interval_s: int = 60


@dataclass
class PerformanceConfig:
    """Performance optimization settings"""
    polyphony_limit: int = 64
    voice_stealing_strategy: str = 'priority'  # 'priority', 'oldest', 'quietest'
    cpu_optimization_level: str = 'balanced'  # 'maximum', 'balanced', 'quality'
    memory_optimization: bool = True
    background_processing: bool = True
    real_time_priority: bool = True


@dataclass
class HardwareConfig:
    """Hardware compatibility configuration"""
    model: str = 'S90'  # 'S70', 'S90', 'S90ES'
    simulate_hardware_latency: bool = True
    hardware_parameter_ranges: bool = True
    authentic_voice_allocation: bool = True


@dataclass
class MIDIConfig:
    """MIDI system configuration"""
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    midi_through: bool = False
    sysex_enabled: bool = True
    nrpn_enabled: bool = True
    rpn_enabled: bool = True
    midi_clock_source: str = 'internal'  # 'internal', 'external', 'auto'


@dataclass
class PathConfig:
    """File system paths configuration"""
    sample_directories: List[str] = None
    preset_directories: List[str] = None
    user_data_directory: str = '~/.syxg'
    temp_directory: str = '/tmp/syxg'
    log_directory: str = '~/.syxg/logs'

    def __post_init__(self):
        if self.sample_directories is None:
            self.sample_directories = [
                '~/.syxg/samples',
                '/usr/share/sounds/sf2',
                '/usr/share/soundfonts'
            ]
        if self.preset_directories is None:
            self.preset_directories = [
                '~/.syxg/presets',
                './presets'
            ]


@dataclass
class InterfaceConfig:
    """User interface configuration"""
    theme: str = 'dark'
    language: str = 'en'
    show_tooltips: bool = True
    auto_save_settings: bool = True
    keyboard_shortcuts: Dict[str, str] = None

    def __post_init__(self):
        if self.keyboard_shortcuts is None:
            self.keyboard_shortcuts = {
                'play': 'space',
                'stop': 'escape',
                'record': 'r',
                'save': 'ctrl+s'
            }


class SynthConfig:
    """
    Synthesizer Configuration Manager

    Central configuration management system for all synthesizer settings,
    providing validation, persistence, and runtime configuration updates.
    """

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_file = config_file or self._get_default_config_path()

        # Configuration sections
        self.audio = AudioConfig()
        self.engine = EngineConfig()
        self.memory = MemoryConfig()
        self.performance = PerformanceConfig()
        self.hardware = HardwareConfig()
        self.midi = MIDIConfig()
        self.paths = PathConfig()
        self.interface = InterfaceConfig()

        # Configuration metadata
        self.version = "2.0.0"
        self.last_modified = None
        self.created = None

        # Load configuration if exists
        self.load()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        config_dir = Path.home() / '.syxg'
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'config.json')

    def load(self, config_file: Optional[str] = None) -> bool:
        """
        Load configuration from file.

        Args:
            config_file: Path to config file (uses default if None)

        Returns:
            True if loaded successfully
        """
        config_path = config_file or self.config_file

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)

                # Load configuration sections
                self._load_audio_config(data.get('audio', {}))
                self._load_engine_config(data.get('engine', {}))
                self._load_memory_config(data.get('memory', {}))
                self._load_performance_config(data.get('performance', {}))
                self._load_hardware_config(data.get('hardware', {}))
                self._load_midi_config(data.get('midi', {}))
                self._load_path_config(data.get('paths', {}))
                self._load_interface_config(data.get('interface', {}))

                # Load metadata
                self.version = data.get('version', self.version)
                self.last_modified = data.get('last_modified')
                self.created = data.get('created')

                return True
            else:
                # Create default configuration
                self.save()
                return True

        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False

    def save(self, config_file: Optional[str] = None) -> bool:
        """
        Save configuration to file.

        Args:
            config_file: Path to config file (uses default if None)

        Returns:
            True if saved successfully
        """
        config_path = config_file or self.config_file

        try:
            # Prepare configuration data
            config_data = {
                'version': self.version,
                'audio': asdict(self.audio),
                'engine': asdict(self.engine),
                'memory': asdict(self.memory),
                'performance': asdict(self.performance),
                'hardware': asdict(self.hardware),
                'midi': asdict(self.midi),
                'paths': asdict(self.paths),
                'interface': asdict(self.interface),
                'last_modified': self._get_timestamp(),
                'created': self.created or self._get_timestamp()
            }

            # Expand user paths
            config_data = self._expand_paths(config_data)

            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # Save configuration
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.last_modified = config_data['last_modified']
            return True

        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def _load_audio_config(self, data: Dict[str, Any]):
        """Load audio configuration"""
        for key, value in data.items():
            if hasattr(self.audio, key):
                setattr(self.audio, key, value)

    def _load_engine_config(self, data: Dict[str, Any]):
        """Load engine configuration"""
        for key, value in data.items():
            if hasattr(self.engine, key):
                setattr(self.engine, key, value)

    def _load_memory_config(self, data: Dict[str, Any]):
        """Load memory configuration"""
        for key, value in data.items():
            if hasattr(self.memory, key):
                setattr(self.memory, key, value)

    def _load_performance_config(self, data: Dict[str, Any]):
        """Load performance configuration"""
        for key, value in data.items():
            if hasattr(self.performance, key):
                setattr(self.performance, key, value)

    def _load_hardware_config(self, data: Dict[str, Any]):
        """Load hardware configuration"""
        for key, value in data.items():
            if hasattr(self.hardware, key):
                setattr(self.hardware, key, value)

    def _load_midi_config(self, data: Dict[str, Any]):
        """Load MIDI configuration"""
        for key, value in data.items():
            if hasattr(self.midi, key):
                setattr(self.midi, key, value)

    def _load_path_config(self, data: Dict[str, Any]):
        """Load path configuration"""
        for key, value in data.items():
            if hasattr(self.paths, key):
                setattr(self.paths, key, value)

    def _load_interface_config(self, data: Dict[str, Any]):
        """Load interface configuration"""
        for key, value in data.items():
            if hasattr(self.interface, key):
                setattr(self.interface, key, value)

    def _expand_paths(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Expand user paths in configuration"""
        expanded = config_data.copy()

        # Expand paths in path configuration
        if 'paths' in expanded:
            paths = expanded['paths']
            for key in ['sample_directories', 'preset_directories',
                       'user_data_directory', 'log_directory']:
                if key in paths and isinstance(paths[key], str):
                    paths[key] = os.path.expanduser(paths[key])
                elif key in paths and isinstance(paths[key], list):
                    paths[key] = [os.path.expanduser(p) for p in paths[key]]

        return expanded

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_expanded_paths(self) -> PathConfig:
        """Get path configuration with expanded user paths"""
        expanded = PathConfig()
        expanded.sample_directories = [os.path.expanduser(p) for p in self.paths.sample_directories]
        expanded.preset_directories = [os.path.expanduser(p) for p in self.paths.preset_directories]
        expanded.user_data_directory = os.path.expanduser(self.paths.user_data_directory)
        expanded.temp_directory = self.paths.temp_directory
        expanded.log_directory = os.path.expanduser(self.paths.log_directory)
        return expanded

    def validate_configuration(self) -> List[str]:
        """
        Validate current configuration.

        Returns:
            List of validation error messages
        """
        errors = []

        # Audio validation
        if self.audio.sample_rate not in [22050, 44100, 48000, 96000]:
            errors.append(f"Invalid sample rate: {self.audio.sample_rate}")
        if self.audio.buffer_size < 64 or self.audio.buffer_size > 8192:
            errors.append(f"Invalid buffer size: {self.audio.buffer_size}")
        if self.audio.channels not in [1, 2]:
            errors.append(f"Invalid channel count: {self.audio.channels}")

        # Memory validation
        if self.memory.sample_cache_mb < 64:
            errors.append("Sample cache too small (minimum 64MB)")
        if self.memory.max_loaded_samples < 10:
            errors.append("Max loaded samples too low")

        # Performance validation
        if self.performance.polyphony_limit < 1 or self.performance.polyphony_limit > 256:
            errors.append(f"Invalid polyphony limit: {self.performance.polyphony_limit}")
        if self.performance.voice_stealing_strategy not in ['priority', 'oldest', 'quietest']:
            errors.append(f"Invalid voice stealing strategy: {self.performance.voice_stealing_strategy}")

        # Hardware validation
        if self.hardware.model not in ['S70', 'S90', 'S90ES']:
            errors.append(f"Invalid hardware model: {self.hardware.model}")

        return errors

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.audio = AudioConfig()
        self.engine = EngineConfig()
        self.memory = MemoryConfig()
        self.performance = PerformanceConfig()
        self.hardware = HardwareConfig()
        self.midi = MIDIConfig()
        self.paths = PathConfig()
        self.interface = InterfaceConfig()

    def get_performance_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get performance preset configuration.

        Args:
            preset_name: Name of performance preset

        Returns:
            Preset configuration or None
        """
        presets = {
            'maximum_performance': {
                'polyphony_limit': 32,
                'cpu_optimization_level': 'maximum',
                'memory_optimization': True,
                'background_processing': False,
                'sample_cache_mb': 256
            },
            'balanced': {
                'polyphony_limit': 48,
                'cpu_optimization_level': 'balanced',
                'memory_optimization': True,
                'background_processing': True,
                'sample_cache_mb': 384
            },
            'maximum_quality': {
                'polyphony_limit': 64,
                'cpu_optimization_level': 'quality',
                'memory_optimization': False,
                'background_processing': True,
                'sample_cache_mb': 512
            }
        }

        return presets.get(preset_name)

    def apply_performance_preset(self, preset_name: str) -> bool:
        """
        Apply performance preset.

        Args:
            preset_name: Name of performance preset

        Returns:
            True if applied successfully
        """
        preset = self.get_performance_preset(preset_name)
        if preset:
            for key, value in preset.items():
                if hasattr(self.performance, key):
                    setattr(self.performance, key, value)
                elif hasattr(self.memory, key):
                    setattr(self.memory, key, value)
            return True
        return False

    def get_hardware_profile(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get hardware profile configuration.

        Args:
            model: Hardware model ('S70', 'S90', 'S90ES')

        Returns:
            Hardware profile configuration
        """
        profiles = {
            'S70': {
                'polyphony_limit': 64,
                'an_engines': False,
                'wave_rom_mb': 32,
                'sample_cache_mb': 256
            },
            'S90': {
                'polyphony_limit': 64,
                'an_engines': True,
                'wave_rom_mb': 64,
                'sample_cache_mb': 384
            },
            'S90ES': {
                'polyphony_limit': 128,
                'an_engines': True,
                'wave_rom_mb': 64,
                'sample_cache_mb': 512
            }
        }

        return profiles.get(model)

    def apply_hardware_profile(self, model: str) -> bool:
        """
        Apply hardware profile.

        Args:
            model: Hardware model

        Returns:
            True if applied successfully
        """
        profile = self.get_hardware_profile(model)
        if profile:
            self.hardware.model = model
            for key, value in profile.items():
                if hasattr(self.performance, key):
                    setattr(self.performance, key, value)
                elif hasattr(self.memory, key):
                    setattr(self.memory, key, value)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'version': self.version,
            'audio': asdict(self.audio),
            'engine': asdict(self.engine),
            'memory': asdict(self.memory),
            'performance': asdict(self.performance),
            'hardware': asdict(self.hardware),
            'midi': asdict(self.midi),
            'paths': asdict(self.paths),
            'interface': asdict(self.interface),
            'last_modified': self.last_modified,
            'created': self.created
        }

    def from_dict(self, data: Dict[str, Any]):
        """Load configuration from dictionary"""
        self.version = data.get('version', self.version)
        self._load_audio_config(data.get('audio', {}))
        self._load_engine_config(data.get('engine', {}))
        self._load_memory_config(data.get('memory', {}))
        self._load_performance_config(data.get('performance', {}))
        self._load_hardware_config(data.get('hardware', {}))
        self._load_midi_config(data.get('midi', {}))
        self._load_path_config(data.get('paths', {}))
        self._load_interface_config(data.get('interface', {}))
        self.last_modified = data.get('last_modified')
        self.created = data.get('created')

    def __str__(self) -> str:
        """String representation"""
        return f"SynthConfig(version={self.version}, model={self.hardware.model}, polyphony={self.performance.polyphony_limit})"


# Global configuration instance
_global_config: Optional[SynthConfig] = None


def get_global_config() -> SynthConfig:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = SynthConfig()
    return _global_config


def audio_config() -> AudioConfig:
    """Get audio configuration (for backward compatibility)"""
    return get_global_config().audio


def max_buffer_size() -> int:
    """Get maximum buffer size for buffer pool initialization"""
    config = get_global_config()
    # Use a reasonable multiple of the configured buffer size for maximum
    return config.audio.buffer_size * 8  # Allow up to 8x the configured buffer size
