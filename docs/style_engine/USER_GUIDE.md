# Style Engine User Guide

## Quick Start

### Basic Usage

```python
from synth.style import StyleLoader, StylePlayer, AutoAccompaniment

# Create synthesizer (your synth implementation)
synth = YourSynthesizer(sample_rate=44100)

# Create style player
player = StylePlayer(synth)

# Load a style
loader = StyleLoader()
style = loader.load_style_file("examples/styles/edm_pop.yaml")
player.load_style(style)

# Start playback
player.start()

# Play chords with left hand (notes 36-60)
# Style automatically follows chords
```

### Section Navigation

```python
# Change to different sections
player.set_section("main_a")
player.set_section("main_b")

# Trigger fill before next section
player.trigger_fill()

# Go to intro
player.trigger_intro(length=2)

# Go to ending
player.trigger_ending(length=2)

# Cycle through sections
player.next_section()
```

## Chord Detection

### Detection Zone

By default, chords are detected in the range C2-C5 (MIDI 36-72):
- **Bass zone**: C2-C3 (36-48) - Determines inversions
- **Chord zone**: C3-C5 (48-72) - Determines chord type

### Supported Chords

The enhanced chord detector supports 50+ chord types:

| Type | Notation | Example | Notes |
|------|----------|---------|-------|
| Major | C | C, D, E | Root, 3rd, 5th |
| Minor | Cm | Cm, Dm, Em | Root, b3, 5th |
| Seventh | C7 | C7, D7 | Dominant 7th |
| Major Seventh | Cmaj7 | Cmaj7, Dmaj7 | Major triad + maj7 |
| Minor Seventh | Cm7 | Cm7, Dm7 | Minor triad + b7 |
| Minor Seventh Flat Five | Cm7b5 | Cm7b5 | Half-diminished |
| Diminished | Cdim | Cdim | Root, b3, b5 |
| Diminished Seventh | Cdim7 | Cdim7 | Fully diminished |
| Augmented | Caug | Caug | Root, 3rd, #5 |
| Suspended Fourth | Csus4 | Csus4 | Root, 4th, 5th |
| Suspended Second | Csus2 | Csus2 | Root, 2nd, 5th |
| Sixth | C6 | C6 | Major triad + 6th |
| Ninth | C9 | C9 | Dominant 9th |
| Major Ninth | Cmaj9 | Cmaj9 | Major 9th |
| Minor Ninth | Cm9 | Cm9 | Minor 9th |
| Eleventh | C11 | C11 | Dominant 11th |
| Thirteenth | C13 | C13 | Dominant 13th |
| Power | C5 | C5 | Root, 5th only |

### Fuzzy Matching

The enhanced detector handles:
- Extra notes (tensions like 9th, 11th, 13th)
- Missing notes (can detect from just root + 3rd)
- Inversions (bass note detection)

```python
from synth.style.chord_detection_enhanced import EnhancedChordDetector

detector = EnhancedChordDetector()

# Even with extra tension notes, detects correctly
detector.note_on(60)  # C
detector.note_on(64)  # E
detector.note_on(67)  # G
detector.note_on(74)  # D (9th)

chord = detector.get_current_chord()
print(chord.chord_name)  # "C" or "Cadd9"
```

## Scale Detection

The scale detector identifies the musical key from played notes:

```python
from synth.style import ScaleDetector

scale_detector = ScaleDetector()

# Play C major scale
for note in [60, 62, 64, 65, 67, 69, 71]:
    scale_detector.add_note(note)

scale = scale_detector.get_current_scale()
if scale:
    print(f"Key: {scale.full_name}")  # "C Major (Ionian)"
    print(f"Confidence: {scale.confidence:.2f}")
```

### Supported Scales

- Major (Ionian)
- Natural Minor (Aeolian)
- Harmonic Minor
- Melodic Minor
- Dorian
- Phrygian
- Lydian
- Mixolydian
- Locrian
- Pentatonic Major
- Pentatonic Minor
- Blues Major
- Blues Minor
- Whole Tone
- Diminished (Octatonic)

## OTS (One Touch Settings)

OTS provides instant voice changes linked to your style:

```python
# Activate OTS preset
player.set_ots_preset(0)  # Piano
player.set_ots_preset(1)  # Organ

# Next/previous preset
player.next_ots()
```

Each style includes 8 OTS presets with complete voice configurations.

## Registration Memory

Save and recall complete panel setups:

