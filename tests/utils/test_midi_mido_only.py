"""
Simple test script to parse MIDI file using mido library only.

This script parses 'tests/test.mid' using mido and displays the results.
"""

import sys
import os
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido


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
    tempo = 500000  # Default tempo (120 BPM)
    
    for track_idx, track in enumerate(mid.tracks):
        track_time = 0.0
        
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


def print_messages(messages: list[dict[str, Any]], file_info: dict[str, Any], max_messages: int = 50):
    """
    Print messages in a readable format.
    
    Args:
        messages: List of message dictionaries
        file_info: File information dictionary
        max_messages: Maximum number of messages to print
    """
    print("\n" + "=" * 80)
    print("MIDI FILE PARSING RESULTS (mido)")
    print("=" * 80)
    
    print(f"\nFile Info:")
    print(f"  Format: {file_info['format']}")
    print(f"  Tracks: {file_info['tracks']}")
    print(f"  Ticks/Beat: {file_info['ticks_per_beat']}")
    print(f"  Total Messages: {len(messages)}")
    
    print(f"\nMessages (showing first {min(max_messages, len(messages))}):")
    print("-" * 80)
    
    for i, msg in enumerate(messages[:max_messages]):
        time_str = f"{msg['time']:.6f}s"
        type_str = msg['type']
        
        # Build data string
        data_parts = []
        if 'channel' in msg:
            data_parts.append(f"ch{msg['channel']}")
        if 'note' in msg:
            data_parts.append(f"note={msg['note']}")
        if 'velocity' in msg:
            data_parts.append(f"vel={msg['velocity']}")
        if 'controller' in msg:
            data_parts.append(f"cc={msg['controller']}")
        if 'value' in msg:
            data_parts.append(f"val={msg['value']}")
        if 'program' in msg:
            data_parts.append(f"prog={msg['program']}")
        if 'text' in msg:
            data_parts.append(f"text=\"{msg['text'][:30]}...\"" if len(msg['text']) > 30 else f"text=\"{msg['text']}\"")
        if 'name' in msg:
            data_parts.append(f"name=\"{msg['name']}\"")
        if 'key' in msg:
            data_parts.append(f"key={msg['key']}")
        if 'numerator' in msg:
            data_parts.append(f"time_sig={msg['numerator']}/{msg['denominator']}")
        
        data_str = ", ".join(data_parts) if data_parts else ""
        
        print(f"  [{i+1:4d}] {time_str:12s} {type_str:20s} {data_str}")
    
    if len(messages) > max_messages:
        print(f"\n  ... and {len(messages) - max_messages} more messages")
    
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
    print("\nParsing with mido library...")
    try:
        messages, file_info = parse_with_mido(test_file)
        print(f"✓ Successfully parsed {len(messages)} messages")
    except Exception as e:
        print(f"✗ Error parsing with mido: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print results
    print_messages(messages, file_info)
    
    # Count message types
    print("\nMessage Type Statistics:")
    print("-" * 40)
    type_counts = {}
    for msg in messages:
        msg_type = msg['type']
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
    
    for msg_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {msg_type:25s}: {count:5d}")
    
    print("\n✓ Test completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())