"""
MIDI 2.0 Deployment Package

Deployment package for MIDI 2.0 features in the XG Synthesizer.
Contains all necessary components for MIDI 2.0 support with proper packaging.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import json


class MIDIDeploymentPackage:
    """
    MIDI 2.0 Deployment Package
    
    Creates a complete deployment package for MIDI 2.0 features
    with all necessary components and dependencies.
    """
    
    def __init__(self, version: str = "2.0.0"):
        """
        Initialize the MIDI 2.0 deployment package.

        Args:
            version: Version string for the package
        """
        self.version = version
        self.package_name = f"xg_midi2_package_{version}"
        self.package_dir = Path(f"./{self.package_name}")
        self.components = self._get_midi2_components()
        self.dependencies = self._get_dependencies()
        self.documentation = self._get_documentation_files()
    
    def _get_midi2_components(self) -> List[str]:
        """Get list of MIDI 2.0 component files."""
        return [
            # Core MIDI 2.0 infrastructure
            "synth/midi/ump_packets.py",
            "synth/midi/file.py",
            "synth/midi/realtime.py",
            "synth/midi/types.py",
            "synth/midi/message.py",
            "synth/midi/buffer.py",
            
            # Advanced parameter control
            "synth/midi/advanced_parameter_control.py",
            
            # MIDI 2.0 effects processing
            "synth/effects/midi_2_effects_processor.py",
            "synth/effects/xg_effects_integration.py",
            
            # Channel with MIDI 2.0 support
            "synth/channel/channel.py",
            
            # Voice instance with MIDI 2.0 support
            "synth/voice/voice_instance.py",
            
            # Profile configuration
            "synth/midi/profile_configurator.py",
            
            # Conversion utilities
            "synth/midi/conversion.py",
            
            # Tests
            "tests/test_midi_2_features.py",
            "tests/test_suite_runner.py",
        ]
    
    def _get_dependencies(self) -> List[str]:
        """Get list of required dependencies."""
        return [
            "numpy>=1.21.0",
            "scipy>=1.7.0",  # For advanced audio processing
            "typing-extensions>=3.10.0",  # For newer typing features
        ]
    
    def _get_documentation_files(self) -> List[str]:
        """Get list of documentation files."""
        return [
            "docs/midi_2_api_reference.md",
            "docs/midi_2_user_guide.md",
        ]
    
    def create_package(self, output_dir: str = "./packages") -> str:
        """
        Create the MIDI 2.0 deployment package.

        Args:
            output_dir: Directory to place the package

        Returns:
            Path to the created package
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Create package directory
        self.package_dir.mkdir(exist_ok=True)
        
        # Create package structure
        self._create_package_structure()
        
        # Copy components
        self._copy_components()
        
        # Copy documentation
        self._copy_documentation()
        
        # Create package manifest
        self._create_manifest()
        
        # Create requirements file
        self._create_requirements()
        
        # Create setup script
        self._create_setup_script()
        
        # Create README
        self._create_readme()
        
        # Create ZIP archive
        zip_path = output_path / f"{self.package_name}.zip"
        self._create_zip_archive(zip_path)
        
        # Clean up temporary directory
        shutil.rmtree(self.package_dir)
        
        print(f"MIDI 2.0 deployment package created: {zip_path}")
        return str(zip_path)
    
    def _create_package_structure(self):
        """Create the package directory structure."""
        # Create main directories
        (self.package_dir / "synth" / "midi").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "synth" / "effects").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "synth" / "channel").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "synth" / "voice").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "tests").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "docs").mkdir(parents=True, exist_ok=True)
        (self.package_dir / "examples").mkdir(parents=True, exist_ok=True)
    
    def _copy_components(self):
        """Copy all MIDI 2.0 components to package."""
        for component_path in self.components:
            src_path = Path(component_path)
            if src_path.exists():
                dst_path = self.package_dir / component_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                print(f"Copied: {component_path}")
            else:
                print(f"Warning: Component not found: {component_path}")
    
    def _copy_documentation(self):
        """Copy documentation files to package."""
        for doc_path in self.documentation:
            src_path = Path(doc_path)
            if src_path.exists():
                dst_path = self.package_dir / doc_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                print(f"Copied documentation: {doc_path}")
            else:
                print(f"Warning: Documentation not found: {doc_path}")
    
    def _create_manifest(self):
        """Create package manifest file."""
        manifest = {
            "name": "XG MIDI 2.0 Extension Package",
            "version": self.version,
            "description": "Complete MIDI 2.0 implementation for XG Synthesizer",
            "author": "XG Development Team",
            "license": "MIT",
            "components": self.components,
            "dependencies": self.dependencies,
            "documentation": self.documentation,
            "features": [
                "Universal MIDI Packet (UMP) support",
                "32-bit parameter resolution",
                "Per-note controller processing",
                "MPE+ extensions",
                "XG effects with MIDI 2.0 integration",
                "Profile configuration system",
                "Capability discovery",
                "Advanced parameter mapping",
                "Real-time MIDI 2.0 processing"
            ],
            "installation_instructions": [
                "1. Extract package to your XG Synthesizer installation directory",
                "2. Install dependencies: pip install -r requirements.txt",
                "3. Update your synthesizer configuration to enable MIDI 2.0",
                "4. Restart the synthesizer application"
            ]
        }
        
        manifest_path = self.package_dir / "MANIFEST.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        print("Created package manifest")
    
    def _create_requirements(self):
        """Create requirements.txt file."""
        req_content = "\n".join(self.dependencies) + "\n"
        
        req_path = self.package_dir / "requirements.txt"
        with open(req_path, 'w', encoding='utf-8') as f:
            f.write(req_content)
        
        print("Created requirements file")
    
    def _create_setup_script(self):
        """Create setup/installation script."""
        setup_script = f'''#!/usr/bin/env python3
"""
XG MIDI 2.0 Setup Script

Installation script for MIDI 2.0 features in XG Synthesizer.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("Failed to install dependencies")
        return False
    return True


def backup_existing_installation():
    """Create backup of existing installation."""
    print("Creating backup of existing installation...")
    synth_dir = Path("synth")
    if synth_dir.exists():
        backup_dir = Path("synth_backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(synth_dir, backup_dir)
        print(f"Backup created: {backup_dir}")
    return True


def install_midi2_features():
    """Install MIDI 2.0 features."""
    print("Installing MIDI 2.0 features...")
    
    # Copy new files
    source_dirs = ["synth", "tests", "docs"]
    for src_dir in source_dirs:
        src_path = Path(src_dir)
        if src_path.exists():
            dst_path = Path("../") / src_dir
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"Installed {src_dir}/")
    
    print("MIDI 2.0 features installed successfully")
    return True


def verify_installation():
    """Verify the installation."""
    print("Verifying installation...")
    
    # Check for key files
    required_files = [
        "synth/midi/ump_packets.py",
        "synth/midi/advanced_parameter_control.py",
        "synth/effects/midi_2_effects_processor.py"
    ]
    
    all_present = True
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"Missing: {file_path}")
            all_present = False
    
    if all_present:
        print("Installation verified successfully")
        return True
    else:
        print("Installation verification failed")
        return False


def main():
    """Main installation function."""
    print("XG MIDI 2.0 Feature Installation")
    print("=" * 40)
    
    if not backup_existing_installation():
        print("Failed to create backup. Aborting.")
        return False
    
    if not install_dependencies():
        print("Dependency installation failed. Aborting.")
        return False
    
    if not install_midi2_features():
        print("Feature installation failed. Aborting.")
        return False
    
    if not verify_installation():
        print("Installation verification failed. Please check the installation.")
        return False
    
    print("\\nMIDI 2.0 features installed successfully!")
    print("Restart your XG Synthesizer to use the new features.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
        
        setup_path = self.package_dir / "install_midi2.py"
        with open(setup_path, 'w', encoding='utf-8') as f:
            f.write(setup_script)
        
        # Make executable (on Unix systems)
        if os.name != 'nt':  # Not Windows
            os.chmod(setup_path, 0o755)
        
        print("Created installation script")
    
    def _create_readme(self):
        """Create README file for the package."""
        readme_content = f"""# XG MIDI 2.0 Extension Package v{self.version}

This package adds complete MIDI 2.0 support to the XG Synthesizer, including:

## Features
- Universal MIDI Packet (UMP) support
- 32-bit parameter resolution (vs 7-bit in MIDI 1.0)
- Per-note controller processing for expressive performance
- MPE+ (MIDI Polyphonic Expression Plus) extensions
- XG effects integration with MIDI 2.0 parameter resolution
- Profile configuration and capability discovery system
- Advanced parameter mapping and modulation
- Real-time MIDI 2.0 processing

## Installation

### Method 1: Using the Installation Script
1. Extract this package to a temporary directory
2. Run: `python install_midi2.py`
3. Follow the prompts to complete installation

### Method 2: Manual Installation
1. Backup your existing XG Synthesizer installation
2. Copy the `synth/` directory contents to your XG installation
3. Install dependencies: `pip install -r requirements.txt`
4. Update your configuration to enable MIDI 2.0 features
5. Restart the XG Synthesizer

## Dependencies
- Python 3.8+
- numpy>=1.21.0
- scipy>=1.7.0
- typing-extensions>=3.10.0

## Usage
After installation, MIDI 2.0 features will be available in your XG Synthesizer. See the documentation files for detailed usage instructions.

## Documentation
- `docs/midi_2_api_reference.md` - Complete API reference
- `docs/midi_2_user_guide.md` - User guide with examples

## Support
For support, please contact the XG development team or consult the online documentation.
"""
        
        readme_path = self.package_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("Created README file")
    
    def _create_zip_archive(self, zip_path: Path):
        """Create ZIP archive of the package."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.package_dir.parent)
                    zipf.write(file_path, arc_path)
        
        print(f"ZIP archive created: {zip_path}")


def create_midi2_deployment_package(version: str = "2.0.0") -> str:
    """
    Create a complete MIDI 2.0 deployment package.

    Args:
        version: Version string for the package

    Returns:
        Path to the created package
    """
    package = MIDIDeploymentPackage(version)
    return package.create_package()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create XG MIDI 2.0 Deployment Package")
    parser.add_argument("--version", "-v", default="2.0.0", help="Package version (default: 2.0.0)")
    parser.add_argument("--output", "-o", default="./packages", help="Output directory (default: ./packages)")
    
    args = parser.parse_args()
    
    print(f"Creating XG MIDI 2.0 Deployment Package v{args.version}")
    print("=" * 50)
    
    package_path = create_midi2_deployment_package(args.version)
    
    print(f"\\nPackage created successfully: {package_path}")
    print("You can now distribute this package to deploy MIDI 2.0 features.")