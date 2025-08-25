#!/usr/bin/env python3
"""
MIDI to MP3 Converter using XG Synthesizer

This utility converts MIDI files to MP3 format using the XG-compatible synthesizer.
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
from pydub import AudioSegment

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xg_synthesizer import XGSynthesizer

class MIDIToMP3Converter:
    """Converts MIDI files to MP3 using XG Synthesizer"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the converter with configuration
        
        Args:
            config: Configuration dictionary with synthesizer settings
        """
        self.config = config
        
        # Extract configuration parameters
        sample_rate = config.get('sample_rate', 44100)
        block_size = config.get('block_size', 512)
        max_polyphony = config.get('max_polyphony', 64)
        master_volume = config.get('master_volume', 1.0)
        
        # Create synthesizer
        self.synth = XGSynthesizer(
            sample_rate=sample_rate,
            block_size=block_size,
            max_polyphony=max_polyphony
        )
        
        # Set master volume
        self.synth.set_master_volume(master_volume)
        
        # Load SF2 files if specified
        sf2_files = config.get('sf2_files', [])
        if sf2_files:
            self.synth.set_sf2_files(sf2_files)
            
            # Apply bank blacklists if specified
            bank_blacklists = config.get('bank_blacklists', {})
            for sf2_path, banks in bank_blacklists.items():
                self.synth.set_bank_blacklist(sf2_path, banks)
                
            # Apply preset blacklists if specified
            preset_blacklists = config.get('preset_blacklists', {})
            for sf2_path, presets in preset_blacklists.items():
                self.synth.set_preset_blacklist(sf2_path, presets)
                
            # Apply bank mappings if specified
            bank_mappings = config.get('bank_mappings', {})
            for sf2_path, mapping in bank_mappings.items():
                self.synth.set_bank_mapping(sf2_path, mapping)
        
        # Store other parameters
        self.sample_rate = sample_rate
        self.block_size = block_size
        
    def convert_midi_to_mp3(self, midi_file: str, output_file: str, 
                           tempo_ratio: float = 1.0) -> bool:
        """
        Convert a MIDI file to MP3
        
        Args:
            midi_file: Path to the input MIDI file
            output_file: Path to the output MP3 file
            tempo_ratio: Tempo adjustment ratio (1.0 = original tempo)
            
        Returns:
            True if successful, False otherwise
        """
        try:
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
            estimated_duration = (total_ticks * tempo) / (1000000 * tick_rate) / tempo_ratio
            
            print(f"Converting {midi_file} to {output_file}")
            print(f"Estimated duration: {estimated_duration:.2f} seconds")
            
            # Create a temporary WAV file for the output
            temp_wav = output_file.replace('.mp3', '.wav') if output_file.endswith('.mp3') else output_file + '.wav'
            
            # Process the MIDI file and generate audio
            self._process_midi_messages(midi, temp_wav, tempo_ratio)
            
            # Convert WAV to MP3
            if output_file.endswith('.mp3'):
                self._convert_wav_to_mp3(temp_wav, output_file)
                # Remove temporary WAV file
                os.remove(temp_wav)
            
            print(f"Conversion completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error converting {midi_file}: {e}")
            return False
    
    def _process_midi_messages(self, midi: mido.MidiFile, output_file: str, 
                              tempo_ratio: float = 1.0):
        """
        Process MIDI messages and generate audio
        
        Args:
            midi: Loaded MIDI file
            output_file: Output WAV file path
            tempo_ratio: Tempo adjustment ratio
        """
        # Open output file for writing
        with open(output_file, 'wb') as f:
            # Write WAV header
            self._write_wav_header(f)
            
            # Initialize tempo and timing
            tempo = 500000  # Microseconds per beat
            tick_rate = midi.ticks_per_beat
            
            # Process all tracks
            for track in midi.tracks:
                # Reset synthesizer for each track
                # self.synth.reset()  # Don't reset to allow multi-track mixing
                
                # Process messages
                abs_time = 0  # Absolute time in ticks
                for msg in track:
                    abs_time += msg.time
                    
                    # Handle tempo changes
                    if msg.type == 'set_tempo':
                        tempo = msg.tempo
                    
                    # Send message to synthesizer
                    if not msg.is_meta:
                        self._send_midi_message_to_synth(msg)
            
            # Generate audio in blocks
            total_samples = 0
            while True:
                # Check if there are active voices
                active_voices = self.synth.get_active_voice_count()
                if active_voices == 0:
                    # Check if we've generated enough audio
                    # (approximately 1 second of silence at the end)
                    if total_samples > self.sample_rate:
                        break
                
                # Generate audio block
                left_channel, right_channel = self.synth.generate_audio_block(self.block_size)
                
                # Convert to 16-bit integers
                left_int16 = (left_channel * 32767).astype(np.int16)
                right_int16 = (right_channel * 32767).astype(np.int16)
                
                # Interleave channels (LRLRLR...)
                interleaved = np.empty((left_int16.size + right_int16.size,), dtype=np.int16)
                interleaved[0::2] = left_int16
                interleaved[1::2] = right_int16
                
                # Write to file
                f.write(interleaved.tobytes())
                total_samples += self.block_size
                
                # Progress indicator
                if total_samples % (self.sample_rate * 10) == 0:  # Every 10 seconds
                    print(f"Generated {total_samples // self.sample_rate} seconds of audio...")
            
            # Update WAV header with correct file size
            self._update_wav_header(f)
    
    def _send_midi_message_to_synth(self, msg: mido.Message):
        """
        Send a mido MIDI message to the synthesizer
        
        Args:
            msg: MIDI message to send
        """
        if msg.type == 'note_on':
            self.synth.send_midi_message(0x90 + msg.channel, msg.note, msg.velocity)
        elif msg.type == 'note_off':
            self.synth.send_midi_message(0x80 + msg.channel, msg.note, msg.velocity)
        elif msg.type == 'control_change':
            self.synth.send_midi_message(0xB0 + msg.channel, msg.control, msg.value)
        elif msg.type == 'program_change':
            self.synth.send_midi_message(0xC0 + msg.channel, msg.program)
        elif msg.type == 'pitchwheel':
            # Convert 14-bit pitch wheel value to MSB/LSB
            value = msg.pitch + 8192  # mido range is -8192 to 8191, MIDI is 0 to 16383
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            self.synth.send_midi_message(0xE0 + msg.channel, lsb, msb)
        elif msg.type == 'polytouch':
            self.synth.send_midi_message(0xA0 + msg.channel, msg.note, msg.value)
        elif msg.type == 'aftertouch':
            self.synth.send_midi_message(0xD0 + msg.channel, msg.value)
    
    def _write_wav_header(self, f):
        """
        Write initial WAV header (will be updated later)
        """
        # WAV header format
        f.write(b'RIFF')  # Chunk ID
        f.write(b'\\x00\\x00\\x00\\x00')  # Chunk Size (will update later)
        f.write(b'WAVE')  # Format
        f.write(b'fmt ')  # Subchunk1 ID
        f.write(b'\\x10\\x00\\x00\\x00')  # Subchunk1 Size (16 for PCM)
        f.write(b'\\x01\\x00')  # Audio Format (1 = PCM)
        f.write(b'\\x02\\x00')  # Number of Channels (2 = stereo)
        f.write((self.sample_rate).to_bytes(4, byteorder='little'))  # Sample Rate
        f.write((self.sample_rate * 2 * 2).to_bytes(4, byteorder='little'))  # Byte Rate
        f.write(b'\\x04\\x00')  # Block Align
        f.write(b'\\x10\\x00')  # Bits Per Sample (16)
        f.write(b'data')  # Subchunk2 ID
        f.write(b'\\x00\\x00\\x00\\x00')  # Subchunk2 Size (will update later)
    
    def _update_wav_header(self, f):
        """
        Update WAV header with correct file sizes
        """
        # Get file size
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        data_size = file_size - 44  # Subtract header size
        
        # Update RIFF chunk size
        f.seek(4)
        f.write((file_size - 8).to_bytes(4, byteorder='little'))
        
        # Update data chunk size
        f.seek(40)
        f.write((data_size).to_bytes(4, byteorder='little'))
    
    def _convert_wav_to_mp3(self, wav_file: str, mp3_file: str):
        """
        Convert WAV file to MP3 using pydub
        
        Args:
            wav_file: Input WAV file path
            mp3_file: Output MP3 file path
        """
        print(f"Converting {wav_file} to {mp3_file}...")
        try:
            audio = AudioSegment.from_wav(wav_file)
            audio.export(mp3_file, format="mp3", bitrate="320k")
            print("MP3 conversion completed!")
        except Exception as e:
            print(f"Error converting to MP3: {e}")
            # If MP3 conversion fails, keep the WAV file
            print(f"Keeping WAV file: {wav_file}")


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
        'sample_rate': 44100,
        'block_size': 512,
        'max_polyphony': 64,
        'master_volume': 1.0,
        'sf2_files': [],
        'bank_blacklists': {},
        'preset_blacklists': {},
        'bank_mappings': {}
    }
    
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
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
        description="Convert MIDI files to MP3 using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  midi_to_mp3.py input.mid output.mp3
  midi_to_mp3.py -c config.yaml input.mid output.mp3
  midi_to_mp3.py --sf2 soundfont.sf2 input.mid output.mp3
  midi_to_mp3.py --sample-rate 48000 input.mid output.mp3
        """
    )
    
    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input MIDI file(s) to convert'
    )
    
    parser.add_argument(
        'output',
        help='Output file or directory (if multiple inputs)'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Path to YAML configuration file'
    )
    
    parser.add_argument(
        '--sf2',
        action='append',
        dest='sf2_files',
        help='SoundFont (.sf2) file paths (can be used multiple times)'
    )
    
    parser.add_argument(
        '--sample-rate',
        type=int,
        dest='sample_rate',
        help='Audio sample rate in Hz (default: 44100)'
    )
    
    parser.add_argument(
        '--block-size',
        type=int,
        dest='block_size',
        help='Audio processing block size (default: 512)'
    )
    
    parser.add_argument(
        '--polyphony',
        type=int,
        dest='max_polyphony',
        help='Maximum polyphony (default: 64)'
    )
    
    parser.add_argument(
        '--volume',
        type=float,
        dest='master_volume',
        help='Master volume (0.0 to 1.0, default: 1.0)'
    )
    
    parser.add_argument(
        '--tempo',
        type=float,
        default=1.0,
        help='Tempo ratio (default: 1.0 = original tempo)'
    )
    
    return parser.parse_args()


