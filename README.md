# CM3 Batch Automations

Automated file parsing, validation, and comparison tool for CM3 batch processing with Oracle database integration and REST API.

## Features

### Core Capabilities
- **Universal Mapping Structure**: Standardized mapping format for all file types (pipe-delimited, fixed-width, CSV, TSV)
- **Template-Based Configuration**: Create mappings from Excel/CSV templates without custom scripts
- **File Parsing**: Support for multiple file formats with auto-detection
- **Database Integration**: Oracle database connectivity with `oracledb` (thin mode supported)
- **Data Validation**: Comprehensive validation with interactive HTML reports
- **File Comparison**: Compare files and identify differences with field-level analysis
- **HTML Reporting**: Generate detailed comparison and validation reports
- **REST API**: FastAPI-based REST API with Swagger UI (interactive documentation)

### Validation Features (New!)
- **Interactive Field-Level Analysis**: Search, sort, and paginate through field statistics
- **Date Field Detection**: Automatic detection of date fields with YYYYMMDD format support
- **Data Quality Metrics**: Overall quality score, completeness, and uniqueness tracking
- **Visual Dashboards**: Chart.js-powered visualizations and quality gauges
- **Detailed Appendix**: Validation configuration, mapping details, and affected rows summary
- **Duplicate Detection**: Identify and report duplicate records
- **Issue Categorization**: Errors, warnings, and info messages with field-level details
- **Business Rule Validation**: Execute complex validation rules defined in Excel/CSV templates

### Advanced Features
- **Configurable**: JSON-based configuration for different environments
- **Transaction Management**: Full transaction support with rollback and savepoints
- **Schema Reconciliation**: Validate mappings against database schema
- **Threshold Evaluation**: Configurable pass/fail criteria
- **CLI Interface**: Command-line tools for all operations
- **API Interface**: RESTful API for web-based access and integration
- **Source Data Verification**: Validate generated files against trusted source data using custom SQL queries

## Quick Start

### CLI Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Check system info
cm3-batch info

# Detect file format
cm3-batch detect -f data/samples/customers.txt

# Parse file
cm3-batch parse -f data/samples/customers.txt

# Parse with chunked processing (large files)
cm3-batch parse -f data/samples/customers.txt --use-chunked --chunk-size 50000 -o reports/parsed.csv

# Validate file with HTML report
cm3-batch validate -f data/samples/customers.txt -m config/mappings/customer_mapping.json -o reports/validation.html --detailed

# Validate with chunked processing (large files)
cm3-batch validate -f data/samples/customers.txt -m config/mappings/customer_mapping.json --use-chunked -o reports/validation.json

# Compare files
cm3-batch compare -f1 file1.txt -f2 file2.txt -k customer_id -o report.html

# Validate mapping against database
cm3-batch reconcile -m config/mappings/customer_mapping.json

# Validate all mappings in a directory
cm3-batch reconcile-all -d config/mappings -o reports/reconcile_all.json

# Detect reconciliation drift vs baseline
cm3-batch reconcile-all -d config/mappings -o reports/reconcile_all_new.json \
  --baseline reports/reconcile_all_baseline.json --fail-on-drift

# Extract data from database
cm3-batch extract -t CUSTOMER -o output.txt -l 1000

# Convert business rules template
cm3-batch convert-rules -t config/templates/rules.xlsx -o config/rules.json
```

### Batch Automation Scripts

```bash
# 1) Convert all mapping templates from mappings/csv -> config/mappings
#    Strict mode: malformed rows fail conversion and produce row-level CSV reports
#    under reports/template_validation/*.errors.csv
./scripts/run_convert_mappings.sh

# 2) Convert all rules templates from rules/csv -> config/rules
#    Strict mode: malformed rows fail conversion and produce row-level CSV reports
#    under reports/template_validation/*.errors.csv
./scripts/run_convert_rules.sh

# 3) Validate all data files based on manifest mapping
./scripts/run_validate_all.sh config/validation_manifest.csv

# 4) Validate with auto-discovery fallback (if manifest missing)
./scripts/run_validate_all.sh config/validation_manifest.csv true
```

Manifest recommendation: **CSV** (not .properties), because QA teams can edit it easily in Excel.

Starter sample files checked in:

- `mappings/csv/mapping_template.sample.csv`
- `rules/csv/rules_template.sample.csv`
- `config/validation_manifest.sample.csv`

Sample manifest columns:

- `data_file` (required)
- `mapping_file` (required)
- `rules_file` (optional)
- `report_file` (optional)
- `chunked` (optional)
- `chunk_size` (optional)

### Business Rule Validation (Build Gate Friendly)

You can run validation with business rules JSON and fail builds when violations are found:

```bash
cm3-batch validate \
  -f data/samples/customers.txt \
  -m config/mappings/customer_mapping.json \
  -r config/rules/p327_business_rules.json \
  -o reports/validation-with-rules.html \
  --detailed
