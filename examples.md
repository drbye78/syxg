# XG Synthesizer API Examples

## Basic Usage Examples

### 1. Simple Note Playback

```python
from xg_synthesizer import XGSynthesizer
import time

# Create synthesizer
synth = XGSynthesizer(sample_rate=44100, block_size=512)

# Load SF2 file (replace with actual path)
# synth.set_sf2_files(["path/to/soundfont.sf2"])

# Play a simple melody
melody = [60, 62, 64, 65, 67, 69, 71, 72]  # C Major scale

for note in melody:
    # Note On
    synth.send_midi_message(0x90, note, 100)
    time.sleep(0.5)  # Hold note for 0.5 seconds
    
    # Note Off
    synth.send_midi_message(0x80, note, 64)
    time.sleep(0.1)  # Short pause between notes

print("Melody playback completed")
```

### 2. Chord Progression

```python
from xg_synthesizer import XGSynthesizer
import time

synth = XGSynthesizer()

# Define chords (C major, F major, G major, C major)
chords = [
    [60, 64, 67],  # C major (C-E-G)
    [65, 69, 72],  # F major (F-A-C)
    [67, 71, 74],  # G major (G-B-D)
    [60, 64, 67]   # C major (C-E-G)
]

# Select piano program
synth.send_midi_message(0xC0, 0)  # Program 0 = Piano

# Play chord progression
for chord in chords:
    # Play all notes in chord
    for note in chord:
        synth.send_midi_message(0x90, note, 90)
    
    time.sleep(1.0)  # Hold chord
    
    # Release all notes in chord
    for note in chord:
        synth.send_midi_message(0x80, note, 64)
    
    time.sleep(0.2)  # Short pause

print("Chord progression completed")
```

### 3. Real-time Audio Generation

```python
from xg_synthesizer import XGSynthesizer
import numpy as np

def generate_real_time_audio(duration_seconds=5.0):
    """
    Generate real-time audio with changing parameters
    """
    sample_rate = 44100
    block_size = 1024
    synth = XGSynthesizer(sample_rate=sample_rate, block_size=block_size)
    
    # Calculate number of blocks needed
    total_samples = int(duration_seconds * sample_rate)
    blocks_needed = total_samples // block_size
    
    all_left = []
    all_right = []
    
    # Play a sustained note with modulating parameters
    synth.send_midi_message(0x90, 60, 100)  # C4
    
    for block_num in range(blocks_needed):
        # Modulate parameters over time
        time_position = block_num / blocks_needed
        
        # Change modulation wheel
        mod_wheel_value = int(127 * (0.5 + 0.5 * np.sin(2 * np.pi * time_position * 2)))
        synth.send_midi_message(0xB0, 1, mod_wheel_value)
        
        # Change expression
        expression_value = int(127 * (0.7 + 0.3 * np.sin(2 * np.pi * time_position * 0.5)))
        synth.send_midi_message(0xB0, 11, expression_value)
        
        # Generate audio block
        left, right = synth.generate_audio_block(block_size)
        all_left.extend(left)
        all_right.extend(right)
    
    # Note off
    synth.send_midi_message(0x80, 60, 64)
    
    return np.array(all_left), np.array(all_right)

# Generate audio
left_audio, right_audio = generate_real_time_audio(3.0)
print(f"Generated {len(left_audio)} stereo samples")
```

## Advanced Usage Examples

### 4. Multi-timbral Setup

```python
from xg_synthesizer import XGSynthesizer
import time

synth = XGSynthesizer(max_polyphony=128)

# Setup different instruments on different channels
# Channel 0: Piano
synth.send_midi_message(0xC0, 0)  # Channel 0, Program 0 (Piano)

# Channel 1: Strings
synth.send_midi_message(0xC1, 48)  # Channel 1, Program 48 (Strings)

# Channel 2: Brass
synth.send_midi_message(0xC2, 56)  # Channel 2, Program 56 (Trumpet)

# Play notes on different channels
notes_channel_0 = [60, 64, 67, 72]  # C major chord on piano
notes_channel_1 = [48, 52, 55]      # C major triad on strings (lower octave)
notes_channel_2 = [60, 62, 64]      # Melody on brass

# Play simultaneously
for i in range(max(len(notes_channel_0), len(notes_channel_1), len(notes_channel_2))):
    if i < len(notes_channel_0):
        synth.send_midi_message(0x90, notes_channel_0[i], 80)  # Channel 0
    if i < len(notes_channel_1):
        synth.send_midi_message(0x91, notes_channel_1[i], 70)  # Channel 1
    if i < len(notes_channel_2):
        synth.send_midi_message(0x92, notes_channel_2[i], 90)  # Channel 2
    
    time.sleep(0.3)

# Release all notes
for note in notes_channel_0:
    synth.send_midi_message(0x80, note, 64)
for note in notes_channel_1:
    synth.send_midi_message(0x81, note, 64)
for note in notes_channel_2:
    synth.send_midi_message(0x82, note, 64)

print("Multi-timbral playback completed")
```

### 5. XG System Exclusive Messages

