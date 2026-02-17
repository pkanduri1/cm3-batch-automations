#!/usr/bin/env python3
"""Bulk convert mapping templates (CSV/XLS/XLSX) to mapping JSON files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.config.template_converter import TemplateConverter

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def convert_file(template_path: Path, output_dir: Path, file_format: str | None = None) -> Path:
    converter = TemplateConverter()
    mapping_name = template_path.stem

    if template_path.suffix.lower() == ".csv":
        converter.from_csv(str(template_path), mapping_name=mapping_name, file_format=file_format)
    else:
        converter.from_excel(str(template_path), mapping_name=mapping_name, file_format=file_format)

    out_path = output_dir / f"{mapping_name}.json"
    converter.save(str(out_path))
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="mappings/csv", help="Directory containing mapping CSV/Excel templates")
    parser.add_argument("--output-dir", default="config/mappings", help="Directory to write mapping JSON files")
    parser.add_argument("--format", choices=["pipe_delimited", "fixed_width", "csv", "tsv"],
                        help="Optional mapping source format override")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return 1

    templates = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)
    if not templates:
        print(f"⚠️ No mapping templates found in {input_dir} (supported: {sorted(SUPPORTED_EXTS)})")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    for template in templates:
        try:
            out_path = convert_file(template, output_dir, file_format=args.format)
            print(f"✅ {template.name} -> {out_path}")
            success += 1
        except Exception as exc:
            print(f"❌ Failed to convert {template}: {exc}")
            failed += 1

    print(f"\nDone. Converted: {success}, Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
