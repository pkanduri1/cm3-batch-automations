"""Unit tests for the condition evaluator.

Tests are written before implementation — they are expected to fail initially.
Covers evaluate_condition for NullCheckCondition: missing key, None value,
whitespace-only string, non-null value, and negated variants.
"""

import pytest
from src.transforms import NullCheckCondition, evaluate_condition


class TestNullCheckCondition:
    """evaluate_condition with NullCheckCondition (negate=False means IS NULL)."""

    def test_missing_key_is_null(self):
        """Field absent from the row dict is treated as null — condition is True."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {}) is True

    def test_none_value_is_null(self):
        """Field present but None is treated as null — condition is True."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {"amount": None}) is True

    def test_whitespace_only_is_null(self):
        """Field containing only whitespace is treated as null — condition is True."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {"amount": "   "}) is True

    def test_empty_string_is_null(self):
        """Empty string is treated as null — condition is True."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {"amount": ""}) is True

    def test_non_null_value_is_false(self):
        """Field with a real value is NOT null — condition is False."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {"amount": "100"}) is False

    def test_zero_string_is_not_null(self):
        """The string '0' has content and is NOT null — condition is False."""
        condition = NullCheckCondition(field="amount")
        assert evaluate_condition(condition, {"amount": "0"}) is False


class TestNullCheckConditionNegated:
    """evaluate_condition with NullCheckCondition(negate=True) means IS NOT NULL."""

    def test_negated_missing_key_is_false(self):
        """Field absent from row: IS NOT NULL → False."""
        condition = NullCheckCondition(field="amount", negate=True)
        assert evaluate_condition(condition, {}) is False

    def test_negated_none_is_false(self):
        """Field is None: IS NOT NULL → False."""
        condition = NullCheckCondition(field="amount", negate=True)
        assert evaluate_condition(condition, {"amount": None}) is False

    def test_negated_whitespace_is_false(self):
        """Whitespace-only: IS NOT NULL → False."""
        condition = NullCheckCondition(field="amount", negate=True)
        assert evaluate_condition(condition, {"amount": "   "}) is False

    def test_negated_non_null_is_true(self):
        """Field with a real value: IS NOT NULL → True."""
        condition = NullCheckCondition(field="amount", negate=True)
        assert evaluate_condition(condition, {"amount": "100"}) is True

    def test_negated_zero_string_is_true(self):
        """String '0' has content: IS NOT NULL → True."""
        condition = NullCheckCondition(field="amount", negate=True)
        assert evaluate_condition(condition, {"amount": "0"}) is True


class TestNullCheckConditionType:
    """NullCheckCondition model structure."""

    def test_default_type_is_null_check(self):
        """NullCheckCondition.type defaults to 'null_check'."""
        condition = NullCheckCondition(field="x")
        assert condition.type == "null_check"

    def test_default_negate_is_false(self):
        """NullCheckCondition.negate defaults to False."""
        condition = NullCheckCondition(field="x")
        assert condition.negate is False


class TestEvaluateConditionUnsupported:
    """evaluate_condition raises TypeError for unrecognised condition objects."""

    def test_unsupported_type_raises(self):
        """Passing an unrecognised condition type raises TypeError."""
        with pytest.raises(TypeError, match="Unsupported condition type"):
            evaluate_condition(object(), {"field": "value"})
