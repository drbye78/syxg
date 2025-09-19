#!/usr/bin/env python3
"""
Analyze profiling results and identify performance bottlenecks
"""

import re
import sys

def analyze_profile_results(profile_file):
    """Analyze the profiling results to identify bottlenecks"""
    
    try:
        with open(profile_file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Profile file {profile_file} not found")
        return
    
    print(f"=== Analysis of {profile_file} ===\n")
    
    # Extract function call information
    lines = content.split('\n')
    
    # Look for the most time-consuming functions
    function_calls = []
    
    for line in lines:
        # Match function call lines (they start with whitespace followed by numbers)
        # Pattern: ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        match = re.match(r'^\s*(\d+)(?:/\d+)?\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(.+)$', line)
        if match:
            ncalls_str, tottime, percall_tot, cumtime, percall_cum, func_name = match.groups()
            # Handle recursive calls (e.g., 123/45)
            ncalls = int(ncalls_str.split('/')[0])
            function_calls.append({
                'ncalls': ncalls,
                'tottime': float(tottime),
                'cumtime': float(cumtime),
                'percall_cum': float(percall_cum),
                'percall_tot': float(percall_tot),
                'func_name': func_name.strip()
            })
    
    # Sort by cumulative time (most expensive functions)
    function_calls.sort(key=lambda x: x['cumtime'], reverse=True)
    
    print("Top 20 Most Time-Consuming Functions:")
    print("-" * 80)
    print(f"{'Cumulative':<12} {'Total':<12} {'Per Call':<12} {'Calls':<10} {'Function'}")
    print(f"{'Time (s)':<12} {'Time (s)':<12} {'(s)':<12} {'Count':<10} {'Name'}")
    print("-" * 80)
    
    for i, func in enumerate(function_calls[:20]):
        print(f"{func['cumtime']:<12.4f} {func['tottime']:<12.4f} {func['percall_cum']:<12.6f} {func['ncalls']:<10} {func['func_name']}")
    
    print("\n" + "=" * 80)
    
    # Look for functions that might be candidates for optimization
    optimization_candidates = []
    
    # High per-call time functions (potential algorithmic issues)
    high_per_call = [f for f in function_calls if f['percall_cum'] > 0.001]  # More than 1ms per call
    high_per_call.sort(key=lambda x: x['percall_cum'], reverse=True)
    
    # High call count functions (potential for batching)
    high_call_count = [f for f in function_calls if f['ncalls'] > 1000]
    high_call_count.sort(key=lambda x: x['ncalls'], reverse=True)
    
    print("\nFunctions with High Per-Call Time (>1ms):")
    print("-" * 80)
    print(f"{'Per Call':<12} {'Cumulative':<12} {'Calls':<10} {'Function'}")
    print(f"{'(s)':<12} {'Time (s)':<12} {'Count':<10} {'Name'}")
    print("-" * 80)
    
    for func in high_per_call[:15]:
        print(f"{func['percall_cum']:<12.6f} {func['cumtime']:<12.4f} {func['ncalls']:<10} {func['func_name']}")
    
    print("\nFunctions with High Call Counts (>1000):")
    print("-" * 80)
    print(f"{'Calls':<12} {'Cumulative':<12} {'Per Call':<12} {'Function'}")
    print(f"{'Count':<12} {'Time (s)':<12} {'(s)':<12} {'Name'}")
    print("-" * 80)
    
    for func in high_call_count[:15]:
        print(f"{func['ncalls']:<12} {func['cumtime']:<12.4f} {func['percall_cum']:<12.6f} {func['func_name']}")
    
    # Look for specific patterns that might indicate bottlenecks
    print("\n" + "=" * 80)
    print("Potential Bottleneck Analysis:")
    print("-" * 80)
    
    # Search for SF2-related functions that might be slow
    sf2_functions = [f for f in function_calls if 'sf2' in f['func_name'].lower() or 'soundfont' in f['func_name'].lower()]
    if sf2_functions:
        print("\nSF2/SoundFont Related Functions:")
        print("-" * 50)
        sf2_functions.sort(key=lambda x: x['cumtime'], reverse=True)
        for func in sf2_functions[:10]:
            print(f"Cumulative: {func['cumtime']:.4f}s, Calls: {func['ncalls']}, Function: {func['func_name']}")
    
    # Search for envelope-related functions
    envelope_functions = [f for f in function_calls if 'envelope' in f['func_name'].lower()]
    if envelope_functions:
        print("\nEnvelope Related Functions:")
        print("-" * 50)
        envelope_functions.sort(key=lambda x: x['cumtime'], reverse=True)
        for func in envelope_functions[:10]:
            print(f"Cumulative: {func['cumtime']:.4f}s, Calls: {func['ncalls']}, Function: {func['func_name']}")
    
    # Search for audio processing functions
    audio_functions = [f for f in function_calls if any(keyword in f['func_name'].lower() for keyword in ['audio', 'generate', 'process', 'render'])]
    if audio_functions:
        print("\nAudio Processing Functions:")
        print("-" * 50)
        audio_functions.sort(key=lambda x: x['cumtime'], reverse=True)
        for func in audio_functions[:10]:
            print(f"Cumulative: {func['cumtime']:.4f}s, Calls: {func['ncalls']}, Function: {func['func_name']}")
    
    # Search for modulation-related functions
    modulation_functions = [f for f in function_calls if 'modul' in f['func_name'].lower() or 'lfo' in f['func_name'].lower()]
    if modulation_functions:
        print("\nModulation/LFO Related Functions:")
        print("-" * 50)
        modulation_functions.sort(key=lambda x: x['cumtime'], reverse=True)
        for func in modulation_functions[:10]:
            print(f"Cumulative: {func['cumtime']:.4f}s, Calls: {func['ncalls']}, Function: {func['func_name']}")

def main():
    """Main analysis function"""
    if len(sys.argv) > 1:
        profile_file = sys.argv[1]
    else:
        profile_file = 'conversion_profile.txt'
    
    analyze_profile_results(profile_file)

if __name__ == "__main__":
    main()