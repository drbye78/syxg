#!/usr/bin/env python3
"""
Benchmark different ADSR envelope implementations
"""

import time
import numpy as np

# Import all envelope implementations
from synth.core.envelope import ADSREnvelope as OriginalEnvelope
from synth.audio.optimized_envelope import OptimizedADSREnvelope
from synth.audio.fast_envelope import FastADSREnvelope
from synth.core.vectorized_envelope import VectorizedADSREnvelope

def benchmark_envelope(envelope_class, name, iterations=10000):
    """Benchmark a single envelope implementation"""
    print(f"Benchmarking {name}...")
    
    # Create envelope instance
    envelope = envelope_class(attack=0.1, decay=0.2, sustain=0.7, release=0.3)
    
    # Determine method names
    if hasattr(envelope, 'note_on_optimized'):
        note_on_method = envelope.note_on_optimized
        note_off_method = envelope.note_off_optimized
        process_method = envelope.process_optimized if hasattr(envelope, 'process_optimized') else envelope.process
    elif hasattr(envelope, 'note_on'):
        note_on_method = envelope.note_on
        note_off_method = envelope.note_off
        process_method = envelope.process
    else:
        print(f"  ERROR: No note_on method found for {name}")
        return 0, 0
    
    # Benchmark note_on/note_off cycle
    start_time = time.time()
    for i in range(iterations):
        note_on_method(100, 60)  # velocity=100, note=60
        # Process a few samples
        for _ in range(100):
            process_method()
        note_off_method()
        # Process release phase
        for _ in range(100):
            process_method()
    end_time = time.time()
    
    elapsed = end_time - start_time
    ops_per_second = (iterations * 200) / elapsed  # 200 process calls per iteration
    
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Operations/sec: {ops_per_second:.0f}")
    print()
    
    return elapsed, ops_per_second

def benchmark_vectorized_envelope(iterations=10000):
    """Benchmark vectorized envelope implementation"""
    print("Benchmarking Vectorized ADSR Envelope...")
    
    # Create envelope instance for 100 simultaneous voices
    envelope = VectorizedADSREnvelope(attack=0.1, decay=0.2, sustain=0.7, release=0.3)
    
    # For vectorized envelope, we need to work with the existing interface
    # Let's benchmark single voice processing to be consistent with others
    
    # Benchmark note_on/note_off cycle for single voice processing
    start_time = time.time()
    for i in range(iterations):
        # Note on
        envelope.note_on(100, 60)  # velocity=100, note=60
        # Process a few samples
        for _ in range(100):
            envelope.process()
        # Note off
        envelope.note_off()
        # Process release phase
        for _ in range(100):
            envelope.process()
    end_time = time.time()
    
    elapsed = end_time - start_time
    ops_per_second = (iterations * 200) / elapsed  # 200 process calls per iteration
    
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Operations/sec: {ops_per_second:.0f}")
    print()
    
    return elapsed, ops_per_second

def main():
    print("=== ADSR Envelope Performance Benchmark ===\n")
    
    results = []
    
    # Benchmark original envelope
    elapsed, ops = benchmark_envelope(OriginalEnvelope, "Original ADSR Envelope")
    results.append(("Original", ops))
    
    # Benchmark optimized envelope
    elapsed, ops = benchmark_envelope(OptimizedADSREnvelope, "Optimized ADSR Envelope")
    results.append(("Optimized", ops))
    
    # Benchmark fast envelope
    elapsed, ops = benchmark_envelope(FastADSREnvelope, "Fast ADSR Envelope")
    results.append(("Fast", ops))
    
    # Benchmark vectorized envelope
    elapsed, ops = benchmark_vectorized_envelope()
    results.append(("Vectorized", ops))
    
    # Print summary
    print("=== SUMMARY ===")
    results.sort(key=lambda x: x[1], reverse=True)
    for i, (name, ops_per_sec) in enumerate(results):
        print(f"{i+1}. {name}: {ops_per_sec:,.0f} operations/second")

if __name__ == "__main__":
    main()