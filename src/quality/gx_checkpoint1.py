"""Great Expectations Checkpoint 1 runner (BA-friendly, config-first)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class TargetConfig:
    target_id: str
    data_file: str
    delimiter: str = "|"
    has_header: bool = False
    mapping_file: str | None = None
    key_columns: list[str] | None = None
    required_columns: list[str] | None = None


@dataclass
class ExpectationConfig:
    target_id: str
    expectation_type: str
    enabled: bool = True
    column: str | None = None
    column_list: list[str] | None = None
    value_set: list[str] | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    mostly: float | None = None
    notes: str | None = None


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _as_list(value: str | None) -> list[str] | None:
    if value is None or str(value).strip() == "":
        return None
    return [x.strip() for x in str(value).split("|") if x.strip()]


def _as_number(value: str | None) -> float | int | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    return float(text)


def _load_mapping_columns(mapping_file: str) -> list[str]:
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    if "fields" in mapping:
        return [f["name"] for f in mapping["fields"]]
    if "mappings" in mapping:
        return [m["source_column"] for m in mapping["mappings"]]
    raise ValueError(f"Unsupported mapping format in {mapping_file}")


def load_targets_csv(path: str) -> list[TargetConfig]:
    targets: list[TargetConfig] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"target_id", "data_file"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Targets file must include columns: {sorted(required)}")

        for row in reader:
            if _as_bool(row.get("enabled"), default=True) is False:
                continue
            targets.append(
                TargetConfig(
                    target_id=row["target_id"].strip(),
                    data_file=row["data_file"].strip(),
                    delimiter=(row.get("delimiter") or "|").strip() or "|",
                    has_header=_as_bool(row.get("has_header"), default=False),
                    mapping_file=(row.get("mapping_file") or "").strip() or None,
                    key_columns=_as_list(row.get("key_columns")),
                    required_columns=_as_list(row.get("required_columns")),
                )
            )
    return targets


def load_expectations_csv(path: str) -> list[ExpectationConfig]:
    expectations: list[ExpectationConfig] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"target_id", "expectation_type"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Expectations file must include columns: {sorted(required)}")

        for row in reader:
            if _as_bool(row.get("enabled"), default=True) is False:
                continue
            expectations.append(
                ExpectationConfig(
                    target_id=row["target_id"].strip(),
                    expectation_type=row["expectation_type"].strip(),
                    enabled=True,
                    column=(row.get("column") or "").strip() or None,
                    column_list=_as_list(row.get("column_list")),
                    value_set=_as_list(row.get("value_set")),
                    min_value=_as_number(row.get("min_value")),
                    max_value=_as_number(row.get("max_value")),
                    mostly=_as_number(row.get("mostly")),
                    notes=(row.get("notes") or "").strip() or None,
                )
            )
    return expectations


def _read_target_data(target: TargetConfig) -> pd.DataFrame:
    header = 0 if target.has_header else None
    df = pd.read_csv(target.data_file, sep=target.delimiter, dtype=str, header=header)

    if not target.has_header:
        if target.mapping_file:
            df.columns = _load_mapping_columns(target.mapping_file)
        else:
            df.columns = [f"col_{i+1}" for i in range(df.shape[1])]
    return df


def _add_default_expectations(validator: Any, target: TargetConfig, df: pd.DataFrame) -> None:
    if target.mapping_file:
        expected_columns = _load_mapping_columns(target.mapping_file)
        validator.expect_table_columns_to_match_ordered_list(column_list=expected_columns)

    if target.required_columns:
        for col in target.required_columns:
            validator.expect_column_values_to_not_be_null(column=col)

    if target.key_columns:
        for col in target.key_columns:
            validator.expect_column_values_to_not_be_null(column=col)
            validator.expect_column_values_to_be_unique(column=col)

    validator.expect_table_row_count_to_be_between(min_value=1, max_value=max(len(df), 1_000_000_000))


def _apply_expectation(validator: Any, exp: ExpectationConfig) -> None:
    et = exp.expectation_type

    if et == "expect_table_columns_to_match_ordered_list":
        validator.expect_table_columns_to_match_ordered_list(column_list=exp.column_list or [])
    elif et == "expect_column_values_to_not_be_null":
        validator.expect_column_values_to_not_be_null(column=exp.column)
    elif et == "expect_column_values_to_be_unique":
        validator.expect_column_values_to_be_unique(column=exp.column)
    elif et == "expect_column_values_to_be_in_set":
        validator.expect_column_values_to_be_in_set(column=exp.column, value_set=exp.value_set or [])
    elif et == "expect_column_values_to_be_between":
        kwargs: dict[str, Any] = {"column": exp.column, "min_value": exp.min_value, "max_value": exp.max_value}
        if exp.mostly is not None:
            kwargs["mostly"] = exp.mostly
        validator.expect_column_values_to_be_between(**kwargs)
    elif et == "expect_table_row_count_to_be_between":
        validator.expect_table_row_count_to_be_between(min_value=exp.min_value, max_value=exp.max_value)
    else:
        raise ValueError(f"Unsupported expectation_type: {et}")


def run_checkpoint_1(
    targets_csv: str,
    expectations_csv: str,
    output_json: str | None = None,
    data_docs_dir: str | None = None,
) -> dict[str, Any]:
    try:
        import great_expectations as gx
    except ImportError as exc:
        raise RuntimeError(
            "Great Expectations is not installed. Install with: pip install great_expectations"
        ) from exc

    targets = load_targets_csv(targets_csv)
    expectations = load_expectations_csv(expectations_csv)

    exp_by_target: dict[str, list[ExpectationConfig]] = {}
    for exp in expectations:
        exp_by_target.setdefault(exp.target_id, []).append(exp)

    context = gx.get_context(mode="ephemeral")

    run_results: list[dict[str, Any]] = []
    overall_success = True

    for target in targets:
        df = _read_target_data(target)

        ds_name = "cm3_checkpoint1_ds"
        suite_name = f"checkpoint1_{target.target_id}"
        asset_name = f"{target.target_id}_asset"
        batch_def_name = f"{target.target_id}_whole_df"

        datasource = context.data_sources.add_or_update_pandas(name=ds_name)
        asset = datasource.add_dataframe_asset(name=asset_name)
        batch_definition = asset.add_batch_definition_whole_dataframe(batch_def_name)

        batch_request = batch_definition.build_batch_request(options={"dataframe": df})
        validator = context.get_validator(batch_request=batch_request, expectation_suite_name=suite_name)

        _add_default_expectations(validator, target, df)
        for exp in exp_by_target.get(target.target_id, []):
            _apply_expectation(validator, exp)

        checkpoint = context.checkpoints.add_or_update(
            gx.Checkpoint(
                name=f"checkpoint1_{target.target_id}",
                validations=[
                    {
                        "batch_request": batch_request,
                        "expectation_suite_name": suite_name,
                    }
                ],
            )
        )

        result = checkpoint.run()
        success = bool(result.get("success", False))
        overall_success = overall_success and success
        run_results.append(
            {
                "target_id": target.target_id,
                "success": success,
                "result": result.to_json_dict() if hasattr(result, "to_json_dict") else result,
            }
        )

    summary = {
        "success": overall_success,
        "targets_run": len(targets),
        "targets": run_results,
    }

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if data_docs_dir:
        context.build_data_docs()

    return summary
