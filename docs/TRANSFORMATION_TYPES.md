# Transformation Types Reference

## Overview

Transformations are applied to field values during data processing. They modify the data before it's validated or loaded into the target system.

---

## 📋 Available Transformation Types

### 1. `trim`
**Remove leading and trailing whitespace**

```json
{
  "type": "trim"
}
```

**Example:**
- Input: `"  John Doe  "`
- Output: `"John Doe"`

**Use Cases:**
- Clean up user input
- Remove padding from fixed-width fields
- Standardize data

---

### 2. `upper`
**Convert text to uppercase**

```json
{
  "type": "upper"
}
```

**Example:**
- Input: `"john doe"`
- Output: `"JOHN DOE"`

**Use Cases:**
- Standardize names
- Match database column naming conventions
- Case-insensitive comparisons

---

### 3. `lower`
**Convert text to lowercase**

```json
{
  "type": "lower"
}
```

**Example:**
- Input: `"JOHN DOE"`
- Output: `"john doe"`

**Use Cases:**
- Normalize email addresses
- Standardize codes
- Case-insensitive matching

---

### 4. `substring`
**Extract portion of text**

```json
{
  "type": "substring",
  "parameters": {
    "start": 0,
    "length": 10
  }
}
```

**Parameters:**
- `start` (required): Starting position (0-indexed)
- `length` (optional): Number of characters to extract. If omitted, extracts to end

**Examples:**

Extract first 5 characters:
```json
{
  "type": "substring",
  "parameters": {"start": 0, "length": 5}
}
```
- Input: `"CUSTOMER123"`
- Output: `"CUSTO"`

Extract from position 8 to end:
```json
{
  "type": "substring",
  "parameters": {"start": 8}
}
```
- Input: `"CUSTOMER123"`
- Output: `"123"`

**Use Cases:**
- Extract year from date string
- Get prefix/suffix from codes
- Split concatenated fields

---

### 5. `replace`
**Replace text with another value**

```json
{
  "type": "replace",
  "parameters": {
    "old": "-",
    "new": ""
  }
}
```

**Parameters:**
- `old` (required): Text to find
- `new` (required): Replacement text

**Examples:**

Remove dashes:
```json
{
  "type": "replace",
  "parameters": {"old": "-", "new": ""}
}
```
- Input: `"555-123-4567"`
- Output: `"5551234567"`

Replace spaces with underscores:
```json
{
  "type": "replace",
  "parameters": {"old": " ", "new": "_"}
}
```
- Input: `"John Doe"`
- Output: `"John_Doe"`

**Use Cases:**
- Remove special characters
- Standardize formats
- Clean phone numbers, SSNs, etc.

---

### 6. `cast`
**Convert data type**

```json
{
  "type": "cast",
  "parameters": {
    "to_type": "number"
  }
}
```

**Parameters:**
- `to_type` (required): Target type - `"number"`, `"date"`, or `"string"`

**Examples:**

Convert to number:
```json
{
  "type": "cast",
  "parameters": {"to_type": "number"}
}
```
- Input: `"123.45"`
- Output: `123.45`

Convert to date:
```json
{
  "type": "cast",
  "parameters": {"to_type": "date"}
}
```
- Input: `"2026-02-07"`
- Output: `2026-02-07` (datetime object)

**Use Cases:**
- Convert string amounts to numbers
- Parse date strings
- Type conversion for calculations

**Note:** Invalid conversions will result in `NaN` or `NaT` (Not a Time)

---

## 🔗 Chaining Transformations

You can apply multiple transformations in sequence. They are executed in order:

```json
"transformations": [
  {"type": "trim"},
  {"type": "upper"},
  {
    "type": "replace",
    "parameters": {"old": "-", "new": ""}
  }
]
```

**Example:**
- Input: `"  john-doe  "`
- After `trim`: `"john-doe"`
- After `upper`: `"JOHN-DOE"`
- After `replace`: `"JOHNDOE"`

---

## 📝 Complete Examples

### Example 1: Clean Customer Name

```json
{
  "source_column": "customer_name",
  "target_column": "CUSTOMER_NAME",
  "data_type": "string",
  "transformations": [
    {"type": "trim"},
    {"type": "upper"}
  ]
}
```

### Example 2: Format Phone Number

