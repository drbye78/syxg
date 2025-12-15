#!/usr/bin/env python3
"""
MIDI to XGML Converter

Converts MIDI files to XGML (XG Markup Language) format for high-level XG synthesizer control.
Transforms low-level MIDI messages into human-readable XGML with semantic abstractions.

XGML provides:
- Human-readable parameter names instead of numerical IDs
- High-level semantic abstractions (pan: "center", program_change: "acoustic_grand_piano")
- Time-bound musical sequences
- Comprehensive XG effects configuration
"""

import os
import sys
import argparse
import yaml
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import math

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.midi.parser import MIDIParser, MIDIMessage
from synth.xgml.constants import (
    PROGRAM_NAMES, CONTROLLER_NAMES, PAN_POSITIONS,
    XGML_VERSION
)


class MIDItoXGMLConverter:
    """
    Converts MIDI files to XGML format.

    Extracts MIDI events and converts them to high-level XGML abstractions
    with human-readable parameter names and semantic values.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def convert_midi_to_xgml(self, midi_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Convert MIDI file to XGML document.

        Args:
            midi_file_path: Path to MIDI file

        Returns:
            XGML document dictionary or None on error
        """
        try:
            # Parse MIDI file
            parser = MIDIParser(midi_file_path)
            midi_messages = parser.get_all_messages()

            if not midi_messages:
                self.warnings.append("No MIDI messages found in file")
                return None

            # Create XGML document structure
            xgml_doc = self._create_xgml_document(midi_messages)

            return xgml_doc

        except Exception as e:
            self.errors.append(f"Error converting MIDI file: {e}")
            return None

    def _create_xgml_document(self, midi_messages: List[MIDIMessage]) -> Dict[str, Any]:
        """Create XGML document from MIDI messages."""
        xgml_doc = {
            'xg_dsl_version': XGML_VERSION,
            'description': 'Converted from MIDI file',
            'timestamp': self._get_current_timestamp()
        }

        # Extract different types of MIDI events
        basic_messages = self._extract_basic_messages(midi_messages)
        if basic_messages:
            xgml_doc['basic_messages'] = basic_messages

        sequences = self._extract_sequences(midi_messages)
        if sequences:
            xgml_doc['sequences'] = sequences

        return xgml_doc

    def _extract_basic_messages(self, messages: List[MIDIMessage]) -> Optional[Dict[str, Any]]:
        """Extract static configuration messages (program changes, controllers, etc.)."""
        channels_data = {}

        for msg in messages:
            if msg.time > 0:  # Skip timed messages
                continue

            channel_num = msg.channel
            if channel_num is None:
                continue

            channel_key = f"channel_{channel_num + 1}"  # Convert to 1-based indexing

            if channel_key not in channels_data:
                channels_data[channel_key] = {}

            # Program change
            if msg.type == 'program_change':
                program_name = self._midi_program_to_name(msg.program)
                channels_data[channel_key]['program_change'] = program_name

            # Control changes
            elif msg.type == 'control_change':
                controller_name = self._midi_controller_to_name(msg.control)
                if controller_name:
                    value = self._midi_controller_value_to_semantic(controller_name, msg.value)
                    channels_data[channel_key][controller_name] = value

        return {'channels': channels_data} if channels_data else None

    def _extract_sequences(self, messages: List[MIDIMessage]) -> Optional[Dict[str, Any]]:
        """Extract time-bound sequences from MIDI messages."""
        # Group messages by channel
        channel_sequences = {}

        for msg in messages:
            if msg.channel is None:
                continue

            channel = msg.channel
            if channel not in channel_sequences:
                channel_sequences[channel] = []

            # Convert MIDI message to XGML event
            xgml_event = self._midi_message_to_xgml_event(msg)
            if xgml_event:
                channel_sequences[channel].append(xgml_event)

        if not channel_sequences:
            return None

        # Create sequence structure
        sequences = {}
        track_num = 0

        for channel, events in channel_sequences.items():
            if not events:
                continue

            sequence_name = f"midi_track_{track_num}"
            sequences[sequence_name] = {
                'tempo': 120,  # Default tempo
                'time_signature': '4/4',
                'quantization': '1/8',
                'tracks': [{
                    'track': {
                        'channel': channel,
                        'events': events
                    }
                }]
            }
            track_num += 1

        return sequences

    def _midi_message_to_xgml_event(self, msg: MIDIMessage) -> Optional[Dict[str, Any]]:
        """Convert MIDI message to XGML event."""
        if msg.type == 'note_on':
            return {
                'at': {
                    'time': msg.time,
                    'note_on': {
                        'note': self._midi_note_to_name(msg.note),
                        'velocity': msg.velocity
                    }
                }
            }

        elif msg.type == 'note_off':
            return {
                'at': {
                    'time': msg.time,
                    'note_off': {
                        'note': self._midi_note_to_name(msg.note),
                        'velocity': msg.velocity
                    }
                }
            }

        elif msg.type == 'control_change':
            controller_name = self._midi_controller_to_name(msg.control)
            if controller_name:
                value = self._midi_controller_value_to_semantic(controller_name, msg.value)
                return {
                    'at': {
                        'time': msg.time,
                        controller_name: value
                    }
                }

        elif msg.type == 'program_change':
            program_name = self._midi_program_to_name(msg.program)
            return {
                'at': {
                    'time': msg.time,
                    'program_change': program_name
                }
            }

        return None

    def _midi_note_to_name(self, note_number: int) -> str:
        """Convert MIDI note number to note name (e.g., 60 -> 'C4')."""
        if not (0 <= note_number <= 127):
            return str(note_number)

        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_number // 12) - 1
        note = note_names[note_number % 12]

        return f"{note}{octave}"

    def _midi_program_to_name(self, program: int) -> str:
        """Convert MIDI program number to program name."""
        # Find the name for this program number
        for name, prog_num in PROGRAM_NAMES.items():
            if prog_num == program:
                return name
        return str(program)  # Return as string if not found

    def _midi_controller_to_name(self, controller: int) -> Optional[str]:
        """Convert MIDI controller number to controller name."""
        # CONTROLLER_NAMES has string keys, so we need to find the name by value
        for name, ctrl_num in CONTROLLER_NAMES.items():
            if ctrl_num == controller:
                return name
        return None

    def _midi_controller_value_to_semantic(self, controller: str, value: int) -> Union[str, int, bool]:
        """Convert MIDI controller value to semantic representation."""
        if controller == 'pan':
            # Find closest pan position
            closest_pos = min(PAN_POSITIONS.items(), key=lambda x: abs(x[1] - value))
            if abs(closest_pos[1] - value) <= 5:  # Within 5 units
                return closest_pos[0]
            return value

        # Boolean controllers
        if controller in ['sustain', 'portamento', 'sostenuto', 'soft_pedal', 'legato_foot', 'hold_2']:
            return value >= 64

        return value

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def save_xgml_file(self, xgml_doc: Dict[str, Any], output_path: str) -> bool:
        """Save XGML document to file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(xgml_doc, f, default_flow_style=False, sort_keys=False, indent=2)
            return True
        except Exception as e:
            self.errors.append(f"Error saving XGML file: {e}")
            return False

    def get_errors(self) -> List[str]:
        """Get list of conversion errors."""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get list of conversion warnings."""
        return self.warnings.copy()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert MIDI files to XGML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Convert MIDI files to XGML (XG Markup Language) for high-level XG synthesizer control.

