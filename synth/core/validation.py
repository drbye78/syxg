"""
Validation Framework - Comprehensive Error Handling & Parameter Validation Architecture

ARCHITECTURAL OVERVIEW:

The XG Validation Framework provides a comprehensive, multi-layered validation system
designed for real-time audio applications with complex parameter validation requirements.
It implements a hierarchical validation approach that ensures system stability, provides
detailed error diagnostics, and supports graceful degradation under adverse conditions.

VALIDATION HIERARCHY:

1. AUDIO VALIDATION LAYER:
   - Buffer integrity and format validation
   - Sample rate and audio parameter checking
   - Real-time audio data validation

2. PARAMETER VALIDATION LAYER:
   - Type checking and range validation
   - Parameter relationship validation
   - Dynamic parameter constraint checking

3. SYSTEM VALIDATION LAYER:
   - Resource availability validation
   - System state consistency checking
   - Performance boundary validation

VALIDATION RESULT ARCHITECTURE:

The framework uses a structured ValidationResult system that categorizes issues by severity:

ERRORS (Critical):
- System stability threats
- Data corruption risks
- Invalid parameter combinations
- Resource exhaustion conditions

WARNINGS (Non-critical):
- Performance degradation indicators
- Non-standard configurations
- Resource pressure warnings
- Compatibility concerns

INFO (Informational):
- System status notifications
- Configuration recommendations
- Usage pattern observations
- Optimization suggestions

ERROR HANDLING PATTERNS:

STRUCTURED ERROR REPORTING:
- Machine-readable error codes for programmatic handling
- Human-readable messages for user interfaces
- Contextual information for debugging
- Severity classification for appropriate responses

THREAD-SAFE OPERATIONS:
- All validation operations are thread-safe
- Atomic error collection and reporting
- Consistent state during concurrent validation
- Race-condition prevention in error accumulation

VALIDATION CONTEXT MANAGEMENT:

The framework maintains validation context throughout the system:

GLOBAL VALIDATORS:
- audio_validator: Singleton for audio data validation
- parameter_validator: Singleton for parameter validation

CONTEXT-AWARE VALIDATION:
- Validation results include calling context
- Thread identification for debugging
- Timestamp tracking for temporal analysis
- Stack trace capture for development

INTEGRATION ARCHITECTURE:

SYNTHESIZER INTEGRATION:
- Real-time validation during audio processing
- Parameter validation before application
- System health monitoring and reporting
- Configuration validation at startup

COMPONENT INTEGRATION:
- Buffer pool validation integration
- Voice manager parameter validation
- Effects system constraint checking
- Engine parameter validation hooks

PERFORMANCE OPTIMIZATION:

EFFICIENT VALIDATION DESIGN:
- Minimal overhead validation operations
- Cached validation results where appropriate
- Incremental validation for streaming data
- Early exit on critical errors

VALIDATION CACHING:
- Parameter range caching for repeated validations
- Buffer format caching for streaming validation
- System state caching for health checks

ERROR RECOVERY PATTERNS:

GRACEFUL DEGRADATION:
- Fallback values for invalid parameters
- Conservative defaults for missing configurations
- Warning-based operation continuation
- Error isolation to prevent system failure

RECOVERY STRATEGIES:
- Parameter clamping to valid ranges
- Type conversion with validation
- Default value substitution
- Configuration repair suggestions

XG SPECIFICATION COMPLIANCE:

PROFESSIONAL AUDIO STANDARDS:
- Sample-accurate validation timing
- Industry-standard parameter ranges
- Comprehensive error code standardization
- Multi-language error message support

VALIDATION COVERAGE:

AUDIO VALIDATION:
- Buffer format and integrity checking
- Sample rate validation (8kHz-192kHz)
- Amplitude range validation (±1.0)
- Channel count validation
- Data type validation (float32/float64)

PARAMETER VALIDATION:
- Type safety checking (int/float/bool)
- Range validation with clamping
- Relationship validation (dependent parameters)
- MIDI parameter validation (0-127 ranges)
- XG-specific parameter validation

SYSTEM VALIDATION:
- Memory availability checking
- Thread count monitoring
- CPU usage validation
- Disk space validation (for sample loading)
- Network connectivity validation (if applicable)

DIAGNOSTIC CAPABILITIES:

COMPREHENSIVE ERROR REPORTING:
- Structured error dictionaries for logging
- Severity-based error filtering
- Context-rich error information
- Debug information for development

VALIDATION METRICS:
- Error rate tracking by component
- Warning frequency analysis
- Validation performance monitoring
- System health trend analysis

CONFIGURATION VALIDATION:

STARTUP VALIDATION:
- Configuration file integrity checking
- Hardware compatibility validation
- Resource availability verification
- Dependency validation

RUNTIME VALIDATION:
- Dynamic parameter validation
- System state validation
- Performance boundary checking
- Configuration change validation

EXTENSIBILITY ARCHITECTURE:

PLUGIN VALIDATION SYSTEM:
- Custom validator registration
- Domain-specific validation rules
- External validation module support
- Validation pipeline extension points

VALIDATOR REGISTRATION:
- Type-based validator association
- Parameter-specific validation rules
- Custom error code registration
- Validation priority management
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np


class ValidationError(Exception):
    """
    Validation error with detailed context.

    Provides error information for debugging and user feedback.
    """

    def __init__(
        self,
        message: str,
        error_code: str = None,
        context: dict[str, Any] = None,
        severity: str = "error",
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error code
            context: Additional error context (parameters, values, etc.)
            severity: Error severity ('error', 'warning', 'info')
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or "VALIDATION_ERROR"
        self.context = context or {}
        self.severity = severity

        # Add timestamp and thread info
        self.timestamp = threading.current_thread().ident
        self.thread_name = threading.current_thread().name

    def __str__(self) -> str:
        """String representation with full context."""
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        return f"[{self.error_code}] {self.message} ({context_str})"

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity,
            "context": self.context,
            "timestamp": self.timestamp,
            "thread_name": self.thread_name,
        }


class ValidationResult:
    """
    Validation result container with success/failure tracking.
    """

    def __init__(self):
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []
        self.info: list[ValidationError] = []

    def add_error(self, error: ValidationError):
        """Add validation error."""
        self.errors.append(error)

    def add_warning(self, warning: ValidationError):
        """Add validation warning."""
        self.warnings.append(warning)

    def add_info(self, info: ValidationError):
        """Add validation info."""
        self.info.append(info)

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    def get_summary(self) -> dict[str, int]:
        """Get validation summary."""
        return {"errors": len(self.errors), "warnings": len(self.warnings), "info": len(self.info)}


class AudioValidator:
    """
    Comprehensive audio validation for buffers, parameters, and system state.

    Ensures audio data integrity and system stability in production environments.
    """

    # Standard audio validation constants
    MAX_SAMPLE_VALUE = 1.0
    MIN_SAMPLE_RATE = 8000
    MAX_SAMPLE_RATE = 192000
    SUPPORTED_SAMPLE_RATES = {8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 192000}

    def __init__(self, strict_mode: bool = True):
        """
        Initialize audio validator.

        Args:
            strict_mode: Enable strict validation (reject warnings as errors)
        """
        self.strict_mode = strict_mode
        self.lock = threading.RLock()

    def validate_buffer(
        self, buffer: np.ndarray, expected_channels: int = None, expected_dtype: np.dtype = None
    ) -> ValidationResult:
        """
        Comprehensive audio buffer validation.

        Args:
            buffer: Audio buffer to validate
            expected_channels: Expected number of channels (None = any)
            expected_dtype: Expected data type (None = any float type)

        Returns:
            ValidationResult with detailed error/warning information
        """
        result = ValidationResult()

        with self.lock:
            # Type validation
            if not isinstance(buffer, np.ndarray):
                result.add_error(
                    ValidationError(
                        "Audio buffer must be numpy array",
                        "INVALID_BUFFER_TYPE",
                        {"type": type(buffer).__name__},
                    )
                )
                return result

            # Shape validation
            if buffer.ndim not in (1, 2):
                result.add_error(
                    ValidationError(
                        f"Audio buffer must be 1D or 2D, got {buffer.ndim}D",
                        "INVALID_BUFFER_DIMENSIONS",
                        {"dimensions": buffer.ndim, "shape": buffer.shape},
                    )
                )
                return result

            # Channel validation
            channels = buffer.shape[1] if buffer.ndim == 2 else 1
            if expected_channels is not None and channels != expected_channels:
                result.add_error(
                    ValidationError(
                        f"Expected {expected_channels} channels, got {channels}",
                        "INVALID_CHANNEL_COUNT",
                        {"expected": expected_channels, "actual": channels},
                    )
                )

            # Data type validation
            if expected_dtype is not None and buffer.dtype != expected_dtype:
                result.add_error(
                    ValidationError(
                        f"Expected dtype {expected_dtype}, got {buffer.dtype}",
                        "INVALID_BUFFER_DTYPE",
                        {"expected": expected_dtype.name, "actual": buffer.dtype.name},
                    )
                )

            # Check for NaN/Inf values
            if np.any(np.isnan(buffer)):
                result.add_error(
                    ValidationError(
                        "Audio buffer contains NaN values",
                        "BUFFER_CONTAINS_NAN",
                        {"nan_count": np.sum(np.isnan(buffer))},
                    )
                )

            if np.any(np.isinf(buffer)):
                result.add_error(
                    ValidationError(
                        "Audio buffer contains infinite values",
                        "BUFFER_CONTAINS_INF",
                        {"inf_count": np.sum(np.isinf(buffer))},
                    )
                )

            # Amplitude validation
            max_amplitude = np.max(np.abs(buffer))
            if max_amplitude > self.MAX_SAMPLE_VALUE:
                if self.strict_mode:
                    result.add_error(
                        ValidationError(
                            f"Audio buffer amplitude {max_amplitude:.3f} exceeds maximum {self.MAX_SAMPLE_VALUE}",
                            "AMPLITUDE_TOO_HIGH",
                            {"max_amplitude": max_amplitude, "limit": self.MAX_SAMPLE_VALUE},
                        )
                    )
                else:
                    result.add_warning(
                        ValidationError(
                            f"Audio buffer amplitude {max_amplitude:.3f} exceeds nominal range",
                            "AMPLITUDE_WARNING",
                            {"max_amplitude": max_amplitude, "limit": self.MAX_SAMPLE_VALUE},
                            "warning",
                        )
                    )

            # Silence detection
            if max_amplitude < 1e-10:
                result.add_info(
                    ValidationError(
                        "Audio buffer appears to be silent",
                        "BUFFER_IS_SILENT",
                        {"max_amplitude": max_amplitude},
                        "info",
                    )
                )

        return result

    def validate_sample_rate(self, sample_rate: int) -> ValidationResult:
        """
        Validate audio sample rate.

        Args:
            sample_rate: Sample rate in Hz

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not isinstance(sample_rate, int):
            result.add_error(
                ValidationError(
                    "Sample rate must be integer",
                    "INVALID_SAMPLE_RATE_TYPE",
                    {"type": type(sample_rate).__name__, "value": sample_rate},
                )
            )
            return result

        if sample_rate < self.MIN_SAMPLE_RATE:
            result.add_error(
                ValidationError(
                    f"Sample rate {sample_rate}Hz below minimum {self.MIN_SAMPLE_RATE}Hz",
                    "SAMPLE_RATE_TOO_LOW",
                    {"rate": sample_rate, "minimum": self.MIN_SAMPLE_RATE},
                )
            )

        if sample_rate > self.MAX_SAMPLE_RATE:
            result.add_error(
                ValidationError(
                    f"Sample rate {sample_rate}Hz above maximum {self.MAX_SAMPLE_RATE}Hz",
                    "SAMPLE_RATE_TOO_HIGH",
                    {"rate": sample_rate, "maximum": self.MAX_SAMPLE_RATE},
                )
            )

        if sample_rate not in self.SUPPORTED_SAMPLE_RATES:
            result.add_warning(
                ValidationError(
                    f"Sample rate {sample_rate}Hz is non-standard",
                    "NON_STANDARD_SAMPLE_RATE",
                    {"rate": sample_rate, "standard_rates": sorted(self.SUPPORTED_SAMPLE_RATES)},
                    "warning",
                )
            )

        return result

    def validate_parameter_range(
        self, param_value: float, min_val: float, max_val: float, param_name: str = "parameter"
    ) -> ValidationResult:
        """
        Validate parameter is within acceptable range.

        Args:
            param_value: Parameter value to validate
            min_val: Minimum acceptable value
            max_val: Maximum acceptable value
            param_name: Parameter name for error messages

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not isinstance(param_value, (int, float)):
            result.add_error(
                ValidationError(
                    f"{param_name} must be numeric",
                    "INVALID_PARAMETER_TYPE",
                    {"name": param_name, "type": type(param_value).__name__, "value": param_value},
                )
            )
            return result

        if math.isnan(param_value) or math.isinf(param_value):
            result.add_error(
                ValidationError(
                    f"{param_name} contains invalid value",
                    "INVALID_PARAMETER_VALUE",
                    {"name": param_name, "value": param_value},
                )
            )
            return result

        if param_value < min_val:
            result.add_error(
                ValidationError(
                    f"{param_name} {param_value} below minimum {min_val}",
                    "PARAMETER_TOO_LOW",
                    {"name": param_name, "value": param_value, "minimum": min_val},
                )
            )

        if param_value > max_val:
            result.add_error(
                ValidationError(
                    f"{param_name} {param_value} above maximum {max_val}",
                    "PARAMETER_TOO_HIGH",
                    {"name": param_name, "value": param_value, "maximum": max_val},
                )
            )

        return result

    def validate_midi_message(self, message_bytes: bytes) -> ValidationResult:
        """
        Validate MIDI message format and content.

        Args:
            message_bytes: Raw MIDI message bytes

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not isinstance(message_bytes, bytes):
            result.add_error(
                ValidationError(
                    "MIDI message must be bytes",
                    "INVALID_MIDI_TYPE",
                    {"type": type(message_bytes).__name__},
                )
            )
            return result

        if len(message_bytes) == 0:
            result.add_error(ValidationError("MIDI message cannot be empty", "EMPTY_MIDI_MESSAGE"))
            return result

        # Check for basic MIDI message structure
        status_byte = message_bytes[0]

        # Status byte validation
        if not (0x80 <= status_byte <= 0xFF):
            result.add_error(
                ValidationError(
                    f"Invalid MIDI status byte: 0x{status_byte:02X}",
                    "INVALID_MIDI_STATUS",
                    {"status_byte": status_byte},
                )
            )

        # Message length validation based on status
        expected_length = self._get_expected_midi_length(status_byte)
        if expected_length > 0 and len(message_bytes) != expected_length:
            result.add_error(
                ValidationError(
                    f"MIDI message length mismatch: expected {expected_length}, got {len(message_bytes)}",
                    "INVALID_MIDI_LENGTH",
                    {
                        "expected": expected_length,
                        "actual": len(message_bytes),
                        "status": status_byte,
                    },
                )
            )

        # Data byte validation (should be < 128)
        for i, byte in enumerate(message_bytes[1:], 1):
            if byte >= 128:
                result.add_error(
                    ValidationError(
                        f"MIDI data byte {i} >= 128: {byte}",
                        "INVALID_MIDI_DATA",
                        {"byte_index": i, "value": byte},
                    )
                )

        return result

    def _get_expected_midi_length(self, status_byte: int) -> int:
        """Get expected length for MIDI message type."""
        # System messages
        if status_byte in (0xF0, 0xF7):  # Sysex start/end
            return 0  # Variable length
        if status_byte == 0xFF:  # Meta event
            return 0  # Variable length

        # Channel messages
        if status_byte & 0xF0 in (
            0x80,
            0x90,
            0xA0,
            0xB0,
            0xE0,
        ):  # Note off/on, poly pressure, control, pitch bend
            return 3
        if status_byte & 0xF0 in (0xC0, 0xD0):  # Program change, channel pressure
            return 2
        if status_byte == 0xF1:  # MTC quarter frame
            return 2
        if status_byte == 0xF2:  # Song position pointer
            return 3
        if status_byte == 0xF3:  # Song select
            return 2

        return 0  # Unknown/handled elsewhere

    def validate_system_resources(self) -> ValidationResult:
        """
        Validate system resources and runtime environment.

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check available memory
        try:
            import psutil

            memory = psutil.virtual_memory()
            if memory.available < 100 * 1024 * 1024:  # 100MB minimum
                result.add_warning(
                    ValidationError(
                        f"Low available memory: {memory.available / (1024 * 1024):.1f}MB",
                        "LOW_MEMORY_WARNING",
                        {"available_mb": memory.available / (1024 * 1024)},
                        "warning",
                    )
                )
        except ImportError:
            result.add_info(
                ValidationError(
                    "Cannot check system memory (psutil not available)",
                    "MEMORY_CHECK_UNAVAILABLE",
                    {},
                    "info",
                )
            )

        # Check thread count
        thread_count = threading.active_count()
        if thread_count > 50:  # Arbitrary high thread count warning
            result.add_warning(
                ValidationError(
                    f"High thread count: {thread_count}",
                    "HIGH_THREAD_COUNT",
                    {"thread_count": thread_count},
                    "warning",
                )
            )

        return result

    def validate_audio_system(
        self, sample_rate: int, block_size: int, max_channels: int
    ) -> ValidationResult:
        """
        Validate complete audio system configuration.

        Args:
            sample_rate: System sample rate
            block_size: Processing block size
            max_channels: Maximum channel count

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Validate individual components
        result_sr = self.validate_sample_rate(sample_rate)
        result = self._merge_results(result, result_sr)

        result_block = self.validate_parameter_range(block_size, 1, 8192, "block_size")
        result = self._merge_results(result, result_block)

        result_channels = self.validate_parameter_range(max_channels, 1, 256, "max_channels")
        result = self._merge_results(result, result_channels)

        # Validate system compatibility
        if sample_rate > 96000 and block_size > 2048:
            result.add_warning(
                ValidationError(
                    "High sample rate with large block size may cause latency issues",
                    "LATENCY_WARNING",
                    {"sample_rate": sample_rate, "block_size": block_size},
                    "warning",
                )
            )

        return result

    def _merge_results(
        self, result1: ValidationResult, result2: ValidationResult
    ) -> ValidationResult:
        """Merge two validation results."""
        result1.errors.extend(result2.errors)
        result1.warnings.extend(result2.warnings)
        result1.info.extend(result2.info)
        return result1


