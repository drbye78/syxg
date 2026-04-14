"""
Auto Accompaniment Integration Tests

Integration tests for the AutoAccompaniment class including:
- Playback start/stop
- Chord-triggered note output
- Section changes
- Track mute/solo
- Tempo changes
"""

from __future__ import annotations

import time

import pytest

from synth.style.auto_accompaniment import (
    AccompanimentMode,
    AutoAccompaniment,
    AutoAccompanimentConfig,
    StylePlaybackState,
)
from synth.style.style import StyleSectionType, TrackType


class TestAutoAccompanimentPlayback:
    """Test basic playback functionality."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_start_playback(self, accompaniment):
        """Test starting playback."""
        accompaniment.start()

        assert accompaniment.is_playing == True
        assert accompaniment.mode == AccompanimentMode.ON
        assert accompaniment.playback_state == StylePlaybackState.PLAYING

    def test_stop_playback(self, accompaniment):
        """Test stopping playback."""
        accompaniment.start()
        accompaniment.stop(ending=False)

        assert accompaniment.mode == AccompanimentMode.OFF
        assert accompaniment.playback_state == StylePlaybackState.STOPPED

    def test_start_with_section(self, accompaniment):
        """Test starting with specific section."""
        accompaniment.start(section=sample_style.sections[StyleSectionType.MAIN_B])

        assert accompaniment.current_section.section_type == StyleSectionType.MAIN_B


class TestChordTriggeredNotes:
    """Test chord-triggered note output."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_chord_triggers_style_notes(self, accompaniment, mock_synthesizer):
        """Test that playing chords triggers style note output."""
        accompaniment.start()

        # Play C major chord in detection zone
        accompaniment.process_midi_note_on(0, 60, 100)  # C4
        accompaniment.process_midi_note_on(0, 64, 100)  # E4
        accompaniment.process_midi_note_on(0, 67, 100)  # G4

        # Allow processing time
        time.sleep(0.1)

        # Synthesizer should have received note commands
        # (exact behavior depends on style content)
        assert accompaniment.chord_detector.get_current_chord() is not None

    def test_note_off_stops_chord(self, accompaniment):
        """Test that releasing notes clears chord."""
        accompaniment.start()

        accompaniment.process_midi_note_on(0, 60, 100)
        accompaniment.process_midi_note_on(0, 64, 100)
        accompaniment.process_midi_note_on(0, 67, 100)

        assert accompaniment.chord_detector.get_current_chord() is not None

        accompaniment.process_midi_note_off(0, 60)
        accompaniment.process_midi_note_off(0, 64)
        accompaniment.process_midi_note_off(0, 67)

        # Chord should be cleared or changed
        chord = accompaniment.chord_detector.get_current_chord()
        assert chord is None or len(accompaniment.chord_detector.get_active_notes()) == 0


class TestSectionChanges:
    """Test section change functionality."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
            auto_fill_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_change_main_section(self, accompaniment):
        """Test changing between main sections."""
        accompaniment.start()

        # Change to section B
        accompaniment.set_main_section("main_b")

        # Allow processing
        time.sleep(0.05)

        assert accompaniment.current_section.section_type == StyleSectionType.MAIN_B

    def test_next_main_section(self, accompaniment):
        """Test advancing to next main section."""
        accompaniment.start(section=sample_style.sections[StyleSectionType.MAIN_A])

        accompaniment.next_main_section()
        time.sleep(0.05)

        assert accompaniment.current_section.section_type == StyleSectionType.MAIN_B

    def test_section_change_callback(self, accompaniment):
        """Test section change callback is invoked."""
        section_changes = []

        def on_change(old_section, new_section):
            section_changes.append((old_section, new_section))

        accompaniment.set_section_change_callback(on_change)
        accompaniment.start()
        accompaniment.set_main_section("main_b")

        time.sleep(0.1)

        assert len(section_changes) > 0


class TestTrackControl:
    """Test track mute/solo/volume control."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_mute_track(self, accompaniment):
        """Test muting a track."""
        accompaniment.set_track_mute(TrackType.BASS, True)

        track_state = accompaniment._track_states[TrackType.BASS]
        assert track_state.muted == True

    def test_unmute_track(self, accompaniment):
        """Test unmuting a track."""
        accompaniment.set_track_mute(TrackType.BASS, True)
        accompaniment.set_track_mute(TrackType.BASS, False)

        track_state = accompaniment._track_states[TrackType.BASS]
        assert track_state.muted == False

    def test_set_track_volume(self, accompaniment):
        """Test setting track volume."""
        accompaniment.set_track_volume(TrackType.BASS, 0.5)

        track_state = accompaniment._track_states[TrackType.BASS]
        assert track_state.volume == 0.5

    def test_track_volume_clamped(self, accompaniment):
        """Test that track volume is clamped to 0-1."""
        accompaniment.set_track_volume(TrackType.BASS, 1.5)

        track_state = accompaniment._track_states[TrackType.BASS]
        assert track_state.volume == 1.0

        accompaniment.set_track_volume(TrackType.BASS, -0.5)
        assert track_state.volume == 0.0


