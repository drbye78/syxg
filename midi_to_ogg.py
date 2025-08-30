#!/usr/bin/env python3
"""
MIDI to OGG Converter using XG Synthesizer

This utility converts MIDI files to OGG format using the XG-compatible synthesizer.
It supports command-line arguments and YAML configuration files for setting
synthesizer parameters, SF2 files, and output options.
"""

import argparse
import yaml
import os
import sys
import mido
import numpy as np
from typing import List, Dict, Any, Optional
import opuslib

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xg_synthesizer import XGSynthesizer


class MIDIToOGGConverter:
    """Converts MIDI files to OGG using XG Synthesizer"""

    def __init__(self, config: Dict[str, Any], silent: bool = False):
        """
        Initialize the converter with configuration

        Args:
            config: Configuration dictionary with synthesizer settings
            silent: Whether to suppress console output
        """
        self.config = config
        self.silent = silent

        # Extract configuration parameters
        sample_rate = config.get("sample_rate", 44100)
        block_size = config.get("block_size", 512)
        max_polyphony = config.get("max_polyphony", 64)
        master_volume = config.get("master_volume", 1.0)

        # Create synthesizer
        self.synth = XGSynthesizer(
            sample_rate=sample_rate, block_size=block_size, max_polyphony=max_polyphony
        )

        # Set master volume
        self.synth.set_master_volume(master_volume)

        # Load SF2 files if specified
        sf2_files = config.get("sf2_files", [])
        if sf2_files:
            self.synth.set_sf2_files(sf2_files)

            # Apply bank blacklists if specified
            bank_blacklists = config.get("bank_blacklists", {})
            for sf2_path, banks in bank_blacklists.items():
                self.synth.set_bank_blacklist(sf2_path, banks)

            # Apply preset blacklists if specified
            preset_blacklists = config.get("preset_blacklists", {})
            for sf2_path, presets in preset_blacklists.items():
                self.synth.set_preset_blacklist(sf2_path, presets)

            # Apply bank mappings if specified
            bank_mappings = config.get("bank_mappings", {})
            for sf2_path, mapping in bank_mappings.items():
                self.synth.set_bank_mapping(sf2_path, mapping)

        # Store other parameters
        self.sample_rate = sample_rate
        self.block_size = block_size

    def convert_midi_to_ogg(
        self, midi_file: str, output_file: str, tempo_ratio: float = 1.0
    ) -> bool:
        """
        Convert a MIDI file to OGG

        Args:
            midi_file: Path to the input MIDI file
            output_file: Path to the output OGG file
            tempo_ratio: Tempo adjustment ratio (1.0 = original tempo)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to absolute paths
            midi_file = os.path.abspath(midi_file)
            output_file = os.path.abspath(output_file)

            # Verify input file exists
            if not os.path.exists(midi_file):
                if not self.silent:
                    print(f"Error: Input file '{midi_file}' not found")
                return False

            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Load the MIDI file
            midi = mido.MidiFile(midi_file)

            # Calculate total number of ticks and duration
            tick_rate = midi.ticks_per_beat
            tempo = 500000  # Default tempo (microseconds per beat)

            # Process all messages to calculate duration
            total_ticks = 0
            for track in midi.tracks:
                track_ticks = sum(msg.time for msg in track)
                total_ticks = max(total_ticks, track_ticks)

            # Estimate duration in seconds
            estimated_duration = (
                (total_ticks * tempo) / (1000000 * tick_rate) / tempo_ratio
            )

            if not self.silent:
                print(f"Converting {midi_file} to {output_file}")
                print(f"Estimated duration: {estimated_duration:.2f} seconds")

            # Process the MIDI file and generate audio directly to OGG
            self._process_midi_to_ogg(midi, output_file, tempo_ratio)

            if not self.silent:
                print(f"Conversion completed successfully!")
            return True

        except Exception as e:
            if not self.silent:
                print(f"Error converting {midi_file}: {e}")
            return False

    def _process_midi_to_ogg(
        self, midi: mido.MidiFile, output_file: str, tempo_ratio: float = 1.0
    ):
        """
        Process MIDI messages and generate OGG audio directly

        Args:
            midi: Loaded MIDI file
            output_file: Output OGG file path
            tempo_ratio: Tempo adjustment ratio
        """
        # Create Opus encoder
        encoder = opuslib.Encoder(
            fs=self.sample_rate, channels=2, application=opuslib.APPLICATION_AUDIO
        )  # Stereo

        # Open OGG file for writing
        with open(output_file, "wb") as ogg_file:
            # Initialize tempo and timing
            tempo = 500000  # Microseconds per beat
            tick_rate = midi.ticks_per_beat

            # Process all tracks
            for track in midi.tracks:
                # Process messages
                abs_time = 0  # Absolute time in ticks
                for msg in track:
                    abs_time += msg.time

                    # Handle tempo changes
                    if msg.type == "set_tempo":
                        tempo = msg.tempo

                    # Send message to synthesizer
                    if not msg.is_meta:
                        self._send_midi_message_to_synth(msg)

            # Generate audio in blocks and encode directly to OGG
            total_samples = 0
            silence_samples = 0  # Count consecutive silent samples

            # Buffer for collecting audio blocks before encoding
            audio_buffer = np.array([], dtype=np.float32)

            while True:
                # Check if there are active voices
                active_voices = self.synth.get_active_voice_count()

                # Generate audio block
                left_channel, right_channel = self.synth.generate_audio_block(
                    self.block_size
                )

                # Convert to float32 in range [-1.0, 1.0]
                left_float32 = left_channel.astype(np.float32)
                right_float32 = right_channel.astype(np.float32)

                # Interleave channels (LRLRLR...)
                interleaved = np.empty(
                    (left_float32.size + right_float32.size,), dtype=np.float32
                )
                interleaved[0::2] = left_float32
                interleaved[1::2] = right_float32

                # Add to buffer
                audio_buffer = np.concatenate([audio_buffer, interleaved])
                total_samples += self.block_size

                # Check for silence (all samples close to zero)
                if np.max(np.abs(interleaved)) < 0.001:  # Threshold for silence
                    silence_samples += self.block_size
                else:
                    silence_samples = 0  # Reset counter if we hear sound

                # Encode when we have enough samples for a full frame
                # Opus frame size is typically 960 at 48kHz (20ms)
                frame_size = 960
                samples_per_frame = frame_size * 2  # Multiply by 2 for stereo

                if len(audio_buffer) >= samples_per_frame:
                    # Take exactly the number of samples we need for encoding
                    encode_data = audio_buffer[:samples_per_frame]

                    # Reshape for stereo
                    encode_data = encode_data.reshape(-1, 2)

                    # Encode chunk
                    encoded_data = encoder.encode(encode_data.tobytes(), frame_size)

                    # Write to OGG file
                    ogg_file.write(encoded_data)

                    # Remove the encoded data from buffer
                    audio_buffer = audio_buffer[samples_per_frame:]

                # Stop if we've had 1 second of silence and some audio has been generated
                if (
                    silence_samples > self.sample_rate
                    and total_samples > self.sample_rate * 2
                ):
                    break

                # Progress indicator
                if (
                    not self.silent and total_samples % (self.sample_rate * 10) == 0
                ):  # Every 10 seconds
                    print(
                        f"Generated {total_samples // self.sample_rate} seconds of audio..."
                    )

            # Encode any remaining samples in the buffer
            if len(audio_buffer) > 0:
                # Pad with zeros if needed
                if len(audio_buffer) < samples_per_frame:
                    padding = np.zeros(
                        (samples_per_frame - len(audio_buffer),), dtype=np.float32
                    )
                    audio_buffer = np.concatenate([audio_buffer, padding])

                # Reshape for stereo
                audio_buffer = audio_buffer.reshape(-1, 2)

                # Encode final chunk
                encoded_data = encoder.encode(audio_buffer.tobytes(), frame_size)

                # Write to OGG file
                ogg_file.write(encoded_data)

    def _send_midi_message_to_synth(self, msg: mido.Message):
        """
        Send a mido MIDI message to the synthesizer

        Args:
            msg: MIDI message to send
        """
        if msg.type == "note_on":
            self.synth.send_midi_message(0x90 + msg.channel, msg.note, msg.velocity)
        elif msg.type == "note_off":
            self.synth.send_midi_message(0x80 + msg.channel, msg.note, msg.velocity)
        elif msg.type == "control_change":
            self.synth.send_midi_message(0xB0 + msg.channel, msg.control, msg.value)
        elif msg.type == "program_change":
            self.synth.send_midi_message(0xC0 + msg.channel, msg.program)
        elif msg.type == "pitchwheel":
            # Convert 14-bit pitch wheel value to MSB/LSB
            value = msg.pitch + 8192  # mido range is -8192 to 8191, MIDI is 0 to 16383
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            self.synth.send_midi_message(0xE0 + msg.channel, lsb, msb)
        elif msg.type == "polytouch":
            self.synth.send_midi_message(0xA0 + msg.channel, msg.note, msg.value)
        elif msg.type == "aftertouch":
            self.synth.send_midi_message(0xD0 + msg.channel, msg.value)


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file or use defaults

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    # Default configuration
    default_config = {
        "sample_rate": 44100,
        "block_size": 512,
        "max_polyphony": 64,
        "master_volume": 1.0,
        "sf2_files": [],
        "bank_blacklists": {},
        "preset_blacklists": {},
        "bank_mappings": {},
    }

    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(config or {})
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
            print("Using default configuration.")

    return default_config


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert MIDI files to OGG using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  midi_to_ogg.py input.mid output.ogg
  midi_to_ogg.py -c config.yaml input.mid output.ogg
  midi_to_ogg.py --sf2 soundfont.sf2 input.mid output.ogg
  midi_to_ogg.py --sample-rate 48000 input.mid output.ogg
  midi_to_ogg.py --silent input.mid output.ogg
        """,
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI file(s) to convert")

    parser.add_argument("output", help="Output file or directory (if multiple inputs)")

    parser.add_argument(
        "-c", "--config", help="Path to YAML configuration file", default="config.yaml"
    )

    parser.add_argument(
        "--sf2",
        action="append",
        dest="sf2_files",
        help="SoundFont (.sf2) file paths (can be used multiple times)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        dest="sample_rate",
        help="Audio sample rate in Hz (default: 44100)",
    )

    parser.add_argument(
        "--block-size",
        type=int,
        dest="block_size",
        help="Audio processing block size (default: 512)",
    )

    parser.add_argument(
        "--polyphony",
        type=int,
        dest="max_polyphony",
        help="Maximum polyphony (default: 64)",
    )

    parser.add_argument(
        "--volume",
        type=float,
        dest="master_volume",
        help="Master volume (0.0 to 1.0, default: 1.0)",
    )

    parser.add_argument(
        "--tempo",
        type=float,
        default=1.0,
        help="Tempo ratio (default: 1.0 = original tempo)",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress console output during conversion",
    )

    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Load configuration
    config = load_config(args.config)

    # Override config with command-line arguments
    if args.sf2_files:
        config["sf2_files"] = args.sf2_files
    if args.sample_rate:
        config["sample_rate"] = args.sample_rate
    if args.block_size:
        config["block_size"] = args.block_size
    if args.max_polyphony:
        config["max_polyphony"] = args.max_polyphony
    if args.master_volume is not None:
        config["master_volume"] = args.master_volume

    # Check if output is a directory
    output_is_dir = os.path.isdir(args.output) or len(args.input_files) > 1

    # Validate inputs
    if not args.input_files:
        if not args.silent:
            print("Error: No input files specified")
        return 1

    # Check if all input files exist
    for input_file in args.input_files:
        if not os.path.exists(input_file):
            if not args.silent:
                print(f"Error: Input file '{input_file}' not found")
            return 1

    # Create converter
    converter = MIDIToOGGConverter(config, args.silent)

    # Process files
    success_count = 0
    for input_file in args.input_files:
        # Determine output file name
        if output_is_dir:
            # Generate output file name based on input file
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            if args.output.endswith(".ogg") and len(args.input_files) == 1:
                output_file = args.output
            else:
                output_file = os.path.join(args.output, f"{base_name}.ogg")
        else:
            output_file = args.output

        # Convert file
        if converter.convert_midi_to_ogg(input_file, output_file, args.tempo):
            success_count += 1
        else:
            if not args.silent:
                print(f"Failed to convert {input_file}")

    if not args.silent:
        print(
            f"\nConversion completed: {success_count}/{len(args.input_files)} files successful"
        )
    return 0 if success_count == len(args.input_files) else 1


if __name__ == "__main__":
    sys.exit(main())