```

### On-Prem Oracle Smoke Test (No Docker Required)

Set your Oracle credentials in `.env`:

```bash
ORACLE_USER=CM3INT
ORACLE_PASSWORD=<password>
ORACLE_DSN=<hostname>:1521/<service_name>
```

Create test objects and run parse -> validate -> load verification:

```bash
# Create test tables in CM3INT/CM3AUDIT
sqlplus system/<sys_password>@<hostname>:1521/<service_name> @scripts/setup_cm3_test_tables.sql

# Run smoke ETL
python scripts/cm3_smoke_etl.py
```

### Universal Mapping (New!)

```bash
# Convert Excel template to universal mapping
python src/config/template_converter.py \
  data/mappings/my_template.xlsx \
  config/mappings/my_mapping.json \
  my_mapping_name \
  fixed_width

# Validate mapping
python src/config/universal_mapping_parser.py \
  config/mappings/my_mapping.json
```

### Standardized CSV -> Mapping JSON + Rules JSON

Use standardized CSV templates:
- `config/templates/csv/mapping_template.standard.csv`
- `config/templates/csv/business_rules_template.standard.csv`

Generate JSON artifacts from CSV in one command:

```bash
python scripts/generate_from_csv_templates.py \
  --mapping-csv config/templates/csv/mapping_template.standard.csv \
  --mapping-out config/mappings/customer_batch_universal.json \
  --mapping-name customer_batch_universal \
  --mapping-format pipe_delimited \
  --rules-csv config/templates/csv/business_rules_template.standard.csv \
  --rules-out config/rules/customer_business_rules.json
```

### REST API (New!)

```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Access Swagger UI
open http://localhost:8000/docs

# Example API calls
curl -X POST "http://localhost:8000/api/v1/mappings/upload" \
  -F "file=@template.xlsx" \
  -F "mapping_name=my_mapping"

curl "http://localhost:8000/api/v1/mappings/"
```

## Project Structure

```
cm3-batch-automations/
├── src/                  # Source code
│   ├── api/             # REST API (FastAPI)
│   │   ├── main.py      # API application
│   │   ├── models/      # Pydantic models
│   │   ├── routers/     # API endpoints
│   │   └── services/    # Business logic
│   ├── parsers/         # File parsers
│   ├── database/        # Oracle DB connectivity
│   ├── validators/      # Validation logic
│   ├── comparators/     # File comparison
│   ├── config/          # Configuration management
│   │   ├── universal_mapping_parser.py  # Universal parser
│   │   └── template_converter.py        # Excel/CSV converter
│   ├── reporters/       # Report generation
│   └── utils/           # Utilities
├── tests/               # Test suite
├── config/              # Configuration files
│   ├── schemas/         # JSON schemas
│   ├── templates/       # Mapping templates
│   └── mappings/        # Universal mappings
├── data/                # Data directory
│   └── mappings/        # CSV/Excel mapping templates for new integrations
├── scripts/             # Utility scripts (smoke ETL, setup SQL, helpers)
├── uploads/             # API file uploads
├── logs/                # Log files
└── docs/                # Documentation
    ├── UNIVERSAL_MAPPING_GUIDE.md
    └── architecture.md
```

## Prerequisites

- **Python**: 3.9 or higher
- **pip**: Latest version
- **Oracle Database** access (on-prem, container, or managed)

> Note: the project uses `python-oracledb` and works in **thin mode** by default (no Oracle Instant Client required for basic connectivity).

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cm3-batch-automations
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .  # enables cm3-batch CLI command
```

### 4. (Optional) Install Oracle Instant Client

#### Windows