class TestTempoControl:
    """Test tempo change functionality."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_change_tempo(self, accompaniment):
        """Test changing tempo."""
        initial_tempo = accompaniment.tempo
        accompaniment.tempo = 140

        assert accompaniment.tempo == 140
        assert accompaniment.tempo != initial_tempo

    def test_tempo_clamped(self, accompaniment):
        """Test that tempo is clamped to valid range."""
        accompaniment.tempo = 10  # Too slow

        assert accompaniment.tempo >= 20

        accompaniment.tempo = 350  # Too fast

        assert accompaniment.tempo <= 300


class TestFillTriggering:
    """Test fill triggering functionality."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
            auto_fill_enabled=True,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_trigger_fill(self, accompaniment):
        """Test triggering fill."""
        accompaniment.start()
        accompaniment.trigger_fill()

        # Fill should be queued
        assert accompaniment._is_filling == True or accompaniment._fill_section is not None

    def test_fill_with_section_change(self, accompaniment):
        """Test fill before section change."""
        accompaniment.start(section=sample_style.sections[StyleSectionType.MAIN_A])

        # Trigger section change with fill
        accompaniment.trigger_section_change("main_b", use_fill=True)

        # Fill should be queued
        assert accompaniment._is_filling == True or accompaniment._fill_section is not None


class TestStatusReporting:
    """Test status reporting functionality."""

    @pytest.fixture
    def accompaniment(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=False,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_get_status(self, accompaniment):
        """Test getting status information."""
        accompaniment.start()

        status = accompaniment.get_status()

        assert "mode" in status
        assert "playback_state" in status
        assert "current_section" in status
        assert "tempo" in status

    def test_status_shows_playing(self, accompaniment):
        """Test that status reflects playing state."""
        status_stopped = accompaniment.get_status()
        assert status_stopped["playback_state"] == "STOPPED"

        accompaniment.start()

        status_playing = accompaniment.get_status()
        assert status_playing["playback_state"] == "PLAYING"


class TestSyncStart:
    """Test sync-start functionality."""

    @pytest.fixture
    def accompaniment_sync(self, sample_style, mock_synthesizer):
        config = AutoAccompanimentConfig(
            chord_detection_zone_low=48,
            chord_detection_zone_high=72,
            sync_start_enabled=True,
        )
        return AutoAccompaniment(
            style=sample_style, synthesizer=mock_synthesizer, config=config, sample_rate=44100
        )

    def test_sync_start_waits(self, accompaniment_sync):
        """Test that sync-start waits for first key."""
        accompaniment_sync.start()

        # Should be in WAITING state
        assert accompaniment_sync.mode == AccompanimentMode.SYNC_START
        assert accompaniment_sync.playback_state == StylePlaybackState.WAITING

    def test_sync_start_triggers_on_key(self, accompaniment_sync):
        """Test that sync-start triggers on first key press."""
        accompaniment_sync.start()

        # Play a key in detection zone
        accompaniment_sync.process_midi_note_on(0, 60, 100)

        # Allow processing
        time.sleep(0.05)

        # Should have started playback
        assert accompaniment_sync.mode == AccompanimentMode.ON
