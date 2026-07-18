"""
Style Dynamics & Groove Unit Tests

Comprehensive tests for:
- synth.style.dynamics (DynamicsParameter, DynamicsCurve, StyleDynamics)
- synth.style.groove (GrooveType, GrooveTemplate, GROOVE_TEMPLATES, GrooveQuantizer)
"""

from __future__ import annotations

import pytest

from synth.style.dynamics import (
    DynamicsCurve,
    DynamicsParameter,
    StyleDynamics,
)
from synth.style.groove import (
    GROOVE_TEMPLATES,
    GrooveQuantizer,
    GrooveTemplate,
    GrooveType,
    get_default_groove_quantizer,
)

# =============================================================================
# DynamicsParameter Enum
# =============================================================================


class TestDynamicsParameter:
    """Test DynamicsParameter enum values and properties."""

    def test_enum_values(self):
        """Verify all enum members have expected string values."""
        assert DynamicsParameter.VELOCITY.value == "velocity"
        assert DynamicsParameter.VOLUME.value == "volume"
        assert DynamicsParameter.FILTER_CUTOFF.value == "filter_cutoff"
        assert DynamicsParameter.FILTER_RESONANCE.value == "filter_resonance"
        assert DynamicsParameter.REVERB_MIX.value == "reverb_mix"
        assert DynamicsParameter.CHORUS_MIX.value == "chorus_mix"
        assert DynamicsParameter.TEMPO.value == "tempo"
        assert DynamicsParameter.INTRO_LENGTH.value == "intro_length"
        assert DynamicsParameter.ENDING_LENGTH.value == "ending_length"

    def test_enum_members_count(self):
        """Verify expected number of enum members."""
        assert len(DynamicsParameter) == 9

    def test_enum_from_name_roundtrip(self):
        """Verify name-based lookup works."""
        assert DynamicsParameter["VELOCITY"] == DynamicsParameter.VELOCITY
        assert DynamicsParameter["VOLUME"] == DynamicsParameter.VOLUME
        assert DynamicsParameter["FILTER_CUTOFF"] == DynamicsParameter.FILTER_CUTOFF
        assert DynamicsParameter["CHORUS_MIX"] == DynamicsParameter.CHORUS_MIX


# =============================================================================
# DynamicsCurve
# =============================================================================


class TestDynamicsCurve:
    """Test DynamicsCurve dataclass and apply method."""

    @pytest.fixture
    def linear_curve(self) -> DynamicsCurve:
        return DynamicsCurve(DynamicsParameter.VOLUME, 0.0, 1.0, "linear")

    @pytest.fixture
    def exponential_curve(self) -> DynamicsCurve:
        return DynamicsCurve(DynamicsParameter.VOLUME, 0.0, 1.0, "exponential")

    @pytest.fixture
    def logarithmic_curve(self) -> DynamicsCurve:
        return DynamicsCurve(DynamicsParameter.VOLUME, 0.0, 1.0, "logarithmic")

    @pytest.fixture
    def s_curve(self) -> DynamicsCurve:
        return DynamicsCurve(DynamicsParameter.VOLUME, 0.0, 1.0, "s_curve")

    def test_init(self):
        """Test basic initialization."""
        curve = DynamicsCurve(DynamicsParameter.VELOCITY, 0.5, 1.0, "linear")
        assert curve.parameter == DynamicsParameter.VELOCITY
        assert curve.min_value == 0.5
        assert curve.max_value == 1.0
        assert curve.curve == "linear"

    def test_init_defaults(self):
        """Test default values."""
        curve = DynamicsCurve(DynamicsParameter.VELOCITY)
        assert curve.min_value == 0.0
        assert curve.max_value == 1.0
        assert curve.curve == "linear"

    def test_apply_linear_midpoint(self, linear_curve):
        """Linear curve at midpoint (64/127 ≈ 0.504)."""
        result = linear_curve.apply(64)
        # normalized = 64/127 ≈ 0.5039, min=0, max=1
        assert result == pytest.approx(64 / 127.0)

    def test_apply_linear_min(self, linear_curve):
        """Linear curve at minimum (0)."""
        result = linear_curve.apply(0)
        assert result == 0.0

    def test_apply_linear_max(self, linear_curve):
        """Linear curve at maximum (127)."""
        result = linear_curve.apply(127)
        assert result == 1.0

    def test_apply_linear_scaled(self):
        """Linear curve with non-unit range."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 0.3, 1.0, "linear")
        result = curve.apply(64)
        expected = 0.3 + (1.0 - 0.3) * (64 / 127.0)
        assert result == pytest.approx(expected)

    def test_apply_exponential(self, exponential_curve):
        """Exponential curve (squared normalized)."""
        result_min = exponential_curve.apply(0)
        assert result_min == 0.0

        result_max = exponential_curve.apply(127)
        assert result_max == 1.0

        result_mid = exponential_curve.apply(64)
        normalized = 64 / 127.0
        assert result_mid == pytest.approx(normalized**2)

    def test_apply_logarithmic(self, logarithmic_curve):
        """Logarithmic curve (sqrt normalized)."""
        result_min = logarithmic_curve.apply(0)
        assert result_min == 0.0

        result_max = logarithmic_curve.apply(127)
        assert result_max == 1.0

        result_mid = logarithmic_curve.apply(64)
        normalized = 64 / 127.0
        assert result_mid == pytest.approx(normalized**0.5)

    def test_apply_logarithmic_zero_normalized(self):
        """Logarithmic at zero should not divide by zero."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 0.1, 1.0, "logarithmic")
        result = curve.apply(0)
        assert result == 0.1  # min_value returned for normalized == 0

    def test_apply_s_curve(self, s_curve):
        """S-curve (smoothstep)."""
        normalized = 64 / 127.0
        expected = normalized * normalized * (3 - 2 * normalized)

        result_min = s_curve.apply(0)
        assert result_min == 0.0

        result_max = s_curve.apply(127)
        assert result_max == 1.0

        result_mid = s_curve.apply(64)
        assert result_mid == pytest.approx(expected)

    def test_apply_unknown_curve_falls_back_to_linear(self):
        """Unknown curve type falls back to linear."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 0.2, 0.8, "zigzag")
        expected = 0.2 + (0.8 - 0.2) * (64 / 127.0)
        assert curve.apply(64) == pytest.approx(expected)

    def test_apply_min_greater_than_max(self):
        """Handle reversed range (min > max) gracefully."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 1.0, 0.0, "linear")
        result = curve.apply(64)
        expected = 1.0 + (0.0 - 1.0) * (64 / 127.0)
        assert result == pytest.approx(expected)

    def test_slots(self):
        """DynamicsCurve uses __slots__ via dataclass(slots=True)."""
        curve = DynamicsCurve(DynamicsParameter.VELOCITY)
        with pytest.raises(AttributeError):
            curve.new_attr = "should_fail"


