# Architecture

## High-Level Architecture

```mermaid
flowchart TD
    U[Users / CI / Schedulers] --> C[CLI: cm3-batch]
    U --> A[REST API: FastAPI]

    C --> O[Orchestration Layer\nsrc/main.py]
    A --> O

    O --> P[Parsing Layer\nformat detector + parsers]
    O --> V[Validation Layer\nenhanced + chunked + rules]
    O --> M[Mapping Layer\nconverter + parser + schemas]
    O --> D[Database Layer\nOracle connection/extractor/reconcile]
    O --> R[Reporting Layer\nHTML/JSON/CSV adapters]
    O --> G[GE Layer\ncheckpoint1 config-driven]

    P --> DF[(DataFrame)]
    V --> DF
    M --> DF
    D --> DF
    DF --> R
    DF --> G

    R --> OUT[Reports\nHTML + JSON + CSV]
    G --> OUT
```

## Validation Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as cm3-batch validate
    participant Parser
    participant Validator
    participant Rules as RuleEngine
    participant Reporter

    User->>CLI: validate -f file -m mapping [-r rules]
    CLI->>Parser: parse file (standard/chunked)
    Parser-->>CLI: DataFrame/chunks
    CLI->>Validator: schema + quality checks
    alt rules provided
      CLI->>Rules: execute business rules
      Rules-->>Validator: violations
    end
    Validator-->>CLI: validation result
    CLI->>Reporter: render report
    Reporter-->>User: HTML/JSON (+ warnings CSV)
```

## Core Modules
- `src/main.py` — command orchestration
- `src/parsers/` — format detection and parsing
- `src/parsers/enhanced_validator.py` — standard validation
- `src/parsers/chunked_validator.py` — chunked validation
- `src/validators/` — business and field validators
- `src/database/` — Oracle connectivity and extraction
- `src/reports/` — unified report rendering/adapters/contracts
- `src/reporters/` + `src/reporting/` — backward-compatible shims (deprecated)
- `src/quality/gx_checkpoint1.py` — Great Expectations checkpoint integration

## Design Principles
- Mapping-driven processing (no hardcoded file layouts)
- Fail-fast exit codes for CI correctness
- Memory-safe chunked processing for large files
- Human + machine outputs for operations and automation
