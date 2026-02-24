# Style Engine API Reference

## Core Classes

### Style

Main container for style data.

```python
class Style:
    """
    Complete style data structure.
    
    Attributes:
        metadata: StyleMetadata with name, tempo, category
        sections: Dict[StyleSectionType, StyleSection]
        chord_tables: Dict[StyleSectionType, ChordTable]
        default_section: StyleSectionType
    """
    
    def get_section(section_type: StyleSectionType) -> StyleSection
    def get_main_sections() -> List[StyleSection]
    def get_intro_sections() -> List[StyleSection]
    def get_ending_sections() -> List[StyleSection]
    def get_fill_for_main(main_section: StyleSectionType) -> List[StyleSection]
    def get_next_main(current: StyleSectionType) -> Optional[StyleSectionType]
    def to_dict() -> Dict[str, Any]
    def to_yaml() -> str
    def save(filepath: Path)
    
    @classmethod
    def from_dict(data: Dict[str, Any]) -> Style
    @classmethod
    def from_yaml(yaml_str: str) -> Style
    @classmethod
    def from_file(file_path: Path) -> Style
    
    @property
    def name -> str
    @property
    def tempo -> int
    @property
    def category -> StyleCategory
```

### StylePlayer

High-level style playback controller.

```python
class StylePlayer:
    """
    High-level style playback with section management.
    
    Args:
        synthesizer: Synthesizer instance
        sample_rate: Audio sample rate (default: 44100)
    """
    
    # Playback control
    def load_style(style: Style)
    def start(section: Optional[StyleSectionType] = None)
    def stop(use_ending: bool = True)
    def pause()
    def resume()
    
    # Section control
    def set_section(section: StyleSectionType)
    def next_section()
    def trigger_fill()
    def trigger_intro(length: int = 1)
    def trigger_ending(length: int = 1)
    
    # Track control
    def set_track_mute(track_type: str, muted: bool)
    def set_track_volume(track_type: str, volume: float)
    
    # OTS
    def set_ots_preset(preset_id: int)
    def next_ots()
    
    # MIDI input
    def process_midi_note_on(channel: int, note: int, velocity: int)
    def process_midi_note_off(channel: int, note: int)
    
    # Callbacks
    def set_section_change_callback(callback: Callable[[StyleSectionType, StyleSectionType], None])
    def set_chord_change_callback(callback: Callable[[DetectedChord], None])
    def set_state_change_callback(callback: Callable[[str], None])
    
    # Properties
    @property
    def is_playing -> bool
    @property
    def current_section -> Optional[StyleSectionType]
    @property
    def tempo -> float
    @tempo.setter
    def tempo(value: float)
    
    def get_status() -> Dict[str, Any]
    def reset()
    def shutdown()
```

### AutoAccompaniment

Main accompaniment engine.

```python
class AutoAccompaniment:
    """
    Core auto-accompaniment engine.
    
    Args:
        style: Style to play
        synthesizer: Synthesizer instance
        config: AutoAccompanimentConfig
        sample_rate: Audio sample rate
    """
    
    # Playback
    def start(section: Optional[Any] = None)
    def stop(ending: bool = True)
    
    # Section control
    def set_main_section(section_name: str)
    def next_main_section()
    def trigger_fill()
    def trigger_section_change(target_section: str, use_fill: bool = True)
    
    # Track control
    def set_track_mute(track_type: TrackType, muted: bool)
    def set_track_solo(track_type: TrackType, soloed: bool)
    def set_track_volume(track_type: TrackType, volume: float)
    
    # Groove/Humanize
    def set_groove(groove_type: str, intensity: float = 0.5)
    def set_swing(amount: float)
    def set_humanize(amount: float = 0.0, velocity: float = 0.0, timing: float = 0.0)
    
    # MIDI input
    def process_midi_note_on(channel: int, note: int, velocity: int)
    def process_midi_note_off(channel: int, note: int)
    
    # Callbacks
    def set_note_callbacks(note_on: Callable, note_off: Callable)
    def set_section_change_callback(callback: Callable)
    def set_chord_change_callback(callback: Callable)
    
    # Properties
    @property
    def tempo -> float
    @tempo.setter
    def tempo(value: float)
    @property
    def is_playing -> bool
    @property
    def current_section -> Any
    
    def get_status() -> Dict[str, Any]
    def reset()
    def shutdown()
```

