#!/usr/bin/env python3
"""
MIDI to OGG Converter using XG Synthesizer

This utility converts MIDI files to OGG format using the XG-compatible synthesizer.
It supports command-line arguments and YAML configuration files for setting
synthesizer parameters, SF2 files, and output options.
"""
# pyright: basic, reportAttributeAccessIssue=false

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

    # Opus supported sample rates
    OPUS_SUPPORTED_SAMPLE_RATES = [8000, 12000, 16000, 24000, 48000]
    
    # Opus frame durations in milliseconds
    OPUS_SUPPORTED_FRAME_DURATIONS = [2.5, 5, 10, 20, 40, 60]

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
        sample_rate = config.get("sample_rate", 48000)  # Changed default to 48kHz
        chunk_size_ms = config.get("chunk_size_ms", 20)  # Changed to milliseconds
        max_polyphony = config.get("max_polyphony", 64)
        master_volume = config.get("master_volume", 1.0)

        # Validate sample rate
        self._validate_sample_rate(sample_rate)
        
        # Validate chunk size
        self._validate_chunk_size(chunk_size_ms, sample_rate)

        # Calculate block size in samples from chunk size in milliseconds
        block_size = int(sample_rate * chunk_size_ms / 1000.0)

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
        self.chunk_size_ms = chunk_size_ms
        self.block_size = block_size

    def _validate_sample_rate(self, sample_rate: int):
        """
        Validate sample rate against Opus requirements

        Args:
            sample_rate: Sample rate to validate
        """
        if sample_rate not in self.OPUS_SUPPORTED_SAMPLE_RATES:
            raise ValueError(f"Unsupported sample rate {sample_rate}. Supported rates: {self.OPUS_SUPPORTED_SAMPLE_RATES}")

    def _validate_chunk_size(self, chunk_size_ms: float, sample_rate: int):
        """
        Validate chunk size against Opus requirements

        Args:
            chunk_size_ms: Chunk size in milliseconds
            sample_rate: Sample rate in Hz
        """
        # Calculate frame size in samples
        frame_size_samples = int(sample_rate * chunk_size_ms / 1000.0)
        
        # Valid frame sizes for Opus
        valid_frame_sizes = [120, 240, 480, 960, 1920, 2880]  # For 48kHz sample rate
        
        # Check if frame size is valid
        if frame_size_samples not in valid_frame_sizes:
            # Find closest valid frame size
            closest_size = min(valid_frame_sizes, key=lambda x: abs(x - frame_size_samples))
            closest_ms = closest_size * 1000.0 / sample_rate
            
            if not self.silent:
                print(f"Warning: Chunk size {chunk_size_ms}ms ({frame_size_samples} samples) is not optimal for Opus.")
                print(f"Closest valid chunk size: {closest_ms:.1f}ms ({closest_size} samples)")

    def convert_midi_to_ogg(
        self, midi_file: str, output_file: str, tempo_ratio: float = 1.0, output_format: str = "ogg"
    ) -> bool:
        """
        Convert a MIDI file to OGG or WAV using sample-accurate processing

        Args:
            midi_file: Path to the input MIDI file
            output_file: Path to the output audio file
            tempo_ratio: Tempo adjustment ratio (1.0 = original tempo)
            output_format: Output format ("ogg" or "wav")

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

            # Process the MIDI file and generate audio in the specified format using sample-accurate processing
            if output_format.lower() == "wav":
                self._process_midi_to_wav(midi, output_file, tempo_ratio)
            else:
                self._process_midi_to_ogg(midi, output_file, tempo_ratio)

            if not self.silent:
                print(f"Conversion completed successfully!")
            return True

        except Exception as e:
            if not self.silent:
                print(f"Error converting {midi_file}: {e}")
            return False

    def _collect_midi_messages(self, midi: mido.MidiFile):
        """
        Collect all MIDI messages with their absolute timestamps

        Args:
            midi: Loaded MIDI file

        Returns:
            tuple of (midi_messages, sysex_messages)
        """
        midi_messages = []
        sysex_messages = []
        tempo = 500000  # Initial tempo (microseconds per beat)
        tick_rate = midi.ticks_per_beat

        # Process all tracks and collect messages with absolute time
        for track in midi.tracks:
            abs_time = 0  # Absolute time in ticks
            for msg in track:
                abs_time += msg.time
                
                # Handle tempo changes
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                
                # Store all messages with their absolute time
                if msg.type == "sysex":
                    # Convert ticks to seconds for SYSEX message
                    seconds = (abs_time * tempo) / (1000000.0 * tick_rate)
                    sysex_messages.append((seconds, list(msg.bytes())))
                elif not msg.is_meta:
                    # Convert ticks to seconds for regular MIDI message
                    seconds = (abs_time * tempo) / (1000000.0 * tick_rate)
                    # Convert mido message to status/data format
                    if msg.type == "note_on":
                        midi_messages.append((seconds, 0x90 + msg.channel, msg.note, msg.velocity))
                    elif msg.type == "note_off":
                        midi_messages.append((seconds, 0x80 + msg.channel, msg.note, msg.velocity))
                    elif msg.type == "control_change":
                        midi_messages.append((seconds, 0xB0 + msg.channel, msg.control, msg.value))
                    elif msg.type == "program_change":
                        midi_messages.append((seconds, 0xC0 + msg.channel, msg.program, 0))
                    elif msg.type == "pitchwheel":
                        # Convert 14-bit pitch wheel value to MSB/LSB
                        value = msg.pitch + 8192  # mido range is -8192 to 8191, MIDI is 0 to 16383
                        lsb = value & 0x7F
                        msb = (value >> 7) & 0x7F
                        midi_messages.append((seconds, 0xE0 + msg.channel, lsb, msb))
                    elif msg.type == "polytouch":
                        midi_messages.append((seconds, 0xA0 + msg.channel, msg.note, msg.value))
                    elif msg.type == "aftertouch":
                        midi_messages.append((seconds, 0xD0 + msg.channel, msg.value, 0))

        # Sort both message lists by their timestamps to ensure proper chronological order
        midi_messages.sort(key=lambda x: x[0])  # Sort by timestamp (first element)
        sysex_messages.sort(key=lambda x: x[0])  # Sort by timestamp (first element)

        return midi_messages, sysex_messages

    def _process_audio_blocks(self, midi: mido.MidiFile, tempo_ratio: float = 1.0):
        """
        Generate audio blocks from MIDI file using sample-accurate mode

        Args:
            midi: Loaded MIDI file
            tempo_ratio: Tempo adjustment ratio

        Yields:
            tuple of (left_channel, right_channel) audio blocks
        """
        # Collect all messages with their absolute timestamps
        midi_messages, sysex_messages = self._collect_midi_messages(midi)

        # Send all messages to synthesizer in blocks using sample-accurate processing
        self.synth.send_midi_message_block(midi_messages, sysex_messages)
        for m in midi_messages:
            if 0x90 <= m[1] < 0xa0:
                self.synth.set_buffered_mode_time(m[0])
                break

        # Generate audio with proper timing using sample-accurate mode
        block_duration = self.block_size / self.sample_rate
        time_increment = block_duration / tempo_ratio
        
        # Generate audio blocks with automatic time management
        total_blocks = int(midi.length * self.sample_rate / self.block_size * tempo_ratio) + int(2.0 / block_duration)  # +2 seconds for decay
        
        for i in range(total_blocks):
            # Generate audio block at current time with sample-accurate processing
            left_channel, right_channel = self.synth.generate_audio_block_sample_accurate(
                self.block_size
            )
            
            yield left_channel, right_channel

            # Progress indicator
            if not self.silent and (i + 1) % max(1, total_blocks // 10) == 0:  # Every 10% or at least once
                progress_percent = (i + 1) / total_blocks * 100
                print(f"Progress: {progress_percent:.1f}% ({(i + 1) * self.block_size // self.sample_rate} seconds)")

    def _process_midi_to_ogg(
        self, midi: mido.MidiFile, output_file: str, tempo_ratio: float = 1.0
    ):
        """
        Process MIDI messages and generate OGG audio directly with sample-accurate timing

        Args:
            midi: Loaded MIDI file
            output_file: Output OGG file path
            tempo_ratio: Tempo adjustment ratio
        """
        # Create Opus encoder with validated parameters
        try:
            encoder = opuslib.Encoder(
                fs=self.sample_rate, channels=2, application=opuslib.APPLICATION_AUDIO
            )  # Stereo
        except Exception as e:
            raise ValueError(f"Failed to create Opus encoder with sample rate {self.sample_rate}: {e}")

        # Open OGG file for writing
        with open(output_file, "wb") as ogg_file:
            # Generate and process audio blocks with sample-accurate processing
            for left_channel, right_channel in self._process_audio_blocks(midi, tempo_ratio):
                # Convert to float32 in range [-1.0, 1.0]
                left_float32 = left_channel.astype(np.float32)
                right_float32 = right_channel.astype(np.float32)

                # Interleave channels (LRLRLR...)
                interleaved = np.empty(
                    (left_float32.size + right_float32.size,), dtype=np.float32
                )
                interleaved[0::2] = left_float32
                interleaved[1::2] = right_float32

                # Calculate frame size in samples (for 48kHz, 20ms = 960 samples)
                frame_size_samples = int(self.sample_rate * self.chunk_size_ms / 1000.0)
                samples_per_frame = frame_size_samples * 2  # Multiply by 2 for stereo
                
                # Process in chunks
                for j in range(0, len(interleaved), samples_per_frame):
                    chunk = interleaved[j:j+samples_per_frame]
                    if len(chunk) == samples_per_frame:
                        # Reshape for stereo
                        chunk = chunk.reshape(-1, 2)
                        # Encode chunk
                        try:
                            encoded_data = encoder.encode(chunk.tobytes(), frame_size_samples)
                            # Write to OGG file
                            ogg_file.write(encoded_data)
                        except Exception as e:
                            # Handle encoding errors silently
                            if not self.silent:
                                print(f"Warning: Opus encoding error: {e}")
                            pass

                # Progress indicator
                if not self.silent:
                    # We'll handle progress differently since we don't know total blocks upfront
                    pass

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

    def _send_sysex_message_to_synth(self, msg: mido.Message):
        """
        Send a mido SYSEX message to the synthesizer

        Args:
            msg: SYSEX message to send
        """
        if msg.type == "sysex":
            # Convert mido sysex format to list of integers including F0 and F7
            sysex_data = [0xF0] + list(msg.data) + [0xF7]
            self.synth.send_sysex(sysex_data)

    def _process_midi_to_wav(self, midi: mido.MidiFile, output_file: str, tempo_ratio: float = 1.0):
        """
        Process MIDI messages and generate WAV audio directly with sample-accurate timing

        Args:
            midi: Loaded MIDI file
            output_file: Output WAV file path
            tempo_ratio: Tempo adjustment ratio
        """
        import wave

        # Open WAV file for writing
        with wave.open(output_file, 'wb') as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)

            # Generate and process audio blocks with sample-accurate processing
            for left_channel, right_channel in self._process_audio_blocks(midi, tempo_ratio):
                # Convert to 16-bit PCM
                left_int16 = np.clip(left_channel, -1.0, 1.0) * 32767
                right_int16 = np.clip(right_channel, -1.0, 1.0) * 32767

                # Interleave channels (LRLRLR...)
                interleaved = np.empty((left_int16.size + right_int16.size,), dtype=np.int16)
                interleaved[0::2] = left_int16.astype(np.int16)
                interleaved[1::2] = right_int16.astype(np.int16)

                # Write to WAV file
                wav_file.writeframes(interleaved.tobytes())

                # Progress indicator
                if not self.silent:
                    # We'll handle progress differently since we don't know total blocks upfront
                    pass

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file or use defaults

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    # Default configuration with updated defaults
    default_config = {
        "sample_rate": 48000,  # Changed default to 48kHz
        "chunk_size_ms": 20,   # Changed to milliseconds with default 20ms
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
        help="Audio sample rate in Hz (default: 48000)",
    )

    parser.add_argument(
        "--chunk-size-ms",
        type=float,
        dest="chunk_size_ms",
        help="Audio processing chunk size in milliseconds (default: 20)",
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

    parser.add_argument(
    "--format",
    choices=["wav", "ogg"],
    default="ogg",
    help="Output audio format (default: ogg)"
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
    if args.chunk_size_ms:  # Updated parameter name
        config["chunk_size_ms"] = args.chunk_size_ms
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
    try:
        converter = MIDIToOGGConverter(config, args.silent)
    except ValueError as e:
        if not args.silent:
            print(f"Error: {e}")
        return 1

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
        if converter.convert_midi_to_ogg(input_file, output_file, args.tempo, args.format):
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
