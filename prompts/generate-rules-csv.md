# Generate Valdo Rules CSV from Specification Document

Copy this entire prompt, then paste your specification document content below the `---` line.

---

## Instructions

You are converting a batch file specification document into a business rules CSV template for the **Valdo** file validation tool. Extract validation rules from the spec's Required flags, Valid Values, Format codes, Transformation logic, and Notes.

### Output Format

Generate a CSV with exactly these columns (in this order):

```
Rule ID,Rule Name,Field,Type,Severity,Enabled,Message,Value
```

### Column Definitions

| Column | Description | Values |
|--------|-------------|--------|
| `Rule ID` | Unique ID: `R001`, `R002`... for field rules, `CR001`... for cross-row | Sequential |
| `Rule Name` | Snake_case descriptive name | e.g. `account_not_empty` |
| `Field` | Field name(s) the rule applies to | See syntax below |
| `Type` | Rule type | See type reference below |
| `Severity` | `error` or `warning` | Use `error` for Required fields, `warning` for soft checks |
| `Enabled` | `Yes` | Always `Yes` |
| `Message` | Human-readable error message | Describe what went wrong |
| `Value` | Rule parameter (if needed) | Depends on type |

### Field Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `FIELD_NAME` | Single field | `BALANCE` |
| `FIELD1\|FIELD2` | Multiple fields (cross_field or unique_composite) | `STATUS\|BALANCE` |
| `KEY>TARGET` | Key field → target field (cross_row) | `LN-NUM-ERT>BK-NUM-ERT` |

### Rule Type Reference

Extract these rules from the specification:

#### Per-Row Rules (from Required, Format, Valid Values columns)

| Spec Pattern | Rule Type | Value | Example |
|-------------|-----------|-------|---------|
| `Required = Y` | `not_empty` | (blank) | Field must not be empty |
| `Format = 9(n)` | `numeric` | (blank) | Field must be numeric |
| `Format = MM/DD/CCYY` or `CCYYMMDD` | `date_format` | The format string | `CCYYMMDD` |
| `Valid Values = X` (single value) | `valid_values` | The value | `32010` |
| `Valid Values = A\|B\|C` (multiple) | `valid_values` | Pipe-separated values | `A\|I\|C` |
| `Length = N` (for Required fields) | `exact_length` | The length | `18` |
| Known numeric field | `min_value` | `0` | Non-negative amounts |
| Known numeric field | `max_value` | Upper limit | `999999999` |

#### Cross-Field Rules (from Transformation IF/ELSE logic within same row)

| Spec Pattern | Rule Type | Value |
|-------------|-----------|-------|
| `IF field1 = X THEN field2 must be Y` | `cross_field` | `field1=X AND field2=Y` |
| `IF TYPE = '7' THEN field = 'C' ELSE 'I'` | `cross_field` | Condition expression |

#### Cross-Row Rules (from patterns across multiple rows)

| Spec Pattern | Rule Type (with `cross_row:` prefix) | Value |
|-------------|--------------------------------------|-------|
| "must be unique" / "no duplicates" | `cross_row:unique` | (blank) |
| "unique combination of fields" | `cross_row:unique_composite` | (blank) |
| "must be same for all rows with same key" | `cross_row:consistent` | (blank) |
| "1st then '1', 2nd then '2', nth then 'n'" / sequential | `cross_row:sequential` | Start value (usually `1`) |
| "count must match number of records" | `cross_row:group_count` | (blank) |
| "total must not exceed" / aggregate limit | `cross_row:group_sum` | Max value |

### How to Read the Specification

1. **Required = Y** → Generate a `not_empty` rule
2. **Format = 9(n)** → Generate a `numeric` rule
3. **Format with date pattern** → Generate a `date_format` rule
4. **Valid Values column** → Generate `valid_values` rule (skip vague entries like "Bank Control Table")
5. **Transformation with IF/ELSE** → Generate `cross_field` rule
6. **Notes mentioning "sequential", "1st/2nd/nth"** → Generate `cross_row:sequential` rule
7. **Notes mentioning "unique"** → Generate `cross_row:unique` rule
8. **Fields with same name appearing in multiple rows** → Consider `cross_row:consistent` for key fields
9. **Fields labeled as count/total** → Consider `cross_row:group_count` or `cross_row:group_sum`
10. **Skip** rules for FILLER fields and fields marked `N/A` unless they have explicit validation

### Example

**Input spec (pipe-separated):**
```
Transformation|Column|Definition|Data Type|Position|Format|Length|Required|Valid Values|Notes
Default to '00040'|BK-NUM-ERT|Bank identifier|Numeric|1|9(5)|5|Y|Bank Control Table|
Default to '001'|APP-ERT|Application code|Numeric|6|9(3)|3|Y|Application Control Table|
LN-NUM-ERT = BR + CUS + LN|LN-NUM-ERT|Account number|String|9||18|Y||
Default to '32010'|TRN-COD-ERT|Transaction code|Numeric|170|9(5)|5|Y|32010|
if 1st in batch then '1'; if nth then 'n'|BAT-ITM-NUM-ERT|Sequential batch item|Numeric|175|9(9)|9|Y||
|TRN-CNT-ERT|Transaction count|Numeric|187|9(4)|4|Y||
```

**Output CSV:**
```csv
Rule ID,Rule Name,Field,Type,Severity,Enabled,Message,Value
R001,bk_num_not_empty,BK-NUM-ERT,not_empty,error,Yes,Bank number must not be empty,
R002,bk_num_numeric,BK-NUM-ERT,numeric,error,Yes,Bank number must be numeric,
R003,app_not_empty,APP-ERT,not_empty,error,Yes,Application code must not be empty,
R004,app_numeric,APP-ERT,numeric,error,Yes,Application code must be numeric,
R005,ln_num_not_empty,LN-NUM-ERT,not_empty,error,Yes,Account number must not be empty,
R006,ln_num_length,LN-NUM-ERT,exact_length,error,Yes,Account number must be exactly 18 characters,18
R007,trn_cod_not_empty,TRN-COD-ERT,not_empty,error,Yes,Transaction code must not be empty,
R008,trn_cod_valid,TRN-COD-ERT,valid_values,error,Yes,Transaction code must be 32010,32010
R009,bat_itm_not_empty,BAT-ITM-NUM-ERT,not_empty,error,Yes,Batch item number must not be empty,
R010,bat_itm_numeric,BAT-ITM-NUM-ERT,numeric,error,Yes,Batch item number must be numeric,
R011,trn_cnt_not_empty,TRN-CNT-ERT,not_empty,error,Yes,Transaction count must not be empty,
R012,trn_cnt_numeric,TRN-CNT-ERT,numeric,error,Yes,Transaction count must be numeric,
CR001,unique_account,LN-NUM-ERT,cross_row:unique,error,Yes,Account number must be unique across all rows,
CR002,sequential_batch_items,LN-NUM-ERT>BAT-ITM-NUM-ERT,cross_row:sequential,error,Yes,Batch items must be sequential (1 2 3...) per account,1
CR003,txn_count_matches,LN-NUM-ERT>TRN-CNT-ERT,cross_row:group_count,error,Yes,Transaction count must match actual records per account,
CR004,consistent_bank,LN-NUM-ERT>BK-NUM-ERT,cross_row:consistent,error,Yes,Bank number must be consistent for same account,
```

---

## Your Specification Document

Paste your specification content below this line:


