"""Condition evaluator for the transform engine.

Provides :func:`evaluate_condition`, which tests a condition object against a
source row dictionary and returns ``True`` when the condition is satisfied.

Currently supports :class:`~src.transforms.models.NullCheckCondition`.
Additional condition types will be added in later phases.
"""

from __future__ import annotations

from src.transforms.models import NullCheckCondition


def _is_null(value: object) -> bool:
    """Return True when *value* is considered null.

    A value is null when it is absent (represented here as the sentinel
    ``_MISSING``), ``None``, or a whitespace-only string.

    Args:
        value: The field value extracted from the row dict, or ``None`` if the
            key was absent.

    Returns:
        ``True`` when the value is null; ``False`` otherwise.
    """
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def evaluate_condition(condition: NullCheckCondition, row: dict) -> bool:
    """Evaluate a condition against a data row and return the boolean result.

    Args:
        condition: A :class:`~src.transforms.models.NullCheckCondition`
            describing the check to perform.
        row: A mapping of field names to their string (or ``None``) values
            for the current record.

    Returns:
        ``True`` when the condition is satisfied, ``False`` otherwise.

    Raises:
        TypeError: If *condition* is not a recognised condition type.

    Example::

        cond = NullCheckCondition(field="amount")
        evaluate_condition(cond, {"amount": None})   # True  (IS NULL)
        evaluate_condition(cond, {"amount": "100"})  # False (not null)

        neg = NullCheckCondition(field="amount", negate=True)
        evaluate_condition(neg, {"amount": "100"})   # True  (IS NOT NULL)
    """
    if isinstance(condition, NullCheckCondition):
        null = _is_null(row.get(condition.field))
        return (not null) if condition.negate else null

    raise TypeError(
        f"Unsupported condition type: {type(condition).__name__!r}"
    )
