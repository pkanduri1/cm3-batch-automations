from pathlib import Path

import scripts.run_manifest_workflow as manifest_wf
import scripts.run_regression_workflow as regression_wf


def test_regression_parse_stage_delegates_to_engine(monkeypatch):
    captured = {}

    def fake_run_stage(name, py, cfg, cwd):
        captured["name"] = name
        captured["py"] = py
        captured["cfg"] = cfg
        captured["cwd"] = cwd
        return {"exit_code": 0, "output": "ok", "status": "PASS"}

    monkeypatch.setattr(regression_wf, "run_stage", fake_run_stage)

    cfg = {
        "input_file": "data/samples/customers.txt",
        "mapping": "config/mappings/customer_mapping.json",
        "use_chunked": True,
        "chunk_size": 123,
    }
    out = regression_wf._parse_stage("python", cfg)

    assert out["exit_code"] == 0
    assert captured["name"] == "parse"
    assert captured["cfg"]["chunk_size"] == 123
    assert captured["cfg"]["use_chunked"] is True


def test_manifest_run_validate_delegates_to_engine(monkeypatch, tmp_path):
    captured = {}

    def fake_run_stage(name, py, cfg, cwd):
        captured["name"] = name
        captured["py"] = py
        captured["cfg"] = cfg
        captured["cwd"] = cwd
        return {"exit_code": 0, "output": "ok", "status": "PASS"}

    monkeypatch.setattr(manifest_wf, "run_stage", fake_run_stage)

    rc, output = manifest_wf.run_validate(
        project_root=Path.cwd(),
        py=Path("python"),
        data_file=tmp_path / "in.txt",
        mapping_file=tmp_path / "map.json",
        rules_file=None,
        report_file=tmp_path / "report.html",
        chunked=True,
        chunk_size=500,
    )

    assert rc == 0
    assert output == "ok"
    assert captured["name"] == "validate"
    assert captured["cfg"]["use_chunked"] is True
    assert captured["cfg"]["chunk_size"] == 500
