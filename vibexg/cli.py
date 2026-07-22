"""

Vibexg CLI - Command Line Interface

This module provides the command-line interface for the vibexg
workstation, including argument parsing and the main entry point.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from synth.io.midi import RTMIDI_AVAILABLE, get_input_names, get_output_names

from .config import WorkstationConfig
from .types import DEFAULT_BUFFER_SIZE, DEFAULT_SAMPLE_RATE
from .workstation import XGWorkstation

logger = logging.getLogger(__name__)


def _default_log_path() -> Path:
    """Return the default log file path (XDG data home / vibexg / vibexg.log)."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = Path(xdg_data)
    else:
        base = Path.home() / ".local" / "share"
    path = base / "vibexg"
    path.mkdir(parents=True, exist_ok=True)
    return path / "vibexg.log"


def setup_file_logging(level: int, log_path: str | None = None) -> str:
    """Configure root logger to write to a file with rotation.

    Removes all pre-existing handlers from the root logger so nothing
    goes to stderr/console by default.

    Args:
        level: Logging level (e.g. ``logging.DEBUG``).
        log_path: Optional explicit log path. Defaults to XDG data home.

    Returns:
        The resolved log file path.
    """
    path = Path(log_path) if log_path else _default_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    # Remove any default stderr handler (e.g. from basicConfig or library imports)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    return str(path)


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
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Configuration file path (default: config.yaml)",
    )

    parser.add_argument(
        "--midi-input",
        "-i",
        action="append",
        dest="midi_inputs",
        metavar="TYPE[:NAME]",
        help="MIDI input interface (keyboard, mido_port:NAME, virtual_port, "
        "network_midi, file:PATH, stdin)",
    )

    parser.add_argument(
        "--audio-output",
        "-o",
        type=str,
        default="sounddevice",
        metavar="TYPE[:PATH]",
        help="Audio output (sounddevice[:DEVICE], file:PATH.wav, none)",
    )

    parser.add_argument(
        "--sample-rate",
        "-sr",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Audio sample rate (default: {DEFAULT_SAMPLE_RATE})",
    )

    parser.add_argument(
        "--buffer-size",
        "-bs",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=f"Audio buffer size (default: {DEFAULT_BUFFER_SIZE})",
    )

    parser.add_argument("--no-tui", action="store_true", help="Disable TUI (text user interface)")

    parser.add_argument(
        "--demo",
        type=str,
        choices=["scale", "chords", "arpeggio"],
        help="Run demo pattern (scale, chords, arpeggio)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path (default: ~/.local/share/vibexg/vibexg.log)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging to file (sets log level to DEBUG)",
    )

    parser.add_argument(
        "--list-ports", action="store_true", help="List available MIDI ports and exit"
    )

    # =========================================================================
    # Synthesizer feature flags
    # =========================================================================
    sfx = parser.add_argument_group("synthesizer features")

    sfx.add_argument(
        "--soundfont",
        default="tests/ref.sf2",
        help="SoundFont file path for the SF2 engine (default: tests/ref.sf2)",
    )

    # Protocol toggles (store_true/store_false so the default is None = "not set on CLI")
    sfx.add_argument(
        "--xg", dest="xg", action="store_true", default=None, help="Enable XG (default: on)"
    )
    sfx.add_argument("--no-xg", dest="xg", action="store_false", help="Disable XG")
    sfx.add_argument(
        "--gs", dest="gs", action="store_true", default=None, help="Enable GS (default: on)"
    )
    sfx.add_argument("--no-gs", dest="gs", action="store_false", help="Disable GS")
    sfx.add_argument(
        "--mpe", dest="mpe", action="store_true", default=None, help="Enable MPE (default: off)"
    )
    sfx.add_argument("--no-mpe", dest="mpe", action="store_false", help="Disable MPE")
    sfx.add_argument(
        "--midi2", dest="midi2", action="store_true", default=None, help="Enable MIDI 2.0"
    )
    sfx.add_argument(
        "--no-midi2", dest="midi2", action="store_false", help="Disable MIDI 2.0 (default)"
    )
    sfx.add_argument(
        "--acoustic",
        dest="acoustic",
        action="store_true",
        default=None,
        help="Enable acoustic behavior modeling (SuperNATURAL-like)",
    )
    sfx.add_argument(
        "--no-acoustic",
        dest="acoustic",
        action="store_false",
        help="Disable acoustic behavior (default)",
    )
    sfx.add_argument(
        "--s90",
        dest="s90",
        action="store_true",
        default=None,
        help="Enable S90/S70 compatibility mode",
    )
    sfx.add_argument(
        "--gs-mode",
        dest="gs_mode",
        choices=["auto", "xg", "gs"],
        default=None,
        help="GS/XG mode selection (default: auto)",
    )
    sfx.add_argument(
        "--effects",
        dest="effects",
        action="store_true",
        default=None,
        help="Enable effects pipeline",
    )
    sfx.add_argument(
        "--no-effects",
        dest="effects",
        action="store_false",
        help="Disable effects pipeline (dry mix)",
    )
    sfx.add_argument(
        "--sart2",
        dest="sart2",
        action="store_true",
        default=None,
        help="Enable S.Art2 articulation",
    )
    sfx.add_argument(
        "--no-sart2", dest="sart2", action="store_false", help="Disable S.Art2 articulation"
    )

    # Per-component effect toggles
    for flag, dest, desc in [
        ("--reverb", "reverb", "System reverb"),
        ("--chorus", "chorus", "System chorus"),
        ("--variation", "variation", "Variation effect"),
        ("--insertion", "insertion", "Insertion effects"),
        ("--master-eq", "master_eq", "Master EQ"),
    ]:
        sfx.add_argument(flag, dest=dest, action="store_true", default=None, help=f"Enable {desc}")
        sfx.add_argument(
            f"--no-{dest.replace('_', '-')}",
            dest=dest,
            action="store_false",
            help=f"Disable {desc}",
        )

    return parser.parse_args()


