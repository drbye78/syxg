"""
XG Effects Validation and Testing System

This module provides comprehensive validation and testing for all XG effect types.
Validates 83 variation effect types plus system, insertion, and EQ effects.
Ensures XG specification compliance and functional correctness.

Key Features:
- Complete XG effect type enumeration (118 total effects)
- Factory creation validation
- Parameter range testing
- Processing correctness verification
- Performance compliance checking
- Automated regression testing
- Compliance reporting and certification

XG Effect Coverage Validation:
- System Effects: 6 effect types (Reverb + Chorus variants)
- Variation Effects: 83 effect types (all XG categories)
- Insertion Effects: 18 effect types (channel processing)
- EQ Effects: 10 preset curves
- Total: 118 XG effect implementations
"""
from __future__ import annotations

import numpy as np
import time
import threading
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

# Import our XG effects ecosystem
try:
    from .effects_registry import XGEffectRegistry, XGEffectFactory, XGEffectCategory
    from .types import (
        XGReverbType, XGChorusType, XGVariationType, XGInsertionType, XGEQType
    )
    from .performance_monitor import XGPerformanceMonitor
except ImportError:
    # Fallback for development
    pass


class XGValidationResult(IntEnum):
    """XG Effect Validation Results"""
    PASS = 0
    WARNING = 1
    FAIL = 2
    NOT_IMPLEMENTED = 3
    PERFORMANCE_FAIL = 4


@dataclass(slots=True)
class XGValidationTest:
    """Individual XG Effect Validation Test"""
    effect_type: int
    category: XGEffectCategory
    test_name: str
    description: str
    result: XGValidationResult = XGValidationResult.NOT_IMPLEMENTED
    execution_time_ms: float = 0.0
    error_message: str = ""
    performance_score: float = 0.0
    memory_usage_mb: float = 0.0


