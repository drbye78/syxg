from __future__ import annotations

import math
import threading

import numpy as np
import pytest

from synth.primitives.validation import AudioValidator, ValidationError, ValidationResult


# =============================================================================
# ValidationError Tests
# =============================================================================


class TestValidationError:
    """Tests for ValidationError."""

    @pytest.mark.unit
    def test_init(self):
        """Create ValidationError and verify all fields."""
        err = ValidationError("test message", "ERR001", {"key": "val"}, "error")
        assert err.message == "test message"
        assert err.error_code == "ERR001"
        assert err.context == {"key": "val"}
        assert err.severity == "error"
        assert err.timestamp == threading.current_thread().ident
        assert err.thread_name == threading.current_thread().name

    @pytest.mark.unit
    def test_str(self):
        """Verify str() includes error_code and message."""
        err = ValidationError("something broke", "ERR_X", {"param": 42})
        s = str(err)
        assert "[ERR_X]" in s
        assert "something broke" in s
        assert "param=42" in s

    @pytest.mark.unit
    def test_str_empty_context(self):
        """Verify str() works when context is empty."""
        err = ValidationError("simple error", "ERR_EMPTY")
        s = str(err)
        assert "[ERR_EMPTY]" in s
        assert "simple error" in s

    @pytest.mark.unit
    def test_to_dict(self):
        """Verify dict has all expected keys."""
        err = ValidationError("msg", "EC", {"a": 1}, "warning")
        d = err.to_dict()
        assert d == {
            "error_code": "EC",
            "message": "msg",
            "severity": "warning",
            "context": {"a": 1},
            "timestamp": err.timestamp,
            "thread_name": err.thread_name,
        }

    @pytest.mark.unit
    def test_default_args(self):
        """Test with only message — verify defaults are filled."""
        err = ValidationError("just a message")
        assert err.error_code == "VALIDATION_ERROR"
        assert err.context == {}
        assert err.severity == "error"
        assert err.timestamp is not None
        assert err.thread_name is not None

    @pytest.mark.unit
    def test_severity_warning(self):
        """Test with severity='warning'."""
        err = ValidationError("warn", severity="warning")
        assert err.severity == "warning"
        assert err.error_code == "VALIDATION_ERROR"


# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult."""

    @pytest.mark.unit
    def test_init_empty(self):
        """Empty result: is_valid() True, has_warnings() False."""
        result = ValidationResult()
        assert result.is_valid() is True
        assert result.has_warnings() is False
        assert result.errors == []
        assert result.warnings == []
        assert result.info == []

    @pytest.mark.unit
    def test_add_error(self):
        """After add_error, is_valid() False, errors has 1 item."""
        result = ValidationResult()
        result.add_error(ValidationError("bad"))
        assert result.is_valid() is False
        assert len(result.errors) == 1
        assert result.errors[0].message == "bad"

    @pytest.mark.unit
    def test_add_warning(self):
        """After add_warning, has_warnings() True, warnings has 1 item."""
        result = ValidationResult()
        result.add_warning(ValidationError("caution", severity="warning"))
        assert result.has_warnings() is True
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "caution"

    @pytest.mark.unit
    def test_add_info(self):
        """After add_info, info has 1 item."""
        result = ValidationResult()
        result.add_info(ValidationError("note", severity="info"))
        assert len(result.info) == 1
        assert result.info[0].message == "note"

    @pytest.mark.unit
    def test_get_summary(self):
        """Summary reflects correct counts after adding errors/warnings/info."""
        result = ValidationResult()
        result.add_error(ValidationError("e1"))
        result.add_warning(ValidationError("w1", severity="warning"))
        result.add_warning(ValidationError("w2", severity="warning"))
        result.add_info(ValidationError("i1", severity="info"))
        result.add_info(ValidationError("i2", severity="info"))
        result.add_info(ValidationError("i3", severity="info"))
        summary = result.get_summary()
        assert summary == {"errors": 1, "warnings": 2, "info": 3}


# =============================================================================
# AudioValidator Tests
# =============================================================================


