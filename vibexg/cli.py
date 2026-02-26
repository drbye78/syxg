"""
Vibexg CLI - Command Line Interface

This module provides the command-line interface for the vibexg
workstation, including argument parsing and the main entry point.
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict

from synth.midi import get_input_names, get_output_names, RTMIDI_AVAILABLE

from .workstation import XGWorkstation
from .types import DEFAULT_SAMPLE_RATE, DEFAULT_BUFFER_SIZE

logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        Parsed argument namespace
    """
    parser = argparse.ArgumentParser(
        description="Vibexg - Vibe XG Real-Time MIDI Workstation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with keyboard input and real-time audio output
  python vibexg.py

  # Run with specific MIDI port
  python vibexg.py --midi-input mido_port:"USB MIDI Device"

  # Run with file output
  python vibexg.py --audio-output file:output.wav

  # Run demo mode
  python vibexg.py --demo scale

  # Run with network MIDI
  python vibexg.py --midi-input network_midi:host=192.168.1.100,port=5004

  # Load configuration from file
  python vibexg.py --config workstation.yaml
        """
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )

    parser.add_argument(
        "--midi-input", "-i",
        action="append",
        dest="midi_inputs",
        metavar="TYPE[:NAME]",
        help="MIDI input interface (keyboard, mido_port:NAME, virtual_port, network_midi, file:PATH, stdin)"
    )

    parser.add_argument(
        "--audio-output", "-o",
        type=str,
        default="sounddevice",
        metavar="TYPE[:PATH]",
        help="Audio output (sounddevice[:DEVICE], file:PATH.wav, none)"
    )

    parser.add_argument(
        "--sample-rate", "-sr",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Audio sample rate (default: {DEFAULT_SAMPLE_RATE})"
    )

    parser.add_argument(
        "--buffer-size", "-bs",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=f"Audio buffer size (default: {DEFAULT_BUFFER_SIZE})"
    )

    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable TUI (text user interface)"
    )

    parser.add_argument(
        "--demo",
        type=str,
        choices=["scale", "chords", "arpeggio"],
        help="Run demo pattern (scale, chords, arpeggio)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List available MIDI ports and exit"
    )

    return parser.parse_args()


def parse_input_spec(spec: str) -> Dict[str, Any]:
    """
    Parse MIDI input specification string.

    Args:
        spec: Input specification string (e.g., "mido_port:USB MIDI")

    Returns:
        Dictionary with type and options
    """
    if ':' in spec:
        parts = spec.split(':', 1)
        input_type = parts[0]
        options = {'name': parts[1]} if len(parts) > 1 else {}

        if input_type == 'file':
            options['file_path'] = parts[1]
        elif input_type == 'mido_port':
            options['port_name'] = parts[1]
        elif input_type == 'network_midi':
            # Parse host and port
            for param in parts[1].split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key == 'host':
                        options['host'] = value
                    elif key == 'port':
                        options['port'] = int(value)

        return {'type': input_type, 'options': options}
    else:
        return {'type': spec}


def parse_output_spec(spec: str) -> Dict[str, Any]:
    """
    Parse audio output specification string.

    Args:
        spec: Output specification string (e.g., "file:output.wav")

    Returns:
        Dictionary with output configuration
    """
    if ':' in spec:
        parts = spec.split(':', 1)
        output_type = parts[0]
        path = parts[1]

        if output_type == 'file':
            return {
                'type': 'file',
                'file_path': path,
                'file_format': Path(path).suffix[1:] or 'wav'
            }
        elif output_type == 'sounddevice':
            return {'type': 'sounddevice', 'device_name': path}
    else:
        return {'type': spec}

    return {'type': 'sounddevice'}


def list_midi_ports():
    """List available MIDI ports."""
    if not RTMIDI_AVAILABLE:
        print("MIDI port support not available - install rtmidi: pip install rtmidi")
        return

    print("\nAvailable MIDI Input Ports:")
    print("-" * 40)
    for port in get_input_names():
        print(f"  - {port}")

    print("\nAvailable MIDI Output Ports:")
    print("-" * 40)
    for port in get_output_names():
        print(f"  - {port}")


def main():
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # List ports if requested
    if args.list_ports:
        list_midi_ports()
        return 0

    # Build configuration
    config = {
        'sample_rate': args.sample_rate,
        'buffer_size': args.buffer_size,
        'config_file': args.config,
        'midi_inputs': [],
        'audio_output': parse_output_spec(args.audio_output)
    }

    # Parse MIDI inputs
    if args.midi_inputs:
        for spec in args.midi_inputs:
            config['midi_inputs'].append(parse_input_spec(spec))

    # Create and run workstation
    try:
        workstation = XGWorkstation(config)

        # Handle signals
        def signal_handler(sig, frame):
            print("\nShutting down...")
            workstation.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run demo if specified
        if args.demo:
            print(f"Running demo: {args.demo}")
            workstation.start()
            workstation.run_demo(args.demo)
            # Wait for demo to complete
            time.sleep(5)
            workstation.stop()
            return 0

        # Run workstation
        if args.no_tui:
            config['enable_tui'] = False
            workstation.run()
        else:
            workstation.run()

        return 0

    except Exception as e:
        logger.error(f"Workstation error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
