from __future__ import annotations

import json
from typing import Any

from src.comparators.chunked_comparator import ChunkedFileComparator
from src.comparators.file_comparator import FileComparator
from src.parsers.fixed_width_parser import FixedWidthParser
from src.parsers.format_detector import FormatDetector


def _build_fixed_width_specs(cfg: dict[str, Any]) -> list[tuple[str, int, int]]:
    field_specs = []
    current_pos = 0
    for field in cfg.get('fields', []):
        name = field['name']
        length = int(field['length'])
        if field.get('position') is not None:
            start = int(field['position']) - 1
        else:
            start = current_pos
        end = start + length
        field_specs.append((name, start, end))
        current_pos = end
    return field_specs


def run_compare_service(
    file1: str,
    file2: str,
    keys: str | None = None,
    mapping: str | None = None,
    detailed: bool = True,
    chunk_size: int = 100000,
    progress: bool = False,
    use_chunked: bool = False,
) -> dict[str, Any]:
    """Shared compare workflow used by CLI and API."""
    key_columns = [k.strip() for k in keys.split(',')] if keys else None

    if use_chunked:
        if not key_columns:
            raise ValueError("Row-by-row comparison is not supported with chunked processing; provide keys.")

        delimiter = ','
        if file1.endswith('.txt') or file1.endswith('.dat'):
            delimiter = '|'

        comparator = ChunkedFileComparator(
            file1, file2, key_columns,
            delimiter=delimiter,
            chunk_size=chunk_size,
        )
        return comparator.compare(detailed=detailed, show_progress=progress)

    detector = FormatDetector()
    mapping_config = None
    if mapping:
        with open(mapping, 'r', encoding='utf-8') as f:
            mapping_config = json.load(f)

    parser1_class = detector.get_parser_class(file1)
    if parser1_class == FixedWidthParser:
        if not (mapping_config and mapping_config.get('fields')):
            raise ValueError("fixed-width compare requires mapping with fields/length metadata")
        parser1 = FixedWidthParser(file1, _build_fixed_width_specs(mapping_config))
    else:
        parser1 = parser1_class(file1)

    parser2_class = detector.get_parser_class(file2)
    if parser2_class == FixedWidthParser:
        if not (mapping_config and mapping_config.get('fields')):
            raise ValueError("fixed-width compare requires mapping with fields/length metadata")
        parser2 = FixedWidthParser(file2, _build_fixed_width_specs(mapping_config))
    else:
        parser2 = parser2_class(file2)

    df1 = parser1.parse()
    df2 = parser2.parse()

    if key_columns and any(k not in df1.columns for k in key_columns):
        try:
            import pandas as pd

            # Header-derived fallback for delimited files.
            df1h = pd.read_csv(file1, sep='|', dtype=str, keep_default_na=False, header=0)
            df2h = pd.read_csv(file2, sep='|', dtype=str, keep_default_na=False, header=0)
            if all(k in df1h.columns for k in key_columns) and all(k in df2h.columns for k in key_columns):
                df1, df2 = df1h, df2h
            elif mapping_config and mapping_config.get('fields'):
                # Mapping-derived fallback for files without header rows.
                names = [f.get('name') for f in mapping_config.get('fields', []) if f.get('name')]
                if names:
                    df1m = pd.read_csv(file1, sep='|', dtype=str, keep_default_na=False, header=None, names=names)
                    df2m = pd.read_csv(file2, sep='|', dtype=str, keep_default_na=False, header=None, names=names)
                    if all(k in df1m.columns for k in key_columns) and all(k in df2m.columns for k in key_columns):
                        df1, df2 = df1m, df2m
        except Exception:
            pass

    comparator = FileComparator(df1, df2, key_columns)
    return comparator.compare(detailed=detailed)
