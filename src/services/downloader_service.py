"""File downloader service — path validation, browse, archive handling, and search."""

import fnmatch
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Optional

_ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".zip")
_MAX_SEARCH_RESULTS = 50


def _is_archive(name: str) -> bool:
    return any(name.endswith(s) for s in _ARCHIVE_SUFFIXES)


@dataclass
class BrowseEntry:
    """A file or archive entry returned by browse_path."""

    name: str
    type: Literal["plain", "archive"]
    size_bytes: int


@dataclass
class SearchHit:
    """A single line match from a search operation."""

    file: str
    line: int
    content: str
    archive: Optional[str] = None


@dataclass
class DownloadRef:
    """Reference for the UI to issue a targeted download after a truncated search."""

    path: str
    filename: str
    archive: Optional[str] = None


@dataclass
class SearchResult:
    """Result of a search operation."""

    results: list = field(default_factory=list)
    truncated: bool = False
    total_matches: int = 0
    shown: int = 0
    download_ref: Optional[DownloadRef] = None


def validate_path(requested: str, allowed_paths: list[str]) -> Path:
    """Resolve *requested* and verify it is under one of *allowed_paths*.

    Args:
        requested: Path string from user input or config.
        allowed_paths: Allowed base paths from file-downloader.yml.

    Returns:
        Resolved ``Path``.

    Raises:
        ValueError: If *requested* is not under any allowed base path.
    """
    resolved = Path(requested).resolve()
    for allowed in allowed_paths:
        try:
            resolved.relative_to(Path(allowed).resolve())
            return resolved
        except ValueError:
            continue
    raise ValueError(f"Path '{requested}' is not within any configured allowed path")


def browse_path(path: Path, pattern: Optional[str] = None) -> list:
    """List files in *path*, optionally filtered by *pattern*.

    Args:
        path: Directory to list (already validated).
        pattern: Optional ``fnmatch`` wildcard (e.g. ``"batch_*.tar.gz"``).

    Returns:
        Sorted list of :class:`BrowseEntry` objects (directories excluded).
    """
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    entries: list[BrowseEntry] = []
    for item in sorted(path.iterdir()):
        if not item.is_file():
            continue
        if pattern and not fnmatch.fnmatch(item.name, pattern):
            continue
        entry_type: Literal["plain", "archive"] = "archive" if _is_archive(item.name) else "plain"
        entries.append(BrowseEntry(name=item.name, type=entry_type, size_bytes=item.stat().st_size))
    return entries
