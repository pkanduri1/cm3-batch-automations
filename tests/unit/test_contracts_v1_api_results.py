import json
from pathlib import Path

from src.api.models.file import FileCompareResult, FileValidationResult


ROOT = Path(__file__).resolve().parents[2]


def _assert_matches_min_schema(payload: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for key in schema.get("required", []):
        assert key in payload, f"missing required key: {key}"

    type_map = {"integer": int, "number": (int, float), "boolean": bool, "string": str, "array": list, "object": dict}
    for key, spec in schema.get("properties", {}).items():
        if key not in payload:
            continue
        expected = spec.get("type")
        if isinstance(expected, list):
            if payload[key] is None and "null" in expected:
                continue
            allowed = tuple(type_map[t] for t in expected if t != "null" and t in type_map)
            if allowed:
                assert isinstance(payload[key], allowed), f"type mismatch for {key}"
        elif expected in type_map:
            assert isinstance(payload[key], type_map[expected]), f"type mismatch for {key}"


def test_compare_result_contract_v1():
    payload = FileCompareResult(
        total_rows_file1=10,
        total_rows_file2=10,
        matching_rows=8,
        only_in_file1=1,
        only_in_file2=1,
        differences=2,
        report_url="/uploads/r.html",
    ).model_dump()

    schema = ROOT / "docs/contracts/compare_result_v1.schema.json"
    _assert_matches_min_schema(payload, schema)


def test_validation_result_contract_v1():
    payload = FileValidationResult(
        valid=False,
        total_rows=10,
        valid_rows=8,
        invalid_rows=2,
        errors=[{"message": "e"}],
        warnings=["w"],
        quality_score=88.8,
        report_url="/uploads/v.html",
    ).model_dump()

    schema = ROOT / "docs/contracts/validation_result_v1.schema.json"
    _assert_matches_min_schema(payload, schema)
