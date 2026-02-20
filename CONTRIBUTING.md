# 🤝 Contributing to XG Synthesizer

Thank you for your interest in contributing to the XG Synthesizer project! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

## 📜 Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- **Be respectful** and inclusive in all interactions
- **Be collaborative** and help fellow contributors
- **Be patient** and understanding of different skill levels
- **Focus on constructive feedback** and solutions
- **Respect diverse perspectives** and experiences

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.8+** installed
- **Git** for version control
- **Basic understanding** of digital audio and MIDI concepts
- **Familiarity** with synthesis techniques (helpful but not required)

### Quick Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/syxg.git
cd syxg

# Set up development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,audio,performance,visualization]"

# Run tests to verify setup
pytest

# Check that everything works
render-midi --help
```

## 🛠️ Development Setup

### Environment Configuration

Create a `.env` file for local development settings:

```bash
# Development settings
XG_SYNTH_DEBUG=1
XG_SYNTH_LOG_LEVEL=DEBUG
XG_SYNTH_SAMPLE_DIR=./samples
XG_SYNTH_CACHE_DIR=./cache

# Test settings
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
PYTEST_PLUGINS=pytest_cov,pytest_xdist
```

### IDE Setup

#### VS Code (Recommended)
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm
- Set Python interpreter to the virtual environment
- Enable Flake8 and MyPy inspections
- Configure Black as the code formatter

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
pip install pre-commit
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 📝 Contributing Guidelines

### Code Style

This project uses:

- **Black** for code formatting (line length: 88 characters)
- **Flake8** for linting
- **MyPy** for type checking
- **isort** for import sorting

```bash
# Format code
black synth/ tests/

# Check linting
flake8 synth/ tests/

# Type checking
mypy synth/

# Sort imports
isort synth/ tests/
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing changes
- `chore`: Maintenance tasks

Examples:
```
feat(synthesis): add FM-X algorithm support
fix(audio): resolve buffer overflow in real-time rendering
docs(api): update parameter descriptions
```

### Branch Naming

Use descriptive branch names:

```
feature/fm-x-algorithms
bugfix/audio-crackling
docs/api-reference
refactor/engine-architecture
```

## 🔄 Development Workflow

### 1. Choose an Issue

