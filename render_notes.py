#!/usr/bin/env python3
"""
Test script for rendering notes to MP3 using XG Synthesizer.

Renders several notes of a given instrument to an MP3 file with configurable:
- SoundFont file (default: tests/ref.sf2)
- MIDI bank (default: 0)
- MIDI program number (default: 0)
- Number of notes (default: 10)
- Optional XGML-based configuration

Each note has:
- 3 seconds between note on and note off
- 2 seconds after note off before next note starts

Notes are rendered sequentially with random note numbers and velocities.
"""

import argparse
import os
import random
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
from synth.midi import MIDIMessage
from synth.xgml import XGMLParser, XGMLToMIDITranslator


DEFAULT_SOUNDFONT = "tests/ref.sf2"
DEFAULT_MIDI_BANK = 0
DEFAULT_MIDI_PROGRAM = 0
DEFAULT_NUM_NOTES = 10


class NoteRenderer:
    """Renders MIDI notes to audio using XG Synthesizer."""

    def __init__(
        self,
        soundfont: str = DEFAULT_SOUNDFONT,
        sample_rate: int = 44100,
    ):
        self.sample_rate = sample_rate

        self.synth = ModernXGSynthesizer(
            sample_rate=sample_rate,
            max_channels=16,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=False,
            device_id=0x10,
        )

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
            parser = XGMLParser()
            document = parser.parse_file(xgml_path)

            if document is None:
                print(f"Warning: Failed to parse XGML file: {xgml_path}, skipping config")
                return False

            translator = XGMLToMIDITranslator()
            try:
                messages = translator.translate_document(document)
            except AttributeError as e:
                if "time" in str(e):
                    print(f"Warning: XGML translator has compatibility issue, attempting fallback")
                    messages = []
                    try:
                        messages.extend(translator._translate_basic_messages(document))
                        messages.extend(translator._translate_effects(document))
                        messages.extend(translator._translate_system_exclusive(document))
                    except Exception:
                        pass

            if translator.has_errors():
                for error in translator.get_errors():
                    print(f"  - {error}")

            applied_count = 0
            for msg in messages:
                if hasattr(msg, "timestamp"):
                    msg.timestamp = 0.0

                if hasattr(msg, "to_bytes"):
                    msg_bytes = msg.to_bytes()
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
        )


def main():
    parser = argparse.ArgumentParser(
        description="Render notes to MP3 using XG Synthesizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Examples:
    python render_notes.py output.mp3
    python render_notes.py output.mp3 --soundfont tests/ref.sf2 --bank 0 --program 0 --num-notes 10
    python render_notes.py output.mp3 --xgml-config my_config.xgml
    python render_notes.py output.mp3 --num-notes 5 --note-on-duration 2.0 --note-off-duration 1.0
""",
    )

    parser.add_argument("output", help="Output MP3 file path")
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
        "--sample-rate",
        type=int,
        default=44100,
        help="Audio sample rate in Hz (default: 44100)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.soundfont):
        print(f"Error: SoundFont file not found: {args.soundfont}")
        return 1

    print(f"Initializing Note Renderer...")
    print(f"  SoundFont: {args.soundfont}")
    print(f"  Bank: {args.bank}, Program: {args.program}")
    print(f"  Notes to render: {args.num_notes}")
    print(f"  Note on duration: {args.note_on_duration}s")
    print(f"  Note off duration: {args.note_off_duration}s")
    if args.xgml_config:
        print(f"  XGML config: {args.xgml_config}")
    print()

    renderer = NoteRenderer(soundfont=args.soundfont, sample_rate=args.sample_rate)

    success = renderer.render_to_mp3(
        output_path=args.output,
        num_notes=args.num_notes,
        bank=args.bank,
        program=args.program,
        xgml_config=args.xgml_config,
        note_on_duration=args.note_on_duration,
        note_off_duration=args.note_off_duration,
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
