#!/usr/bin/env python3
"""
Benchmark different AudioEngine implementations
"""

import time
import numpy as np

# Import all audio engine implementations
from synth.audio.engine import AudioEngine as OriginalEngine
from synth.audio.optimized_engine import OptimizedAudioEngine
from synth.audio.vectorized_engine import VectorizedAudioEngine

def create_mock_channel_renderers(num_renderers=16):
    """Create mock channel renderers for testing"""
    class MockChannelRenderer:
        def __init__(self, channel_id):
            self.channel = channel_id
            self.active = True
            
        def is_active(self):
            return self.active
            
        def generate_sample_block(self, block_size):
            # Generate mock audio data
            left = np.random.randn(block_size).astype(np.float32) * 0.1
            right = np.random.randn(block_size).astype(np.float32) * 0.1
            return left, right
    
    return [MockChannelRenderer(i) for i in range(num_renderers)]

def benchmark_audio_engine(engine_class, name, iterations=1000):
    """Benchmark a single audio engine implementation"""
    print(f"Benchmarking {name}...")
    
    # Create audio engine instance
    engine = engine_class(sample_rate=48000, block_size=512, num_channels=16)
    
    # Create mock channel renderers
    channel_renderers = create_mock_channel_renderers(16)
    
    # Mock effect manager
    class MockEffectManager:
        def process_audio(self, input_channels, block_size):
            # Simple passthrough for benchmarking
            return input_channels
            
        def reset(self):
            pass
    
    effect_manager = MockEffectManager()
    
    # Benchmark audio generation
    start_time = time.time()
    for i in range(iterations):
        left, right = engine.generate_audio_block(channel_renderers, effect_manager, 512)
    end_time = time.time()
    
    elapsed = end_time - start_time
    blocks_per_second = iterations / elapsed
    samples_per_second = blocks_per_second * 512
    
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Blocks/sec: {blocks_per_second:.0f}")
    print(f"  Samples/sec: {samples_per_second:,.0f}")
    print()
    
    return elapsed, blocks_per_second, samples_per_second

def main():
    print("=== Audio Engine Performance Benchmark ===\n")
    
    results = []
    
    # Benchmark original engine
    elapsed, blocks, samples = benchmark_audio_engine(OriginalEngine, "Original Audio Engine")
    results.append(("Original", samples))
    
    # Benchmark optimized engine
    elapsed, blocks, samples = benchmark_audio_engine(OptimizedAudioEngine, "Optimized Audio Engine")
    results.append(("Optimized", samples))
    
    # Benchmark vectorized engine
    elapsed, blocks, samples = benchmark_audio_engine(VectorizedAudioEngine, "Vectorized Audio Engine")
    results.append(("Vectorized", samples))
    
    # Print summary
    print("=== SUMMARY ===")
    results.sort(key=lambda x: x[1], reverse=True)
    for i, (name, samples_per_sec) in enumerate(results):
        print(f"{i+1}. {name}: {samples_per_sec:,.0f} samples/second")

if __name__ == "__main__":
    main()