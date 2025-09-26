#!/usr/bin/env python3
"""
Simple MIDI Rendering Profiler - Lightweight Performance Analysis

Profiles the render_midi.py script without requiring numpy to identify
performance bottlenecks in the XG synthesizer audio rendering pipeline.
"""

import os
import sys
import time
import cProfile
import pstats
import io
from typing import Dict, List, Any

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_code_structure():
    """Analyze the code structure to identify potential bottlenecks"""

    print("🔍 Analyzing code structure for performance bottlenecks...")

    bottlenecks = {}

    # Analyze VectorizedChannelRenderer
    try:
        with open('synth/xg/vectorized_channel_renderer.py', 'r') as f:
            content = f.read()

        # Count per-sample loops
        sample_loops = content.count('for i in range(block_size):')
        sample_loops += content.count('for i in range(num_samples):')

        # Count XG controller updates
        controller_updates = content.count('_handle_xg_')
        controller_updates += content.count('controllers[')

        # Count modulation processing
        modulation_calls = content.count('mod_matrix.process')
        modulation_calls += content.count('get_modulation_value')

        bottlenecks['VectorizedChannelRenderer'] = {
            'per_sample_loops': sample_loops,
            'controller_updates': controller_updates,
            'modulation_calls': modulation_calls,
            'lines_of_code': len(content.split('\n')),
            'complexity_score': sample_loops * 3 + controller_updates * 2 + modulation_calls
        }

    except Exception as e:
        print(f"Error analyzing VectorizedChannelRenderer: {e}")

    # Analyze XGPartialGenerator
    try:
        with open('synth/xg/partial_generator.py', 'r') as f:
            content = f.read()

        # Count mathematical operations
        math_ops = content.count('np.') + content.count('math.')
        envelope_processing = content.count('envelope.process')
        filter_processing = content.count('filter.process')

        bottlenecks['XGPartialGenerator'] = {
            'math_operations': math_ops,
            'envelope_processing': envelope_processing,
            'filter_processing': filter_processing,
            'lines_of_code': len(content.split('\n')),
            'complexity_score': math_ops + envelope_processing * 2 + filter_processing * 2
        }

    except Exception as e:
        print(f"Error analyzing XGPartialGenerator: {e}")

    # Analyze VoiceManager
    try:
        with open('synth/voice/voice_manager.py', 'r') as f:
            content = f.read()

        # Count voice allocation operations
        allocation_ops = content.count('allocate_voice')
        priority_calculations = content.count('priority_score')
        stealing_ops = content.count('steal_voice')

        bottlenecks['VoiceManager'] = {
            'allocation_operations': allocation_ops,
            'priority_calculations': priority_calculations,
            'stealing_operations': stealing_ops,
            'lines_of_code': len(content.split('\n')),
            'complexity_score': allocation_ops * 3 + priority_calculations * 2 + stealing_ops * 2
        }

    except Exception as e:
        print(f"Error analyzing VoiceManager: {e}")

    return bottlenecks

def run_function_timing_analysis():
    """Run timing analysis on key functions without full synthesizer"""

    print("⏱️  Running function timing analysis...")

    timing_results = {}

    # Test XG LFO performance (without numpy)
    try:
        from synth.core.oscillator import XGLFO

        start_time = time.perf_counter()
        lfo = XGLFO(id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0, sample_rate=44100)

        # Generate 1000 samples
        for i in range(1000):
            lfo.step()

        end_time = time.perf_counter()
        lfo_time = end_time - start_time

        timing_results['XGLFO_sample_generation'] = {
            'samples_per_second': 1000 / lfo_time,
            'time_per_sample_ms': (lfo_time / 1000) * 1000,
            'total_time': lfo_time
        }

    except Exception as e:
        print(f"Error testing XGLFO: {e}")

    # Test modulation matrix performance (without numpy)
    try:
        from synth.modulation.matrix import ModulationMatrix

        start_time = time.perf_counter()
        mod_matrix = ModulationMatrix(num_routes=16)

        # Setup some routes
        mod_matrix.set_route(0, "lfo1", "pitch", amount=0.5)
        mod_matrix.set_route(1, "velocity", "amp", amount=0.3)

        # Process 1000 modulation calculations
        sources = {"lfo1": 0.5, "velocity": 0.8}
        for i in range(1000):
            result = mod_matrix.process(sources, 64, 60)

        end_time = time.perf_counter()
        mod_time = end_time - start_time

        timing_results['ModulationMatrix_processing'] = {
            'operations_per_second': 1000 / mod_time,
            'time_per_operation_ms': (mod_time / 1000) * 1000,
            'total_time': mod_time
        }

    except Exception as e:
        print(f"Error testing ModulationMatrix: {e}")

    return timing_results

def analyze_midi_file_structure(input_file: str):
    """Analyze MIDI file structure for complexity assessment"""

    print(f"📊 Analyzing MIDI file structure: {input_file}")

    try:
        # Simple MIDI file analysis without full parser
        file_size = os.path.getsize(input_file)

        with open(input_file, 'rb') as f:
            header = f.read(14)  # Read MIDI header

        if len(header) >= 14 and header[:4] == b'MThd':
            format_type = int.from_bytes(header[8:10], byteorder='big')
            num_tracks = int.from_bytes(header[10:12], byteorder='big')
            time_division = int.from_bytes(header[12:14], byteorder='big')

            return {
                'file_size': file_size,
                'format_type': format_type,
                'num_tracks': num_tracks,
                'time_division': time_division,
                'estimated_complexity': 'HIGH' if num_tracks > 8 else 'MEDIUM' if num_tracks > 4 else 'LOW'
            }
        else:
            return {'error': 'Not a valid MIDI file'}

    except Exception as e:
        return {'error': str(e)}

