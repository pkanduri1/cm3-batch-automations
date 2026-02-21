# Next Feature Roadmap (Architecture-Aligned)

Date: 2026-02-21
Branch baseline: `main` (post architecture-review merge)

## Status
All backlog items in this roadmap have been implemented on `feature/next-architecture-features`.

## Completion Verification
- Full test suite: `154 passed`
- Coverage gate: `81.69%` (threshold 80%)
- Regression workflow: PASS
- Manifest workflow: PASS (expected invalid scenarios captured in telemetry)

## Prioritized Backlog

## 1) Compare API v2: Async Jobs ✅ COMPLETE

### Goal
Support large file compares over API without blocking request threads.

### Scope
- Create async compare job endpoint
- Provide job status polling endpoint
- Reuse `src/services/compare_service.py` for compare execution
- Return `report_url` and compare metrics when complete

### Acceptance Criteria
- `POST /api/v1/files/compare-async` returns `job_id`
- `GET /api/v1/files/compare-jobs/{job_id}` returns `running|completed|failed`
- Completed jobs return canonical compare result payload

### Estimate
- 1-2 days

---

## 2) Validate API v2 strict/chunked parity ✅ COMPLETE

### Goal
Expose strict validation controls and chunked strict behavior over API.

### Scope
- Add strict flags to API validation request model
- Support chunked strict validation path in API
- Return structured row/field defects

### Acceptance Criteria
- API supports strict fixed-width settings equivalent to CLI
- Chunked strict API reports include field-level defect codes

### Estimate
- 2-3 days

---

## 3) Report Contracts v1 ✅ COMPLETE

### Goal
Freeze result shape for validation/compare payloads to prevent regressions.

### Scope
- JSON schema contracts for compare and validate result objects
- Contract tests in unit/integration suites

### Acceptance Criteria
- Contract tests fail on shape drift
- Docs include contract references

### Estimate
- 1-2 days

---

## 4) Workflow Engine pluginization ✅ COMPLETE

### Goal
Make workflow stages pluggable and reusable.

### Scope
- Stage registry in `src/workflows/*`
- Shared telemetry envelope across wrappers

### Acceptance Criteria
- `run_manifest_workflow.py` and `run_regression_workflow.py` remain thin wrappers
- New stage can be added without script duplication

### Estimate
- 2 days

---

## 5) Operational hardening ✅ COMPLETE

### Goal
Improve production reliability and observability.

### Scope
- Health endpoint real dependency checks
- Replace deprecated `datetime.utcnow()` usage

### Acceptance Criteria
- No deprecation warnings from utcnow in tests
- Health endpoint includes real status signals

### Estimate
- 1 day
