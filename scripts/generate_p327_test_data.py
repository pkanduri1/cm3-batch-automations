"""Generate sample P327 test data file."""

import json
from datetime import datetime, timedelta
import random


def generate_sample_record(field_specs):
    """Generate a single sample record based on field specifications."""
    record = ""
    
    for field in field_specs:
        field_name = field['name']
        length = field['length']
        data_type = field['data_type']
        required = field['required']
        
        # Generate sample data based on type
        if data_type == 'String':
            if 'LOCATION' in field_name:
                value = 'LOC001'
            elif 'ACCT' in field_name or 'NUM' in field_name:
                value = f"ACCT{random.randint(100000, 999999):012d}"
            elif 'TYPE' in field_name:
                value = random.choice(['01', '02', '03', '04'])
            elif 'FMT' in field_name:
                value = random.choice(['A', 'B', 'C'])
            else:
                value = 'TEST' + str(random.randint(1, 999))
        
        elif data_type == 'Numeric':
            if 'AMT' in field_name:
                # Generate amount with decimals
                amount = random.uniform(0, 999999)
                # Format based on field format if available
                if field['format'] and 'V' in str(field['format']):
                    # Has decimal places
                    value = f"{amount:019.6f}".replace('.', '')
                else:
                    value = f"{int(amount):0{length}d}"
            elif 'CNT' in field_name or 'COUNT' in field_name:
                value = f"{random.randint(0, 99):0{length}d}"
            elif 'DAYS' in field_name:
                value = f"{random.randint(0, 365):0{length}d}"
            else:
                value = f"{random.randint(0, 10**length - 1):0{length}d}"
        
        elif data_type == 'Date':
            # Generate random date in CCYYMMDD format
            base_date = datetime(2024, 1, 1)
            random_days = random.randint(0, 365)
            date = base_date + timedelta(days=random_days)
            value = date.strftime('%Y%m%d')
        
        else:
            value = ' ' * length
        
        # Pad or truncate to exact length
        value = str(value)[:length].ljust(length)
        record += value
    
    return record


def generate_test_file(config_path: str, output_path: str, num_records: int = 10):
    """
    Generate test file based on P327 mapping configuration.
    
    Args:
        config_path: Path to JSON configuration file
        output_path: Path to output test file
        num_records: Number of records to generate
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    field_specs = config['fields']
    record_length = config['total_record_length']
    
    print(f"Generating {num_records} test records...")
    print(f"Record length: {record_length} characters")
    
    # Generate records
    with open(output_path, 'w') as f:
        for i in range(num_records):
            record = generate_sample_record(field_specs)
            
            # Verify record length
            if len(record) != record_length:
                print(f"WARNING: Record {i+1} length mismatch: {len(record)} vs {record_length}")
            
            f.write(record + '\n')
    
    print(f"\nTest file generated: {output_path}")
    print(f"Total records: {num_records}")
    print(f"File size: {num_records * (record_length + 1)} bytes")


if __name__ == '__main__':
    config_path = 'config/mappings/p327_mapping.json'
    output_path = 'data/samples/p327_test_data.txt'
    
    generate_test_file(config_path, output_path, num_records=10)
    
    # Display first record
    print("\nFirst record preview (first 200 chars):")
    with open(output_path, 'r') as f:
        first_line = f.readline()
        print(first_line[:200])
        print(f"... (total {len(first_line.strip())} characters)")
