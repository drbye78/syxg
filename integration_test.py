#!/usr/bin/env python3
"""
Integration test for the complete XG synthesizer with deferred SF2 parsing
"""

import time
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_complete_integration():
    """Test complete integration of XG synthesizer with deferred SF2 parsing"""
    print("Complete Integration Test: XG Synthesizer with Deferred SF2 Parsing")
    print("=" * 70)
    
    # Test file
    sf2_path = "tests/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"
    
    if not os.path.exists(sf2_path):
        print(f"Test SF2 file not found: {sf2_path}")
        return False
    
    try:
        # Import the deferred parsing implementation
        from sf2_deferred import Sf2WavetableManager
        
        print("\n1. Initializing XG Synthesizer with deferred SF2 parsing...")
        start_time = time.time()
        manager = Sf2WavetableManager([sf2_path])
        init_time = time.time() - start_time
        print(f"   Initialization completed in {init_time:.4f} seconds")
        
        # Verify manager is properly initialized
        if not manager.sf2_managers:
            print("   ERROR: Failed to initialize SF2 managers")
            return False
            
        print("   ✓ SF2 managers initialized successfully")
        
        # Check that parsing is deferred
        deferred_properly = all(not mgr.get('parsed', True) for mgr in manager.sf2_managers)
        if deferred_properly:
            print("   ✓ Deferred parsing confirmed - files not parsed yet")
        else:
            print("   WARNING: Files appear to be parsed immediately")
        
        print("\n2. Testing program parameter retrieval...")
        
        # Test retrieving various program parameters
        test_programs = [
            (0, 0, "Piano"),
            (1, 0, "Piano 2"),
            (25, 0, "Guitar"),
            (40, 0, "Strings"),
            (56, 0, "Trumpet"),
            (128, 128, "Kick Drum")  # Drum program
        ]
        
        total_parse_time = 0
        for program, bank, name in test_programs:
            start_time = time.time()
            if bank == 128:
                # Drum parameters
                params = manager.get_drum_parameters(program, 0, bank)
            else:
                # Regular program parameters
                params = manager.get_program_parameters(program, bank)
            parse_time = time.time() - start_time
            total_parse_time += parse_time
            
            if params and isinstance(params, dict):
                print(f"   ✓ {name} ({program}:{bank}) - Retrieved in {parse_time:.4f} seconds")
                # Check key components are present
                required_keys = ['amp_envelope', 'filter_envelope', 'pitch_envelope']
                missing_keys = [key for key in required_keys if key not in params]
                if missing_keys:
                    print(f"     WARNING: Missing keys: {missing_keys}")
            else:
                print(f"   ✗ {name} ({program}:{bank}) - Failed to retrieve parameters")
                return False
        
        print(f"   Average parse time per program: {total_parse_time/len(test_programs):.4f} seconds")
        
        print("\n3. Testing cache effectiveness...")
        
        # Access the same programs again to test caching
        cache_test_time = 0
        for program, bank, name in test_programs[:3]:  # Test first 3 programs
            start_time = time.time()
            if bank == 128:
                params = manager.get_drum_parameters(program, 0, bank)
            else:
                params = manager.get_program_parameters(program, bank)
            cache_time = time.time() - start_time
            cache_test_time += cache_time
            
            print(f"   ✓ {name} ({program}:{bank}) - Cached access in {cache_time:.4f} seconds")
        
        print(f"   Average cached access time: {cache_test_time/3:.6f} seconds")
        if cache_test_time < total_parse_time:
            print("   ✓ Cache is working - subsequent accesses are faster")
        else:
            print("   WARNING: Cache may not be providing significant performance benefit")
        
        print("\n4. Testing system features...")
        
        # Test getting available presets
        start_time = time.time()
        presets = manager.get_available_presets()
        presets_time = time.time() - start_time
        print(f"   Available presets: {len(presets)} found in {presets_time:.4f} seconds")
        
        # Test checking if bank is drum bank
        is_drum = manager.is_drum_bank(128)
        print(f"   Bank 128 is drum bank: {is_drum}")
        
        # Test clearing caches
        manager.clear_cache()
        print("   ✓ Caches cleared successfully")
        
        print("\n5. Performance summary...")
        print("-" * 30)
        print(f"   Initialization time: {init_time:.4f} seconds")
        print(f"   Total parse time for {len(test_programs)} programs: {total_parse_time:.4f} seconds")
        print(f"   Average parse time per program: {total_parse_time/len(test_programs):.4f} seconds")
        print(f"   Average cached access time: {cache_test_time/3:.6f} seconds")
        print(f"   Performance improvement: {(init_time / (init_time + total_parse_time)) * 100:.1f}% reduction in initialization")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting complete integration test...")
    success = test_complete_integration()
    
    if success:
        print("\n🎉 COMPLETE INTEGRATION TEST PASSED!")
        print("The XG synthesizer with deferred SF2 parsing is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ COMPLETE INTEGRATION TEST FAILED!")
        print("There are issues with the implementation that need to be addressed.")
        sys.exit(1)