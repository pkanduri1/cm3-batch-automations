from pathlib import Path

from src.reports.renderers.validation_renderer import ValidationReporter


def _sample_result():
    return {
        "valid": True,
        "timestamp": "2026-02-20T00:00:00Z",
        "file_metadata": {
            "file_name": "sample.txt",
            "format": "pipe_delimited",
            "size_bytes": 100,
            "size_mb": 0.0001,
            "modified_time": "2026-02-20T00:00:00",
        },
        "quality_metrics": {
            "quality_score": 99.5,
            "total_rows": 2,
            "total_columns": 2,
            "completeness_pct": 100.0,
            "uniqueness_pct": 100.0,
            "total_cells": 4,
            "filled_cells": 4,
            "null_cells": 0,
            "unique_rows": 2,
            "duplicate_rows": 0,
        },
        "errors": [],
        "warnings": [{"severity": "warning", "message": "sample warning"}],
        "info": [{"severity": "info", "message": "sample info"}],
        "error_count": 0,
        "warning_count": 1,
        "info_count": 1,
        "field_analysis": {
            0: {"inferred_type": "string", "fill_rate_pct": 100.0, "unique_count": 2},
            "name": {"inferred_type": "string", "fill_rate_pct": 100.0, "unique_count": 2},
        },
        "duplicate_analysis": {"unique_rows": 2, "duplicate_rows": 0, "duplicate_pct": 0.0},
        "date_analysis": {},
        "business_rules": None,
        "appendix": {"sample_records": []},
    }


def test_validation_renderer_generates_html_and_sidecars(tmp_path):
    out = tmp_path / "report.html"
    reporter = ValidationReporter()
    reporter.generate(_sample_result(), str(out))

    assert out.exists()
    html = out.read_text(encoding="utf-8").lower()
    assert "file validation report" in html

    err = tmp_path / "report_errors.csv"
    warn = tmp_path / "report_warnings.csv"
    assert err.exists()
    assert warn.exists()
