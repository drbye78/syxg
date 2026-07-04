"""
Deprecated re-export shim for ArticulationController.

This module exports ArticulationController from controllers.py for backward
compatibility. New code should import from .controllers directly.
This shim will be removed in a future version.
"""

from __future__ import annotations

from .controllers import ArticulationController
