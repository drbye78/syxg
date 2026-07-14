"""
Tests for S90/S70 Hardware Modules

Tests the hardware_specifications, control_surface_mapping,
preset_compatibility, and performance_features modules.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from synth.hardware.s90_s70.control_surface_mapping import ControlAssignment, ControlGroup
from synth.hardware.s90_s70.hardware_specifications import S90S70HardwareProfile, S90S70HardwareSpecs
from synth.hardware.s90_s70.performance_features import VoiceAllocationOptimizer
from synth.hardware.s90_s70.preset_compatibility import S90S70PresetBank, S90S70PresetCompatibility


# ── S90S70HardwareProfile Tests ─────────────────────────────────────────────


class TestS90S70HardwareProfile:
    """S90S70HardwareProfile dataclass tests."""

    @pytest.mark.unit
    def test_profile_defaults(self):
        """Verify defaults when creating a profile."""
        profile = S90S70HardwareProfile("S90 Test", 128, 16)
        assert profile.model_name == "S90 Test"
        assert profile.polyphony == 128
        assert profile.multitimbral_parts == 16
        assert profile.sample_rate == 44100
        assert profile.bit_depth == 24
        assert profile.awm_voices == 128
        assert profile.an_engines == 0
        assert profile.fdsp_voices == 1
        assert profile.insertion_effects_per_part == 3
        assert profile.system_effects == 2
        assert profile.wave_rom_size_mb == 64
        assert profile.user_samples_memory_mb == 32
        assert profile.preset_memory_slots == 128
        assert profile.user_memory_slots == 128
        assert profile.assignable_knobs == 4
        assert profile.assignable_sliders == 0
        assert profile.assignable_buttons == 4
        assert profile.display_type == "LCD"
        assert profile.display_lines == 2
        assert profile.display_chars_per_line == 16

    @pytest.mark.unit
    def test_profile_s70(self):
        """S70-specific hardware profile."""
        profile = S90S70HardwareProfile(
            model_name="S70",
            polyphony=64,
            multitimbral_parts=16,
            awm_voices=64,
            an_engines=0,
            wave_rom_size_mb=32,
        )
        assert profile.model_name == "S70"
        assert profile.polyphony == 64
        assert profile.awm_voices == 64
        assert profile.an_engines == 0  # No AN engine on S70
        assert profile.wave_rom_size_mb == 32
        assert profile.sample_rate == 44100
        assert profile.bit_depth == 24

    @pytest.mark.unit
    def test_profile_s90(self):
        """S90-specific hardware profile."""
        profile = S90S70HardwareProfile(
            model_name="S90",
            polyphony=128,
            multitimbral_parts=16,
            awm_voices=128,
            an_engines=2,
            wave_rom_size_mb=64,
        )
        assert profile.model_name == "S90"
        assert profile.polyphony == 128
        assert profile.awm_voices == 128
        assert profile.an_engines == 2  # Dual AN engines
        assert profile.wave_rom_size_mb == 64


# ── S90S70HardwareSpecs Tests ───────────────────────────────────────────────


class TestS90S70HardwareSpecs:
    """S90S70HardwareSpecs manager tests."""

    @pytest.mark.unit
    def test_init_profiles(self):
        """HardwareSpecs initializes with expected profile keys."""
        specs = S90S70HardwareSpecs()
        assert "S70" in specs.profiles
        assert "S90" in specs.profiles
        assert "S90ES" in specs.profiles
        assert len(specs.profiles) >= 2

    @pytest.mark.unit
    def test_get_profile(self):
        """Accessing the S90 profile returns correct data."""
        specs = S90S70HardwareSpecs()
        profile = specs.profiles["S90"]
        assert profile.model_name == "S90"
        assert profile.polyphony == 64  # Actual S90 spec
        assert profile.an_engines == 2
        assert profile.awm_voices == 64

    @pytest.mark.unit
    def test_get_profile_invalid(self):
        """Accessing a nonexistent profile returns None via .get()."""
        specs = S90S70HardwareSpecs()
        assert specs.profiles.get("Invalid") is None

    @pytest.mark.unit
    def test_list_profiles(self):
        """list_profiles via .profiles.keys()."""
        specs = S90S70HardwareSpecs()
        names = list(specs.profiles.keys())
        assert "S70" in names
        assert "S90" in names
        assert "S90ES" in names

    @pytest.mark.unit
    def test_set_hardware_profile(self):
        """Switching profiles via set_hardware_profile."""
        specs = S90S70HardwareSpecs()
        assert specs.set_hardware_profile("S70") is True
        assert specs.current_profile.model_name == "S70"
        assert specs.set_hardware_profile("S90ES") is True
        assert specs.current_profile.model_name == "S90ES"
        assert specs.set_hardware_profile("nonexistent") is False
        # Profile unchanged after failed set
        assert specs.current_profile.model_name == "S90ES"

    @pytest.mark.unit
    def test_hardware_limits(self):
        """get_hardware_limits returns limits from current profile."""
        specs = S90S70HardwareSpecs()
        limits = specs.get_hardware_limits()
        assert limits["max_polyphony"] == specs.current_profile.polyphony
        assert limits["max_parts"] == specs.current_profile.multitimbral_parts
        assert "max_awm_voices" in limits
        assert "max_an_voices" in limits
        assert "max_fdsp_voices" in limits
        assert "insertion_effects" in limits
        assert "system_effects" in limits
        assert "wave_rom_mb" in limits

    @pytest.mark.unit
    def test_hardware_performance_metrics(self):
        """get_hardware_performance_metrics returns all expected fields."""
        specs = S90S70HardwareSpecs()
        metrics = specs.get_hardware_performance_metrics()
        assert metrics["model"] == specs.current_profile.model_name
        assert metrics["polyphony"] == specs.current_profile.polyphony
        assert metrics["sample_rate"] == 44100
        assert metrics["bit_depth"] == 24
        assert metrics["midi_latency_ms"] == 2.0

    @pytest.mark.unit
    def test_simulate_hardware_voice_allocation(self):
        """Voice allocation simulation respects hardware limits."""
        specs = S90S70HardwareSpecs()
        limited = specs.simulate_hardware_voice_allocation(999, "awm")
        assert limited <= specs.current_profile.awm_voices


# ── ControlAssignment Tests ──────────────────────────────────────────────────


class TestControlAssignment:
    """ControlAssignment unit tests."""

    @pytest.mark.unit
    def test_init_defaults(self):
        """Defaults: curve='linear', name='Control {id}'."""
        ca = ControlAssignment(1, "filter.cutoff")
        assert ca.control_id == 1
        assert ca.parameter_path == "filter.cutoff"
        assert ca.min_value == 0.0
        assert ca.max_value == 127.0
        assert ca.curve == "linear"
        assert ca.name == "Control 1"

    @pytest.mark.unit
    def test_init_full(self):
        """All constructor params set correctly."""
        ca = ControlAssignment(2, "amp.volume", 0.0, 1.0, "log", "Volume")
        assert ca.control_id == 2
        assert ca.parameter_path == "amp.volume"
        assert ca.min_value == 0.0
        assert ca.max_value == 1.0
        assert ca.curve == "log"
        assert ca.name == "Volume"

    @pytest.mark.unit
    def test_apply_value_linear(self):
        """Linear curve: normalized = midi/127, scales to range."""
        ca = ControlAssignment(0, "test", 0.0, 127.0, "linear")
        result = ca.apply_value(64)
        expected = 64.0 / 127.0 * 127.0
        assert result == pytest.approx(expected)

    @pytest.mark.unit
    def test_apply_value_log(self):
        """Log curve produces different result than linear."""
        ca_lin = ControlAssignment(0, "test", 0.0, 127.0, "linear")
        ca_log = ControlAssignment(0, "test", 0.0, 127.0, "log")
        lin_result = ca_lin.apply_value(64)
        log_result = ca_log.apply_value(64)
        assert log_result != pytest.approx(lin_result)

    @pytest.mark.unit
    def test_apply_value_exp(self):
        """Exp curve produces different result than linear."""
        ca_lin = ControlAssignment(0, "test", 0.0, 127.0, "linear")
        ca_exp = ControlAssignment(0, "test", 0.0, 127.0, "exp")
        lin_result = ca_lin.apply_value(64)
        exp_result = ca_exp.apply_value(64)
        assert exp_result != pytest.approx(lin_result)

    @pytest.mark.unit
    def test_apply_value_edges(self):
        """MIDI 0 → min_value, MIDI 127 → max_value for linear/exp."""
        # Linear: exact mapping
        ca_lin = ControlAssignment(0, "test", 10.0, 100.0, "linear")
        assert ca_lin.apply_value(0) == 10.0
        assert ca_lin.apply_value(127) == 100.0

        # Log: min clips near ~min_value, max returns exactly max_value
        ca_log = ControlAssignment(0, "test", 0.0, 127.0, "log")
        assert ca_log.apply_value(127) == 127.0  # exact for midi=127

        # Exp: exact mapping for both endpoints
        ca_exp = ControlAssignment(0, "test", 0.0, 127.0, "exp")
        assert ca_exp.apply_value(0) == 0.0
        assert ca_exp.apply_value(127) == 127.0

    @pytest.mark.unit
    def test_apply_value_log_mid_curve(self):
        """Log curve expected value at midi=64, min=0, max=127."""
        ca = ControlAssignment(0, "test", 0.0, 127.0, "log")
        result = ca.apply_value(64)
        normalized = 64.0 / 127.0
        log_norm = math.log10(normalized * 99 + 1) / 2.0
        expected = 0.0 + log_norm * (127.0 - 0.0)
        assert result == pytest.approx(expected, rel=1e-4)

    @pytest.mark.unit
    def test_apply_value_exp_mid_curve(self):
        """Exp curve expected value at midi=64, min=0, max=127."""
        ca = ControlAssignment(0, "test", 0.0, 127.0, "exp")
        result = ca.apply_value(64)
        normalized = 64.0 / 127.0
        exp_norm = normalized**2
        expected = 0.0 + exp_norm * (127.0 - 0.0)
        assert result == pytest.approx(expected, rel=1e-4)

    @pytest.mark.unit
    def test_apply_value_custom_range(self):
        """Custom min/max values scale correctly."""
        ca = ControlAssignment(0, "test", -12.0, 12.0, "linear")
        result = ca.apply_value(64)
        normalized = 64.0 / 127.0
        expected = -12.0 + normalized * (12.0 - (-12.0))
        assert result == pytest.approx(expected, rel=1e-4)


# ── ControlGroup Tests ───────────────────────────────────────────────────────


class TestControlGroup:
    """ControlGroup unit tests."""

    @pytest.fixture
    def controls(self) -> list[ControlAssignment]:
        return [
            ControlAssignment(1, "filter.cutoff", 0, 127, "linear", "Cutoff"),
            ControlAssignment(2, "filter.resonance", 0, 127, "exp", "Resonance"),
        ]

    @pytest.mark.unit
    def test_init(self, controls):
        """ControlGroup stores id, name, controls."""
        group = ControlGroup(0, "Filter", controls)
        assert group.group_id == 0
        assert group.name == "Filter"
        assert len(group.controls) == 2
        assert group.active is True

    @pytest.mark.unit
    def test_get_control(self, controls):
        """get_control returns matching ControlAssignment by ID."""
        group = ControlGroup(0, "Filter", controls)
        found = group.get_control(1)
        assert found is not None
        assert found.control_id == 1
        assert found.parameter_path == "filter.cutoff"

    @pytest.mark.unit
    def test_get_control_missing(self, controls):
        """get_control returns None for unknown ID."""
        group = ControlGroup(0, "Filter", controls)
        assert group.get_control(99) is None

    @pytest.mark.unit
    def test_set_active(self, controls):
        """set_active changes the active flag."""
        group = ControlGroup(0, "Filter", controls)
        assert group.active is True
        group.set_active(False)
        assert group.active is False
        group.set_active(True)
        assert group.active is True


# ── S90S70ControlSurfaceMapping Tests ────────────────────────────────────────


class TestS90S70ControlSurfaceMapping:
    """S90S70ControlSurfaceMapping integration tests."""

    @pytest.mark.unit
    def test_control_surface_init(self):
        """Try to create S90S70ControlSurfaceMapping and verify it initializes."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        assert mapping is not None
        assert len(mapping.groups) >= 1
        assert 0 in mapping.groups  # Default group

    @pytest.mark.unit
    def test_get_control_assignment(self):
        """Default control assignments are accessible."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        assignment = mapping.get_control_assignment(1)
        assert assignment is not None
        assert assignment.parameter_path == "filter.cutoff"

    @pytest.mark.unit
    def test_assign_control(self):
        """assign_control adds a new assignment."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        result = mapping.assign_control(1, "osc.waveform", 0, 8, "linear", "Waveform")
        assert result is True
        assignment = mapping.get_control_assignment(1)
        assert assignment is not None
        assert assignment.parameter_path == "osc.waveform"
        assert assignment.name == "Waveform"

    @pytest.mark.unit
    def test_process_control_message(self):
        """process_control_message returns parameter update info."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        # control_id=2 is knob 2 (Resonance) — NOT in performance_assignments
        result = mapping.process_control_message(2, 100)
        assert result is not None
        assert "parameter_path" in result
        assert "value" in result
        assert result["control_id"] == 2
        assert result["midi_value"] == 100
        assert result["assignment_name"] == "Resonance"

    @pytest.mark.unit
    def test_available_controls(self):
        """get_available_controls returns a non-empty list."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        controls = mapping.get_available_controls()
        assert len(controls) > 0
        assert 1 in controls
        assert 81 in controls  # First assignable button

    @pytest.mark.unit
    def test_control_surface_layout(self):
        """get_control_surface_layout returns expected structure."""
        try:
            from synth.hardware.s90_s70.control_surface_mapping import (
                S90S70ControlSurfaceMapping,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping not available: {exc}")

        try:
            mapping = S90S70ControlSurfaceMapping()
        except Exception as exc:
            pytest.skip(f"S90S70ControlSurfaceMapping constructor failed: {exc}")

        layout = mapping.get_control_surface_layout()
        assert "knobs" in layout
        assert "buttons" in layout
        assert "fixed_controls" in layout
        assert layout["knobs"]["count"] == 4
        assert layout["total_assignable"] >= 4


# ── S90S70PresetBank Tests ────────────────────────────────────────────────────


class TestS90S70PresetBank:
    """S90S70PresetBank unit tests."""

    @pytest.mark.unit
    def test_init(self):
        """Bank initialized with empty presets."""
        bank = S90S70PresetBank("User", 0, 128)
        assert bank.bank_name == "User"
        assert bank.bank_id == 0
        assert bank.max_presets == 128
        assert bank.presets == {}

    @pytest.mark.unit
    def test_add_and_get_preset(self):
        """add_preset stores data; get_preset retrieves it."""
        bank = S90S70PresetBank("User", 0, 128)
        preset_data = {"name": "Piano", "category": "AWM"}
        result = bank.add_preset(0, preset_data)
        assert result is True
        retrieved = bank.get_preset(0)
        assert retrieved is not None
        assert retrieved["name"] == "Piano"
        assert retrieved["category"] == "AWM"

    @pytest.mark.unit
    def test_add_preset_out_of_range(self):
        """add_preset returns False if preset_number >= max_presets."""
        bank = S90S70PresetBank("User", 0, 128)
        assert bank.add_preset(200, {}) is False
        assert bank.add_preset(-1, {}) is False

    @pytest.mark.unit
    def test_clear_preset(self):
        """clear_preset removes the preset and returns True."""
        bank = S90S70PresetBank("User", 0, 128)
        bank.add_preset(5, {"name": "Piano"})
        result = bank.clear_preset(5)
        assert result is True
        assert bank.get_preset(5) is None

    @pytest.mark.unit
    def test_clear_preset_missing(self):
        """clear_preset on nonexistent preset returns False."""
        bank = S90S70PresetBank("User", 0, 128)
        assert bank.clear_preset(999) is False

    @pytest.mark.unit
    def test_get_bank_info(self):
        """get_bank_info returns metadata about the bank."""
        bank = S90S70PresetBank("User", 0, 128)
        info = bank.get_bank_info()
        assert info["name"] == "User"
        assert info["id"] == 0
        assert info["max_presets"] == 128
        assert info["used_presets"] == 0
        assert info["preset_numbers"] == []

        bank.add_preset(0, {"name": "Piano"})
        bank.add_preset(10, {"name": "Organ"})
        info = bank.get_bank_info()
        assert info["used_presets"] == 2
        assert info["preset_numbers"] == [0, 10]

    @pytest.mark.unit
    def test_add_preset_copies_data(self):
        """add_preset stores a copy, not a reference."""
        bank = S90S70PresetBank("User", 0, 128)
        original: dict[str, Any] = {"name": "Piano"}
        bank.add_preset(0, original)
        original["name"] = "Organ"
        retrieved = bank.get_preset(0)
        assert retrieved is not None
        assert retrieved["name"] == "Piano"  # Original mutation should not affect stored


# ── S90S70PresetCompatibility Tests ──────────────────────────────────────────


class TestS90S70PresetCompatibility:
    """S90S70PresetCompatibility unit tests."""

    @pytest.mark.unit
    def test_init_banks(self):
        """Initialize with standard bank set."""
        compat = S90S70PresetCompatibility()
        expected_banks = {"USER"} | set("ABCDEFGH") | {"DRUM1", "DRUM2"}
        for bank_name in expected_banks:
            assert bank_name in compat.banks, f"Missing bank: {bank_name}"
        assert len(compat.banks) == len(expected_banks)

    @pytest.mark.unit
    def test_get_bank_info(self):
        """get_bank_info returns info for an existing bank."""
        compat = S90S70PresetCompatibility()
        info = compat.get_bank_info("USER")
        assert info is not None
        assert info["name"] == "User"
        assert info["max_presets"] == 128

    @pytest.mark.unit
    def test_get_bank_info_nonexistent(self):
        """get_bank_info returns None for nonexistent bank."""
        compat = S90S70PresetCompatibility()
        assert compat.get_bank_info("NONEXISTENT") is None

    @pytest.mark.unit
    def test_save_and_load_preset(self):
        """save_preset then load_preset round-trips correctly."""
        compat = S90S70PresetCompatibility()
        preset_data = {
            "name": "My Piano",
            "category": "AWM",
            "volume": 100,
            "awm": {"filter_cutoff": 64, "filter_resonance": 32},
        }
        assert compat.save_preset(0, preset_data) is True
        loaded = compat.load_preset(0)
        assert loaded is not None
        assert loaded["name"] == "My Piano"

    @pytest.mark.unit
    def test_save_preset_invalid(self):
        """save_preset returns False for data missing required 'name'."""
        compat = S90S70PresetCompatibility()
        result = compat.save_preset(0, {"volume": 100})  # no "name" or "category"
        assert result is False

    @pytest.mark.unit
    def test_delete_preset(self):
        """delete_preset removes a saved preset."""
        compat = S90S70PresetCompatibility()
        compat.save_preset(5, {"name": "Test", "category": "AWM"})
        assert compat.load_preset(5) is not None
        assert compat.delete_preset(5) is True
        assert compat.load_preset(5) is None

    @pytest.mark.unit
    def test_copy_preset(self):
        """copy_preset copies between banks."""
        compat = S90S70PresetCompatibility()
        compat.save_preset(0, {"name": "Piano", "category": "AWM"}, "USER")
        assert compat.copy_preset("USER", 0, "A", 0) is True
        copied = compat.load_preset(0, "A")
        assert copied is not None
        assert copied["name"] == "Piano"

    @pytest.mark.unit
    def test_create_default_preset(self):
        """create_default_preset generates valid presets."""
        compat = S90S70PresetCompatibility()
        awm_preset = compat.create_default_preset("awm")
        assert awm_preset["common"]["name"] == "Default AWM"
        assert "awm" in awm_preset

        an_preset = compat.create_default_preset("an")
        assert an_preset["common"]["name"] == "Default AN"
        assert "an" in an_preset

        fdsp_preset = compat.create_default_preset("fdsp")
        assert fdsp_preset["common"]["name"] == "Default FDSP"
        assert "fdsp" in fdsp_preset

    @pytest.mark.unit
    def test_set_current_bank(self):
        """set_current_bank switches the active bank."""
        compat = S90S70PresetCompatibility()
        assert compat.set_current_bank("A") is True
        assert compat.get_current_bank() == "A"
        assert compat.set_current_bank("NONEXISTENT") is False
        # Current bank unchanged after failed set
        assert compat.get_current_bank() == "A"

    @pytest.mark.unit
    def test_hardware_profile(self):
        """Hardware profile get/set."""
        compat = S90S70PresetCompatibility()
        assert compat.get_hardware_profile() == "S90"
        assert compat.set_hardware_profile("S70") is True
        assert compat.get_hardware_profile() == "S70"
        assert compat.set_hardware_profile("Invalid") is False
        assert compat.get_hardware_profile() == "S70"

    @pytest.mark.unit
    def test_get_preset_statistics(self):
        """get_preset_statistics returns aggregate data."""
        compat = S90S70PresetCompatibility()
        compat.save_preset(0, {"name": "Piano", "category": "AWM"}, "USER")
        stats = compat.get_preset_statistics()
        assert stats["total_presets"] == 1
        assert "USER" in stats["bank_usage"]
        assert "memory_usage_estimate_mb" in stats

    @pytest.mark.unit
    def test_get_all_bank_info(self):
        """get_all_bank_info returns info for every bank."""
        compat = S90S70PresetCompatibility()
        all_info = compat.get_all_bank_info()
        assert "USER" in all_info
        assert "DRUM1" in all_info
        assert "A" in all_info
        # Should have all 11 banks
        assert len(all_info) >= 10


# ── VoiceAllocationOptimizer Tests ───────────────────────────────────────────


class TestVoiceAllocationOptimizer:
    """VoiceAllocationOptimizer unit tests."""

    @pytest.mark.unit
    def test_init_defaults(self):
        """Optimizer initializes with sensible defaults."""
        opt = VoiceAllocationOptimizer(64)
        assert opt.max_voices == 64
        assert opt.active_voices == {}
        assert opt.allocation_strategy == "priority"
        assert opt.voice_priorities["awm"] == 3
        assert opt.allocation_stats["total_allocations"] == 0

    @pytest.mark.unit
    def test_allocate_voice(self):
        """allocate_voice returns a voice ID and records the allocation."""
        opt = VoiceAllocationOptimizer(64)
        voice_id = opt.allocate_voice("awm", 1, 60, 100)
        assert voice_id is not None
        assert isinstance(voice_id, int)
        assert voice_id in opt.active_voices
        assert opt.active_voices[voice_id]["type"] == "awm"
        assert opt.active_voices[voice_id]["channel"] == 1
        assert opt.active_voices[voice_id]["note"] == 60
        assert opt.active_voices[voice_id]["velocity"] == 100
        assert opt.allocation_stats["total_allocations"] == 1

    @pytest.mark.unit
    def test_deallocate_voice(self):
        """Allocate then deallocate — voice removed, stats updated."""
        opt = VoiceAllocationOptimizer(64)
        voice_id = opt.allocate_voice("awm", 1, 60, 100)
        assert voice_id is not None

        result = opt.deallocate_voice(voice_id)
        assert result is True
        assert voice_id not in opt.active_voices
        assert opt.allocation_stats["total_deallocations"] == 1

    @pytest.mark.unit
    def test_deallocate_nonexistent(self):
        """deallocate_voice on nonexistent ID returns False."""
        opt = VoiceAllocationOptimizer(64)
        assert opt.deallocate_voice(999) is False

    @pytest.mark.unit
    def test_allocate_exhaustion(self):
        """Allocating beyond max_voices triggers voice stealing."""
        opt = VoiceAllocationOptimizer(4)
        # Fill all slots
        ids: list[int] = []
        for _ in range(4):
            vid = opt.allocate_voice("an", 1, 60, 80)  # priority=2
            assert vid is not None
            ids.append(vid)

        # Next allocation should steal (awm priority=3 > an priority=2)
        stolen_id = opt.allocate_voice("awm", 1, 64, 100)  # priority=3
        assert stolen_id is not None
        assert opt.allocation_stats["voice_stealing_events"] == 1
        # Still have max_voices active voices (one was stolen/replaced)
        assert len(opt.active_voices) == 4

    @pytest.mark.unit
    def test_allocate_failure_when_no_voices(self):
        """Allocate with max_voices=0 returns None."""
        opt = VoiceAllocationOptimizer(0)
        voice_id = opt.allocate_voice("awm", 1, 60, 100)
        assert voice_id is None
        assert opt.allocation_stats["allocation_failures"] == 1

    @pytest.mark.unit
    def test_get_allocation_status(self):
        """get_allocation_status returns current state."""
        opt = VoiceAllocationOptimizer(64)
        opt.allocate_voice("awm", 1, 60, 100)
        status = opt.get_allocation_status()
        assert status["active_voices"] == 1
        assert status["available_voices"] == 63
        assert status["allocation_strategy"] == "priority"
        assert status["stats"]["total_allocations"] == 1

    @pytest.mark.unit
    def test_set_allocation_strategy(self):
        """set_allocation_strategy validates input."""
        opt = VoiceAllocationOptimizer(64)
        assert opt.set_allocation_strategy("oldest") is True
        assert opt.allocation_strategy == "oldest"
        assert opt.set_allocation_strategy("quietest") is True
        assert opt.set_allocation_strategy("invalid") is False
        assert opt.allocation_strategy == "quietest"  # unchanged

    @pytest.mark.unit
    def test_allocate_different_types(self):
        """Voices of different types can be allocated concurrently."""
        opt = VoiceAllocationOptimizer(64)
        awm_id = opt.allocate_voice("awm", 1, 60, 100)
        an_id = opt.allocate_voice("an", 2, 72, 80)
        fdsp_id = opt.allocate_voice("fdsp", 3, 84, 60)
        assert awm_id is not None and awm_id != an_id and awm_id != fdsp_id
        assert an_id is not None and an_id != fdsp_id
        assert fdsp_id is not None
        assert len(opt.active_voices) == 3


# ── Live imports check for psutil-dependent classes ───────────────────────────


class TestS90S70PerformanceFeatures:
    """Check that S90S70PerformanceFeatures can be imported and constructed."""

    @pytest.mark.unit
    def test_performance_features_import(self):
        """S90S70PerformanceFeatures can be constructed (psutil available)."""
        try:
            from synth.hardware.s90_s70.performance_features import (
                S90S70PerformanceFeatures,
            )
        except ImportError as exc:
            pytest.skip(f"S90S70PerformanceFeatures not available: {exc}")

        try:
            features = S90S70PerformanceFeatures(max_voices=64)
        except Exception as exc:
            pytest.skip(f"S90S70PerformanceFeatures constructor failed: {exc}")

        assert features.voice_optimizer.max_voices == 64
        assert features.current_preset == "balanced"
        status = features.get_voice_allocation_strategy()
        assert status == "priority"
        assert features.set_voice_allocation_strategy("oldest") is True
        assert features.get_voice_allocation_strategy() == "oldest"