```python
from synth.style import RegistrationMemory

memory = RegistrationMemory()
memory.set_synthesizer(synth)

# Store current setup
memory.store(name="My Setup", bank=0, slot=0)

# Recall setup
memory.recall(bank=0, slot=0)

# Navigate
memory.next_bank()
memory.next_slot()

# Save to file
memory.save_to_file("my_registrations.json")

# Load from file
memory = RegistrationMemory.load_from_file("my_registrations.json")
```

### Freeze Function

Exclude specific parameters from recall:

```python
from synth.style.registration import RegistrationParameter

# Freeze tempo across all registrations
memory.set_global_freeze(RegistrationParameter.TEMPO, True)

# Now recalling registrations won't change tempo
memory.recall(bank=0, slot=1)  # Tempo stays the same
```

## Dynamics Control

Adjust style intensity:

```python
from synth.style import StyleDynamics

dynamics = StyleDynamics()

# Set dynamics (0-127)
dynamics.set_dynamics(64)  # Medium

# Adjust incrementally
dynamics.adjust(10)   # Louder
dynamics.adjust(-10)  # Softer

# Get current parameter values
velocity_scale = dynamics.get_velocity_scale()
volume_scale = dynamics.get_volume_scale()
```

## Groove and Swing

Apply rhythmic feel:

```python
from synth.style.groove import GrooveQuantizer, GrooveType

quantizer = GrooveQuantizer()

# Set groove type
quantizer.set_groove(GrooveType.SWING_1_3)
quantizer.set_groove_by_name("shuffle")

# Adjust intensity
quantizer.set_intensity(0.7)  # 70%

# Available grooves:
# - swing_1_3, swing_2_3
# - shuffle, funk, pop
# - latin, jazz, bossa
# - waltz
```

## MIDI Learn

Map physical controllers to style parameters:

```python
from synth.style import MIDILearn, LearnTargetType

learn = MIDILearn()

# Start learn mode for tempo
learn.start_learn(LearnTargetType.STYLE_TEMPO, "tempo")

# Turn a knob on your MIDI controller
# The CC is automatically mapped

# Process MIDI
result = learn.process_midi(cc_number=1, channel=0, value=64)
if result:
    print(f"Target: {result['target_type']}")
    print(f"Value: {result['value']}")

# Save mappings
learn.save_to_file("my_mappings.json")

# Load mappings
learn.load_from_file("my_mappings.json")
```

### Mappable Targets

| Target | Type | Description |
|--------|------|-------------|
| STYLE_START_STOP | Toggle | Start/stop style |
| STYLE_SECTION_A-D | Select | Select main section |
| STYLE_FILL | Trigger | Trigger fill |
| STYLE_TEMPO | Continuous | Tempo control (40-280) |
| STYLE_DYNAMICS | Continuous | Dynamics (0-127) |
| STYLE_VOLUME | Continuous | Volume (0-127) |
| OTS_1-8 | Select | Select OTS preset |
| EFFECT_REVERB | Continuous | Reverb send |
| EFFECT_CHORUS | Continuous | Chorus send |

### Response Curves

- **linear**: Direct mapping
- **exponential**: More sensitivity at low values
- **logarithmic**: More sensitivity at high values
- **sine**: S-curve for fine control

```python
from synth.style.midi_learn import MIDILearnMapping

mapping = MIDILearnMapping(
    cc_number=1,
    channel=0,
    target_type=LearnTargetType.STYLE_TEMPO,
    target_param="tempo",
    min_val=40,
    max_val=280,
    curve="exponential",  # Fine control at low tempo
)
learn.add_mapping(mapping)
```

## Style File Format

Styles are stored in YAML format:

```yaml
style_format_version: "1.0"

metadata:
  name: "EDM Pop"
  category: "POP"
  tempo: 128
  author: "Your Name"

sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1:
        notes:
          - tick: 0
            note: 36
            velocity: 100
            duration: 120
      bass:
        notes:
          - tick: 0
            note: 36
            velocity: 90
            duration: 480

chord_tables:
  main_a:
    mappings:
      "0_major":
        chord_1: [0, 4, 7]
        bass: [0]
```

## Performance Tips

1. **Use sync-start** for tight timing with live playing
2. **Enable count-in** for predictable starts
3. **Adjust detection zone** based on your playing style
4. **Use freeze** for parameters you want to control manually
5. **Save registrations** for quick setup changes

## Troubleshooting

### Chords not detected
- Check notes are in detection zone (36-72)
- Ensure at least 2-3 notes are played
- Check for conflicting notes outside the chord

### Timing issues
- Reduce block_size for lower latency
- Use higher sample_rate if available
- Enable sync-start for live playing

### Style not playing
- Check style is loaded
- Verify start() was called
- Check track mute states
