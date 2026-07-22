#!/usr/bin/env python3
"""
Universal Audio Converter - XG Synthesizer with MIDI & XGML Support

Converts MIDI and XGML (XG Markup Language) files to high-quality audio using XG Synthesizer.
Supports unified audio encoding with keyboard abort capability and advanced XG parameter control.

XGML provides a high-level YAML interface for XG synthesizer control with human-readable
parameter names and semantic abstractions instead of numerical MIDI values.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import threading
import time
from pathlib import Path

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.io.audio.converter import AudioConverter
from synth.io.audio.writer import AudioWriter
from synth.primitives.config_manager import ConfigManager
from synth.synthesizers.rendering import ModernXGSynthesizer
from synth.utils.keyboard import KeyboardListener

# Feature defaults. Acoustic behavior is OFF by default per project policy;
# protocol features fall back to the synthesizer's own defaults when not set.
FEATURE_DEFAULTS: dict = {
    "xg": None,  # None => use ModernXGSynthesizer default (True)
    "gs": None,
    "mpe": None,
    "midi2": None,
    "acoustic": False,  # explicitly disabled by default
    "s90": False,
    "gs_mode": None,  # None => synthesizer default ("auto")
    "effects": None,  # None => synthesizer default (enabled)
    "sart2": None,  # None => synthesizer default (enabled)
    # Per-component effect toggles (None = use global effects toggle behavior)
    "reverb": None,
    "chorus": None,
    "variation": None,
    "insertion": None,
    "master_eq": None,
}


class FeatureConfig:
    """Resolved synthesizer feature toggles.

    ``None`` means "use the synthesizer's built-in default" so we only pass
    explicitly-configured values to the constructor.
    """

    def __init__(
        self,
        xg=None,
        gs=None,
        mpe=None,
        midi2=None,
        acoustic=False,
        s90=False,
        gs_mode=None,
        effects=None,
        sart2=None,
        reverb=None,
        chorus=None,
        variation=None,
        insertion=None,
        master_eq=None,
    ):
        self.xg = xg
        self.gs = gs
        self.mpe = mpe
        self.midi2 = midi2
        self.acoustic = acoustic
        self.s90 = s90
        self.gs_mode = gs_mode
        self.effects = effects
        self.sart2 = sart2
        self.reverb = reverb
        self.chorus = chorus
        self.variation = variation
        self.insertion = insertion
        self.master_eq = master_eq

    @classmethod
    def from_dict(cls, data: dict) -> FeatureConfig:
        return cls(
            xg=data.get("xg", FEATURE_DEFAULTS["xg"]),
            gs=data.get("gs", FEATURE_DEFAULTS["gs"]),
            mpe=data.get("mpe", FEATURE_DEFAULTS["mpe"]),
            midi2=data.get("midi2", FEATURE_DEFAULTS["midi2"]),
            acoustic=data.get("acoustic", FEATURE_DEFAULTS["acoustic"]),
            s90=data.get("s90", FEATURE_DEFAULTS["s90"]),
            gs_mode=data.get("gs_mode", FEATURE_DEFAULTS["gs_mode"]),
            effects=data.get("effects", FEATURE_DEFAULTS["effects"]),
            sart2=data.get("sart2", FEATURE_DEFAULTS["sart2"]),
            reverb=data.get("reverb", FEATURE_DEFAULTS["reverb"]),
            chorus=data.get("chorus", FEATURE_DEFAULTS["chorus"]),
            variation=data.get("variation", FEATURE_DEFAULTS["variation"]),
            insertion=data.get("insertion", FEATURE_DEFAULTS["insertion"]),
            master_eq=data.get("master_eq", FEATURE_DEFAULTS["master_eq"]),
        )

    def merge_cli(self, cli: FeatureConfig) -> FeatureConfig:
        """Return a new config with CLI-provided (non-None) values overriding."""
        return FeatureConfig(
            xg=cli.xg if cli.xg is not None else self.xg,
            gs=cli.gs if cli.gs is not None else self.gs,
            mpe=cli.mpe if cli.mpe is not None else self.mpe,
            midi2=cli.midi2 if cli.midi2 is not None else self.midi2,
            acoustic=cli.acoustic if cli.acoustic is not None else self.acoustic,
            s90=cli.s90 if cli.s90 is not None else self.s90,
            gs_mode=cli.gs_mode if cli.gs_mode is not None else self.gs_mode,
            effects=cli.effects if cli.effects is not None else self.effects,
            sart2=cli.sart2 if cli.sart2 is not None else self.sart2,
            reverb=cli.reverb if cli.reverb is not None else self.reverb,
            chorus=cli.chorus if cli.chorus is not None else self.chorus,
            variation=cli.variation if cli.variation is not None else self.variation,
            insertion=cli.insertion if cli.insertion is not None else self.insertion,
            master_eq=cli.master_eq if cli.master_eq is not None else self.master_eq,
        )

    def describe(self) -> str:
        parts = []
        for name, val in (
            ("XG", self.xg),
            ("GS", self.gs),
            ("MPE", self.mpe),
            ("MIDI2", self.midi2),
            ("Acoustic", self.acoustic),
            ("S90", self.s90),
            ("Effects", self.effects),
            ("S.Art2", self.sart2),
            ("Reverb", self.reverb),
            ("Chorus", self.chorus),
            ("Variation", self.variation),
            ("Insertion", self.insertion),
            ("MasterEQ", self.master_eq),
        ):
            parts.append(f"{name}={'on' if val else ('off' if val is False else 'default')}")
        if self.gs_mode is not None:
            parts.append(f"gs_mode={self.gs_mode}")
        return ", ".join(parts)


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
   render_midi.py input.mid                         # Output: input.mp3
   render_midi.py -o output.wav input.mid            # Output: output.wav
   render_midi.py --format ogg input.xgml            # Output: input.ogg
   render_midi.py --volume 0.8 *.mid                 # Convert multiple files
   render_midi.py --recursive *.mid output/           # Recurse subdirectories
   render_midi.py --keyboard-abort input.xgml         # XGML with abort control
   render_midi.py --no-reverb --no-chorus input.mid   # Render without reverb/chorus
   render_midi.py --feature-config features.json *.mid # Load feature config from JSON
""",
    )

    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input MIDI/XGML file(s) or patterns to convert (supports wildcards)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file or directory (optional; if omitted, uses input name with new extension)",
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to YAML configuration file",
        default="config.yaml",
    )
    parser.add_argument(
        "--feature-config",
        default=None,
        help="JSON feature configuration file (CLI flags override file values)",
    )
    parser.add_argument(
        "--sf2",
        nargs="+",
        action="extend",
        dest="sf2_files",
        help="SoundFont (.sf2) file paths. Accepts one or more paths per use, "
        "e.g. --sf2 font1.sf2 font2.sf2 or --sf2 a.sf2 --sf2 b.sf2. "
        "For advanced options (priority, blacklist, remap), use config.yaml",
    )
    parser.add_argument(
        "--sample-rate", type=int, dest="sample_rate", help="Audio sample rate in Hz"
    )
    parser.add_argument(
        "--chunk-size-ms",
        type=float,
        dest="chunk_size_ms",
        help="Audio processing chunk size in milliseconds",
    )
    parser.add_argument("--polyphony", type=int, dest="max_polyphony", help="Maximum polyphony")
    parser.add_argument(
        "--volume", type=float, dest="master_volume", help="Master volume (0.0 to 1.0)"
    )
    parser.add_argument(
        "--tempo", type=float, default=1.0, help="Tempo ratio (default: 1.0 = original tempo)"
    )
    parser.add_argument(
        "--silent", action="store_true", help="Suppress console output during conversion"
    )
    parser.add_argument(
        "--keyboard-abort", action="store_true", help="Enable keyboard abort with SPACE key"
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Recurse into subdirectories"
    )
    parser.add_argument(
        "--format",
        choices=list(AudioWriter.SUPPORTED_FORMATS.keys()),
        default="mp3",
        help="Output audio format",
    )
    parser.add_argument(
        "--synth",
        choices=["modern", "optimized"],
        default="modern",
        help="[DEPRECATED] Both options use ModernXGSynthesizer. "
        "'optimized' prints a migration warning.",
    )

    # --- Feature toggles (CLI) ---
    feat = parser.add_argument_group("synthesizer features")
    feat.add_argument(
        "--xg", dest="xg", action="store_true", default=None, help="Enable XG (default: library default)"
    )
    feat.add_argument("--no-xg", dest="xg", action="store_false", help="Disable XG")
    feat.add_argument(
        "--gs", dest="gs", action="store_true", default=None, help="Enable GS (default: library default)"
    )
    feat.add_argument("--no-gs", dest="gs", action="store_false", help="Disable GS")
    feat.add_argument(
        "--mpe", dest="mpe", action="store_true", default=None, help="Enable MPE (default: library default)"
    )
    feat.add_argument("--no-mpe", dest="mpe", action="store_false", help="Disable MPE")
    feat.add_argument(
        "--midi2", dest="midi2", action="store_true", default=None, help="Enable MIDI 2.0"
    )
    feat.add_argument("--no-midi2", dest="midi2", action="store_false", help="Disable MIDI 2.0 (default)")
    feat.add_argument(
        "--acoustic",
        dest="acoustic",
        action="store_true",
        default=None,
        help="Enable acoustic behavior layer (SuperNATURAL-Acoustic alike)",
    )
    feat.add_argument(
        "--no-acoustic",
        dest="acoustic",
        action="store_false",
        help="Disable acoustic behavior layer (default)",
    )
    feat.add_argument(
        "--s90", dest="s90", action="store_true", default=None, help="Enable S90/S70 compatibility mode"
    )
    feat.add_argument(
        "--gs-mode",
        dest="gs_mode",
        choices=["auto", "xg", "gs"],
        default=None,
        help="GS/XG mode selection (default: auto)",
    )
    feat.add_argument(
        "--effects",
        dest="effects",
        action="store_true",
        default=None,
        help="Enable the XG effects pipeline (reverb, chorus, variation, insertion, master EQ)",
    )
    feat.add_argument(
        "--no-effects",
        dest="effects",
        action="store_false",
        help="Disable the XG effects pipeline (dry mix)",
    )
    feat.add_argument(
        "--sart2",
        dest="sart2",
        action="store_true",
        default=None,
        help="Enable S.Art2 articulation processing",
    )
    feat.add_argument(
        "--no-sart2",
        dest="sart2",
        action="store_false",
        help="Disable S.Art2 articulation processing",
    )

    # Per-component effect pipeline toggles
    for flag, dest, desc in [
        ("--reverb", "reverb", "System reverb"),
        ("--chorus", "chorus", "System chorus"),
        ("--variation", "variation", "Variation effect"),
        ("--insertion", "insertion", "Insertion effects"),
        ("--master-eq", "master_eq", "Master EQ"),
    ]:
        feat.add_argument(flag, dest=dest, action="store_true", default=None, help=f"Enable {desc}")
        feat.add_argument(
            f"--no-{dest.replace('_', '-')}",
            dest=dest,
            action="store_false",
            help=f"Disable {desc}",
        )

    # --- Tracing ---
    trace = parser.add_argument_group("voice tracing")
    trace.add_argument(
        "--trace-voices",
        action="store_true",
        default=False,
        help="Trace program-change messages and print voice assignment details",
    )

    return parser.parse_args()


