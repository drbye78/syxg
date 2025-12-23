from setuptools import setup, find_packages
import os
from synth.version import __version__

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(this_directory, 'README.md')
long_description = ''
try:
    if os.path.exists(readme_path):
        with open(readme_path, encoding='utf-8') as f:
            long_description = f.read()
except (OSError, IOError) as e:
    print(f"Warning: Could not read README.md: {e}")

# Read requirements from requirements.txt
requirements_path = os.path.join(this_directory, 'requirements.txt')
install_requires = []
try:
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    install_requires.append(line)
except (OSError, IOError) as e:
    print(f"Warning: Could not read requirements.txt: {e}")

setup(
    name='xg-synthesizer',
    version=__version__,
    author='Roger',
    author_email='roger@syxg.dev',
    description='High-performance MIDI XG (eXtended General MIDI) '
                'synthesizer implemented in Python with optimized '
                'vectorized processing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/roger/syxg',
    license='MIT',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: MIDI',
        'Topic :: Multimedia :: Sound/Audio :: Sound Synthesis',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=install_requires,
    tests_require=[
        'pytest>=6.0',
        'pytest-cov>=2.10.1',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.10.1',
            'black>=21.0.0',
            'flake8>=3.8.0',
            'mypy>=0.812',
            'cython>=0.29.0',
        ],
        'performance': [
            'numba>=0.56.0',
        ],
        'audio': [
            'pydub>=0.25.1',
            'librosa>=0.9.0',
            'soundfile>=0.10.3',
            'av>=9.0.0',
        ],
        'visualization': [
            'matplotlib>=3.3.0',
            'seaborn>=0.11.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'render-midi = render_midi:main',
        ],
    },
    keywords=['audio', 'synthesizer', 'midi', 'xg', 'soundfont', 'sf2'],
    project_urls={
        'Bug Reports': 'https://github.com/roger/syxg/issues',
        'Source': 'https://github.com/roger/syxg',
    },
    include_package_data=True,
    zip_safe=False,
)
