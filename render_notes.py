#!/usr/bin/env python3
"""
Render MIDI notes to an audio file using the XG Synthesizer.

Renders a sequence of notes for a given instrument to an audio file with
configurable:
- SoundFont file (default: tests/ref.sf2)
- MIDI bank / program (default: 0 / 0)
- Number of notes (default: 10)
- Optional XGML-based configuration
- Synthesizer feature flags: XG, GS, MPE, MIDI 2.0, S90 mode, and the
  acoustic behavior layer (SuperNATURAL-Acoustic alike cross-note modeling)

Feature flags can be set on the command line or via a JSON config file
(``--config path.json``). Command-line flags override the config file.
By default the acoustic behavior layer is DISABLED; all other protocol
features (XG, GS, MPE) keep their library defaults unless overridden.

Each note has:
- ``note-on-duration`` seconds between note-on and note-off
- ``note-off-duration`` seconds of silence after note-off before the next note

Notes are rendered sequentially with random note numbers and velocities.
"""

import argparse
import json
import os
import random
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from synth.io.audio.writer import AudioWriter
from synth.io.midi import MIDIMessage, midimessage_to_bytes
from synth.synthesizers.rendering import ModernXGSynthesizer
from synth.xgml import XGMLConfigParser, XGMLMIDIBridge

DEFAULT_SOUNDFONT = "tests/ref.sf2"
DEFAULT_MIDI_BANK = 0
DEFAULT_MIDI_PROGRAM = 0
DEFAULT_NUM_NOTES = 10

