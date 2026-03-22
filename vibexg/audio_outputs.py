"""
Vibexg Audio Outputs - Audio output engine implementations

This module provides audio output engines including:
- Real-time audio output via sounddevice
- File-based audio rendering with proper finalization
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from synth.audio.writer import AudioWriter
from synth.core.synthesizer import Synthesizer

from .types import AudioOutputConfig

logger = logging.getLogger(__name__)


class AudioOutputEngine:
    """
    Base class for audio output engines.

    All audio output engines inherit from this class and implement
    the _start_output() and _stop_output() methods.
    """

    def __init__(self, config: AudioOutputConfig, synthesizer: Synthesizer):
        """
        Initialize the audio output engine.

        Args:
            config: Configuration for this audio output
            synthesizer: Synthesizer instance to render audio from
        """
        self.config = config
        self.synthesizer = synthesizer
        self.running = False

    def start(self):
        """Start audio output."""
        self.running = True
        self._start_output()

    def stop(self):
        """Stop audio output."""
        self.running = False
        self._stop_output()

    def _start_output(self):
        """Override to start specific output."""
        pass

    def _stop_output(self):
        """Override to stop specific output."""
        pass


class SoundDeviceOutput(AudioOutputEngine):
    """
    Real-time audio output via sounddevice.

    Provides low-latency real-time audio output using the sounddevice
    library, which wraps PortAudio.
    """

    def __init__(self, config: AudioOutputConfig, synthesizer: Synthesizer):
        super().__init__(config, synthesizer)
        self.stream = None

    def _start_output(self):
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not available for audio output")
            return

        try:
            device = self.config.device_name or None
            self.stream = sd.OutputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.buffer_size,
                channels=self.config.channels,
                dtype="float32",
                callback=self._audio_callback,
                device=device,
            )
            self.stream.start()
            logger.info(f"SoundDevice audio output started: {device or 'default'}")
        except Exception as e:
            logger.error(f"Failed to start SoundDevice output: {e}")

    def _stop_output(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Audio callback for real-time output.

        Args:
            outdata: Output buffer to fill with audio samples
            frames: Number of frames to render
            time_info: Timing information
            status: Stream status flags
        """
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Render audio block
        self.synthesizer.render_block(outdata)


class FileAudioOutput(AudioOutputEngine):
    """
    Audio output to file with proper finalization.

    Renders audio to a file format (WAV, FLAC, etc.) with proper
    header finalization when stopped.
    """

    def __init__(self, config: AudioOutputConfig, synthesizer: Synthesizer):
        super().__init__(config, synthesizer)
        self.audio_writer: AudioWriter | None = None
        self.av_writer = None
        self.total_samples = 0
        self.samples_buffer: list[np.ndarray] = []

    def _start_output(self):
        try:
            # Ensure output directory exists
            output_path = Path(self.config.file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.audio_writer = AudioWriter(
                sample_rate=self.config.sample_rate,
                chunk_size_ms=self.config.buffer_size / self.config.sample_rate * 1000,
            )
            # Create the actual writer
            self.av_writer = self.audio_writer.create_writer(
                self.config.file_path, self.config.file_format
            )
            self.av_writer.__enter__()
            self.total_samples = 0
            self.samples_buffer = []
            logger.info(f"File audio output started: {self.config.file_path}")
        except Exception as e:
            logger.error(f"Failed to start file audio output: {e}")

    def _stop_output(self):
        if self.av_writer:
            # Write all buffered samples
            for samples in self.samples_buffer:
                self.av_writer.write(samples)

            # Finalize and close file
            try:
                self.av_writer.__exit__(None, None, None)
                logger.info(
                    f"Audio file written: {self.config.file_path} ({self.total_samples} samples)"
                )
            except Exception as e:
                logger.error(f"Failed to finalize audio file: {e}")
            finally:
                self.av_writer = None
                self.samples_buffer = []

    def render_block(self, audio_data: np.ndarray):
        """
        Render audio block to file.

        Args:
            audio_data: Numpy array of audio samples to write
        """
        if self.av_writer is not None:
            # Buffer the data for final write
            self.samples_buffer.append(audio_data.copy())
            self.total_samples += len(audio_data)
