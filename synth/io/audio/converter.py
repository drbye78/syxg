"""

Audio Converter Engine

Core conversion logic for MIDI and XGML to audio conversion.
Separated from frontend CLI interface for better modularity.
"""

from __future__ import annotations

import logging
import threading
import time


from synth.io.audio.writer import AudioWriter
from synth.io.midi import FileParser, MIDIMessage
from synth.synthesizers.rendering import ModernXGSynthesizer
from synth.utils.progress import ProgressReporter
from synth.xgml import XGMLConfigParser, XGMLMIDIBridge

logger = logging.getLogger(__name__)


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

    def parse_audio_file(
        self, file_path: str, skip_silence: bool = False
    ) -> tuple[list | None, float | None]:
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
                    timestamps = [msg.timestamp or 0.0 for msg in all_messages]
                    min_ts = min(timestamps)
                    # Normalize all timestamps to start at zero
                    if min_ts > 0:
                        for msg in all_messages:
                            if msg.timestamp is not None:
                                msg.timestamp -= min_ts
                    # Fast-forward through silent leading/trailing messages
                    if skip_silence:
                        all_messages, _ = _fast_forward_silence_events(all_messages)
                    timestamps = [msg.timestamp or 0.0 for msg in all_messages]
                    duration = max(timestamps) + 1.0
                    # Add 1 second padding for release tails
                else:
                    duration = 10.0  # Default duration

                return all_messages, duration
            except Exception as e:
                logger.error(f"Error parsing MIDI file {file_path}: {e}")
                return None, None

        elif file_ext in ["xgml", "yaml", "yml"] or file_path.lower().endswith(
            (".xgml", ".yaml", ".yml")
        ):
            # Parse as XGML file — use new typed parser + MIDI bridge
            try:
                parser = XGMLConfigParser()
                config = parser.parse_file(file_path)

                if config is None:
                    if parser.has_errors():
                        logger.error(f"Error parsing XGML {file_path}:")
                        for error in parser.get_errors():
                            logger.error(f"  - {error}")
                    else:
                        logger.warning(f"No XGML content found in {file_path}")
                    return None, None

                if parser.has_warnings():
                    logger.warning(f"XGML warnings in {file_path}:")
                    for warning in parser.get_warnings():
                        logger.warning(f"  - {warning}")

                # Translate to MIDI
                bridge = XGMLMIDIBridge()
                midi_messages = bridge.translate(config)

                if bridge.has_errors():
                    logger.error(f"XGML translation errors in {file_path}:")
                    for error in bridge.get_errors():
                        logger.error(f"  - {error}")
                    return None, None

                if bridge.has_warnings():
                    logger.warning(f"XGML translation warnings in {file_path}:")
                    for warning in bridge.get_warnings():
                        logger.warning(f"  - {warning}")

                # Calculate duration from sequences (convert beats → seconds)
                duration = 0.0
                if config.sequences:
                    for seq in config.sequences.values():
                        tempo = seq.tempo or 120
                        sec_per_beat = 60.0 / tempo
                        for track in seq.tracks:
                            for event in track.events:
                                duration = max(duration, event.at * sec_per_beat)

                # Minimum duration fallback
                if duration == 0.0:
                    duration = 10.0

                return midi_messages, duration

            except Exception as e:
                logger.error(f"Error processing XGML file {file_path}: {e}")
                return None, None

        else:
            logger.info(f"Unsupported file format: {file_path}")
            return None, None

    def _fast_forward_silence_events(
        self, messages: list
    ) -> tuple[list, float]:
        """Compact inaudible leading/trailing messages to track boundaries.

        Leading: fast-forwards to the first note-on event.  All
        messages before it (meta, sysex, program changes, CCs) are
        still processed but compacted to time 0 so they do not add
        dead air.

        Trailing: only meta events and sysex are compacted after the
        last audible event.  CC changes, program changes, and pitch
        bend resets keep their timing — they can affect the release
        tail (e.g. sustain pedal off, reverb send changes).
        """
        if not messages:
            return messages, 0.0

        # ── leading silence → first note_on ──────────────────────
        first_idx = next(
            (i for i, m in enumerate(messages) if m.type == "note_on"), None
        )
        if first_idx is None:
            return messages, 0.0
        first_ts = messages[first_idx].timestamp or 0.0
        for i in range(first_idx):
            if messages[i].timestamp is not None:
                messages[i].timestamp = 0.0

        # ── trailing silence → meta-only compaction ──────────────
        _AUDIBLE = {
            "note_on", "note_off", "program_change", "control_change",
            "pitch_bend", "channel_pressure", "poly_pressure",
        }
        last_idx = next(
            (i for i in range(len(messages) - 1, -1, -1)
             if messages[i].type in _AUDIBLE), first_idx
        )
        last_ts = messages[last_idx].timestamp or 0.0

        # Compress only meta/sysex events after the last audible event.
        # CCs, program changes, pitch bends keep their original timing
        # because they may affect the release tail or subsequent state.
        _META_ONLY = {"meta", "sysex"}
        for i in range(last_idx + 1, len(messages)):
            if messages[i].timestamp is not None and messages[i].type in _META_ONLY:
                messages[i].timestamp = last_ts

        # Shift everything so the first note-on is at time 0
        if first_ts > 0:
            for msg in messages[first_idx:]:
                if msg.timestamp is not None:
                    msg.timestamp -= first_ts

        return messages, first_ts

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

        try:
            if not silent:
                logger.info(f"Converting {input_file} -> {output_file}")

            # Parse input file (MIDI or XGML)
            logger.debug(f"Parsing audio file {input_file}")
            midi_messages, duration = self.parse_audio_file(input_file)
            logger.info(
                f"DEBUG: Parsed {len(midi_messages) if midi_messages else 0} messages, duration={duration}",
            )

            if midi_messages is None or duration is None:
                return False

            file_type = (
                "XGML" if input_file.lower().endswith((".xgml", ".yaml", ".yml")) else "MIDI"
            )
            if not silent:
                logger.info(
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
                    self.synthesizer.set_current_time(first_note_time)

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
                            logger.info("\nConversion aborted by user.")
                        return False

                    # Check for timeout
                    if abort_at and time.time() > abort_at:
                        if not silent:
                            logger.info(f"\nConversion timed out after {timeout_seconds} seconds.")
                        return True

                    out_buffer = self.synthesizer.generate_audio_block()
                    writer.write(out_buffer)

                    # Update progress
                    progress_reporter.progress(self.synthesizer.get_current_time())

            # Finalize audio logging after conversion is complete
            self.synthesizer.finalize_audio_logging()

            if not silent:
                logger.info(f"Conversion complete: {output_file}")

            return True

        except Exception as e:
            logger.error(f"Error converting {input_file}: {e}")
            return False
