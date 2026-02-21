"""Backward-compatible shim for standard result adapter.

Deprecated: import from `src.reports.adapters.result_adapter_standard`.
"""

from src.reports.adapters.result_adapter_standard import adapt_standard_validation_result

__all__ = ["adapt_standard_validation_result"]
