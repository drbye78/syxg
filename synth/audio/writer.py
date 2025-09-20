import av
import numpy as np
from typing import Optional
from fractions import Fraction
import sys

class AudioWriter:
    """Handles writing audio data to various formats using pyav"""

    SUPPORTED_FORMATS = {
        'ogg': 'ogg',
        'wav': 'wav',
        'mp3': 'mp3',
        'aac': 'aac',
        'flac': 'flac',
        'm4a': 'aac'
    }
    
    def __init__(self, sample_rate: int, chunk_size_ms: float):
        self.sample_rate = sample_rate
        self.chunk_size_ms = chunk_size_ms
        
    def create_writer(self, output_file: str, format: str):
        """Create AV writer context"""
        try:
            return AvWriter(output_file, format, self.sample_rate)
        except ImportError as e:
            print("Error: Audio encoding requires 'av' library")
            print("Install with: pip install av")
            sys.exit(1)

class AvWriter:
    """Context manager for audio output using pyav"""

    def __init__(self, output_file: str, format: str, sample_rate: int):
        self.output_file = output_file
        self.format = format
        self.sample_rate = sample_rate
        self.container = None
        self.stream = None

    def __enter__(self):
        self.container = av.open(self.output_file, mode='w', format=self.format)
        self.stream = self.container.add_stream(self._get_codec(self.format), rate=self.sample_rate)
        
        # Set channel layout for stereo
        self.stream.layout = 'stereo'

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
            
    def write(self, left: np.ndarray, right: np.ndarray):
        """Write stereo audio block with multiple AV compatibility approaches"""
        if not self.container or not self.stream:
            return
        
        # Ensure arrays are the same length
        assert len(left) == len(right), "Left and right channels must have the same length"

        packet = np.vstack([left, right])
        
        # Create audio frame with float format
        frame = av.AudioFrame.from_ndarray(packet, format='fltp', layout='stereo')
        frame.sample_rate = self.sample_rate
        frame.time_base = Fraction(1, self.sample_rate)
        
        # Encode and write the frame
        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def _get_codec(self, format_name: str) -> str:
        """Get the appropriate codec for a given format"""
        codec_mapping = {
            'wav': 'pcm_s16le',
            'flac': 'flac',
            'mp3': 'mp3',
            'aac': 'aac',
            'ogg': 'vorbis',
            'm4a': 'aac'
        }
        return codec_mapping.get(format_name, 'vorbis')
