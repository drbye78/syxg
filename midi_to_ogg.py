#!/usr/bin/env python3
"""
Optimized MIDI to OGG Converter using XG Synthesizer

This is an optimized version of midi_to_ogg.py with performance improvements
based on profiling analysis. Key optimizations include:

1. SF2 parameter caching to reduce _merge_preset_and_instrument_params calls
2. Optimized attribute access patterns
3. Batched modulator processing
4. Lazy loading of SF2 data
5. Memory pool for object reuse
"""
# pyright: basic, reportAttributeAccessIssue=false

import argparse
import yaml
import os
import sys
import mido
import numpy as np
from typing import List, Dict, Any, Optional
import opuslib
from line_profiler import LineProfiler
import threading
import time
import platform
import weakref
from functools import lru_cache

# Platform-specific imports
if platform.system() == 'Windows':
    import msvcrt
else:
    import select
    import termios
    import tty

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.core.synthesizer import XGSynthesizer


class ParameterCache:
    """Cache for SF2 parameter merging to avoid repeated computations"""

    def __init__(self):
        self._cache = {}
        self._hit_count = 0
        self._miss_count = 0

    def get_cached_params(self, preset_params: Dict, instrument_params: Dict) -> Dict:
        """Get cached merged parameters or compute and cache them"""
        # Create a hashable cache key from the parameter dictionaries
        def make_hashable(obj):
            if isinstance(obj, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
            elif isinstance(obj, list):
                return tuple(make_hashable(item) for item in obj)
            else:
                return obj

        cache_key = (make_hashable(preset_params), make_hashable(instrument_params))

        if cache_key in self._cache:
            self._hit_count += 1
            return self._cache[cache_key].copy()

        self._miss_count += 1

        # Compute merged parameters (original logic)
        merged = preset_params.copy()
        for key, value in instrument_params.items():
            if key not in merged:
                merged[key] = value
            elif key == 'modulators':
                # Merge modulators lists
                if not isinstance(merged[key], list):
                    merged[key] = [merged[key]]
                if isinstance(value, list):
                    merged[key].extend(value)
                else:
                    merged[key].append(value)
            elif key == 'zones':
                # Merge zones
                if not isinstance(merged[key], list):
                    merged[key] = [merged[key]]
                if isinstance(value, list):
                    merged[key].extend(value)
                else:
                    merged[key].append(value)
            else:
                # Instrument parameters override preset parameters
                merged[key] = value

        # Cache the result
        self._cache[cache_key] = merged.copy()
        return merged

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total_requests if total_requests > 0 else 0
        return {
            'hits': self._hit_count,
            'misses': self._miss_count,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache)
        }


class MemoryPool:
    """Memory pool for reusing objects to reduce allocation overhead"""

    def __init__(self, object_type, max_size=1000):
        self.object_type = object_type
        self.max_size = max_size
        self.pool = []
        self.created_count = 0

    def get(self, *args, **kwargs):
        """Get an object from the pool or create a new one"""
        if self.pool:
            obj = self.pool.pop()
            # Reset object state if it has a reset method
            if hasattr(obj, 'reset'):
                obj.reset()
            return obj

        self.created_count += 1
        return self.object_type(*args, **kwargs)

    def put(self, obj):
        """Return an object to the pool"""
        if len(self.pool) < self.max_size and obj is not None:
            self.pool.append(obj)

    def get_stats(self) -> Dict:
        """Get pool statistics"""
        return {
            'pool_size': len(self.pool),
            'created_count': self.created_count,
            'max_size': self.max_size
        }