def trace_voice_assignments(
    synthesizer: ModernXGSynthesizer,
    midi_messages: list,
) -> None:
    """Trace program-change messages and print voice assignment details.

    Scans the message list for bank-select (CC0/CC32) and program-change
    events, feeds them through the synthesizer one-by-one, then queries the
    channel state for the assigned voice name and engine type.

    Args:
        synthesizer: Initialised (reset) synthesizer instance.
        midi_messages: Parsed MIDIMessage list from the file.
    """
    from synth.io.midi import midimessage_to_bytes

    # Per-channel running bank select state
    bank_msb: dict[int, int] = {}
    bank_lsb: dict[int, int] = {}

    # Collect trace entries: (timestamp, channel, bank_msb, bank_lsb, program)
    trace_entries: list[tuple[float, int, int, int, int]] = []

    for msg in midi_messages:
        ch = msg.channel if msg.channel is not None else 0

        if msg.type == "control_change":
            ctrl = msg.controller or 0
            val = msg.value or 0
            if ctrl == 0:
                bank_msb[ch] = val
            elif ctrl == 32:
                bank_lsb[ch] = val

        elif msg.type == "program_change":
            program = msg.program or 0
            msb = bank_msb.get(ch, 0)
            lsb = bank_lsb.get(ch, 0)
            timestamp = msg.timestamp if msg.timestamp is not None else 0.0
            trace_entries.append((timestamp, ch, msb, lsb, program))

    if not trace_entries:
        print("  No program-change messages found.")
        return

    # Replay messages through the synth to resolve voice names.
    # Process incrementally: feed all messages up to each program-change,
    # then query the channel for its resolved voice info.
    synth = synthesizer
    synth.reset()

    msg_idx = 0
    results: list[dict] = []

    for entry_idx, (timestamp, ch, msb, lsb, program) in enumerate(trace_entries):
        # Find the index of the program-change message that produced this entry
        prog_idx = 0
        count = 0
        for i, m in enumerate(midi_messages):
            mc = m.channel if m.channel is not None else 0
            if m.type == "program_change":
                if count == entry_idx:
                    prog_idx = i
                    break
                count += 1

        # Feed all messages up to and including this program-change
        while msg_idx <= prog_idx:
            msg = midi_messages[msg_idx]
            raw = midimessage_to_bytes(msg)
            if raw:
                synth.process_midi_message(raw)
            msg_idx += 1

        # Query channel state after the program change
        ch_obj = synth.channels[ch]
        voice = getattr(ch_obj, "current_voice", None)
        if voice is not None:
            preset_name = voice.get_preset_name()
            engine_type = voice.get_engine_type()
        else:
            preset_name = "(none)"
            engine_type = "?"
        part_mode = getattr(ch_obj, "xg_part_mode", "normal")

        results.append({
            "time": timestamp,
            "part": ch,
            "bank_msb": msb,
            "bank_lsb": lsb,
            "program": program,
            "part_mode": part_mode,
            "engine": engine_type,
            "voice_name": preset_name,
        })

    # Print trace table
    header = (
        f"{'Time':>10s}  {'Part':>4s}  {'MSB':>3s}  {'LSB':>3s}  {'Prog':>4s}  "
        f"{'Mode':<8s}  {'Engine':<6s}  {'Voice Name'}"
    )
    print(header)
    print("-" * len(header))

    for r in results:
        t = r["time"]
        mins = int(t) // 60
        secs = t - mins * 60
        print(
            f"{mins:5d}:{secs:05.2f}  {r['part']:4d}  {r['bank_msb']:3d}  "
            f"{r['bank_lsb']:3d}  {r['program']:4d}  {r['part_mode']:<8s}  "
            f"{r['engine']:<6s}  {r['voice_name']}"
        )


