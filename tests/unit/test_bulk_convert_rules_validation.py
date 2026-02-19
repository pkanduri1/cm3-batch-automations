"""Tests for strict validation in bulk_convert_rules script."""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import tempfile


_SCRIPT = Path('scripts/bulk_convert_rules.py')
_spec = spec_from_file_location('bulk_convert_rules', _SCRIPT)
_mod = module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_ba_template_validation_positive():
    content = (
        'Rule ID,Rule Name,Field,Rule Type,Severity,Expected / Values,Condition (optional),Enabled\n'
        'BR1001,Status in list,status,Allowed Values,Warning,"ACTIVE,INACTIVE",status = ACTIVE,Y\n'
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        p = Path(f.name)

    issues, kind = _mod.validate_template_strict(p)
    assert kind == 'ba_friendly'
    assert issues == []


def test_ba_template_validation_negative():
    content = (
        'Rule ID,Rule Name,Field,Rule Type,Severity,Expected / Values,Condition (optional),Enabled\n'
        'B!,Bad rule,status,Compare Fields,Sev,>=,status ~~ ACTIVE,Y\n'
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        p = Path(f.name)

    issues, kind = _mod.validate_template_strict(p)
    assert kind == 'ba_friendly'
    assert len(issues) >= 3
    problems = ' | '.join(i['issue'] for i in issues)
    assert 'Invalid Rule ID format' in problems
    assert 'Invalid severity' in problems
