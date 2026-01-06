"""
Sample Format Handler - Audio Format Conversion and Processing

Provides comprehensive audio format conversion, validation, and processing
capabilities for the XG synthesizer's sample management system.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
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
        'wav': ['.wav', '.wave'],
        'aiff': ['.aiff', '.aif'],
        'flac': ['.flac'],
        'ogg': ['.ogg'],
        'mp3': ['.mp3'],
        'raw': ['.raw', '.pcm']
    }

    # Format specifications
    FORMAT_SPECS = {
        'int8': {'bits': 8, 'signed': True, 'numpy_dtype': np.int8},
        'int16': {'bits': 16, 'signed': True, 'numpy_dtype': np.int16},
        'int24': {'bits': 24, 'signed': True, 'numpy_dtype': None},  # Special handling
        'int32': {'bits': 32, 'signed': True, 'numpy_dtype': np.int32},
        'float32': {'bits': 32, 'signed': False, 'numpy_dtype': np.float32},
        'float64': {'bits': 64, 'signed': False, 'numpy_dtype': np.float64}
    }

    def __init__(self):
        """Initialize format handler."""
        self.format_cache = {}
        self.conversion_cache = {}

    def detect_format(self, file_path: str) -> Optional[str]:
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
            with open(file_path, 'rb') as f:
                header = f.read(12)
                return self._detect_format_from_header(header)
        except:
            pass

        return None

    def _detect_format_from_header(self, header: bytes) -> Optional[str]:
        """Detect format from file header bytes."""
        if len(header) < 4:
            return None

        # WAV detection
        if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
            return 'wav'

        # AIFF detection
        if header.startswith(b'FORM') and header[8:12] == b'AIFF':
            return 'aiff'

        # FLAC detection
        if header.startswith(b'fLaC'):
            return 'flac'

        # OGG detection
        if header.startswith(b'OggS'):
            return 'ogg'

        # MP3 detection (simplified)
        if header.startswith(b'\xFF\xFB') or header.startswith(b'\xFF\xF3') or header.startswith(b'\xFF\xF2'):
            return 'mp3'

        return None

    def load_audio_file(self, file_path: str) -> Optional[Dict[str, Any]]:
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
            if fmt == 'wav':
                return self._load_wav_file(file_path)
            elif fmt == 'aiff':
                return self._load_aiff_file(file_path)
            elif fmt == 'flac':
                return self._load_flac_file(file_path)
            elif fmt == 'ogg':
                return self._load_ogg_file(file_path)
            elif fmt == 'mp3':
                return self._load_mp3_file(file_path)
            else:
                return self._load_raw_file(file_path)
        except Exception as e:
            print(f"Error loading {fmt} file {file_path}: {e}")
            return None

    def _load_wav_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load WAV file."""
        try:
            with wave.open(file_path, 'rb') as wav_file:
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
                    'data': data,
                    'sample_rate': sample_rate,
                    'channels': n_channels,
                    'format': 'float32',
                    'original_format': 'wav',
                    'bit_depth': sample_width * 8
                }

        except Exception as e:
            print(f"WAV load error: {e}")
            return None

    def _load_aiff_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load AIFF file (simplified implementation)."""
        # AIFF loading would require aiff-specific library
        # For now, return None to indicate not implemented
        return None

    def _load_flac_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load FLAC file."""
        try:
            import soundfile as sf
            data, sample_rate = sf.read(file_path, dtype='float32')
            return {
                'data': data if data.ndim == 2 else data.reshape(-1, 1),
                'sample_rate': sample_rate,
                'channels': data.shape[1] if data.ndim == 2 else 1,
                'format': 'float32',
                'original_format': 'flac',
                'bit_depth': 24  # FLAC typically 24-bit
            }
        except ImportError:
            print("soundfile library required for FLAC support")
            return None
        except Exception as e:
            print(f"FLAC load error: {e}")
            return None

    def _load_ogg_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load OGG file."""
        try:
            import soundfile as sf
            data, sample_rate = sf.read(file_path, dtype='float32')
            return {
                'data': data if data.ndim == 2 else data.reshape(-1, 1),
                'sample_rate': sample_rate,
                'channels': data.shape[1] if data.ndim == 2 else 1,
                'format': 'float32',
                'original_format': 'ogg',
                'bit_depth': 16
            }
        except ImportError:
            print("soundfile library required for OGG support")
            return None
        except Exception as e:
            print(f"OGG load error: {e}")
            return None

    def _load_mp3_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load MP3 file."""
        try:
            import pydub
            audio = pydub.AudioSegment.from_mp3(file_path)
            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                samples = samples.reshape(-1, 2)

            # Normalize
            samples = samples.astype(np.float32)
            if audio.sample_width == 2:
                samples /= 32767.0
            elif audio.sample_width == 1:
                samples /= 127.0

            return {
                'data': samples,
                'sample_rate': audio.frame_rate,
                'channels': audio.channels,
                'format': 'float32',
                'original_format': 'mp3',
                'bit_depth': audio.sample_width * 8
            }
        except ImportError:
            print("pydub library required for MP3 support")
            return None
        except Exception as e:
            print(f"MP3 load error: {e}")
            return None

    def _load_raw_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load raw PCM file."""
        # Raw files need format specification
        # For now, assume 16-bit mono 44.1kHz
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                samples = np.frombuffer(data, dtype=np.int16)
                samples = samples.astype(np.float32) / 32767.0

                return {
                    'data': samples.reshape(-1, 1),
                    'sample_rate': 44100,  # Assumed
                    'channels': 1,
                    'format': 'float32',
                    'original_format': 'raw',
                    'bit_depth': 16
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
                sample_bytes = data[i:i+3] + b'\x00'
                sample = struct.unpack('<i', sample_bytes)[0]
                # Sign extend if necessary
                if sample & 0x800000:
                    sample |= 0xFF000000
                samples.append(sample)

        return np.array(samples, dtype=np.int32)

    def convert_format(self, audio_data: np.ndarray, from_format: str,
                      to_format: str, bit_depth: int = 16) -> np.ndarray:
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
        if from_format in ['int8', 'int16', 'int24', 'int32']:
            spec = self.FORMAT_SPECS[from_format]
            if spec['numpy_dtype']:
                # Normalize
                if from_format == 'int8':
                    audio_data = audio_data.astype(np.float32) / 127.0
                elif from_format == 'int16':
                    audio_data = audio_data.astype(np.float32) / 32767.0
                elif from_format == 'int24':
                    audio_data = audio_data.astype(np.float32) / 8388607.0
                elif from_format == 'int32':
                    audio_data = audio_data.astype(np.float32) / 2147483647.0

        # Convert to target format
        if to_format == 'float32':
            return audio_data.astype(np.float32)
        elif to_format == 'float64':
            return audio_data.astype(np.float64)
        elif to_format in ['int8', 'int16', 'int32']:
            spec = self.FORMAT_SPECS[to_format]
            # Denormalize
            if to_format == 'int8':
                converted = np.clip(audio_data * 127.0, -128, 127).astype(np.int8)
            elif to_format == 'int16':
                converted = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
            elif to_format == 'int32':
                converted = np.clip(audio_data * 2147483647.0, -2147483648, 2147483647).astype(np.int32)
            return converted
        else:
            # Return as float32 for unsupported formats
            return audio_data.astype(np.float32)

    def validate_audio_data(self, audio_data: np.ndarray,
                           sample_rate: int, channels: int) -> Dict[str, Any]:
        """
        Validate audio data and provide analysis.

        Args:
            audio_data: Audio data to validate
            sample_rate: Expected sample rate
            channels: Expected number of channels

        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }

        # Check data type
        if not isinstance(audio_data, np.ndarray):
            results['valid'] = False
            results['errors'].append("Audio data must be numpy array")
            return results

        # Check shape
        if audio_data.ndim not in [1, 2]:
            results['valid'] = False
            results['errors'].append("Audio data must be 1D or 2D array")
            return results

        actual_channels = audio_data.shape[1] if audio_data.ndim == 2 else 1
        if actual_channels != channels:
            results['warnings'].append(f"Channel count mismatch: expected {channels}, got {actual_channels}")

        # Check sample rate range
        if sample_rate < 8000 or sample_rate > 192000:
            results['warnings'].append(f"Unusual sample rate: {sample_rate} Hz")

        # Check for NaN or Inf values
        if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
            results['errors'].append("Audio data contains NaN or Inf values")
            results['valid'] = False

        # Check amplitude range for float data
        if audio_data.dtype in [np.float32, np.float64]:
            if np.max(np.abs(audio_data)) > 1.0:
                results['warnings'].append("Audio data exceeds normal range (>1.0)")

        # Calculate statistics
        results['info'] = {
            'shape': audio_data.shape,
            'dtype': str(audio_data.dtype),
            'duration_seconds': len(audio_data) / sample_rate / (actual_channels if audio_data.ndim == 2 else 1),
            'peak_level': float(np.max(np.abs(audio_data))),
            'rms_level': float(np.sqrt(np.mean(audio_data**2)))
        }

        return results

    def get_format_info(self, format_name: str) -> Optional[Dict[str, Any]]:
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

    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        return list(self.SUPPORTED_FORMATS.keys())
