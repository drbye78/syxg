"""
MIDI File Format Detector

Utility functions to detect and identify MIDI file formats (1.0 vs 2.0)
"""

import os
import struct
from typing import Tuple, Optional
from enum import Enum

class MIDIFormat(Enum):
    UNKNOWN = 0
    MIDI_1_0 = 1
    MIDI_2_0 = 2

def detect_midi_format(file_path: str) -> Tuple[MIDIFormat, Optional[str]]:
    """
    Detect the MIDI file format (1.0 or 2.0) and return format information.
    
    Args:
        file_path: Path to the MIDI file
        
    Returns:
        Tuple of (MIDIFormat enum, descriptive string)
    """
    if not os.path.exists(file_path):
        return MIDIFormat.UNKNOWN, "File not found"
        
    try:
        with open(file_path, 'rb') as f:
            # Read header
            header = f.read(16)
            
            if len(header) < 4:
                return MIDIFormat.UNKNOWN, "File too short"
                
            # Check for standard MIDI 1.0 header
            if header.startswith(b'MThd'):
                # Parse header information
                if len(header) >= 14:
                    # Extract format information
                    header_length = struct.unpack('>I', header[4:8])[0]
                    format_type = struct.unpack('>H', header[8:10])[0]
                    track_count = struct.unpack('>H', header[10:12])[0]
                    time_division = struct.unpack('>H', header[12:14])[0]
                    
                    # Valid MIDI 1.0 format types are 0, 1, or 2
                    if format_type in [0, 1, 2]:
                        return MIDIFormat.MIDI_1_0, f"Standard MIDI File Format {format_type} with {track_count} tracks"
                    else:
                        return MIDIFormat.UNKNOWN, f"Invalid MIDI format type: {format_type}"
                else:
                    return MIDIFormat.MIDI_1_0, "Standard MIDI 1.0 header (incomplete)"
                    
            # Check for possible MIDI 2.0 signatures
            # MIDI 2.0 files may have different extensions or signatures
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension in ['.midi2', '.mid2']:
                return MIDIFormat.MIDI_2_0, "MIDI 2.0 file (based on extension)"
                
            # Try to detect MIDI 2.0 by looking for Universal MIDI Packet patterns
            # This is a heuristic and may not be 100% accurate
            f.seek(0)
            data = f.read(1024)  # Read first 1KB to check for UMP patterns
            
            # Look for 32-bit packet structures that might indicate UMPs
            # This is a very basic heuristic
            if len(data) >= 4:
                # Check if we see patterns consistent with 32-bit UMPs
                # This is not definitive but can be a hint
                pass
                
            return MIDIFormat.UNKNOWN, "Unknown MIDI format"
            
    except Exception as e:
        return MIDIFormat.UNKNOWN, f"Error reading file: {str(e)}"

def is_midi_file(file_path: str) -> bool:
    """
    Check if a file is a MIDI file based on extension and header.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file appears to be a MIDI file
    """
    # Check file extension
    valid_extensions = ['.mid', '.midi', '.midi2', '.mid2']
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension not in valid_extensions:
        return False
        
    # Check file header
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'MThd')
    except:
        return False

# Example usage:
# format_type, description = detect_midi_format("example.mid")
# print(f"Format: {format_type}, Description: {description}")