#!/usr/bin/env python3
"""
SF2 Soundfont Preset Scanner

Scans the current directory for SF2 soundfont files and generates a CSV file
listing all presets with detailed information about each preset.

For each preset, the following information is collected:
- Bank number
- Program number
- Preset name
- Number of instruments
- Total number of instrument zones
- Total number of samples
- Total size of samples (in bytes)
- Total number of generators
- Total number of modulators

Usage:
    python scan_sf2_presets.py [--output OUTPUT.csv] [--directory /path/to/scan]
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any


def find_sf2_files(directory: str) -> list[Path]:
    """
    Find all SF2 soundfont files in the specified directory.

    Args:
        directory: Directory path to scan

    Returns:
        List of Path objects for found SF2 files
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory does not exist: {directory}")
        return []

    sf2_files = sorted(dir_path.glob("*.sf2"))
    return sf2_files


def scan_sf2_preset(sf2_file: Path) -> list[dict[str, Any]] | None:
    """
    Scan a single SF2 file and extract preset information.

    Args:
        sf2_file: Path to the SF2 file

    Returns:
        List of preset information dictionaries, or None if file cannot be read
    """
    try:
        from synth.sf2.sf2_file_loader import SF2FileLoader
    except ImportError as e:
        print(f"Error importing SF2 modules: {e}")
        return None

    try:
        # Load the SF2 file
        loader = SF2FileLoader(str(sf2_file))
        if not loader.load_file():
            print(f"  Failed to load: {sf2_file.name}")
            return None

        # Get file info
        file_info = loader.get_file_info()
        soundfont_name = file_info.get("bank_name", sf2_file.stem)

        # Parse preset headers
        preset_headers = loader.parse_preset_headers()
        if not preset_headers:
            print(f"  No presets found: {sf2_file.name}")
            return []

        presets_data = []

        for preset_header in preset_headers:
            bank = preset_header["bank"]
            program = preset_header["program"]
            preset_name = preset_header["name"]
            preset_bag_index = preset_header["bag_index"]
            preset_index = preset_header["header_index"]

            # Skip the terminator preset (last one with bag_ndx pointing to end)
            if preset_name == "EOI" or (
                preset_index == len(preset_headers) - 1 and not preset_name.strip()
            ):
                continue

            # Get the next preset's bag index to determine zone range
            if preset_index < len(preset_headers) - 1:
                next_preset = loader.parse_preset_header_at_index(preset_index + 1)
                next_bag_index = next_preset["bag_index"] if next_preset else preset_bag_index + 1
            else:
                # Last preset - get total bag count
                bag_data = loader.get_bag_data("preset")
                next_bag_index = len(bag_data) if bag_data else preset_bag_index + 1

            # Get bag data for this preset's zones
            bag_data = loader.get_bag_data_in_range("preset", preset_bag_index, next_bag_index + 1)

            if not bag_data or len(bag_data) < 2:
                # Preset with no zones
                presets_data.append({
                    "soundfont_file": sf2_file.name,
                    "soundfont_name": soundfont_name,
                    "bank": bank,
                    "program": program,
                    "preset_name": preset_name,
                    "num_instruments": 0,
                    "num_zones": 0,
                    "num_samples": 0,
                    "total_sample_size_bytes": 0,
                    "num_generators": 0,
                    "num_modulators": 0,
                })
                continue

            # Get global generator and modulator ranges
            gen_start_global = bag_data[0][0]
            gen_end_global = bag_data[-1][0]
            mod_start_global = bag_data[0][1]
            mod_end_global = bag_data[-1][1]

            # Get generator and modulator data
            gen_data = loader.get_generator_data_in_range("preset", gen_start_global, gen_end_global + 1)
            mod_data = loader.get_modulator_data_in_range("preset", mod_start_global, mod_end_global + 1)

            # Track unique instruments and their details
            instrument_indices = set()
            total_zones = 0
            total_generators = 0
            total_modulators = 0
            sample_ids = set()

            # Process each zone
            for zone_idx in range(len(bag_data) - 1):
                current_bag = bag_data[zone_idx]
                next_bag = bag_data[zone_idx + 1]

                gen_start = current_bag[0]
                gen_end = next_bag[0]
                mod_start = current_bag[1]
                mod_end = next_bag[1]

                # Convert to local indices
                gen_start_local = gen_start - gen_start_global
                gen_end_local = gen_end - gen_start_global
                mod_start_local = mod_start - mod_start_global
                mod_end_local = mod_end - mod_start_global

                # Count generators and modulators for this zone
                zone_generators = max(0, gen_end_local - gen_start_local)
                zone_modulators = max(0, mod_end_local - mod_start_local)

                total_generators += zone_generators
                total_modulators += zone_modulators

                # Get zone generators to find instrument index
                zone_gen_data = gen_data[gen_start_local:gen_end_local] if gen_data else []

                for gen_type, gen_amount in zone_gen_data:
                    if gen_type == 41:  # instrument generator
                        instrument_indices.add(gen_amount)
                        break

            # Now process each instrument to get zones, samples, etc.
            total_instrument_zones = 0
            total_instrument_generators = 0
            total_instrument_modulators = 0

            # Get total number of instruments from instrument headers
            all_instruments = loader.parse_instrument_headers()
            num_instruments = len(all_instruments)

            for inst_idx in instrument_indices:
                inst_header = loader.parse_instrument_header_at_index(inst_idx)
                if not inst_header:
                    continue

                inst_bag_index = inst_header["bag_index"]

                # Get next instrument's bag index
                if inst_idx < num_instruments - 1:
                    next_inst_header = loader.parse_instrument_header_at_index(inst_idx + 1)
                    next_inst_bag_index = next_inst_header["bag_index"] if next_inst_header else inst_bag_index + 1
                else:
                    # Last instrument
                    bag_data_inst = loader.get_bag_data("instrument")
                    next_inst_bag_index = len(bag_data_inst) if bag_data_inst else inst_bag_index + 1

                # Get bag data for this instrument's zones
                inst_bag_data = loader.get_bag_data_in_range("instrument", inst_bag_index, next_inst_bag_index + 1)

                if not inst_bag_data or len(inst_bag_data) < 2:
                    continue

                # Get generator and modulator ranges for instrument
                inst_gen_start_global = inst_bag_data[0][0]
                inst_gen_end_global = inst_bag_data[-1][0]
                inst_mod_start_global = inst_bag_data[0][1]
                inst_mod_end_global = inst_bag_data[-1][1]

                # Get generator and modulator data
                inst_gen_data = loader.get_generator_data_in_range("instrument", inst_gen_start_global, inst_gen_end_global + 1)
                inst_mod_data = loader.get_modulator_data_in_range("instrument", inst_mod_start_global, inst_mod_end_global + 1)

                # Process each instrument zone
                for zone_idx in range(len(inst_bag_data) - 1):
                    current_bag = inst_bag_data[zone_idx]
                    next_bag = inst_bag_data[zone_idx + 1]

                    gen_start = current_bag[0]
                    gen_end = next_bag[0]
                    mod_start = current_bag[1]
                    mod_end = next_bag[1]

                    # Convert to local indices
                    gen_start_local = gen_start - inst_gen_start_global
                    gen_end_local = gen_end - inst_gen_start_global
                    mod_start_local = mod_start - inst_mod_start_global
                    mod_end_local = mod_end - inst_mod_start_global

                    # Count generators and modulators
                    zone_generators = max(0, gen_end_local - gen_start_local)
                    zone_modulators = max(0, mod_end_local - mod_start_local)

                    total_instrument_generators += zone_generators
                    total_instrument_modulators += zone_modulators

                    # Get zone generators to find sample ID
                    zone_gen_data = inst_gen_data[gen_start_local:gen_end_local] if inst_gen_data else []

                    for gen_type, gen_amount in zone_gen_data:
                        if gen_type == 53:  # sampleStartAddrCoarseOffset (sample ID)
                            sample_ids.add(gen_amount)
                            break
                        elif gen_type == 50 and gen_amount not in sample_ids:  # sampleID (fallback)
                            sample_ids.add(gen_amount)
                            break

                total_instrument_zones += len(inst_bag_data) - 1

            # Calculate total sample size
            total_sample_size = 0
            for sample_id in sample_ids:
                try:
                    sample_header = loader.parse_sample_header_at_index(sample_id)
                    if sample_header:
                        sample_start = sample_header.get("start", 0)
                        sample_end = sample_header.get("end", 0)
                        # Each sample point is typically 2 bytes (16-bit)
                        sample_size = (sample_end - sample_start) * 2
                        total_sample_size += sample_size
                except:
                    pass

            presets_data.append({
                "soundfont_file": sf2_file.name,
                "soundfont_name": soundfont_name,
                "bank": bank,
                "program": program,
                "preset_name": preset_name,
                "num_instruments": len(instrument_indices),
                "num_zones": total_instrument_zones,
                "num_samples": len(sample_ids),
                "total_sample_size_bytes": total_sample_size,
                "num_generators": total_instrument_generators,
                "num_modulators": total_instrument_modulators,
            })

        return presets_data

    except Exception as e:
        print(f"  Error scanning {sf2_file.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def scan_directory(directory: str, output_file: str) -> None:
    """
    Scan directory for SF2 files and generate CSV report.

    Args:
        directory: Directory to scan
        output_file: Output CSV file path
    """
    print(f"Scanning directory: {directory}")
    print("-" * 60)

    # Find all SF2 files
    sf2_files = find_sf2_files(directory)

    if not sf2_files:
        print(f"No SF2 files found in {directory}")
        return

    print(f"Found {len(sf2_files)} SF2 file(s)")
    print("-" * 60)

    # Scan each SF2 file
    all_presets = []

    for sf2_file in sf2_files:
        print(f"Processing: {sf2_file.name}")
        presets_data = scan_sf2_preset(sf2_file)

        if presets_data:
            all_presets.extend(presets_data)
            print(f"  Found {len(presets_data)} preset(s)")

    if not all_presets:
        print("\nNo presets found in any SF2 files.")
        return

    # Write CSV file
    fieldnames = [
        "soundfont_file",
        "soundfont_name",
        "bank",
        "program",
        "preset_name",
        "num_instruments",
        "num_zones",
        "num_samples",
        "total_sample_size_bytes",
        "num_generators",
        "num_modulators",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_presets)

    print("-" * 60)
    print(f"\nCSV report generated: {output_file}")
    print(f"Total presets: {len(all_presets)}")
    print(f"Total SF2 files: {len(sf2_files)}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan directory for SF2 soundfonts and generate preset CSV report"
    )
    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        default=".",
        help="Directory to scan for SF2 files (default: current directory)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="sf2_presets.csv",
        help="Output CSV file path (default: sf2_presets.csv)",
    )

    args = parser.parse_args()

    # Add the project root to Python path for imports
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    scan_directory(args.directory, args.output)


if __name__ == "__main__":
    main()