def _load_config_file(path: str | None) -> dict:
    """Load a JSON feature/config file. Returns {} on missing/invalid."""
    if not path:
        return {}
    if not os.path.exists(path):
        print(f"Warning: config file not found: {path}")
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print(f"Warning: config file {path} is not a JSON object; ignoring")
            return {}
        return data
    except Exception as e:
        print(f"Warning: could not parse config file {path}: {e}")
        return {}


def _build_feature_config(args: argparse.Namespace, config_data: dict) -> FeatureConfig:
    """Merge config-file features with CLI flags (CLI wins)."""
    file_cfg = FeatureConfig.from_dict(config_data.get("features", config_data))

    cli = FeatureConfig(
        xg=args.xg,
        gs=args.gs,
        mpe=args.mpe,
        midi2=args.midi2,
        acoustic=args.acoustic,
        s90=args.s90,
        gs_mode=args.gs_mode,
        effects=args.effects,
        sart2=args.sart2,
        reverb=args.reverb,
        chorus=args.chorus,
        variation=args.variation,
        insertion=args.insertion,
        master_eq=args.master_eq,
    )
    return file_cfg.merge_cli(cli)


def expand_file_patterns(patterns: list[str], recursive: bool = False) -> list[str]:
    """Expand file patterns and optionally recurse into subdirectories for MIDI and XGML files."""
    audio_files = []

    for pattern in patterns:
        # Handle both file paths and glob patterns
        if "*" in pattern or "?" in pattern:
            # It's a glob pattern
            if recursive:
                # Use ** for recursive globbing
                pattern_path = Path(pattern)
                if "**" in pattern or pattern_path.parent != Path("."):
                    # Complex pattern, use glob with **
                    if "**" not in pattern:
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
                if file_path.lower().endswith((".mid", ".midi", ".xgml", ".yaml", ".yml")):
                    audio_files.append(file_path)
        else:
            # Direct file path
            if Path(pattern).exists():
                ext = pattern.lower().split(".")[-1] if "." in pattern else ""
                if ext in ["mid", "midi", "xgml", "yaml", "yml"] or pattern.lower().endswith(
                    (".mid", ".midi", ".xgml", ".yaml", ".yml")
                ):
                    audio_files.append(pattern)
            elif recursive and Path(pattern).is_dir():
                # Directory with recursive flag - find all supported files in subdirs
                for root, dirs, files in os.walk(pattern):
                    for file in files:
                        if file.lower().endswith((".mid", ".midi", ".xgml", ".yaml", ".yml")):
                            audio_files.append(os.path.join(root, file))

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file in audio_files:
        if file not in seen:
            seen.add(file)
            unique_files.append(file)

    return unique_files


