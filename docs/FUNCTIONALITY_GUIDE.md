# CM3 Batch Automations - Complete Functionality Guide

## Overview

CM3 Batch Automations is a comprehensive tool for Oracle data extraction, file processing, validation, and comparison. It provides both CLI and REST API interfaces.

---

## 🎯 Core Functionalities

### 1. File Format Detection
### 2. File Parsing
### 3. File Validation
### 4. File Comparison
### 5. Oracle Data Extraction
### 6. Mapping Reconciliation
### 7. REST API
### 8. Reporting
### 9. Business Rules Validation (New!)
### 10. Source Data Verification (New!)

---

## 1. 📂 File Format Detection

**Automatically detect file formats** without manual specification.

### Command
```bash
cm3-batch detect -f <file>
```

### Supported Formats
- **Pipe-delimited** (`|`)
- **Fixed-width**
- **CSV** (`,`)
- **TSV** (tab)

### How It Works
1. Reads sample lines from file
2. Analyzes delimiters and patterns
3. Returns format with confidence score

### Example
```bash
cm3-batch detect -f data/customers.txt
```

**Output:**
```
File: data/customers.txt
Format: pipe_delimited
Confidence: 95.00%
Delimiter: |
Sample lines: 100
```

### Implementation
- **Class**: `FormatDetector`
- **Location**: [`src/parsers/format_detector.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/parsers/format_detector.py)

---

## 2. 📄 File Parsing

**Parse files** into structured DataFrames.

### Command
```bash
cm3-batch parse -f <file> [-t <format>] [-o <output>]
```

### Options
- `-f, --file`: Input file path (required)
- `-t, --format`: Format type (`pipe`, `fixed`, auto-detect if omitted)
- `-o, --output`: Output CSV file (stdout if omitted)

### Supported Parsers

#### Pipe-Delimited Parser
```bash
cm3-batch parse -f data.txt -t pipe -o output.csv
```

**Features:**
- Automatic delimiter detection
- Header row detection
- Column name normalization

#### Fixed-Width Parser
```bash
cm3-batch parse -f data.txt -t fixed -o output.csv
```

**Features:**
- Position-based field extraction
- Length-based parsing
- Handles no delimiters

### Auto-Detection
```bash
# Automatically detects format
cm3-batch parse -f data.txt -o output.csv
```

### Implementation
- **Base Class**: `BaseParser`
- **Pipe Parser**: `PipeDelimitedParser`
- **Fixed Parser**: `FixedWidthParser`
- **Location**: [`src/parsers/`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/parsers/)

---

## 3. ✅ File Validation

**Validate file structure and content** against rules.

### Command
```bash
cm3-batch validate -f <file> [-m <mapping>]
```

### Options
- `-f, --file`: File to validate (required)
- `-m, --mapping`: Mapping file for schema validation (optional)

### Validation Types

#### 1. Structure Validation
- File format correctness
- Column count consistency
- Data type validation

#### 2. Schema Validation (with mapping)
- Required fields present
- Data types match
- Validation rules pass

### Example
```bash
cm3-batch validate -f data.txt -m config/mappings/customer_mapping.json
```

### Validation Rules

#### Available Rules
1. **`not_null`** - Field must have value
2. **`min_length`** - Minimum string length
3. **`max_length`** - Maximum string length
4. **`regex`** - Pattern matching
5. **`range`** - Numeric range
6. **`in_list`** - Value in allowed list

See [`docs/VALIDATION_RULES.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/VALIDATION_RULES.md) for details.

### Output
```
✓ File is valid

Warnings:
  Optional column missing: middle_name
```

