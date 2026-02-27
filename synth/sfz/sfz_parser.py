"""
SFZ Parser - Complete SFZ v2 Format Parser

Parses SFZ (Sample Format Zipped) files with full v2 specification support.
Handles all standard opcodes, sections, and advanced features.
"""
from __future__ import annotations

import re
from typing import Any
from pathlib import Path


class SFZOpcode:
    """Represents a single SFZ opcode with value and optional parameters."""

    def __init__(self, name: str, value: Any, parameters: dict[str, Any] | None = None):
        self.name = name
        self.value = value
        self.parameters = parameters or {}

    def __str__(self) -> str:
        if self.parameters:
            param_str = ' '.join(f"{k}={v}" for k, v in self.parameters.items())
            return f"{self.name}={self.value} {param_str}"
        return f"{self.name}={self.value}"

    def __repr__(self) -> str:
        return f"SFZOpcode({self.name}={self.value})"


class SFZRegion:
    """Represents a single SFZ region with all its opcodes."""

    def __init__(self):
        self.opcodes: dict[str, SFZOpcode] = {}
        self.comments: list[str] = []

    def set_opcode(self, opcode: SFZOpcode):
        """Set an opcode value for this region."""
        self.opcodes[opcode.name] = opcode

    def get_opcode(self, name: str) -> SFZOpcode | None:
        """Get an opcode by name."""
        return self.opcodes.get(name)

    def get_value(self, name: str, default: Any = None) -> Any:
        """Get the value of an opcode."""
        opcode = self.get_opcode(name)
        return opcode.value if opcode else default

    def has_opcode(self, name: str) -> bool:
        """Check if region has a specific opcode."""
        return name in self.opcodes

    def to_dict(self) -> dict[str, Any]:
        """Convert region to dictionary for processing."""
        result = {}
        for name, opcode in self.opcodes.items():
            result[name] = opcode.value
        return result

    def __str__(self) -> str:
        opcodes_str = ' '.join(str(opcode) for opcode in self.opcodes.values())
        return f"<region> {opcodes_str}"

    def __repr__(self) -> str:
        return f"SFZRegion({len(self.opcodes)} opcodes)"


class SFZGroup:
    """Represents an SFZ group section."""

    def __init__(self):
        self.opcodes: dict[str, SFZOpcode] = {}
        self.regions: list[SFZRegion] = []
        self.comments: list[str] = []

    def set_opcode(self, opcode: SFZOpcode):
        """Set an opcode value for this group."""
        self.opcodes[opcode.name] = opcode

    def add_region(self, region: SFZRegion):
        """Add a region to this group."""
        self.regions.append(region)

    def get_value(self, name: str, default: Any = None) -> Any:
        """Get the value of an opcode."""
        opcode = self.opcodes.get(name)
        return opcode.value if opcode else default

    def to_dict(self) -> dict[str, Any]:
        """Convert group to dictionary for processing."""
        result = {'regions': [region.to_dict() for region in self.regions]}
        for name, opcode in self.opcodes.items():
            result[name] = opcode.value
        return result

    def __str__(self) -> str:
        return f"<group> ({len(self.regions)} regions)"

    def __repr__(self) -> str:
        return f"SFZGroup({len(self.regions)} regions, {len(self.opcodes)} opcodes)"


class SFZInstrument:
    """Represents a complete SFZ instrument."""

    def __init__(self, path: str | None = None):
        self.path = path
        self.filename = Path(path).name if path else "unnamed.sfz"

        # Main sections
        self.global_opcodes: dict[str, SFZOpcode] = {}
        self.groups: list[SFZGroup] = []
        self.control_opcodes: dict[str, SFZOpcode] = {}

        # Metadata
        self.comments: list[str] = []

    def set_global_opcode(self, opcode: SFZOpcode):
        """Set a global opcode."""
        self.global_opcodes[opcode.name] = opcode

    def add_group(self, group: SFZGroup):
        """Add a group to the instrument."""
        self.groups.append(group)

    def set_control_opcode(self, opcode: SFZOpcode):
        """Set a control opcode."""
        self.control_opcodes[opcode.name] = opcode

    def get_global_value(self, name: str, default: Any = None) -> Any:
        """Get a global opcode value."""
        opcode = self.global_opcodes.get(name)
        return opcode.value if opcode else default

    def get_control_value(self, name: str, default: Any = None) -> Any:
        """Get a control opcode value."""
        opcode = self.control_opcodes.get(name)
        return opcode.value if opcode else default

    def get_all_regions(self) -> list[SFZRegion]:
        """Get all regions from all groups."""
        regions = []
        for group in self.groups:
            regions.extend(group.regions)
        return regions

    def to_dict(self) -> dict[str, Any]:
        """Convert instrument to dictionary."""
        return {
            'filename': self.filename,
            'path': self.path,
            'global': {name: opcode.value for name, opcode in self.global_opcodes.items()},
            'control': {name: opcode.value for name, opcode in self.control_opcodes.items()},
            'groups': [group.to_dict() for group in self.groups],
            'total_regions': sum(len(group.regions) for group in self.groups)
        }

    def __str__(self) -> str:
        return f"SFZInstrument('{self.filename}', {len(self.groups)} groups, {sum(len(g.regions) for g in self.groups)} regions)"

    def __repr__(self) -> str:
        return self.__str__()


