"""
Vibexg Audio Outputs - Audio output engine implementations

This module provides audio output engines including:
- Real-time audio output via sounddevice
- File-based audio rendering with proper finalization
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from synth.io.audio.writer import AudioWriter
from synth.synthesizers.realtime import Synthesizer

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
    header finalization when stopped. Runs a background rendering
    thread that continuously pulls audio from the synthesizer.
    """

    def __init__(self, config: AudioOutputConfig, synthesizer: Synthesizer):
        super().__init__(config, synthesizer)
        self.audio_writer: AudioWriter | None = None
        self.av_writer = None
        self.total_samples = 0
        self._render_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

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
            self._stop_event.clear()
            self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self._render_thread.start()
            logger.info(f"File audio output started: {self.config.file_path}")
        except Exception as e:
            logger.error(f"Failed to start file audio output: {e}")

    def _stop_output(self):
        self._stop_event.set()
        if self._render_thread and self._render_thread.is_alive():
            self._render_thread.join(timeout=2.0)
        if self.av_writer:
            try:
                self.av_writer.__exit__(None, None, None)
                logger.info(
                    f"Audio file written: {self.config.file_path} ({self.total_samples} samples)"
                )
            except Exception as e:
                logger.error(f"Failed to finalize audio file: {e}")
            finally:
                self.av_writer = None

    def _render_loop(self):
        """Background thread that renders audio blocks to file."""
        block_size = self.config.buffer_size
        buffer = np.zeros((block_size, 2), dtype=np.float32)
        seconds_per_block = block_size / self.config.sample_rate

        while not self._stop_event.is_set():
            try:
                buffer.fill(0.0)
                self.synthesizer.render_block(buffer)
                if self.av_writer is not None:
                    self.av_writer.write(buffer)
                    self.total_samples += block_size
            except Exception as e:
                logger.error(f"File render error: {e}")
            self._stop_event.wait(seconds_per_block)