### Implementation
- **Class**: `FileValidator`
- **Location**: [`src/parsers/validator.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/parsers/validator.py)

---

## 4. 🔍 File Comparison

**Compare two files** and identify differences at row and field level.

### Command
```bash
cm3-batch compare -f1 <file1> -f2 <file2> -k <keys> [-o <report>] [-t <thresholds>] [--detailed]
```

### Options
- `-f1, --file1`: First file (required)
- `-f2, --file2`: Second file (required)
- `-k, --keys`: Key columns for matching (comma-separated, required)
- `-o, --output`: HTML report output path (optional)
- `-t, --thresholds`: Threshold configuration file (optional)
- `--detailed/--basic`: Detailed field analysis (default: detailed)

### How File Comparison Works

#### Step 1: Parse Both Files
```
File 1: source_data.txt → DataFrame 1
File 2: target_data.txt → DataFrame 2
```

#### Step 2: Identify Unique Rows
- **Only in File 1**: Rows with keys not in File 2
- **Only in File 2**: Rows with keys not in File 1

#### Step 3: Find Matching Rows
- Merge on key columns
- Compare all non-key fields

#### Step 4: Analyze Differences

##### Basic Mode
- Reports which fields differ
- Shows old vs new values

##### Detailed Mode
- **String Analysis**:
  - Length difference
  - Case-only differences
  - Whitespace differences
  
- **Numeric Analysis**:
  - Absolute difference
  - Percent change
  - Sign change detection

- **Field Statistics**:
  - Count of differences per field
  - Most different field
  - Difference type distribution

### Example

```bash
cm3-batch compare \
  -f1 data/source.txt \
  -f2 data/target.txt \
  -k customer_id,account_num \
  -o report.html \
  --detailed
```

### Output

```
Comparison Summary:
  Total rows (File 1): 1000
  Total rows (File 2): 1005
  Matching rows: 950
  Only in File 1: 25
  Only in File 2: 30
  Rows with differences: 25

Field-Level Statistics:
  Fields with differences: 5
  Most different field: amount

Threshold Evaluation:
  ✓ PASS
```

### Comparison Results Structure

```json
{
  "only_in_file1": [...],
  "only_in_file2": [...],
  "differences": [
    {
      "keys": {"customer_id": "CUST001"},
      "differences": {
        "amount": {
          "file1": 100.50,
          "file2": 150.75,
          "type": "value_difference",
          "numeric_analysis": {
            "absolute_difference": 50.25,
            "percent_change": 50.0,
            "sign_change": false
          }
        }
      },
      "difference_count": 1
    }
  ],
  "field_statistics": {
    "fields_with_differences": 5,
    "field_difference_counts": {
      "amount": 15,
      "status": 10
    },
    "most_different_field": "amount"
  }
}
```

### Threshold Evaluation

Define acceptable difference thresholds:

**`config/thresholds.json`:**
```json
{
  "thresholds": {
    "max_missing_rows": 10,
    "max_extra_rows": 10,
    "max_different_rows": 50,
    "max_difference_percentage": 5.0
  }
}
```

**Usage:**
```bash
cm3-batch compare -f1 file1.txt -f2 file2.txt -k id -t config/thresholds.json
```

### HTML Report Generation

When `-o report.html` is specified, generates interactive HTML report with:
- Summary statistics
- Detailed difference tables
- Field-level analysis
- Visual charts (if available)

### Implementation
- **Comparator**: `FileComparator`
- **Reporter**: `HTMLReporter`
- **Thresholds**: `ThresholdEvaluator`
- **Location**: 
  - [`src/comparators/file_comparator.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/comparators/file_comparator.py)
  - [`src/reporters/html_reporter.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/reporters/html_reporter.py)
  - [`src/validators/threshold.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/validators/threshold.py)

---

## 5. 🗄️ Oracle Data Extraction

**Extract data from Oracle database** to files.

### Command
```bash
cm3-batch extract -t <table> -o <output> [-l <limit>] [-d <delimiter>]
```

### Options
- `-t, --table`: Table name to extract (required)
- `-o, --output`: Output file path (required)
- `-l, --limit`: Limit number of rows (optional)
- `-d, --delimiter`: Output delimiter (default: `|`)

### Features