# =============================================================================
# StyleDynamics
# =============================================================================


class TestStyleDynamics:
    """Test StyleDynamics main functionality."""

    @pytest.fixture
    def dynamics(self) -> StyleDynamics:
        return StyleDynamics()

    def test_init_default_value(self, dynamics):
        """Default dynamics value should be 64."""
        assert dynamics.dynamics_value == 64

    def test_set_dynamics(self, dynamics):
        """Set to explicit value."""
        dynamics.set_dynamics(100)
        assert dynamics.dynamics_value == 100

    def test_set_dynamics_clamps_low(self, dynamics):
        """Values below 0 are clamped to 0."""
        dynamics.set_dynamics(-10)
        assert dynamics.dynamics_value == 0

    def test_set_dynamics_clamps_high(self, dynamics):
        """Values above 127 are clamped to 127."""
        dynamics.set_dynamics(200)
        assert dynamics.dynamics_value == 127

    def test_adjust_positive(self, dynamics):
        """Positive delta increases value."""
        dynamics.set_dynamics(50)
        dynamics.adjust(10)
        assert dynamics.dynamics_value == 60

    def test_adjust_negative(self, dynamics):
        """Negative delta decreases value."""
        dynamics.set_dynamics(50)
        dynamics.adjust(-10)
        assert dynamics.dynamics_value == 40

    def test_adjust_clamps(self, dynamics):
        """Adjust clamps to valid range."""
        dynamics.adjust(-200)
        assert dynamics.dynamics_value == 0

        dynamics.adjust(500)
        assert dynamics.dynamics_value == 127

    def test_increment(self, dynamics):
        """Increment increases by 1."""
        dynamics.set_dynamics(50)
        dynamics.increment()
        assert dynamics.dynamics_value == 51

    def test_increment_at_max(self, dynamics):
        """Increment at max stays at 127."""
        dynamics.set_dynamics(127)
        dynamics.increment()
        assert dynamics.dynamics_value == 127

    def test_decrement(self, dynamics):
        """Decrement decreases by 1."""
        dynamics.set_dynamics(50)
        dynamics.decrement()
        assert dynamics.dynamics_value == 49

    def test_decrement_at_min(self, dynamics):
        """Decrement at min stays at 0."""
        dynamics.set_dynamics(0)
        dynamics.decrement()
        assert dynamics.dynamics_value == 0

    def test_reset(self, dynamics):
        """Reset restores value to 64."""
        dynamics.set_dynamics(127)
        dynamics.reset()
        assert dynamics.dynamics_value == 64

    # --- Curves ---

    def test_set_curve_updates_existing(self, dynamics):
        """set_curve updates existing curve's type and values."""
        dynamics.set_curve(
            DynamicsParameter.VELOCITY,
            curve="exponential",
            min_value=0.2,
            max_value=0.9,
        )
        params = dynamics.get_all_parameters()
        assert DynamicsParameter.VELOCITY in params

    def test_set_curve_partial_update(self, dynamics):
        """Partial update preserves existing min/max."""
        dynamics.set_curve(
            DynamicsParameter.VELOCITY,
            curve="exponential",
        )
        velocity_val = dynamics.get_parameter(DynamicsParameter.VELOCITY)
        # Should use existing min=0.5, max=1.0 with exponential curve
        assert velocity_val > 0.5

    def test_set_curve_new_parameter(self, dynamics):
        """set_curve with unknown parameter creates new curve with provided range."""
        dynamics.set_curve(
            DynamicsParameter.INTRO_LENGTH,
            curve="linear",
            min_value=0.0,
            max_value=4.0,
        )
        val = dynamics.get_parameter(DynamicsParameter.INTRO_LENGTH)
        expected = 0.0 + (4.0 - 0.0) * (64 / 127.0)
        assert val == pytest.approx(expected)

    def test_get_parameter(self, dynamics):
        """get_parameter returns computed value for a parameter."""
        val = dynamics.get_parameter(DynamicsParameter.VOLUME)
        expected = 0.3 + (1.0 - 0.3) * (64 / 127.0)
        assert val == pytest.approx(expected)

    def test_get_parameter_unknown_returns_default(self, dynamics):
        """get_parameter for unregistered param returns 0.5."""
        # Clean out defaults by setting dynamics to a new one with empty curves
        # Actually let's test directly: INTRO_LENGTH is not in default curves
        val = dynamics.get_parameter(DynamicsParameter.INTRO_LENGTH)
        assert val == 0.5

    def test_get_all_parameters(self, dynamics):
        """get_all_parameters returns all registered parameters."""
        params = dynamics.get_all_parameters()
        assert DynamicsParameter.VELOCITY in params
        assert DynamicsParameter.VOLUME in params
        assert DynamicsParameter.FILTER_CUTOFF in params
        assert DynamicsParameter.FILTER_RESONANCE in params
        assert DynamicsParameter.REVERB_MIX in params
        assert DynamicsParameter.CHORUS_MIX in params
        assert DynamicsParameter.TEMPO in params
        # INTRO_LENGTH and ENDING_LENGTH are not in default curves
        assert DynamicsParameter.INTRO_LENGTH not in params
        assert DynamicsParameter.ENDING_LENGTH not in params
        assert len(params) == 7

    # --- Convenience getters ---

    def test_get_velocity_scale(self, dynamics):
        """get_velocity_scale returns velocity parameter value."""
        expected = dynamics.get_parameter(DynamicsParameter.VELOCITY)
        assert dynamics.get_velocity_scale() == expected

    def test_get_volume_scale(self, dynamics):
        """get_volume_scale returns volume parameter value."""
        expected = dynamics.get_parameter(DynamicsParameter.VOLUME)
        assert dynamics.get_volume_scale() == expected

    def test_get_filter_cutoff(self, dynamics):
        """get_filter_cutoff returns filter cutoff value."""
        expected = dynamics.get_parameter(DynamicsParameter.FILTER_CUTOFF)
        assert dynamics.get_filter_cutoff() == expected

    def test_get_reverb_mix(self, dynamics):
        """get_reverb_mix returns reverb mix value."""
        expected = dynamics.get_parameter(DynamicsParameter.REVERB_MIX)
        assert dynamics.get_reverb_mix() == expected

    def test_get_chorus_mix(self, dynamics):
        """get_chorus_mix returns chorus mix value."""
        expected = dynamics.get_parameter(DynamicsParameter.CHORUS_MIX)
        assert dynamics.get_chorus_mix() == expected

    def test_get_tempo_scale(self, dynamics):
        """get_tempo_scale returns tempo scaling factor."""
        expected = dynamics.get_parameter(DynamicsParameter.TEMPO)
        assert dynamics.get_tempo_scale() == expected

    # --- Callbacks ---

    def test_add_callback_is_called(self, dynamics):
        """Callback fires on set_dynamics."""
        results = []

        def callback(value, params):
            results.append((value, params))

        dynamics.add_callback(callback)
        dynamics.set_dynamics(100)

        assert len(results) == 1
        assert results[0][0] == 100
        assert isinstance(results[0][1], dict)

    def test_add_callback_not_duplicated(self, dynamics):
        """Adding same callback twice only registers once."""
        count = 0

        def callback(value, params):
            nonlocal count
            count += 1

        dynamics.add_callback(callback)
        dynamics.add_callback(callback)
        dynamics.set_dynamics(50)

        assert count == 1

    def test_remove_callback(self, dynamics):
        """Removed callback no longer fires."""
        results = []

        def callback(value, params):
            results.append(value)

        dynamics.add_callback(callback)
        dynamics.remove_callback(callback)
        dynamics.set_dynamics(100)

        assert len(results) == 0

    def test_remove_nonexistent_callback(self, dynamics):
        """Removing an unregistered callback does not raise."""

        def some_callback(value, params):
            pass

        # Should not raise
        dynamics.remove_callback(some_callback)

    def test_callbacks_on_adjust(self, dynamics):
        """Callbacks fire on adjust."""
        results = []

        def callback(value, params):
            results.append(value)

        dynamics.add_callback(callback)
        dynamics.set_dynamics(50)
        dynamics.adjust(10)

        assert len(results) == 2
        assert results[1] == 60

    def test_callbacks_on_reset(self, dynamics):
        """Callbacks fire on reset."""
        results = []

        def callback(value, params):
            results.append(value)

        dynamics.add_callback(callback)
        dynamics.reset()

        assert len(results) >= 1
        assert results[-1] == 64

    # --- to_dict / from_dict ---

    def test_to_dict(self, dynamics):
        """to_dict exports expected keys."""
        dynamics.set_dynamics(80)
        data = dynamics.to_dict()

        assert data["dynamics_value"] == 80
        assert "curves" in data
        assert DynamicsParameter.VELOCITY.name in data["curves"]
        assert DynamicsParameter.VOLUME.name in data["curves"]

        vel_curve = data["curves"][DynamicsParameter.VELOCITY.name]
        assert vel_curve["curve"] == "linear"
        assert vel_curve["min_value"] == 0.5
        assert vel_curve["max_value"] == 1.0

    def test_from_dict_roundtrip(self, dynamics):
        """to_dict -> from_dict roundtrip preserves state."""
        dynamics.set_dynamics(90)
        dynamics.set_curve(
            DynamicsParameter.VOLUME,
            curve="exponential",
            min_value=0.1,
            max_value=0.9,
        )

        data = dynamics.to_dict()
        restored = StyleDynamics.from_dict(data)

        assert restored.dynamics_value == 90
        original_params = dynamics.get_all_parameters()
        restored_params = restored.get_all_parameters()
        for param in original_params:
            assert restored_params[param] == pytest.approx(original_params[param])

    def test_from_dict_defaults(self):
        """from_dict with empty data uses defaults."""
        restored = StyleDynamics.from_dict({})
        assert restored.dynamics_value == 64

    def test_from_dict_dynamics_value(self):
        """from_dict reads dynamics_value."""
        restored = StyleDynamics.from_dict({"dynamics_value": 127})
        assert restored.dynamics_value == 127

    def test_from_dict_invalid_parameter_skipped(self):
        """from_dict skips unknown curve parameters gracefully."""
        data = {
            "dynamics_value": 64,
            "curves": {
                "NONEXISTENT_PARAM": {"curve": "linear", "min_value": 0.0, "max_value": 1.0},
            },
        }
        restored = StyleDynamics.from_dict(data)
        # Should not raise, should use defaults
        assert restored.dynamics_value == 64

    # --- Status ---

    def test_get_status(self, dynamics):
        """get_status returns expected keys and types."""
        dynamics.set_dynamics(80)
        status = dynamics.get_status()

        assert status["dynamics_value"] == 80
        assert "parameters" in status
        assert DynamicsParameter.VELOCITY.name in status["parameters"]
        assert isinstance(status["parameters"], dict)


