from __future__ import annotations
#!/usr/bin/env python3
"""
Test suite for layered configuration (includes) feature
"""

import os
import sys
import unittest
import tempfile
import yaml
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synth.core.config_manager import ConfigManager


class TestLayeredConfiguration(unittest.TestCase):
    """Test cases for layered configuration with includes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_simple_include(self):
        """Test simple file include"""
        # Create base config
        base_config = {
            'audio': {
                'sample_rate': 48000
            },
            'includes': ['effects.yaml']
        }
        
        # Create included config
        effects_config = {
            'effects': {
                'reverb': {
                    'enabled': True,
                    'type': 4
                }
            }
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'effects.yaml'), 'w') as f:
            yaml.dump(effects_config, f)
        
        # Load config
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        
        # Verify merged config
        self.assertEqual(config.get_sample_rate(), 48000)
        self.assertEqual(config.get_effects_config()['reverb']['enabled'], True)
        self.assertEqual(config.get_effects_config()['reverb']['type'], 4)
    
    def test_multiple_includes(self):
        """Test multiple includes with precedence"""
        # Create base config
        base_config = {
            'audio': {
                'sample_rate': 44100,
                'polyphony': 64
            },
            'includes': ['audio_boost.yaml', 'effects.yaml']
        }
        
        # Create first include (lower precedence)
        audio_boost = {
            'audio': {
                'polyphony': 128
            }
        }
        
        # Create second include (higher precedence)
        effects_config = {
            'effects': {
                'reverb': {
                    'enabled': True
                }
            }
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'audio_boost.yaml'), 'w') as f:
            yaml.dump(audio_boost, f)
        with open(os.path.join(self.test_dir, 'effects.yaml'), 'w') as f:
            yaml.dump(effects_config, f)
        
        # Load config
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        
        # audio_boost.yaml overrides polyphony but not sample_rate (deep merge)
        self.assertEqual(config.get_sample_rate(), 44100)
        self.assertEqual(config.get_polyphony(), 128)
        
        # Effects loaded
        self.assertTrue(config.get_effects_config()['reverb']['enabled'])
    
    def test_nested_includes(self):
        """Test nested includes"""
        # Create base config
        base_config = {
            'audio': {
                'sample_rate': 48000
            },
            'includes': ['base.yaml']
        }
        
        # Create base.yaml which includes nested.yaml
        base = {
            'includes': ['nested.yaml'],
            'audio': {
                'polyphony': 64
            }
        }
        
        # Create nested config
        nested = {
            'effects': {
                'reverb': {
                    'enabled': True
                }
            }
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'base.yaml'), 'w') as f:
            yaml.dump(base, f)
        with open(os.path.join(self.test_dir, 'nested.yaml'), 'w') as f:
            yaml.dump(nested, f)
        
        # Load config
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        
        # Verify all merged
        self.assertEqual(config.get_sample_rate(), 48000)
        self.assertEqual(config.get_polyphony(), 64)
        self.assertTrue(config.get_effects_config()['reverb']['enabled'])
    
    def test_include_stack_tracking(self):
        """Test that includes are tracked via get_includes()"""
        base_config = {
            'includes': ['level1.yaml']
        }
        level1 = {
            'includes': ['level2.yaml']
        }
        level2 = {
            'audio': {'sample_rate': 96000}
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'level1.yaml'), 'w') as f:
            yaml.dump(level1, f)
        with open(os.path.join(self.test_dir, 'level2.yaml'), 'w') as f:
            yaml.dump(level2, f)
        
        # Load config
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        self.assertEqual(config.get_sample_rate(), 96000)
        
        # Check includes from main config
        includes = config.get_includes()
        self.assertIn('level1.yaml', includes)
    
    def test_relative_path_resolution(self):
        """Test that relative paths are resolved from including file"""
        # Create subdirectory
        subdir = os.path.join(self.test_dir, 'configs')
        os.makedirs(subdir)
        
        # Base config in subdir includes file in parent dir
        base_config = {
            'includes': ['../shared.yaml']
        }
        
        shared = {
            'audio': {'sample_rate': 96000}
        }
        
        # Write config files
        with open(os.path.join(subdir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'shared.yaml'), 'w') as f:
            yaml.dump(shared, f)
        
        # Load config
        config = ConfigManager(os.path.join(subdir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        self.assertEqual(config.get_sample_rate(), 96000)
    
    def test_none_removes_key(self):
        """Test that None value removes key from base"""
        base_config = {
            'effects': {
                'reverb': {'enabled': True},
                'chorus': {'enabled': True}
            },
            'includes': ['remove_chorus.yaml']
        }
        
        remove_chorus = {
            'effects': {
                'chorus': None
            }
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'remove_chorus.yaml'), 'w') as f:
            yaml.dump(remove_chorus, f)
        
        # Load config
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        self.assertTrue(result)
        
        # Reverb should still exist
        self.assertIn('reverb', config.get_effects_config())
        
        # Chorus should be removed
        self.assertNotIn('chorus', config.get_effects_config())
    
    def test_circular_include_detection(self):
        """Test that circular includes are detected"""
        base_config = {
            'includes': ['a.yaml']
        }
        a_config = {
            'includes': ['b.yaml']
        }
        b_config = {
            'includes': ['a.yaml']  # Circular!
        }
        
        # Write config files
        with open(os.path.join(self.test_dir, 'config.yaml'), 'w') as f:
            yaml.dump(base_config, f)
        with open(os.path.join(self.test_dir, 'a.yaml'), 'w') as f:
            yaml.dump(a_config, f)
        with open(os.path.join(self.test_dir, 'b.yaml'), 'w') as f:
            yaml.dump(b_config, f)
        
        # Load config - should handle circular gracefully
        config = ConfigManager(os.path.join(self.test_dir, 'config.yaml'))
        result = config.load()
        
        # Should complete without error
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