## Chord Detection

### ChordDetector

Basic chord detection.

```python
class ChordDetector:
    """
    Real-time chord detection.
    
    Args:
        config: Optional ChordDetectionConfig
    """
    
    def note_on(note: int, velocity: int = 100, timestamp: float = None)
    def note_off(note: int)
    def get_current_chord() -> Optional[DetectedChord]
    def get_chord_history(count: int = 10) -> List[DetectedChord]
    def force_chord(root: ChordRoot, chord_type: ChordType, bass_note: int = None)
    def reset()
    def get_active_notes() -> List[int]
    
    @property
    def detection_count -> int
    
    def get_detailed_info() -> Dict
```

### EnhancedChordDetector

Advanced chord detection with fuzzy matching.

```python
class EnhancedChordDetector:
    """
    Enhanced chord detection with:
    - Fuzzy template matching
    - 50+ chord types
    - Voice-leading optimization
    - Harmonic context awareness
    """
    
    def note_on(note: int, velocity: int = 100, timestamp: float = None)
    def note_off(note: int)
    def get_current_chord() -> Optional[DetectedChord]
    def get_chord_history(count: int = 10) -> List[DetectedChord]
    def get_key_context() -> Optional[KeyContext]
    def force_chord(root: ChordRoot, chord_type: ChordType, bass_note: int = None)
    def reset()
    
    def get_status() -> Dict[str, Any]
```

### DetectedChord

Chord detection result.

```python
@dataclass
class DetectedChord:
    """Detected chord information."""
    
    root: ChordRoot
    chord_type: ChordType
    bass_note: Optional[int]
    inversion: int
    confidence: float
    notes: List[int]
    is_inversion: bool
    
    @property
    def chord_name -> str  # e.g., "Cmaj7", "Cm7/E"
    @property
    def root_midi -> int
    @property
    def intervals -> List[int]
    
    def get_notes_for_root(root_midi: int, octave: int = 3) -> List[int]
    def get_all_notes(min_note: int = 36, max_note: int = 84) -> List[int]
```

### ChordRoot

Musical root notes.

```python
class ChordRoot(Enum):
    C = 0
    C_SHARP = 1
    D = 2
    D_SHARP = 3
    E = 4
    F = 5
    F_SHARP = 6
    G = 7
    G_SHARP = 8
    A = 9
    A_SHARP = 10
    B = 11
    
    @classmethod
    def from_midi(note: int) -> ChordRoot
    @classmethod
    def from_name(name: str) -> ChordRoot
    
    @property
    def name_display -> str  # "C", "C#", etc.
```

### ChordType

Chord type classifications.

```python
class ChordType(Enum):
    MAJOR = auto()
    MINOR = auto()
    SEVENTH = auto()
    MAJOR_SEVENTH = auto()
    MINOR_SEVENTH = auto()
    DIMINISHED = auto()
    DIMINISHED_SEVENTH = auto()
    AUGMENTED = auto()
    SUSPENDED_SECOND = auto()
    SUSPENDED_FOURTH = auto()
    ADD_NINE = auto()
    SIXTH = auto()
    NINTH = auto()
    MAJOR_NINTH = auto()
    MINOR_NINTH = auto()
    ELEVENTH = auto()
    MAJOR_THIRTEENTH = auto()
    MINOR_THIRTEENTH = auto()
    HALF_DIMINISHED = auto()
    POWER = auto()
    
    @property
    def intervals -> List[int]  # Semitone intervals
    @property
    def name_display -> str  # "", "m", "7", "maj7", etc.
    
    @classmethod
    def from_intervals(intervals: List[int]) -> ChordType
    @classmethod
    def from_name(name: str) -> ChordType
```