#### 1. Full Table Extraction
```bash
cm3-batch extract -t CUSTOMERS -o customers.txt
```

**Features:**
- Chunked processing for large tables
- Memory-efficient streaming
- Progress tracking

#### 2. Limited Extraction
```bash
cm3-batch extract -t CUSTOMERS -o sample.txt -l 1000
```

**Features:**
- Extract first N rows
- Useful for sampling/testing

#### 3. Custom Delimiter
```bash
cm3-batch extract -t CUSTOMERS -o customers.csv -d ","
```

### Output
```
Extracting from table: CUSTOMERS
Extracted 50000 rows to customers.txt
Chunks written: 5
✓ Extraction complete
```

### Environment Setup

**`.env` file:**
```bash
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
ORACLE_DSN=localhost:1521/ORCLPDB1
```

### Implementation
- **Connection**: `OracleConnection`
- **Extractor**: `DataExtractor`
- **Location**: 
  - [`src/database/connection.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/database/connection.py)
  - [`src/database/extractor.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/database/extractor.py)

---

## 6. 🔗 Mapping Reconciliation

**Validate mapping files** against Oracle database schema.

### Command
```bash
cm3-batch reconcile -m <mapping>
```

### Options
- `-m, --mapping`: Mapping file to validate (required)

### What It Checks

#### 1. Table Existence
- Target table exists in database

#### 2. Column Existence
- All mapped columns exist in table

#### 3. Data Type Compatibility
- Mapping data types match database types

#### 4. Nullable Constraints
- Required fields match NOT NULL constraints

#### 5. Length Constraints
- String lengths within database limits

### Example
```bash
cm3-batch reconcile -m config/mappings/customer_mapping.json
```

### Output
```
Reconciling mapping: customer_file_to_db
Target table: CUSTOMER_DATA

✓ Mapping is valid

Warnings:
  Column EMAIL: validation max_length (100) exceeds database length (50)
  Required database columns not in mapping: [CREATED_DATE]

Mapped columns: 7
Database columns: 8
```

### Implementation
- **Class**: `SchemaReconciler`
- **Location**: [`src/database/reconciliation.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/database/reconciliation.py)

---

## 7. 🌐 REST API

**HTTP API** for file processing and mapping management.

### Starting the API

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### File Operations

**Upload and Parse File**
```http
POST /api/v1/files/upload
Content-Type: multipart/form-data

file: <file>
format: pipe_delimited (optional)
```

**List Files**
```http
GET /api/v1/files/
```

**Get File Info**
```http
GET /api/v1/files/{file_id}
```

#### Mapping Operations

**Upload Excel Template**
```http
POST /api/v1/mappings/upload
Content-Type: multipart/form-data

file: <excel_file>
mapping_name: my_mapping (optional)
file_format: fixed_width (optional)
```

**List Mappings**
```http
GET /api/v1/mappings/
```

**Get Mapping**
```http
GET /api/v1/mappings/{mapping_id}
```

**Validate Mapping**
```http
POST /api/v1/mappings/validate
Content-Type: application/json

{mapping_json}
```

**Delete Mapping**
```http
DELETE /api/v1/mappings/{mapping_id}
```

#### System Operations

**Health Check**
```http
GET /api/v1/system/health
```

**System Info**
```http
GET /api/v1/system/info
```

### Implementation
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Location**: [`src/api/`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/api/)

See [`docs/API_UPLOAD_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/API_UPLOAD_GUIDE.md) for details.

---

## 8. 📊 Reporting

**Generate HTML reports** for comparison results.

### Features
- Interactive HTML reports
- Summary statistics
- Detailed difference tables
- Field-level analysis
- Threshold evaluation results

### Usage
```bash
cm3-batch compare -f1 file1.txt -f2 file2.txt -k id -o report.html
```

### Report Sections
1. **Summary**: Overall statistics
2. **Unique Rows**: Rows only in one file
3. **Differences**: Field-level changes
4. **Field Statistics**: Most changed fields
5. **Threshold Results**: Pass/fail status

