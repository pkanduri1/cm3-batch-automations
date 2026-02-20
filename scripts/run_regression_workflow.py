#!/usr/bin/env python3
"""Run an end-to-end regression workflow: parse -> validate -> compare.

Configuration is provided via JSON (see config/pipeline/regression_workflow.sample.json).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    p = Path(path_value)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _run(cmd: List[str]) -> Dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True)
    duration = round(time.perf_counter() - started, 3)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "duration_seconds": duration,
        "output": out.strip(),
        "status": "PASS" if proc.returncode == 0 else "FAIL",
    }


def _parse_stage(py: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [py, "-m", "src.main", "parse", "-f", str(_resolve(cfg["input_file"])), "-m", str(_resolve(cfg["mapping"]))]
    if cfg.get("output"):
        out = _resolve(cfg["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["-o", str(out)])
    if cfg.get("format"):
        cmd.extend(["--format", str(cfg["format"])])
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000))])
    return _run(cmd)


def _validate_stage(py: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [py, "-m", "src.main", "validate", "-f", str(_resolve(cfg["input_file"])), "-m", str(_resolve(cfg["mapping"]))]
    if cfg.get("rules"):
        cmd.extend(["-r", str(_resolve(cfg["rules"]))])
    if cfg.get("output"):
        out = _resolve(cfg["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["-o", str(out)])
    if cfg.get("detailed", True):
        cmd.append("--detailed")
    if cfg.get("strict_fixed_width"):
        cmd.append("--strict-fixed-width")
        if cfg.get("strict_level"):
            cmd.extend(["--strict-level", str(cfg["strict_level"])])
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000)), "--no-progress"])
    return _run(cmd)


def _compare_stage(py: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        py,
        "-m",
        "src.main",
        "compare",
        "-f1",
        str(_resolve(cfg["baseline_file"])),
        "-f2",
        str(_resolve(cfg["current_file"])),
    ]
    if cfg.get("keys"):
        cmd.extend(["-k", str(cfg["keys"])])
    if cfg.get("mapping"):
        cmd.extend(["-m", str(_resolve(cfg["mapping"]))])
    if cfg.get("output"):
        out = _resolve(cfg["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["-o", str(out)])
    if cfg.get("detailed", True):
        cmd.append("--detailed")
    else:
        cmd.append("--basic")
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000)), "--no-progress"])
    return _run(cmd)


def _require(cfg: Dict[str, Any], fields: List[str], stage: str) -> None:
    missing = [f for f in fields if not cfg.get(f)]
    if missing:
        raise ValueError(f"{stage}: missing required field(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/pipeline/regression_workflow.sample.json", help="Workflow config JSON path")
    parser.add_argument("--summary-out", default="reports/regression_workflow/summary.json", help="Summary output JSON path")
    args = parser.parse_args()

    cfg_path = _resolve(args.config)
    if not cfg_path or not cfg_path.exists():
        print(f"❌ Config not found: {args.config}")
        return 1

    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    py = str(PROJECT_ROOT / ".venv" / "bin" / "python")

    results: Dict[str, Any] = {
        "workflow_name": config.get("name", "regression_workflow"),
        "config_file": str(cfg_path.relative_to(PROJECT_ROOT)) if cfg_path.is_relative_to(PROJECT_ROOT) else str(cfg_path),
        "started_at_epoch": int(time.time()),
        "stages": {},
    }

    fail_fast = bool(config.get("gates", {}).get("fail_fast", True))
    overall_pass = True

    try:
        parse_cfg = config.get("parse", {})
        if parse_cfg.get("enabled"):
            _require(parse_cfg, ["input_file", "mapping"], "parse")
            print("▶ Running parse stage...")
            r = _parse_stage(py, parse_cfg)
            results["stages"]["parse"] = r
            print(r["output"])
            if r["exit_code"] != 0:
                overall_pass = False
                if fail_fast:
                    raise RuntimeError("parse stage failed")

        validate_cfg = config.get("validate", {})
        if validate_cfg.get("enabled"):
            _require(validate_cfg, ["input_file", "mapping"], "validate")
            print("▶ Running validate stage...")
            r = _validate_stage(py, validate_cfg)
            results["stages"]["validate"] = r
            print(r["output"])
            if r["exit_code"] != 0:
                overall_pass = False
                if fail_fast:
                    raise RuntimeError("validate stage failed")

        compare_cfg = config.get("compare", {})
        if compare_cfg.get("enabled"):
            _require(compare_cfg, ["baseline_file", "current_file"], "compare")
            if compare_cfg.get("use_chunked") and not compare_cfg.get("keys"):
                raise ValueError("compare: keys are required when use_chunked=true")
            print("▶ Running compare stage...")
            r = _compare_stage(py, compare_cfg)
            results["stages"]["compare"] = r
            print(r["output"])
            if r["exit_code"] != 0:
                overall_pass = False
                if fail_fast:
                    raise RuntimeError("compare stage failed")

    except Exception as exc:
        results["error"] = str(exc)
        overall_pass = False

    results["overall_status"] = "PASS" if overall_pass else "FAIL"
    results["completed_at_epoch"] = int(time.time())

    summary_path = _resolve(args.summary_out)
    assert summary_path is not None
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\n📄 Summary: {summary_path}")
    print(f"🏁 Overall: {results['overall_status']}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
