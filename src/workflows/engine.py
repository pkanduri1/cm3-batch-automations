from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Callable


StageBuilder = Callable[[str, dict[str, Any]], list[str]]
_STAGE_REGISTRY: dict[str, StageBuilder] = {}


def resolve_path(path_value: str | None, project_root: Path) -> Path | None:
    if not path_value:
        return None
    p = Path(path_value)
    return p if p.is_absolute() else project_root / p


def telemetry_envelope(stage: str, cmd: list[str], exit_code: int, output: str, duration_seconds: float) -> dict[str, Any]:
    return {
        "stage": stage,
        "command": " ".join(cmd),
        "exit_code": exit_code,
        "duration_seconds": round(duration_seconds, 3),
        "output": output.strip(),
        "status": "PASS" if exit_code == 0 else "FAIL",
    }


def run_subprocess(cmd: list[str], cwd: Path, stage: str = "stage") -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return telemetry_envelope(stage, cmd, proc.returncode, out, time.perf_counter() - started)


def register_stage(name: str):
    def _decorator(builder: StageBuilder):
        _STAGE_REGISTRY[name] = builder
        return builder
    return _decorator


def run_stage(name: str, py: str, cfg: dict[str, Any], cwd: Path) -> dict[str, Any]:
    if name not in _STAGE_REGISTRY:
        raise ValueError(f"Unknown workflow stage: {name}")
    cmd = _STAGE_REGISTRY[name](py, cfg)
    return run_subprocess(cmd, cwd, stage=name)


@register_stage("parse")
def build_parse_cmd(
    py: str,
    cfg: dict[str, Any],
) -> list[str]:
    cmd = [py, "-m", "src.main", "parse", "-f", cfg["input_file"], "-m", cfg["mapping"]]
    if cfg.get("output"):
        cmd.extend(["-o", cfg["output"]])
    if cfg.get("format"):
        cmd.extend(["--format", cfg["format"]])
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000))])
    return cmd


@register_stage("validate")
def build_validate_cmd(
    py: str,
    cfg: dict[str, Any],
) -> list[str]:
    cmd = [py, "-m", "src.main", "validate", "-f", cfg["input_file"], "-m", cfg["mapping"]]
    if cfg.get("rules"):
        cmd.extend(["-r", cfg["rules"]])
    if cfg.get("output"):
        cmd.extend(["-o", cfg["output"]])
    cmd.append("--detailed" if cfg.get("detailed", True) else "--basic")
    if cfg.get("strict_fixed_width"):
        cmd.append("--strict-fixed-width")
        if cfg.get("strict_level"):
            cmd.extend(["--strict-level", cfg["strict_level"]])
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000))])
        cmd.append("--progress" if cfg.get("progress", False) else "--no-progress")
    return cmd


@register_stage("compare")
def build_compare_cmd(
    py: str,
    cfg: dict[str, Any],
) -> list[str]:
    cmd = [py, "-m", "src.main", "compare", "-f1", cfg["baseline_file"], "-f2", cfg["current_file"]]
    if cfg.get("keys"):
        cmd.extend(["-k", cfg["keys"]])
    if cfg.get("mapping"):
        cmd.extend(["-m", cfg["mapping"]])
    if cfg.get("output"):
        cmd.extend(["-o", cfg["output"]])
    cmd.append("--detailed" if cfg.get("detailed", True) else "--basic")
    if cfg.get("use_chunked"):
        cmd.extend(["--use-chunked", "--chunk-size", str(cfg.get("chunk_size", 100000)), "--no-progress"])
    return cmd


def stage_registry() -> dict[str, StageBuilder]:
    return dict(_STAGE_REGISTRY)
