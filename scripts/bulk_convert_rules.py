#!/usr/bin/env python3
"""Bulk convert rules templates (CSV/XLS/XLSX) to rules JSON files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.config.rules_template_converter import RulesTemplateConverter
from src.config.ba_rules_template_converter import BARulesTemplateConverter
import pandas as pd

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def load_template_df(template_path: Path) -> pd.DataFrame:
    if template_path.suffix.lower() == ".csv":
        return pd.read_csv(template_path, dtype=str)
    return pd.read_excel(template_path, dtype=str)


def detect_template_type(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    if {'Rule ID', 'Rule Name', 'Field', 'Rule Type', 'Severity', 'Expected / Values', 'Enabled'}.issubset(cols):
        return 'ba_friendly'
    if {'Rule ID', 'Rule Name', 'Description', 'Type', 'Severity', 'Operator'}.issubset(cols):
        return 'standard'
    return 'unknown'


def validate_template_strict(template_path: Path) -> tuple[list[dict], str]:
    """Return row-level validation errors and detected template type."""
    df = load_template_df(template_path)
    df.columns = [c.strip() for c in df.columns]

    template_type = detect_template_type(df)
    issues: list[dict] = []

    if template_type == 'standard':
        required_columns = ['Rule ID', 'Rule Name', 'Description', 'Type', 'Severity', 'Operator']
        valid_types = {'field_validation', 'cross_field'}
        valid_severities = {'error', 'warning', 'info'}
    elif template_type == 'ba_friendly':
        required_columns = ['Rule ID', 'Rule Name', 'Field', 'Rule Type', 'Severity', 'Expected / Values', 'Enabled']
        valid_types = {'required', 'allowed values', 'range', 'length', 'regex', 'date format', 'compare fields'}
        valid_severities = {'error', 'warning', 'info'}
    else:
        issues.append({
            'row': 'HEADER',
            'field': '<headers>',
            'issue': 'Unknown template format. Expected standard or BA-friendly rules template columns.',
            'value': ''
        })
        return issues, template_type

    missing_headers = [c for c in required_columns if c not in df.columns]
    if missing_headers:
        issues.append({
            'row': 'HEADER',
            'field': '<headers>',
            'issue': f'Missing required headers: {missing_headers}',
            'value': ''
        })
        return issues, template_type

    # duplicate Rule ID check
    dup_ids = df['Rule ID'].dropna().astype(str).str.strip()
    dup_ids = dup_ids[dup_ids.duplicated()]
    for rid in sorted(set(dup_ids.tolist())):
        issues.append({'row': 'MULTI', 'field': 'Rule ID', 'issue': 'Duplicate Rule ID', 'value': rid})

    for idx, row in df.iterrows():
        row_no = idx + 2

        for c in required_columns:
            v = (row.get(c) or '').strip() if pd.notna(row.get(c)) else ''
            if not v:
                issues.append({'row': row_no, 'field': c, 'issue': 'Required value is empty', 'value': ''})

        if template_type == 'standard':
            type_v = (row.get('Type') or '').strip().lower() if pd.notna(row.get('Type')) else ''
        else:
            type_v = (row.get('Rule Type') or '').strip().lower() if pd.notna(row.get('Rule Type')) else ''

        sev_v = (row.get('Severity') or '').strip().lower() if pd.notna(row.get('Severity')) else ''

        if type_v and type_v not in valid_types:
            issues.append({'row': row_no, 'field': 'Type' if template_type == 'standard' else 'Rule Type', 'issue': 'Invalid type', 'value': type_v})
        if sev_v and sev_v not in valid_severities:
            issues.append({'row': row_no, 'field': 'Severity', 'issue': 'Invalid severity', 'value': sev_v})

    return issues, template_type


def write_error_report(report_dir: Path, template_path: Path, issues: list[dict]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{template_path.stem}.errors.csv"
    pd.DataFrame(issues, columns=['row', 'field', 'issue', 'value']).to_csv(report_path, index=False)
    return report_path


def convert_file(template_path: Path, output_dir: Path, template_type: str) -> Path:
    if template_type == 'ba_friendly':
        converter = BARulesTemplateConverter()
    else:
        converter = RulesTemplateConverter()

    if template_path.suffix.lower() == ".csv":
        converter.from_csv(str(template_path))
    else:
        converter.from_excel(str(template_path))

    out_path = output_dir / f"{template_path.stem}.json"
    converter.save(str(out_path))
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="rules/csv", help="Directory containing rules CSV/Excel templates")
    parser.add_argument("--output-dir", default="config/rules", help="Directory to write rules JSON files")
    parser.add_argument("--error-report-dir", default="reports/template_validation",
                        help="Directory to write strict validation error reports")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return 1

    templates = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)
    if not templates:
        print(f"⚠️ No rules templates found in {input_dir} (supported: {sorted(SUPPORTED_EXTS)})")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    error_report_dir = Path(args.error_report_dir)

    success = 0
    failed = 0
    for template in templates:
        issues, template_type = validate_template_strict(template)
        if issues:
            report = write_error_report(error_report_dir, template, issues)
            print(f"❌ Validation failed for {template.name}. Report: {report}")
            failed += 1
            continue

        try:
            out_path = convert_file(template, output_dir, template_type)
            print(f"✅ {template.name} [{template_type}] -> {out_path}")
            success += 1
        except Exception as exc:
            print(f"❌ Failed to convert {template}: {exc}")
            failed += 1

    print(f"\nDone. Converted: {success}, Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