# Feature defaults. Acoustic behavior is OFF by default per project policy;
# protocol features fall back to the synthesizer's own defaults when not set.
FEATURE_DEFAULTS = {
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
    def from_dict(cls, data: dict) -> "FeatureConfig":
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

    def merge_cli(self, cli: "FeatureConfig") -> "FeatureConfig":
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


class NoteRenderer:
    """Renders MIDI notes to audio using the XG Synthesizer."""

    def __init__(
        self,
        soundfont: str = DEFAULT_SOUNDFONT,
        sample_rate: int = 44100,
        features: FeatureConfig | None = None,
        seed: int | None = None,
    ):
        self.sample_rate = sample_rate
        features = features or FeatureConfig()

        # Seed the RNG. When None, use an arbitrary seed so each run differs;
        # when an int is given, the sequence is reproducible.
        if seed is None:
            seed = random.randrange(2**31 - 1)
        self.seed = seed
        random.seed(seed)

        # Only pass explicitly-configured feature flags; leave the rest at the
        # synthesizer's built-in defaults by not specifying them.
        kwargs: dict = {
            "sample_rate": sample_rate,
            "max_channels": 16,
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

        self.synth = ModernXGSynthesizer(**kwargs)

        # Runtime toggles not exposed as constructor params.
        if features.effects is not None:
            self.synth.set_effects_enabled(features.effects)
        if features.sart2 is not None:
            self.synth.set_sart2_enabled(features.sart2)

        # Per-component effect pipeline toggles.
        # When a per-component flag is set (True/False), it overrides the
        # effect component regardless of the global --effects toggle.
        for comp_flag, setter in (
            ("reverb", self.synth.set_reverb_enabled),
            ("chorus", self.synth.set_chorus_enabled),
            ("variation", self.synth.set_variation_enabled),
            ("insertion", self.synth.set_insertion_enabled),
            ("master_eq", self.synth.set_master_eq_enabled),
        ):
            val = getattr(features, comp_flag, None)
            if val is not None:
                setter(val)

        if os.path.exists(soundfont):
            self.synth.load_soundfont(soundfont, priority=0)
        else:
            print(f"Warning: SoundFont not found: {soundfont}")

    def apply_xgml_config(self, xgml_path: str) -> bool:
        """Apply XGML configuration to synthesizer."""
        if not os.path.exists(xgml_path):
            print(f"Warning: XGML config file not found: {xgml_path}")
            return False

        try:
            parser = XGMLConfigParser(validate_schema=False)
            config = parser.parse_file(xgml_path)

            if config is None:
                print(f"Warning: Failed to parse XGML file: {xgml_path}, skipping config")
                if parser.has_errors():
                    for error in parser.get_errors():
                        print(f"  - {error}")
                return False

            bridge = XGMLMIDIBridge()
            messages = bridge.translate(config)

            if bridge.has_errors():
                for error in bridge.get_errors():
                    print(f"  - {error}")

            applied_count = 0
            for msg in messages:
                msg.timestamp = 0.0  # apply immediately

                msg_bytes = midimessage_to_bytes(msg)
                if msg_bytes:
                    try:
                        self.synth.process_midi_message(msg_bytes)
                        applied_count += 1
                    except Exception:
                        pass

            print(f"Applied XGML configuration from: {xgml_path} ({applied_count} messages)")
            return applied_count > 0

        except Exception as e:
            print(f"Warning: Could not apply XGML config: {e}")
            return False

    def set_instrument(self, bank: int, program: int):
        """Set MIDI bank and program for the instrument."""
        channel = 0
        self.synth.set_channel_program(channel, bank, program)
        print(f"Set instrument: bank={bank}, program={program}")

    def render_notes_streaming(
        self,
        output_path: str,
        num_notes: int,
        note_on_duration: float = 3.0,
        note_off_duration: float = 2.0,
        note_range: tuple[int, int] = (36, 96),
        velocity_range: tuple[int, int] = (60, 127),
    ) -> bool:
        """
        Render multiple notes sequentially to audio in streaming mode.

        Audio is written to the output file as it's generated, without storing
        the entire audio in RAM.

        Args:
            output_path: Output file path
            num_notes: Number of notes to render
            note_on_duration: Duration of note-on state (seconds)
            note_off_duration: Duration after note-off before next note (seconds)
            note_range: Tuple of (min_note, max_note) MIDI note numbers
            velocity_range: Tuple of (min_velocity, max_velocity)

        Returns:
            True if successful
        """
        note_on_samples = int(note_on_duration * self.sample_rate)
        note_off_samples = int(note_off_duration * self.sample_rate)
        samples_per_note = note_on_samples + note_off_samples
        total_samples = num_notes * samples_per_note

        print(f"Rendering {num_notes} notes (streaming mode)...")
        print(
            f"  Note duration: {note_on_duration}s on + {note_off_duration}s off = {note_on_duration + note_off_duration}s per note"
        )
        print(f"  Total duration: {(num_notes * (note_on_duration + note_off_duration)):.1f}s")
        print(
            f"  Note range: {note_range[0]}-{note_range[1]}, Velocity range: {velocity_range[0]}-{velocity_range[1]}"
        )

        channel = 0
        messages = []
        current_time = 0.0

        for note_idx in range(num_notes):
            note = random.randint(note_range[0], note_range[1])
            velocity = random.randint(velocity_range[0], velocity_range[1])

            print(f"  Note {note_idx + 1}/{num_notes}: MIDI note {note}, velocity {velocity}")

            note_on_msg = MIDIMessage(
                type="note_on",
                channel=channel,
                note=note,
                velocity=velocity,
                timestamp=current_time,
            )
            messages.append(note_on_msg)

            note_off_msg = MIDIMessage(
                type="note_off",
                channel=channel,
                note=note,
                velocity=64,
                timestamp=current_time + note_on_duration,
            )
            messages.append(note_off_msg)

            current_time += note_on_duration + note_off_duration

        self.synth.send_midi_message_block(messages)
        self.synth.set_current_time(0.0)

        audio_writer = AudioWriter(self.sample_rate, 10.0)

        try:
            with audio_writer.create_writer(output_path, "mp3") as writer:
                generated_samples = 0
                while generated_samples < total_samples:
                    block = self.synth.generate_audio_block()
                    block_samples = min(len(block), total_samples - generated_samples)
                    writer.write(block[:block_samples])
                    generated_samples += block_samples

            print("Rendering complete!")
            print(f"Output written to: {output_path}")
            return True

        except Exception as e:
            print(f"Error writing audio: {e}")
            return False

    def render_to_mp3(
        self,
        output_path: str,
        num_notes: int,
        bank: int = DEFAULT_MIDI_BANK,
        program: int = DEFAULT_MIDI_PROGRAM,
        xgml_config: str | None = None,
        note_on_duration: float = 3.0,
        note_off_duration: float = 2.0,
        note_range: tuple[int, int] = (36, 96),
        velocity_range: tuple[int, int] = (60, 127),
    ) -> bool:
        """Render notes to MP3 file using streaming mode."""

        self.set_instrument(bank, program)

        if xgml_config:
            self.apply_xgml_config(xgml_config)

        return self.render_notes_streaming(
            output_path=output_path,
            num_notes=num_notes,
            note_on_duration=note_on_duration,
            note_off_duration=note_off_duration,
            note_range=note_range,
            velocity_range=velocity_range,
        )


def _load_config_file(path: str) -> dict:
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


def main():
    parser = argparse.ArgumentParser(
        description="Render notes to an audio file using the XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
    python render_notes.py output.mp3
    python render_notes.py output.mp3 --soundfont tests/ref.sf2 --bank 0 --program 0 --num-notes 10
    python render_notes.py output.mp3 --acoustic            # enable behavior modeling
    python render_notes.py output.mp3 --no-xg --no-gs        # disable protocol layers
    python render_notes.py output.mp3 --config my_config.json
    python render_notes.py output.mp3 --num-notes 5 --note-on-duration 2.0 --note-off-duration 1.0

Config file (JSON) example:
    {
      "soundfont": "tests/ref.sf2",
      "bank": 0,
      "program": 0,
      "num_notes": 10,
      "note_on_duration": 3.0,
      "note_off_duration": 2.0,
      "features": {
        "xg": true, "gs": true, "mpe": true,
        "midi2": false, "acoustic": true, "s90": false, "gs_mode": "auto",
        "reverb": true, "chorus": false, "variation": true,
        "insertion": false, "master_eq": true
      }
    }
""",
    )

    parser.add_argument("output", help="Output audio file path")
    parser.add_argument(
        "--soundfont",
        default=DEFAULT_SOUNDFONT,
        help=f"SoundFont file path (default: {DEFAULT_SOUNDFONT})",
    )
    parser.add_argument(
        "--bank",
        type=int,
        default=DEFAULT_MIDI_BANK,
        help=f"MIDI bank number (default: {DEFAULT_MIDI_BANK})",
    )
    parser.add_argument(
        "--program",
        type=int,
        default=DEFAULT_MIDI_PROGRAM,
        help=f"MIDI program number (default: {DEFAULT_MIDI_PROGRAM})",
    )
    parser.add_argument(
        "--num-notes",
        type=int,
        default=DEFAULT_NUM_NOTES,
        help=f"Number of notes to render (default: {DEFAULT_NUM_NOTES})",
    )
    parser.add_argument(
        "--xgml-config",
        help="XGML configuration file to apply before rendering",
    )
    parser.add_argument(
        "--note-on-duration",
        type=float,
        default=3.0,
        help="Duration of note-on state in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--note-off-duration",
        type=float,
        default=2.0,
        help="Duration after note-off before next note in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--note-range",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=None,
        help="MIDI note range inclusive, e.g. --note-range 48 72 (default: 36 96)",
    )
    parser.add_argument(
        "--velocity-range",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=None,
        help="MIDI velocity range inclusive, e.g. --velocity-range 80 127 (default: 60 127)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible note/velocity generation (default: arbitrary per run)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Audio sample rate in Hz (default: 44100)",
    )
    parser.add_argument(
        "--config",
        help="JSON config file with render/feature settings (CLI flags override it)",
    )

    # --- Feature toggles (CLI) ---
    # Store True/False/None: None means "not specified on CLI".
    feat = parser.add_argument_group("synthesizer features")
    feat.add_argument("--xg", dest="xg", action="store_true", default=None, help="Enable XG (default: library default)")
    feat.add_argument("--no-xg", dest="xg", action="store_false", help="Disable XG")
    feat.add_argument("--gs", dest="gs", action="store_true", default=None, help="Enable GS (default: library default)")
    feat.add_argument("--no-gs", dest="gs", action="store_false", help="Disable GS")
    feat.add_argument("--mpe", dest="mpe", action="store_true", default=None, help="Enable MPE (default: library default)")
    feat.add_argument("--no-mpe", dest="mpe", action="store_false", help="Disable MPE")
    feat.add_argument("--midi2", dest="midi2", action="store_true", default=None, help="Enable MIDI 2.0")
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
    feat.add_argument("--s90", dest="s90", action="store_true", default=None, help="Enable S90/S70 compatibility mode")
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

    # --- Per-component effect pipeline toggles ---
    # When None, each component inherits the global --effects/--no-effects setting.
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

    args = parser.parse_args()

    # Load config file first; CLI flags override.
    config_data = _load_config_file(args.config)
    # Config file may also carry top-level render settings.
    soundfont = config_data.get("soundfont", args.soundfont)
    bank = config_data.get("bank", args.bank)
    program = config_data.get("program", args.program)
    num_notes = config_data.get("num_notes", args.num_notes)
    note_on_duration = config_data.get("note_on_duration", args.note_on_duration)
    note_off_duration = config_data.get("note_off_duration", args.note_off_duration)
    xgml_config = args.xgml_config or config_data.get("xgml_config")

    # Note/velocity ranges: config file value, overridden by CLI when given.
    cfg_note_range = tuple(config_data["note_range"]) if "note_range" in config_data else None
    cfg_velocity_range = (
        tuple(config_data["velocity_range"]) if "velocity_range" in config_data else None
    )
    cfg_seed = config_data.get("seed", None)

    note_range = args.note_range if args.note_range is not None else cfg_note_range
    velocity_range = args.velocity_range if args.velocity_range is not None else cfg_velocity_range
    seed = args.seed if args.seed is not None else cfg_seed

    features = _build_feature_config(args, config_data)

    if not os.path.exists(soundfont):
        print(f"Error: SoundFont file not found: {soundfont}")
        return 1

    print("Initializing Note Renderer...")
    print(f"  SoundFont: {soundfont}")
    print(f"  Bank: {bank}, Program: {program}")
    print(f"  Notes to render: {num_notes}")
    print(f"  Note on duration: {note_on_duration}s")
    print(f"  Note off duration: {note_off_duration}s")
    print(
        f"  Note range: {note_range[0]}-{note_range[1]}, Velocity range: {velocity_range[0]}-{velocity_range[1]}"
    )
    print(f"  Seed: {seed} (arbitrary)" if seed is None else f"  Seed: {seed} (reproducible)")
    print(f"  Features: {features.describe()}")
    if xgml_config:
        print(f"  XGML config: {xgml_config}")
    print()

    renderer = NoteRenderer(
        soundfont=soundfont, sample_rate=args.sample_rate, features=features, seed=seed
    )

    success = renderer.render_to_mp3(
        output_path=args.output,
        num_notes=num_notes,
        bank=bank,
        program=program,
        xgml_config=xgml_config,
        note_on_duration=note_on_duration,
        note_off_duration=note_off_duration,
        note_range=note_range,
        velocity_range=velocity_range,
    )

    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
