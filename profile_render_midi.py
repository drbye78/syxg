#!/usr/bin/env python3
"""
MIDI Rendering Profiler - Performance Analysis Tool

Profiles the render_midi.py script to identify performance bottlenecks
in the XG synthesizer audio rendering pipeline.
"""

import os
import sys
import cProfile
import pstats
import io
import time
from typing import Dict, List, Any

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_profiling_wrapper():
    """Create a profiling wrapper for the render_midi functions"""

    # Import after path is set
    from synth.engine.optimized_xg_synthesizer import OptimizedXGSynthesizer
    from synth.audio.writer import AudioWriter
    from synth.midi.parser import MIDIParser
    import threading

    # Profiling data storage
    profiling_data = {
        'function_calls': {},
        'timing_breakdown': {},
        'memory_usage': {},
        'bottleneck_analysis': {}
    }

    def profile_function_call(func_name: str):
        """Decorator to profile function calls"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Track function entry
                if func_name not in profiling_data['function_calls']:
                    profiling_data['function_calls'][func_name] = {
                        'calls': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0,
                        'max_time': 0.0
                    }

                profiling_data['function_calls'][func_name]['calls'] += 1

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time

                    # Update timing statistics
                    stats = profiling_data['function_calls'][func_name]
                    stats['total_time'] += execution_time
                    stats['max_time'] = max(stats['max_time'], execution_time)
                    stats['avg_time'] = stats['total_time'] / stats['calls']

            return wrapper
        return decorator

    @profile_function_call("audio_block_generation")
    def profile_audio_block_generation(synthesizer, duration: float) -> Dict[str, float]:
        """Profile audio block generation performance"""
        block_times = []
        total_blocks = 0
        start_time = time.perf_counter()

        while synthesizer.get_current_time() < duration:
            block_start = time.perf_counter()
            synthesizer.generate_audio_block()
            block_end = time.perf_counter()

            block_times.append(block_end - block_start)
            total_blocks += 1

        end_time = time.perf_counter()
        total_time = end_time - start_time

        return {
            'total_time': total_time,
            'total_blocks': total_blocks,
            'avg_block_time': sum(block_times) / len(block_times) if block_times else 0,
            'max_block_time': max(block_times) if block_times else 0,
            'min_block_time': min(block_times) if block_times else 0,
            'blocks_per_second': total_blocks / total_time if total_time > 0 else 0
        }

    @profile_function_call("midi_message_processing")
    def profile_midi_message_processing(synthesizer, messages: List) -> Dict[str, float]:
        """Profile MIDI message processing performance"""
        start_time = time.perf_counter()

        synthesizer.send_midi_message_block(messages)

        end_time = time.perf_counter()
        processing_time = end_time - start_time

        return {
            'total_time': processing_time,
            'messages_per_second': len(messages) / processing_time if processing_time > 0 else 0,
            'avg_time_per_message': processing_time / len(messages) if messages else 0
        }

    @profile_function_call("synthesizer_initialization")
    def profile_synthesizer_initialization(sample_rate: int, max_polyphony: int) -> Dict[str, float]:
        """Profile synthesizer initialization performance"""
        start_time = time.perf_counter()

        synthesizer = OptimizedXGSynthesizer(
            sample_rate=sample_rate,
            max_polyphony=max_polyphony
        )

        end_time = time.perf_counter()
        init_time = end_time - start_time

        return {
            'initialization_time': init_time,
            'sample_rate': sample_rate,
            'max_polyphony': max_polyphony
        }

    def run_comprehensive_profiling(input_file: str, output_file: str = "/tmp/test_output.wav") -> Dict[str, Any]:
        """Run comprehensive profiling of the MIDI rendering pipeline"""

        print(f"🔍 Starting comprehensive profiling of {input_file}")

        # Profile synthesizer initialization
        print("📊 Profiling synthesizer initialization...")
        init_stats = profile_synthesizer_initialization(48000, 64)

        # Load and parse MIDI file
        print("📊 Profiling MIDI file parsing...")
        midi_start = time.perf_counter()
        parser = MIDIParser(input_file)
        all_messages = parser.get_all_messages()
        midi_end = time.perf_counter()
        midi_parse_time = midi_end - midi_start

        # Profile MIDI message processing
        print("📊 Profiling MIDI message processing...")
        msg_stats = profile_midi_message_processing(init_stats['synthesizer'], all_messages)

        # Profile audio block generation
        print("📊 Profiling audio block generation...")
        duration = min(parser.get_total_duration(), 10.0)  # Limit to 10 seconds for profiling
        block_stats = profile_audio_block_generation(init_stats['synthesizer'], duration)

        # Compile comprehensive results
        results = {
            'profiling_summary': {
                'total_profiling_time': sum([
                    init_stats['initialization_time'],
                    midi_parse_time,
                    msg_stats['total_time'],
                    block_stats['total_time']
                ]),
                'midi_file_info': {
                    'duration': parser.get_total_duration(),
                    'message_count': len(all_messages),
                    'parse_time': midi_parse_time
                }
            },
            'component_breakdown': {
                'synthesizer_initialization': init_stats,
                'midi_parsing': {
                    'parse_time': midi_parse_time,
                    'messages_per_second': len(all_messages) / midi_parse_time if midi_parse_time > 0 else 0
                },
                'midi_message_processing': msg_stats,
                'audio_block_generation': block_stats
            },
            'function_call_statistics': profiling_data['function_calls'],
            'bottleneck_analysis': analyze_bottlenecks(profiling_data, block_stats, msg_stats)
        }

        return results

    def analyze_bottlenecks(profiling_data: Dict, block_stats: Dict, msg_stats: Dict) -> Dict[str, Any]:
        """Analyze profiling data to identify performance bottlenecks"""

        bottlenecks = {}

        # Analyze function call statistics
        if profiling_data['function_calls']:
            sorted_functions = sorted(
                profiling_data['function_calls'].items(),
                key=lambda x: x[1]['total_time'],
                reverse=True
            )

            bottlenecks['top_functions_by_time'] = [
                {
                    'function': name,
                    'total_time': stats['total_time'],
                    'calls': stats['calls'],
                    'avg_time': stats['avg_time'],
                    'percentage': (stats['total_time'] / sum(f[1]['total_time'] for f in sorted_functions)) * 100
                }
                for name, stats in sorted_functions[:10]  # Top 10 functions
            ]

        # Analyze block generation performance
        if block_stats['total_blocks'] > 0:
            bottlenecks['block_generation'] = {
                'avg_block_time_ms': block_stats['avg_block_time'] * 1000,
                'max_block_time_ms': block_stats['max_block_time'] * 1000,
                'blocks_per_second': block_stats['blocks_per_second'],
                'real_time_factor': block_stats['avg_block_time'] / (1.0 / 48000),  # Assuming 48kHz
                'performance_rating': 'EXCELLENT' if block_stats['avg_block_time'] < 0.001
                                   else 'GOOD' if block_stats['avg_block_time'] < 0.005
                                   else 'FAIR' if block_stats['avg_block_time'] < 0.010
                                   else 'POOR'
            }

        # Analyze MIDI processing performance
        if msg_stats['messages_per_second'] > 0:
            bottlenecks['midi_processing'] = {
                'messages_per_second': msg_stats['messages_per_second'],
                'avg_time_per_message_ms': msg_stats['avg_time_per_message'] * 1000,
                'performance_rating': 'EXCELLENT' if msg_stats['avg_time_per_message'] < 0.001
                                   else 'GOOD' if msg_stats['avg_time_per_message'] < 0.005
                                   else 'FAIR' if msg_stats['avg_time_per_message'] < 0.010
                                   else 'POOR'
            }

        return bottlenecks

    return run_comprehensive_profiling

def run_detailed_cprofile_analysis(input_file: str) -> str:
    """Run detailed cProfile analysis of the rendering process"""

    print(f"🔍 Running detailed cProfile analysis of {input_file}")

    # Import the main conversion function
    from render_midi import convert_midi_to_audio_buffered
    from synth.engine.optimized_xg_synthesizer import OptimizedXGSynthesizer
    from synth.audio.writer import AudioWriter
    from synth.midi.parser import MIDIParser

    def profiled_conversion():
        """Conversion function wrapped for profiling"""
        try:
            # Initialize components
            synthesizer = OptimizedXGSynthesizer(sample_rate=48000, max_polyphony=64)
            audio_writer = AudioWriter(48000, 50)

            # Parse MIDI file
            parser = MIDIParser(input_file)
            all_messages = parser.get_all_messages()

            # Process messages
            synthesizer.reset()
            synthesizer.send_midi_message_block(all_messages)

            # Generate audio (limited duration for profiling)
            duration = min(parser.get_total_duration(), 5.0)  # Limit to 5 seconds

            writer = audio_writer.create_writer("/tmp/profile_test.wav", "wav")

            with writer:
                while synthesizer.get_current_time() < duration:
                    out_buffer = synthesizer.generate_audio_block()
                    writer.write(out_buffer)

        except Exception as e:
            print(f"Error during profiled conversion: {e}")

    # Run cProfile
    pr = cProfile.Profile()
    pr.enable()

    profiled_conversion()

    pr.disable()

    # Save detailed stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(50)  # Top 50 functions

    return s.getvalue()

def main():
    """Main profiling function"""
    if len(sys.argv) != 2:
        print("Usage: python profile_render_midi.py <midi_file>")
        print("Example: python profile_render_midi.py tests/test.mid")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    print("🎯 MIDI Rendering Performance Profiler")
    print("=" * 50)

    # Run comprehensive profiling
    run_profiling = create_profiling_wrapper()
    results = run_profiling(input_file, "/tmp/profile_test.wav")

    # Run detailed cProfile analysis
    print("\n📊 Running detailed cProfile analysis...")
    cprofile_output = run_detailed_cprofile_analysis(input_file)

    # Print comprehensive results
    print("\n" + "=" * 60)
    print("📈 PROFILING RESULTS SUMMARY")
    print("=" * 60)

    # Overall timing breakdown
    summary = results['profiling_summary']
    print("⏱️  TIMING BREAKDOWN:")
    print(f"   • Total profiling time: {summary['total_profiling_time']:.3f}s")
    print(f"   • MIDI file duration: {summary['midi_file_info']['duration']:.2f}s")
    print(f"   • MIDI messages: {summary['midi_file_info']['message_count']}")
    print(f"   • Parse time: {summary['midi_file_info']['parse_time']:.3f}s")

    # Component breakdown
    components = results['component_breakdown']
    print("\n🔧 COMPONENT PERFORMANCE:")
    print(f"   • Initialization: {components['synthesizer_initialization']['initialization_time']:.3f}s")
    print(f"   • MIDI processing: {components['midi_message_processing']['total_time']:.3f}s")
    print(f"   • Audio generation: {components['audio_block_generation']['total_time']:.3f}s")

    # Bottleneck analysis
    bottlenecks = results['bottleneck_analysis']
    print("\n🚨 BOTTLENECK ANALYSIS:")

    if 'block_generation' in bottlenecks:
        bg = bottlenecks['block_generation']
        print("   🎵 AUDIO BLOCK GENERATION:")
        print(f"      • Avg block time: {bg['avg_block_time_ms']:.2f}ms")
        print(f"      • Max block time: {bg['max_block_time_ms']:.2f}ms")
        print(f"      • Blocks/second: {bg['blocks_per_second']:.1f}")
        print(f"      • Performance: {bg['performance_rating']}")

    if 'midi_processing' in bottlenecks:
        mp = bottlenecks['midi_processing']
        print("   🎹 MIDI PROCESSING:")
        print(f"      • Messages/second: {mp['messages_per_second']:.0f}")
        print(f"      • Avg time/msg: {mp['avg_time_per_message_ms']:.3f}ms")
        print(f"      • Performance: {mp['performance_rating']}")

    if 'top_functions_by_time' in bottlenecks:
        print("   🔝 TOP FUNCTIONS BY EXECUTION TIME:")
        for func in bottlenecks['top_functions_by_time'][:5]:  # Show top 5
            print(f"      • {func['function']}: {func['total_time']:.3f}s ({func['percentage']:.1f}%)")

    # Recommendations
    print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
    if 'block_generation' in bottlenecks:
        bg = bottlenecks['block_generation']
        if bg['performance_rating'] in ['FAIR', 'POOR']:
            print("   ⚠️  Audio block generation is a major bottleneck")
            print("      → Consider optimizing per-sample processing loops")
            print("      → Implement true vectorized batch processing")
            print("      → Review XG controller parameter update frequency")

    if 'midi_processing' in bottlenecks:
        mp = bottlenecks['midi_processing']
        if mp['performance_rating'] in ['FAIR', 'POOR']:
            print("   ⚠️  MIDI message processing is a bottleneck")
            print("      → Consider batching MIDI message processing")
            print("      → Optimize voice allocation algorithms")
            print("      → Implement message buffering strategies")

    # Save detailed cProfile output
    with open('/tmp/cprofile_output.txt', 'w') as f:
        f.write("DETAILED CPROFILE ANALYSIS\n")
        f.write("=" * 40 + "\n")
        f.write(cprofile_output)

    print("\n📋 Detailed cProfile analysis saved to: /tmp/cprofile_output.txt")

    # Calculate efficiency metrics
    total_time = summary['total_profiling_time']
    audio_gen_time = components['audio_block_generation']['total_time']
    efficiency = (audio_gen_time / total_time) * 100 if total_time > 0 else 0

    print("\n📊 EFFICIENCY METRICS:")
    print(f"   • Audio generation efficiency: {efficiency:.1f}%")
    if 'block_generation' in bottlenecks:
        bg = bottlenecks['block_generation']
        print(f"   • Real-time performance factor: {bg.get('real_time_factor', 0):.2f}x")

        if efficiency < 70:
            print("   ⚠️  Low efficiency - significant optimization needed")
        elif efficiency < 85:
            print("   ℹ️  Moderate efficiency - some optimization beneficial")
        else:
            print("   ✅ High efficiency - well optimized")

    return results

if __name__ == "__main__":
    try:
        results = main()
        print("\n✅ Profiling completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Profiling failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)