# Sample Data Files

This directory contains sample data files for testing and demonstration.

## Files

### customers.txt
- **Format**: Pipe-delimited (|)
- **Columns**: customer_id, first_name, last_name, email, phone, account_balance, status
- **Rows**: 10 sample customer records
- **Mapping**: Use `config/mappings/customer_mapping.json`

### transactions.txt
- **Format**: Fixed-width
- **Columns**: transaction_id (13), customer_id (10), transaction_date (10), amount (10), transaction_type (8), description (20)
- **Rows**: 10 sample transaction records
- **Mapping**: Use `config/mappings/transaction_mapping.json`

## Column Specifications

### customers.txt (Pipe-delimited)
```
customer_id|first_name|last_name|email|phone|account_balance|status
```

### transactions.txt (Fixed-width)
```
Position  Length  Column
0-13      13      transaction_id
13-23     10      customer_id
23-33     10      transaction_date
33-43     10      amount
43-51     8       transaction_type
51-71     20      description
```

## Usage Examples

### Detect Format
```bash
cm3-batch detect -f data/samples/customers.txt
```

### Parse File
```bash
cm3-batch parse -f data/samples/customers.txt
```

### Validate File
```bash
cm3-batch validate -f data/samples/customers.txt
```

### Compare Files
```bash
cm3-batch compare -f1 data/samples/customers.txt -f2 data/samples/customers_updated.txt -k customer_id -o report.html
```

## Creating Test Data

You can create additional test files following these formats:

### Pipe-delimited
- Use `|` as delimiter
- No header row (column names in mapping)
- String values without quotes

### Fixed-width
- Fixed column positions
- Pad with spaces
- No delimiters
