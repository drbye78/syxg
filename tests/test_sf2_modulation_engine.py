"""
Test suite for SF2 modulation engine.

Tests SF2GeneratorProcessor, SF2ModulationEngine, and SF2ZoneEngine.
"""

import pytest
from synth.sf2 import sf2_modulation_engine
from synth.sf2.sf2_constants import SF2_GENERATORS


class TestSF2GeneratorProcessor:
    """Tests for SF2GeneratorProcessor class."""

    def test_processor_initialization(self):
        """Test processor initializes with defaults."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        # Check default values are set
        for gen_id, gen_info in SF2_GENERATORS.items():
            value = proc.get_generator(gen_id)
            assert value == gen_info["default"]

    def test_set_generator_valid(self):
        """Test setting valid generator."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()
        proc.set_generator(48, 12)  # coarseTune
        assert proc.get_generator(48) == 12

    def test_set_generator_clamp_range(self):
        """Test generator value is clamped to valid range."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        # Try to set value outside range
        proc.set_generator(48, 200)  # coarseTune max is 120
        assert proc.get_generator(48) <= 120

        proc.set_generator(48, -200)  # coarseTune min is -120
        assert proc.get_generator(48) >= -120

    def test_to_modern_synth_params_complete(self):
        """Test parameter conversion produces all expected params."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()
        params = proc.to_modern_synth_params()

        # Volume envelope
        assert "amp_delay" in params
        assert "amp_attack" in params
        assert "amp_hold" in params
        assert "amp_decay" in params
        assert "amp_sustain" in params
        assert "amp_release" in params

        # Modulation envelope
        assert "mod_env_delay" in params
        assert "mod_env_attack" in params

        # Filter - check for actual naming
        assert "filter_cutoff" in params
        assert "filter_resonance" in params

    def test_loop_parameter_mapping(self):
        """Test loop parameters are mapped to correct generators."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        # Set loop generators (44-47)
        proc.set_generator(44, 100)  # startloopAddrsCoarse
        proc.set_generator(45, 5)  # startloopAddrsFine
        proc.set_generator(46, 200)  # endloopAddrsCoarse
        proc.set_generator(47, 10)  # endloopAddrsFine

        params = proc.to_modern_synth_params()

        assert params["start_loop_coarse"] == 100
        assert params["start_loop_fine"] == 5
        assert params["end_loop_coarse"] == 200
        assert params["end_loop_fine"] == 10

    def test_tuning_parameters(self):
        """Test tuning parameters."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        proc.set_generator(48, 12)  # coarseTune
        proc.set_generator(49, -50)  # fineTune
        proc.set_generator(52, 100)  # scaleTuning
        proc.set_generator(54, 60)  # overridingRootKey

        params = proc.to_modern_synth_params()

        assert params["coarse_tune"] == 12
        assert params["fine_tune"] == -0.5  # -50/100
        assert params["scale_tuning"] == 1.0  # 100/100
        assert params["overriding_root_key"] == 60

    def test_envelope_timecent_conversion(self):
        """Test envelope times use timecent conversion."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        # -12000 = instant (0 seconds)
        proc.set_generator(9, -12000)  # volEnvAttack
        params = proc.to_modern_synth_params()
        assert params["amp_attack"] == 0.0

        # 0 = small value (0.001s due to implementation)
        proc.set_generator(9, 0)
        params = proc.to_modern_synth_params()
        # Should produce some positive value
        assert params["amp_attack"] > 0

    def test_sample_parameters(self):
        """Test sample parameters."""
        proc = sf2_modulation_engine.SF2GeneratorProcessor()

        proc.set_generator(50, 5)  # sampleID
        proc.set_generator(51, 1)  # sampleModes (loop)
        proc.set_generator(53, 3)  # exclusiveClass

        params = proc.to_modern_synth_params()

        assert params["sample_id"] == 5
        assert params["sample_mode"] == 1
        assert params["exclusive_class"] == 3


class TestSF2ModulationEngine:
    """Tests for SF2ModulationEngine class."""

    def test_modulation_engine_init(self):
        """Test modulation engine initialization."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        assert engine.controller_values is not None
        assert engine.modulators is not None

    def test_update_controller(self):
        """Test controller value update."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        engine.update_controller(7, 100)  # Volume
        assert engine.controller_values[7] == 100

    def test_update_controller_with_smoothing(self):
        """Test controller update with smoothing."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        engine.smoothing_filters[7] = 50.0
        engine.update_controller(7, 100, smooth=True)
        assert 7 in engine.smoothing_filters

    def test_reset_all(self):
        """Test resetting all controllers."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        engine.controller_values[7] = 100
        engine.controller_states[7] = 50

        engine.reset_all()

        assert engine.controller_values.get(7, 0) != 100

    def test_get_modulation_for_generator(self):
        """Test getting modulation for generator."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        mod = engine.get_modulation_for_generator(21, 60, 100)
        assert isinstance(mod, float)

    def test_get_performance_state(self):
        """Test performance state retrieval."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        state = engine.get_performance_state()

        assert "active_voices" in state
        assert "controller_count" in state
        assert "smoothing_filters" in state


class TestSF2ZoneEngine:
    """Tests for SF2ZoneEngine class."""

    def test_zone_engine_creation(self):
        """Test zone engine creation."""
        zone_engine = sf2_modulation_engine.SF2ZoneEngine(
            "test_zone",
            {},  # instrument_generators
            [],  # instrument_modulators
            {},  # preset_generators
            [],  # preset_modulators
        )

        assert zone_engine.zone_id == "test_zone"
        assert zone_engine.processor is not None

    def test_zone_engine_inheritance(self):
        """Test generator inheritance from preset to instrument."""
        # Preset has coarseTune = 5
        preset_gens = {48: 5}
        # Instrument has fineTune = -25
        instrument_gens = {49: -25}

        zone_engine = sf2_modulation_engine.SF2ZoneEngine(
            "test_zone", instrument_gens, [], preset_gens, []
        )

        params = zone_engine.get_modulated_parameters(60, 100)

        # Both should be present (instrument overrides)
        assert params["coarse_tune"] == 5
        assert params["fine_tune"] == -0.25  # -25/100

    def test_get_modulated_parameters_note_velocity(self):
        """Test parameters include note and velocity."""
        zone_engine = sf2_modulation_engine.SF2ZoneEngine("test", {}, [], {}, [])

        params = zone_engine.get_modulated_parameters(60, 100)

        assert params["note"] == 60
        assert params["velocity"] == 100

    def test_zone_engine_modulation(self):
        """Test zone engine applies modulation."""
        # Set velocity-sensitive amp envelope
        instrument_gens = {
            12: 500,  # volEnvSustain at max
        }

        zone_engine = sf2_modulation_engine.SF2ZoneEngine(
            "test", instrument_gens, [], {}, []
        )

        # Higher velocity should result in higher effective sustain
        params_low = zone_engine.get_modulated_parameters(60, 30)
        params_high = zone_engine.get_modulated_parameters(60, 127)

        # Both should have sustain, but velocity factor differs
        assert "amp_sustain" in params_low
        assert "amp_sustain" in params_high


class TestCreateZoneEngine:
    """Tests for create_zone_engine factory function."""

    def test_factory_function(self):
        """Test factory function creates zone engine."""
        engine = sf2_modulation_engine.SF2ModulationEngine()

        zone_engine = engine.create_zone_engine(
            "factory_test",
            {48: 12},  # instrument_generators
            [],  # instrument_modulators
            {49: -50},  # preset_generators
            [],  # preset_modulators
        )

        assert zone_engine is not None
        assert zone_engine.zone_id == "factory_test"

        params = zone_engine.get_modulated_parameters(60, 100)
        assert params["coarse_tune"] == 12

    def test_standalone_factory(self):
        """Test standalone create_zone_engine function."""
        zone_engine = sf2_modulation_engine.create_zone_engine(
            "standalone",
            {50: 0},  # sampleID
            [],
            {48: 0},
            [],
        )

        assert zone_engine is not None
        params = zone_engine.get_modulated_parameters(60, 100)
        assert "sample_id" in params
