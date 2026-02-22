import asyncio
import io
import json
from pathlib import Path

from fastapi import UploadFile

from src.api.models.file import FileCompareRequest
from src.api.routers.files import compare_files_async, compare_job_status


ROOT = Path(__file__).resolve().parents[2]
MAPPINGS_DIR = ROOT / "config" / "mappings"


def _write_test_mapping(mapping_id: str):
    payload = {
        "mapping_name": mapping_id,
        "version": "1.0.0",
        "source": {"type": "file", "format": "pipe_delimited", "has_header": False},
        "fields": [
            {"name": "id", "data_type": "string"},
            {"name": "name", "data_type": "string"},
        ],
        "key_columns": ["id"],
    }
    path = MAPPINGS_DIR / f"{mapping_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _upload(name: str, content: str) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content.encode("utf-8")))


def test_compare_async_job_lifecycle_direct():
    mapping_id = "test_async_compare_mapping"
    mapping_path = _write_test_mapping(mapping_id)
    try:
        req = FileCompareRequest(mapping_id=mapping_id, key_columns=["id"], detailed=True)
        created = asyncio.run(
            compare_files_async(
                file1=_upload("f1.txt", "1|Alice\n2|Bob\n"),
                file2=_upload("f2.txt", "1|Alice\n3|Charlie\n"),
                request=req,
            )
        )
        job_id = created.job_id

        final = None
        for _ in range(40):
            status = asyncio.run(compare_job_status(job_id))
            if status.status in {"completed", "failed"}:
                final = status
                break
            asyncio.run(asyncio.sleep(0.05))

        assert final is not None
        assert final.status == "completed"
        assert final.result is not None
        assert final.result.matching_rows >= 0
        assert final.result.report_url is not None
    finally:
        if mapping_path.exists():
            mapping_path.unlink()
