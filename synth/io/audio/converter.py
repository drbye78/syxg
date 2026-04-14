"""
Audio Converter Engine

Core conversion logic for MIDI and XGML to audio conversion.
Separated from frontend CLI interface for better modularity.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import numpy as np

logger = logging.getLogger(__name__)

from synth.io.audio.writer import AudioWriter
from synth.synthesizers.rendering import ModernXGSynthesizer
from synth.io.midi import FileParser, MIDIMessage
from synth.utils.progress import ProgressReporter
from synth.xgml import XGMLParser, XGMLToMIDITranslator


class AudioConverter:
    """Core audio conversion engine for MIDI and XGML files."""

    def __init__(self, synthesizer: ModernXGSynthesizer, audio_writer: AudioWriter):
        """
        Initialize the audio converter.

        Args:
            synthesizer: The XG synthesizer instance
            audio_writer: The audio writer instance
        """
        self.synthesizer = synthesizer
        self.audio_writer = audio_writer

    def parse_audio_file(self, file_path: str) -> tuple[list | None, float | None]:
        """
        Parse audio file (MIDI or XGML) and return MIDI messages and duration.

        Args:
            file_path: Path to audio file (MIDI or XGML)

        Returns:
            Tuple of (midi_messages, duration_seconds) or (None, None) on error
        """
        file_ext = file_path.lower().split(".")[-1]

        if file_ext in ["mid", "midi"]:
            # Parse as MIDI file
            try:
                parser = FileParser()
                all_messages = parser.parse_file(file_path)

                # Calculate duration from message timestamps
                if all_messages:
                    duration = (
                        max(msg.timestamp for msg in all_messages) + 1.0
                    )  # Add 1 second padding
                else:
                    duration = 10.0  # Default duration

                return all_messages, duration
            except Exception as e:
                print(f"Error parsing MIDI file {file_path}: {e}")
                return None, None

        elif file_ext in ["xgml", "yaml", "yml"] or file_path.lower().endswith(
            (".xgml", ".yaml", ".yml")
        ):
            # Parse as XGML file
            try:
                # Parse XGML
                parser = XGMLParser()
                document = parser.parse_file(file_path)

                if document is None:
                    if not parser.has_errors():
                        print(f"Warning: No XGML content found in {file_path}")
                    else:
                        print(f"Error parsing XGML {file_path}:")
                        for error in parser.get_errors():
                            print(f"  - {error}")
                    return None, None

                if parser.has_warnings():
                    print(f"XGML warnings in {file_path}:")
                    for warning in parser.get_warnings():
                        print(f"  - {warning}")

                # Translate to MIDI
                translator = XGMLToMIDITranslator()
                midi_messages = translator.translate_document(document)

                if translator.has_errors():
                    print(f"XGML translation errors in {file_path}:")
                    for error in translator.get_errors():
                        print(f"  - {error}")
                    return None, None

                if translator.has_warnings():
                    print(f"XGML translation warnings in {file_path}:")
                    for warning in translator.get_warnings():
                        print(f"  - {warning}")

                # Calculate duration from sequences
                duration = 0.0
                sequences = document.get_section("sequences")
                if sequences:
                    for seq_name, seq_data in sequences.items():
                        # Check for explicit duration or calculate from events
                        if "duration" in seq_data:
                            duration = max(duration, seq_data["duration"])
                        else:
                            # Calculate from last event time
                            for track in seq_data.get("tracks", []):
                                for event in track.get("events", []):
                                    if "at" in event:
                                        event_time = event["at"].get("time", 0)
                                        if isinstance(event_time, (int, float)):
                                            duration = max(duration, float(event_time))

                # Minimum duration fallback
                if duration == 0.0:
                    duration = 10.0  # Default 10 seconds

                return midi_messages, duration

            except Exception as e:
                print(f"Error processing XGML file {file_path}: {e}")
                return None, None

        else:
            print(f"Unsupported file format: {file_path}")
            return None, None

    def convert_audio_to_audio_buffered(
        self,
        input_file: str,
        output_file: str,
        format: str,
        tempo: float = 1.0,
        volume: float = 0.8,
        silent: bool = False,
        render_limit: float | None = None,
        abort_event: threading.Event | None = None,
        timeout_seconds: float | None = None,
    ) -> bool:
        """
        Convert a single audio file (MIDI or XGML) to audio using buffered processing mode.

        Args:
            input_file: Input audio file path
            output_file: Output audio file path
            format: Output audio format
            tempo: Tempo ratio
            volume: Master volume
            silent: Suppress console output
            render_limit: Maximum render duration
            abort_event: Threading event for abort signal
            timeout_seconds: Timeout in seconds

        Returns:
            True if conversion successful, False otherwise
        """
        import sys

        try:
            if not silent:
                print(f"Converting {input_file} -> {output_file}")

            # Parse input file (MIDI or XGML)
            logger.debug(f"Parsing audio file {input_file}")
            midi_messages, duration = self.parse_audio_file(input_file)
            print(
                f"DEBUG: Parsed {len(midi_messages) if midi_messages else 0} messages, duration={duration}",
                file=sys.stderr,
            )

            if midi_messages is None or duration is None:
                return False

            file_type = (
                "XGML" if input_file.lower().endswith((".xgml", ".yaml", ".yml")) else "MIDI"
            )
            if not silent:
                print(
                    f"{file_type} parsed: {len(midi_messages)} MIDI messages, duration: {duration:.2f} seconds"
                )

            self.synthesizer.reset()

            # Apply tempo scaling if needed (only affects MIDI timing)
            if tempo != 1.0 and file_type == "MIDI":
                # Scale timestamps for tempo adjustment
                scaled_messages = []
                for msg in midi_messages:
                    scaled_msg = MIDIMessage(
                        type=msg.type,
                        channel=msg.channel,
                        data=msg.data.copy(),
                        timestamp=msg.timestamp / tempo,
                    )
                    scaled_messages.append(scaled_msg)
                midi_messages = scaled_messages

            self.synthesizer.send_midi_message_block(midi_messages)

            # For XGML files, we don't adjust start time as sequences are already properly timed
            if file_type == "MIDI":
                # Find first note-on time for MIDI files
                first_note_time = None
                for msg in midi_messages:
                    if msg.type == "note_on" and msg.timestamp is not None:
                        if first_note_time is None or msg.timestamp < first_note_time:
                            first_note_time = msg.timestamp
                        break
                if first_note_time:
                    self.synthesizer.set_current_time(first_note_time / tempo)

            # Create audio writer
            writer = self.audio_writer.create_writer(output_file, format)

            # Set synthesizer volume
            self.synthesizer.set_master_volume(volume)

            # Initialize progress reporter
            adjusted_duration = (
                duration / tempo
                if file_type == "MIDI" and tempo != 1.0
                else (duration if not render_limit else min(duration, render_limit))
            )
            progress_reporter = ProgressReporter(silent=silent)
            progress_reporter.start(adjusted_duration)
            abort_at = time.time() + timeout_seconds if timeout_seconds else None

            # Buffer processing
            with writer:
                while self.synthesizer.get_current_time() < adjusted_duration:
                    # Check for abort signal
                    if abort_event and abort_event.is_set():
                        if not silent:
                            print("\nConversion aborted by user.")
                        return False

                    # Check for timeout
                    if abort_at and time.time() > abort_at:
                        if not silent:
                            print(f"\nConversion timed out after {timeout_seconds} seconds.")
                        return True

                    out_buffer = self.synthesizer.generate_audio_block()
                    writer.write(out_buffer)

                    # Update progress
                    progress_reporter.progress(self.synthesizer.get_current_time())

            # Finalize audio logging after conversion is complete
            self.synthesizer.finalize_audio_logging()

            if not silent:
                print(f"Conversion complete: {output_file}")

            return True

        except Exception as e:
            print(f"Error converting {input_file}: {e}")
            return False
