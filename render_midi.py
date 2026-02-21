#!/usr/bin/env python3
"""
Universal Audio Converter - XG Synthesizer with MIDI & XGML Support

Converts MIDI and XGML (XG Markup Language) files to high-quality audio using XG Synthesizer.
Supports unified audio encoding with keyboard abort capability and advanced XG parameter control.

XGML provides a high-level YAML interface for XG synthesizer control with human-readable
parameter names and semantic abstractions instead of numerical MIDI values.
"""

import os
import sys
import argparse
import yaml
import glob
from typing import List, Optional, Tuple, Union
from pathlib import Path
import threading
import time

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.audio.converter import AudioConverter
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
# Lazy import for OptimizedXGSynthesizer to avoid dependency issues
# from synth.engine.optimized_xg_synthesizer import OptimizedXGSynthesizer
from synth.utils.keyboard import KeyboardListener
from synth.core.config_manager import ConfigManager, get_config_manager


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert MIDI and XGML files to audio using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Supported input formats: MIDI (.mid, .midi), XGML (.xgml, .yaml, .yml)
Supported output formats: ogg, wav, mp3, aac, flac, m4a

XGML (XG Markup Language) provides high-level YAML interface for XG synthesizer control
with human-readable parameter names and semantic abstractions.

Examples:
   render_midi.py input.mid                    # MIDI: Output input.ogg
   render_midi.py input.xgml                   # XGML: Output input.ogg
   render_midi.py input.mid output.wav         # Output: output.wav
   render_midi.py --format mp3 input.xgml      # Output: input.mp3
   render_midi.py --volume 0.8 *.mid *.xgml    # Convert multiple files
   render_midi.py --recursive *.mid output/    # Recurse subdirectories
   render_midi.py --keyboard-abort input.xgml  # XGML with abort control
        """
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI/XGML file(s) or patterns to convert (supports wildcards)")
    parser.add_argument("output", nargs="?", default=None, help="Output file or directory (optional)")
    parser.add_argument("-c", "--config", help="Path to YAML configuration file", default="config.yaml")
    parser.add_argument("--sf2", action="append", dest="sf2_files", 
                       help="SoundFont (.sf2) file paths (can be specified multiple times). "
                            "For advanced options (priority, blacklist, remap), use config.yaml")
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
    parser.add_argument("--architecture", choices=["legacy", "voice"], default="legacy",
                       help="Synthesizer architecture: legacy=existing XG implementation, voice=new Voice-based architecture")
    parser.add_argument("--synth", choices=["modern", "optimized"], default="modern",
                       help="XG synthesizer engine: modern=ModernXGSynthesizer, optimized=OptimizedXGSynthesizer")

    return parser.parse_args()

def expand_file_patterns(patterns: List[str], recursive: bool = False) -> List[str]:
    """Expand file patterns and optionally recurse into subdirectories for MIDI and XGML files."""
    audio_files = []

    for pattern in patterns:
        # Handle both file paths and glob patterns
        if '*' in pattern or '?' in pattern:
            # It's a glob pattern
            if recursive:
                # Use ** for recursive globbing
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

            # Filter for supported audio files (MIDI and XGML)
            for file_path in matched_files:
                if file_path.lower().endswith(('.mid', '.midi', '.xgml', '.yaml', '.yml')):
                    audio_files.append(file_path)
        else:
            # Direct file path
            if Path(pattern).exists():
                ext = pattern.lower().split('.')[-1] if '.' in pattern else ''
                if ext in ['mid', 'midi', 'xgml', 'yaml', 'yml'] or pattern.lower().endswith(('.mid', '.midi', '.xgml', '.yaml', '.yml')):
                    audio_files.append(pattern)
            elif recursive and Path(pattern).is_dir():
                # Directory with recursive flag - find all supported files in subdirs
                for root, dirs, files in os.walk(pattern):
                    for file in files:
                        if file.lower().endswith(('.mid', '.midi', '.xgml', '.yaml', '.yml')):
                            audio_files.append(os.path.join(root, file))

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file in audio_files:
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




def main():
    """Main conversion function."""

    # Parse arguments
    args = parse_arguments()

    # Load unified configuration using ConfigManager
    config_manager = ConfigManager(args.config)
    config_manager.load()
    
    # Get configuration values from ConfigManager
    sample_rate = args.sample_rate or config_manager.get_sample_rate()
    chunk_size_ms = args.chunk_size_ms or (config_manager.get_block_size() / config_manager.get_sample_rate() * 1000)
    max_polyphony = args.max_polyphony or config_manager.get_polyphony()
    master_volume = args.master_volume or config_manager.get_volume()
    
    # Process SoundFont configurations
    # Priority: command line --sf2 > config.yaml soundfonts > config.yaml sf2_path
    soundfont_configs = []
    
    # Add from config.yaml soundfonts (highest priority from config)
    config_soundfonts = config_manager.get_soundfonts()
    for sf_config in config_soundfonts:
        sf_path = sf_config.get('path')
        if sf_path:
            soundfont_configs.append(sf_config)
    
    # Add simple --sf2 paths with default priority (these override config if specified)
    if args.sf2_files:
        for sf2_path in args.sf2_files:
            # Check if this path is already added from config
            if not any(c.get('path') == sf2_path for c in soundfont_configs):
                soundfont_configs.append({
                    'path': sf2_path,
                    'priority': 0,
                    'blacklist': [],
                    'remap': {}
                })
    
    # Fallback to legacy sf2_path if no soundfonts configured
    if not soundfont_configs:
        legacy_path = config_manager.get_sf2_path()
        if legacy_path:
            soundfont_configs.append({
                'path': legacy_path,
                'priority': 0,
                'blacklist': [],
                'remap': {}
            })
    
    # Extract just the paths for synthesizers that need them
    sf2_files = [c['path'] for c in soundfont_configs if c.get('path')]
    
    architecture = args.architecture
    synth_choice = args.synth

    format = args.format
    tempo = args.tempo
    silent = args.silent
    keyboard_abort = args.keyboard_abort
    recursive = args.recursive
    render_log_level = args.render_log_level

    # Expand file patterns to get actual MIDI files
    input_files = expand_file_patterns(args.input_files, recursive)

    if not input_files:
        print("Error: No audio files found matching the specified patterns.")
        return False

    if not silent:
        print(f"Found {len(input_files)} audio file(s) to convert")
        if soundfont_configs:
            print(f"Configuring {len(soundfont_configs)} SoundFont(s)")

    # Determine if we have multiple files
    multiple_files = len(input_files) > 1

    # Initialize synthesizer
    synth_start = time.time()

    if synth_choice == "optimized":
        # Calculate block size for OptimizedXGSynthesizer
        block_size = int(sample_rate * chunk_size_ms / 1000)
        synthesizer = OptimizedXGSynthesizer(
            sample_rate=sample_rate,
            max_polyphony=max_polyphony,
            block_size=block_size,
            sf2_files=sf2_files if sf2_files else None,
            render_log_level=render_log_level,
            architecture=architecture
        )
        if not silent:
            print(f"Using OptimizedXGSynthesizer engine")
    else:  # modern
        synthesizer = ModernXGSynthesizer(
            sample_rate=sample_rate,
            max_channels=max_polyphony,  # ModernXGSynthesizer uses max_channels instead of max_polyphony
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=True,
            device_id=0x10
        )
        
        # Load SoundFonts with their configurations (including blacklist/remap from config)
        for sf_config in soundfont_configs:
            sf_path = sf_config.get('path')
            if sf_path and os.path.exists(sf_path):
                priority = sf_config.get('priority', 0)
                success = synthesizer.load_soundfont(sf_path, priority=priority)
                if success:
                    # Apply blacklisting if specified in config
                    for bank, prog in sf_config.get('blacklist', []):
                        synthesizer.blacklist_program(bank, prog)
                    
                    # Apply remapping if specified in config
                    for (from_bank, from_prog), (to_bank, to_prog) in sf_config.get('remap', {}).items():
                        synthesizer.remap_program(from_bank, from_prog, to_bank, to_prog)
        
        # Apply full configuration from config.yaml
        synthesizer.configure_from_config(config_manager)
        
        if not silent:
            print(f"Using ModernXGSynthesizer engine (refactored modular architecture)")

    # Initialize audio writer
    audio_writer = AudioWriter(sample_rate, chunk_size_ms)

    # Initialize audio converter
    converter = AudioConverter(synthesizer, audio_writer)

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

            if converter.convert_audio_to_audio_buffered(
                input_file=input_file,
                output_file=output_file,
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