### Implementation
- **Class**: `HTMLReporter`
- **Location**: [`src/reporters/html_reporter.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/reporters/html_reporter.py)

---

## 9. ✅ Business Rules Validation (New!)

**Execute complex business logic** against file data.

### Command
```bash
cm3-batch validate -f <file> -r <rules_config> -o <report>
```

### Options
- `-f, --file`: File to validate (required)
- `-r, --rules`: Business rules JSON configuration (optional)
- `-o, --output`: HTML report output path (optional)

### Features

#### 1. Rule Definition
Define rules in JSON or convert from Excel templates:

**Excel Template → JSON:**
```bash
cm3-batch convert-rules \
  -t config/templates/p327_rules.xlsx \
  -o config/rules/p327_rules.json
```

#### 2. Rule Types

**Field Validation:**
- `not_null`: Field must have a value
- `range`: Numeric range checks
- `regex`: Pattern matching
- `in_list`: Value must be in allowed list
- `length`: String length constraints

**Cross-Field Validation:**
- `field_comparison`: Compare two fields (e.g., `end_date > start_date`)
- `depends_on`: Conditional requirements
- `mutually_exclusive`: Only one field can have a value

**Example Rule:**
```json
{
  "rule_id": "R001",
  "rule_name": "Account Number Format",
  "type": "field_validation",
  "severity": "error",
  "field": "ACCT-NUM",
  "operator": "regex",
  "value": "^[0-9]{10}$"
}
```

#### 3. Validation Execution
```bash
cm3-batch validate \
  -f data/p327_test.txt \
  -m config/mappings/p327.json \
  -r config/rules/p327_rules.json \
  -o reports/validation.html
```

### Output

The HTML report includes:
- **Summary Metrics**: Total rules, violations, compliance rate
- **Violations by Rule**: Grouped by rule ID with severity badges
- **Detailed Violations**: Row numbers, fields, values, and expected outcomes

### Implementation
- **Engine**: `RuleEngine`
- **Validators**: `FieldValidator`, `CrossFieldValidator`
- **Converter**: `RulesTemplateConverter`
- **Location**: 
  - [`src/validators/rule_engine.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/validators/rule_engine.py)
  - [`src/validators/field_validator.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/validators/field_validator.py)
  - [`src/config/rules_template_converter.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/config/rules_template_converter.py)

---

## 10. 🔍 Source Data Verification (New!)

**Validate generated files** against trusted source data using custom SQL.

### Command
```bash
cm3-batch extract --sql-file <query.sql> -o <output>
```

### Options
- `-t, --table`: Table name (for simple extraction)
- `-q, --query`: Inline SQL query
- `-s, --sql-file`: Path to SQL file
- `-o, --output`: Output file path (required)
- `-d, --delimiter`: Output delimiter (default: `|`)

### Extraction Modes

#### 1. Table Mode (Original)
```bash
cm3-batch extract -t CUSTOMERS -o customers.txt
```

#### 2. SQL File Mode (New!)
```bash
cm3-batch extract \
  --sql-file config/queries/p327_source.sql \
  -o trusted_p327.txt \
  -d "|"
```

#### 3. Inline Query Mode (New!)
```bash
cm3-batch extract \
  --query "SELECT a.account_number FROM accounts a WHERE a.status = 'ACTIVE'" \
  -o active_accounts.txt
```

### Trusted Source Verification Workflow

**Step 1: Define Source Logic**

Create `config/queries/p327_source.sql`:
```sql
SELECT 
    l.location_code AS "LOCATION-CODE",
    a.account_number AS "ACCT-NUM",
    c.currency_code AS "BASE-CURRENCY"
FROM accounts a
JOIN locations l ON a.location_id = l.id
JOIN currencies c ON a.currency_id = c.id
WHERE a.status = 'ACTIVE'
  AND a.balance > 0
ORDER BY a.account_number
```

