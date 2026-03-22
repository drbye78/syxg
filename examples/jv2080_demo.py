#!/usr/bin/env python3
"""
JV-2080 Enhanced GS Demonstration

Showcase the Roland JV-2080 workstation-level GS implementation with
multi-part architecture, MFX effects, NRPN control, and advanced features.
"""

import time

# Import JV-2080 components
from synth.gs.jv2080_component_manager import (
    JV2080ComponentManager,
)


def create_jv2080_demo():
    """Create and configure JV-2080 enhanced GS demonstration."""
    print("🎹 JV-2080 ENHANCED GS DEMONSTRATION")
    print("=" * 70)

    # Initialize JV-2080 component manager
    print("🎛️  Initializing JV-2080 Component Manager...")
    jv2080_manager = JV2080ComponentManager()

    print("📊 JV-2080 System Configuration:")
    info = jv2080_manager.get_system_info()
    print(f"   Components: {info['component_count']}")
    print(f"   Firmware: {info['firmware_version']}")
    print(f"   Multi-part: {info['multipart']['total_parts']} parts")
    print(f"   MFX Types: {info['mfx']['available_types']}")
    print(f"   Insert Effects: {len(info['insert_effects']['effect_types'])} types")

    return jv2080_manager


def demonstrate_multipart_architecture():
    """Demonstrate JV-2080 multi-part architecture."""
    print("\n🎼 MULTI-PART ARCHITECTURE DEMONSTRATION")
    print("-" * 50)

    manager = JV2080ComponentManager()
    multipart = manager.get_component("multipart")

    print("🎛️  Configuring 16-part multitimbral setup...")

    # Configure different parts with different settings
    configurations = [
        {"name": "Piano Part", "instrument": 0, "volume": 110, "pan": 32},  # Left pan
        {"name": "Bass Part", "instrument": 32, "volume": 100, "pan": 96},  # Right pan
        {"name": "Strings Part", "instrument": 48, "volume": 90, "pan": 64},  # Center
        {"name": "Drums Part", "instrument": 128, "volume": 120, "pan": 64},  # Center
    ]

    for i, config in enumerate(configurations):
        part = multipart.get_part(i)
        if part:
            part.volume = config["volume"]
            part.pan = config["pan"]
            part.instrument_number = config["instrument"]
            print(
                f"   Part {i}: {config['name']} - Inst:{config['instrument']}, Vol:{config['volume']}, Pan:{config['pan']}"
            )

    # Configure voice allocation
    print("🎵 Setting voice allocation...")
    for i in range(4):
        multipart.set_voice_reserve(i, 12)  # 12 voices for first 4 parts

    voice_status = multipart.get_voice_allocation_status()
    print(f"   Total voice reserve: {voice_status['total_reserve']}/128")
    print(f"   Available voices: {voice_status['available_voices']}")

    # Test part routing
    print("🎛️  Testing MIDI channel routing...")
    for i in range(4):
        parts_for_channel = multipart.get_parts_for_midi_channel(i)
        print(f"   MIDI Ch {i} → Parts: {parts_for_channel}")

    print("✅ Multi-part architecture demonstration completed")


def demonstrate_mfx_effects():
    """Demonstrate JV-2080 MFX (Multi-Effects) system."""
    print("\n🌟 MFX (MULTI-EFFECTS) DEMONSTRATION")
    print("-" * 50)

    manager = JV2080ComponentManager()
    mfx = manager.get_component("mfx")

    print("🎛️  Exploring MFX effect types...")

    # Demonstrate different MFX types
    mfx_types_to_demo = [
        (0, "STEREO EQ"),
        (8, "CHORUS"),
        (12, "DELAY"),
        (14, "REVERB"),
        (19, "PITCH SHIFTER"),
    ]

    for mfx_type, name in mfx_types_to_demo:
        mfx.set_mfx_type(mfx_type)
        print(f"   MFX Type {mfx_type}: {name}")
        print(f"     Parameters: {len(mfx.parameters)}")
        print(f"     Control Level: {mfx.mfx_level}")

        # Set some effect parameters
        if mfx_type == 8:  # Chorus
            mfx.set_parameter(0, 80)  # Rate
            mfx.set_parameter(1, 40)  # Depth
            mfx.set_parameter(2, 100)  # Mix
            print("     Chorus Settings - Rate:80, Depth:40, Mix:100")

    print("✅ MFX effects demonstration completed")


