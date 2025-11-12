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
import time

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.engine.optimized_xg_synthesizer import OptimizedXGSynthesizer
from synth.midi.parser import MIDIParser, MIDIMessage
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
    parser.add_argument("--render-log-level", type=int, choices=[0, 1, 2], default=0,
                       help="Audio rendering logging level: 0=no logging, 1=log combined channel audio before effects, 2=log each channel renderer output")

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
    render_limit: Optional[float] = None,
    abort_event: Optional[threading.Event] = None,
    timeout_seconds:Optional[float] = None
) -> bool:
    """Convert a single MIDI file to audio using buffered processing mode."""
    try:
        if not silent:
            print(f"Converting {input_file} -> {output_file}")

        # Load MIDI file using new MIDIParser that supports both MIDI 1.0 and 2.0
        parser = MIDIParser(input_file)

        # Get duration info
        total_duration_seconds = parser.get_total_duration()
        if not silent:
            print(f"Total duration: {total_duration_seconds:.2f} seconds")

        all_messages = parser.get_all_messages()
        synthesizer.reset()

        if tempo == 1.0:
            synthesizer.send_midi_message_block(all_messages)
        else:
            scaled_messahes = [x.with_tempo(tempo) for x in all_messages]
            synthesizer.send_midi_message_block(scaled_messahes)

        time0 = parser.get_first_note_on_time()
        if time0:
            synthesizer.set_current_time(time0 / tempo)

        # Create audio writer
        writer = audio_writer.create_writer(output_file, format)

        # Set synthesizer volume
        synthesizer.set_master_volume(volume)

        # Initialize progress reporter
        adjusted_duration = total_duration_seconds / tempo if not render_limit else render_limit
        progress_reporter = ProgressReporter(silent=silent)
        progress_reporter.start(adjusted_duration)
        abort_at = time.time() + timeout_seconds if timeout_seconds else None

        # Buffer processing
        with writer:
            while synthesizer.get_current_time() < adjusted_duration:
                # Check for abort signal
                if abort_event and abort_event.is_set():
                    if not silent:
                        print("\nConversion aborted by user.")
                    return False

                # Check for timeout
                if abort_at and time.time() > abort_at:
                    if not silent:
                        print(f"\nConversion timed out after {timeout_seconds} seconds.")
                    return True

                out_buffer = synthesizer.generate_audio_block()
                writer.write(out_buffer)

                # Update progress
                progress_reporter.progress(synthesizer.get_current_time())

        # Finalize audio logging after conversion is complete
        synthesizer.finalize_audio_logging()

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
    chunk_size_ms = args.chunk_size_ms or config.get("chunk_size_ms", 50)
    max_polyphony = args.max_polyphony or config.get("polyphony", 64)
    master_volume = args.master_volume or config.get("volume", 0.8)
    sf2_files = args.sf2_files or config.get("sf2_files", [])

    format = args.format
    tempo = args.tempo
    silent = args.silent
    keyboard_abort = args.keyboard_abort
    recursive = args.recursive
    render_log_level = args.render_log_level

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
    synth_start = time.time()
    synthesizer = OptimizedXGSynthesizer(
        sample_rate=sample_rate,
        max_polyphony=max_polyphony,
        sf2_files=sf2_files,
        render_log_level=render_log_level
    )

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

    # Set up timeout mechanism (always active, regardless of keyboard abort)
    abort_event = threading.Event()

    # Initialize keyboard listener for abort if requested
    keyboard_listener = None

    if keyboard_abort:
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
                abort_event=abort_event,
                render_limit=50.0,
                timeout_seconds=150.0
            ):
                success_count += 1
            else:
                if abort_event.is_set():
                    break  # Stop processing if aborted or timed out
                print(f"Failed to convert: {input_file}")

        # Print summary
        if not silent:
            if abort_event and abort_event.is_set():
                print(f"\nConversion aborted or timed out. {success_count}/{len(input_files)} files converted successfully.")
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