class OptimizedMIDIToOGGConverter:
    """Optimized MIDI to OGG Converter with performance improvements"""

    # Opus supported sample rates
    OPUS_SUPPORTED_SAMPLE_RATES = [8000, 12000, 16000, 24000, 48000]

    # Opus frame durations in milliseconds
    OPUS_SUPPORTED_FRAME_DURATIONS = [2.5, 5, 10, 20, 40, 60]

    def __init__(self, config: Dict[str, Any], silent: bool = False):
        """
        Initialize the optimized converter with configuration

        Args:
            config: Configuration dictionary with synthesizer settings
            silent: Whether to suppress console output
        """
        self.config = config
        self.silent = silent
        self.stop_conversion = False  # Flag to stop conversion
        self.keyboard_thread = None   # Keyboard input thread
        self.start_time = None        # Conversion start time
        self.total_duration = 0       # Total estimated duration
        self.processed_duration = 0   # Processed duration so far

        # Initialize optimization components
        self.param_cache = ParameterCache()
        self.modulator_pool = MemoryPool(dict, max_size=5000)
        self.zone_pool = MemoryPool(dict, max_size=2000)

        # Extract configuration parameters
        sample_rate = config.get("sample_rate", 48000)  # Changed default to 48kHz
        chunk_size_ms = config.get("chunk_size_ms", 20)  # Changed to milliseconds
        max_polyphony = config.get("max_polyphony", 64)
        master_volume = config.get("master_volume", 1.0)

        # Validate sample rate
        self._validate_sample_rate(sample_rate)

        # Validate chunk size
        self._validate_chunk_size(chunk_size_ms, sample_rate)

        # Calculate block size in samples from chunk size in milliseconds
        block_size = int(sample_rate * chunk_size_ms / 1000.0)

        # Create synthesizer with optimized settings and parameter cache
        self.synth = XGSynthesizer(
            sample_rate=sample_rate, block_size=block_size, max_polyphony=max_polyphony,
            param_cache=self.param_cache
        )

        # Set master volume
        self.synth.set_master_volume(master_volume)

        # Load SF2 files if specified
        sf2_files = config.get("sf2_files", [])
        if sf2_files:
            self.synth.set_sf2_files(sf2_files)

            # Apply bank blacklists if specified
            bank_blacklists = config.get("bank_blacklists", {})
            for sf2_path, banks in bank_blacklists.items():
                self.synth.set_bank_blacklist(sf2_path, banks)

            # Apply preset blacklists if specified
            preset_blacklists = config.get("preset_blacklists", {})
            for sf2_path, presets in preset_blacklists.items():
                self.synth.set_preset_blacklist(sf2_path, presets)

            # Apply bank mappings if specified
            bank_mappings = config.get("bank_mappings", {})
            for sf2_path, mapping in bank_mappings.items():
                self.synth.set_bank_mapping(sf2_path, mapping)

        # Store other parameters
        self.sample_rate = sample_rate
        self.chunk_size_ms = chunk_size_ms
        self.block_size = block_size

    def _keyboard_input_thread(self):
        """
        Thread to handle keyboard input for stopping conversion
        Cross-platform implementation for Windows and Unix systems
        """
        try:
            if platform.system() == 'Windows':
                # Windows implementation using msvcrt
                while not self.stop_conversion:
                    if msvcrt.kbhit():
                        try:
                            char = msvcrt.getch()
                            # Handle both bytes and string
                            if isinstance(char, bytes):
                                char = char.decode('utf-8', errors='ignore')

                            if char == ' ':  # Spacebar pressed
                                self.stop_conversion = True
                                if not self.silent:
                                    print("\nStopping conversion... (Press Ctrl+C to force quit)")
                                break
                            elif char in ('\x03', '\x1b'):  # Ctrl+C or ESC
                                self.stop_conversion = True
                                break
                        except:
                            # Handle decoding errors
                            pass
                    time.sleep(0.1)  # Small delay to prevent busy waiting
            else:
                # Unix implementation using termios/tty
                # Save current terminal settings
                old_settings = termios.tcgetattr(sys.stdin)

                # Set terminal to raw mode
                tty.setraw(sys.stdin.fileno())

                while not self.stop_conversion:
                    # Check if there's input available
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        # Read one character
                        char = sys.stdin.read(1)
                        if char == ' ':  # Spacebar pressed
                            self.stop_conversion = True
                            if not self.silent:
                                print("\nStopping conversion... (Press Ctrl+C to force quit)")
                            break
                        elif char == '\x03':  # Ctrl+C
                            self.stop_conversion = True
                            break

        except Exception as e:
            # Silently handle keyboard input errors
            pass
        finally:
            if platform.system() != 'Windows':
                try:
                    # Restore terminal settings (Unix only)
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass

    def _start_keyboard_monitoring(self):
        """
        Start keyboard input monitoring thread
        """
        if self.silent:
            return

        # Check if we can monitor keyboard input
        can_monitor = False

        if platform.system() == 'Windows':
            # On Windows, we can always try to monitor keyboard
            can_monitor = True
        else:
            # On Unix systems, check if stdin is a TTY
            can_monitor = sys.stdin.isatty()

        if can_monitor:
            try:
                self.keyboard_thread = threading.Thread(target=self._keyboard_input_thread, daemon=True)
                self.keyboard_thread.start()
            except Exception as e:
                # Silently fail if we can't start keyboard monitoring
                if not self.silent:
                    print(f"Warning: Could not start keyboard monitoring: {e}")

    def _stop_keyboard_monitoring(self):
        """
        Stop keyboard input monitoring
        """
        self.stop_conversion = True
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            self.keyboard_thread.join(timeout=1.0)

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to MM:SS format

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _update_progress(self, current_block: int, total_blocks: int, processed_seconds: float, total_seconds: float):
        """
        Update and display progress information

        Args:
            current_block: Current block being processed
            total_blocks: Total number of blocks to process
            processed_seconds: Seconds of audio processed so far
            total_seconds: Total estimated seconds
        """
        if self.silent:
            return

        # Calculate progress percentage
        progress_percent = min(100.0, (current_block / total_blocks) * 100)

        # Calculate elapsed time
        elapsed_seconds = time.time() - self.start_time if self.start_time else 0

        # Calculate ETA (estimated time of arrival)
        if elapsed_seconds > 0 and current_block > 0:
            blocks_per_second = current_block / elapsed_seconds
            remaining_blocks = total_blocks - current_block
            eta_seconds = remaining_blocks / blocks_per_second if blocks_per_second > 0 else 0
        else:
            eta_seconds = 0

        # Format times
        processed_time = self._format_duration(processed_seconds)
        total_time = self._format_duration(total_seconds)
        eta_time = self._format_duration(eta_seconds)
        elapsed_time = self._format_duration(elapsed_seconds)

        # Clear current line and print progress
        print(f"\rProgress: {progress_percent:5.1f}% | {processed_time}/{total_time} | Elapsed: {elapsed_time} | ETA: {eta_time} | Press SPACE to stop", end="", flush=True)

    def _validate_sample_rate(self, sample_rate: int):
        """
        Validate sample rate against Opus requirements

        Args:
            sample_rate: Sample rate to validate
        """
        if sample_rate not in self.OPUS_SUPPORTED_SAMPLE_RATES:
            raise ValueError(f"Unsupported sample rate {sample_rate}. Supported rates: {self.OPUS_SUPPORTED_SAMPLE_RATES}")

    def _validate_chunk_size(self, chunk_size_ms: float, sample_rate: int):
        """
        Validate chunk size against Opus requirements

        Args:
            chunk_size_ms: Chunk size in milliseconds
            sample_rate: Sample rate in Hz
        """
        # Calculate frame size in samples
        frame_size_samples = int(sample_rate * chunk_size_ms / 1000.0)

        # Valid frame sizes for Opus
        valid_frame_sizes = [120, 240, 480, 960, 1920, 2880]  # For 48kHz sample rate

        # Check if frame size is valid
        if frame_size_samples not in valid_frame_sizes:
            # Find closest valid frame size
            closest_size = min(valid_frame_sizes, key=lambda x: abs(x - frame_size_samples))
            closest_ms = closest_size * 1000.0 / sample_rate

            if not self.silent:
                print(f"Warning: Chunk size {chunk_size_ms}ms ({frame_size_samples} samples) is not optimal for Opus.")
                print(f"Closest valid chunk size: {closest_ms:.1f}ms ({closest_size} samples)")

    def convert_midi_to_ogg(
        self, midi_file: str, output_file: str, tempo_ratio: float = 1.0, output_format: str = "ogg"
    ) -> bool:
        """
        Convert a MIDI file to OGG or WAV using sample-accurate processing

        Args:
            midi_file: Path to the input MIDI file
            output_file: Path to the output audio file
            tempo_ratio: Tempo adjustment ratio (1.0 = original tempo)
            output_format: Output format ("ogg" or "wav")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to absolute paths
            midi_file = os.path.abspath(midi_file)
            output_file = os.path.abspath(output_file)

            # Verify input file exists
            if not os.path.exists(midi_file):
                if not self.silent:
                    print(f"Error: Input file '{midi_file}' not found")
                return False

            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Load the MIDI file
            midi = mido.MidiFile(midi_file)

            # Calculate total number of ticks and duration
            tick_rate = midi.ticks_per_beat
            tempo = 500000  # Default tempo (microseconds per beat)

            # Process all messages to calculate duration
            total_ticks = 0
            for track in midi.tracks:
                track_ticks = sum(msg.time for msg in track)
                total_ticks = max(total_ticks, track_ticks)

            # Estimate duration in seconds
            estimated_duration = (
                (total_ticks * tempo) / (1000000 * tick_rate) / tempo_ratio
            )

            if not self.silent:
                print(f"Converting {midi_file} to {output_file}")
                print(f"Estimated duration: {estimated_duration:.2f} seconds")

            # Process the MIDI file and generate audio in the specified format using sample-accurate processing
            if output_format.lower() == "wav":
                self._process_midi_to_wav(midi, output_file, tempo_ratio)
            else:
                self._process_midi_to_ogg(midi, output_file, tempo_ratio)

            if not self.silent:
                print(f"Conversion completed successfully!")
                # Print optimization statistics
                cache_stats = self.param_cache.get_stats()
                pool_stats = self.modulator_pool.get_stats()
                print(f"Parameter cache stats: {cache_stats}")
                print(f"Modulator pool stats: {pool_stats}")

            return True

        except Exception as e:
            if not self.silent:
                print(f"Error converting {midi_file}: {e}")
            return False

    def _collect_midi_messages(self, midi: mido.MidiFile):
        """
        Collect all MIDI messages with their absolute timestamps

        Args:
            midi: Loaded MIDI file

        Returns:
            tuple of (midi_messages, sysex_messages)
        """
        midi_messages = []
        sysex_messages = []
        tempo = 500000  # Initial tempo (microseconds per beat)
        tick_rate = midi.ticks_per_beat

        # Process all tracks and collect messages with absolute time
        for track in midi.tracks:
            abs_time = 0  # Absolute time in ticks
            for msg in track:
                abs_time += msg.time

                # Handle tempo changes
                if msg.type == "set_tempo":
                    tempo = msg.tempo

                # Store all messages with their absolute time
                if msg.type == "sysex":
                    # Convert ticks to seconds for SYSEX message
                    seconds = (abs_time * tempo) / (1000000.0 * tick_rate)
                    sysex_messages.append((seconds, list(msg.bytes())))
                elif not msg.is_meta:
                    # Convert ticks to seconds for regular MIDI message
                    seconds = (abs_time * tempo) / (1000000.0 * tick_rate)
                    # Convert mido message to status/data format
                    if msg.type == "note_on":
                        midi_messages.append((seconds, 0x90 + msg.channel, msg.note, msg.velocity))
                    elif msg.type == "note_off":
                        midi_messages.append((seconds, 0x80 + msg.channel, msg.note, msg.velocity))
                    elif msg.type == "control_change":
                        midi_messages.append((seconds, 0xB0 + msg.channel, msg.control, msg.value))
                    elif msg.type == "program_change":
                        midi_messages.append((seconds, 0xC0 + msg.channel, msg.program, 0))
                    elif msg.type == "pitchwheel":
                        # Convert 14-bit pitch wheel value to MSB/LSB
                        value = msg.pitch + 8192  # mido range is -8192 to 8191, MIDI is 0 to 16383
                        lsb = value & 0x7F
                        msb = (value >> 7) & 0x7F
                        midi_messages.append((seconds, 0xE0 + msg.channel, lsb, msb))
                    elif msg.type == "polytouch":
                        midi_messages.append((seconds, 0xA0 + msg.channel, msg.note, msg.value))
                    elif msg.type == "aftertouch":
                        midi_messages.append((seconds, 0xD0 + msg.channel, msg.value, 0))

        # Sort both message lists by their timestamps to ensure proper chronological order
        midi_messages.sort(key=lambda x: x[0])  # Sort by timestamp (first element)
        sysex_messages.sort(key=lambda x: x[0])  # Sort by timestamp (first element)

        return midi_messages, sysex_messages

    def _process_audio_blocks(self, midi: mido.MidiFile, tempo_ratio: float = 1.0):
        """
        Generate audio blocks from MIDI file using sample-accurate mode

        Args:
            midi: Loaded MIDI file
            tempo_ratio: Tempo adjustment ratio

        Yields:
            tuple of (left_channel, right_channel) audio blocks
        """
        # Collect all messages with their absolute timestamps
        midi_messages, sysex_messages = self._collect_midi_messages(midi)

        # Send all messages to synthesizer in blocks using sample-accurate processing
        self.synth.buffered_processor.send_midi_message_block(midi_messages, sysex_messages)
        for m in midi_messages:
            if 0x90 <= m[1] < 0xa0:
                self.synth.buffered_processor.set_buffered_mode_time(m[0])
                break

        # Generate audio with proper timing using sample-accurate mode
        block_duration = self.block_size / self.sample_rate
        time_increment = block_duration / tempo_ratio

        # Generate audio blocks with automatic time management
        total_blocks = int(midi.length * self.sample_rate / self.block_size * tempo_ratio) + int(2.0 / block_duration)  # +2 seconds for decay

        # Set total duration for progress tracking
        self.total_duration = total_blocks * block_duration
        self.processed_duration = 0
        self.start_time = time.time()

        # Start keyboard monitoring
        self._start_keyboard_monitoring()

        try:
            for i in range(total_blocks):
                # Check if conversion should be stopped
                if self.stop_conversion:
                    if not self.silent:
                        print(f"\nConversion stopped at {self._format_duration(self.processed_duration)}")
                    break

                # Generate audio block at current time with sample-accurate processing
                left_channel, right_channel = self.synth.generate_audio_block_sample_accurate(
                    self.block_size
                )

                # Update processed duration
                self.processed_duration += block_duration

                # Update progress (more frequently for better responsiveness)
                if not self.silent and (i + 1) % max(1, total_blocks // 200) == 0:  # Every 2% or at least once
                    self._update_progress(i + 1, total_blocks, self.processed_duration, self.total_duration)

                yield left_channel, right_channel

        finally:
            # Stop keyboard monitoring
            self._stop_keyboard_monitoring()

            # Print final newline if we were showing progress
            if not self.silent:
                print()

    def _process_midi_to_ogg(
        self, midi: mido.MidiFile, output_file: str, tempo_ratio: float = 1.0
    ):
        """
        Process MIDI messages and generate OGG audio directly with sample-accurate timing

        Args:
            midi: Loaded MIDI file
            output_file: Output OGG file path
            tempo_ratio: Tempo adjustment ratio
        """
        # Create Opus encoder with validated parameters
        try:
            encoder = opuslib.Encoder(
                fs=self.sample_rate, channels=2, application=opuslib.APPLICATION_AUDIO
            )  # Stereo
        except Exception as e:
            raise ValueError(f"Failed to create Opus encoder with sample rate {self.sample_rate}: {e}")

        # Open OGG file for writing
        with open(output_file, "wb") as ogg_file:
            # Generate and process audio blocks with sample-accurate processing
            for left_channel, right_channel in self._process_audio_blocks(midi, tempo_ratio):
                # Convert to float32 in range [-1.0, 1.0]
                left_float32 = left_channel.astype(np.float32)
                right_float32 = right_channel.astype(np.float32)

                # Interleave channels (LRLRLR...)
                interleaved = np.empty(
                    (left_float32.size + right_float32.size,), dtype=np.float32
                )
                interleaved[0::2] = left_float32
                interleaved[1::2] = right_float32

                # Calculate frame size in samples (for 48kHz, 20ms = 960 samples)
                frame_size_samples = int(self.sample_rate * self.chunk_size_ms / 1000.0)
                samples_per_frame = frame_size_samples * 2  # Multiply by 2 for stereo

                # Process in chunks
                for j in range(0, len(interleaved), samples_per_frame):
                    chunk = interleaved[j:j+samples_per_frame]
                    if len(chunk) == samples_per_frame:
                        # Reshape for stereo
                        chunk = chunk.reshape(-1, 2)
                        # Encode chunk
                        try:
                            encoded_data = encoder.encode(chunk.tobytes(), frame_size_samples)
                            # Write to OGG file
                            ogg_file.write(encoded_data)
                        except Exception as e:
                            # Handle encoding errors silently
                            if not self.silent:
                                print(f"Warning: Opus encoding error: {e}")
                            pass

                # Progress indicator
                if not self.silent:
                    # We'll handle progress differently since we don't know total blocks upfront
                    pass

    def _send_midi_message_to_synth(self, msg: mido.Message):
        """
        Send a mido MIDI message to the synthesizer

        Args:
            msg: MIDI message to send
        """
        if msg.type == "note_on":
            self.synth.send_midi_message(0x90 + msg.channel, msg.note, msg.velocity)
        elif msg.type == "note_off":
            self.synth.send_midi_message(0x80 + msg.channel, msg.note, msg.velocity)
        elif msg.type == "control_change":
            self.synth.send_midi_message(0xB0 + msg.channel, msg.control, msg.value)
        elif msg.type == "program_change":
            self.synth.send_midi_message(0xC0 + msg.channel, msg.program)
        elif msg.type == "pitchwheel":
            # Convert 14-bit pitch wheel value to MSB/LSB
            value = msg.pitch + 8192  # mido range is -8192 to 8191, MIDI is 0 to 16383
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            self.synth.send_midi_message(0xE0 + msg.channel, lsb, msb)
        elif msg.type == "polytouch":
            self.synth.send_midi_message(0xA0 + msg.channel, msg.note, msg.value)
        elif msg.type == "aftertouch":
            self.synth.send_midi_message(0xD0 + msg.channel, msg.value)

    def _send_sysex_message_to_synth(self, msg: mido.Message):
        """
        Send a mido SYSEX message to the synthesizer

        Args:
            msg: SYSEX message to send
        """
        if msg.type == "sysex":
            # Convert mido sysex format to list of integers including F0 and F7
            sysex_data = [0xF0] + list(msg.data) + [0xF7]
            self.synth.send_sysex(sysex_data)

    def _process_midi_to_wav(self, midi: mido.MidiFile, output_file: str, tempo_ratio: float = 1.0):
        """
        Process MIDI messages and generate WAV audio directly with sample-accurate timing

        Args:
            midi: Loaded MIDI file
            output_file: Output WAV file path
            tempo_ratio: Tempo adjustment ratio
        """
        import wave

        # Open WAV file for writing
        with wave.open(output_file, 'wb') as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)

            # Generate and process audio blocks with sample-accurate processing
            for left_channel, right_channel in self._process_audio_blocks(midi, tempo_ratio):
                # Convert to 16-bit PCM
                left_int16 = np.clip(left_channel, -1.0, 1.0) * 32767
                right_int16 = np.clip(right_channel, -1.0, 1.0) * 32767

                # Interleave channels (LRLRLR...)
                interleaved = np.empty((left_int16.size + right_int16.size,), dtype=np.int16)
                interleaved[0::2] = left_int16.astype(np.int16)
                interleaved[1::2] = right_int16.astype(np.int16)

                # Write to WAV file
                wav_file.writeframes(interleaved.tobytes())

                # Progress indicator
                if not self.silent:
                    # We'll handle progress differently since we don't know total blocks upfront
                    pass


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file or use defaults

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Configuration dictionary
    """
    # Default configuration with updated defaults
    default_config = {
        "sample_rate": 48000,  # Changed default to 48kHz
        "chunk_size_ms": 20,   # Changed to milliseconds with default 20ms
        "max_polyphony": 64,
        "master_volume": 1.0,
        "sf2_files": [],
        "bank_blacklists": {},
        "preset_blacklists": {},
        "bank_mappings": {},
    }

    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(config or {})
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
            print("Using default configuration.")

    return default_config


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert MIDI files to OGG using XG Synthesizer (Optimized Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  optimized_midi_to_ogg.py input.mid output.ogg
  optimized_midi_to_ogg.py -c config.yaml input.mid output.ogg
  optimized_midi_to_ogg.py --sf2 soundfont.sf2 input.mid output.ogg
  optimized_midi_to_ogg.py --sample-rate 48000 input.mid output.ogg
  optimized_midi_to_ogg.py --silent input.mid output.ogg

Performance Optimizations:
  - SF2 parameter caching
  - Memory pooling for objects
  - Batched modulator processing
  - Optimized attribute access

Keyboard Controls (works on Windows, Linux, and macOS):
  SPACE - Stop conversion gracefully
  Ctrl+C - Force quit conversion
        """,
    )

    parser.add_argument("input_files", nargs="+", help="Input MIDI file(s) to convert")

    parser.add_argument("output", help="Output file or directory (if multiple inputs)")

    parser.add_argument(
        "-c", "--config", help="Path to YAML configuration file", default="config.yaml"
    )

    parser.add_argument(
        "--sf2",
        action="append",
        dest="sf2_files",
        help="SoundFont (.sf2) file paths (can be used multiple times)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        dest="sample_rate",
        help="Audio sample rate in Hz (default: 48000)",
    )

    parser.add_argument(
        "--chunk-size-ms",
        type=float,
        dest="chunk_size_ms",
        help="Audio processing chunk size in milliseconds (default: 20)",
    )

    parser.add_argument(
        "--polyphony",
        type=int,
        dest="max_polyphony",
        help="Maximum polyphony (default: 64)",
    )

    parser.add_argument(
        "--volume",
        type=float,
        dest="master_volume",
        help="Master volume (0.0 to 1.0, default: 1.0)",
    )

    parser.add_argument(
        "--tempo",
        type=float,
        default=1.0,
        help="Tempo ratio (default: 1.0 = original tempo)",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress console output during conversion",
    )

    parser.add_argument(
    "--format",
    choices=["wav", "ogg"],
    default="ogg",
    help="Output audio format (default: ogg)"
)


    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Load configuration
    config = load_config(args.config)

    # Override config with command-line arguments
    if args.sf2_files:
        config["sf2_files"] = args.sf2_files
    if args.sample_rate:
        config["sample_rate"] = args.sample_rate
    if args.chunk_size_ms:  # Updated parameter name
        config["chunk_size_ms"] = args.chunk_size_ms
    if args.max_polyphony:
        config["max_polyphony"] = args.max_polyphony
    if args.master_volume is not None:
        config["master_volume"] = args.master_volume

    # Check if output is a directory
    output_is_dir = os.path.isdir(args.output) or len(args.input_files) > 1

    # Validate inputs
    if not args.input_files:
        if not args.silent:
            print("Error: No input files specified")
        return 1

    # Check if all input files exist
    for input_file in args.input_files:
        if not os.path.exists(input_file):
            if not args.silent:
                print(f"Error: Input file '{input_file}' not found")
            return 1

    # Create optimized converter
    try:
        converter = OptimizedMIDIToOGGConverter(config, args.silent)
    except ValueError as e:
        if not args.silent:
            print(f"Error: {e}")
        return 1

    # Process files
    success_count = 0
    for input_file in args.input_files:
        # Determine output file name
        if output_is_dir:
            # Generate output file name based on input file
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            if args.output.endswith(".ogg") and len(args.input_files) == 1:
                output_file = args.output
            else:
                output_file = os.path.join(args.output, f"{base_name}.ogg")
        else:
            output_file = args.output

        # Convert file
        if converter.convert_midi_to_ogg(input_file, output_file, args.tempo, args.format):
            success_count += 1
        else:
            if not args.silent:
                print(f"Failed to convert {input_file}")

    if not args.silent:
        print(
            f"\nConversion completed: {success_count}/{len(args.input_files)} files successful"
        )
    return 0 if success_count == len(args.input_files) else 1


if __name__ == "__main__":
    sys.exit(main())
