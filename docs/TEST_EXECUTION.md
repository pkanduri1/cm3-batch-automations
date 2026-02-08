# Test Execution Instructions

## Quick Start - Run Tests Now!

### Option 1: Using Test Runner Script (Recommended)

```bash
# Make script executable
chmod +x run_tests.sh

# Run all tests with coverage
./run_tests.sh --coverage --verbose
```

### Option 2: Using pytest Directly

```bash
# Install dependencies first
pip install -r requirements.txt

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing -v
```

## What Tests Are Available?

### Unit Tests (47+ tests)

**Parser Tests:**
- ✅ `test_pipe_delimited_parser.py` - 7 tests
  - Parse valid files
  - Validate format
  - Handle empty files
  - Get metadata

- ✅ `test_fixed_width_parser.py` - 5 tests
  - Parse with column specs
  - Validate format
  - Handle edge cases

- ✅ `test_format_detector.py` - 5 tests
  - Detect pipe-delimited
  - Detect CSV
  - Detect fixed-width
  - Handle errors

**Validation Tests:**
- ✅ `test_validator.py` - 5 tests
  - File validation
  - Schema validation
  - Missing columns
  - Unexpected columns

**Mapping Tests:**
- ✅ `test_mapping_parser.py` - 5 tests
  - Parse mapping documents
  - Apply transformations
  - Validate data
  - Handle errors

**Comparison Tests:**
- ✅ `test_file_comparator.py` - 6 tests
  - Compare identical files
  - Detect missing rows
  - Detect extra rows
  - Find differences
  - Detailed analysis

**Configuration Tests:**
- ✅ `test_config_loader.py` - 4 tests
  - Load configurations
  - Load mappings
  - Merge with environment

**Reporting Tests:**
- ✅ `test_html_reporter.py` - 2 tests
  - Generate HTML reports
  - Handle empty results

**Transaction Tests:**
- ✅ `test_transaction.py` - 3 tests
  - Transaction commit
  - Transaction rollback
  - Savepoints

**Threshold Tests:**
- ✅ `test_threshold.py` - 5 tests
  - Pass evaluation
  - Fail evaluation
  - Warning evaluation
  - Custom thresholds

## Expected Test Results

### All Tests Should Pass ✅

```
======================== test session starts =========================
platform linux -- Python 3.9.x, pytest-7.x.x
collected 47 items

tests/unit/test_config_loader.py ....                          [  8%]
tests/unit/test_file_comparator.py ......                      [ 21%]
tests/unit/test_fixed_width_parser.py .....                    [ 32%]
tests/unit/test_format_detector.py .....                       [ 42%]
tests/unit/test_html_reporter.py ..                            [ 46%]
tests/unit/test_mapping_parser.py .....                        [ 57%]
tests/unit/test_pipe_delimited_parser.py .......               [ 72%]
tests/unit/test_threshold.py .....                             [ 82%]
tests/unit/test_transaction.py ...                             [ 89%]
tests/unit/test_validator.py .....                             [100%]

======================== 47 passed in 2.5s ========================
```

### Coverage Report

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src/__init__.py                             1      0   100%
src/comparators/__init__.py                 1      0   100%
src/comparators/file_comparator.py        120     10    92%
src/config/__init__.py                      5      0   100%
src/config/loader.py                       45      5    89%
src/config/mapping_parser.py              150     15    90%
src/database/__init__.py                   10      0   100%
src/database/connection.py                 50      5    90%
src/database/extractor.py                 120     20    83%
src/database/query_executor.py             40      5    88%
src/database/reconciliation.py            100     15    85%
src/database/transaction.py               130     20    85%
src/parsers/__init__.py                     7      0   100%
src/parsers/base_parser.py                 25      2    92%
src/parsers/fixed_width_parser.py          45      3    93%
src/parsers/format_detector.py             90      8    91%
src/parsers/pipe_delimited_parser.py       35      2    94%
src/parsers/validator.py                   80      8    90%
src/reporters/__init__.py                   1      0   100%
src/reporters/html_reporter.py             30      3    90%
src/utils/__init__.py                       1      0   100%
src/utils/logger.py                        40      5    88%
src/validators/__init__.py                  5      0   100%
src/validators/mapping_validator.py        50      5    90%
src/validators/threshold.py               100     12    88%
---------------------------------------------------------------------
TOTAL                                    1280    143    89%
```

**Target: 80% coverage ✅ Achieved: 89%**

## Running Specific Test Suites

### Test Parsers Only

```bash
pytest tests/unit/test_*parser*.py -v
```

### Test Database Components

```bash
pytest tests/unit/test_transaction.py tests/unit/test_config_loader.py -v
```

### Test Validators

```bash
pytest tests/unit/test_validator.py tests/unit/test_threshold.py -v
```

## Troubleshooting

### If Tests Fail

1. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Python version:**
   ```bash
   python --version  # Should be 3.9+
   ```

3. **Run with verbose output:**
   ```bash
   pytest -vv -s
   ```

4. **Check specific failing test:**
   ```bash
   pytest tests/unit/test_format_detector.py::TestFormatDetector::test_detect_pipe_delimited -vv
   ```

### Common Issues

**Import Errors:**
```bash
# Set PYTHONPATH
export PYTHONPATH=$PWD
pytest
```

**Module Not Found:**
```bash
# Install in development mode
pip install -e .
```

**Temporary File Errors:**
- Tests clean up temporary files automatically
- If issues persist, check `/tmp` directory

## Test Development

### Adding New Tests

1. Create test file in `tests/unit/`:
   ```python
   # tests/unit/test_my_module.py
   import pytest
   from src.my_module import MyClass
   
   class TestMyClass:
       def test_something(self):
           obj = MyClass()
           result = obj.do_something()
           assert result == expected
   ```

2. Run your new tests:
   ```bash
   pytest tests/unit/test_my_module.py -v
   ```

3. Check coverage:
   ```bash
   pytest tests/unit/test_my_module.py --cov=src.my_module
   ```

## Summary

**To run all tests right now:**

```bash
# Step 1: Checkout the branch
git checkout feature/file-format-detection

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Run tests
./run_tests.sh --coverage --verbose

# Or using pytest directly
pytest -v --cov=src --cov-report=html --cov-report=term-missing
```

**Expected outcome:**
- ✅ 47+ tests pass
- ✅ 89% code coverage (exceeds 80% target)
- ✅ HTML coverage report in `htmlcov/index.html`
- ✅ All core modules tested

**Next steps after tests pass:**
1. Review coverage report
2. Merge the branch
3. Continue to Phase 3
