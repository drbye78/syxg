#!/usr/bin/env python3
"""
MIDI to Audio Converter - Unified Audio Encoding with Keyboard Control

Converts MIDI files to high-quality audio using XG Synthesizer with
unified audio writing support for multiple formats and keyboard abort capability.
"""

import os
import sys
import argparse
import yaml
import glob
from typing import List, Optional, Tuple
from pathlib import Path
import threading

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.core.optimized_xg_synthesizer import OptimizedXGSynthesizer
from synth.midi.parser import MIDIParser
from synth.utils.keyboard import KeyboardListener
from synth.utils.progress import ProgressReporter


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert MIDI files to audio using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Supported formats: ogg, wav, mp3, aac, flac, m4a
Examples:
   render_midi.py input.mid                    # Output: input.ogg (same name, format extension)
   render_midi.py input.mid output.wav         # Output: output.wav
   render_midi.py --format mp3 input.mid       # Output: input.mp3
   render_midi.py --volume 0.8 *.mid           # Output to current directory
   render_midi.py --recursive *.mid output/    # Recurse subdirectories
   render_midi.py --keyboard-abort input.mid
        """
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI file(s) or patterns to convert (supports wildcards)")
    parser.add_argument("output", nargs="?", default=None, help="Output file or directory (optional)")
    parser.add_argument("-c", "--config", help="Path to YAML configuration file", default="config.yaml")
    parser.add_argument("--sf2", action="append", dest="sf2_files", help="SoundFont (.sf2) file paths")
    parser.add_argument("--sample-rate", type=int, dest="sample_rate", help="Audio sample rate in Hz")
    parser.add_argument("--chunk-size-ms", type=float, dest="chunk_size_ms", help="Audio processing chunk size in milliseconds")
    parser.add_argument("--polyphony", type=int, dest="max_polyphony", help="Maximum polyphony")
    parser.add_argument("--volume", type=float, dest="master_volume", help="Master volume (0.0 to 1.0)")
    parser.add_argument("--tempo", type=float, default=1.0, help="Tempo ratio (default: 1.0 = original tempo)")
    parser.add_argument("--silent", action="store_true", help="Suppress console output during conversion")
    parser.add_argument("--keyboard-abort", action="store_true", help="Enable keyboard abort with SPACE key")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recurse into subdirectories")
    parser.add_argument("--format", choices=list(AudioWriter.SUPPORTED_FORMATS.keys()), default="ogg", help="Output audio format")

    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    default_config = {
        "sample_rate": 48000,
        "chunk_size_ms": 512 / 48000 * 1000,  # Convert to ms
        "polyphony": 64,
        "volume": 0.8,
        "sf2_files": []
    }

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        default_config.update(user_config)

    return default_config


def expand_file_patterns(patterns: List[str], recursive: bool = False) -> List[str]:
    """Expand file patterns and optionally recurse into subdirectories."""
    midi_files = []

    for pattern in patterns:
        # Handle both file paths and glob patterns
        if '*' in pattern or '?' in pattern:
            # It's a glob pattern
            if recursive:
                # Use ** for recursive globbing
                import fnmatch
                import os

                # For recursive, we need to walk directories
                pattern_path = Path(pattern)
                if '**' in pattern or pattern_path.parent != Path('.'):
                    # Complex pattern, use glob with **
                    if '**' not in pattern:
                        # Convert simple pattern to recursive
                        pattern_parts = Path(pattern).parts
                        if len(pattern_parts) > 1:
                            # Has directory parts
                            base_dir = Path(*pattern_parts[:-1])
                            file_pattern = pattern_parts[-1]
                            search_pattern = str(base_dir / "**" / file_pattern)
                        else:
                            search_pattern = f"**/{pattern}"
                    else:
                        search_pattern = pattern

                    matched_files = glob.glob(search_pattern, recursive=True)
                else:
                    # Simple recursive glob
                    matched_files = glob.glob(f"**/{pattern}", recursive=True)
            else:
                # Non-recursive glob
                matched_files = glob.glob(pattern, recursive=False)

            # Filter for MIDI files
            for file_path in matched_files:
                if file_path.lower().endswith(('.mid', '.midi')):
                    midi_files.append(file_path)
        else:
            # Direct file path
            if Path(pattern).exists() and pattern.lower().endswith(('.mid', '.midi')):
                midi_files.append(pattern)
            elif recursive and Path(pattern).is_dir():
                # Directory with recursive flag - find all MIDI files in subdirs
                for root, dirs, files in os.walk(pattern):
                    for file in files:
                        if file.lower().endswith(('.mid', '.midi')):
                            midi_files.append(os.path.join(root, file))

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file in midi_files:
        if file not in seen:
            seen.add(file)
            unique_files.append(file)

    return unique_files


def get_output_path(input_file: str, output: Optional[str], format: str, multiple_files: bool = False) -> str:
    """Determine the output file path based on input and output specifications."""
    input_path = Path(input_file)

    if output is None:
        # No output specified
        if multiple_files:
            # Multiple files -> output to current directory
            output_name = input_path.stem + f".{format}"
            return str(Path(".") / output_name)
        else:
            # Single file -> same name, different extension
            return str(input_path.with_suffix(f".{format}"))

    # Output specified
    output_path = Path(output)

    if output_path.is_dir() or (not output_path.suffix and multiple_files):
        # Output is a directory or multiple files with no extension
        output_name = input_path.stem + f".{format}"
        return str(output_path / output_name)
    else:
        # Single output file specified
        if output_path.suffix:
            return str(output_path)
        else:
            return str(output_path.with_suffix(f".{format}"))


def convert_midi_to_audio_buffered(
    input_file: str,
    output_file: str,
    synthesizer: OptimizedXGSynthesizer,
    audio_writer: AudioWriter,
    format: str,
    tempo: float = 1.0,
    volume: float = 0.8,
    silent: bool = False,
    chunk_size_ms: float = 10.6667,
    abort_event: Optional[threading.Event] = None
) -> bool:
    """Convert a single MIDI file to audio using buffered processing mode."""
    try:
        if not silent:
            print(f"Converting {input_file} -> {output_file}")

        # Load MIDI file using new MIDIParser that supports both MIDI 1.0 and 2.0
        parser = MIDIParser(input_file)

        # Get all messages upfront for buffered processing
        all_messages = parser.get_all_messages()

        # Get duration info
        total_duration_seconds = parser.get_total_duration()
        adjusted_duration_seconds = total_duration_seconds / tempo
        total_samples = int(adjusted_duration_seconds * synthesizer.sample_rate)

        if not silent:
            print(f"Total duration: {total_duration_seconds:.2f} seconds")

        # Prepare buffered messages
        midi_messages = []
        sysex_messages = []

        for msg in all_messages:
            # Adjust timing for tempo
            adjusted_time = msg['time'] / tempo

            msg_type = msg.get('type')
            if msg_type == 'sysex':
                # SYSEX message
                sysex_messages.append((adjusted_time, msg['data']))
            elif 'status' in msg and 'data' in msg:
                # Channel message with raw data
                status = msg['status']
                data = msg['data'] if isinstance(msg['data'], list) else [msg['data']]
                data1 = data[0] if len(data) > 0 else 0
                data2 = data[1] if len(data) > 1 else 0
                midi_messages.append((adjusted_time, status, data1, data2))
            elif msg_type in ['note_on', 'note_off', 'control_change', 'program_change', 'pitch_bend']:
                # Handle parsed message format
                if msg_type in ['note_on', 'note_off']:
                    midi_messages.append((adjusted_time, msg['status'], msg['note'], msg['velocity']))
                elif msg_type == 'control_change':
                    midi_messages.append((adjusted_time, msg['status'], msg['control'], msg['value']))
                elif msg_type == 'program_change':
                    midi_messages.append((adjusted_time, msg['status'], msg['program'], 0))
                elif msg_type == 'pitch_bend':
                    # Convert 14-bit pitch bend to two bytes
                    pitch_value = msg['pitch'] + 8192  # Convert from signed to unsigned
                    data1 = pitch_value & 0x7F
                    data2 = (pitch_value >> 7) & 0x7F
                    midi_messages.append((adjusted_time, msg['status'], data1, data2))

        # Send all messages to synthesizer's buffered processor
        synthesizer.send_midi_message_block(midi_messages, sysex_messages)

        # Create audio writer
        writer = audio_writer.create_writer(output_file, format)

        # Set synthesizer volume
        synthesizer.set_master_volume(volume)

        # Initialize progress reporter
        progress_reporter = ProgressReporter(silent=silent)
        progress_reporter.start(total_samples)

        # Buffer processing
        block_size = synthesizer.block_size
        processed_samples = 0
        current_time = 0.0

        with writer:
            while processed_samples < total_samples:
                # Check for abort signal
                if abort_event and abort_event.is_set():
                    if not silent:
                        print("\nConversion aborted by user.")
                    return False

                current_block_size = min(block_size, total_samples - processed_samples)

                # Generate audio block using buffered processing
                # The synthesizer will automatically process buffered messages
                left, right = synthesizer.generate_audio_block(current_block_size)

                # Write audio block
                writer.write(left, right)

                processed_samples += current_block_size

                # Update progress
                progress_reporter.update(current_block_size)

        if not silent:
            print(f"Conversion complete: {output_file}")

        return True

    except Exception as e:
        print(f"Error converting {input_file}: {e}")
        return False


def main():
    """Main conversion function."""
    # Parse arguments
    args = parse_arguments()

    # Load configuration
    config = load_config(args.config)

    # Get configuration values (command line overrides config file)
    sample_rate = args.sample_rate or config.get("sample_rate", 48000)
    chunk_size_ms = args.chunk_size_ms or config.get("chunk_size_ms", 512 / 48000 * 1000)
    max_polyphony = args.max_polyphony or config.get("polyphony", 64)
    master_volume = args.master_volume or config.get("volume", 0.8)
    sf2_files = args.sf2_files or config.get("sf2_files", [])

    format = args.format
    tempo = args.tempo
    silent = args.silent
    keyboard_abort = args.keyboard_abort
    recursive = args.recursive

    # Expand file patterns to get actual MIDI files
    input_files = expand_file_patterns(args.input_files, recursive)

    if not input_files:
        print("Error: No MIDI files found matching the specified patterns.")
        return False

    if not silent:
        print(f"Found {len(input_files)} MIDI file(s) to convert")

    # Determine if we have multiple files
    multiple_files = len(input_files) > 1

    # Initialize synthesizer
    synthesizer = OptimizedXGSynthesizer(
        sample_rate=sample_rate,
        block_size=int(chunk_size_ms / 1000 * sample_rate),
        max_polyphony=max_polyphony
    )

    # Set SF2 files if provided
    if sf2_files:
        synthesizer.set_sf2_files(sf2_files)

    # Initialize audio writer
    audio_writer = AudioWriter(sample_rate, chunk_size_ms)

    # Ensure output directory exists if needed
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir() or (not output_path.suffix and multiple_files):
            output_path.mkdir(parents=True, exist_ok=True)
    elif multiple_files:
        # Multiple files with no output specified -> use current directory
        Path(".").mkdir(parents=True, exist_ok=True)

    # Initialize keyboard listener for abort if requested
    abort_event = None
    keyboard_listener = None

    if keyboard_abort:
        abort_event = threading.Event()
        keyboard_listener = KeyboardListener()

        def on_key_press(key: str):
            if key.upper() == ' ':
                print("\nSPACE pressed - Aborting conversion...")
                abort_event.set()

        keyboard_listener.add_callback(on_key_press)
        keyboard_listener.start()

        if not silent:
            print("Press SPACE to abort conversion at any time.")

    try:
        # Convert each input file
        success_count = 0
        for input_file in input_files:
            if not os.path.exists(input_file):
                print(f"Error: Input file not found: {input_file}")
                continue

            output_file = get_output_path(input_file, args.output, format, multiple_files)

            if convert_midi_to_audio_buffered(
                input_file=input_file,
                output_file=output_file,
                synthesizer=synthesizer,
                audio_writer=audio_writer,
                format=format,
                tempo=tempo,
                volume=master_volume,
                silent=silent,
                chunk_size_ms=chunk_size_ms,
                abort_event=abort_event
            ):
                success_count += 1
            else:
                if abort_event and abort_event.is_set():
                    break  # Stop processing if aborted
                print(f"Failed to convert: {input_file}")

        # Print summary
        if not silent:
            if abort_event and abort_event.is_set():
                print(f"\nConversion aborted. {success_count}/{len(input_files)} files converted successfully.")
            else:
                print(f"\nConversion complete. {success_count}/{len(input_files)} files converted successfully.")

        return success_count == len(input_files)

    finally:
        # Clean up keyboard listener
        if keyboard_listener:
            keyboard_listener.stop()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
