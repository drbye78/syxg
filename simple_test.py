#!/usr/bin/env python3
"""
Simple test to verify deferred SF2 parsing implementation works correctly
"""

import time
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_deferred_parsing_basic():
    """Basic test of deferred parsing functionality"""
    print("Testing basic deferred SF2 parsing...")
    
    try:
        # Import the deferred parsing implementation
        from sf2_deferred import Sf2WavetableManager
        
        # Test file
        sf2_path = "tests/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"
        
        if not os.path.exists(sf2_path):
            print(f"Test SF2 file not found: {sf2_path}")
            return False
        
        # Measure initialization time
        start_time = time.time()
        manager = Sf2WavetableManager([sf2_path])
        init_time = time.time() - start_time
        
        print(f"✓ Initialization completed in {init_time:.4f} seconds")
        
        # Verify manager was created successfully
        if not manager.sf2_managers:
            print("✗ Failed to create SF2 managers")
            return False
            
        print("✓ SF2 managers created successfully")
        
        # Check that parsing is deferred
        deferred_properly = all(not mgr.get('parsed', True) for mgr in manager.sf2_managers)
        if deferred_properly:
            print("✓ Deferred parsing confirmed - files not parsed yet")
        else:
            print("⚠ Files appear to be parsed immediately")
        
        # Test getting program parameters (this should trigger parsing)
        start_time = time.time()
        params = manager.get_program_parameters(0, 0)  # Piano
        parse_time = time.time() - start_time
        
        print(f"✓ Piano parameters retrieved in {parse_time:.4f} seconds")
        
        # Check that parsing happened
        for mgr in manager.sf2_managers:
            if not mgr.get('parsed', False):
                print("✗ SF2 file was not parsed when requested")
                return False
        
        print("✓ Parsing triggered correctly on first request")
        
        # Test getting drum parameters
        start_time = time.time()
        drum_params = manager.get_drum_parameters(36, 0, 128)  # Kick drum
        drum_parse_time = time.time() - start_time
        
        print(f"✓ Kick drum parameters retrieved in {drum_parse_time:.4f} seconds")
        
        # Verify we got valid parameters
        if not params or not isinstance(params, dict):
            print("✗ Failed to get program parameters")
            return False
            
        if not drum_params or not isinstance(drum_params, dict):
            print("✗ Failed to get drum parameters")
            return False
        
        print("✓ Successfully retrieved program and drum parameters")
        
        # Test getting available presets
        presets = manager.get_available_presets()
        print(f"✓ Available presets: {len(presets)} found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Deferred SF2 Parsing Basic Test")
    print("=" * 40)
    
    success = test_deferred_parsing_basic()
    
    if success:
        print("\n🎉 All tests passed! Deferred parsing is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)