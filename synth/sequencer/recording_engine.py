"""
Recording Engine - Real-time MIDI and Audio Recording

Provides comprehensive recording capabilities for the XG sequencer,
including MIDI sequence recording, audio recording, and overdub features.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np


class RecordingEngine:
    """
    Real-time recording engine for MIDI and audio.

    Provides professional recording capabilities with punch-in/punch-out,
    overdubbing, and real-time monitoring for the XG workstation.
    """

    def __init__(self, sample_rate: int = 44100, max_tracks: int = 64):
        """
        Initialize recording engine.

        Args:
            sample_rate: Audio sample rate
            max_tracks: Maximum number of tracks
        """
        self.sample_rate = sample_rate
        self.max_tracks = max_tracks

        # Recording state
        self.is_recording = False
        self.is_playing = False
        self.current_position = 0
        self.recording_start_time = 0

        # Track management
        self.tracks: dict[int, dict[str, Any]] = {}
        self.active_record_tracks: set = set()

        # Recording parameters
        self.ppq = 960  # Pulses per quarter note
        self.tempo = 120.0
        self.time_signature = (4, 4)

        # Punch-in/punch-out
        self.punch_in_enabled = False
        self.punch_out_enabled = False
        self.punch_in_position = 0
        self.punch_out_position = 0

        # Overdub settings
        self.overdub_enabled = False
        self.replace_enabled = True

        # Monitoring
        self.input_monitoring = True
        self.record_monitoring = True

        # Audio recording buffers
        self.audio_buffers: dict[int, list[np.ndarray]] = {}
        self.current_audio_buffer: np.ndarray | None = None

        # Threading
        self.lock = threading.RLock()
        self.recording_thread: threading.Thread | None = None

    def start_recording(
        self, track_number: int, record_type: str = "midi", start_position: int = 0
    ) -> bool:
        """
        Start recording on a specific track.

        Args:
            track_number: Track to record on
            record_type: 'midi' or 'audio'
            start_position: Starting position in ticks

        Returns:
            Success status
        """
        with self.lock:
            if track_number >= self.max_tracks:
                return False

            if track_number not in self.tracks:
                self.tracks[track_number] = {
                    "type": record_type,
                    "events": [],
                    "audio_data": [],
                    "start_position": start_position,
                    "length": 0,
                }

            self.active_record_tracks.add(track_number)
            self.is_recording = True
            self.recording_start_time = time.time()
            self.current_position = start_position

            # Initialize audio buffer if recording audio
            if record_type == "audio":
                self.current_audio_buffer = np.zeros(
                    (self.sample_rate * 60, 2), dtype=np.float32
                )  # 60 seconds max
                self.audio_buffers[track_number] = []

            print(f"🎙️  Started recording on track {track_number} ({record_type})")
            return True

    def stop_recording(self) -> bool:
        """
        Stop recording on all tracks.

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording:
                return False

            self.is_recording = False
            self.active_record_tracks.clear()

            # Process recorded data
            self._process_recorded_data()

            print("⏹️  Recording stopped")
            return True

    def record_midi_event(self, track_number: int, event_data: dict[str, Any]) -> bool:
        """
        Record a MIDI event on a track.

        Args:
            event_data: MIDI event data

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording or track_number not in self.active_record_tracks:
                return False

            if self.tracks[track_number]["type"] != "midi":
                return False

            # Add timestamp
            event_with_time = event_data.copy()
            event_with_time["timestamp"] = time.time() - self.recording_start_time
            event_with_time["tick"] = self.current_position

            self.tracks[track_number]["events"].append(event_with_time)

            # Update track length
            self.tracks[track_number]["length"] = max(
                self.tracks[track_number]["length"], self.current_position
            )

            return True

    def record_audio_block(
        self, track_number: int, audio_block: np.ndarray, block_position: int
    ) -> bool:
        """
        Record an audio block on a track.

        Args:
            track_number: Track number
            audio_block: Audio data block
            block_position: Position in samples

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording or track_number not in self.active_record_tracks:
                return False

            if self.tracks[track_number]["type"] != "audio":
                return False

            # Store audio block
            if track_number not in self.audio_buffers:
                self.audio_buffers[track_number] = []

            self.audio_buffers[track_number].append((block_position, audio_block.copy()))

            # Update track length
            end_position = block_position + len(audio_block)
            self.tracks[track_number]["length"] = max(
                self.tracks[track_number]["length"], end_position
            )

            return True

    def _process_recorded_data(self):
        """Process and finalize recorded data."""
        for track_num in self.tracks:
            track = self.tracks[track_num]

            if track["type"] == "midi":
                # Sort MIDI events by tick
                track["events"].sort(key=lambda x: x["tick"])

                # Quantize if enabled
                if hasattr(self, "quantize_enabled") and self.quantize_enabled:
                    self._quantize_track(track_num)

            elif track["type"] == "audio":
                # Concatenate audio blocks
                if track_num in self.audio_buffers:
                    self._concatenate_audio_blocks(track_num)

    def _quantize_track(self, track_number: int, grid_size: int = 480):  # 1/8 note
        """Quantize MIDI events on a track."""
        track = self.tracks[track_number]

        for event in track["events"]:
            if "tick" in event:
                quantized_tick = round(event["tick"] / grid_size) * grid_size
                event["tick"] = quantized_tick

        # Re-sort after quantization
        track["events"].sort(key=lambda x: x["tick"])

    def _concatenate_audio_blocks(self, track_number: int):
        """Concatenate recorded audio blocks into continuous audio."""
        if track_number not in self.audio_buffers:
            return

        blocks = self.audio_buffers[track_number]
        if not blocks:
            return

        # Sort blocks by position
        blocks.sort(key=lambda x: x[0])

        # Find total length
        max_end = 0
        for pos, block in blocks:
            max_end = max(max_end, pos + len(block))

        # Create output buffer
        output_buffer = np.zeros((max_end, 2), dtype=np.float32)

        # Mix blocks into output buffer
        for pos, block in blocks:
            end_pos = pos + len(block)
            if end_pos <= len(output_buffer):
                if self.replace_enabled:
                    output_buffer[pos:end_pos] = block
                else:
                    # Overdub (mix)
                    output_buffer[pos:end_pos] += block

        # Store in track
        self.tracks[track_number]["audio_data"] = output_buffer

        # Clean up
        del self.audio_buffers[track_number]

    def enable_punch_in_out(self, punch_in: int, punch_out: int) -> bool:
        """
        Enable punch-in/punch-out recording.

        Args:
            punch_in: Punch-in position in ticks
            punch_out: Punch-out position in ticks

        Returns:
            Success status
        """
        with self.lock:
            self.punch_in_enabled = True
            self.punch_out_enabled = True
            self.punch_in_position = punch_in
            self.punch_out_position = punch_out
            return True

    def disable_punch_in_out(self) -> bool:
        """
        Disable punch-in/punch-out recording.

        Returns:
            Success status
        """
        with self.lock:
            self.punch_in_enabled = False
            self.punch_out_enabled = False
            return True

    def set_overdub_mode(self, enabled: bool) -> bool:
        """
        Set overdub mode.

        Args:
            enabled: True for overdub, False for replace

        Returns:
            Success status
        """
        with self.lock:
            self.overdub_enabled = enabled
            self.replace_enabled = not enabled
            return True

    def get_recording_status(self) -> dict[str, Any]:
        """
        Get current recording status.

        Returns:
            Recording status information
        """
        with self.lock:
            return {
                "is_recording": self.is_recording,
                "is_playing": self.is_playing,
                "active_tracks": list(self.active_record_tracks),
                "current_position": self.current_position,
                "punch_in_enabled": self.punch_in_enabled,
                "punch_out_enabled": self.punch_out_enabled,
                "punch_in_position": self.punch_in_position,
                "punch_out_position": self.punch_out_position,
                "overdub_enabled": self.overdub_enabled,
                "replace_enabled": self.replace_enabled,
                "tempo": self.tempo,
                "time_signature": self.time_signature,
            }

    def get_track_data(self, track_number: int) -> dict[str, Any] | None:
        """
        Get recorded data for a track.

        Args:
            track_number: Track number

        Returns:
            Track data or None if track doesn't exist
        """
        with self.lock:
            return self.tracks.get(track_number)

    def clear_track(self, track_number: int) -> bool:
        """
        Clear all recorded data from a track.

        Args:
            track_number: Track number

        Returns:
            Success status
        """
        with self.lock:
            if track_number in self.tracks:
                self.tracks[track_number] = {
                    "type": self.tracks[track_number]["type"],
                    "events": [],
                    "audio_data": [],
                    "start_position": 0,
                    "length": 0,
                }
                return True
            return False

    def export_track(self, track_number: int, filename: str, format_type: str = "midi") -> bool:
        """
        Export track data to file.

        Args:
            track_number: Track to export
            filename: Output filename
            format_type: Export format ('midi' or 'wav')

        Returns:
            Success status
        """
        with self.lock:
            if track_number not in self.tracks:
                return False

            track = self.tracks[track_number]

            if format_type.lower() == "midi":
                return self._export_midi(track, filename)
            elif format_type.lower() == "wav":
                return self._export_wav(track, filename)
            else:
                return False

    def _export_midi(self, track: dict[str, Any], filename: str) -> bool:
        """Export MIDI track to file."""
        from ..io.midi.file_writer import MIDIFileWriter

        try:
            events = track.get("events", [])
            if not events:
                return False

            writer = MIDIFileWriter(format=0, division=self.ppq)

            tempo_us = int(60000000 / self.tempo)
            writer.set_tempo(tempo_us)

            midi_messages = []
            for event in events:
                event_type = event.get("type")
                if event_type in ["note_on", "note_off"]:
                    msg_type = event_type
                elif event_type == "note":
                    msg_type = "note_on" if event.get("velocity", 0) > 0 else "note_off"
                else:
                    continue

                from ..io.midi.message import MIDIMessage

                msg = MIDIMessage(
                    type=msg_type,
                    channel=event.get("channel", 0),
                    note=event.get("note", 60),
                    velocity=event.get("velocity", 64),
                    timestamp=event.get("timestamp", 0.0),
                )
                midi_messages.append(msg)

            if midi_messages:
                writer.add_track(midi_messages)
                writer.save(filename)
                print(f"✓ Exported MIDI track to {filename}")
                return True

            return False
        except Exception as e:
            print(f"Error exporting MIDI: {e}")
            return False

    def _export_wav(self, track: dict[str, Any], filename: str) -> bool:
        """Export audio track to WAV file."""
        try:
            import wave

            import numpy as np

            audio_data = track.get("audio_data")
            if audio_data is None or len(audio_data) == 0:
                audio_buffers = self.audio_buffers.get(track.get("track_number", 0), [])
                if not audio_buffers:
                    return False
                # Concatenate audio blocks
                audio_data = np.concatenate([block for _, block in sorted(audio_buffers)])

            if audio_data is None or len(audio_data) == 0:
                return False

            # Ensure stereo
            if len(audio_data.shape) == 1:
                audio_data = np.column_stack([audio_data, audio_data])

            # Convert float32 to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)

            with wave.open(filename, "wb") as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())

            print(f"✓ Exported audio track to {filename}")
            return True
        except Exception as e:
            print(f"Error exporting WAV: {e}")
            return False

    def import_track(self, track_number: int, filename: str) -> bool:
        """
        Import track data from file.

        Args:
            track_number: Track to import to
            filename: Input filename

        Returns:
            Success status
        """
        with self.lock:
            if track_number >= self.max_tracks:
                return False

            # Determine file type from extension
            ext = filename.lower().split(".")[-1]

            if ext == "mid" or ext == "midi":
                return self._import_midi(track_number, filename)
            elif ext == "wav":
                return self._import_wav(track_number, filename)
            else:
                return False

    def _import_midi(self, track_number: int, filename: str) -> bool:
        """Import MIDI track from file."""
        try:
            from ..io.midi.file_handler import MIDIFileHandler

            handler = MIDIFileHandler()
            midi_data = handler.load_midi_file(filename)

            if not midi_data:
                return False

            tracks = midi_data.get("tracks", [])
            if not tracks:
                return False

            # Get first track's events
            track_events = tracks[0]

            # Extract tempo and time signature if available
            for event in track_events:
                if event.get("type") == "tempo_change":
                    self.tempo = event.get("tempo", 120.0)
                elif event.get("type") == "time_signature":
                    self.time_signature = (
                        event.get("numerator", 4),
                        event.get("denominator", 4),
                    )

            # Convert to internal format
            events = []
            for event in track_events:
                event_type = event.get("type")
                if event_type in [
                    "note_on",
                    "note_off",
                    "control_change",
                    "program_change",
                    "pitch_bend",
                ]:
                    tick = event.get("ticks", 0)
                    seconds = tick / self.ppq * (60.0 / self.tempo)

                    internal_event = {
                        "type": event_type,
                        "channel": event.get("channel", 0),
                        "timestamp": seconds,
                        "tick": tick,
                    }

                    if event_type in ["note_on", "note_off"]:
                        internal_event["note"] = event.get("note", 60)
                        internal_event["velocity"] = event.get("velocity", 64)
                    elif event_type == "control_change":
                        internal_event["controller"] = event.get("controller", 0)
                        internal_event["value"] = event.get("value", 0)
                    elif event_type == "program_change":
                        internal_event["program"] = event.get("program", 0)
                    elif event_type == "pitch_bend":
                        internal_event["bend_value"] = event.get("value", 8192)

                    events.append(internal_event)

            # Calculate track length
            max_tick = max((e.get("tick", 0) for e in events), default=0)

            # Create or update track
            self.tracks[track_number] = {
                "type": "midi",
                "events": events,
                "audio_data": [],
                "start_position": 0,
                "length": max_tick,
            }

            print(f"✓ Imported MIDI track from {filename} ({len(events)} events)")
            return True
        except Exception as e:
            print(f"Error importing MIDI: {e}")
            return False

    def _import_wav(self, track_number: int, filename: str) -> bool:
        """Import audio track from WAV file."""
        try:
            import wave

            import numpy as np

            with wave.open(filename, "rb") as wav_file:
                num_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                num_frames = wav_file.getnframes()

                audio_bytes = wav_file.readframes(num_frames)

                # Convert to numpy
                if sample_width == 2:
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                elif sample_width == 4:
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int32)
                else:
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int8)

                if num_channels > 1:
                    audio_int16 = audio_int16.reshape(-1, num_channels)

                # Convert to float32
                audio_float = audio_int16.astype(np.float32) / 32768.0

                # Mix to stereo if needed
                if num_channels == 1:
                    audio_float = np.column_stack([audio_float, audio_float])
                elif num_channels > 2:
                    # Mix down to stereo
                    audio_float = np.mean(audio_float[:, :2], axis=1, keepdims=True)
                    audio_float = np.column_stack([audio_float[:, 0], audio_float[:, 0]])

            # Create or update track
            self.tracks[track_number] = {
                "type": "audio",
                "events": [],
                "audio_data": audio_float,
                "start_position": 0,
                "length": len(audio_float),
            }

            self.sample_rate = sample_rate
            print(f"✓ Imported audio track from {filename} ({len(audio_float)} samples)")
            return True
        except Exception as e:
            print(f"Error importing WAV: {e}")
            return False

    def set_quantize_settings(self, enabled: bool, grid_size: int = 480) -> bool:
        """
        Set quantization settings.

        Args:
            enabled: Enable/disable quantization
            grid_size: Quantization grid size in ticks

        Returns:
            Success status
        """
        with self.lock:
            self.quantize_enabled = enabled
            self.quantize_grid = grid_size
            return True

    def get_recording_stats(self) -> dict[str, Any]:
        """
        Get recording statistics.

        Returns:
            Recording statistics
        """
        with self.lock:
            total_events = sum(len(track.get("events", [])) for track in self.tracks.values())
            total_tracks = len(self.tracks)

            return {
                "total_tracks": total_tracks,
                "total_events": total_events,
                "recording_time": time.time() - self.recording_start_time
                if self.is_recording
                else 0,
                "average_events_per_track": total_events / max(1, total_tracks),
            }
