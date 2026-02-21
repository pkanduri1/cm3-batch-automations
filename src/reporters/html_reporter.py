"""Backward-compatible shim for HTMLReporter.

Deprecated: import from `src.reports.renderers.comparison_renderer`.
"""

from src.reports.renderers.comparison_renderer import HTMLReporter

__all__ = ["HTMLReporter"]