## Scale Detection

### ScaleDetector

Musical scale/key detection.

```python
class ScaleDetector:
    """
    Real-time scale detection using Krumhansl-Schmiedler algorithm.
    
    Supports 15 scale types including modes, pentatonic, and blues.
    """
    
    def add_note(note: int, velocity: int = 100, timestamp: float = None)
    def remove_note(note: int)
    def add_chord(chord: DetectedChord)
    def get_current_scale() -> Optional[DetectedScale]
    def get_suggested_voicing(chord_root: int, chord_type: str) -> List[int]
    def is_chord_diatonic(chord_root: int, chord_type: str) -> bool
    def get_diatonic_chords() -> Dict[int, str]
    def reset()
    
    def get_status() -> Dict[str, Any]
```

### DetectedScale

Scale detection result.

```python
@dataclass
class DetectedScale:
    """Detected scale information."""
    
    root: int  # 0-11
    scale_type: ScaleType
    confidence: float
    chroma: np.ndarray
    fit_score: float
    notes_in_scale: List[int]
    
    @property
    def root_name -> str  # "C", "C#", etc.
    @property
    def full_name -> str  # "C Major (Ionian)"
    @property
    def is_major -> bool
    @property
    def is_minor -> bool
    
    def get_scale_notes(root_midi: int = 60, octaves: int = 2) -> List[int]
    def is_diatonic(note: int) -> bool
    def get_tension_level(note: int) -> str  # "chord_tone", "scale_tone", etc.
```

### ScaleType

Scale type classifications.

```python
class ScaleType(Enum):
    MAJOR = "major"
    NATURAL_MINOR = "natural_minor"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"
    BLUES_MAJOR = "blues_major"
    BLUES_MINOR = "blues_minor"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    WHOLE_TONE = "whole_tone"
    DIMINISHED = "diminished"
```

## MIDI Learn

### MIDILearn

MIDI controller learning system.

```python
class MIDILearn:
    """
    MIDI learn system with 30+ mappable targets.
    
    Features:
    - Real-time learn mode
    - Multiple response curves
    - Snap-to-grid
    - Momentary switches
    - Persistent storage
    """
    
    def start_learn(target_type: LearnTargetType, target_param: str = "", 
                    timeout: float = None)
    def cancel_learn()
    def process_midi(cc_number: int, channel: int, value: int) -> Optional[Dict]
    
    def add_mapping(mapping: MIDILearnMapping) -> bool
    def remove_mapping(cc_number: int, channel: int) -> bool
    def get_mapping(cc_number: int, channel: int) -> Optional[MIDILearnMapping]
    def get_all_mappings() -> List[MIDILearnMapping]
    def get_mappings_by_group(group: str) -> List[MIDILearnMapping]
    
    def register_callback(target_type: LearnTargetType, callback: Callable)
    def unregister_callback(target_type: LearnTargetType, callback: Callable) -> bool
    
    def load_default_mappings(controller_preset: str) -> bool
    def save_to_file(filepath: str) -> bool
    def load_from_file(filepath: str) -> bool
    
    def clear_all_mappings()
    
    def get_status() -> Dict[str, Any]
```

### MIDILearnMapping

Single MIDI mapping.

```python
class MIDILearnMapping:
    """
    MIDI mapping configuration.
    
    Args:
        cc_number: MIDI CC number (0-127)
        channel: MIDI channel (0-15)
        target_type: LearnTargetType
        target_param: Parameter name
        min_val: Minimum output value
        max_val: Maximum output value
        curve: Response curve ("linear", "exponential", etc.)
        momentary: Return to default on release
        snap_to_grid: Snap to increments (0 = disabled)
        inverted: Invert CC value
    """
    
    def process_value(raw_value: int) -> float
    
    def to_dict() -> Dict[str, Any]
    
    @classmethod
    def from_dict(data: Dict[str, Any]) -> MIDILearnMapping
```