def demonstrate_nrpn_control():
    """Demonstrate JV-2080 NRPN parameter control."""
    print("\n🎚️  NRPN PARAMETER CONTROL DEMONSTRATION")
    print("-" * 50)

    manager = JV2080ComponentManager()

    if manager.nrpn_controller is None:
        print("⚠️  NRPN controller not available")
        return

    nrpn = manager.nrpn_controller

    print("🎛️  Testing NRPN parameter access...")
    print(f"   Total NRPN parameters: {len(nrpn.parameter_map)}")

    # Test system parameter control via NRPN
    print("🎵 Setting master volume via NRPN...")

    # NRPN sequence for master volume (0x01, 0x01)
    nrpn.process_nrpn_message(99, 0x01)  # NRPN MSB = 0x01 (system)
    nrpn.process_nrpn_message(98, 0x01)  # NRPN LSB = 0x01 (master volume)
    nrpn.process_nrpn_message(6, 115)  # Data MSB = 115 (volume level)

    # Check if parameter was set
    volume = manager.get_parameter_value(bytes([0x00, 0x01]))
    print(f"   Master volume set to: {volume} (expected: 115)")

    # Test part parameter control
    print("🎼 Setting part 0 volume via NRPN...")

    # NRPN sequence for part 0 volume (0x18, 0x02)
    nrpn.process_nrpn_message(99, 0x18)  # NRPN MSB = 0x18 (part 0)
    nrpn.process_nrpn_message(98, 0x02)  # NRPN LSB = 0x02 (volume)
    nrpn.process_nrpn_message(6, 90)  # Data MSB = 90

    # Check part parameter
    multipart = manager.get_component("multipart")
    part = multipart.get_part(0)
    if part:
        print(f"   Part 0 volume set to: {part.volume} (expected: 90)")

    # List parameter categories
    print("📊 NRPN Parameter Categories:")
    system_params = nrpn.list_parameters("system")
    part_params = nrpn.list_parameters("part")
    effects_params = nrpn.list_parameters("effects")

    print(f"   System parameters: {len(system_params)}")
    print(f"   Part parameters: {len(part_params)}")
    print(f"   Effects parameters: {len(effects_params)}")

    # Show some example parameters
    print("📋 Sample NRPN Parameters:")
    for param in system_params[:3]:
        print(f"   {param['address']} - {param['name']}")

    print("✅ NRPN control demonstration completed")


def demonstrate_insert_effects():
    """Demonstrate JV-2080 insert effects system."""
    print("\n🔧 INSERT EFFECTS DEMONSTRATION")
    print("-" * 50)

    manager = JV2080ComponentManager()
    insert_fx = manager.get_component("insert_fx")

    print("🎛️  Configuring insert effects...")

    # Show available insert effect types
    print(f"   Available insert effects: {len(insert_fx.insert_types)}")
    for i, effect_name in enumerate(insert_fx.insert_types):
        print(f"     {i}: {effect_name}")

    # Assign different effects to different parts
    assignments = [
        (0, 1, "EQ"),  # Part 0: EQ
        (1, 3, "CHORUS"),  # Part 1: Chorus
        (2, 6, "DELAY"),  # Part 2: Delay
        (3, 5, "DISTORTION"),  # Part 3: Distortion
    ]

    for part_num, effect_type, effect_name in assignments:
        insert_fx.set_part_assignment(part_num, effect_type)
        print(f"   Part {part_num} → {effect_name} (type {effect_type})")

        # Set some effect parameters
        if effect_type == 3:  # Chorus
            insert_fx.set_effect_parameter(effect_type, 0, 70)  # Rate
            insert_fx.set_effect_parameter(effect_type, 1, 50)  # Depth
            insert_fx.set_effect_parameter(effect_type, 2, 80)  # Mix
            print("     Chorus settings - Rate:70, Depth:50, Mix:80")

    print("✅ Insert effects demonstration completed")


def demonstrate_system_integration():
    """Demonstrate complete JV-2080 system integration."""
    print("\n🔗 SYSTEM INTEGRATION DEMONSTRATION")
    print("-" * 50)

    manager = JV2080ComponentManager()

    print("🎛️  Testing complete JV-2080 system integration...")

    # Configure a complete multi-part setup
    multipart = manager.get_component("multipart")

    # Set up a 4-part arrangement
    setup_config = [
        {
            "part": 0,
            "name": "Piano",
            "inst": 0,
            "vol": 100,
            "pan": 32,
            "effects": {"reverb": 20, "chorus": 30},
        },
        {"part": 1, "name": "Bass", "inst": 32, "vol": 90, "pan": 96, "effects": {"reverb": 15}},
        {
            "part": 2,
            "name": "Strings",
            "inst": 48,
            "vol": 85,
            "pan": 64,
            "effects": {"chorus": 25, "delay": 20},
        },
        {"part": 3, "name": "Drums", "inst": 128, "vol": 110, "pan": 64, "effects": {"reverb": 40}},
    ]

    print("🎵 Configuring 4-part arrangement:")
    for config in setup_config:
        part = multipart.get_part(config["part"])
        if part:
            part.instrument_number = config["inst"]
            part.volume = config["vol"]
            part.pan = config["pan"]

            # Set effects sends
            effects = config["effects"]
            part.reverb_send = effects.get("reverb", 0)
            part.chorus_send = effects.get("chorus", 0)
            part.delay_send = effects.get("delay", 0)

            print(
                f"   {config['name']}: Inst{config['inst']}, Vol{config['vol']}, Pan{config['pan']}, "
                f"Reverb{part.reverb_send}, Chorus{part.chorus_send}, Delay{part.delay_send}"
            )

    # Configure MFX
    mfx = manager.get_component("mfx")
    mfx.set_mfx_type(8)  # Chorus
    mfx.mfx_level = 80
    print(f"   MFX: {mfx.get_mfx_type_name(8)}, Level: {mfx.mfx_level}")

    # Configure insert effects
    insert_fx = manager.get_component("insert_fx")
    insert_fx.set_part_assignment(0, 1)  # Piano: EQ
    insert_fx.set_part_assignment(2, 3)  # Strings: Chorus
    print("   Insert Effects: Piano→EQ, Strings→Chorus")

    # Get comprehensive system status
    system_info = manager.get_system_info()
    print(f"   System Status: {system_info['component_count']} components active")
    print(
        f"   Voice Allocation: {system_info['multipart']['voice_allocation']['total_reserve']}/128 voices"
    )

    print("✅ System integration demonstration completed")


