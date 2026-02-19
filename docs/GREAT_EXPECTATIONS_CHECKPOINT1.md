# Great Expectations Integration (Checkpoint 1)

This project includes a **BA-friendly, low/no-code** Great Expectations integration focused on Checkpoint 1 controls:

- Schema / column order checks
- Required field non-null checks
- Key uniqueness checks
- Allowed value checks
- Numeric range checks
- Row-count guardrails

---

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

> Runtime note: Great Expectations currently requires running this command with a supported Python runtime (recommended **3.11 or 3.12**).

---

## 2) Use CSV templates (no Python coding required)

Start from templates:

- `config/templates/csv/gx_checkpoint1_targets_template.csv`
- `config/templates/csv/gx_checkpoint1_expectations_template.csv`

You can also reference examples:

- `config/gx/targets.sample.csv`
- `config/gx/expectations.sample.csv`

### targets CSV columns

- `target_id` *(required)*: logical dataset id
- `data_file` *(required)*: path to file to validate
- `delimiter`: default `|`
- `has_header`: `true`/`false`
- `mapping_file`: mapping JSON; if provided, schema is read from mapping
- `key_columns`: pipe-separated key fields (`COL1|COL2`)
- `required_columns`: pipe-separated required fields
- `enabled`: `true`/`false`

### expectations CSV columns

- `target_id` *(required)*: must match targets CSV
- `expectation_type` *(required)*: one of supported expectation types
- `column`: column name for column-level checks
- `column_list`: pipe-separated ordered columns (for schema order checks)
- `value_set`: pipe-separated allowed values
- `min_value` / `max_value`: numeric limits
- `mostly`: optional tolerance (e.g., `0.99`)
- `notes`: BA notes/documentation
- `enabled`: `true`/`false`

---

## 3) Run Checkpoint 1

```bash
cm3-batch gx-checkpoint1 \
  --targets config/gx/targets.sample.csv \
  --expectations config/gx/expectations.sample.csv \
  --output reports/gx_checkpoint1_summary.json
```

If checks fail, command exits non-zero for CI/CD compatibility.

---

## 4) Supported expectation types

- `expect_table_columns_to_match_ordered_list`
- `expect_column_values_to_not_be_null`
- `expect_column_values_to_be_unique`
- `expect_column_values_to_be_in_set`
- `expect_column_values_to_be_between`
- `expect_table_row_count_to_be_between`

---

## 5) BA workflow recommendation

1. Copy the two template CSVs into a project-specific folder.
2. Fill `targets` first (what to validate).
3. Fill `expectations` next (validation rules).
4. Run `cm3-batch gx-checkpoint1` locally.
5. Commit CSVs with source control for traceability.
6. Add the command to CI pipeline for regression enforcement.

This keeps control in data/business teams without custom Python code.
