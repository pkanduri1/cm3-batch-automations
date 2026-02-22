import json
from pathlib import Path

from src.services.parse_service import run_parse_service
from src.services.validate_service import run_validate_service


ROOT = Path(__file__).resolve().parents[2]


def _write_mapping(mapping_id: str) -> Path:
    path = ROOT / "config" / "mappings" / f"{mapping_id}.json"
    payload = {
        "mapping_name": mapping_id,
        "version": "1.0.0",
        "source": {"type": "file", "format": "pipe_delimited", "has_header": False},
        "fields": [{"name": "id", "data_type": "string"}, {"name": "name", "data_type": "string"}],
        "key_columns": ["id"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_parse_service_basic(tmp_path):
    mapping = _write_mapping("test_parse_service_mapping")
    try:
        data = tmp_path / "in.txt"
        data.write_text("1|Alice\n2|Bob\n", encoding="utf-8")
        out = run_parse_service(str(data), str(mapping), str(tmp_path))
        assert out["rows_parsed"] == 2
        assert out["columns"] == 2
        assert Path(out["output_file"]).exists()
    finally:
        if mapping.exists():
            mapping.unlink()


def test_validate_service_basic(tmp_path):
    mapping = _write_mapping("test_validate_service_mapping")
    try:
        data = tmp_path / "in.txt"
        data.write_text("1|Alice\n2|Bob\n", encoding="utf-8")
        out = run_validate_service(
            file_path=str(data),
            mapping_path=str(mapping),
            output_html=False,
        )
        assert "valid" in out
        assert out["total_rows"] >= 0
    finally:
        if mapping.exists():
            mapping.unlink()
