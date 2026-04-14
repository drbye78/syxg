from __future__ import annotations

#!/usr/bin/env python3
"""
Test suite for ConfigManager and configuration system
"""

import os
import sys
import tempfile
import unittest

import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synth.primitives.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_config_path = tempfile.mktemp(suffix=".yaml")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_load_default_config(self):
        """Test loading default configuration"""
        # Use a path that definitely doesn't exist in any search path
        # Note: Since project has config.yaml, it may find that, so we test defaults are set
        manager = ConfigManager("/tmp/this_does_not_exist_12345.yaml")
        result = manager.load()

        # Either loads from fallback path or uses defaults
        self.assertIsNotNone(manager.config)
        self.assertIsNotNone(manager.config.get("audio"))

    def test_load_from_file(self):
        """Test loading configuration from file"""
        # Create test config file
        test_config = {
            "audio": {
                "sample_rate": 44100,
                "bit_depth": 24,
                "block_size": 512,
                "polyphony": 64,
                "volume": 0.5,
            },
            "midi": {
                "xg_enabled": False,
                "gs_enabled": True,
                "mpe_enabled": False,
                "device_id": 10,
            },
            "mpe": {"enabled": False},
            "engines": {"default": "fm", "priority": {"fm": 10, "sf2": 5}},
            "parts": {"part_0": {"engine": "fm", "program": 5, "volume": 80, "pan": 32}},
            "fm": {"algorithm": 2, "operators": {"op_0": {"frequency_ratio": 1.0}}},
            "effects": {"reverb": {"enabled": True, "type": 2, "time": 1.5}},
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        # Load config
        manager = ConfigManager(self.test_config_path)
        result = manager.load()

        self.assertTrue(result)
        self.assertTrue(manager.is_loaded())

        # Verify audio settings
        self.assertEqual(manager.get_sample_rate(), 44100)
        self.assertEqual(manager.get_bit_depth(), 24)
        self.assertEqual(manager.get_block_size(), 512)
        self.assertEqual(manager.get_polyphony(), 64)
        self.assertEqual(manager.get_volume(), 0.5)

        # Verify MIDI settings
        self.assertFalse(manager.get_xg_enabled())
        self.assertTrue(manager.get_gs_enabled())
        self.assertFalse(manager.get_mpe_enabled())
        self.assertEqual(manager.get_device_id(), 10)

        # Verify engine settings
        self.assertEqual(manager.get_default_engine(), "fm")
        self.assertEqual(manager.get_engine_priorities(), {"fm": 10, "sf2": 5})

        # Verify part settings
        part0 = manager.get_part_config(0)
        self.assertEqual(part0.get("engine"), "fm")
        self.assertEqual(part0.get("program"), 5)
        self.assertEqual(part0.get("volume"), 80)

        # Verify FM config
        fm_config = manager.get_fm_config()
        self.assertEqual(fm_config.get("algorithm"), 2)

        # Verify effects config
        effects = manager.get_effects_config()
        reverb = effects.get("reverb", {})
        self.assertTrue(reverb.get("enabled"))
        self.assertEqual(reverb.get("type"), 2)

    def test_get_audio_config(self):
        """Test audio config getter"""
        test_config = {"audio": {"sample_rate": 96000, "polyphony": 256}}

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        audio = manager.get_audio_config()
        self.assertEqual(audio["sample_rate"], 96000)
        self.assertEqual(audio["polyphony"], 256)

    def test_get_midi_config(self):
        """Test MIDI config getter"""
        test_config = {
            "midi": {"xg_enabled": True, "gs_enabled": True, "mpe_enabled": True, "device_id": 16}
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        midi = manager.get_midi_config()
        self.assertTrue(midi["xg_enabled"])
        self.assertTrue(midi["gs_enabled"])
        self.assertTrue(midi["mpe_enabled"])
        self.assertEqual(midi["device_id"], 16)

    def test_get_parts_config(self):
        """Test parts config getter"""
        test_config = {
            "parts": {
                "part_0": {"engine": "sf2", "program": 0},
                "part_1": {"engine": "fm", "program": 10},
                "part_15": {"engine": "sf2", "program": 127},
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        parts = manager.get_parts_config()
        self.assertEqual(parts["part_0"]["engine"], "sf2")
        self.assertEqual(parts["part_1"]["engine"], "fm")
        self.assertEqual(parts["part_15"]["program"], 127)

    def test_get_part_config(self):
        """Test individual part config getter"""
        test_config = {
            "parts": {
                "part_5": {
                    "engine": "fm",
                    "program": 42,
                    "volume": 90,
                    "pan": 50,
                    "reverb_send": 35,
                    "chorus_send": 10,
                }
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        part5 = manager.get_part_config(5)
        self.assertEqual(part5["engine"], "fm")
        self.assertEqual(part5["program"], 42)
        self.assertEqual(part5["volume"], 90)
        self.assertEqual(part5["pan"], 50)
        self.assertEqual(part5["reverb_send"], 35)
        self.assertEqual(part5["chorus_send"], 10)

    def test_get_fm_config(self):
        """Test FM config getter"""
        test_config = {
            "fm": {
                "algorithm": 5,
                "algorithm_name": "complex",
                "master_volume": 0.7,
                "pitch_bend_range": 4,
                "operators": {
                    "op_0": {"enabled": True, "frequency_ratio": 1.0},
                    "op_1": {"enabled": True, "frequency_ratio": 2.0},
                },
                "lfos": {"lfo_1": {"enabled": True, "frequency": 1.0}},
                "modulation": [{"source": "lfo1", "destination": "pitch", "amount": 0.5}],
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        fm = manager.get_fm_config()
        self.assertEqual(fm["algorithm"], 5)
        self.assertEqual(fm["algorithm_name"], "complex")
        self.assertEqual(fm["master_volume"], 0.7)

        operators = manager.get_fm_operators()
        self.assertEqual(len(operators), 8)
        self.assertTrue(operators[0].get("enabled"))

    def test_get_effects_config(self):
        """Test effects config getter"""
        test_config = {
            "effects": {
                "reverb": {"enabled": True, "type": 4, "time": 2.5, "level": 0.8},
                "chorus": {"enabled": True, "type": 1},
                "variation": {"enabled": False, "type": 12},
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        reverb = manager.get_reverb_config()
        self.assertTrue(reverb["enabled"])
        self.assertEqual(reverb["type"], 4)
        self.assertEqual(reverb["time"], 2.5)

        chorus = manager.get_chorus_config()
        self.assertTrue(chorus["enabled"])

        variation = manager.get_variation_config()
        self.assertFalse(variation["enabled"])

    def test_get_arpeggiator_config(self):
        """Test arpeggiator config getter"""
        test_config = {
            "arpeggiator": {
                "enabled": True,
                "tempo": 140,
                "swing": 0.1,
                "gate_time": 0.8,
                "octave_range": 3,
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        arp = manager.get_arpeggiator_config()
        self.assertTrue(arp["enabled"])
        self.assertEqual(arp["tempo"], 140)
        self.assertEqual(arp["swing"], 0.1)

        self.assertTrue(manager.get_arpeggiator_enabled())
        self.assertEqual(manager.get_arpeggiator_tempo(), 140)

    def test_get_mpe_config(self):
        """Test MPE config getter"""
        test_config = {
            "mpe": {
                "enabled": True,
                "zones": [
                    {"zone_id": 1, "lower_channel": 0, "upper_channel": 7, "pitch_bend_range": 48}
                ],
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        mpe = manager.get_mpe_config()
        self.assertTrue(mpe["enabled"])

        zones = manager.get_mpe_zones()
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["pitch_bend_range"], 48)

        self.assertTrue(manager.get_mpe_enabled())

    def test_get_tuning_config(self):
        """Test tuning config getter"""
        test_config = {
            "tuning": {"temperament": "just", "a4_frequency": 442.0, "global_offset": 5.0}
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        tuning = manager.get_tuning_config()
        self.assertEqual(tuning["temperament"], "just")
        self.assertEqual(tuning["a4_frequency"], 442.0)

        self.assertEqual(manager.get_temperament(), "just")
        self.assertEqual(manager.get_a4_frequency(), 442.0)

    def test_get_voices_config(self):
        """Test voice management config getter"""
        test_config = {
            "voices": {
                "max_polyphony": 256,
                "stealing_policy": "quietest",
                "part_0": 16,
                "part_1": 16,
            }
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        self.assertEqual(manager.get_max_polyphony(), 256)
        self.assertEqual(manager.get_stealing_policy(), "quietest")

        reserve = manager.get_voice_reserve()
        self.assertEqual(reserve[0], 16)
        self.assertEqual(reserve[1], 16)

    def test_full_config_access(self):
        """Test getting full config"""
        test_config = {
            "audio": {"sample_rate": 48000},
            "midi": {"xg_enabled": True},
            "engines": {"default": "sf2"},
            "parts": {},
            "fm": {},
            "effects": {},
            "arpeggiator": {},
            "mpe": {},
            "tuning": {},
        }

        with open(self.test_config_path, "w") as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(self.test_config_path)
        manager.load()

        full = manager.get_full_config()
        self.assertIn("audio", full)
        self.assertIn("midi", full)
        self.assertIn("engines", full)


class TestConfigIntegration(unittest.TestCase):
    """Integration tests for config with ModernXGSynthesizer"""

    def test_config_manager_with_real_config(self):
        """Test ConfigManager loads the actual config.yaml"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
        )

        if os.path.exists(config_path):
            manager = ConfigManager(config_path)
            result = manager.load()

            # Config should load successfully
            self.assertTrue(result)
            self.assertTrue(manager.is_loaded())

            # Check key values from actual config
            self.assertGreater(manager.get_sample_rate(), 0)
            self.assertGreater(manager.get_polyphony(), 0)

            # Check engines section exists
            engines = manager.get_engines_config()
            self.assertIn("default", engines)
            self.assertIn("priority", engines)

            # Check parts section
            parts = manager.get_parts_config()
            self.assertIsInstance(parts, dict)

            # Check effects section
            effects = manager.get_effects_config()
            self.assertIsInstance(effects, dict)
        else:
            self.skipTest("config.yaml not found")


if __name__ == "__main__":
    unittest.main()