```python
from xg_synthesizer import XGSynthesizer

synth = XGSynthesizer()

# XG System On
xg_system_on = [0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7]
synth.send_sysex(xg_system_on)

# Set reverb type to "Hall 1"
reverb_type_hall1 = [0xF0, 0x43, 0x10, 0x4C, 0x02, 0x01, 0x00, 0x00, 0xF7]
synth.send_sysex(reverb_type_hall1)

# Set chorus type to "Chorus 1"
chorus_type_chorus1 = [0xF0, 0x43, 0x10, 0x4C, 0x02, 0x01, 0x01, 0x00, 0xF7]
synth.send_sysex(chorus_type_chorus1)

# Set variation effect
variation_effect = [0xF0, 0x43, 0x10, 0x4C, 0x02, 0x01, 0x02, 0x00, 0xF7]
synth.send_sysex(variation_effect)

print("XG system messages sent")
```

### 6. RPN/NRPN Parameter Control

```python
from xg_synthesizer import XGSynthesizer

synth = XGSynthesizer()

# Set Pitch Bend Range using RPN
# RPN MSB = 0, LSB = 0 (Pitch Bend Range)
synth.send_midi_message(0xB0, 101, 0)  # RPN MSB
synth.send_midi_message(0xB0, 100, 0)  # RPN LSB
synth.send_midi_message(0xB0, 6, 2)    # Data Entry MSB (2 semitones)
synth.send_midi_message(0xB0, 38, 0)  # Data Entry LSB (0 cents)

# Set Fine Tuning using RPN
# RPN MSB = 0, LSB = 1 (Fine Tuning)
synth.send_midi_message(0xB0, 101, 0)  # RPN MSB
synth.send_midi_message(0xB0, 100, 1)  # RPN LSB
synth.send_midi_message(0xB0, 6, 64)   # Data Entry MSB (center)
synth.send_midi_message(0xB0, 38, 0)  # Data Entry LSB (0 cents)

# Set Coarse Tuning using RPN
# RPN MSB = 0, LSB = 2 (Coarse Tuning)
synth.send_midi_message(0xB0, 101, 0)  # RPN MSB
synth.send_midi_message(0xB0, 100, 2)  # RPN LSB
synth.send_midi_message(0xB0, 6, 64)   # Data Entry MSB (center)
synth.send_midi_message(0xB0, 38, 0)   # Data Entry LSB (0 cents)

print("RPN parameters set")
```

### 7. Drum Kit Programming

```python
from xg_synthesizer import XGSynthesizer
import time

synth = XGSynthesizer()

# Switch to drum channel (usually channel 9 in XG)
# Set bank to 128 for drums
synth.send_midi_message(0xB9, 0, 128)  # Bank select MSB
synth.send_midi_message(0xB9, 32, 0)   # Bank select LSB
synth.send_midi_message(0xC9, 0)      # Program 0 on drum channel

# Play drum pattern
drum_pattern = [
    (36, 100),  # Bass Drum
    (38, 80),   # Snare Drum
    (42, 70),   # Closed Hi-hat
    (46, 70),   # Open Hi-hat
    (49, 90),   # Crash Cymbal
    (51, 80),   # Ride Cymbal
]

# Play rhythm
for beat in range(16):
    for drum_note, velocity in drum_pattern:
        # Play on beats 0, 4, 8, 12
        if beat % 4 == 0 and drum_note == 36:  # Bass drum on main beats
            synth.send_midi_message(0x99, drum_note, velocity)
            synth.send_midi_message(0x89, drum_note, 64)
        elif beat % 2 == 0 and drum_note == 38:  # Snare on back beats
            synth.send_midi_message(0x99, drum_note, velocity)
            synth.send_midi_message(0x89, drum_note, 64)
        elif drum_note in [42, 46]:  # Hi-hats on every beat
            synth.send_midi_message(0x99, drum_note, velocity)
            synth.send_midi_message(0x89, drum_note, 64)
    
    time.sleep(0.25)  # 16th note timing at 120 BPM

print("Drum pattern completed")
```

### 8. Performance Monitoring

```python
from xg_synthesizer import XGSynthesizer
import time

synth = XGSynthesizer()

# Monitor system performance
def monitor_performance():
    print("=== Performance Monitor ===")
    print(f"Sample Rate: {synth.sample_rate} Hz")
    print(f"Block Size: {synth.block_size} samples")
    print(f"Max Polyphony: {synth.max_polyphony}")
    print(f"Current Active Voices: {synth.get_active_voice_count()}")
    
    # Available programs
    programs = synth.get_available_programs()
    print(f"Available Programs: {len(programs)}")
    if programs:
        print("First 5 programs:")
        for bank, prog, name in programs[:5]:
            print(f"  Bank {bank}, Program {prog}: {name}")

# Play some notes and monitor
monitor_performance()

notes = [60, 64, 67, 72]
for note in notes:
    synth.send_midi_message(0x90, note, 100)
    time.sleep(0.1)

print(f"After playing notes - Active Voices: {synth.get_active_voice_count()}")

# Release notes
for note in notes:
    synth.send_midi_message(0x80, note, 64)

monitor_performance()
```

These examples demonstrate the core functionality of the XG synthesizer, showing how to:
- Play individual notes and chords
- Generate real-time audio with parameter modulation
- Use multi-timbral setups with different instruments
- Send XG system exclusive messages
- Control parameters via RPN/NRPN
- Program drum kits
- Monitor performance metrics

The synthesizer is designed to be flexible and extensible, allowing integration into various musical applications.