- Check [GitHub Issues](https://github.com/drbye78/syxg/issues) for open tasks
- Look for `good first issue` or `help wanted` labels
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b bugfix/issue-description
```

### 3. Make Changes

```bash
# Write tests first (TDD approach)
# Implement your changes
# Run tests frequently

# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new synthesis feature

- Implement algorithm X
- Add parameter validation
- Update documentation
"
```

### 4. Test Your Changes

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Test specific functionality
python -c "
# Quick test of your changes
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
# ... your test code
"
```

### 5. Update Documentation

```bash
# Update relevant documentation
# Add docstrings to new functions
# Update user guides if needed
```

### 6. Submit a Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request on GitHub
# Fill out the PR template
# Link to the issue it resolves
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=synth --cov-report=html

# Run specific test file
pytest tests/test_synthesis_engine.py

# Run tests matching pattern
pytest -k "test_fm" -v

# Run integration tests
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

### Writing Tests

#### Unit Tests
```python
# tests/test_your_feature.py
import pytest
from synth.your_module import YourClass

class TestYourFeature:
    def test_basic_functionality(self):
        """Test basic feature operation."""
        obj = YourClass()
        result = obj.do_something()
        assert result == expected_value

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        obj = YourClass()
        with pytest.raises(ValueError):
            obj.do_something(invalid_input)

    def test_performance(self):
        """Test performance requirements."""
        import time
        start = time.time()
        # ... perform operation
        duration = time.time() - start
        assert duration < 0.1  # Must complete in < 100ms
```

#### Integration Tests
```python
# tests/integration/test_audio_rendering.py
import pytest
import numpy as np
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

class TestAudioRendering:
    def test_full_render_pipeline(self):
        """Test complete MIDI to audio rendering."""
        synth = ModernXGSynthesizer()

        # Load configuration
        synth.load_xgml_config("examples/simple_piano.xgdsl")

        # Render audio
        audio = synth.render_midi_file("test.mid", "output.wav")

        # Verify output
        assert audio is not None
        assert len(audio) > 0
        assert audio.dtype == np.float32
        assert audio.shape[1] == 2  # Stereo

    def test_realtime_performance(self):
        """Test real-time rendering performance."""
        synth = ModernXGSynthesizer(real_time=True)

        # Measure latency
        start_time = time.time()
        audio = synth.generate_audio(1024)
        end_time = time.time()

        latency = end_time - start_time
        assert latency < 0.01  # Less than 10ms latency
```

### Test Coverage

Maintain test coverage above 80%:

```bash
# Check coverage
pytest --cov=synth --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=synth --cov-report=html
# Open htmlcov/index.html in browser
```

## 📚 Documentation

### Documentation Standards

- Use **Google-style docstrings** for all public functions
- Include **type hints** for function parameters and return values
- Provide **usage examples** in docstrings
- Keep **documentation current** with code changes

```python
def render_midi_file(
    self,
    midi_file: Union[str, Path],
    output_file: Union[str, Path],
    sample_rate: Optional[int] = None,
    normalize: bool = True
) -> bool:
    """Render MIDI file to audio.

    Args:
        midi_file: Path to input MIDI file
        output_file: Path to output audio file
        sample_rate: Audio sample rate (uses instance rate if None)
        normalize: Whether to normalize audio to prevent clipping

    Returns:
        True if rendering succeeded, False otherwise

    Raises:
        FileNotFoundError: If MIDI file doesn't exist
        AudioError: If audio rendering fails

    Example:
        >>> synth = ModernXGSynthesizer()
        >>> synth.render_midi_file("input.mid", "output.wav")
        True
    """
```

### Updating Documentation

```bash
# Update API documentation
# Edit relevant .md files in docs/
# Update examples if needed
# Test documentation builds
```

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Clear title** describing the issue
2. **Steps to reproduce** the problem
3. **Expected vs. actual behavior**
4. **Environment information**:
   - OS and version
   - Python version
   - XG Synthesizer version
   - Audio hardware/software
5. **Error messages** and stack traces
6. **Minimal test case** that reproduces the issue

### Example Bug Report

```
Title: Audio crackling during real-time playback

Description:
When using real-time synthesis, occasional crackling/popping sounds occur.

Steps to reproduce:
1. Create ModernXGSynthesizer(real_time=True)
2. Load complex XGML configuration
3. Play sustained notes for 30+ seconds
4. Crackling starts after ~10 seconds

Expected behavior:
Clean, uninterrupted audio playback

Actual behavior:
Intermittent crackling/popping sounds

Environment:
- OS: Ubuntu 22.04
- Python: 3.9.7
- XG Synthesizer: 1.0.0
- Audio: ALSA, 48kHz

Additional info:
CPU usage spikes to 80% during crackling
```

## 💡 Feature Requests

### Submitting Feature Requests

1. **Check existing issues** to avoid duplicates
2. **Use clear, descriptive titles**
3. **Provide detailed description**:
   - What problem does this solve?
   - How would it work?
   - Why is it valuable?
4. **Include examples** or mockups if applicable
5. **Consider backward compatibility**

### Feature Request Template

```
Title: Add granular synthesis engine

Description:
Implement a granular synthesis engine for creating cloud-like textures and experimental sounds.

Problem:
Current synthesis engines don't support granular techniques used in modern sound design.

Proposed Solution:
Add GranularEngine class with parameters for:
- Grain size and overlap
- Grain envelope shapes
- Playback direction (forward/backward)
- Density control
- Position randomization

Benefits:
- Enable new creative sound design possibilities
- Support modern experimental music techniques
- Complement existing synthesis engines

Compatibility:
- Maintains backward compatibility
- Uses existing XGML configuration framework
- Integrates with current effects system

Implementation Notes:
- Use efficient grain scheduling
- Support real-time parameter changes
- Include presets for common granular effects
```

## 🎯 Development Priorities

### High Priority
- **Bug fixes** and stability improvements
- **Performance optimizations**
- **API stability** and backward compatibility
- **Documentation completeness**

### Medium Priority
- **New synthesis engines** (granular, wavetable, physical modeling)
- **Advanced effects** (convolution reverb, spectral processing)
- **MPE support** enhancements
- **Real-time performance** improvements

### Low Priority
- **GUI interfaces** (web, desktop)
- **Plugin formats** (VST, AU)
- **Alternative audio backends**
- **Mobile platform support**

## 🤝 Recognition

Contributors are recognized through:

- **GitHub contributor list**
- **Changelog entries**
- **Documentation credits**
- **Community acknowledgments**

### Becoming a Core Contributor

Core contributors demonstrate:
- **Consistent quality** contributions
- **Community engagement** and support
- **Code review** participation
- **Documentation** improvements
- **Testing** and quality assurance

---

**Thank you for contributing to XG Synthesizer! Your efforts help make professional audio synthesis accessible to everyone.**