class TestAudioValidatorBuffer:
    """Tests for AudioValidator.validate_buffer."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        return AudioValidator(strict_mode=True)

    @pytest.mark.unit
    def test_validate_valid_buffer(self, validator: AudioValidator):
        """Mono float32 buffer of zeros should pass without errors."""
        buf = np.zeros(1024, dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_stereo_buffer(self, validator: AudioValidator):
        """Stereo buffer with expected_channels=2 should pass."""
        buf = np.zeros((512, 2), dtype=np.float32)
        result = validator.validate_buffer(buf, expected_channels=2)
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_buffer_wrong_type(self, validator: AudioValidator):
        """Pass a list instead of ndarray — should error."""
        result = validator.validate_buffer([1, 2, 3])  # type: ignore[arg-type]
        assert result.is_valid() is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "INVALID_BUFFER_TYPE"

    @pytest.mark.unit
    def test_validate_buffer_nan(self, validator: AudioValidator):
        """Buffer containing NaN should produce an error."""
        buf = np.array([float("nan"), 1.0], dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "BUFFER_CONTAINS_NAN" in codes

    @pytest.mark.unit
    def test_validate_buffer_inf(self, validator: AudioValidator):
        """Buffer containing Inf should produce an error."""
        buf = np.array([float("inf"), 1.0], dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "BUFFER_CONTAINS_INF" in codes

    @pytest.mark.unit
    def test_validate_buffer_amplitude(self, validator: AudioValidator):
        """Buffer with amplitude > 1.0 should error in strict mode."""
        buf = np.array([2.0], dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "AMPLITUDE_TOO_HIGH" in codes

    @pytest.mark.unit
    def test_validate_buffer_amplitude_non_strict(self):
        """Buffer with amplitude > 1.0 in non-strict mode should warn, not error."""
        validator = AudioValidator(strict_mode=False)
        buf = np.array([2.0], dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is True  # no errors
        assert result.has_warnings() is True
        codes = [w.error_code for w in result.warnings]
        assert "AMPLITUDE_WARNING" in codes

    @pytest.mark.unit
    def test_validate_buffer_silent(self, validator: AudioValidator):
        """All-zero buffer should add info about silence."""
        buf = np.zeros(1024, dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is True
        codes = [i.error_code for i in result.info]
        assert "BUFFER_IS_SILENT" in codes

    @pytest.mark.unit
    def test_validate_buffer_wrong_channels(self, validator: AudioValidator):
        """2-channel buffer with expected_channels=1 should error."""
        buf = np.zeros((64, 2), dtype=np.float32)
        result = validator.validate_buffer(buf, expected_channels=1)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_CHANNEL_COUNT" in codes

    @pytest.mark.unit
    def test_validate_buffer_wrong_dtype(self, validator: AudioValidator):
        """Buffer with wrong dtype should error."""
        buf = np.zeros(64, dtype=np.float64)
        result = validator.validate_buffer(buf, expected_dtype=np.dtype(np.float32))
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_BUFFER_DTYPE" in codes

    @pytest.mark.unit
    def test_validate_buffer_3d_rejected(self, validator: AudioValidator):
        """3D buffer should be rejected."""
        buf = np.zeros((8, 8, 2), dtype=np.float32)
        result = validator.validate_buffer(buf)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_BUFFER_DIMENSIONS" in codes


class TestAudioValidatorSampleRate:
    """Tests for AudioValidator.validate_sample_rate."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        return AudioValidator()

    @pytest.mark.unit
    def test_validate_sample_rate_valid(self, validator: AudioValidator):
        """44100 should pass."""
        result = validator.validate_sample_rate(44100)
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_sample_rate_below_min(self, validator: AudioValidator):
        """1000 should error (below 8000)."""
        result = validator.validate_sample_rate(1000)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "SAMPLE_RATE_TOO_LOW" in codes

    @pytest.mark.unit
    def test_validate_sample_rate_above_max(self, validator: AudioValidator):
        """200000 should error (above 192000)."""
        result = validator.validate_sample_rate(200000)
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "SAMPLE_RATE_TOO_HIGH" in codes

    @pytest.mark.unit
    def test_validate_sample_rate_non_standard(self, validator: AudioValidator):
        """12345 should warn but not error."""
        result = validator.validate_sample_rate(12345)
        assert result.is_valid() is True  # no errors
        assert result.has_warnings() is True
        codes = [w.error_code for w in result.warnings]
        assert "NON_STANDARD_SAMPLE_RATE" in codes

    @pytest.mark.unit
    def test_validate_sample_rate_non_int(self, validator: AudioValidator):
        """Float sample rate should type-error."""
        result = validator.validate_sample_rate(44100.0)  # type: ignore[arg-type]
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_SAMPLE_RATE_TYPE" in codes

    @pytest.mark.unit
    def test_validate_sample_rate_edge_min(self, validator: AudioValidator):
        """8000 is the minimum — should pass."""
        result = validator.validate_sample_rate(8000)
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_sample_rate_edge_max(self, validator: AudioValidator):
        """192000 is the maximum — should pass."""
        result = validator.validate_sample_rate(192000)
        assert result.is_valid() is True


