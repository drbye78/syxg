"""Wavetable bank."""
from __future__ import annotations
from typing import Any
import numpy as np
from .wavetable import Wavetable
from .oscillator import WavetableOscillator
class WavetableBank:
    """
    Bank of wavetables with morphing capabilities.

    Manages multiple wavetables and provides crossfading/morphing
    between different wavetables for rich timbral control.
    """

    def __init__(self, max_wavetables: int = 64):
        self.max_wavetables = max_wavetables
        self.wavetables: dict[str, Wavetable] = {}
        self.morph_groups: dict[str, list[str]] = {}

    def add_wavetable(self, wavetable: Wavetable, name: str) -> bool:
        """
        Add wavetable to bank.

        Args:
            wavetable: Wavetable to add
            name: Unique name for the wavetable

        Returns:
            True if added successfully
        """
        if len(self.wavetables) >= self.max_wavetables:
            return False

        self.wavetables[name] = wavetable
        return True

    def load_wavetable_from_file(
        self, file_path: str, name: str, sample_manager: PyAVSampleManager | None = None
    ) -> bool:
        """
        Load wavetable from audio file.

        Args:
            file_path: Path to audio file
            name: Name for the wavetable
            sample_manager: Optional sample manager for loading

        Returns:
            True if loaded successfully
        """
        try:
            if sample_manager:
                sample = sample_manager.load_sample(file_path)
                data = sample.data
                sample_rate = sample.sample_rate
            else:
                # Basic WAV loading implementation
                data, sample_rate = self._load_wav_file(file_path)

            # Extract single cycle (assume file contains one cycle)
            # In practice, you might want to analyze the file for cycle boundaries
            wavetable = Wavetable(data, sample_rate, name)
            return self.add_wavetable(wavetable, name)

        except Exception as e:
            print(f"Failed to load wavetable from {file_path}: {e}")
            return False

    def _load_wav_file(self, file_path: str) -> tuple[np.ndarray, int]:
        """
        Basic WAV file loader implementation.

        Args:
            file_path: Path to WAV file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        with open(file_path, "rb") as f:
            # Read RIFF header
            riff_header = f.read(12)
            if riff_header[:4] != b"RIFF" or riff_header[8:12] != b"WAVE":
                raise ValueError("Not a valid WAV file")

            # Find fmt and data chunks
            fmt_chunk = None
            data_chunk = None

            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    break

                chunk_id = chunk_header[:4]
                chunk_size = int.from_bytes(chunk_header[4:8], byteorder="little")

                if chunk_id == b"fmt ":
                    fmt_chunk = f.read(chunk_size)
                elif chunk_id == b"data":
                    data_chunk = f.read(chunk_size)
                    break  # Data chunk is usually last
                else:
                    # Skip unknown chunks
                    f.seek(chunk_size, 1)

            if fmt_chunk is None or data_chunk is None:
                raise ValueError("WAV file missing fmt or data chunk")

            # Parse fmt chunk
            audio_format = int.from_bytes(fmt_chunk[0:2], byteorder="little")
            if audio_format != 1:
                raise ValueError("Only PCM WAV files are supported")

            num_channels = int.from_bytes(fmt_chunk[2:4], byteorder="little")
            sample_rate = int.from_bytes(fmt_chunk[4:8], byteorder="little")
            bits_per_sample = int.from_bytes(fmt_chunk[14:16], byteorder="little")

            if bits_per_sample not in [8, 16, 24, 32]:
                raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")

            # Parse data chunk
            data = None
            if bits_per_sample == 8:
                dtype = np.uint8
                data = np.frombuffer(data_chunk, dtype=dtype)
                # Convert unsigned 8-bit to signed float
                data = (data.astype(np.float32) - 128.0) / 128.0
            elif bits_per_sample == 16:
                dtype = np.int16
                data = np.frombuffer(data_chunk, dtype=dtype)
                data = data.astype(np.float32) / 32768.0
            elif bits_per_sample == 24:
                # 24-bit is tricky - need to handle manually
                data = np.zeros(len(data_chunk) // 3, dtype=np.float32)
                for i in range(len(data_chunk) // 3):
                    # Read 3 bytes as 24-bit signed integer
                    bytes_24 = data_chunk[i * 3 : (i + 1) * 3]
                    value = int.from_bytes(bytes_24, byteorder="little", signed=True)
                    # Convert to float (-1.0 to 1.0)
                    data[i] = value / 8388608.0
            elif bits_per_sample == 32:
                dtype = np.int32
                data = np.frombuffer(data_chunk, dtype=dtype)
                data = data.astype(np.float32) / 2147483648.0

            if data is None:
                raise ValueError(f"Unsupported bits per sample: {bits_per_sample}")

            # Handle multi-channel (take first channel for wavetable)
            if num_channels > 1:
                data = data.reshape(-1, num_channels)[:, 0]

            return data, sample_rate

    def create_wavetable_from_waveform(
        self, waveform_type: str, name: str, size: int = 2048, harmonics: int = 16
    ) -> bool:
        """
        Create wavetable from mathematical waveform.

        Args:
            waveform_type: Type of waveform ('sine', 'triangle', 'square', 'sawtooth')
            name: Name for the wavetable
            size: Wavetable size in samples
            harmonics: Number of harmonics for complex waveforms

        Returns:
            True if created successfully
        """
        try:
            # Generate single cycle
            t = np.linspace(0, 2 * np.pi, size, endpoint=False)

            match waveform_type:
                case "sine":
                    data = np.sin(t)
                case "triangle":
                    data = np.abs((t % (2 * np.pi)) - np.pi) / (np.pi / 2) - 1
                case "square":
                    data = np.sign(np.sin(t))
                case "sawtooth":
                    data = (t % (2 * np.pi)) / np.pi - 1
                case "noise":
                    data = np.random.uniform(-1, 1, size)
                case _:
                    data = np.sin(t)

            wavetable = Wavetable(data, 44100, name)
            return self.add_wavetable(wavetable, name)

        except Exception as e:
            print(f"Failed to create wavetable '{name}': {e}")
            return False

    def get_wavetable(self, name: str) -> Wavetable | None:
        """Get wavetable by name."""
        return self.wavetables.get(name)

    def get_morphed_wavetable(self, sources: list[str], position: float) -> Wavetable | None:
        """
        Get morphed wavetable between multiple sources.

        Args:
            sources: List of wavetable names to morph between
            position: Morph position (0.0 = first source, 1.0 = last source)

        Returns:
            Morphed wavetable or None if sources not found
        """
        if not sources or len(sources) < 2:
            return self.get_wavetable(sources[0]) if sources else None

        # Get source wavetables
        source_tables = []
        for name in sources:
            wt = self.get_wavetable(name)
            if wt:
                source_tables.append(wt)
            else:
                return None

        # Simple linear morphing between first and last
        # More sophisticated morphing could interpolate between all sources
        wt1 = source_tables[0]
        wt2 = source_tables[-1]

        # Ensure same length for morphing
        min_length = min(wt1.length, wt2.length)
        morphed_data = wt1.data[:min_length] * (1.0 - position) + wt2.data[:min_length] * position

        morphed_name = f"morph_{sources[0]}_{sources[-1]}_{position:.2f}"
        return Wavetable(morphed_data, wt1.sample_rate, morphed_name)

    def create_morph_group(self, group_name: str, wavetable_names: list[str]):
        """Create a morph group for easy access."""
        self.morph_groups[group_name] = wavetable_names.copy()

    def get_morph_group(self, group_name: str) -> list[str]:
        """Get wavetable names in a morph group."""
        return self.morph_groups.get(group_name, [])

    def list_wavetables(self) -> list[str]:
        """Get list of all wavetable names."""
        return list(self.wavetables.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get wavetable bank statistics."""
        total_samples = sum(wt.length for wt in self.wavetables.values())
        avg_length = total_samples / len(self.wavetables) if self.wavetables else 0

        return {
            "total_wavetables": len(self.wavetables),
            "total_samples": total_samples,
            "average_length": avg_length,
            "morph_groups": len(self.morph_groups),
            "memory_usage_mb": total_samples * 4 / (1024 * 1024),  # float32 = 4 bytes
        }


