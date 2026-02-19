"""Unit tests for BA-friendly rules template conversion."""

import os
import tempfile
import json

from src.config.ba_rules_template_converter import BARulesTemplateConverter


def test_ba_converter_builds_allowed_values_rule():
    csv_content = """Rule ID,Rule Name,Field,Rule Type,Severity,Expected / Values,Condition (optional),Enabled,Notes
BR1,Status allowed,status,Allowed Values,Warning,ACTIVE, ,Y,
"""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(csv_content)
        path = f.name

    try:
        conv = BARulesTemplateConverter()
        out = conv.from_csv(path)
        assert len(out['rules']) == 1
        r = out['rules'][0]
        assert r['type'] == 'field_validation'
        assert r['operator'] == 'in'
        assert r['values'] == ['ACTIVE']
    finally:
        os.unlink(path)


def test_ba_converter_builds_compare_fields_rule():
    csv_content = """Rule ID,Rule Name,Field,Rule Type,Severity,Expected / Values,Condition (optional),Enabled,Notes
BR2,Compare totals,total_due_amt,Compare Fields,Error,>= CURRENT_DUE_AMT,,Y,
"""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(csv_content)
        path = f.name

    try:
        conv = BARulesTemplateConverter()
        out = conv.from_csv(path)
        r = out['rules'][0]
        assert r['type'] == 'cross_field'
        assert r['left_field'] == 'total_due_amt'
        assert r['right_field'] == 'CURRENT_DUE_AMT'
        assert r['operator'] == '>='
    finally:
        os.unlink(path)