### LearnTargetType

Mappable parameter types.

```python
class LearnTargetType(Enum):
    # Transport
    STYLE_START_STOP = "style_start_stop"
    STYLE_PLAY_PAUSE = "style_play_pause"
    
    # Sections
    STYLE_SECTION_NEXT = "style_section_next"
    STYLE_SECTION_A = "style_section_a"
    STYLE_SECTION_B = "style_section_b"
    STYLE_SECTION_C = "style_section_c"
    STYLE_SECTION_D = "style_section_d"
    
    # Fills
    STYLE_FILL = "style_fill"
    STYLE_BREAK = "style_break"
    STYLE_INTRO = "style_intro"
    STYLE_ENDING = "style_ending"
    
    # Continuous
    STYLE_TEMPO = "style_tempo"
    STYLE_DYNAMICS = "style_dynamics"
    STYLE_VOLUME = "style_volume"
    
    # OTS
    OTS_1 = "ots_1"
    OTS_2 = "ots_2"
    # ... OTS_3 through OTS_8
    OTS_NEXT = "ots_next"
    
    # Registration
    REGISTRATION_1 = "registration_1"
    # ... REGISTRATION_2 through REGISTRATION_4
    REGISTRATION_NEXT = "registration_next"
    
    # Effects
    EFFECT_REVERB = "effect_reverb"
    EFFECT_CHORUS = "effect_chorus"
    EFFECT_VARIATION = "effect_variation"
```

## Registration Memory

### RegistrationMemory

Complete registration memory system.

```python
class RegistrationMemory:
    """
    128 registration memories (8 banks × 16 slots).
    
    Features:
    - Freeze function
    - Copy/swap operations
    - File I/O
    - Callbacks
    """
    
    def __init__(num_banks: int = 8, slots_per_bank: int = 16)
    
    def set_synthesizer(synthesizer: Any)
    def set_style_player(style_player: Any)
    def set_ots(ots: Any)
    
    # Navigation
    def set_bank(bank_id: int) -> bool
    def next_bank()
    def previous_bank()
    def set_slot(slot: int) -> bool
    def next_slot()
    def previous_slot()
    
    # Recall/Store
    def recall(bank: int = None, slot: int = None, ignore_freeze: bool = False) -> bool
    def store(name: str = "", bank: int = None, slot: int = None, 
              capture_all: bool = True) -> bool
    
    # Operations
    def copy_slot(from_bank: int, from_slot: int, to_bank: int, to_slot: int) -> bool
    def swap_slots(bank1: int, slot1: int, bank2: int, slot2: int) -> bool
    def clear_slot(bank: int = None, slot: int = None) -> bool
    
    # Freeze
    def set_global_freeze(parameter: RegistrationParameter, frozen: bool)
    def get_global_freeze() -> Set[RegistrationParameter]
    def clear_global_freeze()
    
    # File I/O
    def save_to_file(filepath: str) -> bool
    @classmethod
    def load_from_file(filepath: str) -> Optional[RegistrationMemory]
    
    # Callbacks
    def set_recall_callback(callback: Callable[[Registration], None])
    def set_store_callback(callback: Callable[[int, int, Registration], None])
    def set_change_callback(callback: Callable[[], None])
    
    def get_status() -> Dict[str, Any]
```

### Registration

Single registration entry.

```python
@dataclass
class Registration:
    """Single registration memory."""
    
    slot_id: int
    name: str
    voice_parts: Dict[int, Dict[str, Any]]
    style_name: str
    style_tempo: int
    ots_preset: int
    transpose: int
    tune: int
    master_volume: int
    reverb_type: int
    chorus_type: int
    variation_type: int
    scale_type: str
    freeze_mask: Set[RegistrationParameter]
    created_at: float
    modified_at: float
    
    def set_freeze(parameter: RegistrationParameter, frozen: bool)
    def is_frozen(parameter: RegistrationParameter) -> bool
    
    def to_dict() -> Dict[str, Any]
    
    @classmethod
    def from_dict(data: Dict[str, Any]) -> Registration
```

