"""
XGML v3.0 Parser

Advanced parser for XGML v3.0 with complete feature support including:
- Hierarchical configuration processing
- Template system
- Schema validation
- Intelligent defaults expansion
- Backward compatibility
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class XGMLParseError(Exception):
    """XGML parsing error."""

    pass


class XGMLValidationError(Exception):
    """XGML validation error."""

    pass


class TemplateNotFoundError(XGMLParseError):
    """Template not found error."""

    pass


class ConfigurationSection(Enum):
    """XGML v3.0 configuration sections."""

    SYNTHESIZER_CORE = "synthesizer_core"
    WORKSTATION_FEATURES = "workstation_features"
    SYNTHESIS_ENGINES = "synthesis_engines"
    EFFECTS_PROCESSING = "effects_processing"
    MODULATION_SYSTEM = "modulation_system"
    PERFORMANCE_CONTROLS = "performance_controls"
    SEQUENCING = "sequencing"


@dataclass(slots=True)
class XGMLConfigV3:
    """XGML v3.0 configuration container."""

    # Metadata
    version: str = "3.0"
    description: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Configuration sections
    synthesizer_core: dict[str, Any] = field(default_factory=dict)
    workstation_features: dict[str, Any] = field(default_factory=dict)
    synthesis_engines: dict[str, Any] = field(default_factory=dict)
    effects_processing: dict[str, Any] = field(default_factory=dict)
    modulation_system: dict[str, Any] = field(default_factory=dict)
    performance_controls: dict[str, Any] = field(default_factory=dict)
    sequencing: dict[str, Any] = field(default_factory=dict)

    # Template information
    template: str | None = None
    template_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "xg_dsl_version": self.version,
        }

        if self.description:
            result["description"] = self.description
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.metadata:
            result["metadata"] = self.metadata
        if self.template:
            result["template"] = self.template

        # Add non-empty sections
        for section in ConfigurationSection:
            section_data = getattr(self, section.value)
            if section_data:
                result[section.value] = section_data

        return result


class TemplateManager:
    """Manages XGML v3.0 configuration templates."""

    def __init__(self):
        self.templates = self._load_builtin_templates()

    def _load_builtin_templates(self) -> dict[str, dict[str, Any]]:
        """Load built-in configuration templates."""
        return {
            "childrens_piano": {
                "description": "Simple piano for children's lessons",
                "synthesizer_core": {
                    "performance": {"max_polyphony": 8},
                    "audio": {"sample_rate": 44100, "buffer_size": 512},
                },
                "effects_processing": {
                    "system_effects": {
                        "reverb": {"algorithm": "hall_1", "parameters": {"level": 0.3}}
                    }
                },
            },
            "basic_piano": {
                "description": "Standard acoustic piano",
                "synthesis_engines": {
                    "registry": {"default_engine": "sf2"},
                    "channel_engines": {"channel_0": "sf2"},
                    "sf2_engine": {"enabled": True, "program": 0, "velocity_curve": "concave"},
                },
            },
            "jazz_combo": {
                "description": "Classic jazz combo setup",
                "synthesis_engines": {
                    "channel_engines": {
                        "channel_0": "sf2",  # Piano
                        "channel_1": "sf2",  # Bass
                        "channel_9": "sfz",  # Drums
                    }
                },
                "effects_processing": {
                    "system_effects": {
                        "reverb": {"algorithm": "club", "parameters": {"level": 0.4}}
                    }
                },
            },
            "classical_orchestra": {
                "description": "Professional orchestral setup",
                "workstation_features": {"multi_timbral": {"channels": 16}},
                "synthesis_engines": {
                    "channel_engines": {
                        "channel_0": "physical",  # Violins
                        "channel_1": "physical",  # Violas
                        "channel_2": "physical",  # Cellos
                        "channel_3": "physical",  # Bass
                        "channel_4": "sf2",  # Woodwinds
                        "channel_5": "sf2",  # Brass
                        "channel_6": "sf2",  # Percussion
                    }
                },
                "effects_processing": {
                    "system_effects": {
                        "reverb": {"algorithm": "cathedral", "parameters": {"level": 0.6}}
                    }
                },
            },
            "electronic_workstation": {
                "description": "Complete electronic music production setup",
                "synthesis_engines": {
                    "channel_engines": {
                        "channel_0": "fm",  # Lead
                        "channel_1": "spectral",  # Pads
                        "channel_2": "fm",  # Bass
                        "channel_9": "sfz",  # Drums
                    }
                },
                "effects_processing": {
                    "variation_effects": [
                        {"type": 12, "parameters": {"rate": 0.3, "depth": 0.7}},
                        {"type": 48, "parameters": {"drive": 0.4, "tone": 0.7}},
                    ]
                },
                "modulation_system": {
                    "matrix": {
                        "routes": [
                            {
                                "source": "lfo1",
                                "destination": "pitch",
                                "amount": 0.1,
                                "bipolar": True,
                            }
                        ]
                    }
                },
            },
        }

    def get_template(self, name: str) -> dict[str, Any]:
        """Get template configuration."""
        if name not in self.templates:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return self.templates[name].copy()

    def apply_template(
        self,
        base_config: dict[str, Any],
        template_name: str,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply template to base configuration with optional overrides."""
        template = self.get_template(template_name)

        # Deep merge template into base config
        result = self._deep_merge(base_config, template)

        # Apply overrides if provided
        if overrides:
            result = self._deep_merge(result, overrides)

        return result

    def _deep_merge(self, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


class DefaultsExpander:
    """Expands XGML v3.0 configurations with intelligent defaults."""

    def __init__(self):
        self.defaults = self._load_defaults()

    def _load_defaults(self) -> dict[str, Any]:
        """Load comprehensive default values."""
        return {
            "xg_dsl_version": "3.0",
            "synthesizer_core": {
                "audio": {"sample_rate": 44100, "buffer_size": 512, "real_time": True},
                "performance": {
                    "max_polyphony": 128,
                    "voice_stealing": "priority",
                    "dynamic_polyphony": True,
                },
                "memory": {
                    "buffer_pool_size": 128,
                    "envelope_pool_size": 512,
                    "filter_pool_size": 256,
                    "lfo_pool_size": 128,
                },
                "monitoring": {
                    "enabled": False,
                    "metrics": ["cpu", "latency", "polyphony", "memory"],
                    "thresholds": {
                        "max_cpu_percent": 80.0,
                        "max_latency_ms": 5.0,
                        "max_memory_mb": 512.0,
                    },
                },
            },
            "synthesis_engines": {
                "registry": {
                    "default_engine": "sf2",
                    "fallback_engine": "sf2",
                    "engine_priorities": {
                        "sf2": 100,
                        "sfz": 90,
                        "physical": 80,
                        "fm": 70,
                        "spectral": 60,
                    },
                },
                "sf2_engine": {"enabled": True, "velocity_curve": "concave"},
            },
            "effects_processing": {
                "coordinator": {
                    "enabled": True,
                    "routing_matrix": False,
                    "sidechain_enabled": False,
                    "wet_dry_matrix": False,
                }
            },
            "modulation_system": {
                "matrix": {
                    "enabled": True,
                    "max_routes": 128,
                    "bipolar_support": True,
                    "curve_interpolation": "smooth",
                }
            },
            "workstation_features": {},
            "performance_controls": {},
            "sequencing": {
                "sequencer_core": {
                    "enabled": True,
                    "resolution": 960,
                    "tempo": 128.0,
                    "time_signature": "4/4",
                    "swing": 0.0,
                    "quantization": "1/16",
                }
            },
        }

    def expand(self, config: dict[str, Any]) -> dict[str, Any]:
        """Expand configuration with defaults."""
        return self._deep_merge(self.defaults, config)

    def get_full_defaults(self) -> dict[str, Any]:
        """Get complete default configuration."""
        return self.defaults.copy()

    def _deep_merge(self, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


class SchemaValidator:
    """XGML v3.0 JSON Schema validator."""

    def __init__(self):
        self.schema = self._load_schema()

    def _load_schema(self) -> dict[str, Any]:
        """Load XGML v3.0 JSON schema."""
        schema_path = Path(__file__).parent.parent / "docs" / "xgml_v3_schema.json"
        try:
            with open(schema_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback to embedded minimal schema
            return {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "xg_dsl_version": {"type": "string", "enum": ["3.0"]},
                    "description": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                },
                "required": ["xg_dsl_version"],
            }

    def validate(self, config: dict[str, Any]) -> list[str]:
        """Validate configuration against schema."""
        try:
            jsonschema.validate(config, self.schema)
            return []
        except jsonschema.ValidationError as e:
            return [f"Schema validation error: {e.message}"]
        except Exception as e:
            return [f"Validation error: {e!s}"]


class XGMLParserV3:
    """
    XGML v3.0 Parser with complete feature support.

    Features:
    - Hierarchical configuration processing
    - Template system
    - Schema validation
    - Intelligent defaults expansion
    - Backward compatibility
    """

    def __init__(self):
        self.template_manager = TemplateManager()
        self.defaults_expander = DefaultsExpander()
        self.schema_validator = SchemaValidator()
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def parse_file(self, file_path: str | Path) -> XGMLConfigV3 | None:
        """Parse XGML v3.0 file."""
        try:
            path = Path(file_path)
            if not path.exists():
                self.errors.append(f"File not found: {file_path}")
                return None

            with open(path, encoding="utf-8") as f:
                content = f.read()

            return self.parse_string(content)

        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return None

    def parse_string(self, yaml_string: str) -> XGMLConfigV3 | None:
        """Parse XGML v3.0 from string."""
        try:
            data = yaml.safe_load(yaml_string)
            return self.parse_data(data)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return None

    def parse_data(self, data: dict[str, Any]) -> XGMLConfigV3 | None:
        """Parse XGML v3.0 from dictionary data."""
        self.errors = []
        self.warnings = []

        if not isinstance(data, dict):
            self.errors.append("XGML document must be a dictionary")
            return None

        # Validate version
        version = data.get("xg_dsl_version", "3.0")
        if version != "3.0":
            self.warnings.append(f"XGML version {version} - parsing as v3.0")

        # Apply template if specified
        if "template" in data:
            template_name = data["template"]
            template_overrides = data.get("template_overrides", {})
            try:
                data = self.template_manager.apply_template(data, template_name, template_overrides)
                data["template"] = template_name
            except TemplateNotFoundError as e:
                self.errors.append(str(e))
                return None

        # Expand with defaults
        expanded_data = self.defaults_expander.expand(data)

        # Validate against schema
        validation_errors = self.schema_validator.validate(expanded_data)
        if validation_errors:
            self.errors.extend(validation_errors)
            return None

        # Create configuration object
        try:
            config = XGMLConfigV3(
                version=expanded_data.get("xg_dsl_version", "3.0"),
                description=expanded_data.get("description"),
                timestamp=expanded_data.get("timestamp"),
                metadata=expanded_data.get("metadata", {}),
                template=expanded_data.get("template"),
                template_overrides=expanded_data.get("template_overrides", {}),
                synthesizer_core=expanded_data.get("synthesizer_core", {}),
                workstation_features=expanded_data.get("workstation_features", {}),
                synthesis_engines=expanded_data.get("synthesis_engines", {}),
                effects_processing=expanded_data.get("effects_processing", {}),
                modulation_system=expanded_data.get("modulation_system", {}),
                performance_controls=expanded_data.get("performance_controls", {}),
                sequencing=expanded_data.get("sequencing", {}),
            )

            return config

        except Exception as e:
            self.errors.append(f"Error creating configuration: {e}")
            return None

    def get_expanded_config(self) -> XGMLConfigV3 | None:
        """Get fully expanded default configuration."""
        defaults = self.defaults_expander.get_full_defaults()
        return self.parse_data(defaults)

    def get_errors(self) -> list[str]:
        """Get parsing errors."""
        return self.errors.copy()

    def get_warnings(self) -> list[str]:
        """Get parsing warnings."""
        return self.warnings.copy()

    def has_errors(self) -> bool:
        """Check if there are errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0
