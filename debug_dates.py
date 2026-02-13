#!/usr/bin/env python3
"""Debug script to check date field values in P327 file."""

import sys
sys.path.insert(0, '/Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection')

from src.parsers.format_detector import FormatDetector
import pandas as pd
import re

# Detect and parse the file
detector = FormatDetector()
file_path = 'data/samples/p327_test_data.txt'

print(f"Analyzing: {file_path}\n")

# Get parser
parser_class = detector.get_parser_class(file_path)
print(f"Parser class: {parser_class.__name__}\n")

# Load mapping
import json
with open('config/mappings/p327_universal.json', 'r') as f:
    mapping = json.load(f)

# Create parser with mapping
parser = parser_class(file_path, mapping['fields'])
df = parser.parse()

print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}\n")

# Find date fields
date_fields = [col for col in df.columns if 'DATE' in col.upper()]
print(f"Found {len(date_fields)} fields with 'DATE' in name:\n")

for field in date_fields[:5]:  # Check first 5 date fields
    print(f"=== {field} ===")
    series = df[field]
    
    # Show raw values
    print(f"Raw values (first 5):")
    for i, val in enumerate(series.head(5)):
        print(f"  [{i}] '{val}' (type: {type(val).__name__}, len: {len(str(val))})")
    
    # Check pattern
    sample = series.head(100).astype(str).str.strip()
    yyyymmdd_pattern = r'^\d{8}$'
    matches = sample.str.match(yyyymmdd_pattern)
    print(f"\nYYYYMMDD pattern matches: {matches.sum()}/{len(sample)}")
    
    # Show non-matching values
    non_matches = sample[~matches]
    if len(non_matches) > 0:
        print(f"Non-matching values:")
        for val in non_matches.head(3):
            print(f"  '{val}' (len: {len(val)})")
    
    # Try parsing
    try:
        parsed = pd.to_datetime(sample, format='%Y%m%d', errors='coerce')
        valid = parsed.notna().sum()
        print(f"\nParseable as YYYYMMDD: {valid}/{len(sample)}")
        if valid > 0:
            print(f"Sample parsed dates: {parsed.dropna().head(3).tolist()}")
    except Exception as e:
        print(f"\nError parsing: {e}")
    
    print()
