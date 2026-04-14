"""
Tests for vibexg.types module

Tests data classes, enums, and constants.
"""

from __future__ import annotations

from vibexg.types import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_SAMPLE_RATE,
    MIDI_CHANNELS,
    AudioOutputConfig,
    AudioOutputType,
    InputInterfaceType,
    MIDIInputConfig,
    PresetData,
    WorkstationState,
)


class TestConstants:
    """Test module constants."""

    def test_default_sample_rate(self):
        """Test default sample rate constant."""
        assert DEFAULT_SAMPLE_RATE == 44100

    def test_default_buffer_size(self):
        """Test default buffer size constant."""
        assert DEFAULT_BUFFER_SIZE == 512

    def test_midi_channels(self):
        """Test MIDI channels constant."""
        assert MIDI_CHANNELS == 16


class TestInputInterfaceType:
    """Test InputInterfaceType enum."""

    def test_mido_port(self):
        """Test MIDO_PORT enum value."""
        assert InputInterfaceType.MIDO_PORT.value == "mido_port"

    def test_keyboard(self):
        """Test KEYBOARD enum value."""
        assert InputInterfaceType.KEYBOARD.value == "keyboard"

    def test_midi_file(self):
        """Test MIDI_FILE enum value."""
        assert InputInterfaceType.MIDI_FILE.value == "midi_file"

    def test_all_values(self):
        """Test all enum values exist."""
        values = [e.value for e in InputInterfaceType]
        assert "mido_port" in values
        assert "keyboard" in values
        assert "midi_file" in values
        assert "stdin" in values


class TestAudioOutputType:
    """Test AudioOutputType enum."""

    def test_sounddevice(self):
        """Test SOUNDDEVICE enum value."""
        assert AudioOutputType.SOUNDDEVICE.value == "sounddevice"

    def test_file(self):
        """Test FILE enum value."""
        assert AudioOutputType.FILE.value == "file"

    def test_none(self):
        """Test NONE enum value."""
        assert AudioOutputType.NONE.value == "none"


class TestMIDIInputConfig:
    """Test MIDIInputConfig dataclass."""

    def test_default_values(self):
        """Test default field values."""
        config = MIDIInputConfig(interface_type=InputInterfaceType.KEYBOARD)
        assert config.name == ""
        assert config.port_name == ""
        assert config.enabled is True
        assert config.velocity_offset == 0
        assert config.transpose == 0
        assert config.options == {}

    def test_custom_values(self):
        """Test custom field values."""
        config = MIDIInputConfig(
            interface_type=InputInterfaceType.MIDO_PORT,
            name="Test Port",
            port_name="USB MIDI",
            velocity_offset=10,
            transpose=-2,
        )
        assert config.name == "Test Port"
        assert config.port_name == "USB MIDI"
        assert config.velocity_offset == 10
        assert config.transpose == -2

    def test_channel_filter(self):
        """Test channel filter list."""
        config = MIDIInputConfig(
            interface_type=InputInterfaceType.KEYBOARD,
            channel_filter=[0, 1, 2],
        )
        assert config.channel_filter == [0, 1, 2]


class TestAudioOutputConfig:
    """Test AudioOutputConfig dataclass."""

    def test_default_values(self):
        """Test default field values."""
        config = AudioOutputConfig(output_type=AudioOutputType.SOUNDDEVICE)
        assert config.device_name == ""
        assert config.file_path == ""
        assert config.file_format == "wav"
        assert config.sample_rate == DEFAULT_SAMPLE_RATE
        assert config.buffer_size == DEFAULT_BUFFER_SIZE
        assert config.channels == 2

    def test_file_output(self):
        """Test file output configuration."""
        config = AudioOutputConfig(
            output_type=AudioOutputType.FILE,
            file_path="output/test.wav",
            file_format="wav",
        )
        assert config.output_type == AudioOutputType.FILE
        assert config.file_path == "output/test.wav"

    def test_custom_sample_rate(self):
        """Test custom sample rate."""
        config = AudioOutputConfig(
            output_type=AudioOutputType.SOUNDDEVICE,
            sample_rate=48000,
        )
        assert config.sample_rate == 48000


class TestPresetData:
    """Test PresetData dataclass."""

    def test_default_values(self):
        """Test default field values."""
        preset = PresetData()
        assert preset.name == "Init"
        assert preset.master_volume == 0.8
        assert preset.tempo == 120.0
        assert preset.programs == {}
        assert preset.midi_learn_mappings == []

    def test_custom_preset(self):
        """Test custom preset values."""
        preset = PresetData(
            name="My Preset",
            master_volume=0.75,
            tempo=110.0,
            programs={0: 1, 1: 5},
        )
        assert preset.name == "My Preset"
        assert preset.master_volume == 0.75
        assert preset.tempo == 110.0
        assert preset.programs[0] == 1
        assert preset.programs[1] == 5

    def test_timestamps(self):
        """Test timestamp fields are set."""
        preset = PresetData()
        assert preset.created_at > 0
        assert preset.modified_at > 0


class TestWorkstationState:
    """Test WorkstationState dataclass."""

    def test_default_values(self):
        """Test default field values."""
        state = WorkstationState()
        assert state.running is False
        assert state.recording is False
        assert state.playing is False
        assert state.tempo == 120.0
        assert state.master_volume == 0.8
        assert state.current_preset == "Init"
        assert state.voices_active == 0

    def test_midi_activity(self):
        """Test MIDI activity dictionary."""
        state = WorkstationState()
        assert len(state.midi_activity) == 16
        assert all(v == 0 for v in state.midi_activity.values())

    def test_update_state(self):
        """Test updating state fields."""
        state = WorkstationState()
        state.running = True
        state.recording = True
        state.tempo = 130.0
        state.voices_active = 10

        assert state.running is True
        assert state.recording is True
        assert state.tempo == 130.0
        assert state.voices_active == 10
