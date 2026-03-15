# Configuration change management

This project enforces change control for mapping/rules configuration artifacts.

## Scope

- `config/mappings/`
- `config/rules/`
- `config/test_suites/`

## Approval process

1. Open a pull request from a feature branch (no direct pushes to `main`).
2. Ensure config validation workflow passes.
3. Obtain CODEOWNER approval for touched config paths.
4. Merge only after required approvals and status checks are green.

## Branch protection (GitHub)

Configure `main` branch protection:

- Require pull request before merging
- Require at least 1 approving review
- Require review from Code Owners
- Require status checks:
  - `CI / test-and-docs`
  - `Config Change Validation / validate-config-changes`

## Audit traceability note

Structured audit events should include config git SHA + file hashes. The repository now enforces PR approval checks for config files; SHA enrichment in centralized audit events is tracked with Splunk audit integration work.