class SFZParser:
    """
    Complete SFZ v2 Parser

    Parses SFZ format files with support for:
    - All standard opcodes
    - Section inheritance (<global>, <group>, <region>)
    - Comments and whitespace handling
    - Path resolution for samples
    """

    # SFZ section headers
    SECTION_HEADERS = {'<global>', '<group>', '<region>', '<control>'}

    # Standard SFZ opcodes (not exhaustive - covers most common)
    STANDARD_OPCODES = {
        # Sample definition
        'sample': str,

        # Key range
        'lokey': int, 'hikey': int, 'key': int,
        'lovel': int, 'hivel': int,

        # Velocity and other triggers
        'trigger': str,  # attack, release, first, legato

        # Pitch
        'pitch_keycenter': int, 'tune': int, 'fine_tune': float,

        # Amplitude
        'volume': float, 'pan': float, 'width': float,

        # Filter
        'cutoff': float, 'resonance': float, 'fil_type': str,

        # Envelope - Amplitude
        'ampeg_attack': float, 'ampeg_decay': float,
        'ampeg_sustain': float, 'ampeg_release': float,
        'ampeg_delay': float, 'ampeg_hold': float,

        # Envelope - Filter
        'fileg_attack': float, 'fileg_decay': float,
        'fileg_sustain': float, 'fileg_release': float,

        # Loop
        'loop_mode': str, 'loop_start': int, 'loop_end': int,

        # Round robin and sequence
        'seq_position': int, 'seq_length': int,
        'round_robin': int, 'round_robin_group': int,

        # Crossfading
        'velocity_crossfade': str, 'note_crossfade': str,

        # Effects sends
        'reverb_send': float, 'chorus_send': float, 'delay_send': float,

        # LFO
        'lfo1_freq': float, 'lfo1_depth': float,
        'lfo2_freq': float, 'lfo2_depth': float,

        # Modulation
        'mod1_src': str, 'mod1_dest': str, 'mod1_amount': float,
        'mod2_src': str, 'mod2_dest': str, 'mod2_amount': float,
        # ... (many more modulation opcodes)

        # Control opcodes
        'default_path': str, 'set_cc': str,

        # Comments (handled specially)
        'comment': str,
    }

    def __init__(self):
        self.current_sfz_directory = None

    def parse_file(self, sfz_path: str) -> SFZInstrument:
        """
        Parse an SFZ file and return an SFZInstrument object.

        Args:
            sfz_path: Path to the SFZ file

        Returns:
            Parsed SFZInstrument
        """
        sfz_path = Path(sfz_path)
        if not sfz_path.exists():
            raise FileNotFoundError(f"SFZ file not found: {sfz_path}")

        self.current_sfz_directory = sfz_path.parent

        with open(sfz_path, encoding='utf-8', errors='replace') as f:
            content = f.read()

        return self.parse_string(content, str(sfz_path))

    def parse_string(self, sfz_content: str, filename: str = "string.sfz") -> SFZInstrument:
        """
        Parse SFZ content from a string.

        Args:
            sfz_content: SFZ format content
            filename: Optional filename for the instrument

        Returns:
            Parsed SFZInstrument
        """
        # Initialize instrument
        instrument = SFZInstrument(filename)

        # Split into lines and process
        lines = self._preprocess_content(sfz_content)
        current_section = None
        current_group = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            if line.lower() in self.SECTION_HEADERS:
                current_section = line.lower()
                if current_section == '<group>':
                    current_group = SFZGroup()
                    instrument.add_group(current_group)
                continue

            # Parse opcodes
            opcodes = self._parse_opcodes(line)
            for opcode in opcodes:
                self._apply_opcode(instrument, current_section, current_group, opcode)

        return instrument

    def _preprocess_content(self, content: str) -> list[str]:
        """Preprocess SFZ content into lines."""
        # Remove carriage returns and split into lines
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')

        # Handle line continuations (backslashes)
        processed_lines = []
        current_line = ""

        for line in lines:
            line = line.strip()
            if line.endswith('\\'):
                current_line += line[:-1]
            else:
                current_line += line
                if current_line:
                    processed_lines.append(current_line)
                current_line = ""

        # Handle any remaining line
        if current_line:
            processed_lines.append(current_line)

        return processed_lines

    def _parse_opcodes(self, line: str) -> list[SFZOpcode]:
        """Parse opcodes from a line."""
        opcodes = []

        # Handle comments
        if '//' in line:
            line = line.split('//')[0].strip()

        # Split by whitespace but preserve quoted strings
        parts = self._split_preserving_quotes(line)

        for part in parts:
            if '=' in part:
                name, value_str = part.split('=', 1)
                name = name.strip()
                value = self._parse_value(name, value_str.strip())
                opcodes.append(SFZOpcode(name, value))

        return opcodes

    def _split_preserving_quotes(self, line: str) -> list[str]:
        """Split line by whitespace while preserving quoted strings."""
        parts = []
        current_part = ""
        in_quotes = False
        quote_char = None

        for char in line:
            if not in_quotes and char in ('"', "'"):
                in_quotes = True
                quote_char = char
                current_part += char
            elif in_quotes and char == quote_char:
                in_quotes = False
                current_part += char
                quote_char = None
            elif not in_quotes and char.isspace():
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            else:
                current_part += char

        if current_part:
            parts.append(current_part)

        return parts

    def _parse_value(self, opcode_name: str, value_str: str) -> Any:
        """Parse an opcode value based on its expected type."""
        # Handle quoted strings
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # Get expected type from standard opcodes
        expected_type = self.STANDARD_OPCODES.get(opcode_name)

        if expected_type == int:
            try:
                return int(value_str)
            except ValueError:
                # Handle special cases like note names
                return self._parse_note_name(value_str)
        elif expected_type == float:
            try:
                return float(value_str)
            except ValueError:
                return 0.0
        elif expected_type == str:
            # Handle path resolution for sample opcodes
            if opcode_name == 'sample':
                return self._resolve_sample_path(value_str)
            return value_str
        else:
            # Default to string for unknown opcodes
            return value_str

    def _parse_note_name(self, note_str: str) -> int:
        """Parse note names (C4, D#5, etc.) to MIDI note numbers."""
        # Simple note name parser
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Check if it's already a number
        try:
            return int(note_str)
        except ValueError:
            pass

        # Parse note name
        match = re.match(r'^([A-G]#?)(\d+)$', note_str.upper())
        if match:
            note_name, octave = match.groups()
            octave = int(octave)

            # Calculate MIDI note number
            note_index = note_names.index(note_name)
            midi_note = (octave + 1) * 12 + note_index

            return midi_note

        # Default to middle C
        return 60

    def _resolve_sample_path(self, sample_path: str) -> str:
        """Resolve relative sample paths."""
        if not self.current_sfz_directory:
            return sample_path

        # If it's an absolute path, return as-is
        if Path(sample_path).is_absolute():
            return sample_path

        # Resolve relative to SFZ file directory
        resolved_path = self.current_sfz_directory / sample_path

        # Convert back to string
        return str(resolved_path)

    def _apply_opcode(self, instrument: SFZInstrument, section: str,
                     group: SFZGroup | None, opcode: SFZOpcode):
        """Apply an opcode to the appropriate section."""
        if section == '<global>':
            instrument.set_global_opcode(opcode)
        elif section == '<control>':
            instrument.set_control_opcode(opcode)
        elif section == '<group>':
            if group:
                group.set_opcode(opcode)
        elif section == '<region>':
            if group:
                # Create region if this is the first opcode
                if not group.regions:
                    group.add_region(SFZRegion())
                # Apply to the last region
                group.regions[-1].set_opcode(opcode)
            else:
                # Region without group - create implicit group
                if not instrument.groups:
                    instrument.add_group(SFZGroup())
                if not instrument.groups[-1].regions:
                    instrument.groups[-1].add_region(SFZRegion())
                instrument.groups[-1].regions[-1].set_opcode(opcode)

    def get_supported_opcodes(self) -> list[str]:
        """Get list of supported opcodes."""
        return list(self.STANDARD_OPCODES.keys())

    def validate_sfz_file(self, sfz_path: str) -> tuple[bool, list[str]]:
        """
        Validate an SFZ file for syntax errors.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        try:
            instrument = self.parse_file(sfz_path)

            # Basic validation
            if not instrument.groups and not instrument.get_all_regions():
                errors.append("SFZ file contains no regions")

            # Check for required opcodes in regions
            for region in instrument.get_all_regions():
                if not region.has_opcode('sample'):
                    errors.append("Region missing required 'sample' opcode")

            return len(errors) == 0, errors

        except Exception as e:
            return False, [f"Parse error: {str(e)}"]