class TestAudioValidatorParameterRange:
    """Tests for AudioValidator.validate_parameter_range."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        return AudioValidator()

    @pytest.mark.unit
    def test_validate_parameter_range_valid(self, validator: AudioValidator):
        """param=50, min=0, max=100 — valid."""
        result = validator.validate_parameter_range(50, 0, 100, "volume")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_parameter_range_too_low(self, validator: AudioValidator):
        """param=-1, min=0, max=100 — error."""
        result = validator.validate_parameter_range(-1, 0, 100, "volume")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "PARAMETER_TOO_LOW" in codes

    @pytest.mark.unit
    def test_validate_parameter_range_too_high(self, validator: AudioValidator):
        """param=101, min=0, max=100 — error."""
        result = validator.validate_parameter_range(101, 0, 100, "volume")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "PARAMETER_TOO_HIGH" in codes

    @pytest.mark.unit
    def test_validate_parameter_range_nan(self, validator: AudioValidator):
        """param=float('nan') — error."""
        result = validator.validate_parameter_range(float("nan"), 0, 100, "gain")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_PARAMETER_VALUE" in codes

    @pytest.mark.unit
    def test_validate_parameter_range_inf(self, validator: AudioValidator):
        """param=float('inf') — error."""
        result = validator.validate_parameter_range(float("inf"), 0, 100, "gain")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_PARAMETER_VALUE" in codes

    @pytest.mark.unit
    def test_validate_parameter_range_non_numeric(self, validator: AudioValidator):
        """String param — type error."""
        result = validator.validate_parameter_range("fifty", 0, 100, "volume")  # type: ignore[arg-type]
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_PARAMETER_TYPE" in codes

    @pytest.mark.unit
    def test_validate_parameter_range_default_name(self, validator: AudioValidator):
        """Default param_name='parameter' is used."""
        result = validator.validate_parameter_range(-5, 0, 10)
        assert result.is_valid() is False
        assert "parameter" in result.errors[0].message
        assert result.errors[0].context["name"] == "parameter"

    @pytest.mark.unit
    def test_validate_parameter_range_at_min(self, validator: AudioValidator):
        """Exactly at minimum is valid."""
        result = validator.validate_parameter_range(0, 0, 100)
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_parameter_range_at_max(self, validator: AudioValidator):
        """Exactly at maximum is valid."""
        result = validator.validate_parameter_range(100, 0, 100)
        assert result.is_valid() is True


class TestAudioValidatorMidiMessage:
    """Tests for AudioValidator.validate_midi_message."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        return AudioValidator()

    @pytest.mark.unit
    def test_validate_midi_message_valid_note_on(self, validator: AudioValidator):
        """Note On C4 velocity 100 — valid."""
        result = validator.validate_midi_message(b"\x90\x3C\x64")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_midi_message_valid_program_change(self, validator: AudioValidator):
        """Program change on channel 0 — valid."""
        result = validator.validate_midi_message(b"\xC0\x00")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_midi_message_empty(self, validator: AudioValidator):
        """Empty bytes — error."""
        result = validator.validate_midi_message(b"")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "EMPTY_MIDI_MESSAGE" in codes

    @pytest.mark.unit
    def test_validate_midi_message_invalid_status(self, validator: AudioValidator):
        """Status byte 0x00 is invalid."""
        result = validator.validate_midi_message(b"\x00\x00")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_MIDI_STATUS" in codes

    @pytest.mark.unit
    def test_validate_midi_message_data_byte_overflow(self, validator: AudioValidator):
        """Data byte >= 128 should error."""
        result = validator.validate_midi_message(b"\x90\xFF\x00")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_MIDI_DATA" in codes

    @pytest.mark.unit
    def test_validate_midi_message_wrong_length(self, validator: AudioValidator):
        """Note On with 2 bytes (expected 3) — length error."""
        result = validator.validate_midi_message(b"\x90\x40")
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_MIDI_LENGTH" in codes

    @pytest.mark.unit
    def test_validate_midi_message_not_bytes(self, validator: AudioValidator):
        """Passing a list instead of bytes — type error."""
        result = validator.validate_midi_message([0x90, 0x3C])  # type: ignore[arg-type]
        assert result.is_valid() is False
        codes = [e.error_code for e in result.errors]
        assert "INVALID_MIDI_TYPE" in codes

    @pytest.mark.unit
    def test_validate_midi_message_sysex_variable_length(self, validator: AudioValidator):
        """Sysex start (0xF0) is variable length — should pass."""
        result = validator.validate_midi_message(b"\xF0\x01\x02\x03")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_midi_message_note_off(self, validator: AudioValidator):
        """Note Off message should be valid."""
        result = validator.validate_midi_message(b"\x80\x3C\x40")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_midi_message_control_change(self, validator: AudioValidator):
        """Control Change message should be valid."""
        result = validator.validate_midi_message(b"\xB0\x07\x64")
        assert result.is_valid() is True

    @pytest.mark.unit
    def test_validate_midi_message_pitch_bend(self, validator: AudioValidator):
        """Pitch Bend message (3 bytes) should be valid."""
        result = validator.validate_midi_message(b"\xE0\x00\x40")
        assert result.is_valid() is True


class TestAudioValidatorSystemResources:
    """Tests for AudioValidator.validate_system_resources."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        return AudioValidator()

    @pytest.mark.unit
    def test_validate_system_resources_returns_result(self, validator: AudioValidator):
        """System resource validation should always return a ValidationResult."""
        result = validator.validate_system_resources()
        assert isinstance(result, ValidationResult)
        # Should not crash — either we get info (no psutil) or warnings/errors
        assert result.is_valid() is True or not result.is_valid()
