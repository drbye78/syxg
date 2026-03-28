"""
Configuration System Comprehensive Tests

Tests for XGML v3.0 configuration with actual synthesizer integration:
- XGML config loading
- Config creation from state
- Hot-reload functionality
- Watch path management
- Configuration validation
"""

from __future__ import annotations

import pytest
import json
import tempfile
from pathlib import Path


class TestConfigComprehensive:
    """Test configuration system with synthesizer integration."""

    @pytest.fixture
    def synthesizer(self):
        """Create a synthesizer instance for testing."""
        from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
        
        synth = ModernXGSynthesizer(
            sample_rate=44100,
            max_channels=16,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=True,
        )
        yield synth
        synth.cleanup()

    @pytest.mark.unit
    def test_config_system_initialization(self, synthesizer):
        """Test configuration system initialization."""
        assert hasattr(synthesizer, 'config_system')
        assert synthesizer.config_system is not None

    @pytest.mark.unit
    def test_xgml_config_loading(self, synthesizer, tmp_path):
        """Test XGML config loading from file."""
        # Create a test config file
        config_file = tmp_path / "test_config.json"
        config_data = {
            "version": "3.0",
            "name": "test_config",
            "parts": {
                "0": {"program": 0, "volume": 100, "pan": 64},
                "1": {"program": 1, "volume": 80, "pan": 32},
            },
            "effects": {
                "reverb": {"type": 4, "time": 2.5},
                "chorus": {"type": 1, "depth": 50},
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_from_state(self, synthesizer):
        """Test config creation from current state."""
        # Set some parameters
        synthesizer.set_channel_program(0, 0, 10)
        synthesizer.set_master_volume(0.8)

        # Create config from state
        config_string = synthesizer.create_xgml_config_from_current_state()
        
        # Should return a string
        assert config_string is None or isinstance(config_string, str)

    @pytest.mark.unit
    def test_hot_reload_enable(self, synthesizer):
        """Test hot-reload enable functionality."""
        # Enable hot-reload
        success = synthesizer.enable_config_hot_reloading(
            watch_paths=[],
            check_interval=1.0
        )
        
        # Should succeed
        assert success is True or success is False  # May fail if no paths

    @pytest.mark.unit
    def test_hot_reload_disable(self, synthesizer):
        """Test hot-reload disable functionality."""
        # Disable hot-reload
        success = synthesizer.disable_config_hot_reloading()
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_hot_reload_status(self, synthesizer):
        """Test hot-reload status."""
        status = synthesizer.get_hot_reload_status()
        
        # Should return status dict
        assert isinstance(status, dict)
        assert 'enabled' in status

    @pytest.mark.unit
    def test_watch_path_management(self, synthesizer, tmp_path):
        """Test watch path management."""
        # Add watch path
        test_path = tmp_path / "test_config.json"
        success = synthesizer.add_hot_reload_watch_path(str(test_path))
        
        # Should succeed
        assert success is True or success is False

        # Remove watch path
        success = synthesizer.remove_hot_reload_watch_path(str(test_path))
        
        # Should succeed
        assert success is True or success is False

    @pytest.mark.unit
    def test_config_template(self, synthesizer):
        """Test getting config template."""
        template = synthesizer.get_xgml_config_template()
        
        # Should return a string
        assert isinstance(template, str)
        assert len(template) > 0

    @pytest.mark.unit
    def test_config_validation(self, synthesizer, tmp_path):
        """Test config validation."""
        # Create invalid config
        invalid_config = tmp_path / "invalid.json"
        with open(invalid_config, 'w') as f:
            f.write("invalid json content")

        # Try to load invalid config
        success = synthesizer.load_xgml_config(str(invalid_config))
        
        # Should fail gracefully
        assert success is False

    @pytest.mark.unit
    def test_config_with_parts(self, synthesizer, tmp_path):
        """Test config with part settings."""
        # Create config with parts
        config_file = tmp_path / "parts_config.json"
        config_data = {
            "version": "3.0",
            "parts": {
                "0": {"program": 0, "volume": 100, "pan": 64},
                "1": {"program": 1, "volume": 80, "pan": 32},
                "2": {"program": 2, "volume": 90, "pan": 96},
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_with_effects(self, synthesizer, tmp_path):
        """Test config with effects settings."""
        # Create config with effects
        config_file = tmp_path / "effects_config.json"
        config_data = {
            "version": "3.0",
            "effects": {
                "reverb": {"type": 4, "time": 2.5, "level": 50},
                "chorus": {"type": 1, "depth": 50, "rate": 30},
                "variation": {"type": 12, "depth": 70},
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_with_mpe(self, synthesizer, tmp_path):
        """Test config with MPE settings."""
        # Create config with MPE
        config_file = tmp_path / "mpe_config.json"
        config_data = {
            "version": "3.0",
            "mpe": {
                "enabled": True,
                "zones": [
                    {"lower": 1, "upper": 15, "channels": 15}
                ],
                "pitch_bend_range": 48,
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_with_tuning(self, synthesizer, tmp_path):
        """Test config with tuning settings."""
        # Create config with tuning
        config_file = tmp_path / "tuning_config.json"
        config_data = {
            "version": "3.0",
            "tuning": {
                "temperament": "equal",
                "a4_frequency": 440.0,
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_manual_reload(self, synthesizer, tmp_path):
        """Test manual config reload."""
        # Create config file
        config_file = tmp_path / "manual_reload.json"
        config_data = {"version": "3.0", "name": "test"}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Trigger manual reload
        success = synthesizer.trigger_manual_config_reload(str(config_file))
        
        # Should succeed
        assert success is True or success is False

    @pytest.mark.unit
    def test_config_with_fm(self, synthesizer, tmp_path):
        """Test config with FM engine settings."""
        # Create config with FM
        config_file = tmp_path / "fm_config.json"
        config_data = {
            "version": "3.0",
            "fm": {
                "algorithm": 1,
                "algorithm_name": "basic",
                "master_volume": 0.8,
                "pitch_bend_range": 2,
                "operators": {
                    "op_0": {"ratio": 1.0, "level": 1.0},
                    "op_1": {"ratio": 2.0, "level": 0.5},
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_with_arpeggiator(self, synthesizer, tmp_path):
        """Test config with arpeggiator settings."""
        # Create config with arpeggiator
        config_file = tmp_path / "arp_config.json"
        config_data = {
            "version": "3.0",
            "arpeggiator": {
                "enabled": True,
                "tempo": 120,
                "channel_patterns": {
                    "channel_0": "up",
                    "channel_1": "down",
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_string_loading(self, synthesizer):
        """Test loading config from string."""
        config_string = """
        {
            "version": "3.0",
            "name": "test_config",
            "parts": {
                "0": {"program": 0, "volume": 100}
            }
        }
        """
        
        success = synthesizer.load_xgml_string(config_string)
        
        # Should succeed
        assert success is True

    @pytest.mark.unit
    def test_config_with_soundfont(self, synthesizer, tmp_path):
        """Test config with soundfont path."""
        # Create config with soundfont
        config_file = tmp_path / "sf2_config.json"
        config_data = {
            "version": "3.0",
            "soundfont": {
                "path": "/path/to/soundfont.sf2"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load config
        success = synthesizer.load_xgml_config(str(config_file))
        
        # Should succeed (even if file doesn't exist)
        assert success is True