1. Download Oracle Instant Client from [Oracle website](https://www.oracle.com/database/technologies/instant-client/downloads.html)
2. Extract to `C:\oracle\instantclient_19_x`
3. Add to PATH:
   ```cmd
   setx PATH "%PATH%;C:\oracle\instantclient_19_x"
   ```

#### Linux

```bash
# Download and extract
wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linux.x64-19.x.x.x.zip
unzip instantclient-basic-linux.x64-19.x.x.x.zip -d /opt/oracle

# Set environment variables
export ORACLE_HOME=/opt/oracle/instantclient_19_x
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH

# Add to ~/.bashrc for persistence
echo 'export ORACLE_HOME=/opt/oracle/instantclient_19_x' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH' >> ~/.bashrc
echo 'export PATH=$ORACLE_HOME:$PATH' >> ~/.bashrc
```

#### macOS

```bash
# Download and extract
curl -O https://download.oracle.com/otn_software/mac/instantclient/instantclient-basic-macos.x64-19.x.x.x.zip
unzip instantclient-basic-macos.x64-19.x.x.x.zip -d ~/oracle

# Set environment variables
export ORACLE_HOME=~/oracle/instantclient_19_x
export DYLD_LIBRARY_PATH=$ORACLE_HOME:$DYLD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH

# Add to ~/.zshrc or ~/.bash_profile
echo 'export ORACLE_HOME=~/oracle/instantclient_19_x' >> ~/.zshrc
echo 'export DYLD_LIBRARY_PATH=$ORACLE_HOME:$DYLD_LIBRARY_PATH' >> ~/.zshrc
echo 'export PATH=$ORACLE_HOME:$PATH' >> ~/.zshrc
```

### 5. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your Oracle credentials
# ORACLE_USER=your_username
# ORACLE_PASSWORD=your_password
# ORACLE_DSN=hostname:port/service_name
```

## Configuration

### Database Configuration

Edit `config/dev.json` for development settings:

```json
{
  "database": {
    "username": "your_user",
    "dsn": "localhost:1521/XEPDB1",
    "encoding": "UTF-8"
  }
}
```

### Column Mappings

Create mapping files in `config/mappings/` to define file-to-database column mappings:

```json
{
  "file_column_1": "DB_COLUMN_1",
  "file_column_2": "DB_COLUMN_2"
}
```

## Usage

### Basic File Parsing

```python
from src.parsers.pipe_delimited_parser import PipeDelimitedParser

parser = PipeDelimitedParser("data/samples/input.txt")
df = parser.parse()
print(df.head())
```

### Database Connection

```python
from src.database.connection import OracleConnection
from src.database.query_executor import QueryExecutor

# Using environment variables
conn = OracleConnection.from_env()
executor = QueryExecutor(conn)

df = executor.execute_query("SELECT * FROM my_table WHERE rownum <= 10")
```

### File Comparison

```python
from src.comparators.file_comparator import FileComparator
from src.reporters.html_reporter import HTMLReporter

comparator = FileComparator(df1, df2, key_columns=["id"])
results = comparator.compare()

reporter = HTMLReporter()
reporter.generate(results, "reports/comparison_report.html")
```

### Universal Mapping Structure

```python
from src.config.universal_mapping_parser import UniversalMappingParser
from src.config.template_converter import TemplateConverter

# Convert Excel template to universal mapping
converter = TemplateConverter()
mapping = converter.from_excel(
    "data/mappings/my_template.xlsx",
    mapping_name="my_mapping",
    file_format="fixed_width"
)
converter.save("config/mappings/my_mapping.json")

# Use universal mapping
parser = UniversalMappingParser(mapping_path="config/mappings/my_mapping.json")

# Get field positions for fixed-width files
if parser.get_format() == 'fixed_width':
    positions = parser.get_field_positions()
    # Returns: [('FIELD1', 0, 10), ('FIELD2', 10, 25), ...]

# Get column names for delimited files
else:
    columns = parser.get_column_names()
    delimiter = parser.get_delimiter()

# Validate mapping
validation = parser.validate_schema()
if validation['valid']:
    print("✓ Mapping is valid")
```

### REST API Usage

```python
import requests

# Upload Excel template
with open('template.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/mappings/upload',
        files={'file': f},
        params={'mapping_name': 'my_mapping', 'file_format': 'fixed_width'}
    )
mapping = response.json()

# List all mappings
response = requests.get('http://localhost:8000/api/v1/mappings/')
mappings = response.json()

# Parse file
with open('data.txt', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/files/parse',
        files={'file': f},
        json={'mapping_id': 'my_mapping'}
    )
result = response.json()

# Compare files
with open('file1.txt', 'rb') as f1, open('file2.txt', 'rb') as f2:
    response = requests.post(
        'http://localhost:8000/api/v1/files/compare',
        files={'file1': f1, 'file2': f2},
        json={'mapping_id': 'my_mapping', 'key_columns': ['id']}
    )
comparison = response.json()
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_parsers.py

# Run with verbose output
pytest -v
```

## Development

### Code Formatting

```bash
# Format code with Black
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Linting

```bash
# Run flake8
flake8 src/ tests/

# Run pylint
pylint src/
```

### Type Checking

```bash
# Run mypy
mypy src/
```

## Logging

Logs are written to the `logs/` directory. Configure logging in your code:

```python
from src.utils.logger import setup_logger
import logging

logger = setup_logger("my_module", log_dir="logs", level=logging.INFO)
logger.info("Processing started")
```

## Troubleshooting

### Oracle Instant Client Issues

**Error: DPI-1047: Cannot locate a 64-bit Oracle Client library**

- Ensure Oracle Instant Client is installed
- Verify PATH/LD_LIBRARY_PATH includes Instant Client directory
- Restart terminal after setting environment variables

**Error: ORA-12154: TNS:could not resolve the connect identifier**

- Check DSN format: `hostname:port/service_name`
- Verify database is accessible from your network
- Check TNS_ADMIN environment variable if using tnsnames.ora

### Import Errors

- Ensure virtual environment is activated
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.9+)

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a merge request

## License

Internal use only.