**Step 2: Extract Trusted Source**
```bash
cm3-batch extract \
  --sql-file config/queries/p327_source.sql \
  -o trusted_p327.txt
```

**Step 3: Compare with Generated File**
```bash
cm3-batch compare \
  -f1 generated_p327.txt \
  -f2 trusted_p327.txt \
  -k account_number \
  -o verification_report.html
```

### Use Cases

1. **Validate Filter Logic**: Ensure generated files contain only expected records
2. **Verify Joins**: Confirm join logic produces correct results
3. **Check Transformations**: Validate data transformations match business rules
4. **Audit Data**: Create audit trail by comparing against source

### Implementation
- **Extractor**: `DataExtractor.extract_to_file` (enhanced)
- **Location**: [`src/database/extractor.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/database/extractor.py)

---

## 🛠️ System Information

**Check system configuration** and dependencies.

### Command
```bash
cm3-batch info
```

### Output
```
CM3 Batch Automations v0.1.0
Python version: 3.11.5
Working directory: /path/to/project
oracledb version: 2.0.1
✓ Oracle connectivity available (thin mode)
```

---

## 📚 Complete CLI Reference

### All Commands

| Command | Description |
|---------|-------------|
| `detect` | Detect file format |
| `parse` | Parse file to CSV |
| `validate` | Validate file structure |
| `compare` | Compare two files |
| `extract` | Extract Oracle data |
| `reconcile` | Validate mapping |
| `info` | System information |

### Global Options
- `--version`: Show version
- `--help`: Show help message

---

## 🔧 Configuration Files

### Mapping Files
**Location**: `config/mappings/*.json`

Define how to map source files to database tables.

See:
- [`docs/MAPPING_QUICKSTART.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/MAPPING_QUICKSTART.md)
- [`docs/UNIVERSAL_MAPPING_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/UNIVERSAL_MAPPING_GUIDE.md)

### Threshold Files
**Location**: `config/thresholds.json`

Define acceptable difference thresholds for comparisons.

### Environment Files
**Location**: `.env`

Store Oracle credentials and configuration.

---

## 📖 Additional Documentation

- **Transformations**: [`docs/TRANSFORMATION_TYPES.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/TRANSFORMATION_TYPES.md)
- **Validations**: [`docs/VALIDATION_RULES.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/VALIDATION_RULES.md)
- **Oracle Setup**: [`docs/ORACLE_RHEL_SETUP.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/ORACLE_RHEL_SETUP.md)
- **API Guide**: [`docs/API_UPLOAD_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/API_UPLOAD_GUIDE.md)
- **Usage Guide**: [`docs/USAGE_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/USAGE_GUIDE.md)
- **Testing Guide**: [`docs/TESTING_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/TESTING_GUIDE.md)

---

## 💡 Common Workflows

### Workflow 1: Process New File Type

```bash
# 1. Detect format
cm3-batch detect -f newfile.txt

# 2. Parse to CSV
cm3-batch parse -f newfile.txt -o parsed.csv

# 3. Validate structure
cm3-batch validate -f newfile.txt
```

### Workflow 2: Compare Source vs Target

```bash
# 1. Extract from Oracle
cm3-batch extract -t SOURCE_TABLE -o source.txt

# 2. Compare with target file
cm3-batch compare \
  -f1 source.txt \
  -f2 target.txt \
  -k customer_id \
  -o comparison_report.html \
  -t config/thresholds.json
```

### Workflow 3: Create and Validate Mapping

```bash
# 1. Upload Excel template via API
curl -X POST http://localhost:8000/api/v1/mappings/upload \
  -F "file=@template.xlsx" \
  -F "mapping_name=my_mapping"

# 2. Reconcile with database
cm3-batch reconcile -m config/mappings/my_mapping.json
```

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Oracle connection
cp .env.example .env
# Edit .env with your credentials

# Test Oracle connection
python test_oracle_connection.py

# Run CLI
cm3-batch --help

# Start API
uvicorn src.api.main:app --reload
```