def get_output_path(
    input_file: str, output: str | None, format: str, multiple_files: bool = False
) -> str:
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
    # (use 'is not None' to avoid falsy-value bugs like --volume 0.0)
    sample_rate = args.sample_rate if args.sample_rate is not None else config_manager.get_sample_rate()
    chunk_size_ms = args.chunk_size_ms if args.chunk_size_ms is not None else (
        config_manager.get_block_size() / config_manager.get_sample_rate() * 1000
    )
    max_polyphony = args.max_polyphony if args.max_polyphony is not None else config_manager.get_polyphony()
    master_volume = args.master_volume if args.master_volume is not None else config_manager.get_volume()

    # Process SoundFont configurations
    # Priority: command line --sf2 > config.yaml soundfonts > config.yaml sf2_path
    soundfont_configs = []

    # Add from config.yaml soundfonts (highest priority from config)
    config_soundfonts = config_manager.get_soundfonts()
    for sf_config in config_soundfonts:
        sf_path = sf_config.get("path")
        if sf_path:
            soundfont_configs.append(sf_config)

    # Add simple --sf2 paths with default priority (these override config if specified)
    if args.sf2_files:
        for sf2_path in args.sf2_files:
            # Check if this path is already added from config
            if not any(c.get("path") == sf2_path for c in soundfont_configs):
                soundfont_configs.append(
                    {"path": sf2_path, "priority": 0, "blacklist": [], "remap": {}}
                )

    # Fallback to legacy sf2_path if no soundfonts configured
    if not soundfont_configs:
        legacy_path = config_manager.get_sf2_path()
        if legacy_path:
            soundfont_configs.append(
                {"path": legacy_path, "priority": 0, "blacklist": [], "remap": {}}
            )

    format = args.format
    tempo = args.tempo
    silent = args.silent
    keyboard_abort = args.keyboard_abort
    recursive = args.recursive

    # Load feature config from JSON file (if provided)
    feature_config_data = _load_config_file(args.feature_config)
    features = _build_feature_config(args, feature_config_data)

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

    if args.synth == "optimized":
        print(
            "Warning: OptimizedXGSynthesizer has been moved to legacy package. "
            "Using ModernXGSynthesizer instead."
        )

    # Build feature-enabled kwargs for the synthesizer
    kwargs: dict = {
        "sample_rate": sample_rate,
        "max_channels": 16,  # Bug fix: 16 MIDI channels, not max_polyphony
        "device_id": 0x10,
    }
    if features.xg is not None:
        kwargs["xg_enabled"] = features.xg
    if features.gs is not None:
        kwargs["gs_enabled"] = features.gs
    if features.mpe is not None:
        kwargs["mpe_enabled"] = features.mpe
    if features.midi2 is not None:
        kwargs["midi_2_enabled"] = features.midi2
    if features.acoustic is not None:
        kwargs["acoustic_behavior"] = features.acoustic
    if features.s90:
        kwargs["s90_mode"] = True
    if features.gs_mode is not None:
        kwargs["gs_mode"] = features.gs_mode

    synthesizer = ModernXGSynthesizer(**kwargs)

    # Load SoundFonts with their configurations (including blacklist/remap from config)
    for sf_config in soundfont_configs:
        sf_path = sf_config.get("path")
        if sf_path and os.path.exists(sf_path):
            priority = sf_config.get("priority", 0)
            success = synthesizer.load_soundfont(sf_path, priority=priority)
            if success:
                # Apply blacklisting if specified in config
                for bank, prog in sf_config.get("blacklist", []):
                    synthesizer.blacklist_program(bank, prog)

                # Apply remapping if specified in config
                for (from_bank, from_prog), (to_bank, to_prog) in sf_config.get(
                    "remap", {}
                ).items():
                    synthesizer.remap_program(from_bank, from_prog, to_bank, to_prog)

    # Apply full configuration from config.yaml
    synthesizer.configure_from_config(config_manager)

    # Apply runtime feature toggles (not exposed as constructor params)
    if features.effects is not None:
        synthesizer.set_effects_enabled(features.effects)
    if features.sart2 is not None:
        synthesizer.set_sart2_enabled(features.sart2)

    # Per-component effect pipeline toggles
    for comp_flag, setter in (
        ("reverb", synthesizer.set_reverb_enabled),
        ("chorus", synthesizer.set_chorus_enabled),
        ("variation", synthesizer.set_variation_enabled),
        ("insertion", synthesizer.set_insertion_enabled),
        ("master_eq", synthesizer.set_master_eq_enabled),
    ):
        val = getattr(features, comp_flag, None)
        if val is not None:
            setter(val)

    if not silent:
        print("Using ModernXGSynthesizer engine (refactored modular architecture)")
        print(f"  Features: {features.describe()}")

    # Initialize audio writer
    audio_writer = AudioWriter(sample_rate, chunk_size_ms)

    # Initialize audio converter
    converter = AudioConverter(synthesizer, audio_writer)

    # Ensure output directory exists if needed
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir() or (not output_path.suffix and multiple_files):
            output_path.mkdir(parents=True, exist_ok=True)

    # Set up timeout mechanism (always active, regardless of keyboard abort)
    abort_event = threading.Event()

    # Initialize keyboard listener for abort if requested
    keyboard_listener = None

    if keyboard_abort:
        keyboard_listener = KeyboardListener()

        def on_key_press(key: str):
            if key.upper() == " ":
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

            # Trace voice assignments if requested
            if args.trace_voices:
                # Parse the file to get MIDI messages
                file_ext = input_file.lower().split(".")[-1]
                if file_ext in ("mid", "midi"):
                    from synth.io.midi import FileParser

                    parser = FileParser()
                    midi_msgs = parser.parse_file(input_file)
                    if midi_msgs:
                        print(f"\n--- Voice Assignments: {input_file} ---")
                        trace_voice_assignments(synthesizer, midi_msgs)
                    else:
                        print(f"  No MIDI messages in {input_file}")
                else:
                    print(f"  Voice tracing only supported for MIDI files (skipped {input_file})")

            if converter.convert_audio_to_audio_buffered(
                input_file=input_file,
                output_file=output_file,
                format=format,
                tempo=tempo,
                volume=master_volume,
                silent=silent,
                abort_event=abort_event,
                render_limit=None,  # Remove the 5 second limit
                timeout_seconds=150.0,
            ):
                success_count += 1
            else:
                if abort_event.is_set():
                    break  # Stop processing if aborted or timed out
                print(f"Failed to convert: {input_file}")

        # Print summary
        if not silent:
            if abort_event and abort_event.is_set():
                print(
                    f"\nConversion aborted or timed out. {success_count}/{len(input_files)} files converted successfully."
                )
            else:
                print(
                    f"\nConversion complete. {success_count}/{len(input_files)} files converted successfully."
                )

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
