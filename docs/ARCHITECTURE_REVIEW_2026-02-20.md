# Architecture Review (Critical) — 2026-02-20

Branch: `feature/architecture-review`
Reviewer stance: Test Engineering Architecture (critical review)

## Executive Summary

The platform has strong functional breadth (CLI + API + pipeline orchestration + chunked processing), but architecture quality is being held back by **orchestration sprawl**, **inconsistent contracts**, and **unsafe command execution patterns**.

Most severe risks:
1. Monolithic command orchestrator and duplicated orchestration logic.
2. `shell=True` execution of profile/config-derived commands.
3. Inconsistent report/output behavior between chunked vs non-chunked paths.
4. API and CLI behavior drift (same use-case, different quality).

---

## Key Findings

### 1) Orchestrator God Object (maintainability bottleneck)
- `src/main.py` is 1041 lines and mixes command parsing, business orchestration, output formatting, adapter wiring, and error/exit policy.
- This causes fragile changes and repeated regressions when modifying one command path.

**Evidence**
- `src/main.py` (1041 LOC)

**Impact**
- High regression risk, slow onboarding, difficult test isolation.

**Recommendation**
- Extract command handlers into modules:
  - `src/commands/parse.py`
  - `src/commands/validate.py`
  - `src/commands/compare.py`
  - `src/commands/reconcile.py`
- Keep `main.py` as Click entry/wiring only.

---

### 2) Unsafe command execution in pipeline path
- Pipeline execution uses shell invocation with config-provided command strings.

**Evidence**
- `src/pipeline/runner.py` uses `subprocess.run(cmd, shell=True, ...)`.
- `src/pipeline/output_regression_suite.py` uses `subprocess.run(cmd, shell=True, ...)`.

**Impact**
- Command injection risk and quoting fragility.
- Harder cross-platform predictability.

**Recommendation**
- Replace with argument-array execution (`shell=False`) and explicit command builders.
- Restrict/validate allowed commands for pipeline profiles.
- Add tests for quoting and unsafe chars.

---

### 3) Inconsistent output contract (validate command)
- Non-chunked validate path always routes through `ValidationReporter` regardless output extension.
- Chunked path supports extension-aware behavior (`.json` vs `.html`).

**Evidence**
- `src/main.py` validate non-chunked: `reporter.generate(result, output)` (no extension switch).
- `src/main.py` chunked validate: explicit `.json`/`.html` branching.

**Impact**
- Surprising behavior and format bugs.
- Automation scripts become brittle.

**Recommendation**
- Define a single output contract for validate (both modes):
  - `.json` => machine JSON
  - `.html` => HTML
  - optional sidecars for warnings/errors
- Implement shared output writer used by both paths.

---

### 4) Layering confusion: `reporters/` vs `reporting/`
- Two similarly named packages split responsibilities ambiguously.

**Evidence**
- `src/reporters/*` (renderers) and `src/reporting/*` (result adapters)

**Impact**
- Discoverability and ownership confusion.
- Increases accidental duplication.

**Recommendation**
- Consolidate under one namespace (e.g., `src/reports/`):
  - `renderers/`
  - `adapters/`
  - `contracts/`

---

### 5) API/CLI capability drift
- API comparison endpoint is simplified and not feature-equivalent with CLI.
- Health endpoint reports static DB status with TODO.

**Evidence**
- `src/api/routers/files.py`: compare returns simplistic counts and `report_url=None` TODO.
- `src/api/routers/system.py`: `database_connected=False` TODO.

**Impact**
- Different truth depending on interface.
- Misleading API health in production contexts.

**Recommendation**
- Establish parity matrix (CLI vs API) and track gaps as explicit backlog.
- Move comparison logic to shared service used by both CLI and API.
- Implement real DB connectivity check (optional timeout, degraded status semantics).

---

### 6) Workflow script sprawl and duplication
- Multiple overlapping scripts orchestrate similar flows (`validate_data_files.py`, `run_manifest_workflow.py`, `run_regression_workflow.py`, shell/ps1 wrappers).

**Impact**
- Repeated argument parsing, telemetry logic, error handling.
- Divergent behavior over time.

**Recommendation**
- Create unified orchestration library:
  - `src/workflows/engine.py`
  - reusable stages + shared telemetry schema
- Keep scripts as thin wrappers only.

---

### 7) Config typing/validation is too loose in orchestrators
- Workflow and pipeline config consumed mostly as untyped dicts.

**Impact**
- Late runtime failures, poor error messaging.

**Recommendation**
- Add Pydantic models for pipeline/workflow config contracts.
- Validate at load-time with friendly, field-level errors.

---

### 8) CI design fragility in matrix artifact naming (already observed)
- Pipeline regression workflow previously used matrix profile path directly in artifact name.

**Impact**
- CI failures on invalid artifact characters.

**Recommendation**
- Keep sanitized matrix metadata (`source_name`) for display and artifact naming.
- Add lint/check for forbidden chars in workflow-generated identifiers.

---

### 9) Generated data + sample artifacts in repo root paths
- `data/files/*`, `reports/*` patterns are mixed with source-managed assets.

**Impact**
- Repository hygiene drift and accidental commits of generated output.

**Recommendation**
- Enforce clear generated-output directories with `.gitignore` policy.
- Separate immutable sample fixtures (`test_fixtures/`) from runtime outputs (`reports/`, temp dirs).

---

## Priority Fix Plan

### P0 (Immediate)
1. Replace `shell=True` pipeline execution paths. ✅
2. Standardize validate output contract (json/html parity across modes). ✅
3. Split `main.py` into command modules. ✅ (started for parse/validate/compare)

### P1 (Near-term)
4. Consolidate reporting namespace (`reporters` + `reporting`).
5. API/CLI comparison parity via shared service.
6. Typed config contracts for pipeline/workflow.

### P2 (Medium-term)
7. Unify scripts onto shared workflow engine.
8. Formal architecture decision records (ADRs) for parsing/validation/reporting boundaries.

---

## Suggested Target Architecture (north star)

- `src/commands/*` (CLI-only thin handlers)
- `src/services/*` (core business workflows)
- `src/reports/{adapters,renderers,contracts}`
- `src/workflows/*` (pipeline/manifest/regression engine)
- `src/api/*` calling shared services only

This will reduce drift, remove duplicated orchestration code, and make test architecture significantly cleaner.
