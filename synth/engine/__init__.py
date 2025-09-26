"""
SYNTHESIS ENGINE PACKAGE

This package contains the core synthesis engine components:
- OptimizedXGSynthesizer: Main XG synthesizer implementation with high-performance processing
- OptimizedCoefficientManager: Performance optimization components for real-time synthesis
"""

from .optimized_xg_synthesizer import OptimizedXGSynthesizer
from .optimized_coefficient_manager import OptimizedCoefficientManager, get_global_coefficient_manager

__all__ = [
    'OptimizedXGSynthesizer',
    'OptimizedCoefficientManager',
    'get_global_coefficient_manager'
]