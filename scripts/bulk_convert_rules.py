#!/usr/bin/env python3
"""Bulk convert rules templates (CSV/XLS/XLSX) to rules JSON files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.config.rules_template_converter import RulesTemplateConverter
import pandas as pd

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def load_template_df(template_path: Path) -> pd.DataFrame:
    if template_path.suffix.lower() == ".csv":
        return pd.read_csv(template_path, dtype=str)
    return pd.read_excel(template_path, dtype=str)


def validate_template_strict(template_path: Path) -> tuple[list[dict], str]:
    """Return row-level validation errors and detected template kind.

    Returns:
        (issues, kind) where kind is one of: ba_friendly, standard
    """
    df = load_template_df(template_path)
    df.columns = [c.strip() for c in df.columns]

    ba_required = ['Rule ID', 'Rule Name', 'Field', 'Rule Type', 'Severity', 'Expected / Values', 'Enabled']
    std_required = ['Rule ID', 'Rule Name', 'Description', 'Type', 'Severity', 'Operator']

    issues: list[dict] = []

    is_ba = all(c in df.columns for c in ba_required)
    kind = 'ba_friendly' if is_ba else 'standard'

    required_columns = ba_required if is_ba else std_required
    valid_severities = {'error', 'warning', 'info'}

    missing_headers = [c for c in required_columns if c not in df.columns]
    if missing_headers:
        issues.append({
            'row': 'HEADER',
            'field': '<headers>',
            'issue': f'Missing required headers: {missing_headers}',
            'value': ''
        })
        return issues, kind

    # duplicate Rule ID check
    dup_ids = df['Rule ID'].dropna().astype(str).str.strip()
    dup_ids = dup_ids[dup_ids.duplicated()]
    for rid in sorted(set(dup_ids.tolist())):
        issues.append({'row': 'MULTI', 'field': 'Rule ID', 'issue': 'Duplicate Rule ID', 'value': rid})

    for idx, row in df.iterrows():
        row_no = idx + 2

        rid = (row.get('Rule ID') or '').strip() if pd.notna(row.get('Rule ID')) else ''
        if rid and not rid.startswith('BR'):
            issues.append({'row': row_no, 'field': 'Rule ID', 'issue': 'Invalid Rule ID format', 'value': rid})

        for c in required_columns:
            v = (row.get(c) or '').strip() if pd.notna(row.get(c)) else ''
            if not v:
                issues.append({'row': row_no, 'field': c, 'issue': 'Required value is empty', 'value': ''})

        if is_ba:
            sev_v = (row.get('Severity') or '').strip().lower() if pd.notna(row.get('Severity')) else ''
            if sev_v and sev_v not in valid_severities:
                issues.append({'row': row_no, 'field': 'Severity', 'issue': 'Invalid severity', 'value': sev_v})

            cond_v = (row.get('Condition (optional)') or '').strip() if pd.notna(row.get('Condition (optional)')) else ''
            if '~~' in cond_v:
                issues.append({'row': row_no, 'field': 'Condition (optional)', 'issue': 'Invalid condition syntax', 'value': cond_v})
        else:
            type_v = (row.get('Type') or '').strip().lower() if pd.notna(row.get('Type')) else ''
            sev_v = (row.get('Severity') or '').strip().lower() if pd.notna(row.get('Severity')) else ''
            valid_types = {'field_validation', 'cross_field'}
            if type_v and type_v not in valid_types:
                issues.append({'row': row_no, 'field': 'Type', 'issue': 'Invalid type', 'value': type_v})
            if sev_v and sev_v not in valid_severities:
                issues.append({'row': row_no, 'field': 'Severity', 'issue': 'Invalid severity', 'value': sev_v})

    return issues, kind


def write_error_report(report_dir: Path, template_path: Path, issues: list[dict]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{template_path.stem}.errors.csv"
    pd.DataFrame(issues, columns=['row', 'field', 'issue', 'value']).to_csv(report_path, index=False)
    return report_path


def convert_file(template_path: Path, output_dir: Path) -> Path:
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
        issues, _kind = validate_template_strict(template)
        if issues:
            report = write_error_report(error_report_dir, template, issues)
            print(f"❌ Validation failed for {template.name}. Report: {report}")
            failed += 1
            continue

        try:
            out_path = convert_file(template, output_dir)
            print(f"✅ {template.name} -> {out_path}")
            success += 1
        except Exception as exc:
            print(f"❌ Failed to convert {template}: {exc}")
            failed += 1

    print(f"\nDone. Converted: {success}, Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