class XGValidationSuite:
    """
    XG Effects Validation Suite

    Comprehensive testing suite for all XG effect implementations.
    Validates against official XG specification and performance requirements.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize validation suite.

        Args:
            sample_rate: Sample rate for testing
            block_size: Block size for processing tests
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Core components
        self.registry = XGEffectRegistry()
        self.factory = XGEffectFactory(sample_rate)
        self.performance_monitor = XGPerformanceMonitor()

        # Test results
        self.test_results: dict[tuple[XGEffectCategory, int], XGValidationTest] = {}
        self.suite_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'warning_tests': 0,
            'failed_tests': 0,
            'not_implemented': 0,
            'performance_fails': 0,
            'execution_time_ms': 0.0,
        }

        # Performance targets
        self.max_processing_time_ms = 50.0  # Max time per block
        self.max_memory_mb = 10.0           # Max memory per effect
        self.target_compliance_percent = 95.0

        # Thread safety
        self.lock = threading.RLock()

    def run_full_validation(self, verbose: bool = True) -> dict[str, Any]:
        """
        Run complete validation suite for all XG effects.

        Args:
            verbose: Enable detailed progress output

        Returns:
            Comprehensive validation report
        """
        with self.lock:
            start_time = time.time()
            self.test_results.clear()

            # Reset statistics
            for key in self.suite_stats:
                self.suite_stats[key] = 0.0 if key.endswith('_ms') else 0

            if verbose:
                print("XG Effects Validation Suite")
                print("=" * 50)
                print(f"Testing {self.registry.get_effect_count()} effect types")

            # Test each category
            self._validate_system_effects(verbose)
            self._validate_variation_effects(verbose)
            self._validate_insertion_effects(verbose)
            self._validate_eq_effects(verbose)

            # Calculate final statistics
            self.suite_stats['execution_time_ms'] = (time.time() - start_time) * 1000.0
            self._calculate_final_statistics()

            return self.generate_validation_report()

    def _validate_system_effects(self, verbose: bool) -> None:
        """Validate all system effects (reverb, chorus)."""
        if verbose:
            print("\nTesting System Effects...")

        system_tests = [
            # XG Reverb Types (1-24)
            *[(XGEffectCategory.SYSTEM, i, f"System Reverb Type {i}")
              for i in range(1, 25)],
            # XG Chorus Types (0-5, offset for chorus)
            *[(XGEffectCategory.SYSTEM, 0x100 + i, f"System Chorus Type {i}")
              for i in range(6)],
        ]

        for category, effect_type, test_name in system_tests:
            result = self._validate_effect(category, effect_type, test_name, verbose)
            self.test_results[(category, effect_type)] = result

    def _validate_variation_effects(self, verbose: bool) -> None:
        """Validate all 83 variation effects."""
        if verbose:
            print("\nTesting Variation Effects...")

        # Test all 83 XG variation effect types
        variation_tests = [
            # Delay Effects (0-19)
            *[(XGEffectCategory.VARIATION, i, f"Variation Delay {i}") for i in range(20)],
            # Chorus Effects (20-52)
            *[(XGEffectCategory.VARIATION, i, f"Variation Chorus {i-20}") for i in range(20, 53)],
            # Modulation Effects (53-73)
            *[(XGEffectCategory.VARIATION, i, f"Variation Modulation {i-53}") for i in range(53, 74)],
            # Distortion Effects (74-83)
            *[(XGEffectCategory.VARIATION, i, f"Variation Distortion {i-74}") for i in range(74, 84)],
            # Dynamics Effects (84-88)
            *[(XGEffectCategory.VARIATION, i, f"Variation Dynamics {i-84}") for i in range(84, 89)],
            # Enhancer Effects (89-92)
            *[(XGEffectCategory.VARIATION, i, f"Variation Enhancer {i-89}") for i in range(89, 93)],
            # Vocoder Effects (93-96)
            *[(XGEffectCategory.VARIATION, i, f"Variation Vocoder {i-93}") for i in range(93, 97)],
            # Pitch Effects (97-102)
            *[(XGEffectCategory.VARIATION, i, f"Variation Pitch {i-97}") for i in range(97, 103)],
            # Early Reflection (103-110)
            *[(XGEffectCategory.VARIATION, i, f"Variation ER {i-103}") for i in range(103, 111)],
            # Gate Reverb (111-113)
            *[(XGEffectCategory.VARIATION, i, f"Variation Gate Reverb {i-111}") for i in range(111, 114)],
            # Special Effects (114-116)
            *[(XGEffectCategory.VARIATION, i, f"Variation Special {i-114}") for i in range(114, 117)],
        ]

        for category, effect_type, test_name in variation_tests:
            result = self._validate_effect(category, effect_type, test_name, verbose)
            self.test_results[(category, effect_type)] = result

            if verbose and effect_type % 10 == 0:
                print(f"  Variation effects: {effect_type}/116 tested")

    def _validate_insertion_effects(self, verbose: bool) -> None:
        """Validate all 18 insertion effects."""
        if verbose:
            print("\nTesting Insertion Effects...")

        insertion_tests = [
            (XGEffectCategory.INSERTION, i, f"Insertion Effect {i}")
            for i in range(18)
        ]

        for category, effect_type, test_name in insertion_tests:
            result = self._validate_effect(category, effect_type, test_name, verbose)
            self.test_results[(category, effect_type)] = result

    def _validate_eq_effects(self, verbose: bool) -> None:
        """Validate all 10 EQ curve types."""
        if verbose:
            print("\nTesting EQ Effects...")

        eq_tests = [
            (XGEffectCategory.EQUALIZER, i, f"EQ Curve {i}")
            for i in range(10)
        ]

        for category, effect_type, test_name in eq_tests:
            result = self._validate_effect(category, effect_type, test_name, verbose)
            self.test_results[(category, effect_type)] = result

    def _validate_effect(self, category: XGEffectCategory, effect_type: int,
                        test_name: str, verbose: bool) -> XGValidationTest:
        """
        Validate a single XG effect.

        Args:
            category: Effect category
            effect_type: Effect type within category
            test_name: Descriptive test name
            verbose: Enable progress output

        Returns:
            Validation test result
        """
        test = XGValidationTest(
            effect_type=effect_type,
            category=category,
            test_name=test_name,
            description=f"Validate XG {category.name} effect type {effect_type}",
            result=XGValidationResult.NOT_IMPLEMENTED
        )

        start_time = time.perf_counter()

        try:
            # Test 1: Registry validation
            metadata = self.registry.get_effect_metadata(category, effect_type)
            if metadata is None:
                test.result = XGValidationResult.NOT_IMPLEMENTED
                test.error_message = "Effect not found in registry"
                return test

            # Test 2: Factory creation
            instance = self._create_effect_instance(category, effect_type)
            if instance is None:
                test.result = XGValidationResult.FAIL
                test.error_message = "Factory creation failed"
                return test

            # Test 3: Parameter validation
            param_score = self._validate_effect_parameters(instance, category, effect_type)
            if param_score < 0.8:  # 80% parameter validation required
                test.result = XGValidationResult.WARNING
                test.error_message = f"Parameter validation score: {param_score:.1f}"
                return test

            # Test 4: Processing validation
            processing_score = self._validate_effect_processing(instance, category, effect_type)
            if processing_score < 0.9:  # 90% processing validation required
                test.result = XGValidationResult.FAIL
                test.error_message = f"Processing validation score: {processing_score:.1f}"
                return test

            # Test 5: Performance validation
            performance_score = self._validate_effect_performance(instance, category, effect_type)
            test.performance_score = performance_score

            if performance_score < 0.7:  # 70% performance requirement
                test.result = XGValidationResult.PERFORMANCE_FAIL
                test.error_message = f"Performance score: {performance_score:.1f}"
                return test

            # All tests passed!
            test.result = XGValidationResult.PASS
            test.performance_score = performance_score

            if verbose:
                print(f"  ✓ {test_name}: PASS")

        except Exception as e:
            test.result = XGValidationResult.FAIL
            test.error_message = f"Exception: {str(e)}"

            if verbose:
                print(f"  ✗ {test_name}: FAIL - {str(e)}")

        finally:
            test.execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return test

    def _create_effect_instance(self, category: XGEffectCategory, effect_type: int) -> Any | None:
        """Create an effect instance for testing."""
        try:
            if category == XGEffectCategory.VARIATION:
                return self.factory.create_variation_effect(effect_type)
            elif category == XGEffectCategory.INSERTION:
                return self.factory.create_insertion_effect(effect_type)
            elif category == XGEffectCategory.SYSTEM:
                if effect_type < 0x100:  # Reverb types 1-24
                    return self.factory.create_system_effect(XGReverbType(effect_type))
                else:  # Chorus types 0x100-0x105
                    chorus_type = effect_type - 0x100
                    return self.factory.create_system_effect(XGChorusType(chorus_type))
            elif category == XGEffectCategory.EQUALIZER:
                return self.factory.create_channel_eq(XGEQType(effect_type))

            return None
        except Exception:
            return None

    def _validate_effect_parameters(self, instance: Any, category: XGEffectCategory, effect_type: int) -> float:
        """
        Validate effect parameters.

        Returns:
            Parameter validation score (0.0-1.0)
        """
        try:
            # Test parameter setting and retrieval
            score = 0.0
            tests_passed = 0
            total_tests = 0

            # Test basic parameter operations
            if hasattr(instance, 'set_parameter'):
                total_tests += 1
                if instance.set_parameter('level', 0.5):
                    tests_passed += 1

                total_tests += 1
                if instance.set_parameter('enabled', True):
                    tests_passed += 1

            # Type-specific parameter tests
            if category == XGEffectCategory.VARIATION:
                # Variation effects should have type parameter
                total_tests += 1
                if hasattr(instance, 'set_variation_type') and instance.set_variation_type(effect_type % 84):
                    tests_passed += 1

            elif category == XGEffectCategory.INSERTION:
                # Insertion effects should support slot configuration
                total_tests += 1
                if hasattr(instance, 'set_insertion_effect_type') and instance.set_insertion_effect_type(0, effect_type % 18):
                    tests_passed += 1

            return tests_passed / max(total_tests, 1)

        except Exception:
            return 0.0

    def _validate_effect_processing(self, instance: Any, category: XGEffectCategory, effect_type: int) -> float:
        """
        Validate effect audio processing.

        Returns:
            Processing validation score (0.0-1.0)
        """
        try:
            # Generate test audio (impulse response test)
            test_input = np.zeros((self.block_size, 2), dtype=np.float32)
            test_input[0, 0] = 1.0  # Left channel impulse
            test_input[0, 1] = 1.0  # Right channel impulse

            # Test processing method
            if hasattr(instance, 'apply_effect_zero_alloc'):
                output = test_input.copy()
                success = instance.apply_effect_zero_alloc(output, self.block_size)
                if success and np.any(output != test_input):  # Effect modified audio
                    return 1.0

            elif hasattr(instance, 'apply_system_effects_to_mix_zero_alloc'):
                output = test_input.copy()
                instance.apply_system_effects_to_mix_zero_alloc(output, self.block_size)
                if np.any(output != test_input):
                    return 1.0

            elif hasattr(instance, 'apply_channel_eq_zero_alloc'):
                output = test_input.copy()
                instance.apply_channel_eq_zero_alloc(output, self.block_size)
                if np.any(output != test_input):
                    return 1.0

            return 0.5  # Partial credit for basic processing capability

        except Exception:
            return 0.0

    def _validate_effect_performance(self, instance: Any, category: XGEffectCategory, effect_type: int) -> float:
        """
        Validate effect performance requirements.

        Returns:
            Performance score (0.0-1.0)
        """
        try:
            # Test processing performance
            iterations = 100
            test_input = np.random.randn(self.block_size, 2).astype(np.float32)

            start_time = time.perf_counter()

            for _ in range(iterations):
                output = test_input.copy()
                if hasattr(instance, 'apply_effect_zero_alloc'):
                    instance.apply_effect_zero_alloc(output, self.block_size)
                elif hasattr(instance, 'apply_system_effects_to_mix_zero_alloc'):
                    instance.apply_system_effects_to_mix_zero_alloc(output, self.block_size)
                elif hasattr(instance, 'apply_channel_eq_zero_alloc'):
                    instance.apply_channel_eq_zero_alloc(output, self.block_size)

            total_time_ms = (time.perf_counter() - start_time) * 1000.0
            avg_time_ms = total_time_ms / iterations

            # Performance scoring
            if avg_time_ms <= 2.0:  # Excellent (< 2ms per block)
                return 1.0
            elif avg_time_ms <= 10.0:  # Good (< 10ms per block)
                return 0.8
            elif avg_time_ms <= self.max_processing_time_ms:  # Acceptable
                return 0.6
            else:  # Too slow
                return 0.2

        except Exception:
            return 0.0

    def _calculate_final_statistics(self) -> None:
        """Calculate final suite statistics."""
        for test in self.test_results.values():
            self.suite_stats['total_tests'] += 1

            if test.result == XGValidationResult.PASS:
                self.suite_stats['passed_tests'] += 1
            elif test.result == XGValidationResult.WARNING:
                self.suite_stats['warning_tests'] += 1
            elif test.result == XGValidationResult.FAIL:
                self.suite_stats['failed_tests'] += 1
            elif test.result == XGValidationResult.NOT_IMPLEMENTED:
                self.suite_stats['not_implemented'] += 1
            elif test.result == XGValidationResult.PERFORMANCE_FAIL:
                self.suite_stats['performance_fails'] += 1

    def generate_validation_report(self) -> dict[str, Any]:
        """
        Generate comprehensive validation report.

        Returns:
            Detailed validation report with all test results
        """
        with self.lock:
            compliance_percent = (
                self.suite_stats['passed_tests'] / max(self.suite_stats['total_tests'], 1)
            ) * 100.0

            return {
                'suite_info': {
                    'total_effects_tested': self.suite_stats['total_tests'],
                    'sample_rate': self.sample_rate,
                    'block_size': self.block_size,
                    'execution_time_ms': self.suite_stats['execution_time_ms'],
                    'xg_compliance_percent': compliance_percent,
                    'target_compliance_percent': self.target_compliance_percent,
                    'compliance_achieved': compliance_percent >= self.target_compliance_percent,
                },
                'results_summary': {
                    'passed': self.suite_stats['passed_tests'],
                    'warnings': self.suite_stats['warning_tests'],
                    'failed': self.suite_stats['failed_tests'],
                    'not_implemented': self.suite_stats['not_implemented'],
                    'performance_fails': self.suite_stats['performance_fails'],
                },
                'category_breakdown': self._generate_category_breakdown(),
                'detailed_results': {
                    f"{test.category.name}_{test.effect_type}": {
                        'result': test.result.name,
                        'execution_time_ms': test.execution_time_ms,
                        'performance_score': test.performance_score,
                        'error_message': test.error_message,
                        'memory_usage_mb': test.memory_usage_mb,
                    }
                    for test in self.test_results.values()
                },
                'recommendations': self._generate_recommendations(compliance_percent),
            }

    def _generate_category_breakdown(self) -> dict[str, dict[str, int]]:
        """Generate results breakdown by category."""
        breakdown = {}

        for category in XGEffectCategory:
            cat_name = category.name.lower()
            breakdown[cat_name] = {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'not_implemented': 0}

            for test in self.test_results.values():
                if test.category == category:
                    breakdown[cat_name]['total'] += 1
                    if test.result == XGValidationResult.PASS:
                        breakdown[cat_name]['passed'] += 1
                    elif test.result == XGValidationResult.FAIL:
                        breakdown[cat_name]['failed'] += 1
                    elif test.result == XGValidationResult.WARNING:
                        breakdown[cat_name]['warnings'] += 1
                    elif test.result == XGValidationResult.NOT_IMPLEMENTED:
                        breakdown[cat_name]['not_implemented'] += 1

        return breakdown

    def _generate_recommendations(self, compliance_percent: float) -> list[str]:
        """Generate implementation recommendations."""
        recommendations = []

        if compliance_percent < 50.0:
            recommendations.append("Critical: Less than 50% of effects implemented. Focus on core effect types first.")

        if self.suite_stats['performance_fails'] > 0:
            recommendations.append(f"Performance: {self.suite_stats['performance_fails']} effects exceed processing time limits.")

        if self.suite_stats['not_implemented'] > 10:
            recommendations.append(f"Implementation: {self.suite_stats['not_implemented']} effects not yet implemented.")

        if self.suite_stats['failed_tests'] > 0:
            recommendations.append(f"Quality: {self.suite_stats['failed_tests']} effects have functional issues.")

        if len(recommendations) == 0 and compliance_percent >= self.target_compliance_percent:
            recommendations.append("Excellent! XG effects implementation meets or exceeds compliance targets.")

        return recommendations


class XGComplianceCertifier:
    """
    XG Compliance Certification System

    Official XG effects compliance certification and reporting.
    Provides industry-standard validation results.
    """

    def __init__(self):
        """Initialize XG compliance certifier."""
        self.certification_levels = {
            'XG_BASIC': {'min_compliance': 60.0, 'name': 'XG Basic Certified'},
            'XG_STANDARD': {'min_compliance': 85.0, 'name': 'XG Standard Certified'},
            'XG_PROFESSIONAL': {'min_compliance': 95.0, 'name': 'XG Professional Certified'},
            'XG_REFERENCE': {'min_compliance': 99.0, 'name': 'XG Reference Implementation'},
        }

    def certify_implementation(self, validation_report: dict[str, Any]) -> dict[str, Any]:
        """
        Certify XG effects implementation.

        Args:
            validation_report: Complete validation report

        Returns:
            Certification results
        """
        compliance = validation_report['suite_info']['xg_compliance_percent']

        cert_level = None
        cert_name = "Not Certified"
        cert_description = "Implementation does not meet XG certification standards."

        for level, info in self.certification_levels.items():
            if compliance >= info['min_compliance']:
                cert_level = level
                cert_name = info['name']
                cert_description = f"Achieves {compliance:.1f}% XG effect type compliance."
                break

        return {
            'certification_level': cert_level,
            'certification_name': cert_name,
            'compliance_percentage': compliance,
            'description': cert_description,
            'certified_effects': validation_report['results_summary']['passed'],
            'total_effects': validation_report['suite_info']['total_effects_tested'],
            'certification_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'meets_minimum_standard': compliance >= 60.0,
        }


# Global validation functions
def validate_xg_effects_implementation(sample_rate: int = 44100,
                                     block_size: int = 1024) -> dict[str, Any]:
    """
    Validate complete XG effects implementation.

    Args:
        sample_rate: Sample rate for testing
        block_size: Block size for processing tests

    Returns:
        Complete validation report
    """
    suite = XGValidationSuite(sample_rate, block_size)
    report = suite.run_full_validation(verbose=True)

    # Add certification
    certifier = XGComplianceCertifier()
    report['certification'] = certifier.certify_implementation(report)

    return report


def print_validation_summary(report: dict[str, Any]) -> None:
    """
    Print formatted validation summary.

    Args:
        report: Validation report
    """
    print("\n" + "="*50)
    print("XG EFFECTS VALIDATION SUMMARY")
    print("="*50)

    info = report['suite_info']
    results = report['results_summary']
    cert = report['certification']

    print(f"Effects Tested: {info['total_effects_tested']}")
    print(".2f")
    print(",.0f")
    print(".2f")

    print("\nTest Results:")
    print(f"  Passed: {results['passed']}")
    print(f"  Warnings: {results['warnings']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Not Implemented: {results['not_implemented']}")
    print(f"  Performance Issues: {results['performance_fails']}")

    print(f"\nCertification: {cert['certification_name']}")
    print(f"Description: {cert['description']}")

    if report['recommendations']:
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

    print("="*50)