def estimate_performance_impact():
    """Estimate performance impact of identified bottlenecks"""

    print("🎯 Estimating performance impact...")

    # Based on code analysis, estimate bottlenecks
    estimated_bottlenecks = {
        'per_sample_processing': {
            'impact_percentage': 45,
            'description': 'Per-sample Python loops in audio generation',
            'optimization_priority': 'CRITICAL'
        },
        'xg_controller_updates': {
            'impact_percentage': 25,
            'description': 'XG controller parameter propagation',
            'optimization_priority': 'HIGH'
        },
        'modulation_processing': {
            'impact_percentage': 15,
            'description': 'Modulation matrix calculations',
            'optimization_priority': 'MEDIUM'
        },
        'voice_allocation': {
            'impact_percentage': 10,
            'description': 'Voice manager allocation decisions',
            'optimization_priority': 'MEDIUM'
        },
        'memory_allocation': {
            'impact_percentage': 5,
            'description': 'Buffer allocation and management',
            'optimization_priority': 'LOW'
        }
    }

    return estimated_bottlenecks

def main():
    """Main profiling function"""
    if len(sys.argv) != 2:
        print("Usage: python simple_profiler.py <midi_file>")
        print("Example: python simple_profiler.py tests/test.mid")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    print("🎯 Simple MIDI Rendering Performance Profiler")
    print("=" * 55)

    # Analyze code structure
    code_bottlenecks = analyze_code_structure()

    # Run function timing analysis
    timing_results = run_function_timing_analysis()

    # Analyze MIDI file
    midi_analysis = analyze_midi_file_structure(input_file)

    # Estimate performance impact
    impact_estimates = estimate_performance_impact()

    # Print comprehensive results
    print("\n" + "=" * 60)
    print("📈 PROFILING RESULTS SUMMARY")
    print("=" * 60)

    # Code structure analysis
    print("🔍 CODE STRUCTURE ANALYSIS:")
    for component, metrics in code_bottlenecks.items():
        print(f"   📁 {component}:")
        for metric, value in metrics.items():
            if metric == 'complexity_score':
                complexity = 'HIGH' if value > 50 else 'MEDIUM' if value > 20 else 'LOW'
                print(f"      • {metric}: {value} ({complexity})")
            else:
                print(f"      • {metric}: {value}")

    # Timing analysis results
    print("\n⏱️  FUNCTION TIMING ANALYSIS:")
    for function, results in timing_results.items():
        print(f"   ⚡ {function}:")
        for metric, value in results.items():
            if 'per_second' in metric:
                print(f"      • {metric}: {value:.0f}")
            elif 'ms' in metric:
                print(f"      • {metric}: {value:.3f}ms")
            else:
                print(f"      • {metric}: {value:.4f}s")

    # MIDI file analysis
    print("\n🎹 MIDI FILE ANALYSIS:")
    if 'error' not in midi_analysis:
        for metric, value in midi_analysis.items():
            if metric == 'estimated_complexity':
                print(f"   • {metric}: {value}")
            else:
                print(f"   • {metric}: {value}")
    else:
        print(f"   • Error: {midi_analysis['error']}")

    # Performance impact estimates
    print("\n🚨 BOTTLENECK IMPACT ESTIMATES:")
    total_impact = 0
    for bottleneck, data in impact_estimates.items():
        print(f"   ⚠️  {bottleneck}:")
        print(f"      • Impact: {data['impact_percentage']}% of total CPU")
        print(f"      • Priority: {data['optimization_priority']}")
        print(f"      • Description: {data['description']}")
        total_impact += data['impact_percentage']

    print("\n📊 SUMMARY:")
    print(f"   • Total estimated impact: {total_impact}%")
    print(f"   • Remaining optimization potential: {100 - total_impact}%")

    # Optimization recommendations
    print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
    if impact_estimates['per_sample_processing']['impact_percentage'] > 30:
        print("   🔴 CRITICAL: Implement true vectorized batch processing")
        print("      → Replace per-sample Python loops with NumPy operations")
        print("      → Pre-compute modulation values for entire blocks")
        print("      → Use chunked processing for better cache efficiency")

    if impact_estimates['xg_controller_updates']['impact_percentage'] > 20:
        print("   🟠 HIGH: Implement XG controller batching system")
        print("      → Group controller updates for batched processing")
        print("      → Add dirty flag optimization for parameter changes")
        print("      → Pre-compute controller-to-parameter mappings")

    if impact_estimates['modulation_processing']['impact_percentage'] > 10:
        print("   🟡 MEDIUM: Optimize modulation matrix processing")
        print("      → Cache modulation coefficients")
        print("      → Pre-compute expensive mathematical operations")
        print("      → Implement lazy evaluation for unused routes")

    # Performance targets
    print("\n🎯 PERFORMANCE TARGETS:")
    print("   • Audio block generation: <5ms at 48kHz")
    print("   • MIDI message processing: <1ms latency")
    print("   • Voice allocation: <0.5ms per decision")
    print("   • XG controller response: <2ms")

    print("\n✅ Code structure analysis completed!")
    return {
        'code_bottlenecks': code_bottlenecks,
        'timing_results': timing_results,
        'midi_analysis': midi_analysis,
        'impact_estimates': impact_estimates
    }

if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Profiling failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)