```json
{
  "source_column": "phone",
  "target_column": "PHONE",
  "data_type": "string",
  "transformations": [
    {"type": "trim"},
    {
      "type": "replace",
      "parameters": {"old": "-", "new": ""}
    },
    {
      "type": "replace",
      "parameters": {"old": "(", "new": ""}
    },
    {
      "type": "replace",
      "parameters": {"old": ")", "new": ""}
    },
    {
      "type": "replace",
      "parameters": {"old": " ", "new": ""}
    }
  ]
}
```
- Input: `"(555) 123-4567"`
- Output: `"5551234567"`

### Example 3: Extract Year from Date

```json
{
  "source_column": "transaction_date",
  "target_column": "YEAR",
  "data_type": "string",
  "transformations": [
    {"type": "trim"},
    {
      "type": "substring",
      "parameters": {"start": 0, "length": 4}
    }
  ]
}
```
- Input: `"2026-02-07"`
- Output: `"2026"`

### Example 4: Normalize Email

```json
{
  "source_column": "email",
  "target_column": "EMAIL",
  "data_type": "string",
  "transformations": [
    {"type": "trim"},
    {"type": "lower"}
  ]
}
```
- Input: `"  JOHN.DOE@EXAMPLE.COM  "`
- Output: `"john.doe@example.com"`

### Example 5: Convert Amount to Number

```json
{
  "source_column": "amount",
  "target_column": "AMOUNT",
  "data_type": "number",
  "transformations": [
    {"type": "trim"},
    {
      "type": "replace",
      "parameters": {"old": "$", "new": ""}
    },
    {
      "type": "replace",
      "parameters": {"old": ",", "new": ""}
    },
    {
      "type": "cast",
      "parameters": {"to_type": "number"}
    }
  ]
}
```
- Input: `"$1,234.56"`
- Output: `1234.56`

### Example 6: Extract Account Number

```json
{
  "source_column": "full_account",
  "target_column": "ACCOUNT_NUM",
  "data_type": "string",
  "transformations": [
    {"type": "trim"},
    {
      "type": "substring",
      "parameters": {"start": 3, "length": 10}
    }
  ]
}
```
- Input: `"ACC1234567890XYZ"`
- Output: `"1234567890"`

---

## 🎯 Common Patterns

### Pattern 1: Standard Text Field
```json
"transformations": [
  {"type": "trim"}
]
```

### Pattern 2: Code/ID Field
```json
"transformations": [
  {"type": "trim"},
  {"type": "upper"}
]
```

### Pattern 3: Email/Username
```json
"transformations": [
  {"type": "trim"},
  {"type": "lower"}
]
```

### Pattern 4: Numeric Field
```json
"transformations": [
  {"type": "trim"},
  {"type": "cast", "parameters": {"to_type": "number"}}
]
```

### Pattern 5: Remove All Special Characters
```json
"transformations": [
  {"type": "trim"},
  {"type": "replace", "parameters": {"old": "-", "new": ""}},
  {"type": "replace", "parameters": {"old": " ", "new": ""}},
  {"type": "replace", "parameters": {"old": ".", "new": ""}}
]
```

---

## ⚠️ Important Notes

1. **Order Matters**: Transformations are applied in the order specified
2. **String Operations**: `trim`, `upper`, `lower`, `substring`, `replace` only work on string data
3. **Type Conversion**: Use `cast` carefully - invalid conversions produce `NaN`/`NaT`
4. **Null Values**: Most transformations handle null/empty values gracefully
5. **Performance**: Minimize transformation chains for large datasets

---

## 🔍 Transformation Implementation

All transformations are implemented in:
[`src/config/mapping_parser.py`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/src/config/mapping_parser.py)

The `_apply_transformation` method (lines 149-185) handles all transformation logic.

---

## 📚 Related Documentation

- **Mapping Quick Start**: [`docs/MAPPING_QUICKSTART.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/MAPPING_QUICKSTART.md)
- **Universal Mapping Guide**: [`docs/UNIVERSAL_MAPPING_GUIDE.md`](file:///Users/pavankanduri/google-agy/cm3-batch-automations-feature-file-format-detection/docs/UNIVERSAL_MAPPING_GUIDE.md)
- **Validation Rules**: See mapping documentation for validation rule types

---

## 💡 Tips

1. **Always trim first**: Start with `{"type": "trim"}` to remove whitespace
2. **Test transformations**: Use small sample files to verify transformations work as expected
3. **Document complex chains**: Add comments in your mapping file explaining multi-step transformations
4. **Consider performance**: Each transformation adds processing time
5. **Handle edge cases**: Test with empty values, special characters, and boundary conditions
