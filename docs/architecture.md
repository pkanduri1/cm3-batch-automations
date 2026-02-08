# CM3 Batch Automations - Architecture

## Overview

CM3 Batch Automations is a comprehensive Python-based system for automated file parsing, validation, and comparison workflows. The system features a **universal mapping structure**, **REST API with Swagger UI**, and **Oracle database integration**.

---

## Technology Stack

### Core Frameworks
- **Python 3.9+**: Primary programming language
- **FastAPI**: Modern REST API framework with automatic OpenAPI documentation
- **Pandas**: Data manipulation and analysis
- **Pydantic**: Data validation and settings management
- **cx_Oracle**: Oracle database connectivity

### API & Web
- **Uvicorn**: ASGI server for FastAPI
- **Starlette**: ASGI framework (FastAPI dependency)
- **python-multipart**: File upload support
- **aiofiles**: Async file operations

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
- **pylint**: Code analysis

### Additional Libraries
- **Jinja2**: HTML template rendering
- **click**: CLI interface
- **python-dotenv**: Environment variable management
- **openpyxl**: Excel file processing

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Swagger UI  │  │  CLI Tools   │  │  Python SDK  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    REST API Layer (FastAPI)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Mappings   │  │    Files     │  │   System     │      │
│  │   Endpoints  │  │  Endpoints   │  │  Endpoints   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Universal  │  │    Format    │  │     File     │      │
│  │   Mapping    │  │   Detector   │  │  Comparator  │      │
│  │   Parser     │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Template   │  │  Validators  │  │   Reporters  │      │
│  │  Converter   │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Access Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Parsers   │  │   Database   │  │    Config    │      │
│  │  (Fixed-     │  │  Connection  │  │    Loader    │      │
│  │   Width,     │  │   (Oracle)   │  │              │      │
│  │  Delimited)  │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. REST API Layer (`src/api/`)

**Purpose**: Provide RESTful API access to all system functionality

#### Main Application (`main.py`)
- FastAPI application with CORS middleware
- Global exception handling
- Auto-generated OpenAPI documentation
- Swagger UI at `/docs`
- ReDoc at `/redoc`

#### Pydantic Models (`models/`)
- **mapping.py**: Mapping request/response models
  - `MappingCreate`, `MappingResponse`, `FieldSpec`
  - `ValidationResult`, `UploadResponse`
- **file.py**: File operation models
  - `FileDetectionResult`, `FileParseResult`
  - `FileCompareResult`, `FileValidationResult`
- **response.py**: Common response models
  - `SuccessResponse`, `ErrorResponse`
  - `HealthResponse`, `SystemInfoResponse`

#### Routers (`routers/`)

**Mappings Router** (`mappings.py`)
- `POST /api/v1/mappings/upload` - Upload Excel/CSV template
- `GET /api/v1/mappings/` - List all mappings
- `GET /api/v1/mappings/{id}` - Get mapping by ID
- `POST /api/v1/mappings/validate` - Validate mapping
- `DELETE /api/v1/mappings/{id}` - Delete mapping

**Files Router** (`files.py`)
- `POST /api/v1/files/detect` - Detect file format
- `POST /api/v1/files/parse` - Parse file with mapping
- `POST /api/v1/files/compare` - Compare two files

**System Router** (`system.py`)
- `GET /api/v1/system/health` - Health check
- `GET /api/v1/system/info` - System information

---

### 2. Universal Mapping System (`src/config/`)

**Purpose**: Standardized mapping structure for all file formats

#### Universal Mapping Parser (`universal_mapping_parser.py`)
- Parse universal mapping JSON files
- Extract field positions for fixed-width files
- Extract column names for delimited files
- Validate mapping schema
- Get transformations and validations

**Key Methods**:
```python
get_format() -> str
get_field_positions() -> List[Tuple[str, int, int]]
get_column_names() -> List[str]
validate_schema() -> Dict[str, Any]
get_transformations(field_name: str) -> List[Dict]
```

#### Template Converter (`template_converter.py`)
- Convert Excel/CSV templates to universal mappings
- Auto-detect file format (fixed-width vs delimited)
- Normalize data types
- Generate field specifications

**Key Methods**:
```python
from_excel(excel_path: str) -> dict
from_csv(csv_path: str) -> dict
save(output_path: str)
```

#### Mapping Schema (`config/schemas/`)
- **universal_mapping_schema.json**: JSON Schema definition
- Supports all file formats (pipe-delimited, fixed-width, CSV, TSV)
- Field-level specifications (position, length, type)
- Transformations and validation rules

---

### 3. Parsers (`src/parsers/`)

**Purpose**: Parse different file formats into standardized DataFrames

