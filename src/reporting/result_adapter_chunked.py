"""Backward-compatible shim for chunked result adapter.

Deprecated: import from `src.reports.adapters.result_adapter_chunked`.
"""

from src.reports.adapters.result_adapter_chunked import adapt_chunked_validation_result

__all__ = ["adapt_chunked_validation_result"]
