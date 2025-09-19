#!/usr/bin/env python3
"""
Benchmark script to test performance of different AudioEngine and ADSREnvelope implementations
"""

import time
import numpy as np
from typing import List, Tuple

# Import all implementations
from synth.audio.engine import AudioEngine
from synth.audio.optimized_engine import OptimizedAudioEngine
from synth.audio.vectorized_engine import VectorizedAudioEngine

from synth.core.envelope import ADSREnvelope
from synth.core.vectorized_envelope import VectorizedADSREnvelope
from synth.audio.optimized_envelope import OptimizedADSREnvelope
from synth.audio.fast_envelope import FastADSREnvelope

class DummyChannelRenderer:
    """Dummy channel renderer for testing audio engines"""
    def __init__(self, active=True):
        self._active = active
        self.sample_count = 0
    
    def is_active(self):
        return self._active
    
    def generate_sample(self):
        self.sample_count += 1
        # Generate some dummy audio data
        left = np.sin(self.sample_count * 0.01) * 0.1
        right = np.cos(self.sample_count * 0.01) * 0.1
        return left, right
    
    def generate_sample_block_vectorized(self, block_size):
        # Generate block of dummy audio data
        samples = np.arange(self.sample_count, self.sample_count + block_size)
        self.sample_count += block_size
        left = np.sin(samples * 0.01) * 0.1
        right = np.cos(samples * 0.01) * 0.1
        return left.astype(np.float32), right.astype(np.float32)

class DummyEffectManager:
    """Dummy effect manager for testing audio engines"""
    def process_audio(self, input_channels, block_size):
        # Simple dummy processing that just returns the input
        return input_channels
    
    def process_stereo_audio_vectorized(self, stereo_input):
        # Simple dummy processing that just returns the input
        return stereo_input

def benchmark_audio_engines():
    """Benchmark different AudioEngine implementations"""
    print("Benchmarking AudioEngine implementations...")
    print("=" * 50)
    
    # Test parameters
    sample_rate = 48000
    block_size = 512
    num_channels = 16
    num_blocks = 100
    
    # Create dummy renderers and effect manager
    channel_renderers = [DummyChannelRenderer() for _ in range(num_channels)]
    effect_manager = DummyEffectManager()
    
    # Test original AudioEngine
    print("Testing original AudioEngine...")
    engine1 = AudioEngine(sample_rate, block_size, num_channels)
    start_time = time.time()
    for _ in range(num_blocks):
        left, right = engine1.generate_audio_block(channel_renderers, effect_manager, block_size)
    time1 = time.time() - start_time
    print(f"Original AudioEngine: {time1:.4f} seconds")
    
    # Test OptimizedAudioEngine
    print("Testing OptimizedAudioEngine...")
    engine2 = OptimizedAudioEngine(sample_rate, block_size, num_channels)
    start_time = time.time()
    for _ in range(num_blocks):
        left, right = engine2.generate_audio_block(channel_renderers, effect_manager, block_size)
    time2 = time.time() - start_time
    print(f"OptimizedAudioEngine: {time2:.4f} seconds")
    
    # Test VectorizedAudioEngine
    print("Testing VectorizedAudioEngine...")
    engine3 = VectorizedAudioEngine(sample_rate, block_size, num_channels)
    start_time = time.time()
    for _ in range(num_blocks):
        left, right = engine3.generate_audio_block(channel_renderers, effect_manager, block_size)
    time3 = time.time() - start_time
    print(f"VectorizedAudioEngine: {time3:.4f} seconds")
    
    # Calculate speedups
    if time2 > 0:
        speedup2 = time1 / time2
        print(f"OptimizedAudioEngine speedup: {speedup2:.2f}x")
    
    if time3 > 0:
        speedup3 = time1 / time3
        print(f"VectorizedAudioEngine speedup: {speedup3:.2f}x")
    
    print()

def benchmark_adsr_envelopes():
    """Benchmark different ADSREnvelope implementations"""
    print("Benchmarking ADSREnvelope implementations...")
    print("=" * 50)
    
    # Test parameters
    num_envelopes = 1000
    num_samples = 1000
    
    # Test original ADSREnvelope
    print("Testing original ADSREnvelope...")
    envelopes1 = [ADSREnvelope() for _ in range(num_envelopes)]
    start_time = time.time()
    for envelope in envelopes1:
        envelope.note_on(velocity=100, note=60)
        for _ in range(num_samples):
            level = envelope.process()
    time1 = time.time() - start_time
    print(f"Original ADSREnvelope: {time1:.4f} seconds")
    
    # Test VectorizedADSREnvelope
    print("Testing VectorizedADSREnvelope...")
    envelope2 = VectorizedADSREnvelope()
    velocities = np.full(num_envelopes, 100, dtype=np.float32)
    notes = np.full(num_envelopes, 60, dtype=np.float32)
    start_time = time.time()
    envelope2.note_on_vectorized(velocities, notes)
    for _ in range(num_samples):
        levels = envelope2.process_block_vectorized(num_envelopes)
    time2 = time.time() - start_time
    print(f"VectorizedADSREnvelope: {time2:.4f} seconds")
    
    # Test OptimizedADSREnvelope
    print("Testing OptimizedADSREnvelope...")
    envelopes3 = [OptimizedADSREnvelope() for _ in range(num_envelopes)]
    start_time = time.time()
    for envelope in envelopes3:
        envelope.note_on(velocity=100, note=60)
        for _ in range(num_samples):
            level = envelope.process()
    time3 = time.time() - start_time
    print(f"OptimizedADSREnvelope: {time3:.4f} seconds")
    
    # Test FastADSREnvelope
    print("Testing FastADSREnvelope...")
    envelopes4 = [FastADSREnvelope() for _ in range(num_envelopes)]
    start_time = time.time()
    for envelope in envelopes4:
        envelope.note_on(velocity=100, note=60)
        for _ in range(num_samples):
            level = envelope.process()
    time4 = time.time() - start_time
    print(f"FastADSREnvelope: {time4:.4f} seconds")
    
    # Calculate speedups
    if time2 > 0:
        speedup2 = time1 / time2
        print(f"VectorizedADSREnvelope speedup: {speedup2:.2f}x")
    
    if time3 > 0:
        speedup3 = time1 / time3
        print(f"OptimizedADSREnvelope speedup: {speedup3:.2f}x")
    
    if time4 > 0:
        speedup4 = time1 / time4
        print(f"FastADSREnvelope speedup: {speedup4:.2f}x")
    
    print()

def main():
    """Main benchmark function"""
    print("Performance Benchmark for XG Synthesizer Implementations")
    print("=" * 60)
    
    # Run benchmarks
    benchmark_audio_engines()
    benchmark_adsr_envelopes()
    
    print("Benchmark completed!")

if __name__ == "__main__":
    main()