#### Base Parser (`base_parser.py`)
- Abstract interface defining parsing contract
- Common functionality for all parsers

#### Format Detector (`format_detector.py`)
- Auto-detect file format
- Confidence scoring
- Sample line analysis

**Detection Methods**:
- `_score_pipe_delimited()`: Score pipe-delimited likelihood
- `_score_fixed_width()`: Score fixed-width likelihood
- `_score_csv()`: Score CSV likelihood
- `_score_tsv()`: Score TSV likelihood

#### Specific Parsers
- **PipeDelimitedParser**: Handles pipe-delimited (|) files
- **FixedWidthParser**: Handles fixed-width format files
- **CSVParser**: Handles comma-separated values
- **TSVParser**: Handles tab-separated values

**Key Methods**:
```python
parse() -> pd.DataFrame
validate_format() -> bool
get_metadata() -> Dict[str, Any]
```

---

### 4. Database Layer (`src/database/`)

**Purpose**: Manage Oracle database connections and operations

#### Oracle Connection (`connection.py`)
- Connection management with context manager
- Environment variable configuration
- Connection pooling support
- Transaction management

**Key Methods**:
```python
from_env() -> OracleConnection
execute_query(query: str) -> pd.DataFrame
commit()
rollback()
```

#### Query Executor (`query_executor.py`)
- Execute queries and return DataFrames
- Parameterized queries for security
- Batch operations support

---

### 5. Validators (`src/validators/`)

**Purpose**: Validate data integrity and mappings

#### Mapping Validator (`mapping_validator.py`)
- Validate file-to-database column mappings
- Column existence validation
- Data type validation
- Mapping completeness checks

#### Schema Reconciliation
- Compare mapping with database schema
- Identify missing columns
- Validate data type compatibility

---

### 6. Comparators (`src/comparators/`)

**Purpose**: Compare files and identify differences

#### File Comparator (`file_comparator.py`)
- Compare two DataFrames based on key columns
- Identify rows unique to each file
- Find rows with matching keys but different values
- Generate field-level statistics

**Comparison Features**:
```python
compare(detailed: bool = False) -> Dict[str, Any]
get_differences() -> pd.DataFrame
get_field_statistics() -> Dict[str, int]
```

---

### 7. Reporters (`src/reporters/`)

**Purpose**: Generate reports from processing results

#### HTML Reporter (`html_reporter.py`)
- Generate HTML comparison reports
- Jinja2 template rendering
- Summary statistics
- Detailed difference tables

**Report Contents**:
- Total rows compared
- Matching/differing rows
- Field-level differences
- Timestamps and metadata

---

### 8. Utilities (`src/utils/`)

**Purpose**: Common utilities and helpers

#### Logger (`logger.py`)
- Centralized logging configuration
- Console and file logging
- Log rotation
- Configurable log levels

---

## Data Flow

### 1. Mapping Creation Flow
```
Excel/CSV Template
    ↓
Template Converter
    ↓
Universal Mapping JSON
    ↓
Universal Mapping Parser
    ↓
Field Specifications
```

### 2. File Parsing Flow
```
Data File
    ↓
Format Detector (auto-detect)
    ↓
Appropriate Parser (Fixed-Width/Delimited)
    ↓
pandas DataFrame
    ↓
Validation
    ↓
Output (CSV/JSON/Excel)
```

### 3. File Comparison Flow
```
File 1 + File 2
    ↓
Parse both files
    ↓
File Comparator
    ↓
Difference Analysis
    ↓
HTML Report
```

### 4. API Request Flow
```
HTTP Request (Swagger UI/Client)
    ↓
FastAPI Router
    ↓
Pydantic Validation
    ↓
Business Logic Layer
    ↓
Data Access Layer
    ↓
HTTP Response (JSON)
```

---

## Configuration Management

### Universal Mapping Configuration
- **Location**: `config/mappings/*.json`
- **Schema**: `config/schemas/universal_mapping_schema.json`
- **Templates**: `config/templates/*.json`

### Environment-Based Configuration
- `config/dev.json`: Development settings
- `config/staging.json`: Staging settings
- `.env`: Environment variables (credentials)

### Configuration Hierarchy
1. Environment variables (highest priority)
2. Environment-specific JSON files
3. Universal mapping files
4. Default values in code

---

## Error Handling

### API Layer
- **Pydantic Validation**: Automatic request/response validation
- **HTTP Exceptions**: Proper status codes (400, 404, 500)
- **Global Exception Handler**: Catch-all for unhandled errors

### Business Logic Layer
- **File Parsing Errors**: Caught and logged with file context
- **Database Errors**: Connection and query errors handled gracefully
- **Validation Errors**: Detailed error messages with field information

