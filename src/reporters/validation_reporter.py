"""Backward-compatible shim for ValidationReporter.

Deprecated: import from `src.reports.renderers.validation_renderer`.
"""

from src.reports.renderers.validation_renderer import ValidationReporter

__all__ = ["ValidationReporter"]
