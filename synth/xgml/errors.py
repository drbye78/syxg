"""XGML exception hierarchy."""

from __future__ import annotations


class XGMLError(Exception):
    """Base exception for all XGML errors."""


class ParseError(XGMLError):
    """Raised when XGML document parsing fails."""


class ValidationError(XGMLError):
    """Raised when XGML document validation fails."""


class BridgeError(XGMLError):
    """Raised when XGML→MIDI or XGML→synth bridge translation fails."""


class UnsupportedVersionError(ParseError):
    """Raised when XGML document version is not supported."""


class SchemaValidationError(ValidationError):
    """Raised when XGML document fails schema validation."""


class MissingFieldError(ValidationError):
    """Raised when a required field is missing from XGML config."""
