"""Unit tests for strict fixed-width validation modes."""

import os
import tempfile

from src.parsers.fixed_width_parser import FixedWidthParser
from src.parsers.enhanced_validator import EnhancedFileValidator


def _make_mapping():
    return {
        'file_path': 'dummy_mapping.json',
        'fields': [
            {'name': 'ACCOUNT', 'position': 1, 'length': 4, 'required': True, 'format': '9(4)'},
            {'name': 'STATUS', 'position': 5, 'length': 1, 'required': False, 'valid_values': ['A', 'B']},
        ],
        'total_record_length': 5,
    }


def test_strict_basic_only_checks_length_and_required():
    # Row 2 has STATUS='Z' (invalid valid_values), but basic mode should ignore format/value checks.
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('1234A\n')
        f.write('5678Z\n')
        temp_file = f.name

    try:
        parser = FixedWidthParser(temp_file, [('ACCOUNT', 0, 4), ('STATUS', 4, 5)])
        validator = EnhancedFileValidator(parser, _make_mapping())
        result = validator.validate(detailed=False, strict_fixed_width=True, strict_level='basic')

        assert result['valid'] is True
        assert result['strict_fixed_width']['enabled'] is True
        assert result['strict_fixed_width']['strict_level'] == 'basic'
        assert result['strict_fixed_width']['format_errors'] == 0
    finally:
        os.unlink(temp_file)


def test_strict_format_checks_valid_values_for_non_empty_optional_fields():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('1234A\n')
        f.write('5678Z\n')
        temp_file = f.name

    try:
        parser = FixedWidthParser(temp_file, [('ACCOUNT', 0, 4), ('STATUS', 4, 5)])
        validator = EnhancedFileValidator(parser, _make_mapping())
        result = validator.validate(detailed=False, strict_fixed_width=True, strict_level='format')

        assert result['valid'] is False
        errs = result['errors']
        assert any(e.get('code') == 'FW_VAL_001' for e in errs)
    finally:
        os.unlink(temp_file)


def test_strict_format_allows_empty_optional_fields():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('1234 \n')
        temp_file = f.name

    try:
        parser = FixedWidthParser(temp_file, [('ACCOUNT', 0, 4), ('STATUS', 4, 5)])
        validator = EnhancedFileValidator(parser, _make_mapping())
        result = validator.validate(detailed=False, strict_fixed_width=True, strict_level='format')

        assert result['valid'] is True
    finally:
        os.unlink(temp_file)