def main():
    """Main function"""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments
    if args.sf2_files:
        config['sf2_files'] = args.sf2_files
    if args.sample_rate:
        config['sample_rate'] = args.sample_rate
    if args.block_size:
        config['block_size'] = args.block_size
    if args.max_polyphony:
        config['max_polyphony'] = args.max_polyphony
    if args.master_volume is not None:
        config['master_volume'] = args.master_volume
    
    # Check if output is a directory
    output_is_dir = os.path.isdir(args.output) or len(args.input_files) > 1
    
    # Validate inputs
    if not args.input_files:
        print("Error: No input files specified")
        return 1
    
    # Check if all input files exist
    for input_file in args.input_files:
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' not found")
            return 1
    
    # Create converter
    converter = MIDIToMP3Converter(config)
    
    # Process files
    success_count = 0
    for input_file in args.input_files:
        # Determine output file name
        if output_is_dir:
            # Generate output file name based on input file
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            if args.output.endswith('.mp3') and len(args.input_files) == 1:
                output_file = args.output
            else:
                output_file = os.path.join(
                    args.output,
                    f"{base_name}.mp3"
                )
        else:
            output_file = args.output
        
        # Convert file
        if converter.convert_midi_to_mp3(input_file, output_file, args.tempo):
            success_count += 1
        else:
            print(f"Failed to convert {input_file}")
    
    print(f"\nConversion completed: {success_count}/{len(args.input_files)} files successful")
    return 0 if success_count == len(args.input_files) else 1


if __name__ == "__main__":
    sys.exit(main())