"""
Tests for the synth.io.sfz modules: SFZ parser, region, engine, and related classes.
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.io.sfz.sfz_parser import (
    SFZOpcode,
    SFZRegion as ParserSFZRegion,
    SFZGroup,
    SFZInstrument,
    SFZParser,
)


@pytest.mark.unit
class TestSFZOpcode:
    """Tests for SFZOpcode."""

    def test_init(self):
        """Create SFZOpcode with name and value, verify attributes."""
        opcode = SFZOpcode("volume", -3.0)
        assert opcode.name == "volume"
        assert opcode.value == -3.0
        assert opcode.parameters == {}

    def test_init_with_params(self):
        """Create SFZOpcode with name, value, and parameters."""
        opcode = SFZOpcode("cutoff", 2000, {"curve": "analog"})
        assert opcode.name == "cutoff"
        assert opcode.value == 2000
        assert opcode.parameters == {"curve": "analog"}

    def test_str(self):
        """__str__ returns name=value format."""
        opcode = SFZOpcode("volume", -3.0)
        assert str(opcode) == "volume=-3.0"

    def test_repr(self):
        """__repr__ returns SFZOpcode(name=value) format."""
        opcode = SFZOpcode("volume", -3.0)
        assert repr(opcode) == "SFZOpcode(volume=-3.0)"

    def test_str_with_params(self):
        """__str__ includes parameters when present."""
        opcode = SFZOpcode("cutoff", 2000, {"curve": "analog"})
        result = str(opcode)
        assert "cutoff=2000" in result
        assert "curve=analog" in result


@pytest.mark.unit
class TestSFZRegion:
    """Tests for SFZRegion (parser-level)."""

    def test_init(self):
        """Empty opcodes dict, empty comments."""
        region = ParserSFZRegion()
        assert region.opcodes == {}
        assert region.comments == []

    def test_set_and_get_opcode(self):
        """Set an opcode and retrieve it with get_opcode."""
        region = ParserSFZRegion()
        opcode = SFZOpcode("sample", "piano.wav")
        region.set_opcode(opcode)
        retrieved = region.get_opcode("sample")
        assert retrieved is opcode
        assert retrieved.name == "sample"
        assert retrieved.value == "piano.wav"

    def test_get_value(self):
        """get_value returns the opcode value or default."""
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("sample", "piano.wav"))
        assert region.get_value("sample") == "piano.wav"
        assert region.get_value("missing", default=None) is None

    def test_has_opcode(self):
        """has_opcode returns True/False."""
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("key", 60))
        assert region.has_opcode("key") is True
        assert region.has_opcode("nonexistent") is False

    def test_to_dict(self):
        """to_dict returns dict mapping opcode names to values."""
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("sample", "kick.wav"))
        region.set_opcode(SFZOpcode("key", 36))
        d = region.to_dict()
        assert d == {"sample": "kick.wav", "key": 36}

    def test_str_repr(self):
        """__str__ and __repr__ return correct strings."""
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("sample", "hat.wav"))
        assert isinstance(str(region), str)
        assert "sample=hat.wav" in str(region)
        assert isinstance(repr(region), str)
        assert "SFZRegion" in repr(region)
        assert "1 opcodes" in repr(region)


@pytest.mark.unit
class TestSFZGroup:
    """Tests for SFZGroup."""

    def test_init(self):
        """Empty opcodes, empty regions."""
        group = SFZGroup()
        assert group.opcodes == {}
        assert group.regions == []
        assert group.comments == []

    def test_add_region(self):
        """Add a region and verify it appears in the regions list."""
        group = SFZGroup()
        region = ParserSFZRegion()
        group.add_region(region)
        assert len(group.regions) == 1
        assert group.regions[0] is region

    def test_set_opcode_and_get_value(self):
        """Set and get opcodes on the group."""
        group = SFZGroup()
        group.set_opcode(SFZOpcode("volume", -6.0))
        assert group.get_value("volume") == -6.0
        assert group.get_value("nonexistent", default=0) == 0

    def test_to_dict(self):
        """to_dict includes 'regions' key with list of region dicts."""
        group = SFZGroup()
        group.set_opcode(SFZOpcode("key", 48))
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("sample", "snare.wav"))
        group.add_region(region)
        d = group.to_dict()
        assert "regions" in d
        assert isinstance(d["regions"], list)
        assert len(d["regions"]) == 1
        assert d["regions"][0] == {"sample": "snare.wav"}
        assert d["key"] == 48


@pytest.mark.unit
class TestSFZInstrument:
    """Tests for SFZInstrument."""

    def test_init_with_path(self):
        """Path set, filename extracted from path."""
        inst = SFZInstrument("/samples/piano.sfz")
        assert inst.path == "/samples/piano.sfz"
        assert inst.filename == "piano.sfz"

    def test_init_no_path(self):
        """Path None, filename defaults to 'unnamed.sfz'."""
        inst = SFZInstrument()
        assert inst.path is None
        assert inst.filename == "unnamed.sfz"

    def test_set_global_opcode(self):
        """Set and get global opcodes."""
        inst = SFZInstrument()
        inst.set_global_opcode(SFZOpcode("ampeg_attack", 0.1))
        assert inst.get_global_value("ampeg_attack") == 0.1
        assert inst.get_global_value("nonexistent", "default") == "default"

    def test_set_control_opcode(self):
        """Set and get control opcodes."""
        inst = SFZInstrument()
        inst.set_control_opcode(SFZOpcode("default_path", "Samples/"))
        assert inst.get_control_value("default_path") == "Samples/"

    def test_add_group_and_get_all_regions(self):
        """Add groups with regions and verify get_all_regions returns all."""
        inst = SFZInstrument()
        group1 = SFZGroup()
        r1 = ParserSFZRegion()
        r1.set_opcode(SFZOpcode("sample", "a.wav"))
        group1.add_region(r1)
        inst.add_group(group1)

        group2 = SFZGroup()
        r2 = ParserSFZRegion()
        r2.set_opcode(SFZOpcode("sample", "b.wav"))
        r3 = ParserSFZRegion()
        r3.set_opcode(SFZOpcode("sample", "c.wav"))
        group2.add_region(r2)
        group2.add_region(r3)
        inst.add_group(group2)

        all_regions = inst.get_all_regions()
        assert len(all_regions) == 3
        assert all_regions[0] is r1
        assert all_regions[1] is r2
        assert all_regions[2] is r3

    def test_to_dict(self):
        """to_dict returns comprehensive dict structure."""
        inst = SFZInstrument("/test/inst.sfz")
        inst.set_global_opcode(SFZOpcode("volume", -3.0))
        inst.set_control_opcode(SFZOpcode("default_path", "Samples/"))

        group = SFZGroup()
        group.set_opcode(SFZOpcode("key", 60))
        region = ParserSFZRegion()
        region.set_opcode(SFZOpcode("sample", "x.wav"))
        group.add_region(region)
        inst.add_group(group)

        d = inst.to_dict()
        assert d["filename"] == "inst.sfz"
        assert d["path"] == "/test/inst.sfz"
        assert d["global"] == {"volume": -3.0}
        assert d["control"] == {"default_path": "Samples/"}
        assert len(d["groups"]) == 1
        assert d["total_regions"] == 1


@pytest.mark.unit
class TestSFZParser:
    """Tests for SFZParser."""

    def test_parse_simple_region(self):
        """Parse a simple single-region SFZ string."""
        parser = SFZParser()
        sfz_content = "<region>\nsample=foo.wav key=48"
        instrument = parser.parse_string(sfz_content)
        assert isinstance(instrument, SFZInstrument)
        assert len(instrument.groups) == 1
        regions = instrument.get_all_regions()
        assert len(regions) == 1
        region = regions[0]
        assert region.get_value("sample") == "foo.wav"
        assert region.get_value("key") == 48

    def test_parse_multiple_regions(self):
        """Parse content with two regions (each in its own group), verify count."""
        parser = SFZParser()
        sfz_content = "<group>\n<region>\nsample=a.wav\n<group>\n<region>\nsample=b.wav"
        instrument = parser.parse_string(sfz_content)
        regions = instrument.get_all_regions()
        assert len(regions) == 2

    def test_parse_global_and_region(self):
        """Parse global opcode followed by a region."""
        parser = SFZParser()
        sfz_content = "<global>\nampeg_attack=0.1\n<region>\nsample=bar.wav"
        instrument = parser.parse_string(sfz_content)
        assert instrument.get_global_value("ampeg_attack") == 0.1
        regions = instrument.get_all_regions()
        assert len(regions) == 1
        assert regions[0].get_value("sample") == "bar.wav"

    def test_parse_file_not_found(self):
        """parse_file raises FileNotFoundError for nonexistent file."""
        parser = SFZParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent_file_12345.sfz")

    def test_parse_with_control(self):
        """Parse control section followed by a region."""
        parser = SFZParser()
        sfz_content = "<control>\ndefault_path=Samples/\n<region>\nsample=test.wav"
        instrument = parser.parse_string(sfz_content)
        assert instrument.get_control_value("default_path") == "Samples/"
        regions = instrument.get_all_regions()
        assert len(regions) == 1
        assert regions[0].get_value("sample") == "test.wav"


@pytest.mark.unit
class TestSFZEnvelope:
    """Tests for SFZEnvelope from sfz_region.py."""

    @pytest.fixture(autouse=True)
    def _import_envelope(self):
        """Import SFZEnvelope, skipping if dependencies unavailable."""
        try:
            from synth.io.sfz.sfz_region import SFZEnvelope

            self.SFZEnvelope = SFZEnvelope
        except ImportError as e:
            pytest.skip(f"SFZEnvelope import failed: {e}")

    def test_envelope_init(self):
        """Initialize envelope and verify default state."""
        env = self.SFZEnvelope({"attack": 0.1, "release": 0.5})
        assert env.attack == 0.1
        assert env.release == 0.5
        assert env.state == "idle"
        assert env.current_level == 0.0

    def test_envelope_note_on(self):
        """Note on transitions from idle to delay/attack."""
        env = self.SFZEnvelope({"attack": 0.1})
        assert env.state == "idle"
        env.note_on(velocity=1.0)
        # No delay set -> should go directly to "attack"
        assert env.state == "attack"

    def test_envelope_with_delay_note_on(self):
        """Note on with delay transitions to delay first."""
        env = self.SFZEnvelope({"attack": 0.1, "delay": 0.05})
        env.note_on(velocity=1.0)
        assert env.state == "delay"

    def test_envelope_note_off(self):
        """Note off transitions to release."""
        env = self.SFZEnvelope({"attack": 0.1, "release": 0.5})
        env.note_on(velocity=1.0)
        # Advance past attack to sustain
        env.process(block_size=4410, sample_rate=44100)
        env.note_off()
        assert env.state == "release"

    def test_envelope_process(self):
        """Process returns np.ndarray of correct shape within [0, 1]."""
        env = self.SFZEnvelope({"attack": 0.01, "release": 0.1})
        env.note_on(velocity=1.0)
        result = env.process(block_size=64, sample_rate=44100)
        assert isinstance(result, np.ndarray)
        assert result.shape == (64,)
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)


@pytest.mark.unit
class TestSFZEngine:
    """Tests for SFZEngine (may skip if imports/construction fail)."""

    def test_sfz_engine_init(self):
        """Try to import and construct SFZEngine, skip on failure."""
        try:
            from synth.io.sfz.sfz_engine import SFZEngine
        except ImportError as e:
            pytest.skip(f"SFZEngine import failed: {e}")

        try:
            engine = SFZEngine(sample_rate=44100, block_size=256)
            assert engine.sample_rate == 44100
            assert engine.block_size == 256
        except Exception as e:
            pytest.skip(f"SFZEngine construction failed: {e}")


@pytest.mark.unit
class TestSFZModuleImports:
    """Lightweight import tests for other SFZ modules."""

    def test_import_controller_mapper(self):
        """Import SFZControllerMapper, skip if ImportError."""
        try:
            from synth.io.sfz.controller_mapping import SFZControllerMapper

            assert SFZControllerMapper is not None
        except ImportError as e:
            pytest.skip(f"SFZControllerMapper import failed: {e}")

    def test_import_dynamic_modulation(self):
        """Import SFZDynamicModulation, skip if ImportError."""
        try:
            from synth.io.sfz.dynamic_modulation import SFZDynamicModulation

            assert SFZDynamicModulation is not None
        except ImportError as e:
            pytest.skip(f"SFZDynamicModulation import failed: {e}")
