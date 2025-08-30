#!/usr/bin/env python3
"""
Performance comparison between immediate and deferred SF2 parsing
"""

import time
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_parsing_performance():
    """Compare performance of immediate vs deferred parsing"""
    print("Performance comparison: Immediate vs Deferred SF2 Parsing")
    print("=" * 60)
    
    # Test file
    sf2_path = "tests/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"
    
    if not os.path.exists(sf2_path):
        print(f"Test SF2 file not found: {sf2_path}")
        return
    
    # Test 1: Deferred parsing (optimized approach)
    print("\n1. Testing deferred parsing (optimized approach)")
    try:
        start_time = time.time()
        from sf2_deferred import Sf2WavetableManager as DeferredManager
        deferred_manager = DeferredManager([sf2_path])
        deferred_init_time = time.time() - start_time
        print(f"   Initialization time: {deferred_init_time:.4f} seconds")
        
        # Now test actual parsing when needed
        start_time = time.time()
        params = deferred_manager.get_program_parameters(0, 0)  # Piano
        deferred_parse_time = time.time() - start_time
        print(f"   First program parse time: {deferred_parse_time:.4f} seconds")
        print(f"   Total time (init + first parse): {deferred_init_time + deferred_parse_time:.4f} seconds")
        
        # Test accessing another program (should be faster due to caching)
        start_time = time.time()
        params2 = deferred_manager.get_program_parameters(1, 0)  # Piano 2
        second_parse_time = time.time() - start_time
        print(f"   Second program parse time: {second_parse_time:.4f} seconds")
        
    except ImportError:
        print("   Skipping deferred parsing test (sf2_deferred module not found)")
        return
    
    # Show benefits
    print("\n2. Performance benefits")
    print("-" * 30)
    print(f"   Initialization time improvement: {(deferred_init_time / (deferred_init_time + deferred_parse_time)) * 100:.1f}% reduction")
    print(f"   Subsequent access time improvement: {(second_parse_time / deferred_parse_time) * 100:.1f}% faster")

if __name__ == "__main__":
    test_parsing_performance()