"""
Sample Format Handler - Audio Format Conversion and Processing

Provides comprehensive audio format conversion, validation, and processing
capabilities for the XG synthesizer's sample management system.
"""

from __future__ import annotations

import numpy as np
from typing import Any
import struct
import wave
import io


class SampleFormatHandler:
    """
    Comprehensive audio format handler for sample conversion and validation.

    Supports multiple audio formats with conversion, validation, and metadata
    extraction capabilities for professional sample management.
    """

    # Supported audio formats
    SUPPORTED_FORMATS = {
        "wav": [".wav", ".wave"],
        "aiff": [".aiff", ".aif"],
        "flac": [".flac"],
        "ogg": [".ogg"],
        "mp3": [".mp3"],
        "raw": [".raw", ".pcm"],
    }

    # Format specifications
    FORMAT_SPECS = {
        "int8": {"bits": 8, "signed": True, "numpy_dtype": np.int8},
        "int16": {"bits": 16, "signed": True, "numpy_dtype": np.int16},
        "int24": {"bits": 24, "signed": True, "numpy_dtype": None},  # Special handling
        "int32": {"bits": 32, "signed": True, "numpy_dtype": np.int32},
        "float32": {"bits": 32, "signed": False, "numpy_dtype": np.float32},
        "float64": {"bits": 64, "signed": False, "numpy_dtype": np.float64},
    }

    def __init__(self):
        """Initialize format handler."""
        self.format_cache = {}
        self.conversion_cache = {}

    def detect_format(self, file_path: str) -> str | None:
        """
        Detect audio format from file extension and content.

        Args:
            file_path: Path to audio file

        Returns:
            Detected format or None if unknown
        """
        import os

        # Check file extension
        _, ext = os.path.splitext(file_path.lower())

        for fmt, extensions in self.SUPPORTED_FORMATS.items():
            if ext in extensions:
                return fmt

        # Try content-based detection
        try:
            with open(file_path, "rb") as f:
                header = f.read(12)
                return self._detect_format_from_header(header)
        except:
            pass

        return None

    def _detect_format_from_header(self, header: bytes) -> str | None:
        """Detect format from file header bytes."""
        if len(header) < 4:
            return None

        # WAV detection
        if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
            return "wav"

        # AIFF detection
        if header.startswith(b"FORM") and header[8:12] == b"AIFF":
            return "aiff"

        # FLAC detection
        if header.startswith(b"fLaC"):
            return "flac"

        # OGG detection
        if header.startswith(b"OggS"):
            return "ogg"

        # MP3 detection (simplified)
        if (
            header.startswith(b"\xff\xfb")
            or header.startswith(b"\xff\xf3")
            or header.startswith(b"\xff\xf2")
        ):
            return "mp3"

        return None

    def load_audio_file(self, file_path: str) -> dict[str, Any] | None:
        """
        Load audio file and return standardized format.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio data, sample rate, channels, etc.
        """
        fmt = self.detect_format(file_path)
        if not fmt:
            return None

        try:
            match fmt:
                case "wav":
                    return self._load_wav_file(file_path)
                case "aiff":
                    return self._load_aiff_file(file_path)
                case "flac":
                    return self._load_flac_file(file_path)
                case "ogg":
                    return self._load_ogg_file(file_path)
                case "mp3":
                    return self._load_mp3_file(file_path)
                case _:
                    return self._load_raw_file(file_path)
        except Exception as e:
            print(f"Error loading {fmt} file {file_path}: {e}")
            return None

    def _load_wav_file(self, file_path: str) -> dict[str, Any] | None:
        """Load WAV file."""
        try:
            with wave.open(file_path, "rb") as wav_file:
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()

                # Read frames
                frames = wav_file.readframes(n_frames)

                # Convert to numpy array
                if sample_width == 1:  # 8-bit
                    data = np.frombuffer(frames, dtype=np.int8)
                elif sample_width == 2:  # 16-bit
                    data = np.frombuffer(frames, dtype=np.int16)
                elif sample_width == 3:  # 24-bit (packed)
                    data = self._unpack_24bit(frames)
                elif sample_width == 4:  # 32-bit
                    data = np.frombuffer(frames, dtype=np.int32)
                else:
                    return None

                # Reshape for multiple channels
                data = data.reshape(-1, n_channels)

                # Normalize to float32
                if sample_width == 1:
                    data = data.astype(np.float32) / 127.0
                elif sample_width == 2:
                    data = data.astype(np.float32) / 32767.0
                elif sample_width == 3:
                    data = data.astype(np.float32) / 8388607.0
                elif sample_width == 4:
                    data = data.astype(np.float32) / 2147483647.0

                return {
                    "data": data,
                    "sample_rate": sample_rate,
                    "channels": n_channels,
                    "format": "float32",
                    "original_format": "wav",
                    "bit_depth": sample_width * 8,
                }

        except Exception as e:
            print(f"WAV load error: {e}")
            return None

    def _load_aiff_file(self, file_path: str) -> dict[str, Any] | None:
        """Load AIFF file using PyAV."""
        return self._load_audio_file_pyav(file_path, "aiff")

    def _load_flac_file(self, file_path: str) -> dict[str, Any] | None:
        """Load FLAC file using PyAV."""
        return self._load_audio_file_pyav(file_path, "flac")

    def _load_ogg_file(self, file_path: str) -> dict[str, Any] | None:
        """Load OGG file using PyAV."""
        return self._load_audio_file_pyav(file_path, "ogg")

    def _load_mp3_file(self, file_path: str) -> dict[str, Any] | None:
        """Load MP3 file using PyAV."""
        return self._load_audio_file_pyav(file_path, "mp3")

    def _load_audio_file_pyav(self, file_path: str, format_name: str) -> dict[str, Any] | None:
        """
        Load audio file using PyAV (unified loader for all formats).

        This replaces the format-specific loaders (pydub, soundfile) with a single
        PyAV-based implementation that supports all audio formats.

        Args:
            file_path: Path to audio file
            format_name: Format name for reporting (mp3, flac, ogg, wav, aiff, etc.)

        Returns:
            Dictionary with audio data and metadata, or None on error
        """
        try:
            import av

            container = av.open(file_path)

            # Find audio stream
            audio_stream = None
            for stream in container.streams:
                if stream.type == "audio":
                    audio_stream = stream
                    break

            if not audio_stream:
                container.close()
                print(f"No audio stream found in {file_path}")
                return None

            # Decode all frames
            frames = []
            for frame in container.decode(audio_stream):
                # Convert to numpy: (channels, samples) -> (samples, channels)
                frame_data = frame.to_ndarray().astype(np.float32).T
                frames.append(frame_data)

            container.close()

            if not frames:
                print(f"No audio frames decoded from {file_path}")
                return None

            # Concatenate frames
            data = np.concatenate(frames, axis=0)

            # Ensure 2D shape (samples, channels)
            if data.ndim == 1:
                data = data.reshape(-1, 1)

            # Get bit depth from format
            bit_depth = self._get_bit_depth_from_format(audio_stream.format.name)

            return {
                "data": data,
                "sample_rate": audio_stream.sample_rate,
                "channels": audio_stream.channels,
                "format": "float32",
                "original_format": format_name,
                "bit_depth": bit_depth,
                "codec": audio_stream.codec.name if audio_stream.codec else "unknown",
            }

        except ImportError:
            print("PyAV (av) library required for audio file loading")
            return None
        except Exception as e:
            print(f"PyAV load error for {file_path}: {e}")
            return None

    def _get_bit_depth_from_format(self, format_name: str) -> int:
        """
        Get bit depth from PyAV format name.

        Args:
            format_name: PyAV format name (e.g., 'flt', 's16', 's32', 'u8')

        Returns:
            Bit depth in bits (8, 16, 24, 32, 64), defaults to 16
        """
        format_map = {
            "u8": 8,
            "s16": 16,
            "s32": 32,
            "flt": 32,
            "dbl": 64,
            "u8p": 8,
            "s16p": 16,
            "s32p": 32,
            "fltp": 32,
            "dblp": 64,
            # Common FFmpeg format names
            "pcm_s16le": 16,
            "pcm_s24le": 24,
            "pcm_s32le": 32,
            "pcm_f32le": 32,
            "pcm_f64le": 64,
            "mp3": 16,
            "aac": 16,
            "vorbis": 16,
            "flac": 24,
        }
        # Extract base format (handle variants like 'fltp' -> 'flt')
        base_format = format_name.lower().rstrip("p")
        return format_map.get(base_format, format_map.get(format_name.lower(), 16))

    def _load_raw_file(self, file_path: str) -> dict[str, Any] | None:
        """Load raw PCM file."""
        # Raw files need format specification
        # For now, assume 16-bit mono 44.1kHz
        try:
            with open(file_path, "rb") as f:
                data = f.read()
                samples = np.frombuffer(data, dtype=np.int16)
                samples = samples.astype(np.float32) / 32767.0

                return {
                    "data": samples.reshape(-1, 1),
                    "sample_rate": 44100,  # Assumed
                    "channels": 1,
                    "format": "float32",
                    "original_format": "raw",
                    "bit_depth": 16,
                }
        except Exception as e:
            print(f"Raw file load error: {e}")
            return None

    def _unpack_24bit(self, data: bytes) -> np.ndarray:
        """Unpack 24-bit packed samples to 32-bit integers."""
        samples = []
        for i in range(0, len(data), 3):
            if i + 2 < len(data):
                # Little-endian 24-bit to 32-bit
                sample_bytes = data[i : i + 3] + b"\x00"
                sample = struct.unpack("<i", sample_bytes)[0]
                # Sign extend if necessary
                if sample & 0x800000:
                    sample |= 0xFF000000
                samples.append(sample)

        return np.array(samples, dtype=np.int32)

    def convert_format(
        self, audio_data: np.ndarray, from_format: str, to_format: str, bit_depth: int = 16
    ) -> np.ndarray:
        """
        Convert between audio formats.

        Args:
            audio_data: Audio data array
            from_format: Source format
            to_format: Target format
            bit_depth: Bit depth for integer formats

        Returns:
            Converted audio data
        """
        # Convert to float32 first if needed
        if from_format in ["int8", "int16", "int24", "int32"]:
            spec = self.FORMAT_SPECS[from_format]
            if spec["numpy_dtype"]:
                # Normalize
                if from_format == "int8":
                    audio_data = audio_data.astype(np.float32) / 127.0
                elif from_format == "int16":
                    audio_data = audio_data.astype(np.float32) / 32767.0
                elif from_format == "int24":
                    audio_data = audio_data.astype(np.float32) / 8388607.0
                elif from_format == "int32":
                    audio_data = audio_data.astype(np.float32) / 2147483647.0

        # Convert to target format
        if to_format == "float32":
            return audio_data.astype(np.float32)
        elif to_format == "float64":
            return audio_data.astype(np.float64)
        elif to_format in ["int8", "int16", "int32"]:
            spec = self.FORMAT_SPECS[to_format]
            # Denormalize
            if to_format == "int8":
                converted = np.clip(audio_data * 127.0, -128, 127).astype(np.int8)
            elif to_format == "int16":
                converted = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
            elif to_format == "int32":
                converted = np.clip(audio_data * 2147483647.0, -2147483648, 2147483647).astype(
                    np.int32
                )
            return converted
        else:
            # Return as float32 for unsupported formats
            return audio_data.astype(np.float32)

    def validate_audio_data(
        self, audio_data: np.ndarray, sample_rate: int, channels: int
    ) -> dict[str, Any]:
        """
        Validate audio data and provide analysis.

        Args:
            audio_data: Audio data to validate
            sample_rate: Expected sample rate
            channels: Expected number of channels

        Returns:
            Validation results
        """
        results = {"valid": True, "errors": [], "warnings": [], "info": {}}

        # Check data type
        if not isinstance(audio_data, np.ndarray):
            results["valid"] = False
            results["errors"].append("Audio data must be numpy array")
            return results

        # Check shape
        if audio_data.ndim not in [1, 2]:
            results["valid"] = False
            results["errors"].append("Audio data must be 1D or 2D array")
            return results

        actual_channels = audio_data.shape[1] if audio_data.ndim == 2 else 1
        if actual_channels != channels:
            results["warnings"].append(
                f"Channel count mismatch: expected {channels}, got {actual_channels}"
            )

        # Check sample rate range
        if sample_rate < 8000 or sample_rate > 192000:
            results["warnings"].append(f"Unusual sample rate: {sample_rate} Hz")

        # Check for NaN or Inf values
        if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
            results["errors"].append("Audio data contains NaN or Inf values")
            results["valid"] = False

        # Check amplitude range for float data
        if audio_data.dtype in [np.float32, np.float64]:
            if np.max(np.abs(audio_data)) > 1.0:
                results["warnings"].append("Audio data exceeds normal range (>1.0)")

        # Calculate statistics
        results["info"] = {
            "shape": audio_data.shape,
            "dtype": str(audio_data.dtype),
            "duration_seconds": len(audio_data)
            / sample_rate
            / (actual_channels if audio_data.ndim == 2 else 1),
            "peak_level": float(np.max(np.abs(audio_data))),
            "rms_level": float(np.sqrt(np.mean(audio_data**2))),
        }

        return results

    def get_format_info(self, format_name: str) -> dict[str, Any] | None:
        """
        Get information about a supported format.

        Args:
            format_name: Format name

        Returns:
            Format information or None if not supported
        """
        if format_name in self.FORMAT_SPECS:
            return self.FORMAT_SPECS[format_name].copy()
        return None

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return list(self.SUPPORTED_FORMATS.keys())
