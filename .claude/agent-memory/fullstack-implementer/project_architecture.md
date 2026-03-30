---
name: Project architecture and service patterns
description: Layered architecture, service locations, CLI registration pattern, key entry points
type: project
---

## Layer stack

CLI/API → Commands/Routers → Services → Parsers/Validators/DB/Reporting

## Key service locations

- `src/services/validate_service.py` — `run_validate_service(file, mapping, rules, ...)` → dict with `valid`, `error_count`, `total_rows`
- `src/services/compare_service.py` — `run_compare_service(file1, file2, keys, mapping, ...)` → dict with `structure_compatible`, `rows_with_differences`
- `src/services/db_file_compare_service.py` — `compare_db_to_file(query_or_table, mapping_config, actual_file, ...)` → dict with `workflow.status` and `compare` sub-dict
- `src/pipeline/suite_runner.py` — `SuiteRunner` with `StepConfig`/`SuiteConfig`/`StepResult`/`SuiteResult`

## CLI registration pattern

In `src/main.py`: `@cli.command('command-name')` + `@click.option(...)` decorator stack, then body does `from src.commands.foo_command import run_foo_command` and delegates. Never put business logic in main.py.

## Existing `run-pipeline` command

There is already a `run-pipeline` command in main.py that uses `src/pipeline/runner.py` and `PipelineRunner`. The new ETL pipeline uses `run-etl-pipeline` (different command name) and `src/pipeline/etl_pipeline_runner.py`.

## Pipeline module layout

```
src/pipeline/
  suite_runner.py       — generic step orchestrator (retry, timeout, callbacks)
  suite_config.py       — Pydantic models for suite YAML
  etl_config.py         — Pydantic models for ETL pipeline YAML (#156)
  etl_pipeline_runner.py — ETL gate orchestrator, delegates to services (#156)
  runner.py             — source-system profile runner (older, uses PipelineRunner)
```

## Config directories

```
config/
  mappings/     — generated mapping JSON files
  rules/        — generated rules JSON files
  suites/       — suite YAML files for run-tests
  pipelines/    — ETL pipeline YAML files for run-etl-pipeline (#156)
```

## Oracle DB

Username: CM3INT, DSN: localhost:1521/FREEPDB1. Credentials in .env (gitignored). 17 tables: SHAW_SRC_P327 etc.

## Pluggable DB adapters (issue #151)

New package at `src/database/adapters/`. Public API:

```python
from src.database.adapters import DatabaseAdapter, get_database_adapter
```

- `base.py` — `DatabaseAdapter` ABC with 6 abstract methods
- `oracle_adapter.py` — reads `ORACLE_USER/PASSWORD/DSN`, uses oracledb thin mode
- `postgresql_adapter.py` — reads `DB_HOST/PORT/NAME/USER/PASSWORD`, dynamic psycopg2 import (graceful)
- `sqlite_adapter.py` — reads `DB_PATH`, uses built-in sqlite3 (perfect for tests)
- `factory.py` — `get_database_adapter(adapter_type=None)` reads `DB_ADAPTER` env var

`src/config/db_config.py` extended: `DbConfig` has new fields `db_adapter`, `db_host`, `db_port`, `db_name` (all backward-compatible — default to oracle/None).

PostgreSQL adapter uses dynamic `sys.modules["psycopg2"]` lookup in `connect()` so tests can inject mock via `patch.dict("sys.modules", ...)` without module reload.
