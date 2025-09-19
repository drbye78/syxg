#!/usr/bin/env python3
"""
Detailed profiling script for MIDI to OGG conversion
"""

import cProfile
import pstats
import io
import time
import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def profile_conversion():
    """Profile the MIDI to OGG conversion process"""
    from midi_to_ogg import OptimizedMIDIToOGGConverter
    
    # Configuration for profiling
    config = {
        "sample_rate": 48000,
        "chunk_size_ms": 20,
        "max_polyphony": 64,
        "master_volume": 1.0,
        "sf2_files": ["tests/ref.sf2"]
    }
    
    # Create converter with silent mode to avoid console output interference
    converter = OptimizedMIDIToOGGConverter(config, silent=True)
    
    # Profile the conversion process
    pr = cProfile.Profile()
    pr.enable()
    
    try:
        # Convert the test MIDI file
        success = converter.convert_midi_to_ogg(
            "tests/test.mid", 
            "profile_output.ogg", 
            tempo_ratio=1.0, 
            output_format="ogg"
        )
        
        if success:
            print("Conversion completed successfully")
        else:
            print("Conversion failed")
            
    except Exception as e:
        print(f"Error during conversion: {e}")
    
    pr.disable()
    
    # Save profiling results
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats()
    
    # Save to file
    with open('conversion_profile.txt', 'w') as f:
        f.write(s.getvalue())
    
    # Also save top 100 functions by cumulative time
    s_top = io.StringIO()
    ps_top = pstats.Stats(pr, stream=s_top)
    ps_top.sort_stats('cumulative')
    ps_top.print_stats(100)
    
    with open('conversion_profile_top100.txt', 'w') as f:
        f.write(s_top.getvalue())
    
    print("Profiling completed. Results saved to conversion_profile.txt and conversion_profile_top100.txt")

def detailed_function_profiling():
    """Profile specific functions in detail"""
    from midi_to_ogg import OptimizedMIDIToOGGConverter
    import mido
    
    print("Starting detailed function profiling...")
    
    # Configuration
    config = {
        "sample_rate": 48000,
        "chunk_size_ms": 20,
        "max_polyphony": 64,
        "master_volume": 1.0,
        "sf2_files": ["tests/ref.sf2"]
    }
    
    # Create converter with silent mode
    converter = OptimizedMIDIToOGGConverter(config, silent=True)
    
    # Load MIDI file
    midi = mido.MidiFile("tests/test.mid")
    
    # Time individual functions
    print("\nTiming individual functions:")
    
    # 1. _collect_midi_messages
    start_time = time.perf_counter()
    midi_messages, sysex_messages = converter._collect_midi_messages(midi)
    collect_time = time.perf_counter() - start_time
    print(f"_collect_midi_messages: {collect_time:.4f} seconds")
    print(f"  - MIDI messages collected: {len(midi_messages)}")
    print(f"  - SYSEX messages collected: {len(sysex_messages)}")
    
    # 2. send_midi_message_block
    start_time = time.perf_counter()
    converter.synth.buffered_processor.send_midi_message_block(midi_messages, sysex_messages)
    send_time = time.perf_counter() - start_time
    print(f"send_midi_message_block: {send_time:.4f} seconds")
    
    # 3. set_buffered_mode_time
    start_time = time.perf_counter()
    for m in midi_messages:
        if 0x90 <= m[1] < 0xa0:
            converter.synth.buffered_processor.set_buffered_mode_time(m[0])
            break
    set_time = time.perf_counter() - start_time
    print(f"set_buffered_mode_time: {set_time:.6f} seconds")
    
    # 4. generate_audio_block_sample_accurate
    start_time = time.perf_counter()
    left, right = converter.synth.generate_audio_block_sample_accurate(512)  # Small block for testing
    gen_time = time.perf_counter() - start_time
    print(f"generate_audio_block_sample_accurate (512 samples): {gen_time:.4f} seconds")
    
    # 5. Multiple blocks generation
    start_time = time.perf_counter()
    block_count = 10
    for i in range(block_count):
        left, right = converter.synth.generate_audio_block_sample_accurate(512)
    multi_gen_time = time.perf_counter() - start_time
    print(f"{block_count} blocks generation: {multi_gen_time:.4f} seconds ({multi_gen_time/block_count:.4f} per block)")
    
    print("\nDetailed function profiling completed.")

def memory_usage_analysis():
    """Analyze memory usage during conversion"""
    try:
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        
        print("Starting memory usage analysis...")
        
        # Initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Initial memory usage: {initial_memory:.1f} MB")
        
        # Import and create converter
        from midi_to_ogg import OptimizedMIDIToOGGConverter
        
        config = {
            "sample_rate": 48000,
            "chunk_size_ms": 20,
            "max_polyphony": 64,
            "master_volume": 1.0,
            "sf2_files": ["tests/ref.sf2"]
        }
        
        # Memory after imports
        gc.collect()
        import_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Memory after imports: {import_memory:.1f} MB (+{import_memory - initial_memory:.1f} MB)")
        
        # Create converter
        converter = OptimizedMIDIToOGGConverter(config, silent=True)
        gc.collect()
        synth_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Memory after converter creation: {synth_memory:.1f} MB (+{synth_memory - import_memory:.1f} MB)")
        
        # Load SF2 file
        converter.synth.set_sf2_files(["tests/ref.sf2"])
        gc.collect()
        sf2_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Memory after SF2 loading: {sf2_memory:.1f} MB (+{sf2_memory - synth_memory:.1f} MB)")
        
        print("Memory usage analysis completed.")
        
    except ImportError:
        print("psutil not available for memory analysis")

def main():
    """Main profiling function"""
    print("=== MIDI to OGG Conversion Profiling ===")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if test files exist
    if not os.path.exists("tests/test.mid"):
        print("Error: tests/test.mid not found")
        return
        
    if not os.path.exists("tests/ref.sf2"):
        print("Error: tests/ref.sf2 not found")
        return
    
    # Run different profiling approaches
    print("1. Running overall conversion profiling...")
    profile_conversion()
    
    print("\n2. Running detailed function profiling...")
    detailed_function_profiling()
    
    print("\n3. Running memory usage analysis...")
    memory_usage_analysis()
    
    print("\n=== Profiling Completed ===")

if __name__ == "__main__":
    main()