"""
Synthesis Engine Package

This package contains the synthesis engine components:
- optimized_xg_synthesizer: Main XG synthesizer implementation
- optimized_coefficient_manager: Performance optimization components
"""

from .optimized_xg_synthesizer import OptimizedXGSynthesizer
from .optimized_coefficient_manager import OptimizedCoefficientManager, get_global_coefficient_manager

__all__ = [
    'OptimizedXGSynthesizer',
    'OptimizedCoefficientManager',
    'get_global_coefficient_manager'
]