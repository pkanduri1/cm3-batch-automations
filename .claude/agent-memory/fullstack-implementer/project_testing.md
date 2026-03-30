---
name: Test patterns and coverage notes
description: pytest setup, coverage baseline, test fixture patterns, ignored test files
type: project
---

## Test command (per CLAUDE.md)

```bash
pytest tests/unit/ \
    --ignore=tests/unit/test_contracts_pipeline.py \
    --ignore=tests/unit/test_pipeline_runner.py \
    --ignore=tests/unit/test_workflow_wrapper_parity.py \
    --cov=src --cov-report=term-missing -q
```

## Coverage baseline

Overall project coverage is ~72% (below 80%). This is pre-existing. New modules should target ≥80% individually. The pytest.ini config enforces 80% on the full run but this has always been below threshold for the project as a whole.

## Test fixture patterns

- Use `tmp_path` (pytest builtin) for YAML/JSON fixtures — write inline with `textwrap.dedent` then `p.write_text()`
- Mock service calls with `patch("src.pipeline.etl_pipeline_runner.run_validate_service", return_value={...})`
- For db_compare steps, also patch `_load_mapping_config` since it reads a JSON file before calling the service

## Ignored test files

These three files are excluded from the normal test run (they import modules that don't exist or have external deps):
- `tests/unit/test_contracts_pipeline.py`
- `tests/unit/test_pipeline_runner.py`
- `tests/unit/test_workflow_wrapper_parity.py`

## Test file count as of 2026-03-26

968 tests passing in the unit suite.
