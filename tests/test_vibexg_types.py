"""Tests for vibexg types and utils."""
from __future__ import annotations

import pytest

from synth.io.midi import MIDIMessage


class TestInputInterfaceType:
    def test_enum_values(self) -> None:
        from vibexg.types import InputInterfaceType

        assert InputInterfaceType.MIDO_PORT is not None
        assert InputInterfaceType.VIRTUAL_PORT is not None
        assert InputInterfaceType.NETWORK_MIDI is not None
        assert InputInterfaceType.MIDI_FILE is not None
        assert InputInterfaceType.KEYBOARD is not None
        assert InputInterfaceType.STDIN is not None


class TestAudioOutputType:
    def test_enum_values(self) -> None:
        from vibexg.types import AudioOutputType

        assert AudioOutputType.SOUNDDEVICE is not None
        assert AudioOutputType.FILE is not None
        assert AudioOutputType.NONE is not None


class TestMIDIInputConfig:
    def test_create(self) -> None:
        from vibexg.types import InputInterfaceType, MIDIInputConfig

        config = MIDIInputConfig(
            interface_type=InputInterfaceType.MIDO_PORT, port_name="test"
        )
        assert config.interface_type == InputInterfaceType.MIDO_PORT
        assert config.port_name == "test"

    def test_defaults(self) -> None:
        from vibexg.types import InputInterfaceType, MIDIInputConfig

        config = MIDIInputConfig(interface_type=InputInterfaceType.KEYBOARD)
        assert config.enabled is True
        assert config.name == ""
        assert config.velocity_offset == 0
        assert config.transpose == 0


class TestAudioOutputConfig:
    def test_create(self) -> None:
        from vibexg.types import AudioOutputConfig, AudioOutputType

        config = AudioOutputConfig(
            output_type=AudioOutputType.SOUNDDEVICE, device_name="default"
        )
        assert config.output_type == AudioOutputType.SOUNDDEVICE
        assert config.device_name == "default"

    def test_defaults(self) -> None:
        from vibexg.types import AudioOutputConfig, AudioOutputType

        config = AudioOutputConfig(output_type=AudioOutputType.FILE)
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.file_format == "wav"


class TestPresetData:
    def test_create(self) -> None:
        from vibexg.types import PresetData

        preset = PresetData(name="test")
        assert preset.name == "test"
        assert preset.master_volume == 0.8
        assert preset.tempo == 120.0

    def test_defaults(self) -> None:
        from vibexg.types import PresetData

        preset = PresetData()
        assert preset.name == "Init"
        assert preset.programs == {}
        assert preset.volumes == {}
        assert preset.pans == {}


class TestWorkstationState:
    def test_create(self) -> None:
        from vibexg.types import WorkstationState

        state = WorkstationState()
        assert state is not None
        assert state.running is False
        assert state.recording is False
        assert state.tempo == 120.0
        assert state.master_volume == 0.8

    def test_adjust_voices_active(self) -> None:
        from vibexg.types import WorkstationState

        state = WorkstationState()
        assert state.voices_active == 0
        state.adjust_voices_active(3)
        assert state.voices_active == 3
        state.adjust_voices_active(-1)
        assert state.voices_active == 2
        # Should not go below zero
        state.adjust_voices_active(-10)
        assert state.voices_active == 0

    def test_increment_midi_activity(self) -> None:
        from vibexg.types import WorkstationState

        state = WorkstationState()
        state.increment_midi_activity(0)
        assert state.midi_activity[0] == 1
        state.increment_midi_activity(0)
        assert state.midi_activity[0] == 2


class TestVibexgUtils:
    def test_midimessage_to_bytes(self) -> None:
        from vibexg.utils import midimessage_to_bytes

        msg = MIDIMessage(
            type="note_on",
            channel=0,
            note=60,
            velocity=100,
        )
        result = midimessage_to_bytes(msg)
        assert result is not None
        assert result == bytes([0x90, 0x3C, 0x64])

    def test_bytes_to_midimessage(self) -> None:
        from vibexg.utils import bytes_to_midimessage

        result = bytes_to_midimessage(bytes([0x90, 0x3C, 0x64]))
        assert result is not None
        assert len(result) == 1
        assert result[0].type == "note_on"
        assert result[0].channel == 0
        assert result[0].note == 60
        assert result[0].velocity == 100
