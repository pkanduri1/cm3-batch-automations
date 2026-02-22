"""Command handler for bulk mapping template conversion."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.config.template_converter import TemplateConverter

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def _load_template_df(template_path: Path) -> pd.DataFrame:
    if template_path.suffix.lower() == ".csv":
        return pd.read_csv(template_path, dtype=str)
    return pd.read_excel(template_path, dtype=str)


def _validate_template_strict(template_path: Path) -> list[dict]:
    """Return row-level validation errors for strict template conversion."""
    df = _load_template_df(template_path)
    df.columns = [c.strip() for c in df.columns]

    required_columns = ["Field Name", "Data Type"]
    fixed_width_columns = ["Position", "Length"]

    issues: list[dict] = []

    missing_headers = [c for c in required_columns if c not in df.columns]
    if missing_headers:
        issues.append({
            "row": "HEADER",
            "field": "<headers>",
            "issue": f"Missing required headers: {missing_headers}",
            "value": "",
        })
        return issues

    is_fixed_width = all(c in df.columns for c in fixed_width_columns)

    for idx, row in df.iterrows():
        row_no = idx + 2

        for c in required_columns:
            v = (row.get(c) or "").strip() if pd.notna(row.get(c)) else ""
            if not v:
                issues.append({"row": row_no, "field": c, "issue": "Required value is empty", "value": ""})

        if is_fixed_width:
            for c in fixed_width_columns:
                v = (row.get(c) or "").strip() if pd.notna(row.get(c)) else ""
                if not v.isdigit():
                    issues.append({
                        "row": row_no,
                        "field": c,
                        "issue": "Expected numeric value for fixed-width template",
                        "value": v,
                    })

    return issues


def _write_error_report(report_dir: Path, template_path: Path, issues: list[dict]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{template_path.stem}.errors.csv"
    pd.DataFrame(issues, columns=["row", "field", "issue", "value"]).to_csv(report_path, index=False)
    return report_path


def _convert_file(template_path: Path, output_dir: Path, file_format: Optional[str] = None) -> Path:
    converter = TemplateConverter()
    mapping_name = template_path.stem

    if template_path.suffix.lower() == ".csv":
        converter.from_csv(str(template_path), mapping_name=mapping_name, file_format=file_format)
    else:
        converter.from_excel(str(template_path), mapping_name=mapping_name, file_format=file_format)

    out_path = output_dir / f"{mapping_name}.json"
    converter.save(str(out_path))
    return out_path


def run_convert_mappings_command(
    input_dir: str,
    output_dir: str,
    file_format: Optional[str],
    error_report_dir: str,
    logger,
) -> int:
    """Bulk convert mapping templates to mapping JSON files.

    Returns process-style exit code: 0 success, 1 if there were failures.
    """
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)

    if not in_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {in_dir}")

    templates = sorted(p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)
    if not templates:
        logger.info(f"No mapping templates found in {in_dir} (supported: {sorted(SUPPORTED_EXTS)})")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(error_report_dir)

    success = 0
    failed = 0
    for template in templates:
        issues = _validate_template_strict(template)
        if issues:
            report = _write_error_report(report_dir, template, issues)
            logger.error(f"Validation failed for {template.name}. Report: {report}")
            failed += 1
            continue

        try:
            out_path = _convert_file(template, out_dir, file_format=file_format)
            logger.info(f"Converted {template.name} -> {out_path}")
            success += 1
        except Exception as exc:
            logger.error(f"Failed to convert {template}: {exc}")
            failed += 1

    logger.info(f"Done. Converted: {success}, Failed: {failed}")
    return 1 if failed else 0