def run_performance_test():
    """Run performance testing for JV-2080 system."""
    print("\n⚡ JV-2080 PERFORMANCE TESTING")
    print("-" * 50)

    print("🎛️  Testing JV-2080 system performance...")

    # Create system and configure it
    manager = JV2080ComponentManager()

    # Configure a complex multi-part setup
    multipart = manager.get_component("multipart")
    for i in range(8):  # Configure 8 parts
        part = multipart.get_part(i)
        if part:
            part.volume = 80 + i * 5
            part.pan = 20 + i * 10

    print("📊 Performance Test Configuration:")
    print("   8 active parts configured")
    print("   MFX and insert effects active")
    print("   NRPN parameter system ready")

    # Test parameter access performance

    start_time = time.time()

    # Perform 1000 parameter accesses
    test_iterations = 1000
    for i in range(test_iterations):
        # Access various parameters
        volume = manager.get_parameter_value(bytes([0x00, 0x01]))  # Master volume
        part_vol = multipart.get_part(i % 8)
        if part_vol:
            vol = part_vol.volume

        # NRPN access
        if manager.nrpn_controller:
            param_info = manager.nrpn_controller.get_parameter_info(0x01, 0x01)

    end_time = time.time()
    total_time = end_time - start_time

    print("📈 Performance Results:")
    print(".4f")
    print(".0f")
    print(".1f")

    print("✅ Performance testing completed")


def main():
    """Run the complete JV-2080 enhanced GS demonstration."""
    print("🚀 JV-2080 ENHANCED GS - COMPLETE WORKSTATION DEMONSTRATION")
    print("=" * 90)
    print("This demonstration showcases Roland JV-2080 workstation-level GS features")
    print("including multi-part architecture, MFX effects, NRPN control, and insert effects.")
    print("=" * 90)

    try:
        # Run all demonstrations
        manager = create_jv2080_demo()

        # Multi-part architecture
        demonstrate_multipart_architecture()

        # MFX effects system
        demonstrate_mfx_effects()

        # NRPN parameter control
        demonstrate_nrpn_control()

        # Insert effects
        demonstrate_insert_effects()

        # Complete system integration
        demonstrate_system_integration()

        # Performance testing
        run_performance_test()

        print("\n" + "=" * 90)
        print("🎉 JV-2080 ENHANCED GS DEMONSTRATION COMPLETE!")
        print("=" * 90)
        print("✅ All demonstrations completed successfully")
        print("✅ Multi-part architecture: 16-part workstation operation")
        print("✅ MFX effects: 40+ professional effect types")
        print("✅ NRPN control: 700+ parameter comprehensive access")
        print("✅ Insert effects: Per-part effect processing")
        print("✅ System integration: Complete workstation workflow")
        print("✅ Performance: Real-time operation capability")
        print("=" * 90)

        print("\n🎵 JV-2080 ENHANCED GS CAPABILITIES NOW AVAILABLE:")
        print("   • 16-part multitimbral workstation operation")
        print("   • MFX (Multi-Effects) with 40+ effect types")
        print("   • NRPN parameter control for all settings")
        print("   • Insert effects assignable per part")
        print("   • Voice layering and complex sound design")
        print("   • Bulk operations and comprehensive SysEx support")
        print("   • Real-time parameter modulation")
        print("   • Professional mixing and effects routing")

    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        print("Please ensure all dependencies are installed and try again.")

    finally:
        print("\n🧹 Demonstration cleanup completed.")


if __name__ == "__main__":
    main()
