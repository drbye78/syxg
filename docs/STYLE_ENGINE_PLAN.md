# Style Engine Implementation Plan

## Priority 1: Core Integration (High)

### 1.1 Integrate StylePlayer with Synthesizer Core

**Objective**: Connect StylePlayer to the main synthesizer for MIDI routing

**Tasks**:
1. Modify synth/core/synthesizer.py:
   - Add StylePlayer import
   - Add style_player: Optional[StylePlayer] attribute
   - Add initialize_style_engine() method
   - Add process_midi_to_style() method for chord detection

2. Add MIDI input routing in Synthesizer.note_on():
   - Route left-hand notes (channels 0-1, notes < 60) to chord detector
   - Route right-hand notes to normal voice processing

3. Add MIDI output routing from StylePlayer:
   - Route style notes to appropriate channels
   - Handle velocity, timing, and events

4. Add control methods:
   - synthesizer.start_style(section?)
   - synthesizer.stop_style()
   - synthesizer.set_style_section(name)
   - synthesizer.trigger_style_fill()
   - synthesizer.set_style_tempo(bpm)
   - synthesizer.set_style_dynamics(value)

**File Changes**:
- synth/core/synthesizer.py - Add StylePlayer integration
- synth/style/auto_accompaniment.py - Refine MIDI callbacks


### 1.2 Full Chord Table Integration

**Objective**: Use chord tables for intelligent note mapping

**Tasks**:
1. Enhance AutoAccompaniment._map_note_to_chord():
   - Load chord table for current section
   - Look up note intervals for detected chord type
   - Map style notes to correct chord tones
   - Handle bass note separately

2. Add ChordTable lookup in AutoAccompaniment:
   - Load chord table when section changes
   - Cache current chord table
   - Handle missing chord types gracefully

3. Extend chord detection:
   - Add more chord types (13th, altered dominants)
   - Add tension note detection (9, 11, 13)
   - Improve inversion handling

4. Add chord vocabulary:
   - Support for slash chords (C/E, Am/G)
   - Add sus4/9 chords
   - Add diminished/half-diminished

**File Changes**:
- synth/style/auto_accompaniment.py - Enhance note mapping
- synth/style/chord_detector.py - Extend chord types
- synth/style/style.py - Add more chord table structures


### 1.3 Complete Section Transition Logic

**Objective**: Implement proper fill triggering and section transitions

**Tasks**:
1. Enhance section state machine:
   - States: STOPPED, WAITING, COUNT_IN, PLAYING, TRANSITIONING
   - Handle INTRO -> MAIN transitions
   - Handle MAIN -> FILL -> MAIN (next) transitions
   - Handle MAIN -> ENDING transitions
   - Handle BREAK -> MAIN transitions

2. Implement fill system:
   - Detect when user requests section change
   - Trigger appropriate fill section (1 bar)
   - Auto-advance to target section after fill
   - Handle manual vs auto fill modes

3. Add transition timing:
   - Configurable fill length
   - Count-in handling
   - Synced start (wait for first key)

4. Add section change callbacks:
   - Notify UI of section changes
   - Update OTS if linked
   - Update display indicators

**File Changes**:
- synth/style/auto_accompaniment.py - State machine and transitions
- synth/style/style_player.py - Section control methods


## Priority 2: Processing Features (Medium)

### 2.1 Groove Quantization

**Objective**: Apply groove templates to style timing

**Tasks**:
1. Create GrooveTemplate class:
   - Define groove patterns (swing, shuffle, funk, etc.)
   - Store timing offsets per 16th note
   - Support groove strength parameter

2. Add groove processing:
   - Load groove template in StyleTrackData
   - Apply timing offsets during event scheduling
   - Handle groove intensity parameter

3. Create built-in groove library:
   - Swing 1:3 (basic swing)
   - Swing 2:3 (strong swing)
   - Shuffle
   - Funk
   - Pop
   - Latin

4. Add groove UI controls:
   - Select groove template
   - Adjust groove intensity


### 2.2 Swing and Humanize Processing

**Objective**: Add natural timing variations

**Tasks**:
1. Implement swing processing:
   - Shift even 16th notes later
   - Make swing amount configurable (0-100%)
   - Apply per-track or global

2. Implement humanize:
   - Random velocity variation (+-%)
   - Random timing variation (+-ticks)
   - Random note duration variation
   - Per-note vs continuous modes

3. Add parameters to StyleTrackData:
   - swing: float (-1.0 to 1.0)
   - humanize: float (0.0 to 1.0)
   - humanize_velocity: float
   - humanize_timing: float
   - humanize_duration: float

4. Apply in event scheduling:
   - Calculate swing offset per beat
   - Apply humanize at event trigger time
   - Store original timing for reset


### 2.3 Extended OTS System

**Objective**: Full OTS implementation with section linking

**Tasks**:
1. Extend OTSPreset:
   - Add 8 preset slots (vs current 4)
   - Add preset names
   - Add detailed part configurations

