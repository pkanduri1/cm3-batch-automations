"""Schema drift detector — detects when a file's layout differs from its mapping.

Fixed-width files are sensitive to layout changes: an upstream producer adding
or removing bytes causes all downstream field positions to silently shift.  This
module implements a heuristic detector that samples the first 20 non-blank
lines of a file and checks whether each field's declared start position begins
with non-whitespace content.  When a field's expected start is consistently
blank but a nearby position has non-blank content, a drift record is emitted.
"""

from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_SIZE = 20
_MIN_SAMPLE_LINES = 3
_LEADING_BLANK_THRESHOLD = 0.8   # >80% of lines have blank at expected start → suspect drift
_CONTENT_RATIO_THRESHOLD = 0.5   # >50% of lines must have boundary-start to accept position
_SEARCH_RADIUS = 15              # bytes left/right of expected position to scan
_SEARCH_MAX_POS = 200            # upper bound for position scan
_LARGE_OFFSET_THRESHOLD = 5     # offsets larger than this → severity='error'


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _detect_fixed_width_drift(lines: list[str], mapping: dict[str, Any]) -> dict[str, Any]:
    """Detect position/width drift in a fixed-width file.

    Samples the first ``_SAMPLE_SIZE`` non-blank lines and checks whether each
    field's declared byte position begins with non-whitespace.  When more than
    80 % of sample lines have whitespace at the declared start byte and a
    nearby position has a clear content boundary in more than 50 % of lines,
    the field is reported as drifted.

    Args:
        lines: List of text lines from the file (newlines may be present but
            are not stripped — callers may pass raw ``file.readlines()`` output).
        mapping: Mapping dict with a ``'fields'`` list.  Each field entry must
            have ``'name'`` and ``'length'`` keys.  ``'position'`` is a 1-indexed
            byte offset; when absent, the field is skipped.

    Returns:
        On success::

            {'drifted': bool, 'fields': list[dict]}

        Each entry in ``fields`` has keys:
            ``name``, ``expected_start`` (1-indexed), ``expected_length``,
            ``actual_start`` (1-indexed), ``actual_length``, ``severity``
            (``'warning'`` for offset <= 5, ``'error'`` for offset > 5).

        On early exit::

            {'drifted': False, 'fields': [], 'skipped': True, 'reason': str}

        Possible ``reason`` values: ``'too_short'``, ``'no_fields'``.
    """
    sample = [line for line in lines if line.strip()][:_SAMPLE_SIZE]

    if len(sample) < _MIN_SAMPLE_LINES:
        return {"drifted": False, "fields": [], "skipped": True, "reason": "too_short"}

    fields = mapping.get("fields", [])
    if not fields:
        return {"drifted": False, "fields": [], "skipped": True, "reason": "no_fields"}

    drifted_fields: list[dict[str, Any]] = []

    for field in fields:
        name = field.get("name", "")
        position = field.get("position")  # 1-indexed byte offset; may be absent
        length = field.get("length", 0)

        if not length:
            continue

        # When position is absent the field carries no positional information
        # and cannot be drift-checked.
        if position is None:
            continue

        begin = int(position) - 1  # convert to 0-indexed
        length_int = int(length)

        # Drift signal: count lines where the expected start byte is blank.
        # A consistently blank start byte means content did not begin here.
        leading_blank_count = sum(
            1
            for line in sample
            if len(line) <= begin or not line[begin : begin + 1].strip()
        )
        leading_blank_ratio = leading_blank_count / len(sample)

        if leading_blank_ratio > _LEADING_BLANK_THRESHOLD:
            actual_begin = _find_actual_position(sample, begin, length_int)
            if actual_begin is not None and actual_begin != begin:
                offset = abs(actual_begin - begin)
                severity = "error" if offset > _LARGE_OFFSET_THRESHOLD else "warning"
                drifted_fields.append(
                    {
                        "name": name,
                        "expected_start": int(position),       # 1-indexed
                        "expected_length": length_int,
                        "actual_start": actual_begin + 1,      # back to 1-indexed
                        "actual_length": length_int,
                        "severity": severity,
                    }
                )

    return {
        "drifted": len(drifted_fields) > 0,
        "fields": drifted_fields,
    }


def _find_actual_position(
    sample: list[str],
    expected_begin: int,
    length: int,
) -> Optional[int]:
    """Scan nearby byte positions to find where content actually begins.

    Uses a "boundary-start" heuristic: a position scores a point for each
    sample line where that byte is non-whitespace AND the preceding byte is
    whitespace (or it is position 0).  This identifies where a field's content
    starts rather than where it merely overlaps.

    Searches within ``_SEARCH_RADIUS`` bytes on either side of ``expected_begin``
    (excluding ``expected_begin`` itself) for the position whose boundary-start
    score exceeds 50 % of sample lines.

    Args:
        sample: Non-blank lines to inspect (already filtered).
        expected_begin: 0-indexed byte offset that is known to be mostly blank.
        length: Field byte length (used only to bound the line-length check).

    Returns:
        The 0-indexed byte offset of the best candidate position, or ``None``
        when no candidate exceeds the 50 % boundary-start threshold.
    """
    low = max(0, expected_begin - _SEARCH_RADIUS)
    high = min(_SEARCH_MAX_POS, expected_begin + _SEARCH_RADIUS)

    best_pos: Optional[int] = None
    best_score = 0

    for pos in range(low, high):
        if pos == expected_begin:
            continue

        boundary_start_count = sum(
            1
            for line in sample
            if len(line) >= pos + 1
            and line[pos : pos + 1].strip()                   # current byte is non-blank
            and (pos == 0 or not line[pos - 1 : pos].strip()) # preceding byte is blank (or start)
        )

        if boundary_start_count > best_score:
            best_score = boundary_start_count
            best_pos = pos

    threshold = len(sample) * _CONTENT_RATIO_THRESHOLD
    return best_pos if best_score > threshold else None