---

## Logging Strategy

### Structured Logging
- **Console Logging**: Real-time feedback during execution
- **File Logging**: Persistent logs in `logs/` directory
- **API Request Logging**: All API requests logged
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Timestamp-based log files

### Log Format
```
[TIMESTAMP] [LEVEL] [MODULE] - MESSAGE
```

---

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Coverage target: 80% minimum

### Integration Tests
- Test component interactions
- Test API endpoints
- Test database operations

### API Testing
- Swagger UI for manual testing
- Automated tests with pytest
- Request/response validation

### Test Fixtures
- Reusable test data
- Mock mappings
- Sample files

---

## Performance Considerations

### Data Processing
- **Pandas**: Efficient DataFrame operations
- **Chunked Processing**: For large files
- **Lazy Loading**: Load data only when needed

### Database
- **Connection Pooling**: Reuse connections
- **Parameterized Queries**: Prevent SQL injection
- **Batch Operations**: Bulk inserts/updates

### API
- **Async Operations**: Non-blocking file operations with aiofiles
- **Background Tasks**: For long-running operations
- **File Upload Limits**: Configurable size limits

---

## Security

### API Security
- **CORS**: Configurable allowed origins
- **File Upload Validation**: File type and size checks
- **Input Validation**: Pydantic models validate all inputs

### Database Security
- **Credentials**: Stored in environment variables
- **SQL Injection**: Parameterized queries only
- **Connection Encryption**: SSL/TLS support

### File Security
- **Path Validation**: Prevent directory traversal
- **Temporary Files**: Automatic cleanup
- **Sanitization**: Remove sensitive data from logs

---

## Extensibility

### Adding New File Formats
1. Create parser class inheriting from `BaseParser`
2. Implement `parse()` and `validate_format()` methods
3. Add to format detector scoring
4. Update universal mapping schema if needed

### Adding New API Endpoints
1. Create Pydantic models in `src/api/models/`
2. Add router in `src/api/routers/`
3. Include router in `main.py`
4. Documentation auto-generated

### Adding New Transformations
1. Add transformation type to schema
2. Implement in universal mapping parser
3. Add tests

### Adding New Validators
1. Create validator class in `src/validators/`
2. Implement validation logic
3. Add to validation pipeline

---

## Dependencies

### Production Dependencies
```
fastapi>=0.109.0              # REST API framework
uvicorn[standard]>=0.27.0     # ASGI server
pydantic>=2.5.0               # Data validation
pandas>=1.5.0                 # Data manipulation
cx_Oracle>=8.3.0              # Oracle connectivity
python-multipart>=0.0.6       # File uploads
aiofiles>=23.2.1              # Async file operations
Jinja2>=3.0.0                 # Template rendering
click>=8.0.0                  # CLI interface
python-dotenv>=0.19.0         # Environment variables
openpyxl>=3.1.0               # Excel processing
```

### Development Dependencies
```
pytest>=7.0.0                 # Testing
pytest-cov>=3.0.0             # Coverage
black>=22.0.0                 # Formatting
flake8>=4.0.0                 # Linting
mypy>=0.950                   # Type checking
pylint>=2.13.0                # Code analysis
```

---

## Deployment Architecture

### Development
```
uvicorn src.api.main:app --reload --port 8000
```

### Production
```
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment Options
- **AWS**: Lambda + API Gateway, ECS, or EC2
- **Azure**: App Service or Container Instances
- **Google Cloud**: Cloud Run or App Engine
- **On-Premise**: Docker containers with reverse proxy

---

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Features
- Try-it-out functionality
- Request/response examples
- Schema validation
- Authentication support (future)

---

## Future Enhancements

### Completed ✅
- ~~CLI interface with Click~~ ✅
- ~~Additional file format support (CSV, Excel)~~ ✅
- ~~REST API interface~~ ✅
- ~~Universal mapping structure~~ ✅

### Planned
- [ ] WebSocket support for real-time progress
- [ ] Background job processing with Celery
- [ ] Database write operations
- [ ] Scheduled batch processing
- [ ] Email notifications
- [ ] Authentication (API keys, JWT)
- [ ] Rate limiting
- [ ] Caching layer (Redis)
- [ ] Metrics and monitoring (Prometheus)
- [ ] GraphQL API option

---

## Version History

- **v1.0.0** (2026-02-07): REST API with FastAPI, Universal Mapping Structure
- **v0.9.0**: P327 mapping support, Excel template conversion
- **v0.8.0**: Initial CLI implementation
- **v0.7.0**: File comparison and HTML reporting
- **v0.6.0**: Oracle database integration
- **v0.5.0**: Basic file parsing (pipe-delimited, fixed-width)
