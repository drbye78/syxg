"""
Test script to compare MIDI file parsing between mido library and synth/midi/file.py FileParser.

This script parses 'tests/test.mid' using both parsers and compares the results
to ensure compatibility and correctness.
"""

import sys
import os
from typing import Any

# Add parent directory to path to import synth modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido

# Import only the specific classes we need to avoid full module import
# which might hang due to rtmidi dependency
from synth.midi.message import MIDIMessage

# Import FileParser by adding synth directory to path
synth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "synth")
if synth_path not in sys.path:
    sys.path.insert(0, synth_path)

# Now import the midi.file module
from midi.file import FileParser


def parse_with_mido(filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Parse MIDI file using mido library.
    
    Args:
        filename: Path to MIDI file
        
    Returns:
        Tuple of (message list, file info dictionary)
    """
    mid = mido.MidiFile(filename)
    messages = []
    
    # Get file info
    file_info = {
        "format": mid.type,
        "tracks": len(mid.tracks),
        "ticks_per_beat": mid.ticks_per_beat,
    }
    
    # Process all tracks
    absolute_time = 0.0
    tempo = 500000  # Default tempo (120 BPM)
    
    for track_idx, track in enumerate(mid.tracks):
        track_time = 0.0
        track_name = None
        
        for msg in track:
            track_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
            
            # Handle tempo changes
            if msg.type == "set_tempo":
                tempo = msg.tempo
            
            # Convert mido message to standardized format
            msg_dict = {
                "type": msg.type,
                "time": track_time,
                "track": track_idx,
            }
            
            # Add message-specific data
            if hasattr(msg, "channel"):
                msg_dict["channel"] = msg.channel
            
            if msg.type == "note_on":
                msg_dict["note"] = msg.note
                msg_dict["velocity"] = msg.velocity
            elif msg.type == "note_off":
                msg_dict["note"] = msg.note
                msg_dict["velocity"] = msg.velocity
            elif msg.type == "control_change":
                msg_dict["controller"] = msg.control
                msg_dict["value"] = msg.value
            elif msg.type == "program_change":
                msg_dict["program"] = msg.program
            elif msg.type == "pitch_bend":
                msg_dict["value"] = msg.pitch
            elif msg.type == "aftertouch":
                msg_dict["value"] = msg.value
            elif msg.type == "polytouch":
                msg_dict["note"] = msg.note
                msg_dict["value"] = msg.value
            elif msg.type == "sysex":
                msg_dict["data"] = list(msg.data)
            elif msg.type == "text":
                msg_dict["text"] = msg.text
            elif msg.type == "track_name":
                msg_dict["name"] = msg.name
                track_name = msg.name
            elif msg.type == "instrument_name":
                msg_dict["name"] = msg.name
            elif msg.type == "lyrics":
                msg_dict["text"] = msg.text
            elif msg.type == "marker":
                msg_dict["text"] = msg.text
            elif msg.type == "cue_marker":
                msg_dict["text"] = msg.text
            elif msg.type == "key_signature":
                msg_dict["key"] = msg.key
            elif msg.type == "time_signature":
                msg_dict["numerator"] = msg.numerator
                msg_dict["denominator"] = msg.denominator
                msg_dict["clocks_per_click"] = msg.clocks_per_click
                msg_dict["notated_32nd_notes_per_beat"] = msg.notated_32nd_notes_per_beat
            elif msg.type == "smpte_offset":
                msg_dict["frame_rate"] = msg.frame_rate
                msg_dict["hours"] = msg.hours
                msg_dict["minutes"] = msg.minutes
                msg_dict["seconds"] = msg.seconds
                msg_dict["frames"] = msg.frames
                msg_dict["sub_frames"] = msg.sub_frames
            elif msg.type == "end_of_track":
                pass  # No additional data
            
            messages.append(msg_dict)
    
    return messages, file_info


def parse_with_fileparser(filename: str) -> tuple[list[MIDIMessage], dict[str, Any]]:
    """
    Parse MIDI file using synth/midi/file.py FileParser.
    
    Args:
        filename: Path to MIDI file
        
    Returns:
        Tuple of (message list, file info dictionary)
    """
    parser = FileParser()
    messages = parser.parse_file(filename)

    prev = None
    for idx, m in enumerate(messages):
        if prev and m.timestamp - prev.timestamp >30:
            print(idx)
        prev = m

    file_info = parser.get_file_info()
    return messages, file_info


def normalize_mido_message(msg: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize mido message to match FileParser output format.
    
    Args:
        msg: mido message dictionary
        
    Returns:
        Normalized message dictionary
    """
    normalized = {
        "type": msg["type"],
        "timestamp": msg["time"],
    }
    
    if "channel" in msg:
        normalized["channel"] = msg["channel"]
    
    # Normalize data fields
    data = {}
    
    if msg["type"] == "note_on":
        data["note"] = msg.get("note", 0)
        data["velocity"] = msg.get("velocity", 0)
    elif msg["type"] == "note_off":
        data["note"] = msg.get("note", 0)
        data["velocity"] = msg.get("velocity", 0)
    elif msg["type"] == "control_change":
        data["controller"] = msg.get("controller", 0)
        data["value"] = msg.get("value", 0)
    elif msg["type"] == "program_change":
        data["program"] = msg.get("program", 0)
    elif msg["type"] == "pitch_bend":
        data["value"] = msg.get("value", 0)
    elif msg["type"] == "aftertouch":
        data["pressure"] = msg.get("value", 0)
    elif msg["type"] == "polytouch":
        data["note"] = msg.get("note", 0)
        data["pressure"] = msg.get("value", 0)
    elif msg["type"] == "sysex":
        data["raw_data"] = msg.get("data", [])
    elif msg["type"] == "text":
        data["text"] = msg.get("text", "")
    elif msg["type"] == "track_name":
        data["name"] = msg.get("name", "")
    elif msg["type"] == "instrument_name":
        data["name"] = msg.get("name", "")
    elif msg["type"] == "lyrics":
        data["text"] = msg.get("text", "")
    elif msg["type"] == "marker":
        data["text"] = msg.get("text", "")
    elif msg["type"] == "cue_marker":
        data["text"] = msg.get("text", "")
    elif msg["type"] == "key_signature":
        data["key"] = msg.get("key", "C")
    elif msg["type"] == "time_signature":
        data["numerator"] = msg.get("numerator", 4)
        data["denominator"] = msg.get("denominator", 4)
    elif msg["type"] == "smpte_offset":
        data["smpte_seconds"] = (
            msg.get("hours", 0) * 3600 +
            msg.get("minutes", 0) * 60 +
            msg.get("seconds", 0) +
            msg.get("frames", 0) / 30.0
        )
    
    normalized["data"] = data
    return normalized


def normalize_fileparser_message(msg: MIDIMessage) -> dict[str, Any]:
    """
    Normalize FileParser message to standard format.
    
    Args:
        msg: MIDIMessage object
        
    Returns:
        Normalized message dictionary
    """
    normalized = {
        "type": msg.type,
        "timestamp": msg.timestamp,
    }
    
    if msg.channel is not None:
        normalized["channel"] = msg.channel
    
    normalized["data"] = msg.data.copy() if msg.data else {}
    return normalized


def compare_messages(mido_msgs: list[dict], fileparser_msgs: list[dict], tolerance: float = 0.001) -> dict[str, Any]:
    """
    Compare messages from both parsers.
    
    Args:
        mido_msgs: Messages from mido parser
        fileparser_msgs: Messages from FileParser
        tolerance: Time comparison tolerance in seconds
        
    Returns:
        Comparison results dictionary
    """
    results = {
        "mido_count": len(mido_msgs),
        "fileparser_count": len(fileparser_msgs),
        "matches": [],
        "mismatches": [],
        "mido_only": [],
        "fileparser_only": [],
    }
    
    # Create copies for matching
    mido_remaining = mido_msgs.copy()
    fileparser_remaining = fileparser_msgs.copy()
    
    # Match messages by type and time
    for mido_msg in mido_msgs[:]:
        for fp_msg in fileparser_msgs[:]:
            # Check if messages match
            if (mido_msg["type"] == fp_msg["type"] and
                abs(mido_msg["timestamp"] - fp_msg["timestamp"]) < tolerance):
                
                # Check channel
                mido_channel = mido_msg.get("channel")
                fp_channel = fp_msg.get("channel")
                
                if mido_channel == fp_channel:
                    # Compare data
                    data_match = compare_message_data(mido_msg, fp_msg)
                    
                    match_info = {
                        "type": mido_msg["type"],
                        "timestamp": mido_msg["timestamp"],
                        "channel": mido_channel,
                        "data_match": data_match["match"],
                        "data_diff": data_match["diff"],
                    }
                    
                    if data_match["match"]:
                        results["matches"].append(match_info)
                    else:
                        results["mismatches"].append(match_info)
                    
                    # Remove from remaining
                    if mido_msg in mido_remaining:
                        mido_remaining.remove(mido_msg)
                    if fp_msg in fileparser_remaining:
                        fileparser_remaining.remove(fp_msg)
                    break
    
    # Record unmatched messages
    results["mido_only"] = mido_remaining
    results["fileparser_only"] = fileparser_remaining
    
    return results


def compare_message_data(mido_msg: dict, fp_msg: dict) -> dict[str, Any]:
    """
    Compare data fields between two messages.
    
    Args:
        mido_msg: mido message
        fp_msg: FileParser message
        
    Returns:
        Comparison result with match status and differences
    """
    mido_data = mido_msg.get("data", {})
    fp_data = fp_msg.get("data", {})
    
    differences = []
    
    # Compare each field
    all_keys = set(mido_data.keys()) | set(fp_data.keys())
    
    for key in all_keys:
        mido_val = mido_data.get(key)
        fp_val = fp_data.get(key)
        
        if mido_val != fp_val:
            differences.append({
                "field": key,
                "mido_value": mido_val,
                "fileparser_value": fp_val,
            })
    
    return {
        "match": len(differences) == 0,
        "diff": differences,
    }


def print_comparison_results(results: dict[str, Any]):
    """
    Print comparison results in a readable format.
    
    Args:
        results: Comparison results dictionary
    """
    print("\n" + "=" * 80)
    print("MIDI PARSING COMPARISON RESULTS")
    print("=" * 80)
    
    print(f"\nMessage Counts:")
    print(f"  mido:      {results['mido_count']} messages")
    print(f"  FileParser: {results['fileparser_count']} messages")
    
    print(f"\nMatching Messages: {len(results['matches'])}")
    if results['matches']:
        print("  (First 10 matches)")
        for match in results['matches'][:10]:
            print(f"    - {match['type']} at {match['timestamp']:.6f}s (ch{match['channel']})")
    
    print(f"\nMismatches: {len(results['mismatches'])}")
    for mismatch in results['mismatches']:
        print(f"  - {mismatch['type']} at {mismatch['timestamp']:.6f}s (ch{mismatch['channel']})")
        for diff in mismatch['data_diff']:
            print(f"      {diff['field']}: mido={diff['mido_value']}, FileParser={diff['fileparser_value']}")
    
    print(f"\nMessages only in mido: {len(results['mido_only'])}")
    if results['mido_only']:
        print("  (First 5)")
        for msg in results['mido_only'][:5]:
            print(f"    - {msg['type']} at {msg['timestamp']:.6f}s")
    
    print(f"\nMessages only in FileParser: {len(results['fileparser_only'])}")
    if results['fileparser_only']:
        print("  (First 5)")
        for msg in results['fileparser_only'][:5]:
            print(f"    - {msg['type']} at {msg['timestamp']:.6f}s")
    
    # Calculate match percentage
    total_compared = len(results['matches']) + len(results['mismatches'])
    if total_compared > 0:
        match_percentage = (len(results['matches']) / total_compared) * 100
        print(f"\nMatch Rate: {match_percentage:.2f}%")
    
    print("\n" + "=" * 80)


def main():
    """Main test function."""
    test_file = "tests/test.mid"
    
    if not os.path.exists(test_file):
        print(f"Error: Test file not found: {test_file}")
        return 1
    
    print(f"Parsing MIDI file: {test_file}")
    print("-" * 80)
    
    # Parse with mido
    print("\n1. Parsing with mido library...")
    try:
        mido_messages, mido_info = parse_with_mido(test_file)
        print(f"   ✓ Successfully parsed {len(mido_messages)} messages")
        print(f"   Format: {mido_info['format']}, Tracks: {mido_info['tracks']}, Ticks/Beat: {mido_info['ticks_per_beat']}")
    except Exception as e:
        print(f"   ✗ Error parsing with mido: {e}")
        return 1
    
    # Parse with FileParser
    print("\n2. Parsing with FileParser...")
    try:
        fileparser_messages, fp_info = parse_with_fileparser(test_file)
        print(f"   ✓ Successfully parsed {len(fileparser_messages)} messages")
        print(f"   Format: {fp_info['midi_format']}, Tracks: {fp_info['tracks']}, Division: {fp_info['division']}")
    except Exception as e:
        print(f"   ✗ Error parsing with FileParser: {e}")
        return 1
    
    # Normalize messages for comparison
    print("\n3. Normalizing messages for comparison...")
    mido_normalized = [normalize_mido_message(msg) for msg in mido_messages]
    fp_normalized = [normalize_fileparser_message(msg) for msg in fileparser_messages]
    
    # Compare results
    print("\n4. Comparing results...")
    comparison_results = compare_messages(mido_normalized, fp_normalized)
    
    # Print results
    print_comparison_results(comparison_results)
    
    # Determine test result
    if len(comparison_results['mismatches']) == 0 and len(comparison_results['mido_only']) == 0 and len(comparison_results['fileparser_only']) == 0:
        print("\n✓ TEST PASSED: Both parsers produce identical results!")
        return 0
    else:
        print("\n✗ TEST FAILED: Parsers produce different results")
        return 1


if __name__ == "__main__":
    sys.exit(main())