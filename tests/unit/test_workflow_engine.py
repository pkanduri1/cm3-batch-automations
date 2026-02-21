from pathlib import Path

from src.workflows.engine import build_validate_cmd, resolve_path, run_stage, stage_registry


ROOT = Path(__file__).resolve().parents[2]


def test_resolve_path_handles_relative_and_absolute():
    rel = resolve_path("data/samples/customers.txt", ROOT)
    assert str(rel).endswith("data/samples/customers.txt")

    abs_in = str(ROOT / "data/samples/customers.txt")
    abs_out = resolve_path(abs_in, ROOT)
    assert str(abs_out) == abs_in


def test_build_validate_cmd_includes_strict_flags():
    cmd = build_validate_cmd(
        py="python",
        cfg={
            "input_file": "in.txt",
            "mapping": "m.json",
            "detailed": False,
            "strict_fixed_width": True,
            "strict_level": "format",
        },
    )
    assert "--basic" in cmd
    assert "--strict-fixed-width" in cmd
    assert "--strict-level" in cmd


def test_stage_registry_and_run_stage_error():
    assert "parse" in stage_registry()
    try:
        run_stage("unknown", "python", {}, ROOT)
        assert False, "expected ValueError"
    except ValueError:
        assert True