# =============================================================================
# GrooveType Enum
# =============================================================================


class TestGrooveType:
    """Test GrooveType enum values and properties."""

    def test_enum_values(self):
        """Verify all enum members have expected string values."""
        assert GrooveType.OFF.value == "off"
        assert GrooveType.SWING_1_3.value == "swing_1_3"
        assert GrooveType.SWING_2_3.value == "swing_2_3"
        assert GrooveType.SHUFFLE.value == "shuffle"
        assert GrooveType.FUNK.value == "funk"
        assert GrooveType.POP.value == "pop"
        assert GrooveType.LATIN.value == "latin"
        assert GrooveType.JAZZ.value == "jazz"
        assert GrooveType.BOSSA.value == "bossa"
        assert GrooveType.WALTZ.value == "waltz"
        assert GrooveType.CUSTOM.value == "custom"

    def test_enum_members_count(self):
        """Verify expected number of enum members."""
        assert len(GrooveType) == 11


# =============================================================================
# GrooveTemplate
# =============================================================================


class TestGrooveTemplate:
    """Test GrooveTemplate dataclass."""

    @pytest.fixture
    def swing_template(self) -> GrooveTemplate:
        return GROOVE_TEMPLATES[GrooveType.SWING_1_3]

    @pytest.fixture
    def off_template(self) -> GrooveTemplate:
        return GROOVE_TEMPLATES[GrooveType.OFF]

    def test_init_defaults(self):
        """Default GrooveTemplate uses Off type with zero offsets."""
        tpl = GrooveTemplate()
        assert tpl.name == "Off"
        assert tpl.groove_type == GrooveType.OFF
        assert tpl.timing_offsets == [0] * 16
        assert tpl.velocity_offsets == [0] * 16
        assert tpl.description == ""

    def test_get_timing_offset(self, swing_template):
        """get_timing_offset returns correct values."""
        assert swing_template.get_timing_offset(0) == 0
        assert swing_template.get_timing_offset(1) == 30
        assert swing_template.get_timing_offset(2) == 0
        assert swing_template.get_timing_offset(4) == 0
        assert swing_template.get_timing_offset(5) == 30

    def test_get_timing_offset_wraps(self, swing_template):
        """get_timing_offset wraps around at position 16."""
        assert swing_template.get_timing_offset(16) == swing_template.get_timing_offset(0)
        assert swing_template.get_timing_offset(17) == swing_template.get_timing_offset(1)

    def test_get_velocity_offset_default(self, swing_template):
        """Default velocity offsets are all zero."""
        assert swing_template.get_velocity_offset(0) == 0
        assert swing_template.get_velocity_offset(7) == 0
        assert swing_template.get_velocity_offset(15) == 0

    def test_get_velocity_offset_wraps(self, off_template):
        """get_velocity_offset wraps around at position 16."""
        assert off_template.get_velocity_offset(16) == off_template.get_velocity_offset(0)

    def test_post_init_pads_timing_offsets(self):
        """Short timing_offsets get padded to 16."""
        tpl = GrooveTemplate(timing_offsets=[10, 20, 30])
        assert len(tpl.timing_offsets) == 16
        assert tpl.timing_offsets[0] == 10
        assert tpl.timing_offsets[1] == 20
        assert tpl.timing_offsets[2] == 30
        assert tpl.timing_offsets[3] == 0

    def test_post_init_pads_velocity_offsets(self):
        """Short velocity_offsets get padded to 16."""
        tpl = GrooveTemplate(velocity_offsets=[5, -5])
        assert len(tpl.velocity_offsets) == 16
        assert tpl.velocity_offsets[0] == 5
        assert tpl.velocity_offsets[1] == -5
        assert tpl.velocity_offsets[2] == 0

    def test_exact_16_length_no_padding(self):
        """Exactly 16 offsets are not modified."""
        offsets = list(range(16))
        tpl = GrooveTemplate(timing_offsets=offsets[:])
        assert tpl.timing_offsets == offsets

    def test_negative_timing_offsets(self):
        """Negative timing offsets work correctly."""
        tpl = GrooveTemplate(timing_offsets=[-10, -20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        assert tpl.get_timing_offset(0) == -10
        assert tpl.get_timing_offset(1) == -20

    def test_negative_velocity_offsets(self):
        """Negative velocity offsets work correctly."""
        tpl = GrooveTemplate(velocity_offsets=[-5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        assert tpl.get_velocity_offset(0) == -5

    def test_slots(self):
        """GrooveTemplate uses __slots__ via dataclass(slots=True)."""
        tpl = GrooveTemplate()
        with pytest.raises(AttributeError):
            tpl.new_attr = "should_fail"


# =============================================================================
# GROOVE_TEMPLATES Dict
# =============================================================================


class TestGrooveTemplatesDict:
    """Test the built-in GROOVE_TEMPLATES dictionary."""

    def test_all_groove_types_present(self):
        """All GrooveType values except CUSTOM have entries."""
        for gt in GrooveType:
            if gt == GrooveType.CUSTOM:
                continue
            assert gt in GROOVE_TEMPLATES, f"Missing template for {gt}"

        # CUSTOM should NOT be in the dict (no pre-defined template)
        assert GrooveType.CUSTOM not in GROOVE_TEMPLATES

    def test_off_template_zero_offsets(self):
        """OFF template has all zero offsets."""
        tpl = GROOVE_TEMPLATES[GrooveType.OFF]
        assert all(o == 0 for o in tpl.timing_offsets)
        assert all(o == 0 for o in tpl.velocity_offsets)

    def test_swing_templates_have_swing_on_even_eighths(self):
        """Swing templates have non-zero offset on positions 1,5,9,13."""
        for gt in [GrooveType.SWING_1_3, GrooveType.SWING_2_3]:
            tpl = GROOVE_TEMPLATES[gt]
            for i in [1, 5, 9, 13]:
                assert tpl.get_timing_offset(i) != 0, f"{gt} offset at {i} should be non-zero"
            for i in [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15]:
                assert tpl.get_timing_offset(i) == 0, f"{gt} offset at {i} should be zero"

    def test_templates_have_descriptions(self):
        """All templates have non-empty descriptions."""
        for gt, tpl in GROOVE_TEMPLATES.items():
            assert tpl.description, f"Template {gt} missing description"

    def test_templates_have_correct_type(self):
        """Each template's groove_type matches its key."""
        for gt, tpl in GROOVE_TEMPLATES.items():
            assert tpl.groove_type == gt


# =============================================================================
# GrooveQuantizer
# =============================================================================


class TestGrooveQuantizer:
    """Test GrooveQuantizer main functionality."""

    @pytest.fixture
    def quantizer(self) -> GrooveQuantizer:
        return GrooveQuantizer()

    def test_init_off_and_disabled(self, quantizer):
        """Default quantizer is OFF and disabled."""
        assert quantizer.current_groove.groove_type == GrooveType.OFF
        assert not quantizer.enabled
        assert quantizer.intensity == 1.0

    def test_set_groove_known(self, quantizer):
        """set_groove with known type returns True and enables."""
        result = quantizer.set_groove(GrooveType.SWING_1_3)
        assert result is True
        assert quantizer.enabled
        assert quantizer.current_groove.groove_type == GrooveType.SWING_1_3

    def test_set_groove_off_disables(self, quantizer):
        """set_groove to OFF disables quantizer."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        assert quantizer.enabled

        quantizer.set_groove(GrooveType.OFF)
        assert not quantizer.enabled

    def test_set_groove_unknown_returns_false(self, quantizer):
        """set_groove with unknown type returns False."""
        result = quantizer.set_groove(GrooveType.CUSTOM)
        assert result is False
        assert not quantizer.enabled

    def test_set_groove_by_name_known(self, quantizer):
        """set_groove_by_name with valid name works."""
        result = quantizer.set_groove_by_name("swing_1_3")
        assert result is True
        assert quantizer.current_groove.groove_type == GrooveType.SWING_1_3

    def test_set_groove_by_name_case_insensitive(self, quantizer):
        """set_groove_by_name is case-insensitive."""
        result = quantizer.set_groove_by_name("FUNK")
        assert result is True
        assert quantizer.current_groove.groove_type == GrooveType.FUNK

    def test_set_groove_by_name_unknown(self, quantizer):
        """set_groove_by_name with unknown name returns False."""
        result = quantizer.set_groove_by_name("nonexistent_groove")
        assert result is False

    def test_set_intensity(self, quantizer):
        """set_intensity sets value in [0, 1] range."""
        quantizer.set_intensity(0.5)
        assert quantizer.intensity == 0.5

    def test_set_intensity_clamps_low(self, quantizer):
        """set_intensity clamps below 0."""
        quantizer.set_intensity(-0.5)
        assert quantizer.intensity == 0.0

    def test_set_intensity_clamps_high(self, quantizer):
        """set_intensity clamps above 1."""
        quantizer.set_intensity(1.5)
        assert quantizer.intensity == 1.0

    def test_set_intensity_boundary(self, quantizer):
        """set_intensity at exact boundaries."""
        quantizer.set_intensity(0.0)
        assert quantizer.intensity == 0.0

        quantizer.set_intensity(1.0)
        assert quantizer.intensity == 1.0

    # --- apply_timing_offset ---

    def test_apply_timing_offset_disabled(self, quantizer):
        """When disabled, timing offset returns original tick."""
        result = quantizer.apply_timing_offset(100, 1)
        assert result == 100

    def test_apply_timing_offset_zero_intensity(self, quantizer):
        """When intensity is 0, timing offset returns original tick."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        quantizer.set_intensity(0.0)
        result = quantizer.apply_timing_offset(100, 1)
        assert result == 100

    def test_apply_timing_offset_full_intensity(self, quantizer):
        """Full intensity applies full offset."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        result = quantizer.apply_timing_offset(100, 1)
        assert result == 130  # 100 + 30

    def test_apply_timing_offset_partial_intensity(self, quantizer):
        """Partial intensity scales offset."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        quantizer.set_intensity(0.5)
        result = quantizer.apply_timing_offset(100, 1)
        assert result == 115  # 100 + int(30 * 0.5)

    def test_apply_timing_offset_negative(self, quantizer):
        """Negative timing offsets work correctly."""
        quantizer.set_groove(GrooveType.LATIN)
        result = quantizer.apply_timing_offset(200, 1)
        assert result == 190  # 200 + (-10)

    def test_apply_timing_offset_off_position(self, quantizer):
        """Positions with zero offset return unchanged."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        result = quantizer.apply_timing_offset(100, 0)
        assert result == 100  # position 0 has offset 0

    # --- apply_velocity_offset ---

    def test_apply_velocity_offset_disabled(self, quantizer):
        """When disabled, velocity offset returns original."""
        result = quantizer.apply_velocity_offset(100, 1)
        assert result == 100

    def test_apply_velocity_offset_zero_intensity(self, quantizer):
        """When intensity is 0, velocity offset returns original."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        quantizer.set_intensity(0.0)
        result = quantizer.apply_velocity_offset(100, 1)
        assert result == 100

    def test_apply_velocity_offset_defaults_zero(self, quantizer):
        """Default templates have zero velocity offsets."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        result = quantizer.apply_velocity_offset(100, 1)
        assert result == 100  # velocity_offsets are all 0

    def test_apply_velocity_offset_custom(self, quantizer):
        """Velocity offset from custom template works."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        # Manually assign the template
        quantizer.current_groove = custom
        quantizer.enabled = True
        result = quantizer.apply_velocity_offset(100, 0)
        assert result == 110  # 100 + 10
        result2 = quantizer.apply_velocity_offset(100, 1)
        assert result2 == 100  # offset 0 for position 1

    def test_apply_velocity_offset_clamps(self, quantizer):
        """Velocity offset clamps to 0-127 range."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[200, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        quantizer.current_groove = custom
        quantizer.enabled = True
        result = quantizer.apply_velocity_offset(100, 0)
        assert result == 127  # clamped

    def test_apply_velocity_offset_clamps_low(self, quantizer):
        """Negative velocity offset clamps to 0."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[-200, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        quantizer.current_groove = custom
        quantizer.enabled = True
        result = quantizer.apply_velocity_offset(10, 0)
        assert result == 0  # clamped

    def test_apply_velocity_offset_partial_intensity(self, quantizer):
        """Partial intensity scales velocity offset."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        quantizer.current_groove = custom
        quantizer.enabled = True
        quantizer.set_intensity(0.5)
        result = quantizer.apply_velocity_offset(100, 0)
        assert result == 110  # 100 + int(20 * 0.5)

    # --- get_available_grooves ---

    def test_get_available_grooves(self, quantizer):
        """get_available_grooves returns list of dicts with keys."""
        grooves = quantizer.get_available_grooves()
        assert isinstance(grooves, list)
        assert len(grooves) == len(GROOVE_TEMPLATES)

        for entry in grooves:
            assert "type" in entry
            assert "name" in entry
            assert "description" in entry

    def test_get_available_grooves_off_present(self, quantizer):
        """OFF groove is in available grooves."""
        grooves = quantizer.get_available_grooves()
        types = [g["type"] for g in grooves]
        assert "off" in types

    # --- status ---

    def test_get_status_default(self, quantizer):
        """get_status reflects initial state."""
        status = quantizer.get_status()
        assert status["enabled"] is False
        assert status["groove_type"] == "off"
        assert status["groove_name"] == "Off"
        assert status["intensity"] == 1.0

    def test_get_status_after_change(self, quantizer):
        """get_status reflects changes."""
        quantizer.set_groove(GrooveType.FUNK)
        quantizer.set_intensity(0.75)
        status = quantizer.get_status()

        assert status["enabled"] is True
        assert status["groove_type"] == "funk"
        assert status["groove_name"] == "Funk"
        assert status["intensity"] == 0.75


# =============================================================================
# get_default_groove_quantizer
# =============================================================================


class TestGetDefaultGrooveQuantizer:
    """Test the module-level get_default_groove_quantizer function."""

    def test_returns_groove_quantizer(self):
        """Function returns a GrooveQuantizer instance."""
        instance = get_default_groove_quantizer()
        assert isinstance(instance, GrooveQuantizer)

    def test_singleton_behavior(self):
        """Function always returns the same instance."""
        a = get_default_groove_quantizer()
        b = get_default_groove_quantizer()
        assert a is b

    def test_default_state(self):
        """Default instance starts with OFF groove."""
        instance = get_default_groove_quantizer()
        assert instance.current_groove.groove_type == GrooveType.OFF


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def quantizer(self) -> GrooveQuantizer:
        return GrooveQuantizer()

    # --- Dynamics edge cases ---

    def test_dynamics_value_at_zero(self):
        """Dynamics at 0 yields min values for all curves."""
        dyn = StyleDynamics()
        dyn.set_dynamics(0)
        params = dyn.get_all_parameters()

        for param, curve in dyn._curves.items():
            assert params[param] == pytest.approx(curve.min_value), (
                f"Parameter {param} should be at min_value {curve.min_value}, got {params[param]}"
            )

    def test_dynamics_value_at_max(self):
        """Dynamics at 127 yields max values for all curves."""
        dyn = StyleDynamics()
        dyn.set_dynamics(127)
        params = dyn.get_all_parameters()

        for param, curve in dyn._curves.items():
            assert params[param] == pytest.approx(curve.max_value), (
                f"Parameter {param} should be at max_value {curve.max_value}, got {params[param]}"
            )

    def test_dynamics_negative_adjust_below_zero(self):
        """Adjust by a large negative value from low value."""
        dyn = StyleDynamics()
        dyn.set_dynamics(10)
        dyn.adjust(-100)
        assert dyn.dynamics_value == 0

    def test_multiple_concurrent_set_dynamics(self):
        """Multiple rapid set_dynamics calls all reflect latest value."""
        dyn = StyleDynamics()
        for val in [0, 50, 100, 127, 0, 64]:
            dyn.set_dynamics(val)
        assert dyn.dynamics_value == 64

    def test_thread_safety_with_lock(self):
        """Lock prevents concurrent access issues (basic check)."""
        dyn = StyleDynamics()
        assert hasattr(dyn, "_lock")
        assert hasattr(dyn._lock, "acquire")
        assert hasattr(dyn._lock, "release")
        assert hasattr(dyn._lock, "__enter__")
        assert hasattr(dyn._lock, "__exit__")

    # --- Curve edge cases ---

    def test_curve_same_min_max(self):
        """When min == max, curve returns constant value."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 0.5, 0.5, "linear")
        assert curve.apply(0) == 0.5
        assert curve.apply(64) == 0.5
        assert curve.apply(127) == 0.5

    def test_curve_reversed_range(self):
        """Reversed range (min > max) still computes correctly."""
        curve = DynamicsCurve(DynamicsParameter.VOLUME, 1.0, 0.0, "linear")
        assert curve.apply(0) == 1.0
        assert curve.apply(127) == 0.0
        mid = curve.apply(64)
        assert mid == pytest.approx(1.0 - (64 / 127.0))

    # --- GrooveTemplate edge cases ---

    def test_groove_timing_offset_underflow(self):
        """Timing offset at negative position wraps."""
        tpl = GROOVE_TEMPLATES[GrooveType.SWING_1_3]
        # position -1 % 16 = 15
        assert tpl.get_timing_offset(-1) == tpl.get_timing_offset(15)

    def test_groove_timing_offset_large_position(self):
        """Large position wraps around."""
        tpl = GROOVE_TEMPLATES[GrooveType.SWING_1_3]
        # 100 % 16 = 4
        assert tpl.get_timing_offset(100) == tpl.get_timing_offset(4)
        # 101 % 16 = 5
        assert tpl.get_timing_offset(101) == tpl.get_timing_offset(5)

    def test_velocity_offset_underflow(self):
        """Velocity offset at negative position wraps."""
        tpl = GROOVE_TEMPLATES[GrooveType.OFF]
        assert tpl.get_velocity_offset(-1) == 0

    # --- GrooveQuantizer edge cases ---

    def test_apply_timing_offset_negative_tick(self):
        """apply_timing_offset with negative tick position."""
        quantizer = GrooveQuantizer()
        quantizer.set_groove(GrooveType.SWING_1_3)
        result = quantizer.apply_timing_offset(-50, 1)
        assert result == -20  # -50 + 30

    def test_apply_velocity_offset_boundary_max(self):
        """Velocity at 127 with positive offset clamps."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        quantizer = GrooveQuantizer()
        quantizer.current_groove = custom
        quantizer.enabled = True
        result = quantizer.apply_velocity_offset(127, 0)
        assert result == 127

    def test_apply_velocity_offset_boundary_min(self):
        """Velocity at 0 with negative offset clamps."""
        custom = GrooveTemplate(
            name="Custom",
            groove_type=GrooveType.CUSTOM,
            timing_offsets=[0] * 16,
            velocity_offsets=[-10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        )
        quantizer = GrooveQuantizer()
        quantizer.current_groove = custom
        quantizer.enabled = True
        result = quantizer.apply_velocity_offset(0, 0)
        assert result == 0

    def test_set_groove_by_name_empty_string(self, quantizer):
        """Empty string does not match any groove."""
        quantizer.set_groove_by_name("")
        # Should not change from OFF
        assert quantizer.current_groove.groove_type == GrooveType.OFF

    def test_set_groove_by_name_partial(self, quantizer):
        """Partial name match should still work (not exact but .value matches)."""
        result = quantizer.set_groove_by_name("swing")
        # This doesn't match any full .value, so it should fail
        assert result is False

    def test_multiple_groove_switches(self, quantizer):
        """Switching grooves multiple times updates state correctly."""
        quantizer.set_groove(GrooveType.SWING_1_3)
        assert quantizer.enabled
        assert quantizer.current_groove.groove_type == GrooveType.SWING_1_3

        quantizer.set_groove(GrooveType.FUNK)
        assert quantizer.current_groove.groove_type == GrooveType.FUNK

        quantizer.set_groove(GrooveType.OFF)
        assert not quantizer.enabled

    def test_all_swing_timing_offsets(self):
        """All swing template timing offsets at even 8th positions."""
        for gt in [GrooveType.SWING_1_3, GrooveType.SWING_2_3]:
            tpl = GROOVE_TEMPLATES[gt]
            for i in range(16):
                offset = tpl.get_timing_offset(i)
                if i in (1, 5, 9, 13):
                    assert offset > 0, f"Expected positive offset at {i} for {gt}"
                else:
                    assert offset == 0, f"Expected zero offset at {i} for {gt}"