## Groove

### GrooveQuantizer

Groove template processor.

```python
class GrooveQuantizer:
    """Apply groove templates to note timing."""
    
    def set_groove(groove_type: GrooveType) -> bool
    def set_groove_by_name(name: str) -> bool
    def set_intensity(intensity: float)
    
    def apply_timing_offset(tick_position: int, measure_position_16th: int) -> int
    def apply_velocity_offset(velocity: int, measure_position_16th: int) -> int
    
    def get_available_grooves() -> List[Dict[str, str]]
    def get_status() -> Dict
```

### GrooveType

Groove template types.

```python
class GrooveType(Enum):
    OFF = "off"
    SWING_1_3 = "swing_1_3"
    SWING_2_3 = "swing_2_3"
    SHUFFLE = "shuffle"
    FUNK = "funk"
    POP = "pop"
    LATIN = "latin"
    JAZZ = "jazz"
    BOSSA = "bossa"
    WALTZ = "waltz"
```

## Style Loader

### StyleLoader

YAML style file parser.

```python
class StyleLoader:
    """Load and parse YAML style files."""
    
    def __init__(validate: bool = True)
    
    def load_style_file(file_path: Union[str, Path]) -> Style
    def parse_style_data(data: Dict[str, Any]) -> Style
    def validate_style(style: Style) -> bool
    
    def create_minimal_style(name: str = "New Style", 
                            category: StyleCategory = StyleCategory.POP,
                            tempo: int = 120) -> Style
    def create_example_style(name: str = "Example Style",
                            category: StyleCategory = StyleCategory.POP,
                            tempo: int = 120) -> Style
    
    def save_style(style: Style, file_path: Union[str, Path])
    def get_available_styles(directory: Union[str, Path]) -> List[Dict[str, Any]]
```

## Enums Reference

### StyleSectionType

```python
class StyleSectionType(Enum):
    INTRO_1 = "intro_1"      # 1 bar
    INTRO_2 = "intro_2"      # 2 bars
    INTRO_3 = "intro_3"      # 4 bars
    MAIN_A = "main_a"
    MAIN_B = "main_b"
    MAIN_C = "main_c"
    MAIN_D = "main_d"
    FILL_IN_AA = "fill_in_aa"
    FILL_IN_AB = "fill_in_ab"
    # ... all fill combinations
    BREAK = "break"
    ENDING_1 = "ending_1"    # 1 bar
    ENDING_2 = "ending_2"    # 2 bars
    ENDING_3 = "ending_3"    # 4 bars
    
    @property
    def is_intro -> bool
    @property
    def is_main -> bool
    @property
    def is_fill -> bool
    @property
    def is_ending -> bool
    @property
    def length_bars -> int
```

### TrackType

```python
class TrackType(Enum):
    RHYTHM_1 = "rhythm_1"    # Channel 9 (drums)
    RHYTHM_2 = "rhythm_2"    # Channel 9 (drums)
    BASS = "bass"            # Channel 0
    CHORD_1 = "chord_1"      # Channel 1
    CHORD_2 = "chord_2"      # Channel 2
    PAD = "pad"              # Channel 3
    PHRASE_1 = "phrase_1"    # Channel 4
    PHRASE_2 = "phrase_2"    # Channel 5
    
    @property
    def default_midi_channel -> int
    @property
    def is_drum -> bool
    @property
    def is_chordal -> bool
```

### StyleCategory

```python
class StyleCategory(Enum):
    POP = "pop"
    ROCK = "rock"
    DANCE = "dance"
    JAZZ = "jazz"
    SWING = "swing"
    BALLAD = "ballad"
    BOSSANOVA = "bossa_nova"
    LATIN = "latin"
    COUNTRY = "country"
    RNB = "rnb"
    FUNK = "funk"
    ELECTRONIC = "electronic"
    CLASSICAL = "classical"
    # ... and more
```
