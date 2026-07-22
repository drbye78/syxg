"""
Vibexg Configuration — Typed configuration dataclass

Replaces bare dict[str, Any] config with a validated WorkstationConfig
dataclass. Provides factory methods for building from CLI args or YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_SAMPLE_RATE,
    AudioOutputConfig,
    AudioOutputType,
    MIDIInputConfig,
)


@dataclass
class WorkstationConfig:
    """Validated workstation configuration."""

    sample_rate: int = DEFAULT_SAMPLE_RATE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    midi_inputs: list[MIDIInputConfig] = field(default_factory=list)
    audio_output: AudioOutputConfig | None = None
    preset_dir: str = "presets"
    config_file: str = "config.yaml"
    no_tui: bool = False
    style_paths: list[str] = field(default_factory=list)

    # SoundFont
    soundfont: str = "tests/ref.sf2"

    # Synthesizer feature flags
    xg_enabled: bool = True
    gs_enabled: bool = True
    mpe_enabled: bool = False
    midi_2_enabled: bool = False
    acoustic_behavior: bool = False
    s90_mode: bool = False
    gs_mode: str | None = None  # "auto", "xg", "gs", or None for library default

    # Effects pipeline toggles (None = use library default)
    effects_enabled: bool | None = None
    sart2_enabled: bool | None = None
    reverb_enabled: bool | None = None
    chorus_enabled: bool | None = None
    variation_enabled: bool | None = None
    insertion_enabled: bool | None = None
    master_eq_enabled: bool | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.sample_rate not in (22050, 44100, 48000, 88200, 96000, 192000):
            raise ValueError(
                f"Unsupported sample rate: {self.sample_rate}. "
                f"Supported: 22050, 44100, 48000, 88200, 96000, 192000"
            )
        if self.buffer_size <= 0 or self.buffer_size & (self.buffer_size - 1) != 0:
            raise ValueError(f"Buffer size must be a positive power of two, got {self.buffer_size}")

    @classmethod
    def from_cli_args(cls, args: Any) -> WorkstationConfig:
        """Build from parsed CLI arguments namespace.

        Args:
            args: argparse.Namespace or compatible object

        Returns:
            WorkstationConfig instance
        """
        # Build audio output config
        audio_output = _build_audio_output_config(
            args.audio_output, args.sample_rate, args.buffer_size
        )

        # Build MIDI input configs
        midi_inputs: list[MIDIInputConfig] = []
        for spec in args.midi_inputs or []:
            from .cli import parse_input_spec  # avoid circular import

            parsed = parse_input_spec(spec)
            midi_inputs.append(_dict_to_midi_input_config(parsed))

        # Feature flags: CLI uses store_true/store_false (None = not provided on CLI).
        # When None, fall back to the dataclass field default so YAML-only or
        # CLI-only runs get sensible values without double-encoding defaults.
        def _clf(name: str, default: Any = None) -> Any:
            val = getattr(args, name, None)
            return default if val is None else val

        return cls(
            sample_rate=args.sample_rate,
            buffer_size=args.buffer_size,
            config_file=args.config,
            midi_inputs=midi_inputs,
            audio_output=audio_output,
            no_tui=args.no_tui,
            soundfont=_clf("soundfont", "tests/ref.sf2"),
            xg_enabled=_clf("xg", True),
            gs_enabled=_clf("gs", True),
            mpe_enabled=_clf("mpe", False),
            midi_2_enabled=_clf("midi2", False),
            acoustic_behavior=_clf("acoustic", False),
            s90_mode=_clf("s90", False),
            gs_mode=_clf("gs_mode", None),
            effects_enabled=_clf("effects", None),
            sart2_enabled=_clf("sart2", None),
            reverb_enabled=_clf("reverb", None),
            chorus_enabled=_clf("chorus", None),
            variation_enabled=_clf("variation", None),
            insertion_enabled=_clf("insertion", None),
            master_eq_enabled=_clf("master_eq", None),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationConfig:
        """Build from a dictionary (e.g., loaded from YAML config).

        Args:
            data: Configuration dictionary with known keys

        Returns:
            WorkstationConfig instance
        """
        midi_inputs: list[MIDIInputConfig] = []
        for inp in data.get("midi_inputs", []):
            midi_inputs.append(_dict_to_midi_input_config(inp))

        audio_data = data.get("audio_output")
        audio_output = (
            _build_audio_output_config(
                (
                    audio_data.get("type", "sounddevice")
                    if isinstance(audio_data, dict)
                    else "sounddevice"
                ),
                data.get("sample_rate", DEFAULT_SAMPLE_RATE),
                data.get("buffer_size", DEFAULT_BUFFER_SIZE),
                audio_data,
            )
            if audio_data
            else None
        )

        synth_data = data.get("synthesizer", {})
        fx_data = data.get("effects", {})

        return cls(
            sample_rate=data.get("sample_rate", DEFAULT_SAMPLE_RATE),
            buffer_size=data.get("buffer_size", DEFAULT_BUFFER_SIZE),
            config_file=data.get("config_file", "config.yaml"),
            midi_inputs=midi_inputs,
            audio_output=audio_output,
            preset_dir=data.get("preset_dir", "presets"),
            style_paths=data.get("style_paths", []),
            no_tui=data.get("no_tui", False),
            soundfont=synth_data.get("soundfont", "tests/ref.sf2"),
            xg_enabled=synth_data.get("xg_enabled", True),
            gs_enabled=synth_data.get("gs_enabled", True),
            mpe_enabled=synth_data.get("mpe_enabled", False),
            midi_2_enabled=synth_data.get("midi_2_enabled", False),
            acoustic_behavior=synth_data.get("acoustic_behavior", False),
            s90_mode=synth_data.get("s90_mode", False),
            gs_mode=synth_data.get("gs_mode", None),
            effects_enabled=fx_data.get("enabled", None),
            sart2_enabled=synth_data.get("sart2_enabled", None),
            reverb_enabled=fx_data.get("reverb_enabled", None),
            chorus_enabled=fx_data.get("chorus_enabled", None),
            variation_enabled=fx_data.get("variation_enabled", None),
            insertion_enabled=fx_data.get("insertion_enabled", None),
            master_eq_enabled=fx_data.get("master_eq_enabled", None),
        )


def _dict_to_midi_input_config(data: dict[str, Any]) -> MIDIInputConfig:
    """Convert a parsed input spec dict to MIDIInputConfig."""
    from .types import InputInterfaceType

    spec_type = data.get("type", "")
    options = data.get("options", {})

    return MIDIInputConfig(
        interface_type=InputInterfaceType(spec_type) if spec_type else InputInterfaceType.KEYBOARD,
        name=options.get("name", options.get("port_name", spec_type)),
        port_name=options.get("port_name", ""),
        channel_filter=options.get("channel_filter"),
        velocity_offset=options.get("velocity_offset", 0),
        transpose=options.get("transpose", 0),
        options=options,
    )


def _build_audio_output_config(
    spec: str | dict[str, Any],
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
    audio_data: dict[str, Any] | None = None,
) -> AudioOutputConfig | None:
    """Build AudioOutputConfig from CLI spec or dict data.

    Args:
        spec: CLI spec string (e.g. "sounddevice", "file:out.wav") or dict
        sample_rate: Audio sample rate
        buffer_size: Audio buffer size
        audio_data: Optional dict with additional config fields

    Returns:
        AudioOutputConfig or None for "none" type
    """
    from .cli import parse_output_spec  # avoid circular import

    if isinstance(spec, str):
        parsed = parse_output_spec(spec)
    elif isinstance(spec, dict):
        parsed = spec
    else:
        parsed = {"type": "sounddevice"}

    output_type_str = parsed.get("type", "sounddevice")
    if output_type_str == "none":
        return None

    output_type = AudioOutputType(output_type_str)

    if audio_data:
        return AudioOutputConfig(
            output_type=output_type,
            device_name=audio_data.get("device_name", parsed.get("device_name", "")),
            file_path=audio_data.get("file_path", parsed.get("file_path", "")),
            file_format=audio_data.get("file_format", parsed.get("file_format", "wav")),
            sample_rate=audio_data.get("sample_rate", sample_rate),
            buffer_size=audio_data.get("buffer_size", buffer_size),
        )

    return AudioOutputConfig(
        output_type=output_type,
        device_name=parsed.get("device_name", ""),
        file_path=parsed.get("file_path", ""),
        file_format=parsed.get("file_format", "wav"),
        sample_rate=sample_rate,
        buffer_size=buffer_size,
    )


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration file if it exists.

    Args:
        path: Path to config file

    Returns:
        Dictionary with config values, or empty dict if file not found
    """
    path = Path(path)
    if not path.exists():
        return {}

    try:
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except ImportError:
        import logging

        logging.getLogger(__name__).warning("PyYAML not available, skipping config file")
        return {}
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to load config file {path}: {e}")
        return {}
