"""
XGML Parser

Parses XGML (XG Markup Language) YAML documents and provides structured access
to XG synthesizer parameters and sequences.
"""

import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

from .constants import XGML_VERSION, XGML_SECTIONS


class XGMLDocument:
    """Represents a parsed XGML document."""

    def __init__(self, data: Dict[str, Any]):
        self.version = data.get('xg_dsl_version', XGML_VERSION)
        self.description = data.get('description', '')
        self.timestamp = data.get('timestamp')
        self.sections = {}

        # Parse all sections
        for section_name in XGML_SECTIONS:
            if section_name in data:
                self.sections[section_name] = data[section_name]

    def has_section(self, section_name: str) -> bool:
        """Check if document has a specific section."""
        return section_name in self.sections

    def get_section(self, section_name: str) -> Optional[Any]:
        """Get a specific section data."""
        return self.sections.get(section_name)

    def get_sections(self) -> List[str]:
        """Get list of available sections."""
        return list(self.sections.keys())


class XGMLParser:
    """
    XGML Parser - converts XGML YAML files to structured documents.

    Provides validation and structured access to XGML document components.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def parse_file(self, file_path: Union[str, Path]) -> Optional[XGMLDocument]:
        """
        Parse XGML file from path.

        Args:
            file_path: Path to XGML file

        Returns:
            XGMLDocument instance or None if parsing failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.errors.append(f"File not found: {file_path}")
                return None

            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            return self.parse_data(data)

        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return None

    def parse_string(self, yaml_string: str) -> Optional[XGMLDocument]:
        """
        Parse XGML from string.

        Args:
            yaml_string: XGML YAML content as string

        Returns:
            XGMLDocument instance or None if parsing failed
        """
        try:
            data = yaml.safe_load(yaml_string)
            return self.parse_data(data)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return None

    def parse_data(self, data: Dict[str, Any]) -> Optional[XGMLDocument]:
        """
        Parse XGML from dictionary data.

        Args:
            data: XGML data as dictionary

        Returns:
            XGMLDocument instance or None if parsing failed
        """
        self.errors = []
        self.warnings = []

        if not isinstance(data, dict):
            self.errors.append("XGML document must be a dictionary")
            return None

        # Validate version
        version = data.get('xg_dsl_version', XGML_VERSION)
        if version != XGML_VERSION:
            self.warnings.append(f"XGML version {version} may not be fully compatible with parser version {XGML_VERSION}")

        # Check for required structure
        if not any(section in data for section in XGML_SECTIONS):
            self.warnings.append("No XGML sections found in document")

        # Validate timestamp if present
        timestamp = data.get('timestamp')
        if timestamp:
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                self.warnings.append(f"Invalid timestamp format: {timestamp}")

        try:
            return XGMLDocument(data)
        except Exception as e:
            self.errors.append(f"Error creating XGML document: {e}")
            return None

    def get_errors(self) -> List[str]:
        """Get list of parsing errors."""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get list of parsing warnings."""
        return self.warnings.copy()

    def has_errors(self) -> bool:
        """Check if there are any parsing errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any parsing warnings."""
        return len(self.warnings) > 0

    def validate_section_structure(self, section_name: str, section_data: Any) -> bool:
        """
        Validate structure of a specific section.

        Args:
            section_name: Name of the section
            section_data: Section data to validate

        Returns:
            True if section structure is valid
        """
        # Basic validation - can be extended for each section type
        if section_data is None:
            return True

        if not isinstance(section_data, (dict, list)):
            self.errors.append(f"Section '{section_name}' must be a dictionary or list")
            return False

        return True
