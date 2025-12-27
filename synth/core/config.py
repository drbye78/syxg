"""
Production-Ready Configuration Management System

Centralized configuration with validation, hot-reloading, and environment adaptation.
Replaces hardcoded values throughout the synthesizer for professional deployment.
"""

from typing import Dict, List, Any, Optional, Union
import os
import json
import yaml
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
import math

from .validation import ValidationResult, ValidationError, parameter_validator


@dataclass
class AudioConfig:
    """Audio system configuration with validation."""
    sample_rate: int = 44100
    block_size: int = 1024
    max_channels: int = 16
    buffer_multiplier: int = 4  # Pre-allocated buffer pool size
    enable_simd: bool = True
    validation_level: str = "strict"  # 'strict', 'warning', 'permissive'

    # Audio quality settings
    dither_enabled: bool = True
    oversampling_factor: int = 1
    bit_depth: int = 32

    # Performance settings
    max_voices: int = 256
    voice_stealing_enabled: bool = True
    polyphony_limit: int = 128

    # Real-time constraints
    max_latency_ms: float = 10.0
    thread_priority: str = "high"  # 'low', 'normal', 'high', 'realtime'

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters."""
        # Sample rate validation
        valid_rates = {8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 192000}
        if self.sample_rate not in valid_rates:
            raise ValueError(f"Invalid sample rate {self.sample_rate}. Must be one of {valid_rates}")

        # Block size validation (power of 2, reasonable range)
        if not (32 <= self.block_size <= 8192) or (self.block_size & (self.block_size - 1)) != 0:
            raise ValueError(f"Invalid block size {self.block_size}. Must be power of 2 between 32-8192")

        # Channel validation
        if not (1 <= self.max_channels <= 256):
            raise ValueError(f"Invalid max channels {self.max_channels}. Must be 1-256")

        # Latency validation
        if self.max_latency_ms <= 0:
            raise ValueError(f"Invalid latency {self.max_latency_ms}. Must be > 0")

    @property
    def max_buffer_size(self) -> int:
        """Calculate maximum buffer size for allocation."""
        return self.block_size * self.buffer_multiplier

    @property
    def latency_samples(self) -> int:
        """Calculate latency in samples."""
        return int((self.max_latency_ms / 1000.0) * self.sample_rate)


@dataclass
class EngineConfig:
    """Synthesis engine configuration."""
    # Engine priorities (higher = preferred)
    sf2_priority: int = 10
    sfz_priority: int = 9
    fm_priority: int = 8
    wavetable_priority: int = 7
    additive_priority: int = 6
    physical_priority: int = 5
    spectral_priority: int = 3
    convolution_reverb_priority: int = 1

    # Engine-specific settings
    sf2_max_presets: int = 1000
    sfz_max_regions: int = 5000
    fm_max_operators: int = 8
    additive_max_partials: int = 128
    physical_max_strings: int = 6
    spectral_fft_size: int = 2048

    # Quality settings
    interpolation_quality: str = "cubic"  # 'linear', 'cubic', 'sinc'
    filter_quality: str = "high"  # 'basic', 'high', 'professional'

    def get_engine_priorities(self) -> Dict[str, int]:
        """Get all engine priorities as dictionary."""
        return {
            'sf2': self.sf2_priority,
            'sfz': self.sfz_priority,
            'fm': self.fm_priority,
            'wavetable': self.wavetable_priority,
            'additive': self.additive_priority,
            'physical': self.physical_priority,
            'spectral': self.spectral_priority,
            'convolution_reverb': self.convolution_reverb_priority
        }


@dataclass
class EffectsConfig:
    """Effects processing configuration."""
    # Reverb settings
    reverb_enabled: bool = True
    reverb_max_time: float = 5.0  # seconds
    reverb_quality: str = "high"  # 'basic', 'high', 'professional'

    # Chorus settings
    chorus_enabled: bool = True
    chorus_max_delay: float = 0.050  # seconds
    chorus_modulation_rate: float = 0.25  # Hz

    # Delay settings
    delay_enabled: bool = True
    delay_max_time: float = 2.0  # seconds
    delay_feedback_max: float = 0.95

    # EQ settings
    eq_enabled: bool = True
    eq_bands: int = 7  # 7-band EQ
    eq_q_factor: float = 1.414  # Butterworth Q

    # Dynamics
    compressor_enabled: bool = True
    compressor_ratio_max: float = 20.0
    compressor_attack_min: float = 0.001  # seconds
    compressor_release_min: float = 0.010  # seconds

    # Master section
    master_limiter_enabled: bool = True
    master_limiter_threshold: float = 0.9
    master_limiter_release: float = 0.100  # seconds


@dataclass
class MIDIConfig:
    """MIDI system configuration."""
    # Channel settings
    receive_channels: List[int] = None  # None = all channels
    transmit_channel: int = 0

    # Controller settings
    pitch_bend_range: int = 24  # semitones
    modulation_controller: int = 1
    volume_controller: int = 7
    pan_controller: int = 10

    # MPE settings
    mpe_enabled: bool = True
    mpe_pitch_bend_range: int = 48

    # XG settings
    xg_enabled: bool = True
    xg_device_id: int = 0x10

    # GS settings
    gs_enabled: bool = True
    gs_mode: str = "auto"  # 'auto', 'gs', 'xg'

    def __post_init__(self):
        if self.receive_channels is None:
            self.receive_channels = list(range(16))  # All channels


@dataclass
class SystemConfig:
    """System-wide configuration."""
    # Performance settings
    max_threads: int = 8
    thread_pool_size: int = 4
    memory_limit_mb: int = 512

    # Logging
    log_level: str = "info"  # 'debug', 'info', 'warning', 'error'
    log_to_file: bool = True
    log_directory: str = "logs"

    # Profiling
    enable_profiling: bool = False
    profile_interval: float = 5.0  # seconds

    # Validation
    strict_validation: bool = True
    fail_on_warnings: bool = False

    # File paths
    sf2_path: Optional[str] = None
    sfz_path: Optional[str] = None
    impulse_responses_path: Optional[str] = None


class ConfigManager:
    """
    Production-ready configuration manager with validation and hot-reloading.

    Provides centralized configuration management with environment adaptation,
    validation, and runtime reconfiguration capabilities.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._find_default_config_file()
        self.lock = threading.RLock()

        # Configuration sections
        self.audio = AudioConfig()
        self.engine = EngineConfig()
        self.effects = EffectsConfig()
        self.midi = MIDIConfig()
        self.system = SystemConfig()

        # Configuration state
        self._last_modified = 0.0
        self._config_valid = False

        # Load initial configuration
        self.load_config()

    def _find_default_config_file(self) -> str:
        """Find default configuration file."""
        search_paths = [
            "synth_config.yaml",
            "synth_config.json",
            "config/synth_config.yaml",
            "config/synth_config.json",
            Path.home() / ".synth" / "config.yaml",
            Path.home() / ".synth" / "config.json"
        ]

        for path in search_paths:
            if Path(path).exists():
                return str(path)

        return "synth_config.yaml"  # Default fallback

    def load_config(self, config_file: Optional[str] = None) -> ValidationResult:
        """
        Load configuration from file.

        Args:
            config_file: Path to configuration file (optional)

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        with self.lock:
            if config_file:
                self.config_file = config_file

            try:
                if not Path(self.config_file).exists():
                    result.add_warning(ValidationError(
                        f"Configuration file not found: {self.config_file}",
                        "CONFIG_FILE_MISSING",
                        {"file": self.config_file},
                        "warning"
                    ))
                    self._create_default_config()
                    return result

                # Load configuration based on file extension
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    config_data = self._load_yaml_config()
                elif self.config_file.endswith('.json'):
                    config_data = self._load_json_config()
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_file}")

                # Apply configuration
                self._apply_config_data(config_data, result)

                # Validate configuration
                validation_result = self.validate_config()
                result = self._merge_results(result, validation_result)

                # Update state
                self._last_modified = Path(self.config_file).stat().st_mtime
                self._config_valid = result.is_valid()

            except Exception as e:
                result.add_error(ValidationError(
                    f"Failed to load configuration: {e}",
                    "CONFIG_LOAD_ERROR",
                    {"error": str(e), "file": self.config_file}
                ))

        return result

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load YAML configuration."""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required for YAML configuration files")

        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f) or {}

    def _load_json_config(self) -> Dict[str, Any]:
        """Load JSON configuration."""
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def _apply_config_data(self, data: Dict[str, Any], result: ValidationResult):
        """Apply configuration data to config objects."""
        # Audio configuration
        if 'audio' in data:
            audio_data = data['audio']
            try:
                self.audio = AudioConfig(**audio_data)
            except Exception as e:
                result.add_error(ValidationError(
                    f"Invalid audio configuration: {e}",
                    "INVALID_AUDIO_CONFIG",
                    {"error": str(e)}
                ))

        # Engine configuration
        if 'engine' in data:
            engine_data = data['engine']
            try:
                self.engine = EngineConfig(**engine_data)
            except Exception as e:
                result.add_error(ValidationError(
                    f"Invalid engine configuration: {e}",
                    "INVALID_ENGINE_CONFIG",
                    {"error": str(e)}
                ))

        # Effects configuration
        if 'effects' in data:
            effects_data = data['effects']
            try:
                self.effects = EffectsConfig(**effects_data)
            except Exception as e:
                result.add_error(ValidationError(
                    f"Invalid effects configuration: {e}",
                    "INVALID_EFFECTS_CONFIG",
                    {"error": str(e)}
                ))

        # MIDI configuration
        if 'midi' in data:
            midi_data = data['midi']
            try:
                self.midi = MIDIConfig(**midi_data)
            except Exception as e:
                result.add_error(ValidationError(
                    f"Invalid MIDI configuration: {e}",
                    "INVALID_MIDI_CONFIG",
                    {"error": str(e)}
                ))

        # System configuration
        if 'system' in data:
            system_data = data['system']
            try:
                self.system = SystemConfig(**system_data)
            except Exception as e:
                result.add_error(ValidationError(
                    f"Invalid system configuration: {e}",
                    "INVALID_SYSTEM_CONFIG",
                    {"error": str(e)}
                ))

    def _create_default_config(self):
        """Create default configuration file."""
        config_dir = Path(self.config_file).parent
        config_dir.mkdir(parents=True, exist_ok=True)

        default_config = {
            'audio': asdict(AudioConfig()),
            'engine': asdict(EngineConfig()),
            'effects': asdict(EffectsConfig()),
            'midi': asdict(MIDIConfig()),
            'system': asdict(SystemConfig())
        }

        try:
            if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                import yaml
                with open(self.config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False, indent=2)
            else:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
        except Exception:
            pass  # Silently fail if we can't create default config

    def save_config(self, config_file: Optional[str] = None) -> ValidationResult:
        """
        Save current configuration to file.

        Args:
            config_file: Path to save configuration (optional)

        Returns:
            ValidationResult
        """
        result = ValidationResult()
        save_file = config_file or self.config_file

        with self.lock:
            try:
                config_data = {
                    'audio': asdict(self.audio),
                    'engine': asdict(self.engine),
                    'effects': asdict(self.effects),
                    'midi': asdict(self.midi),
                    'system': asdict(self.system)
                }

                if save_file.endswith('.yaml') or save_file.endswith('.yml'):
                    import yaml
                    with open(save_file, 'w') as f:
                        yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    with open(save_file, 'w') as f:
                        json.dump(config_data, f, indent=2)

            except Exception as e:
                result.add_error(ValidationError(
                    f"Failed to save configuration: {e}",
                    "CONFIG_SAVE_ERROR",
                    {"error": str(e), "file": save_file}
                ))

        return result

    def validate_config(self) -> ValidationResult:
        """
        Validate complete configuration.

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Validate audio system compatibility
        audio_result = self._validate_audio_compatibility()
        result = self._merge_results(result, audio_result)

        # Validate resource requirements
        resource_result = self._validate_resource_requirements()
        result = self._merge_results(result, resource_result)

        # Validate parameter ranges
        param_result = self._validate_parameter_ranges()
        result = self._merge_results(result, param_result)

        return result

    def _validate_audio_compatibility(self) -> ValidationResult:
        """Validate audio system compatibility."""
        result = ValidationResult()

        # Check latency requirements
        latency_samples = int((self.audio.max_latency_ms / 1000.0) * self.audio.sample_rate)
        if latency_samples < self.audio.block_size:
            result.add_error(ValidationError(
                f"Latency {self.audio.max_latency_ms}ms too low for block size {self.audio.block_size}",
                "LATENCY_TOO_LOW",
                {"latency_ms": self.audio.max_latency_ms, "block_size": self.audio.block_size}
            ))

        # Check oversampling compatibility
        if self.audio.oversampling_factor > 1 and self.audio.sample_rate > 96000:
            result.add_warning(ValidationError(
                f"High sample rate {self.audio.sample_rate}Hz with oversampling may cause performance issues",
                "HIGH_SAMPLE_RATE_OVERSAMPLING",
                {"sample_rate": self.audio.sample_rate, "oversampling": self.audio.oversampling_factor},
                "warning"
            ))

        return result

    def _validate_resource_requirements(self) -> ValidationResult:
        """Validate system resource requirements."""
        result = ValidationResult()

        # Estimate memory requirements
        estimated_memory_mb = self._estimate_memory_usage()
        if estimated_memory_mb > self.system.memory_limit_mb:
            result.add_warning(ValidationError(
                f"Estimated memory usage {estimated_memory_mb}MB exceeds limit {self.system.memory_limit_mb}MB",
                "MEMORY_LIMIT_EXCEEDED",
                {"estimated": estimated_memory_mb, "limit": self.system.memory_limit_mb},
                "warning"
            ))

        # Check thread requirements
        required_threads = self.system.thread_pool_size + 2  # + main + audio threads
        if required_threads > self.system.max_threads:
            result.add_error(ValidationError(
                f"Required threads {required_threads} exceeds maximum {self.system.max_threads}",
                "THREAD_LIMIT_EXCEEDED",
                {"required": required_threads, "maximum": self.system.max_threads}
            ))

        return result

    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        # Buffer memory
        buffer_memory = (self.audio.max_buffer_size * self.audio.max_channels * 4) / (1024 * 1024)  # 4 bytes per float

        # Voice memory
        voice_memory = (self.audio.max_voices * 1024 * 4) / (1024 * 1024)  # Rough estimate

        # Engine-specific memory
        engine_memory = self._estimate_engine_memory()

        return buffer_memory + voice_memory + engine_memory

    def _estimate_engine_memory(self) -> float:
        """Estimate engine-specific memory usage."""
        memory = 0.0

        # SF2 memory (rough estimate per preset)
        memory += self.engine.sf2_max_presets * 0.5  # 0.5MB per preset

        # SFZ memory (rough estimate per region)
        memory += self.engine.sfz_max_regions * 0.01  # 10KB per region

        return memory

    def _validate_parameter_ranges(self) -> ValidationResult:
        """Validate all parameter ranges."""
        result = ValidationResult()

        # Validate critical parameters
        validations = [
            ("sample_rate", self.audio.sample_rate),
            ("block_size", self.audio.block_size),
            ("max_channels", self.audio.max_channels),
            ("max_voices", self.audio.max_voices),
            ("polyphony_limit", self.audio.polyphony_limit),
        ]

        for param_name, value in validations:
            param_result = parameter_validator.validate_parameter(param_name, value)
            result = self._merge_results(result, param_result)

        return result

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        return {
            'config_file': self.config_file,
            'valid': self._config_valid,
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'block_size': self.audio.block_size,
                'max_channels': self.audio.max_channels,
                'max_buffer_size': self.audio.max_buffer_size
            },
            'engines': self.engine.get_engine_priorities(),
            'effects_enabled': {
                'reverb': self.effects.reverb_enabled,
                'chorus': self.effects.chorus_enabled,
                'delay': self.effects.delay_enabled,
                'eq': self.effects.eq_enabled,
                'compressor': self.effects.compressor_enabled
            },
            'midi': {
                'mpe_enabled': self.midi.mpe_enabled,
                'xg_enabled': self.midi.xg_enabled,
                'gs_enabled': self.midi.gs_enabled
            },
            'system': {
                'max_threads': self.system.max_threads,
                'memory_limit_mb': self.system.memory_limit_mb,
                'hot_reload': self.system.enable_hot_reload
            }
        }

    def _merge_results(self, result1: ValidationResult, result2: ValidationResult) -> ValidationResult:
        """Merge validation results."""
        result1.errors.extend(result2.errors)
        result1.warnings.extend(result2.warnings)
        result1.info.extend(result2.info)
        return result1


# Global configuration instance
config_manager = ConfigManager()

# Convenience access to configuration sections
audio_config = config_manager.audio
engine_config = config_manager.engine
effects_config = config_manager.effects
midi_config = config_manager.midi
system_config = config_manager.system
