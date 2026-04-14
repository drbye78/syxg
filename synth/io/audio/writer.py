from __future__ import annotations

import sys
from fractions import Fraction

import av
import numpy as np


class AudioWriter:
    """Handles writing audio data to various formats using pyav"""

    SUPPORTED_FORMATS = {
        "ogg": "ogg",
        "wav": "wav",
        "mp3": "mp3",
        "aac": "aac",
        "flac": "flac",
        "m4a": "aac",
    }

    def __init__(self, sample_rate: int, chunk_size_ms: float):
        self.sample_rate = sample_rate
        self.chunk_size_ms = chunk_size_ms

    def create_writer(self, output_file: str, format: str):
        """Create AV writer context"""
        try:
            return AvWriter(output_file, format, self.sample_rate)
        except ImportError:
            print("Error: Audio encoding requires 'av' library")
            print("Install with: pip install av")
            sys.exit(1)

    def write_multiple_files(
        self, audio_data: list[np.ndarray], output_files: list[str], formats: list[str]
    ) -> None:
        """
        Write audio to multiple files with exception grouping.

        Python 3.11+: Uses ExceptionGroup to collect all errors

        Args:
            audio_data: List of audio arrays
            output_files: List of output file paths
            formats: List of output formats

        Raises:
            ExceptionGroup: If multiple files fail to write
        """
        errors = []

        for i, (audio, output_file, format) in enumerate(zip(audio_data, output_files, formats, strict=False)):
            try:
                writer = self.create_writer(output_file, format)
                with writer:
                    writer.write(audio)
            except Exception as e:
                # Python 3.11+: Add context
                e.add_note(f"Failed to write file {i + 1}: {output_file}")
                e.add_note(f"Format: {format}")
                e.add_note(f"Audio shape: {audio.shape}")
                errors.append(e)

        # Python 3.11+: Raise exception group if multiple errors
        if len(errors) > 1:
            raise ExceptionGroup("Failed to write multiple audio files", errors)
        elif len(errors) == 1:
            raise errors[0]


class AvWriter:
    """Context manager for audio output using pyav"""

    def __init__(self, output_file: str, format: str, sample_rate: int):
        self.output_file = output_file
        self.format = format
        self.sample_rate = sample_rate
        self.container = None
        self.stream = None

    def __enter__(self):
        self.container = av.open(self.output_file, mode="w", format=self.format)
        self.stream = self.container.add_stream(self._get_codec(self.format), rate=self.sample_rate)
        codec_context = self.stream.codec_context
        codec_context.options = {"strict": "2"}
        # Set channel layout for stereo
        self.stream.layout = "stereo"

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.container and self.stream:
            # Flush the stream to ensure all packets are written
            try:
                for packet in self.stream.encode():
                    self.container.mux(packet)
            except Exception as e:
                print(f"Warning: Error flushing audio stream: {e}")
        if self.container:
            self.container.close()

    def write(self, audio: np.ndarray):
        """Write stereo audio block with multiple AV compatibility approaches"""
        if not self.container or not self.stream:
            return

        # Create audio frame with float format
        rawdata = audio.reshape((1, -1))
        frame = av.AudioFrame.from_ndarray(rawdata, format="flt", layout="stereo")
        frame.sample_rate = self.sample_rate
        frame.time_base = Fraction(1, self.sample_rate)

        # Encode and write the frame
        for packet in self.stream.encode(frame):
            self.container.mux(packet)
            return

        # Create audio frame with float format
        rawdata = audio.reshape((1, -1))
        frame = av.AudioFrame.from_ndarray(rawdata, format="flt", layout="stereo")
        frame.sample_rate = self.sample_rate
        frame.time_base = Fraction(1, self.sample_rate)

        # Encode and write the frame
        packets_written = 0
        for packet in self.stream.encode(frame):
            self.container.mux(packet)
            packets_written += 1

        # Print debug info every 100 writes
        if not hasattr(self, "_write_count"):
            self._write_count = 0
        self._write_count += 1
        if self._write_count % 100 == 0:
            print(
                f"DEBUG: AudioWriter wrote {self._write_count} blocks, packets_written={packets_written}",
                file=sys.stderr,
            )

    def _get_codec(self, format_name: str) -> str:
        """Get the appropriate codec for a given format"""
        codec_mapping = {
            "wav": "pcm_s16le",
            "flac": "flac",
            "mp3": "mp3",
            "aac": "aac",
            "ogg": "vorbis",
            "m4a": "aac",
        }
        return codec_mapping.get(format_name, "vorbis")
