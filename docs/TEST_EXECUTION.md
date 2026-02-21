# Test Execution Instructions

## Quick Start

```bash
# full suite with configured coverage gate
.venv/bin/pytest -q

# targeted verification packs
.venv/bin/pytest -q -o addopts='' tests/unit/test_workflow_engine.py tests/unit/test_workflow_wrapper_parity.py
```

## Current Baseline (feature/architecture-review)

- Full suite: **149 passed**
- Coverage gate: **80% required**
- Latest measured coverage: **~82%** (passes gate)

## Workflow Verification Commands

```bash
# Regression workflow
.venv/bin/python scripts/run_regression_workflow.py \
  --config config/pipeline/regression_workflow.sample.json \
  --summary-out reports/verification/premerge_regression_summary.json

# Manifest workflow
.venv/bin/python scripts/run_manifest_workflow.py \
  --manifest config/validation_manifest_10_scenarios.csv \
  --reports-dir reports/verification_manifest_p2

# Pipeline dry-runs
.venv/bin/python -m src.main run-pipeline \
  --config config/pipeline/source_profile.SRC_A.sample.json --dry-run \
  -o reports/verification/p2_pipeline_src_a.json

.venv/bin/python -m src.main run-pipeline \
  --config config/pipeline/source_profile.SRC_B.sample.json --dry-run \
  -o reports/verification/p2_pipeline_src_b.json
```

## Notes
- Some manifest scenarios are intentionally invalid; these are expected failures and should be captured in telemetry.
- Strict fixed-width validation is available in both non-chunked and chunked validate paths.
