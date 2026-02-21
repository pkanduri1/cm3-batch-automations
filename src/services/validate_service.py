from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.parsers.chunked_parser import ChunkedFixedWidthParser
from src.parsers.chunked_validator import ChunkedFileValidator
from src.parsers.enhanced_validator import EnhancedFileValidator
from src.parsers.fixed_width_parser import FixedWidthParser
from src.parsers.format_detector import FormatDetector
from src.reports.adapters.result_adapter_chunked import adapt_chunked_validation_result
from src.reports.renderers.validation_renderer import ValidationReporter


def _field_specs(mapping_config: dict[str, Any]) -> list[tuple[str, int, int]]:
    specs = []
    current_pos = 0
    for field in mapping_config.get("fields", []):
        length = int(field.get("length", 0))
        start = int(field.get("position") - 1) if field.get("position") is not None else current_pos
        end = start + length
        specs.append((field["name"], start, end))
        current_pos = end
    return specs


def _count_rows(result: dict[str, Any], chunked: bool) -> tuple[int, int, int]:
    total_rows = int(result.get("total_rows", 0)) if chunked else int((result.get("quality_metrics") or {}).get("total_rows", 0))
    invalid_rows = len({
        int(e.get("row")) for e in (result.get("errors", []) or [])
        if isinstance(e, dict) and e.get("row") is not None and str(e.get("row")).isdigit()
    })
    valid_rows = max(total_rows - invalid_rows, 0)
    return total_rows, valid_rows, invalid_rows


def run_validate_service(
    *,
    file_path: str,
    mapping_path: str,
    detailed: bool = True,
    use_chunked: bool = False,
    chunk_size: int = 100000,
    progress: bool = False,
    strict_fixed_width: bool = False,
    strict_level: str = "format",
    output_html: bool = True,
    output_dir: str = "uploads",
) -> dict[str, Any]:
    mapping_file = Path(mapping_path)
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping not found: {mapping_path}")

    mapping_config = json.loads(mapping_file.read_text(encoding="utf-8"))
    mapping_config["file_path"] = str(mapping_file)
    source_format = str((mapping_config.get("source") or {}).get("format") or "").lower()
    is_fixed_width = source_format in {"fixed_width", "fixedwidth"}

    report_url = None
    upload_path = Path(file_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if use_chunked:
        parser_class = FixedWidthParser if is_fixed_width else FormatDetector().get_parser_class(str(upload_path))
        chunk_parser = None
        if parser_class == FixedWidthParser and is_fixed_width and mapping_config.get("fields"):
            chunk_parser = ChunkedFixedWidthParser(str(upload_path), _field_specs(mapping_config), chunk_size=chunk_size)

        expected_row_length = sum(int(f.get("length", 0)) for f in mapping_config.get("fields", [])) if is_fixed_width else None
        strict_fields = mapping_config.get("fields", []) if is_fixed_width else []

        validator = ChunkedFileValidator(
            file_path=str(upload_path),
            delimiter="|",
            chunk_size=chunk_size,
            parser=chunk_parser,
            expected_row_length=expected_row_length,
            strict_fixed_width=strict_fixed_width,
            strict_level=strict_level,
            strict_fields=strict_fields,
        )

        expected_columns = [f["name"] for f in mapping_config.get("fields", [])] if mapping_config.get("fields") else []
        if expected_columns:
            required_columns = [f["name"] for f in mapping_config.get("fields", []) if f.get("required", False)]
            result = validator.validate_with_schema(
                expected_columns=expected_columns,
                required_columns=required_columns if required_columns else expected_columns,
                show_progress=progress,
            )
        else:
            result = validator.validate(show_progress=progress)

        if output_html:
            report_path = out_dir / f"validation_{upload_path.stem}.html"
            adapted = adapt_chunked_validation_result(result, file_path=str(upload_path), mapping=str(mapping_file))
            ValidationReporter().generate(adapted, str(report_path))
            report_url = f"/uploads/{report_path.name}"

        total_rows, valid_rows, invalid_rows = _count_rows(result, chunked=True)
        return {
            "valid": bool(result.get("valid", False)),
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows,
            "errors": [e if isinstance(e, dict) else {"message": str(e)} for e in (result.get("errors", []) or [])],
            "warnings": [w.get("message", str(w)) if isinstance(w, dict) else str(w) for w in (result.get("warnings", []) or [])],
            "quality_score": None,
            "report_url": report_url,
        }

    parser_class = FixedWidthParser if is_fixed_width else FormatDetector().get_parser_class(str(upload_path))
    parser = FixedWidthParser(str(upload_path), _field_specs(mapping_config)) if parser_class == FixedWidthParser and is_fixed_width and mapping_config.get("fields") else parser_class(str(upload_path))

    result = EnhancedFileValidator(parser, mapping_config).validate(
        detailed=detailed,
        strict_fixed_width=strict_fixed_width,
        strict_level=strict_level,
    )

    if output_html:
        report_path = out_dir / f"validation_{upload_path.stem}.html"
        ValidationReporter().generate(result, str(report_path))
        report_url = f"/uploads/{report_path.name}"

    total_rows, valid_rows, invalid_rows = _count_rows(result, chunked=False)
    return {
        "valid": bool(result.get("valid", False)),
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "errors": [e if isinstance(e, dict) else {"message": str(e)} for e in (result.get("errors", []) or [])],
        "warnings": [w.get("message", str(w)) if isinstance(w, dict) else str(w) for w in (result.get("warnings", []) or [])],
        "quality_score": (result.get("quality_metrics") or {}).get("quality_score"),
        "report_url": report_url,
    }