XGML provides human-readable parameter names and semantic abstractions:
- program_change: "acoustic_grand_piano" instead of 0
- pan: "center" instead of 64
- Time-bound sequences with readable event timing

Examples:
   midi_to_xgml.py input.mid                    # Output: input.xgml
   midi_to_xgml.py input.mid output.xgml        # Specify output file
   midi_to_xgml.py *.mid --output-dir xgml/     # Convert multiple files
        """
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI file(s) to convert")
    parser.add_argument("output", nargs="?", help="Output XGML file or directory")
    parser.add_argument("--output-dir", "-d", help="Output directory for multiple files")

    return parser.parse_args()


def get_output_path(input_file: str, output: Optional[str], output_dir: Optional[str], multiple_files: bool) -> str:
    """Determine output path for XGML file."""
    input_path = Path(input_file)

    if output and not multiple_files:
        # Single output file specified
        output_path = Path(output)
        if output_path.suffix.lower() not in ['.xgml', '.yaml', '.yml']:
            output_path = output_path.with_suffix('.xgml')
        return str(output_path)

    # Determine output directory
    if output_dir:
        output_base = Path(output_dir)
    elif output and Path(output).is_dir():
        output_base = Path(output)
    else:
        output_base = Path(".")

    # Generate output filename
    output_filename = input_path.stem + '.xgml'
    return str(output_base / output_filename)


def main():
    """Main conversion function."""
    args = parse_arguments()

    # Check if we have multiple files
    multiple_files = len(args.input_files) > 1 or '*' in str(args.input_files) or '?' in str(args.input_files)

    success_count = 0

    for input_file in args.input_files:
        if not Path(input_file).exists():
            print(f"Error: Input file not found: {input_file}")
            continue

        if not input_file.lower().endswith(('.mid', '.midi')):
            print(f"Warning: Skipping non-MIDI file: {input_file}")
            continue

        # Determine output path
        output_file = get_output_path(input_file, args.output, args.output_dir, multiple_files)

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Converting {input_file} -> {output_file}")

        # Convert MIDI to XGML
        converter = MIDItoXGMLConverter()
        xgml_doc = converter.convert_midi_to_xgml(input_file)

        if xgml_doc is None:
            print(f"Failed to convert: {input_file}")
            if converter.get_errors():
                for error in converter.get_errors():
                    print(f"  - {error}")
            continue

        if converter.get_warnings():
            for warning in converter.get_warnings():
                print(f"Warning: {warning}")

        # Save XGML file
        if converter.save_xgml_file(xgml_doc, output_file):
            print(f"Conversion complete: {output_file}")
            success_count += 1
        else:
            print(f"Failed to save: {output_file}")
            for error in converter.get_errors():
                print(f"  - {error}")

    print(f"\nConversion summary: {success_count}/{len(args.input_files)} files converted successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nConversion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
