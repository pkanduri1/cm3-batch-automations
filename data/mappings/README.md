# CSV Mapping Templates for Batch Integrations

These CSV templates are sample inputs for `src/config/template_converter.py`.

## Included templates

- `customer_batch_template.csv` → pipe-delimited style mapping template
- `transaction_batch_template.csv` → fixed-width style mapping template (includes Position/Length)
- `order_batch_template.csv` → delimited order integration template with default values

## Convert template to universal JSON mapping

```bash
python src/config/template_converter.py \
  data/mappings/customer_batch_template.csv \
  config/mappings/customer_batch_universal.json \
  customer_batch_universal \
  pipe_delimited
```

```bash
python src/config/template_converter.py \
  data/mappings/transaction_batch_template.csv \
  config/mappings/transaction_batch_universal.json \
  transaction_batch_universal \
  fixed_width
```

```bash
python src/config/template_converter.py \
  data/mappings/order_batch_template.csv \
  config/mappings/order_batch_universal.json \
  order_batch_universal \
  csv
```

## Required columns

- Always required: `Field Name`, `Data Type`
- Optional: `Position`, `Length`, `Format`, `Required`, `Description`, `Default Value`, `Target Name`