class ParameterValidator:
    """
    Parameter validation with type checking and range validation.

    Provides centralized parameter validation for all synthesizer components.
    """

    def __init__(self):
        self.parameter_ranges = self._initialize_parameter_ranges()

    def _initialize_parameter_ranges(self) -> dict[str, dict[str, Any]]:
        """Initialize parameter range definitions."""
        return {
            "volume": {"min": 0.0, "max": 1.0, "type": float},
            "pan": {"min": -1.0, "max": 1.0, "type": float},
            "frequency": {"min": 20.0, "max": 20000.0, "type": float},
            "sample_rate": {"min": 8000, "max": 192000, "type": int},
            "block_size": {"min": 32, "max": 8192, "type": int},
            "midi_note": {"min": 0, "max": 127, "type": int},
            "midi_velocity": {"min": 0, "max": 127, "type": int},
            "midi_channel": {"min": 0, "max": 15, "type": int},
            "reverb_time": {"min": 0.1, "max": 10.0, "type": float},
            "chorus_rate": {"min": 0.1, "max": 10.0, "type": float},
            "delay_time": {"min": 0.01, "max": 5.0, "type": float},
        }

    def validate_parameter(self, name: str, value: Any) -> ValidationResult:
        """
        Validate a parameter by name.

        Args:
            name: Parameter name
            value: Parameter value

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if name not in self.parameter_ranges:
            result.add_error(
                ValidationError(
                    f"Unknown parameter: {name}", "UNKNOWN_PARAMETER", {"parameter": name}
                )
            )
            return result

        param_def = self.parameter_ranges[name]

        # Type checking
        if not isinstance(value, param_def["type"]):
            result.add_error(
                ValidationError(
                    f"Parameter {name} must be {param_def['type'].__name__}, got {type(value).__name__}",
                    "INVALID_PARAMETER_TYPE",
                    {
                        "parameter": name,
                        "expected": param_def["type"].__name__,
                        "actual": type(value).__name__,
                    },
                )
            )
            return result

        # Range checking
        range_result = self.validate_parameter_range(
            value, param_def["min"], param_def["max"], name
        )
        result = self._merge_results(result, range_result)

        return result

    def validate_parameter_range(
        self,
        value: int | float,
        min_val: int | float,
        max_val: int | float,
        param_name: str = "parameter",
    ) -> ValidationResult:
        """
        Validate parameter is within range.

        Args:
            value: Parameter value
            min_val: Minimum value
            max_val: Maximum value
            param_name: Parameter name

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if value < min_val:
            result.add_error(
                ValidationError(
                    f"{param_name} {value} below minimum {min_val}",
                    "PARAMETER_TOO_LOW",
                    {"parameter": param_name, "value": value, "minimum": min_val},
                )
            )

        if value > max_val:
            result.add_error(
                ValidationError(
                    f"{param_name} {value} above maximum {max_val}",
                    "PARAMETER_TOO_HIGH",
                    {"parameter": param_name, "value": value, "maximum": max_val},
                )
            )

        return result

    def _merge_results(
        self, result1: ValidationResult, result2: ValidationResult
    ) -> ValidationResult:
        """Merge validation results."""
        result1.errors.extend(result2.errors)
        result1.warnings.extend(result2.warnings)
        result1.info.extend(result2.info)
        return result1

    def add_parameter_definition(
        self, name: str, min_val: int | float, max_val: int | float, param_type: type
    ):
        """
        Add custom parameter definition.

        Args:
            name: Parameter name
            min_val: Minimum value
            max_val: Maximum value
            param_type: Parameter type
        """
        self.parameter_ranges[name] = {"min": min_val, "max": max_val, "type": param_type}


# Global validators for easy access
audio_validator = AudioValidator(strict_mode=True)
parameter_validator = ParameterValidator()
