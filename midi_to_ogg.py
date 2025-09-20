#!/usr/bin/env python3
"""
MIDI to Audio Converter - Unified Audio Encoding

Converts MIDI files to high-quality audio using XG Synthesizer with
unified audio writing support for multiple formats.
"""

import os
import sys
import argparse
import yaml
from typing import List, Optional, Tuple
from pathlib import Path

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.core.optimized_xg_synthesizer import OptimizedXGSynthesizer
from synth.midi.parser import MIDIParser


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert MIDI files to audio using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Supported formats: ogg, wav, mp3, aac, flac, m4a
Examples:
  midi_to_ogg.py input.mid output.ogg
  midi_to_ogg.py --format mp3 input.mid output.mp3
  midi_to_ogg.py --volume 0.8 *.mid output/
        """
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI file(s) to convert")
    parser.add_argument("output", default=".", help="Output file or directory")
    parser.add_argument("-c", "--config", help="Path to YAML configuration file", default="config.yaml")
    parser.add_argument("--sf2", action="append", dest="sf2_files", help="SoundFont (.sf2) file paths")
    parser.add_argument("--sample-rate", type=int, dest="sample_rate", help="Audio sample rate in Hz")
    parser.add_argument("--chunk-size-ms", type=float, dest="chunk_size_ms", help="Audio processing chunk size in milliseconds")
    parser.add_argument("--polyphony", type=int, dest="max_polyphony", help="Maximum polyphony")
    parser.add_argument("--volume", type=float, dest="master_volume", help="Master volume (0.0 to 1.0)")
    parser.add_argument("--tempo", type=float, default=1.0, help="Tempo ratio (default: 1.0 = original tempo)")
    parser.add_argument("--silent", action="store_true", help="Suppress console output during conversion")
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


def get_output_path(input_file: str, output: str, format: str) -> str:
    """Determine the output file path."""
    input_path = Path(input_file)

    if Path(output).is_dir():
        # Output directory
        output_name = input_path.stem + f".{format}"
        return str(Path(output) / output_name)
    else:
        # Single output file
        output_path = Path(output)
        if output_path.suffix:
            return str(output_path)
        else:
            return str(output_path.with_suffix(f".{format}"))


def convert_midi_to_audio(
    input_file: str,
    output_file: str,
    synthesizer: OptimizedXGSynthesizer,
    audio_writer: AudioWriter,
    format: str,
    tempo: float = 1.0,
    volume: float = 0.8,
    silent: bool = False,
    chunk_size_ms: float = 10.6667
) -> bool:
    """Convert a single MIDI file to audio."""
    try:
        if not silent:
            print(f"Converting {input_file} -> {output_file}")

        # Load MIDI file using new MIDIParser that supports both MIDI 1.0 and 2.0
        parser = MIDIParser(input_file)

        # Get duration info
        total_duration_ms = parser.get_total_duration() * 1000  # Convert to milliseconds
        adjusted_duration_ms = total_duration_ms / tempo
        total_samples = int(adjusted_duration_ms / 1000 * synthesizer.sample_rate)

        if not silent:
            print(f"Total duration: {total_duration_ms:.2f} ms")

        # Create audio writer
        writer = audio_writer.create_writer(output_file, format)

        # Set synthesizer volume
        synthesizer.set_master_volume(volume)

        # Buffer processing
        block_size = synthesizer.block_size
        processed_samples = 0
        last_progress = 0

        # Resample messages at tempo-adjusted rate
        chunk_duration_ms = chunk_size_ms / tempo

        with writer:
            while processed_samples < total_samples:
                current_block_size = min(block_size, total_samples - processed_samples)

                # Get MIDI messages for this time chunk
                next_len = current_block_size / synthesizer.sample_rate * 1000.0
                messages = parser.get_next_messages(next_len)

                # Send MIDI messages to synthesizer
                for msg in messages:
                    msg_type = msg.get('type')
                    if msg_type == 'sysex':
                        # Send SysEx message
                        synthesizer.send_sysex(msg['data'])
                    elif 'status' in msg and 'data' in msg:
                        # Send channel message
                        status = msg['status']
                        data = msg['data'] if isinstance(msg['data'], list) else [msg['data']]
                        data1 = data[0] if len(data) > 0 else 0
                        data2 = data[1] if len(data) > 1 else 0
                        synthesizer.send_midi_message(status, data1, data2)
                    elif msg_type in ['note_on', 'note_off', 'control_change', 'program_change', 'pitch_bend']:
                        # Handle parsed message format
                        if msg_type in ['note_on', 'note_off']:
                            synthesizer.send_midi_message(msg['status'], msg['note'], msg['velocity'])
                        elif msg_type == 'control_change':
                            synthesizer.send_midi_message(msg['status'], msg['control'], msg['value'])
                        elif msg_type == 'program_change':
                            synthesizer.send_midi_message(msg['status'], msg['program'], 0)
                        elif msg_type == 'pitch_bend':
                            # Convert 14-bit pitch bend to two bytes
                            pitch_value = msg['pitch'] + 8192  # Convert from signed to unsigned
                            data1 = pitch_value & 0x7F
                            data2 = (pitch_value >> 7) & 0x7F
                            synthesizer.send_midi_message(msg['status'], data1, data2)

                # Generate audio block
                left, right = synthesizer.generate_audio_block_sample_accurate(current_block_size)

                # Write audio block
                writer.write(left, right)

                processed_samples += current_block_size

                # Show progress
                if not silent:
                    progress = int(processed_samples / total_samples * 100)
                    if progress >= last_progress + 10:
                        print(f"Progress: {progress}%")
                        last_progress = progress

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

    # Ensure output directory exists if specified as directory
    output_path = Path(args.output)
    if len(args.input_files) > 1 or not output_path.suffix:
        output_path.mkdir(parents=True, exist_ok=True)

    # Convert each input file
    success_count = 0
    for input_file in args.input_files:
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            continue

        output_file = get_output_path(input_file, args.output, format)

        if convert_midi_to_audio(
            input_file=input_file,
            output_file=output_file,
            synthesizer=synthesizer,
            audio_writer=audio_writer,
            format=format,
            tempo=tempo,
            volume=master_volume,
            silent=silent,
            chunk_size_ms=chunk_size_ms
        ):
            success_count += 1
        else:
            print(f"Failed to convert: {input_file}")

    # Print summary
    if not silent:
        print(f"\nConversion complete. {success_count}/{len(args.input_files)} files converted successfully.")

    return success_count == len(args.input_files)


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
