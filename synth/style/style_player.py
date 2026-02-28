"""
Style Player - High-Level Style Playback Controller

Provides the high-level interface for style playback with
section management and transitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from collections.abc import Callable
import threading
import time

from .style import Style, StyleSectionType
from .auto_accompaniment import AutoAccompaniment, AccompanimentMode, StylePlaybackState
from .style_ots import OneTouchSettings
from .dynamics import StyleDynamics


class SectionTransitionType(Enum):
    """Types of section transitions"""

    IMMEDIATE = auto()
    FILL = auto()
    COUNT_IN = auto()
    INTRO = auto()
    ENDING = auto()


@dataclass(slots=True)
class SectionTransition:
    """Represents a section transition request"""

    from_section: StyleSectionType | None
    to_section: StyleSectionType
    transition_type: SectionTransitionType
    trigger_time: float = 0.0
    fill_section: StyleSectionType | None = None


class StylePlayer:
    """
    Professional high-level style player with advanced features.

    This is the main interface for working with styles, providing:
    - Start/stop/control of style playback
    - Section management and transitions
    - OTS integration
    - Style dynamics control
    - Integration with the synthesizer
    - Advanced features: chord memory, pattern variations, dynamic arrangement
    """

    def __init__(self, synthesizer: Any, sample_rate: int = 44100):
        self.synthesizer = synthesizer
        self.sample_rate = sample_rate

        self._lock = threading.RLock()

        self._style: Style | None = None
        self._accompaniment: AutoAccompaniment | None = None
        self._ots: OneTouchSettings | None = None
        self._dynamics: StyleDynamics | None = None

        self._playing = False
        self._current_section: StyleSectionType | None = None

        # Advanced style features
        self._chord_memory: list[Any] = []  # Chord progression memory
        self._pattern_variations: dict[int, list[int]] = {}  # Pattern variations per section
        self._dynamic_arrangement = True  # Dynamic arrangement enabled
        self._auto_fill = True  # Automatic fill patterns
        self._break_probability = 0.0  # Probability of breaks (0.0-1.0)
        
        # Callbacks
        self._on_section_change: Callable[[StyleSectionType, StyleSectionType], None] | None = None
        self._on_chord_change: Callable[[Any], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None

    @property
    def style(self) -> Style | None:
        return self._style

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def current_section(self) -> StyleSectionType | None:
        return self._current_section

    @property
    def tempo(self) -> float:
        if self._accompaniment:
            return self._accompaniment.tempo
        return 120.0

    @tempo.setter
    def tempo(self, value: float):
        if self._accompaniment:
            self._accompaniment.tempo = value

    def load_style(self, style: Style):
        """Load a style"""
        with self._lock:
            self._style = style

            self._accompaniment = AutoAccompaniment(
                style, self.synthesizer, sample_rate=self.sample_rate
            )
            self._accompaniment.set_note_callbacks(
                note_on=self._handle_note_on, note_off=self._handle_note_off
            )

            self._ots = OneTouchSettings()
            self._ots.set_synthesizer(self.synthesizer)

            self._dynamics = StyleDynamics()

            self._current_section = style.default_section

    def start(self, section: StyleSectionType | None = None):
        """Start style playback"""
        with self._lock:
            if not self._accompaniment or not self._style:
                return

            target = section or self._current_section

            self._accompaniment.start(target)
            self._playing = True
            self._current_section = target

            if self._on_state_change:
                self._on_state_change("playing")

    def stop(self, use_ending: bool = True):
        """Stop style playback"""
        with self._lock:
            if not self._accompaniment:
                return

            self._accompaniment.stop(ending=use_ending)
            self._playing = False

            if self._on_state_change:
                self._on_state_change("stopped")

    def pause(self):
        """Pause style playback"""
        with self._lock:
            if self._accompaniment:
                self._accompaniment.stop(ending=False)

    def resume(self):
        """Resume style playback"""
        with self._lock:
            if self._accompaniment and self._current_section:
                self._accompaniment.start(self._current_section)

    def set_section(self, section: StyleSectionType):
        """Change to a specific section"""
        with self._lock:
            if not self._accompaniment:
                return

            self._accompaniment.set_main_section(section.value)
            self._current_section = section

            if self._on_section_change:
                self._on_section_change(self._current_section, section)

    def next_section(self):
        """Advance to next main section (A→B→C→D→A)"""
        if not self._style or not self._current_section:
            return

        main_sections = [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]

        try:
            idx = main_sections.index(self._current_section)
            next_section = main_sections[(idx + 1) % len(main_sections)]
            self.set_section(next_section)
        except ValueError:
            self.set_section(StyleSectionType.MAIN_A)

    def trigger_fill(self):
        """Trigger fill before next section change"""
        if self._accompaniment:
            self._accompaniment.trigger_fill()

    def trigger_intro(self, length: int = 1):
        """Trigger intro section"""
        intro_map = {
            1: StyleSectionType.INTRO_1,
            2: StyleSectionType.INTRO_2,
            4: StyleSectionType.INTRO_3,
        }
        intro = intro_map.get(length, StyleSectionType.INTRO_1)
        self.set_section(intro)

    def trigger_ending(self, length: int = 1):
        """Trigger ending section"""
        ending_map = {
            1: StyleSectionType.ENDING_1,
            2: StyleSectionType.ENDING_2,
            4: StyleSectionType.ENDING_3,
        }
        ending = ending_map.get(length, StyleSectionType.ENDING_1)
        self.set_section(ending)
        self.stop(use_ending=True)

    def set_track_mute(self, track_type: str, muted: bool):
        """Mute/unmute a track"""
        if self._accompaniment:
            from .style import TrackType

            try:
                tt = TrackType(track_type)
                self._accompaniment.set_track_mute(tt, muted)
            except ValueError:
                pass

    def set_track_volume(self, track_type: str, volume: float):
        """Set track volume"""
        if self._accompaniment:
            from .style import TrackType

            try:
                tt = TrackType(track_type)
                self._accompaniment.set_track_volume(tt, volume)
            except ValueError:
                pass

    def set_ots_preset(self, preset_id: int):
        """Activate OTS preset"""
        if self._ots:
            self._ots.activate_preset(preset_id)

    def next_ots(self):
        """Activate next OTS preset"""
        if self._ots:
            self._ots.next_preset()

    def set_dynamics(self, value: int):
        """Set style dynamics (0-127)"""
        if self._dynamics:
            self._dynamics.set_dynamics(value)

    def adjust_dynamics(self, delta: int):
        """Adjust dynamics by delta"""
        if self._dynamics:
            self._dynamics.adjust(delta)

    def process_midi_note_on(self, channel: int, note: int, velocity: int):
        """Process incoming MIDI note-on"""
        if self._accompaniment:
            self._accompaniment.process_midi_note_on(channel, note, velocity)

    def process_midi_note_off(self, channel: int, note: int):
        """Process incoming MIDI note-off"""
        if self._accompaniment:
            self._accompaniment.process_midi_note_off(channel, note)

    def _handle_note_on(self, channel: int, note: int, velocity: int):
        """Handle note-on from accompaniment"""
        pass

    def _handle_note_off(self, channel: int, note: int):
        """Handle note-off from accompaniment"""
        pass

    def set_section_change_callback(
        self, callback: Callable[[StyleSectionType, StyleSectionType], None]
    ):
        """Set section change callback"""
        self._on_section_change = callback

    def set_chord_change_callback(self, callback: Callable[[Any], None]):
        """Set chord change callback"""
        self._on_chord_change = callback

    def set_state_change_callback(self, callback: Callable[[str], None]):
        """Set state change callback"""
        self._on_state_change = callback

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive player status with advanced features."""
        status = {
            "playing": self._playing,
            "style_loaded": self._style is not None,
            "style_name": self._style.name if self._style else None,
            "current_section": self._current_section.value
            if self._current_section
            else None,
            "tempo": self.tempo,
            # Advanced features status
            "dynamic_arrangement": self._dynamic_arrangement,
            "auto_fill": self._auto_fill,
            "chord_memory_size": len(self._chord_memory),
            "break_probability": self._break_probability,
        }

        if self._accompaniment:
            status.update(self._accompaniment.get_status())

        if self._ots:
            status["ots"] = self._ots.get_status()

        if self._dynamics:
            status["dynamics"] = self._dynamics.get_status()

        return status

    # ========== ADVANCED STYLE FEATURES ==========

    def set_chord_memory(self, chords: list[Any]):
        """Set chord progression memory for intelligent accompaniment."""
        with self._lock:
            self._chord_memory = chords.copy()
            
    def add_chord_to_memory(self, chord: Any):
        """Add chord to progression memory."""
        with self._lock:
            self._chord_memory.append(chord)
            
    def clear_chord_memory(self):
        """Clear chord progression memory."""
        with self._lock:
            self._chord_memory.clear()
            
    def get_chord_memory(self) -> list[Any]:
        """Get current chord progression memory."""
        with self._lock:
            return self._chord_memory.copy()
            
    def set_pattern_variation(self, section_type: StyleSectionType, variation_ids: list[int]):
        """Set pattern variations for a section."""
        with self._lock:
            self._pattern_variations[section_type.value] = variation_ids
            
    def get_pattern_variation(self, section_type: StyleSectionType) -> list[int]:
        """Get pattern variations for a section."""
        with self._lock:
            return self._pattern_variations.get(section_type.value, [])
            
    def enable_dynamic_arrangement(self, enabled: bool = True):
        """Enable/disable dynamic arrangement for intelligent accompaniment."""
        with self._lock:
            self._dynamic_arrangement = enabled
            
    def set_auto_fill(self, enabled: bool = True):
        """Enable/disable automatic fill patterns between sections."""
        with self._lock:
            self._auto_fill = enabled
            
    def set_break_probability(self, probability: float):
        """Set probability of breaks in accompaniment (0.0-1.0)."""
        with self._lock:
            self._break_probability = max(0.0, min(1.0, probability))
            
    def trigger_break(self):
        """Trigger an immediate break in the accompaniment."""
        with self._lock:
            if self._accompaniment:
                self._accompaniment.trigger_break()
                
    def get_chord_progression_analysis(self) -> dict[str, Any]:
        """Analyze current chord progression in memory."""
        with self._lock:
            if not self._chord_memory:
                return {"analysis": "No chord progression in memory"}
            
            # Simple analysis
            analysis = {
                "chord_count": len(self._chord_memory),
                "unique_chords": len(set(str(c) for c in self._chord_memory)),
                "progression": [str(c) for c in self._chord_memory],
            }
            return analysis

    def reset(self):
        """Reset player state"""
        if self._accompaniment:
            self._accompaniment.reset()
        self._playing = False

    def shutdown(self):
        """Shutdown player"""
        if self._accompaniment:
            self._accompaniment.shutdown()
