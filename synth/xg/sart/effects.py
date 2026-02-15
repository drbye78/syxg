"""
Effects processing for S.Art2 synthesizer.
"""

import numpy as np
from typing import List, Optional


class ReverbEffect:
    """
    Schroeder reverb implementation.
    Based on multiple comb filters in parallel and allpass filters in series.
    """
    
    def __init__(self, sample_rate: int = 44100, 
                 room_size: float = 0.5, wet_dry: float = 0.3):
        self.sample_rate = sample_rate
        self.room_size = np.clip(room_size, 0.0, 1.0)
        self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
        
        # Comb filter delays (in samples) - typical Schroeder values
        self.comb_delays = [1557, 1617, 1491, 1422, 1277, 1356]
        self.comb_buffers: List[np.ndarray] = []
        self.comb_indices: List[int] = []
        
        # Allpass filter delays
        self.allpass_delays = [225, 556, 441, 341]
        self.allpass_buffers: List[np.ndarray] = []
        self.allpass_indices: List[int] = []
        
        # Feedback coefficients based on room size
        self.comb_feedback = [0.28, 0.3, 0.26, 0.32, 0.24, 0.28]
        
        self._initialize_buffers()
    
    def _initialize_buffers(self):
        """Initialize delay buffers."""
        for delay in self.comb_delays:
            self.comb_buffers.append(np.zeros(delay))
            self.comb_indices.append(0)
        
        for delay in self.allpass_delays:
            self.allpass_buffers.append(np.zeros(delay))
            self.allpass_indices.append(0)
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through reverb."""
        if len(audio) == 0:
            return audio
        
        # Ensure stereo
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=1)
        
        output = np.zeros_like(audio)
        
        # Process through comb filters (parallel)
        for comb_idx in range(len(self.comb_buffers)):
            buffer = self.comb_buffers[comb_idx]
            idx = self.comb_indices[comb_idx]
            delay = self.comb_delays[comb_idx]
            feedback = self.comb_feedback[comb_idx] * self.room_size
            
            for sample_idx in range(len(audio)):
                # Read delayed sample
                read_idx = (idx - delay) % len(buffer)
                delayed = buffer[read_idx]
                
                # Write new sample with feedback
                buffer[idx] = audio[sample_idx, 0] + delayed * feedback
                
                # Add to output
                output[sample_idx, 0] += delayed
                output[sample_idx, 1] += delayed
                
                # Advance index
                idx = (idx + 1) % len(buffer)
            
            self.comb_indices[comb_idx] = idx
        
        # Mix wet/dry
        wet_gain = self.wet_dry * 0.5
        dry_gain = 1.0 - wet_gain * 0.5
        output = audio * dry_gain + output * wet_gain
        
        # Apply allpass filters (series) for diffusion
        for allpass_idx in range(len(self.allpass_buffers)):
            buffer = self.allpass_buffers[allpass_idx]
            idx = self.allpass_indices[allpass_idx]
            
            for sample_idx in range(len(output)):
                delayed = buffer[idx]
                # Allpass filter: output = input + feedback * delayed
                allpass_out = output[sample_idx, 0] + delayed * 0.5
                buffer[idx] = allpass_out - delayed * 0.5
                
                # Apply to both channels
                output[sample_idx, 0] = allpass_out
                output[sample_idx, 1] = allpass_out
                
                idx = (idx + 1) % len(buffer)
            
            self.allpass_indices[allpass_idx] = idx
        
        # Normalize and clip
        max_val = np.max(np.abs(output))
        if max_val > 0.95:
            output = output / max_val * 0.95
        
        return output
    
    def set_parameters(self, room_size: Optional[float] = None, wet_dry: Optional[float] = None):
        """Update reverb parameters."""
        if room_size is not None:
            self.room_size = np.clip(room_size, 0.0, 1.0)
        if wet_dry is not None:
            self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
    
    def reset(self):
        """Clear all buffers."""
        for buffer in self.comb_buffers:
            buffer.fill(0)
        for buffer in self.allpass_buffers:
            buffer.fill(0)
        self.comb_indices = [0] * len(self.comb_indices)
        self.allpass_indices = [0] * len(self.allpass_indices)


class DelayEffect:
    """
    Delay effect with feedback and stereo support.
    """
    
    def __init__(self, sample_rate: int = 44100,
                 delay_time: float = 0.375, feedback: float = 0.3, wet_dry: float = 0.2):
        self.sample_rate = sample_rate
        self.delay_time = delay_time
        self.feedback = np.clip(feedback, 0.0, 0.95)
        self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
        
        # Stereo delay buffers
        delay_samples = int(delay_time * sample_rate)
        self.delay_samples = max(delay_samples, 1)
        self.buffer = np.zeros((self.delay_samples * 2, 2))
        self.write_index = 0
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through delay."""
        if len(audio) == 0:
            return audio
        
        # Ensure stereo
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=1)
        
        output = np.zeros_like(audio)
        
        for i in range(len(audio)):
            # Read delayed sample from circular buffer
            read_index = (self.write_index - self.delay_samples) % len(self.buffer)
            delayed = self.buffer[read_index]
            
            # Mix dry and wet signals
            output[i] = audio[i] + delayed * self.wet_dry
            
            # Write to buffer with feedback (stereo)
            self.buffer[self.write_index] = audio[i] + delayed * self.feedback
            
            # Advance write index
            self.write_index = (self.write_index + 1) % len(self.buffer)
        
        return output
    
    def set_parameters(self, delay_time: Optional[float] = None,
                       feedback: Optional[float] = None, wet_dry: Optional[float] = None):
        """Update delay parameters."""
        if delay_time is not None:
            self.delay_time = delay_time
            delay_samples = int(delay_time * self.sample_rate)
            self.delay_samples = max(delay_samples, 1)
            # Recreate buffer with new size
            self.buffer = np.zeros((self.delay_samples * 2, 2))
            self.write_index = 0
        if feedback is not None:
            self.feedback = np.clip(feedback, 0.0, 0.95)
        if wet_dry is not None:
            self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
    
    def reset(self):
        """Clear delay buffer."""
        self.buffer.fill(0)
        self.write_index = 0