2. Implement section linking:
   - Link OTS to specific style sections
   - Auto-load OTS when section changes
   - Manual OTS override option

3. Add OTS MIDI handling change on:
   - Program part change
   - Bank select (MSB/LSB)
   - Volume/pan/effects sends

4. Add OTS UI methods:
   - ots.activate_preset(id)
   - ots.store_current_to_preset(id)
   - ots.copy_preset(from, to)


### 2.4 Registration Memory Integration

**Objective**: Connect registration to synthesizer

**Tasks**:
1. Enhance Registration class:
   - Store full voice configurations
   - Store effect parameters
   - Store style/section selections
   - Store tempo/transpose/tuning

2. Implement recall logic:
   - Load voices to parts
   - Apply effect settings
   - Set style and section
   - Apply master settings

3. Implement store logic:
   - Capture current synthesizer state
   - Store to registration slot
   - Handle partial data

4. Add bank management:
   - 8 banks x 16 slots
   - Bank/slot navigation
   - Copy/clear operations

5. Add file I/O:
   - Save registrations to JSON
   - Load registrations from file
   - Import/export functionality


## Priority 3: Advanced Features (Low)

### 3.1 MIDI Learn System

**Objective**: Allow user mapping of controllers

**Tasks**:
1. Create MIDILearn class:
   - Store CC mappings (CC# -> target)
   - Handle learn mode toggle
   - Persist mappings

2. Add mappable targets:
   - Style play/stop
   - Section changes (Intro/Main A-D/Fill/Ending)
   - OTS changes
   - Registration changes
   - Dynamics
   - Volume controls

3. Add default mappings:
   - Foot switches for sections
   - Knobs for effects
   - Buttons for registrations


### 3.2 Scale/Tuning Integration

**Objective**: Support micro-tuning and scale settings

**Tasks**:
1. Add ScaleSetting class:
   - Scale type (equal, just, pythagorean, etc.)
   - Root note
   - Custom note mappings

2. Implement scale application:
   - Apply to style chord detection
   - Apply to MIDI note output
   - Handle scale follow mode

3. Add tuning system:
   - Master tuning (cents)
   - Part tuning
   - Scale-independent tuning


### 3.3 Additional Example Styles

**Objective**: Create comprehensive style library

**Tasks**:
1. Create genre styles:
   - pop_ballad.yaml (done)
   - pop_straight.yaml
   - rock_standard.yaml
   - rock_heavy.yaml
   - jazz_swing.yaml
   - jazz_bossa.yaml
   - latin_salsa.yaml
   - latin_bossa.yaml
   - dance_electronic.yaml
   - country_standard.yaml
   - waltz_simple.yaml

2. Each style should have:
   - All sections (Intro 1-3, Main A-D, Fill A-D, Break, Ending 1-3)
   - Realistic patterns
   - Chord tables
   - OTS presets

3. Add style documentation:
   - Genre description
   - Recommended usage
   - Parameter suggestions


### 3.4 Yamaha .sty Parser (Optional)

**Objective**: Support proprietary style format

**Tasks**:
1. Research .sty format:
   - Analyze existing .sty files
   - Identify binary structures
   - Document chord/note encoding

2. Create STYParser class:
   - Binary file reading
   - Section data extraction
   - Pattern decoding
   - OTS extraction

3. Add converter:
   - .sty -> YAML conversion
   - Preserve all data
   - Handle unknown fields gracefully

Note: This is low priority as YAML format is more maintainable


## Implementation Order

Phase 1: Core Integration (Week 1-2)
- 1.1 Synthesizer integration
- 1.2 Chord table integration
- 1.3 Section transitions

Phase 2: Processing (Week 2-3)
- 2.1 Groove quantization
- 2.2 Swing/humanize
- 2.3 OTS extension
- 2.4 Registration integration

Phase 3: Advanced (Week 3-4)
- 3.1 MIDI learn
- 3.2 Scale/tuning
- 3.3 Example styles
- 3.4 .sty parser (optional)


## Testing Plan

Unit Tests:
- ChordDetector: 30+ chord types
- StyleLoader: Valid/invalid files
- Note mapping: Chord-following accuracy
- Section transitions: State machine

Integration Tests:
- Synthesizer -> StylePlayer -> output
- MIDI input -> chord detection -> style playback
- OTS -> voice changes
- Registration -> recall/store

Style Tests:
- Load all example styles
- Verify all sections play
- Check chord following
- Validate transitions


## Files to Modify/Create

Modified:
- synth/core/synthesizer.py
- synth/xg/xg_system.py
- synth/style/auto_accompaniment.py
- synth/style/chord_detector.py
- synth/style/style_player.py
- synth/style/style_ots.py
- synth/style/registration.py

Created:
- synth/style/groove.py (new)
- synth/style/midi_learn.py (new)
- synth/style/scale.py (new)
- synth/parsers/sty_parser.py (new)
- examples/styles/*.yaml (multiple)