def parse_input_spec(spec: str) -> dict[str, Any]:
    """
    Parse MIDI input specification string.

    Args:
        spec: Input specification string (e.g., "mido_port:USB MIDI")

    Returns:
        Dictionary with type and options
    """
    if ":" in spec:
        parts = spec.split(":", 1)
        input_type = parts[0]
        options = {"name": parts[1]} if len(parts) > 1 else {}

        if input_type == "file":
            options["file_path"] = parts[1]
        elif input_type == "mido_port":
            options["port_name"] = parts[1]
        elif input_type == "network_midi":
            # Parse host and port
            for param in parts[1].split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key == "host":
                        options["host"] = value
                    elif key == "port":
                        options["port"] = int(value)

        return {"type": input_type, "options": options}
    else:
        return {"type": spec}


def parse_output_spec(spec: str) -> dict[str, Any]:
    """
    Parse audio output specification string.

    Args:
        spec: Output specification string (e.g., "file:output.wav")

    Returns:
        Dictionary with output configuration
    """
    if ":" in spec:
        parts = spec.split(":", 1)
        output_type = parts[0]
        path = parts[1]

        if output_type == "file":
            return {
                "type": "file",
                "file_path": path,
                "file_format": Path(path).suffix[1:] or "wav",
            }
        elif output_type == "sounddevice":
            return {"type": "sounddevice", "device_name": path}
        else:
            logger.warning(
                "Unrecognized audio output type '%s', falling back to sounddevice",
                output_type,
            )
            return {"type": "sounddevice"}
    else:
        spec_type = spec
        if spec_type not in ("sounddevice", "file", "none"):
            logger.warning(
                "Unrecognized audio output type '%s', falling back to sounddevice",
                spec_type,
            )
            return {"type": "sounddevice"}
        return {"type": spec_type}


def list_midi_ports():
    """List available MIDI ports to stdout."""
    if not RTMIDI_AVAILABLE:
        logger.warning(
            "MIDI port support not available - install python-rtmidi: pip install python-rtmidi"
        )
        return

    print("\nAvailable MIDI Input Ports:")
    print("-" * 40)
    for port in get_input_names():
        print(f"  - {port}")

    print("\nAvailable MIDI Output Ports:")
    print("-" * 40)
    for port in get_output_names():
        print(f"  - {port}")


def _redirect_stderr(log_path: str | None = None) -> None:
    """Redirect stderr (fd 2) to a file (or /dev/null) to suppress C-level terminal output.

    ALSA's ``snd_pcm_recover()`` calls ``fprintf(stderr, ...)`` from C code for
    every buffer underrun. These bypass Python's logging entirely and corrupt
    the TUI display. The only reliable fix is to redirect file descriptor 2
    at the OS level — every ``fprintf(stderr, ...)`` from any C library
    (ALSA, PortAudio, JACK) goes to the redirect target.

    When a *log_path* is given stderr is sent there (so Textual's internal
    logging is captured for debugging). Otherwise it goes to ``/dev/null``.

    Python logging via ``RotatingFileHandler`` writes to a file fd (not stderr)
    so it is unaffected. The TUI uses stdout (fd 1), also unaffected.
    """
    try:
        if log_path:
            target = os.open(log_path, os.O_WRONLY | os.O_APPEND)
        else:
            target = os.open(os.devnull, os.O_WRONLY)
        os.dup2(target, 2)  # replace fd 2 with target
        os.close(target)
    except Exception:
        logger.debug("Could not redirect stderr (non-fatal)")


def main():
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()

    # Configure file logging (replaces default stderr output)
    level = logging.DEBUG if args.verbose else logging.INFO
    log_path = setup_file_logging(level, args.log_file)
    logger.info("Logging to %s", log_path)

    # Redirect stderr to the log file (catches ALSA/PortAudio C-level fprintf
    # AND captures Textual's internal logging for debugging)
    _redirect_stderr(log_path)

    # List ports if requested
    if args.list_ports:
        list_midi_ports()
        return 0

    # Build configuration using typed config
    config = WorkstationConfig.from_cli_args(args)

    # Create and run workstation
    try:
        workstation = XGWorkstation(config)

        # Handle signals
        def signal_handler(sig, frame):
            sig_name = signal.Signals(sig).name
            logger.warning("Received signal %s — shutting down", sig_name)
            workstation.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run demo if specified
        if args.demo:
            logger.info("Running demo: %s", args.demo)
            workstation.start()
            workstation.run_demo(args.demo)
            # Wait for demo thread to finish (generous timeout)
            demo_thread = workstation.demo_mode.thread
            if demo_thread and demo_thread.is_alive():
                demo_thread.join(timeout=30)
            workstation.stop()
            return 0

        # Run workstation
        workstation.run()

        return 0

    except Exception as e:
        logger.error(f"Workstation error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
